"""Models for transparent Government of India data-quality framework alignment."""

from typing import Literal

from pydantic import BaseModel, Field

QualityDimensionName = Literal[
    "Accuracy",
    "Completeness",
    "Consistency",
    "Timeliness",
    "Validity",
    "Uniqueness",
]
CoverageStatus = Literal["implemented", "partially_implemented", "external_or_manual"]


class GovernmentFrameworkReference(BaseModel):
    """Authoritative public reference used to explain the alignment."""

    title: str
    publisher: str
    url: str
    relevance: str


class GovernmentQualityDimension(BaseModel):
    """Implementation coverage for one operational data-quality dimension."""

    name: QualityDimensionName
    coverage: CoverageStatus
    explanation: str
    implemented_checks: list[str] = Field(default_factory=list)
    external_or_manual_checks: list[str] = Field(default_factory=list)
    detected_issue_count: int = 0
    detected_issue_codes: list[str] = Field(default_factory=list)


class GovernmentFrameworkMapping(BaseModel):
    """Non-certifying alignment of ADIP checks with government data-quality guidance."""

    framework_name: str
    mapping_name: str
    disclaimer: str
    references: list[GovernmentFrameworkReference]
    dimensions: list[GovernmentQualityDimension]
