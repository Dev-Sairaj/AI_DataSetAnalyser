from adip.exceptions import ReportExportError
from adip.reporting.base import BaseExporter
from adip.reporting.excel_exporter import ExcelExporter
from adip.reporting.html_exporter import HtmlExporter
from adip.reporting.json_exporter import JsonExporter

_EXPORTERS: dict[str, type[BaseExporter]] = {
    "html": HtmlExporter,
    "json": JsonExporter,
    "excel": ExcelExporter,
}
_ALIASES = {"xlsx": "excel"}


def available_formats() -> list[str]:
    return sorted(_EXPORTERS)


def get_exporter(name: str) -> BaseExporter:
    key = _ALIASES.get(name.lower(), name.lower())
    cls = _EXPORTERS.get(key)
    if cls is None:
        raise ReportExportError(
            f"Unknown export format '{name}'. Available: {', '.join(available_formats())}"
        )
    return cls()


__all__ = ["BaseExporter", "available_formats", "get_exporter"]