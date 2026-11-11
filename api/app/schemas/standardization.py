"""Request and response contracts for deterministic dataset standardization."""

from typing import Literal

from adip.fixes import FixReport
from pydantic import BaseModel, Field

TextCase = Literal["preserve", "lower", "upper", "title"]
ScalingMethod = Literal["none", "minmax", "zscore"]


class StandardizeRequest(BaseModel):
    """User-approved standardization operations for one completed analysis job."""

    text_columns: list[str] = Field(default_factory=list)
    text_case: TextCase = "preserve"
    date_columns: list[str] = Field(default_factory=list)
    date_format: str = "%Y-%m-%d"
    dayfirst: bool = False
    phone_columns: list[str] = Field(default_factory=list)
    phone_country_code: str = "91"
    numeric_columns: list[str] = Field(default_factory=list)
    scaling_method: ScalingMethod = "none"

    def has_operations(self) -> bool:
        """Return whether the request contains at least one executable operation."""
        return bool(
            self.text_columns
            or self.date_columns
            or self.phone_columns
            or (self.numeric_columns and self.scaling_method != "none")
        )


class StandardizationResponse(BaseModel):
    """Audit result and download metadata for a standardized dataset copy."""

    file_format: Literal["csv", "xlsx"]
    download_name: str
    report: FixReport
