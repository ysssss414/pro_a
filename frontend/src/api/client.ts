import type {
  ClaimResult,
  ClaimImpactCandidatesResult,
  CurrentViewCompareResult,
  CurrentViewHistoryResult,
  CurrentViewResult,
  HealthResponse,
  KnowledgeGapResult,
  NeighborGraph,
  NodeDetail,
  NodeSearchResult,
  NodeSource,
  ResearchQuestionResult,
  SourceDetail,
  SourceImpactCandidatesResult,
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

export function getCurrentView(
  nodeId: string,
  signal?: AbortSignal,
): Promise<CurrentViewResult | null> {
  return request<CurrentViewResult | null>(
    `/api/nodes/${encodeURIComponent(nodeId)}/current-view`,
    signal,
  );
}

export function getCurrentViewHistory(
  nodeId: string,
  signal?: AbortSignal,
): Promise<CurrentViewHistoryResult> {
  return request<CurrentViewHistoryResult>(
    `/api/nodes/${encodeURIComponent(nodeId)}/current-view-history`,
    signal,
  );
}

export function getCurrentViewCompare(
  nodeId: string,
  baseViewId: string,
  targetViewId: string,
  signal?: AbortSignal,
): Promise<CurrentViewCompareResult> {
  const params = new URLSearchParams({
    base_view_id: baseViewId,
    target_view_id: targetViewId,
  });
  return request<CurrentViewCompareResult>(
    `/api/nodes/${encodeURIComponent(nodeId)}/current-view-compare?${params.toString()}`,
    signal,
  );
}

export function getResearchQuestion(
  nodeId: string,
  signal?: AbortSignal,
): Promise<ResearchQuestionResult | null> {
  return request<ResearchQuestionResult | null>(
    `/api/nodes/${encodeURIComponent(nodeId)}/research-question`,
    signal,
  );
}

export function getKnowledgeGaps(
  nodeId: string,
  signal?: AbortSignal,
): Promise<KnowledgeGapResult[]> {
  return request<KnowledgeGapResult[]>(
    `/api/nodes/${encodeURIComponent(nodeId)}/knowledge-gaps`,
    signal,
  );
}

export function getSourceDetail(
  sourceId: string,
  signal?: AbortSignal,
): Promise<SourceDetail> {
  return request<SourceDetail>(
    `/api/sources/${encodeURIComponent(sourceId)}`,
    signal,
  );
}

export function getSourceImpactCandidates(
  sourceId: string,
  signal?: AbortSignal,
): Promise<SourceImpactCandidatesResult> {
  return request<SourceImpactCandidatesResult>(
    `/api/sources/${encodeURIComponent(sourceId)}/impact-candidates`,
    signal,
  );
}

export function getClaimImpactCandidates(
  claimId: string,
  signal?: AbortSignal,
): Promise<ClaimImpactCandidatesResult> {
  return request<ClaimImpactCandidatesResult>(
    `/api/claims/${encodeURIComponent(claimId)}/impact-candidates`,
    signal,
  );
}
