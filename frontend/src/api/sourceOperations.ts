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
  community_provenance?: { bundle_id: string; bundle_sha256: string; topic_count: number; group_id: string; date_min: string | null; date_max: string | null; pdf_sha256: string; trust_policy: string } | null;
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

export type OperationalCapacity = {
  enabled: boolean;
  policy_version: string | null;
  capacity_policy_version?: string;
  operational_pending_rows?: number;
  operational_pending_review_rows?: number;
  native_pending_rows?: number;
  native_pending_review_rows?: number;
  historical_lifecycle_closed?: number;
  lifecycle_resolved_rows?: number;
  human_user_qualified?: number;
  ai_policy_closed?: number;
  followup_governance?: number;
  wip_state?: "OPEN" | "SOFT_WARNING" | "HARD_STOP";
  new_intake_allowed?: boolean;
  pending_semantics?: "OPERATIONAL_PENDING";
};

export const listSourceOperations = (signal: AbortSignal) =>
  request<SourcePage>("/source-operations?limit=25", signal);
export const getOperationalCapacity = (signal: AbortSignal) =>
  request<OperationalCapacity>("/operations/capacity", signal);
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

export type CommunityPreview = {
  target_company: { node_id: string; canonical_name: string };
  company_input: string; group_id: string; group_label: string;
  topic_count: number; date_min: string | null; date_max: string | null;
  bundle_id: string; bundle_sha256: string; trust_policy: string;
};
export const previewCommunity = (file: File, companyId: string, csrf: string, signal: AbortSignal) =>
  request<CommunityPreview>("/source-operations/community-preview", signal, {
    method: "POST", headers: { "Content-Type": "application/zip", "X-Company-Node-ID": companyId, "X-CSRF-Token": csrf }, body: file,
  });
export const getCommunityDomains = (signal: AbortSignal) =>
  request<{ items: Array<{ domain_id: string; version: string; sha256: string }> }>("/source-operations/community-domains", signal);
export const importCommunity = (file: File, companyId: string, domainId: string, csrf: string, signal: AbortSignal) =>
  request<{ preview: CommunityPreview; source: PrivateSource; run: SourceRun; duplicate: boolean }>("/source-operations/community-import", signal, {
    method: "POST", headers: { "Content-Type": "application/zip", "X-Company-Node-ID": companyId,
      "X-Primary-Domain": domainId, "X-CSRF-Token": csrf }, body: file,
  });
