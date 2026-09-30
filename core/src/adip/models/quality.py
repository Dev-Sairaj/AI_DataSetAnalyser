from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, Field

Severity = Literal["info", "warning", "critical"]


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


class QualityReport(BaseModel):
    score: float  # 0-100
    grade: str  # A-F
    score_breakdown: dict[str, float]
    issues: list[QualityIssue]
    outliers: list[OutlierSummary]