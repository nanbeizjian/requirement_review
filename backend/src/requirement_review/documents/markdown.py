import re

from requirement_review.domain.models import EvidenceRef, RequirementItem


def parse_markdown(document_id: str, version: int, text: str) -> list[RequirementItem]:
    if len(text) > 100_000:
        raise ValueError("document exceeds 100000 characters")

    heading_path: list[tuple[int, str]] = []
    paragraph_no = 0
    items: list[RequirementItem] = []

    def current_heading() -> str:
        return "/".join(title for _, title in heading_path) or "root"

    def add_requirement(block: str) -> None:
        nonlocal paragraph_no
        paragraph_no += 1
        requirement_id = f"REQ-{len(items) + 1:03d}"
        evidence = EvidenceRef(
            source_type="requirement",
            document_id=document_id,
            version=version,
            locator=f"{current_heading()}#p{paragraph_no}",
            quote=block,
        )
        items.append(
            RequirementItem(
                requirement_id=requirement_id, text=block, evidence=evidence
            )
        )

    pending: list[str] = []

    def flush_pending() -> None:
        if pending:
            add_requirement("\n".join(pending).strip())
            pending.clear()

    for line in text.splitlines():
        heading_match = re.match(r"^(#{1,6})\s+(.+?)\s*$", line)
        if heading_match:
            flush_pending()
            level = len(heading_match.group(1))
            heading_path[:] = [
                (existing_level, title)
                for existing_level, title in heading_path
                if existing_level < level
            ]
            heading_path.append((level, heading_match.group(2)))
            continue

        if not line.strip():
            flush_pending()
            continue

        if re.match(r"^\s*(?:[-*+] |\d+[.)] )", line):
            flush_pending()
            add_requirement(line.strip())
            continue

        pending.append(line.strip())

    flush_pending()
    return items
