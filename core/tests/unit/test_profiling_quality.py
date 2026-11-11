from adip.models.quality import IssueCode
from adip.profiling import ProfilingEngine
from adip.quality import QualityEngine
from adip.quality.government_mapping import build_government_framework_mapping


def test_profile_basics(messy_df):
    profile = ProfilingEngine().run(messy_df)
    assert profile.n_rows == 202
    assert profile.n_cols == 7
    assert profile.duplicate_rows == 2
    kinds = {c.name: c.kind for c in profile.columns}
    assert kinds["age"] == "numeric"
    assert kinds["empty"] == "empty"
    assert kinds["city"] == "categorical"


def test_quality_detects_injected_issues(messy_df):
    profile = ProfilingEngine().run(messy_df)
    report = QualityEngine().run(messy_df, profile)
    found = {(i.code, i.column) for i in report.issues}

    assert (IssueCode.MISSING_VALUES, "age") in found
    assert (IssueCode.EMPTY_COLUMN, "empty") in found
    assert (IssueCode.CONSTANT_COLUMN, "constant") in found
    assert (IssueCode.NUMERIC_AS_TEXT, "num_as_text") in found
    assert (IssueCode.OUTLIERS, "income") in found
    assert (IssueCode.DUPLICATE_ROWS, None) in found
    assert 0 <= report.score <= 100
    assert report.grade in {"A", "B", "C", "D", "F"}
    assert report.status in {"Needs Cleaning", "Critical Issues"}
    assert len(report.status_rules) == 3


def test_clean_data_scores_high():
    import numpy as np
    import pandas as pd

    rng = np.random.default_rng(1)
    df = pd.DataFrame({"a": rng.normal(size=300), "b": rng.choice(["x", "y", "z"], 300)})
    report = QualityEngine().run(df, ProfilingEngine().run(df))
    assert report.score >= 85


def test_clean_status_requires_no_detected_quality_issues():
    """A dataset is clean only when every implemented check passes."""
    import pandas as pd

    df = pd.DataFrame(
        {
            "row_id": range(100),
            "category": ["north", "south", "east", "west"] * 25,
        }
    )
    report = QualityEngine().run(df, ProfilingEngine().run(df))

    assert report.status == "Clean"
    assert report.issues == []
    assert next(rule for rule in report.status_rules if rule.name == "Clean").triggered


def test_no_missing_values_does_not_hide_inconsistent_formats():
    """Formatting issues prevent a dataset with complete values from being marked clean."""
    import pandas as pd

    df = pd.DataFrame(
        {
            "row_id": range(6),
            "city": ["Delhi", " delhi ", "Mumbai", "MUMBAI", "Pune", "Pune  "],
        }
    )
    report = QualityEngine().run(df, ProfilingEngine().run(df))

    assert report.status == "Needs Cleaning"
    assert any(issue.code == IssueCode.INCONSISTENT_FORMAT for issue in report.issues)


def test_critical_issue_sets_critical_dataset_status():
    """A critical finding takes precedence over all non-critical status rules."""
    import numpy as np
    import pandas as pd

    df = pd.DataFrame(
        {
            "row_id": range(10),
            "value": [1.0, 2.0, 3.0, 4.0, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan],
        }
    )
    report = QualityEngine().run(df, ProfilingEngine().run(df))

    assert report.status == "Critical Issues"
    assert next(rule for rule in report.status_rules if rule.name == "Critical Issues").triggered


def test_government_framework_mapping_separates_automated_and_external_checks(messy_df):
    """Government mapping exposes six dimensions without claiming DGQI certification."""
    quality = QualityEngine().run(messy_df, ProfilingEngine().run(messy_df))
    mapping = build_government_framework_mapping(quality)

    assert [dimension.name for dimension in mapping.dimensions] == [
        "Accuracy",
        "Completeness",
        "Consistency",
        "Timeliness",
        "Validity",
        "Uniqueness",
    ]
    timeliness = next(
        dimension for dimension in mapping.dimensions if dimension.name == "Timeliness"
    )
    assert timeliness.coverage == "external_or_manual"
    assert timeliness.implemented_checks == []
    assert timeliness.external_or_manual_checks
    assert "not an official DGQI assessment" in mapping.disclaimer
