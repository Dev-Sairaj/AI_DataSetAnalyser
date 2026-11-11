"""Apply approved standardization operations and save a separate dataset copy."""

import os
from pathlib import Path

from adip.config import LoaderConfig
from adip.fixes import FixEngine, FixPlan, FixReport, FixStep
from adip.loaders import load_dataset
from adip.models import AnalysisReport
from adip.reporting.pdf_exporter import PdfExporter
from adip.visualization import render_plots

from app.schemas.standardization import StandardizationResponse, StandardizeRequest
from app.services.job_manager import JobManager, JobStateError


def _build_plan(request: StandardizeRequest, target: str | None) -> FixPlan:
    """Translate an API request into an allow-listed deterministic fix plan.

    Args:
        request: Validated standardization selections.
        target: Optional protected machine-learning target column.

    Returns:
        Ordered, validated fix plan.
    """
    steps: list[FixStep] = []
    if request.text_columns:
        steps.append(
            FixStep(
                fix="standardize_text",
                columns=request.text_columns,
                params={"case": request.text_case},
                reason="Normalize text and categorical values.",
                source="user",
            )
        )
    if request.date_columns:
        steps.append(
            FixStep(
                fix="normalize_dates",
                columns=request.date_columns,
                params={"format": request.date_format, "dayfirst": request.dayfirst},
                reason="Normalize parseable dates while retaining invalid values.",
                source="user",
            )
        )
    if request.phone_columns:
        steps.append(
            FixStep(
                fix="standardize_phone",
                columns=request.phone_columns,
                params={"country_code": request.phone_country_code},
                reason="Validate and normalize phone numbers.",
                source="user",
            )
        )
    if request.numeric_columns and request.scaling_method != "none":
        steps.append(
            FixStep(
                fix="scale",
                columns=request.numeric_columns,
                params={"method": request.scaling_method},
                reason="Apply optional numerical standardization.",
                source="user",
            )
        )
    return FixPlan(source="user", target=target, steps=steps)


def _write_standardized_dataset(frame, path: Path, sheet: str | None) -> None:
    """Atomically write a standardized CSV or XLSX artifact.

    Args:
        frame: Standardized pandas dataframe.
        path: Final output path with CSV or XLSX extension.
        sheet: Optional original Excel sheet name.

    Raises:
        ValueError: If the output extension is unsupported.
        OSError: If the artifact cannot be written or moved into place.
    """
    temporary = path.with_name(f".{path.stem}.tmp{path.suffix}")
    try:
        if path.suffix == ".csv":
            frame.to_csv(temporary, index=False)
        elif path.suffix == ".xlsx":
            frame.to_excel(temporary, index=False, sheet_name=sheet or "Standardized")
        else:
            raise ValueError(f"Unsupported output format: {path.suffix}")
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _refresh_pdf_report(job_id: str, jobs: JobManager, comparison: FixReport) -> None:
    """Regenerate the final PDF with the latest cleaning comparison.

    Args:
        job_id: Completed analysis job identifier.
        jobs: Job manager providing isolated report storage.
        comparison: Latest standardization audit to embed.

    Returns:
        None.

    Raises:
        ReportExportError: If the final PDF cannot be regenerated.
        OSError: If the stored JSON analysis cannot be read.
        ValueError: If the stored analysis report is invalid.
    """
    analysis = AnalysisReport.model_validate_json(
        jobs.storage.report_path(job_id, "json").read_text(encoding="utf-8")
    )
    PdfExporter().export(
        analysis,
        jobs.storage.report_path(job_id, "pdf"),
        render_plots(analysis.charts),
        comparison,
    )


def standardize_dataset(
    job_id: str, jobs: JobManager, request: StandardizeRequest
) -> StandardizationResponse:
    """Create a standardized copy without modifying the uploaded dataset.

    Args:
        job_id: Completed analysis job identifier.
        jobs: Job manager used to access status and isolated storage.
        request: User-approved standardization operations.

    Returns:
        Audit report and standardized-file metadata.

    Raises:
        JobStateError: If analysis is incomplete or no operation was selected.
        ADIPError: If the original dataset cannot be loaded or standardized.
        OSError: If derived artifacts cannot be written.
    """
    record = jobs.get(job_id)
    if record.status != "completed":
        raise JobStateError("Standardization is available only after analysis completes.")
    if not request.has_operations():
        raise JobStateError("Select at least one standardization operation.")

    source = jobs.storage.input_path(job_id)
    loaded = load_dataset(source, LoaderConfig(), record.sheet)
    plan = _build_plan(request, record.target)
    outcome = FixEngine().apply(loaded.df, plan, target=record.target)

    extension = ".xlsx" if source.suffix.lower() == ".xlsx" else ".csv"
    output = jobs.storage.new_standardized_data_path(job_id, extension)
    _write_standardized_dataset(outcome.df, output, record.sheet)
    jobs.storage.standardization_report_path(job_id).write_text(
        outcome.report.model_dump_json(indent=2), encoding="utf-8"
    )
    _refresh_pdf_report(job_id, jobs, outcome.report)
    return StandardizationResponse(
        file_format=extension.lstrip("."),
        download_name=f"{Path(record.filename).stem}_standardized{extension}",
        report=outcome.report,
    )


def read_standardization(job_id: str, jobs: JobManager) -> StandardizationResponse:
    """Read the latest saved standardization result for a job.

    Args:
        job_id: Completed analysis job identifier.
        jobs: Job manager used to access isolated storage.

    Returns:
        Saved audit report and standardized-file metadata.

    Raises:
        JobStateError: If no standardized output currently exists.
    """
    record = jobs.get(job_id)
    report_path = jobs.storage.standardization_report_path(job_id)
    try:
        report = FixReport.model_validate_json(report_path.read_text(encoding="utf-8"))
        output = jobs.storage.standardized_data_path(job_id)
    except (FileNotFoundError, ValueError) as exc:
        raise JobStateError("No standardized dataset is available for this job.") from exc
    return StandardizationResponse(
        file_format=output.suffix.lstrip("."),
        download_name=f"{Path(record.filename).stem}_standardized{output.suffix}",
        report=report,
    )
