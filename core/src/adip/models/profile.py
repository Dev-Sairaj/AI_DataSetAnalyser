from typing import Literal

from pydantic import BaseModel

ColumnKind = Literal["numeric", "categorical", "boolean", "datetime", "text", "empty"]


class ColumnProfile(BaseModel):
    name: str
    dtype: str
    kind: ColumnKind
    non_null: int
    missing: int
    missing_pct: float
    unique: int
    unique_pct: float  # unique / non-null * 100
    memory_bytes: int
    sample_values: list[str]


class DatasetProfile(BaseModel):
    n_rows: int
    n_cols: int
    memory_bytes: int
    total_cells: int
    total_missing: int
    missing_pct: float
    duplicate_rows: int
    duplicate_pct: float
    columns: list[ColumnProfile]

    def names_of_kind(self, *kinds: str) -> list[str]:
        return [c.name for c in self.columns if c.kind in kinds]