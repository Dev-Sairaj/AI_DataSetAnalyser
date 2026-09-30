import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ApiError, api } from "./client";
import type { RunRequest } from "../types/api";

export function useJob(jobId: string) {
  return useQuery({
    queryKey: ["job", jobId],
    queryFn: () => api.job(jobId),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === "queued" || status === "running" ? 1000 : false;
    },
    retry: (count, error) => !(error instanceof ApiError && error.status === 404) && count < 2,
  });
}

export function useResult(jobId: string, enabled: boolean) {
  return useQuery({
    queryKey: ["result", jobId],
    queryFn: () => api.result(jobId),
    enabled,
    staleTime: Infinity,
  });
}

export function useJobs() {
  return useQuery({ queryKey: ["jobs"], queryFn: api.jobs });
}

export function useUpload() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (file: File) => api.upload(file),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["jobs"] }),
  });
}

export function useRunJob() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ jobId, body }: { jobId: string; body: RunRequest }) => api.run(jobId, body),
    onSuccess: (record) => {
      qc.setQueryData(["job", record.job_id], record);
      qc.removeQueries({ queryKey: ["result", record.job_id] });
      qc.invalidateQueries({ queryKey: ["jobs"] });
    },
  });
}

export function useDeleteJob() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (jobId: string) => api.remove(jobId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["jobs"] }),
  });
}
