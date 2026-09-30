"""API settings. Every value can be overridden with an environment variable."""

import os
from dataclasses import dataclass
from pathlib import Path

# api/app/core/config.py -> api/storage/jobs
DEFAULT_STORAGE_DIR = Path(__file__).resolve().parents[2] / "storage" / "jobs"
DEFAULT_CORS = ("http://localhost:5173", "http://127.0.0.1:5173")


@dataclass(frozen=True)
class Settings:
    storage_dir: Path = DEFAULT_STORAGE_DIR
    max_upload_mb: int = 500
    max_concurrent_jobs: int = 2
    job_ttl_hours: int = 24
    cors_origins: tuple[str, ...] = DEFAULT_CORS
    log_level: str = "INFO"

    @classmethod
    def from_env(cls) -> "Settings":
        env = os.environ
        origins = env.get("ADIP_CORS_ORIGINS")
        return cls(
            storage_dir=Path(env.get("ADIP_STORAGE_DIR", str(DEFAULT_STORAGE_DIR))),
            max_upload_mb=int(env.get("ADIP_MAX_UPLOAD_MB", "500")),
            max_concurrent_jobs=int(env.get("ADIP_MAX_CONCURRENT_JOBS", "2")),
            job_ttl_hours=int(env.get("ADIP_JOB_TTL_HOURS", "24")),
            cors_origins=tuple(o.strip() for o in origins.split(",") if o.strip())
            if origins
            else DEFAULT_CORS,
            log_level=env.get("ADIP_LOG_LEVEL", "INFO"),
        )