"""Static PNG charts for the HTML and Excel exports.

Uses matplotlib's object-oriented Figure API (no pyplot) so it is thread-safe
inside the FastAPI background worker.
"""

import base64
import io
import logging
from collections.abc import Callable
from dataclasses import dataclass

import numpy as np
import seaborn as sns
from matplotlib.figure import Figure

from adip.models.eda import BoxPlotData, CorrelationResult, HistogramData
from adip.models.report import ChartData

logger = logging.getLogger(__name__)

PRIMARY = "#4F46E5"
LIGHT = "#C7D2FE"
MAX_NUMERIC_PLOTS = 12
MAX_CATEGORY_PLOTS = 8
MAX_BARS = 20


@dataclass(frozen=True)
class StaticPlot:
    key: str
    title: str
    group: str  # missing | correlation | histogram | boxplot | category
    png: bytes

    @property
    def b64(self) -> str:
        return base64.b64encode(self.png).decode("ascii")


def _fig(width: float, height: float) -> tuple[Figure, object]:
    fig = Figure(figsize=(width, height), layout="constrained")
    ax = fig.add_subplot(111)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.grid(alpha=0.25)
    ax.set_axisbelow(True)
    return fig, ax


def _png(fig: Figure) -> bytes:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=110)
    return buf.getvalue()


def _histogram(h: HistogramData) -> bytes:
    fig, ax = _fig(5.2, 3.3)
    edges = np.array(h.bin_edges)
    ax.bar(edges[:-1], h.counts, width=np.diff(edges), align="edge",
           color=PRIMARY, edgecolor="white", linewidth=0.5)
    ax.set_title(h.column, fontsize=11)
    ax.set_ylabel("Count")
    if h.clipped_count:
        ax.text(0.99, 0.97, f"{h.clipped_count} extreme values not shown", transform=ax.transAxes,
                ha="right", va="top", fontsize=7, color="#6B7280")
    return _png(fig)


def _boxplot(b: BoxPlotData) -> bytes:
    fig, ax = _fig(3.2, 3.8)
    stats = [{
        "med": b.median, "q1": b.q1, "q3": b.q3, "whislo": b.whisker_low,
        "whishi": b.whisker_high, "fliers": b.outlier_values, "label": b.column,
    }]
    ax.bxp(
        stats, patch_artist=True,
        boxprops={"facecolor": LIGHT, "edgecolor": PRIMARY},
        medianprops={"color": "#DC2626", "linewidth": 1.6},
        flierprops={"marker": "o", "markersize": 3, "markerfacecolor": PRIMARY, "alpha": 0.5},
    )
    ax.set_title(f"{b.column}\n{b.n_outliers} outliers", fontsize=10)
    return _png(fig)


def _heatmap(c: CorrelationResult) -> bytes:
    n = len(c.columns)
    size = min(max(4.5, 0.55 * n + 2), 14)
    fig = Figure(figsize=(size, size * 0.85), layout="constrained")
    ax = fig.add_subplot(111)
    sns.heatmap(
        np.array(c.matrix, dtype=float), ax=ax, cmap="coolwarm", vmin=-1, vmax=1, center=0,
        annot=n <= 12, fmt=".2f", annot_kws={"size": 8}, square=True,
        xticklabels=c.columns, yticklabels=c.columns, linewidths=0.4,
        cbar_kws={"shrink": 0.8},
    )
    ax.set_title("Correlation matrix (Pearson)", fontsize=11)
    ax.tick_params(axis="x", rotation=60, labelsize=8)
    ax.tick_params(axis="y", labelsize=8)
    return _png(fig)


def _missing(charts: ChartData) -> bytes:
    rows = charts.missing[:MAX_BARS]
    fig, ax = _fig(6.5, max(2.5, 0.35 * len(rows) + 1.2))
    ax.barh([r.column for r in rows][::-1], [r.missing_pct for r in rows][::-1], color="#F59E0B")
    ax.set_xlabel("Missing (%)")
    ax.set_title("Missing values by column", fontsize=11)
    ax.set_xlim(0, max(100, 1) if max(r.missing_pct for r in rows) > 50 else None)
    return _png(fig)


def _categories(column: str, values) -> bytes:
    fig, ax = _fig(5.4, max(2.4, 0.32 * len(values) + 1.2))
    ax.barh([v.value for v in values][::-1], [v.count for v in values][::-1], color=PRIMARY)
    ax.set_title(f"{column}: top categories", fontsize=11)
    ax.set_xlabel("Count")
    return _png(fig)


def _safe(key: str, title: str, group: str, fn: Callable[[], bytes]) -> StaticPlot | None:
    try:
        return StaticPlot(key, title, group, fn())
    except Exception:  # one bad chart must not break the report
        logger.warning("Could not render plot '%s'", key, exc_info=True)
        return None


def render_plots(charts: ChartData) -> list[StaticPlot]:
    plots: list[StaticPlot | None] = []
    if charts.missing:
        plots.append(_safe("missing", "Missing values", "missing", lambda: _missing(charts)))
    if charts.correlation:
        corr = charts.correlation
        plots.append(_safe("correlation", "Correlation heatmap", "correlation", lambda: _heatmap(corr)))
    for h in charts.histograms[:MAX_NUMERIC_PLOTS]:
        plots.append(_safe(f"hist_{h.column}", f"Distribution of {h.column}", "histogram",
                           lambda h=h: _histogram(h)))
    for b in charts.boxplots[:MAX_NUMERIC_PLOTS]:
        plots.append(_safe(f"box_{b.column}", f"Box plot of {b.column}", "boxplot",
                           lambda b=b: _boxplot(b)))
    for column, values in list(charts.category_frequencies.items())[:MAX_CATEGORY_PLOTS]:
        if values:
            plots.append(_safe(f"cat_{column}", f"Categories of {column}", "category",
                               lambda column=column, values=values: _categories(column, values)))
    return [p for p in plots if p is not None]