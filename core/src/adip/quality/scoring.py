"""Configurable six-dimension dataset quality scoring."""

from dataclasses import dataclass

from adip.config import GradeThresholds, ScoringConfig
from adip.models.profile import DatasetProfile
from adip.models.quality import DimensionScore, IssueCode, OutlierSummary, QualityIssue

CONSISTENCY_CODES = {IssueCode.INCONSISTENT_FORMAT, IssueCode.MIXED_TYPES}
VALIDITY_CODES = {
    IssueCode.INVALID_DTYPE,
    IssueCode.NUMERIC_AS_TEXT,
    IssueCode.INFINITE_VALUES,
}


@dataclass(frozen=True)
class ScoringResult:
    """Complete result of the configured quality-scoring calculation."""

    score: float
    grade: str
    breakdown: dict[str, float]
    dimensions: list[DimensionScore]
    score_explanation: str
    grade_explanation: str
    thresholds: dict[str, float]


def _clamp(value: float) -> float:
    """Constrain a dimension score to the inclusive 0-100 range.

    Args:
        value: Raw score value.

    Returns:
        The value constrained to the valid scoring range.

    Raises:
        No exceptions are raised.
    """
    return max(0.0, min(100.0, value))


def _column_score(
    profile: DatasetProfile,
    issues: list[QualityIssue],
    codes: set[IssueCode],
) -> tuple[float, set[str]]:
    """Calculate the share of columns without selected findings.

    Args:
        profile: Dataset profile containing the total column count.
        issues: Detected quality findings.
        codes: Issue codes that reduce the dimension score.

    Returns:
        A score from 0 to 100 and the affected column names.

    Raises:
        No exceptions are raised for a validated dataset profile.
    """
    affected = {issue.column for issue in issues if issue.code in codes and issue.column}
    score = 100 * (1 - len(affected) / max(profile.n_cols, 1))
    return _clamp(score), affected


def grade_for(score: float, thresholds: GradeThresholds | None = None) -> str:
    """Map an overall score to a grade using inclusive configured thresholds.

    Args:
        score: Overall quality score from 0 to 100.
        thresholds: Optional A-through-D minimum score configuration.

    Returns:
        One of ``A``, ``B``, ``C``, ``D``, or ``F``.

    Raises:
        No exceptions are raised for a valid threshold model.
    """
    configured = thresholds or GradeThresholds()
    for threshold, grade in (
        (configured.a, "A"),
        (configured.b, "B"),
        (configured.c, "C"),
        (configured.d, "D"),
    ):
        if score >= threshold:
            return grade
    return "F"


def _grade_explanation(score: float, grade: str, thresholds: GradeThresholds) -> str:
    """Build a user-facing explanation of the selected grade band.

    Args:
        score: Calculated overall score.
        grade: Grade assigned to the score.
        thresholds: Active grade thresholds.

    Returns:
        Plain-language grade explanation.

    Raises:
        No exceptions are raised for valid scoring inputs.
    """
    if grade == "A":
        band = f"score >= {thresholds.a:g}"
    elif grade == "B":
        band = f"{thresholds.b:g} <= score < {thresholds.a:g}"
    elif grade == "C":
        band = f"{thresholds.c:g} <= score < {thresholds.b:g}"
    elif grade == "D":
        band = f"{thresholds.d:g} <= score < {thresholds.c:g}"
    else:
        band = f"score < {thresholds.d:g}"
    return f"Grade {grade} was assigned because the overall score is {score:g} ({band})."


def compute_score(
    profile: DatasetProfile,
    issues: list[QualityIssue],
    outliers: list[OutlierSummary],
    config: ScoringConfig | None = None,
) -> ScoringResult:
    """Calculate six quality dimensions and a configurable overall score.

    Unassessed dimensions are excluded and assessed weights are proportionally
    renormalized. Timeliness is not inferred without reporting-period metadata.
    Accuracy uses numeric outliers only as a proxy for anomaly risk.

    Args:
        profile: Dataset-level and column-level profile.
        issues: Findings produced by the quality engine.
        outliers: Numeric outlier summaries.
        config: Optional scoring weights, thresholds, and unassessed policy.

    Returns:
        Detailed dimension scores, effective weights, overall score, and grade.

    Raises:
        ValueError: If no assessed dimension has a positive configured weight.
    """
    cfg = config or ScoringConfig()
    weights = cfg.weights.model_dump()
    consistency, consistency_columns = _column_score(profile, issues, CONSISTENCY_CODES)
    validity, validity_columns = _column_score(profile, issues, VALIDITY_CODES)

    if outliers:
        average_outlier_pct = sum(item.pct for item in outliers) / len(outliers)
        accuracy_score: float | None = _clamp(100 - average_outlier_pct * 5)
        accuracy_assessment = "proxy"
        accuracy_evidence = (
            f"Average numeric outlier rate is {average_outlier_pct:.2f}% across "
            f"{len(outliers)} assessed numeric column(s)."
        )
    else:
        accuracy_score = None
        accuracy_assessment = "not_assessed"
        accuracy_evidence = "No numeric column was available for the automated outlier proxy."

    dimensions = [
        DimensionScore(
            name="Accuracy",
            score=round(accuracy_score, 2) if accuracy_score is not None else None,
            assessment=accuracy_assessment,
            configured_weight=weights["accuracy"],
            effective_weight=0.0,
            formula="100 - min(100, average numeric outlier percentage x 5)",
            evidence=accuracy_evidence,
            limitation=(
                "This is an anomaly-based proxy. Factual correctness requires trusted reference "
                "data or manual verification."
            ),
        ),
        DimensionScore(
            name="Completeness",
            score=round(_clamp(100 - profile.missing_pct), 2),
            assessment="automated",
            configured_weight=weights["completeness"],
            effective_weight=0.0,
            formula="100 - missing cell percentage",
            evidence=f"Dataset missing-cell rate is {profile.missing_pct:.2f}%.",
        ),
        DimensionScore(
            name="Consistency",
            score=round(consistency, 2),
            assessment="automated",
            configured_weight=weights["consistency"],
            effective_weight=0.0,
            formula="100 x (1 - columns with mixed types or inconsistent formats / all columns)",
            evidence=(
                f"{len(consistency_columns)} of {profile.n_cols} column(s) have consistency findings."
            ),
        ),
        DimensionScore(
            name="Timeliness",
            score=None,
            assessment="not_assessed",
            configured_weight=weights["timeliness"],
            effective_weight=0.0,
            formula="Requires reporting-period, update-frequency, or reference-date metadata",
            evidence="No reporting deadline or authoritative freshness metadata was supplied.",
            limitation="No timeliness score is invented from file timestamps.",
        ),
        DimensionScore(
            name="Validity",
            score=round(validity, 2),
            assessment="automated",
            configured_weight=weights["validity"],
            effective_weight=0.0,
            formula="100 x (1 - columns with invalid types or infinite values / all columns)",
            evidence=f"{len(validity_columns)} of {profile.n_cols} column(s) have validity findings.",
        ),
        DimensionScore(
            name="Uniqueness",
            score=round(_clamp(100 - profile.duplicate_pct), 2),
            assessment="automated",
            configured_weight=weights["uniqueness"],
            effective_weight=0.0,
            formula="100 - duplicate row percentage",
            evidence=f"Dataset duplicate-row rate is {profile.duplicate_pct:.2f}%.",
        ),
    ]

    assessed_weight = sum(item.configured_weight for item in dimensions if item.score is not None)
    if assessed_weight <= 0:
        raise ValueError("At least one assessed quality dimension must have a positive weight.")

    weighted_dimensions: list[DimensionScore] = []
    for item in dimensions:
        effective_weight = (
            item.configured_weight / assessed_weight if item.score is not None else 0.0
        )
        weighted_dimensions.append(
            item.model_copy(update={"effective_weight": round(effective_weight, 6)})
        )

    score = round(
        sum((item.score or 0.0) * item.effective_weight for item in weighted_dimensions), 2
    )
    grade = grade_for(score, cfg.thresholds)
    breakdown = {
        item.name.lower(): item.score for item in weighted_dimensions if item.score is not None
    }
    omitted = [item.name for item in weighted_dimensions if item.score is None]
    explanation = (
        "Overall score is the weighted average of assessed dimensions. Configured weights were "
        "proportionally renormalized across assessed dimensions"
        + (f"; omitted as not assessed: {', '.join(omitted)}." if omitted else ".")
    )
    thresholds = {
        "A": cfg.thresholds.a,
        "B": cfg.thresholds.b,
        "C": cfg.thresholds.c,
        "D": cfg.thresholds.d,
        "F": 0.0,
    }
    return ScoringResult(
        score=score,
        grade=grade,
        breakdown=breakdown,
        dimensions=weighted_dimensions,
        score_explanation=explanation,
        grade_explanation=_grade_explanation(score, grade, cfg.thresholds),
        thresholds=thresholds,
    )
