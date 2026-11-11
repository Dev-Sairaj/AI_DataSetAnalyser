"""Built-in fixes. See registry.py for the contract every fix follows."""

import re
import unicodedata

import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler, RobustScaler, StandardScaler

from adip.fixes.registry import FixSkipped, Stage, register_fix


def _names(cols: list[str], limit: int = 6) -> str:
    shown = ", ".join(f"'{c}'" for c in cols[:limit])
    extra = len(cols) - limit
    return f"{shown} and {extra} more" if extra > 0 else shown


MIN_PARSE_SHARE = 0.5  # cast_numeric refuses columns where fewer values than this parse


def _is_numeric(series: pd.Series) -> bool:
    return pd.api.types.is_numeric_dtype(series) and not pd.api.types.is_bool_dtype(series)


def _as_float(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").astype("float64")


# --------------------------------------------------------------------------- drop
@register_fix(
    "drop_columns",
    order=Stage.DROP,
    label="Drop columns",
    description="Remove columns that are empty, constant, identifiers or redundant.",
)
def drop_columns(df, cols, params):
    return df.drop(columns=cols), f"Dropped {len(cols)} column(s): {_names(cols)}."


@register_fix(
    "drop_duplicates",
    order=Stage.DROP + 1,
    label="Drop duplicate rows",
    description="Remove rows that repeat an earlier row. Columns are optional; "
    "without them whole rows are compared.",
    needs_columns=False,
    changes_rows=True,
    params={"keep": "'first' (default) or 'last'"},
)
def drop_duplicates(df, cols, params):
    keep = params.get("keep", "first")
    if keep not in ("first", "last"):
        raise ValueError(f"keep must be 'first' or 'last', got {keep!r}")
    subset = cols or None
    try:
        mask = df.duplicated(subset=subset, keep=keep)
    except TypeError:  # unhashable values such as lists
        mask = df.astype(str).duplicated(subset=subset, keep=keep)
    removed = int(mask.sum())
    if removed == 0:
        raise FixSkipped("No duplicate rows found.")
    scope = f" on {_names(cols)}" if cols else ""
    return df.loc[~mask].reset_index(drop=True), f"Removed {removed} duplicate row(s){scope}."


# -------------------------------------------------------------------------- types
@register_fix(
    "cast_numeric",
    order=Stage.TYPES,
    label="Convert to numeric",
    description="Convert text columns that hold numbers (spaces and thousands commas "
    "are stripped). Values that cannot be parsed become missing.",
)
def cast_numeric(df, cols, params):
    new: dict[str, pd.Series] = {}
    notes: list[str] = []
    refused: list[str] = []
    for c in cols:
        s = df[c]
        if _is_numeric(s):
            continue
        text = s.astype(str).str.strip().str.replace(",", "", regex=False).where(s.notna())
        numeric = pd.to_numeric(text, errors="coerce")
        non_null = int(s.notna().sum())
        parsed = int(numeric.notna().sum())
        if non_null == 0 or parsed / non_null < MIN_PARSE_SHARE:
            # Guard: converting genuine text would silently wipe the column.
            refused.append(f"'{c}' (only {parsed} of {non_null} values are numbers)")
            continue
        new[c] = numeric
        lost = non_null - parsed
        if lost > 0:
            notes.append(f"'{c}': {lost} unparseable value(s) became missing")
    if refused:
        notes.append("left unchanged: " + ", ".join(refused))
    if not new:
        reason = ": " + "; ".join(notes) if notes else ": already numeric"
        raise FixSkipped(
            "No column was converted" + reason + "."
        )
    for c, values in new.items():
        df[c] = values
    msg = f"Converted {len(new)} column(s) to numeric: {_names(list(new))}."
    return df, msg + (" " + "; ".join(notes) + "." if notes else "")


# ------------------------------------------------------------------- standardize
def _normalize_text_value(value: object, case: str) -> str:
    """Normalize Unicode, whitespace, and optional letter case for one value.

    Args:
        value: Original non-null cell value.
        case: One of ``preserve``, ``lower``, ``upper``, or ``title``.

    Returns:
        Normalized string value.

    Raises:
        ValueError: If the requested case strategy is unsupported.
    """
    text = " ".join(unicodedata.normalize("NFKC", str(value)).split())
    if case == "preserve":
        return text
    if case == "lower":
        return text.lower()
    if case == "upper":
        return text.upper()
    if case == "title":
        return text.title()
    raise ValueError("case must be one of preserve, lower, upper or title")


@register_fix(
    "standardize_text",
    order=Stage.TRANSFORM,
    label="Standardize text values",
    description="Normalize Unicode and whitespace, with optional lower, upper or title casing.",
    params={"case": "'preserve' (default), 'lower', 'upper' or 'title'"},
)
def standardize_text(df, cols, params):
    """Standardize selected text and categorical columns without changing nulls.

    Args:
        df: Private working dataframe owned by the fix engine.
        cols: Selected columns to standardize.
        params: Standardization parameters containing the optional case strategy.

    Returns:
        Updated dataframe and an audit message.

    Raises:
        FixSkipped: If none of the selected columns contain changeable values.
        ValueError: If the case strategy is unsupported.
    """
    case = str(params.get("case", "preserve"))
    changed_cells = 0
    changed_columns: list[str] = []
    for column in cols:
        series = df[column]
        if not (series.dtype == object or pd.api.types.is_string_dtype(series.dtype)):
            continue
        non_null = series.notna()
        normalized = series.astype(object).copy()
        normalized.loc[non_null] = series.loc[non_null].map(
            lambda value: _normalize_text_value(value, case)
        )
        changed = int(
            (series.loc[non_null].astype(str) != normalized.loc[non_null].astype(str)).sum()
        )
        if changed:
            df[column] = normalized
            changed_cells += changed
            changed_columns.append(column)
    if not changed_columns:
        raise FixSkipped("Selected text columns already use the requested standard format.")
    return (
        df,
        f"Standardized {changed_cells} value(s) across {len(changed_columns)} column(s): "
        f"{_names(changed_columns)}.",
    )


@register_fix(
    "normalize_dates",
    order=Stage.TRANSFORM + 1,
    label="Normalize date formats",
    description="Parse recognizable dates and write them in one explicit output format.",
    params={
        "format": "strftime output format; default '%Y-%m-%d'",
        "dayfirst": "true when ambiguous dates should be interpreted day-first",
    },
)
def normalize_dates(df, cols, params):
    """Normalize parseable date values while retaining invalid originals for review.

    Args:
        df: Private working dataframe owned by the fix engine.
        cols: Selected date columns.
        params: Output format and day-first parsing preference.

    Returns:
        Updated dataframe and an audit message containing invalid-value counts.

    Raises:
        FixSkipped: If no selected values can be parsed as dates.
        ValueError: If the supplied date format is invalid.
    """
    output_format = str(params.get("format", "%Y-%m-%d"))
    dayfirst = bool(params.get("dayfirst", False))
    normalized_columns: list[str] = []
    parsed_total = 0
    invalid_total = 0
    for column in cols:
        series = df[column]
        non_null = series.notna()
        if not non_null.any():
            continue
        parsed = pd.to_datetime(
            series.loc[non_null].astype(str).str.strip(),
            errors="coerce",
            dayfirst=dayfirst,
            format="mixed",
        )
        valid = parsed.notna()
        parsed_count = int(valid.sum())
        if parsed_count == 0:
            invalid_total += int(non_null.sum())
            continue
        result = series.astype(object).copy()
        valid_index = parsed.index[valid]
        result.loc[valid_index] = parsed.loc[valid].dt.strftime(output_format)
        df[column] = result
        normalized_columns.append(column)
        parsed_total += parsed_count
        invalid_total += int((~valid).sum())
    if not normalized_columns:
        raise FixSkipped(
            f"No parseable date values found; {invalid_total} value(s) remain invalid."
        )
    return (
        df,
        f"Normalized {parsed_total} date value(s) in {_names(normalized_columns)} to "
        f"'{output_format}'; {invalid_total} invalid value(s) were retained unchanged.",
    )


def _normalize_phone_value(value: object, country_code: str) -> str | None:
    """Validate and normalize one local or international phone number.

    Args:
        value: Original non-null phone value.
        country_code: Default numeric country code for local numbers.

    Returns:
        E.164-style number when valid; otherwise ``None``.

    Raises:
        No exceptions are raised for ordinary scalar values.
    """
    text = unicodedata.normalize("NFKC", str(value)).strip()
    international = text.startswith("+") or text.startswith("00")
    digits = re.sub(r"\D", "", text)
    if text.startswith("00"):
        digits = digits[2:] if digits.startswith("00") else digits
        international = True

    if international:
        return f"+{digits}" if 8 <= len(digits) <= 15 else None

    local = digits[1:] if digits.startswith("0") else digits
    if country_code == "91" and (len(local) != 10 or local[0] not in "6789"):
        return None
    combined = f"{country_code}{local}"
    return f"+{combined}" if 8 <= len(combined) <= 15 else None


@register_fix(
    "standardize_phone",
    order=Stage.TRANSFORM + 2,
    label="Validate and standardize phone numbers",
    description="Validate selected phone fields and normalize valid values to E.164-style text.",
    params={"country_code": "default numeric country code for local numbers; default '91'"},
)
def standardize_phone(df, cols, params):
    """Normalize valid phone values and retain invalid values for correction.

    Args:
        df: Private working dataframe owned by the fix engine.
        cols: Selected phone-number columns.
        params: Parameters containing the default country code.

    Returns:
        Updated dataframe and validation summary.

    Raises:
        FixSkipped: If the selected columns contain no non-null values.
        ValueError: If the default country code is not numeric.
    """
    country_code = str(params.get("country_code", "91")).lstrip("+")
    if not country_code.isdigit():
        raise ValueError("country_code must contain digits only")

    valid_total = 0
    invalid_total = 0
    changed_total = 0
    processed_columns: list[str] = []
    for column in cols:
        series = df[column]
        non_null = series.notna()
        if not non_null.any():
            continue
        result = series.astype(object).copy()
        for index, value in series.loc[non_null].items():
            normalized = _normalize_phone_value(value, country_code)
            if normalized is None:
                invalid_total += 1
                continue
            valid_total += 1
            if str(value) != normalized:
                result.at[index] = normalized
                changed_total += 1
        df[column] = result
        processed_columns.append(column)
    if not processed_columns:
        raise FixSkipped("Selected phone columns contain no values to validate.")
    return (
        df,
        f"Validated {valid_total + invalid_total} phone value(s) in {_names(processed_columns)}: "
        f"{valid_total} valid, {invalid_total} invalid, {changed_total} normalized. "
        "Invalid values were retained unchanged.",
    )


# ------------------------------------------------------------------------- impute
def _impute_numeric(df, cols, how: str):
    new: dict[str, pd.Series] = {}
    done: list[str] = []
    skipped: list[str] = []
    for c in cols:
        s = df[c]
        n_missing = int(s.isna().sum())
        if n_missing == 0:
            continue
        if not _is_numeric(s):
            skipped.append(f"'{c}' (not numeric, convert it first)")
            continue
        num = _as_float(s)
        value = num.median() if how == "median" else num.mean()
        if pd.isna(value):
            skipped.append(f"'{c}' (no values to learn from)")
            continue
        new[c] = num.fillna(value)
        done.append(f"'{c}' ({n_missing} -> {value:.6g})")
    note = f" Skipped {', '.join(skipped)}." if skipped else ""
    if not new:
        raise FixSkipped("Nothing to impute." + note)
    for c, values in new.items():
        df[c] = values
    return df, f"Filled missing values with the {how}: {', '.join(done)}.{note}"


@register_fix(
    "impute_median",
    order=Stage.IMPUTE,
    label="Impute with median",
    description="Fill missing numeric values with the column median. Robust to skew and outliers.",
)
def impute_median(df, cols, params):
    return _impute_numeric(df, cols, "median")


@register_fix(
    "impute_mean",
    order=Stage.IMPUTE + 1,
    label="Impute with mean",
    description="Fill missing numeric values with the column mean. Best for symmetric columns.",
)
def impute_mean(df, cols, params):
    return _impute_numeric(df, cols, "mean")


@register_fix(
    "impute_mode",
    order=Stage.IMPUTE + 2,
    label="Impute with most frequent value",
    description="Fill missing values with the most frequent value, or with a fixed label.",
    params={"label": "optional text to use instead of the mode, e.g. 'Missing'"},
)
def impute_mode(df, cols, params):
    label = params.get("label")
    new: dict[str, pd.Series] = {}
    done: list[str] = []
    for c in cols:
        s = df[c]
        n_missing = int(s.isna().sum())
        if n_missing == 0:
            continue
        if label is not None:
            value = label
        else:
            modes = s.mode(dropna=True)
            if modes.empty:
                continue
            value = modes.iloc[0]
        if isinstance(s.dtype, pd.CategoricalDtype):
            s = s.astype(object)
        new[c] = s.fillna(value)
        done.append(f"'{c}' ({n_missing} -> {value!r})")
    if not new:
        raise FixSkipped("Nothing to impute.")
    for c, values in new.items():
        df[c] = values
    return df, f"Filled missing values with the most frequent value: {', '.join(done)}."


# ------------------------------------------------------------------------- encode
@register_fix(
    "one_hot",
    order=Stage.ENCODE,
    label="One-hot encode",
    description="Replace a categorical column with one 0/1 column per category. "
    "Booleans become 0/1. Columns with too many categories are skipped.",
    params={
        "max_categories": "skip columns with more distinct values than this (config default)",
        "drop_first": "true to drop the first category (gives one 0/1 column for binary data)",
    },
)
def one_hot(df, cols, params):
    max_cat = int(params.get("max_categories", 50))
    drop_first = bool(params.get("drop_first", False))
    encode: list[str] = []
    booleans: list[str] = []
    skipped: list[str] = []
    for c in cols:
        s = df[c]
        n_unique = int(s.nunique(dropna=True))
        if pd.api.types.is_bool_dtype(s):
            booleans.append(c)
        elif n_unique == 0:
            skipped.append(f"'{c}' (empty)")
        elif n_unique > max_cat:
            skipped.append(f"'{c}' ({n_unique} categories, limit {max_cat})")
        else:
            encode.append(c)
    note = f" Skipped {', '.join(skipped)}." if skipped else ""
    if not encode and not booleans:
        raise FixSkipped("Nothing to encode." + note)

    cast = {c: df[c].astype(int) for c in booleans}
    out = pd.get_dummies(df, columns=encode, drop_first=drop_first, dtype=int) if encode else df
    for c, values in cast.items():
        out[c] = values
    parts = []
    if encode:
        added = out.shape[1] - df.shape[1] + len(encode)
        parts.append(f"One-hot encoded {_names(encode)} into {added} column(s)")
    if booleans:
        parts.append(f"cast {_names(booleans)} to 0/1")
    return out, "; ".join(parts) + "." + note


# -------------------------------------------------------------------------- scale
_SCALE_LABELS = {
    "standard": "Standard-scaled",
    "zscore": "Z-score standardized",
    "minmax": "Min-Max scaled",
    "robust": "Robust-scaled (median/IQR)",
    "log": "Log1p-transformed then standard-scaled",
}


@register_fix(
    "scale",
    order=Stage.SCALE,
    label="Scale numeric columns",
    description="Scale numeric columns. 'standard'/'zscore' = zero mean/unit variance, "
    "'minmax' = 0 to 1, 'robust' = "
    "median/IQR (outlier-resistant), 'log' = log1p then standard (for right-skewed, "
    "non-negative data).",
    params={"method": "'standard' (default), 'zscore', 'minmax', 'robust' or 'log'"},
)
def scale(df, cols, params):
    method = params.get("method", "standard")
    if method not in _SCALE_LABELS:
        raise ValueError(f"method must be one of {', '.join(_SCALE_LABELS)}; got {method!r}")
    new: dict[str, np.ndarray] = {}
    skipped: list[str] = []
    for c in cols:
        if not _is_numeric(df[c]):
            skipped.append(f"'{c}' (not numeric)")
            continue
        values = _as_float(df[c]).to_numpy()
        if np.isinf(values).any():
            skipped.append(f"'{c}' (has infinite values)")
            continue
        if not np.isfinite(values).any():
            skipped.append(f"'{c}' (no values)")
            continue
        if method == "log":
            if np.nanmin(values) < 0:
                skipped.append(f"'{c}' (negative values, log not defined)")
                continue
            values = np.log1p(values)
        if method == "robust":
            scaler = RobustScaler()
        elif method == "minmax":
            scaler = MinMaxScaler()
        else:
            scaler = StandardScaler()
        new[c] = scaler.fit_transform(values.reshape(-1, 1)).ravel()
    note = f" Skipped {', '.join(skipped)}." if skipped else ""
    if not new:
        raise FixSkipped("No numeric columns could be scaled." + note)
    for c, values in new.items():
        df[c] = values
    return df, f"{_SCALE_LABELS[method]} {len(new)} column(s): {_names(list(new))}.{note}"
