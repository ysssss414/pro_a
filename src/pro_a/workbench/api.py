from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
from pathlib import Path
import secrets
import time
from urllib.parse import urlsplit

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from pro_a.api import create_app as create_explorer_app
from .artifacts import Artifacts
from .config import BoundaryError, WorkbenchConfig
from .store import Store
from .review_store import recover_workbench
from .review_workbench import ReviewError, ReviewWorkbench

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


def create_app(config: WorkbenchConfig | None = None):
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

        try:
            response = await guarded()
        except Exception:
            response = denied('APPLICATION_UNAVAILABLE', 503)
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
        return reviews.read(artifact_id)

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

    return app
