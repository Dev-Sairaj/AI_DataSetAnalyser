from pathlib import Path

from adip.loaders import supported_extensions
from fastapi import APIRouter, HTTPException, UploadFile
from starlette.concurrency import run_in_threadpool

from app.core.deps import JobsDep, SettingsDep
from app.schemas.job import InspectResponse, UploadResponse
from app.services.analysis_service import inspect_dataset
from app.services.storage import save_upload

router = APIRouter(prefix="/api/datasets", tags=["datasets"])


@router.post("", response_model=UploadResponse, status_code=201)
async def upload_dataset(file: UploadFile, jobs: JobsDep, settings: SettingsDep) -> UploadResponse:
    """Upload a CSV/XLSX file. Returns a job id plus columns and sheets for the setup form."""
    filename = Path(file.filename or "dataset").name
    ext = Path(filename).suffix.lower()
    if ext not in supported_extensions():
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type '{ext or '(none)'}'. "
            f"Supported: {', '.join(supported_extensions())}",
        )

    record = jobs.create(filename=filename, file_size_bytes=0, file_format=ext.lstrip("."))
    dest = jobs.storage.job_dir(record.job_id) / f"input{ext}"
    try:
        size = await save_upload(file, dest, settings.max_upload_mb * 1024 * 1024)
        inspected = await run_in_threadpool(inspect_dataset, dest)
    except Exception:
        jobs.storage.delete(record.job_id)  # do not leave a half-created job behind
        raise

    record = jobs.update(record.job_id, file_size_bytes=size)
    return UploadResponse(job=record, sheets=inspected.sheets, columns=inspected.columns)


@router.get("/{job_id}/columns", response_model=InspectResponse)
def dataset_columns(job_id: str, jobs: JobsDep, sheet: str | None = None) -> InspectResponse:
    """Columns of another Excel sheet (used when the user switches sheet in the UI)."""
    jobs.get(job_id)  # 404 if unknown
    inspected = inspect_dataset(jobs.storage.input_path(job_id), sheet or None)
    return InspectResponse(sheets=inspected.sheets, columns=inspected.columns)