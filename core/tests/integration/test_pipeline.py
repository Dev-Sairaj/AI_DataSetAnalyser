import json

import openpyxl
import pytest

from adip import ADIP
from adip.exceptions import ReportExportError, TargetColumnError


@pytest.fixture
def csv_path(tmp_path, messy_df):
    path = tmp_path / "data.csv"
    messy_df.to_csv(path, index=False)
    return path


def test_end_to_end_exports(csv_path, tmp_path):
    adip = ADIP(csv_path)
    report = adip.run()
    assert report.profile.n_rows == 202

    files = adip.export(tmp_path / "out")
    assert set(files) == {"html", "json", "excel"}
    assert all(p.exists() and p.stat().st_size > 0 for p in files.values())

    html = files["html"].read_text(encoding="utf-8")
    assert "data.csv" in html and "data:image/png;base64" in html

    data = json.loads(files["json"].read_text(encoding="utf-8"))
    assert data["profile"]["n_rows"] == 202

    wb = openpyxl.load_workbook(files["excel"])
    assert {"Summary", "Profile", "Recommendations"} <= set(wb.sheetnames)


def test_progress_callback(csv_path):
    calls = []
    ADIP(csv_path).run(lambda msg, frac: calls.append(frac))
    assert calls[0] < calls[-1] == 1.0


def test_invalid_target(csv_path):
    with pytest.raises(TargetColumnError):
        ADIP(csv_path, target="nope").run()


def test_unknown_format(csv_path, tmp_path):
    with pytest.raises(ReportExportError):
        ADIP(csv_path).export(tmp_path, formats=["pdf"])