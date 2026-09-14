from requirement_review.domain.models import (
    EvidenceRef,
    ReviewDimension,
    ReviewFinding,
    Severity,
)
from requirement_review.review.evidence import validate_finding


def make_finding(
    *, evidence: list[EvidenceRef], uses_system_fact: bool = False
) -> ReviewFinding:
    return ReviewFinding(
        requirement_id="REQ-001",
        dimension=ReviewDimension.TESTABILITY,
        severity=Severity.HIGH,
        issue="缺少可验证指标",
        impact="无法验收",
        recommendation="补充响应时间阈值",
        confidence=0.9,
        evidence=evidence,
        uses_system_fact=uses_system_fact,
    )


def requirement_evidence(locator: str = "功能#p1") -> EvidenceRef:
    return EvidenceRef(
        source_type="requirement",
        document_id="doc-x",
        version=1,
        locator=locator,
        quote="系统应快速登录",
    )


def knowledge_evidence(locator: str = "架构#p1") -> EvidenceRef:
    return EvidenceRef(
        source_type="knowledge",
        document_id="knowledge-x",
        version=2,
        locator=locator,
        quote="登录服务依赖外部身份提供商",
    )


def test_rejects_unknown_requirement_locator() -> None:
    finding = make_finding(evidence=[requirement_evidence("功能#p9")])

    assert not validate_finding(finding, {("doc-x", 1, "功能#p1")}, set())


def test_rejects_unknown_knowledge_locator_for_system_fact() -> None:
    finding = make_finding(
        evidence=[requirement_evidence(), knowledge_evidence("架构#p9")],
        uses_system_fact=True,
    )

    assert not validate_finding(
        finding,
        {("doc-x", 1, "功能#p1")},
        {("knowledge-x", 2, "架构#p1")},
    )


def test_rejects_unknown_source_type() -> None:
    finding = make_finding(
        evidence=[
            requirement_evidence(),
            EvidenceRef(
                source_type="generated",
                document_id="doc-x",
                version=1,
                locator="功能#p2",
                quote="模型推断",
            ),
        ]
    )

    assert not validate_finding(finding, {("doc-x", 1, "功能#p1")}, set())


def test_rejects_unknown_knowledge_even_when_not_a_system_fact() -> None:
    finding = make_finding(
        evidence=[requirement_evidence(), knowledge_evidence("架构#p9")],
    )

    assert not validate_finding(
        finding,
        {("doc-x", 1, "功能#p1")},
        {("knowledge-x", 2, "架构#p1")},
    )


def test_accepts_whitelisted_requirement_and_knowledge_evidence() -> None:
    finding = make_finding(
        evidence=[requirement_evidence(), knowledge_evidence()],
        uses_system_fact=True,
    )

    assert validate_finding(
        finding,
        {("doc-x", 1, "功能#p1")},
        {("knowledge-x", 2, "架构#p1")},
    )
