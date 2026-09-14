export type NativeItem = {
  candidate_id: string;
  candidate_type: string;
  content: Record<string, unknown>;
  content_sha256: string;
  allowed_decisions: string[];
  decision_effects: Record<string, unknown>;
};

export type PacketSummary = {
  artifact_id: string;
  packet_id: string;
  run_id: string;
  mode: "PRIVATE" | "DEMO";
  validation_state: string;
  source: { source_id: string; source_sha256: string; size_bytes: number; source_type: string };
  summary: Record<string, string | number>;
};

export type ReviewPacket = PacketSummary & {
  packet_file_sha256: string;
  immutable_packet_sha256: string;
  packet_status: string;
  items: NativeItem[];
  excluded_relation_inventory: { count: number; candidate_ids: string[]; policy: string; relation_review_reopened: boolean };
  capabilities: { read_only: boolean; decision_save_available: boolean; native_decisions_are_metadata_only: boolean };
  review?: { enabled: false } | PersistentReview;
  attribution_available?: boolean;
};

export type DecisionState = { decision: string; reason: string; target_node_id: string; reviewer: string; actor: string; session_id: string; revision: number; updated_at: string };
export type ReviewRow = { candidate_id: string; state: DecisionState | null; queues: string[]; available_decisions: string[];
  blocked_decisions: Record<string, string>; reuse_target: string | null; undo_event_id: number | null; decision_effect: string | null; nonpromotable: boolean };
export type ReviewAudit = { event_id: number; candidate_id: string | null; event_type: string; reviewer: string; actor: string;
  reason: string; revision: number; created_at: string; old_state: Record<string, unknown> | null; new_state: Record<string, unknown> | null };
export type ReviewProgress = { total_native_rows: number; required: number; completed: number; remaining: number; excluded: number;
  deferred: number; nonpromotable: number; warnings: number; invalid: number; dependency_blocked: number };
export type PersistentReview = { enabled: true; basis_id: string; review_id: string; reviewer: string; revision: number; status: "DRAFT" | "SEALED";
  progress: ReviewProgress; rows: ReviewRow[]; audit: ReviewAudit[]; sealed: { objects: { kind: string; object_id: string; sha256: string }[];
    validation: Record<string, unknown>; production_authorized: false; qualification_created: false } | null };
export type ReviewOperation = { basis_id: string; expected_revision: number; operation_id: string; reviewer: string; reason: string };
export type DecisionOperation = ReviewOperation & { candidate_id: string; decision: string; target_node_id: string };

const messages: Record<string, string> = {
  REVISION_CONFLICT: "This review changed in another tab. Your attempted decision is preserved. Inspect the refreshed state and explicitly retry.",
  IDEMPOTENCY_CONFLICT: "This operation identity was already used for a different request. Refresh and reconcile before retrying.",
  VALIDATION_ERROR: "The native review rules reject this input. Check the decision, reason and exact target.",
  DEPENDENCY_INVALID: "Parent CREATE requires a compatible child Node CREATE.",
  IMMUTABLE_FIELD_DRIFT: "The immutable review basis changed. Review is blocked.",
  ARTIFACT_IDENTITY_MISMATCH: "The registered artifact identity does not match. Review is blocked.",
  ALREADY_SEALED: "This review is sealed and read-only.",
  NOT_REVIEWABLE: "This item is excluded or not independently reviewable.",
  RECOVERY_REQUIRED: "Review storage requires operator recovery. No automatic repair was made.",
  REVIEWER_MISMATCH: "Use the named reviewer already bound to this review.",
  UNDO_NOT_AVAILABLE: "Only the most recent Save for this item can be undone before sealing.",
  ATTRIBUTION_DEFERRED: "Deferred attribution blocks qualification. No canonical changes were authorized.",
  ATTRIBUTION_INCOMPLETE: "Every accepted Claim requires an explicit attribution outcome before sealing.",
  ATTRIBUTION_BASIS_MISMATCH: "The attribution basis differs from the sealed native review. Refresh and inspect the identities.",
  ATTRIBUTION_ROLE_INVALID: "Choose a native subject, context or related role explicitly for each link.",
  ATTRIBUTION_LINK_COUNT_INVALID: "LINK needs one Node; MULTI_LINK needs two or more. NO_LINK and DEFER have no links.",
  STALE_BASELINE: "The canonical baseline changed. Qualification cannot be applied against this baseline.",
  RECEIPT_NOT_REGISTERED: "An external operator must register a verified execution receipt first.",
  NODE_QUALIFICATION_BLOCKED: "Native Node qualification is blocked by identity, collision or exact REUSE constraints. No package was staged.",
  PARENT_QUALIFICATION_BLOCKED: "Parent placement failed native qualification. Inspect the child and parent identities.",
  CLAIM_QUALIFICATION_BLOCKED: "The accepted Claim set does not match the qualified canonical inserts.",
  SOURCE_MATERIALIZATION_MISMATCH: "Materialized Source bytes do not match the sealed evidence basis.",
  ATTRIBUTION_NODE_INVALID: "Select an exact Node identity from this sealed review's CREATE or REUSE results.",
  ATTRIBUTION_SCOPE_MISMATCH: "Attribution scope must match the immutable Claim scope.",
  VIEW_NOT_FOUND: "No eligible Current View or Node was found.",
  UNSUPPORTED_NODE_TYPE: "Stage 3 View maintenance supports Company and Product Nodes only.",
  INITIAL_VIEW_RACE: "An official View now exists. This initial draft is stale and cannot become an update automatically.",
  BASELINE_STALE: "The official View or evidence basis changed. Explicit re-evaluation is required.",
  EVIDENCE_NOT_FOUND: "A selected evidence identity is no longer available.",
  PRIMARY_EVIDENCE_INVALID: "Primary Evidence must consist only of eligible Subject Claims.",
  QUALITY_VALIDATION_FAILED: "The existing Current View quality contract rejected this draft.",
  NO_EFFECTIVE_CHANGE: "The deterministic comparison found no effective structured change.",
  DRAFT_IDENTITY_MISMATCH: "The persisted draft identity or revision no longer matches.",
  PACKAGE_NOT_REGISTERED: "The qualified View package is not registered.",
  RECEIPT_MISMATCH: "The activation receipt does not match the qualified package.",
  IMPACT_PATH_NOT_FOUND: "This direct evidence path no longer exists in the current snapshot.",
  UNSUPPORTED_RELATION_TYPE: "This recorded relationship is outside the direct-impact contract.",
  EVIDENCE_NOT_RESOLVED: "The recorded evidence identity could not be resolved.",
  STALE_SNAPSHOT: "The evidence snapshot changed. Refresh before recording an attention outcome.",
  TARGET_NOT_FOUND: "The requested recorded object was not found.",
  NONCURRENT_RELATION: "The requested relationship or View is not current.",
  AMBIGUOUS_TEMPORAL_STATE: "The recorded temporal state is ambiguous.",
  IMPACT_SCHEMA_REQUIRED: "Prepare the Stage 4 Workbench schema before using Changes & Impact.",
};

export class WorkbenchError extends Error {
  constructor(public status: number, public code = "", public currentRevision?: number) {
    super(status === 401 ? "Sign in to the Workbench." : messages[code] ?? "Workbench request unavailable. Verify the registered packet and application configuration.");
  }
}

const prefix = "/api/workbench/v1";
export async function request<T>(path: string, signal: AbortSignal, options: RequestInit = {}): Promise<T> {
  const response = await fetch(prefix + path, {
    signal, credentials: "same-origin", cache: "no-store",
    ...options,
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new WorkbenchError(response.status, typeof error.detail === "string" && error.detail in messages ? error.detail : "",
      typeof error.current_revision === "number" ? error.current_revision : undefined);
  }
  return response.json() as Promise<T>;
}

export const getSession = (signal: AbortSignal) => request<{ actor: string; mode: string; csrf_token?: string }>("/session", signal);
export const loginWorkbench = (token: string, signal: AbortSignal) => request("/session", signal, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ token }) });
export const listPackets = (signal: AbortSignal) => request<{ packets: PacketSummary[] }>("/review-packets", signal);
export const getPacket = (id: string, signal: AbortSignal) => request<ReviewPacket>("/reviews/" + encodeURIComponent(id), signal);

export function mutateReview(id: string, action: "decisions" | "undo" | "validate" | "seal", body: object, csrf: string, signal: AbortSignal) {
  return request<{ revision: number; validation?: Record<string, unknown> }>("/reviews/" + encodeURIComponent(id) + "/" + action, signal,
    { method: "POST", headers: { "Content-Type": "application/json", "X-CSRF-Token": csrf }, body: JSON.stringify(body) });
}

export type ViewEvidence = {
  claim_id: string; statement: string; nature: string; status: string; confidence: number | null;
  role: "subject" | "context" | "related"; scope: string; attributed_to: string;
  evidence_excerpt: string; evidence_pointer: string; source_locator: Record<string, unknown> | null;
  source: { source_id: string; title: string; publication_time: string; source_rank: string; source_type: string; organization: string; sha256: string };
  business_date: string | null; freshness_basis: string; primary_eligible: boolean; evidence_class?: "PRIMARY" | "CONTEXT_ONLY";
  resolved?: boolean; officially_referenced?: boolean;
};

export type PersistedViewDraft = {
  draft_id: string; revision: number; reviewer: string; status: "DRAFT" | "VALIDATED" | "STALE";
  basis_sha256: string; updated_at: string; mode: "INITIAL" | "UPDATE"; expected_official_view_id: string;
  content: Record<string, unknown>; primary_claim_ids: string[]; context_claim_ids: string[];
  change_level: "initial" | "minor" | "material" | "thesis"; quality_validation: Record<string, unknown> | null;
  audit: Array<{ revision: number; action: string; reviewer: string; reason: string; updated_at: string }>;
};

export type CurrentViewWorkbenchState = {
  node: { node_id: string; canonical_name: string; primary_type: string; status: string };
  selection_rule: string; official: import("./types").CurrentViewResult | null;
  previous_official: import("./types").CurrentViewResult | null;
  history: import("./types").CurrentViewResult[]; baseline_views: import("./types").CurrentViewResult[];
  history_labels: Array<{ view_id: string; state: "OFFICIAL" | "PRIOR_OFFICIAL" }>;
  official_comparison: Record<string, unknown> | null;
  official_evidence: Array<Partial<ViewEvidence> & { claim_id: string; resolved: boolean; officially_referenced: boolean; evidence_class: "PRIMARY" | "CONTEXT_ONLY"; error?: string }>;
  available_evidence: ViewEvidence[]; freshness: Array<{ claim_id: string; business_date: string | null; basis: string }>;
  uncertainty: Record<string, string[]>; basis_sha256: string; draft: PersistedViewDraft | null;
  activation_packages: Array<{ object_id: string; draft_revision: number; predicted_diff: Record<string, unknown>; production_authorized: false }>;
  activation_receipts: Array<{ object_id: string; package_id: string; status: string }>;
  capabilities: { initial_supported: boolean; update_supported: boolean; browser_activation: false; canonical_write: false };
};

export const getViewWorkbench = (nodeId: string, signal: AbortSignal) =>
  request<CurrentViewWorkbenchState>("/current-views/" + encodeURIComponent(nodeId), signal);

export const saveViewDraft = (nodeId: string, body: object, csrf: string, signal: AbortSignal) =>
  request<{ draft_id: string; revision: number; status: string; basis_sha256: string }>("/current-views/" + encodeURIComponent(nodeId) + "/draft", signal,
    { method: "PUT", headers: { "Content-Type": "application/json", "X-CSRF-Token": csrf }, body: JSON.stringify(body) });

export const validateViewDraft = (nodeId: string, body: object, csrf: string, signal: AbortSignal) =>
  request<{ draft_id: string; revision: number; status: string; quality_validation: Record<string, unknown> }>("/current-views/" + encodeURIComponent(nodeId) + "/validate", signal,
    { method: "POST", headers: { "Content-Type": "application/json", "X-CSRF-Token": csrf }, body: JSON.stringify(body) });

export const qualifyViewDraft = (nodeId: string, draftId: string, revision: number, csrf: string, signal: AbortSignal) =>
  request<{ object_id: string; adapter_version: string; production_authorized: false; predicted_diff: Record<string, unknown>; operator_action: string }>("/current-views/" + encodeURIComponent(nodeId) + "/qualify", signal,
    { method: "POST", headers: { "Content-Type": "application/json", "X-CSRF-Token": csrf }, body: JSON.stringify({ draft_id: draftId, revision }) });

export const reconcileViewReceipt = (nodeId: string, objectId: string, csrf: string, signal: AbortSignal) =>
  request<{ status: "VERIFIED"; receipt_id: string; package_id: string; official_view_id: string }>("/current-views/" + encodeURIComponent(nodeId) + "/reconcile", signal,
    { method: "POST", headers: { "Content-Type": "application/json", "X-CSRF-Token": csrf }, body: JSON.stringify({ object_id: objectId }) });

export type ImpactPathStep = {
  object_type: "SOURCE" | "CLAIM" | "NODE" | "VIEW" | "VIEW_DRAFT" | "CLAIM_RELATION" | "RELATION";
  object_id: string;
  label: string;
  status: string;
};

export type ImpactAttentionState = {
  outcome: "NO_CHANGE" | "MINOR" | "MATERIAL" | "THESIS";
  revision: number;
  reviewer: string;
  actor: string;
  reason: string;
  updated_at: string;
  status: "CURRENT" | "STALE";
  snapshot_id: string;
};

export type DirectImpactItem = {
  impact_id: string;
  impact_type: string;
  origin_type: "SOURCE";
  origin_id: string;
  target_type: string;
  target_id: string;
  path_steps: ImpactPathStep[];
  relationship_types: string[];
  attribution_role: "subject" | "context" | "related" | null;
  official_or_staged: "OFFICIAL" | "STAGED" | "RECORDED" | "CURRENT" | "CATEGORICAL" | "HISTORICAL";
  reason_code: string;
  evidence_refs: Array<Record<string, string>>;
  temporal_status: Record<string, unknown>;
  current_status: string;
  is_current_impact: boolean;
  snapshot_id: string;
  attention_state: ImpactAttentionState | null;
};

export type ImpactChange = {
  source: { source_id: string; title: string; publication_time: string; ingested_at: string; status: string; source_type: string; source_rank: string };
  evidence_date: string;
  current_status: string;
  claim_count: number;
  claims: Array<{ claim_id: string; statement: string; status: string; fact_time: string; publication_time: string }>;
  snapshot_id: string;
  items: DirectImpactItem[];
};

export type ImpactChangesResult = {
  snapshot: { snapshot_id: string; knowledge_sha256: string; workbench_projection_sha256: string; cache: "NONE"; consistency: string; query_count: number };
  changes: ImpactChange[];
  items: DirectImpactItem[];
  limit: number;
  offset: number;
};

export const getImpactChanges = (signal: AbortSignal) =>
  request<ImpactChangesResult>("/impact/changes?limit=50&offset=0", signal);

export const saveImpactAttention = (impactId: string, body: object, csrf: string, signal: AbortSignal) =>
  request<{ attention_state: ImpactAttentionState; canonical_write: false; production_authorized: false }>(
    "/impact/item/" + encodeURIComponent(impactId) + "/attention", signal,
    { method: "PUT", headers: { "Content-Type": "application/json", "X-CSRF-Token": csrf }, body: JSON.stringify(body) },
  );
