"""Synthetic archive/authorities only; no real Provider or production paths."""
import copy
from dataclasses import asdict
import json
import os
import subprocess
import sys

import pytest

from pro_a import recovered_candidate_origin as bridge, node_evidence_recovery as recovery
from pro_a import output_provider_record_v7 as v7
from pro_a.bounded_extraction import expand_source_analysis_wire_v3
from pro_a.candidate_origin import semantic_projection
from pro_a.evidence_binding import identity
from pro_a.workbench.candidate_inputs import CandidateInputs
from pro_a.workbench.candidate_lifecycle import RevisionLifecycle, _required, freeze, require_documents
from pro_a.workbench.config import BoundaryError
from test_output_qualification import fixture, advance
from test_candidate_origin_v2 import isolated_review_chain, select_document
from series_binding_helpers import rows, synthetic_providers, batch_record, response_content, ToolResponse

HUMAN={'actor':'TEST_FIXTURE_HUMAN','session_id':'TEST_FIXTURE_SESSION','principal_type':'HUMAN_USER'}


class DuplicateSupport:
    """Five raw claims are sufficient: two held, three independently executable.

    Build the synthetic v7 response without inventing a Context-only source row
    for the common 18-unit transport fixture. The request itself is untouched.
    """
    def __init__(self):self.calls=[]

    def __call__(self,endpoint,**kwargs):
        from types import SimpleNamespace
        from unittest.mock import patch
        from pro_a import output_decomposition as output
        from node_intent_helpers import from_valid_v4
        from test_evidence_intent_v7 import new_record
        request=kwargs['json'];self.calls.append(copy.deepcopy(request))
        document=json.loads(request['messages'][1]['content']);target=document['frozen_target']
        source=''.join('['+r['evidence_ref']+']'+r['text']+'[/'+r['evidence_ref']+']'
            if r['role']=='ASSIGNED' else r['text'] for r in document['source_regions'])
        record=from_valid_v4(batch_record(json.loads(response_content(target,source)),
                              {**target,'provider_record_version':output.RECORD_VERSION}))
        for node in record['node_candidates']:node.pop('ownership_evidence_ref')
        anchors={r['evidence_ref']:r['anchor_id'] for r in document['source_regions'] if 'anchor_id' in r}
        catalog=SimpleNamespace(units=[SimpleNamespace(evidence_ref=k) for k in anchors])
        with patch.object(v7,'unit_anchor',lambda u:anchors[u.evidence_ref]):
            record=new_record(record,catalog)
        record['claims']=record['claims'][:5]
        node=record['node_candidates'][0]
        node.update(canonical_name='Synthetic Held Technology',primary_type='Technology')
        node['evidence_properties']=[{'field':'evidence_ref','value':copy.deepcopy(c['evidence'])} for c in record['claims'][:2]]
        for i,c in enumerate(record['claims']):
            c['related_candidate_names']=[node['canonical_name']] if i<2 else []
        record['relation_candidates']=[]
        nodes=document['scoped_node_catalog']
        record['claims'][0]['related_node_ids']=[n['node_id'] for n in nodes]
        record['node_matches']=[{'node_id':n['node_id'],'role':'related','confidence':'0.9',
            'reason':'Explicit synthetic name','evidence':copy.deepcopy(record['claims'][0]['evidence'])} for n in nodes]
        assert request['tools'][0]['function']['parameters']==v7.record_schema()
        return ToolResponse(json.dumps(record))


def failed_case(tmp_path,monkeypatch):
    monkeypatch.setattr('requests.sessions.Session.request',lambda *a,**k:pytest.fail('EXTERNAL_NETWORK'))
    import test_output_qualification as fixtures
    original_pdf=fixtures.clean_pdf
    small='\n'.join(f'Synthetic Company product {i:03d} states Synthetic Product uses Synthetic Capacity with capacity {i+1} units.' for i in range(5))
    monkeypatch.setattr(fixtures,'clean_pdf',lambda *a,**k:original_pdf(*a,**{**k,'text':small}))
    value,run=fixture(tmp_path,monkeypatch,v7.VERSION)
    from pro_a.admission_schema import migrate
    from pro_a.production_promotion import sha256_file
    migrate(value['config'].knowledge_db,expected_sha256=sha256_file(value['config'].knowledge_db),
        backup_path=tmp_path/'schema-backup.db',configured_production_path=value['config'].knowledge_db)
    rid=run['processing_run_id']
    advance(value,rid); final=advance(value,rid,DuplicateSupport())
    for _ in range(4):
        if final['state']=='BLOCKED':break
        final=advance(value,rid,DuplicateSupport())
    assert final['state']=='BLOCKED' and not rows(value,'bounded_extraction_segment_results')
    service=value['service']
    from pro_a.workbench.output_qualification import frozen_worker
    worker=frozen_worker(service,rid)
    binding,ctx,cat,series=worker.output_batches.inputs(worker.get_run(rid))[0]
    _,plan,_,_=worker.output_batches.ledger.read(series.series_id)
    attempt=rows(value,'bounded_extraction_attempts')[0]
    outcome=rows(value,'bounded_extraction_outcomes')[0]
    ledger=worker.output_batches.ledger
    _,raw=ledger._decode_envelope(attempt,ledger._read_artifact(series.series_id,attempt['attempt_id']+'.raw.json',outcome))
    proposal={'version':recovery.PLAN,'raw_sha256':__import__('hashlib').sha256(raw).hexdigest(),
        'scope':recovery.scope(series,plan.leaves[0],ctx),'conversions':[{'candidate_index':0,
        'canonical_name':'Synthetic Held Technology','semantics':recovery.SEMANTICS,
        'reviewer':'TEST_MODEL_NOT_HUMAN','reason':'Explicit synthetic support classification'}]}
    artifact=recovery.recover(raw,proposal,series,plan.leaves[0],cat,ctx,plan=plan)
    original=artifact['projected_record']
    revisions={'version':bridge.REVISION,'recovery_identity':artifact['identity'],
        'reviewer':'TEST_MODEL_NOT_HUMAN','reason':'Explicit full-field proposals','claims':[], 'nodes':[],
        'matches':[{'parent_index':i,'parent_sha256':identity(m),'disposition':'KEEP','reason':'Explicit synthetic name'}
                   for i,m in enumerate(original['node_matches'])]}
    for i,c in enumerate(original['claims']):
        child=copy.deepcopy(c)
        child['structured_json']=json.dumps({'one_proposition':child['statement']})
        revisions['claims'].append({'child_id':str(i),'parent_index':i,'parent_sha256':identity(c),
            'previous_draft':c,'previous_draft_sha256':identity(c),'record':child,
            'reason':'One synthetic proposition','field_review':{k:'Explicit fixture field review' for k in child}})
    node=copy.deepcopy(original['node_candidates'][0]);node['description']='Synthetic identity only; temporary predictions remain Claims.'
    revisions['nodes']=[{'parent_index':0,'parent_sha256':identity(original['node_candidates'][0]),
                         'record':node,'reason':'Explicit Node description revision, remains deferred'}]
    archive=CandidateInputs(service)
    ref=archive.publish_recovered(rid,attempt['attempt_id'],proposal,revisions)
    doc=archive.read(ref)
    value.update(original_id=rid,attempt=attempt['attempt_id'],archive=archive,reference=ref,document=doc,
        revisions=revisions,recovery_proposal=proposal,raw=raw,inputs=(ctx,cat,series,plan),artifact=artifact)
    return value


def metadata(doc):
    from pro_a import source_metadata_authority as authority
    c=authority.candidate_resolution(doc['metadata_scope'],[])
    return authority.authorize_resolution(c,{'version':authority.DECISION_VERSION,'candidate_identity':c['identity'],
        'scope_sha256':identity(doc['metadata_scope']),'approved':True,'actor':'TEST_FIXTURE_HUMAN',
        'reason':'Fixture only, never production approval','decision_reference':'TEST_FIXTURE_ONLY',
        'values':{k:doc['source_metadata'].get(k,'') for k in authority.FIELDS if k!='summary'},
        'summary_policy':'PRESERVE_ALL_VARIANTS_UNRESOLVED'})


def prepared(tmp_path,monkeypatch):
    value=failed_case(tmp_path,monkeypatch)
    ref=value['archive'].publish_recovered(value['original_id'],value['attempt'],value['recovery_proposal'],
        value['revisions'],metadata_resolution=metadata(value['document']))
    doc=value['archive'].read(ref)
    with pytest.raises(BoundaryError,match='CANDIDATE_REVISION_NOT_CURRENT'):
        value['service'].start_recovered_review([ref],idempotency_key='unselected-recovery-0001',entry_contract=bridge.ENTRY_CONTRACT)
    select_document(value,doc)
    value.update(selected_ref=ref,selected=doc)
    return value


def packet(value,ref,key):
    service=value['service']
    run=service.start_recovered_review([ref],idempotency_key=key,entry_contract=bridge.ENTRY_CONTRACT)['run']
    rid=run['processing_run_id']
    for _ in range(2):run=service.advance_once(worker_id='TEST_FIXTURE',processing_run_id=rid)
    with synthetic_providers(value) as providers:
        providers['SEMANTIC_DECOMPOSITION'].provider_identity=service.jobs.profile.provider
        providers['SEMANTIC_DECOMPOSITION'].adapter_version=service.jobs.profile.adapter_for_operation('SEMANTIC_DECOMPOSITION')
        run=service.advance_once(worker_id='TEST_FIXTURE',processing_run_id=rid,provider=providers)
    assert run['state']=='HUMAN_REVIEW_REQUIRED',run.get('error')
    return run


def test_trusted_archive_idempotent_restart_and_failed_accepted_entry(tmp_path,monkeypatch):
    value=failed_case(tmp_path,monkeypatch)
    archive,doc=value['archive'],value['document']
    assert doc['version']==bridge.VERSION and 'acceptance' not in doc
    assert len(doc['recovery']['support_mappings'])==2 and not doc['canonical_permission']
    before={t:rows(value,t) for t in ('bounded_extraction_attempts','bounded_extraction_outcomes',
        'bounded_extraction_dispatches','bounded_extraction_segment_results','bounded_extraction_series','source_processing_runs')}
    assert archive.publish_recovered(value['original_id'],value['attempt'],value['recovery_proposal'],value['revisions'])==value['reference']
    with pytest.raises(BoundaryError,match='RECOVERED_EXPECTED_IDENTITY_MISMATCH'):
        archive.publish_recovered(value['original_id'],value['attempt'],value['recovery_proposal'],value['revisions'],expected_identity='0'*64)
    assert before=={t:rows(value,t) for t in before}
    with pytest.raises(BoundaryError,match='CANDIDATE_ACCEPTED_RESULT_REQUIRED'):
        archive.publish(value['original_id'],value['attempt'])
    with pytest.raises(BoundaryError,match='CANDIDATE_ATTEMPT_OUTSIDE_RUN'):
        archive.publish_recovered(value['original_id'],'ATTEMPT_FORGED',value['recovery_proposal'],value['revisions'])
    from pro_a.workbench.source_operations import SourceOperationError
    from pro_a.candidate_origin_v2 import ENTRY_CONTRACT as ACCEPTED_ENTRY
    with pytest.raises(SourceOperationError,match='CANDIDATE_REVIEW_ENTRY_CONTRACT_REQUIRED'):
        value['service'].start_v7_review([value['reference']],idempotency_key='wrong-origin-entry-0001',entry_contract=ACCEPTED_ENTRY)
    with pytest.raises(SourceOperationError,match='SOURCE_METADATA_AUTHORITY_REQUIRED'):
        value['service'].start_recovered_review([value['reference']],idempotency_key='unselected-meta-0001',entry_contract=bridge.ENTRY_CONTRACT)
    job=tmp_path/'restart.json';job.write_text(json.dumps({'config':asdict(value['config']),'ref':value['reference']},default=str))
    result=subprocess.run([sys.executable,'-B','-c',
        'import json,sys; from pathlib import Path; from pro_a.workbench.config import WorkbenchConfig; '
        'from pro_a.workbench.candidate_inputs import CandidateArchive,CandidateInputs; j=json.loads(Path(sys.argv[1]).read_text()); '
        '[j["config"].update({k:Path(j["config"][k])}) for k in ("knowledge_db","state_db","artifact_root")]; '
        'print(CandidateInputs(CandidateArchive(WorkbenchConfig(**j["config"]))).read(j["ref"])["identity"])',str(job)],
        capture_output=True,env={**os.environ,'PYTHONPATH':os.pathsep.join(sys.path)},timeout=60)
    assert result.returncode==0,result.stderr.decode(errors='replace')
    assert doc['identity'] in result.stdout.decode()
    # A forged upload can recompute all its own hashes. Durable reconstruction,
    # rather than these caller-supplied hashes/flags, must still reject it.
    import hashlib
    from pro_a.workbench.bounded_extraction_persistence import canonical
    for mutate in ('permission','source'):
        forged=copy.deepcopy(doc)
        if mutate=='permission':forged['canonical_permission']=True
        else:forged['scope']['source_id']='SRC_FORGED'
        forged['identity']=identity({k:v for k,v in forged.items() if k!='identity'})
        content=canonical(forged).encode();digest=hashlib.sha256(content).hexdigest()
        relative='candidate-inputs/'+digest+'.json'
        (value['config'].artifact_root/relative).write_bytes(content)
        with pytest.raises(BoundaryError,match='CANDIDATE_ORIGIN_DRIFT'):
            archive.read({'version':bridge.VERSION,'identity':forged['identity'],
                          'artifact_relative':relative,'artifact_sha256':digest})


def test_full_fields_bindings_dependencies_and_tampering(tmp_path,monkeypatch):
    value=prepared(tmp_path,monkeypatch);doc=value['selected'];cfg=value['config']
    analysis=semantic_projection([doc])
    assert len(analysis.claims)==3 and not analysis.node_candidates
    assert all(not c['related_candidate_names'] and set(c['structured'])=={'one_proposition'} for c in analysis.claims)
    assert sum(o['status']=='DEFER' for o in doc['objects'] if 'parent' in o)==2
    assert len(_required([doc]))==6
    assert all('recovery' in c['candidate_observations'][0]['lineage'] and
        'acceptance' not in c['candidate_observations'][0]['lineage'] for c in analysis.claims)
    for fault in ('source','recovery','parent','previous','evidence','field_review','node_identity'):
        rev=copy.deepcopy(value['revisions']);plan=copy.deepcopy(value['recovery_proposal'])
        if fault=='source':plan['scope']['source_sha256']='0'*64
        elif fault=='recovery':rev['recovery_identity']='0'*64
        elif fault=='parent':rev['claims'][0]['parent_sha256']='0'*64
        elif fault=='previous':rev['claims'][0]['previous_draft_sha256']='0'*64
        elif fault=='evidence':rev['claims'][0]['record']['evidence']['unit_anchor']='EA_FORGED'
        elif fault=='field_review':rev['claims'][0]['field_review'].pop('statement')
        else:rev['nodes'][0]['record']['canonical_name']='Forged identity'
        with pytest.raises(ValueError):
            value['archive'].publish_recovered(value['original_id'],value['attempt'],plan,rev)
    wrong=metadata(value['document']);wrong['scope']['source_id']='SRC_OTHER_MATERIAL'
    with pytest.raises(ValueError):
        value['archive'].publish_recovered(value['original_id'],value['attempt'],value['recovery_proposal'],
            value['revisions'],metadata_resolution=wrong)
    lifecycle=RevisionLifecycle(cfg);binding=freeze(cfg,[doc])
    ref=_required([doc])[0]
    with pytest.raises(BoundaryError,match='HUMAN_USER_REQUIRED'):
        lifecycle.decide('REVOKE',ref,expected_head=lifecycle.read(ref)['head_sha256'],
            identity={**HUMAN,'principal_type':'MODEL'},reason='not human',idempotency_key='forged-human-0001',confirm=True)
    lifecycle.decide('REVOKE',ref,expected_head=lifecycle.read(ref)['head_sha256'],identity=HUMAN,
        reason='Fixture revoke',idempotency_key='test-revoke-00001',confirm=True)
    with pytest.raises(BoundaryError,match='NOT_CURRENT'):require_documents(cfg,[doc],binding)


def test_recovered_origin_native_review_packet_and_existing_authority_chain(tmp_path,monkeypatch):
    value=prepared(tmp_path,monkeypatch)
    run=packet(value,value['selected_ref'],'recovered-review-0001')
    from pro_a.read_model.review_context import basis
    from pro_a.read_model.service import ReadService
    _,candidates,_=basis(ReadService(value['config']),run['packet_artifact_id'],'blind',None)
    claims=[c for c in candidates if c.candidate_type=='CLAIM']
    assert len(claims)==3
    assert all(o.lineage.recovery['formal_accepted'] is False for c in claims for o in c.content.candidate_origin.observations)
    assert not rows(value,'bounded_extraction_segment_results')
    isolated_review_chain(value,run,tmp_path,monkeypatch)
    assert value['service'].get_run(value['original_id'])['state']=='BLOCKED'


def proposal(value):
    revisions=copy.deepcopy(value['revisions'])
    revisions['claims'][2]['reason']='TEST FIXTURE explicit replacement of same proposition'
    ref=value['archive'].publish_recovered(value['original_id'],value['attempt'],value['recovery_proposal'],
        revisions,metadata_resolution=metadata(value['document']))
    return ref,value['archive'].read(ref)


def test_recovered_replacement_invalidates_old_advice_seal_and_execution(tmp_path,monkeypatch):
    # Reuse the complete existing test body, including P0/P1/P2 services and a
    # fresh re-review after supersession, with the new failed-Raw Origin fixture.
    import test_candidate_lifecycle as existing
    monkeypatch.setattr(existing,'prepared',prepared)
    monkeypatch.setattr(existing,'packet',packet)
    monkeypatch.setattr(existing,'proposal',proposal)
    existing.test_replacement_blocks_old_authority_then_fresh_review_executes(tmp_path,monkeypatch)


@pytest.mark.parametrize('winner',['execution','replacement'])
def test_recovered_cross_process_execution_and_replacement_serial_order(tmp_path,monkeypatch,winner):
    # Exactly the existing cross-process race, not a stand-in transaction.
    import test_candidate_lifecycle as existing
    monkeypatch.setattr(existing,'prepared',prepared)
    monkeypatch.setattr(existing,'packet',packet)
    monkeypatch.setattr(existing,'proposal',proposal)
    existing.test_cross_process_execution_and_replacement_serial_order(tmp_path,monkeypatch,winner)
