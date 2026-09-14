from requirement_review.domain.models import ReviewFinding

RefKey = tuple[str, int, str]


def _reference_key(document_id: str, version: int, locator: str) -> RefKey:
    return (document_id, version, locator)


def validate_finding(
    finding: ReviewFinding,
    requirement_refs: set[RefKey],
    knowledge_refs: set[RefKey],
) -> bool:
    """Return whether every required finding citation is from an approved source."""
    if any(e.source_type not in {"requirement", "knowledge"} for e in finding.evidence):
        return False

    requirement_evidence = {
        _reference_key(e.document_id, e.version, e.locator)
        for e in finding.evidence
        if e.source_type == "requirement"
    }
    knowledge_evidence = {
        _reference_key(e.document_id, e.version, e.locator)
        for e in finding.evidence
        if e.source_type == "knowledge"
    }
    return (
        bool(requirement_evidence)
        and requirement_evidence <= requirement_refs
        and knowledge_evidence <= knowledge_refs
        and (not finding.uses_system_fact or bool(knowledge_evidence))
    )
