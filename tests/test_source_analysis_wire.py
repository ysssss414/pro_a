"""Offline contract, exact-span, native equivalence and volume qualification."""
import copy
import hashlib
import json
from dataclasses import FrozenInstanceError, replace
from types import SimpleNamespace

import pytest

from pro_a.analyzer import Analyzer, SourcePiece, resolve_evidence_locator
from pro_a.cloud_contract import DeterministicFakeProvider, operation_contract
from pro_a.operational_ingestion import deterministic_id
from pro_a.source_analysis_wire import (
    SOURCE_ANALYSIS_EVIDENCE_UNIT_VERSION, SOURCE_ANALYSIS_WIRE_EXPANDER_VERSION,
    SOURCE_ANALYSIS_WIRE_SCHEMA_VERSION, SourceAnalysisWireError, SourcePieceContext,
    build_source_evidence_catalog, expand_source_analysis_wire_v2, validate_source_analysis_wire_v2,
)
from stability_helpers import make_config


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    monkeypatch.setattr("requests.sessions.Session.request", lambda *a, **k: pytest.fail("Network forbidden"))
    monkeypatch.setattr("pro_a.llm.ChatLLM.json", lambda *a, **k: pytest.fail("Model call forbidden"))


def encoded(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def context(text, node_ids=(), *, source_sha=None, chunk_index=1):
    piece = SourcePiece(chunk_index, 1, "", 0, text, text)
    return SourcePieceContext(source_sha or hashlib.sha256(text.encode()).hexdigest(), piece, tuple(node_ids))


def normal_node(name="示例公司"):
    return {"canonical_name": name, "primary_type": "Entity", "aliases": [],
        "description": "独立合成研究对象。", "suggested_parent_node_ids": [], "reason": "材料明确出现。",
        "confidence": 0.9, "candidate_kind": "normal", "independent_research_value": True,
        "maintenance_rationale": "长期维护独立判断。", "is_discrete_event": False, "event_time": "",
        "evidence_excerpt": "", "long_term_research_value": False, "cross_source_or_node_value": False,
        "question": "", "importance": "", "what_would_change_my_mind": ""}


def canonical_claim(statement, unit, ordinal=1, **overrides):
    return {"claim_ref": f"C{ordinal}", "statement": statement, "nature": "fact",
        "related_node_ids": [], "related_candidate_names": [], "fact_time": "", "evidence_pointer": f"[[{unit.locator}]]" if unit.locator != "TEXT" else "TEXT",
        "evidence_excerpt": unit.exact_text, "attributed_to": "示例公司管理层", "scope": "示例公司产品",
        "assumption": "", "status": "current", "confidence": 0.9, "novelty_level": "N2", "structured": {}, **overrides}


def empty_canonical():
    return {"source_metadata": {"title": "合成材料", "author": "", "organization": "",
        "publication_time": "2026-09-15", "source_rank": "A", "source_origin_type": "primary", "summary": ""},
        "node_matches": [], "node_candidates": [], "claims": [], "relation_candidates": [], "source_references": []}


def compact_fixture(canonical, catalog, *, refs=True):
    """Test-only inverse for representable, full canonical fixtures, not live code.

    Ref-free mode is a serialization projection only, not a valid V2 response.
    """
    wire = copy.deepcopy(canonical)
    wire["wire_version"] = SOURCE_ANALYSIS_WIRE_SCHEMA_VERSION
    defaults = {"source_metadata": {"author": "", "organization": "", "summary": ""},
        "claims": {"related_node_ids": [], "related_candidate_names": [], "assumption": "", "status": "current", "structured": {}},
        "node_matches": {"reason": ""}, "relation_candidates": {"reason": ""}, "source_references": {"note": ""}}
    variants = {"Event": {"is_discrete_event", "event_time", "evidence_ref"},
        "Theme": {"long_term_research_value", "cross_source_or_node_value"},
        "ResearchQuestion": {"question", "importance", "what_would_change_my_mind"}}
    type_fields = set().union(*variants.values())
    def ref_for(excerpt):
        matches = [u for u in catalog.units if u.exact_text == excerpt]
        assert len(matches) == 1, "Fixture must select an unambiguous exact catalog span"
        return matches[0].evidence_ref
    for group, objects in list(wire.items()):
        if group == "wire_version":
            continue
        for i, obj in enumerate([objects] if group == "source_metadata" else objects):
            if group == "claims":
                assert obj.pop("claim_ref") == f"C{i+1}"
                if refs:
                    unit = next(u for u in catalog.units if u.evidence_ref == ref_for(obj["evidence_excerpt"]))
                    assert obj["evidence_pointer"] == (f"[[{unit.locator}]]" if unit.locator != "TEXT" else "TEXT")
                    obj["evidence_ref"] = ref_for(obj.pop("evidence_excerpt"))
                    obj.pop("evidence_pointer")
            if group == "node_matches" and refs:
                obj["evidence_ref"] = ref_for(obj.pop("evidence_excerpt"))
            if group == "node_candidates":
                assert obj.pop("candidate_kind") == ("research_question" if obj["primary_type"] == "ResearchQuestion" else "normal")
                variant = variants.get(obj["primary_type"], set())
                for key, default in {"aliases": [], "description": "", "suggested_parent_node_ids": [], "reason": "",
                    "is_discrete_event": False, "event_time": "", "evidence_excerpt": "", "long_term_research_value": False,
                    "cross_source_or_node_value": False, "question": "", "importance": "", "what_would_change_my_mind": ""}.items():
                    if key in obj and obj[key] == default and key not in variant:
                        del obj[key]
                if refs and obj.get("evidence_excerpt"):
                    obj["evidence_ref"] = ref_for(obj.pop("evidence_excerpt"))
                if refs:
                    preserved = {k: obj.pop(k) for k in sorted(type_fields-variant) if k in obj}
                    if preserved:
                        obj["preserved_fields"] = preserved
            for key, default in defaults.get(group, {}).items():
                if key in obj and obj[key] == default:
                    del obj[key]
        if group != "source_metadata" and not objects and group != "claims":
            del wire[group]
    return wire


def dense_fixture():
    lines = [f"Stage Seven Synthetic Company reported product {i:03d} capacity of {i*13} units in 2026." for i in range(1, 41)]
    ctx = context("[[PARA:1]]\n" + "\n".join(lines))
    catalog = build_source_evidence_catalog(ctx)
    raw = copy.deepcopy(DeterministicFakeProvider._source_analysis_output(SimpleNamespace(payload={"source_text": ctx.piece.source_text})))
    template = raw["claims"][0]
    raw["claims"] = [{**copy.deepcopy(template), "claim_ref": f"C{i}", "statement": unit.exact_text,
        "evidence_excerpt": unit.exact_text, "evidence_pointer": "[[PARA:1]]"} for i, unit in enumerate(catalog.units, 1)]
    return ctx, catalog, raw


def mixed_fixture(node_ids=("NODE_A", "NODE_B")):
    text = "[[PARA:1]]\n示例产品甲采用示例技术乙，当前产能为13台。\n[[PAGE:2]]\n示例公司于2026-09-15举办发布会。\n[[SHEET:样例:ROW:1]]\n示例公司管理层：若需求达到预期，示例公司预计Q4产能可能增长20%；该目标尚不确定。\n[[PARA:4]]\n合成专家：该目标尚不确定。"
    ctx = context(text, node_ids)
    catalog = build_source_evidence_catalog(ctx)
    first, event_unit, conditional, expert_unit = catalog.units
    raw = empty_canonical()
    raw["source_metadata"].update(author="合成作者", organization="示例公司", summary="合成摘要。")
    normal = normal_node()
    normal.update(aliases=["示例别名"], suggested_parent_node_ids=[node_ids[0]])
    event = normal_node("示例发布会")
    event.update(primary_type="Event", is_discrete_event=True, event_time="2026-09-15", evidence_excerpt=event_unit.exact_text)
    theme = normal_node("示例长期主题")
    theme.update(primary_type="Theme", long_term_research_value=True, cross_source_or_node_value=True)
    question = normal_node("示例增长能否持续")
    question.update(primary_type="ResearchQuestion", candidate_kind="research_question", question="增长能否持续？",
        importance="影响合成判断。", what_would_change_my_mind="需求下降。", independent_research_value=False)
    raw["node_candidates"] = [normal, event, theme, question]
    raw["claims"] = [canonical_claim("示例产品甲采用示例技术乙。", first, related_node_ids=list(node_ids)),
        canonical_claim("示例公司预计Q4产能可能增长20%。", conditional, 2, nature="company_guidance", fact_time="Q4",
            assumption="若需求达到预期", status="pending_verification", structured={"company": "示例公司", "scenario": {"uncertain": True, "values": [1, None]}}, related_candidate_names=["示例公司"]),
        canonical_claim("专家认为该目标尚不确定。", expert_unit, 3, nature="expert_judgment", attributed_to="合成专家", scope="该目标", confidence=0.6, novelty_level="N3"),
        canonical_claim("示例产品甲当前产能为13台。", first, 4, nature="data", fact_time="当前", scope="示例产品甲", attributed_to="")]
    raw["node_matches"] = [{"node_id": node_ids[0], "role": "primary", "confidence": 0.9, "reason": "明确名称。", "evidence_excerpt": first.exact_text}]
    raw["relation_candidates"] = [{"from_node_id": node_ids[0], "relation_type": "uses", "to_node_id": node_ids[1], "scope": "示例产品甲", "supporting_claim_refs": ["C1"], "confidence": 0.9, "reason": "C1直接支持采用关系。"}]
    raw["source_references"] = [{"title": "合成前期资料", "relation_type": "references", "note": "显式引用。"}]
    return ctx, catalog, raw


@pytest.mark.parametrize("factory", [dense_fixture, mixed_fixture])
def test_full_canonical_exact_order_values_and_deterministic_expansion(factory):
    ctx, catalog, raw = factory()
    wire = compact_fixture(raw, catalog)
    original = encoded(wire)
    validate_source_analysis_wire_v2(wire, catalog, ctx)
    first = expand_source_analysis_wire_v2(wire, catalog, ctx)
    second = expand_source_analysis_wire_v2(wire, catalog, ctx)
    assert first == raw
    assert encoded(first) == encoded(second) == encoded(raw)
    assert encoded(wire) == original
    first["claims"][0]["structured"]["mutation"] = True
    assert "mutation" not in second["claims"][0]["structured"]


def test_native_validation_merge_origins_claim_identity_and_record_equivalence(tmp_path):
    cfg, db = make_config(tmp_path)
    a = db.add_node("示例产品甲", "Product")
    b = db.add_node("示例技术乙", "Technology")
    ctx, catalog, raw = mixed_fixture((a, b))
    expanded = expand_source_analysis_wire_v2(compact_fixture(raw, catalog), catalog, ctx)
    analyzer = Analyzer(cfg, db)
    def native(response):
        analyzer.llm = SimpleNamespace(available=True, json=lambda *a: copy.deepcopy(response))
        return analyzer.analyze_source("synthetic.txt", ctx.piece.source_text, "deep", adaptive_retry_policy="forbid")
    left = native(raw)
    right = native(expanded)
    assert left == right
    assert all(claim["evidence_validated"] for claim in right.claims)
    assert all(node["quality_eligible"] for node in right.node_candidates)
    assert len(right.relation_candidates) == 1
    from pro_a.pipeline import build_claim_record
    for index, (old, new) in enumerate(zip(left.claims, right.claims)):
        def claim_id(claim):
            return deterministic_id("CLM", {"source_sha256": ctx.source_sha256, "claim_index": index,
                "claim": {k: v for k, v in claim.items() if not k.startswith("origin_")}})
        assert claim_id(old) == claim_id(new)
        assert old["origin_pieces"] == new["origin_pieces"]
        assert old["origin_piece_sha256"] == ctx.piece.source_sha256
        assert build_claim_record(claim_id(old), "SRC_SYNTHETIC", old, "2026-09-15", ctx.piece.source_text,
            ingestion_time="2026-09-15T00:00:00Z", created_at="2026-09-15T00:00:00Z") == build_claim_record(
            claim_id(new), "SRC_SYNTHETIC", new, "2026-09-15", ctx.piece.source_text,
            ingestion_time="2026-09-15T00:00:00Z", created_at="2026-09-15T00:00:00Z")


@pytest.mark.parametrize("text", [
    "[[PAGE:1]]重复原文。重复原文。\n[[PAGE:2]]重复原文。",
    "[[PARA:1]]主持人：这是问题？\n专家：若订单满足，产能可能提升；仍不确定。\n\n专家：第二段！",
    "[[SHEET:样例:ROW:1]]Alice: A may grow, if orders arrive; uncertainty remains.\n12:30 Bob: B remains flat!",
    "\n\n[[PARA:1]]\r\n  Dr. Li reports 1.5 units, not 2; this is uncertain.  \r\n\r\nNext sentence。\n",
    "[[PARA:1]]" + "长话语，含条件；" * 400,
    "[[PARA:1]]ＡＢＣ，123；保持标点！标点变体?",
    "[[PARA:1]]Speaker 1: conditional premise without punctuation\nSpeaker 2: independent answer without punctuation",
    "[[PARA:1]][12:30]专家：如果条件满足，可能增长 [12:31]主持人：这是问题",
])
def test_catalog_exact_lossless_represented_text_boundaries_and_duplicates(text):
    ctx = context(text)
    catalog = build_source_evidence_catalog(ctx)
    assert catalog == build_source_evidence_catalog(ctx)
    assert [u.ordinal for u in catalog.units] == list(range(1, len(catalog.units)+1))
    assert len({u.evidence_ref for u in catalog.units}) == len(catalog.units)
    covered = set()
    for unit in catalog.units:
        assert unit.exact_text == text[unit.source_start:unit.source_end]
        assert unit.exact_text_sha256 == hashlib.sha256(unit.exact_text.encode()).hexdigest()
        assert unit.piece_id == ctx.piece.piece_id and unit.piece_sha256 == ctx.piece.source_sha256
        assert unit.source_sha256 == ctx.source_sha256
        assert unit.source_start < unit.source_end <= len(text)
        assert not covered.intersection(range(unit.source_start, unit.source_end))
        covered.update(range(unit.source_start, unit.source_end))
    from pro_a.parsers import SOURCE_MARKER
    marker_positions = {i for m in SOURCE_MARKER.finditer(text) for i in range(m.start(), m.end())}
    assert all(i in covered or i in marker_positions or char.isspace() for i, char in enumerate(text))
    # Reassemble original Source including non-evidence marker/whitespace gaps.
    restored, offset = [], 0
    for unit in catalog.units:
        restored.extend((text[offset:unit.source_start], unit.exact_text))
        offset = unit.source_end
    restored.append(text[offset:])
    assert "".join(restored) == text
    with pytest.raises(FrozenInstanceError):
        catalog.units[0].exact_text = "modified"
    if "主持人" in text:
        assert not any("主持人" in u.exact_text and "专家" in u.exact_text for u in catalog.units)
    if "12:30" in text:
        assert not any("Alice" in u.exact_text and "Bob" in u.exact_text for u in catalog.units)
        assert not any("12:30" in u.exact_text and "12:31" in u.exact_text for u in catalog.units)
    if "Speaker 1" in text:
        assert not any("Speaker 1" in u.exact_text and "Speaker 2" in u.exact_text for u in catalog.units)
    if "Dr." in text:
        assert any("Dr. Li reports 1.5 units" in u.exact_text for u in catalog.units)
    if "长话语" in text:
        assert len(catalog.units) == 1


def test_ids_source_piece_locator_order_bound_and_claim_independent():
    ctx = context("[[PAGE:1]]重复。重复。\n[[PAGE:2]]重复。")
    catalog = build_source_evidence_catalog(ctx)
    assert len(catalog.units) == 3 and len({u.evidence_ref for u in catalog.units}) == 3
    assert resolve_evidence_locator(ctx.piece.source_text, "重复。")["status"] == "ambiguous"
    foreign_source = replace(ctx, source_sha256="a"*64)
    foreign_piece = replace(ctx, piece=replace(ctx.piece, chunk_index=2))
    assert not {u.evidence_ref for u in catalog.units}.intersection(u.evidence_ref for u in build_source_evidence_catalog(foreign_source).units)
    assert not {u.evidence_ref for u in catalog.units}.intersection(u.evidence_ref for u in build_source_evidence_catalog(foreign_piece).units)
    assert build_source_evidence_catalog(ctx) == catalog
    assert SOURCE_ANALYSIS_EVIDENCE_UNIT_VERSION == "source-analysis-evidence-unit-v1"
    assert SOURCE_ANALYSIS_WIRE_EXPANDER_VERSION == "source-analysis-wire-expander-v1"


def test_repeated_quote_ref_selects_exact_occurrence_and_locator():
    ctx = context("[[PAGE:1]]重复原文。重复原文。\n[[PAGE:2]]重复原文。")
    catalog = build_source_evidence_catalog(ctx)
    wire = {"wire_version": SOURCE_ANALYSIS_WIRE_SCHEMA_VERSION,
        "source_metadata": {"title": "合成重复引文", "publication_time": "", "source_rank": "A", "source_origin_type": "primary"},
        "claims": [{"statement": "重复原文。", "nature": "fact", "evidence_ref": unit.evidence_ref,
            "attributed_to": "", "fact_time": "", "scope": "", "confidence": 0.9, "novelty_level": "N2"} for unit in catalog.units]}
    expanded = expand_source_analysis_wire_v2(wire, catalog, ctx)
    assert [c["evidence_pointer"] for c in expanded["claims"]] == ["[[PAGE:1]]", "[[PAGE:1]]", "[[PAGE:2]]"]
    assert [c["claim_ref"] for c in expanded["claims"]] == ["C1", "C2", "C3"]
    assert all(c["evidence_excerpt"] == "重复原文。" for c in expanded["claims"])


@pytest.mark.parametrize("mutation", [
    lambda w: w.update(unrecognized=True),
    lambda w: w.update(wire_version="old"),
    lambda w: w["claims"][0].update(unrecognized=True),
    lambda w: w["claims"][0].pop("nature"),
    lambda w: w["claims"][0].pop("confidence"),
    lambda w: w["claims"][0].pop("attributed_to"),
    lambda w: w["claims"][0].pop("scope"),
    lambda w: w["claims"][0].pop("fact_time"),
    lambda w: w["claims"][0].update(evidence_ref="EV_FOREIGN"),
    lambda w: w["claims"][0].update(evidence_ref=["E1", "E2"]),
    lambda w: w["claims"][0].update(evidence_excerpt="generated quote"),
    lambda w: w["claims"][0].update(claim_ref="C1"),
    lambda w: w["claims"][1].update(claim_ref="C1"),
    lambda w: w["claims"][0].update(nature="invalid"),
    lambda w: w["claims"][0].update(status="invalid"),
    lambda w: w["claims"][0].update(novelty_level="N4"),
    lambda w: w["claims"][0].update(confidence=True),
    lambda w: w["claims"][0].update(confidence=float("nan")),
    lambda w: w["claims"][0].update(confidence=1.1),
    lambda w: w["claims"][0].update(related_node_ids=["NODE_FAKE"]),
    lambda w: w["claims"][0].update(related_candidate_names=["unknown"]),
    lambda w: w["node_candidates"][0].update(primary_type="invalid"),
    lambda w: w["node_candidates"][0].update(event_time="2026"),
    lambda w: w["node_candidates"][1].pop("event_time"),
    lambda w: w["node_candidates"][1].update(is_discrete_event="true"),
    lambda w: w["node_candidates"][2].update(long_term_research_value=1),
    lambda w: w["node_candidates"][3].pop("question"),
    lambda w: w["node_candidates"][0].update(preserved_fields={"canonical_name": "changed"}),
    lambda w: w["relation_candidates"][0].update(supporting_claim_refs=["C9"]),
    lambda w: w["relation_candidates"][0].update(supporting_claim_refs=["C1", "C1"]),
    lambda w: w["relation_candidates"][0].update(to_node_id="NODE_FAKE"),
    lambda w: w["relation_candidates"][0].update(relation_type="part_of"),
    lambda w: w["source_metadata"].update(source_rank="X"),
    lambda w: w["source_references"][0].update(relation_type="inferred"),
])
def test_strict_invalid_wire_rejected_without_repairs(mutation):
    ctx, catalog, raw = mixed_fixture()
    wire = compact_fixture(raw, catalog)
    mutation(wire)
    with pytest.raises(SourceAnalysisWireError):
        expand_source_analysis_wire_v2(wire, catalog, ctx)


@pytest.mark.parametrize("mutation", [
    lambda c: replace(c, piece_sha256="a"*64),
    lambda c: replace(c, source_sha256="a"*64),
    lambda c: replace(c, units=c.units+c.units[:1]),
    lambda c: replace(c, units=tuple(reversed(c.units))),
    lambda c: replace(c, units=(replace(c.units[0], exact_text="corrupt"), *c.units[1:])),
    lambda c: replace(c, units=(replace(c.units[0], exact_text_sha256="a"*64), *c.units[1:])),
    lambda c: replace(c, units=(replace(c.units[0], source_start=0), *c.units[1:])),
    lambda c: replace(c, units=(replace(c.units[0], locator="PAGE:9"), *c.units[1:])),
    lambda c: replace(c, units=(replace(c.units[0], ordinal=True), *c.units[1:])),
])
def test_corrupt_catalog_rejected(mutation):
    ctx, catalog, raw = mixed_fixture()
    with pytest.raises(SourceAnalysisWireError):
        expand_source_analysis_wire_v2(compact_fixture(raw, catalog), mutation(catalog), ctx)


def test_cross_source_and_piece_ref_rejected():
    ctx, catalog, raw = mixed_fixture()
    wire = compact_fixture(raw, catalog)
    for foreign in (replace(ctx, source_sha256="b"*64), replace(ctx, piece=replace(ctx.piece, chunk_index=2))):
        with pytest.raises(SourceAnalysisWireError):
            expand_source_analysis_wire_v2(wire, build_source_evidence_catalog(foreign), foreign)


def test_native_quality_and_relation_gates_not_weakened(tmp_path):
    cfg, db = make_config(tmp_path)
    a, b = db.add_node("示例产品甲", "Product"), db.add_node("示例技术乙", "Technology")
    ctx, catalog, raw = mixed_fixture((a, b))
    raw["node_candidates"][1]["is_discrete_event"] = False
    raw["node_candidates"][2]["long_term_research_value"] = False
    raw["relation_candidates"][0]["from_node_id"] = b
    raw["relation_candidates"][0]["to_node_id"] = a
    expanded = expand_source_analysis_wire_v2(compact_fixture(raw, catalog), catalog, ctx)
    analyzer = Analyzer(cfg, db)
    old = analyzer._validate_source_output(raw, ctx.piece.source_text)
    new = analyzer._validate_source_output(expanded, ctx.piece.source_text)
    assert old == new
    assert not new["node_candidates"][1]["quality_eligible"]
    assert not new["node_candidates"][2]["quality_eligible"]
    assert not new["relation_candidates"] and new["rejected_relation_candidates"]


def size_benchmark():
    ctx, catalog, raw = dense_fixture()
    wire = compact_fixture(raw, catalog)
    expanded = expand_source_analysis_wire_v2(wire, catalog, ctx)
    sparse = compact_fixture(raw, catalog, refs=False)
    def size(v):
        text = encoded(v)
        return {"chars": len(text), "bytes": len(text.encode())}
    result = {"canonical": size(raw), "sparse_projection_only": size(sparse), "compact_wire": size(wire), "expanded_canonical": size(expanded)}
    result["reduction_chars_pct"] = 100*(1-result["compact_wire"]["chars"]/result["canonical"]["chars"])
    # Sequential ablations account exactly for savings, with protocol overhead.
    obj = copy.deepcopy(raw)
    previous = size(obj)
    changes = {}
    for category in ("claim_ref_derivation", "evidence_excerpt_and_pointer_reference"):
        if category == "evidence_excerpt_and_pointer_reference":
            for i, claim in enumerate(obj["claims"]):
                claim.pop("evidence_excerpt")
                claim.pop("evidence_pointer")
                claim["evidence_ref"] = wire["claims"][i]["evidence_ref"]
        else:
            for claim in obj["claims"]:
                claim.pop("claim_ref")
        current = size(obj)
        changes[category] = {k: previous[k]-current[k] for k in previous}
        previous = current
    obj["node_candidates"] = copy.deepcopy(wire["node_candidates"])
    current = size(obj)
    changes["node_sparse_variants_and_refs"] = {k: previous[k]-current[k] for k in previous}
    changes["other_defaults_root_and_version_overhead"] = {k: current[k]-result["compact_wire"][k] for k in current}
    assert sum(v["chars"] for v in changes.values()) == result["canonical"]["chars"]-result["compact_wire"]["chars"]
    assert sum(v["bytes"] for v in changes.values()) == result["canonical"]["bytes"]-result["compact_wire"]["bytes"]
    return {"fixture": "R2-derived synthetic 40 Claims, authoritative PARA pointer, ordinal refs, full legacy Node values retained", "claim_count": 40, "units": len(catalog.units),
        "serialization": "minified UTF-8 JSON ensure_ascii=False sort_keys=True", "sizes": result, "savings_decomposition": changes, "token_estimates": None, "canonical_exact_equal": expanded == raw}


def test_dense_40_claim_size_gate():
    result = size_benchmark()
    assert result["canonical_exact_equal"]
    assert result["sizes"]["reduction_chars_pct"] >= 30
    assert result["sizes"]["expanded_canonical"] == result["sizes"]["canonical"]


def test_dense_fixture_existing_native_validation(tmp_path):
    cfg, db = make_config(tmp_path)
    ctx, catalog, raw = dense_fixture()
    expanded = expand_source_analysis_wire_v2(compact_fixture(raw, catalog), catalog, ctx)
    analyzer = Analyzer(cfg, db)
    old = analyzer._validate_source_output(raw, ctx.piece.source_text)
    new = analyzer._validate_source_output(expanded, ctx.piece.source_text)
    assert old == new and len(new["claims"]) == 40
    assert all(c["evidence_validated"] for c in new["claims"])
    assert all(c["quality_eligible"] for c in new["node_candidates"])


def test_foundation_dormant_and_schema12_surfaces_fail_closed():
    from pro_a.workbench.retry_compatibility import _execution_surface_comparison
    from pro_a.workbench.source_operations import MAX_STAGE1_JOBS_PER_RUN, SourceProfile
    from pro_a.cloud_contract import OPERATION_MAX_OUTPUT_TOKENS
    baseline = "27fd74d31bdf48f6684a71904b10de5d391820c3"
    # Additive schema acceptance changes the protected cloud surface. It must
    # remain incompatible; dormant Wire support does not authorize a retry.
    cloud = _execution_surface_comparison("cloud", baseline)
    native = _execution_surface_comparison("native", baseline)
    assert not cloud["compatible"] and cloud["reason"] == "SEMANTIC_SURFACE_CHANGED"
    assert native["compatible"] and native["reason"] == "SEMANTIC_SURFACE_EXACT"
    assert MAX_STAGE1_JOBS_PER_RUN == 31
    assert SourceProfile.__dataclass_fields__["max_extraction_pieces"].default == 16
    assert OPERATION_MAX_OUTPUT_TOKENS == {"SOURCE_ANALYSIS_PIECE": 12000, "SEMANTIC_DECOMPOSITION": 8192}
    assert operation_contract("SOURCE_ANALYSIS_PIECE")["provider_adapter_version"] == "source-analysis-piece-adapter-v2"
    assert operation_contract("SOURCE_ANALYSIS_PIECE")["prompt_version"] == "phase3e2sl6"
