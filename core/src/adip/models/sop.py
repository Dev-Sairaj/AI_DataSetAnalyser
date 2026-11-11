"""Versioned contracts for the dataset quality assessment SOP."""

from typing import Literal

from pydantic import BaseModel, Field

AutomationMode = Literal["automatic", "user_triggered", "automatic_and_user_triggered"]


class SOPStage(BaseModel):
    """Documented contract for one assessment stage."""

    step: int
    name: str
    purpose: str
    input: str
    method: str
    output: str
    automation: AutomationMode
    testing_criteria: list[str] = Field(default_factory=list)


class AssessmentSOP(BaseModel):
    """Complete versioned Standard Operating Procedure included with each report."""

    title: str
    version: str
    scope: str
    stages: list[SOPStage]
