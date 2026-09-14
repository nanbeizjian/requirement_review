from enum import StrEnum

from pydantic import BaseModel, Field, model_validator


class ReviewDimension(StrEnum):
    COMPLETENESS = "completeness"
    CONSISTENCY = "consistency"
    CLARITY = "clarity"
    FEASIBILITY = "feasibility"
    TESTABILITY = "testability"
    SECURITY = "security"
    PERFORMANCE = "performance"
    DATA_INTERFACE = "data_interface"


class Severity(StrEnum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class DataPolicy(StrEnum):
    LOCAL_ONLY = "local_only"
    CLOUD_ALLOWED = "cloud_allowed"
    CLOUD_REDACTED = "cloud_redacted"


class EvidenceValidationError(ValueError):
    """An evidence invariant failed while validating a finding."""


class EvidenceRef(BaseModel):
    source_type: str
    document_id: str
    version: int
    locator: str
    quote: str


class KnowledgeChunk(BaseModel):
    chunk_id: str
    project_id: str
    document_id: str
    version: int
    locator: str
    text: str
    score: float = 0.0


class RequirementItem(BaseModel):
    requirement_id: str
    text: str
    evidence: EvidenceRef


class ReviewFinding(BaseModel):
    finding_id: str | None = None
    requirement_id: str
    dimension: ReviewDimension
    severity: Severity
    issue: str
    impact: str
    recommendation: str
    confidence: float = Field(ge=0, le=1)
    evidence: list[EvidenceRef]
    uses_system_fact: bool

    @model_validator(mode="after")
    def require_evidence(self) -> "ReviewFinding":
        if not any(e.source_type == "requirement" for e in self.evidence):
            raise EvidenceValidationError("requirement evidence is required")
        if self.uses_system_fact and not any(
            e.source_type == "knowledge" for e in self.evidence
        ):
            raise EvidenceValidationError(
                "knowledge evidence is required for system facts"
            )
        return self
