"""Public data-fix and standardization API."""

from adip.fixes import builtin as _builtin
from adip.fixes.engine import FixEngine, FixOutcome
from adip.fixes.plan import FixPlan, FixReport, FixStep, FixStepResult, QualityScore
from adip.fixes.registry import fix_catalog, get_fix, list_fixes, register_fix

__all__ = [
    "FixEngine",
    "FixOutcome",
    "FixPlan",
    "FixReport",
    "FixStep",
    "FixStepResult",
    "QualityScore",
    "fix_catalog",
    "get_fix",
    "list_fixes",
    "register_fix",
]

# Importing builtin registers the approved deterministic operations.
_ = _builtin
