import pytest

from adip.exceptions import DatasetLoadError, EmptyDatasetError, UnsupportedFormatError
from adip.loaders import load_dataset


def test_csv_load(tmp_path, messy_df):
    path = tmp_path / "data.csv"
    messy_df.to_csv(path, index=False)
    loaded = load_dataset(path)
    assert loaded.info.file_format == "csv"
    assert loaded.info.rows_loaded == len(messy_df)
    assert loaded.info.columns_loaded == 7


def test_excel_load(tmp_path, messy_df):
    path = tmp_path / "data.xlsx"
    messy_df.to_excel(path, index=False)
    loaded = load_dataset(path)
    assert loaded.info.file_format == "xlsx"
    assert loaded.info.sheet_name is not None
    assert loaded.info.rows_loaded == len(messy_df)


def test_unsupported_format(tmp_path):
    path = tmp_path / "data.json"
    path.write_text("{}")
    with pytest.raises(UnsupportedFormatError):
        load_dataset(path)


def test_missing_file(tmp_path):
    with pytest.raises(DatasetLoadError):
        load_dataset(tmp_path / "nope.csv")


def test_header_only_csv(tmp_path):
    path = tmp_path / "empty.csv"
    path.write_text("a,b\n")
    with pytest.raises(EmptyDatasetError):
        load_dataset(path)