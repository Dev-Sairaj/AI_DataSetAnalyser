import { Badge, Card, gradeTone } from "../ui";
import type { DatasetStatus, QualityReport } from "../../types/api";
import type { Tone } from "../ui";

const STATUS_TONE: Record<DatasetStatus, Tone> = {
  Clean: "green",
  "Needs Cleaning": "amber",
  "Critical Issues": "red",
};

/** Displays dataset status, grade, and transparent six-dimension scoring details. */
export default function ScoreCard({ quality }: { quality: QualityReport }) {
  return (
    <Card>
      <div className="mb-4">
        <div className="text-sm text-slate-500">Dataset status</div>
        <div className="mt-1 flex items-center gap-2">
          <Badge tone={STATUS_TONE[quality.status]}>{quality.status}</Badge>
          <span className="text-sm text-slate-600">{quality.status_summary}</span>
        </div>
      </div>
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
      <p className="mt-3 text-sm text-slate-600">{quality.score_explanation}</p>
      <p className="mt-1 text-sm text-slate-500">{quality.grade_explanation}</p>
      <div className="mt-5 space-y-3">
        {quality.dimension_scores.map((dimension) => (
          <div key={dimension.name} className="rounded-lg border border-slate-200 p-3">
            <div className="flex justify-between text-sm">
              <span className="font-medium">{dimension.name}</span>
              <span className="text-slate-500">
                {dimension.score === null ? "Not assessed" : `${dimension.score} / 100`}
              </span>
            </div>
            {dimension.score !== null && (
              <div className="mt-1 h-2 overflow-hidden rounded-full bg-slate-200">
                <div
                  className="h-full rounded-full bg-indigo-600"
                  style={{ width: `${dimension.score}%` }}
                />
              </div>
            )}
            <div className="mt-2 flex flex-wrap gap-x-3 text-xs text-slate-500">
              <span>Assessment: {dimension.assessment.replace("_", " ")}</span>
              <span>Configured weight: {(dimension.configured_weight * 100).toFixed(1)}%</span>
              <span>Effective weight: {(dimension.effective_weight * 100).toFixed(1)}%</span>
            </div>
            <p className="mt-1 text-xs text-slate-500">{dimension.evidence}</p>
            {dimension.limitation && (
              <p className="mt-1 text-xs text-amber-700">Limitation: {dimension.limitation}</p>
            )}
          </div>
        ))}
      </div>
    </Card>
  );
}
