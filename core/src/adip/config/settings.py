"""Validated configuration models."""

from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from adip.exceptions import ConfigError

DEFAULT_CONFIG_PATH = Path(__file__).parent / "default_config.yaml"


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class LoaderConfig(_Strict):
    chunk_size: int = Field(100_000, gt=0)
    max_file_size_mb: int = Field(1024, gt=0)
    max_rows: int | None = Field(None, gt=0)
    excel_sheet: int | str = 0


class QualityConfig(_Strict):
    outlier_method: Literal["iqr", "zscore", "isolation_forest"] = "iqr"
    iqr_multiplier: float = Field(1.5, gt=0)
    zscore_threshold: float = Field(3.0, gt=0)
    missing_warn_pct: float = Field(5.0, ge=0, le=100)
    missing_critical_pct: float = Field(40.0, ge=0, le=100)
    high_cardinality_ratio: float = Field(0.5, gt=0, le=1)
    high_cardinality_min_unique: int = Field(50, gt=0)


class DimensionWeights(_Strict):
    """Configured relative importance of the six data-quality dimensions."""

    accuracy: float = Field(0.20, ge=0)
    completeness: float = Field(0.20, ge=0)
    consistency: float = Field(0.15, ge=0)
    timeliness: float = Field(0.10, ge=0)
    validity: float = Field(0.20, ge=0)
    uniqueness: float = Field(0.15, ge=0)

    @model_validator(mode="after")
    def _require_positive_total(self) -> "DimensionWeights":
        """Reject a configuration that gives no dimension any influence."""
        if sum(self.model_dump().values()) <= 0:
            raise ValueError("At least one quality dimension weight must be greater than zero.")
        return self


class GradeThresholds(_Strict):
    """Minimum inclusive overall scores for grades A through D."""

    a: float = Field(90.0, ge=0, le=100)
    b: float = Field(80.0, ge=0, le=100)
    c: float = Field(70.0, ge=0, le=100)
    d: float = Field(60.0, ge=0, le=100)

    @model_validator(mode="after")
    def _require_descending_thresholds(self) -> "GradeThresholds":
        """Ensure grades form strict, non-overlapping descending bands."""
        if not self.a > self.b > self.c > self.d:
            raise ValueError("Grade thresholds must satisfy A > B > C > D.")
        return self


class ScoringConfig(_Strict):
    """Configurable weighting and grading policy for overall dataset quality."""

    weights: DimensionWeights = DimensionWeights()
    thresholds: GradeThresholds = GradeThresholds()
    unassessed_dimension_policy: Literal["renormalize"] = "renormalize"

    @model_validator(mode="after")
    def _require_automated_weight(self) -> "ScoringConfig":
        """Require weight on a dimension available for every valid dataset."""
        always_assessed = (
            self.weights.completeness
            + self.weights.consistency
            + self.weights.validity
            + self.weights.uniqueness
        )
        if always_assessed <= 0:
            raise ValueError(
                "At least one of completeness, consistency, validity, or uniqueness "
                "must have a positive weight."
            )
        return self


class EdaConfig(_Strict):
    sample_size: int = Field(50_000, gt=0)
    correlation_threshold: float = Field(0.85, gt=0, le=1)
    max_categories_shown: int = Field(15, gt=0)
    histogram_bins: int = Field(30, gt=0)


class FeaturesConfig(_Strict):
    id_unique_pct: float = Field(99.5, gt=0, le=100)
    onehot_max_unique: int = Field(10, gt=1)
    skew_threshold: float = Field(1.0, gt=0)
    near_constant_pct: float = Field(99.0, gt=0, le=100)
    robust_outlier_pct: float = Field(5.0, ge=0, le=100)
    target_regression_min_unique: int = Field(10, gt=1)
    max_correlation_recommendations: int = Field(20, gt=0)


class FixesConfig(_Strict):
    # A step that removes more than this share of the ORIGINAL rows gets a warning.
    max_row_loss_pct: float = Field(20.0, gt=0, le=100)
    # one_hot skips any column with more distinct values than this.
    one_hot_max_categories: int = Field(50, gt=1)


class InsightsConfig(_Strict):
    enabled: bool = False  # AI is opt-in; the rule-based path never needs it
    providers: list[str] = Field(
        default_factory=lambda: ["gemini", "groq", "openrouter", "mistral", "ollama"]
    )  # fallback order, first provider is tried first


class ADIPConfig(_Strict):
    loader: LoaderConfig = LoaderConfig()
    quality: QualityConfig = QualityConfig()
    scoring: ScoringConfig = ScoringConfig()
    eda: EdaConfig = EdaConfig()
    features: FeaturesConfig = FeaturesConfig()
    fixes: FixesConfig = FixesConfig()
    insights: InsightsConfig = InsightsConfig()


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def load_config(path: str | Path | None = None) -> ADIPConfig:
    """Load defaults, optionally overridden by a user YAML file."""
    defaults = yaml.safe_load(DEFAULT_CONFIG_PATH.read_text(encoding="utf-8")) or {}
    user: dict[str, Any] = {}
    if path is not None:
        try:
            user = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
        except FileNotFoundError as exc:
            raise ConfigError(f"Config file not found: {path}") from exc
        except yaml.YAMLError as exc:
            raise ConfigError(f"Invalid YAML in {path}: {exc}") from exc
    try:
        return ADIPConfig.model_validate(_deep_merge(defaults, user))
    except ValidationError as exc:
        raise ConfigError(f"Invalid configuration: {exc}") from exc
