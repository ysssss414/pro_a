"""Bounded post-extraction semantic decomposition over frozen Claims.

The deterministic layer creates stable Evidence units before inference. The
semantic backend may only select their IDs and bounded semantic enums.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any, Mapping, Protocol, Sequence

from .analyzer import canonicalize_text
from .llm import ChatLLM, LLMError
from .proposition_ir import (
    COHERENCE_TYPES,
    MODALITIES,
    NATURES,
    PREDICATE_FAMILIES,
    PROPOSITION_IR_VERSION,
    TIME_SCOPES,
    derived_evidence_unit_id,
    derived_proposition_id,
    validate_proposition_ir,
)


SEMANTIC_DECOMPOSITION_SYSTEM = f"""
You perform bounded semantic decomposition of existing frozen Claims.

Hard invariants:
- Return exactly one result for every supplied parent_claim_id and copy that ID exactly.
- Never create, rewrite, merge, split, renumber, or omit a parent Claim.
- Analyze only claim_text, evidence_units, and the minimal metadata supplied for that Claim.
- Evidence units are immutable. Select one or more existing evidence_unit_id values for every proposition.
- Never invent Evidence text, quotes, character offsets, locators, or Evidence IDs.
- If safe decomposition is not possible, return ir_status=AMBIGUOUS and units=[].
- A proposition unit is independently reviewable; it is not every noun or number.
- Units independently acceptable, rejectable, updateable, or sourceable use separate coherence_key values and coherence_type=INDEPENDENT.
- Units that together express one canonical vector, scenario, route, event, or bounded causal judgment share one coherence_key and the most specific non-INDEPENDENT coherence_type.
- Protect these coherent single-Claim forms: coordinated specifications; paired simulation outputs; capacity/size/weight comparisons; P=UI calculations; one-period reporting vectors; sequential architecture routes; bounded analyst causal judgments; attributes of one event.
- Do not group independent lifecycle events, counterparties/projects, capabilities, or status-plus-scale facts merely because they share a subject.
- Do not output subject, predicate text, explanation, rewritten text, quotes, raw offsets, or external knowledge.
- Digits alone do not make a proposition data. Measurements and calculated quantities may be data; project/validation/production/deployment/operating status remains fact.
- A source reporting that a company proposed an architecture is an actual reporting fact; the architecture proposal complement is not automatically a forecast.
- Expert/analyst qualitative conclusions retain their attributed epistemic nature.
- Distinguish future auxiliaries (预计将/未来将/计划将/将进一步提高) from object-fronting constructions (将800V转换为50V/将方案应用于/可将温升控制在/提出将高压电分配).

Allowed predicate_family: {', '.join(PREDICATE_FAMILIES)}
Allowed modality: {', '.join(MODALITIES)}
Allowed time_scope: {', '.join(TIME_SCOPES)}
Allowed nature: {', '.join(NATURES)}
Allowed coherence_type: {', '.join(COHERENCE_TYPES)}

Return one JSON object only:
{{
  "claims": [
    {{
      "parent_claim_id": "exact input ID",
      "ir_status": "VALID or AMBIGUOUS",
      "units": [
        {{
          "predicate_family": "allowed enum",
          "modality": "allowed enum",
          "nature": "allowed enum",
          "support_evidence_unit_ids": ["one or more existing IDs"],
          "coherence_key": "k1",
          "coherence_type": "allowed enum",
          "time_scope": "allowed enum"
        }}
      ]
    }}
  ]
}}
""".strip()

SEMANTIC_DECOMPOSITION_USER = """Analyze exactly these frozen Claims.
The array is the complete batch. Do not return any other parent_claim_id.

{claims_json}
"""

SEMANTIC_MAX_OUTPUT_TOKENS = 8_192

MODEL_RESULT_FIELDS = {"parent_claim_id", "ir_status", "units"}
MODEL_UNIT_FIELDS = {
    "predicate_family",
    "modality",
    "nature",
    "support_evidence_unit_ids",
    "coherence_key",
    "coherence_type",
    "time_scope",
}

_EVIDENCE_BOUNDARY = re.compile(r"\s*(?:[，,；;。！？!?]+)\s*")


class SemanticDecompositionError(RuntimeError):
    pass


class SemanticBackend(Protocol):
    """Backend-neutral boundary for cloud or a future local implementation."""

    @property
    def backend_name(self) -> str: ...

    @property
    def last_call_metadata(self) -> Mapping[str, Any]: ...

    def decompose_batch(self, claims: Sequence[Mapping[str, Any]]) -> dict[str, Any]: ...


class ChatLLMSemanticBackend:
    """Configured ChatLLM adapter; it does not change extraction."""

    def __init__(self, llm: ChatLLM):
        self.llm = llm

    @property
    def backend_name(self) -> str:
        return f"chat-completions:{self.llm.cfg.model}"

    @property
    def last_call_metadata(self) -> Mapping[str, Any]:
        return self.llm.last_call_metadata

    def decompose_batch(self, claims: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
        payload = [
            {
                "parent_claim_id": item["claim_id"],
                "claim_text": item["claim_text"],
                "evidence_units": item["evidence_units"],
                "attribution": item.get("attribution") or "",
                "scope": item.get("scope") or "",
                "fact_time": item.get("fact_time") or "",
                "assigned_nature": item.get("assigned_nature") or "",
            }
            for item in claims
        ]
        user = SEMANTIC_DECOMPOSITION_USER.format(
            claims_json=json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        )
        return self.llm.json(SEMANTIC_DECOMPOSITION_SYSTEM, user)


def build_evidence_units(
    *, parent_claim_id: str, bounded_evidence: str, source_locator: str
) -> list[dict[str, Any]]:
    """Segment already-bounded Evidence into stable normalized clauses."""
    normalized = canonicalize_text(bounded_evidence)
    clauses = [canonicalize_text(item) for item in _EVIDENCE_BOUNDARY.split(normalized)]
    clauses = [item for item in clauses if item]
    if not clauses and normalized:
        clauses = [normalized]
    units: list[dict[str, Any]] = []
    for order, text in enumerate(clauses):
        units.append(
            {
                "evidence_unit_id": derived_evidence_unit_id(
                    parent_claim_id, text, source_locator, order
                ),
                "normalized_text": text,
                "source_locator": source_locator,
                "order": order,
            }
        )
    return units


def build_semantic_claim_inputs(
    *,
    bundle: Mapping[str, Any],
    evidence_draft: Mapping[str, Any],
    quote_fidelity: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Build minimal deterministic inputs without PDF text or node catalogs."""
    evidence_by_id = {
        item["claim_id"]: item for item in evidence_draft.get("claims") or []
    }
    quote_by_id = {
        item["claim_id"]: item for item in quote_fidelity.get("claims") or []
    }
    claims = list(bundle.get("claims") or [])
    claim_ids = [str(item.get("claim_id") or "") for item in claims]
    if not all(claim_ids) or len(set(claim_ids)) != len(claim_ids):
        raise SemanticDecompositionError("PRIMARY_CLAIM_IDS_MISSING_OR_DUPLICATE")
    if not set(claim_ids) <= set(evidence_by_id) or not set(claim_ids) <= set(quote_by_id):
        raise SemanticDecompositionError("SEMANTIC_INPUT_EVIDENCE_UNIVERSE_MISMATCH")
    result: list[dict[str, Any]] = []
    for claim in claims:
        claim_id = str(claim["claim_id"])
        quote = quote_by_id[claim_id]
        contract = quote.get("evidence_contract") or {}
        bounded_evidence = str(
            contract.get("canonical_ready_evidence")
            or claim.get("evidence_excerpt")
            or evidence_by_id[claim_id].get("original_evidence_excerpt")
            or ""
        )
        if not bounded_evidence:
            raise SemanticDecompositionError(f"BOUNDED_EVIDENCE_MISSING:{claim_id}")
        resolved = quote.get("resolved_locator") or contract.get("resolved_locator") or {}
        source_locator = str(
            resolved.get("locator")
            or quote.get("bound_page")
            or quote.get("provenance_page")
            or quote.get("provenance_pointer")
            or ""
        )
        if not source_locator:
            raise SemanticDecompositionError(f"SOURCE_LOCATOR_MISSING:{claim_id}")
        evidence_units = build_evidence_units(
            parent_claim_id=claim_id,
            bounded_evidence=bounded_evidence,
            source_locator=source_locator,
        )
        if not evidence_units:
            raise SemanticDecompositionError(f"EVIDENCE_UNITS_MISSING:{claim_id}")
        result.append(
            {
                "claim_id": claim_id,
                "claim_text": str(claim.get("statement") or ""),
                "evidence_units": evidence_units,
                "attribution": str(claim.get("attributed_to") or ""),
                "scope": str(claim.get("scope") or ""),
                "fact_time": str(claim.get("fact_time") or ""),
                "assigned_nature": str(claim.get("nature") or ""),
            }
        )
    return result


def _generation_issue(code: str, *, unit_index: int | None = None) -> dict[str, Any]:
    issue: dict[str, Any] = {"code": code}
    if unit_index is not None:
        issue["unit_index"] = unit_index
    return issue


def normalize_model_result(
    claim: Mapping[str, Any],
    model_result: Any,
    *,
    inherited_issues: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    """Bind model enum choices to immutable Evidence IDs and child IDs."""
    parent_claim_id = str(claim["claim_id"])
    evidence_units = copy.deepcopy(list(claim["evidence_units"]))
    evidence_order = {
        str(item["evidence_unit_id"]): int(item["order"]) for item in evidence_units
    }
    issues = [dict(item) for item in inherited_issues]
    if not isinstance(model_result, Mapping):
        issues.append(_generation_issue("MODEL_RESULT_NOT_AN_OBJECT"))
        model_result = {}
    if set(model_result) - MODEL_RESULT_FIELDS:
        issues.append(_generation_issue("UNSUPPORTED_PROPOSITION_CONTENT"))
    if model_result.get("parent_claim_id") != parent_claim_id:
        issues.append(_generation_issue("PARENT_CLAIM_ID_MISMATCH"))
    model_status = model_result.get("ir_status")
    if model_status not in {"VALID", "AMBIGUOUS"}:
        issues.append(_generation_issue("INVALID_MODEL_IR_STATUS"))
        model_status = "AMBIGUOUS"
    raw_units = model_result.get("units")
    if not isinstance(raw_units, list):
        issues.append(_generation_issue("MODEL_UNITS_NOT_AN_ARRAY"))
        raw_units = []

    prepared_units: list[dict[str, Any]] = []
    for index, raw_unit in enumerate(raw_units):
        if not isinstance(raw_unit, Mapping):
            issues.append(_generation_issue("MODEL_UNIT_NOT_AN_OBJECT", unit_index=index))
            continue
        if set(raw_unit) - MODEL_UNIT_FIELDS:
            issues.append(
                _generation_issue("UNSUPPORTED_PROPOSITION_CONTENT", unit_index=index)
            )
        support = raw_unit.get("support_evidence_unit_ids")
        if not isinstance(support, list):
            support = []
        raw_key = raw_unit.get("coherence_key")
        if not isinstance(raw_key, str) or not raw_key:
            issues.append(_generation_issue("INVALID_COHERENCE_KEY", unit_index=index))
            raw_key = f"__missing_{index}"
        prepared_units.append(
            {
                "predicate_family": raw_unit.get("predicate_family"),
                "modality": raw_unit.get("modality"),
                "nature": raw_unit.get("nature"),
                "support_evidence_unit_ids": list(support),
                "raw_coherence_key": raw_key,
                "coherence_type": raw_unit.get("coherence_type"),
                "time_scope": raw_unit.get("time_scope", "unspecified"),
            }
        )

    def sort_key(unit: Mapping[str, Any]) -> tuple[Any, ...]:
        support = list(unit["support_evidence_unit_ids"])
        orders = tuple(evidence_order.get(str(value), 10**9) for value in support)
        return (
            min(orders, default=10**9),
            orders,
            str(unit["predicate_family"]),
            str(unit["modality"]),
            str(unit["nature"]),
            str(unit["raw_coherence_key"]),
            str(unit["coherence_type"]),
        )

    prepared_units.sort(key=sort_key)
    key_map: dict[str, str] = {}
    units: list[dict[str, Any]] = []
    for ordinal, unit in enumerate(prepared_units, 1):
        raw_key = str(unit.pop("raw_coherence_key"))
        if raw_key not in key_map:
            key_map[raw_key] = f"k{len(key_map) + 1}"
        unit["coherence_key"] = key_map[raw_key]
        support = list(unit["support_evidence_unit_ids"])
        support.sort(key=lambda value: evidence_order.get(str(value), 10**9))
        unit["support_evidence_unit_ids"] = support
        unit_id = derived_proposition_id(parent_claim_id, support, ordinal)
        units.append(
            {
                "unit_id": unit_id,
                "predicate_family": unit["predicate_family"],
                "modality": unit["modality"],
                "nature": unit["nature"],
                "support_evidence_unit_ids": support,
                "coherence_key": unit["coherence_key"],
                "coherence_type": unit["coherence_type"],
                "time_scope": unit["time_scope"],
            }
        )

    ir_status = "AMBIGUOUS" if model_status == "AMBIGUOUS" or issues else "VALID"
    proposition_ir = {
        "schema_version": PROPOSITION_IR_VERSION,
        "parent_claim_id": parent_claim_id,
        "ir_status": ir_status,
        "units": units,
    }
    validation = validate_proposition_ir(
        proposition_ir,
        claim_statement=str(claim.get("claim_text") or ""),
        expected_parent_claim_id=parent_claim_id,
        evidence_units=evidence_units,
        generation_issues=issues,
    )
    return {
        "parent_claim_id": parent_claim_id,
        "evidence_units": evidence_units,
        "proposition_ir": proposition_ir,
        "validation": validation,
        "model_ir_status": model_status,
    }


@dataclass
class SemanticDecomposer:
    backend: SemanticBackend
    batch_size: int = 8
    max_split_depth: int = 4

    def __post_init__(self) -> None:
        if not 1 <= self.batch_size <= 10:
            raise ValueError("semantic batch_size must be between 1 and 10")

    def run(self, claims: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
        frozen_claims = [copy.deepcopy(dict(item)) for item in claims]
        input_ids = [str(item.get("claim_id") or "") for item in frozen_claims]
        if not all(input_ids) or len(input_ids) != len(set(input_ids)):
            raise SemanticDecompositionError("SEMANTIC_PARENT_IDS_MISSING_OR_DUPLICATE")
        evidence_identity_before = {
            str(item["claim_id"]): [
                str(unit["evidence_unit_id"]) for unit in item.get("evidence_units") or []
            ]
            for item in frozen_claims
        }
        result_by_id: dict[str, dict[str, Any]] = {}
        call_records: list[dict[str, Any]] = []
        unexpected_model_parent_ids: set[str] = set()
        length_retries = 0

        def record_call(batch: Sequence[Mapping[str, Any]], status: str) -> None:
            metadata = copy.deepcopy(dict(self.backend.last_call_metadata or {}))
            call_records.append(
                {
                    "call_index": len(call_records) + 1,
                    "batch_parent_claim_ids": [item["claim_id"] for item in batch],
                    "batch_claim_count": len(batch),
                    "status": status,
                    "metadata": metadata,
                }
            )

        def process_batch(batch: Sequence[Mapping[str, Any]], split_depth: int = 0) -> None:
            nonlocal length_retries
            try:
                response = self.backend.decompose_batch(batch)
            except LLMError as exc:
                record_call(batch, "FAILED")
                is_length = "failure_category=output_truncation" in str(exc)
                if is_length and len(batch) > 1 and split_depth < self.max_split_depth:
                    length_retries += 1
                    midpoint = len(batch) // 2
                    process_batch(batch[:midpoint], split_depth + 1)
                    process_batch(batch[midpoint:], split_depth + 1)
                    return
                raise SemanticDecompositionError(
                    f"SEMANTIC_BACKEND_FAILURE:{type(exc).__name__}:{exc}"
                ) from exc
            record_call(batch, "SUCCESS")
            raw_results = response.get("claims") if isinstance(response, Mapping) else None
            if not isinstance(raw_results, list):
                raw_results = []
                batch_issue = [_generation_issue("MODEL_BATCH_RESULTS_NOT_AN_ARRAY")]
            else:
                batch_issue = []
            rows_by_id: dict[str, list[Any]] = {}
            batch_ids = {item["claim_id"] for item in batch}
            for row in raw_results:
                raw_parent = row.get("parent_claim_id") if isinstance(row, Mapping) else None
                if raw_parent not in batch_ids:
                    if raw_parent:
                        unexpected_model_parent_ids.add(str(raw_parent))
                    continue
                rows_by_id.setdefault(str(raw_parent), []).append(row)
            for claim in batch:
                parent_claim_id = str(claim["claim_id"])
                rows = rows_by_id.get(parent_claim_id, [])
                inherited = list(batch_issue)
                if not rows:
                    inherited.append(_generation_issue("MISSING_MODEL_PARENT_RESULT"))
                    row: Any = {
                        "parent_claim_id": parent_claim_id,
                        "ir_status": "AMBIGUOUS",
                        "units": [],
                    }
                elif len(rows) > 1:
                    inherited.append(_generation_issue("DUPLICATE_MODEL_PARENT_RESULT"))
                    row = rows[0]
                else:
                    row = rows[0]
                result_by_id[parent_claim_id] = normalize_model_result(
                    claim, row, inherited_issues=inherited
                )

        for start in range(0, len(frozen_claims), self.batch_size):
            process_batch(frozen_claims[start : start + self.batch_size])

        outputs = [result_by_id[claim_id] for claim_id in input_ids]
        output_ids = [item["parent_claim_id"] for item in outputs]
        if output_ids != input_ids:
            raise SemanticDecompositionError("SEMANTIC_PARENT_CLAIM_ORDER_CHANGED")
        evidence_identity_after = {
            str(item["parent_claim_id"]): [
                str(unit["evidence_unit_id"]) for unit in item.get("evidence_units") or []
            ]
            for item in outputs
        }
        if evidence_identity_after != evidence_identity_before:
            raise SemanticDecompositionError("SEMANTIC_RETRY_CHANGED_EVIDENCE_IDENTITY")
        attempts = [
            attempt
            for record in call_records
            for attempt in (record.get("metadata") or {}).get("attempts") or []
        ]
        usage = {
            key: sum(int(attempt.get(key) or 0) for attempt in attempts)
            for key in ("prompt_tokens", "completion_tokens", "total_tokens")
        }
        validations = [item["validation"] for item in outputs]
        return {
            "document_type": "phase3e2se1_post_extraction_semantic_decomposition",
            "schema_version": "2.1",
            "proposition_ir_version": PROPOSITION_IR_VERSION,
            "architecture": "DECOUPLED_POST_EXTRACTION_PROPOSITION_PASS",
            "evidence_binding_architecture": "DETERMINISTIC_EVIDENCE_IDS",
            "invariants": {
                "MODEL_GENERATED_RAW_EVIDENCE_OFFSETS": False,
                "PARENT_EVIDENCE_IDENTITY_DETERMINISTIC": True,
                "PROPOSITION_SUPPORT_REFERENCES_EXISTING_EVIDENCE_IDS": all(
                    item.get("evidence_binding_failures") == 0 for item in validations
                ),
            },
            "backend": self.backend.backend_name,
            "batch_size": self.batch_size,
            "input_parent_claim_ids": input_ids,
            "output_parent_claim_ids": output_ids,
            "parent_claims_before": len(input_ids),
            "parent_claims_after": len(output_ids),
            "parent_claim_id_match": len(set(input_ids) & set(output_ids)),
            "new_parent_claims": len(set(output_ids) - set(input_ids)),
            "missing_parent_claims": len(set(input_ids) - set(output_ids)),
            "unexpected_model_parent_ids": sorted(unexpected_model_parent_ids),
            "primary_extraction_llm_calls": 0,
            "semantic_length_retry_changes_claims": False,
            "semantic_length_retry_changes_evidence_units": False,
            "semantic_llm_calls": len(attempts),
            "semantic_length_retries": length_retries,
            "usage": usage,
            "counts": {
                "valid_proposition_ir_claims": sum(
                    item["status"] == "VALID" for item in validations
                ),
                "ambiguous_or_invalid_ir_claims": sum(
                    item["status"] != "VALID" for item in validations
                ),
                "proposition_evidence_binding_failures": sum(
                    int(item.get("evidence_binding_failures") or 0)
                    for item in validations
                ),
                "unsupported_proposition_content": sum(
                    int(item.get("unsupported_content_failures") or 0)
                    for item in validations
                ),
            },
            "call_records": call_records,
            "results": outputs,
        }


def semantic_prompt_sha256() -> str:
    return hashlib.sha256(SEMANTIC_DECOMPOSITION_SYSTEM.encode("utf-8")).hexdigest()
