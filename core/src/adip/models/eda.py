from pydantic import BaseModel, Field


class NumericStats(BaseModel):
    column: str
    count: int
    mean: float | None
    std: float | None
    min: float | None
    q1: float | None
    median: float | None
    q3: float | None
    max: float | None
    iqr: float | None
    skewness: float | None
    kurtosis: float | None
    n_zero: int
    n_negative: int
    shape: str  # e.g. "highly right-skewed"


class HistogramData(BaseModel):
    column: str
    bin_edges: list[float]
    counts: list[int]
    clipped_count: int = 0  # extreme values excluded from the plotted range


class BoxPlotData(BaseModel):
    column: str
    whisker_low: float
    q1: float
    median: float
    q3: float
    whisker_high: float
    n_outliers: int
    outlier_values: list[float] = Field(default_factory=list)  # capped sample for plotting


class CategoryCount(BaseModel):
    value: str
    count: int
    pct: float


class CategoricalStats(BaseModel):
    column: str
    unique: int
    mode: str
    mode_pct: float
    top_values: list[CategoryCount]
    other_count: int = 0
    other_pct: float = 0.0


class CorrelationPair(BaseModel):
    column_a: str
    column_b: str
    coefficient: float


class CorrelationResult(BaseModel):
    method: str
    columns: list[str]
    matrix: list[list[float | None]]
    high_pairs: list[CorrelationPair]
    threshold: float
    n_rows_used: int
    sampled: bool
    columns_truncated: bool = False


class EdaReport(BaseModel):
    numeric: list[NumericStats]
    categorical: list[CategoricalStats]
    histograms: list[HistogramData]
    boxplots: list[BoxPlotData]
    correlation: CorrelationResult | None = None