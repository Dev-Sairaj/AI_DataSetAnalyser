import numpy as np
import pandas as pd
import pytest
from pydantic import ValidationError

from adip.config import FixesConfig, load_config
from adip.exceptions import FixError, TargetColumnError, UnknownFixError
from adip.fixes import (
    FixEngine,
    FixPlan,
    FixStep,
    get_fix,
    list_fixes,
    register_fix,
)

EXPECTED = {
    "drop_columns",
    "drop_duplicates",
    "cast_numeric",
    "impute_median",
    "impute_mean",
    "impute_mode",
    "standardize_text",
    "normalize_dates",
    "standardize_phone",
    "one_hot",
    "scale",
}


def step(fix, *columns, **params):
    return FixStep(fix=fix, columns=list(columns), params=params)


def plan(*steps, target=None):
    return FixPlan(steps=list(steps), target=target)


def run(df, *steps, target=None, config=None):
    return FixEngine(config).apply(df, plan(*steps, target=target), target=target)


# ------------------------------------------------------------------ registry / plan
def test_builtin_fixes_registered_in_execution_order():
    fixes = list_fixes()
    assert EXPECTED <= {f.name for f in fixes}
    orders = [f.order for f in fixes]
    assert orders == sorted(orders)


def test_duplicate_registration_rejected():
    with pytest.raises(ValueError):
        register_fix("drop_columns", order=1, label="x", description="x")(lambda d, c, p: (d, ""))


def test_unknown_fix_rejected(messy_df):
    with pytest.raises(UnknownFixError):
        get_fix("does_not_exist")
    with pytest.raises(UnknownFixError):
        run(messy_df, step("does_not_exist", "age"))


def test_plan_assigns_ids_and_rejects_duplicates():
    p = plan(step("drop_columns", "a"), step("drop_columns", "b"))
    assert [s.id for s in p.steps] == ["step-1", "step-2"]
    with pytest.raises(ValidationError):
        FixPlan(steps=[FixStep(id="x", fix="scale"), FixStep(id="x", fix="scale")])


def test_config_defaults_include_fixes_and_insights():
    cfg = load_config()
    assert cfg.fixes.max_row_loss_pct == 20.0
    assert cfg.insights.enabled is False
    assert cfg.insights.providers[0] == "gemini"
    assert cfg.scoring.weights.accuracy == 0.20
    assert cfg.scoring.weights.timeliness == 0.10
    assert cfg.scoring.thresholds.a == 90.0


# ------------------------------------------------------------------------ the fixes
def test_original_dataframe_is_never_modified(messy_df):
    before = messy_df.copy()
    run(
        messy_df,
        step("drop_columns", "empty"),
        step("impute_median", "age"),
        step("drop_duplicates"),
        step("scale", "income"),
    )
    pd.testing.assert_frame_equal(messy_df, before)


def test_drop_columns_and_duplicates(messy_df):
    out = run(messy_df, step("drop_columns", "constant", "empty"), step("drop_duplicates"))
    assert out.df.shape == (200, 5)
    assert out.report.rows_before == 202 and out.report.rows_after == 200
    assert out.report.cols_before == 7 and out.report.cols_after == 5


def test_cast_numeric(messy_df):
    out = run(messy_df, step("cast_numeric", "num_as_text"))
    assert pd.api.types.is_numeric_dtype(out.df["num_as_text"])
    assert out.df["num_as_text"].iloc[10] == 10


def test_cast_numeric_refuses_real_text(messy_df):
    out = run(messy_df, step("cast_numeric", "city"))
    assert out.report.steps[0].status == "skipped"
    assert out.df["city"].notna().all()  # the column was left alone


def test_impute_median_mean_mode():
    df = pd.DataFrame(
        {
            "n": [1.0, 2.0, np.nan, 100.0],
            "m": [1.0, 3.0, np.nan, 5.0],
            "c": ["a", "a", None, "b"],
        }
    )
    out = run(df, step("impute_median", "n"), step("impute_mean", "m"), step("impute_mode", "c"))
    assert out.df["n"].tolist() == [1.0, 2.0, 2.0, 100.0]
    assert out.df["m"].tolist() == [1.0, 3.0, 3.0, 5.0]
    assert out.df["c"].tolist() == ["a", "a", "a", "b"]
    assert all(r.status == "applied" for r in out.report.steps)


def test_impute_mode_with_label():
    df = pd.DataFrame({"c": ["a", None, "b"], "x": [1, 2, 3]})
    out = run(df, step("impute_mode", "c", label="Missing"))
    assert out.df["c"].tolist() == ["a", "Missing", "b"]


def test_impute_numeric_skips_text_columns(messy_df):
    out = run(messy_df, step("impute_median", "city"))
    assert out.report.steps[0].status == "skipped"


def test_one_hot(messy_df):
    out = run(messy_df, step("one_hot", "city"))
    assert "city" not in out.df.columns
    assert {"city_Pune", "city_Mumbai", "city_Delhi"} <= set(out.df.columns)
    assert out.df[["city_Pune", "city_Mumbai", "city_Delhi"]].sum(axis=1).eq(1).all()


def test_one_hot_drop_first_gives_binary_flag():
    df = pd.DataFrame({"flag": ["yes", "no", "yes", "no"], "x": [1, 2, 3, 4]})
    out = run(df, step("one_hot", "flag", drop_first=True))
    assert [c for c in out.df.columns if c.startswith("flag")] == ["flag_yes"]


def test_one_hot_skips_high_cardinality_from_config():
    df = pd.DataFrame({"c": [f"v{i}" for i in range(30)], "x": range(30)})
    out = run(df, step("one_hot", "c"), config=FixesConfig(one_hot_max_categories=10))
    assert out.report.steps[0].status == "skipped"
    assert "c" in out.df.columns
    assert out.report.steps[0].params["max_categories"] == 10  # resolved params recorded


def test_scale_methods():
    rng = np.random.default_rng(0)
    df = pd.DataFrame({"a": rng.normal(10, 3, 200), "b": rng.lognormal(2, 1, 200)})
    std = run(df, step("scale", "a")).df["a"]
    assert abs(std.mean()) < 1e-9 and abs(std.std(ddof=0) - 1) < 1e-9
    rob = run(df, step("scale", "a", method="robust")).df["a"]
    assert abs(rob.median()) < 1e-9
    log = run(df, step("scale", "b", method="log")).df["b"]
    assert abs(log.mean()) < 1e-9
    minmax = run(df, step("scale", "a", method="minmax")).df["a"]
    assert minmax.min() == pytest.approx(0.0) and minmax.max() == pytest.approx(1.0)
    zscore = run(df, step("scale", "a", method="zscore")).df["a"]
    assert abs(zscore.mean()) < 1e-9 and abs(zscore.std(ddof=0) - 1) < 1e-9


def test_text_date_and_phone_standardization_preserves_invalid_values():
    """Standardization normalizes valid values without discarding invalid originals."""
    df = pd.DataFrame(
        {
            "city": [" New   Delhi ", "MUMBAI"],
            "event_date": ["31/12/2025", "not-a-date"],
            "phone": ["98765 43210", "invalid"],
        }
    )
    original = df.copy()
    out = run(
        df,
        step("standardize_text", "city", case="lower"),
        step("normalize_dates", "event_date", format="%Y-%m-%d", dayfirst=True),
        step("standardize_phone", "phone", country_code="91"),
    )

    assert out.df["city"].tolist() == ["new delhi", "mumbai"]
    assert out.df["event_date"].tolist() == ["2025-12-31", "not-a-date"]
    assert out.df["phone"].tolist() == ["+919876543210", "invalid"]
    date_result = next(result for result in out.report.steps if result.fix == "normalize_dates")
    phone_result = next(result for result in out.report.steps if result.fix == "standardize_phone")
    assert "1 invalid" in date_result.message
    assert "1 invalid" in phone_result.message
    pd.testing.assert_frame_equal(df, original)


def test_before_after_comparison_counts_quality_and_record_changes():
    """Comparison metrics separate changed retained records from removed records."""
    df = pd.DataFrame(
        {
            "amount": [1.0, 1.0, np.nan],
            "numeric_text": ["1", "1", "2"],
        }
    )
    out = run(
        df,
        step("drop_duplicates"),
        step("cast_numeric", "numeric_text"),
        step("impute_median", "amount"),
    )

    assert out.report.before.missing_values == 1
    assert out.report.after.missing_values == 0
    assert out.report.before.duplicate_records == 1
    assert out.report.after.duplicate_records == 0
    assert out.report.before.invalid_values > out.report.after.invalid_values
    assert out.report.records_removed == 1
    assert out.report.records_modified == 2
    assert out.report.missing_values_delta == -1
    assert out.report.duplicate_records_delta == -1
    assert out.report.comparison_notes


def test_scale_log_skips_negative_columns():
    df = pd.DataFrame({"neg": [-1.0, 2.0, 3.0], "pos": [1.0, 2.0, 3.0]})
    out = run(df, step("scale", "neg", "pos", method="log"))
    assert out.df["neg"].tolist() == [-1.0, 2.0, 3.0]
    assert out.df["pos"].mean() == pytest.approx(0.0)


# ------------------------------------------------------------------ engine behaviour
def test_steps_run_in_stage_order_not_plan_order(messy_df):
    out = run(
        messy_df,
        step("scale", "income"),
        step("one_hot", "city"),
        step("impute_median", "age"),
        step("cast_numeric", "num_as_text"),
        step("drop_duplicates"),
        step("drop_columns", "constant"),
    )
    assert [r.fix for r in out.report.steps] == [
        "drop_columns",
        "drop_duplicates",
        "cast_numeric",
        "impute_median",
        "one_hot",
        "scale",
    ]


def test_disabled_steps_are_not_run(messy_df):
    p = plan(FixStep(fix="drop_columns", columns=["constant"], enabled=False))
    out = FixEngine().apply(messy_df, p)
    assert out.report.steps == []
    assert "constant" in out.df.columns


def test_target_column_is_protected():
    df = pd.DataFrame({"x": [1.0, np.nan, 3.0, 4.0], "y": [1.0, np.nan, 0.0, 1.0]})
    out = run(df, step("impute_median", "x", "y"), target="y")
    assert out.df["x"].notna().all()
    assert out.df["y"].isna().sum() == 1
    assert out.report.steps[0].ignored_columns == ["y"]


def test_target_only_step_is_skipped_and_allow_target_overrides():
    df = pd.DataFrame({"x": [1.0, 2.0, 3.0], "y": [1.0, np.nan, 0.0]})
    out = run(df, step("impute_median", "y"), target="y")
    assert out.report.steps[0].status == "skipped"
    allowed = FixPlan(steps=[FixStep(fix="impute_median", columns=["y"], allow_target=True)])
    out = FixEngine().apply(df, allowed, target="y")
    assert out.df["y"].notna().all()


def test_unknown_target_raises(messy_df):
    with pytest.raises(TargetColumnError):
        run(messy_df, step("drop_duplicates"), target="nope")


def test_missing_columns_are_ignored_not_fatal(messy_df):
    out = run(messy_df, step("drop_columns", "constant", "ghost"))
    assert "constant" not in out.df.columns
    res = out.report.steps[0]
    assert res.status == "applied" and res.ignored_columns == ["ghost"]
    out = run(messy_df, step("drop_columns", "ghost"))
    assert out.report.steps[0].status == "skipped"


def test_failed_step_is_reported_and_later_steps_still_run(messy_df):
    out = run(messy_df, step("scale", "income", method="bogus"), step("drop_columns", "constant"))
    statuses = {r.fix: r.status for r in out.report.steps}
    assert statuses == {"drop_columns": "applied", "scale": "failed"}
    assert "constant" not in out.df.columns


def test_row_loss_guard_warns():
    df = pd.DataFrame({"a": list(range(10)) * 10, "b": list(range(10)) * 10})
    out = run(df, step("drop_duplicates"), config=FixesConfig(max_row_loss_pct=20))
    assert len(out.df) == 10
    assert out.report.steps[0].warning and "90" in out.report.steps[0].warning
    assert out.report.warnings


def test_no_warning_for_small_row_loss(messy_df):
    out = run(messy_df, step("drop_duplicates"))
    assert out.report.steps[0].warning is None
    assert out.report.warnings == []


def test_removing_everything_is_an_error(messy_df):
    with pytest.raises(FixError):
        run(messy_df, step("drop_columns", *messy_df.columns))


def test_plan_improves_quality_score(messy_df):
    out = run(
        messy_df,
        step("drop_columns", "constant", "empty"),
        step("drop_duplicates"),
        step("cast_numeric", "num_as_text"),
        step("impute_median", "age"),
    )
    assert out.report.after.score > out.report.before.score
    assert out.report.score_delta > 0
    assert out.report.after.issues < out.report.before.issues
