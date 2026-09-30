"""Rule functions that turn analysis results into guidance. None of them modify data."""

from collections import defaultdict

import pandas as pd

from adip.config import FeaturesConfig, QualityConfig
from adip.models.eda import CategoricalStats, CorrelationResult, NumericStats
from adip.models.features import Recommendation, RecCategory
from adip.models.profile import ColumnProfile, DatasetProfile
from adip.models.quality import IssueCode, OutlierSummary, QualityReport, Severity


def _rec(
    category: RecCategory,
    severity: Severity,
    title: str,
    recommendation: str,
    rationale: str,
    column: str | None = None,
    columns: list[str] | None = None,
) -> Recommendation:
    return Recommendation(
        category=category,
        severity=severity,
        column=column,
        columns=columns or ([column] if column else []),
        title=title,
        recommendation=recommendation,
        rationale=rationale,
    )


def is_identifier(col: ColumnProfile, cfg: FeaturesConfig) -> bool:
    """Column that is (almost) unique per row: an ID, not a predictive feature."""
    if col.non_null < 20 or col.unique_pct < cfg.id_unique_pct:
        return False
    if col.kind == "categorical":
        return True
    if col.kind == "numeric":
        return col.dtype.lower().startswith(("int", "uint"))
    return False


def type_rules(quality: QualityReport, skip: set[str]) -> list[Recommendation]:
    return [
        _rec(
            "data_types",
            "warning",
            f"Convert '{i.column}' to numeric",
            "Cast the column to a numeric dtype (for example with pd.to_numeric).",
            "Every value parses as a number, but the column is stored as text.",
            column=i.column,
        )
        for i in quality.issues
        if i.code == IssueCode.NUMERIC_AS_TEXT and i.column and i.column not in skip
    ]


def missing_rules(
    profile: DatasetProfile,
    stats: dict[str, NumericStats],
    qcfg: QualityConfig,
    fcfg: FeaturesConfig,
    skip: set[str],
) -> list[Recommendation]:
    recs = []
    for col in profile.columns:
        if col.name in skip or col.missing == 0 or col.kind == "empty":
            continue
        if col.missing_pct >= qcfg.missing_critical_pct:
            recs.append(
                _rec(
                    "missing_values",
                    "critical",
                    f"Consider dropping '{col.name}'",
                    "Drop the column, or collect more data. Imputing this much is unreliable.",
                    f"{col.missing_pct}% of values are missing (critical threshold "
                    f"{qcfg.missing_critical_pct}%).",
                    column=col.name,
                )
            )
            continue

        if col.kind == "numeric":
            s = stats.get(col.name)
            skewed = bool(s and s.skewness is not None and abs(s.skewness) >= fcfg.skew_threshold)
            method = "median imputation" if skewed else "mean imputation"
            why = "the distribution is skewed, so the median is more robust" if skewed else (
                "the distribution is roughly symmetric"
            )
        elif col.kind in ("categorical", "boolean"):
            method = "mode imputation or an explicit 'Missing' category"
            why = "the column is categorical"
        elif col.kind == "datetime":
            method = "forward/backward fill if the data is time-ordered, otherwise drop the rows"
            why = "the column is a date/time"
        else:
            method = "fill with an empty string or drop the rows"
            why = "the column is free text"

        low = col.missing_pct < qcfg.missing_warn_pct
        extra = " Dropping the affected rows is also reasonable at this level." if low else ""
        recs.append(
            _rec(
                "missing_values",
                "info" if low else "warning",
                f"Impute '{col.name}'",
                f"Use {method}.{extra}",
                f"{col.missing} values missing ({col.missing_pct}%); {why}.",
                column=col.name,
            )
        )
    return recs


def encoding_rules(
    profile: DatasetProfile,
    qcfg: QualityConfig,
    fcfg: FeaturesConfig,
    skip: set[str],
) -> list[Recommendation]:
    recs = []
    for col in profile.columns:
        if col.name in skip:
            continue
        if col.kind == "boolean":
            recs.append(
                _rec("encoding", "info", f"Cast '{col.name}' to 0/1",
                     "Convert the boolean to an integer flag.",
                     "Most models need numeric input.", column=col.name)
            )
        elif col.kind == "categorical" and col.unique > 1:
            u = col.unique
            if u == 2:
                rec, why, sev = "Binary (label) encoding to 0/1.", "Only two categories.", "info"
            elif u <= fcfg.onehot_max_unique:
                rec, why, sev = "One-hot encoding.", f"{u} categories keeps dimensionality low.", "info"
            elif u >= qcfg.high_cardinality_min_unique and col.unique_pct / 100 >= qcfg.high_cardinality_ratio:
                rec = "Target, frequency or hashing encoding. Avoid one-hot."
                why, sev = f"{u} categories ({col.unique_pct}% unique) would explode a one-hot matrix.", "warning"
            else:
                rec = "Target, frequency or ordinal encoding (one-hot only if the model handles wide inputs)."
                why, sev = f"{u} categories would add {u} one-hot columns.", "info"
            recs.append(_rec("encoding", sev, f"Encode '{col.name}'", rec, why, column=col.name))
        elif col.kind == "text":
            recs.append(
                _rec("encoding", "info", f"Vectorize '{col.name}'",
                     "Use TF-IDF or text embeddings, or exclude the column.",
                     "Long free text cannot be one-hot encoded.", column=col.name)
            )
        elif col.kind == "datetime":
            recs.append(
                _rec("encoding", "info", f"Extract features from '{col.name}'",
                     "Derive year, month, day of week, hour or elapsed time.",
                     "Models cannot use raw timestamps directly.", column=col.name)
            )
    return recs


def scaling_rules(
    profile: DatasetProfile,
    stats: dict[str, NumericStats],
    outliers: list[OutlierSummary],
    fcfg: FeaturesConfig,
    skip: set[str],
) -> list[Recommendation]:
    outlier_pct = {o.column: o.pct for o in outliers}
    log_cols: list[str] = []
    robust_cols: list[str] = []
    std_cols: list[str] = []
    ranges: list[float] = []

    for col in profile.columns:
        if col.kind != "numeric" or col.name in skip or col.unique <= 2:
            continue
        s = stats.get(col.name)
        if s is None or not s.std or s.min is None or s.max is None:
            continue
        ranges.append(s.max - s.min)
        skew = s.skewness or 0.0
        if skew >= fcfg.skew_threshold and s.n_negative == 0:
            log_cols.append(col.name)
        elif abs(skew) >= fcfg.skew_threshold or outlier_pct.get(col.name, 0) >= fcfg.robust_outlier_pct:
            robust_cols.append(col.name)
        else:
            std_cols.append(col.name)

    positive = [r for r in ranges if r > 0]
    spread = max(positive) / min(positive) if len(positive) > 1 else 1.0
    severity: Severity = "warning" if spread >= 100 else "info"
    note = f"Feature ranges differ by a factor of about {spread:,.0f}. " if spread >= 100 else ""
    tail = " Tree-based models do not need scaling."

    recs = []
    if log_cols:
        recs.append(_rec("scaling", severity, "Log-transform, then scale",
                         "Apply log1p, then StandardScaler." + tail,
                         note + "These columns are highly right-skewed and non-negative.",
                         columns=log_cols))
    if robust_cols:
        recs.append(_rec("scaling", severity, "Use RobustScaler",
                         "Scale with median and IQR (RobustScaler)." + tail,
                         note + "These columns are skewed or have many outliers, which distort mean/std scaling.",
                         columns=robust_cols))
    if std_cols:
        recs.append(_rec("scaling", severity, "Use StandardScaler",
                         "Standardize to zero mean and unit variance." + tail,
                         note + "These columns are roughly symmetric with few outliers.",
                         columns=std_cols))
    return recs


def low_value_rules(
    profile: DatasetProfile,
    cats: dict[str, CategoricalStats],
    ids: set[str],
    fcfg: FeaturesConfig,
    skip: set[str],
) -> list[Recommendation]:
    recs = []
    for col in profile.columns:
        if col.name in skip:
            continue
        if col.kind == "empty":
            recs.append(_rec("low_value", "warning", f"Drop '{col.name}'",
                             "Remove the column.", "It contains no values.", column=col.name))
        elif col.unique == 1 and profile.n_rows > 1:
            recs.append(_rec("low_value", "warning", f"Drop '{col.name}'",
                             "Remove the column.", "It holds a single constant value, so it carries no signal.",
                             column=col.name))
        elif col.name in ids:
            recs.append(_rec("low_value", "warning", f"Exclude '{col.name}' from modelling",
                             "Keep it as a row key only.",
                             f"{col.unique_pct}% of values are unique, so it looks like an identifier "
                             "and would cause overfitting.", column=col.name))
        elif (c := cats.get(col.name)) is not None and c.unique > 1 and c.mode_pct >= fcfg.near_constant_pct:
            recs.append(_rec("low_value", "info", f"'{col.name}' is nearly constant",
                             "Consider dropping it.",
                             f"One value ('{c.mode}') makes up {c.mode_pct}% of the rows.", column=col.name))
    return recs


def find_duplicate_columns(df: pd.DataFrame, profile: DatasetProfile) -> list[tuple[str, str]]:
    """Pairs of columns holding identical values (cheap pre-grouping, then exact compare)."""
    groups: dict[tuple[str, int, int], list[int]] = defaultdict(list)
    for i, c in enumerate(profile.columns):
        if c.kind != "empty" and c.unique > 1:
            groups[(c.dtype, c.unique, c.missing)].append(i)

    pairs: list[tuple[str, str]] = []
    names = [c.name for c in profile.columns]
    for idxs in groups.values():
        representatives: list[int] = []
        for i in idxs:
            for j in representatives:
                if df.iloc[:, i].equals(df.iloc[:, j]):
                    pairs.append((names[j], names[i]))
                    break
            else:
                representatives.append(i)
    return pairs


def redundancy_rules(
    df: pd.DataFrame,
    profile: DatasetProfile,
    correlation: CorrelationResult | None,
    fcfg: FeaturesConfig,
    skip: set[str],
) -> list[Recommendation]:
    recs = []
    for keep, drop in find_duplicate_columns(df, profile):
        if keep in skip or drop in skip:
            continue
        recs.append(_rec("redundancy", "warning", f"'{drop}' duplicates '{keep}'",
                         f"Drop '{drop}'.", "Both columns contain identical values.",
                         columns=[keep, drop]))

    if correlation:
        missing = {c.name: c.missing for c in profile.columns}
        for pair in correlation.high_pairs[: fcfg.max_correlation_recommendations]:
            a, b = pair.column_a, pair.column_b
            if a in skip or b in skip:
                continue
            drop = a if missing.get(a, 0) > missing.get(b, 0) else b
            keep = b if drop == a else a
            recs.append(_rec("redundancy", "warning", f"'{a}' and '{b}' are highly correlated",
                             f"Keep '{keep}' and consider dropping '{drop}'.",
                             f"Pearson r = {pair.coefficient} (threshold {correlation.threshold}). "
                             "Redundant features add multicollinearity without new information.",
                             columns=[a, b]))
    return recs