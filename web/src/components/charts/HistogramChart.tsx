import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { fmtCompact, fmtInt } from "../../lib/format";
import type { HistogramData } from "../../types/api";

export default function HistogramChart({ hist }: { hist: HistogramData }) {
  const data = hist.counts.map((count, i) => ({
    range: `${fmtCompact(hist.bin_edges[i])} – ${fmtCompact(hist.bin_edges[i + 1])}`,
    count,
  }));
  return (
    <div className="rounded-lg border border-slate-200 p-3">
      <div className="text-sm font-medium">{hist.column}</div>
      <ResponsiveContainer width="100%" height={190}>
        <BarChart data={data} margin={{ left: -12, right: 8, top: 8 }} barCategoryGap={1}>
          <CartesianGrid vertical={false} strokeDasharray="3 3" stroke="#e2e8f0" />
          <XAxis
            dataKey="range"
            tick={{ fontSize: 10 }}
            interval="preserveStartEnd"
            minTickGap={28}
            tickFormatter={(v: string) => v.split(" – ")[0]}
          />
          <YAxis tick={{ fontSize: 10 }} />
          <Tooltip />
          <Bar dataKey="count" fill="#4f46e5" />
        </BarChart>
      </ResponsiveContainer>
      {hist.clipped_count > 0 && (
        <p className="text-xs text-slate-400">
          {fmtInt(hist.clipped_count)} extreme values not shown
        </p>
      )}
    </div>
  );
}