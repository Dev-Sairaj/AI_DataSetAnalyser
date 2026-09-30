import numpy as np
import pandas as pd

from adip.eda import EdaEngine
from adip.features import FeatureEngine
from adip.profiling import ProfilingEngine
from adip.quality import QualityEngine


def _run(df, target=None):
    profile = ProfilingEngine().run(df)
    quality = QualityEngine().run(df, profile)
    eda = EdaEngine().run(df, profile)
    features = FeatureEngine().run(df, profile, quality, eda, target)
    return profile, quality, eda, features


def test_eda_outputs(messy_df):
    _, _, eda, _ = _run(messy_df)
    stats = {s.column: s for s in eda.numeric}
    assert {"age", "income"} <= set(stats)
    assert "highly right-skewed" in stats["income"].shape
    assert any(b.column == "income" and b.n_outliers >= 1 for b in eda.boxplots)
    assert any(h.column == "age" for h in eda.histograms)
    assert {c.column for c in eda.categorical} >= {"city"}
    assert eda.correlation is not None and "age" in eda.correlation.columns
    assert "constant" not in eda.correlation.columns


def test_recommendations_for_injected_issues(messy_df):
    _, _, _, features = _run(messy_df)
    found = {(r.category, r.column) for r in features.recommendations}
    assert ("low_value", "constant") in found
    assert ("low_value", "empty") in found
    assert ("missing_values", "age") in found
    assert ("encoding", "city") in found
    assert ("data_types", "num_as_text") in found
    assert any(r.category == "scaling" for r in features.recommendations)


def test_identifier_and_duplicate_columns():
    rng = np.random.default_rng(3)
    x = rng.normal(size=300)
    df = pd.DataFrame({"id": range(300), "x": x, "x_copy": x, "z": rng.normal(size=300)})
    _, _, _, features = _run(df)
    found = {(r.category, r.column) for r in features.recommendations}
    assert ("low_value", "id") in found
    assert any(r.category == "redundancy" and set(r.columns) == {"x", "x_copy"}
               for r in features.recommendations)


def test_target_classification():
    rng = np.random.default_rng(5)
    x1, x2 = rng.normal(size=600), rng.normal(size=600)
    y = (x1 + rng.normal(scale=0.3, size=600) > 0).astype(int)
    _, _, _, features = _run(pd.DataFrame({"x1": x1, "x2": x2, "y": y}), target="y")
    t = features.target
    assert t is not None and t.task == "classification"
    assert len(t.class_balance) == 2
    assert t.signals[0].column == "x1"


def test_target_regression():
    rng = np.random.default_rng(6)
    x1, x2 = rng.normal(size=400), rng.normal(size=400)
    y = 3 * x1 + rng.normal(scale=0.5, size=400)
    _, _, _, features = _run(pd.DataFrame({"x1": x1, "x2": x2, "y": y}), target="y")
    t = features.target
    assert t is not None and t.task == "regression"
    assert t.signals[0].column == "x1" and t.signals[0].score > 0.9