# Government Data Quality Framework Mapping

## Scope

ADIP uses six operational dimensions for explaining dataset-level quality:
Accuracy, Completeness, Consistency, Timeliness, Validity, and Uniqueness.

This is an ADIP mapping informed by Government of India data-quality guidance. It is not an
official DGQI assessment, Government of India approval, certification, or compliance claim.
DGQI is a broader institutional self-assessment covering data strategy, data systems, and
data-driven outcomes. Its methodology must be contextualized by the adopting organization.

## Authoritative references

- [DGQI 2.0 Methodology Toolkit](https://dmeo.gov.in/sites/default/files/2022-04/DGQI_2.0_Toolkit_28042022.pdf), Development Monitoring and Evaluation Office, NITI Aayog, April 2022.
- [DGQI Repository](https://www.dmeo.gov.in/en/content/dgqi-repository), Development Monitoring and Evaluation Office, NITI Aayog.

The DGQI data-quality theme includes documented quality-control mechanisms, automation,
missing and incorrect value checks, summary statistics and abnormalities, metadata checks,
duplicate detection, data integrity, and feedback or backcheck mechanisms.

## ADIP coverage

| Dimension | Automated ADIP coverage | External or manual requirements |
|---|---|---|
| Accuracy | Outliers, infinite values, non-numeric anomalies, summary statistics | Ground truth, authoritative sources, inspections, audits, and beneficiary backchecks |
| Completeness | Missing cells, empty columns, non-null coverage | Expected population, mandatory fields, and reporting-unit coverage |
| Consistency | Mixed types, inconsistent text formats, numeric values stored as text | Cross-system integrity, business rules, units, and controlled code lists |
| Timeliness | No automatic result without declared dates and frequency | Reporting period, update frequency, submission deadline, and cross-system recency |
| Validity | Type-level validity, numeric parsing, infinities, optional date/phone validation | Domain ranges, reference codes, identifiers, and owner-approved schema rules |
| Uniqueness | Exact duplicate rows, distinct counts, high-cardinality signals | Primary keys, fuzzy entity matching, and cross-dataset deduplication |

Each generated report includes detected automated findings separately from checks that require
reference data, organizational metadata, or human verification.
