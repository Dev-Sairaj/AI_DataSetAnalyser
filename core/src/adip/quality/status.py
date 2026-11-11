"""Transparent rules for classifying a dataset's cleaning status."""

from adip.models.quality import DatasetStatus, QualityIssue, StatusRuleResult


def assess_dataset_status(
    issues: list[QualityIssue],
) -> tuple[DatasetStatus, str, list[StatusRuleResult]]:
    """Classify dataset cleanliness from all detected quality findings.

    Args:
        issues: Quality findings produced by the quality engine.

    Returns:
        Dataset status, user-facing summary, and evaluations of every status rule.

    Raises:
        No exceptions are raised by this deterministic assessment.
    """
    critical_count = sum(issue.severity == "critical" for issue in issues)
    non_critical_count = len(issues) - critical_count

    if critical_count:
        status: DatasetStatus = "Critical Issues"
        summary = f"{critical_count} critical quality issue(s) require attention before use."
    elif issues:
        status = "Needs Cleaning"
        summary = f"{len(issues)} quality issue(s) were detected and should be reviewed."
    else:
        status = "Clean"
        summary = "No quality issues were detected by the implemented automated checks."

    rules = [
        StatusRuleResult(
            name="Critical Issues",
            condition="At least one detected issue has critical severity.",
            triggered=critical_count > 0,
            evidence=f"Detected {critical_count} critical issue(s).",
        ),
        StatusRuleResult(
            name="Needs Cleaning",
            condition="At least one issue is detected and none are critical.",
            triggered=bool(issues) and critical_count == 0,
            evidence=f"Detected {non_critical_count} non-critical issue(s).",
        ),
        StatusRuleResult(
            name="Clean",
            condition="No issues are detected across any implemented quality check.",
            triggered=not issues,
            evidence=f"Detected {len(issues)} total issue(s).",
        ),
    ]
    return status, summary, rules
