"""Filesystem storage: one folder per job (no database, per the SRS).

    storage/jobs/<job_id>/
        input.csv | input.xlsx      the upload (client filename is never used as a path)
        status.json                 job state
        reports/report.{html,json,xlsx}
"""

import re
import shutil
import uuid
from pathlib import Path

from fastapi import UploadFile

_JOB_ID_RE = re.compile(r"^[0-9a-f]{32}$")
_UPLOAD_CHUNK = 1024 * 1024

# format -> (file name on disk, media type)
REPORT_FILES: dict[str, tuple[str, str]] = {
    "html": ("report.html", "text/html"),
    "json": ("report.json", "application/json"),
    "excel": (
        "report.xlsx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ),
}


class JobNotFoundError(Exception):
    """Unknown or malformed job id."""


class FileTooLargeError(Exception):
    def __init__(self, limit_mb: int) -> None:
        super().__init__(f"File exceeds the {limit_mb} MB upload limit.")
        self.limit_mb = limit_mb


class JobStorage:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def new_job_id() -> str:
        return uuid.uuid4().hex

    def job_dir(self, job_id: str) -> Path:
        # Strict id format: this is what blocks path traversal like "../../etc".
        if not _JOB_ID_RE.match(job_id):
            raise JobNotFoundError(job_id)
        return self.root / job_id

    def input_path(self, job_id: str) -> Path:
        matches = sorted(self.job_dir(job_id).glob("input.*"))
        if not matches:
            raise JobNotFoundError(job_id)
        return matches[0]

    def reports_dir(self, job_id: str) -> Path:
        return self.job_dir(job_id) / "reports"

    def report_path(self, job_id: str, fmt: str) -> Path:
        return self.reports_dir(job_id) / REPORT_FILES[fmt][0]

    def list_ids(self) -> list[str]:
        return [p.name for p in self.root.iterdir() if p.is_dir() and _JOB_ID_RE.match(p.name)]

    def delete(self, job_id: str) -> None:
        shutil.rmtree(self.job_dir(job_id), ignore_errors=True)


async def save_upload(file: UploadFile, dest: Path, max_bytes: int) -> int:
    """Stream the upload to disk in chunks, aborting as soon as it exceeds the limit."""
    size = 0
    with dest.open("wb") as out:
        while chunk := await file.read(_UPLOAD_CHUNK):
            size += len(chunk)
            if size > max_bytes:
                raise FileTooLargeError(max_bytes // (1024 * 1024))
            out.write(chunk)
    return size