"""Outlier detectors. Add a new method by adding a branch and a config literal."""

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

from adip.config import QualityConfig
from adip.models.quality import OutlierSummary

MIN_VALUES = 10


def detect_outliers(
    series: pd.Series, method: str, cfg: QualityConfig
) -> OutlierSummary | None:
    """Return an outlier summary, or None if the column is unsuitable (binary/constant/tiny)."""
    values = (
        pd.to_numeric(series, errors="coerce")
        .astype("float64")
        .replace([np.inf, -np.inf], np.nan)
        .dropna()
    )
    if len(values) < MIN_VALUES or values.nunique() <= 2:
        return None

    lower: float | None = None
    upper: float | None = None

    if method == "iqr":
        q1, q3 = values.quantile([0.25, 0.75])
        iqr = q3 - q1
        if iqr == 0:
            return None
        lower = float(q1 - cfg.iqr_multiplier * iqr)
        upper = float(q3 + cfg.iqr_multiplier * iqr)
        mask = (values < lower) | (values > upper)
    elif method == "zscore":
        std = values.std(ddof=0)
        if std == 0:
            return None
        mean = values.mean()
        lower = float(mean - cfg.zscore_threshold * std)
        upper = float(mean + cfg.zscore_threshold * std)
        mask = ((values - mean) / std).abs() > cfg.zscore_threshold
    elif method == "isolation_forest":
        model = IsolationForest(n_estimators=100, contamination="auto", random_state=42)
        mask = pd.Series(
            model.fit_predict(values.to_numpy().reshape(-1, 1)) == -1, index=values.index
        )
    else:
        raise ValueError(f"Unknown outlier method: {method}")

    count = int(mask.sum())
    return OutlierSummary(
        column=str(series.name),
        method=method,
        count=count,
        pct=round(count / len(values) * 100, 2),
        lower_bound=lower,
        upper_bound=upper,
    )