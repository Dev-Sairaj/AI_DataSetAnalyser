import { useState } from "react";
import { useReport } from "../hooks/useReport";
import BarList from "../components/charts/BarList";
import ScoreCard from "../components/charts/ScoreCard";
import { Button, Card, Section, SeverityBadge, Stat, Table, Td, Th } from "../components/ui";
import { fmtInt, fmtNum } from "../lib/format";
import type { Severity } from "../types/api";

type Filter = "all" | Severity;

export default function QualityPage() {
  const { report } = useReport();
  const { quality, charts } = report;
  const [filter, setFilter] = useState<Filter>("all");

  const count = (s: Severity) => quality.issues.filter((i) => i.severity === s).length;
  const issues = quality.issues.filter((i) => filter === "all" || i.severity === filter);
  const missing = charts.missing.slice(0, 20).map((m) => ({ name: m.column, value: m.missing_pct }));

  return (
    <div className="space-y-8">
      <div className="grid gap-6 lg:grid-cols-3">
        <ScoreCard quality={quality} />
        <div className="grid content-start gap-4 sm:grid-cols-3 lg:col-span-2">
          <Stat label="Critical" value={count("critical")} />
          <Stat label="Warnings" value={count("warning")} />
          <Stat label="Informational" value={count("info")} />
        </div>
      </div>

      <Section title="Findings">
        <div className="flex flex-wrap gap-2">
          {(["all", "critical", "warning", "info"] as const).map((f) => (
            <Button
              key={f}
              variant={filter === f ? "primary" : "secondary"}
              onClick={() => setFilter(f)}
              className="capitalize"
            >
              {f}
            </Button>
          ))}
        </div>
        <Card className="p-0">
          {issues.length === 0 ? (
            <p className="p-5 text-sm text-slate-500">No issues in this category.</p>
          ) : (
            <Table>
              <thead>
                <tr>
                  <Th>Severity</Th>
                  <Th>Issue</Th>
                  <Th>Column</Th>
                  <Th>Details</Th>
                </tr>
              </thead>
              <tbody>
                {issues.map((i, idx) => (
                  <tr key={`${i.code}-${i.column}-${idx}`}>
                    <Td>
                      <SeverityBadge severity={i.severity} />
                    </Td>
                    <Td className="whitespace-nowrap font-mono text-xs">{i.code}</Td>
                    <Td className="font-medium">{i.column ?? "–"}</Td>
                    <Td className="text-slate-600">{i.message}</Td>
                  </tr>
                ))}
              </tbody>
            </Table>
          )}
        </Card>
      </Section>

      {quality.outliers.length > 0 && (
        <Section
          title="Outliers"
          subtitle={`Detected with ${quality.outliers[0].method.toUpperCase()} on numeric columns.`}
        >
          <Card className="p-0">
            <Table>
              <thead>
                <tr>
                  <Th>Column</Th>
                  <Th>Outliers</Th>
                  <Th>Share</Th>
                  <Th>Lower bound</Th>
                  <Th>Upper bound</Th>
                </tr>
              </thead>
              <tbody>
                {quality.outliers.map((o) => (
                  <tr key={o.column}>
                    <Td className="font-medium">{o.column}</Td>
                    <Td>{fmtInt(o.count)}</Td>
                    <Td>{o.pct}%</Td>
                    <Td>{fmtNum(o.lower_bound)}</Td>
                    <Td>{fmtNum(o.upper_bound)}</Td>
                  </tr>
                ))}
              </tbody>
            </Table>
          </Card>
        </Section>
      )}

      {missing.length > 0 && (
        <Section title="Missing values by column" subtitle="Share of missing values per column (%).">
          <Card>
            <BarList data={missing} color="#f59e0b" suffix="%" max={100} />
          </Card>
        </Section>
      )}
    </div>
  );
}