from requirement_review.domain.models import KnowledgeChunk, RequirementItem
from requirement_review.domain.protocols import KnowledgeSource


class KnowledgeService:
    def __init__(self, source: KnowledgeSource) -> None:
        self.source = source

    async def context_for(
        self, project_id: str, requirement: RequirementItem
    ) -> list[KnowledgeChunk]:
        return await self.source.search(requirement.text, project_id, {"limit": 8})
