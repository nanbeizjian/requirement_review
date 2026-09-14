from pydantic import ValidationError

from requirement_review.documents.markdown import parse_markdown
from requirement_review.domain.models import (
    DataPolicy,
    EvidenceValidationError,
    ReviewDimension,
    ReviewFinding,
)
from requirement_review.domain.protocols import ModelGateway
from requirement_review.graph.state import DimensionResult, ReviewState
from requirement_review.knowledge.service import KnowledgeService
from requirement_review.review.evidence import validate_finding
from requirement_review.review.merge import merge_findings


class EvidenceInvalidError(ValueError):
    """A finding cites evidence outside the available requirement or knowledge scope."""


def _parse_model_finding(payload: object) -> ReviewFinding:
    try:
        return ReviewFinding.model_validate(payload)
    except ValidationError as exc:
        if any(
            error["loc"][:1] == ("evidence",)
            or isinstance(error.get("ctx", {}).get("error"), EvidenceValidationError)
            for error in exc.errors(include_input=False, include_url=False)
        ):
            raise EvidenceInvalidError("invalid evidence structure") from None
        raise


class ReviewServices:
    def __init__(
        self, knowledge_service: KnowledgeService, model_gateway: ModelGateway
    ) -> None:
        self.knowledge_service = knowledge_service
        self.model_gateway = model_gateway

    def parse(self, state: ReviewState) -> dict:
        try:
            policy = DataPolicy(state["data_policy"])
            requirements = parse_markdown(
                state["document_id"],
                state.get("document_version", 1),
                state["document_text"],
            )
            if not requirements:
                raise ValueError("no requirements")
        except (ValueError, TypeError, KeyError):
            return {"status": "FAILED", "errors": ["parse_failed"]}
        return {
            "requirements": requirements,
            "data_policy": policy,
            "status": "RETRIEVING",
            "findings": [],
            "failed_dimensions": [],
            "errors": [],
        }

    async def retrieve(self, state: ReviewState) -> dict:
        try:
            knowledge = {
                requirement.requirement_id: await self.knowledge_service.context_for(
                    state["project_id"], requirement
                )
                for requirement in state["requirements"]
            }
            if any(
                chunk.project_id != state["project_id"]
                for chunks in knowledge.values()
                for chunk in chunks
            ):
                raise PermissionError("knowledge project mismatch")
        except Exception as exc:  # noqa: BLE001 - provider boundary; persist safe failure codes
            code = (
                "permission_denied"
                if isinstance(exc, PermissionError)
                else "retrieval_failed"
            )
            return {"status": "FAILED", "errors": [code]}
        return {
            "knowledge_by_requirement": knowledge,
            "status": "REVIEWING",
            "selected_dimensions": list(ReviewDimension),
        }

    @staticmethod
    def validate_findings(state: ReviewState, findings: list[ReviewFinding]) -> None:
        requirements = {r.requirement_id: r for r in state["requirements"]}
        for finding in findings:
            requirement = requirements.get(finding.requirement_id)
            if requirement is None:
                raise EvidenceInvalidError("unknown requirement")
            ref = requirement.evidence
            knowledge = state["knowledge_by_requirement"][requirement.requirement_id]
            if not validate_finding(
                finding,
                {(ref.document_id, ref.version, ref.locator)},
                {
                    (chunk.document_id, chunk.version, chunk.locator)
                    for chunk in knowledge
                },
            ):
                raise EvidenceInvalidError("invalid evidence")

    async def review_dimension(self, state: ReviewState) -> dict:
        dimension = ReviewDimension(state["active_dimension"])
        findings: list[ReviewFinding] = []
        error = None
        try:
            for requirement in state["requirements"]:
                result = await self.model_gateway.review(
                    project_id=state["project_id"],
                    data_policy=state["data_policy"],
                    dimension=dimension,
                    requirement=requirement,
                    knowledge=state["knowledge_by_requirement"][
                        requirement.requirement_id
                    ],
                )
                validated = [_parse_model_finding(finding) for finding in result]
                if any(
                    finding.dimension != dimension
                    or finding.requirement_id != requirement.requirement_id
                    for finding in validated
                ):
                    raise ValueError("mismatched review scope")
                self.validate_findings(state, validated)
                findings.extend(validated)
        except Exception as exc:  # noqa: BLE001 - one provider failure must not abort siblings
            # Never persist exception text: model/transport errors can contain document bodies.
            if isinstance(exc, PermissionError):
                error = "permission_denied"
            elif isinstance(exc, EvidenceInvalidError):
                error = "evidence_invalid"
            else:
                error = "review_failed"
            findings = []
        return {
            "dimension_results": {
                dimension.value: {"findings": findings, "error": error}
            }
        }

    def prepare_consolidation(self, state: ReviewState) -> dict:
        results = state["dimension_results"]
        failed = sorted(
            dimension for dimension, result in results.items() if result["error"]
        )
        errors = []
        if any(result["error"] == "permission_denied" for result in results.values()):
            errors.append("permission_denied")
        if any(result["error"] == "evidence_invalid" for result in results.values()):
            errors.append("evidence_invalid")
        if all(result["error"] for result in results.values()):
            errors.append("all_dimensions_failed")
        return {
            "failed_dimensions": failed,
            "errors": errors,
            "status": "FAILED" if errors else "CONSOLIDATING",
            **({"findings": []} if errors else {}),
        }

    def consolidate(self, state: ReviewState) -> dict:
        findings = merge_findings(
            [
                finding
                for result in state["dimension_results"].values()
                for finding in result["findings"]
            ]
        )
        return {"findings": findings, "status": "WAITING_APPROVAL"}

    def modify(self, state: ReviewState, payload: object) -> dict[str, DimensionResult]:
        """Apply a complete human-edited finding list, preserving visible failures."""
        if not isinstance(payload, list):
            raise TypeError("findings must be a list")
        findings = [ReviewFinding.model_validate(finding) for finding in payload]
        self.validate_findings(state, findings)
        return {
            dimension.value: {
                "findings": [
                    finding for finding in findings if finding.dimension == dimension
                ],
                "error": state["dimension_results"][dimension.value]["error"],
            }
            for dimension in ReviewDimension
        }
