"""Full family native equivalence, exact sentinels and frozen schema recovery."""
import copy
import json
from dataclasses import replace
from types import SimpleNamespace

import pytest
from pro_a.constants import NODE_TYPES
from pro_a.analyzer import Analyzer
from pro_a.bounded_extraction import expand_source_analysis_wire_v3
from pro_a.source_analysis_provider_record import provider_record_to_wire_v3
from pro_a.source_analysis_wire import _NODE_VARIANTS
from pro_a.workbench.whole_piece_raw import persist
from pro_a.workbench.cloud_jobs import JobError
from lexical_record_helpers import from_canonical
from stability_helpers import make_config
from test_source_analysis_wire import mixed_fixture, normal_node
from test_lexical_tool_adapter import request


@pytest.mark.parametrize('value', [0, 1, 0.0, 1.0, -0.0, 5e-324, 1e-100, 0.9999999999999999])
def test_confidence_canonical_numeric_identity(value):
    ctx, catalog, canonical = mixed_fixture()
    for family in ('claims', 'node_matches', 'node_candidates', 'relation_candidates'):
        for obj in canonical[family]:
            obj['confidence'] = value
    expanded = expand_source_analysis_wire_v3(provider_record_to_wire_v3(from_canonical(canonical, catalog)), catalog, ctx)
    assert json.dumps(expanded, sort_keys=True) == json.dumps(canonical, sort_keys=True)


@pytest.mark.parametrize('node_type', NODE_TYPES)
def test_all_node_types_native_accept_reject_equivalence(tmp_path, node_type):
    cfg, db = make_config(tmp_path)
    nodes = (db.add_node('示例产品甲', 'Product'), db.add_node('示例技术乙', 'Technology'))
    ctx, catalog, canonical = mixed_fixture(nodes)
    candidate = normal_node('Synthetic Candidate')
    candidate.update(primary_type=node_type, is_discrete_event=True, event_time='2026-01-01',
        evidence_excerpt=catalog.units[1].exact_text, long_term_research_value=True,
        cross_source_or_node_value=True, question='Synthetic question?', importance='Synthetic importance',
        what_would_change_my_mind='Synthetic contrary evidence',
        candidate_kind='research_question' if node_type == 'ResearchQuestion' else 'normal')
    canonical['node_candidates'] = [candidate]
    for claim in canonical['claims']:
        claim['related_candidate_names'] = []
    converted = expand_source_analysis_wire_v3(provider_record_to_wire_v3(from_canonical(canonical, catalog)), catalog, ctx)
    assert converted == canonical
    analyzer = Analyzer(cfg, db)
    def native(value):
        analyzer.llm = SimpleNamespace(available=True, json=lambda *a: copy.deepcopy(value))
        return analyzer.analyze_source('synthetic.txt', ctx.piece.source_text, 'deep', adaptive_retry_policy='forbid')
    assert native(canonical) == native(converted)


def test_native_relation_rejection_still_equivalent(tmp_path):
    cfg, db = make_config(tmp_path)
    ctx, catalog, canonical = mixed_fixture((db.add_node('示例产品甲', 'Product'), db.add_node('示例技术乙', 'Technology')))
    for claim in canonical['claims']:
        claim['related_node_ids'] = []
    # As in the lexical mini probe: a uses Claim does not establish related_to.
    canonical['relation_candidates'][0]['relation_type'] = 'related_to'
    converted = expand_source_analysis_wire_v3(provider_record_to_wire_v3(from_canonical(canonical, catalog)), catalog, ctx)
    analyzer = Analyzer(cfg, db)
    def native(value):
        analyzer.llm = SimpleNamespace(available=True, json=lambda *a: copy.deepcopy(value))
        return analyzer.analyze_source('synthetic.txt', ctx.piece.source_text, 'deep', adaptive_retry_policy='forbid')
    left, right = native(canonical), native(converted)
    assert left == right and right.relation_candidates == []
    assert right.rejected_relation_candidates[0]['reason'] == 'semantic support insufficient'


@pytest.mark.parametrize('field', ['tool_schema_sha256', 'tool_name', 'tool_strict', 'tool_parameters', 'provider_record_version', 'bool_alias', 'schema_bool_alias'])
def test_frozen_schema_drift_prevents_raw_recovery(field):
    frozen = request()
    identity = copy.deepcopy(frozen.prompt_identity)
    if field == 'bool_alias': identity['tool_strict'] = 1
    elif field == 'schema_bool_alias': identity['tool_parameters']['additionalProperties'] = 0
    else: identity[field] = 'drift'
    # Identity must fail before any database access or ProviderRecord parse.
    with pytest.raises(JobError, match='WHOLE_PIECE_TOOL_SCHEMA_IDENTITY_MISMATCH'):
        persist(None, None, replace(frozen, prompt_identity=identity), None)


@pytest.mark.parametrize('variant', ['Event', 'Theme', 'ResearchQuestion'])
def test_preserved_active_fields_forbidden(variant):
    _, catalog, raw = mixed_fixture()
    record = from_canonical(raw, catalog)
    obj = next(n for n in record['node_candidates'] if n['primary_type'] == variant)
    field = sorted(_NODE_VARIANTS[variant] - {'evidence_ref'})[0]
    obj['preserved_fields'][field] = {'present': 'TRUE', 'value': obj[field]}
    with pytest.raises(ValueError, match='ACTIVE_FIELD_IN_PRESERVED_SLOT'):
        provider_record_to_wire_v3(record)


@pytest.mark.parametrize('family,field', [('source_metadata', 'author'), ('source_metadata', 'organization'), ('source_metadata', 'summary'),
    ('claims', 'related_node_ids'), ('claims', 'related_candidate_names'), ('claims', 'assumption'),
    ('node_matches', 'reason'), ('node_candidates', 'aliases'), ('node_candidates', 'suggested_parent_node_ids'),
    ('node_candidates', 'description'), ('node_candidates', 'reason'), ('relation_candidates', 'reason'), ('source_references', 'note')])
def test_each_empty_optional_sentinel_exact_default(family, field):
    ctx, catalog, canonical = mixed_fixture()
    obj = canonical[family] if family == 'source_metadata' else canonical[family][0]
    obj[field] = [] if field in ('related_node_ids', 'related_candidate_names', 'aliases', 'suggested_parent_node_ids') else ''
    wire = provider_record_to_wire_v3(from_canonical(canonical, catalog))
    assert expand_source_analysis_wire_v3(wire, catalog, ctx) == canonical
    obj = wire[family] if family == 'source_metadata' else wire[family][0]
    del obj[field]
    assert expand_source_analysis_wire_v3(wire, catalog, ctx) == canonical
