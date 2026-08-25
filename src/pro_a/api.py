from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Literal

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from .config import load_config
from .query import MAX_QUERY_LIMIT, ReadOnlyDatabaseError, ReadOnlyQuery


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
    source: SourceMetadata


class SourceProvenance(BaseModel):
    origin_path: Literal["direct", "claim"]
    role: str
    link_origin: str
    evidence_excerpt: str
    claim_id: str | None


class NodeSource(SourceMetadata):
    provenance: list[SourceProvenance]


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
