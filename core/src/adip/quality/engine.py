import logging

import numpy as np
import pandas as pd

from adip.config import QualityConfig, ScoringConfig
from adip.models.profile import DatasetProfile
from adip.models.quality import (
    IssueCode,
    OutlierSummary,
    QualityIssue,
    QualityReport,
    Severity,
)
from adip.quality.outliers import detect_outliers
from adip.quality.scoring import compute_score
from adip.quality.status import assess_dataset_status
from adip.utils.validation import has_mixed_types, numeric_text_ratio, pct

logger = logging.getLogger(__name__)

_SEVERITY_ORDER = {"critical": 0, "warning": 1, "info": 2}


def _issue(
    code: IssueCode,
    severity: Severity,
    message: str,
    column: str | None = None,
    count: int = 0,
    affected_pct: float = 0.0,
    **details: object,
) -> QualityIssue:
    return QualityIssue(
        code=code,
        severity=severity,
        column=column,
        message=message,
        affected_count=count,
        affected_pct=affected_pct,
        details=dict(details),
    )


class QualityEngine:
    """Detects data quality problems and produces an overall quality assessment."""

    def __init__(
        self,
        config: QualityConfig | None = None,
        scoring_config: ScoringConfig | None = None,
    ) -> None:
        """Initialize quality checks and scoring policy.

        Args:
            config: Detection thresholds and outlier settings.
            scoring_config: Dimension weights and grade thresholds.

        Raises:
            No exceptions are raised for validated configuration models.
        """
        self.config = config or QualityConfig()
        self.scoring_config = scoring_config or ScoringConfig()

    def run(self, df: pd.DataFrame, profile: DatasetProfile) -> QualityReport:
        issues: list[QualityIssue] = []
        issues += self._missing(profile)
        issues += self._duplicates(profile)
        issues += self._structure(profile)
        issues += self._dtypes(df, profile)
        outlier_issues, outliers = self._outliers(df, profile)
        issues += outlier_issues

        issues.sort(key=lambda i: (_SEVERITY_ORDER[i.severity], i.code, i.column or ""))
        scoring = compute_score(profile, issues, outliers, self.scoring_config)
        status, status_summary, status_rules = assess_dataset_status(issues)
        logger.info(
            "Quality score %.1f (%s), status %s, %d issues",
            scoring.score,
            scoring.grade,
            status,
            len(issues),
        )
        return QualityReport(
            score=scoring.score,
            grade=scoring.grade,
            status=status,
            status_summary=status_summary,
            status_rules=status_rules,
            score_breakdown=scoring.breakdown,
            dimension_scores=scoring.dimensions,
            score_explanation=scoring.score_explanation,
            grade_explanation=scoring.grade_explanation,
            grading_thresholds=scoring.thresholds,
            issues=issues,
            outliers=outliers,
        )

    def _missing(self, profile: DatasetProfile) -> list[QualityIssue]:
        cfg, found = self.config, []
        for col in profile.columns:
            if col.kind == "empty" or col.missing == 0:
                continue
            if col.missing_pct >= cfg.missing_critical_pct:
                severity: Severity = "critical"
            elif col.missing_pct >= cfg.missing_warn_pct:
                severity = "warning"
            else:
                severity = "info"
            found.append(
                _issue(
                    IssueCode.MISSING_VALUES,
                    severity,
                    f"'{col.name}' has {col.missing} missing values ({col.missing_pct}%).",
                    col.name,
                    col.missing,
                    col.missing_pct,
                )
            )
        return found

    def _duplicates(self, profile: DatasetProfile) -> list[QualityIssue]:
        if profile.duplicate_rows == 0:
            return []
        severity: Severity = "warning" if profile.duplicate_pct >= 1 else "info"
        return [
            _issue(
                IssueCode.DUPLICATE_ROWS,
                severity,
                f"{profile.duplicate_rows} duplicate rows ({profile.duplicate_pct}%).",
                None,
                profile.duplicate_rows,
                profile.duplicate_pct,
            )
        ]

    def _structure(self, profile: DatasetProfile) -> list[QualityIssue]:
        cfg, found = self.config, []
        for col in profile.columns:
            if col.kind == "empty":
                found.append(
                    _issue(
                        IssueCode.EMPTY_COLUMN,
                        "warning",
                        f"'{col.name}' is completely empty.",
                        col.name,
                        col.missing,
                        100.0,
                    )
                )
            elif col.unique == 1 and profile.n_rows > 1:
                found.append(
                    _issue(
                        IssueCode.CONSTANT_COLUMN,
                        "warning",
                        f"'{col.name}' has a single constant value.",
                        col.name,
                        col.non_null,
                        100.0,
                    )
                )
            elif (
                col.kind in ("categorical", "text")
                and col.unique >= cfg.high_cardinality_min_unique
                and col.unique_pct / 100 >= cfg.high_cardinality_ratio
            ):
                found.append(
                    _issue(
                        IssueCode.HIGH_CARDINALITY,
                        "warning",
                        f"'{col.name}' has {col.unique} distinct values ({col.unique_pct}%).",
                        col.name,
                        col.unique,
                        col.unique_pct,
                    )
                )
        return found

    def _dtypes(self, df: pd.DataFrame, profile: DatasetProfile) -> list[QualityIssue]:
        found: list[QualityIssue] = []
        for i, col in enumerate(profile.columns):
            if col.kind == "empty":
                continue
            series = df.iloc[:, i]

            if col.kind == "numeric":
                as_float = pd.to_numeric(series, errors="coerce").astype("float64")
                n_inf = int(np.isinf(as_float).sum())
                if n_inf:
                    found.append(
                        _issue(
                            IssueCode.INFINITE_VALUES,
                            "warning",
                            f"'{col.name}' contains {n_inf} infinite values.",
                            col.name,
                            n_inf,
                            pct(n_inf, profile.n_rows),
                        )
                    )

            ratio = numeric_text_ratio(series)
            if ratio is not None:
                if ratio == 1.0:
                    found.append(
                        _issue(
                            IssueCode.NUMERIC_AS_TEXT,
                            "warning",
                            f"'{col.name}' looks numeric but is stored as text.",
                            col.name,
                            col.non_null,
                            100.0,
                        )
                    )
                elif ratio >= 0.9:
                    bad = round((1 - ratio) * col.non_null)
                    found.append(
                        _issue(
                            IssueCode.INVALID_DTYPE,
                            "warning",
                            f"'{col.name}' is mostly numeric but {bad} values are not.",
                            col.name,
                            bad,
                            pct(bad, col.non_null),
                        )
                    )

            if has_mixed_types(series):
                found.append(
                    _issue(
                        IssueCode.MIXED_TYPES,
                        "warning",
                        f"'{col.name}' mixes several Python types.",
                        col.name,
                        col.non_null,
                        100.0,
                    )
                )

            inconsistent = self._inconsistent_text_format(series, col.name, col.non_null)
            if inconsistent is not None:
                found.append(inconsistent)
        return found

    @staticmethod
    def _inconsistent_text_format(
        series: pd.Series, column: str, non_null_count: int
    ) -> QualityIssue | None:
        """Detect whitespace and letter-case variants in textual values.

        Args:
            series: Source column values.
            column: User-facing column name.
            non_null_count: Number of non-null values used as the percentage denominator.

        Returns:
            A quality issue when inconsistent formatting is found; otherwise ``None``.

        Raises:
            No exceptions are raised for supported pandas series.
        """
        if not (series.dtype == object or pd.api.types.is_string_dtype(series.dtype)):
            return None

        values = series.dropna().astype(str)
        if values.empty:
            return None

        spacing_normalized = values.str.strip().str.replace(r"\s+", " ", regex=True)
        canonical = spacing_normalized.str.casefold()
        spacing_problem = values.ne(spacing_normalized)
        variant_counts = values.groupby(canonical).nunique()
        variant_keys = set(variant_counts[variant_counts > 1].index)
        variant_problem = canonical.isin(variant_keys)
        affected = int((spacing_problem | variant_problem).sum())
        if affected == 0:
            return None

        examples = list(dict.fromkeys(values[spacing_problem | variant_problem].head(10)))
        return _issue(
            IssueCode.INCONSISTENT_FORMAT,
            "warning",
            f"'{column}' contains {affected} values with inconsistent spacing or letter case.",
            column,
            affected,
            pct(affected, non_null_count),
            examples=examples,
            normalization="trim, collapse whitespace, and compare case-insensitively",
        )

    def _outliers(
        self, df: pd.DataFrame, profile: DatasetProfile
    ) -> tuple[list[QualityIssue], list[OutlierSummary]]:
        issues: list[QualityIssue] = []
        summaries: list[OutlierSummary] = []
        for i, col in enumerate(profile.columns):
            if col.kind != "numeric":
                continue
            summary = detect_outliers(df.iloc[:, i], self.config.outlier_method, self.config)
            if summary is None:
                continue
            summaries.append(summary)
            if summary.count > 0:
                severity: Severity = "warning" if summary.pct >= 10 else "info"
                issues.append(
                    _issue(
                        IssueCode.OUTLIERS,
                        severity,
                        f"'{col.name}' has {summary.count} outliers ({summary.pct}%) "
                        f"by {summary.method.upper()}.",
                        col.name,
                        summary.count,
                        summary.pct,
                        method=summary.method,
                        lower_bound=summary.lower_bound,
                        upper_bound=summary.upper_bound,
                    )
                )
        return issues, summaries
