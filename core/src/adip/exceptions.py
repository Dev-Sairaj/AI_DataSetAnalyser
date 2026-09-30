"""Custom exceptions so callers get meaningful, catchable errors."""


class ADIPError(Exception):
    """Base class for all ADIP errors."""


class UnsupportedFormatError(ADIPError):
    """The file extension is not supported."""


class DatasetLoadError(ADIPError):
    """The dataset could not be read."""


class EmptyDatasetError(ADIPError):
    """The dataset contains no usable rows or columns."""


class ConfigError(ADIPError):
    """Configuration is missing or invalid."""


class ReportExportError(ADIPError):
    """A report could not be generated or written."""



class TargetColumnError(ADIPError):
    """The requested target column does not exist in the dataset."""