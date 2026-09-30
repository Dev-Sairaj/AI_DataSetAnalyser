"""Orchestrates every engine. This is the single entry point for the library, CLI and API."""

import logging
from collections.abc import Callable
from pathlib import Path

from adip import __version__
from adip.config import ADIPConfig, load_config
from adip.eda import EdaEngine
from adip.exceptions import TargetColumnError
from adip.features import FeatureEngine
from adip.loaders import load_dataset
from adip.models.report import AnalysisReport
from adip.profiling import ProfilingEngine
from adip.quality import QualityEngine
from adip.reporting import get_exporter
from adip.visualization import build_chart_data, render_plots

logger = logging.getLogger(__name__)

ProgressCallback = Callable[[str, float], None]
DEFAULT_FORMATS = ("html", "json", "excel")


class ADIP:
    """Usage: ``report = ADIP("data.csv", target="churn").run()``"""

    def __init__(
        self,
        path: str | Path,
        config: ADIPConfig | str | Path | None = None,
        sheet: str | int | None = None,
        target: str | None = None,
    ) -> None:
        self.path = Path(path)
        self.config = config if isinstance(config, ADIPConfig) else load_config(config)
        self.sheet = sheet
        self.target = target
        self.report: AnalysisReport | None = None

    def run(self, progress: ProgressCallback | None = None) -> AnalysisReport:
        def step(message: str, fraction: float) -> None:
            logger.info(message)
            if progress:
                progress(message, fraction)

        cfg = self.config

        step("Loading dataset", 0.05)
        dataset = load_dataset(self.path, cfg.loader, self.sheet)
        df = dataset.df

        if self.target is not None and self.target not in df.columns:
            preview = ", ".join(map(str, list(df.columns)[:30]))
            raise TargetColumnError(f"Target column '{self.target}' not found. Columns: {preview}")

        step("Profiling dataset", 0.20)
        profile = ProfilingEngine().run(df)

        step("Assessing data quality", 0.40)
        quality = QualityEngine(cfg.quality).run(df, profile)

        step("Running exploratory analysis", 0.60)
        eda = EdaEngine(cfg.eda).run(df, profile)

        step("Generating feature recommendations", 0.80)
        features = FeatureEngine(cfg.features, cfg.quality, cfg.eda).run(
            df, profile, quality, eda, self.target
        )

        step("Preparing chart data", 0.95)
        charts = build_chart_data(profile, eda)

        self.report = AnalysisReport(
            adip_version=__version__,
            dataset=dataset.info,
            target=self.target,
            profile=profile,
            quality=quality,
            eda=eda,
            features=features,
            charts=charts,
            config=cfg.model_dump(),
        )
        step("Analysis complete", 1.0)
        return self.report

    def export(
        self,
        output_dir: str | Path,
        formats: list[str] | tuple[str, ...] = DEFAULT_FORMATS,
        basename: str | None = None,
    ) -> dict[str, Path]:
        """Write reports. Returns {format: path}. Runs the analysis first if needed."""
        exporters = [get_exporter(f) for f in dict.fromkeys(formats)]  # validate + de-duplicate
        report = self.report or self.run()

        plots = render_plots(report.charts) if any(e.needs_plots for e in exporters) else []
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        stem = basename or f"{Path(report.dataset.name).stem}_adip_report"

        written: dict[str, Path] = {}
        for exporter in exporters:
            written[exporter.format_name] = exporter.export(
                report, out / f"{stem}{exporter.extension}", plots
            )
            logger.info("Wrote %s", written[exporter.format_name])
        return written


def analyze(
    path: str | Path,
    config: ADIPConfig | str | Path | None = None,
    sheet: str | int | None = None,
    target: str | None = None,
) -> AnalysisReport:
    """One-liner for notebooks: ``report = analyze("data.csv")``."""
    return ADIP(path, config, sheet, target).run()