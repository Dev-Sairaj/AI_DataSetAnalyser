// Mirrors the Pydantic models in core/src/adip/models and api/app/schemas.

export type JobStatus = "uploaded" | "queued" | "running" | "completed" | "failed";
export type ColumnKind = "numeric" | "categorical" | "boolean" | "datetime" | "text" | "empty";
export type Severity = "info" | "warning" | "critical";
export type DatasetStatus = "Clean" | "Needs Cleaning" | "Critical Issues";
export type ExportFormat = "html" | "json" | "excel" | "pdf";
export type TextCase = "preserve" | "lower" | "upper" | "title";
export type ScalingMethod = "none" | "minmax" | "zscore";

export interface JobRecord {
  job_id: string;
  status: JobStatus;
  progress: number;
  message: string;
  error: string | null;
  filename: string;
  file_format: string;
  file_size_bytes: number;
  target: string | null;
  sheet: string | null;
  created_at: string;
  updated_at: string;
  started_at: string | null;
  finished_at: string | null;
  available_downloads: ExportFormat[];
}

export interface ColumnInfo {
  name: string;
  kind: ColumnKind;
}

export interface InspectResponse {
  sheets: string[];
  columns: ColumnInfo[];
}

export interface UploadResponse extends InspectResponse {
  job: JobRecord;
}

export interface RunRequest {
  target: string | null;
  sheet: string | null;
}

export interface DatasetInfo {
  name: string;
  source_path: string | null;
  file_format: string;
  file_size_bytes: number;
  sheet_name: string | null;
  rows_loaded: number;
  columns_loaded: number;
  truncated: boolean;
}

export interface ColumnProfile {
  name: string;
  dtype: string;
  kind: ColumnKind;
  non_null: number;
  missing: number;
  missing_pct: number;
  unique: number;
  unique_pct: number;
  memory_bytes: number;
  sample_values: string[];
}

export interface DatasetProfile {
  n_rows: number;
  n_cols: number;
  memory_bytes: number;
  total_cells: number;
  total_missing: number;
  missing_pct: number;
  duplicate_rows: number;
  duplicate_pct: number;
  columns: ColumnProfile[];
}

export interface QualityIssue {
  code: string;
  severity: Severity;
  column: string | null;
  message: string;
  affected_count: number;
  affected_pct: number;
  details: Record<string, unknown>;
}

export interface OutlierSummary {
  column: string;
  method: string;
  count: number;
  pct: number;
  lower_bound: number | null;
  upper_bound: number | null;
}

export interface StatusRuleResult {
  name: DatasetStatus;
  condition: string;
  triggered: boolean;
  evidence: string;
}

export type QualityDimensionName =
  | "Accuracy"
  | "Completeness"
  | "Consistency"
  | "Timeliness"
  | "Validity"
  | "Uniqueness";

export type DimensionAssessment = "automated" | "proxy" | "not_assessed";

export interface DimensionScore {
  name: QualityDimensionName;
  score: number | null;
  assessment: DimensionAssessment;
  configured_weight: number;
  effective_weight: number;
  formula: string;
  evidence: string;
  limitation: string | null;
}

export interface QualityReport {
  score: number;
  grade: string;
  status: DatasetStatus;
  status_summary: string;
  status_rules: StatusRuleResult[];
  score_breakdown: Record<string, number>;
  dimension_scores: DimensionScore[];
  score_explanation: string;
  grade_explanation: string;
  grading_thresholds: Record<string, number>;
  issues: QualityIssue[];
  outliers: OutlierSummary[];
}

export interface NumericStats {
  column: string;
  count: number;
  mean: number | null;
  std: number | null;
  min: number | null;
  q1: number | null;
  median: number | null;
  q3: number | null;
  max: number | null;
  iqr: number | null;
  skewness: number | null;
  kurtosis: number | null;
  n_zero: number;
  n_negative: number;
  shape: string;
}

export interface HistogramData {
  column: string;
  bin_edges: number[];
  counts: number[];
  clipped_count: number;
}

export interface BoxPlotData {
  column: string;
  whisker_low: number;
  q1: number;
  median: number;
  q3: number;
  whisker_high: number;
  n_outliers: number;
  outlier_values: number[];
}

export interface CategoryCount {
  value: string;
  count: number;
  pct: number;
}

export interface CategoricalStats {
  column: string;
  unique: number;
  mode: string;
  mode_pct: number;
  top_values: CategoryCount[];
  other_count: number;
  other_pct: number;
}

export interface CorrelationPair {
  column_a: string;
  column_b: string;
  coefficient: number;
}

export interface CorrelationResult {
  method: string;
  columns: string[];
  matrix: (number | null)[][];
  high_pairs: CorrelationPair[];
  threshold: number;
  n_rows_used: number;
  sampled: boolean;
  columns_truncated: boolean;
}

export interface EdaReport {
  numeric: NumericStats[];
  categorical: CategoricalStats[];
  histograms: HistogramData[];
  boxplots: BoxPlotData[];
  correlation: CorrelationResult | null;
}

export type RecCategory =
  | "data_types"
  | "missing_values"
  | "encoding"
  | "scaling"
  | "low_value"
  | "redundancy"
  | "target";

export interface Recommendation {
  category: RecCategory;
  severity: Severity;
  column: string | null;
  columns: string[];
  title: string;
  recommendation: string;
  rationale: string;
}

export interface FeatureSignal {
  column: string;
  score: number;
}

export interface TargetAnalysis {
  column: string;
  task: "classification" | "regression";
  n_classes: number | null;
  class_balance: CategoryCount[];
  imbalance_ratio: number | null;
  signal_metric: string;
  signals: FeatureSignal[];
  notes: string[];
}

export interface FeatureReport {
  recommendations: Recommendation[];
  target: TargetAnalysis | null;
}

export type GovernmentCoverage =
  | "implemented"
  | "partially_implemented"
  | "external_or_manual";

export interface GovernmentFrameworkReference {
  title: string;
  publisher: string;
  url: string;
  relevance: string;
}

export interface GovernmentQualityDimension {
  name: "Accuracy" | "Completeness" | "Consistency" | "Timeliness" | "Validity" | "Uniqueness";
  coverage: GovernmentCoverage;
  explanation: string;
  implemented_checks: string[];
  external_or_manual_checks: string[];
  detected_issue_count: number;
  detected_issue_codes: string[];
}

export interface GovernmentFrameworkMapping {
  framework_name: string;
  mapping_name: string;
  disclaimer: string;
  references: GovernmentFrameworkReference[];
  dimensions: GovernmentQualityDimension[];
}

export type SOPAutomation = "automatic" | "user_triggered" | "automatic_and_user_triggered";

export interface SOPStage {
  step: number;
  name: string;
  purpose: string;
  input: string;
  method: string;
  output: string;
  automation: SOPAutomation;
  testing_criteria: string[];
}

export interface AssessmentSOP {
  title: string;
  version: string;
  scope: string;
  stages: SOPStage[];
}

export interface MissingBar {
  column: string;
  missing: number;
  missing_pct: number;
}

export interface ChartData {
  histograms: HistogramData[];
  boxplots: BoxPlotData[];
  correlation: CorrelationResult | null;
  category_frequencies: Record<string, CategoryCount[]>;
  missing: MissingBar[];
}

export interface AnalysisReport {
  adip_version: string;
  generated_at: string;
  dataset: DatasetInfo;
  target: string | null;
  profile: DatasetProfile;
  quality: QualityReport;
  eda: EdaReport;
  features: FeatureReport;
  government_framework: GovernmentFrameworkMapping;
  sop: AssessmentSOP;
  charts: ChartData;
  config: Record<string, unknown>;
}

export interface StandardizeRequest {
  text_columns: string[];
  text_case: TextCase;
  date_columns: string[];
  date_format: string;
  dayfirst: boolean;
  phone_columns: string[];
  phone_country_code: string;
  numeric_columns: string[];
  scaling_method: ScalingMethod;
}

export interface FixStepResult {
  step_id: string;
  fix: string;
  label: string;
  status: "applied" | "skipped" | "failed";
  message: string;
  columns: string[];
  ignored_columns: string[];
  params: Record<string, unknown>;
  rows_before: number;
  rows_after: number;
  cols_before: number;
  cols_after: number;
  warning: string | null;
}

export interface StandardizationQualityScore {
  score: number;
  grade: string;
  status: DatasetStatus | null;
  issues: number;
  issue_details: QualityIssue[];
  breakdown: Record<string, number>;
  dimensions: DimensionScore[];
  score_explanation: string;
  grade_explanation: string;
  missing_values: number;
  duplicate_records: number;
  invalid_values: number;
}

export interface FixReport {
  generated_at: string;
  target: string | null;
  steps: FixStepResult[];
  rows_before: number;
  rows_after: number;
  cols_before: number;
  cols_after: number;
  before: StandardizationQualityScore;
  after: StandardizationQualityScore;
  records_modified: number;
  records_removed: number;
  comparison_notes: string[];
  warnings: string[];
  score_delta: number;
  missing_values_delta: number;
  duplicate_records_delta: number;
  invalid_values_delta: number;
}

export interface StandardizationResponse {
  file_format: "csv" | "xlsx";
  download_name: string;
  report: FixReport;
}
