export interface HealthResponse {
  status: "ok";
}

export interface StatsResponse {
  active_node_count: number;
  alias_count: number;
  current_relation_count: number;
  current_part_of_count: number;
  source_count: number;
  claim_count: number;
  current_view_count: number;
  open_knowledge_gap_count: number;
  open_research_question_count: number;
}

export interface NodeSummary {
  node_id: string;
  canonical_name: string;
  primary_type: string;
}

export interface NodeSearchResult extends NodeSummary {
  matched_by: "canonical_name" | "alias";
  matched_text: string;
}

export interface RelationResult {
  relation_id: string;
  from_node_id: string;
  relation_type: string;
  to_node_id: string;
  scope: string;
  status: string;
  confidence: number | null;
  from_canonical_name: string;
  to_canonical_name: string;
}

export interface NodeDetail extends NodeSummary {
  description: string;
  status: string;
  aliases: string[];
  parents: NodeSummary[];
  children: NodeSummary[];
  incoming_relations: RelationResult[];
  outgoing_relations: RelationResult[];
}

export interface NeighborGraph {
  center: NodeSummary;
  nodes: NodeSummary[];
  edges: RelationResult[];
}

export interface SourceMetadata {
  source_id: string;
  title: string;
  original_name: string;
  author: string;
  organization: string;
  publication_time: string;
  source_type: string;
  source_rank: string;
}

export interface ClaimResult {
  claim_id: string;
  statement: string;
  nature: string;
  fact_time: string;
  publication_time: string;
  status: string;
  confidence: number | null;
  novelty_level: string;
  attributed_to: string;
  scope: string;
  evidence_pointer: string;
  evidence_excerpt: string;
  source_id: string;
  source: SourceMetadata;
}

export interface SourceProvenance {
  origin_path: "direct" | "claim";
  role: string;
  link_origin: string;
  evidence_excerpt: string;
  claim_id: string | null;
}

export interface NodeSource extends SourceMetadata {
  provenance: SourceProvenance[];
}
