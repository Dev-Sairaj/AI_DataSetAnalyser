import numpy as np
import pandas as pd

from adip.config import EdaConfig
from adip.eda.statistics import to_float_array
from adip.models.eda import CorrelationPair, CorrelationResult
from adip.models.profile import DatasetProfile

MAX_CORR_COLUMNS = 40


def compute_correlation(
    df: pd.DataFrame, profile: DatasetProfile, cfg: EdaConfig
) -> CorrelationResult | None:
    picked = [(i, c.name) for i, c in enumerate(profile.columns) if c.kind == "numeric"]
    if len(picked) < 2:
        return None

    n = len(df)
    rows = None
    if n > cfg.sample_size:
        rows = np.sort(np.random.default_rng(42).choice(n, cfg.sample_size, replace=False))

    data = {}
    for i, name in picked:
        arr = to_float_array(df.iloc[:, i])
        data[name] = arr if rows is None else arr[rows]
    frame = pd.DataFrame(data)
    frame = frame.loc[:, frame.nunique() > 1]  # constant columns have no correlation
    truncated = frame.shape[1] > MAX_CORR_COLUMNS
    frame = frame.iloc[:, :MAX_CORR_COLUMNS]
    if frame.shape[1] < 2:
        return None

    corr = frame.corr(method="pearson", min_periods=3)
    values = corr.to_numpy()
    cols = [str(c) for c in corr.columns]

    pairs: list[CorrelationPair] = []
    for i in range(len(cols)):
        for j in range(i + 1, len(cols)):
            v = values[i, j]
            if not np.isnan(v) and abs(v) >= cfg.correlation_threshold:
                pairs.append(CorrelationPair(column_a=cols[i], column_b=cols[j], coefficient=round(float(v), 4)))
    pairs.sort(key=lambda p: abs(p.coefficient), reverse=True)

    return CorrelationResult(
        method="pearson",
        columns=cols,
        matrix=[[None if np.isnan(v) else round(float(v), 4) for v in row] for row in values],
        high_pairs=pairs,
        threshold=cfg.correlation_threshold,
        n_rows_used=int(len(frame)),
        sampled=rows is not None,
        columns_truncated=truncated,
    )