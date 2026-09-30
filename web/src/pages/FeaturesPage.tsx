import { useState } from "react";
import { useReport } from "../hooks/useReport";
import BarList from "../components/charts/BarList";
import { Alert, Badge, Button, Card, Section, SeverityBadge, Stat } from "../components/ui";
import type { RecCategory, Severity } from "../types/api";

const LABELS: Record<RecCategory, string> = {
  target: "Target",
  data_types: "Data types",
  missing_values: "Missing values",
  low_value: "Columns with limited analytical value",
  redundancy: "Redundancy and correlation",
  encoding: "Encoding",
  scaling: "Scaling",
};
const ORDER = Object.keys(LABELS) as RecCategory[];

type Filter = "all" | Severity;

export default function FeaturesPage() {
  const { report } = useReport();
  const { recommendations, target } = report.features;
  const [filter, setFilter] = useState<Filter>("all");

  const visible = recommendations.filter((r) => filter === "all" || r.severity === filter);

  return (
    <div className="space-y-8">
      <Alert tone="blue">
        These are recommendations only. ADIP never modifies your dataset.
      </Alert>

      {target && (
        <Section title={`Target analysis: ${target.column}`}>
          <div className="grid gap-4 sm:grid-cols-3">
            <Stat label="Task type" value={<span className="capitalize">{target.task}</span>} />
            {target.n_classes !== null && <Stat label="Classes" value={target.n_classes} />}
            {target.imbalance_ratio !== null && (
              <Stat
                label="Imbalance ratio"
                value={`${target.imbalance_ratio}×`}
                hint="largest class / smallest class"
              />
            )}
          </div>
          {target.notes.map((n) => (
            <Alert key={n}>{n}</Alert>
          ))}
          <div className="grid gap-4 md:grid-cols-2">
            {target.class_balance.length > 0 && (
              <Card>
                <h3 className="mb-2 font-medium">Class balance</h3>
                <BarList
                  data={target.class_balance.map((c) => ({ name: c.value, value: c.count }))}
                  color="#0ea5e9"
                />
              </Card>
            )}
            {target.signals.length > 0 && (
              <Card>
                <h3 className="font-medium">Strongest numeric relationships</h3>
                <p className="mb-2 text-xs text-slate-500">
                  {target.signal_metric === "pearson"
                    ? "Pearson correlation with the target"
                    : "Mutual information with the target"}
                </p>
                <BarList data={target.signals.map((s) => ({ name: s.column, value: s.score }))} />
              </Card>
            )}
          </div>
        </Section>
      )}

      <Section title={`Recommendations (${recommendations.length})`}>
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

        {visible.length === 0 && (
          <Card>
            <p className="text-sm text-slate-500">
              {recommendations.length === 0
                ? "No recommendations. The dataset looks ready for modelling."
                : "No recommendations in this category."}
            </p>
          </Card>
        )}

        {ORDER.map((cat) => {
          const items = visible.filter((r) => r.category === cat);
          if (items.length === 0) return null;
          return (
            <div key={cat} className="space-y-2">
              <h3 className="pt-2 font-medium text-slate-700">{LABELS[cat]}</h3>
              {items.map((r, i) => (
                <Card key={`${r.title}-${i}`} className="space-y-1.5 !p-4">
                  <div className="flex flex-wrap items-center gap-2">
                    <SeverityBadge severity={r.severity} />
                    <span className="font-medium">{r.title}</span>
                  </div>
                  {r.columns.length > 1 && (
                    <div className="flex flex-wrap gap-1">
                      {r.columns.map((c) => (
                        <Badge key={c}>{c}</Badge>
                      ))}
                    </div>
                  )}
                  <p className="text-sm">{r.recommendation}</p>
                  <p className="text-sm text-slate-500">{r.rationale}</p>
                </Card>
              ))}
            </div>
          );
        })}
      </Section>
    </div>
  );
}