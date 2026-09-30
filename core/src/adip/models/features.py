from typing import Literal

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
    """Guidance only. ADIP never modifies the dataset."""

    category: RecCategory
    severity: Severity
    column: str | None = None
    columns: list[str] = Field(default_factory=list)
    title: str
    recommendation: str
    rationale: str


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