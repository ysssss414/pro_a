"""Review Copilot allowlists, separate from the unchanged Stage 0 schemas."""
from typing import Literal

from pydantic import BaseModel, Field

from .schemas import Claim, CurrentView, FrozenContext, Identity, ReviewState, SourceMetadata

Projection = Literal["blind", "stateful"]
Queue = Literal["all", "needs_review", "high_attention", "entity_resolution", "parent_placement", "deferred", "completed"]


class PacketSource(BaseModel):
    source_id: str | None
    source_sha256: str | None = None
    size_bytes: int | None = None
    source_type: str | None = None
    canonical: SourceMetadata | None = None


class FrozenRun(BaseModel):
    run_id: str
    processing_run_id: str | None = None
    frozen_context: FrozenContext = Field(default_factory=FrozenContext)


class Diagnostic(BaseModel):
    status: str | None = None
    issue_codes: list[str] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)
    review_eligible: bool | None = None


class Guards(BaseModel):
    overall_guard_disposition: str | None = None
    guard_reasons: list[str] = Field(default_factory=list)
    proposition_ir_validation: Diagnostic | None = None


class EvidenceLocator(BaseModel):
    status: str | None = None
    authoritative: bool | None = None
    locator: str | None = None
    paragraph: int | None = None
    section: str | None = None
    page: int | None = None


class EvidenceValidation(BaseModel):
    bound: bool | None = None
    fidelity_status: str | None = None
    authoritative_locator: EvidenceLocator | None = None


class SupportingEvidence(BaseModel):
    claim_id: str | None = None
    evidence_id: str | None = None
    statement: str | None = None
    evidence_pointer: str | None = None
    evidence_excerpt: str | None = None


class Collision(BaseModel):
    normalized_term: str
    candidate_ids: list[str]


class Collisions(BaseModel):
    prospective_node_id_exists: bool | None = None
    package_internal_normalized_term_collisions: list[Collision] = Field(default_factory=list)
    production_nocase_or_nfkc_target_ids: list[str] = Field(default_factory=list)


class ExactResolution(BaseModel):
    candidate_target_node_ids: list[str] = Field(default_factory=list)


class CandidateContent(BaseModel):
    statement: str | None = None
    nature: str | None = None
    fact_time: str | None = None
    publication_time: str | None = None
    attributed_to: str | None = None
    scope: str | None = None
    evidence_pointer: str | None = None
    evidence_excerpt: str | None = None
    evidence_validation: EvidenceValidation | None = None
    table_eligibility: Diagnostic | None = None
    semantic_admission: Guards | None = None
    scope_preservation: Diagnostic | None = None
    review_admitted: bool | None = None
    duplicate_of_claim_id: str | None = None
    proposed_name: str | None = None
    proposed_type: str | None = None
    proposed_aliases: list[str] = Field(default_factory=list)
    prospective_node_id: str | None = None
    supporting_claim_ids: list[str] = Field(default_factory=list)
    supporting_evidence: list[SupportingEvidence] = Field(default_factory=list)
    phase3c_validation_state: Diagnostic | None = None
    current_defer_reason: str | None = None
    exact_production_resolution: ExactResolution | None = None
    collision_diagnostics: Collisions | None = None
    child_node_candidate_id: str | None = None
    prospective_child_node_id: str | None = None
    parent_node_id: str | None = None
    relation_type: str | None = None
    suggestion_type: str | None = None
    governance_status: str | None = None


class DecisionState(BaseModel):
    decision: str
    reason: str
    target_node_id: str | None = None


class Candidate(BaseModel):
    candidate_id: str
    candidate_type: Literal["CLAIM", "NODE", "PARENT_PLACEMENT"]
    content_sha256: str
    content: CandidateContent
    allowed_decisions: list[str]
    available_decisions: list[str]
    blocked_decisions: dict[str, str]
    canonical_node_ids: list[str]
    supporting_candidate_ids: list[str]


class CanonicalNode(BaseModel):
    node_id: str
    resolution: Literal["CANONICAL", "NOT_FOUND"]
    identity: Identity | None = None
    aliases: list[str] = Field(default_factory=list)
    current_view: CurrentView | None = None
    claims: list[Claim] = Field(default_factory=list)
    has_more_claims: bool = False


class ContextIdentity(BaseModel):
    artifact_id: str
    packet_id: str
    packet_file_sha256: str
    immutable_packet_sha256: str
    validation_state: str
    projection: Projection
    context_sha256: str
    review_enabled: bool
    disabled_reason: str | None = None
    source: PacketSource
    run: FrozenRun
    # Empty in blind mode; no decision state is read to construct that mode.
    review: ReviewState | None = None
    states: dict[str, DecisionState] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    basis_scope: Literal["WHOLE_PACKET_AND_BOUNDED_CANONICAL_CONTEXT"] = "WHOLE_PACKET_AND_BOUNDED_CANONICAL_CONTEXT"
    consistency: Literal["SEQUENTIAL_READS_NOT_ATOMIC"] = "SEQUENTIAL_READS_NOT_ATOMIC"
    read_only: Literal[True] = True


class ReviewContext(ContextIdentity):
    items: list[Candidate]
    canonical_identities: list[Identity]
    total_candidates: int
    limit: int
    next_cursor: str | None


class ReviewItemContext(ContextIdentity):
    item: Candidate
    supporting_candidates: list[Candidate]
    canonical_nodes: list[CanonicalNode]


class QueuePacket(BaseModel):
    artifact_id: str
    packet_id: str
    run_id: str
    source: PacketSource
    packet_status: str
    validation_state: str
    review: ReviewState
    candidate_type_counts: dict[str, int]
    queue_counts: dict[str, int]
    matching_queues: list[str]
    processing_scope_mode: str | None = None
    domain_assignment_status: str | None = None
    primary_domain: str | None = None


class ReviewQueue(BaseModel):
    queue: Queue
    items: list[QueuePacket]
    limit: int
    next_cursor: str | None
    read_only: Literal[True] = True
