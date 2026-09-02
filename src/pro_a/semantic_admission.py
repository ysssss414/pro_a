"""Deterministic semantic admission guards for proposed Claims.

The guards in this module are pure: they do not call an LLM, mutate a Claim,
or write any canonical/Production state.  Callers must supply the permitted
Source-local support region and any structured provenance metadata.
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from typing import Any, Iterable


ADMISSIBLE = "ADMISSIBLE"
REVIEW_REQUIRED = "REVIEW_REQUIRED"
BLOCKED = "BLOCKED"

QUESTIONER = "QUESTIONER"
ANSWERER = "ANSWERER"
UNKNOWN = "UNKNOWN"

GUARD_CONFIGURATION: dict[str, Any] = {
    "version": "phase3c-iteration2a-v1",
    "disposition_precedence": [BLOCKED, REVIEW_REQUIRED, ADMISSIBLE],
    "question_premise": {
        "question_only_answerer_attribution_without_adoption": BLOCKED,
        "mixed_or_unresolved_role_provenance": REVIEW_REQUIRED,
        "topic_continuation_is_adoption": False,
    },
    "precision_token": {
        "literal_or_local_normalized_anchor_required": True,
        "registry_is_classifier_only": True,
        "missing_token_in_authoritative_region": BLOCKED,
        "missing_token_in_non_authoritative_region": REVIEW_REQUIRED,
    },
    "number_time": {
        "exact_value_anchor_required": True,
        "new_date_inference_rules": False,
        "missing_value_in_authoritative_region": BLOCKED,
        "unit_or_numeric_scope_uncertainty": REVIEW_REQUIRED,
    },
    "subject_scope": {
        "automatic_block_requires_exhaustive_disjoint_anchors": True,
        "unstructured_semantic_guessing": False,
    },
}


def guard_configuration_sha256() -> str:
    payload = json.dumps(
        GUARD_CONFIGURATION,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _normalize(value: str) -> str:
    return unicodedata.normalize("NFKC", value or "").casefold()


def _compact(value: str) -> str:
    return re.sub(r"\s+", "", _normalize(value))


def _guard_result(
    guard: str,
    status: str,
    reason_codes: Iterable[str],
    **details: Any,
) -> dict[str, Any]:
    return {
        "guard": guard,
        "status": status,
        "reason_codes": list(dict.fromkeys(reason_codes)),
        "details": details,
    }


def statement_attribution_role(attributed_to: str) -> str:
    normalized = _compact(attributed_to)
    if normalized in {"专家", "回答者", "answerer", "expert", "受访者"}:
        return ANSWERER
    if normalized in {"采访者", "提问者", "questioner", "interviewer"}:
        return QUESTIONER
    return UNKNOWN


_QUESTION_PATTERNS = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"[?？]",
        r"(?:是不是|是否|能否|可否|对吗|是吗|怎么理解|如何理解)",
        r"(?:您|你)(?:会)?觉得",
        r"(?:请问|请教|想问)",
    )
)


def is_question_premise(text: str) -> bool:
    """Return True only for explicit, locally visible question morphology."""
    normalized = _normalize(text)
    return any(pattern.search(normalized) for pattern in _QUESTION_PATTERNS)


_PURE_AFFIRMATION = re.compile(
    r"^(?:对{1,3}|是|是的|没错|正确|确实|可以)(?:[。.!！,，]*)$",
    re.IGNORECASE,
)


def is_explicit_bound_affirmation(text: str) -> bool:
    """Recognize only a whole-turn, proposition-free direct affirmation."""
    return bool(_PURE_AFFIRMATION.fullmatch(_compact(text)))


def question_premise_admission_guard(
    *,
    supporting_turn_roles: Iterable[str],
    attributed_role: str,
    adoption_status: str = "NOT_APPLICABLE",
) -> dict[str, Any]:
    roles = tuple(dict.fromkeys(supporting_turn_roles)) or (UNKNOWN,)
    invalid_roles = set(roles) - {QUESTIONER, ANSWERER, UNKNOWN}
    if invalid_roles:
        raise ValueError(f"invalid supporting turn roles: {sorted(invalid_roles)}")
    if attributed_role not in {QUESTIONER, ANSWERER, UNKNOWN}:
        raise ValueError(f"invalid attributed role: {attributed_role!r}")
    if adoption_status not in {
        "NOT_APPLICABLE", "EXPLICIT", "NOT_FOUND", "UNRESOLVED"
    }:
        raise ValueError(f"invalid adoption status: {adoption_status!r}")

    details = {
        "supporting_turn_roles": list(roles),
        "statement_attribution_role": attributed_role,
        "answer_adoption_status": adoption_status,
    }
    if attributed_role != ANSWERER or QUESTIONER not in roles:
        return _guard_result(
            "QUESTION_PREMISE_ADMISSION_GUARD",
            ADMISSIBLE,
            ["NO_QUESTION_TO_ANSWERER_ROLE_CONFLICT"],
            **details,
        )
    if ANSWERER in roles or adoption_status == "EXPLICIT":
        return _guard_result(
            "QUESTION_PREMISE_ADMISSION_GUARD",
            ADMISSIBLE,
            ["ANSWERER_ASSERTION_OR_EXPLICIT_ADOPTION_ANCHORED"],
            **details,
        )
    if UNKNOWN in roles or adoption_status == "UNRESOLVED":
        return _guard_result(
            "QUESTION_PREMISE_ADMISSION_GUARD",
            REVIEW_REQUIRED,
            ["QUESTION_ANSWER_ROLE_PROVENANCE_UNRESOLVED"],
            **details,
        )
    return _guard_result(
        "QUESTION_PREMISE_ADMISSION_GUARD",
        BLOCKED,
        ["BLOCKED_SOURCE_ROLE_CONFLICT"],
        **details,
    )


_LATIN_TOKEN = re.compile(
    r"(?<![A-Za-z0-9])"
    r"[A-Za-z][A-Za-z0-9]*(?:[-_/+.][A-Za-z0-9]+)*"
    r"(?:\s+[A-Z][A-Za-z0-9]*(?:[-_/+.][A-Za-z0-9]+)*)*"
    r"(?![A-Za-z0-9])"
)


def _latin_token_is_precision_sensitive(token: str) -> bool:
    letters = "".join(char for char in token if char.isalpha())
    if not letters:
        return False
    if any(char.isdigit() for char in token):
        return True
    if len(letters) >= 2 and letters.isupper():
        return True
    if sum(char.isupper() for char in letters) >= 2:
        return True
    words = token.split()
    return all(word[:1].isupper() and word[1:].islower() for word in words)


def _literal_token_present(token: str, support_text: str) -> bool:
    needle = _compact(token)
    haystack = _compact(support_text)
    if not needle:
        return False
    pattern = re.compile(
        rf"(?<![a-z0-9]){re.escape(needle)}(?![a-z0-9])",
        re.IGNORECASE,
    )
    return bool(pattern.search(haystack))


def precision_sensitive_tokens(
    statement: str,
    *,
    classified_named_entities: Iterable[str] = (),
) -> list[dict[str, str]]:
    candidates: list[tuple[int, str, str]] = []
    for match in _LATIN_TOKEN.finditer(statement or ""):
        token = match.group(0).strip()
        if _latin_token_is_precision_sensitive(token):
            candidates.append((match.start(), token, "LATIN_OR_ALPHANUMERIC"))
    normalized_statement = _normalize(statement)
    for entity in classified_named_entities:
        if not entity or _normalize(entity) not in normalized_statement:
            continue
        candidates.append((normalized_statement.index(_normalize(entity)), entity, "NAMED_ENTITY"))

    seen: set[str] = set()
    result: list[dict[str, str]] = []
    for _, token, token_class in sorted(candidates, key=lambda item: (item[0], -len(item[1]))):
        key = _compact(token)
        if key in seen:
            continue
        seen.add(key)
        result.append({"token": token, "token_class": token_class})
    return result


def precision_token_provenance_guard(
    *,
    statement: str,
    permitted_support_text: str,
    support_region_authoritative: bool,
    classified_named_entities: Iterable[str] = (),
) -> dict[str, Any]:
    tokens = precision_sensitive_tokens(
        statement,
        classified_named_entities=classified_named_entities,
    )
    missing = [
        item for item in tokens
        if not _literal_token_present(item["token"], permitted_support_text)
    ]
    anchored = [item for item in tokens if item not in missing]
    details = {
        "tokens": tokens,
        "anchored_tokens": anchored,
        "unanchored_tokens": missing,
        "support_region_authoritative": support_region_authoritative,
        "registry_used_as_evidence": False,
    }
    if not missing:
        return _guard_result(
            "PRECISION_TOKEN_PROVENANCE_GUARD",
            ADMISSIBLE,
            ["ALL_IDENTIFIED_PRECISION_TOKENS_ANCHORED"],
            **details,
        )
    status = BLOCKED if support_region_authoritative else REVIEW_REQUIRED
    reason = (
        "UNANCHORED_PRECISION_TOKEN"
        if support_region_authoritative
        else "PRECISION_SUPPORT_REGION_NOT_AUTHORITATIVE"
    )
    return _guard_result(
        "PRECISION_TOKEN_PROVENANCE_GUARD",
        status,
        [reason],
        **details,
    )


_ARABIC_NUMBER = re.compile(
    r"(?<![A-Za-z0-9])\d+(?:\.\d+)?(?:\s*(?:-|–|~|至)\s*\d+(?:\.\d+)?)?%?(?![A-Za-z0-9])"
)
_CHINESE_MATERIAL_NUMBER = re.compile(
    r"[零〇一二两三四五六七八九十百千万亿]+(?:多|余|左右)?"
    r"(?:%|年|月|季度|元|度|倍|成|张|家|层)"
)
_RELATIVE_DATE = re.compile(r"(?:今年|明年|后年|去年|上月|本月|下月|本季度|下季度)")


def number_time_tokens(statement: str) -> list[dict[str, str]]:
    rows: list[tuple[int, dict[str, str]]] = []
    for match in _ARABIC_NUMBER.finditer(statement or ""):
        token = re.sub(r"\s+", "", match.group(0))
        bare = token.rstrip("%")
        kind = "PERCENT" if token.endswith("%") else "NUMBER"
        if re.fullmatch(r"(?:19|20)\d{2}", bare):
            kind = "YEAR"
        rows.append((match.start(), {"token": token, "value": bare, "kind": kind}))
    for match in _CHINESE_MATERIAL_NUMBER.finditer(statement or ""):
        token = match.group(0)
        rows.append((match.start(), {"token": token, "value": token, "kind": "CHINESE_NUMBER"}))
    for match in _RELATIVE_DATE.finditer(statement or ""):
        token = match.group(0)
        rows.append((match.start(), {"token": token, "value": token, "kind": "RELATIVE_DATE"}))

    seen: set[tuple[str, str]] = set()
    result: list[dict[str, str]] = []
    for _, item in sorted(rows, key=lambda row: row[0]):
        key = (item["kind"], item["token"])
        if key not in seen:
            seen.add(key)
            result.append(item)
    return result


def _number_anchor_state(token: dict[str, str], support_text: str) -> str:
    if _literal_token_present(token["token"], support_text):
        return "ANCHORED"
    if token["kind"] == "PERCENT" and _literal_token_present(
        token["value"], support_text
    ):
        return "VALUE_ONLY"
    return "MISSING"


def numeric_scope_review_signal(statement: str, tokens: list[dict[str, str]]) -> bool:
    if not tokens:
        return False
    normalized = _normalize(statement)
    has_enumeration = "、" in normalized or "以及" in normalized
    has_collective = any(marker in normalized for marker in ("等", "合计", "整体", "共同", "均"))
    return has_enumeration and has_collective


def number_and_time_provenance_guard(
    *,
    statement: str,
    permitted_support_text: str,
    support_region_authoritative: bool,
) -> dict[str, Any]:
    tokens = number_time_tokens(statement)
    states = [
        {**token, "anchor_state": _number_anchor_state(token, permitted_support_text)}
        for token in tokens
    ]
    missing = [item for item in states if item["anchor_state"] == "MISSING"]
    value_only = [item for item in states if item["anchor_state"] == "VALUE_ONLY"]
    scope_review = numeric_scope_review_signal(statement, tokens)
    details = {
        "tokens": states,
        "support_region_authoritative": support_region_authoritative,
        "numeric_scope_review_signal": scope_review,
        "new_date_resolution_rule_used": False,
    }
    if missing:
        status = BLOCKED if support_region_authoritative else REVIEW_REQUIRED
        reason = (
            "UNANCHORED_NUMBER_OR_TIME"
            if support_region_authoritative
            else "NUMBER_TIME_SUPPORT_REGION_NOT_AUTHORITATIVE"
        )
        return _guard_result(
            "NUMBER_AND_TIME_PROVENANCE_GUARD",
            status,
            [reason],
            **details,
        )
    reasons: list[str] = []
    if value_only:
        reasons.append("NUMERIC_UNIT_REVIEW_REQUIRED")
    if scope_review:
        reasons.append("NUMERIC_SCOPE_REVIEW_REQUIRED")
    if reasons:
        return _guard_result(
            "NUMBER_AND_TIME_PROVENANCE_GUARD",
            REVIEW_REQUIRED,
            reasons,
            **details,
        )
    return _guard_result(
        "NUMBER_AND_TIME_PROVENANCE_GUARD",
        ADMISSIBLE,
        ["ALL_IDENTIFIED_NUMBERS_AND_TIMES_ANCHORED"],
        **details,
    )


def subject_scope_anchor_guard(
    *,
    claim_subject_anchors: Iterable[str] = (),
    source_subject_anchors: Iterable[str] = (),
    source_subjects_exhaustive: bool = False,
    numeric_scope_review_required: bool = False,
) -> dict[str, Any]:
    claim = {_compact(value) for value in claim_subject_anchors if _compact(value)}
    source = {_compact(value) for value in source_subject_anchors if _compact(value)}
    details = {
        "claim_subject_anchors": sorted(claim),
        "source_subject_anchors": sorted(source),
        "source_subjects_exhaustive": source_subjects_exhaustive,
        "automatic_semantic_parser_used": False,
    }
    if source_subjects_exhaustive and claim and source and claim.isdisjoint(source):
        return _guard_result(
            "SUBJECT_SCOPE_ANCHOR_GUARD",
            BLOCKED,
            ["EXPLICIT_EXHAUSTIVE_SUBJECT_ANCHOR_MISMATCH"],
            **details,
        )
    if numeric_scope_review_required:
        return _guard_result(
            "SUBJECT_SCOPE_ANCHOR_GUARD",
            REVIEW_REQUIRED,
            ["SUBJECT_SCOPE_REVIEW_REQUIRED"],
            **details,
        )
    return _guard_result(
        "SUBJECT_SCOPE_ANCHOR_GUARD",
        ADMISSIBLE,
        ["NO_HIGH_CONFIDENCE_SUBJECT_SCOPE_CONFLICT_DEMONSTRATED"],
        **details,
    )


def evaluate_semantic_admission(
    *,
    statement: str,
    attributed_to: str,
    permitted_support_text: str,
    support_region_authoritative: bool,
    supporting_turn_roles: Iterable[str] = (),
    adoption_status: str = "NOT_APPLICABLE",
    classified_named_entities: Iterable[str] = (),
    claim_subject_anchors: Iterable[str] = (),
    source_subject_anchors: Iterable[str] = (),
    source_subjects_exhaustive: bool = False,
) -> dict[str, Any]:
    question = question_premise_admission_guard(
        supporting_turn_roles=supporting_turn_roles,
        attributed_role=statement_attribution_role(attributed_to),
        adoption_status=adoption_status,
    )
    precision = precision_token_provenance_guard(
        statement=statement,
        permitted_support_text=permitted_support_text,
        support_region_authoritative=support_region_authoritative,
        classified_named_entities=classified_named_entities,
    )
    number_time = number_and_time_provenance_guard(
        statement=statement,
        permitted_support_text=permitted_support_text,
        support_region_authoritative=support_region_authoritative,
    )
    subject_scope = subject_scope_anchor_guard(
        claim_subject_anchors=claim_subject_anchors,
        source_subject_anchors=source_subject_anchors,
        source_subjects_exhaustive=source_subjects_exhaustive,
        numeric_scope_review_required=number_time["details"][
            "numeric_scope_review_signal"
        ],
    )
    guards = [question, precision, number_time, subject_scope]
    if any(item["status"] == BLOCKED for item in guards):
        disposition = BLOCKED
    elif any(item["status"] == REVIEW_REQUIRED for item in guards):
        disposition = REVIEW_REQUIRED
    else:
        disposition = ADMISSIBLE
    reasons = [
        reason
        for item in guards
        if item["status"] != ADMISSIBLE
        for reason in item["reason_codes"]
    ]
    return {
        "question_premise_guard": question,
        "precision_token_guard": precision,
        "number_time_guard": number_time,
        "subject_scope_guard": subject_scope,
        "overall_guard_disposition": disposition,
        "guard_reasons": list(dict.fromkeys(reasons)),
    }
