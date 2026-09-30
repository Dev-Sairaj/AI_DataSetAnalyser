from collections import defaultdict
from pathlib import Path
from typing import ClassVar

from jinja2 import Environment, FileSystemLoader, TemplateError

from adip.exceptions import ReportExportError
from adip.models.report import AnalysisReport
from adip.reporting.base import BaseExporter
from adip.visualization.static_plots import StaticPlot

TEMPLATE_DIR = Path(__file__).parent / "templates"

CATEGORY_LABELS = {
    "target": "Target",
    "data_types": "Data types",
    "missing_values": "Missing values",
    "low_value": "Columns with limited analytical value",
    "redundancy": "Feature redundancy and correlation",
    "encoding": "Encoding",
    "scaling": "Scaling",
}


def _num(value: float | int | None) -> str:
    if value is None:
        return "-"
    if isinstance(value, int):
        return f"{value:,}"
    return f"{value:,.0f}" if abs(value) >= 1000 else f"{value:.4g}"


def _size(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024  # type: ignore[assignment]
    return f"{n} B"


class HtmlExporter(BaseExporter):
    format_name: ClassVar[str] = "html"
    extension: ClassVar[str] = ".html"
    needs_plots: ClassVar[bool] = True

    def __init__(self) -> None:
        self.env = Environment(loader=FileSystemLoader(TEMPLATE_DIR), autoescape=True)
        self.env.filters["num"] = _num
        self.env.filters["size"] = _size

    def export(self, report: AnalysisReport, path: Path, plots: list[StaticPlot] | None = None) -> Path:
        grouped_plots: dict[str, list[StaticPlot]] = defaultdict(list)
        for p in plots or []:
            grouped_plots[p.group].append(p)

        recs: dict[str, list] = {}
        for key, label in CATEGORY_LABELS.items():
            items = [r for r in report.features.recommendations if r.category == key]
            if items:
                recs[label] = items

        severity_counts = defaultdict(int)
        for issue in report.quality.issues:
            severity_counts[issue.severity] += 1

        try:
            html = self.env.get_template("report.html.j2").render(
                r=report, plots=grouped_plots, recs=recs, severity_counts=severity_counts
            )
            path.write_text(html, encoding="utf-8")
        except (TemplateError, OSError) as exc:
            raise ReportExportError(f"Could not write {path.name}: {exc}") from exc
        return path