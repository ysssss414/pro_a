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
};

export class WorkbenchError extends Error {
  constructor(public status: number) {
    super(status === 401 ? "Sign in to the Workbench." : "Workbench request unavailable. Verify the registered packet and application configuration.");
  }
}

const prefix = "/api/workbench/v1";
async function request<T>(path: string, signal: AbortSignal, token?: string): Promise<T> {
  const response = await fetch(prefix + path, {
    signal, credentials: "same-origin", cache: "no-store",
    ...(token === undefined ? {} : { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ token }) }),
  });
  if (!response.ok) throw new WorkbenchError(response.status);
  return response.json() as Promise<T>;
}

export const getSession = (signal: AbortSignal) => request<{ actor: string; mode: string }>("/session", signal);
export const loginWorkbench = (token: string, signal: AbortSignal) => request("/session", signal, token);
export const listPackets = (signal: AbortSignal) => request<{ packets: PacketSummary[] }>("/review-packets", signal);
export const getPacket = (id: string, signal: AbortSignal) => request<ReviewPacket>("/review-packets/" + encodeURIComponent(id), signal);
