"""Authoritative Standard Operating Procedure for ADIP dataset assessment."""

from adip.models.sop import AssessmentSOP, SOPStage


def build_assessment_sop() -> AssessmentSOP:
    """Build the versioned assessment SOP embedded in every analysis report.

    Returns:
        Complete eight-stage SOP with inputs, methods, outputs, and acceptance criteria.

    Raises:
        No exceptions are raised because the SOP definition is static and validated.
    """
    return AssessmentSOP(
        title="ADIP Dataset Quality Assessment Standard Operating Procedure",
        version="1.0",
        scope=(
            "Assessment of uploaded CSV and XLSX datasets from intake through profiling, "
            "quality analysis, optional standardization, scoring, grading, and reporting."
        ),
        stages=[
            SOPStage(
                step=1,
                name="Dataset upload",
                purpose="Accept a dataset safely and create an isolated analysis job.",
                input="User-supplied CSV or XLSX file.",
                method=(
                    "Sanitize the client filename, verify the extension, stream the file in "
                    "bounded chunks, enforce the upload-size limit, and store it under a generated "
                    "job identifier."
                ),
                output=(
                    "Immutable original upload, job record, detected sheets, and preview columns."
                ),
                automation="automatic",
                testing_criteria=[
                    "Supported CSV/XLSX uploads return a job identifier and column preview.",
                    "Unsupported extensions are rejected with HTTP 415.",
                    "Oversized uploads are rejected with HTTP 413 and leave no partial job.",
                    "The stored original bytes remain unchanged by later operations.",
                ],
            ),
            SOPStage(
                step=2,
                name="File validation",
                purpose=(
                    "Confirm the stored file is readable and structurally suitable for analysis."
                ),
                input="Stored original upload plus optional Excel sheet selection.",
                method=(
                    "Validate file existence and size, select the registered loader by extension, "
                    "parse the requested sheet or CSV content, and reject empty or malformed data."
                ),
                output="Validated in-memory dataframe or a specific user-facing validation error.",
                automation="automatic",
                testing_criteria=[
                    "Missing and unsupported files fail with explicit errors.",
                    "Header-only or empty datasets are rejected.",
                    "Excel sheet selection returns the correct sheet columns.",
                    "Loaded row and column counts match the selected source data.",
                ],
            ),
            SOPStage(
                step=3,
                name="Data profiling",
                purpose="Establish the dataset structure and baseline measurements.",
                input="Validated dataframe.",
                method=(
                    "Measure rows, columns, memory, inferred analytical types, missing values, "
                    "unique values, duplicate rows, and representative samples."
                ),
                output="DatasetProfile and per-column profiles used by downstream checks.",
                automation="automatic",
                testing_criteria=[
                    "Profile shape equals the loaded dataframe shape.",
                    "Missing, non-null, and unique counts are internally consistent.",
                    "Duplicate-row count is reproducible.",
                    "Every loaded column has exactly one profile entry.",
                ],
            ),
            SOPStage(
                step=4,
                name="Quality checks",
                purpose="Detect actionable data-quality issues using transparent rules.",
                input="Validated dataframe, DatasetProfile, and quality configuration.",
                method=(
                    "Check missing values, duplicate rows, empty and constant columns, "
                    "cardinality, "
                    "incorrect or mixed types, infinite values, inconsistent text formats, and "
                    "numeric outliers. Assign Clean, Needs Cleaning, or Critical Issues status."
                ),
                output=(
                    "Quality findings with severity, affected counts, evidence, and status rules."
                ),
                automation="automatic",
                testing_criteria=[
                    "Injected missing, duplicate, type, format, and outlier defects are detected.",
                    "A dataset is Clean only when no implemented check reports an issue.",
                    "Any critical finding produces Critical Issues status.",
                    "Every status includes the rules and evidence used to determine it.",
                ],
            ),
            SOPStage(
                step=5,
                name="Standardization and cleaning",
                purpose="Apply only user-approved transformations to a separate working copy.",
                input="Original dataframe and selected text, date, phone, or numeric operations.",
                method=(
                    "Copy the dataframe, execute allow-listed operations in deterministic order, "
                    "protect the target column, retain invalid values for review, and record every "
                    "applied, skipped, or failed step."
                ),
                output="Separate standardized CSV/XLSX file and a machine-readable change log.",
                automation="user_triggered",
                testing_criteria=[
                    "The original dataframe and uploaded file remain unchanged.",
                    "Whitespace, case, date, and phone operations produce expected normalized "
                    "values.",
                    "Min-Max values fall between 0 and 1; Z-scores have mean 0 and standard "
                    "deviation 1.",
                    "Invalid date and phone values are retained and counted in the audit message.",
                ],
            ),
            SOPStage(
                step=6,
                name="Quality score calculation",
                purpose="Produce a reproducible overall quality score from measurable findings.",
                input="DatasetProfile, quality findings, and outlier summaries.",
                method=(
                    "Calculate Accuracy, Completeness, Consistency, Timeliness, Validity, and "
                    "Uniqueness dimensions. Exclude dimensions that cannot be assessed, "
                    "renormalize configured weights across assessed dimensions, and recalculate "
                    "after approved cleaning. Accuracy is an outlier-based proxy; Timeliness "
                    "requires reporting metadata."
                ),
                output=(
                    "Overall score from 0 to 100 plus six dimension assessments, formulas, "
                    "evidence, limitations, and configured/effective weights."
                ),
                automation="automatic_and_user_triggered",
                testing_criteria=[
                    "Every subscore and overall score remains within 0 to 100.",
                    "The same input and configuration produce the same score.",
                    "Before and after scores use the same scoring method.",
                    "The reported overall score equals the weighted subscore calculation.",
                    "Unassessed dimensions have no score and zero effective weight.",
                ],
            ),
            SOPStage(
                step=7,
                name="Quality grading",
                purpose="Translate the numerical score into an understandable quality grade.",
                input="Overall quality score between 0 and 100.",
                method=(
                    "Apply configured inclusive thresholds. Defaults are A >= 90, B >= 80, "
                    "C >= 70, D >= 60, else F."
                ),
                output="Quality grade A, B, C, D, or F with the supporting numerical score.",
                automation="automatic",
                testing_criteria=[
                    "Scores 90, 80, 70, and 60 map to A, B, C, and D respectively.",
                    "Scores below 60 map to F.",
                    "Grade is always derived from the reported score, never entered manually.",
                    "Boundary behavior is covered by automated tests.",
                    "Configured thresholds remain strictly descending and within 0 to 100.",
                ],
            ),
            SOPStage(
                step=8,
                name="Final report generation",
                purpose="Deliver traceable results in human-readable and machine-readable formats.",
                input=(
                    "Dataset metadata, profile, findings, score, grade, EDA, recommendations, "
                    "government mapping, SOP, and optional standardization audit."
                ),
                method=(
                    "Validate the report model, serialize JSON, render HTML and PDF, generate "
                    "Excel sheets, "
                    "and expose controlled download endpoints."
                ),
                output=(
                    "Dashboard result plus non-empty JSON, HTML, Excel, and PDF reports and downloads."
                ),
                automation="automatic",
                testing_criteria=[
                    "JSON parses and validates against the AnalysisReport contract.",
                    "HTML contains dataset identity, findings, score, grade, and required "
                    "sections.",
                    "Excel opens successfully and contains the expected worksheets.",
                    "PDF opens successfully and contains the required final quality sections.",
                    "Reports are available only after the job reaches completed status.",
                ],
            ),
        ],
    )
