"""Tests for the versioned dataset assessment SOP."""

from adip.sop import build_assessment_sop


def test_sop_documents_all_required_stages_and_contract_fields():
    """Every required stage exposes purpose, I/O, method, automation, and test criteria."""
    sop = build_assessment_sop()

    assert sop.version == "1.0"
    assert [stage.name for stage in sop.stages] == [
        "Dataset upload",
        "File validation",
        "Data profiling",
        "Quality checks",
        "Standardization and cleaning",
        "Quality score calculation",
        "Quality grading",
        "Final report generation",
    ]
    assert [stage.step for stage in sop.stages] == list(range(1, 9))
    for stage in sop.stages:
        assert stage.purpose
        assert stage.input
        assert stage.method
        assert stage.output
        assert stage.testing_criteria


def test_sop_marks_cleaning_as_user_triggered():
    """The SOP must make clear that cleaning requires an explicit user action."""
    sop = build_assessment_sop()
    cleaning = next(stage for stage in sop.stages if stage.name == "Standardization and cleaning")

    assert cleaning.automation == "user_triggered"
    assert "original" in cleaning.testing_criteria[0].lower()
