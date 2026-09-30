"""Loader interface. New formats (JSON, Parquet, SQL) plug in by subclassing BaseLoader."""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

import pandas as pd

from adip.config import LoaderConfig
from adip.exceptions import ADIPError, DatasetLoadError, EmptyDatasetError
from adip.models.dataset import DatasetInfo

logger = logging.getLogger(__name__)


@dataclass
class LoadedDataset:
    df: pd.DataFrame
    info: DatasetInfo


class BaseLoader(ABC):
    format_name: ClassVar[str]
    extensions: ClassVar[tuple[str, ...]]

    def __init__(
        self,
        path: str | Path,
        config: LoaderConfig | None = None,
        sheet: str | int | None = None,
    ) -> None:
        self.path = Path(path)
        self.config = config or LoaderConfig()
        self.sheet = sheet
        self.sheet_name_used: str | None = None
        self.truncated = False

    def validate_file(self) -> None:
        if not self.path.exists():
            raise DatasetLoadError(f"File not found: {self.path}")
        if not self.path.is_file():
            raise DatasetLoadError(f"Not a file: {self.path}")
        size = self.path.stat().st_size
        if size == 0:
            raise EmptyDatasetError(f"File is empty: {self.path.name}")
        limit = self.config.max_file_size_mb * 1024 * 1024
        if size > limit:
            raise DatasetLoadError(
                f"{self.path.name} is {size / 1024 / 1024:.0f} MB, above the "
                f"{self.config.max_file_size_mb} MB limit."
            )

    @abstractmethod
    def _read(self) -> pd.DataFrame:
        """Read the file into a DataFrame."""

    def load(self) -> LoadedDataset:
        self.validate_file()
        logger.info("Loading %s (%s)", self.path.name, self.format_name)
        try:
            df = self._read()
        except ADIPError:
            raise
        except Exception as exc:
            raise DatasetLoadError(f"Could not read {self.path.name}: {exc}") from exc

        df.columns = [str(c) for c in df.columns]
        if df.shape[0] == 0 or df.shape[1] == 0:
            raise EmptyDatasetError(f"{self.path.name} contains no data rows or columns.")

        info = DatasetInfo(
            name=self.path.name,
            source_path=str(self.path.resolve()),
            file_format=self.format_name,
            file_size_bytes=self.path.stat().st_size,
            sheet_name=self.sheet_name_used,
            rows_loaded=int(df.shape[0]),
            columns_loaded=int(df.shape[1]),
            truncated=self.truncated,
        )
        logger.info("Loaded %d rows x %d columns", info.rows_loaded, info.columns_loaded)
        return LoadedDataset(df=df, info=info)