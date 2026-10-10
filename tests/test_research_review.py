"""Partial research access never becomes acceptance. Synthetic writes only."""
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from pro_a import output_provider_record_v7 as v7
from pro_a.bounded_extraction import SeriesBudget, series_coverage
from pro_a.research_quarantine import inspect_response, parse_prefix
from pro_a.workbench import research_review as review
from pro_a.workbench.config import BoundaryError
from test_evidence_intent_prototype import setup, all_families, no_provider
from test_evidence_intent_v7 import new_record


def data_case(text='青松公司产能100台。\n前文背景。', budget=SeriesBudget()):
    data = setup(text, budget=budget)
    _, old = all_families(data, data[3].leaves[0])
    return data, new_record(old, data[1])


def inspect(data, record, raw=None):
    return inspect_response(raw if raw is not None else json.dumps(record, ensure_ascii=False).encode(),
        {'provider_record_version': v7.VERSION, 'run_id': 'SYNTHETIC', 'attempt_id': 'SYNTHETIC_ATTEMPT'},
        data[3].leaves[0], data[1], data[0], failure_code='INVALID_SEGMENT_RESPONSE')


def test_strict_utf8_spans_nested_strings_and_duplicate_keys():
    raw = '{"claims":[{"statement":"汉字 😀 \\\" } ] ","nested":{"a":[1,{"b":"[{}]"}]}} ,{"x":1,"x":2}],"node_matches":[]}'.encode()
    parsed = parse_prefix(raw)
    assert not parsed['complete'] and len(parsed['objects']) == 1
    obj = parsed['objects'][0]; a, b = obj['byte_span']
    assert json.loads(raw[a:b]) == obj['value']
    assert obj['object_sha256'] == hashlib.sha256(raw[a:b]).hexdigest()
    assert b > len(raw[:b].decode())  # Bytes are not Unicode character offsets.
    assert parsed['error']['code'] == 'DUPLICATE_KEY'


@pytest.mark.parametrize('suffix', [',{"statement":"unclosed', ',{"a":[1,2 INVALID', ',{"a":NaN}', ',{"a":1e999}', ',{"a":"\\ud800"}', ',]', ',{"x":1,"x":2}'])
def test_never_repairs_or_scans_suffix(suffix):
    parsed = parse_prefix(('{"claims":[{"a":1}'+suffix+'],"node_matches":[{"late":true}]}').encode())
    assert not parsed['complete']
    assert [(o['family'], o['index']) for o in parsed['objects']] == [('claims', 0)]
    assert all('late' not in o['value'] for o in parsed['objects'])


@pytest.mark.parametrize('raw', [b'{"claims":[{"a":', b'{"claims":[{"a":1}],"claims":[]}', b'\xff'])
def test_unproven_or_ambiguous_membership_has_no_candidates(raw):
    result = parse_prefix(raw)
    assert not result['complete'] and not result['objects']


def test_full_json_bad_evidence_retains_every_original_object_and_dependencies():
    data, record = data_case()
    original = copy.deepcopy(record)
    record['claims'][0]['evidence']['unit_anchor'] = 'EA_FORGED'
    document = inspect(data, record)
    assert not document['incomplete_response'] and len(document['objects']) == 6
    claim = next(o for o in document['objects'] if o['family'] == 'claims')
    assert claim['location_status'] == 'INVALID_EVIDENCE'
    for obj in document['objects']:
        assert obj['value'] == record[obj['family']][obj['index']]
        assert obj['semantic_review_status'] == 'SEMANTIC_REVIEW_REQUIRED'
    for obj in document['objects']:
        if obj['family'] in ('node_candidates', 'relation_candidates'):
            assert obj['reference_status'] == 'FAIL'
    assert record != original and not document['accepted'] and not document['canonical_permission']


@pytest.mark.parametrize('mutation', ['missing_candidate', 'missing_claim', 'unsupported', 'duplicate_property', 'foreign', 'context_invalid'])
def test_schema_ownership_and_reference_faults_are_separate(mutation):
    data, record = data_case(budget=SeriesBudget(initial_evidence_refs=1))
    if mutation == 'missing_candidate': record['claims'][0]['related_candidate_names'] = ['Missing']
    elif mutation == 'missing_claim': record['relation_candidates'][0]['supporting_claim_refs'] = ['C9']
    elif mutation == 'unsupported': record['claims'][0]['related_candidate_names'] = []
    elif mutation == 'duplicate_property': record['node_candidates'][1]['text_properties'] *= 2
    elif mutation == 'foreign': record['claims'][0]['evidence'] = v7.unit_selection(data[1].units[-1])
    elif mutation == 'context_invalid':
        record['claims'][0]['research_review']['context_dependencies'] = [{'evidence': {**record['claims'][0]['evidence'], 'unit_anchor': 'EA_FORGED'}, 'relationship': 'ANAPHORA', 'reason': 'Unproved'}]
    doc = inspect(data, record)
    assert any(o['local_errors'] or o['reference_errors'] for o in doc['objects'])
    if mutation == 'foreign':
        claim = next(o for o in doc['objects'] if o['family'] == 'claims')
        assert claim['location_status'] == 'LOCATION_VERIFIED'
        assert claim['ownership_status'] == 'FAIL'
    elif mutation == 'duplicate_property':
        assert next(o for o in doc['objects'] if o['family'] == 'node_candidates' and o['index'] == 1)['schema_status'] == 'FAIL'
    assert not doc['accepted']


def test_prefix_cross_objects_always_unknown_and_false_semantics_remain_pending():
    data, record = data_case()
    claim = record['claims'][0]
    claim['statement'] = '青松公司产能9999台。'  # Deliberately false, exact evidence remains 100.
    raw = ('{"claims":['+json.dumps(claim, ensure_ascii=False)+',{"structured_json":"broken').encode()
    doc = inspect(data, record, raw)
    obj = doc['objects'][0]
    assert obj['schema_status'] == 'PASS' and obj['location_status'] == 'LOCATION_VERIFIED'
    assert obj['reference_status'] == 'REFERENCE_UNRESOLVED'
    assert obj['semantic_truth'] == 'NOT_ESTABLISHED'
    assert doc['suffix_status'] == 'UNKNOWN_SUFFIX' and doc['total_object_counts'] == 'UNKNOWN'
    assert len(doc['objects']) == 1


def test_complete_root_order_does_not_change_dependency_status():
    data, record = data_case()
    record['claims'][0]['related_candidate_names'].append('Missing')
    left = inspect(data, record)
    right = inspect(data, dict(reversed(list(record.items()))))
    statuses = lambda d: {(o['family'],o['index']): (o['reference_status'],o['ownership_status']) for o in d['objects']}
    assert statuses(left) == statuses(right)


def test_formal_fake_run_blocked_reader_artifacts_restart_annotations_and_isolation(tmp_path, monkeypatch):
    from dataclasses import asdict
    from test_output_qualification import fixture, advance, FakeTransport
    from series_binding_helpers import rows
    from pro_a.workbench import output_qualification as operator
    value, run = fixture(tmp_path, monkeypatch, v7.VERSION)
    rid = run['processing_run_id']
    production = value['config'].knowledge_db.read_bytes()
    advance(value, rid)
    fake = FakeTransport()
    first = advance(value, rid, fake)
    assert first['accepted_leaf_calls'] == 1

    class Broken(FakeTransport):
        def __call__(self, *args, **kwargs):
            response = super().__call__(*args, **kwargs)
            fn = response.value['choices'][0]['message']['tool_calls'][0]['function']
            record = json.loads(fn['arguments'])
            fn['arguments'] = '{"claims":['+json.dumps(record['claims'][0])+',{"structured_json":"unclosed'
            return response

    failed = advance(value, rid, Broken())
    assert failed['state'] == 'BLOCKED'
    service = value['service']
    tables = ('bounded_extraction_events','bounded_extraction_segment_results','source_processing_events','source_processing_jobs','bounded_extraction_series_results')
    before = {t: rows(value,t) for t in tables}
    view = review.project_run(service, rid)
    assert view['accepted_segment_count'] == 1 and view['source_status'] == 'SOURCE_INCOMPLETE'
    assert {o['family'] for o in view['segments'][0]['objects']} >= {'claims','node_matches','node_candidates','relation_candidates'}
    assert all(o['evidence'] for o in view['segments'][0]['objects'])
    attempt = rows(value,'bounded_extraction_attempts')[-1]['attempt_id']
    document = review.inspect_attempt(service,rid,attempt)
    assert len(document['objects']) == 1 and document['incomplete_response']
    store = review.ResearchAttachments(service)
    def interrupted(name):
        if name == 'research_after_publish': raise RuntimeError('SIMULATED_INTERRUPT')
    monkeypatch.setattr(review,'checkpoint',interrupted)
    with pytest.raises(RuntimeError,match='SIMULATED_INTERRUPT'): store.publish(rid,attempt)
    monkeypatch.setattr(review,'checkpoint',lambda _:None)
    reference = store.publish(rid,attempt)
    assert store.read(reference) == document and store.publish(rid,attempt) == reference
    oid = document['objects'][0]['object_id']
    marker = store.annotate(reference,oid,reviewer='synthetic-reviewer',decision='INTERESTING',reason='Requires subject verification.')
    assert not marker['canonical_permission']
    store.annotate(reference,oid,reviewer='synthetic-reviewer',decision='NEEDS_FOLLOWUP',reason='Check the number.')
    def marker_interrupted(name):
        if name == 'research_marker_after_publish': raise RuntimeError('MARKER_INTERRUPT')
    monkeypatch.setattr(review,'checkpoint',marker_interrupted)
    with pytest.raises(RuntimeError,match='MARKER_INTERRUPT'):
        store.annotate(reference,oid,reviewer='synthetic-reviewer',decision='NOT_USEFUL',reason='Preserved independent research assessment.')
    monkeypatch.setattr(review,'checkpoint',lambda _:None)
    assert len(store.markers(reference)) == 3
    with pytest.raises(BoundaryError): store.annotate(reference,oid,reviewer='x',decision='KEEP',reason='Unauthorized')
    html = review.render_html(view,[document],store.markers(reference))
    assert 'INTERESTING' in html and 'REFERENCE_UNRESOLVED' in html and 'No promotion authority' in html
    hostile = copy.deepcopy(document); hostile['objects'][0]['value']['statement'] = '<script>alert(1)</script>'
    assert '<script>alert(1)</script>' not in review.render_html(view,[hostile])
    payload = {'config':asdict(value['config']),'profile':asdict(value['source_profile']),'cloud':asdict(service.jobs.profile),
               'run':rid,'attempt':attempt,'reference':reference,'object':oid}
    restart = tmp_path/'review-restart.json'; restart.write_text(json.dumps(payload,default=str))
    child = subprocess.run([sys.executable,'-B','-c','''
import json,sys,socket
from pathlib import Path
from pro_a.workbench.config import WorkbenchConfig
from pro_a.workbench.source_operations import SourceOperations,SourceProfile
from pro_a.workbench.cloud_jobs import CloudProfile
from pro_a.workbench.research_review import ResearchAttachments,project_run
socket.socket.connect=lambda *a: (_ for _ in ()).throw(AssertionError('NETWORK_FORBIDDEN'))
d=json.loads(Path(sys.argv[1]).read_text())
for k in ('knowledge_db','state_db','artifact_root'):d['config'][k]=Path(d['config'][k])
d['profile']['phase4_config_path']=Path(d['profile']['phase4_config_path'])
d['cloud']['accepted_model_aliases']=tuple(d['cloud']['accepted_model_aliases'])
s=SourceOperations(WorkbenchConfig(**d['config']),SourceProfile(**d['profile']),CloudProfile(**d['cloud']))
a=ResearchAttachments(s)
assert a.publish(d['run'],d['attempt'])==d['reference']
assert len(a.markers(d['reference']))==3
assert project_run(s,d['run'])['accepted_segment_count']==1
print('RESTART_PASS')
''',str(restart)],capture_output=True,timeout=60,env={**os.environ,'PYTHONPATH':os.pathsep.join([str(Path(__file__).parent),*sys.path])})
    assert child.returncode == 0, child.stderr.decode(errors='replace')
    assert b'RESTART_PASS' in child.stdout
    # Exercise the shipped reader entrypoint with frozen Run components, not
    # just its standalone render helper. Export cannot overwrite artifacts.
    from pro_a.workbench.config import WorkbenchConfig
    monkeypatch.setattr(WorkbenchConfig,'load',classmethod(lambda cls,path:value['config']))
    destination = tmp_path/'research.html'
    cli = ['--config','synthetic.toml','--run',rid,'--inspect-attempt',attempt,'--output',str(destination)]
    review.main(cli)
    assert 'SOURCE_INCOMPLETE' in destination.read_text(encoding='utf-8')
    with pytest.raises(FileExistsError): review.main(cli)
    with pytest.raises(BoundaryError,match='EXPORT_INSIDE_ARTIFACT_STORE_FORBIDDEN'):
        review.main(cli[:-1]+[str(value['config'].artifact_root/'forbidden.html')])
    worker = operator.frozen_worker(service,rid)
    binding = worker.output_batches.inputs(service.get_run(rid))[0]
    series, plan = worker.output_batches.ledger.read(binding[3].series_id)[:2]
    assert not series_coverage(series,plan,(),binding[2],binding[1]).complete
    from pro_a.claim_observations import build_observation_ledger
    with pytest.raises(ValueError): build_observation_ledger(run['source_id'],series,plan,(),binding[2],binding[1])
    with pytest.raises(ValueError): v7.compile_result(json.dumps(document),series,plan.leaves[-1],binding[2],binding[1])
    assert all(rows(value,t)==before[t] for t in tables)
    assert not rows(value,'source_processing_jobs') and not rows(value,'bounded_extraction_series_results')
    assert value['config'].knowledge_db.read_bytes() == production
    assert len(rows(value,'bounded_extraction_attempts')) == 2
    # The original failed Raw remains exactly hash-bound and never reaccepted.
    assert review.inspect_attempt(service,rid,attempt)==document
    marker_path = value['config'].artifact_root/'research-quarantine'/'markers'/reference['artifact_sha256']/'00000003.json'
    saved = marker_path.read_bytes()
    tampered = json.loads(saved); tampered['decision'] = 'KEEP'
    marker_path.write_text(json.dumps(tampered))
    with pytest.raises(BoundaryError,match='RESEARCH_MARKER_IDENTITY_MISMATCH'): store.markers(reference)
    marker_path.write_bytes(saved)
