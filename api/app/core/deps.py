"""FastAPI dependencies. Shared objects live on app.state so tests can build isolated apps."""

from typing import Annotated

from fastapi import Depends, Request

from app.core.config import Settings
from app.services.job_manager import JobManager


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_jobs(request: Request) -> JobManager:
    return request.app.state.jobs


SettingsDep = Annotated[Settings, Depends(get_settings)]
JobsDep = Annotated[JobManager, Depends(get_jobs)]