from datetime import UTC, datetime
from typing import Literal

from adip.models import ColumnKind
from pydantic import BaseModel, Field

JobStatus = Literal["uploaded", "queued", "running", "completed", "failed"]


def utcnow() -> datetime:
    return datetime.now(UTC)


class JobRecord(BaseModel):
    job_id: str
    status: JobStatus
    progress: float = Field(0.0, ge=0, le=1)
    message: str = ""
    error: str | None = None
    filename: str
    file_format: str
    file_size_bytes: int = 0
    target: str | None = None
    sheet: str | None = None
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
    started_at: datetime | None = None
    finished_at: datetime | None = None
    available_downloads: list[str] = Field(default_factory=list)


class RunRequest(BaseModel):
    target: str | None = None
    sheet: str | None = None


class ColumnInfo(BaseModel):
    name: str
    kind: ColumnKind


class InspectResponse(BaseModel):
    sheets: list[str]  # empty for CSV
    columns: list[ColumnInfo]


class UploadResponse(InspectResponse):
    job: JobRecord