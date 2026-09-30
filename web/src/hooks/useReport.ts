import { useOutletContext } from "react-router-dom";
import type { AnalysisReport, JobRecord } from "../types/api";

export interface JobContext {
  report: AnalysisReport;
  job: JobRecord;
}

/** Used by every results page: the completed report is provided by JobLayout. */
export function useReport(): JobContext {
  return useOutletContext<JobContext>();
}