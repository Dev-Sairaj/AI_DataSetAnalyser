from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, Field

from adip.models.governance import QualityDimensionName

Severity = Literal["info", "warning", "critical"]
DatasetStatus = Literal["Clean", "Needs Cleaning", "Critical Issues"]
DimensionAssessment = Literal["automated", "proxy", "not_assessed"]


class IssueCode(StrEnum):
    MISSING_VALUES = "MISSING_VALUES"
    DUPLICATE_ROWS = "DUPLICATE_ROWS"
    EMPTY_COLUMN = "EMPTY_COLUMN"
    CONSTANT_COLUMN = "CONSTANT_COLUMN"
    HIGH_CARDINALITY = "HIGH_CARDINALITY"
    NUMERIC_AS_TEXT = "NUMERIC_AS_TEXT"
    INVALID_DTYPE = "INVALID_DTYPE"
    MIXED_TYPES = "MIXED_TYPES"
    INFINITE_VALUES = "INFINITE_VALUES"
    INCONSISTENT_FORMAT = "INCONSISTENT_FORMAT"
    OUTLIERS = "OUTLIERS"


class QualityIssue(BaseModel):
    code: IssueCode
    severity: Severity
    column: str | None = None
    message: str
    affected_count: int = 0
    affected_pct: float = 0.0
    details: dict[str, Any] = Field(default_factory=dict)


class OutlierSummary(BaseModel):
    column: str
    method: str
    count: int
    pct: float  # of non-null values
    lower_bound: float | None = None
    upper_bound: float | None = None


class StatusRuleResult(BaseModel):
    """Result of one transparent rule used to classify dataset cleanliness."""

    name: str
    condition: str
    triggered: bool
    evidence: str


class DimensionScore(BaseModel):
    """Transparent score and weighting details for one quality dimension."""

    name: QualityDimensionName
    score: float | None = Field(ge=0, le=100)
    assessment: DimensionAssessment
    configured_weight: float = Field(ge=0)
    effective_weight: float = Field(ge=0, le=1)
    formula: str
    evidence: str
    limitation: str | None = None


class QualityReport(BaseModel):
    """Complete quality assessment, including score, findings, and dataset status."""

    score: float  # 0-100
    grade: str  # A-F
    status: DatasetStatus
    status_summary: str
    status_rules: list[StatusRuleResult]
    score_breakdown: dict[str, float]
    dimension_scores: list[DimensionScore]
    score_explanation: str
    grade_explanation: str
    grading_thresholds: dict[str, float]
    issues: list[QualityIssue]
    outliers: list[OutlierSummary]
