from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from adip import __version__
from adip.exceptions import ADIPError
from adip.logging_config import setup_logging
from adip.pipeline import DEFAULT_FORMATS, ADIP
from adip.reporting import available_formats, get_exporter

app = typer.Typer(help="AI Dataset Intelligence Platform: automated dataset analysis.", no_args_is_help=True)
console = Console()
err_console = Console(stderr=True)


@app.command()
def analyze(
    file: Annotated[Path, typer.Argument(exists=True, dir_okay=False, help="CSV or XLSX file.")],
    output: Annotated[Path, typer.Option("--output", "-o", help="Output folder.")] = Path("adip_output"),
    formats: Annotated[
        list[str] | None,
        typer.Option("--format", "-f", help=f"html, json, excel. Repeatable. Default: all. ({', '.join(available_formats())})"),
    ] = None,
    target: Annotated[str | None, typer.Option("--target", "-t", help="Optional target column.")] = None,
    sheet: Annotated[str | None, typer.Option("--sheet", help="Excel sheet name or index.")] = None,
    config: Annotated[Path | None, typer.Option("--config", "-c", exists=True, dir_okay=False, help="YAML config overrides.")] = None,
    verbose: Annotated[bool, typer.Option("--verbose", "-v")] = False,
) -> None:
    """Analyze a dataset and write HTML / JSON / Excel reports."""
    setup_logging("DEBUG" if verbose else "WARNING")
    chosen = formats or list(DEFAULT_FORMATS)
    try:
        for name in chosen:  # fail fast on a bad format, before the analysis runs
            get_exporter(name)
        adip = ADIP(file, config=config, sheet=sheet, target=target)
        with console.status("Starting...") as status:
            report = adip.run(lambda msg, frac: status.update(f"[bold]{msg}[/] ({frac:.0%})"))
            status.update("Writing reports...")
            files = adip.export(output, chosen)
    except ADIPError as exc:
        err_console.print(f"[bold red]Error:[/] {exc}")
        raise typer.Exit(code=1) from exc

    q = report.quality
    table = Table(title=report.dataset.name, show_header=False)
    table.add_row("Rows x columns", f"{report.profile.n_rows:,} x {report.profile.n_cols}")
    table.add_row("Quality", f"{q.grade} ({q.score}/100)")
    table.add_row("Issues", f"{len(q.issues)}")
    table.add_row("Recommendations", f"{len(report.features.recommendations)}")
    console.print(table)
    for fmt, path in files.items():
        console.print(f"[green]{fmt:>6}[/]  {path}")


@app.command()
def version() -> None:
    """Show the ADIP version."""
    console.print(f"ADIP {__version__}")