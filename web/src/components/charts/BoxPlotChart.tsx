import { fmtCompact, fmtNum } from "../../lib/format";
import type { BoxPlotData } from "../../types/api";

export default function BoxPlotChart({ box }: { box: BoxPlotData }) {
  const values = [
    box.whisker_low,
    box.q1,
    box.median,
    box.q3,
    box.whisker_high,
    ...box.outlier_values,
  ];
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = max - min || 1;
  const x = (v: number) => 12 + ((v - min) / span) * 276;

  return (
    <div className="rounded-lg border border-slate-200 p-3">
      <div className="flex items-baseline justify-between text-sm">
        <span className="font-medium">{box.column}</span>
        <span className="text-slate-500">{box.n_outliers} outliers</span>
      </div>
      <svg viewBox="0 0 300 50" className="mt-2 w-full">
        <line x1={x(box.whisker_low)} x2={x(box.whisker_high)} y1={25} y2={25} stroke="#4f46e5" />
        <line x1={x(box.whisker_low)} x2={x(box.whisker_low)} y1={18} y2={32} stroke="#4f46e5" />
        <line x1={x(box.whisker_high)} x2={x(box.whisker_high)} y1={18} y2={32} stroke="#4f46e5" />
        <rect
          x={x(box.q1)}
          y={13}
          width={Math.max(x(box.q3) - x(box.q1), 1)}
          height={24}
          fill="#c7d2fe"
          stroke="#4f46e5"
        />
        <line x1={x(box.median)} x2={x(box.median)} y1={13} y2={37} stroke="#dc2626" strokeWidth={2} />
        {box.outlier_values.map((v, i) => (
          <circle key={i} cx={x(v)} cy={25} r={2.2} fill="#4f46e5" opacity={0.5} />
        ))}
      </svg>
      <div className="flex justify-between text-xs text-slate-500">
        <span>{fmtCompact(min)}</span>
        <span>median {fmtNum(box.median)}</span>
        <span>{fmtCompact(max)}</span>
      </div>
    </div>
  );
}