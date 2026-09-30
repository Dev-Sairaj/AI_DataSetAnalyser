from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import FileResponse

from adip.models import AnalysisReport

from app.core.deps import JobsDep
from app.services.job_manager import JobStateError
from app.services.storage import REPORT_FILES

router = APIRouter(prefix="/api/jobs", tags=["reports"])

# Lets an inline-viewed HTML report render its own styles and images, and nothing else.
_HTML_CSP = "default-src 'none'; img-src data:; style-src 'unsafe-inline'"


def _require_completed(job_id: str, jobs: JobsDep) -> None:
    record = jobs.get(job_id)
    if record.status != "completed":
        raise JobStateError(f"Results are not available: the job is '{record.status}'.")


@router.get("/{job_id}/result", response_model=AnalysisReport)
def get_result(job_id: str, jobs: JobsDep) -> Response:
    """The full analysis (profile, quality, EDA, features, chart data) as JSON."""
    _require_completed(job_id, jobs)
    text = jobs.storage.report_path(job_id, "json").read_text(encoding="utf-8")
    # Returned as-is: the file was already produced from AnalysisReport, so it is not
    # re-validated. response_model above only documents the schema in OpenAPI.
    return Response(content=text, media_type="application/json")


@router.get("/{job_id}/downloads/{fmt}", response_class=FileResponse)
def download_report(job_id: str, fmt: str, jobs: JobsDep, inline: bool = False) -> FileResponse:
    """Download a generated report. `?inline=true` shows the HTML report in the browser."""
    if fmt not in REPORT_FILES:
        raise HTTPException(404, f"Unknown format '{fmt}'. Use: {', '.join(REPORT_FILES)}")
    _require_completed(job_id, jobs)

    path = jobs.storage.report_path(job_id, fmt)
    if not path.exists():
        raise HTTPException(404, "Report file not found.")

    record = jobs.get(job_id)
    extension = path.suffix
    headers = {"Content-Security-Policy": _HTML_CSP} if fmt == "html" else None
    return FileResponse(
        path,
        media_type=REPORT_FILES[fmt][1],
        filename=f"{record.filename.rsplit('.', 1)[0]}_adip_report{extension}",
        content_disposition_type="inline" if inline else "attachment",
        headers=headers,
    )