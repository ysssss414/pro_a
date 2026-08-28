from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Any, Literal

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from .config import load_config
from .current_view_compare import CurrentViewCompareValidationError
from .query import (
    MAX_QUERY_LIMIT,
    CurrentViewCompareNotFoundError,
    ReadOnlyDatabaseError,
    ReadOnlyQuery,
)


class HealthResponse(BaseModel):
    status: Literal["ok"]


class StatsResponse(BaseModel):
    active_node_count: int
    alias_count: int
    current_relation_count: int
    current_part_of_count: int
    source_count: int
    claim_count: int
    current_view_count: int
    open_knowledge_gap_count: int
    open_research_question_count: int


class NodeSummary(BaseModel):
    node_id: str
    canonical_name: str
    primary_type: str


class NodeSearchResult(NodeSummary):
    matched_by: Literal["canonical_name", "alias"]
    matched_text: str


class RelationResult(BaseModel):
    relation_id: str
    from_node_id: str
    relation_type: str
    to_node_id: str
    scope: str
    status: str
    confidence: float | None
    from_canonical_name: str
    to_canonical_name: str


class NodeDetail(NodeSummary):
    description: str
    status: str
    aliases: list[str]
    parents: list[NodeSummary]
    children: list[NodeSummary]
    incoming_relations: list[RelationResult]
    outgoing_relations: list[RelationResult]


class NeighborGraph(BaseModel):
    center: NodeSummary
    nodes: list[NodeSummary]
    edges: list[RelationResult]


class SourceMetadata(BaseModel):
    source_id: str
    title: str
    original_name: str
    author: str
    organization: str
    publication_time: str
    source_type: str
    source_rank: str


class ClaimResult(BaseModel):
    claim_id: str
    statement: str
    nature: str
    fact_time: str
    publication_time: str
    status: str
    confidence: float | None
    novelty_level: str
    attributed_to: str
    scope: str
    evidence_pointer: str
    evidence_excerpt: str
    source_id: str
    link_role: Literal["subject", "context", "related"]
    source: SourceMetadata


class SourceProvenance(BaseModel):
    origin_path: Literal["direct", "claim"]
    role: str
    link_origin: str
    evidence_excerpt: str
    claim_id: str | None


class NodeSource(SourceMetadata):
    provenance: list[SourceProvenance]


class CurrentViewResult(BaseModel):
    view_id: str
    node_id: str
    version: str
    status: str
    change_level: str
    previous_view_id: str | None
    content_md: str
    content_json: dict[str, Any]
    trigger_source_id: str | None
    trigger_claim_ids: list[str]
    revision_date: str
    revision_seq: int
    accepted_proposal_id: str
    created_at: str
    confirmed_at: str


class CurrentViewHistoryResult(BaseModel):
    node_id: str
    views: list[CurrentViewResult]


class CurrentViewCompareResult(BaseModel):
    node_id: str
    base: dict[str, Any]
    target: dict[str, Any]
    scalar_changes: list[dict[str, Any]]
    list_changes: dict[str, dict[str, list[str]]]
    type_specific_changes: dict[str, dict[str, Any]]
    evidence: dict[str, list[dict[str, Any]]]
    trigger_source_change: dict[str, Any]
    has_changes: bool


class ResearchClaimSummary(BaseModel):
    claim_id: str
    statement: str | None
    status: str | None
    confidence: float | None


class ViewProposalSummary(BaseModel):
    proposal_id: str
    status: str
    node_id: str
    node_name: str
    node_type: str
    node_status: str | None
    node_resolved: bool
    decision: Literal["minor", "material", "thesis"]
    reason: str
    trigger_source_id: str
    trigger_source: dict[str, Any]
    previous_view_id: str
    previous_version: str
    created_at: str
    resolved_at: str | None
    human_review_origin: Literal[True]


class ViewProposalDetail(ViewProposalSummary):
    proposal_snapshot: dict[str, Any]
    resolution: dict[str, str] | None
    canonical_alignment: str
    target_official_view: dict[str, Any] | None
    before_current_view: dict[str, Any] | None
    proposed_current_view: dict[str, Any]
    diff: dict[str, Any] | None
    human_review_handoff: dict[str, Any]
    thesis_break: dict[str, str]
    primary_evidence: list[dict[str, Any]]
    context_evidence: list[dict[str, Any]]
    candidate_claims: list[dict[str, str]]


class ResearchQuestionResult(BaseModel):
    rq_id: str
    node_id: str
    question: str
    importance: str
    current_answer: str
    confidence: float | None
    supporting_claim_ids: list[str]
    opposing_claim_ids: list[str]
    key_variables: list[Any]
    supporting_claims: list[ResearchClaimSummary]
    opposing_claims: list[ResearchClaimSummary]
    what_would_change_my_mind: str
    status: str
    created_at: str
    updated_at: str


class KnowledgeGapResult(BaseModel):
    gap_id: str
    node_id: str
    title: str
    description: str
    status: str
    source_claim_ids: list[str]
    freshness_due: str
    resolution_claim_id: str
    superseded_by_gap_id: str
    created_at: str
    updated_at: str


class SourceLinkedNode(NodeSummary):
    role: str
    confidence: float | None
    link_origin: str
    derived_from_node_id: str
    evidence_excerpt: str


class SourceClaimNode(NodeSummary):
    role: str


class SourceClaim(BaseModel):
    claim_id: str
    statement: str
    nature: str
    fact_time: str
    publication_time: str
    status: str
    confidence: float | None
    novelty_level: str
    attributed_to: str
    scope: str
    evidence_pointer: str
    evidence_excerpt: str
    linked_nodes: list[SourceClaimNode]


class SourceDetail(BaseModel):
    source_id: str
    title: str
    original_name: str
    source_type: str
    source_rank: str
    origin_type: str
    author: str
    organization: str
    publication_time: str
    ingested_at: str
    ingestion_mode: str
    analysis_mode: str
    status: str
    underlying_source_id: str
    linked_nodes: list[SourceLinkedNode]
    claims: list[SourceClaim]


class ImpactClaimSummary(BaseModel):
    claim_id: str
    statement: str
    status: str
    confidence: float | None
    role: Literal["subject", "context", "related"]
    fact_time: str
    publication_time: str


class ImpactCurrentViewSummary(BaseModel):
    view_id: str
    version: str
    change_level: str
    revision_date: str


class ImpactCandidate(BaseModel):
    node: NodeSummary
    current_view: ImpactCurrentViewSummary
    roles: list[Literal["subject", "context", "related"]]
    claims: list[ImpactClaimSummary]


class LinkedNodeWithoutCurrentView(BaseModel):
    node: NodeSummary
    roles: list[Literal["subject", "context", "related"]]
    claims: list[ImpactClaimSummary]


class SourceImpactCandidatesResult(BaseModel):
    source_id: str
    claim_count: int
    candidates: list[ImpactCandidate]
    linked_nodes_without_current_view: list[LinkedNodeWithoutCurrentView]


class ClaimImpactCandidatesResult(BaseModel):
    claim_id: str
    candidates: list[ImpactCandidate]
    linked_nodes_without_current_view: list[LinkedNodeWithoutCurrentView]


def create_app(
    db_path: str | Path | None = None,
    *,
    config_path: str | Path | None = None,
) -> FastAPI:
    app = FastAPI(title="pro_a read-only knowledge API")
    explicit_db_path = Path(db_path) if db_path is not None else None
    configured_path = Path(config_path or os.getenv("PROA_CONFIG", "config.toml"))

    def read_model() -> ReadOnlyQuery:
        if explicit_db_path is not None:
            return ReadOnlyQuery(explicit_db_path)
        try:
            return ReadOnlyQuery(load_config(configured_path).db_path)
        except (OSError, ValueError) as exc:
            raise ReadOnlyDatabaseError(
                "Knowledge database configuration is unavailable"
            ) from exc

    @app.exception_handler(ReadOnlyDatabaseError)
    async def database_unavailable(
        _request: Request, _exc: ReadOnlyDatabaseError
    ) -> JSONResponse:
        return JSONResponse(status_code=503, content={"detail": "Knowledge database unavailable"})

    @app.exception_handler(ValueError)
    async def invalid_query_parameter(_request: Request, exc: ValueError) -> JSONResponse:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    @app.get("/api/health", response_model=HealthResponse)
    def health(query_model: ReadOnlyQuery = Depends(read_model)) -> dict[str, str]:
        query_model.health()
        return {"status": "ok"}

    @app.get("/api/stats", response_model=StatsResponse)
    def stats(query_model: ReadOnlyQuery = Depends(read_model)) -> dict[str, int]:
        return query_model.stats()

    @app.get("/api/nodes", response_model=list[NodeSummary])
    def nodes(
        primary_type: str | None = None,
        limit: int = Query(50, ge=1, le=MAX_QUERY_LIMIT),
        offset: int = Query(0, ge=0),
        query_model: ReadOnlyQuery = Depends(read_model),
    ) -> list[dict]:
        return query_model.list_nodes(
            primary_type=primary_type,
            limit=limit,
            offset=offset,
        )

    @app.get("/api/nodes/search", response_model=list[NodeSearchResult])
    def search_nodes(
        q: str = Query(..., min_length=1, max_length=200),
        primary_type: str | None = None,
        limit: int = Query(20, ge=1, le=MAX_QUERY_LIMIT),
        query_model: ReadOnlyQuery = Depends(read_model),
    ) -> list[dict]:
        return query_model.search_nodes(q, primary_type=primary_type, limit=limit)

    @app.get("/api/nodes/{node_id}", response_model=NodeDetail)
    def node_detail(
        node_id: str,
        query_model: ReadOnlyQuery = Depends(read_model),
    ) -> dict:
        result = query_model.node_detail(node_id)
        if result is None:
            raise HTTPException(status_code=404, detail="Node not found")
        return result

    @app.get("/api/nodes/{node_id}/neighbors", response_model=NeighborGraph)
    def node_neighbors(
        node_id: str,
        query_model: ReadOnlyQuery = Depends(read_model),
    ) -> dict:
        result = query_model.node_neighbors(node_id)
        if result is None:
            raise HTTPException(status_code=404, detail="Node not found")
        return result

    @app.get("/api/nodes/{node_id}/claims", response_model=list[ClaimResult])
    def node_claims(
        node_id: str,
        query_model: ReadOnlyQuery = Depends(read_model),
    ) -> list[dict]:
        result = query_model.node_claims(node_id)
        if result is None:
            raise HTTPException(status_code=404, detail="Node not found")
        return result

    @app.get("/api/nodes/{node_id}/sources", response_model=list[NodeSource])
    def node_sources(
        node_id: str,
        query_model: ReadOnlyQuery = Depends(read_model),
    ) -> list[dict]:
        result = query_model.node_sources(node_id)
        if result is None:
            raise HTTPException(status_code=404, detail="Node not found")
        return result

    @app.get(
        "/api/nodes/{node_id}/current-view",
        response_model=CurrentViewResult | None,
    )
    def node_current_view(
        node_id: str,
        query_model: ReadOnlyQuery = Depends(read_model),
    ) -> dict | None:
        try:
            return query_model.node_current_view(node_id)
        except KeyError:
            raise HTTPException(status_code=404, detail="Node not found") from None

    @app.get(
        "/api/nodes/{node_id}/current-view-history",
        response_model=CurrentViewHistoryResult,
    )
    def node_current_view_history(
        node_id: str,
        query_model: ReadOnlyQuery = Depends(read_model),
    ) -> dict:
        try:
            return {
                "node_id": node_id,
                "views": query_model.node_current_view_history(node_id),
            }
        except KeyError:
            raise HTTPException(status_code=404, detail="Node not found") from None

    @app.get(
        "/api/nodes/{node_id}/current-view-compare",
        response_model=CurrentViewCompareResult,
    )
    def node_current_view_compare(
        node_id: str,
        base_view_id: str = Query(..., min_length=1),
        target_view_id: str = Query(..., min_length=1),
        query_model: ReadOnlyQuery = Depends(read_model),
    ) -> dict:
        try:
            return query_model.node_current_view_compare(
                node_id,
                base_view_id,
                target_view_id,
            )
        except KeyError:
            raise HTTPException(status_code=404, detail="Node not found") from None
        except CurrentViewCompareNotFoundError:
            raise HTTPException(status_code=404, detail="Current View not found") from None
        except CurrentViewCompareValidationError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from None

    @app.get(
        "/api/nodes/{node_id}/research-question",
        response_model=ResearchQuestionResult | None,
    )
    def node_research_question(
        node_id: str,
        query_model: ReadOnlyQuery = Depends(read_model),
    ) -> dict | None:
        try:
            return query_model.node_research_question(node_id)
        except KeyError:
            raise HTTPException(status_code=404, detail="Node not found") from None

    @app.get(
        "/api/nodes/{node_id}/knowledge-gaps",
        response_model=list[KnowledgeGapResult],
    )
    def node_knowledge_gaps(
        node_id: str,
        query_model: ReadOnlyQuery = Depends(read_model),
    ) -> list[dict]:
        try:
            return query_model.node_knowledge_gaps(node_id)
        except KeyError:
            raise HTTPException(status_code=404, detail="Node not found") from None

    @app.get("/api/view-proposals", response_model=list[ViewProposalSummary])
    def view_proposals(
        limit: int = Query(50, ge=1, le=MAX_QUERY_LIMIT),
        offset: int = Query(0, ge=0),
        status: Literal["pending", "accepted", "rejected"] = "pending",
        query_model: ReadOnlyQuery = Depends(read_model),
    ) -> list[dict]:
        return query_model.list_view_proposals(limit=limit, offset=offset, status=status)

    @app.get("/api/view-proposals/{proposal_id}", response_model=ViewProposalDetail)
    def view_proposal_detail(
        proposal_id: str,
        query_model: ReadOnlyQuery = Depends(read_model),
    ) -> dict:
        result = query_model.view_proposal_detail(proposal_id)
        if result is None:
            raise HTTPException(status_code=404, detail="Human View Proposal not found")
        return result

    @app.get("/api/sources/{source_id}", response_model=SourceDetail)
    def source_detail(
        source_id: str,
        query_model: ReadOnlyQuery = Depends(read_model),
    ) -> dict:
        result = query_model.source_detail(source_id)
        if result is None:
            raise HTTPException(status_code=404, detail="Source not found")
        return result

    @app.get(
        "/api/sources/{source_id}/impact-candidates",
        response_model=SourceImpactCandidatesResult,
    )
    def source_impact_candidates(
        source_id: str,
        query_model: ReadOnlyQuery = Depends(read_model),
    ) -> dict:
        result = query_model.source_impact_candidates(source_id)
        if result is None:
            raise HTTPException(status_code=404, detail="Source not found")
        return result

    @app.get(
        "/api/claims/{claim_id}/impact-candidates",
        response_model=ClaimImpactCandidatesResult,
    )
    def claim_impact_candidates(
        claim_id: str,
        query_model: ReadOnlyQuery = Depends(read_model),
    ) -> dict:
        result = query_model.claim_impact_candidates(claim_id)
        if result is None:
            raise HTTPException(status_code=404, detail="Claim not found")
        return result

    return app


app = create_app()


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Run the pro_a read-only knowledge API")
    parser.add_argument("--config", default=os.getenv("PROA_CONFIG", "config.toml"))
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args(argv)

    config = load_config(args.config)
    query_model = ReadOnlyQuery(config.db_path)
    query_model.health()

    import uvicorn

    uvicorn.run(create_app(config.db_path), host=args.host, port=args.port)


if __name__ == "__main__":
    main()
