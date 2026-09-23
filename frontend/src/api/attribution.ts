import { request } from "./workbench";

export type AttributionDecision = { outcome: string; links: { node_id: string; role: string }[]; scope: string; reviewer: string; reason: string };
export type AttributionState = {
  basis_id: string; revision: number; reviewer: string; status: "DRAFT" | "SEALED"; required: number; completed: number;
  claims: { candidate_id: string; content: Record<string, unknown>; scope: string }[];
  nodes: { node_id: string; candidate_id: string | null; decision: string; content: Record<string, unknown>;
    authority?: string; provenance?: string[]; operator_routing_only?: boolean }[];
  decisions: Record<string, AttributionDecision>; roles: Record<string, string>; audit: Record<string, unknown>[];
  sidecar: { object_id: string } | null;
  qualification: { object_id: string; adapter_version: string; status: string; baseline_sha256: string; diff_id: string;
    changes: Record<string, unknown>[]; tables_touched: string[]; shadow_validation: Record<string, unknown>; operator_action: string } | null;
  receipt: { object_id: string; status: string; actual_mutation_counts: Record<string, number> } | null;
};
export const getAttribution = (handle: string, signal: AbortSignal) => request<AttributionState>("/attribution/" + encodeURIComponent(handle), signal);
export function mutateAttribution(handle: string, action: string, body: object, csrf: string, signal: AbortSignal) {
  return request<Record<string, unknown>>("/attribution/" + encodeURIComponent(handle) + "/" + action, signal,
    { method: "POST", headers: { "Content-Type": "application/json", "X-CSRF-Token": csrf }, body: JSON.stringify(body) });
}
