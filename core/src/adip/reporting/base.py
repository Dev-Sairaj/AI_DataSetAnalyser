from abc import ABC, abstractmethod
from pathlib import Path
from typing import ClassVar

from adip.models.report import AnalysisReport
from adip.visualization.static_plots import StaticPlot


class BaseExporter(ABC):
    """Add a new report format by subclassing this and registering it in reporting/__init__.py."""

    format_name: ClassVar[str]
    extension: ClassVar[str]
    needs_plots: ClassVar[bool] = False

    @abstractmethod
    def export(
        self, report: AnalysisReport, path: Path, plots: list[StaticPlot] | None = None
    ) -> Path:
        """Write the report to `path` and return the path."""