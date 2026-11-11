from typing import Any, Literal

from pydantic import BaseModel, Field

from adip.models.eda import CategoryCount
from adip.models.quality import Severity

RecCategory = Literal[
    "data_types",
    "missing_values",
    "encoding",
    "scaling",
    "low_value",
    "redundancy",
    "target",
]


class Recommendation(BaseModel):
    """Advice, optionally with the fix that would carry it out.

    ``fix`` is a name from the fix registry. Without it the recommendation is
    advice-only and never becomes a plan step. ADIP itself never modifies the
    dataset: fixes only run after the user approves a plan.
    """

    category: RecCategory
    severity: Severity
    column: str | None = None
    columns: list[str] = Field(default_factory=list)
    title: str
    recommendation: str
    rationale: str
    fix: str | None = None
    fix_columns: list[str] = Field(default_factory=list)
    fix_params: dict[str, Any] = Field(default_factory=dict)


class FeatureSignal(BaseModel):
    column: str
    score: float  # Pearson r (regression) or mutual information (classification)


class TargetAnalysis(BaseModel):
    column: str
    task: Literal["classification", "regression"]
    n_classes: int | None = None
    class_balance: list[CategoryCount] = Field(default_factory=list)
    imbalance_ratio: float | None = None
    signal_metric: str = ""
    signals: list[FeatureSignal] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class FeatureReport(BaseModel):
    recommendations: list[Recommendation]
    target: TargetAnalysis | None = None