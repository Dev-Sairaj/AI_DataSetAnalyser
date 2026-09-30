import logging

import pandas as pd

from adip.config import EdaConfig
from adip.eda.correlation import compute_correlation
from adip.eda.distributions import boxplot, histogram
from adip.eda.statistics import categorical_stats, numeric_stats
from adip.models.eda import EdaReport
from adip.models.profile import DatasetProfile

logger = logging.getLogger(__name__)


class EdaEngine:
    """Statistical summaries, distributions and correlations."""

    def __init__(self, config: EdaConfig | None = None) -> None:
        self.config = config or EdaConfig()

    def run(self, df: pd.DataFrame, profile: DatasetProfile) -> EdaReport:
        cfg = self.config
        report = EdaReport(numeric=[], categorical=[], histograms=[], boxplots=[])

        for i, col in enumerate(profile.columns):
            series = df.iloc[:, i]
            if col.kind == "numeric":
                if (stats := numeric_stats(series)) is not None:
                    report.numeric.append(stats)
                if (hist := histogram(series, cfg.histogram_bins)) is not None:
                    report.histograms.append(hist)
                if (box := boxplot(series)) is not None:
                    report.boxplots.append(box)
            elif col.kind in ("categorical", "boolean"):
                if (cat := categorical_stats(series, cfg.max_categories_shown)) is not None:
                    report.categorical.append(cat)

        report.correlation = compute_correlation(df, profile, cfg)
        logger.info(
            "EDA: %d numeric, %d categorical, %d high correlations",
            len(report.numeric),
            len(report.categorical),
            len(report.correlation.high_pairs) if report.correlation else 0,
        )
        return report