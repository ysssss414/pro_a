import type {
  ClaimResult,
  HealthResponse,
  NeighborGraph,
  NodeDetail,
  NodeSearchResult,
  NodeSource,
  StatsResponse,
} from "./types";

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/$/, "");

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, signal?: AbortSignal): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: { Accept: "application/json" },
    signal,
  });
  if (!response.ok) {
    let detail = `Knowledge API request failed (${response.status})`;
    try {
      const body = (await response.json()) as { detail?: string };
      if (body.detail) detail = body.detail;
    } catch {
      // Keep the deterministic HTTP fallback message.
    }
    throw new ApiError(detail, response.status);
  }
  return (await response.json()) as T;
}

export function getHealth(signal?: AbortSignal): Promise<HealthResponse> {
  return request<HealthResponse>("/api/health", signal);
}

export function getStats(signal?: AbortSignal): Promise<StatsResponse> {
  return request<StatsResponse>("/api/stats", signal);
}

export function searchNodes(
  query: string,
  limit = 20,
  signal?: AbortSignal,
): Promise<NodeSearchResult[]> {
  const params = new URLSearchParams({ q: query, limit: String(limit) });
  return request<NodeSearchResult[]>(`/api/nodes/search?${params.toString()}`, signal);
}

export function getNode(nodeId: string, signal?: AbortSignal): Promise<NodeDetail> {
  return request<NodeDetail>(`/api/nodes/${encodeURIComponent(nodeId)}`, signal);
}

export function getNeighbors(
  nodeId: string,
  signal?: AbortSignal,
): Promise<NeighborGraph> {
  return request<NeighborGraph>(
    `/api/nodes/${encodeURIComponent(nodeId)}/neighbors`,
    signal,
  );
}

export function getClaims(nodeId: string, signal?: AbortSignal): Promise<ClaimResult[]> {
  return request<ClaimResult[]>(
    `/api/nodes/${encodeURIComponent(nodeId)}/claims`,
    signal,
  );
}

export function getSources(nodeId: string, signal?: AbortSignal): Promise<NodeSource[]> {
  return request<NodeSource[]>(
    `/api/nodes/${encodeURIComponent(nodeId)}/sources`,
    signal,
  );
}
