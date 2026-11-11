# Before vs After Cleaning Comparison

## Purpose

The comparison uses the immutable uploaded dataset as the original and the latest user-approved
cleaned or standardized output as the after state. It is generated automatically whenever the fix
engine creates a derived dataset.

## Displayed metrics

| Metric | Definition |
|---|---|
| Original quality score | Configured six-dimension score for the uploaded dataset |
| Cleaned quality score | The same scoring policy recalculated for the derived dataset |
| Missing values | Null cells across the complete dataset |
| Duplicate records | Exact full-row duplicates after the first occurrence |
| Invalid values | Detected numeric-as-text, invalid-type, mixed-type, infinite-value, and inconsistent-format rule violations |
| Records modified | Retained records whose values changed; schema or dtype changes mark every retained record as modified |
| Records removed | Original row count minus cleaned row count |

Invalid values are rule-violation occurrences rather than guaranteed distinct cells. A value that
breaks multiple rules can contribute to multiple findings. The dashboard displays this limitation
with the comparison.

## Record-change calculation

When schema and data types are unchanged, the engine compares multiplicities of deterministic row
hashes. This avoids treating reordered rows or removed duplicates as modified records. Removed rows
are reported separately and are not included in the modified count. If schema or data types change,
all retained rows are considered modified because their representation changed.

## Dashboard

The standardization result includes:

- original, cleaned, and score-delta cards;
- modified and removed record cards;
- original-versus-cleaned quality score chart;
- original-versus-cleaned issue-count chart;
- exact metric table and transparent comparison rules.

No LLM is used. All values are produced from deterministic profiles, quality findings, and the
approved transformation output.
