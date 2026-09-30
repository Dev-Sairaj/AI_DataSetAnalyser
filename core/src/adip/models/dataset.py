from pydantic import BaseModel


class DatasetInfo(BaseModel):
    name: str
    source_path: str | None = None
    file_format: str
    file_size_bytes: int = 0
    sheet_name: str | None = None
    rows_loaded: int
    columns_loaded: int
    truncated: bool = False  # True if max_rows cut the file short