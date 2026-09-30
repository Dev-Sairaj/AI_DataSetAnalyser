from adip.models.eda import EdaReport
from adip.models.profile import DatasetProfile
from adip.models.report import ChartData, MissingBar


def build_chart_data(profile: DatasetProfile, eda: EdaReport) -> ChartData:
    """Assemble chart-ready JSON data. The React dashboard renders this directly."""
    missing = sorted(
        (MissingBar(column=c.name, missing=c.missing, missing_pct=c.missing_pct)
         for c in profile.columns if c.missing > 0),
        key=lambda m: m.missing_pct,
        reverse=True,
    )
    return ChartData(
        histograms=eda.histograms,
        boxplots=eda.boxplots,
        correlation=eda.correlation,
        category_frequencies={c.column: c.top_values for c in eda.categorical},
        missing=missing,
    )