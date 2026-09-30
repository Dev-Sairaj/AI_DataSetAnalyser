import { useRef, useState } from "react";
import type { DragEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Play, Trash2, UploadCloud, X } from "lucide-react";
import { api } from "../api/client";
import { useDeleteJob, useJobs, useRunJob, useUpload } from "../api/hooks";
import { Alert, Badge, Button, Card, Section, Spinner, Table, Td, Th } from "../components/ui";
import type { Tone } from "../components/ui";
import { fmtBytes, fmtDate } from "../lib/format";
import type { ColumnInfo, JobStatus, UploadResponse } from "../types/api";

const ACCEPTED = [".csv", ".xlsx"];
const STATUS_TONE: Record<JobStatus, Tone> = {
  uploaded: "slate",
  queued: "blue",
  running: "blue",
  completed: "green",
  failed: "red",
};

export default function UploadPage() {
  const navigate = useNavigate();
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [setup, setSetup] = useState<UploadResponse | null>(null);
  const [columns, setColumns] = useState<ColumnInfo[]>([]);
  const [sheet, setSheet] = useState("");
  const [target, setTarget] = useState("");

  const upload = useUpload();
  const run = useRunJob();
  const jobs = useJobs();
  const remove = useDeleteJob();

  function pick(file: File | undefined) {
    if (!file) return;
    setError(null);
    const ext = file.name.slice(file.name.lastIndexOf(".")).toLowerCase();
    if (!ACCEPTED.includes(ext)) {
      setError(`Unsupported file type. Please upload ${ACCEPTED.join(" or ")}.`);
      return;
    }
    upload.mutate(file, {
      onSuccess: (data) => {
        setSetup(data);
        setColumns(data.columns);
        setSheet(data.sheets[0] ?? "");
        setTarget("");
      },
      onError: (e) => setError(e.message),
    });
  }

  function onDrop(e: DragEvent<HTMLDivElement>) {
    e.preventDefault();
    setDragging(false);
    pick(e.dataTransfer.files[0]);
  }

  async function changeSheet(name: string) {
    if (!setup) return;
    setSheet(name);
    setError(null);
    try {
      const info = await api.columns(setup.job.job_id, name);
      setColumns(info.columns);
      setTarget((t) => (info.columns.some((c) => c.name === t) ? t : ""));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not read that sheet.");
    }
  }

  function start() {
    if (!setup) return;
    const jobId = setup.job.job_id;
    run.mutate(
      { jobId, body: { target: target || null, sheet: sheet || null } },
      { onSuccess: () => navigate(`/jobs/${jobId}`), onError: (e) => setError(e.message) },
    );
  }

  function cancel() {
    if (setup) remove.mutate(setup.job.job_id);
    setSetup(null);
    setError(null);
  }

  return (
    <div className="space-y-10">
      <div className="mx-auto max-w-2xl space-y-5">
        <div className="text-center">
          <h1 className="text-2xl font-semibold">Understand your dataset in seconds</h1>
          <p className="mt-1 text-slate-500">
            Upload a CSV or Excel file for profiling, data quality checks, EDA and preprocessing
            guidance.
          </p>
        </div>

        {error && <Alert tone="red">{error}</Alert>}

        {upload.isPending ? (
          <Card>
            <Spinner label="Uploading and inspecting…" />
          </Card>
        ) : setup ? (
          <Card className="space-y-5">
            <div className="flex items-start justify-between gap-3">
              <div>
                <div className="break-all font-medium">{setup.job.filename}</div>
                <div className="text-sm text-slate-500">
                  {fmtBytes(setup.job.file_size_bytes)} · {columns.length} columns
                </div>
              </div>
              <button
                type="button"
                onClick={cancel}
                className="text-slate-400 hover:text-slate-700"
                aria-label="Cancel"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            {setup.sheets.length > 0 && (
              <label className="block text-sm">
                <span className="font-medium">Excel sheet</span>
                <select
                  value={sheet}
                  onChange={(e) => void changeSheet(e.target.value)}
                  className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2"
                >
                  {setup.sheets.map((s) => (
                    <option key={s} value={s}>
                      {s}
                    </option>
                  ))}
                </select>
              </label>
            )}

            <label className="block text-sm">
              <span className="font-medium">Target column</span>{" "}
              <span className="text-slate-400">(optional)</span>
              <select
                value={target}
                onChange={(e) => setTarget(e.target.value)}
                className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2"
              >
                <option value="">None: general analysis</option>
                {columns.map((c) => (
                  <option key={c.name} value={c.name}>
                    {c.name} ({c.kind})
                  </option>
                ))}
              </select>
              <span className="mt-1 block text-xs text-slate-400">
                Adds class balance, feature signals and leakage checks. Recommendations stay
                guidance-only.
              </span>
            </label>

            <Button onClick={start} disabled={run.isPending} className="w-full">
              <Play className="h-4 w-4" />
              {run.isPending ? "Starting…" : "Run analysis"}
            </Button>
          </Card>
        ) : (
          <div
            onDragOver={(e) => {
              e.preventDefault();
              setDragging(true);
            }}
            onDragLeave={() => setDragging(false)}
            onDrop={onDrop}
            onClick={() => inputRef.current?.click()}
            className={`cursor-pointer rounded-xl border-2 border-dashed px-6 py-14 text-center transition ${
              dragging ? "border-indigo-500 bg-indigo-50" : "border-slate-300 bg-white hover:border-indigo-400"
            }`}
          >
            <UploadCloud className="mx-auto h-10 w-10 text-indigo-500" />
            <p className="mt-3 font-medium">Drop a file here, or click to browse</p>
            <p className="text-sm text-slate-500">CSV or XLSX</p>
            <input
              ref={inputRef}
              type="file"
              accept={ACCEPTED.join(",")}
              className="hidden"
              onChange={(e) => {
                pick(e.target.files?.[0]);
                e.target.value = "";
              }}
            />
          </div>
        )}
      </div>

      {jobs.data && jobs.data.length > 0 && (
        <Section title="Recent analyses">
          <Card className="p-0">
            <Table>
              <thead>
                <tr>
                  <Th>Dataset</Th>
                  <Th>Status</Th>
                  <Th>Target</Th>
                  <Th>Created</Th>
                  <Th />
                </tr>
              </thead>
              <tbody>
                {jobs.data.map((j) => (
                  <tr key={j.job_id}>
                    <Td>
                      <Link to={`/jobs/${j.job_id}`} className="font-medium text-indigo-600 hover:underline">
                        {j.filename}
                      </Link>
                    </Td>
                    <Td>
                      <Badge tone={STATUS_TONE[j.status]}>{j.status}</Badge>
                    </Td>
                    <Td className="text-slate-500">{j.target ?? "–"}</Td>
                    <Td className="text-slate-500">{fmtDate(j.created_at)}</Td>
                    <Td className="text-right">
                      <button
                        type="button"
                        disabled={j.status === "queued" || j.status === "running"}
                        onClick={() => remove.mutate(j.job_id)}
                        className="text-slate-400 hover:text-red-600 disabled:opacity-30"
                        aria-label="Delete"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </Td>
                  </tr>
                ))}
              </tbody>
            </Table>
          </Card>
        </Section>
      )}
    </div>
  );
}