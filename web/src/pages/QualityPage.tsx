import { useState } from "react";
import { useReport } from "../hooks/useReport";
import BarList from "../components/charts/BarList";
import ScoreCard from "../components/charts/ScoreCard";
import { Alert, Badge, Button, Card, Section, SeverityBadge, Stat, Table, Td, Th } from "../components/ui";
import { fmtInt, fmtNum } from "../lib/format";
import type { GovernmentCoverage, Severity } from "../types/api";
import type { Tone } from "../components/ui";

type Filter = "all" | Severity;

const COVERAGE_TONE: Record<GovernmentCoverage, Tone> = {
  implemented: "green",
  partially_implemented: "amber",
  external_or_manual: "slate",
};

const COVERAGE_LABEL: Record<GovernmentCoverage, string> = {
  implemented: "Implemented",
  partially_implemented: "Partially implemented",
  external_or_manual: "External/manual",
};

export default function QualityPage() {
  const { report } = useReport();
  const { quality, charts, government_framework: government } = report;
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

      <Section
        title="Government of India data-quality framework mapping"
        subtitle={`${government.framework_name} — operational alignment for this assessment.`}
      >
        <Alert tone="amber">{government.disclaimer}</Alert>
        <Card className="p-0">
          <Table>
            <thead>
              <tr>
                <Th>Dimension</Th>
                <Th>Coverage</Th>
                <Th>Implemented checks</Th>
                <Th>External or manual checks</Th>
                <Th>Detected findings</Th>
              </tr>
            </thead>
            <tbody>
              {government.dimensions.map((dimension) => (
                <tr key={dimension.name}>
                  <Td>
                    <div className="font-medium">{dimension.name}</div>
                    <div className="mt-1 max-w-xs text-xs text-slate-500">{dimension.explanation}</div>
                  </Td>
                  <Td>
                    <Badge tone={COVERAGE_TONE[dimension.coverage]}>
                      {COVERAGE_LABEL[dimension.coverage]}
                    </Badge>
                  </Td>
                  <Td>
                    <ul className="min-w-64 list-disc space-y-1 pl-4 text-slate-600">
                      {dimension.implemented_checks.map((check) => <li key={check}>{check}</li>)}
                      {dimension.implemented_checks.length === 0 && <li>None automated</li>}
                    </ul>
                  </Td>
                  <Td>
                    <ul className="min-w-64 list-disc space-y-1 pl-4 text-slate-600">
                      {dimension.external_or_manual_checks.map((check) => <li key={check}>{check}</li>)}
                    </ul>
                  </Td>
                  <Td>
                    <div>{dimension.detected_issue_count}</div>
                    <div className="text-xs text-slate-400">
                      {dimension.detected_issue_codes.join(", ") || "No automated finding"}
                    </div>
                  </Td>
                </tr>
              ))}
            </tbody>
          </Table>
        </Card>
        <div className="space-y-1 text-sm">
          {government.references.map((reference) => (
            <p key={reference.url}>
              <a className="text-indigo-600 hover:underline" href={reference.url} target="_blank" rel="noreferrer">
                {reference.title}
              </a>{" "}
              <span className="text-slate-500">— {reference.publisher}</span>
            </p>
          ))}
        </div>
      </Section>

      <Section
        title="How the dataset status was determined"
        subtitle="The status uses all implemented checks, not only missing-value checks."
      >
        <Card className="p-0">
          <Table>
            <thead>
              <tr>
                <Th>Status rule</Th>
                <Th>Condition</Th>
                <Th>Result</Th>
                <Th>Evidence</Th>
              </tr>
            </thead>
            <tbody>
              {quality.status_rules.map((rule) => (
                <tr key={rule.name}>
                  <Td className="font-medium">{rule.name}</Td>
                  <Td className="text-slate-600">{rule.condition}</Td>
                  <Td>{rule.triggered ? "Applied" : "Not applied"}</Td>
                  <Td className="text-slate-600">{rule.evidence}</Td>
                </tr>
              ))}
            </tbody>
          </Table>
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
