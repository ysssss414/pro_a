"""Opt-in, artifact-scoped stdio advice/proposals; no human or Canonical authority."""
from functools import wraps
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from pro_a.review_engine import ReviewEngine, ReviewerConfig as WritePolicy, AdviceItem, plain
from pro_a.workbench.config import BoundaryError
from pro_a.workbench.review_batch import require
from .errors import BridgeError, check_payload
from .service import ArtifactId, ContextHash, Identifier


WRITE_TOOLS = ('submit_reviewer_advice', 'prepare_human_review_batch', 'prepare_attribution_batch')
EXTRA_READ_TOOLS = ('get_review_batch_context', 'get_shadow_qualification')


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
        self.engine = ReviewEngine(config, policy)
        self.config, self.policy, self.batches = config, policy, self.engine.batches

    def guard(self, handle):
        require(self.policy.enabled and handle in self.policy.artifact_ids, 'MCP_WRITE_SCOPE_DENIED')
        self.config.validate()

    @controlled
    def submit_reviewer_advice(self, artifact_id: ArtifactId, slot: Literal['A', 'B'],
                               reviewer_id: Identifier, context_sha256: ContextHash,
                               items: list[AdviceItem]) -> dict[str, object]:
        return self.engine.submit(artifact_id, slot, reviewer_id, context_sha256, items)

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
        from pro_a.operational_qualification import registered_historical_read
        require(type(limit) is int and 1 <= limit <= 50 and type(cursor) is int and cursor >= 0, 'INVALID_ARGUMENT')
        projected = registered_historical_read(self.config, artifact_id)['qualification']
        require(projected is not None, 'SHADOW_QUALIFICATION_REQUIRED')
        # Shadow diagnostics contain schema-wide internals; expose only the verified diff.
        projected.pop('shadow_validation', None)
        changes = projected.pop('changes')
        from collections import Counter
        projected.update(changes=changes[cursor:cursor + limit], total_changes=len(changes),
                         next_cursor=cursor + limit if cursor + limit < len(changes) else None,
                         insert_counts=dict(Counter(i['table'] for i in changes if i['action'] == 'INSERT')))
        return projected
