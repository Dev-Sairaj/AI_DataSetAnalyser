from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field

from adip.models.dataset import DatasetInfo
from adip.models.eda import (
    BoxPlotData,
    CategoryCount,
    CorrelationResult,
    EdaReport,
    HistogramData,
)
from adip.models.features import FeatureReport
from adip.models.governance import GovernmentFrameworkMapping
from adip.models.profile import DatasetProfile
from adip.models.quality import QualityReport
from adip.models.sop import AssessmentSOP


class MissingBar(BaseModel):
    column: str
    missing: int
    missing_pct: float


class ChartData(BaseModel):
    """Chart-ready data. React renders it interactively; matplotlib renders it statically."""

    histograms: list[HistogramData]
    boxplots: list[BoxPlotData]
    correlation: CorrelationResult | None
    category_frequencies: dict[str, list[CategoryCount]]
    missing: list[MissingBar]


class AnalysisReport(BaseModel):
    """The complete result of one ADIP run. This is the API's main response model."""

    adip_version: str
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    dataset: DatasetInfo
    target: str | None = None
    profile: DatasetProfile
    quality: QualityReport
    eda: EdaReport
    features: FeatureReport
    government_framework: GovernmentFrameworkMapping
    sop: AssessmentSOP
    charts: ChartData
    config: dict[str, Any] = Field(default_factory=dict)
