"""Shared Advice engine. Model configuration is trusted operator input, never model output.

The legacy MCP_ADVICE_CONTEXT event name remains the cross-channel provenance
contract so historical Human batch validation stays byte compatible.
"""
import json
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field
from pro_a.read_model.errors import check_payload
from pro_a.read_model.service import ArtifactId, ContextHash, Identifier
from pro_a.workbench.advisory_review import AdvisoryReview, validate_opinion
from pro_a.workbench.review_batch import ReviewBatch, require
from pro_a.workbench.review_policy import ReviewPolicy, slots


class AdviceItem(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    candidate_id: Identifier
    content_sha256: ContextHash
    judgment: Literal['SUPPORTED', 'UNSUPPORTED', 'UNCERTAIN']
    reason: str = Field(min_length=1, max_length=8000)


def plain(value):
    if isinstance(value, BaseModel):
        return value.model_dump(mode='json')
    if isinstance(value, list):
        return [plain(v) for v in value]
    if isinstance(value, dict):
        return {k: plain(v) for k, v in value.items()}
    return value


class ReviewerConfig(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True, frozen=True)
    enabled: bool = False
    artifact_ids: tuple[str, ...]
    slot: Literal['A', 'B']
    reviewer_id: str = Field(min_length=1, max_length=200)
    execution_id: str = Field(min_length=1, max_length=200)
    model: str = Field(min_length=1, max_length=200)
    isolation_attested_by_operator: bool = False
    review_mode: Literal['SINGLE_MODEL_HUMAN', 'DUAL_MODEL_HUMAN'] = 'DUAL_MODEL_HUMAN'


class ReviewEngine:
    def __init__(self, config, policy: ReviewerConfig):
        self.config, self.policy = config, policy
        require(policy.enabled and policy.artifact_ids and
                (policy.isolation_attested_by_operator or policy.review_mode == 'SINGLE_MODEL_HUMAN'), 'MCP_WRITE_DISABLED')
        require(policy.review_mode != 'SINGLE_MODEL_HUMAN' or policy.slot == 'A', 'REVIEWER_BINDING_MISMATCH')
        config.validate()
        self.batches = ReviewBatch(config)
        with self.batches.store.connect() as connection:
            require(connection.execute("SELECT value FROM workbench_meta WHERE key='schema_version'").fetchone()[0] == '12', 'WORKBENCH_SCHEMA_REQUIRED')
        check_payload(policy.model_dump(mode='json'))


    def guard(self, handle):
        require(self.policy.enabled and handle in self.policy.artifact_ids, 'MCP_WRITE_SCOPE_DENIED')
        self.config.validate()
        from pro_a.workbench.candidate_lifecycle import require_handle
        require_handle(self.config, handle)

    def reviewer_binding(self, artifact_id, slot, reviewer_id):
        self.guard(artifact_id)
        require(slot == self.policy.slot and reviewer_id == self.policy.reviewer_id, 'REVIEWER_BINDING_MISMATCH')
        review_policy = ReviewPolicy(self.batches.reviews).read(artifact_id)
        mode = review_policy['mode'] if review_policy else 'DUAL_MODEL_HUMAN'
        require(mode == self.policy.review_mode and slot in slots(review_policy), 'ADVICE_POLICY_MISMATCH')
        with self.batches.store.connect() as connection:
            _, executions = self.batches.events(connection, artifact_id, 'MCP_ADVICE_CONTEXT')
        require(all(p['slot'] == slot or p['execution_id'] != self.policy.execution_id for p in executions),
                'INDEPENDENT_REVIEW_REQUIRED')
        require(all(p['slot'] != slot or (p['execution_id'] == self.policy.execution_id and
                    p['model'] == self.policy.model) for p in executions), 'REVIEW_EXECUTION_CONFLICT')
        return review_policy

    def submit(self, artifact_id: ArtifactId, slot: Literal['A', 'B'],
               reviewer_id: Identifier, context_sha256: ContextHash,
               items: list[AdviceItem]) -> dict[str, object]:
        review_policy = self.reviewer_binding(artifact_id, slot, reviewer_id)
        mode = review_policy['mode'] if review_policy else 'DUAL_MODEL_HUMAN'
        items = plain(items)
        require(isinstance(items, list) and 0 < len(items) <= 100, 'ADVICE_UNIVERSE_INVALID')
        items = [AdviceItem.model_validate(item).model_dump() for item in items]
        check_payload({'items': items})
        service = AdvisoryReview(self.batches.reviews)
        value = service.submit(artifact_id, {'slot': slot, 'reviewer_type': 'MODEL',
            'reviewer_id': reviewer_id, 'context_sha256': context_sha256, 'items': items})
        packet = self.batches.reviews._context(artifact_id)[0]
        # Read the durable opinion and its native registration, including a first A-only submission.
        persisted = json.loads(service._path(packet, slot).read_text(encoding='utf-8'))
        validate_opinion(packet, persisted, review_policy)
        service._registered(packet, persisted)
        require(persisted == value, 'ADVICE_REGISTERED_IDENTITY_MISMATCH')
        provenance = {'slot': slot, 'opinion_sha256': value['sha256'], 'reviewer_id': reviewer_id,
                      'execution_id': self.policy.execution_id, 'model': self.policy.model,
                      'independence_evidence': ('SINGLE_MODEL_OPERATOR_CONFIGURED_NOT_PLATFORM_PROVEN'
                          if mode == 'SINGLE_MODEL_HUMAN' else 'OPERATOR_ATTESTED_SEPARATE_SESSION_NOT_PLATFORM_PROVEN')}
        with self.batches.store.connect(operator_write=True) as connection:
            connection.execute('BEGIN IMMEDIATE')
            from pro_a.workbench.candidate_lifecycle import require_handle
            require_handle(self.config, artifact_id, connection=connection)
            _, existing = self.batches.events(connection, artifact_id, 'MCP_ADVICE_CONTEXT')
            prior = [p for p in existing if p['slot'] == slot]
            require(not prior or prior == [provenance], 'REVIEW_EXECUTION_CONFLICT')
            if not prior:
                require(all(p['execution_id'] != provenance['execution_id'] for p in existing), 'INDEPENDENT_REVIEW_REQUIRED')
                self.batches.record(connection, artifact_id, 'MCP_ADVICE_CONTEXT', provenance)
        return {'opinion': persisted, 'execution': provenance}

    def run(self, artifact_id, context_sha256, backend, *, task_id):
        from .review_execution import run
        return run(self, artifact_id, context_sha256, backend, task_id=task_id)
