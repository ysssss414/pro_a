"""Explicit output allowlists; private metadata never passes through wholesale."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, JsonValue


class Identity(BaseModel):
    node_id: str
    canonical_name: str
    primary_type: str
    status: str


class Health(BaseModel):
    service: Literal["pro_a"] = "pro_a"
    contract_version: str
    pro_a_version: str | None
    production_readable: bool
    workbench_readable: bool
    workbench_schema_version: str | None
    read_only: Literal[True] = True
    capabilities: list[str]


class CompanySearch(BaseModel):
    resolution: Literal["EXACT_UNIQUE", "MATCHES", "AMBIGUOUS_COMPANY"]
    items: list[Identity]
    limit: int
    has_more: bool


class Company(BaseModel):
    identity: Identity
    description: str
    aliases: list[str]


class MaterialNode(BaseModel):
    node_id: str
    canonical_name: str
    primary_type: str
    roles: str


class Material(BaseModel):
    material_id: str
    source_id: str
    processing_run_id: str | None
    title: str
    title_basis: str
    material_kind: str | None
    source_channel: str | None
    material_trust_policy: str | None
    material_date: str | None
    material_date_basis: str | None
    lifecycle: str
    state: str
    private: bool
    canonical: bool
    association_basis: str
    canonical_source_id: str | None
    review_status: str | None
    attribution_status: str | None
    qualification_status: str | None
    claim_count: int | None
    linked_node_count: int | None
    linked_nodes: list[MaterialNode] | None
    current_view_impact_candidate_count: int | None
    uploaded_at: str | None
    publication_time: str | None
    ingested_at: str | None
    updated_at: str
    packet_artifact_id: str | None
    company_material_intent_sha256: str | None
    processing_scope: str | None = None
    domain_assignment_status: str | None = None
    primary_domain: str | None = None


class Counts(BaseModel):
    total: int
    private: int
    canonical: int


class Materials(BaseModel):
    contract_version: str
    company: Identity
    materials: list[Material]
    counts: Counts
    limit: int
    next_cursor: str | None
    snapshot_id: str


class OfficialView(BaseModel):
    view_id: str
    node_id: str
    version: str
    status: Literal["official"]
    change_level: str
    previous_view_id: str | None
    content_md: str
    content_json: dict[str, JsonValue]
    trigger_source_id: str | None
    trigger_claim_ids: list[str]
    revision_date: str
    revision_seq: int
    accepted_proposal_id: str
    created_at: str
    confirmed_at: str


class CurrentView(BaseModel):
    node_id: str
    status: Literal["OFFICIAL", "NO_OFFICIAL_VIEW"]
    current_view: OfficialView | None


class ViewHistory(BaseModel):
    node_id: str
    items: list[OfficialView]
    limit: int
    next_cursor: str | None


class SourceMetadata(BaseModel):
    source_id: str
    title: str
    author: str
    organization: str
    publication_time: str
    source_type: str
    source_rank: str


class Locator(BaseModel):
    status: str
    locator: str | None = None
    locators: list[str] | None = None


class Claim(BaseModel):
    claim_id: str
    statement: str
    nature: str
    fact_time: str
    publication_time: str
    status: str
    confidence: float | None
    attributed_to: str
    scope: str
    evidence_pointer: str
    evidence_excerpt: str
    source_id: str
    link_role: str
    source: SourceMetadata
    source_locator: Locator | None


class Provenance(BaseModel):
    origin_path: str
    role: str
    link_origin: str
    evidence_excerpt: str
    claim_id: str | None


class EvidenceSource(SourceMetadata):
    provenance: list[Provenance]


class Evidence(BaseModel):
    node_id: str
    authority: Literal["CANONICAL"] = "CANONICAL"
    claims: list[Claim]
    sources: list[EvidenceSource]
    limit: int
    next_claim_cursor: str | None
    next_source_cursor: str | None


class CanonicalSource(SourceMetadata):
    origin_type: str
    ingested_at: str
    ingestion_mode: str
    analysis_mode: str
    status: str
    underlying_source_id: str


class PrivateSource(BaseModel):
    source_id: str
    source_sha256: str
    size_bytes: int
    mime_type: str
    uploaded_at: str
    known_canonical_source_id: str | None
    private: Literal[True] = True


class RunReview(BaseModel):
    review_id: str
    status: str
    required: int
    completed: int


class RunError(BaseModel):
    code: str
    stage: str
    manual_recovery_required: bool


class JobState(BaseModel):
    job_id: str
    operation_kind: str
    status: str
    phase: str
    attempt_count: int
    validation_status: str | None
    recovery_required: bool


class FrozenContext(BaseModel):
    contract_version: str | None = None
    context_sha256: str | None = None
    runtime_sha256: str | None = None


class ProcessingRun(BaseModel):
    processing_run_id: str
    source_id: str
    state: str
    stage: str
    source_sha256: str
    packet_artifact_id: str | None
    packet_id: str | None
    created_at: str
    updated_at: str
    ended_at: str | None
    domain_context_status: str
    processing_scope_mode: str | None
    domain_assignment_status: str | None
    primary_domain: str | None
    frozen_context: FrozenContext
    error: RunError | None
    review: RunReview | None
    jobs: list[JobState]


class Source(BaseModel):
    source_id: str
    canonical: CanonicalSource | None
    operational: PrivateSource | None
    latest_run: ProcessingRun | None
    warnings: list[str]


class ReviewContent(BaseModel):
    claim_id: str | None = None
    statement: str | None = None
    evidence_pointer: str | None = None
    evidence_excerpt: str | None = None
    proposed_name: str | None = None
    proposed_type: str | None = None
    prospective_node_id: str | None = None
    child_node_candidate_id: str | None = None
    parent_node_id: str | None = None
    supporting_claim_ids: list[str] = Field(default_factory=list)


class ReviewItem(BaseModel):
    candidate_id: str
    candidate_type: str
    content_sha256: str
    content: ReviewContent


class ReviewProgress(BaseModel):
    required: int
    completed: int
    remaining: int
    deferred: int


class ReviewState(BaseModel):
    enabled: bool
    status: str | None = None
    revision: int | None = None
    basis_id: str | None = None
    progress: ReviewProgress | None = None
    reason: str | None = None


class ReviewPacket(BaseModel):
    artifact_id: str
    packet_id: str
    packet_file_sha256: str
    immutable_packet_sha256: str
    packet_status: str
    validation_state: str
    review: ReviewState
    items: list[ReviewItem]
    limit: int
    next_cursor: str | None
    read_only: Literal[True] = True


class WorkflowState(BaseModel):
    source_id: str
    processing_run_id: str | None
    state: str
    review_status: str | None
    canonical: bool


class EvidenceRef(BaseModel):
    kind: Literal["SOURCE", "CLAIM"]
    id: str
    basis: Literal["CANONICAL_MATERIAL", "OFFICIAL_VIEW_TRIGGER"]
    resolution: Literal["CANONICAL", "REFERENCE_NOT_CHECKED"]


class Snapshot(BaseModel):
    snapshot_id: str
    materials_snapshot_id: str | None
    consistency: Literal["SEQUENTIAL_READS_NOT_ATOMIC"] = "SEQUENTIAL_READS_NOT_ATOMIC"
    cache: Literal["NONE"] = "NONE"


class ResearchContext(BaseModel):
    company: Company
    current_view: CurrentView
    recent_materials: list[Material]
    next_material_cursor: str | None
    material_workflow_states: list[WorkflowState]
    evidence_refs: list[EvidenceRef]
    warnings: list[str]
    snapshot: Snapshot
