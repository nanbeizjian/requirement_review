import pytest
from pydantic import ValidationError

from requirement_review.domain.models import (
    EvidenceRef,
    ReviewDimension,
    ReviewFinding,
    Severity,
)
from requirement_review.review.merge import merge_findings


def make_finding(
    *,
    requirement_id: str = "REQ-001",
    severity: Severity = Severity.LOW,
    issue: str = "缺少可验证指标",
    locator: str = "功能#p1",
) -> ReviewFinding:
    return ReviewFinding(
        requirement_id=requirement_id,
        dimension=ReviewDimension.TESTABILITY,
        severity=severity,
        issue=issue,
        impact="无法验收",
        recommendation="补充响应时间阈值",
        confidence=0.9,
        evidence=[
            EvidenceRef(
                source_type="requirement",
                document_id="doc-x",
                version=1,
                locator=locator,
                quote="系统应快速登录",
            )
        ],
        uses_system_fact=False,
    )


def test_merge_keeps_highest_severity_and_all_evidence() -> None:
    high_finding = make_finding(severity=Severity.HIGH, locator="功能#p2")
    low_duplicate = make_finding(severity=Severity.LOW)

    merged = merge_findings([low_duplicate, high_finding])

    assert len(merged) == 1
    assert merged[0].severity == Severity.HIGH
    assert [e.locator for e in merged[0].evidence] == ["功能#p1", "功能#p2"]


def test_merge_deduplicates_evidence_with_the_same_reference() -> None:
    first = make_finding(locator="功能#p1")
    duplicate = make_finding(locator="功能#p1")

    merged = merge_findings([first, duplicate])

    assert len(merged) == 1
    assert len(merged[0].evidence) == 1


def test_merge_is_stable_regardless_of_input_order() -> None:
    critical = make_finding(requirement_id="REQ-002", severity=Severity.CRITICAL)
    high = make_finding(requirement_id="REQ-003", severity=Severity.HIGH)
    low = make_finding(requirement_id="REQ-001", severity=Severity.LOW)

    forward = merge_findings([low, critical, high])
    reversed_order = merge_findings([high, low, critical])

    assert [finding.requirement_id for finding in forward] == [
        "REQ-002",
        "REQ-003",
        "REQ-001",
    ]
    assert reversed_order == forward


def test_merge_orders_deduplicated_evidence_independently_of_input_order() -> None:
    first = make_finding(locator="功能#p2")
    second = make_finding(locator="功能#p1")

    forward = merge_findings([first, second])
    reversed_order = merge_findings([second, first])

    assert [e.locator for e in forward[0].evidence] == ["功能#p1", "功能#p2"]
    assert reversed_order == forward


def test_merge_chooses_duplicate_evidence_deterministically() -> None:
    first = make_finding(locator="功能#p1")
    second = first.model_copy(
        update={
            "evidence": [
                first.evidence[0].model_copy(update={"quote": "另一段相同定位的原文"})
            ]
        }
    )

    forward = merge_findings([first, second])
    reversed_order = merge_findings([second, first])

    assert len(forward[0].evidence) == 1
    assert reversed_order == forward


def test_merge_keeps_same_locator_from_requirement_and_knowledge_sources() -> None:
    requirement = make_finding(locator="功能#p1")
    knowledge = EvidenceRef(
        source_type="knowledge",
        document_id="doc-x",
        version=1,
        locator="功能#p1",
        quote="同一定位的系统知识",
    )
    system_fact = requirement.model_copy(
        update={
            "evidence": [requirement.evidence[0], knowledge],
            "uses_system_fact": True,
        }
    )

    merged = merge_findings([requirement, system_fact])

    assert [e.source_type for e in merged[0].evidence] == ["knowledge", "requirement"]


def test_merge_revalidates_the_consolidated_finding() -> None:
    invalid_system_fact = make_finding().model_copy(update={"uses_system_fact": True})

    with pytest.raises(ValidationError, match="knowledge evidence is required"):
        merge_findings([invalid_system_fact])


def test_merge_ignores_upstream_ids_when_choosing_business_fields_and_generating_id() -> (
    None
):
    first = make_finding().model_copy(
        update={"finding_id": "aaa-random-id", "recommendation": "Z 推荐"}
    )
    second = make_finding().model_copy(
        update={"finding_id": "zzz-random-id", "recommendation": "A 推荐"}
    )

    forward = merge_findings([first, second])
    reversed_order = merge_findings([second, first])

    assert forward[0].recommendation == "A 推荐"
    assert forward[0].finding_id
    assert forward == reversed_order
