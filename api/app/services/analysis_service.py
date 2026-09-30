"""Runs ADIP for a job (background worker) and inspects uploads (columns / sheets)."""

import logging
from pathlib import Path
from typing import NamedTuple

import pandas as pd
from adip import ADIP
from adip.config import LoaderConfig
from adip.exceptions import ADIPError, DatasetLoadError
from adip.loaders import load_dataset
from adip.utils.validation import infer_kind

from app.schemas.job import ColumnInfo, utcnow
from app.services.job_manager import JobManager
from app.services.storage import REPORT_FILES, JobNotFoundError

logger = logging.getLogger(__name__)

PREVIEW_ROWS = 1000
ANALYSIS_SHARE = 0.85  # progress spent on analysis; the rest is report writing


class InspectResult(NamedTuple):
    sheets: list[str]
    columns: list[ColumnInfo]


def inspect_dataset(path: Path, sheet: str | None = None) -> InspectResult:
    """Cheap look at an upload: sheet names and column names/kinds from the first rows."""
    sheets: list[str] = []
    if path.suffix.lower() == ".xlsx":
        try:
            with pd.ExcelFile(path, engine="openpyxl") as workbook:
                sheets = [str(s) for s in workbook.sheet_names]
        except Exception as exc:
            raise DatasetLoadError(f"Could not read the Excel workbook: {exc}") from exc

    preview = load_dataset(path, LoaderConfig(chunk_size=PREVIEW_ROWS, max_rows=PREVIEW_ROWS), sheet)
    columns = [
        ColumnInfo(name=str(name), kind=infer_kind(preview.df.iloc[:, i]))
        for i, name in enumerate(preview.df.columns)
    ]
    return InspectResult(sheets, columns)


def run_analysis(job_id: str, jobs: JobManager) -> None:
    """Background worker. Never raises: every outcome is recorded in the job's status."""
    try:
        with jobs.slots:
            _execute(job_id, jobs)
    except JobNotFoundError:
        logger.warning("Job %s disappeared while running", job_id)


def _execute(job_id: str, jobs: JobManager) -> None:
    record = jobs.get(job_id)
    jobs.update(job_id, status="running", started_at=utcnow(), progress=0.02, message="Starting")

    def on_progress(message: str, fraction: float) -> None:
        jobs.update(job_id, progress=round(fraction * ANALYSIS_SHARE, 3), message=message)

    try:
        adip = ADIP(jobs.storage.input_path(job_id), sheet=record.sheet, target=record.target)
        adip.run(on_progress)

        jobs.update(job_id, progress=0.9, message="Writing reports")
        written = adip.export(jobs.storage.reports_dir(job_id), basename="report")

        downloads = [fmt for fmt in REPORT_FILES if fmt in written]
        jobs.update(
            job_id,
            status="completed",
            progress=1.0,
            message="Analysis complete",
            finished_at=utcnow(),
            available_downloads=downloads,
        )
    except ADIPError as exc:  # expected problems: bad file, bad target, ...
        logger.info("Job %s failed: %s", job_id, exc)
        _fail(jobs, job_id, str(exc))
    except JobNotFoundError:
        raise
    except Exception:  # unexpected: log the traceback, show a safe message
        logger.exception("Job %s crashed", job_id)
        _fail(jobs, job_id, "Unexpected error while analysing the dataset.")


def _fail(jobs: JobManager, job_id: str, error: str) -> None:
    jobs.update(job_id, status="failed", error=error, message="Failed", finished_at=utcnow())