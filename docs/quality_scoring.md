# Configurable Data Quality Scoring

## Output

Every uploaded dataset receives:

- six dimension assessments: Accuracy, Completeness, Consistency, Timeliness, Validity, and Uniqueness;
- an overall score from 0 to 100;
- a grade from A to F;
- formulas, evidence, limitations, configured weights, and effective weights.

An unassessed dimension has no score and an effective weight of zero. Its configured weight is
proportionally redistributed across assessed dimensions. This prevents unsupported values from
being invented while keeping the overall result on a 0-100 scale.

## Dimension formulas

| Dimension | Automated formula | Limitation |
|---|---|---|
| Accuracy | `100 - min(100, average numeric outlier % x 5)` | An anomaly proxy only. Factual correctness requires trusted reference data or manual verification. |
| Completeness | `100 - missing cell %` | Measures populated cells, not whether all required business fields exist. |
| Consistency | Percentage of columns without mixed-type or inconsistent text-format findings | Cross-system and semantic consistency require external context. |
| Timeliness | Not assessed without reporting-period or freshness metadata | File timestamps are not treated as authoritative freshness evidence. |
| Validity | Percentage of columns without invalid-type or infinite-value findings | Domain rules and reference registries require configuration or external data. |
| Uniqueness | `100 - duplicate row %` | Business-key uniqueness requires a declared key. |

The overall score is:

`sum(dimension score x effective weight)`

## Default weights and rationale

| Dimension | Configured weight |
|---|---:|
| Accuracy | 20% |
| Completeness | 20% |
| Consistency | 15% |
| Timeliness | 10% |
| Validity | 20% |
| Uniqueness | 15% |

Accuracy, Completeness, and Validity receive 20% each because they directly affect whether data is
trustworthy and usable. Consistency and Uniqueness receive 15% each because structural conflicts
and duplication materially affect analysis. Timeliness reserves 10% for future metadata-aware
assessment but is redistributed when it cannot be assessed.

## Default grade thresholds

- A: score >= 90
- B: 80 <= score < 90
- C: 70 <= score < 80
- D: 60 <= score < 70
- F: score < 60

Thresholds are inclusive at the lower boundary and must remain strictly descending.

## Configuration

```yaml
scoring:
  weights:
    accuracy: 0.20
    completeness: 0.20
    consistency: 0.15
    timeliness: 0.10
    validity: 0.20
    uniqueness: 0.15
  thresholds:
    a: 90.0
    b: 80.0
    c: 70.0
    d: 60.0
  unassessed_dimension_policy: renormalize
```

Weights are relative and do not need to total 1. At least one always-assessed dimension must have a
positive weight. This scoring model is an operational assessment, not a Government of India or
DGQI approval, audit, or certification.
