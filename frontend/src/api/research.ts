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
export type CompanyMaterial = {
  material_id: string; source_id: string; processing_run_id: string | null;
  title: string; title_basis: string; material_kind: string | null;
  source_channel: string | null; material_trust_policy: string | null;
  material_date: string | null; material_date_basis: string | null;
  lifecycle: string; state: string; private: boolean; canonical: boolean;
  association_basis: string; review_status: string | null;
  attribution_status: string | null; qualification_status: string | null;
  canonical_source_id: string | null; claim_count: number | null;
  linked_node_count: number | null;
  linked_nodes: Array<{ node_id: string; canonical_name: string; primary_type: string; roles: string }> | null;
  current_view_impact_candidate_count: number | null;
  uploaded_at: string | null; publication_time: string | null;
  ingested_at: string | null; updated_at: string | null;
  packet_artifact_id: string | null; company_material_intent_sha256: string | null;
};
export type CompanyMaterialsPage = {
  company: { node_id: string; canonical_name: string; primary_type: "Company"; status: "active" };
  materials: CompanyMaterial[]; counts: { total: number; private: number; canonical: number };
  snapshot_id: string; next_cursor: string | null;
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
export type QualifiedMapNode = {
  visual_id: string; knowledge_state: "canonical" | "qualified_identity" | "relation_endpoint_reference";
  canonical_node_id: string | null; qualified_candidate_id: string | null; endpoint_reference_id: string | null;
  display_name: string; primary_type: string; distance: number; selected: boolean;
  in_navigation_context: boolean; qualification_stage?: string; qualified_reuse_candidate_ids?: string[];
};
export type QualifiedMapEdge = {
  visual_id: string; knowledge_state: "canonical" | "qualified_relation";
  canonical_relation_id: string | null; qualified_relation_id: string | null;
  from_visual_id: string; to_visual_id: string; relation_type: string; semantic_group: string;
  scope: string; from_endpoint_authority: string; to_endpoint_authority: string;
  candidate_content_sha256?: string; qualification_population_sha256?: string;
  qualification_decision_sha256?: string;
};
export type QualifiedMapResult = {
  domain_id: string; display_name: string; mode: StructureMapMode; selected_visual_id: string | null;
  selected_node_id: string | null; selected_qualified_id: string | null; depth: number;
  nodes: QualifiedMapNode[]; edges: QualifiedMapEdge[]; truncated: boolean; truncation_reasons: string[];
  omitted_reference_hierarchy_relations: number;
  stats: { canonical_nodes: number; qualified_nodes: number; endpoint_references: number;
    canonical_relations: number; qualified_relations: number };
};
export type QualifiedIdentity = {
  candidate_id: string; visual_id: string; display_name: string; primary_type: string;
  qualification_stage: string; human_decision: string; human_reason: string;
  authorization_basis: string; reviewer: string; evidence: Array<Record<string, unknown>>;
  relations: Array<Record<string, unknown>>; production_applied: false;
  candidate_content_sha256?: string; qualification_population_sha256?: string;
  qualification_decision_sha256?: string;
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
export const getResearchCompany = (id: string, signal: AbortSignal) =>
  request<CompanyMaterialsPage["company"]>("/research/companies/" + encodeURIComponent(id), signal);
export const searchResearchCompanies = (q: string, signal: AbortSignal) =>
  request<{ items: CompanyMaterialsPage["company"][] }>("/research/companies/search" + params({ q }), signal);
export const getCompanyMaterials = (id: string, cursor: string | null, signal: AbortSignal) =>
  request<CompanyMaterialsPage>("/research/companies/" + encodeURIComponent(id) + "/materials" + params({ limit: 20, cursor }), signal);
export const getResearchDomains = (signal: AbortSignal) =>
  request<{ domains: NavigationDomain[] }>("/research/domains", signal);
export const getResearchDomainTree = (domainId: string, signal: AbortSignal) =>
  request<NavigationTree>("/research/domains/" + encodeURIComponent(domainId) + "/tree", signal);
export const getResearchStructureMap = (domainId: string, mode: StructureMapMode, nodeId: string,
  depth: number, signal: AbortSignal) => request<StructureMapResult>("/research/domains/" +
  encodeURIComponent(domainId) + "/structure-map" + params({ mode, node_id: nodeId, depth: mode === "focus" ? depth : null }), signal);
export const getQualifiedStructureMap = (domainId: string, mode: StructureMapMode, nodeId: string,
  qualifiedId: string, depth: number, signal: AbortSignal) => request<QualifiedMapResult>("/research/domains/" +
  encodeURIComponent(domainId) + "/qualified-structure-map" +
  params({ mode, node_id: nodeId, qualified_id: qualifiedId, depth: mode === "focus" ? depth : null }), signal);
export const getQualifiedOverlaySummary = (signal: AbortSignal) => request<any>("/research/qualified-overlay", signal);
export const getQualifiedGovernance = (signal: AbortSignal) => request<any>("/research/qualified-overlay/governance", signal);
export const searchQualified = (q: string, signal: AbortSignal) =>
  request<{ results: Array<{ candidate_id: string; display_name: string; primary_type: string;
    qualification_stage: string }> }>("/research/qualified-overlay/search" + params({ q }), signal);
export const getQualifiedNode = (id: string, signal: AbortSignal) =>
  request<QualifiedIdentity>("/research/qualified-overlay/nodes/" + encodeURIComponent(id), signal);
export const getQualifiedRelation = (id: string, signal: AbortSignal) =>
  request<any>("/research/qualified-overlay/relations/" + encodeURIComponent(id), signal);
export const getQualifiedCanonicalProvenance = (id: string, signal: AbortSignal) =>
  request<any>("/research/qualified-overlay/canonical/" + encodeURIComponent(id), signal);
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
