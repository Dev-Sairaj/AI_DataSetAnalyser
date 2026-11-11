"""Polished PDF export for final dataset-quality results."""

import io
import os
from pathlib import Path
from typing import Any, ClassVar
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, StyleSheet1, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    CondPageBreak,
    HRFlowable,
    Image,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.platypus.doctemplate import LayoutError

from adip.exceptions import ReportExportError
from adip.fixes.plan import FixReport
from adip.models.report import AnalysisReport
from adip.reporting.base import BaseExporter
from adip.visualization.static_plots import StaticPlot

PRIMARY = colors.HexColor("#4F46E5")
PRIMARY_DARK = colors.HexColor("#312E81")
MUTED = colors.HexColor("#64748B")
LIGHT = colors.HexColor("#F8FAFC")
BORDER = colors.HexColor("#E2E8F0")
SUCCESS = colors.HexColor("#047857")
WARNING = colors.HexColor("#B45309")
DANGER = colors.HexColor("#B91C1C")
MAX_PDF_ISSUES = 200
MAX_PDF_RECOMMENDATIONS = 100
MAX_PDF_PLOTS = 4


def _styles() -> StyleSheet1:
    """Create the PDF typography system.

    Returns:
        ReportLab stylesheet used by every PDF section.

    Raises:
        No exceptions are raised.
    """
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="ReportTitle",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=22,
            leading=27,
            textColor=PRIMARY_DARK,
            spaceAfter=5 * mm,
        )
    )
    styles.add(
        ParagraphStyle(
            name="SectionTitle",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=15,
            leading=19,
            textColor=PRIMARY_DARK,
            spaceBefore=5 * mm,
            spaceAfter=3 * mm,
        )
    )
    styles.add(
        ParagraphStyle(
            name="Subheading",
            parent=styles["Heading3"],
            fontName="Helvetica-Bold",
            fontSize=10.5,
            leading=14,
            textColor=colors.HexColor("#1E293B"),
            spaceBefore=3 * mm,
            spaceAfter=1.5 * mm,
        )
    )
    styles.add(
        ParagraphStyle(
            name="BodySmall",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=12,
            textColor=colors.HexColor("#334155"),
        )
    )
    styles.add(
        ParagraphStyle(
            name="Muted",
            parent=styles["BodySmall"],
            textColor=MUTED,
        )
    )
    styles.add(
        ParagraphStyle(
            name="Kpi",
            parent=styles["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=14,
            leading=17,
            alignment=TA_CENTER,
            textColor=PRIMARY_DARK,
        )
    )
    return styles


def _p(value: Any, style: ParagraphStyle) -> Paragraph:
    """Convert arbitrary report data to a safe PDF paragraph.

    Args:
        value: Value to render.
        style: Paragraph style.

    Returns:
        XML-escaped ReportLab paragraph.

    Raises:
        No exceptions are raised for string-convertible values.
    """
    text = "-" if value is None or value == "" else str(value)
    return Paragraph(escape(text), style)


def _table(
    rows: list[list[Any]],
    widths: list[float],
    styles: StyleSheet1,
    header: bool = True,
) -> Table:
    """Create a repeatable, page-splitting report table.

    Args:
        rows: Table values, with an optional first header row.
        widths: Column widths in ReportLab units.
        styles: Active report stylesheet.
        header: Whether the first row is a styled repeating header.

    Returns:
        Styled ReportLab table.

    Raises:
        ValueError: If table dimensions are inconsistent.
    """
    body_style = styles["BodySmall"]
    header_style = ParagraphStyle(
        "TableHeader",
        parent=body_style,
        fontName="Helvetica-Bold",
        textColor=colors.white,
    )
    data = []
    for row_index, row in enumerate(rows):
        cell_style = header_style if header and row_index == 0 else body_style
        data.append([cell if isinstance(cell, Paragraph) else _p(cell, cell_style) for cell in row])
    table = Table(data, colWidths=widths, repeatRows=1 if header else 0, hAlign="LEFT")
    commands = [
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.35, BORDER),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("ROWBACKGROUNDS", (0, 1 if header else 0), (-1, -1), [colors.white, LIGHT]),
    ]
    if header:
        commands.extend(
            [
                ("BACKGROUND", (0, 0), (-1, 0), PRIMARY_DARK),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ]
        )
    table.setStyle(TableStyle(commands))
    return table


def _page_decoration(canvas: Any, document: Any) -> None:
    """Draw a consistent header, footer, and page number.

    Args:
        canvas: Active ReportLab canvas.
        document: Active document template.

    Returns:
        None.

    Raises:
        No exceptions are raised for a valid ReportLab canvas.
    """
    canvas.saveState()
    page_width, page_height = A4
    canvas.setStrokeColor(BORDER)
    canvas.setLineWidth(0.5)
    canvas.line(18 * mm, page_height - 14 * mm, page_width - 18 * mm, page_height - 14 * mm)
    canvas.setFont("Helvetica-Bold", 8)
    canvas.setFillColor(PRIMARY_DARK)
    canvas.drawString(18 * mm, page_height - 10 * mm, "ADIP Final Data Quality Report")
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(MUTED)
    canvas.drawRightString(page_width - 18 * mm, 10 * mm, f"Page {document.page}")
    canvas.drawString(18 * mm, 10 * mm, "Generated by ADIP - deterministic assessment")
    canvas.restoreState()


class PdfExporter(BaseExporter):
    """Generate a paginated final quality report with optional cleaning comparison."""

    format_name: ClassVar[str] = "pdf"
    extension: ClassVar[str] = ".pdf"
    needs_plots: ClassVar[bool] = True

    def export(
        self,
        report: AnalysisReport,
        path: Path,
        plots: list[StaticPlot] | None = None,
        comparison: FixReport | None = None,
    ) -> Path:
        """Write an atomic PDF report and return its final path.

        Args:
            report: Completed dataset analysis.
            path: Final PDF output path.
            plots: Optional static EDA plots.
            comparison: Optional latest cleaning or standardization audit.

        Returns:
            Final PDF path.

        Raises:
            ReportExportError: If PDF generation or atomic replacement fails.
        """
        temporary = path.with_name(f".{path.stem}.tmp{path.suffix}")
        try:
            document = SimpleDocTemplate(
                str(temporary),
                pagesize=A4,
                rightMargin=18 * mm,
                leftMargin=18 * mm,
                topMargin=20 * mm,
                bottomMargin=18 * mm,
                title=f"ADIP Report - {report.dataset.name}",
                author="AI Dataset Intelligence Platform",
            )
            document.build(
                self._story(report, plots or [], comparison),
                onFirstPage=_page_decoration,
                onLaterPages=_page_decoration,
            )
            os.replace(temporary, path)
        except (OSError, ValueError, TypeError, LayoutError) as exc:
            temporary.unlink(missing_ok=True)
            raise ReportExportError(f"Could not write {path.name}: {exc}") from exc
        return path

    def _story(
        self,
        report: AnalysisReport,
        plots: list[StaticPlot],
        comparison: FixReport | None,
    ) -> list[Any]:
        """Build the complete ordered list of PDF flowables.

        Args:
            report: Completed dataset analysis.
            plots: Static plots available for the report appendix.
            comparison: Optional cleaning and standardization audit.

        Returns:
            ReportLab flowables ready for document construction.

        Raises:
            No exceptions are raised for validated report models and valid PNG plots.
        """
        styles = _styles()
        comparison_section = self._comparison_section(comparison, styles)
        comparison_intro_size = 2 if comparison is not None else 1
        story: list[Any] = [
            Spacer(1, 3 * mm),
            _p("Final Data Quality Report", styles["ReportTitle"]),
            _p(report.dataset.name, styles["Subheading"]),
            _p(
                f"Generated {report.generated_at.strftime('%Y-%m-%d %H:%M UTC')} | "
                f"ADIP v{report.adip_version}",
                styles["Muted"],
            ),
            Spacer(1, 3 * mm),
            HRFlowable(width="100%", color=PRIMARY, thickness=1.2),
            _p("Executive summary", styles["SectionTitle"]),
            self._summary_table(report, styles, comparison),
            Spacer(1, 2 * mm),
            _p(
                (
                    f"Latest derived dataset status: "
                    f"{comparison.after.status or report.quality.status}; "
                    f"{comparison.after.issues} detected issue(s)."
                    if comparison is not None
                    else report.quality.status_summary
                ),
                styles["BodySmall"],
            ),
            _p(
                comparison.after.score_explanation
                if comparison is not None
                else report.quality.score_explanation,
                styles["Muted"],
            ),
            _p("Six quality dimensions", styles["SectionTitle"]),
            self._dimensions_table(report, styles, comparison),
            _p("Detected issues", styles["SectionTitle"]),
            *self._issues_section(report, styles, comparison),
            KeepTogether(
                [
                    _p("Cleaning and standardization", styles["SectionTitle"]),
                    *comparison_section[:comparison_intro_size],
                ]
            ),
            *comparison_section[comparison_intro_size:],
            _p("Recommendations", styles["SectionTitle"]),
            *self._recommendations_section(report, styles),
            KeepTogether(
                [
                    _p("Final dataset", styles["SectionTitle"]),
                    _p(
                        (
                            "The final dataset is the latest approved cleaned/standardized copy "
                            "when one exists; otherwise it is the preserved original upload. "
                            "Download it from the Final dataset section of the ADIP dashboard."
                        ),
                        styles["BodySmall"],
                    ),
                ]
            ),
            KeepTogether(
                [
                    _p("Assessment limitations", styles["SectionTitle"]),
                    _p(report.government_framework.disclaimer, styles["BodySmall"]),
                ]
            ),
            _p("Government framework alignment", styles["SectionTitle"]),
            *self._governance_section(report, styles),
        ]
        if plots and report.profile.n_rows >= 20:
            story.extend(
                [CondPageBreak(105 * mm), _p("Selected analysis charts", styles["SectionTitle"])]
            )
            for plot in plots[:MAX_PDF_PLOTS]:
                image = Image(io.BytesIO(plot.png))
                image._restrictSize(165 * mm, 90 * mm)
                story.extend([_p(plot.title, styles["Subheading"]), image, Spacer(1, 4 * mm)])
        return story

    @staticmethod
    def _summary_table(
        report: AnalysisReport,
        styles: StyleSheet1,
        comparison: FixReport | None,
    ) -> Table:
        """Create the executive KPI table.

        Args:
            report: Completed dataset analysis.
            styles: Active PDF styles.
            comparison: Optional final derived-dataset assessment.

        Returns:
            Four-column KPI table.

        Raises:
            No exceptions are raised for a validated report.
        """
        if comparison is None:
            values = [
                ("Dataset status", report.quality.status),
                ("Quality score", f"{report.quality.score} / 100"),
                ("Quality grade", report.quality.grade),
                ("Rows", f"{report.profile.n_rows:,}"),
                ("Columns", f"{report.profile.n_cols:,}"),
                ("Missing values", f"{report.profile.total_missing:,}"),
                ("Duplicate records", f"{report.profile.duplicate_rows:,}"),
                ("Detected issues", f"{len(report.quality.issues):,}"),
            ]
        else:
            final = comparison.after
            values = [
                ("Dataset status", final.status or report.quality.status),
                ("Quality score", f"{final.score} / 100"),
                ("Quality grade", final.grade),
                ("Rows", f"{comparison.rows_after:,}"),
                ("Columns", f"{comparison.cols_after:,}"),
                ("Missing values", f"{final.missing_values:,}"),
                ("Duplicate records", f"{final.duplicate_records:,}"),
                ("Detected issues", f"{final.issues:,}"),
            ]
        cells: list[list[Any]] = []
        for index in range(0, len(values), 4):
            group = values[index : index + 4]
            cells.append([_p(value, styles["Kpi"]) for _, value in group])
            cells.append([_p(label, styles["Muted"]) for label, _ in group])
        table = Table(cells, colWidths=[43.5 * mm] * 4)
        table.setStyle(
            TableStyle(
                [
                    ("GRID", (0, 0), (-1, -1), 0.4, BORDER),
                    ("BACKGROUND", (0, 0), (-1, -1), LIGHT),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("TOPPADDING", (0, 0), (-1, -1), 7),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                ]
            )
        )
        return table

    @staticmethod
    def _dimensions_table(
        report: AnalysisReport,
        styles: StyleSheet1,
        comparison: FixReport | None,
    ) -> Table:
        """Create the six-dimension score and evidence table.

        Args:
            report: Completed dataset analysis.
            styles: Active PDF styles.
            comparison: Optional final derived-dataset assessment.

        Returns:
            Dimension table.

        Raises:
            No exceptions are raised for a validated report.
        """
        rows: list[list[Any]] = [["Dimension", "Score", "Assessment", "Weight", "Evidence"]]
        dimensions = (
            comparison.after.dimensions
            if comparison is not None
            else report.quality.dimension_scores
        )
        for dimension in dimensions:
            rows.append(
                [
                    dimension.name,
                    dimension.score if dimension.score is not None else "Not assessed",
                    dimension.assessment.replace("_", " "),
                    f"{dimension.effective_weight * 100:.1f}%",
                    dimension.evidence
                    + (f" Limitation: {dimension.limitation}" if dimension.limitation else ""),
                ]
            )
        return _table(rows, [25 * mm, 20 * mm, 25 * mm, 20 * mm, 84 * mm], styles)

    @staticmethod
    def _issues_section(
        report: AnalysisReport,
        styles: StyleSheet1,
        comparison: FixReport | None,
    ) -> list[Any]:
        """Create the detected-issues table with a documented safety cap.

        Args:
            report: Completed dataset analysis.
            styles: Active PDF styles.
            comparison: Optional final derived-dataset assessment.

        Returns:
            Issue-section flowables.

        Raises:
            No exceptions are raised for a validated report.
        """
        issues = comparison.after.issue_details if comparison is not None else report.quality.issues
        if not issues:
            return [_p("No automated quality issues were detected.", styles["BodySmall"])]
        rows: list[list[Any]] = [["Severity", "Issue", "Column", "Affected", "Details"]]
        for issue in issues[:MAX_PDF_ISSUES]:
            rows.append(
                [
                    issue.severity,
                    issue.code.value,
                    issue.column or "-",
                    f"{issue.affected_count:,}",
                    issue.message,
                ]
            )
        result: list[Any] = [_table(rows, [19 * mm, 31 * mm, 29 * mm, 19 * mm, 76 * mm], styles)]
        omitted = len(issues) - MAX_PDF_ISSUES
        if omitted > 0:
            result.append(
                _p(
                    f"{omitted:,} additional findings are available in the JSON and Excel reports.",
                    styles["Muted"],
                )
            )
        return result

    @staticmethod
    def _governance_section(report: AnalysisReport, styles: StyleSheet1) -> list[Any]:
        """Create government-framework coverage and reference details.

        Args:
            report: Completed dataset analysis.
            styles: Active PDF styles.

        Returns:
            Framework mapping table and authoritative reference list.

        Raises:
            No exceptions are raised for a validated report.
        """
        rows: list[list[Any]] = [
            ["Dimension", "Coverage", "Implemented checks", "External or manual checks"]
        ]
        for dimension in report.government_framework.dimensions:
            rows.append(
                [
                    dimension.name,
                    dimension.coverage.replace("_", " "),
                    "; ".join(dimension.implemented_checks) or "None automated",
                    "; ".join(dimension.external_or_manual_checks),
                ]
            )
        result: list[Any] = [
            _table(rows, [27 * mm, 28 * mm, 58 * mm, 61 * mm], styles),
            _p("References", styles["Subheading"]),
        ]
        for reference in report.government_framework.references:
            result.append(
                _p(
                    f"- {reference.title} ({reference.publisher}): {reference.url}",
                    styles["Muted"],
                )
            )
        return result

    @staticmethod
    def _comparison_section(comparison: FixReport | None, styles: StyleSheet1) -> list[Any]:
        """Create cleaning summary and before-vs-after metrics.

        Args:
            comparison: Latest fix report, if a derived dataset exists.
            styles: Active PDF styles.

        Returns:
            Comparison flowables.

        Raises:
            No exceptions are raised for a validated comparison.
        """
        if comparison is None:
            return [
                _p(
                    "No cleaned or standardized dataset had been generated when this report was "
                    "created. The preserved original upload is currently the final dataset.",
                    styles["BodySmall"],
                )
            ]
        metric_rows = [
            ["Metric", "Original", "Cleaned", "Change"],
            [
                "Quality score",
                comparison.before.score,
                comparison.after.score,
                comparison.score_delta,
            ],
            [
                "Missing values",
                comparison.before.missing_values,
                comparison.after.missing_values,
                comparison.missing_values_delta,
            ],
            [
                "Duplicate records",
                comparison.before.duplicate_records,
                comparison.after.duplicate_records,
                comparison.duplicate_records_delta,
            ],
            [
                "Invalid values",
                comparison.before.invalid_values,
                comparison.after.invalid_values,
                comparison.invalid_values_delta,
            ],
            ["Records modified", "-", comparison.records_modified, "-"],
            ["Records removed", "-", comparison.records_removed, "-"],
        ]
        operation_rows: list[list[Any]] = [["Operation", "Status", "Summary"]]
        for step in comparison.steps:
            operation_rows.append([step.label, step.status, step.message])
        return [
            _p("Before vs after", styles["Subheading"]),
            _table(metric_rows, [60 * mm, 38 * mm, 38 * mm, 38 * mm], styles),
            _p("Cleaning and standardization summary", styles["Subheading"]),
            _table(operation_rows, [43 * mm, 25 * mm, 106 * mm], styles),
            _p("Comparison rules", styles["Subheading"]),
            *[_p(f"- {note}", styles["Muted"]) for note in comparison.comparison_notes],
        ]

    @staticmethod
    def _recommendations_section(report: AnalysisReport, styles: StyleSheet1) -> list[Any]:
        """Create the prioritized recommendation table.

        Args:
            report: Completed dataset analysis.
            styles: Active PDF styles.

        Returns:
            Recommendation-section flowables.

        Raises:
            No exceptions are raised for a validated report.
        """
        recommendations = report.features.recommendations
        if not recommendations:
            return [
                _p("No feature or quality recommendations were generated.", styles["BodySmall"])
            ]
        rows: list[list[Any]] = [["Priority", "Recommendation", "Columns", "Rationale"]]
        for item in recommendations[:MAX_PDF_RECOMMENDATIONS]:
            rows.append(
                [
                    item.severity,
                    f"{item.title}: {item.recommendation}",
                    ", ".join(item.columns) or item.column or "-",
                    item.rationale,
                ]
            )
        result: list[Any] = [_table(rows, [20 * mm, 67 * mm, 35 * mm, 52 * mm], styles)]
        omitted = len(recommendations) - MAX_PDF_RECOMMENDATIONS
        if omitted > 0:
            result.append(
                _p(
                    f"{omitted:,} additional recommendations are available in the JSON report.",
                    styles["Muted"],
                )
            )
        return result
