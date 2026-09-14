from typing import Protocol

from .models import (
    DataPolicy,
    KnowledgeChunk,
    RequirementItem,
    ReviewDimension,
    ReviewFinding,
)


class KnowledgeSource(Protocol):
    async def search(
        self, query: str, project_id: str, filters: dict[str, object]
    ) -> list[KnowledgeChunk]: ...


class ModelGateway(Protocol):
    async def review(
        self,
        *,
        project_id: str,
        data_policy: DataPolicy,
        dimension: ReviewDimension,
        requirement: RequirementItem,
        knowledge: list[KnowledgeChunk],
    ) -> list[ReviewFinding]: ...
