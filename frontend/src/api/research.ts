import { request } from "./workbench";

export type ResearchRouteKind = "home" | "node" | "claim" | "source" | "relation" | "coverage" | "claims" | "sources";
export type SearchResult = {
  object_type: "NODE" | "CLAIM" | "SOURCE" | "RESEARCH_QUESTION" | "GAP";
  object_id: string;
  label: string;
  subtitle: string;
  status: string;
  node_type?: string;
  node_id?: string;
  matched_aliases?: string[];
};
export type Note = {
  note_id: string; object_type: string; object_id: string; text: string;
  status: "OPEN" | "DONE" | "DEFERRED"; revision: number; operator: string;
  created_at: string; updated_at: string;
  route_kind?: ResearchRouteKind; route_id?: string;
};
export type NavigationNode = {
  node_id: string; canonical_name: string; primary_type: string; status: string;
  depth: number; child_count: number; has_children: boolean; children: NavigationNode[];
  anomaly?: "cycle" | "duplicate_path";
};
export type NavigationDomain = {
  domain_id: string; display_name: string; root_count: number;
  visible_node_count: number; max_tree_depth: number; truncated: boolean;
  domain_pack_lifecycle: string; domain_pack_registered: boolean;
};
export type NavigationTree = {
  domain_id: string; display_name: string; roots: NavigationNode[];
  visible_node_count: number; max_tree_depth: number; truncated: boolean;
  truncation_reasons: string[]; snapshot_id: string;
};
export type NodeDomainContext = {
  node_id: string;
  navigation_contexts: { domain_id: string; display_name: string; root_node_id: string;
    path_from_root: string[]; depth: number }[];
  operational_domain_assignments: { primary_domain: string; revision: number }[];
};
export type StructureMapMode = "hierarchy" | "relationship" | "focus";
export type StructureMapNode = {
  node_id: string; canonical_name: string; primary_type: string; status: string;
  distance: number; selected: boolean; in_navigation_context: boolean; navigation_depth: number | null;
  on_selected_path?: boolean;
};
export type StructureMapEdge = {
  relation_id: string; from_node_id: string; to_node_id: string; relation_type: string;
  semantic_group: string; scope: string; status: string; confidence: number | null;
  on_selected_path?: boolean;
};
export type StructureMapResult = {
  domain_id: string; display_name: string; mode: StructureMapMode; selected_node_id: string | null;
  depth: number; nodes: StructureMapNode[]; edges: StructureMapEdge[];
  stats: { node_count: number; edge_count: number }; available_relation_types: string[];
  truncated: boolean; truncation_reasons: string[]; snapshot_id: string;
};

function params(values: Record<string, string | number | boolean | null | undefined>) {
  const search = new URLSearchParams();
  Object.entries(values).forEach(([key, value]) => {
    if (value !== "" && value !== null && value !== undefined) search.set(key, String(value));
  });
  const encoded = search.toString();
  return encoded ? "?" + encoded : "";
}

export const getResearchHome = (signal: AbortSignal) => request<any>("/research/home", signal);
export const searchResearch = (q: string, objectType: string, signal: AbortSignal) =>
  request<{ query: string; results: SearchResult[] }>("/research/search" + params({ q, object_type: objectType, limit: 30 }), signal);
export const getResearchNode = (id: string, signal: AbortSignal) =>
  request<any>("/research/nodes/" + encodeURIComponent(id), signal);
export const getResearchDomains = (signal: AbortSignal) =>
  request<{ domains: NavigationDomain[] }>("/research/domains", signal);
export const getResearchDomainTree = (domainId: string, signal: AbortSignal) =>
  request<NavigationTree>("/research/domains/" + encodeURIComponent(domainId) + "/tree", signal);
export const getResearchStructureMap = (domainId: string, mode: StructureMapMode, nodeId: string,
  depth: number, signal: AbortSignal) => request<StructureMapResult>("/research/domains/" +
  encodeURIComponent(domainId) + "/structure-map" + params({ mode, node_id: nodeId, depth: mode === "focus" ? depth : null }), signal);
export const getNodeDomainContext = (nodeId: string, signal: AbortSignal) =>
  request<NodeDomainContext>("/research/nodes/" + encodeURIComponent(nodeId) + "/domain-context", signal);
export const getResearchClaim = (id: string, signal: AbortSignal) =>
  request<any>("/research/claims/" + encodeURIComponent(id), signal);
export const getResearchSource = (id: string, filters: Record<string, string>, signal: AbortSignal) =>
  request<any>("/research/sources/" + encodeURIComponent(id) + params(filters), signal);
export const getResearchRelation = (id: string, signal: AbortSignal) =>
  request<any>("/research/relations/" + encodeURIComponent(id), signal);
export const getResearchCoverage = (cursor: string, signal: AbortSignal) =>
  request<any>("/research/coverage" + params({ cursor, limit: 25 }), signal);
export const getResearchClaims = (filters: Record<string, string>, signal: AbortSignal) =>
  request<any>("/research/claims" + params({ ...filters, limit: 25 }), signal);
export const getResearchSources = (filters: Record<string, string>, signal: AbortSignal) =>
  request<any>("/research/sources" + params({ ...filters, limit: 25 }), signal);
export const createNote = (body: object, csrf: string, signal: AbortSignal) =>
  request<{ note: Note }>("/research/notes", signal, {
    method: "POST", headers: { "Content-Type": "application/json", "X-CSRF-Token": csrf }, body: JSON.stringify(body),
  });
export const updateNote = (id: string, body: object, csrf: string, signal: AbortSignal) =>
  request<{ note: Note }>("/research/notes/" + encodeURIComponent(id), signal, {
    method: "PUT", headers: { "Content-Type": "application/json", "X-CSRF-Token": csrf }, body: JSON.stringify(body),
  });
