from adip import __version__
from adip.loaders import supported_extensions
from adip.reporting import available_formats
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/api", tags=["health"])


class HealthResponse(BaseModel):
    status: str
    adip_version: str
    supported_extensions: list[str]
    export_formats: list[str]


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        adip_version=__version__,
        supported_extensions=supported_extensions(),
        export_formats=available_formats(),
    )