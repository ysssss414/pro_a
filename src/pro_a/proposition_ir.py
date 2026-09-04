"""Deterministic Proposition IR validation and structural admission policy.

The semantic model selects pre-existing Evidence-unit IDs and bounded enums.
Evidence identity, proposition identity, validation, and admission remain pure
and deterministic.
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from collections import Counter, defaultdict
from typing import Any, Mapping, Sequence


PROPOSITION_IR_VERSION = "proposition-ir-v2.1"

PREDICATE_FAMILIES = (
    "identity",
    "status",
    "lifecycle",
    "capability",
    "measurement",
    "comparison",
    "relationship",
    "application",
    "configuration",
    "architecture_route",
    "calculation",
    "causal_judgment",
)
MODALITIES = ("actual", "future", "conditional", "capability", "proposal")
TIME_SCOPES = ("historical", "current", "future", "unspecified")
NATURES = (
    "fact",
    "data",
    "company_guidance",
    "expert_judgment",
    "broker_forecast",
    "market_rumor",
    "user_judgment",
    "ai_inference",
)
COHERENCE_TYPES = (
    "INDEPENDENT",
    "SPEC_VECTOR",
    "COMPARISON_VECTOR",
    "REPORTING_VECTOR",
    "SIMULATION_SCENARIO",
    "SEQUENTIAL_ROUTE",
    "CAUSAL_JUDGMENT",
    "SINGLE_EVENT_ATTRIBUTES",
    "OTHER_COHERENT",
)

_TOP_LEVEL_FIELDS = {"schema_version", "parent_claim_id", "ir_status", "units"}
_UNIT_FIELDS = {
    "unit_id",
    "predicate_family",
    "modality",
    "nature",
    "support_evidence_unit_ids",
    "coherence_key",
    "coherence_type",
    "time_scope",
}
_EVIDENCE_FIELDS = {"evidence_unit_id", "normalized_text", "source_locator", "order"}
_BINDING_CODES = {
    "EVIDENCE_UNITS_NOT_AN_ARRAY",
    "EVIDENCE_UNIT_NOT_AN_OBJECT",
    "EVIDENCE_UNIT_FIELD_INVALID",
    "EVIDENCE_UNIT_ORDER_INVALID",
    "EVIDENCE_UNIT_ORDER_NONCANONICAL",
    "EVIDENCE_UNIT_ID_MISMATCH",
    "DUPLICATE_EVIDENCE_UNIT_ID",
    "SUPPORT_EVIDENCE_IDS_NOT_AN_ARRAY",
    "SUPPORT_EVIDENCE_IDS_EMPTY",
    "SUPPORT_EVIDENCE_ID_INVALID",
    "SUPPORT_EVIDENCE_ID_NOT_FOUND",
    "SUPPORT_EVIDENCE_IDS_DUPLICATE",
    "SUPPORT_EVIDENCE_IDS_NONCANONICAL",
}
_ATTRIBUTED_NATURES = {
    "company_guidance",
    "expert_judgment",
    "broker_forecast",
    "market_rumor",
    "user_judgment",
    "ai_inference",
}


def _canonical_text(value: Any) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", str(value or ""))).strip()


def _stable_hash(prefix: str, payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return f"{prefix}_{hashlib.sha256(encoded).hexdigest()[:16].upper()}"


def derived_evidence_unit_id(
    parent_claim_id: str,
    normalized_text: str,
    source_locator: str,
    order: int,
) -> str:
    """Derive Evidence identity from the frozen parent, text, locator, and order."""
    return _stable_hash(
        "EVDU",
        {
            "parent_claim_id": str(parent_claim_id),
            "normalized_text": _canonical_text(normalized_text),
            "source_locator": _canonical_text(source_locator),
            "order": order,
        },
    )


def derived_proposition_id(
    parent_claim_id: str,
    support_evidence_unit_ids: Sequence[str],
    ordinal: int,
) -> str:
    """Derive proposition identity without model-authored text or coordinates."""
    return _stable_hash(
        "PRP",
        {
            "parent_claim_id": str(parent_claim_id),
            "support_evidence_unit_ids": list(support_evidence_unit_ids),
            "ordinal": ordinal,
        },
    )


def proposition_ir_schema() -> dict[str, Any]:
    return {
        "$id": f"https://pro-a.local/schema/{PROPOSITION_IR_VERSION}",
        "type": "object",
        "additionalProperties": False,
        "required": ["schema_version", "parent_claim_id", "ir_status", "units"],
        "properties": {
            "schema_version": {"const": PROPOSITION_IR_VERSION},
            "parent_claim_id": {"type": "string", "minLength": 1},
            "ir_status": {"enum": ["VALID", "AMBIGUOUS"]},
            "units": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": [
                        "unit_id",
                        "predicate_family",
                        "modality",
                        "nature",
                        "support_evidence_unit_ids",
                        "coherence_key",
                        "coherence_type",
                    ],
                    "properties": {
                        "unit_id": {"type": "string", "pattern": "^PRP_[0-9A-F]{16}$"},
                        "predicate_family": {"enum": list(PREDICATE_FAMILIES)},
                        "modality": {"enum": list(MODALITIES)},
                        "nature": {"enum": list(NATURES)},
                        "support_evidence_unit_ids": {
                            "type": "array",
                            "minItems": 1,
                            "uniqueItems": True,
                            "items": {
                                "type": "string",
                                "pattern": "^EVDU_[0-9A-F]{16}$",
                            },
                        },
                        "coherence_key": {"type": "string", "pattern": "^k[1-9][0-9]*$"},
                        "coherence_type": {"enum": list(COHERENCE_TYPES)},
                        "time_scope": {"enum": list(TIME_SCOPES)},
                    },
                },
            },
        },
        "$defs": {
            "evidence_unit": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "evidence_unit_id",
                    "normalized_text",
                    "source_locator",
                    "order",
                ],
                "properties": {
                    "evidence_unit_id": {
                        "type": "string",
                        "pattern": "^EVDU_[0-9A-F]{16}$",
                    },
                    "normalized_text": {"type": "string", "minLength": 1},
                    "source_locator": {"type": "string", "minLength": 1},
                    "order": {"type": "integer", "minimum": 0},
                },
            }
        },
    }


def _issue(code: str, *, unit_index: int | None = None, **details: Any) -> dict[str, Any]:
    item: dict[str, Any] = {"code": code}
    if unit_index is not None:
        item["unit_index"] = unit_index
    item.update(details)
    return item


def _normalized_evidence_units(
    parent_claim_id: str,
    evidence_units: Any,
    issues: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if not isinstance(evidence_units, Sequence) or isinstance(evidence_units, (str, bytes)):
        issues.append(_issue("EVIDENCE_UNITS_NOT_AN_ARRAY"))
        return []
    normalized: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, raw in enumerate(evidence_units):
        if not isinstance(raw, Mapping):
            issues.append(_issue("EVIDENCE_UNIT_NOT_AN_OBJECT", unit_index=index))
            continue
        if set(raw) - _EVIDENCE_FIELDS:
            issues.append(_issue("UNSUPPORTED_PROPOSITION_CONTENT", unit_index=index))
        text = _canonical_text(raw.get("normalized_text"))
        locator = _canonical_text(raw.get("source_locator"))
        order = raw.get("order")
        evidence_id = raw.get("evidence_unit_id")
        if not text or not locator or not isinstance(order, int) or order < 0:
            issues.append(_issue("EVIDENCE_UNIT_FIELD_INVALID", unit_index=index))
            continue
        expected = derived_evidence_unit_id(parent_claim_id, text, locator, order)
        if evidence_id != expected:
            issues.append(_issue("EVIDENCE_UNIT_ID_MISMATCH", unit_index=index))
        if evidence_id in seen:
            issues.append(_issue("DUPLICATE_EVIDENCE_UNIT_ID", unit_index=index))
        seen.add(str(evidence_id))
        if order != index:
            issues.append(_issue("EVIDENCE_UNIT_ORDER_NONCANONICAL", unit_index=index))
        normalized.append(
            {
                "evidence_unit_id": str(evidence_id or ""),
                "normalized_text": text,
                "source_locator": locator,
                "order": order,
            }
        )
    if [item["order"] for item in normalized] != list(range(len(normalized))):
        issues.append(_issue("EVIDENCE_UNIT_ORDER_INVALID"))
    return normalized


def validate_proposition_ir(
    proposition_ir: Any,
    *,
    claim_statement: str = "",
    claim_evidence: str = "",
    expected_parent_claim_id: str = "",
    evidence_units: Sequence[Mapping[str, Any]] | None = None,
    generation_issues: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    """Validate a compact IR against deterministic Evidence identities."""
    del claim_statement, claim_evidence  # compatibility-only parameters; never bind offsets.
    if proposition_ir is None:
        return {
            "status": "LEGACY_NOT_PRESENT",
            "valid": True,
            "compatibility_path": "LEGACY_PHASE3E2SB_V1",
            "issue_codes": [],
            "issues": [],
            "evidence_units": [],
            "normalized_units": [],
            "evidence_binding_failures": 0,
            "unsupported_content_failures": 0,
            "duplicate_unit_cases": 0,
            "ambiguous_coherence_cases": 0,
        }

    issues = [dict(item) for item in generation_issues]
    if not isinstance(proposition_ir, Mapping):
        issues.append(_issue("PROPOSITION_IR_NOT_AN_OBJECT"))
        proposition_ir = {}
    if set(proposition_ir) - _TOP_LEVEL_FIELDS:
        issues.append(_issue("UNSUPPORTED_PROPOSITION_CONTENT"))
    parent_claim_id = str(proposition_ir.get("parent_claim_id") or "")
    if proposition_ir.get("schema_version") != PROPOSITION_IR_VERSION:
        issues.append(_issue("SCHEMA_VERSION_MISMATCH"))
    if not parent_claim_id or (
        expected_parent_claim_id and parent_claim_id != expected_parent_claim_id
    ):
        issues.append(_issue("PARENT_CLAIM_ID_MISMATCH"))
    if proposition_ir.get("ir_status") not in {"VALID", "AMBIGUOUS"}:
        issues.append(_issue("INVALID_IR_STATUS"))

    normalized_evidence = _normalized_evidence_units(
        parent_claim_id, evidence_units, issues
    )
    evidence_by_id = {item["evidence_unit_id"]: item for item in normalized_evidence}
    evidence_order = {
        item["evidence_unit_id"]: item["order"] for item in normalized_evidence
    }
    raw_units = proposition_ir.get("units")
    if not isinstance(raw_units, list):
        issues.append(_issue("PROPOSITION_UNITS_NOT_AN_ARRAY"))
        raw_units = []
    if proposition_ir.get("ir_status") == "VALID" and not raw_units:
        issues.append(_issue("VALID_IR_HAS_NO_UNITS"))

    normalized_units: list[dict[str, Any]] = []
    signatures: set[tuple[Any, ...]] = set()
    seen_unit_ids: set[str] = set()
    key_types: dict[str, set[str]] = defaultdict(set)
    for index, raw in enumerate(raw_units):
        if not isinstance(raw, Mapping):
            issues.append(_issue("PROPOSITION_UNIT_NOT_AN_OBJECT", unit_index=index))
            continue
        if set(raw) - _UNIT_FIELDS:
            issues.append(_issue("UNSUPPORTED_PROPOSITION_CONTENT", unit_index=index))
        family = raw.get("predicate_family")
        modality = raw.get("modality")
        nature = raw.get("nature")
        time_scope = raw.get("time_scope", "unspecified")
        key = raw.get("coherence_key")
        coherence_type = raw.get("coherence_type")
        if family not in PREDICATE_FAMILIES:
            issues.append(_issue("PREDICATE_FAMILY_INVALID", unit_index=index))
        if modality not in MODALITIES:
            issues.append(_issue("MODALITY_INVALID", unit_index=index))
        if nature not in NATURES:
            issues.append(_issue("NATURE_INVALID", unit_index=index))
        if time_scope not in TIME_SCOPES:
            issues.append(_issue("TIME_SCOPE_INVALID", unit_index=index))
        if not isinstance(key, str) or not re.fullmatch(r"k[1-9][0-9]*", key):
            issues.append(_issue("INVALID_COHERENCE_KEY", unit_index=index))
        if coherence_type not in COHERENCE_TYPES:
            issues.append(_issue("COHERENCE_TYPE_INVALID", unit_index=index))

        support = raw.get("support_evidence_unit_ids")
        if not isinstance(support, list):
            issues.append(_issue("SUPPORT_EVIDENCE_IDS_NOT_AN_ARRAY", unit_index=index))
            support = []
        if not support:
            issues.append(_issue("SUPPORT_EVIDENCE_IDS_EMPTY", unit_index=index))
        if any(not isinstance(value, str) or not value for value in support):
            issues.append(_issue("SUPPORT_EVIDENCE_ID_INVALID", unit_index=index))
        if len(support) != len(set(support)):
            issues.append(_issue("SUPPORT_EVIDENCE_IDS_DUPLICATE", unit_index=index))
        missing = [value for value in support if value not in evidence_by_id]
        if missing:
            issues.append(
                _issue(
                    "SUPPORT_EVIDENCE_ID_NOT_FOUND",
                    unit_index=index,
                    missing_evidence_unit_ids=missing,
                )
            )
        known_support = [value for value in support if value in evidence_order]
        canonical_support = sorted(known_support, key=evidence_order.__getitem__)
        if known_support != canonical_support:
            issues.append(_issue("SUPPORT_EVIDENCE_IDS_NONCANONICAL", unit_index=index))

        unit_id = raw.get("unit_id")
        expected_unit_id = derived_proposition_id(parent_claim_id, support, index + 1)
        if unit_id != expected_unit_id:
            issues.append(_issue("PROPOSITION_UNIT_ID_MISMATCH", unit_index=index))
        if unit_id in seen_unit_ids:
            issues.append(_issue("DUPLICATE_PROPOSITION_UNIT_ID", unit_index=index))
        seen_unit_ids.add(str(unit_id))
        signature = (family, modality, nature, tuple(support), key, coherence_type, time_scope)
        if signature in signatures:
            issues.append(_issue("DUPLICATE_PROPOSITION_UNIT", unit_index=index))
        signatures.add(signature)
        if isinstance(key, str) and isinstance(coherence_type, str):
            key_types[key].add(coherence_type)
        normalized_units.append(
            {
                "unit_id": str(unit_id or ""),
                "predicate_family": family,
                "modality": modality,
                "nature": nature,
                "support_evidence_unit_ids": list(support),
                "coherence_key": key,
                "coherence_type": coherence_type,
                "time_scope": time_scope,
            }
        )

    expected_keys = [f"k{index}" for index in range(1, len(key_types) + 1)]
    observed_keys = list(dict.fromkeys(unit.get("coherence_key") for unit in normalized_units))
    if observed_keys and observed_keys != expected_keys:
        issues.append(_issue("COHERENCE_KEYS_NONCANONICAL"))
    ambiguous_coherence = 0
    for key, types in key_types.items():
        group_size = sum(unit.get("coherence_key") == key for unit in normalized_units)
        if len(types) != 1 or ("INDEPENDENT" in types and group_size != 1):
            ambiguous_coherence += 1
            issues.append(_issue("AMBIGUOUS_COHERENCE_GROUP", coherence_key=key))

    codes = [str(item.get("code") or "UNKNOWN") for item in issues]
    unsupported = codes.count("UNSUPPORTED_PROPOSITION_CONTENT")
    binding = sum(code in _BINDING_CODES for code in codes)
    status = "VALID" if not issues and proposition_ir.get("ir_status") == "VALID" else "AMBIGUOUS"
    if any(code in {"PARENT_CLAIM_ID_MISMATCH", "SCHEMA_VERSION_MISMATCH"} for code in codes):
        status = "INVALID"
    return {
        "status": status,
        "valid": status == "VALID",
        "compatibility_path": "PROPOSITION_IR_V2_1",
        "issue_codes": list(dict.fromkeys(codes)),
        "issues": issues,
        "evidence_units": normalized_evidence,
        "normalized_units": normalized_units,
        "evidence_binding_failures": binding,
        "unsupported_content_failures": unsupported,
        "duplicate_unit_cases": sum(
            code in {"DUPLICATE_PROPOSITION_UNIT", "DUPLICATE_PROPOSITION_UNIT_ID"}
            for code in codes
        ),
        "ambiguous_coherence_cases": ambiguous_coherence,
    }


def _unit_support_text(
    unit: Mapping[str, Any], evidence_by_id: Mapping[str, Mapping[str, Any]]
) -> str:
    return " ".join(
        str((evidence_by_id.get(evidence_id) or {}).get("normalized_text") or "")
        for evidence_id in unit.get("support_evidence_unit_ids") or []
    ).strip()


def _mechanism_classes(
    units: Sequence[Mapping[str, Any]], evidence_by_id: Mapping[str, Mapping[str, Any]]
) -> list[str]:
    families = Counter(str(unit.get("predicate_family")) for unit in units)
    texts = [_unit_support_text(unit, evidence_by_id) for unit in units]
    result: list[str] = []
    if families["lifecycle"] >= 2 or (families["lifecycle"] and families["status"]):
        result.append("LIFECYCLE_STATUS_SEQUENCE")
    if families["capability"] and families["measurement"]:
        result.append("CAPABILITY_CHAIN_AND_SCALE_METRIC_BUNDLE")
    if families["status"] >= 2 and len(set(texts)) >= 2:
        result.append("INDEPENDENT_COUNTERPARTY_PROJECT_ORDER_STATES")
    if families["capability"] and families["application"]:
        result.append("MULTIPLE_PRODUCT_CAPABILITIES_OR_SPEC_PLUS_SUITABILITY")
    if families["configuration"] and families["architecture_route"]:
        result.append("TOPOLOGY_COUNT_AND_ROUTE_BUNDLE")
    return result


def _bounded_coherence_override(
    units: Sequence[Mapping[str, Any]],
    evidence_by_id: Mapping[str, Mapping[str, Any]],
) -> tuple[str, str] | None:
    """Recognize a small set of coherent forms when model keys are over-split."""
    families = [str(unit.get("predicate_family") or "") for unit in units]
    family_set = set(families)
    modalities = {str(unit.get("modality") or "") for unit in units}
    natures = {str(unit.get("nature") or "") for unit in units}
    coherence_types = {str(unit.get("coherence_type") or "") for unit in units}
    texts = [_unit_support_text(unit, evidence_by_id) for unit in units]
    joined = " ".join(texts)

    non_independent = coherence_types - {"INDEPENDENT"}
    if len(non_independent) == 1 and "INDEPENDENT" not in coherence_types:
        coherence_type = next(iter(non_independent))
        return coherence_type, "SAME_EXPLICIT_COHERENCE_TYPE_ACROSS_KEYS"
    if (
        family_set == {"measurement"}
        and len(units) == 2
        and {"actual", "future"} <= modalities
    ):
        return "COMPARISON_VECTOR", "ACTUAL_FUTURE_MEASUREMENT_PAIR_DEFERRED_TO_NATURE"
    if (
        family_set == {"capability"}
        and "SPEC_VECTOR" in coherence_types
        and len(non_independent) == 1
    ):
        return "SPEC_VECTOR", "SPEC_VECTOR_WITH_CONTINUATION_ATTRIBUTE"
    if (
        family_set == {"lifecycle", "configuration"}
        and len(units) == 2
        and any(
            classify_jiang_modality(text) == "OBJECT_FRONTING_DISPOSAL"
            for text in texts
        )
    ):
        return "SINGLE_EVENT_ATTRIBUTES", "EVENT_WITH_OBJECT_FRONTED_CONFIGURATION"
    if (
        family_set == {"configuration", "relationship"}
        and "SPEC_VECTOR" in coherence_types
        and any(re.search(r"均由.*负责供货", text) for text in texts)
    ):
        return "SINGLE_EVENT_ATTRIBUTES", "PRODUCT_VECTOR_WITH_SHARED_SUPPLY_ATTRIBUTE"
    if (
        family_set == {"lifecycle"}
        and len(units) == 2
        and "动工" in joined
        and "建设阶段" in joined
    ):
        return "SINGLE_EVENT_ATTRIBUTES", "SAME_CONSTRUCTION_EVENT_STATUS_ATTRIBUTES"
    if (
        natures == {"company_guidance"}
        and family_set == {"application", "lifecycle"}
        and "future" in modalities
    ):
        return "SINGLE_EVENT_ATTRIBUTES", "GUIDED_EVENT_AND_ITS_APPLICATION_ATTRIBUTE"
    if (
        len(natures) == 1
        and natures <= _ATTRIBUTED_NATURES
        and "CAUSAL_JUDGMENT" in coherence_types
    ):
        return "CAUSAL_JUDGMENT", "ATTRIBUTED_CAUSAL_JUDGMENT_CONTEXT"
    if (
        natures == {"expert_judgment"}
        and "要求" in joined
        and re.search(r"(?:需|需要).*?(?:验证|爬坡)", joined)
    ):
        return "CAUSAL_JUDGMENT", "REQUIREMENT_TO_VALIDATION_CAUSAL_JUDGMENT"
    return None


def structural_atomicity_result(validation: Mapping[str, Any]) -> dict[str, Any]:
    units = list(validation.get("normalized_units") or [])
    evidence = {
        str(item.get("evidence_unit_id")): item
        for item in validation.get("evidence_units") or []
    }
    groups: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for unit in units:
        groups[str(unit.get("coherence_key") or "")].append(unit)
    coherence_types = sorted(
        {str(unit.get("coherence_type") or "") for unit in units}
    )
    details = {
        "unit_count": len(units),
        "coherence_group_count": len(groups),
        "coherence_types": coherence_types,
        "mechanism_classes": _mechanism_classes(units, evidence),
        "decision_basis": "EXPLICIT_COHERENCE_TYPES",
        "claim_text_rewritten": False,
        "automatic_split_authorized": False,
    }
    if validation.get("status") != "VALID":
        return {
            "status": "REVIEW_REQUIRED",
            "reason_codes": ["INVALID_OR_AMBIGUOUS_PROPOSITION_IR"],
            "details": details,
        }
    if len(units) <= 1:
        return {
            "status": "ADMISSIBLE",
            "reason_codes": ["SINGLE_PROPOSITION_UNIT"],
            "details": details,
        }
    if len(groups) == 1 and "INDEPENDENT" not in coherence_types:
        return {
            "status": "ADMISSIBLE",
            "reason_codes": ["COHERENT_VECTOR_OR_SCENARIO"],
            "details": details,
        }
    override = _bounded_coherence_override(units, evidence)
    if override is not None:
        coherence_type, reason = override
        details["bounded_coherence_override"] = {
            "coherence_type": coherence_type,
            "reason": reason,
        }
        return {
            "status": "ADMISSIBLE",
            "reason_codes": ["COHERENT_VECTOR_OR_SCENARIO"],
            "details": details,
        }
    return {
        "status": "REVIEW_REQUIRED",
        "reason_codes": ["INDEPENDENT_REVIEWABLE_PROPOSITIONS"],
        "details": details,
    }


_FUTURE_PREFIX = re.compile(r"(?:预计|预期|未来|计划|目标|有望|可能|将于|届时).*将?")
_JIANG_FUTURE_VERB = re.compile(
    r"将(?:进一步|继续|持续|显著|明显)?(?:提高|提升|增加|增长|降低|减少|成为|带来|推动|导致|抬升|强化|改善|扩大|加快|促进)"
)
_JIANG_OBJECT = re.compile(
    r"将[^，,；;。]{0,40}(?:转换为|转化为|应用于|集成到|集成至|分割为|分配至|分配到|控制在)"
)


def classify_jiang_modality(statement: str) -> str:
    text = _canonical_text(statement)
    if re.search(r"(?:可|可以|能够)将[^，,；;。]{0,40}(?:控制|转换|降低|提升)", text):
        return "OBJECT_FRONTING_CAPABILITY"
    if re.search(r"(?:提出|建议|拟)将", text):
        return "PROPOSAL_COMPLEMENT"
    if _FUTURE_PREFIX.search(text) or _JIANG_FUTURE_VERB.search(text):
        return "FUTURE_AUXILIARY"
    if _JIANG_OBJECT.search(text):
        return "OBJECT_FRONTING_DISPOSAL"
    if "将" in text:
        return "AMBIGUOUS_JIANG"
    return "NO_JIANG"


def structural_nature_result(
    validation: Mapping[str, Any],
    *,
    claim_nature: str,
    attributed_to: str = "",
) -> dict[str, Any]:
    units = list(validation.get("normalized_units") or [])
    evidence_by_id = {
        str(item.get("evidence_unit_id")): item
        for item in validation.get("evidence_units") or []
    }
    normalized_claim_nature = _canonical_text(claim_nature).casefold()
    unit_results: list[dict[str, Any]] = []
    reasons: list[str] = []
    for unit in units:
        text = _unit_support_text(unit, evidence_by_id)
        unit_nature = str(unit.get("nature") or "")
        family = str(unit.get("predicate_family") or "")
        modality = str(unit.get("modality") or "")
        jiang = classify_jiang_modality(text)
        unit_reasons: list[str] = []
        attributed_match = (
            normalized_claim_nature in _ATTRIBUTED_NATURES
            and unit_nature == normalized_claim_nature
        )
        reported_proposal_fact = (
            normalized_claim_nature == "fact"
            and unit_nature == "fact"
            and family in {"architecture_route", "configuration", "status"}
            and jiang == "PROPOSAL_COMPLEMENT"
        )
        if not attributed_match and not reported_proposal_fact:
            if normalized_claim_nature in {"fact", "data"} and (
                modality in {"future", "conditional"} or jiang == "FUTURE_AUXILIARY"
            ):
                unit_reasons.append("FORWARD_OR_CONDITIONAL_PROPOSITION_CLASSIFIED_AS_FACT_OR_DATA")
            if normalized_claim_nature != unit_nature:
                unit_reasons.append("PROPOSITION_NATURE_INCONSISTENT_WITH_CLAIM")
            if family == "measurement" and unit_nature != "data":
                unit_reasons.append("MEASUREMENT_PROPOSITION_NOT_CLASSIFIED_AS_DATA")
            if family not in {"measurement", "comparison", "calculation"} and unit_nature == "data":
                unit_reasons.append("NON_MEASUREMENT_PROPOSITION_CLASSIFIED_AS_DATA")
        if (
            jiang == "AMBIGUOUS_JIANG"
            and modality == "future"
            and normalized_claim_nature in {"fact", "data"}
        ):
            unit_reasons.append("JIANG_OBJECT_FRONTING_MISCLASSIFIED_AS_FUTURE")
        reasons.extend(unit_reasons)
        unit_results.append(
            {
                "unit_id": unit.get("unit_id"),
                "predicate_family": family,
                "modality": modality,
                "proposition_nature": unit_nature,
                "support_evidence_unit_ids": unit.get("support_evidence_unit_ids") or [],
                "jiang_modality": jiang,
                "attributed_nature_exact_match": attributed_match,
                "reported_proposal_fact": reported_proposal_fact,
                "reason_codes": list(dict.fromkeys(unit_reasons)),
            }
        )
    details = {
        "claim_nature": claim_nature,
        "attributed_to": attributed_to,
        "unit_results": unit_results,
        "evaluation_order": "AFTER_ATOMICITY",
        "nature_mutated": False,
    }
    if validation.get("status") != "VALID":
        return {
            "status": "REVIEW_REQUIRED",
            "reason_codes": ["INVALID_OR_AMBIGUOUS_PROPOSITION_IR"],
            "details": details,
        }
    if reasons:
        return {
            "status": "REVIEW_REQUIRED",
            "reason_codes": list(dict.fromkeys(reasons)),
            "details": details,
        }
    return {
        "status": "ADMISSIBLE",
        "reason_codes": ["PROPOSITION_NATURES_STRUCTURALLY_CONSISTENT"],
        "details": details,
    }
