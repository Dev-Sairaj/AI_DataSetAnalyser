import { Link, NavLink, Outlet, useParams } from "react-router-dom";
import { BarChart3, Download, Lightbulb, LayoutDashboard, ShieldCheck } from "lucide-react";
import { useJob, useResult, useRunJob } from "../../api/hooks";
import type { JobContext } from "../../hooks/useReport";
import { Alert, Badge, Button, Card, ProgressBar, Spinner, gradeTone } from "../ui";
import { fmtInt } from "../../lib/format";

const TABS = [
  ["overview", "Overview", LayoutDashboard],
  ["quality", "Data quality", ShieldCheck],
  ["eda", "Exploratory analysis", BarChart3],
  ["features", "Feature guidance", Lightbulb],
  ["export", "Export", Download],
] as const;

export default function JobLayout() {
  const { jobId = "" } = useParams();
  const job = useJob(jobId);
  const completed = job.data?.status === "completed";
  const result = useResult(jobId, completed);
  const run = useRunJob();

  if (job.isPending) return <Spinner label="Loading…" />;
  if (job.isError) {
    return (
      <div className="space-y-3">
        <Alert tone="red">{job.error.message}</Alert>
        <Link to="/" className="text-indigo-600 hover:underline">
          Back to start
        </Link>
      </div>
    );
  }

  const j = job.data;

  if (j.status === "queued" || j.status === "running") {
    return (
      <Card className="mx-auto max-w-xl space-y-4">
        <div>
          <h1 className="text-lg font-semibold">Analysing {j.filename}</h1>
          <p className="text-sm text-slate-500">{j.message || "Working…"}</p>
        </div>
        <ProgressBar value={j.progress} />
        <p className="text-right text-xs text-slate-400">{Math.round(j.progress * 100)}%</p>
      </Card>
    );
  }

  if (j.status === "failed") {
    return (
      <div className="mx-auto max-w-xl space-y-4">
        <Alert tone="red">
          <p className="font-medium">Analysis failed</p>
          <p>{j.error ?? "Unknown error."}</p>
        </Alert>
        <Link to="/" className="text-indigo-600 hover:underline">
          Start a new analysis
        </Link>
      </div>
    );
  }

  if (j.status === "uploaded") {
    return (
      <Card className="mx-auto max-w-xl space-y-4">
        <h1 className="text-lg font-semibold">{j.filename}</h1>
        <p className="text-sm text-slate-500">This dataset was uploaded but not analysed yet.</p>
        {run.isError && <Alert tone="red">{run.error.message}</Alert>}
        <Button
          disabled={run.isPending}
          onClick={() => run.mutate({ jobId: j.job_id, body: { target: null, sheet: null } })}
        >
          Run analysis
        </Button>
      </Card>
    );
  }

  if (result.isPending) return <Spinner label="Loading results…" />;
  if (result.isError) return <Alert tone="red">{result.error.message}</Alert>;

  const report = result.data;
  const context: JobContext = { report, job: j };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center gap-3">
        <h1 className="break-all text-xl font-semibold">{report.dataset.name}</h1>
        <Badge tone="slate">{report.dataset.file_format.toUpperCase()}</Badge>
        <Badge tone="slate">
          {fmtInt(report.profile.n_rows)} rows × {report.profile.n_cols} cols
        </Badge>
        {report.target && <Badge tone="indigo">target: {report.target}</Badge>}
        <Badge tone={gradeTone(report.quality.grade)}>quality {report.quality.grade}</Badge>
      </div>

      <nav className="flex gap-1 overflow-x-auto border-b border-slate-200">
        {TABS.map(([path, label, Icon]) => (
          <NavLink
            key={path}
            to={path}
            className={({ isActive }) =>
              `flex items-center gap-2 whitespace-nowrap border-b-2 px-4 py-2 text-sm font-medium ${
                isActive
                  ? "border-indigo-600 text-indigo-600"
                  : "border-transparent text-slate-500 hover:text-slate-800"
              }`
            }
          >
            <Icon className="h-4 w-4" />
            {label}
          </NavLink>
        ))}
      </nav>

      <Outlet context={context} />
    </div>
  );
}