from typing import ClassVar

import pandas as pd

from adip.exceptions import DatasetLoadError
from adip.loaders.base import BaseLoader


class ExcelLoader(BaseLoader):
    format_name: ClassVar[str] = "xlsx"
    extensions: ClassVar[tuple[str, ...]] = (".xlsx",)

    def _read(self) -> pd.DataFrame:
        requested = self.sheet if self.sheet is not None else self.config.excel_sheet
        with pd.ExcelFile(self.path, engine="openpyxl") as workbook:
            names = [str(n) for n in workbook.sheet_names]
            if isinstance(requested, int):
                if not 0 <= requested < len(names):
                    raise DatasetLoadError(
                        f"Sheet index {requested} out of range. Available sheets: {names}"
                    )
                name = names[requested]
            elif requested in names:
                name = requested
            elif requested.isdigit() and int(requested) < len(names):
                name = names[int(requested)]
            else:
                raise DatasetLoadError(f"Sheet '{requested}' not found. Available sheets: {names}")
            self.sheet_name_used = name
            df = workbook.parse(name)
        if self.config.max_rows and len(df) > self.config.max_rows:
            self.truncated = True
            df = df.head(self.config.max_rows)
        return df