import type {
  AnalysisReport,
  ExportFormat,
  InspectResponse,
  JobRecord,
  RunRequest,
  UploadResponse,
} from "../types/api";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(url, init);
  } catch {
    throw new ApiError(0, "Cannot reach the ADIP server. Is the API running on port 8000?");
  }
  if (!res.ok) {
    let detail = `Request failed (${res.status})`;
    try {
      const body = await res.json();
      if (typeof body.detail === "string") detail = body.detail;
      else if (Array.isArray(body.detail))
        detail = body.detail.map((d: { msg: string }) => d.msg).join("; ");
    } catch {
      /* non-JSON error body: keep the default message */
    }
    throw new ApiError(res.status, detail);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export const api = {
  upload(file: File) {
    const form = new FormData();
    form.append("file", file);
    return request<UploadResponse>("/api/datasets", { method: "POST", body: form });
  },
  columns(jobId: string, sheet?: string) {
    const query = sheet ? `?sheet=${encodeURIComponent(sheet)}` : "";
    return request<InspectResponse>(`/api/datasets/${jobId}/columns${query}`);
  },
  run(jobId: string, body: RunRequest) {
    return request<JobRecord>(`/api/jobs/${jobId}/run`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  },
  job: (jobId: string) => request<JobRecord>(`/api/jobs/${jobId}`),
  jobs: () => request<JobRecord[]>("/api/jobs"),
  result: (jobId: string) => request<AnalysisReport>(`/api/jobs/${jobId}/result`),
  remove: (jobId: string) => request<void>(`/api/jobs/${jobId}`, { method: "DELETE" }),
  downloadUrl: (jobId: string, fmt: ExportFormat, inline = false) =>
    `/api/jobs/${jobId}/downloads/${fmt}${inline ? "?inline=true" : ""}`,
};