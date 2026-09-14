from typing import Annotated, Literal, TypedDict

from requirement_review.domain.models import (
    DataPolicy,
    KnowledgeChunk,
    RequirementItem,
    ReviewDimension,
    ReviewFinding,
)


class DimensionResult(TypedDict):
    findings: list[ReviewFinding]
    error: str | None


def replace_dimensions(
    current: dict[str, DimensionResult], updates: dict[str, DimensionResult]
) -> dict[str, DimensionResult]:
    """Join distinct workers; later review rounds replace the selected dimensions."""
    return {**current, **updates}


class ReviewState(TypedDict, total=False):
    review_id: str
    project_id: str
    document_id: str
    document_version: int
    document_text: str
    data_policy: DataPolicy
    status: Literal[
        "PARSING",
        "RETRIEVING",
        "REVIEWING",
        "CONSOLIDATING",
        "WAITING_APPROVAL",
        "COMPLETED",
        "FAILED",
    ]
    requirements: list[RequirementItem]
    knowledge_by_requirement: dict[str, list[KnowledgeChunk]]
    dimension_results: Annotated[dict[str, DimensionResult], replace_dimensions]
    active_dimension: ReviewDimension
    selected_dimensions: list[ReviewDimension]
    findings: list[ReviewFinding]
    failed_dimensions: list[str]
    errors: list[str]
    approval: dict[str, object]
    pending_approval: object
    approval_error: str | None
    report_markdown: str
