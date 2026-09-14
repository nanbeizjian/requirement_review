import re
from collections import Counter

from requirement_review.domain.models import KnowledgeChunk


class MarkdownKnowledgeSource:
    def __init__(self, chunks: list[KnowledgeChunk]) -> None:
        chunk_counts = Counter(chunk.project_id for chunk in chunks)
        for project_id, count in chunk_counts.items():
            if count > 10_000:
                raise ValueError(
                    f"project {project_id!r} has {count} Markdown chunks; maximum is 10,000"
                )
        self._chunks = chunks

    @classmethod
    def from_documents(
        cls, documents: list[tuple[str, str, int, str]]
    ) -> "MarkdownKnowledgeSource":
        chunks: list[KnowledgeChunk] = []
        for project_id, document_id, version, text in documents:
            heading = "root"
            position = 0
            for block in re.split(r"\n\s*\n|(?=^#)", text, flags=re.MULTILINE):
                block = block.strip()
                if not block:
                    continue
                if block.startswith("#"):
                    lines = block.splitlines()
                    heading = lines[0].lstrip("#").strip()
                    block = "\n".join(lines[1:]).strip()
                    if not block:
                        continue
                position += 1
                chunks.append(
                    KnowledgeChunk(
                        chunk_id=f"{document_id}:{version}:{position}",
                        project_id=project_id,
                        document_id=document_id,
                        version=version,
                        locator=f"{heading}#p{position}",
                        text=block,
                    )
                )
        return cls(chunks)

    async def search(
        self, query: str, project_id: str, filters: dict[str, object]
    ) -> list[KnowledgeChunk]:
        terms = {term.lower() for term in re.findall(r"[\w.-]+", query)}
        candidates = [chunk for chunk in self._chunks if chunk.project_id == project_id]
        scored = [
            chunk.model_copy(
                update={"score": sum(term in chunk.text.lower() for term in terms)}
            )
            for chunk in candidates
        ]
        return sorted(
            (chunk for chunk in scored if chunk.score > 0),
            key=lambda chunk: chunk.score,
            reverse=True,
        )[:8]
