"""Histogram and box-plot data (chart-ready, no plotting here)."""

import numpy as np
import pandas as pd

from adip.eda.statistics import _f, clean_numeric
from adip.models.eda import BoxPlotData, HistogramData

MAX_FLIERS = 50


def histogram(series: pd.Series, bins: int) -> HistogramData | None:
    x = clean_numeric(series)
    if x.size == 0 or float(np.ptp(x)) == 0:
        return None
    # Clip the plotted range to the 0.5-99.5 percentiles so a single extreme value
    # does not squash the whole histogram. Box plots still show those values.
    lo, hi = np.percentile(x, [0.5, 99.5])
    if not hi > lo:
        lo, hi = float(x.min()), float(x.max())
    counts, edges = np.histogram(x, bins=bins, range=(float(lo), float(hi)))
    clipped = int(x.size - counts.sum())
    return HistogramData(
        column=str(series.name),
        bin_edges=[round(float(e), 6) for e in edges],
        counts=[int(c) for c in counts],
        clipped_count=clipped,
    )


def boxplot(series: pd.Series) -> BoxPlotData | None:
    x = clean_numeric(series)
    if x.size < 5 or float(np.ptp(x)) == 0:
        return None
    q1, median, q3 = (float(v) for v in np.percentile(x, [25, 50, 75]))
    iqr = q3 - q1
    low_fence, high_fence = q1 - 1.5 * iqr, q3 + 1.5 * iqr  # standard box-plot definition
    inside = x[(x >= low_fence) & (x <= high_fence)]
    outside = np.sort(x[(x < low_fence) | (x > high_fence)])
    if outside.size > MAX_FLIERS:
        outside = outside[np.linspace(0, outside.size - 1, MAX_FLIERS).astype(int)]
    return BoxPlotData(
        column=str(series.name),
        whisker_low=_f(inside.min() if inside.size else q1) or 0.0,
        q1=_f(q1) or 0.0,
        median=_f(median) or 0.0,
        q3=_f(q3) or 0.0,
        whisker_high=_f(inside.max() if inside.size else q3) or 0.0,
        n_outliers=int(((x < low_fence) | (x > high_fence)).sum()),
        outlier_values=[float(v) for v in outside],
    )