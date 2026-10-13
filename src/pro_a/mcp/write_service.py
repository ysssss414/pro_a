"""Opt-in, artifact-scoped stdio advice/proposals; no human or Canonical authority."""
from functools import wraps
import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from pro_a.workbench.advisory_review import AdvisoryReview, validate_opinion
from pro_a.workbench.config import BoundaryError
from pro_a.workbench.review_batch import ReviewBatch, require
from .errors import BridgeError, check_payload
from .service import ArtifactId, ContextHash, Identifier


WRITE_TOOLS = ('submit_reviewer_advice', 'prepare_human_review_batch', 'prepare_attribution_batch')
EXTRA_READ_TOOLS = ('get_review_batch_context', 'get_shadow_qualification')


class AdviceItem(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    candidate_id: Identifier
    content_sha256: ContextHash
    judgment: Literal['SUPPORTED', 'UNSUPPORTED', 'UNCERTAIN']
    reason: str = Field(min_length=1, max_length=8000)


class HumanReviewItem(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    candidate_id: Identifier
    content_sha256: ContextHash
    decision: Literal['KEEP', 'KEEP_NEEDS_REVIEW', 'DROP', 'CREATE', 'REUSE', 'DEFER', 'REJECT']
    reason: str = Field(min_length=1, max_length=8000)
    target_node_id: str = Field(max_length=200)


class AttributionLink(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    node_id: Identifier
    role: Literal['subject', 'context', 'related']


class AttributionItem(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    claim_id: Identifier
    content_sha256: ContextHash
    outcome: Literal['LINK', 'MULTI_LINK', 'NO_LINK', 'DEFER']
    reason: str = Field(min_length=1, max_length=8000)
    scope: str = Field(max_length=8000)
    links: list[AttributionLink] = Field(max_length=100)


def plain(value):
    if isinstance(value, BaseModel):
        return value.model_dump(mode='json')
    if isinstance(value, list):
        return [plain(v) for v in value]
    if isinstance(value, dict):
        return {k: plain(v) for k, v in value.items()}
    return value


class WritePolicy(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True, frozen=True)
    enabled: bool = False
    artifact_ids: tuple[str, ...]
    slot: Literal['A', 'B']
    reviewer_id: str = Field(min_length=1, max_length=200)
    execution_id: str = Field(min_length=1, max_length=200)
    model: str = Field(min_length=1, max_length=200)
    isolation_attested_by_operator: bool = False


def controlled(fn):
    @wraps(fn)
    def call(self, artifact_id, *args, **kwargs):
        try:
            self.guard(artifact_id)
            args, kwargs = plain(list(args)), plain(kwargs)
            check_payload({'args': list(args), **kwargs})
            result = fn(self, artifact_id, *args, **kwargs)
            check_payload(result)
            return result
        except BridgeError:
            raise
        except BoundaryError as error:
            # Only fixed internal codes, never echo untrusted exception text.
            code = str(error)
            import re
            raise BridgeError(code if re.fullmatch('[A-Z][A-Z0-9_]{1,80}', code) else 'WRITE_REJECTED') from None
        except Exception:
            raise BridgeError('CONTROLLED_REVIEW_UNAVAILABLE') from None
    return call


class WriteService:
    def __init__(self, config, policy: WritePolicy):
        self.config, self.policy = config, policy
        require(policy.enabled and policy.isolation_attested_by_operator and policy.artifact_ids, 'MCP_WRITE_DISABLED')
        config.validate()
        self.batches = ReviewBatch(config)
        with self.batches.store.connect() as connection:
            require(connection.execute("SELECT value FROM workbench_meta WHERE key='schema_version'").fetchone()[0] == '12', 'WORKBENCH_SCHEMA_REQUIRED')
        check_payload(policy.model_dump(mode='json'))

    def guard(self, handle):
        require(self.policy.enabled and handle in self.policy.artifact_ids, 'MCP_WRITE_SCOPE_DENIED')
        self.config.validate()

    @controlled
    def submit_reviewer_advice(self, artifact_id: ArtifactId, slot: Literal['A', 'B'],
                               reviewer_id: Identifier, context_sha256: ContextHash,
                               items: list[AdviceItem]) -> dict[str, object]:
        require(slot == self.policy.slot and reviewer_id == self.policy.reviewer_id, 'REVIEWER_BINDING_MISMATCH')
        require(0 < len(items) <= 100, 'ADVICE_UNIVERSE_INVALID')
        with self.batches.store.connect() as connection:
            _, executions = self.batches.events(connection, artifact_id, 'MCP_ADVICE_CONTEXT')
        require(all(p['slot'] == slot or p['execution_id'] != self.policy.execution_id for p in executions),
                'INDEPENDENT_REVIEW_REQUIRED')
        require(all(p['slot'] != slot or (p['execution_id'] == self.policy.execution_id and
                    p['model'] == self.policy.model) for p in executions), 'REVIEW_EXECUTION_CONFLICT')
        service = AdvisoryReview(self.batches.reviews)
        value = service.submit(artifact_id, {'slot': slot, 'reviewer_type': 'MODEL',
            'reviewer_id': reviewer_id, 'context_sha256': context_sha256, 'items': items})
        packet = self.batches.reviews._context(artifact_id)[0]
        # Read the durable opinion and its native registration, including a first A-only submission.
        persisted = json.loads(service._path(packet, slot).read_text(encoding='utf-8'))
        validate_opinion(packet, persisted)
        service._registered(packet, persisted)
        require(persisted == value, 'ADVICE_REGISTERED_IDENTITY_MISMATCH')
        provenance = {'slot': slot, 'opinion_sha256': value['sha256'], 'reviewer_id': reviewer_id,
                      'execution_id': self.policy.execution_id, 'model': self.policy.model,
                      'independence_evidence': 'OPERATOR_ATTESTED_SEPARATE_SESSION_NOT_PLATFORM_PROVEN'}
        with self.batches.store.connect(operator_write=True) as connection:
            connection.execute('BEGIN IMMEDIATE')
            _, existing = self.batches.events(connection, artifact_id, 'MCP_ADVICE_CONTEXT')
            prior = [p for p in existing if p['slot'] == slot]
            require(not prior or prior == [provenance], 'REVIEW_EXECUTION_CONFLICT')
            if not prior:
                require(all(p['execution_id'] != provenance['execution_id'] for p in existing), 'INDEPENDENT_REVIEW_REQUIRED')
                self.batches.record(connection, artifact_id, 'MCP_ADVICE_CONTEXT', provenance)
        return {'opinion': persisted, 'execution': provenance}

    @controlled
    def get_review_batch_context(self, artifact_id: ArtifactId, kind: Literal['native', 'attribution'] = 'native') -> dict[str, object]:
        binding, state, context, _, opinions = self.batches.snapshot(artifact_id, kind)
        result = {'binding': binding, 'basis_id': state['basis_id'], 'revision': state['revision'],
                  'status': state['status'], 'advice': opinions, 'production_authorized': False}
        if kind == 'native':
            result['candidates'] = [{k: row[k] for k in ('candidate_id', 'candidate_type', 'content_sha256', 'content')}
                                    for group in ('claims', 'nodes', 'relations') for row in context[group]]
        else:
            content = {r['candidate_id']: r['content_sha256'] for r in context['packet']['claims']}
            result['claims'] = [{**row, 'content_sha256': content[cid]} for cid, row in context['claims'].items()]
            result['nodes'] = list(context['nodes'].values())
            result['roles'] = state['roles']
        return result

    @controlled
    def prepare_human_review_batch(self, artifact_id: ArtifactId, binding: dict, expected_revision: int,
                                   items: list[HumanReviewItem], reason: str) -> dict[str, object]:
        return self.batches.prepare(artifact_id, 'native', binding, expected_revision, items, reason)

    @controlled
    def prepare_attribution_batch(self, artifact_id: ArtifactId, binding: dict, expected_revision: int,
                                  items: list[AttributionItem], reason: str) -> dict[str, object]:
        return self.batches.prepare(artifact_id, 'attribution', binding, expected_revision, items, reason)

    @controlled
    def get_shadow_qualification(self, artifact_id: ArtifactId, limit: int = 25, cursor: int = 0) -> dict[str, object]:
        from pro_a.operational_qualification import package_projection, validate_package
        from pro_a.workbench.attribution import Attribution
        require(type(limit) is int and 1 <= limit <= 50 and type(cursor) is int and cursor >= 0, 'INVALID_ARGUMENT')
        context, sidecar = Attribution(self.config).sealed_context(artifact_id)
        with self.batches.store.connect() as connection:
            row = connection.execute('SELECT body FROM operational_packages WHERE artifact_id=?', (artifact_id,)).fetchone()
            receipt = connection.execute('SELECT body FROM operational_receipts WHERE artifact_id=?', (artifact_id,)).fetchone()
        require(row is not None, 'SHADOW_QUALIFICATION_REQUIRED')
        envelope = json.loads(row[0])
        validate_package(envelope, context, sidecar)
        projected = package_projection(envelope)
        # Shadow diagnostics contain schema-wide internals; expose only the verified diff.
        projected.pop('shadow_validation', None)
        changes = projected.pop('changes')
        from collections import Counter
        projected.update(changes=changes[cursor:cursor + limit], total_changes=len(changes),
                         next_cursor=cursor + limit if cursor + limit < len(changes) else None,
                         insert_counts=dict(Counter(i['table'] for i in changes if i['action'] == 'INSERT')),
                         operator_status='RECEIPT_REGISTERED_UNVERIFIED' if receipt else 'AWAITING_OPERATOR_ACTION')
        return projected
