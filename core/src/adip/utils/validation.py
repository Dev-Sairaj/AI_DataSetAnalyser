"""Small, dependency-light helpers shared by the engines."""

import pandas as pd

from adip.models.profile import ColumnKind


def pct(part: float, whole: float) -> float:
    return round(part / whole * 100, 2) if whole else 0.0


def _is_textual(series: pd.Series) -> bool:
    return series.dtype == object or pd.api.types.is_string_dtype(series.dtype)


def infer_kind(series: pd.Series) -> ColumnKind:
    """Classify a column into a coarse analytical kind."""
    if series.isna().all():
        return "empty"
    if pd.api.types.is_bool_dtype(series):
        return "boolean"
    if pd.api.types.is_numeric_dtype(series):
        return "numeric"
    if pd.api.types.is_datetime64_any_dtype(series):
        return "datetime"
    non_null = series.dropna()
    if non_null.map(lambda v: isinstance(v, bool)).all():
        return "boolean"
    sample = non_null.head(1000).astype(str)
    if sample.str.len().mean() > 50:
        return "text"
    return "categorical"


def numeric_text_ratio(series: pd.Series) -> float | None:
    """Share of non-null text values that parse as numbers (None if not text)."""
    if not _is_textual(series):
        return None
    non_null = series.dropna()
    if non_null.empty:
        return None
    cleaned = non_null.astype(str).str.strip().str.replace(",", "", regex=False)
    return float(pd.to_numeric(cleaned, errors="coerce").notna().mean())


def has_mixed_types(series: pd.Series) -> bool:
    """True if an object column holds more than one Python type."""
    if series.dtype != object:
        return False
    return series.dropna().map(type).nunique() > 1


def safe_nunique(series: pd.Series) -> int:
    try:
        return int(series.nunique(dropna=True))
    except TypeError:  # unhashable values such as lists
        return int(series.astype(str).nunique())


def safe_duplicate_count(df: pd.DataFrame) -> int:
    try:
        return int(df.duplicated().sum())
    except TypeError:
        return int(df.astype(str).duplicated().sum())