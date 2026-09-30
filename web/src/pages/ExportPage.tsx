import { ExternalLink, FileJson, FileSpreadsheet, FileText } from "lucide-react";
import type { ComponentType } from "react";
import { api } from "../api/client";
import { useReport } from "../hooks/useReport";
import { Card, Section, buttonClasses } from "../components/ui";
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
};

export default function ExportPage() {
  const { job } = useReport();
  const available = job.available_downloads;

  return (
    <div className="space-y-8">
      <Section title="Download reports">
        <div className="grid gap-4 md:grid-cols-3">
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