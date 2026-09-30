from pathlib import Path

from adip.config import LoaderConfig
from adip.exceptions import UnsupportedFormatError
from adip.loaders.base import BaseLoader, LoadedDataset
from adip.loaders.csv_loader import CsvLoader
from adip.loaders.excel_loader import ExcelLoader

_LOADERS: dict[str, type[BaseLoader]] = {
    ext: cls for cls in (CsvLoader, ExcelLoader) for ext in cls.extensions
}


def supported_extensions() -> list[str]:
    return sorted(_LOADERS)


def get_loader(
    path: str | Path,
    config: LoaderConfig | None = None,
    sheet: str | int | None = None,
) -> BaseLoader:
    ext = Path(path).suffix.lower()
    loader_cls = _LOADERS.get(ext)
    if loader_cls is None:
        raise UnsupportedFormatError(
            f"Unsupported file type '{ext or '(none)'}'. Supported: {', '.join(supported_extensions())}"
        )
    return loader_cls(path, config, sheet)


def load_dataset(
    path: str | Path,
    config: LoaderConfig | None = None,
    sheet: str | int | None = None,
) -> LoadedDataset:
    return get_loader(path, config, sheet).load()