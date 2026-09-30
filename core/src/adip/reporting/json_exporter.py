from pathlib import Path
from typing import ClassVar

from adip.exceptions import ReportExportError
from adip.models.report import AnalysisReport
from adip.reporting.base import BaseExporter
from adip.visualization.static_plots import StaticPlot


class JsonExporter(BaseExporter):
    format_name: ClassVar[str] = "json"
    extension: ClassVar[str] = ".json"

    def export(self, report: AnalysisReport, path: Path, plots: list[StaticPlot] | None = None) -> Path:
        try:
            path.write_text(report.model_dump_json(indent=2), encoding="utf-8")
        except OSError as exc:
            raise ReportExportError(f"Could not write {path.name}: {exc}") from exc
        return path