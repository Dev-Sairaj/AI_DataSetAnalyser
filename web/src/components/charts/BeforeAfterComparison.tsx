import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { FixReport } from "../../types/api";
import { fmtInt, fmtNum } from "../../lib/format";
import { Badge, Card, Stat, Table, Td, Th } from "../ui";

interface ComparisonRow {
  metric: string;
  original: number;
  cleaned: number;
  change: number;
  score?: boolean;
}

/** Return a signed, formatted metric change for the comparison table. */
function formatChange(value: number, score = false): string {
  const formatted = score ? fmtNum(value) : fmtInt(value);
  return `${value > 0 ? "+" : ""}${formatted}`;
}

/** Render score, defect-count, and record-impact comparisons for a cleaning run. */
export default function BeforeAfterComparison({ report }: { report: FixReport }) {
  const rows: ComparisonRow[] = [
    {
      metric: "Quality score",
      original: report.before.score,
      cleaned: report.after.score,
      change: report.score_delta,
      score: true,
    },
    {
      metric: "Missing values",
      original: report.before.missing_values,
      cleaned: report.after.missing_values,
      change: report.missing_values_delta,
    },
    {
      metric: "Duplicate records",
      original: report.before.duplicate_records,
      cleaned: report.after.duplicate_records,
      change: report.duplicate_records_delta,
    },
    {
      metric: "Invalid values",
      original: report.before.invalid_values,
      cleaned: report.after.invalid_values,
      change: report.invalid_values_delta,
    },
  ];
  const issueData = rows.slice(1).map(({ metric, original, cleaned }) => ({
    metric,
    Original: original,
    Cleaned: cleaned,
  }));
  const scoreData = [
    {
      metric: "Quality score",
      Original: report.before.score,
      Cleaned: report.after.score,
    },
  ];

  return (
    <div className="space-y-5">
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
        <Stat
          label="Original score"
          value={`${fmtNum(report.before.score)} / 100`}
          hint={`Grade ${report.before.grade}`}
        />
        <Stat
          label="Cleaned score"
          value={`${fmtNum(report.after.score)} / 100`}
          hint={`Grade ${report.after.grade}`}
        />
        <Stat
          label="Score change"
          value={formatChange(report.score_delta, true)}
          hint="Cleaned minus original"
        />
        <Stat
          label="Records modified"
          value={fmtInt(report.records_modified)}
          hint="Retained records with changes"
        />
        <Stat
          label="Records removed"
          value={fmtInt(report.records_removed)}
          hint="Not included as modified"
        />
      </div>

      <div className="grid gap-5 lg:grid-cols-2">
        <Card>
          <h3 className="mb-3 font-medium">Quality score</h3>
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={scoreData} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis dataKey="metric" tick={{ fontSize: 12 }} />
              <YAxis domain={[0, 100]} tick={{ fontSize: 11 }} />
              <Tooltip formatter={(value) => fmtNum(Number(value))} />
              <Legend />
              <Bar dataKey="Original" fill="#94a3b8" radius={[4, 4, 0, 0]} />
              <Bar dataKey="Cleaned" fill="#4f46e5" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </Card>
        <Card>
          <h3 className="mb-3 font-medium">Detected quality issues</h3>
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={issueData} margin={{ top: 8, right: 12, left: 0, bottom: 12 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis dataKey="metric" tick={{ fontSize: 11 }} interval={0} />
              <YAxis allowDecimals={false} tick={{ fontSize: 11 }} />
              <Tooltip formatter={(value) => fmtInt(Number(value))} />
              <Legend />
              <Bar dataKey="Original" fill="#94a3b8" radius={[4, 4, 0, 0]} />
              <Bar dataKey="Cleaned" fill="#4f46e5" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </Card>
      </div>

      <Card className="p-0">
        <Table>
          <thead>
            <tr>
              <Th>Metric</Th>
              <Th>Original</Th>
              <Th>Cleaned</Th>
              <Th>Change</Th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => {
              const improved = row.score ? row.change > 0 : row.change < 0;
              const worsened = row.score ? row.change < 0 : row.change > 0;
              return (
                <tr key={row.metric}>
                  <Td className="font-medium">{row.metric}</Td>
                  <Td>{row.score ? fmtNum(row.original) : fmtInt(row.original)}</Td>
                  <Td>{row.score ? fmtNum(row.cleaned) : fmtInt(row.cleaned)}</Td>
                  <Td>
                    <Badge tone={improved ? "green" : worsened ? "red" : "slate"}>
                      {formatChange(row.change, row.score)}
                    </Badge>
                  </Td>
                </tr>
              );
            })}
          </tbody>
        </Table>
      </Card>

      <Card>
        <h3 className="font-medium">Comparison rules</h3>
        <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-slate-600">
          {report.comparison_notes.map((note) => (
            <li key={note}>{note}</li>
          ))}
        </ul>
      </Card>
    </div>
  );
}
