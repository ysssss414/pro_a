from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
from pathlib import Path
import secrets
import time
from urllib.parse import unquote, urlsplit

from fastapi import Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from pro_a.api import create_app as create_explorer_app
from pro_a.direct_impact import DirectImpact, ImpactError
from pro_a.research_explorer import ResearchError, ResearchExplorer
from pro_a.research_navigation import ResearchNavigation
from pro_a.research_structure_map import ResearchStructureMap
from pro_a.qualified_overlay import QualifiedResearchOverlay
from pro_a.company_material_intent import CompanyMaterialError, company
from pro_a.company_materials import CompanyMaterials
from pro_a.operational_contract import WEB_REQUEST
from .artifacts import Artifacts
from .cloud_jobs import CloudJobs, CloudProfile, JobError
from .config import BoundaryError, WorkbenchConfig
from .store import Store
from .review_store import recover_workbench, schema_version
from .review_workbench import ReviewError, ReviewWorkbench
from .research_store import NoteError
from .source_operations import SourceOperationError, SourceOperations, SourceProfile

PREFIX = '/api/workbench/v1'
COOKIE = 'pro_a_workbench_session'


class Login(BaseModel):
    token: str = Field(min_length=32, max_length=512)


class ReviewBasis(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    basis_id: str = Field(pattern=r'^[0-9a-f]{64}$')
    expected_revision: int = Field(ge=0)


class ReviewOperation(ReviewBasis):
    operation_id: str = Field(pattern=r'^[0-9a-f-]{32,36}$')
    reviewer: str = Field(min_length=1, max_length=200)
    reason: str = Field(min_length=1, max_length=8000)


class Decision(ReviewOperation):
    candidate_id: str = Field(min_length=1, max_length=200)
    decision: str = Field(min_length=1, max_length=32)
    target_node_id: str = Field(default='', max_length=200)


class Undo(ReviewOperation):
    candidate_id: str = Field(min_length=1, max_length=200)
    event_id: int = Field(gt=0)


class Seal(ReviewOperation):
    confirm: bool


class AttributionLink(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    node_id: str = Field(min_length=1, max_length=200)
    role: str = Field(min_length=1, max_length=32)


class AttributionDecision(ReviewOperation):
    claim_id: str = Field(min_length=1, max_length=200)
    outcome: str = Field(min_length=1, max_length=32)
    scope: str = Field(max_length=8000)
    links: list[AttributionLink] = Field(max_length=100)


class ObjectReference(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    object_id: str = Field(min_length=1, max_length=150)


class ViewDraftSave(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    basis_sha256: str = Field(pattern=r'^[0-9a-f]{64}$')
    expected_revision: int = Field(ge=0)
    operation_id: str = Field(pattern=r'^[0-9a-f-]{32,36}$')
    reviewer: str = Field(min_length=1, max_length=200)
    reason: str = Field(min_length=1, max_length=8000)
    mode: str = Field(pattern=r'^(INITIAL|UPDATE)$')
    expected_official_view_id: str = Field(max_length=200)
    content: dict[str, object]
    primary_claim_ids: list[str] = Field(min_length=0, max_length=100)
    context_claim_ids: list[str] = Field(min_length=0, max_length=100)
    change_level: str = Field(pattern=r'^(initial|minor|material|thesis)$')


class ViewDraftAction(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    basis_sha256: str = Field(pattern=r'^[0-9a-f]{64}$')
    expected_revision: int = Field(ge=0)
    operation_id: str = Field(pattern=r'^[0-9a-f-]{32,36}$')
    reviewer: str = Field(min_length=1, max_length=200)
    reason: str = Field(min_length=1, max_length=8000)
    draft_id: str = Field(min_length=1, max_length=150)


class ViewQualification(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    draft_id: str = Field(min_length=1, max_length=150)
    revision: int = Field(gt=0)


class ImpactAttention(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    snapshot_id: str = Field(pattern=r'^[0-9a-f]{64}$')
    expected_revision: int = Field(ge=0)
    operation_id: str = Field(pattern=r'^[0-9a-f-]{32,36}$')
    reviewer: str = Field(min_length=1, max_length=200)
    reason: str = Field(min_length=1, max_length=8000)
    outcome: str = Field(pattern=r'^(NO_CHANGE|MINOR|MATERIAL|THESIS)$')


class FollowupNoteCreate(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    operation_id: str = Field(pattern=r'^[0-9a-f-]{32,36}$')
    object_type: str = Field(pattern=r'^(NODE|CLAIM|SOURCE|RELATION|GAP|RESEARCH_QUESTION)$')
    object_id: str = Field(min_length=1, max_length=240)
    text: str = Field(min_length=1, max_length=8000)
    status: str = Field(pattern=r'^(OPEN|DONE|DEFERRED)$')


class FollowupNoteUpdate(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    operation_id: str = Field(pattern=r'^[0-9a-f-]{32,36}$')
    expected_revision: int = Field(ge=1)
    text: str = Field(min_length=1, max_length=8000)
    status: str = Field(pattern=r'^(OPEN|DONE|DEFERRED)$')


class CloudJobSubmission(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    idempotency_key: str = Field(pattern=r'^[A-Za-z0-9][A-Za-z0-9._:-]{15,127}$')
    input_artifact_id: str = Field(pattern=r'^ART_[0-9a-f]{32}$')
    operation_kind: str = Field(pattern=r'^SEMANTIC_DECOMPOSITION$')


class SourceProcessRequest(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    idempotency_key: str = Field(pattern=r'^[A-Za-z0-9][A-Za-z0-9._:-]{15,127}$')
    reprocess_reason: str = Field(default='', max_length=1000)
    company_material_intent: dict[str, object] | None = None


def create_app(config: WorkbenchConfig | None = None, *, cloud_profile: CloudProfile | None = None,
               source_profile: SourceProfile | None = None):
    config = config or WorkbenchConfig.load(Path(os.environ['PRO_A_WORKBENCH_CONFIG']))
    config.validate()
    recover_workbench(config)
    with Store(config).connect():
        pass
    token = os.environ.get(config.session_token_env, '')
    if len(token) < 32 or len(token) > 512:
        raise BoundaryError('SESSION_SECRET_REQUIRED')
    signing_key = secrets.token_bytes(32)
    app = create_explorer_app(db_path=config.knowledge_db)
    app.title = 'pro_a native Review Workbench'
    artifacts = Artifacts(config)
    reviews = ReviewWorkbench(config)
    impacts = DirectImpact(config)
    research = ResearchExplorer(config)
    navigation = ResearchNavigation(config)
    structure_map = ResearchStructureMap(config, navigation=navigation)
    qualified_overlay = QualifiedResearchOverlay(config, structure_map=structure_map)
    company_materials = CompanyMaterials(config)
    jobs = CloudJobs(config, cloud_profile)
    sources = SourceOperations(config, source_profile, cloud_profile) if source_profile else None
    host = urlsplit(config.origin).netloc

    def session(request):
        try:
            body, signature = request.cookies.get(COOKIE, '').split('.')
            expected = hmac.new(signing_key, body.encode(), hashlib.sha256).hexdigest()
            if not hmac.compare_digest(signature, expected):
                return None
            value = json.loads(base64.urlsafe_b64decode(body))
            if value['expires_at'] <= time.time() or value['mode'] != config.mode:
                return None
            return value
        except (ValueError, KeyError):
            return None

    def denied(code, status=403):
        return JSONResponse({'detail': code}, status_code=status)

    @app.middleware('http')
    async def boundary(request: Request, call_next):
        async def guarded():
            if request.headers.get('host') != host:
                return denied('HOST_FORBIDDEN')
            if not config.remote and request.client and request.client.host not in ('127.0.0.1', '::1'):
                return denied('REMOTE_DISABLED')
            origin = request.headers.get('origin')
            if origin is not None and origin != config.origin:
                return denied('ORIGIN_FORBIDDEN')
            unsafe = request.method not in ('GET', 'HEAD', 'OPTIONS')
            if unsafe and origin != config.origin:
                return denied('ORIGIN_REQUIRED')
            login = request.url.path == PREFIX + '/session' and request.method == 'POST'
            identity = session(request)
            if not login and identity is None:
                return denied('SESSION_REQUIRED', 401)
            if unsafe and not login and not hmac.compare_digest(request.headers.get('x-csrf-token', ''), identity['csrf_token']):
                return denied('CSRF_REQUIRED')
            request.state.identity = identity
            config.check_knowledge()
            return await call_next(request)

        marker = WEB_REQUEST.set(True)
        try:
            response = await guarded()
        except Exception:
            response = denied('APPLICATION_UNAVAILABLE', 503)
        finally:
            WEB_REQUEST.reset(marker)
        response.headers['Cache-Control'] = 'no-store'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Referrer-Policy'] = 'no-referrer'
        response.headers['X-Frame-Options'] = 'DENY'
        return response

    @app.exception_handler(BoundaryError)
    async def boundary_error(_request, error):
        return denied(str(error), 404 if str(error) == 'ARTIFACT_NOT_REGISTERED' else 409)

    @app.exception_handler(ReviewError)
    async def review_error(_request, error):
        return JSONResponse({'detail': str(error), 'current_revision': error.current_revision, 'native_code': error.native_code}, status_code=error.status)

    @app.exception_handler(ImpactError)
    async def impact_error(_request, error):
        return JSONResponse({'detail': str(error), 'current_revision': error.current_revision}, status_code=error.status)

    @app.exception_handler(ResearchError)
    async def research_error(_request, error):
        return JSONResponse({'detail': str(error)}, status_code=error.status)

    @app.exception_handler(NoteError)
    async def note_error(_request, error):
        return JSONResponse({'detail': str(error), 'current_revision': error.current_revision}, status_code=error.status)

    @app.exception_handler(JobError)
    async def job_error(_request, error):
        return JSONResponse({'detail': str(error)}, status_code=error.status)

    @app.exception_handler(SourceOperationError)
    async def source_operation_error(_request, error):
        return JSONResponse({'detail': str(error)}, status_code=error.status)

    @app.exception_handler(CompanyMaterialError)
    async def company_material_error(_request, error):
        return JSONResponse({'detail': str(error)}, status_code=error.status)

    @app.exception_handler(RequestValidationError)
    async def bad_input(_request, _error):
        if _request.url.path.startswith(PREFIX + '/reviews/'):
            code = 'IMMUTABLE_FIELD_DRIFT' if any(item['type'] == 'extra_forbidden' for item in _error.errors()) else 'VALIDATION_ERROR'
            return denied(code, 422)
        return denied('INVALID_REQUEST', 422)

    @app.post(PREFIX + '/session')
    def login(body: Login):
        if not hmac.compare_digest(body.token.encode(), token.encode()):
            return denied('INVALID_CREDENTIAL', 401)
        identity = {'actor': 'operator', 'mode': config.mode, 'session_id': secrets.token_hex(16),
                    'csrf_token': secrets.token_hex(32), 'expires_at': int(time.time()) + 28800}
        encoded = base64.urlsafe_b64encode(json.dumps(identity).encode()).decode()
        signed = encoded + '.' + hmac.new(signing_key, encoded.encode(), hashlib.sha256).hexdigest()
        response = JSONResponse(identity)
        response.set_cookie(COOKIE, signed, max_age=28800, httponly=True, secure=config.remote,
                            samesite='strict', path='/')
        return response

    @app.get(PREFIX + '/session')
    def read_session(request: Request):
        return request.state.identity

    @app.get(PREFIX + '/review-packets')
    def packets():
        return {'packets': artifacts.listing()}

    @app.get(PREFIX + '/review-packets/{artifact_id}')
    def packet(artifact_id: str):
        return artifacts.read(artifact_id)

    @app.get(PREFIX + '/reviews/{artifact_id}')
    def review(artifact_id: str):
        result = reviews.read(artifact_id)
        with Store(config).connect() as connection:
            if schema_version(connection) in ('3', '4', '5', '6', '7', '8', '9', '10'): result['attribution_available'] = result['review']['status'] == 'SEALED'
        return result

    @app.get(PREFIX + '/reviews/{artifact_id}/projection')
    def review_projection(
        artifact_id: str,
        cursor: str | None = None,
        limit: int = Query(25, ge=1, le=100),
        queue: str = '',
        candidate_type: str = '',
        domain_id: str = '',
    ):
        return reviews.page(
            artifact_id, cursor=cursor, limit=limit, queue=queue,
            candidate_type=candidate_type, domain_id=domain_id,
        )

    @app.get(PREFIX + '/reviews/{artifact_id}/projection/{candidate_id}')
    def review_projection_item(artifact_id: str, candidate_id: str):
        return reviews.projected_item(artifact_id, candidate_id)

    @app.post(PREFIX + '/reviews/{artifact_id}/decisions')
    def decision(artifact_id: str, body: Decision, request: Request):
        return reviews.mutate(artifact_id, 'decision', body.model_dump(), request.state.identity)

    @app.post(PREFIX + '/reviews/{artifact_id}/undo')
    def undo(artifact_id: str, body: Undo, request: Request):
        return reviews.mutate(artifact_id, 'undo', body.model_dump(), request.state.identity)

    @app.post(PREFIX + '/reviews/{artifact_id}/validate')
    def validate(artifact_id: str, body: ReviewBasis):
        return reviews.validate_completion(artifact_id, body.expected_revision, body.basis_id)

    @app.post(PREFIX + '/reviews/{artifact_id}/seal')
    def seal(artifact_id: str, body: Seal, request: Request):
        return reviews.mutate(artifact_id, 'seal', body.model_dump(), request.state.identity)

    @app.get(PREFIX + '/reviews/{artifact_id}/sealed')
    def sealed(artifact_id: str):
        return reviews.sealed_result(artifact_id)

    @app.get(PREFIX + '/attribution/{artifact_id}')
    def attribution(artifact_id: str):
        from .attribution import Attribution
        return Attribution(config).read(artifact_id)

    @app.post(PREFIX + '/attribution/{artifact_id}/decisions')
    def attribution_decision(artifact_id: str, body: AttributionDecision, request: Request):
        from .attribution import Attribution
        return Attribution(config).mutate(artifact_id, 'SAVE', body.model_dump(), request.state.identity)

    @app.post(PREFIX + '/attribution/{artifact_id}/seal')
    def attribution_seal(artifact_id: str, body: Seal, request: Request):
        from .attribution import Attribution
        return Attribution(config).mutate(artifact_id, 'SEAL', body.model_dump(), request.state.identity)

    @app.post(PREFIX + '/attribution/{artifact_id}/qualify')
    def shadow_qualify(artifact_id: str, body: ObjectReference):
        from pro_a.operational_qualification import qualify, package_projection
        return package_projection(qualify(config, artifact_id, body.object_id))

    @app.post(PREFIX + '/attribution/{artifact_id}/reconcile')
    def reconcile(artifact_id: str, body: ObjectReference):
        from pro_a.operational_qualification import reconcile_registered
        return reconcile_registered(config, artifact_id, body.object_id)

    @app.get(PREFIX + '/current-views/{node_id}')
    def current_view_workbench(node_id: str):
        from pro_a.current_view_workbench import CurrentViewWorkbench
        return CurrentViewWorkbench(config).read(node_id)

    @app.put(PREFIX + '/current-views/{node_id}/draft')
    def save_current_view_draft(node_id: str, body: ViewDraftSave, request: Request):
        from pro_a.current_view_workbench import CurrentViewWorkbench
        return CurrentViewWorkbench(config).save(node_id, body.model_dump(), request.state.identity)

    @app.post(PREFIX + '/current-views/{node_id}/validate')
    def validate_current_view_draft(node_id: str, body: ViewDraftAction, request: Request):
        from pro_a.current_view_workbench import CurrentViewWorkbench
        return CurrentViewWorkbench(config).validate(node_id, body.model_dump(), request.state.identity)

    @app.post(PREFIX + '/current-views/{node_id}/qualify')
    def qualify_current_view_draft(node_id: str, body: ViewQualification):
        from pro_a.current_view_workbench import CurrentViewWorkbench
        package = CurrentViewWorkbench(config).qualify(node_id, body.draft_id, body.revision)
        return {'object_id': package['object_id'], 'adapter_version': package['adapter_version'],
                'production_authorized': False, 'predicted_diff': package['predicted_diff'],
                'operator_action': 'EXTERNAL_OPERATOR_REQUIRED'}

    @app.post(PREFIX + '/current-views/{node_id}/reconcile')
    def reconcile_current_view(node_id: str, body: ObjectReference):
        from pro_a.current_view_workbench import CurrentViewWorkbench
        return CurrentViewWorkbench(config).reconcile(node_id, body.object_id)

    @app.get(PREFIX + '/impact/changes')
    def impact_changes(limit: int = 50, offset: int = 0):
        return impacts.changes(limit=limit, offset=offset)

    @app.get(PREFIX + '/impact/item/{impact_id}')
    def impact_item(impact_id: str):
        return impacts.item(impact_id)

    @app.put(PREFIX + '/impact/item/{impact_id}/attention')
    def impact_attention(impact_id: str, body: ImpactAttention, request: Request):
        return impacts.set_attention(impact_id, body.model_dump(), request.state.identity)

    @app.get(PREFIX + '/sources/{source_id}/impact')
    def source_impact(source_id: str):
        return impacts.source(source_id)

    @app.get(PREFIX + '/claims/{claim_id}/impact')
    def claim_impact(claim_id: str):
        return impacts.claim(claim_id)

    @app.get(PREFIX + '/nodes/{node_id}/impact')
    def node_impact(node_id: str):
        return impacts.node(node_id)

    @app.get(PREFIX + '/views/{view_id}/evidence-impact')
    def view_impact(view_id: str):
        return impacts.view(view_id)

    @app.get(PREFIX + '/research/home')
    def research_home():
        return research.home()

    @app.get(PREFIX + '/research/search')
    def research_search(q: str, object_type: str = '', limit: int = 30):
        return research.search(q, object_type=object_type, limit=limit)

    @app.get(PREFIX + '/research/domains')
    def research_domains():
        return navigation.list_domains()

    @app.get(PREFIX + '/research/domains/{domain_id}/tree')
    def research_domain_tree(domain_id: str, max_depth: int | None = None):
        return navigation.domain_tree(domain_id, max_depth=max_depth)

    @app.get(PREFIX + '/research/domains/{domain_id}/structure-map')
    def research_domain_structure_map(domain_id: str, mode: str | None = None,
                                      node_id: str | None = None, depth: int | None = None):
        return structure_map.structure_map(domain_id, mode=mode, node_id=node_id, depth=depth)

    @app.get(PREFIX + '/research/qualified-overlay')
    def research_qualified_overlay():
        return qualified_overlay.summary()

    @app.get(PREFIX + '/research/qualified-overlay/governance')
    def research_qualified_governance():
        return qualified_overlay.governance()

    @app.get(PREFIX + '/research/qualified-overlay/search')
    def research_qualified_search(q: str):
        return qualified_overlay.search(q)

    @app.get(PREFIX + '/research/qualified-overlay/nodes/{candidate_id}')
    def research_qualified_node(candidate_id: str):
        return qualified_overlay.node(candidate_id)

    @app.get(PREFIX + '/research/qualified-overlay/relations/{candidate_id}')
    def research_qualified_relation(candidate_id: str):
        return qualified_overlay.relation(candidate_id)

    @app.get(PREFIX + '/research/qualified-overlay/canonical/{node_id}')
    def research_qualified_canonical_provenance(node_id: str):
        return qualified_overlay.canonical_provenance(node_id)

    @app.get(PREFIX + '/research/domains/{domain_id}/qualified-structure-map')
    def research_qualified_structure_map(domain_id: str, mode: str | None = None,
                                         node_id: str | None = None, qualified_id: str | None = None,
                                         depth: int | None = None):
        return qualified_overlay.structure_map(domain_id, mode=mode, node_id=node_id,
                                               qualified_id=qualified_id, depth=depth)

    @app.get(PREFIX + '/research/nodes/{node_id}/domain-context')
    def research_node_domain_context(node_id: str):
        return navigation.node_domain_context(node_id)

    @app.get(PREFIX + '/research/companies/search')
    def research_company_search(q: str, limit: int = 20):
        return company_materials.search(q, limit=limit)

    @app.get(PREFIX + '/research/companies/{company_node_id}')
    def research_company(company_node_id: str):
        return company(config, company_node_id)

    @app.get(PREFIX + '/research/companies/{company_node_id}/materials')
    def research_company_materials(company_node_id: str, limit: int = 20,
                                   cursor: str | None = None):
        return company_materials.timeline(company_node_id, limit=limit, cursor=cursor)

    @app.get(PREFIX + '/research/nodes/{node_id}')
    def research_node(node_id: str):
        return research.node(node_id)

    @app.get(PREFIX + '/research/claims')
    def research_claims(cursor: str | None = None, limit: int = 25, q: str = '', source_id: str = '',
                        node_id: str = '', role: str = '', nature: str = '', status: str = '',
                        date_from: str = '', date_to: str = '', cited: bool | None = None,
                        linked: bool | None = None):
        return research.claims(cursor=cursor, limit=limit, q=q, source_id=source_id,
                               node_id=node_id, role=role, nature=nature, status=status,
                               date_from=date_from, date_to=date_to, cited=cited, linked=linked)

    @app.get(PREFIX + '/research/claims/{claim_id}')
    def research_claim(claim_id: str):
        return research.claim(claim_id)

    @app.get(PREFIX + '/research/sources')
    def research_sources(cursor: str | None = None, limit: int = 25, q: str = '', source_type: str = '',
                         status: str = '', date_from: str = '', date_to: str = '',
                         has_claims: bool | None = None, has_attribution: bool | None = None):
        return research.sources(cursor=cursor, limit=limit, q=q, source_type=source_type,
                                status=status, date_from=date_from, date_to=date_to,
                                has_claims=has_claims, has_attribution=has_attribution)

    @app.get(PREFIX + '/research/sources/{source_id}')
    def research_source(source_id: str, claim_cursor: str | None = None, claim_limit: int = 25,
                        claim_q: str = '', claim_status: str = '', claim_nature: str = ''):
        return research.source(source_id, claim_cursor=claim_cursor, claim_limit=claim_limit,
                               claim_q=claim_q, claim_status=claim_status, claim_nature=claim_nature)

    @app.get(PREFIX + '/research/relations')
    def research_relations(cursor: str | None = None, limit: int = 25, node_id: str = '',
                           status: str = '', relation_type: str = ''):
        return research.relations(cursor=cursor, limit=limit, node_id=node_id,
                                  status=status, relation_type=relation_type)

    @app.get(PREFIX + '/research/relations/{relation_id}')
    def research_relation(relation_id: str):
        return research.relation(relation_id)

    @app.get(PREFIX + '/research/coverage')
    def research_coverage(cursor: str | None = None, limit: int = 25):
        return research.coverage(cursor=cursor, limit=limit)

    @app.get(PREFIX + '/research/questions')
    def research_questions(cursor: str | None = None, limit: int = 25, status: str = ''):
        return research.questions(cursor=cursor, limit=limit, status=status)

    @app.get(PREFIX + '/research/gaps')
    def research_gaps(cursor: str | None = None, limit: int = 25, status: str = ''):
        return research.gaps(cursor=cursor, limit=limit, status=status)

    @app.get(PREFIX + '/research/notes')
    def research_notes(object_type: str = '', object_id: str = '', status: str = '', limit: int = 50):
        return research.notes.list(object_type=object_type, object_id=object_id, status=status, limit=limit)

    @app.post(PREFIX + '/research/notes')
    def create_research_note(body: FollowupNoteCreate, request: Request):
        research.validate_object(body.object_type, body.object_id)
        return research.notes.create(body.model_dump(), request.state.identity)

    @app.put(PREFIX + '/research/notes/{note_id}')
    def update_research_note(note_id: str, body: FollowupNoteUpdate, request: Request):
        return research.notes.update(note_id, body.model_dump(), request.state.identity)

    @app.post(PREFIX + '/jobs')
    def submit_cloud_job(body: CloudJobSubmission):
        return jobs.submit(**body.model_dump())

    @app.get(PREFIX + '/jobs')
    def list_cloud_jobs(status: str = '', cursor: str | None = None, limit: int = 25):
        return jobs.list(status=status, cursor=cursor, limit=limit)

    @app.get(PREFIX + '/jobs/{job_id}')
    def get_cloud_job(job_id: str):
        return jobs.get(job_id)

    @app.get(PREFIX + '/jobs/{job_id}/events')
    def get_cloud_job_events(job_id: str, cursor: str | None = None, limit: int = 50):
        return jobs.events(job_id, cursor=cursor, limit=limit)

    @app.get(PREFIX + '/jobs/{job_id}/artifacts')
    def get_cloud_job_artifacts(job_id: str):
        return jobs.results(job_id)

    def source_service() -> SourceOperations:
        if sources is None:
            raise SourceOperationError('SOURCE_OPERATIONS_UNAVAILABLE', 503)
        return sources

    @app.post(PREFIX + '/source-operations/upload')
    async def upload_source(request: Request):
        filename = unquote(request.headers.get('x-source-filename', ''))
        return await source_service().upload(
            request.stream(), filename=filename,
            mime_type=request.headers.get('content-type', ''),
        )

    @app.post(PREFIX + '/source-operations/{source_id}/process')
    def process_source(source_id: str, body: SourceProcessRequest):
        return source_service().start(source_id, **body.model_dump())

    @app.get(PREFIX + '/source-operations')
    def list_source_operations(status: str = '', cursor: str | None = None, limit: int = 25):
        return source_service().list(status=status, cursor=cursor, limit=limit)

    @app.get(PREFIX + '/source-operations/metrics')
    def source_operation_metrics():
        return source_service().metrics()

    @app.get(PREFIX + '/source-operations/runs/{processing_run_id}')
    def source_processing_run(processing_run_id: str):
        return source_service().get_run(processing_run_id)

    @app.get(PREFIX + '/source-operations/runs/{processing_run_id}/events')
    def source_processing_events(processing_run_id: str, cursor: str | None = None,
                                 limit: int = 50):
        return source_service().events(processing_run_id, cursor=cursor, limit=limit)

    @app.get(PREFIX + '/source-operations/{source_id}/runs')
    def source_run_history(source_id: str, cursor: str | None = None, limit: int = 25):
        return source_service().run_history(source_id, cursor=cursor, limit=limit)

    @app.get(PREFIX + '/source-operations/{source_id}')
    def source_operation_detail(source_id: str):
        return source_service().source(source_id)

    return app
