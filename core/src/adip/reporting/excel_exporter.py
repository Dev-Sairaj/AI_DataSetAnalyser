import io
import math
from enum import Enum
from pathlib import Path
from typing import Any, ClassVar

from openpyxl import Workbook
from openpyxl.cell.cell import ILLEGAL_CHARACTERS_RE
from openpyxl.drawing.image import Image as XLImage
from openpyxl.formatting.rule import ColorScaleRule
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.worksheet import Worksheet

from adip.exceptions import ReportExportError
from adip.models.report import AnalysisReport
from adip.reporting.base import BaseExporter
from adip.visualization.static_plots import StaticPlot

HEADER_FILL = PatternFill("solid", fgColor="4F46E5")
HEADER_FONT = Font(bold=True, color="FFFFFF")


def _clean(value: Any) -> Any:
    if isinstance(value, Enum):
        value = value.value
    if isinstance(value, str):
        return ILLEGAL_CHARACTERS_RE.sub("", str(value))
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def _put(ws: Worksheet, row: int, col: int, value: Any) -> None:
    cell = ws.cell(row=row, column=col)
    cell.value = _clean(value)
    if isinstance(cell.value, str):
        cell.data_type = "s"  # never let data starting with '=' become a formula


def _autosize(ws: Worksheet) -> None:
    for idx, cells in enumerate(ws.iter_cols(), start=1):
        longest = max((len(str(c.value)) for c in cells if c.value is not None), default=8)
        ws.column_dimensions[get_column_letter(idx)].width = min(max(longest + 2, 10), 60)


def _table(ws: Worksheet, headers: list[str], rows: list[list[Any]]) -> None:
    for c, h in enumerate(headers, start=1):
        cell = ws.cell(row=1, column=c, value=h)
        cell.fill, cell.font = HEADER_FILL, HEADER_FONT
    for r, row in enumerate(rows, start=2):
        for c, v in enumerate(row, start=1):
            _put(ws, r, c, v)
    ws.freeze_panes = "A2"
    _autosize(ws)


class ExcelExporter(BaseExporter):
    format_name: ClassVar[str] = "excel"
    extension: ClassVar[str] = ".xlsx"
    needs_plots: ClassVar[bool] = True

    def export(self, report: AnalysisReport, path: Path, plots: list[StaticPlot] | None = None) -> Path:
        try:
            wb = Workbook()
            self._summary(wb.active, report)  # type: ignore[arg-type]
            self._scoring(wb.create_sheet("Quality Scoring"), report)
            self._profile(wb.create_sheet("Profile"), report)
            self._quality(wb.create_sheet("Quality Issues"), report)
            self._government_mapping(wb.create_sheet("Govt Framework"), report)
            self._sop(wb.create_sheet("Assessment SOP"), report)
            self._outliers(wb.create_sheet("Outliers"), report)
            self._numeric(wb.create_sheet("Numeric Stats"), report)
            self._categorical(wb.create_sheet("Categorical"), report)
            if report.eda.correlation:
                self._correlation(wb.create_sheet("Correlation"), report)
            self._recommendations(wb.create_sheet("Recommendations"), report)
            if plots:
                self._charts(wb.create_sheet("Charts"), plots)
            wb.save(path)
        except (OSError, ValueError) as exc:
            raise ReportExportError(f"Could not write {path.name}: {exc}") from exc
        return path

    @staticmethod
    def _summary(ws: Worksheet, r: AnalysisReport) -> None:
        ws.title = "Summary"
        rows: list[tuple[str, Any]] = [
            ("Dataset", r.dataset.name), ("Format", r.dataset.file_format),
            ("Sheet", r.dataset.sheet_name or "-"), ("Rows", r.profile.n_rows),
            ("Columns", r.profile.n_cols),
            ("Memory (MB)", round(r.profile.memory_bytes / 1024 / 1024, 2)),
            ("Missing cells (%)", r.profile.missing_pct), ("Duplicate rows", r.profile.duplicate_rows),
            ("Dataset status", r.quality.status),
            ("Status explanation", r.quality.status_summary),
            ("Quality score", r.quality.score), ("Quality grade", r.quality.grade),
            ("Score explanation", r.quality.score_explanation),
            ("Grade explanation", r.quality.grade_explanation),
            ("Target column", r.target or "-"),
            ("Generated", r.generated_at.strftime("%Y-%m-%d %H:%M UTC")),
            ("ADIP version", r.adip_version),
        ]
        for i, (k, v) in enumerate(rows, start=1):
            _put(ws, i, 1, k)
            ws.cell(row=i, column=1).font = Font(bold=True)
            _put(ws, i, 2, v)
        _autosize(ws)

    @staticmethod
    def _scoring(ws: Worksheet, r: AnalysisReport) -> None:
        """Write six-dimension scores, weights, formulas, and limitations.

        Args:
            ws: Destination workbook worksheet.
            r: Completed analysis report.

        Returns:
            None.

        Raises:
            No exceptions are raised for a validated analysis report.
        """
        _table(
            ws,
            [
                "Dimension",
                "Score",
                "Assessment",
                "Configured weight",
                "Effective weight",
                "Formula",
                "Evidence",
                "Limitation",
            ],
            [
                [
                    dimension.name,
                    dimension.score if dimension.score is not None else "Not assessed",
                    dimension.assessment,
                    dimension.configured_weight,
                    dimension.effective_weight,
                    dimension.formula,
                    dimension.evidence,
                    dimension.limitation or "-",
                ]
                for dimension in r.quality.dimension_scores
            ],
        )
        note_row = len(r.quality.dimension_scores) + 4
        _put(ws, note_row, 1, "Overall formula")
        _put(ws, note_row, 2, r.quality.score_explanation)
        _put(ws, note_row + 1, 1, "Grade rule")
        _put(ws, note_row + 1, 2, r.quality.grade_explanation)
        _put(ws, note_row + 2, 1, "Thresholds")
        _put(
            ws,
            note_row + 2,
            2,
            ", ".join(
                f"{grade} >= {threshold:g}"
                for grade, threshold in r.quality.grading_thresholds.items()
                if grade != "F"
            )
            + ", else F",
        )
        for row in range(note_row, note_row + 3):
            ws.cell(row=row, column=1).font = Font(bold=True)
        _autosize(ws)

    @staticmethod
    def _profile(ws: Worksheet, r: AnalysisReport) -> None:
        _table(ws, ["Column", "Type", "Kind", "Non-null", "Missing", "Missing %", "Unique", "Unique %", "Samples"],
               [[c.name, c.dtype, c.kind, c.non_null, c.missing, c.missing_pct, c.unique, c.unique_pct,
                 ", ".join(c.sample_values)] for c in r.profile.columns])

    @staticmethod
    def _quality(ws: Worksheet, r: AnalysisReport) -> None:
        _table(ws, ["Severity", "Issue", "Column", "Affected", "Affected %", "Message"],
               [[i.severity, i.code, i.column or "-", i.affected_count, i.affected_pct, i.message]
                for i in r.quality.issues])

    @staticmethod
    def _government_mapping(ws: Worksheet, r: AnalysisReport) -> None:
        """Write implemented and external/manual framework coverage by dimension."""
        mapping = r.government_framework
        rows = [
            [
                dimension.name,
                dimension.coverage,
                dimension.detected_issue_count,
                ", ".join(dimension.detected_issue_codes) or "-",
                "; ".join(dimension.implemented_checks) or "None automated",
                "; ".join(dimension.external_or_manual_checks),
                dimension.explanation,
            ]
            for dimension in mapping.dimensions
        ]
        _table(
            ws,
            [
                "Dimension",
                "Coverage",
                "Findings",
                "Issue codes",
                "Implemented checks",
                "External/manual checks",
                "Explanation",
            ],
            rows,
        )
        note_row = len(rows) + 4
        _put(ws, note_row, 1, "Disclaimer")
        ws.cell(row=note_row, column=1).font = Font(bold=True)
        _put(ws, note_row, 2, mapping.disclaimer)
        _autosize(ws)

    @staticmethod
    def _sop(ws: Worksheet, r: AnalysisReport) -> None:
        """Write the complete assessment SOP as an auditable worksheet."""
        _table(
            ws,
            [
                "Step",
                "Stage",
                "Purpose",
                "Input",
                "Method",
                "Output",
                "Automation",
                "Testing criteria",
            ],
            [
                [
                    stage.step,
                    stage.name,
                    stage.purpose,
                    stage.input,
                    stage.method,
                    stage.output,
                    stage.automation,
                    "; ".join(stage.testing_criteria),
                ]
                for stage in r.sop.stages
            ],
        )

    @staticmethod
    def _outliers(ws: Worksheet, r: AnalysisReport) -> None:
        _table(ws, ["Column", "Method", "Outliers", "%", "Lower bound", "Upper bound"],
               [[o.column, o.method, o.count, o.pct, o.lower_bound, o.upper_bound] for o in r.quality.outliers])

    @staticmethod
    def _numeric(ws: Worksheet, r: AnalysisReport) -> None:
        _table(ws, ["Column", "Count", "Mean", "Std", "Min", "Q1", "Median", "Q3", "Max", "Skewness", "Kurtosis", "Shape"],
               [[s.column, s.count, s.mean, s.std, s.min, s.q1, s.median, s.q3, s.max, s.skewness, s.kurtosis, s.shape]
                for s in r.eda.numeric])

    @staticmethod
    def _categorical(ws: Worksheet, r: AnalysisReport) -> None:
        rows = [[c.column, c.unique, v.value, v.count, v.pct] for c in r.eda.categorical for v in c.top_values]
        _table(ws, ["Column", "Unique values", "Category", "Count", "%"], rows)

    @staticmethod
    def _correlation(ws: Worksheet, r: AnalysisReport) -> None:
        corr = r.eda.correlation
        assert corr is not None
        _table(ws, ["", *corr.columns], [[name, *row] for name, row in zip(corr.columns, corr.matrix)])
        ref = f"B2:{get_column_letter(len(corr.columns) + 1)}{len(corr.columns) + 1}"
        ws.conditional_formatting.add(
            ref, ColorScaleRule(start_type="num", start_value=-1, start_color="3B82F6",
                                mid_type="num", mid_value=0, mid_color="FFFFFF",
                                end_type="num", end_value=1, end_color="EF4444"))

    @staticmethod
    def _recommendations(ws: Worksheet, r: AnalysisReport) -> None:
        _table(ws, ["Severity", "Category", "Columns", "Title", "Recommendation", "Rationale"],
               [[x.severity, x.category, ", ".join(x.columns) or "-", x.title, x.recommendation, x.rationale]
                for x in r.features.recommendations])

    @staticmethod
    def _charts(ws: Worksheet, plots: list[StaticPlot]) -> None:
        next_row = [2, 2]  # two image columns, always fill the shorter one
        anchors = ["A", "K"]
        for p in plots:
            img = XLImage(io.BytesIO(p.png))
            scale = min(1.0, 460 / img.width)
            img.width, img.height = int(img.width * scale), int(img.height * scale)
            side = 0 if next_row[0] <= next_row[1] else 1
            ws.add_image(img, f"{anchors[side]}{next_row[side]}")
            next_row[side] += math.ceil(img.height / 20) + 2
