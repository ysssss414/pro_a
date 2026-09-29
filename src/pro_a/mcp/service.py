"""Transport-independent composition over the authoritative pro_a read models."""
from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version
import re
from typing import Annotated
import unicodedata

from pydantic import Field

from pro_a.company_material_intent import company
from pro_a.company_materials import CompanyMaterials
from pro_a.production_promotion import canonical_sha256
from pro_a.query import ReadOnlyQuery
from pro_a.workbench.config import BoundaryError, WorkbenchConfig
from pro_a.workbench.store import Store

from . import CONTRACT_VERSION
from .errors import BridgeError, read_operation
from .reads import OperationalReads, ReviewReads
from . import schemas as s
from . import review_schemas as r
from . import review_context


TOOLS = (
    "pro_a_health", "search_companies", "get_company", "list_company_materials",
    "get_current_view", "get_current_view_history", "get_node_evidence",
    "get_source", "get_processing_run", "get_review_packet", "get_company_research_context",
    "list_review_queue", "get_review_context", "get_review_item_context",
)
Identifier = Annotated[str, Field(min_length=1, max_length=200, pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$", strict=True)]
Limit = Annotated[int, Field(ge=1, le=50, strict=True)]
Cursor = Annotated[str, Field(max_length=8, pattern=r"^(0|[1-9][0-9]{0,7})$", strict=True)]
SearchText = Annotated[str, Field(min_length=1, max_length=200, strict=True)]
ArtifactId = Annotated[str, Field(pattern=r"^ART_[0-9a-f]{32}$", strict=True)]
ContextHash = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$", strict=True)]


def review_arguments(artifact_id, projection, expected):
    if not isinstance(artifact_id, str) or not re.fullmatch(r"ART_[0-9a-f]{32}", artifact_id):
        raise BridgeError("INVALID_ARGUMENT")
    if projection not in ("blind", "stateful"):
        raise BridgeError("INVALID_ARGUMENT")
    if expected is not None and (not isinstance(expected, str) or not re.fullmatch(r"[0-9a-f]{64}", expected)):
        raise BridgeError("INVALID_ARGUMENT")


def identifier(value):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,199}", value):
        raise BridgeError("INVALID_ARGUMENT")
    return value


def page(limit, cursor=None):
    if type(limit) is not int or not 1 <= limit <= 50:
        raise BridgeError("INVALID_ARGUMENT")
    if cursor is not None and (not isinstance(cursor, str) or not re.fullmatch(r"0|[1-9][0-9]{0,7}", cursor)):
        raise BridgeError("INVALID_ARGUMENT")
    offset = int(cursor or 0)
    if offset > 10_000_000:
        raise BridgeError("INVALID_ARGUMENT")
    return offset


def portion(items, limit, cursor=None):
    offset = page(limit, cursor)
    return items[offset:offset + limit], str(offset + limit) if offset + limit < len(items) else None


class ReadService:
    def __init__(self, config: WorkbenchConfig):
        self.config = config
        self.query = ReadOnlyQuery(config.knowledge_db)
        self.materials = CompanyMaterials(config)
        self.operations = OperationalReads(config)
        self.reviews = ReviewReads(config)

    @read_operation
    def list_review_queue(self, queue: r.Queue = "all", limit: Limit = 20,
                          cursor: Cursor | None = None) -> r.ReviewQueue:
        offset = page(limit, cursor)
        if queue not in ("all", *review_context.QUEUES):
            raise BridgeError("INVALID_ARGUMENT")
        return review_context.queue(self, queue, limit, offset)

    @read_operation
    def get_review_context(self, artifact_id: ArtifactId, projection: r.Projection = "blind",
                           limit: Limit = 20, cursor: Cursor | None = None,
                           expected_context_sha256: ContextHash | None = None) -> r.ReviewContext:
        review_arguments(artifact_id, projection, expected_context_sha256)
        return review_context.packet_context(self, artifact_id, projection, limit,
                                             page(limit, cursor), expected_context_sha256)

    @read_operation
    def get_review_item_context(self, artifact_id: ArtifactId, candidate_id: Identifier,
                                projection: r.Projection = "blind",
                                expected_context_sha256: ContextHash | None = None) -> r.ReviewItemContext:
        review_arguments(artifact_id, projection, expected_context_sha256)
        identifier(candidate_id)
        return review_context.item_context(self, artifact_id, candidate_id, projection, expected_context_sha256)

    def _production(self):
        try:
            self.config.validate()
        except BoundaryError as error:
            code = "PRODUCTION_UNAVAILABLE" if str(error) in (
                "PATH_UNAVAILABLE", "KNOWLEDGE_SCHEMA_UNAVAILABLE",
            ) else "READ_BOUNDARY_VIOLATION"
            raise BridgeError(code) from None
        except Exception:
            raise BridgeError("PRODUCTION_UNAVAILABLE") from None

    def _workbench(self):
        try:
            with Store(self.config).connect() as conn:
                return conn.execute("SELECT value FROM workbench_meta WHERE key='schema_version'").fetchone()[0]
        except BoundaryError as error:
            code = "WORKBENCH_UNAVAILABLE" if str(error) in (
                "PATH_UNAVAILABLE", "WORKBENCH_SCHEMA_UNSUPPORTED",
            ) else "READ_BOUNDARY_VIOLATION"
            raise BridgeError(code) from None
        except Exception:
            raise BridgeError("WORKBENCH_UNAVAILABLE") from None

    def _node(self, node_id):
        identifier(node_id)
        self._production()
        result = self.query.node_detail(node_id)
        if result is None:
            raise BridgeError("NODE_NOT_FOUND")
        return result

    @read_operation
    def pro_a_health(self) -> s.Health:
        production = workbench = False
        schema = None
        try:
            self._production()
            production = True
        except BridgeError:
            pass
        try:
            schema = self._workbench()
            workbench = True
        except BridgeError:
            pass
        try:
            app_version = version("pro-a")
        except PackageNotFoundError:
            app_version = None
        return s.Health(contract_version=CONTRACT_VERSION, pro_a_version=app_version,
                        production_readable=production, workbench_readable=workbench,
                        workbench_schema_version=schema, capabilities=list(TOOLS))

    @read_operation
    def search_companies(self, query: SearchText, limit: Limit = 20) -> s.CompanySearch:
        page(limit)
        if not isinstance(query, str) or not 1 <= len(query.strip()) <= 200 or any(ord(c) < 32 for c in query):
            raise BridgeError("INVALID_ARGUMENT")
        self._production()
        # Probe independently of the display limit: limit=1 must not hide ambiguity.
        items = self.materials.search(query, limit=50)["items"]
        if not items:
            raise BridgeError("NO_CANONICAL_COMPANY")
        resolution = "AMBIGUOUS_COMPANY" if len(items) > 1 else "MATCHES"
        if len(items) == 1:
            detail = self.query.node_detail(items[0]["node_id"])
            normalize = lambda text: unicodedata.normalize("NFKC", text).casefold()
            if normalize(query.strip()) in {normalize(name) for name in [detail["canonical_name"], *detail["aliases"]]}:
                resolution = "EXACT_UNIQUE"
        return s.CompanySearch(resolution=resolution, items=items[:limit], limit=limit,
                               has_more=len(items) > limit or len(items) == 50)

    @read_operation
    def get_company(self, company_node_id: Identifier) -> s.Company:
        identifier(company_node_id)
        self._production()
        identity = company(self.config, company_node_id)
        detail = self.query.node_detail(company_node_id)
        return s.Company(identity=identity, description=detail["description"], aliases=detail["aliases"])

    @read_operation
    def list_company_materials(self, company_node_id: Identifier, limit: Limit = 20,
                               cursor: Cursor | None = None) -> s.Materials:
        identifier(company_node_id)
        page(limit, cursor)
        self._production()
        self._workbench()
        return s.Materials.model_validate(self.materials.timeline(company_node_id, limit=limit, cursor=cursor))

    @read_operation
    def get_current_view(self, node_id: Identifier) -> s.CurrentView:
        self._node(node_id)
        view = self.query.node_current_view(node_id)
        return s.CurrentView(node_id=node_id, status="OFFICIAL" if view else "NO_OFFICIAL_VIEW", current_view=view)

    @read_operation
    def get_current_view_history(self, node_id: Identifier, limit: Limit = 20,
                                 cursor: Cursor | None = None) -> s.ViewHistory:
        page(limit, cursor)
        self._node(node_id)
        items, following = portion(self.query.node_current_view_history(node_id), limit, cursor)
        return s.ViewHistory(node_id=node_id, items=items, limit=limit, next_cursor=following)

    @read_operation
    def get_node_evidence(self, node_id: Identifier, limit: Limit = 20,
                          claim_cursor: Cursor | None = None, source_cursor: Cursor | None = None) -> s.Evidence:
        page(limit, claim_cursor)
        page(limit, source_cursor)
        self._node(node_id)
        claims, next_claim = portion(self.query.node_claims(node_id), limit, claim_cursor)
        sources, next_source = portion(self.query.node_sources(node_id), limit, source_cursor)
        return s.Evidence(node_id=node_id, claims=claims, sources=sources, limit=limit,
                          next_claim_cursor=next_claim, next_source_cursor=next_source)

    @staticmethod
    def _run_projection(raw):
        context = raw.get("domain_context") or {}
        runtime = raw.get("runtime_identity") or {}
        error = raw.get("error")
        if error and not re.fullmatch(r"[A-Z][A-Z0-9_]{0,99}(?::[A-Z][A-Z0-9_]{0,99})?", error["code"]):
            # Operational diagnostics are classifications, never exception payloads.
            error = {**error, "code": "UNCLASSIFIED_FAILURE"}
        return s.ProcessingRun.model_validate({**raw, "frozen_context": {
            "contract_version": context.get("contract_version"),
            "context_sha256": context.get("context_sha256"),
            "runtime_sha256": runtime.get("runtime_sha256"),
        }, "error": error})

    @read_operation
    def get_processing_run(self, processing_run_id: Identifier) -> s.ProcessingRun:
        identifier(processing_run_id)
        self._workbench()
        return self._run_projection(self.operations.get_run(processing_run_id))

    @read_operation
    def get_source(self, source_id: Identifier) -> s.Source:
        identifier(source_id)
        self._production()
        canonical = self.query.source_detail(source_id)
        operational = None
        warnings = []
        try:
            self._workbench()
        except BridgeError as error:
            if error.code != "WORKBENCH_UNAVAILABLE" or canonical is None:
                raise
            warnings.append(error.code)
        else:
            from pro_a.workbench.source_operations import SourceOperationError
            try:
                operational = self.operations.source(source_id)
            except SourceOperationError as error:
                if str(error) != "SOURCE_NOT_FOUND":
                    raise
        if canonical is None and operational is None:
            raise BridgeError("SOURCE_NOT_FOUND")
        latest = (operational or {}).get("latest_run")
        return s.Source(source_id=source_id, canonical=canonical, operational=operational,
                        latest_run=self._run_projection(latest) if latest else None, warnings=warnings)

    @read_operation
    def get_review_packet(self, artifact_id: ArtifactId, limit: Limit = 20,
                          cursor: Cursor | None = None) -> s.ReviewPacket:
        if not isinstance(artifact_id, str) or not re.fullmatch(r"ART_[0-9a-f]{32}", artifact_id):
            raise BridgeError("INVALID_ARGUMENT")
        page(limit, cursor)
        self._workbench()
        raw = self.reviews.read(artifact_id)
        items, following = portion(raw["items"], limit, cursor)
        return s.ReviewPacket.model_validate({**raw, "items": items, "limit": limit, "next_cursor": following})

    @read_operation
    def get_company_research_context(self, company_node_id: Identifier,
                                      recent_material_limit: Limit = 10) -> s.ResearchContext:
        page(recent_material_limit)
        target = self.get_company(company_node_id)
        view = self.get_current_view(company_node_id)
        warnings = []
        materials = None
        try:
            materials = self.list_company_materials(company_node_id, recent_material_limit)
        except BridgeError as error:
            if error.code != "WORKBENCH_UNAVAILABLE":
                raise
            warnings.append(error.code)
        if view.current_view is None:
            warnings.append("NO_OFFICIAL_VIEW")
        rows = materials.materials if materials else []
        if any(not row.canonical for row in rows):
            warnings.append("PRIVATE_MATERIAL_IS_NOT_CANONICAL_EVIDENCE")
        refs = {("SOURCE", row.canonical_source_id): s.EvidenceRef(
            kind="SOURCE", id=row.canonical_source_id, basis="CANONICAL_MATERIAL", resolution="CANONICAL",
        ) for row in rows if row.canonical and row.canonical_source_id}
        if view.current_view:
            # View trigger IDs remain references, including unresolved historical IDs.
            triggers = [("CLAIM", claim_id) for claim_id in view.current_view.trigger_claim_ids]
            if view.current_view.trigger_source_id:
                triggers.append(("SOURCE", view.current_view.trigger_source_id))
            for kind, ref in triggers:
                refs.setdefault((kind, ref), s.EvidenceRef(kind=kind, id=ref,
                                basis="OFFICIAL_VIEW_TRIGGER", resolution="REFERENCE_NOT_CHECKED"))
            if any(ref.resolution == "REFERENCE_NOT_CHECKED" for ref in refs.values()):
                warnings.append("OFFICIAL_VIEW_TRIGGER_REFERENCES_NOT_REVALIDATED")
        body = dict(company=target, current_view=view, recent_materials=rows,
                    next_material_cursor=materials.next_cursor if materials else None,
                    material_workflow_states=[s.WorkflowState.model_validate(row.model_dump()) for row in rows],
                    evidence_refs=[refs[key] for key in sorted(refs)],
                    warnings=warnings)
        snapshot = s.Snapshot(snapshot_id="", materials_snapshot_id=materials.snapshot_id if materials else None)
        result = s.ResearchContext(**body, snapshot=snapshot)
        result.snapshot.snapshot_id = canonical_sha256(result.model_dump(mode="json"))
        return result
