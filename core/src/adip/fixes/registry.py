"""Fix registry. Every fix is a function ``fn(df, cols, params) -> (df, log_message)``.

Add a fix by decorating a function with ``@register_fix``. Plans, the rule builder
and the AI planner can only ever name fixes that exist here, so this is the whole
surface the pipeline (and any LLM) is allowed to touch.

Contract for a fix function:
  * ``df`` is already a private copy; it may be modified and returned.
  * Compute new values first, then assign, so a failure leaves ``df`` intact.
  * ``cols`` only holds columns that exist and are allowed (target is filtered out
    by the engine). ``params`` has config defaults already merged in.
  * Raise ``FixSkipped("why")`` when there is nothing to do.
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any

import pandas as pd

from adip.exceptions import UnknownFixError
from adip.fixes.plan import FixPlan


class Stage(IntEnum):
    """Execution order: drop, types, impute, outliers, transform, encode, scale."""

    DROP = 10
    TYPES = 20
    IMPUTE = 30
    OUTLIERS = 40
    TRANSFORM = 50
    ENCODE = 60
    SCALE = 70


class FixSkipped(Exception):
    """Raised by a fix when it has nothing to do. The step is reported as skipped."""


FixFn = Callable[[pd.DataFrame, list[str], dict[str, Any]], tuple[pd.DataFrame, str]]


@dataclass(frozen=True)
class FixSpec:
    name: str
    fn: FixFn
    order: int
    label: str
    description: str
    needs_columns: bool = True
    changes_rows: bool = False
    params: dict[str, str] = field(default_factory=dict)  # accepted params -> short doc

    @property
    def stage(self) -> str:
        try:
            return Stage((self.order // 10) * 10).name.lower()
        except ValueError:
            return "custom"

    def describe(self) -> dict[str, Any]:
        """JSON-friendly summary. The AI planner is shown exactly this."""
        return {
            "name": self.name,
            "label": self.label,
            "description": self.description,
            "stage": self.stage,
            "needs_columns": self.needs_columns,
            "changes_rows": self.changes_rows,
            "params": self.params,
        }


_REGISTRY: dict[str, FixSpec] = {}


def register_fix(
    name: str,
    *,
    order: int,
    label: str,
    description: str,
    needs_columns: bool = True,
    changes_rows: bool = False,
    params: dict[str, str] | None = None,
) -> Callable[[FixFn], FixFn]:
    def decorator(fn: FixFn) -> FixFn:
        if name in _REGISTRY:
            raise ValueError(f"Fix '{name}' is already registered.")
        _REGISTRY[name] = FixSpec(
            name=name,
            fn=fn,
            order=int(order),
            label=label,
            description=description,
            needs_columns=needs_columns,
            changes_rows=changes_rows,
            params=params or {},
        )
        return fn

    return decorator


def get_fix(name: str) -> FixSpec:
    spec = _REGISTRY.get(name)
    if spec is None:
        raise UnknownFixError(f"Unknown fix '{name}'. Available: {', '.join(sorted(_REGISTRY))}")
    return spec


def list_fixes() -> list[FixSpec]:
    return sorted(_REGISTRY.values(), key=lambda s: (s.order, s.name))


def fix_catalog() -> list[dict[str, Any]]:
    return [spec.describe() for spec in list_fixes()]


def validate_plan(plan: FixPlan) -> None:
    """Reject plans naming fixes that do not exist. Column names are checked at run time."""
    for step in plan.steps:
        get_fix(step.fix)