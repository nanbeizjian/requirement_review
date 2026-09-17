import asyncio
from collections import Counter
from importlib import import_module

import pytest
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from requirement_review.domain.models import (
    DataPolicy,
    KnowledgeChunk,
    ReviewDimension,
    ReviewFinding,
)
from requirement_review.knowledge.service import KnowledgeService


class EmptySource:
    async def search(self, query, project_id, filters):
        return []


class ReviewModel:
    def __init__(self, failures=(), barrier=False):
        self.failures = set(failures)
        self.calls = Counter()
        self.barrier = asyncio.Event() if barrier else None

    async def review(
        self, *, project_id, data_policy, dimension, requirement, knowledge
    ):
        assert project_id == "project-1"
        assert data_policy == DataPolicy.LOCAL_ONLY
        self.calls[dimension] += 1
        if self.barrier:
            if len(self.calls) == 8:
                self.barrier.set()
            await asyncio.wait_for(self.barrier.wait(), timeout=2)
        if dimension in self.failures:
            raise RuntimeError("private requirement text must not leak")
        return [
            ReviewFinding(
                requirement_id=requirement.requirement_id,
                dimension=dimension,
                severity="medium",
                issue=f"{dimension} issue v{self.calls[dimension]}",
                impact="Unclear behavior",
                recommendation="Specify acceptance criteria",
                confidence=0.8,
                evidence=[requirement.evidence],
                uses_system_fact=False,
            )
        ]


@pytest.fixture
def initial_state():
    return {
        "review_id": "review-1",
        "project_id": "project-1",
        "document_id": "doc-1",
        "document_version": 3,
        "document_text": "# Login\nUsers can log in.",
        "data_policy": DataPolicy.LOCAL_ONLY,
    }


def make_graph(model=None, source=None, checkpointer=None):
    # A missing graph is an explicit feature failure, not a collection error.
    try:
        workflow = import_module("requirement_review.graph.workflow")
        nodes = import_module("requirement_review.review.nodes")
    except ModuleNotFoundError as exc:
        pytest.fail(f"Review workflow is not implemented: {exc}")
    services = nodes.ReviewServices(
        knowledge_service=KnowledgeService(source or EmptySource()),
        model_gateway=model or ReviewModel(),
    )
    return workflow.build_review_graph(services, checkpointer or InMemorySaver())


def config(thread="review-1"):
    return {"configurable": {"thread_id": thread}}


async def test_fanout_runs_all_dimensions_concurrently_and_joins_once(initial_state):
    graph = make_graph(ReviewModel(barrier=True))
    result = await graph.ainvoke(initial_state, config())
    assert result["status"] == "WAITING_APPROVAL"
    assert len(result["findings"]) == 8
    assert result["failed_dimensions"] == []
    assert len(result["__interrupt__"]) == 1
    assert all(finding.finding_id for finding in result["findings"])
    assert result["findings"][0].evidence[0].version == 3


async def test_graph_interrupts_and_resumes_same_thread_after_rebuild(initial_state):
    saver = InMemorySaver()
    graph = make_graph(checkpointer=saver)
    result = await graph.ainvoke(initial_state, config())
    assert "__interrupt__" in result
    snapshot = await graph.aget_state(config())
    assert snapshot.values["status"] == "WAITING_APPROVAL"
    resumed = make_graph(checkpointer=saver)
    final = await resumed.ainvoke(
        Command(resume={"action": "approve", "actor_id": "u1"}), config()
    )
    assert final["status"] == "COMPLETED"
    assert final["approval"]["actor_id"] == "u1"
    assert not (await resumed.aget_state(config())).next


async def test_modify_consolidates_edits_and_requires_another_approval(initial_state):
    graph = make_graph()
    first = await graph.ainvoke(initial_state, config())
    finding = first["findings"][0].model_dump(mode="json")
    finding["issue"] = "Reviewer amended issue"
    modified = await graph.ainvoke(
        Command(
            resume={
                "action": "modify",
                "actor_id": "u1",
                "findings": [finding],
            }
        ),
        config(),
    )
    assert modified["status"] == "WAITING_APPROVAL"
    assert "__interrupt__" in modified
    assert [f.issue for f in modified["findings"]] == ["Reviewer amended issue"]
    final = await graph.ainvoke(
        Command(resume={"action": "approve", "actor_id": "u1"}), config()
    )
    assert final["status"] == "COMPLETED"
    assert len(final["findings"]) == 1


@pytest.mark.parametrize("action", ["re-review", "reject"])
async def test_rereview_replaces_only_selected_dimension_and_reapproves(
    initial_state, action
):
    graph = make_graph()
    first = await graph.ainvoke(initial_state, config())
    again = await graph.ainvoke(
        Command(
            resume={
                "action": action,
                "actor_id": "u1",
                "dimensions": ["security"],
            }
        ),
        config(),
    )
    assert again["status"] == "WAITING_APPROVAL"
    assert "__interrupt__" in again
    assert len(again["findings"]) == 8
    assert [f.issue for f in again["findings"] if f.dimension == "security"] == [
        "security issue v2"
    ]
    assert [f for f in again["findings"] if f.dimension != "security"] == [
        f for f in first["findings"] if f.dimension != "security"
    ]


async def test_one_dimension_failure_is_visible_and_can_recover(initial_state):
    model = ReviewModel(failures={"security"})
    graph = make_graph(model)
    result = await graph.ainvoke(initial_state, config())
    assert result["status"] == "WAITING_APPROVAL"
    assert result["failed_dimensions"] == ["security"]
    assert len(result["findings"]) == 7
    assert "private requirement text" not in str(result)
    model.failures.clear()
    recovered = await graph.ainvoke(
        Command(
            resume={
                "action": "re-review",
                "actor_id": "u1",
                "dimensions": ["security"],
            }
        ),
        config(),
    )
    assert recovered["failed_dimensions"] == []
    assert len(recovered["findings"]) == 8


async def test_requirement_level_model_failure_preserves_other_findings(
    initial_state,
):
    class OneRequirementFails(ReviewModel):
        async def review(self, **kwargs):
            if (
                kwargs["dimension"] == ReviewDimension.SECURITY
                and kwargs["requirement"].requirement_id == "REQ-002"
            ):
                raise RuntimeError("private requirement text must not leak")
            return await super().review(**kwargs)

    text = "# Login\n\nUsers can log in.\n\nUsers can log out."
    result = await make_graph(OneRequirementFails()).ainvoke(
        {**initial_state, "document_text": text}, config()
    )

    assert result["status"] == "WAITING_APPROVAL"
    assert result["failed_dimensions"] == ["security"]
    assert len(result["findings"]) == 15
    assert [
        finding.requirement_id
        for finding in result["findings"]
        if finding.dimension == ReviewDimension.SECURITY
    ] == ["REQ-001"]
    assert "private requirement text" not in str(result)


async def test_all_dimensions_failing_blocks_approval(initial_state):
    graph = make_graph(ReviewModel(failures=set(ReviewDimension)))
    result = await graph.ainvoke(initial_state, config())
    assert result["status"] == "FAILED"
    assert len(result["failed_dimensions"]) == 8
    assert "__interrupt__" not in result
    assert result["errors"]


@pytest.mark.parametrize(
    "text", ["# Only heading", "x" * 100_001], ids=["empty", "oversize"]
)
async def test_parse_failure_blocks_review(initial_state, text):
    graph = make_graph()
    result = await graph.ainvoke({**initial_state, "document_text": text}, config())
    assert result["status"] == "FAILED"
    assert "__interrupt__" not in result
    assert not result.get("findings")


async def test_knowledge_permission_failure_blocks_review(initial_state):
    class ForbiddenSource:
        async def search(self, query, project_id, filters):
            raise PermissionError("private access detail")

    result = await make_graph(source=ForbiddenSource()).ainvoke(initial_state, config())
    assert result["status"] == "FAILED"
    assert "__interrupt__" not in result
    assert "private access detail" not in str(result)


async def test_dimension_permission_failure_is_blocking_not_degraded(initial_state):
    class ForbiddenModel(ReviewModel):
        async def review(self, **kwargs):
            if kwargs["dimension"] == "security":
                raise PermissionError("private access detail")
            return await super().review(**kwargs)

    result = await make_graph(ForbiddenModel()).ainvoke(initial_state, config())
    assert result["status"] == "FAILED"
    assert "__interrupt__" not in result


async def test_untrusted_model_citations_do_not_enter_findings(initial_state):
    class UntrustedModel(ReviewModel):
        async def review(self, **kwargs):
            findings = await super().review(**kwargs)
            findings[0].evidence[0] = (
                findings[0].evidence[0].model_copy(update={"document_id": "invented"})
            )
            return findings

    result = await make_graph(UntrustedModel()).ainvoke(initial_state, config())
    assert result["findings"] == []
    assert result["status"] == "FAILED"


@pytest.mark.parametrize(
    "decision",
    [
        {"action": "approve"},
        {"action": "unknown", "actor_id": "u1"},
        {"action": "re-review", "actor_id": "u1", "dimensions": []},
        {"action": "re-review", "actor_id": "u1", "dimensions": ["invented"]},
    ],
)
async def test_invalid_approval_never_completes(initial_state, decision):
    graph = make_graph()
    await graph.ainvoke(initial_state, config())
    result = await graph.ainvoke(Command(resume=decision), config())
    assert result["status"] == "WAITING_APPROVAL"
    assert "__interrupt__" in result


async def test_approval_does_not_affect_other_threads(initial_state):
    graph = make_graph()
    await graph.ainvoke(initial_state, config("one"))
    await graph.ainvoke({**initial_state, "review_id": "review-2"}, config("two"))
    await graph.ainvoke(
        Command(resume={"action": "approve", "actor_id": "u1"}), config("one")
    )
    assert (await graph.aget_state(config("two"))).values[
        "status"
    ] == "WAITING_APPROVAL"


async def test_cross_project_knowledge_blocks_before_model_review(initial_state):
    class WrongProjectSource:
        async def search(self, query, project_id, filters):
            return [
                KnowledgeChunk(
                    chunk_id="secret",
                    project_id="other-project",
                    document_id="secret-doc",
                    version=1,
                    locator="root#p1",
                    text="Other project's private knowledge",
                )
            ]

    model = ReviewModel()
    result = await make_graph(model, source=WrongProjectSource()).ainvoke(
        initial_state, config()
    )
    assert result["status"] == "FAILED"
    assert result["errors"] == ["permission_denied"]
    assert not model.calls
    assert "Other project's" not in str(result)


async def test_invalid_modification_keeps_existing_findings_and_can_resume(
    initial_state,
):
    graph = make_graph()
    first = await graph.ainvoke(initial_state, config())
    invalid = first["findings"][0].model_dump(mode="json")
    invalid["evidence"][0]["document_id"] = "invented"
    paused = await graph.ainvoke(
        Command(
            resume={
                "action": "modify",
                "actor_id": "u1",
                "findings": [invalid],
            }
        ),
        config(),
    )
    assert paused["status"] == "WAITING_APPROVAL"
    assert paused["findings"] == first["findings"]
    final = await graph.ainvoke(
        Command(resume={"action": "approve", "actor_id": "u1"}), config()
    )
    assert final["status"] == "COMPLETED"


async def test_successful_reviews_with_no_findings_are_not_model_failure(initial_state):
    class CleanModel:
        async def review(self, **kwargs):
            return []

    result = await make_graph(CleanModel()).ainvoke(initial_state, config())
    assert result["status"] == "WAITING_APPROVAL"
    assert result["findings"] == []
    assert result["failed_dimensions"] == []


@pytest.mark.parametrize(
    "bad_reference", [{"locator": "missing#p999"}, {"document_id": "missing"}]
)
async def test_single_dimension_invalid_evidence_blocks_all_approval(
    initial_state, bad_reference
):
    class InvalidEvidenceModel(ReviewModel):
        async def review(self, **kwargs):
            findings = await super().review(**kwargs)
            if kwargs["dimension"] == "security":
                findings[0].evidence[0] = (
                    findings[0].evidence[0].model_copy(update=bad_reference)
                )
            return findings

    result = await make_graph(InvalidEvidenceModel()).ainvoke(initial_state, config())
    assert result["status"] == "FAILED"
    assert result["failed_dimensions"] == ["security"]
    assert result["errors"] == ["evidence_invalid"]
    assert result["dimension_results"]["security"]["error"] == "evidence_invalid"
    assert result["findings"] == []
    assert "__interrupt__" not in result


async def test_repeated_invalid_approvals_use_bounded_fresh_wait_checkpoints(
    initial_state,
):
    saver = InMemorySaver()
    graph = make_graph(checkpointer=saver)
    await graph.ainvoke(initial_state, config())
    resume_lengths = []
    interrupt_ids = []
    current_sizes = []
    untrusted_body = "UNTRUSTED_APPROVAL_BODY:" + "x" * 16_000
    for attempt in range(6):
        result = await graph.ainvoke(
            Command(
                resume={
                    "action": "unknown",
                    "actor_id": "u1",
                    "unused_body": untrusted_body,
                    "attempt": attempt,
                }
            ),
            config(),
        )
        assert result["status"] == "WAITING_APPROVAL"
        interrupt_ids.append(result["__interrupt__"][0].id)
        checkpoint = await saver.aget_tuple(config())
        resumes = [
            value
            for _, channel, value in checkpoint.pending_writes
            if channel == "__resume__"
        ]
        resume_lengths.append(
            sum(len(values) for values in resumes if isinstance(values, list))
        )
        current_sizes.append(
            len(
                repr(
                    (checkpoint.checkpoint["channel_values"], checkpoint.pending_writes)
                )
            )
        )

    assert max(resume_lengths) <= 1
    assert len(set(interrupt_ids)) == 6
    assert max(current_sizes) - min(current_sizes) < 1024
    assert untrusted_body not in repr(
        (checkpoint.checkpoint["channel_values"], checkpoint.pending_writes)
    )
    assert result["__interrupt__"][0].value["error"] == "invalid_approval"

    # Rebuild over the same saver to prove no replay of previous invalid payloads is needed.
    rebuilt = make_graph(checkpointer=saver)
    final = await rebuilt.ainvoke(
        Command(resume={"action": "approve", "actor_id": "u1"}), config()
    )
    assert final["status"] == "COMPLETED"
    assert final["approval"]["actor_id"] == "u1"


@pytest.mark.parametrize("evidence_problem", ["empty", "missing", "malformed"])
async def test_one_dimension_invalid_evidence_structure_blocks_review(
    initial_state, evidence_problem
):
    class InvalidEvidenceStructureModel(ReviewModel):
        async def review(self, **kwargs):
            findings = await super().review(**kwargs)
            if kwargs["dimension"] != "security":
                return findings
            payload = findings[0].model_dump(mode="json")
            if evidence_problem == "empty":
                payload["evidence"] = []
            elif evidence_problem == "missing":
                del payload["evidence"]
            else:
                del payload["evidence"][0]["locator"]
            return [payload]

    result = await make_graph(InvalidEvidenceStructureModel()).ainvoke(
        initial_state, config()
    )
    assert result["status"] == "FAILED"
    assert result["failed_dimensions"] == ["security"]
    assert result["errors"] == ["evidence_invalid"]
    assert result["dimension_results"]["security"]["error"] == "evidence_invalid"
    assert result["findings"] == []
    assert "__interrupt__" not in result


async def test_unrelated_model_schema_error_still_degrades_one_dimension(initial_state):
    class InvalidConfidenceModel(ReviewModel):
        async def review(self, **kwargs):
            findings = await super().review(**kwargs)
            if kwargs["dimension"] != "security":
                return findings
            payload = findings[0].model_dump(mode="json")
            payload["confidence"] = 2
            return [payload]

    result = await make_graph(InvalidConfidenceModel()).ainvoke(initial_state, config())
    assert result["status"] == "WAITING_APPROVAL"
    assert result["failed_dimensions"] == ["security"]
    assert result["dimension_results"]["security"]["error"] == "review_failed"
    assert len(result["findings"]) == 7
    assert "__interrupt__" in result
