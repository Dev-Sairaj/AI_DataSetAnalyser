# ADIP Dataset Quality Assessment SOP

Version: 1.0

## Scope

This SOP governs CSV and XLSX assessment from upload through validation, profiling, quality
analysis, optional standardization, scoring, grading, and report generation. The same versioned
SOP is embedded in every generated JSON, HTML, and Excel report.

## Procedure

| Step | Stage | Purpose | Input | Method | Output | Testing criteria |
|---|---|---|---|---|---|---|
| 1 | Dataset upload | Create an isolated analysis job safely | CSV/XLSX upload | Sanitize filename, validate extension, stream in bounded chunks, enforce size limit | Original upload, job ID, sheets and preview columns | Valid files accepted; unsupported files return 415; oversized files return 413; no partial job remains |
| 2 | File validation | Confirm structural readability | Stored file and optional sheet | Validate existence, size and loader; parse selected content; reject empty/malformed data | Validated dataframe or explicit error | Missing, unsupported, header-only and invalid-sheet cases are rejected; dimensions match source |
| 3 | Data profiling | Establish a reproducible baseline | Validated dataframe | Measure shape, memory, types, missingness, uniqueness, duplicates and samples | Dataset and column profiles | Counts reconcile; every column is represented; duplicate count is reproducible |
| 4 | Quality checks | Detect issues through transparent rules | Dataframe, profile and configuration | Check missing values, duplicates, structure, types, formats, infinities and outliers; determine dataset status | Findings, evidence, severity and status | Injected defects are detected; critical findings produce Critical Issues; Clean requires zero findings |
| 5 | Standardization and cleaning | Apply approved transformations without altering the source | Original data and user selections | Copy data; run allow-listed text/date/phone/scaling operations; protect target; audit every step | Separate standardized file and change log | Original remains unchanged; normalization and scaling produce expected values; invalid values are retained and reported |
| 6 | Quality score calculation | Calculate a repeatable 0–100 score | Profile, findings and outliers | Calculate subscores and weighted total; repeat after cleaning | Overall score and breakdown | All values stay in range; repeated input gives identical score; weighted calculation reconciles |
| 7 | Quality grading | Convert score to a user-friendly grade | Overall score | Apply A ≥ 90, B ≥ 80, C ≥ 70, D ≥ 60, otherwise F | Grade A–F | Threshold boundaries are tested and grade always derives from score |
| 8 | Final report generation | Deliver traceable results | All assessment artifacts | Validate report contract and generate dashboard, JSON, HTML and Excel outputs | Non-empty reports and controlled downloads | JSON validates; HTML includes required sections; workbook opens with expected sheets; incomplete jobs cannot download results |

## Control principles

- The original uploaded file is immutable.
- Automated rules and their thresholds are visible to users.
- Cleaning is user-triggered and allow-listed.
- Every transformation produces an audit result.
- External/manual checks are distinguished from automated checks.
- Report formats must represent the same validated analysis contract.
