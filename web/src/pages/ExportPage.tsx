import { Database, Download, ExternalLink, FileJson, FileSpreadsheet, FileText, FileType2 } from "lucide-react";
import type { ComponentType } from "react";
import { api } from "../api/client";
import { useStandardization } from "../api/hooks";
import BeforeAfterComparison from "../components/charts/BeforeAfterComparison";
import { useReport } from "../hooks/useReport";
import { Badge, Card, Section, Stat, buttonClasses, gradeTone } from "../components/ui";
import type { ExportFormat } from "../types/api";

const FORMATS: Record<
  ExportFormat,
  { label: string; description: string; icon: ComponentType<{ className?: string }> }
> = {
  html: {
    label: "HTML report",
    description: "Self-contained report with charts. Opens in any browser.",
    icon: FileText,
  },
  json: {
    label: "JSON",
    description: "Complete machine-readable results for ML pipelines.",
    icon: FileJson,
  },
  excel: {
    label: "Excel workbook",
    description: "Tables and charts on separate sheets. Works with Power BI.",
    icon: FileSpreadsheet,
  },
  pdf: {
    label: "PDF report",
    description: "Final paginated quality report for review, sharing and printing.",
    icon: FileType2,
  },
};

export default function ExportPage() {
  const { job, report } = useReport();
  const standardization = useStandardization(job.job_id);
  const available = job.available_downloads;

  return (
    <div className="space-y-8">
      <Section
        title="Final output summary"
        subtitle="Consolidated quality results for the original upload and latest approved output."
      >
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
          <Stat label="Dataset status" value={report.quality.status} />
          <Stat label="Quality score" value={`${report.quality.score} / 100`} />
          <Stat
            label="Quality grade"
            value={<Badge tone={gradeTone(report.quality.grade)}>{report.quality.grade}</Badge>}
          />
          <Stat label="Detected issues" value={report.quality.issues.length} />
          <Stat label="Recommendations" value={report.features.recommendations.length} />
        </div>

        <Card>
          <h3 className="font-medium">Six quality dimensions</h3>
          <div className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {report.quality.dimension_scores.map((dimension) => (
              <div key={dimension.name} className="rounded-lg border border-slate-200 p-3">
                <div className="flex items-center justify-between gap-3">
                  <span className="font-medium">{dimension.name}</span>
                  <span className="text-sm text-slate-600">
                    {dimension.score === null ? "Not assessed" : `${dimension.score} / 100`}
                  </span>
                </div>
                <p className="mt-1 text-xs text-slate-500">{dimension.evidence}</p>
              </div>
            ))}
          </div>
        </Card>

        <div className="grid gap-5 lg:grid-cols-2">
          <Card>
            <h3 className="font-medium">Detected issues</h3>
            {report.quality.issues.length === 0 ? (
              <p className="mt-2 text-sm text-slate-500">No automated issues were detected.</p>
            ) : (
              <ul className="mt-3 space-y-2 text-sm text-slate-600">
                {report.quality.issues.slice(0, 10).map((issue, index) => (
                  <li key={`${issue.code}-${issue.column}-${index}`}>
                    <Badge tone={issue.severity === "critical" ? "red" : issue.severity === "warning" ? "amber" : "blue"}>
                      {issue.severity}
                    </Badge>{" "}
                    {issue.message}
                  </li>
                ))}
              </ul>
            )}
            {report.quality.issues.length > 10 && (
              <p className="mt-3 text-xs text-slate-400">
                Showing 10 of {report.quality.issues.length}; see Data quality for all findings.
              </p>
            )}
          </Card>
          <Card>
            <h3 className="font-medium">Recommendations</h3>
            {report.features.recommendations.length === 0 ? (
              <p className="mt-2 text-sm text-slate-500">No recommendations were generated.</p>
            ) : (
              <ul className="mt-3 space-y-3 text-sm text-slate-600">
                {report.features.recommendations.slice(0, 10).map((recommendation, index) => (
                  <li key={`${recommendation.title}-${index}`}>
                    <div className="font-medium text-slate-800">{recommendation.title}</div>
                    <div>{recommendation.recommendation}</div>
                  </li>
                ))}
              </ul>
            )}
          </Card>
        </div>
      </Section>

      {standardization.isSuccess && (
        <Section
          title="Cleaning and standardization summary"
          subtitle="Latest approved transformations and before-vs-after comparison."
        >
          <BeforeAfterComparison report={standardization.data.report} />
          <Card>
            <ul className="space-y-2 text-sm text-slate-600">
              {standardization.data.report.steps.map((step) => (
                <li key={step.step_id}>
                  <span className="font-medium text-slate-800">{step.label}:</span> {step.message}
                </li>
              ))}
            </ul>
          </Card>
        </Section>
      )}

      <Section title="Final dataset">
        <Card className="flex flex-col items-start gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-start gap-3">
            <Database className="mt-0.5 h-7 w-7 text-indigo-600" />
            <div>
              <div className="font-medium">
                {standardization.isSuccess ? "Cleaned and standardized dataset" : "Analysed original dataset"}
              </div>
              <p className="text-sm text-slate-500">
                {standardization.isSuccess
                  ? "The latest approved derived copy; the original upload remains preserved."
                  : "No derived copy exists yet, so the preserved original is the final dataset."}
              </p>
            </div>
          </div>
          <a href={api.finalDatasetDownloadUrl(job.job_id)} className={buttonClasses("primary")}>
            <Download className="h-4 w-4" /> Download final dataset
          </a>
        </Card>
      </Section>

      <Section title="Download reports">
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          {available.map((fmt) => {
            const { label, description, icon: Icon } = FORMATS[fmt];
            return (
              <Card key={fmt} className="flex flex-col gap-3">
                <Icon className="h-7 w-7 text-indigo-600" />
                <div>
                  <div className="font-medium">{label}</div>
                  <p className="text-sm text-slate-500">{description}</p>
                </div>
                <a
                  href={api.downloadUrl(job.job_id, fmt)}
                  download
                  className={`${buttonClasses("primary")} mt-auto`}
                >
                  Download
                </a>
              </Card>
            );
          })}
        </div>
      </Section>

      {available.includes("html") && (
        <Section title="Report preview">
          <a
            href={api.downloadUrl(job.job_id, "html", true)}
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-1 text-sm text-indigo-600 hover:underline"
          >
            Open in a new tab <ExternalLink className="h-3.5 w-3.5" />
          </a>
          <iframe
            title="HTML report preview"
            src={api.downloadUrl(job.job_id, "html", true)}
            sandbox=""
            className="h-[720px] w-full rounded-xl border border-slate-200 bg-white"
          />
        </Section>
      )}
    </div>
  );
}
