import { Badge, Card, gradeTone } from "../ui";
import type { QualityReport } from "../../types/api";

export default function ScoreCard({ quality }: { quality: QualityReport }) {
  return (
    <Card>
      <div className="flex items-center gap-4">
        <div className="text-5xl font-bold">{quality.grade}</div>
        <div>
          <div className="text-sm text-slate-500">Overall quality score</div>
          <div className="flex items-center gap-2">
            <span className="text-2xl font-semibold">{quality.score}</span>
            <span className="text-slate-400">/ 100</span>
            <Badge tone={gradeTone(quality.grade)}>grade {quality.grade}</Badge>
          </div>
        </div>
      </div>
      <div className="mt-5 space-y-3">
        {Object.entries(quality.score_breakdown).map(([name, value]) => (
          <div key={name}>
            <div className="flex justify-between text-sm">
              <span className="capitalize">{name}</span>
              <span className="text-slate-500">{value}</span>
            </div>
            <div className="mt-1 h-2 overflow-hidden rounded-full bg-slate-200">
              <div className="h-full rounded-full bg-indigo-600" style={{ width: `${value}%` }} />
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
}