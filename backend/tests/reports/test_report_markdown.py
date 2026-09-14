from types import SimpleNamespace

from requirement_review.domain.models import (
    EvidenceRef,
    ReviewDimension,
    ReviewFinding,
    Severity,
)
from requirement_review.reports.markdown import render_markdown


def test_report_contains_evidence_failures_and_approval() -> None:
    review = SimpleNamespace(
        report_version=2, status="COMPLETED", failed_dimensions=["security"]
    )
    finding = ReviewFinding(
        finding_id="f1",
        requirement_id="REQ-001",
        dimension=ReviewDimension.CLARITY,
        severity=Severity.HIGH,
        issue="描述含糊",
        impact="无法实现",
        recommendation="补充规则",
        confidence=0.9,
        uses_system_fact=False,
        evidence=[
            EvidenceRef(
                source_type="requirement",
                document_id="d1",
                version=1,
                locator="登录#p2",
                quote="系统应快速登录",
            )
        ],
    )
    approval = SimpleNamespace(actor_id="reviewer-1", action="approve", comment="同意")
    report = render_markdown(review, [finding], [approval])
    assert "登录#p2" in report
    assert "描述含糊" in report
    assert "未完成评审维度" in report and "security" in report
    assert "reviewer-1" in report


def test_report_order_is_deterministic() -> None:
    review = SimpleNamespace(report_version=1, status="COMPLETED", failed_dimensions=[])
    evidence = [
        EvidenceRef(
            source_type="requirement",
            document_id="d",
            version=1,
            locator="root#p1",
            quote="q",
        )
    ]
    low = ReviewFinding(
        requirement_id="REQ-001",
        dimension=ReviewDimension.CLARITY,
        severity=Severity.LOW,
        issue="low",
        impact="i",
        recommendation="r",
        confidence=1,
        evidence=evidence,
        uses_system_fact=False,
    )
    high = low.model_copy(
        update={"finding_id": "h", "severity": Severity.HIGH, "issue": "high"}
    )
    assert render_markdown(review, [low, high], []) == render_markdown(
        review, [high, low], []
    )
