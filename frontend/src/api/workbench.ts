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
};

export class WorkbenchError extends Error {
  constructor(public status: number, public code = "", public currentRevision?: number) {
    super(status === 401 ? "Sign in to the Workbench." : messages[code] ?? "Workbench request unavailable. Verify the registered packet and application configuration.");
  }
}

const prefix = "/api/workbench/v1";
async function request<T>(path: string, signal: AbortSignal, options: RequestInit = {}): Promise<T> {
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
