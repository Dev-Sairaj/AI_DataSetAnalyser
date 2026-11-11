"""Build the ADIP-to-DGQI operational mapping for a completed quality assessment."""

from dataclasses import dataclass

from adip.models.governance import (
    CoverageStatus,
    GovernmentFrameworkMapping,
    GovernmentFrameworkReference,
    GovernmentQualityDimension,
    QualityDimensionName,
)
from adip.models.quality import IssueCode, QualityReport

DGQI_TOOLKIT_URL = (
    "https://dmeo.gov.in/sites/default/files/2022-04/DGQI_2.0_Toolkit_28042022.pdf"
)
DGQI_REPOSITORY_URL = "https://www.dmeo.gov.in/en/content/dgqi-repository"


@dataclass(frozen=True)
class _DimensionDefinition:
    """Static implementation definition for one quality dimension."""

    name: QualityDimensionName
    coverage: CoverageStatus
    explanation: str
    implemented_checks: tuple[str, ...]
    external_or_manual_checks: tuple[str, ...]
    issue_codes: frozenset[IssueCode]


_DIMENSIONS = (
    _DimensionDefinition(
        name="Accuracy",
        coverage="partially_implemented",
        explanation=(
            "ADIP identifies statistical and representation anomalies, but factual correctness "
            "cannot be established from an isolated file."
        ),
        implemented_checks=(
            "Statistical outlier detection for numeric columns",
            "Infinite and non-numeric value detection",
            "Summary statistics for abnormality review",
        ),
        external_or_manual_checks=(
            "Verification against an authoritative source or ground truth",
            "Beneficiary backchecks, field inspections, social audits, or third-party audits",
            "Semantic correctness of real-world values",
        ),
        issue_codes=frozenset(
            {IssueCode.OUTLIERS, IssueCode.INFINITE_VALUES, IssueCode.INVALID_DTYPE}
        ),
    ),
    _DimensionDefinition(
        name="Completeness",
        coverage="partially_implemented",
        explanation=(
            "ADIP measures missing cells and empty columns; expected population and mandatory "
            "record coverage require supplied rules or reference registers."
        ),
        implemented_checks=(
            "Missing-value counts and percentages by column",
            "Completely empty column detection",
            "Dataset-wide non-null coverage",
        ),
        external_or_manual_checks=(
            "Coverage against the expected population or master register",
            "Mandatory-field rules defined by the data owner",
            "Confirmation that all expected reporting units submitted data",
        ),
        issue_codes=frozenset({IssueCode.MISSING_VALUES, IssueCode.EMPTY_COLUMN}),
    ),
    _DimensionDefinition(
        name="Consistency",
        coverage="partially_implemented",
        explanation=(
            "ADIP checks internal type and formatting consistency; cross-system integrity and "
            "domain logic need metadata, code lists, or other datasets."
        ),
        implemented_checks=(
            "Mixed Python type detection within columns",
            "Inconsistent whitespace and letter-case detection",
            "Numeric values stored inconsistently as text",
        ),
        external_or_manual_checks=(
            "Cross-field logical and business-rule validation",
            "Consistency across MIS portals, publications, and source systems",
            "Units, classifications, and controlled code-list conformance",
        ),
        issue_codes=frozenset(
            {IssueCode.MIXED_TYPES, IssueCode.INCONSISTENT_FORMAT, IssueCode.NUMERIC_AS_TEXT}
        ),
    ),
    _DimensionDefinition(
        name="Timeliness",
        coverage="external_or_manual",
        explanation=(
            "A file alone does not define its required refresh frequency, reporting period, or "
            "submission deadline, so ADIP does not assign an automated timeliness result."
        ),
        implemented_checks=(),
        external_or_manual_checks=(
            "Compare data timestamps with a declared reporting period",
            "Check submission and update dates against service-level targets",
            "Verify that the most recent value is reproduced across systems",
        ),
        issue_codes=frozenset(),
    ),
    _DimensionDefinition(
        name="Validity",
        coverage="partially_implemented",
        explanation=(
            "ADIP validates structural and type-level rules; domain ranges and reference values "
            "must be supplied by the responsible department."
        ),
        implemented_checks=(
            "Incorrect and mixed data-type detection",
            "Numeric-as-text and infinite-value detection",
            "Optional deterministic date and phone validation during standardization",
        ),
        external_or_manual_checks=(
            "Department-specific allowable ranges and logical constraints",
            "Reference code, geography, scheme, and identifier validation",
            "Schema and metadata accuracy confirmation by the data owner",
        ),
        issue_codes=frozenset(
            {
                IssueCode.NUMERIC_AS_TEXT,
                IssueCode.INVALID_DTYPE,
                IssueCode.MIXED_TYPES,
                IssueCode.INFINITE_VALUES,
            }
        ),
    ),
    _DimensionDefinition(
        name="Uniqueness",
        coverage="partially_implemented",
        explanation=(
            "ADIP detects exact duplicate rows and profiles distinct values; entity-level "
            "deduplication requires identifiers and matching rules."
        ),
        implemented_checks=(
            "Exact duplicate-row detection",
            "Distinct-value and uniqueness-percentage profiling",
            "High-cardinality and identifier-like column signals",
        ),
        external_or_manual_checks=(
            "Primary-key and composite-key definitions",
            "Fuzzy entity matching across spelling or address variations",
            "Duplicate detection across external datasets or reporting periods",
        ),
        issue_codes=frozenset({IssueCode.DUPLICATE_ROWS, IssueCode.HIGH_CARDINALITY}),
    ),
)


def build_government_framework_mapping(quality: QualityReport) -> GovernmentFrameworkMapping:
    """Map detected ADIP findings to six operational quality dimensions.

    Args:
        quality: Completed deterministic dataset quality assessment.

    Returns:
        Source-backed mapping that separates automated coverage from external/manual checks.

    Raises:
        No exceptions are raised for a valid quality report.
    """
    dimensions: list[GovernmentQualityDimension] = []
    for definition in _DIMENSIONS:
        matching = [issue for issue in quality.issues if issue.code in definition.issue_codes]
        dimensions.append(
            GovernmentQualityDimension(
                name=definition.name,
                coverage=definition.coverage,
                explanation=definition.explanation,
                implemented_checks=list(definition.implemented_checks),
                external_or_manual_checks=list(definition.external_or_manual_checks),
                detected_issue_count=len(matching),
                detected_issue_codes=sorted({issue.code.value for issue in matching}),
            )
        )

    return GovernmentFrameworkMapping(
        framework_name="Data Governance Quality Index (DGQI) 2.0",
        mapping_name="ADIP six-dimension operational data-quality mapping",
        disclaimer=(
            "This is an informational alignment created by ADIP. It is not an official DGQI "
            "assessment, Government of India approval, certification, or compliance claim. "
            "DGQI is a broader institutional self-assessment and must be contextualized by the "
            "responsible organization."
        ),
        references=[
            GovernmentFrameworkReference(
                title="Data Governance Quality Index (DGQI) 2.0 Methodology Toolkit",
                publisher="Development Monitoring and Evaluation Office, NITI Aayog",
                url=DGQI_TOOLKIT_URL,
                relevance=(
                    "Defines DGQI data-quality practices, including documented and automated QC, "
                    "missing/incorrect values, summary statistics, metadata, duplicates, "
                    "integrity, and feedback or backcheck mechanisms."
                ),
            ),
            GovernmentFrameworkReference(
                title="DGQI Repository",
                publisher="Development Monitoring and Evaluation Office, NITI Aayog",
                url=DGQI_REPOSITORY_URL,
                relevance="Hosts DGQI methodology, questionnaires, scoring material, and guidance.",
            ),
        ],
        dimensions=dimensions,
    )
