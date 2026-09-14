import pytest
from pydantic import ValidationError

from requirement_review.domain.models import (
    EvidenceRef,
    ReviewDimension,
    ReviewFinding,
    Severity,
)


def test_finding_requires_requirement_evidence() -> None:
    with pytest.raises(ValidationError):
        ReviewFinding(
            requirement_id="REQ-001",
            dimension=ReviewDimension.TESTABILITY,
            severity=Severity.HIGH,
            issue="缺少可验证指标",
            impact="无法验收",
            recommendation="补充响应时间阈值",
            confidence=0.9,
            evidence=[],
            uses_system_fact=False,
        )


def test_finding_accepts_located_requirement_evidence() -> None:
    finding = ReviewFinding(
        requirement_id="REQ-001",
        dimension=ReviewDimension.TESTABILITY,
        severity=Severity.HIGH,
        issue="缺少可验证指标",
        impact="无法验收",
        recommendation="补充响应时间阈值",
        confidence=0.9,
        evidence=[
            EvidenceRef(
                source_type="requirement",
                document_id="d1",
                version=1,
                locator="功能/登录#p2",
                quote="系统应快速登录",
            )
        ],
        uses_system_fact=False,
    )
    assert finding.evidence[0].locator == "功能/登录#p2"
