import csv
import logging
from typing import ClassVar

import pandas as pd

from adip.exceptions import DatasetLoadError, EmptyDatasetError
from adip.loaders.base import BaseLoader

logger = logging.getLogger(__name__)


class CsvLoader(BaseLoader):
    format_name: ClassVar[str] = "csv"
    extensions: ClassVar[tuple[str, ...]] = (".csv",)

    def _detect_delimiter(self, encoding: str) -> str:
        with open(self.path, encoding=encoding, errors="replace", newline="") as fh:
            sample = fh.read(8192)
        try:
            return csv.Sniffer().sniff(sample, delimiters=",;\t|").delimiter
        except csv.Error:
            return ","

    def _read_chunks(self, encoding: str) -> pd.DataFrame:
        sep = self._detect_delimiter(encoding)
        max_rows = self.config.max_rows
        frames: list[pd.DataFrame] = []
        rows = 0
        reader = pd.read_csv(
            self.path,
            sep=sep,
            encoding=encoding,
            chunksize=self.config.chunk_size,
            low_memory=False,
        )
        with reader as chunks:
            for chunk in chunks:
                frames.append(chunk)
                rows += len(chunk)
                if max_rows and rows >= max_rows:
                    self.truncated = True  # there may be more rows in the file
                    break
        if not frames:
            raise EmptyDatasetError(f"{self.path.name} has a header but no data rows.")
        df = pd.concat(frames, ignore_index=True)
        return df.head(max_rows) if max_rows else df

    def _read(self) -> pd.DataFrame:
        for encoding in ("utf-8-sig", "latin-1"):
            try:
                return self._read_chunks(encoding)
            except UnicodeDecodeError:
                logger.warning("Encoding %s failed, trying next.", encoding)
            except pd.errors.EmptyDataError as exc:
                raise EmptyDatasetError(f"{self.path.name} has no parsable content.") from exc
            except pd.errors.ParserError as exc:
                raise DatasetLoadError(f"CSV parsing failed: {exc}") from exc
        raise DatasetLoadError(f"Could not decode {self.path.name} with a supported encoding.")