# ADIP Project and Feature Guide

## 1. Project overview

ADIP (AI Dataset Intelligence Platform) analyses uploaded CSV and XLSX datasets. It profiles the
data, detects quality problems, calculates transparent quality scores, recommends improvements,
creates a separate standardized dataset, and generates downloadable reports.

The application uses:

- **Core:** Python, pandas, scikit-learn, Pydantic and ReportLab.
- **API:** FastAPI with isolated file storage per analysis job.
- **Dashboard:** React, TypeScript, Tailwind CSS and Recharts.
- **AI/LLM:** Not required for the implemented quality, scoring, cleaning or reporting features.

## 2. Main architecture

| Area | Purpose | Main location |
|---|---|---|
| Core library | Loading, profiling, quality, EDA, recommendations and reports | `core/src/adip/` |
| API | Uploads, background jobs, results and downloads | `api/app/` |
| Dashboard | User workflow and visual results | `web/src/` |
| Tests | Core and API regression tests | `core/tests/`, `api/tests/` |
| Documentation | SOP, scoring, government mapping and feature guides | `docs/` |

## 3. Quick start

From the project root on Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".\core[dev]" -e ".\api[dev]"
npm --prefix web install
```

Start the API:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --app-dir api
```

Start the dashboard in another terminal:

```powershell
npm --prefix web run dev
```

Open `http://localhost:5173`.

## 4. Normal user workflow

1. Upload a CSV or XLSX dataset.
2. Select an Excel sheet and optional ML target column.
3. Run analysis and review Overview, Data Quality, EDA and Feature Guidance.
4. Review the SOP and government-framework mapping.
5. Open Standardize, select approved transformations and create a separate output.
6. Review the before-vs-after comparison.
7. Open Export to download the final dataset and HTML, JSON, Excel or PDF reports.

The original uploaded file is preserved. Cleaning and standardization always produce a separate
derived file.

## 5. Feature reference

| Feature | Why it exists | How to use or check | Main implementation files |
|---|---|---|---|
| Upload and file validation | Reject unsupported, empty, malformed or oversized files safely | Upload CSV/XLSX; invalid files show a clear error | `core/src/adip/loaders/`, `api/app/routers/datasets.py`, `api/app/services/analysis_service.py` |
| Dataset profiling | Establish rows, columns, types, missing cells, unique values and duplicates | Review the Overview tab and column profile table | `core/src/adip/profiling/`, `core/src/adip/models/profile.py`, `web/src/pages/OverviewPage.tsx` |
| Clean vs unclean identification | Prevent datasets with hidden format, type or duplicate problems from being marked clean | Review **Clean**, **Needs Cleaning** or **Critical Issues** and the displayed status rules | `core/src/adip/quality/engine.py`, `core/src/adip/quality/status.py`, `web/src/pages/QualityPage.tsx` |
| Quality checks | Detect missing values, duplicates, empty/constant columns, wrong or mixed types, infinities, inconsistent text and outliers | Review findings in Data Quality; filter by severity | `core/src/adip/quality/engine.py`, `core/src/adip/quality/outliers.py`, `core/src/adip/models/quality.py` |
| Six-dimension scoring | Provide a reproducible 0-100 score instead of an unexplained judgement | Review Accuracy, Completeness, Consistency, Timeliness, Validity and Uniqueness in Data Quality | `core/src/adip/quality/scoring.py`, `core/src/adip/config/settings.py`, `web/src/components/charts/ScoreCard.tsx` |
| Configurable grades | Convert the overall score into A, B, C, D or F using documented thresholds | Change `scoring.weights` or `scoring.thresholds` in YAML and rerun analysis | `core/src/adip/config/default_config.yaml`, `core/src/adip/quality/scoring.py`, `docs/quality_scoring.md` |
| Government/DGQI mapping | Explain how automated checks relate to Government of India quality dimensions without claiming certification | Review the government mapping in Data Quality and reports | `core/src/adip/quality/government_mapping.py`, `core/src/adip/models/governance.py`, `docs/government_data_quality_mapping.md` |
| SOP assessment | Give the team a repeatable upload-to-report operating procedure and test criteria | Open Assessment SOP in the dashboard or exported reports | `core/src/adip/sop.py`, `core/src/adip/models/sop.py`, `web/src/pages/SopPage.tsx`, `docs/data_quality_sop.md` |
| EDA and charts | Help users understand distributions, categories, correlation and outliers | Open Exploratory Analysis after a job completes | `core/src/adip/eda/`, `core/src/adip/visualization/`, `web/src/pages/EdaPage.tsx` |
| Feature guidance | Suggest encoding, scaling, imputation, target handling and redundant-column actions | Select a target during analysis and open Feature Guidance | `core/src/adip/features/`, `core/src/adip/models/features.py`, `web/src/pages/FeaturesPage.tsx` |
| Standardization engine | Normalize text, dates and phone numbers and optionally scale numerical features | Select columns and operations in Standardize, then create the derived dataset | `core/src/adip/fixes/`, `api/app/services/standardization_service.py`, `web/src/pages/StandardizePage.tsx` |
| Before-vs-after comparison | Prove what improved and disclose records modified or removed | Create a standardized dataset and review the comparison cards, charts and table | `core/src/adip/fixes/engine.py`, `core/src/adip/fixes/plan.py`, `web/src/components/charts/BeforeAfterComparison.tsx` |
| Final output and downloads | Provide one consolidated result for technical and non-technical users | Open Export and download the final dataset or HTML/JSON/Excel/PDF report | `core/src/adip/reporting/`, `api/app/routers/reports.py`, `api/app/routers/standardization.py`, `web/src/pages/ExportPage.tsx` |
| PDF report refresh | Ensure the PDF represents the latest approved derived dataset | Download PDF before and after standardization; the later PDF includes comparison details | `core/src/adip/reporting/pdf_exporter.py`, `api/app/services/standardization_service.py` |

## 6. Important scoring behavior

- A dataset is **Clean** only when every implemented automated check passes.
- Timeliness is **Not assessed** without trusted reporting-period or freshness metadata.
- Accuracy is an anomaly-based proxy; factual correctness needs reference data or manual review.
- Unassessed dimension weights are redistributed across assessed dimensions.
- Default grades are A >= 90, B >= 80, C >= 70, D >= 60 and F < 60.
- Government mapping is informational and is not government approval or DGQI certification.

## 7. Configuration

Default configuration is in `core/src/adip/config/default_config.yaml`. It controls:

- upload and row limits;
- missing-value and outlier thresholds;
- scoring weights and grade thresholds;
- EDA limits;
- feature-recommendation thresholds;
- cleaning safety limits.

API environment settings are defined in `api/app/core/config.py`, including storage location,
maximum upload size, concurrency, job lifetime, CORS and logging.

## 8. Storage and safety

- Each upload receives a generated job ID and an isolated folder under `api/storage/jobs/`.
- Original uploads are never overwritten by transformations.
- The final-dataset endpoint returns the latest approved standardized copy; otherwise it returns
  the preserved original.
- Job IDs are validated to prevent path traversal.
- Old jobs are removed according to the configured job lifetime.

## 9. Verification commands

```powershell
.\.venv\Scripts\python.exe -m pytest core/tests -q
.\.venv\Scripts\python.exe -m pytest api/tests -q
npm --prefix web run build
```

Expected current result: **65 core tests**, **10 API tests**, and a successful frontend production
build.

## 10. Supporting documents

- `docs/data_quality_sop.md`
- `docs/government_data_quality_mapping.md`
- `docs/quality_scoring.md`
- `docs/before_after_comparison.md`
- `docs/final_output_representation.md`
