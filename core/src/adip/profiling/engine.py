import logging

import pandas as pd

from adip.models.profile import ColumnProfile, DatasetProfile
from adip.utils.validation import infer_kind, pct, safe_duplicate_count, safe_nunique

logger = logging.getLogger(__name__)


class ProfilingEngine:
    """Computes structural facts about a dataset: shape, types, missing, duplicates, uniques."""

    def run(self, df: pd.DataFrame) -> DatasetProfile:
        n_rows, n_cols = df.shape
        columns = [self._profile_column(df.iloc[:, i], n_rows) for i in range(n_cols)]

        total_cells = n_rows * n_cols
        total_missing = sum(c.missing for c in columns)
        duplicates = safe_duplicate_count(df)
        logger.info("Profiled %d columns", n_cols)

        return DatasetProfile(
            n_rows=n_rows,
            n_cols=n_cols,
            memory_bytes=int(df.memory_usage(deep=True).sum()),
            total_cells=total_cells,
            total_missing=total_missing,
            missing_pct=pct(total_missing, total_cells),
            duplicate_rows=duplicates,
            duplicate_pct=pct(duplicates, n_rows),
            columns=columns,
        )

    @staticmethod
    def _profile_column(series: pd.Series, n_rows: int) -> ColumnProfile:
        missing = int(series.isna().sum())
        non_null = n_rows - missing
        unique = safe_nunique(series)
        samples = series.dropna().head(1000).astype(str).unique()[:3]
        return ColumnProfile(
            name=str(series.name),
            dtype=str(series.dtype),
            kind=infer_kind(series),
            non_null=non_null,
            missing=missing,
            missing_pct=pct(missing, n_rows),
            unique=unique,
            unique_pct=pct(unique, non_null),
            memory_bytes=int(series.memory_usage(deep=True, index=False)),
            sample_values=[str(v)[:40] for v in samples],
        )