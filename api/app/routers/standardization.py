"""Endpoints for creating and downloading standardized dataset copies."""

from fastapi import APIRouter
from fastapi.responses import FileResponse
from starlette.concurrency import run_in_threadpool

from app.core.deps import JobsDep
from app.schemas.standardization import StandardizationResponse, StandardizeRequest
from app.services.job_manager import JobStateError
from app.services.standardization_service import read_standardization, standardize_dataset
from app.services.storage import JobNotFoundError

router = APIRouter(prefix="/api/jobs", tags=["standardization"])


@router.post("/{job_id}/standardize", response_model=StandardizationResponse)
async def standardize_job(
    job_id: str, body: StandardizeRequest, jobs: JobsDep
) -> StandardizationResponse:
    """Apply approved operations to a copy of the original uploaded dataset."""
    return await run_in_threadpool(standardize_dataset, job_id, jobs, body)


@router.get("/{job_id}/standardization", response_model=StandardizationResponse)
def get_standardization(job_id: str, jobs: JobsDep) -> StandardizationResponse:
    """Return the latest standardization audit report for a job."""
    return read_standardization(job_id, jobs)


@router.get("/{job_id}/downloads/standardized", response_class=FileResponse)
def download_standardized(job_id: str, jobs: JobsDep) -> FileResponse:
    """Download the separate standardized dataset artifact."""
    result = read_standardization(job_id, jobs)
    path = jobs.storage.standardized_data_path(job_id)
    media_type = (
        "text/csv"
        if result.file_format == "csv"
        else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    return FileResponse(path, media_type=media_type, filename=result.download_name)


@router.get("/{job_id}/downloads/final-dataset", response_class=FileResponse)
def download_final_dataset(job_id: str, jobs: JobsDep) -> FileResponse:
    """Download the latest approved derived dataset or the preserved original.

    Args:
        job_id: Completed analysis job identifier.
        jobs: Job manager used to resolve isolated artifacts.

    Returns:
        Final dataset as CSV or XLSX.

    Raises:
        JobStateError: If dataset analysis has not completed.
        JobNotFoundError: If the job or its original upload does not exist.
    """
    record = jobs.get(job_id)
    if record.status != "completed":
        raise JobStateError("The final dataset is available only after analysis completes.")
    try:
        path = jobs.storage.standardized_data_path(job_id)
    except JobNotFoundError:
        path = jobs.storage.input_path(job_id)
    media_type = (
        "text/csv"
        if path.suffix.lower() == ".csv"
        else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    stem = record.filename.rsplit(".", 1)[0]
    return FileResponse(path, media_type=media_type, filename=f"{stem}_final{path.suffix}")
