import logging

import numpy as np
import pandas as pd
from sklearn.feature_selection import mutual_info_classif

from adip.config import EdaConfig, FeaturesConfig, QualityConfig
from adip.eda.statistics import to_float_array
from adip.features import rules
from adip.models.eda import CategoryCount, EdaReport
from adip.models.features import FeatureReport, FeatureSignal, Recommendation, TargetAnalysis
from adip.models.profile import DatasetProfile
from adip.models.quality import QualityReport
from adip.utils.validation import pct

logger = logging.getLogger(__name__)

_SEVERITY_ORDER = {"critical": 0, "warning": 1, "info": 2}
_CATEGORY_ORDER = [
    "target", "data_types", "missing_values", "low_value", "redundancy", "encoding", "scaling",
]
MAX_SIGNALS = 15


class FeatureEngine:
    """Produces preprocessing guidance. Never modifies the data."""

    def __init__(
        self,
        features_config: FeaturesConfig | None = None,
        quality_config: QualityConfig | None = None,
        eda_config: EdaConfig | None = None,
    ) -> None:
        self.fcfg = features_config or FeaturesConfig()
        self.qcfg = quality_config or QualityConfig()
        self.ecfg = eda_config or EdaConfig()

    def run(
        self,
        df: pd.DataFrame,
        profile: DatasetProfile,
        quality: QualityReport,
        eda: EdaReport,
        target: str | None = None,
    ) -> FeatureReport:
        skip = {target} if target else set()
        stats = {s.column: s for s in eda.numeric}
        cats = {c.column: c for c in eda.categorical}
        ids = {
            c.name for c in profile.columns
            if c.name not in skip and rules.is_identifier(c, self.fcfg)
        }
        converted = {
            i.column for i in quality.issues if i.code == "NUMERIC_AS_TEXT" and i.column
        }

        recs: list[Recommendation] = []
        recs += rules.type_rules(quality, skip)
        recs += rules.missing_rules(profile, stats, self.qcfg, self.fcfg, skip)
        recs += rules.low_value_rules(profile, cats, ids, self.fcfg, skip)
        recs += rules.redundancy_rules(df, profile, eda.correlation, self.fcfg, skip)
        recs += rules.encoding_rules(profile, self.qcfg, self.fcfg, skip | ids | converted)
        recs += rules.scaling_rules(profile, stats, quality.outliers, self.fcfg, skip | ids)

        target_analysis = None
        if target:
            target_analysis, target_recs = self._analyze_target(df, profile, stats, target)
            recs += target_recs

        recs.sort(
            key=lambda r: (
                _SEVERITY_ORDER[r.severity],
                _CATEGORY_ORDER.index(r.category),
                r.column or "",
            )
        )
        logger.info("Feature intelligence: %d recommendations", len(recs))
        return FeatureReport(recommendations=recs, target=target_analysis)

    # ------------------------------------------------------------------ target-aware
    def _analyze_target(self, df, profile, stats, target):
        col = next(c for c in profile.columns if c.name == target)
        series = df[target]
        recs: list[Recommendation] = []
        notes: list[str] = []

        is_regression = col.kind == "numeric" and col.unique > self.fcfg.target_regression_min_unique
        task = "regression" if is_regression else "classification"

        if col.missing:
            recs.append(Recommendation(
                category="target", severity="warning", column=target, columns=[target],
                title="Target has missing values",
                recommendation="Drop rows with a missing target before training.",
                rationale=f"{col.missing} rows ({col.missing_pct}%) have no target value.",
            ))

        balance: list[CategoryCount] = []
        ratio = None
        n_classes = None
        if task == "classification":
            counts = series.dropna().astype(str).value_counts()
            n_classes = int(len(counts))
            total = int(counts.sum())
            balance = [
                CategoryCount(value=str(k)[:60], count=int(v), pct=pct(int(v), total))
                for k, v in counts.head(self.ecfg.max_categories_shown).items()
            ]
            if n_classes < 2:
                notes.append("The target has a single class; nothing can be learned from it.")
            else:
                ratio = round(float(counts.max() / counts.min()), 2)
                if ratio >= 3:
                    recs.append(Recommendation(
                        category="target", severity="warning", column=target, columns=[target],
                        title="Imbalanced classes",
                        recommendation="Use stratified splits and class weights or resampling; "
                                       "evaluate with F1/PR-AUC rather than accuracy.",
                        rationale=f"Largest class is {ratio}x the smallest.",
                    ))
        else:
            s = stats.get(target)
            if s and s.skewness is not None and abs(s.skewness) >= self.fcfg.skew_threshold:
                recs.append(Recommendation(
                    category="target", severity="info", column=target, columns=[target],
                    title="Skewed regression target",
                    recommendation="Consider a log or Box-Cox transform of the target.",
                    rationale=f"Target is {s.shape} (skewness {s.skewness}).",
                ))

        signals, metric = self._signals(df, profile, target, task)
        if task == "regression" and signals and abs(signals[0].score) >= 0.95:
            recs.append(Recommendation(
                category="target", severity="warning", column=signals[0].column,
                columns=[signals[0].column, target],
                title="Possible target leakage",
                recommendation=f"Check whether '{signals[0].column}' is available at prediction time.",
                rationale=f"Its correlation with the target is {signals[0].score}.",
            ))

        analysis = TargetAnalysis(
            column=target, task=task, n_classes=n_classes, class_balance=balance,
            imbalance_ratio=ratio, signal_metric=metric, signals=signals, notes=notes,
        )
        return analysis, recs

    def _signals(self, df, profile, target, task) -> tuple[list[FeatureSignal], str]:
        metric = "pearson" if task == "regression" else "mutual_info"
        feats = [
            (i, c.name) for i, c in enumerate(profile.columns)
            if c.kind == "numeric" and c.name != target and c.unique > 1
        ]
        if not feats:
            return [], metric
        try:
            if task == "regression":
                y = to_float_array(df[target])
                out = []
                for i, name in feats:
                    x = to_float_array(df.iloc[:, i])
                    m = np.isfinite(x) & np.isfinite(y)
                    if m.sum() < 10 or np.std(x[m]) == 0 or np.std(y[m]) == 0:
                        continue
                    out.append(FeatureSignal(column=name, score=round(float(np.corrcoef(x[m], y[m])[0, 1]), 4)))
            else:
                y_raw = df[target]
                keep = y_raw.notna().to_numpy()
                codes, _ = pd.factorize(y_raw[keep].astype(str))
                x_mat = np.column_stack([to_float_array(df.iloc[:, i]) for i, _ in feats])[keep]
                if len(x_mat) > self.ecfg.sample_size:
                    rows = np.random.default_rng(42).choice(len(x_mat), self.ecfg.sample_size, replace=False)
                    x_mat, codes = x_mat[rows], codes[rows]
                if len(set(codes.tolist())) < 2:
                    return [], metric
                med = np.nan_to_num(np.nanmedian(x_mat, axis=0))
                x_mat = np.where(np.isnan(x_mat), med, x_mat)
                mi = mutual_info_classif(x_mat, codes, random_state=42)
                out = [FeatureSignal(column=n, score=round(float(s), 4)) for (_, n), s in zip(feats, mi)]
        except Exception:  # target analysis must never break the whole run
            logger.warning("Could not compute target signals", exc_info=True)
            return [], metric
        out.sort(key=lambda s: abs(s.score), reverse=True)
        return out[:MAX_SIGNALS], metric