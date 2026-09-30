import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { fmtNum } from "../../lib/format";

export interface BarDatum {
  name: string;
  value: number;
}

interface Props {
  data: BarDatum[];
  color?: string;
  suffix?: string;
  max?: number;
}

/** Horizontal bar chart used for categories, missing values and feature signals. */
export default function BarList({ data, color = "#4f46e5", suffix = "", max }: Props) {
  const height = Math.max(120, data.length * 30 + 44);
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} layout="vertical" margin={{ left: 8, right: 24, top: 4, bottom: 4 }}>
        <CartesianGrid horizontal={false} strokeDasharray="3 3" stroke="#e2e8f0" />
        <XAxis
          type="number"
          tick={{ fontSize: 11 }}
          domain={max !== undefined ? [0, max] : undefined}
          unit={suffix}
        />
        <YAxis
          type="category"
          dataKey="name"
          width={120}
          tick={{ fontSize: 11 }}
          tickFormatter={(v: string) => (v.length > 17 ? `${v.slice(0, 16)}…` : v)}
        />
        <Tooltip formatter={(v) => `${fmtNum(Number(v))}${suffix}`} />
        <Bar dataKey="value" fill={color} radius={[0, 4, 4, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}