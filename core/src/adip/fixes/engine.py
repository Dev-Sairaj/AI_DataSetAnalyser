"""Runs an approved FixPlan on an in-memory copy of the data.

The original DataFrame is never modified. The caller decides what to do with the
cleaned frame (write a new file); this module only transforms and reports.
"""

import logging
from dataclasses import dataclass
from typing import Any

import pandas as pd

from adip.config import FixesConfig, QualityConfig, ScoringConfig
from adip.exceptions import FixError, TargetColumnError
from adip.fixes.plan import FixPlan, FixReport, FixStep, FixStepResult, QualityScore
from adip.fixes.registry import FixSkipped, FixSpec, get_fix, validate_plan
from adip.models.profile import DatasetProfile
from adip.models.quality import IssueCode, QualityReport
from adip.profiling import ProfilingEngine
from adip.quality import QualityEngine

logger = logging.getLogger(__name__)

_INVALID_VALUE_CODES = frozenset(
    {
        IssueCode.NUMERIC_AS_TEXT,
        IssueCode.INVALID_DTYPE,
        IssueCode.MIXED_TYPES,
        IssueCode.INFINITE_VALUES,
        IssueCode.INCONSISTENT_FORMAT,
    }
)

_COMPARISON_NOTES = [
    "Missing values are null cells across the complete dataset.",
    "Duplicate records are exact full-row duplicates after the first occurrence.",
    (
        "Invalid values are detected rule violations for numeric-as-text, invalid or mixed types, "
        "infinite values, and inconsistent text formats; one cell can contribute to multiple "
        "findings."
    ),
    (
        "Modified records are retained rows whose values changed; any schema or data-type change "
        "marks all retained records as modified."
    ),
    "Removed records equal original rows minus cleaned rows and never include modified rows.",
]


@dataclass
class FixOutcome:
    df: pd.DataFrame
    report: FixReport


def _score(report: QualityReport, profile: DatasetProfile) -> QualityScore:
    """Convert a full quality report to a before/after score snapshot.

    Args:
        report: Full quality report produced for a dataset version.
        profile: Profile for the same dataset version.

    Returns:
        Compact quality score with dimension-level explanations.

    Raises:
        No exceptions are raised for a validated quality report.
    """
    return QualityScore(
        score=report.score,
        grade=report.grade,
        status=report.status,
        issues=len(report.issues),
        issue_details=report.issues,
        breakdown=report.score_breakdown,
        dimensions=report.dimension_scores,
        score_explanation=report.score_explanation,
        grade_explanation=report.grade_explanation,
        missing_values=profile.total_missing,
        duplicate_records=profile.duplicate_rows,
        invalid_values=sum(
            issue.affected_count for issue in report.issues if issue.code in _INVALID_VALUE_CODES
        ),
    )


def _count_modified_records(original: pd.DataFrame, cleaned: pd.DataFrame) -> int:
    """Count retained records whose values or schema changed.

    Exact row-hash multiplicities are compared so row reordering and duplicate removal do
    not incorrectly count unchanged records as modified. A schema or dtype change affects
    every retained record because its representation changed.

    Args:
        original: Dataset before approved transformations.
        cleaned: Dataset after approved transformations.

    Returns:
        Number of retained records that were modified.

    Raises:
        No exceptions are raised for valid pandas dataframes.
    """
    retained = min(len(original), len(cleaned))
    if retained == 0:
        return 0
    if list(original.columns) != list(cleaned.columns):
        return retained
    if [str(dtype) for dtype in original.dtypes] != [str(dtype) for dtype in cleaned.dtypes]:
        return retained

    original_counts = pd.util.hash_pandas_object(
        original, index=False, categorize=True
    ).value_counts()
    cleaned_counts = pd.util.hash_pandas_object(
        cleaned, index=False, categorize=True
    ).value_counts()
    matched = original_counts.to_frame("original").join(
        cleaned_counts.to_frame("cleaned"), how="inner"
    )
    unchanged = int(matched.min(axis=1).sum()) if not matched.empty else 0
    return max(0, retained - unchanged)


class FixEngine:
    def __init__(
        self,
        config: FixesConfig | None = None,
        quality_config: QualityConfig | None = None,
        scoring_config: ScoringConfig | None = None,
    ) -> None:
        """Initialize standardization controls and the shared quality policy.

        Args:
            config: Standardization safety configuration.
            quality_config: Quality detection settings.
            scoring_config: Dimension weights and grade thresholds.

        Raises:
            No exceptions are raised for validated configuration models.
        """
        self.config = config or FixesConfig()
        self.quality_config = quality_config or QualityConfig()
        self.scoring_config = scoring_config or ScoringConfig()

    # ------------------------------------------------------------------ public
    def apply(
        self,
        df: pd.DataFrame,
        plan: FixPlan,
        target: str | None = None,
        before: QualityReport | None = None,
    ) -> FixOutcome:
        """Run every enabled step in execution order and re-score the result.

        ``before`` is the quality report of ``df`` if the caller already has it;
        otherwise it is recomputed.
        """
        target = target if target is not None else plan.target
        if target is not None and target not in df.columns:
            raise TargetColumnError(f"Target column '{target}' not found in the dataset.")
        validate_plan(plan)

        steps = [s for s in plan.steps if s.enabled]
        ordered = sorted(enumerate(steps), key=lambda p: (get_fix(p[1].fix).order, p[0]))

        work = df.copy()
        original_rows = len(work)
        results: list[FixStepResult] = []
        warnings: list[str] = []
        for _, step in ordered:
            result = self._run_step(work, step, target, original_rows)
            work = result[0]
            results.append(result[1])
            if result[1].warning:
                warnings.append(f"{result[1].step_id}: {result[1].warning}")

        if work.shape[0] == 0 or work.shape[1] == 0:
            raise FixError("The plan would remove every row or column. Nothing was changed.")

        lost_pct = (original_rows - len(work)) / original_rows * 100 if original_rows else 0.0
        if lost_pct > self.config.max_row_loss_pct and not any("rows" in w for w in warnings):
            warnings.append(f"Overall, {lost_pct:.1f}% of rows were removed.")

        before_profile = ProfilingEngine().run(df)
        if before is None:
            before = QualityEngine(self.quality_config, self.scoring_config).run(df, before_profile)
        after_profile = ProfilingEngine().run(work)
        after = QualityEngine(self.quality_config, self.scoring_config).run(work, after_profile)

        report = FixReport(
            plan=plan,
            target=target,
            steps=results,
            rows_before=original_rows,
            rows_after=len(work),
            cols_before=df.shape[1],
            cols_after=work.shape[1],
            before=_score(before, before_profile),
            after=_score(after, after_profile),
            records_modified=_count_modified_records(df, work),
            records_removed=max(0, len(df) - len(work)),
            comparison_notes=_COMPARISON_NOTES,
            warnings=warnings,
        )
        logger.info(
            "Applied %d step(s): score %.1f -> %.1f",
            sum(r.status == "applied" for r in results),
            report.before.score,
            report.after.score,
        )
        return FixOutcome(df=work, report=report)

    # ----------------------------------------------------------------- internals
    def _config_defaults(self, fix: str) -> dict[str, Any]:
        if fix == "one_hot":
            return {"max_categories": self.config.one_hot_max_categories}
        return {}

    @staticmethod
    def _resolve_columns(
        work: pd.DataFrame, step: FixStep, target: str | None
    ) -> tuple[list[str], list[str], list[str]]:
        """Returns (usable columns, ignored columns, reasons)."""
        usable: list[str] = []
        ignored: list[str] = []
        reasons: list[str] = []
        for c in dict.fromkeys(step.columns):
            if c not in work.columns:
                ignored.append(c)
                reasons.append(f"'{c}' not found")
            elif target is not None and c == target and not step.allow_target:
                ignored.append(c)
                reasons.append(f"'{c}' is the target column and is protected")
            else:
                usable.append(c)
        return usable, ignored, reasons

    def _run_step(
        self, work: pd.DataFrame, step: FixStep, target: str | None, original_rows: int
    ) -> tuple[pd.DataFrame, FixStepResult]:
        spec: FixSpec = get_fix(step.fix)
        cols, ignored, reasons = self._resolve_columns(work, step, target)
        params = {**self._config_defaults(step.fix), **step.params}
        rows0, cols0 = work.shape
        warning: str | None = None

        if (spec.needs_columns or step.columns) and not cols:
            status, message = (
                "skipped",
                "No usable columns: " + ("; ".join(reasons) if reasons else "none were selected."),
            )
        else:
            try:
                work, message = spec.fn(work, cols, params)
                status = "applied"
            except FixSkipped as exc:
                status, message = "skipped", str(exc)
            except Exception as exc:  # one bad step must not abort the whole plan
                logger.warning("Fix step %s (%s) failed", step.id, step.fix, exc_info=True)
                status, message = "failed", f"{type(exc).__name__}: {exc}"
            if status == "applied" and reasons:
                message += " Ignored: " + "; ".join(reasons) + "."

        lost = rows0 - len(work)
        if lost > 0 and original_rows and lost / original_rows * 100 > self.config.max_row_loss_pct:
            warning = (
                f"removed {lost} rows ({lost / original_rows * 100:.1f}% of the original rows), "
                f"above the {self.config.max_row_loss_pct:g}% limit."
            )

        return work, FixStepResult(
            step_id=step.id,
            fix=step.fix,
            label=spec.label,
            status=status,  # type: ignore[arg-type]
            message=message,
            columns=cols,
            ignored_columns=ignored,
            params=params,
            rows_before=rows0,
            rows_after=len(work),
            cols_before=cols0,
            cols_after=work.shape[1],
            warning=warning,
        )
