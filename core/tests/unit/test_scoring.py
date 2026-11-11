import pandas as pd
import pytest
from pydantic import ValidationError

from adip.config import DimensionWeights, GradeThresholds, ScoringConfig
from adip.profiling import ProfilingEngine
from adip.quality import QualityEngine
from adip.quality.scoring import grade_for


def test_default_scoring_exposes_all_six_dimensions() -> None:
    """Default reports expose six dimensions and honest unassessed states."""
    df = pd.DataFrame(
        {
            "value": [10, 11, 12, 13, 14, 15],
            "region": ["north", "south", "east", "west", "north", "south"],
        }
    )

    report = QualityEngine().run(df, ProfilingEngine().run(df))

    assert [dimension.name for dimension in report.dimension_scores] == [
        "Accuracy",
        "Completeness",
        "Consistency",
        "Timeliness",
        "Validity",
        "Uniqueness",
    ]
    timeliness = next(
        dimension for dimension in report.dimension_scores if dimension.name == "Timeliness"
    )
    assert timeliness.score is None
    assert timeliness.assessment == "not_assessed"
    assert timeliness.effective_weight == 0
    assert sum(
        dimension.effective_weight for dimension in report.dimension_scores
    ) == pytest.approx(1.0, abs=1e-5)


def test_overall_score_matches_effective_weight_calculation() -> None:
    """Overall score equals the displayed assessed-dimension weighted sum."""
    df = pd.DataFrame(
        {
            "value": [1.0, 2.0, None, 4.0, 1000.0],
            "category": ["A", "A ", "B", "B", "B"],
        }
    )

    report = QualityEngine().run(df, ProfilingEngine().run(df))
    expected = sum(
        (dimension.score or 0) * dimension.effective_weight for dimension in report.dimension_scores
    )

    assert report.score == pytest.approx(expected, abs=0.01)
    assert "renormalized" in report.score_explanation
    assert report.grade in report.grade_explanation


def test_custom_weights_control_overall_score() -> None:
    """A completeness-only policy produces the completeness dimension score."""
    df = pd.DataFrame({"required": [1, None, 3, None], "label": ["a", "b", "c", "d"]})
    scoring = ScoringConfig(
        weights=DimensionWeights(
            accuracy=0,
            completeness=1,
            consistency=0,
            timeliness=0,
            validity=0,
            uniqueness=0,
        )
    )

    report = QualityEngine(scoring_config=scoring).run(df, ProfilingEngine().run(df))
    completeness = next(
        dimension for dimension in report.dimension_scores if dimension.name == "Completeness"
    )

    assert report.score == completeness.score
    assert completeness.effective_weight == 1


@pytest.mark.parametrize(
    ("score", "expected"),
    [(95, "A"), (85, "B"), (75, "C"), (65, "D"), (64.99, "F")],
)
def test_custom_grade_threshold_boundaries(score: float, expected: str) -> None:
    """Custom grade thresholds use inclusive lower boundaries."""
    thresholds = GradeThresholds(a=95, b=85, c=75, d=65)
    assert grade_for(score, thresholds) == expected


def test_invalid_scoring_configuration_is_rejected() -> None:
    """Invalid grade order and unscorable weights fail during validation."""
    with pytest.raises(ValidationError):
        GradeThresholds(a=80, b=90, c=70, d=60)

    with pytest.raises(ValidationError):
        ScoringConfig(
            weights=DimensionWeights(
                accuracy=1,
                completeness=0,
                consistency=0,
                timeliness=0,
                validity=0,
                uniqueness=0,
            )
        )
