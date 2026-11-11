# Final Output Representation

## Dashboard

The existing React dashboard is the project's supported presentation layer. The Export tab now
provides a consolidated final-output view containing:

- dataset status, overall quality score, and grade;
- all six quality dimensions with evidence;
- detected issue summary;
- recommendations;
- latest cleaning and standardization audit;
- before-vs-after score and issue comparison;
- final dataset download;
- HTML, JSON, Excel, and PDF report downloads.

The final-dataset endpoint returns the latest approved standardized copy when available. If no
derived copy exists, it returns the preserved original upload. The original upload is never
overwritten.

## PDF report

The paginated PDF includes:

1. Dataset status and executive metrics.
2. Overall score and grade explanation.
3. Six quality dimensions, effective weights, evidence, and limitations.
4. Detected quality issues.
5. Cleaning and standardization summary when available.
6. Before-vs-after comparison when available.
7. Recommendations.
8. Final-dataset instructions and assessment limitations.
9. Selected analysis charts.

The PDF is generated atomically with page headers, page numbers, repeating table headers, bounded
issue and recommendation tables, and documented overflow references to JSON/Excel reports. After a
new standardization run, the PDF is regenerated with the latest comparison.

No LLM is used to generate dashboard or report content. All statements come from deterministic
analysis results and user-approved transformation audits.
