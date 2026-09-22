import type { Note } from "../api/research";

export type InspectorClaim = {
  claim_id: string; statement: string; business_date: string; status: string;
  source_id: string; source_title: string; evidence_excerpt?: string | null;
  confidence?: number | null; linked_nodes: { node_id: string; role: string }[];
};
export type InspectorSource = {
  source_id: string; title: string; source_type: string; source_rank: string;
  publication_time?: string | null; ingested_at?: string | null; organization?: string | null;
};
export type InspectorRelation = {
  relation_id: string; from_name: string; to_name: string; relation_type: string;
  status: string; evidence_count: number;
};
export type InspectorGap = {
  gap_id: string; title: string; status: string; freshness_due?: string | null; description?: string | null;
};
export type InspectorImpact = {
  impact_id: string; reason_code: string; official_or_staged: string;
  relationship_types: string[]; path_steps: { object_type: string; object_id: string; label: string; status: string }[];
};
export type InspectorView = {
  version: string; change_level?: string | null; revision_date?: string | null; confirmed_at?: string | null;
  trigger_claim_ids: string[];
  content_json?: { one_line_conclusion?: string; core_logic?: string[]; key_facts?: string[];
    recent_change?: string; investment_implication?: string; major_risks?: string[]; key_watch_items?: string[] } | null;
};
export type InspectorData = {
  node: { node_id: string; canonical_name: string; primary_type: string; status: string;
    aliases: string[]; description?: string | null };
  current_view: InspectorView | null;
  claims: { items: InspectorClaim[]; total: number; limit: number };
  sources: InspectorSource[]; relations: InspectorRelation[];
  research_question: { question: string; current_answer?: string | null; status: string;
    confidence?: number | null; key_variables?: string[] } | null;
  knowledge_gaps: InspectorGap[];
  impact: { items: InspectorImpact[] };
  notes: Note[];
  coverage: { knowledge_level?: string; claims?: number; sources: number; official_views?: number;
    questions?: number; gaps?: number };
};

export type SelectedClaim = { claim: InspectorClaim; label: string };
const roleOrder = ["subject", "context", "related"];
const byDateAndId = (a: InspectorClaim, b: InspectorClaim) =>
  b.business_date.localeCompare(a.business_date) || a.claim_id.localeCompare(b.claim_id);

// Only exact records on the bounded Node Claim page can be selected.
export function selectInspectorClaims(data: InspectorData): SelectedClaim[] {
  const available = new Map(data.claims.items.map((claim) => [claim.claim_id, claim]));
  const chosen: SelectedClaim[] = [];
  const seen = new Set<string>();
  for (const id of data.current_view?.trigger_claim_ids ?? []) {
    const claim = available.get(id);
    if (claim && !seen.has(id)) { chosen.push({ claim, label: "Official View evidence" }); seen.add(id); }
  }
  for (const role of roleOrder) {
    for (const claim of [...data.claims.items].sort(byDateAndId)) {
      if (seen.has(claim.claim_id) || !claim.linked_nodes.some((link) => link.node_id === data.node.node_id && link.role === role)) continue;
      chosen.push({ claim, label: `${role[0].toUpperCase()}${role.slice(1)} Claim` }); seen.add(claim.claim_id);
    }
  }
  return chosen;
}

export function selectLatestEvidence(data: InspectorData): InspectorClaim[] {
  return [...data.claims.items].sort(byDateAndId);
}

export function selectOpenGaps(data: InspectorData): InspectorGap[] {
  return data.knowledge_gaps.filter((gap) => ["open", "reopened", "needs_refresh"].includes(gap.status));
}

export function selectRelatedSources(data: InspectorData, limit = data.sources.length): InspectorSource[] {
  return data.sources.slice(0, limit);
}

export function relationSummary(data: InspectorData) {
  const statuses: Record<string, number> = {};
  const types: Record<string, number> = {};
  for (const relation of data.relations) {
    statuses[relation.status] = (statuses[relation.status] ?? 0) + 1;
    types[relation.relation_type] = (types[relation.relation_type] ?? 0) + 1;
  }
  return { count: data.relations.length, statuses, types };
}

export function currentViewSummary(view: InspectorView | null) {
  const content = view?.content_json;
  return { conclusion: content?.one_line_conclusion ?? "",
    support: [...(content?.core_logic ?? []), ...(content?.key_facts ?? [])].slice(0, 3),
    recentChange: content?.recent_change ?? "" };
}
