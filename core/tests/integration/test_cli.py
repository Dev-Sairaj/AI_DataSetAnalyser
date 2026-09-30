from typer.testing import CliRunner

from adip.cli import app

runner = CliRunner()


def test_cli_analyze(tmp_path, messy_df):
    src = tmp_path / "data.csv"
    messy_df.to_csv(src, index=False)
    out = tmp_path / "out"
    result = runner.invoke(app, ["analyze", str(src), "-o", str(out), "-f", "json", "-f", "html"])
    assert result.exit_code == 0, result.output
    assert (out / "data_adip_report.json").exists()
    assert (out / "data_adip_report.html").exists()


def test_cli_unsupported_file(tmp_path):
    bad = tmp_path / "data.json"
    bad.write_text("{}")
    result = runner.invoke(app, ["analyze", str(bad)])
    assert result.exit_code == 1


def test_cli_version():
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0 and "ADIP" in result.output