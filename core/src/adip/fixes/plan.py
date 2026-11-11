"""Data shapes for the fix pipeline: the plan a user approves and the report of what ran.

A FixPlan is plain validated JSON. Both entry points produce one: the rule-based
plan builder and (later) the AI planner. Nothing in here executes anything.
"""

from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, computed_field, model_validator

from adip.models.quality import DatasetStatus, DimensionScore, QualityIssue

PlanSource = Literal["rules", "ai", "user"]
StepStatus = Literal["applied", "skipped", "failed"]


class FixStep(BaseModel):
    id: str = ""  # filled as step-1, step-2, ... when left empty
    fix: str  # name in the fix registry
    columns: list[str] = Field(default_factory=list)
    params: dict[str, Any] = Field(default_factory=dict)
    enabled: bool = True  # the approval checkbox
    safe: bool = True  # False marks a step that deserves a closer look before ticking
    allow_target: bool = False  # steps never touch the target column unless this is set
    reason: str = ""  # shown next to the checkbox
    source: PlanSource = "rules"


class FixPlan(BaseModel):
    source: PlanSource = "rules"
    target: str | None = None
    steps: list[FixStep] = Field(default_factory=list)

    @model_validator(mode="after")
    def _assign_and_check_ids(self) -> "FixPlan":
        for i, step in enumerate(self.steps, start=1):
            if not step.id:
                step.id = f"step-{i}"
        ids = [s.id for s in self.steps]
        if len(set(ids)) != len(ids):
            raise ValueError("Fix plan has duplicate step ids.")
        return self


class FixStepResult(BaseModel):
    step_id: str
    fix: str
    label: str
    status: StepStatus
    message: str
    columns: list[str] = Field(default_factory=list)  # columns the fix actually received
    ignored_columns: list[str] = Field(default_factory=list)  # missing or target-protected
    params: dict[str, Any] = Field(default_factory=dict)  # resolved, with config defaults applied
    rows_before: int
    rows_after: int
    cols_before: int
    cols_after: int
    warning: str | None = None


class QualityScore(BaseModel):
    """Quality score snapshot captured before or after standardization."""

    score: float
    grade: str
    status: DatasetStatus | None = None
    issues: int
    issue_details: list[QualityIssue] = Field(default_factory=list)
    breakdown: dict[str, float] = Field(default_factory=dict)
    dimensions: list[DimensionScore] = Field(default_factory=list)
    score_explanation: str = ""
    grade_explanation: str = ""
    missing_values: int = Field(0, ge=0)
    duplicate_records: int = Field(0, ge=0)
    invalid_values: int = Field(0, ge=0)


class FixReport(BaseModel):
    """What a FixEngine run did. Saved as change_log.json in a later checkpoint."""

    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    plan: FixPlan
    target: str | None = None
    steps: list[FixStepResult]  # in execution order
    rows_before: int
    rows_after: int
    cols_before: int
    cols_after: int
    before: QualityScore
    after: QualityScore
    records_modified: int = Field(0, ge=0)
    records_removed: int = Field(0, ge=0)
    comparison_notes: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def score_delta(self) -> float:
        """Return the cleaned score minus the original score."""
        return round(self.after.score - self.before.score, 2)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def missing_values_delta(self) -> int:
        """Return the cleaned missing-value count minus the original count."""
        return self.after.missing_values - self.before.missing_values

    @computed_field  # type: ignore[prop-decorator]
    @property
    def duplicate_records_delta(self) -> int:
        """Return the cleaned duplicate count minus the original count."""
        return self.after.duplicate_records - self.before.duplicate_records

    @computed_field  # type: ignore[prop-decorator]
    @property
    def invalid_values_delta(self) -> int:
        """Return the cleaned invalid-value count minus the original count."""
        return self.after.invalid_values - self.before.invalid_values
