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
from typing import Any, Iterable, Mapping

from .proposition_ir import (
    structural_atomicity_result,
    structural_nature_result,
    validate_proposition_ir,
)


ADMISSIBLE = "ADMISSIBLE"
REVIEW_REQUIRED = "REVIEW_REQUIRED"
BLOCKED = "BLOCKED"

QUESTIONER = "QUESTIONER"
ANSWERER = "ANSWERER"
UNKNOWN = "UNKNOWN"

GUARD_CONFIGURATION: dict[str, Any] = {
    "version": "phase3e2se-decoupled-v2",
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
    "atomicity": {
        "primary_abstraction": "versioned_proposition_signatures",
        "legacy_without_ir": "phase3e2sb-v1-explicit-compatibility",
        "compound_claims_are_blocked": False,
        "credible_independent_predicates": REVIEW_REQUIRED,
        "claim_text_rewritten": False,
    },
    "nature_consistency": {
        "evaluation_order": "after_atomicity_per_proposition",
        "bare_jiang_token_is_future": False,
        "metadata_mutated": False,
        "inconsistent_current_future_or_judgment_cues": REVIEW_REQUIRED,
        "inconsistency_alone_is_blocked": False,
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


_SUPPORT_REGION_SEPARATOR = "\u241e"


def join_permitted_support_regions(regions: Iterable[str]) -> str:
    """Join distinct support spans without creating cross-span token boundaries."""
    return _SUPPORT_REGION_SEPARATOR.join(str(region) for region in regions if region)


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


_NUMBER = r"\d+(?:\.\d+)?"
_QUANTITY_UNIT = (
    r"(?:"
    r"(?:万亿|亿|万)?人民币元|(?:万亿|亿|万)?美元|(?:万亿|亿|万)?元|"
    r"个百分点|%|"
    r"(?:[KMGT]i?[bB]|[KMGT]B|[KMGT]b)|"
    r"(?:[KMGT]?bps)|(?:[KMGT]?Hz)|(?:MT/s|GT/s|GTs)|"
    r"年|月|季度|天|周|倍|颗|根|家|台|个|项|层"
    r")"
)
_PERCENT_SERIES = re.compile(
    rf"(?<![A-Za-z0-9.])(?P<token>{_NUMBER}\s*%(?:\s*/\s*{_NUMBER}\s*%)+)(?![A-Za-z0-9.])"
)
_PERCENT_RANGE = re.compile(
    rf"(?<![A-Za-z0-9.])(?P<token>{_NUMBER}\s*%\s*(?:-|–|~|至)\s*{_NUMBER}\s*%)(?![A-Za-z0-9.])"
)
_QUANTITY = re.compile(
    rf"(?<![A-Za-z0-9.])"
    rf"(?P<token>(?P<value>{_NUMBER}(?:\s*/\s*{_NUMBER})+|{_NUMBER}\s*(?:-|–|~|至)\s*{_NUMBER}|{_NUMBER})"
    rf"\s*(?P<unit>{_QUANTITY_UNIT}))"
    rf"(?![A-Za-z0-9])",
    re.IGNORECASE,
)
_QUARTER_IDENTIFIER = re.compile(
    r"(?<![A-Za-z0-9])(?P<token>(?:19|20)\d{2}Q[1-4])(?![A-Za-z0-9])",
    re.IGNORECASE,
)
_TECHNICAL_IDENTIFIER = re.compile(
    r"(?<![A-Za-z0-9])"
    r"[A-Za-z][A-Za-z0-9]*\s*\d+(?:\.(?:\d+|x)|x)?"
    r"(?:\s+Type\s+\d+)?"
    r"(?![A-Za-z0-9])",
    re.IGNORECASE,
)
_COMPOUND_LATIN_IDENTIFIER = re.compile(
    r"(?<![A-Za-z0-9])[A-Za-z][A-Za-z0-9]*(?:[-_/+.][A-Za-z0-9]+)+(?![A-Za-z0-9])"
)
_BARE_LATIN_WORD = re.compile(r"(?<![A-Za-z0-9])[A-Za-z][A-Za-z0-9]*(?![A-Za-z0-9])")


def _overlaps(start: int, end: int, occupied: list[tuple[int, int]]) -> bool:
    return any(start < occupied_end and end > occupied_start for occupied_start, occupied_end in occupied)


def _quantity_matches(text: str) -> list[tuple[int, int, dict[str, str]]]:
    candidates: list[tuple[int, int, dict[str, str]]] = []
    for pattern, kind in ((_PERCENT_SERIES, "PERCENT_SERIES"), (_PERCENT_RANGE, "PERCENT_RANGE")):
        for match in pattern.finditer(text or ""):
            token = re.sub(r"\s+", "", match.group("token"))
            candidates.append((match.start(), match.end(), {
                "token": token,
                "value": token,
                "unit": "%",
                "kind": kind,
            }))
    for match in _QUANTITY.finditer(text or ""):
        token = re.sub(r"\s+", "", match.group("token"))
        value = re.sub(r"\s+", "", match.group("value"))
        unit = re.sub(r"\s+", "", match.group("unit"))
        if unit == "年" and re.fullmatch(r"(?:19|20)\d{2}", value):
            kind = "YEAR"
        elif unit == "年" and re.fullmatch(r"(?:19|20)\d{2}(?:[-–~至/](?:19|20)\d{2})+", value):
            kind = "YEAR_SERIES_OR_RANGE"
        else:
            kind = "QUANTITY"
        candidates.append((match.start(), match.end(), {
            "token": token,
            "value": value,
            "unit": unit,
            "kind": kind,
        }))
    occupied: list[tuple[int, int]] = []
    result: list[tuple[int, int, dict[str, str]]] = []
    for start, end, item in sorted(candidates, key=lambda row: (row[0], -(row[1] - row[0]))):
        if _overlaps(start, end, occupied):
            continue
        occupied.append((start, end))
        result.append((start, end, item))
    return sorted(result, key=lambda row: row[0])


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


def _technical_identifier_is_structural(token: str) -> bool:
    prefix = re.split(r"\d", token, maxsplit=1)[0]
    return any(char.isupper() for char in prefix if char.isalpha())


def _flexible_literal_pattern(value: str) -> str:
    normalized = _normalize(value).strip()
    parts: list[str] = []
    previous_kind = ""
    pending_space = False
    for char in normalized:
        if char.isspace():
            pending_space = True
            continue
        kind = "letter" if char.isascii() and char.isalpha() else (
            "digit" if char.isdigit() else "other"
        )
        if pending_space or {previous_kind, kind} == {"letter", "digit"}:
            parts.append(r"\s*")
        parts.append(re.escape(char))
        previous_kind = kind
        pending_space = False
    return "".join(parts)


def _literal_token_present(token: str, support_text: str) -> bool:
    needle = _flexible_literal_pattern(token)
    haystack = _normalize(support_text)
    if not needle:
        return False
    pattern = re.compile(
        rf"(?<![a-z0-9]){needle}(?![a-z0-9])",
        re.IGNORECASE,
    )
    return bool(pattern.search(haystack))


def precision_sensitive_tokens(
    statement: str,
    *,
    classified_named_entities: Iterable[str] = (),
) -> list[dict[str, str]]:
    candidates: list[tuple[int, str, str]] = []
    occupied = [(start, end) for start, end, _ in _quantity_matches(statement)]
    occupied.extend((match.start(), match.end()) for match in _QUARTER_IDENTIFIER.finditer(statement or ""))
    normalized_statement = _normalize(statement)
    for entity in classified_named_entities:
        normalized_entity = _normalize(entity)
        if not normalized_entity or normalized_entity not in normalized_statement:
            continue
        start = normalized_statement.index(normalized_entity)
        end = start + len(normalized_entity)
        candidates.append((start, entity, "NAMED_ENTITY"))
        occupied.append((start, end))
    for match in _TECHNICAL_IDENTIFIER.finditer(statement or ""):
        if _overlaps(match.start(), match.end(), occupied):
            continue
        token = match.group(0).strip()
        if not _technical_identifier_is_structural(token):
            continue
        candidates.append((match.start(), token, "TECHNICAL_IDENTIFIER"))
        occupied.append((match.start(), match.end()))
    for pattern, token_class in (
        (_COMPOUND_LATIN_IDENTIFIER, "COMPOUND_LATIN_IDENTIFIER"),
        (_BARE_LATIN_WORD, "LATIN_OR_ALPHANUMERIC"),
    ):
        for match in pattern.finditer(statement or ""):
            if _overlaps(match.start(), match.end(), occupied):
                continue
            token = match.group(0).strip()
            if _latin_token_is_precision_sensitive(token):
                candidates.append((match.start(), token, token_class))
                occupied.append((match.start(), match.end()))
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
    support_region_exhaustive: bool = True,
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
        "support_region_exhaustive": support_region_exhaustive,
        "registry_used_as_evidence": False,
    }
    if not missing:
        return _guard_result(
            "PRECISION_TOKEN_PROVENANCE_GUARD",
            ADMISSIBLE,
            ["ALL_IDENTIFIED_PRECISION_TOKENS_ANCHORED"],
            **details,
        )
    status = BLOCKED if support_region_authoritative and support_region_exhaustive else REVIEW_REQUIRED
    if not support_region_authoritative:
        reason = "PRECISION_SUPPORT_REGION_NOT_AUTHORITATIVE"
    elif not support_region_exhaustive:
        reason = "PRECISION_SUPPORT_SCOPE_NOT_EXHAUSTIVE"
    else:
        reason = "UNANCHORED_PRECISION_TOKEN"
    return _guard_result(
        "PRECISION_TOKEN_PROVENANCE_GUARD",
        status,
        [reason],
        **details,
    )


_ARABIC_NUMBER = re.compile(
    r"(?<![A-Za-z0-9.])\d+(?:\.\d+)?(?:\s*(?:-|–|~|至)\s*\d+(?:\.\d+)?)?%?(?![A-Za-z0-9.])"
)
_CHINESE_MATERIAL_NUMBER = re.compile(
    r"[零〇一二两三四五六七八九十百千万亿]+(?:多|余|左右)?"
    r"(?:%|年|月|季度|元|度|倍|成|张|家|层|颗|根|台|个|项)"
)
_RELATIVE_DATE = re.compile(r"(?:今年|明年|后年|去年|上月|本月|下月|本季度|下季度)")


def number_time_tokens(statement: str) -> list[dict[str, str]]:
    rows: list[tuple[int, dict[str, str]]] = []
    occupied: list[tuple[int, int]] = []
    for start, end, item in _quantity_matches(statement):
        rows.append((start, item))
        occupied.append((start, end))
    for match in _QUARTER_IDENTIFIER.finditer(statement or ""):
        if _overlaps(match.start(), match.end(), occupied):
            continue
        token = match.group("token")
        rows.append((match.start(), {"token": token, "value": token, "unit": "", "kind": "QUARTER"}))
        occupied.append((match.start(), match.end()))
    for pattern in (_TECHNICAL_IDENTIFIER, _COMPOUND_LATIN_IDENTIFIER):
        for match in pattern.finditer(statement or ""):
            if pattern is _TECHNICAL_IDENTIFIER and not _technical_identifier_is_structural(
                match.group(0)
            ):
                continue
            if not _overlaps(match.start(), match.end(), occupied):
                occupied.append((match.start(), match.end()))
    for match in _ARABIC_NUMBER.finditer(statement or ""):
        if _overlaps(match.start(), match.end(), occupied):
            continue
        token = re.sub(r"\s+", "", match.group(0))
        bare = token.rstrip("%")
        kind = "PERCENT" if token.endswith("%") else "NUMBER"
        if re.fullmatch(r"(?:19|20)\d{2}", bare):
            kind = "YEAR"
        rows.append((match.start(), {"token": token, "value": bare, "kind": kind}))
    for match in _CHINESE_MATERIAL_NUMBER.finditer(statement or ""):
        if _overlaps(match.start(), match.end(), occupied):
            continue
        token = match.group(0)
        numeral = re.sub(r"(?:多|余|左右)?(?:%|年|月|季度|元|度|倍|成|张|家|层|颗|根|台|个|项)$", "", token)
        if not any(char in numeral for char in "零〇一二两三四五六七八九十百"):
            continue
        rows.append((match.start(), {"token": token, "value": token, "unit": "", "kind": "CHINESE_NUMBER"}))
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


def _numeric_value_present(value: str, support_text: str) -> bool:
    return _literal_token_present(value, support_text)


def _number_anchor_state(token: dict[str, str], support_text: str) -> str:
    literal = (
        f"{token['value']} {token['unit']}"
        if token.get("unit") and token["kind"] in {
            "QUANTITY", "YEAR", "YEAR_SERIES_OR_RANGE"
        }
        else token["token"]
    )
    if _literal_token_present(literal, support_text):
        return "ANCHORED"
    if token["kind"] in {
        "PERCENT", "PERCENT_SERIES", "PERCENT_RANGE", "QUANTITY", "YEAR", "YEAR_SERIES_OR_RANGE"
    } and _numeric_value_present(token["value"], support_text):
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
    support_region_exhaustive: bool = True,
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
        "support_region_exhaustive": support_region_exhaustive,
        "numeric_scope_review_signal": scope_review,
        "new_date_resolution_rule_used": False,
    }
    if missing:
        status = BLOCKED if support_region_authoritative and support_region_exhaustive else REVIEW_REQUIRED
        if not support_region_authoritative:
            reason = "NUMBER_TIME_SUPPORT_REGION_NOT_AUTHORITATIVE"
        elif not support_region_exhaustive:
            reason = "NUMBER_TIME_SUPPORT_SCOPE_NOT_EXHAUSTIVE"
        else:
            reason = "UNANCHORED_NUMBER_OR_TIME"
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


_LIFECYCLE_PATTERNS = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"首发",
        r"推出",
        r"量产",
        r"规模(?:化)?(?:出货|销售)",
        r"送样(?:测试)?",
        r"(?:规模)?试用",
        r"入选",
        r"发布",
        r"采用",
        r"开展合作",
        r"(?:推进|正在).*研发",
        r"(?:推进|产品).*更替",
        r"成为出货主力",
        r"销售收入首次超过",
    )
)
_EVENT_CUE = re.compile(
    r"(?:首发|推出|量产|送样|试用|发布|入选|规模(?:化)?(?:出货|销售)|"
    r"出货量(?:也)?(?:显著|明显|持续)?(?:提升|增加|增长))"
)
_SPECIFICATION_CUE = re.compile(
    r"(?:最高)?支持|传输速率|数据传输速率|协议|捆绑端口|特性|功能|架构|兼容性|安全防护"
)
_CLAUSE_BOUNDARY = re.compile(r"[，,；;]|(?:并且|同时|同年|同期|该(?:芯片|产品|款产品))")
_CURRENT_STATE_CUE = re.compile(r"(?:当前|目前|已|正在|尚处于|规模约为|市场规模约为)")
# Frozen artifacts without proposition IR use this explicitly named legacy
# compatibility cue.  The v2 path never infers future modality from bare 将.
_LEGACY_FUTURE_OR_CONDITIONAL_CUE = re.compile(
    r"(?:预计|有望|未来|(?<!已)将|可能|假设|若|风险)"
)


def _matched_pattern_count(patterns: Iterable[re.Pattern[str]], text: str) -> int:
    return sum(bool(pattern.search(text)) for pattern in patterns)


def claim_atomicity_admission_guard(
    *,
    statement: str,
    proposition_ir_validation: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Advisory-only structural triage; this function never rewrites a Claim."""
    if (
        proposition_ir_validation is not None
        and proposition_ir_validation.get("status") != "LEGACY_NOT_PRESENT"
    ):
        result = structural_atomicity_result(proposition_ir_validation)
        return _guard_result(
            "CLAIM_ATOMICITY_ADMISSION_GUARD",
            str(result["status"]),
            result["reason_codes"],
            **result["details"],
        )

    text = _normalize(statement)
    reasons: list[str] = []

    independent_financial = (
        ("营收" in text and "归母净利润" in text)
        or sum(marker in text for marker in ("管理费用率", "销售费用率", "研发费用率")) >= 2
        or (
            any(marker in text for marker in ("出货量", "出货占比"))
            and any(marker in text for marker in ("平均销售价格", "毛利率"))
        )
        or (
            any(marker in text for marker in ("销售收入", "营收"))
            and "市场份额" in text
        )
        or ("出货量" in text and "渗透率" in text)
        or (
            "归母净利润" in text
            and ("eps" in text or "p/e" in text or "pe" in text)
        )
    )
    paired_revenue_growth_series = (
        "营收" in text
        and "对应收入同比增速" in text
        and "归母净利润" not in text
        and "市场份额" not in text
    )
    if independent_financial and not paired_revenue_growth_series:
        reasons.append("MULTIPLE_INDEPENDENT_FINANCIAL_METRICS")

    if (
        _EVENT_CUE.search(text)
        and _SPECIFICATION_CUE.search(text)
        and _CLAUSE_BOUNDARY.search(text)
    ):
        reasons.append("EVENT_AND_SPECIFICATION_COMBINED")

    lifecycle_count = _matched_pattern_count(_LIFECYCLE_PATTERNS, text)
    if lifecycle_count >= 2 and _CLAUSE_BOUNDARY.search(text):
        reasons.append("MULTIPLE_PRODUCT_LIFECYCLE_EVENTS")

    if re.search(r"首发.*(?:主要)?用于", text):
        reasons.append("PRODUCT_EVENT_AND_USE_CASE_COMBINED")

    generation_mentions = set(
        re.findall(r"(?:第(?:[一二三四五六七八九十]|\d+)(?:子)?代|上一代)", text)
    )
    if len(generation_mentions) >= 3:
        reasons.append("MULTIPLE_GENERATION_EVENTS")

    if re.search(
        r"前(?:两|二|三|\d+)家.*(?:合计|占据).*(?:其中|公司|以).*(?:市场份额|排名|全球)",
        text,
    ):
        reasons.append("MARKET_STRUCTURE_AND_COMPANY_POSITION_COMBINED")

    if (
        _CURRENT_STATE_CUE.search(text)
        and _LEGACY_FUTURE_OR_CONDITIONAL_CUE.search(text)
        and _CLAUSE_BOUNDARY.search(text)
    ):
        reasons.append("ACTUAL_AND_FUTURE_CAPABILITY_COMBINED")
    if re.search(r"可用于.*未来.*(?:可以|可)", text):
        reasons.append("ACTUAL_AND_FUTURE_CAPABILITY_COMBINED")

    if re.search(r"曾.*任职.*(?:并|，).*(?:授予|院士)", text):
        reasons.append("MULTIPLE_INDEPENDENT_BIOGRAPHICAL_FACTS")
    if re.search(r"拥有.*年.*(?:曾|参与).*(?:创建|就任)", text):
        reasons.append("MULTIPLE_INDEPENDENT_BIOGRAPHICAL_FACTS")

    relationship_predicates = sum(
        marker in text
        for marker in ("底层技术均包括", "客户群体高度重合", "直接客户主要", "终端用户主要")
    )
    if relationship_predicates >= 2:
        reasons.append("MULTIPLE_INDEPENDENT_RELATIONSHIP_PREDICATES")

    configuration_predicates = sum(
        bool(re.search(pattern, text))
        for pattern in (r"需配备", r"同时需要", r"根据.*方案.*需要")
    )
    if configuration_predicates >= 2:
        reasons.append("MULTIPLE_CONFIGURATION_OBSERVATIONS")

    if re.search(r"(?:国际领先|占尽市场先机).*(?:规模出货|实现了.*出货)", text):
        reasons.append("JUDGMENT_AND_ACTUAL_EVENT_COMBINED")
    if re.search(r"(?:市占率|市场份额|排名|全球第).*(?:推进|正在).*研发", text):
        reasons.append("MARKET_POSITION_AND_R_AND_D_COMBINED")
    if re.search(r"无(?:实际控制人|实控人).*(?:前三大股东|股东分别)", text):
        reasons.append("CONTROL_STATUS_AND_SHAREHOLDER_LIST_COMBINED")
    if re.search(r"价格.*上调.*平均涨幅|报价.*上调.*平均涨幅", text):
        reasons.append("PRICE_EVENT_AND_MAGNITUDE_COMBINED")
    if re.search(r"全球第一.*(?:更替|迭代).*(?:出货主力|规模出货)", text):
        reasons.append("MARKET_POSITION_AND_GENERATION_EVENTS_COMBINED")

    details = {
        "independent_predicate_reason_count": len(list(dict.fromkeys(reasons))),
        "lifecycle_cue_count": lifecycle_count,
        "generation_mention_count": len(generation_mentions),
        "claim_text_rewritten": False,
        "automatic_split_authorized": False,
    }
    if reasons:
        return _guard_result(
            "CLAIM_ATOMICITY_ADMISSION_GUARD",
            REVIEW_REQUIRED,
            reasons,
            **details,
        )
    return _guard_result(
        "CLAIM_ATOMICITY_ADMISSION_GUARD",
        ADMISSIBLE,
        ["NO_CREDIBLE_MULTI_PROPOSITION_STRUCTURE_DETECTED"],
        **details,
    )


def claim_nature_consistency_guard(
    *,
    statement: str,
    nature: str,
    attributed_to: str = "",
    proposition_ir_validation: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Advisory-only consistency check; nature metadata is never mutated."""
    if (
        proposition_ir_validation is not None
        and proposition_ir_validation.get("status") != "LEGACY_NOT_PRESENT"
    ):
        result = structural_nature_result(
            proposition_ir_validation,
            claim_nature=nature,
            attributed_to=attributed_to,
        )
        return _guard_result(
            "CLAIM_NATURE_CONSISTENCY_GUARD",
            str(result["status"]),
            result["reason_codes"],
            **result["details"],
        )

    text = _normalize(statement)
    normalized_nature = _compact(nature)
    reasons: list[str] = []
    current_cues = bool(_CURRENT_STATE_CUE.search(text))
    future_cues = bool(_LEGACY_FUTURE_OR_CONDITIONAL_CUE.search(text))
    subjective_cues = bool(re.search(r"(?:国际领先|行业领先|占尽市场先机|我们认为|看好)", text))
    explicit_actual_clause = bool(
        re.search(
            r"(?:19|20)\d{2}年[^。；;]*(?:尚处于|已经|已开始|当前|目前|规模约为|市场规模约为)",
            text,
        )
    )

    if normalized_nature == "company_guidance" and current_cues and not future_cues:
        reasons.append("OBSERVED_CURRENT_STATE_CLASSIFIED_AS_COMPANY_GUIDANCE")
    if normalized_nature in {"fact", "data"} and future_cues:
        reasons.append("FORWARD_OR_CONDITIONAL_PROPOSITION_CLASSIFIED_AS_FACT_OR_DATA")
    if normalized_nature in {"fact", "data"} and subjective_cues:
        reasons.append("SUBJECTIVE_JUDGMENT_CLASSIFIED_AS_FACT_OR_DATA")
    if normalized_nature in {"broker_forecast", "company_guidance"} and explicit_actual_clause and future_cues:
        reasons.append("ACTUAL_AND_FORECAST_NATURE_MIXED")

    details = {
        "nature": nature,
        "attributed_to": attributed_to,
        "observed_current_cue": current_cues,
        "future_or_conditional_cue": future_cues,
        "subjective_judgment_cue": subjective_cues,
        "nature_mutated": False,
    }
    if reasons:
        return _guard_result(
            "CLAIM_NATURE_CONSISTENCY_GUARD",
            REVIEW_REQUIRED,
            reasons,
            **details,
        )
    return _guard_result(
        "CLAIM_NATURE_CONSISTENCY_GUARD",
        ADMISSIBLE,
        ["NO_NATURE_METADATA_CONFLICT_DETECTED"],
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
    support_region_exhaustive: bool = True,
    nature: str = "",
    fact_time: str = "",
    claim_status: str = "",
    supporting_turn_roles: Iterable[str] = (),
    adoption_status: str = "NOT_APPLICABLE",
    classified_named_entities: Iterable[str] = (),
    claim_subject_anchors: Iterable[str] = (),
    source_subject_anchors: Iterable[str] = (),
    source_subjects_exhaustive: bool = False,
    parent_claim_id: str = "",
    proposition_ir: Any = None,
    proposition_evidence_text: str = "",
    proposition_evidence_units: Iterable[Mapping[str, Any]] = (),
    proposition_ir_validation: Mapping[str, Any] | None = None,
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
        support_region_exhaustive=support_region_exhaustive,
        classified_named_entities=classified_named_entities,
    )
    number_time = number_and_time_provenance_guard(
        statement=statement,
        permitted_support_text=permitted_support_text,
        support_region_authoritative=support_region_authoritative,
        support_region_exhaustive=support_region_exhaustive,
    )
    subject_scope = subject_scope_anchor_guard(
        claim_subject_anchors=claim_subject_anchors,
        source_subject_anchors=source_subject_anchors,
        source_subjects_exhaustive=source_subjects_exhaustive,
        numeric_scope_review_required=number_time["details"][
            "numeric_scope_review_signal"
        ],
    )
    proposition_validation = (
        dict(proposition_ir_validation)
        if proposition_ir_validation is not None
        else validate_proposition_ir(
            proposition_ir,
            claim_statement=statement,
            claim_evidence=proposition_evidence_text or permitted_support_text,
            expected_parent_claim_id=parent_claim_id,
            evidence_units=list(proposition_evidence_units),
        )
    )
    atomicity = claim_atomicity_admission_guard(
        statement=statement,
        proposition_ir_validation=proposition_validation,
    )
    nature_consistency = claim_nature_consistency_guard(
        statement=statement,
        nature=nature,
        attributed_to=attributed_to,
        proposition_ir_validation=proposition_validation,
    )
    guards = [question, precision, number_time, subject_scope, atomicity, nature_consistency]
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
        "atomicity_guard": atomicity,
        "nature_consistency_guard": nature_consistency,
        "proposition_ir_validation": proposition_validation,
        "semantic_pipeline": {
            "version": "phase3e2se1-decoupled-v2.1",
            "architecture": "DECOUPLED_POST_EXTRACTION_PROPOSITION_PASS",
            "compatibility_path": proposition_validation.get("compatibility_path"),
            "atomicity_then_nature": True,
            "proposition_ir_inside_primary_extraction": False,
        },
        "overall_guard_disposition": disposition,
        "guard_reasons": list(dict.fromkeys(reasons)),
        "claim_metadata_observed": {
            "nature": nature,
            "fact_time": fact_time,
            "status": claim_status,
        },
    }
