"""Overall dataset quality score (0-100) built from four transparent dimensions."""

from adip.models.profile import DatasetProfile
from adip.models.quality import IssueCode, OutlierSummary, QualityIssue

WEIGHTS = {"completeness": 0.35, "uniqueness": 0.20, "validity": 0.25, "outliers": 0.20}

VALIDITY_CODES = {
    IssueCode.EMPTY_COLUMN,
    IssueCode.CONSTANT_COLUMN,
    IssueCode.NUMERIC_AS_TEXT,
    IssueCode.INVALID_DTYPE,
    IssueCode.MIXED_TYPES,
    IssueCode.INFINITE_VALUES,
}


def _clamp(value: float) -> float:
    return max(0.0, min(100.0, value))


def grade_for(score: float) -> str:
    for threshold, grade in ((90, "A"), (80, "B"), (70, "C"), (60, "D")):
        if score >= threshold:
            return grade
    return "F"


def compute_score(
    profile: DatasetProfile,
    issues: list[QualityIssue],
    outliers: list[OutlierSummary],
) -> tuple[float, str, dict[str, float]]:
    completeness = 100 - profile.missing_pct
    uniqueness = 100 - profile.duplicate_pct

    bad_columns = {i.column for i in issues if i.code in VALIDITY_CODES and i.column}
    validity = 100 * (1 - len(bad_columns) / max(profile.n_cols, 1))

    if outliers:
        avg_outlier_pct = sum(o.pct for o in outliers) / len(outliers)
        outlier_score = 100 - avg_outlier_pct * 5  # 20% outliers on average -> 0
    else:
        outlier_score = 100.0

    breakdown = {
        "completeness": round(_clamp(completeness), 2),
        "uniqueness": round(_clamp(uniqueness), 2),
        "validity": round(_clamp(validity), 2),
        "outliers": round(_clamp(outlier_score), 2),
    }
    score = round(sum(WEIGHTS[k] * v for k, v in breakdown.items()), 2)
    return score, grade_for(score), breakdown