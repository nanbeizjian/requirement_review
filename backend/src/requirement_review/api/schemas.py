from typing import Literal

from pydantic import BaseModel, Field, model_validator

from requirement_review.domain.models import DataPolicy, ReviewDimension


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    data_policy: DataPolicy = DataPolicy.LOCAL_ONLY


class ReviewCreate(BaseModel):
    project_id: str
    document_id: str | None = None
    text: str | None = Field(default=None, max_length=100_000)
    data_policy: DataPolicy

    @model_validator(mode="after")
    def require_document_or_text(self) -> "ReviewCreate":
        if not self.document_id and not self.text:
            raise ValueError("document_id or text is required")
        return self


class FindingDecisionRequest(BaseModel):
    action: Literal["accept", "reject", "re-review"]
    comment: str = Field(default="", max_length=2_000)


class ApprovalRequest(BaseModel):
    action: Literal["approve", "modify", "reject", "re-review"]
    comment: str = Field(default="", max_length=2_000)
    dimensions: list[ReviewDimension] | None = None
    findings: list[dict] | None = None
