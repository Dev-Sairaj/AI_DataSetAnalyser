import { useState } from "react";
import { useReport } from "../hooks/useReport";
import ScoreCard from "../components/charts/ScoreCard";
import { Alert, Card, KindBadge, Section, Stat, Table, Td, Th } from "../components/ui";
import { fmtBytes, fmtInt } from "../lib/format";

export default function OverviewPage() {
  const { report } = useReport();
  const { profile, dataset, quality } = report;
  const [filter, setFilter] = useState("");

  const columns = profile.columns.filter((c) =>
    c.name.toLowerCase().includes(filter.trim().toLowerCase()),
  );

  return (
    <div className="space-y-8">
      {dataset.truncated && (
        <Alert tone="amber">
          Only the first {fmtInt(dataset.rows_loaded)} rows were analysed (row limit reached).
        </Alert>
      )}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Stat label="Rows" value={fmtInt(profile.n_rows)} />
        <Stat label="Columns" value={profile.n_cols} />
        <Stat label="Memory" value={fmtBytes(profile.memory_bytes)} />
        <Stat
          label="Missing cells"
          value={`${profile.missing_pct}%`}
          hint={`${fmtInt(profile.total_missing)} of ${fmtInt(profile.total_cells)}`}
        />
        <Stat
          label="Duplicate rows"
          value={fmtInt(profile.duplicate_rows)}
          hint={`${profile.duplicate_pct}% of rows`}
        />
        <Stat label="Issues found" value={quality.issues.length} />
        <Stat label="Numeric columns" value={profile.columns.filter((c) => c.kind === "numeric").length} />
        <Stat
          label="Categorical columns"
          value={profile.columns.filter((c) => c.kind === "categorical").length}
        />
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <ScoreCard quality={quality} />
        <Card className="lg:col-span-2">
          <h3 className="mb-3 font-semibold">Dataset details</h3>
          <dl className="grid grid-cols-[auto_1fr] gap-x-6 gap-y-2 text-sm">
            <dt className="text-slate-500">File</dt>
            <dd className="break-all">{dataset.name}</dd>
            <dt className="text-slate-500">Format</dt>
            <dd>{dataset.file_format.toUpperCase()}</dd>
            <dt className="text-slate-500">File size</dt>
            <dd>{fmtBytes(dataset.file_size_bytes)}</dd>
            {dataset.sheet_name && (
              <>
                <dt className="text-slate-500">Sheet</dt>
                <dd>{dataset.sheet_name}</dd>
              </>
            )}
            <dt className="text-slate-500">Target column</dt>
            <dd>{report.target ?? "none"}</dd>
            <dt className="text-slate-500">Analysed with</dt>
            <dd>ADIP v{report.adip_version}</dd>
          </dl>
        </Card>
      </div>

      <Section title="Column profile">
        <input
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          placeholder="Filter columns…"
          className="w-full max-w-xs rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm"
        />
        <Card className="p-0">
          <Table>
            <thead>
              <tr>
                <Th>Column</Th>
                <Th>Type</Th>
                <Th>Kind</Th>
                <Th>Missing</Th>
                <Th>Unique</Th>
                <Th>Sample values</Th>
              </tr>
            </thead>
            <tbody>
              {columns.map((c) => (
                <tr key={c.name}>
                  <Td className="font-medium">{c.name}</Td>
                  <Td className="text-slate-500">{c.dtype}</Td>
                  <Td>
                    <KindBadge kind={c.kind} />
                  </Td>
                  <Td>
                    {fmtInt(c.missing)} <span className="text-slate-400">({c.missing_pct}%)</span>
                  </Td>
                  <Td>{fmtInt(c.unique)}</Td>
                  <Td className="max-w-xs truncate text-slate-500">{c.sample_values.join(", ")}</Td>
                </tr>
              ))}
              {columns.length === 0 && (
                <tr>
                  <Td className="text-slate-400">No columns match.</Td>
                </tr>
              )}
            </tbody>
          </Table>
        </Card>
      </Section>
    </div>
  );
}