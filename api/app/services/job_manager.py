"""Job state kept in <job_dir>/status.json, guarded by a lock and written atomically."""

import logging
import os
import threading
from datetime import timedelta

from pydantic import ValidationError

from app.schemas.job import JobRecord, utcnow
from app.services.storage import JobNotFoundError, JobStorage

logger = logging.getLogger(__name__)

_ACTIVE = ("queued", "running")


class JobStateError(Exception):
    """The requested action is not allowed in the job's current state."""


class JobManager:
    def __init__(self, storage: JobStorage, max_concurrent: int = 2) -> None:
        self.storage = storage
        self._lock = threading.RLock()
        # Limits how many analyses run at once; extra jobs wait in the "queued" state.
        self.slots = threading.BoundedSemaphore(max_concurrent)

    # ------------------------------------------------------------------ persistence
    def _status_path(self, job_id: str):
        return self.storage.job_dir(job_id) / "status.json"

    def _write(self, record: JobRecord) -> None:
        path = self._status_path(record.job_id)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(record.model_dump_json(indent=2), encoding="utf-8")
        os.replace(tmp, path)  # atomic: readers never see a half-written file

    def get(self, job_id: str) -> JobRecord:
        with self._lock:
            try:
                return JobRecord.model_validate_json(
                    self._status_path(job_id).read_text(encoding="utf-8")
                )
            except (FileNotFoundError, ValidationError) as exc:
                raise JobNotFoundError(job_id) from exc

    def update(self, job_id: str, **fields: object) -> JobRecord:
        with self._lock:
            record = self.get(job_id).model_copy(update={**fields, "updated_at": utcnow()})
            self._write(record)
            return record

    # ------------------------------------------------------------------ lifecycle
    def create(self, filename: str, file_size_bytes: int, file_format: str) -> JobRecord:
        job_id = self.storage.new_job_id()
        self.storage.job_dir(job_id).mkdir(parents=True)
        record = JobRecord(
            job_id=job_id,
            status="uploaded",
            filename=filename,
            file_format=file_format,
            file_size_bytes=file_size_bytes,
            message="Uploaded",
        )
        with self._lock:
            self._write(record)
        return record

    def begin_run(self, job_id: str, target: str | None, sheet: str | None) -> JobRecord:
        """Atomically move a job to 'queued'. Re-running a finished job is allowed."""
        with self._lock:
            record = self.get(job_id)
            if record.status in _ACTIVE:
                raise JobStateError("This job is already queued or running.")
            self.storage.delete_reports(job_id) if hasattr(self.storage, "delete_reports") else None
            return self.update(
                job_id,
                status="queued",
                progress=0.0,
                message="Queued",
                error=None,
                target=target,
                sheet=sheet,
                started_at=None,
                finished_at=None,
                available_downloads=[],
            )

    def delete(self, job_id: str) -> None:
        with self._lock:
            if self.get(job_id).status in _ACTIVE:
                raise JobStateError("Cannot delete a job while it is queued or running.")
            self.storage.delete(job_id)

    def list_recent(self, limit: int = 50) -> list[JobRecord]:
        records: list[JobRecord] = []
        for job_id in self.storage.list_ids():
            try:
                records.append(self.get(job_id))
            except JobNotFoundError:
                continue
        records.sort(key=lambda r: r.created_at, reverse=True)
        return records[:limit]

    # ------------------------------------------------------------------ housekeeping
    def recover_interrupted(self) -> int:
        """Jobs left queued/running by a crash or restart can never finish: mark them failed."""
        count = 0
        for record in self.list_recent(limit=10_000):
            if record.status in _ACTIVE:
                self.update(
                    record.job_id,
                    status="failed",
                    error="The server restarted while this job was running. Please run it again.",
                    message="Interrupted",
                    finished_at=utcnow(),
                )
                count += 1
        return count

    def purge_expired(self, ttl_hours: int) -> int:
        cutoff = utcnow() - timedelta(hours=ttl_hours)
        count = 0
        for record in self.list_recent(limit=10_000):
            if record.status not in _ACTIVE and record.updated_at < cutoff:
                self.storage.delete(record.job_id)
                count += 1
        if count:
            logger.info("Purged %d expired jobs", count)
        return count