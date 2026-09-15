import { request } from "./workbench";

export type CloudJob = {
  job_id: string;
  operation_kind: string;
  input: { artifact_id: string; sha256: string; source_id: string };
  status: "QUEUED" | "RUNNING" | "SUCCEEDED" | "FAILED" | "RECOVERY_REQUIRED" | "BLOCKED_RUNTIME_DRIFT" | "BLOCKED";
  phase: string;
  provider: string;
  requested_model: string;
  provider_reported_model: string | null;
  provider_request_id: string | null;
  model_identity_status: string | null;
  provider_adapter_version: string;
  runtime_identity: Record<string, unknown>;
  prompt_identity: Record<string, unknown>;
  configuration_identity: Record<string, unknown>;
  retry_owner: string;
  attempt_count: number;
  budget: { max_calls: number; max_attempts: number; max_output_tokens: number; max_total_tokens: number; reserved_calls: number; reserved_tokens: number };
  usage: { status: "KNOWN" | "UNKNOWN"; input_tokens: number | null; output_tokens: number | null; total_tokens: number | null; cached_tokens: number | null };
  validation_status: string;
  result_artifact: { artifact_id: string; status: string } | null;
  last_error: string | null;
  recovery_required: boolean;
  created_at: string;
  started_at: string | null;
  ended_at: string | null;
  updated_at: string;
};

export type JobPage = { items: CloudJob[]; total: number; next_cursor: string | null; previous_cursor: string | null };
export type JobEvent = { sequence: number; event_type: string; event: Record<string, unknown>; event_sha256: string; created_at: string };

export const listCloudJobs = (signal: AbortSignal) => request<JobPage>("/jobs?limit=25", signal);
export const getCloudJob = (id: string, signal: AbortSignal) =>
  request<CloudJob>("/jobs/" + encodeURIComponent(id), signal);
export const getCloudJobEvents = (id: string, signal: AbortSignal) =>
  request<{ items: JobEvent[] }>("/jobs/" + encodeURIComponent(id) + "/events?limit=100", signal);
export const getCloudJobArtifacts = (id: string, signal: AbortSignal) =>
  request<{ items: Array<{ result_artifact_id: string; sha256: string; validation_status: string; created_at: string }>; raw_output_exposed: false }>(
    "/jobs/" + encodeURIComponent(id) + "/artifacts", signal);
export const submitCloudJob = (body: object, csrf: string, signal: AbortSignal) =>
  request<{ job: CloudJob; duplicate: boolean }>("/jobs", signal, {
    method: "POST", headers: { "Content-Type": "application/json", "X-CSRF-Token": csrf },
    body: JSON.stringify(body),
  });
