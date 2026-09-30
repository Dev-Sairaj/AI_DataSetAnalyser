import logging

import numpy as np
import pandas as pd

from adip.config import QualityConfig
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

    def __init__(self, config: QualityConfig | None = None) -> None:
        self.config = config or QualityConfig()

    def run(self, df: pd.DataFrame, profile: DatasetProfile) -> QualityReport:
        issues: list[QualityIssue] = []
        issues += self._missing(profile)
        issues += self._duplicates(profile)
        issues += self._structure(profile)
        issues += self._dtypes(df, profile)
        outlier_issues, outliers = self._outliers(df, profile)
        issues += outlier_issues

        issues.sort(key=lambda i: (_SEVERITY_ORDER[i.severity], i.code, i.column or ""))
        score, grade, breakdown = compute_score(profile, issues, outliers)
        logger.info("Quality score %.1f (%s), %d issues", score, grade, len(issues))
        return QualityReport(
            score=score,
            grade=grade,
            score_breakdown=breakdown,
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
        return found

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