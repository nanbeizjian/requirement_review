from typing import Literal

from pydantic import BaseModel, Field, model_validator

from requirement_review.domain.models import DataPolicy, ReviewDimension


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    data_policy: DataPolicy = DataPolicy.CLOUD_ALLOWED


class ReviewCreate(BaseModel):
    project_id: str
    document_id: str | None = None
    text: str | None = Field(default=None, max_length=100_000)
    data_policy: DataPolicy
    source_name: str | None = Field(default=None, max_length=200)

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


class ReviewSummary(BaseModel):
    review_id: str
    project_id: str
    source_name: str | None
    status: str
    finding_count: int
    pending_decision_count: int
    created_at: str


class ReviewDetail(BaseModel):
    review_id: str
    project_id: str
    source_name: str | None
    status: str
    finding_count: int
    pending_decision_count: int
    created_at: str
    failed_dimensions: list[str]
