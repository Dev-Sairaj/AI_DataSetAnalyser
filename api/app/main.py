import logging
from contextlib import asynccontextmanager

from adip import __version__
from adip.exceptions import ADIPError
from adip.logging_config import setup_logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import Settings
from app.routers import datasets, health, jobs, reports
from app.services import JobManager, JobNotFoundError, JobStateError, JobStorage
from app.services.storage import FileTooLargeError

logger = logging.getLogger("adip.api")


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_env()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        setup_logging(settings.log_level)
        jobs: JobManager = app.state.jobs
        interrupted = jobs.recover_interrupted()
        if interrupted:
            logger.warning("Marked %d interrupted jobs as failed", interrupted)
        jobs.purge_expired(settings.job_ttl_hours)
        yield

    app = FastAPI(
        title="ADIP API",
        version=__version__,
        description="AI Dataset Intelligence Platform: upload a dataset, get profiling, "
        "data quality, EDA and feature guidance.",
        lifespan=lifespan,
    )
    app.state.settings = settings
    app.state.jobs = JobManager(JobStorage(settings.storage_dir), settings.max_concurrent_jobs)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["Content-Disposition"],
    )

    def error(status: int, detail: str) -> JSONResponse:
        return JSONResponse(status_code=status, content={"detail": detail})

    @app.exception_handler(JobNotFoundError)
    async def _not_found(_: Request, __: JobNotFoundError) -> JSONResponse:
        return error(404, "Job not found.")

    @app.exception_handler(JobStateError)
    async def _bad_state(_: Request, exc: JobStateError) -> JSONResponse:
        return error(409, str(exc))

    @app.exception_handler(FileTooLargeError)
    async def _too_large(_: Request, exc: FileTooLargeError) -> JSONResponse:
        return error(413, str(exc))

    @app.exception_handler(ADIPError)
    async def _adip_error(_: Request, exc: ADIPError) -> JSONResponse:
        return error(422, str(exc))

    for module in (health, datasets, jobs, reports):
        app.include_router(module.router)
    return app


app = create_app()