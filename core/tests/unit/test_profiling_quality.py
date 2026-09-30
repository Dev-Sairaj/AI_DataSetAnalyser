from adip.models.quality import IssueCode
from adip.profiling import ProfilingEngine
from adip.quality import QualityEngine


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


def test_clean_data_scores_high():
    import numpy as np
    import pandas as pd

    rng = np.random.default_rng(1)
    df = pd.DataFrame({"a": rng.normal(size=300), "b": rng.choice(["x", "y", "z"], 300)})
    report = QualityEngine().run(df, ProfilingEngine().run(df))
    assert report.score >= 85