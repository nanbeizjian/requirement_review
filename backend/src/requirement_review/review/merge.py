import json
from hashlib import sha256

from requirement_review.domain.models import EvidenceRef, ReviewFinding, Severity

RANK = {
    Severity.LOW: 1,
    Severity.MEDIUM: 2,
    Severity.HIGH: 3,
    Severity.CRITICAL: 4,
}


def _finding_key(finding: ReviewFinding) -> tuple[str, str, str]:
    return (
        finding.requirement_id,
        finding.dimension.value,
        " ".join(finding.issue.lower().split()),
    )


def _evidence_key(evidence: EvidenceRef) -> tuple[str, str, int, str]:
    return (
        evidence.source_type,
        evidence.document_id,
        evidence.version,
        evidence.locator,
    )


def _evidence_tiebreaker(evidence: EvidenceRef) -> tuple[str, str, int, str, str]:
    return (
        evidence.source_type,
        evidence.document_id,
        evidence.version,
        evidence.locator,
        evidence.quote,
    )


def _finding_tiebreaker(finding: ReviewFinding) -> tuple[str, str, str, float, bool]:
    return (
        finding.issue,
        finding.impact,
        finding.recommendation,
        finding.confidence,
        finding.uses_system_fact,
    )


def _winner(left: ReviewFinding, right: ReviewFinding) -> ReviewFinding:
    if RANK[right.severity] > RANK[left.severity]:
        return right
    if RANK[right.severity] < RANK[left.severity]:
        return left
    return min(left, right, key=_finding_tiebreaker)


def _deduplicated_evidence(findings: list[ReviewFinding]) -> list[EvidenceRef]:
    by_reference: dict[tuple[str, str, int, str], EvidenceRef] = {}
    for finding in findings:
        for evidence in finding.evidence:
            reference = _evidence_key(evidence)
            existing = by_reference.get(reference)
            if existing is None or _evidence_tiebreaker(
                evidence
            ) < _evidence_tiebreaker(existing):
                by_reference[reference] = evidence
    return sorted(by_reference.values(), key=_evidence_tiebreaker)


def _finding_id(group_key: tuple[str, str, str], evidence: list[EvidenceRef]) -> str:
    payload = {
        "group": group_key,
        "evidence": [
            {
                "source_type": item.source_type,
                "document_id": item.document_id,
                "version": item.version,
                "locator": item.locator,
                "quote": item.quote,
            }
            for item in evidence
        ],
    }
    encoded = json.dumps(
        payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True
    )
    return f"finding-{sha256(encoded.encode()).hexdigest()}"


def merge_findings(findings: list[ReviewFinding]) -> list[ReviewFinding]:
    """Consolidate equivalent findings and rank the result deterministically."""
    grouped: dict[tuple[str, str, str], list[ReviewFinding]] = {}
    for finding in findings:
        grouped.setdefault(_finding_key(finding), []).append(finding)

    merged = []
    for group_key, group in grouped.items():
        winner = group[0]
        for finding in group[1:]:
            winner = _winner(winner, finding)
        evidence = _deduplicated_evidence(group)
        payload = winner.model_dump()
        payload.update(
            {"evidence": evidence, "finding_id": _finding_id(group_key, evidence)}
        )
        merged.append(ReviewFinding.model_validate(payload))

    return sorted(
        merged,
        key=lambda finding: (
            -RANK[finding.severity],
            finding.requirement_id,
            finding.dimension.value,
            " ".join(finding.issue.lower().split()),
        ),
    )
