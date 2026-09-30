"""Descriptive statistics helpers."""

import math

import numpy as np
import pandas as pd
from scipy import stats as sps

from adip.models.eda import CategoricalStats, CategoryCount, NumericStats
from adip.utils.validation import pct


def _f(value: object) -> float | None:
    try:
        v = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    return round(v, 6) if math.isfinite(v) else None


def to_float_array(series: pd.Series) -> np.ndarray:
    """Numeric values as float64, with NaN for missing/non-numeric and +-inf."""
    arr = pd.to_numeric(series, errors="coerce").to_numpy(
        dtype="float64", na_value=np.nan, copy=True
    )
    arr[~np.isfinite(arr)] = np.nan
    return arr


def clean_numeric(series: pd.Series) -> np.ndarray:
    """Finite numeric values only."""
    arr = to_float_array(series)
    return arr[~np.isnan(arr)]


def describe_shape(skew: float | None) -> str:
    if skew is None:
        return "n/a"
    magnitude = abs(skew)
    side = "right" if skew > 0 else "left"
    if magnitude < 0.5:
        return "approximately symmetric"
    if magnitude < 1:
        return f"moderately {side}-skewed"
    return f"highly {side}-skewed"


def numeric_stats(series: pd.Series) -> NumericStats | None:
    x = clean_numeric(series)
    if x.size == 0:
        return None
    q1, median, q3 = np.percentile(x, [25, 50, 75])
    std = float(x.std(ddof=1)) if x.size > 1 else None
    varies = float(np.ptp(x)) > 0
    skew = float(sps.skew(x, bias=False)) if x.size >= 3 and varies else None
    kurt = float(sps.kurtosis(x, bias=False)) if x.size >= 4 and varies else None
    skew_r = _f(skew)
    return NumericStats(
        column=str(series.name),
        count=int(x.size),
        mean=_f(x.mean()),
        std=_f(std),
        min=_f(x.min()),
        q1=_f(q1),
        median=_f(median),
        q3=_f(q3),
        max=_f(x.max()),
        iqr=_f(q3 - q1),
        skewness=skew_r,
        kurtosis=_f(kurt),
        n_zero=int((x == 0).sum()),
        n_negative=int((x < 0).sum()),
        shape=describe_shape(skew_r),
    )


def categorical_stats(series: pd.Series, top_n: int) -> CategoricalStats | None:
    counts = series.dropna().astype(str).value_counts()
    if counts.empty:
        return None
    total = int(counts.sum())
    top = [
        CategoryCount(value=str(k)[:60], count=int(v), pct=pct(int(v), total))
        for k, v in counts.head(top_n).items()
    ]
    other = total - sum(t.count for t in top)
    return CategoricalStats(
        column=str(series.name),
        unique=int(len(counts)),
        mode=top[0].value,
        mode_pct=top[0].pct,
        top_values=top,
        other_count=other,
        other_pct=pct(other, total),
    )