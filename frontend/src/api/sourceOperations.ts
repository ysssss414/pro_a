import { request } from "./workbench";
import type { CloudJob } from "./cloudJobs";

export type CompanyMaterialIntent = {
  target_company_node_id: string; material_kind: string; source_channel: string;
  material_date: string | null; operator_title: string | null;
};
export type BoundCompanyMaterialIntent = CompanyMaterialIntent & {
  target_company_name: string; material_trust_policy: string;
  material_date_basis: string | null; intent_sha256: string;
};

export type SourceRun = {
  processing_run_id: string;
  company_material_intent?: BoundCompanyMaterialIntent | null;
  company_material_intent_sha256?: string | null;
  source_id: string;
  source_sha256: string;
  state: string;
  stage: string;
  runtime_identity: Record<string, unknown>;
  native_execution_id: string | null;
  native_checkpoint: { available: boolean; completed_stage: string };
  packet_artifact_id: string | null;
  packet_id: string | null;
  error: { code: string; stage: string; retry_safe: boolean; manual_recovery_required: boolean; operator_action: string } | null;
  jobs: CloudJob[];
  usage: { status: "KNOWN" | "UNKNOWN"; input_tokens: number | null; output_tokens: number | null; total_tokens: number | null; attempts: number };
  review: { review_id: string; status: string; required: number; completed: number; deep_link: string } | null;
  attribution: { status: string; sidecar_id: string | null; required: number; completed: number } | null;
  qualification: { object_id: string; status: string; diff_id: string } | null;
  activation_receipt: { object_id: string; status: string } | null;
  lineage: Array<{ kind: string; id: string; operation_kind?: string; packet_id?: string }>;
  created_at: string;
  updated_at: string;
};

export type PrivateSource = {
  source_id: string;
  source_sha256: string;
  size_bytes: number;
  safe_filename: string;
  mime_type: string;
  storage_artifact_id: string;
  validation: { gate: string; pages: number; ocr_used: false };
  known_canonical_source_id: string | null;
  uploaded_at: string;
  private: true;
  duplicate?: boolean;
  duplicate_code?: string | null;
  processing_runs?: SourceRun[];
  latest_run?: SourceRun | null;
};

export type SourceCapabilities = {
  source_class: "PRIVATE_CLEAN_PDF";
  mime_types: ["application/pdf"];
  max_pdf_bytes: number;
  single_file: true;
  ocr_supported: false;
};

export type SourcePage = {
  items: PrivateSource[];
  total: number;
  next_cursor: string | null;
  capabilities: SourceCapabilities;
};

export const listSourceOperations = (signal: AbortSignal) =>
  request<SourcePage>("/source-operations?limit=25", signal);
export const getSourceOperation = (id: string, signal: AbortSignal) =>
  request<PrivateSource>("/source-operations/" + encodeURIComponent(id), signal);
export const uploadSource = (file: File, csrf: string, signal: AbortSignal) =>
  request<PrivateSource>("/source-operations/upload", signal, {
    method: "POST",
    headers: { "Content-Type": "application/pdf", "X-Source-Filename": encodeURIComponent(file.name), "X-CSRF-Token": csrf },
    body: file,
  });
export const startSourceProcessing = (sourceId: string, body: object, csrf: string, signal: AbortSignal) =>
  request<{ run: SourceRun; duplicate: boolean }>("/source-operations/" + encodeURIComponent(sourceId) + "/process", signal, {
    method: "POST", headers: { "Content-Type": "application/json", "X-CSRF-Token": csrf }, body: JSON.stringify(body),
  });
