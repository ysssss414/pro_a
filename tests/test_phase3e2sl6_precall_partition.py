from __future__ import annotations

import copy
import inspect
import json
from pathlib import Path

import pytest

from pro_a.analyzer import (
    FROZEN_ACCEPTANCE_INITIAL_MAX_CHARS,
    Analyzer,
)
from pro_a.llm import LLMError

from stability_helpers import make_config


def _empty_payload() -> dict:
    return {
        "source_metadata": {
            "title": "Deterministic partition fixture",
            "author": "",
            "organization": "",
            "publication_time": "2026-09-07",
            "source_rank": "A",
            "source_origin_type": "primary",
            "summary": "Offline partition fixture",
        },
        "node_matches": [],
        "node_candidates": [],
        "claims": [],
        "relation_candidates": [],
        "source_references": [],
    }


class SequenceLLM:
    available = True

    def __init__(self, *responses, before_call=None):
        self.responses = list(responses)
        self.before_call = before_call
        self.calls = 0
        self._last_call_metadata: dict = {}

    @property
    def last_call_metadata(self):
        return copy.deepcopy(self._last_call_metadata)

    def json(self, system, user):
        if self.before_call:
            self.before_call()
        self.calls += 1
        response = self.responses.pop(0)
        self._last_call_metadata = {
            "attempts_used": 1,
            "attempts": [{"attempt_number": 1, "response_model": "fixture"}],
        }
        if isinstance(response, BaseException):
            raise response
        return copy.deepcopy(response)


def test_initial_plan_is_deterministic_and_has_no_model_response_input(tmp_path: Path):
    cfg, db = make_config(tmp_path)
    analyzer = Analyzer(cfg, db)
    text = "[[PARA:1]] Alpha\n[[PARA:2]] Beta"

    first = analyzer.plan_initial_extraction("fixture.txt", text, "deep", adaptive_retry_policy="forbid")
    second = analyzer.plan_initial_extraction("fixture.txt", text, "deep", adaptive_retry_policy="forbid")

    assert first.artifact == second.artifact
    assert first.plan_sha256 == second.plan_sha256
    assert "response" not in inspect.signature(analyzer.plan_initial_extraction).parameters
    assert first.artifact["planning_inputs"]["model_response_consumed"] is False


def test_initial_plan_has_exact_ordered_full_coverage(tmp_path: Path):
    cfg, db = make_config(tmp_path)
    cfg.llm.max_chunk_chars = 17
    analyzer = Analyzer(cfg, db)
    text = "alpha line\nbeta line\ngamma line\ndelta line"

    plan = analyzer.plan_initial_extraction("fixture.txt", text, "deep")

    assert "".join(piece.source_piece.source_text for piece in plan.pieces) == text
    assert [piece.source_start for piece in plan.pieces] == [
        0,
        *[piece.source_end for piece in plan.pieces[:-1]],
    ]
    assert plan.pieces[-1].source_end == len(text)
    assert plan.artifact["coverage"] == {
        "source_chars": len(text),
        "planned_chars": len(text),
        "ordered_exact_reconstruction": True,
        "omitted_chars": 0,
        "duplicated_chars": 0,
    }


def test_locator_units_are_preserved_when_they_fit(tmp_path: Path):
    cfg, db = make_config(tmp_path)
    cfg.llm.max_chunk_chars = 28
    analyzer = Analyzer(cfg, db)
    text = "[[PARA:1]] Alpha text\n[[PARA:2]] Beta text"

    plan = analyzer.plan_initial_extraction("fixture.txt", text, "deep")

    assert [piece.locators for piece in plan.pieces] == [("PARA:1",), ("PARA:2",)]
    assert all(piece.source_piece.source_text.startswith("[[PARA:") for piece in plan.pieces)


def test_oversized_locator_unit_is_split_without_loss_or_duplication(tmp_path: Path):
    cfg, db = make_config(tmp_path)
    cfg.llm.max_chunk_chars = 40
    analyzer = Analyzer(cfg, db)
    text = "[[PARA:1]] " + ("abcdefghij" * 15)

    plan = analyzer.plan_initial_extraction("fixture.txt", text, "deep")

    assert len(plan.pieces) > 1
    assert max(len(piece.source_piece.source_text) for piece in plan.pieces) <= 40
    assert "".join(piece.source_piece.source_text for piece in plan.pieces) == text
    assert all(piece.locators == ("PARA:1",) for piece in plan.pieces)


def test_allow_policy_preserves_configured_initial_partition_and_recovery_mode(tmp_path: Path):
    cfg, db = make_config(tmp_path)
    cfg.llm.max_chunk_chars = 22_000
    analyzer = Analyzer(cfg, db)
    text = "x" * 15_000

    plan = analyzer.plan_initial_extraction("fixture.txt", text, "deep", adaptive_retry_policy="allow")

    assert plan.effective_max_chars == 22_000
    assert len(plan.pieces) == 1
    assert plan.artifact["partition_policy"]["response_time_recovery"] == "ADAPTIVE_RECOVERY_ALLOWED"


def test_forbid_policy_uses_safe_preplanned_initial_partition(tmp_path: Path):
    cfg, db = make_config(tmp_path)
    cfg.llm.max_chunk_chars = 22_000
    analyzer = Analyzer(cfg, db)
    text = "x" * 21_719

    plan = analyzer.plan_initial_extraction("fixture.txt", text, "deep", adaptive_retry_policy="forbid")

    assert plan.effective_max_chars == FROZEN_ACCEPTANCE_INITIAL_MAX_CHARS == 10_000
    assert len(plan.pieces) == 3
    assert max(len(piece.source_piece.source_text) for piece in plan.pieces) <= 10_000
    assert plan.artifact["partition_policy"]["response_time_recovery"] == "FORBIDDEN"


def test_forbid_policy_never_splits_or_retries_after_truncation(tmp_path: Path):
    cfg, db = make_config(tmp_path)
    analyzer = Analyzer(cfg, db)
    truncation = LLMError(
        "LLM returned invalid JSON; failure_category=output_truncation; finish_reason=length"
    )
    analyzer.llm = SequenceLLM(truncation)

    with pytest.raises(LLMError, match="output_truncation"):
        analyzer.analyze_source(
            "fixture.txt", "x" * 21_719, "deep", adaptive_retry_policy="forbid"
        )

    assert analyzer.llm.calls == 1
    assert len(analyzer.last_piece_call_records) == 1
    assert analyzer.last_piece_call_records[0]["adaptive_retry_blocked"] is True
    assert analyzer.last_piece_call_records[0]["split_depth"] == 0


def test_node_catalog_is_scoped_against_each_exact_planned_piece(tmp_path: Path):
    cfg, db = make_config(tmp_path)
    alpha_id = db.add_node("Alpha", "Product")
    beta_id = db.add_node("Beta", "Technology")
    cfg.llm.max_chunk_chars = 25
    analyzer = Analyzer(cfg, db)
    text = "[[PARA:1]] Alpha only\n[[PARA:2]] Beta only"

    plan = analyzer.plan_initial_extraction("fixture.txt", text, "deep")

    assert [piece.scoped_node_ids for piece in plan.pieces] == [(alpha_id,), (beta_id,)]
    assert [item["scoped_node_ids"] for item in plan.artifact["pieces"]] == [
        [alpha_id],
        [beta_id],
    ]


def test_complete_plan_is_persisted_before_first_llm_call(tmp_path: Path):
    cfg, db = make_config(tmp_path)
    analyzer = Analyzer(cfg, db)
    plan_path = tmp_path / "initial_extraction_plan.json"

    def persist(plan_artifact: dict) -> None:
        plan_path.write_text(
            json.dumps(plan_artifact, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    analyzer.llm = SequenceLLM(
        _empty_payload(),
        before_call=lambda: (
            plan_path.is_file()
            and json.loads(plan_path.read_text(encoding="utf-8"))["piece_count"] == 1
        ) or pytest.fail("complete plan was not persisted before LLM call #1"),
    )

    analyzer.analyze_source(
        "fixture.txt",
        "[[PARA:1]] offline fixture",
        "deep",
        adaptive_retry_policy="forbid",
        initial_plan_sink=persist,
    )

    assert analyzer.llm.calls == 1
    assert json.loads(plan_path.read_text(encoding="utf-8")) == analyzer.last_initial_extraction_plan


def test_frozen_source_reconstructs_identical_plan_and_provenance_on_resume(tmp_path: Path):
    cfg, db = make_config(tmp_path)
    analyzer = Analyzer(cfg, db)
    source_text = "[[PAGE:1]]\nAlpha\n[[PAGE:2]]\n" + ("Beta\n" * 3_000)

    original = analyzer.plan_initial_extraction(
        "frozen.pdf", source_text, "deep", adaptive_retry_policy="forbid"
    )
    frozen_artifact = json.loads(json.dumps(original.artifact, ensure_ascii=False))
    reconstructed = Analyzer(cfg, db).plan_initial_extraction(
        "frozen.pdf", source_text, "deep", adaptive_retry_policy="forbid"
    )

    assert reconstructed.artifact == frozen_artifact
    assert reconstructed.plan_sha256 == original.plan_sha256
    assert [piece.source_piece.piece_id for piece in reconstructed.pieces] == [
        piece.source_piece.piece_id for piece in original.pieces
    ]
