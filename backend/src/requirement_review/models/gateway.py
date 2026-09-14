from collections.abc import Awaitable, Callable
from typing import TypeVar

from pydantic import BaseModel

from requirement_review.domain.models import (
    DataPolicy,
    KnowledgeChunk,
    RequirementItem,
    ReviewDimension,
    ReviewFinding,
)

ModelCall = Callable[..., Awaitable[list[ReviewFinding]]]
Model = TypeVar("Model", bound=BaseModel)
REDACTABLE_BODY_FIELDS = frozenset({"text", "quote", "content", "body"})


class PolicyModelGateway:
    def __init__(
        self,
        local_model: ModelCall,
        cloud_model: ModelCall,
        redactor: Callable[[str], str],
    ) -> None:
        self.local_model = local_model
        self.cloud_model = cloud_model
        self.redactor = redactor

    async def review(
        self,
        *,
        project_id: str,
        data_policy: DataPolicy,
        dimension: ReviewDimension,
        requirement: RequirementItem,
        knowledge: list[KnowledgeChunk],
    ) -> list[ReviewFinding]:
        if data_policy is DataPolicy.LOCAL_ONLY:
            return await self.local_model(
                project_id=project_id,
                dimension=dimension,
                requirement=requirement,
                knowledge=knowledge,
            )
        if data_policy is DataPolicy.CLOUD_ALLOWED:
            return await self.cloud_model(
                project_id=project_id,
                dimension=dimension,
                requirement=requirement,
                knowledge=knowledge,
            )
        if data_policy is DataPolicy.CLOUD_REDACTED:
            redacted_requirement = self._redact_model(requirement)
            redacted_knowledge = [self._redact_model(chunk) for chunk in knowledge]
            return await self.cloud_model(
                project_id=project_id,
                dimension=dimension,
                requirement=redacted_requirement,
                knowledge=redacted_knowledge,
            )
        raise ValueError(f"unsupported data policy: {data_policy}")

    def _redact_model(self, model: Model, is_body: bool = False) -> Model:
        updates = {
            field_name: self._redact_value(
                value,
                is_body or field_name in REDACTABLE_BODY_FIELDS,
            )
            for field_name, value in model
        }
        return model.model_copy(update=updates)

    def _redact_value(self, value: object, is_body: bool) -> object:
        if isinstance(value, str):
            return self.redactor(value) if is_body else value
        if isinstance(value, BaseModel):
            return self._redact_model(value, is_body)
        if isinstance(value, list):
            return [self._redact_value(item, is_body) for item in value]
        if isinstance(value, tuple):
            return tuple(self._redact_value(item, is_body) for item in value)
        if isinstance(value, dict):
            return {
                key: self._redact_value(
                    item,
                    is_body or (isinstance(key, str) and key in REDACTABLE_BODY_FIELDS),
                )
                for key, item in value.items()
            }
        return value
