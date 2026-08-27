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
  link_role: "subject" | "context" | "related";
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

export interface CurrentViewResult {
  view_id: string;
  node_id: string;
  version: string;
  status: string;
  change_level: string;
  previous_view_id: string | null;
  content_md: string;
  content_json: CurrentViewContent;
  trigger_source_id: string | null;
  trigger_claim_ids: string[];
  revision_date: string;
  revision_seq: number;
  accepted_proposal_id: string;
  created_at: string;
  confirmed_at: string;
}

export interface CurrentViewHistoryResult {
  node_id: string;
  views: CurrentViewResult[];
}

export interface CurrentViewContent {
  one_line_conclusion?: unknown;
  core_logic?: unknown;
  key_facts?: unknown;
  core_disagreements?: unknown;
  assumptions_to_verify?: unknown;
  investment_implication?: unknown;
  major_risks?: unknown;
  knowledge_gaps?: unknown;
  key_watch_items?: unknown;
  recent_change?: unknown;
  evidence_claim_ids?: unknown;
  type_specific?: unknown;
  [key: string]: unknown;
}

export interface ResearchClaimSummary {
  claim_id: string;
  statement: string | null;
  status: string | null;
  confidence: number | null;
}

export interface ResearchQuestionResult {
  rq_id: string;
  node_id: string;
  question: string;
  importance: string;
  current_answer: string;
  confidence: number | null;
  supporting_claim_ids: string[];
  opposing_claim_ids: string[];
  key_variables: unknown[];
  supporting_claims: ResearchClaimSummary[];
  opposing_claims: ResearchClaimSummary[];
  what_would_change_my_mind: string;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface KnowledgeGapResult {
  gap_id: string;
  node_id: string;
  title: string;
  description: string;
  status: string;
  source_claim_ids: string[];
  freshness_due: string;
  resolution_claim_id: string;
  superseded_by_gap_id: string;
  created_at: string;
  updated_at: string;
}

export interface SourceLinkedNode extends NodeSummary {
  role: string;
  confidence: number | null;
  link_origin: string;
  derived_from_node_id: string;
  evidence_excerpt: string;
}

export interface SourceClaimNode extends NodeSummary {
  role: string;
}

export interface SourceClaim {
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
  linked_nodes: SourceClaimNode[];
}

export interface SourceDetail {
  source_id: string;
  title: string;
  original_name: string;
  source_type: string;
  source_rank: string;
  origin_type: string;
  author: string;
  organization: string;
  publication_time: string;
  ingested_at: string;
  ingestion_mode: string;
  analysis_mode: string;
  status: string;
  underlying_source_id: string;
  linked_nodes: SourceLinkedNode[];
  claims: SourceClaim[];
}
