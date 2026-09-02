"""Frozen, offline Phase 3C Pilot #3 semantic-admission replay."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
import unicodedata
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from .corpus_pilot import PilotError, production_snapshot
from .parsers import parse_source_with_diagnostics
from .prompts import SOURCE_ANALYSIS_SYSTEM
from .semantic_admission import (
    ADMISSIBLE,
    ANSWERER,
    BLOCKED,
    QUESTIONER,
    REVIEW_REQUIRED,
    UNKNOWN,
    evaluate_semantic_admission,
    guard_configuration_sha256,
    is_explicit_bound_affirmation,
    is_question_premise,
)
from .storage import sha256_file, write_json


RUN_ID = "PILOT_20260901_4ED57ED2"
CLAIMS_TOTAL = 56
SOURCE_SHA256 = "1daf977493798d0334dedcd685d8a10f7c39dd25d768a44fa8a99ddf761627be"
PROMPT_TEXT_SHA256 = "4bc28ae13b1b23f1645bec2b133bc264b50aa0b3f29fc61df67b45465129dfa5"
FROZEN_HASHES = {
    "extraction_bundle": "6becc7ef6863008c9502f26ee13541ad71466832673e15b501562933a6972d52",
    "evidence_v2": "80f30b7b803610071f7b8474e810dfb12bea7852e7eefe6c22f61a748bb31e80",
    "quote_fidelity": "c011e34f4bff26fab5e867f071351a406b74b4b7a074e82d6b60398e2783c461",
    "human_decisions": "327e85347281e1aa2075decde538ce7599b834572a5d2f72f502b515fc9aaa22",
    "prompt_file": "4ac7a3ed099797920e57702fd3860f0ed98153fa272f112f2618e5e3fb6edce5",
}
NEXT_GATES = {
    "A": "Pilot #3 Semantic Admission Guard Integration",
    "B": "Pilot #3 Attribution Guard Integration + Noisy-Source Boundary",
    "C": "Define Noisy-Source Boundary for Phase 3C",
    "D": "Pilot #3 Semantic Prompt Repair Iteration 2",
}


@dataclass(frozen=True)
class TranscriptTurn:
    index: int
    timestamp: str | None
    text: str
    role: str
    locators: tuple[str, ...]


_TURN_HEADER = re.compile(
    r"(?:^|\n)\s*发言人\s+(\d{1,2}:\d{2})\s*(?:\n|$)",
    re.MULTILINE,
)
_PAGE_MARKER = re.compile(r"\[\[(PAGE:[1-9]\d*)\]\]")


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PilotError(f"ITERATION2A_INVALID_JSON: {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise PilotError(f"ITERATION2A_JSON_OBJECT_REQUIRED: {path}")
    return value


def _compact_source_text(value: str) -> str:
    value = _PAGE_MARKER.sub("", value or "")
    normalized = unicodedata.normalize("NFKC", value).casefold()
    return "".join(char for char in normalized if char.isalnum())


def split_transcript_turns(full_text: str) -> list[TranscriptTurn]:
    matches = list(_TURN_HEADER.finditer(full_text))
    raw: list[tuple[str | None, str]] = []
    if matches and full_text[: matches[0].start()].strip():
        raw.append((None, full_text[: matches[0].start()]))
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(full_text)
        raw.append((match.group(1), full_text[match.end():end]))
    if not matches and full_text.strip():
        raw.append((None, full_text))

    initial_roles = [QUESTIONER if is_question_premise(text) else UNKNOWN for _, text in raw]
    roles = list(initial_roles)
    for index, role in enumerate(initial_roles):
        if role == UNKNOWN and index > 0 and initial_roles[index - 1] == QUESTIONER:
            roles[index] = ANSWERER
    return [
        TranscriptTurn(
            index=index,
            timestamp=timestamp,
            text=text.strip(),
            role=roles[index],
            locators=tuple(dict.fromkeys(_PAGE_MARKER.findall(text))),
        )
        for index, (timestamp, text) in enumerate(raw)
        if text.strip()
    ]


def _turns_containing_text(
    turns: list[TranscriptTurn],
    text: str,
    preferred_locator: str | None,
) -> list[TranscriptTurn]:
    needle = _compact_source_text(text)
    if not needle:
        return []
    matches = [turn for turn in turns if needle in _compact_source_text(turn.text)]
    if preferred_locator:
        preferred = [turn for turn in matches if preferred_locator in turn.locators]
        if preferred:
            return preferred
    return matches


def _provenance_candidates(
    decision: dict[str, Any],
    quote_item: dict[str, Any],
) -> list[str]:
    rows = [decision.get("immutable_evidence_excerpt") or ""]
    ordered = quote_item.get("resolved_locator") or {}
    rows.extend(span.get("text") or "" for span in ordered.get("spans") or [])
    nearest = decision.get("nearest_deterministic_source_region_reference") or {}
    rows.extend(
        value for value in (nearest.get("source_core_text"), nearest.get("exact_anchor"))
        if value
    )
    return list(dict.fromkeys(value for value in rows if value))


def derive_turn_provenance(
    *,
    decision: dict[str, Any],
    quote_item: dict[str, Any],
    turns: list[TranscriptTurn],
    preferred_locator: str | None,
) -> dict[str, Any]:
    excerpt = decision.get("immutable_evidence_excerpt") or ""
    matched: list[TranscriptTurn] = []
    for candidate in _provenance_candidates(decision, quote_item):
        matched = _turns_containing_text(turns, candidate, preferred_locator)
        if matched:
            break

    if is_question_premise(excerpt):
        roles = [QUESTIONER]
    elif matched:
        roles = list(dict.fromkeys(turn.role for turn in matched))
    else:
        roles = [UNKNOWN]

    adoption = "NOT_APPLICABLE"
    if roles == [QUESTIONER]:
        adoption = "NOT_FOUND"
        for turn in matched:
            tail = re.split(r"[?？]", turn.text, maxsplit=1)
            if len(tail) == 2 and is_explicit_bound_affirmation(tail[1]):
                adoption = "EXPLICIT"
                break
            if turn.index + 1 < len(turns) and is_explicit_bound_affirmation(
                turns[turn.index + 1].text
            ):
                adoption = "EXPLICIT"
                break
        if not matched:
            adoption = "UNRESOLVED"

    return {
        "supporting_turn_roles": roles,
        "answer_adoption_status": adoption,
        "matched_turns": [
            {
                "turn_index": turn.index,
                "timestamp": turn.timestamp,
                "derived_role": turn.role,
                "locators": list(turn.locators),
            }
            for turn in matched
        ],
        "speaker_identity_available": False,
        "derivation": "explicit_question_morphology_then_adjacent_turn_boundary",
    }


def permitted_support_region(
    *,
    decision: dict[str, Any],
    evidence_item: dict[str, Any],
    quote_item: dict[str, Any],
) -> dict[str, Any]:
    fidelity = quote_item.get("fidelity_status")
    authoritative = fidelity != "QUOTE_DRIFT"
    parts = [decision.get("immutable_evidence_excerpt") or ""]
    sources = ["immutable_evidence_excerpt"]

    resolved = quote_item.get("resolved_locator") or {}
    spans = [span.get("text") or "" for span in resolved.get("spans") or []]
    if spans:
        parts.extend(spans)
        sources.append("authoritative_ordered_spans")

    if decision.get("review_mode") == "BOUNDED_CONTEXT":
        contexts = [
            item.get("text") or ""
            for item in evidence_item.get("bounded_context_candidates") or []
        ]
        if contexts:
            parts.extend(contexts)
            sources.append("existing_bounded_context_candidates")

    text = "\n".join(dict.fromkeys(part for part in parts if part))
    return {
        "text": text,
        "authoritative": authoritative,
        "sources": sources,
        "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "characters": len(text),
    }


def _registered_names(production_db_path: Path) -> list[str]:
    with sqlite3.connect(str(production_db_path)) as conn:
        canonical = [
            row[0]
            for row in conn.execute(
                """SELECT canonical_name FROM nodes
                   WHERE primary_type IN ('Company','Entity','Product','Technology','Standard')"""
            ).fetchall()
        ]
        aliases = [
            row[0]
            for row in conn.execute(
                """SELECT a.alias FROM node_aliases a
                   JOIN nodes n ON n.node_id=a.node_id
                   WHERE n.primary_type IN ('Company','Entity','Product','Technology','Standard')"""
            ).fetchall()
        ]
    return list(dict.fromkeys(value for value in (*canonical, *aliases) if value))


def _names_in_statement(statement: str, registry: Iterable[str]) -> list[str]:
    normalized = unicodedata.normalize("NFKC", statement).casefold()
    return sorted(
        {
            value
            for value in registry
            if len(value.strip()) >= 2
            and unicodedata.normalize("NFKC", value).casefold() in normalized
        },
        key=lambda value: (-len(value), value),
    )


def _status_counts(rows: Iterable[dict[str, Any]], field: str) -> dict[str, int]:
    counts = Counter(row[field]["status"] for row in rows)
    return {status: counts[status] for status in (ADMISSIBLE, REVIEW_REQUIRED, BLOCKED)}


def _guard_breakdown(rows: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
    return {
        name: _status_counts(rows, name)
        for name in (
            "question_premise_guard",
            "precision_token_guard",
            "number_time_guard",
            "subject_scope_guard",
        )
    }


def _disposition_counts(rows: Iterable[dict[str, Any]]) -> dict[str, int]:
    counts = Counter(row["overall_guard_disposition"] for row in rows)
    return {status: counts[status] for status in (ADMISSIBLE, REVIEW_REQUIRED, BLOCKED)}


def _select_next_gate(
    *,
    rows: list[dict[str, Any]],
    question_attribution_rows: list[dict[str, Any]],
    scope_rows: list[dict[str, Any]],
) -> tuple[str, str, dict[str, Any]]:
    attribution_acceptance = all(
        row["overall_guard_disposition"] != ADMISSIBLE
        for row in question_attribution_rows
    ) and len(question_attribution_rows) == 2
    question_supported_false_blocks = sum(
        row["human_semantic_outcome"] == "SUPPORTED"
        and row["question_premise_guard"]["status"] == BLOCKED
        for row in rows
    )
    scope_guard_comprehensive = bool(scope_rows) and all(
        row["subject_scope_guard"]["status"] != ADMISSIBLE for row in scope_rows
    )
    criteria = {
        "both_frozen_question_attribution_failures_non_admissible": attribution_acceptance,
        "question_guard_supported_false_blocks": question_supported_false_blocks,
        "subject_scope_guard_comprehensive_on_frozen_scope_failures": scope_guard_comprehensive,
    }
    if attribution_acceptance and question_supported_false_blocks == 0:
        case = "A" if scope_guard_comprehensive else "B"
    elif question_supported_false_blocks > 0:
        case = "C"
    else:
        case = "D"
    return case, NEXT_GATES[case], criteria


def _report_markdown(replay: dict[str, Any]) -> str:
    metrics = replay["metrics"]
    overall = metrics["guard_outcomes_overall"]
    unsupported = metrics["unsupported"]
    supported = metrics["supported"]
    contract = metrics["extraction_contract_failures"]
    source = metrics["source_quality_limits"]
    lines = [
        "# Pilot #3 frozen semantic-admission guard replay",
        "",
        "## Scope and freeze",
        "",
        f"- Frozen run: `{replay['pilot_run_id']}`",
        f"- Total frozen Claims: `{metrics['total_frozen_claims']}`",
        f"- Human SUPPORTED / UNSUPPORTED: `{metrics['human_supported']} / {metrics['human_unsupported']}`",
        "- This is a repair-design replay, not an independent validation sample.",
        "- Prompt changes / extraction reruns / LLM calls: `0 / 0 / 0`",
        f"- Guard configuration SHA256: `{replay['guard_freeze']['configuration_sha256']}`",
        f"- Guard implementation SHA256: `{replay['guard_freeze']['implementation_sha256']}`",
        "- Rules were frozen before replay; no post-replay threshold tuning was performed.",
        "",
        "## Overall outcomes",
        "",
        f"- ADMISSIBLE: `{overall[ADMISSIBLE]}`",
        f"- REVIEW_REQUIRED: `{overall[REVIEW_REQUIRED]}`",
        f"- BLOCKED: `{overall[BLOCKED]}`",
        "",
        "## Human UNSUPPORTED",
        "",
        f"- blocked: `{unsupported['blocked']}`",
        f"- review_required: `{unsupported['review_required']}`",
        f"- missed_admissible: `{unsupported['missed_admissible']}`",
        "",
        "## Human SUPPORTED",
        "",
        f"- admissible: `{supported['admissible']}`",
        f"- review_required: `{supported['review_required']}`",
        f"- false_blocked: `{supported['false_blocked']}`",
        "",
        "## Six extraction-contract failures",
        "",
        f"- caught_by_guard (BLOCKED): `{contract['caught_by_guard']}`",
        f"- review_required: `{contract['review_required']}`",
        f"- missed: `{contract['missed']}`",
        "",
        "| Claim | Human category | Disposition | Non-pass guards |",
        "|---|---|---|---|",
    ]
    for row in contract["rows"]:
        lines.append(
            f"| `{row['claim_id']}` | `{row['human_failure_category']}` | "
            f"`{row['overall_guard_disposition']}` | "
            f"{', '.join(f'`{value}`' for value in row['non_pass_guards']) or '-'} |"
        )
    lines.extend(
        [
            "",
            "## Five upstream Source-quality limits",
            "",
            f"- safe blocked/review: `{source['safe_blocked_or_review']}`",
            f"- unsafe admitted: `{source['unsafe_admitted']}`",
            "",
            "| Claim | Human category | Disposition |",
            "|---|---|---|",
        ]
    )
    for row in source["rows"]:
        lines.append(
            f"| `{row['claim_id']}` | `{row['human_failure_category']}` | "
            f"`{row['overall_guard_disposition']}` |"
        )
    lines.extend(["", "## Guard-type breakdown", ""])
    for population in ("unsupported_guard_breakdown", "supported_guard_breakdown", "contract_guard_breakdown"):
        lines.append(f"### {population}")
        lines.append("")
        lines.append("| Guard | ADMISSIBLE | REVIEW_REQUIRED | BLOCKED |")
        lines.append("|---|---:|---:|---:|")
        for guard, counts in metrics[population].items():
            lines.append(
                f"| `{guard}` | {counts[ADMISSIBLE]} | {counts[REVIEW_REQUIRED]} | {counts[BLOCKED]} |"
            )
        lines.append("")
    isolation = replay["production_isolation"]
    lines.extend(
        [
            "## Boundary and limitations",
            "",
            "- Question-premise acceptance requirement: "
            f"`{'PASS' if metrics['question_premise_acceptance']['passed'] else 'FAIL'}`.",
            "- Node/Alias registry was used only as a precision-token classifier, never as Source evidence.",
            "- Subject/scope automatic blocking remained limited to explicit exhaustive anchors; free-text scope was not guessed.",
            "- Safe fail-closed handling of corrupted transcript terms remains an upstream Source-quality boundary.",
            "- Frozen S3 semantic failure remains `11/56 = 19.64%` and `PILOT3_SEMANTIC_REPAIR_VERDICT = FAIL`.",
            "",
            "## Production isolation",
            "",
            f"- Production SHA: `{isolation['pre_sha256']}` -> `{isolation['post_sha256']}`",
            f"- Production changed: `{'YES' if isolation['production_changed'] else 'NO'}`",
            f"- Table counts changed: `{'YES' if isolation['table_counts_changed'] else 'NO'}`",
            f"- integrity / FK violations: `{isolation['integrity_check']}` / `{isolation['foreign_key_violations']}`",
            "- IMA / propagation / legacy ingestion: `NO / NO / NO`",
            "",
            "## Selected next gate",
            "",
            f"- Decision case: `{replay['next_gate_case']}`",
            f"- `PHASE3C_NEXT_GATE = {replay['PHASE3C_NEXT_GATE']}`",
            "- The selected gate was not executed.",
            "",
        ]
    )
    return "\n".join(lines)


def run_frozen_guard_replay(
    *,
    run_dir: Path,
    evaluation_path: Path,
    source_path: Path,
    production_db_path: Path,
    prompt_file_path: Path,
    output_dir: Path,
) -> dict[str, Any]:
    run_dir = Path(run_dir).resolve()
    source_path = Path(source_path).resolve()
    production_db_path = Path(production_db_path).resolve()
    prompt_file_path = Path(prompt_file_path).resolve()
    output_dir = Path(output_dir).resolve()
    paths = {
        "extraction_bundle": run_dir / "extraction_bundle.json",
        "evidence_v2": run_dir / "evidence_contract_v2.json",
        "quote_fidelity": run_dir / "quote_fidelity.json",
        "human_decisions": run_dir / "pilot3_controlled_reextraction_human_decisions.json",
        "prompt_file": prompt_file_path,
    }
    if any(not path.is_file() for path in (*paths.values(), source_path, production_db_path, Path(evaluation_path))):
        raise PilotError("ITERATION2A_REQUIRED_INPUT_MISSING")
    input_hashes_pre = {name: sha256_file(path) for name, path in paths.items()}
    if input_hashes_pre != FROZEN_HASHES:
        raise PilotError("ITERATION2A_FROZEN_INPUT_HASH_MISMATCH")
    if sha256_file(source_path) != SOURCE_SHA256:
        raise PilotError("ITERATION2A_SOURCE_HASH_MISMATCH")
    prompt_sha = hashlib.sha256(SOURCE_ANALYSIS_SYSTEM.encode("utf-8")).hexdigest()
    if prompt_sha != PROMPT_TEXT_SHA256:
        raise PilotError("ITERATION2A_PROMPT_TEXT_HASH_MISMATCH")

    bundle = _load_json(paths["extraction_bundle"])
    evidence = _load_json(paths["evidence_v2"])
    quote = _load_json(paths["quote_fidelity"])
    decisions = _load_json(paths["human_decisions"])
    evaluation = _load_json(Path(evaluation_path))
    if any(value.get("pilot_run_id") != RUN_ID for value in (bundle, evidence, quote, decisions, evaluation)):
        raise PilotError("ITERATION2A_RUN_BINDING_MISMATCH")
    if decisions.get("status") != "FROZEN" or decisions.get("claims_total") != CLAIMS_TOTAL:
        raise PilotError("ITERATION2A_HUMAN_DECISIONS_NOT_FROZEN")

    bundle_claims = bundle.get("claims") or []
    evidence_by_id = {item["claim_id"]: item for item in evidence.get("claims") or []}
    quote_by_id = {item["claim_id"]: item for item in quote.get("claims") or []}
    decisions_by_id = {item["claim_id"]: item for item in decisions.get("claims") or []}
    claim_ids = [item.get("claim_id") for item in bundle_claims]
    if (
        len(claim_ids) != CLAIMS_TOTAL
        or len(set(claim_ids)) != CLAIMS_TOTAL
        or set(evidence_by_id) != set(claim_ids)
        or set(quote_by_id) != set(claim_ids)
        or set(decisions_by_id) != set(claim_ids)
    ):
        raise PilotError("ITERATION2A_CLAIM_COVERAGE_MISMATCH")

    production_pre = production_snapshot(production_db_path)
    parsed = parse_source_with_diagnostics(source_path)
    if parsed.source_type != "pdf" or parsed.diagnostics.get("empty_extraction"):
        raise PilotError("ITERATION2A_SOURCE_PARSE_INVALID")
    turns = split_transcript_turns(parsed.text)
    registry = _registered_names(production_db_path)

    rows: list[dict[str, Any]] = []
    for claim in bundle_claims:
        claim_id = claim["claim_id"]
        decision = decisions_by_id[claim_id]
        evidence_item = evidence_by_id[claim_id]
        quote_item = quote_by_id[claim_id]
        locator = (quote_item.get("provenance_page") or "").strip() or None
        turn_provenance = derive_turn_provenance(
            decision=decision,
            quote_item=quote_item,
            turns=turns,
            preferred_locator=locator,
        )
        support = permitted_support_region(
            decision=decision,
            evidence_item=evidence_item,
            quote_item=quote_item,
        )
        classified_names = _names_in_statement(claim.get("statement") or "", registry)
        guards = evaluate_semantic_admission(
            statement=claim.get("statement") or "",
            attributed_to=claim.get("attributed_to") or "",
            permitted_support_text=support["text"],
            support_region_authoritative=support["authoritative"],
            supporting_turn_roles=turn_provenance["supporting_turn_roles"],
            adoption_status=turn_provenance["answer_adoption_status"],
            classified_named_entities=classified_names,
        )
        rows.append(
            {
                "claim_id": claim_id,
                "human_semantic_outcome": decision["semantic_support"],
                "human_failure_category": decision["semantic_failure_category"],
                "human_secondary_failure_categories": decision.get("secondary_failure_categories") or [],
                "human_secondary_diagnostics": decision.get("secondary_diagnostics") or [],
                "source_quality_class": "TRANSCRIPT_TEXT_SOURCE",
                "statement_attribution_role": guards["question_premise_guard"]["details"]["statement_attribution_role"],
                "supporting_turn_roles": turn_provenance["supporting_turn_roles"],
                "turn_provenance": turn_provenance,
                "permitted_support_region": {
                    key: value for key, value in support.items() if key != "text"
                },
                "classified_named_entities": classified_names,
                **guards,
            }
        )

    unsupported_rows = [row for row in rows if row["human_semantic_outcome"] == "UNSUPPORTED"]
    supported_rows = [row for row in rows if row["human_semantic_outcome"] == "SUPPORTED"]
    if len(unsupported_rows) != 11 or len(supported_rows) != 45:
        raise PilotError("ITERATION2A_FROZEN_HUMAN_COUNTS_CHANGED")

    diagnosis = evaluation.get("failure_origin_diagnosis") or {}
    contract_ids = set(diagnosis.get("extraction_contract_claim_ids") or [])
    source_ids = set(diagnosis.get("upstream_source_quality_claim_ids") or [])
    contract_rows = [row for row in rows if row["claim_id"] in contract_ids]
    source_rows = [row for row in rows if row["claim_id"] in source_ids]
    if len(contract_rows) != 6 or len(source_rows) != 5 or contract_ids & source_ids:
        raise PilotError("ITERATION2A_FAILURE_BOUNDARY_CHANGED")
    question_rows = [
        row for row in rows
        if row["human_failure_category"] == "ATTRIBUTION_ERROR"
        and "QUESTION_PREMISE_ADOPTION" in row["human_secondary_diagnostics"]
    ]
    scope_rows = [row for row in rows if row["human_failure_category"] == "SCOPE_ERROR"]
    next_case, next_gate, next_criteria = _select_next_gate(
        rows=rows,
        question_attribution_rows=question_rows,
        scope_rows=scope_rows,
    )

    overall = _disposition_counts(rows)
    unsupported_counts = _disposition_counts(unsupported_rows)
    supported_counts = _disposition_counts(supported_rows)
    contract_counts = _disposition_counts(contract_rows)
    source_counts = _disposition_counts(source_rows)

    def summary_rows(selected: list[dict[str, Any]], *, include_guards: bool) -> list[dict[str, Any]]:
        values = []
        for row in selected:
            value = {
                "claim_id": row["claim_id"],
                "human_failure_category": row["human_failure_category"],
                "overall_guard_disposition": row["overall_guard_disposition"],
            }
            if include_guards:
                value["non_pass_guards"] = [
                    name
                    for name in (
                        "question_premise_guard",
                        "precision_token_guard",
                        "number_time_guard",
                        "subject_scope_guard",
                    )
                    if row[name]["status"] != ADMISSIBLE
                ]
            values.append(value)
        return values

    production_post = production_snapshot(production_db_path)
    input_hashes_post = {name: sha256_file(path) for name, path in paths.items()}
    frozen_inputs_unchanged = input_hashes_pre == input_hashes_post == FROZEN_HASHES
    replay = {
        "document_type": "phase3c_pilot3_frozen_semantic_admission_guard_replay",
        "schema_version": "1",
        "status": "COMPLETE",
        "pilot_run_id": RUN_ID,
        "evaluation_only": True,
        "independent_validation_sample": False,
        "source_sha256": SOURCE_SHA256,
        "source_quality_class": "TRANSCRIPT_TEXT_SOURCE",
        "frozen_inputs": {
            name: {"path": str(paths[name]), "sha256": digest}
            for name, digest in input_hashes_pre.items()
        },
        "source": {"path": str(source_path), "sha256": sha256_file(source_path)},
        "prompt": {
            "text_sha256_pre": prompt_sha,
            "text_sha256_post": hashlib.sha256(SOURCE_ANALYSIS_SYSTEM.encode("utf-8")).hexdigest(),
            "modified": False,
        },
        "guard_freeze": {
            "configuration_sha256": guard_configuration_sha256(),
            "implementation_path": str(Path(__file__).with_name("semantic_admission.py").resolve()),
            "implementation_sha256": sha256_file(Path(__file__).with_name("semantic_admission.py")),
            "frozen_before_replay": True,
            "post_replay_threshold_tuning": False,
        },
        "role_derivation": {
            "turns_parsed": len(turns),
            "native_speaker_identity_available": False,
            "question_role_requires_explicit_question_morphology": True,
            "topic_continuation_used_as_adoption": False,
        },
        "claims": rows,
        "metrics": {
            "total_frozen_claims": len(rows),
            "human_supported": len(supported_rows),
            "human_unsupported": len(unsupported_rows),
            "guard_outcomes_overall": overall,
            "unsupported": {
                "blocked": unsupported_counts[BLOCKED],
                "review_required": unsupported_counts[REVIEW_REQUIRED],
                "missed_admissible": unsupported_counts[ADMISSIBLE],
            },
            "supported": {
                "admissible": supported_counts[ADMISSIBLE],
                "review_required": supported_counts[REVIEW_REQUIRED],
                "false_blocked": supported_counts[BLOCKED],
            },
            "extraction_contract_failures": {
                "total": len(contract_rows),
                "caught_by_guard": contract_counts[BLOCKED],
                "review_required": contract_counts[REVIEW_REQUIRED],
                "missed": contract_counts[ADMISSIBLE],
                "rows": summary_rows(contract_rows, include_guards=True),
            },
            "source_quality_limits": {
                "total": len(source_rows),
                "safe_blocked_or_review": source_counts[BLOCKED] + source_counts[REVIEW_REQUIRED],
                "unsafe_admitted": source_counts[ADMISSIBLE],
                "rows": summary_rows(source_rows, include_guards=False),
            },
            "unsupported_guard_breakdown": _guard_breakdown(unsupported_rows),
            "supported_guard_breakdown": _guard_breakdown(supported_rows),
            "contract_guard_breakdown": _guard_breakdown(contract_rows),
            "question_premise_acceptance": {
                "known_frozen_failures": len(question_rows),
                "non_admissible": sum(
                    row["overall_guard_disposition"] != ADMISSIBLE for row in question_rows
                ),
                "passed": len(question_rows) == 2 and all(
                    row["overall_guard_disposition"] != ADMISSIBLE for row in question_rows
                ),
                "rows": summary_rows(question_rows, include_guards=True),
            },
            "next_gate_selection_criteria": next_criteria,
        },
        "historical_semantic_result": {
            "true_semantic_failure": "11/56",
            "true_semantic_failure_percent": 19.64,
            "PILOT3_SEMANTIC_REPAIR_VERDICT": "FAIL",
            "retroactively_changed": False,
        },
        "production_isolation": {
            "pre_sha256": production_pre["sha256"],
            "post_sha256": production_post["sha256"],
            "production_changed": production_pre["sha256"] != production_post["sha256"],
            "table_counts_changed": production_pre["table_counts"] != production_post["table_counts"],
            "integrity_check": production_post["integrity_check"],
            "foreign_key_violations": len(production_post["foreign_key_violations"]),
            "IMA": False,
            "propagation": False,
            "legacy_ingestion": False,
        },
        "frozen_inputs_unchanged": frozen_inputs_unchanged,
        "llm_calls": 0,
        "extraction_reruns": 0,
        "claim_modifications": 0,
        "evidence_v2_modifications": 0,
        "production_writes": 0,
        "NOISY_SOURCE_PREPROCESSING_BACKLOG": True,
        "POST_REPAIR_INDEPENDENT_PILOT_REQUIRED": True,
        "next_gate_case": next_case,
        "PHASE3C_NEXT_GATE": next_gate,
        "selected_next_gate_executed": False,
    }
    if (
        not frozen_inputs_unchanged
        or replay["prompt"]["text_sha256_pre"] != replay["prompt"]["text_sha256_post"]
        or replay["production_isolation"]["production_changed"]
        or replay["production_isolation"]["table_counts_changed"]
        or replay["production_isolation"]["integrity_check"] != "ok"
        or replay["production_isolation"]["foreign_key_violations"] != 0
        or not replay["metrics"]["question_premise_acceptance"]["passed"]
    ):
        raise PilotError("ITERATION2A_ACCEPTANCE_CHECK_FAILED")

    output_dir.mkdir(parents=True, exist_ok=True)
    replay_path = output_dir / "pilot3_frozen_guard_replay.json"
    report_path = output_dir / "pilot3_frozen_guard_replay_report.md"
    write_json(replay_path, replay)
    report_path.write_text(_report_markdown(replay), encoding="utf-8", newline="\n")
    return replay


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--evaluation", required=True, type=Path)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--production-db", required=True, type=Path)
    parser.add_argument("--prompt-file", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    replay = run_frozen_guard_replay(
        run_dir=args.run_dir,
        evaluation_path=args.evaluation,
        source_path=args.source,
        production_db_path=args.production_db,
        prompt_file_path=args.prompt_file,
        output_dir=args.output_dir,
    )
    print(json.dumps(replay["metrics"], ensure_ascii=False, indent=2))
    print(f"PHASE3C_NEXT_GATE={replay['PHASE3C_NEXT_GATE']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
