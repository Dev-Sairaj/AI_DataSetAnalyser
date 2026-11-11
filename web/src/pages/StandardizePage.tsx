import { useMemo, useState } from "react";
import { Download } from "lucide-react";
import { api } from "../api/client";
import { useStandardization, useStandardize } from "../api/hooks";
import { Alert, Badge, Button, Card, Section, Table, Td, Th, buttonClasses } from "../components/ui";
import { useReport } from "../hooks/useReport";
import BeforeAfterComparison from "../components/charts/BeforeAfterComparison";
import type { ScalingMethod, StandardizeRequest, TextCase } from "../types/api";

interface ColumnSelectorProps {
  title: string;
  columns: string[];
  selected: string[];
  onChange: (columns: string[]) => void;
}

/** Renders a compact multi-column selector for one standardization operation. */
function ColumnSelector({ title, columns, selected, onChange }: ColumnSelectorProps) {
  if (columns.length === 0) return <p className="text-sm text-slate-400">No applicable columns detected.</p>;

  return (
    <div>
      <div className="mb-2 flex items-center justify-between">
        <h3 className="font-medium">{title}</h3>
        <div className="flex gap-2 text-xs">
          <button type="button" className="text-indigo-600" onClick={() => onChange(columns)}>
            Select all
          </button>
          <button type="button" className="text-slate-500" onClick={() => onChange([])}>
            Clear
          </button>
        </div>
      </div>
      <div className="grid gap-2 sm:grid-cols-2">
        {columns.map((column) => (
          <label key={column} className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={selected.includes(column)}
              onChange={(event) =>
                onChange(
                  event.target.checked
                    ? [...selected, column]
                    : selected.filter((item) => item !== column),
                )
              }
            />
            <span className="break-all">{column}</span>
          </label>
        ))}
      </div>
    </div>
  );
}

/** Provides user-approved, non-destructive dataset standardization and download. */
export default function StandardizePage() {
  const { report, job } = useReport();
  const columns = report.profile.columns;

  const candidates = useMemo(() => {
    const phonePattern = /(phone|mobile|telephone|contact|tel_no|cell)/i;
    const datePattern = /(date|datetime|timestamp|time|dob|birth)/i;
    const phone = columns.filter((column) => phonePattern.test(column.name)).map((column) => column.name);
    const date = columns
      .filter((column) => column.kind === "datetime" || datePattern.test(column.name))
      .map((column) => column.name)
      .filter((column) => !phone.includes(column));
    const text = columns
      .filter((column) => ["categorical", "text"].includes(column.kind))
      .map((column) => column.name)
      .filter((column) => !phone.includes(column) && !date.includes(column));
    const numeric = columns
      .filter((column) => column.kind === "numeric" && column.name !== report.target)
      .map((column) => column.name);
    return { text, date, phone, numeric };
  }, [columns, report.target]);

  const [textColumns, setTextColumns] = useState<string[]>(candidates.text);
  const [textCase, setTextCase] = useState<TextCase>("preserve");
  const [dateColumns, setDateColumns] = useState<string[]>(candidates.date);
  const [dateFormat, setDateFormat] = useState("%Y-%m-%d");
  const [dayfirst, setDayfirst] = useState(false);
  const [phoneColumns, setPhoneColumns] = useState<string[]>(candidates.phone);
  const [countryCode, setCountryCode] = useState("91");
  const [numericColumns, setNumericColumns] = useState<string[]>([]);
  const [scalingMethod, setScalingMethod] = useState<ScalingMethod>("none");

  const saved = useStandardization(job.job_id);
  const standardize = useStandardize();
  const result = standardize.data ?? saved.data;
  const hasOperation =
    textColumns.length > 0 ||
    dateColumns.length > 0 ||
    phoneColumns.length > 0 ||
    (numericColumns.length > 0 && scalingMethod !== "none");

  /** Submits only the explicitly selected standardization operations. */
  function submit() {
    const body: StandardizeRequest = {
      text_columns: textColumns,
      text_case: textCase,
      date_columns: dateColumns,
      date_format: dateFormat,
      dayfirst,
      phone_columns: phoneColumns,
      phone_country_code: countryCode,
      numeric_columns: numericColumns,
      scaling_method: scalingMethod,
    };
    standardize.mutate({ jobId: job.job_id, body });
  }

  return (
    <div className="space-y-8">
      <Alert tone="blue">
        The uploaded dataset is preserved. Every operation writes a separate standardized copy.
      </Alert>

      <Section title="Text and categorical standardization" subtitle="Normalizes Unicode and removes leading, trailing and repeated spaces.">
        <Card className="space-y-4">
          <ColumnSelector title="Columns" columns={candidates.text} selected={textColumns} onChange={setTextColumns} />
          <label className="block text-sm">
            <span className="mb-1 block font-medium">Letter case</span>
            <select className="rounded-lg border border-slate-300 px-3 py-2" value={textCase} onChange={(event) => setTextCase(event.target.value as TextCase)}>
              <option value="preserve">Preserve</option>
              <option value="lower">lower case</option>
              <option value="upper">UPPER CASE</option>
              <option value="title">Title Case</option>
            </select>
          </label>
        </Card>
      </Section>

      <Section title="Date normalization" subtitle="Parse recognizable dates and retain invalid originals for review.">
        <Card className="space-y-4">
          <ColumnSelector title="Date columns" columns={candidates.date} selected={dateColumns} onChange={setDateColumns} />
          <div className="flex flex-wrap gap-4">
            <label className="text-sm">
              <span className="mb-1 block font-medium">Output format</span>
              <input className="rounded-lg border border-slate-300 px-3 py-2" value={dateFormat} onChange={(event) => setDateFormat(event.target.value)} />
            </label>
            <label className="flex items-end gap-2 pb-2 text-sm">
              <input type="checkbox" checked={dayfirst} onChange={(event) => setDayfirst(event.target.checked)} />
              Interpret ambiguous dates as day-first
            </label>
          </div>
        </Card>
      </Section>

      <Section title="Phone-number validation" subtitle="Valid numbers are normalized to E.164-style text; invalid values remain unchanged.">
        <Card className="space-y-4">
          <ColumnSelector title="Phone columns" columns={candidates.phone} selected={phoneColumns} onChange={setPhoneColumns} />
          <label className="block text-sm">
            <span className="mb-1 block font-medium">Default country code</span>
            <input className="w-32 rounded-lg border border-slate-300 px-3 py-2" value={countryCode} onChange={(event) => setCountryCode(event.target.value.replace(/\D/g, ""))} />
          </label>
        </Card>
      </Section>

      <Section title="Optional numerical scaling" subtitle="Scaling is applied only to selected numerical feature columns; the target remains protected.">
        <Card className="space-y-4">
          <label className="block text-sm">
            <span className="mb-1 block font-medium">Method</span>
            <select className="rounded-lg border border-slate-300 px-3 py-2" value={scalingMethod} onChange={(event) => setScalingMethod(event.target.value as ScalingMethod)}>
              <option value="none">Do not scale</option>
              <option value="minmax">Min-Max scaling (0–1)</option>
              <option value="zscore">Z-score standardization</option>
            </select>
          </label>
          <ColumnSelector title="Numerical columns" columns={candidates.numeric} selected={numericColumns} onChange={setNumericColumns} />
        </Card>
      </Section>

      {standardize.isError && <Alert tone="red">{standardize.error.message}</Alert>}
      <Button disabled={!hasOperation || standardize.isPending} onClick={submit}>
        {standardize.isPending ? "Creating standardized copy…" : "Create standardized dataset"}
      </Button>

      {result && (
        <Section
          title="Before vs after comparison"
          subtitle="Compares the preserved original dataset with the latest cleaned and standardized copy."
        >
          {result.report.warnings.map((warning) => <Alert key={warning}>{warning}</Alert>)}
          <BeforeAfterComparison report={result.report} />
          <h3 className="pt-2 text-lg font-semibold">Cleaning and standardization audit</h3>
          <Card className="p-0">
            <Table>
              <thead><tr><Th>Operation</Th><Th>Status</Th><Th>Summary</Th></tr></thead>
              <tbody>
                {result.report.steps.map((step) => (
                  <tr key={step.step_id}>
                    <Td className="font-medium">{step.label}</Td>
                    <Td><Badge tone={step.status === "applied" ? "green" : step.status === "failed" ? "red" : "amber"}>{step.status}</Badge></Td>
                    <Td className="text-slate-600">{step.message}</Td>
                  </tr>
                ))}
              </tbody>
            </Table>
          </Card>
          <a className={buttonClasses()} href={api.standardizedDownloadUrl(job.job_id)}>
            <Download className="h-4 w-4" /> Download {result.download_name}
          </a>
        </Section>
      )}
    </div>
  );
}
