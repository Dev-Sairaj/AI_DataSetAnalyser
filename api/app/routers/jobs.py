from fastapi import APIRouter, BackgroundTasks, Response

from app.core.deps import JobsDep
from app.schemas.job import JobRecord, RunRequest
from app.services.analysis_service import run_analysis

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


@router.get("", response_model=list[JobRecord])
def list_jobs(jobs: JobsDep) -> list[JobRecord]:
    return jobs.list_recent()


@router.get("/{job_id}", response_model=JobRecord)
def get_job(job_id: str, jobs: JobsDep) -> JobRecord:
    """Poll this endpoint for status and progress."""
    return jobs.get(job_id)


@router.post("/{job_id}/run", response_model=JobRecord, status_code=202)
def run_job(
    job_id: str,
    background: BackgroundTasks,
    jobs: JobsDep,
    body: RunRequest | None = None,
) -> JobRecord:
    """Start the analysis in the background. Optional target column and Excel sheet."""
    body = body or RunRequest()
    record = jobs.begin_run(job_id, target=body.target or None, sheet=body.sheet or None)
    background.add_task(run_analysis, job_id, jobs)
    return record


@router.delete("/{job_id}", status_code=204)
def delete_job(job_id: str, jobs: JobsDep) -> Response:
    jobs.delete(job_id)
    return Response(status_code=204)