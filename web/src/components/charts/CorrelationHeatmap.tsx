import type { CorrelationResult } from "../../types/api";

function cellColor(v: number | null): { background: string; color: string } {
  if (v === null) return { background: "#f1f5f9", color: "#94a3b8" };
  const a = Math.min(1, Math.abs(v));
  const [r, g, b] = v >= 0 ? [239, 68, 68] : [59, 130, 246];
  const mix = (c: number) => Math.round(255 + (c - 255) * a);
  return { background: `rgb(${mix(r)},${mix(g)},${mix(b)})`, color: a > 0.6 ? "#fff" : "#334155" };
}

export default function CorrelationHeatmap({ data }: { data: CorrelationResult }) {
  const showValues = data.columns.length <= 12;
  return (
    <div className="overflow-auto">
      <table className="border-separate border-spacing-0.5 text-xs">
        <thead>
          <tr>
            <th />
            {data.columns.map((c) => (
              <th
                key={c}
                title={c}
                className="max-h-28 overflow-hidden px-1 pb-1 text-left font-normal text-slate-600"
                style={{ writingMode: "vertical-rl", transform: "rotate(180deg)" }}
              >
                {c.length > 16 ? `${c.slice(0, 15)}…` : c}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.matrix.map((row, i) => (
            <tr key={data.columns[i]}>
              <th
                title={data.columns[i]}
                className="whitespace-nowrap pr-2 text-right font-normal text-slate-600"
              >
                {data.columns[i].length > 18 ? `${data.columns[i].slice(0, 17)}…` : data.columns[i]}
              </th>
              {row.map((v, j) => (
                <td
                  key={data.columns[j]}
                  title={`${data.columns[i]} × ${data.columns[j]}: ${v ?? "n/a"}`}
                  className="h-8 min-w-8 rounded-sm text-center"
                  style={cellColor(v)}
                >
                  {showValues && v !== null ? v.toFixed(2) : ""}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}