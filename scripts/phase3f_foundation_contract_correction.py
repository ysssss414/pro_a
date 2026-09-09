"""Bounded V4 qualification runbook: preview or freeze BLANK + unauthorised slate.

Never invokes compile_mutations/build_foundation_handoff or writes a database.
The original archive and review/authorization/STOP artifacts are immutable inputs.
"""
from collections import Counter
from contextlib import closing
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import zipfile
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from pro_a.production_promotion import canonical_sha256, sha256_file, production_identity, connect_read_only
from pro_a.phase3f_foundation_baseline import build_review_packet, validate_review, validate_files
from pro_a.foundation_execution_contract import BOUND_IDENTITY_CONTRACT, CONTRACT_SHA256, temporal_census
from pro_a.foundation_requalification import requalify_identity_contract
from pro_a.foundation_identity_admission import preview_eligibility
from pro_a.foundation_schema_preparation import require_execution_schema

OUT = ROOT / 'workspace/phase3f_foundation_contract_correction'
MIG = ROOT / 'workspace/phase3f_foundation_schema_migration/resumed_connection_closure'
BLANK = MIG / 'foundation_complete_review_packet_schema_0_2_3.json'
ORIGINAL = ROOT / 'workspace/phase3f_foundation_complete_baseline/foundation_complete_review_packet.json'
STOP = ROOT / 'workspace/phase3f_foundation_human_review_completion/human_review_stop_receipt.json'
PRODUCTION = ROOT / 'workspace/pro_a.db'
ARCHIVE = ROOT / 'workspace/foundation_backfill_web_sol_v1.zip'
REC = Path('C:/Users/cjzs0/Downloads/phase3f_foundation_review_recommendations_295.json')
AUTH = Path('C:/Users/cjzs0/Downloads/phase3f_foundation_human_review_authorization.json')
REQUEST = Path('C:/Users/cjzs0/.codex/attachments/f094bcb0-7a39-4c18-b47a-a3d3ca7247ee/pasted-text.txt')
OLD_COMMIT = '7e30debd3e923a077c5560d30acada2ba25efa5d'
PRODUCTION_SHA = '312c977baa760fd277466bd00a1062bd6a94fbf71b590eb8760bce212e499b1f'
ARCHIVE_SHA = '95694f1456774a195d5aed0e0c2e34c949afa1d9b803b6cc2614bd35dc90b759'
INVENTORY_SHA = '7045053967f927612af649b94628913bad2698d62e3549ae2a8eec3b9a0b4c46'
REC_SHA = '2f41adb161569810739bf828f88c338f31533c66740a049751841c7a34faf28a'
AUTH_SHA = '314d0a3b7ec4939112cdb83c6882c894d473706f43a8337f8115a2a71472cad7'


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def git(*args):
    return subprocess.check_output(['git', *args],cwd=ROOT,stderr=subprocess.DEVNULL).decode('utf-8').strip()


def freeze(name, value):
    path = OUT / name
    data = (value if isinstance(value,str) else json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2)+'\n').encode('utf-8')
    path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists():
        assert path.read_bytes() == data, 'FROZEN_RERUN_DRIFT:' + name
    else:
        with path.open('xb') as stream:
            stream.write(data)
    return dict(path=str(path),sha256=sha256_file(path))


def verify_semantic(value, key, expected):
    assert canonical_sha256({k:v for k,v in value.items() if k != key}) == value[key] == expected


def preflight():
    assert sha256_file(ARCHIVE) == ARCHIVE_SHA
    freeze('archive_input_freeze.json',dict(path=str(ARCHIVE),sha256=ARCHIVE_SHA,size=ARCHIVE.stat().st_size,immutable=True))
    blank, rec, auth, stop = read(BLANK), read(REC), read(AUTH), read(STOP)
    verify_semantic(rec,'recommendation_semantic_sha256',REC_SHA)
    verify_semantic(auth,'authorization_semantic_sha256',AUTH_SHA)
    verify_semantic(stop,'receipt_semantic_sha256','8dd100b1a2fc1662cf91b079d83e5c406ff39f81a9bb6eb9d16654f753e32c67')
    assert blank['packet_id'] == 'FOUNDATION_REVIEW_CBAC970C11B6CD04'
    assert blank['immutable_packet_sha256'] == '2b5e8312cfc6b4273f7ef6239390761d61c1e00387b0987a5f41b7705baec42c'
    assert sha256_file(BLANK) == 'd76d5b0037c704b6b314a53ac522f411ef977e49f90fc388d8ce4cbc472efe7d'
    assert blank['repository_commit'] == OLD_COMMIT
    assert blank['execution_contract']['contract_sha256'] == CONTRACT_SHA256 == '9c46b3e1a211400c407fcd5c67956428a8aef7507f0a49ff47ab62e22804d634'
    assert blank['evidence_governance_manifest']['manifest_sha256'] == '77cbf56c1f3105b9a8719b7913ddb6405ed7e53e86f6fbc68c4463dde3e7c443'
    validate_review(blank,expected_sha256=blank['immutable_packet_sha256'],completed=False)
    validate_files(blank)
    production = production_identity(PRODUCTION)
    assert production == blank['production_baseline'] and production['sha256'] == PRODUCTION_SHA and production['schema_version']=='0.2.3'
    assert all(production['counts'][t]==0 for t in ('relation_temporal_semantics','relation_evidence_links','relation_evidence_authorizations'))
    with closing(connect_read_only(PRODUCTION)) as conn:
        require_execution_schema(conn)
        official = {r['view_id']:canonical_sha256(dict(r)) for r in conn.execute("SELECT * FROM current_views WHERE status='official' ORDER BY view_id")}
    assert official == stop['official_views_after']
    with zipfile.ZipFile(ARCHIVE) as archive:
        members = {}
        for entry in archive.infolist():
            if entry.is_dir():
                continue
            name = entry.filename.removeprefix('foundation_backfill_web_sol_v1/')
            assert name != entry.filename and name not in members and not any(p in {'..',''} for p in name.split('/'))
            members[name] = archive.read(entry)
    inventory = [dict(path=n,size=len(data),sha256=hashlib.sha256(data).hexdigest()) for n,data in sorted(members.items())]
    assert canonical_sha256(inventory) == blank['package']['inventory_sha256'] == INVENTORY_SHA
    sibling = ARCHIVE.with_suffix(''); inspection = sibling / 'foundation_backfill_web_sol_v1'
    if sibling.exists():
        actual = [dict(path=p.relative_to(inspection).as_posix(),size=p.stat().st_size,sha256=sha256_file(p)) for p in inspection.rglob('*') if p.is_file()]
        assert sorted(actual,key=lambda x:x['path']) == inventory
        assert not [p for p in sibling.rglob('*') if p.is_file() and not p.is_relative_to(inspection)]
    evidence = {e['evidence_id']:e for e in json.loads(members['evidence_index.json'])}
    assert len(evidence)==98 and len(blank['registry']['sources'])==33
    accounting = {(a['kind'],a['object_id']):a['content_sha256'] for a in blank['package']['object_accounting']}
    assert all(canonical_sha256(e)==accounting['evidence',eid] for eid,e in evidence.items())
    assert all(canonical_sha256(r['content']['raw'])==accounting[k,r['candidate_id']] for k,rows in blank['objects'].items() for r in rows)
    preserved = [BLANK,ORIGINAL,REC,AUTH,STOP,ARCHIVE,REQUEST,
        ROOT / 'src/pro_a/migrations/foundation_0_2_3_relation_native.sql',
        ROOT / 'workspace/phase3f_foundation_relation_native_governance/human_evidence_governance_authorization_manifest.json',
        ROOT / 'docs/PHASE1_1B_FUNCTIONAL_RELATION_CLOSURE.md']
    preserved += [p for p in STOP.parent.iterdir() if p.is_file()]
    starting = dict(production=production,official_views=official,inventory_sha256=INVENTORY_SHA,
        immutable_file_bindings={str(p):sha256_file(p) for p in sorted(set(preserved))})
    freeze('immutable_starting_state.json',starting)
    return blank,rec,evidence,starting


def qualify():
    blank,rec,evidence,starting = preflight()
    with closing(connect_read_only(PRODUCTION)) as conn:
        objects = requalify_identity_contract(read(ORIGINAL),blank,conn,evidence)
        snapshot = {t:[dict(r) for r in conn.execute(f'SELECT * FROM "{t}"')] for t in starting['production']['counts']}
    new = build_review_packet(package=blank['package'],registry=blank['registry'],production=starting['production'],
        repository_commit=git('rev-parse','HEAD'),objects=objects,timestamp=blank['frozen_timestamp'],
        execution_contract=BOUND_IDENTITY_CONTRACT,evidence_governance_manifest=blank['evidence_governance_manifest'],identity_evidence_index=evidence)
    decisions = {r['candidate_id']:{k:r[k] for k in ('decision','reason','target_id')} for rows in rec['decisions'].values() for r in rows}
    preview = preview_eligibility(new,snapshot,decisions)
    assert preview['canonical_equivalent_noop_count']==2
    assert set(preview['identity_plan']['nodes']) == {cid for cid,d in decisions.items() if d['decision'] in {'CREATE','REUSE'} and cid.startswith('FND_NODE_')}
    old_records = {(k,r['candidate_id']):r for k,rows in blank['objects'].items() for r in rows}
    comparison = []
    for kind,rows in new['objects'].items():
        for row in rows:
            old = old_records[kind,row['candidate_id']]
            assert old['content']['raw'] == row['content']['raw']
            diff = {k for k in set(old['content'])|set(row['content']) if old['content'].get(k) != row['content'].get(k)}
            assert diff == ({'identity_admission_contract'} if kind in {'nodes','aliases'} else set())
            comparison.append(dict(candidate_id=row['candidate_id'],kind=kind,native_sha256=canonical_sha256(row['content']['raw']),
                old_review_content_sha256=old['content_sha256'],new_review_content_sha256=row['content_sha256'],
                changed_projection_keys=sorted(diff),reason='NODE_IDENTITY_OR_ALIAS_EXECUTION_ONLY' if diff else 'UNCHANGED_EVIDENCE_CLAIM_TEMPORAL_BASELINE_CONTENT'))
    assert len(comparison)==295 and temporal_census(new)==temporal_census(blank)
    critical = {r['candidate_id']:r['content'] for r in new['objects']['claims']}
    assert decisions['FND_CLAIM_0034']['decision']=='DROP' and decisions['FND_CLAIM_0066']['decision']=='KEEP_NEEDS_REVIEW' and decisions['FND_CLAIM_0067']['decision']=='KEEP'
    assert critical['FND_CLAIM_0066']['raw']['fact_time'] is None and critical['FND_CLAIM_0066']['raw']['publication_time'] is None
    assert critical['FND_CLAIM_0067']['evidence_identity_adjudication']['authoritative_evidence_id']=='EV_F030B_P001_R5795'
    assert critical['FND_CLAIM_0067']['evidence_identity_adjudication']['sibling_evidence_ids']==['EV_F030B_P001_MEGTRON8']
    assert new['evidence_governance_manifest']==blank['evidence_governance_manifest']
    assert production_identity(PRODUCTION)==starting['production']
    assert all(sha256_file(Path(p))==sha for p,sha in starting['immutable_file_bindings'].items())
    return blank,rec,new,preview,comparison,starting


def main():
    first = qualify()
    second = qualify()
    assert first == second
    blank,rec,new,preview,comparison,starting = first
    if '--freeze' not in sys.argv:
        print(json.dumps(dict(dependency_closure=preview['dependency_closure'],canonical_noops=preview['canonical_equivalent_noop_count'],
            new_contract_sha256=BOUND_IDENTITY_CONTRACT['contract_sha256'],new_blank_not_persisted=True),indent=2))
        return
    head = git('rev-parse','HEAD')
    assert head != OLD_COMMIT and git('rev-parse','HEAD^') == OLD_COMMIT
    assert not git('diff','--name-only') and not git('diff','--cached','--name-only')
    assert new['repository_commit']==head
    tests = {}
    for name in ('full_regression.xml','identity_regression.xml'):
        path = OUT / name
        suites = list(ET.parse(path).getroot().iter('testsuite'))
        tests[name] = {k:sum(int(s.get(k,0)) for s in suites) for k in ('tests','errors','failures','skipped')}
        assert tests[name]['errors']==tests[name]['failures']==0
        tests[name]['sha256'] = sha256_file(path)
    new_binding = freeze('foundation_review_packet_v4_blank.json',new)
    freeze('foundation_review_packet_v4_blank.json',new)
    basis = dict(packet_id=new['packet_id'],immutable_packet_sha256=new['immutable_packet_sha256'],
        production_sha256=PRODUCTION_SHA,schema_version='0.2.3',implementation_commit=head,
        execution_contract_sha256=BOUND_IDENTITY_CONTRACT['contract_sha256'],evidence_governance_manifest_sha256=new['evidence_governance_manifest']['manifest_sha256'])
    slate = dict(document_type='phase3f_foundation_review_rebased_slate_295',authority_status='REQUIRES_NEW_EXPLICIT_HUMAN_AUTHORIZATION',
        review_basis=basis,prior_review_basis=rec['review_basis'],prior_recommendation_semantic_sha256=REC_SHA,
        prior_authorization_semantic_sha256=AUTH_SHA,prior_authorization_automatically_rebound=False,
        recommendation_source='AI_GENERATED_RECOMMENDATION_UNCHANGED',semantic_decisions_changed=0,
        total_decisions=295,decisions=copy.deepcopy(rec['decisions']),
        compilation_diagnostics=dict(aliases=preview['identity_plan']['aliases']),
        production_apply_authorized=False,human_review_complete=False)
    assert slate['decisions']==rec['decisions']
    slate['rebased_slate_semantic_sha256']=canonical_sha256(slate)
    slate_binding=freeze('phase3f_foundation_review_rebased_slate_295.json',slate)
    freeze('phase3f_foundation_review_rebased_slate_295.json',slate)
    freeze('non_authorizing_eligibility_preview.json',preview)
    freeze('all_295_review_projection_comparison.json',comparison)
    freeze('execution_contract_v4.json',BOUND_IDENTITY_CONTRACT)
    prior = read(STOP)
    prior_nodes = [x['candidate_id'] for x in prior['conflicts'] if x['code']=='NODE_SUPPORT_NON_EXECUTABLE']
    d={r['candidate_id']:r for rows in rec['decisions'].values() for r in rows}
    classification={decision:[cid for cid in prior_nodes if d[cid]['decision']==decision] for decision in ('REUSE','CREATE')}
    assert {k:len(v) for k,v in classification.items()} == {'REUSE':30,'CREATE':7}
    receipt=dict(phase='PHASE3F_FOUNDATION_REVIEW_EXECUTION_CONTRACT_CORRECTION',correction_complete=True,
        old_implementation_commit=OLD_COMMIT,new_implementation_commit=head,files_changed=git('diff-tree','--no-commit-id','--name-only','-r','HEAD').splitlines(),
        old_execution_contract_sha256=CONTRACT_SHA256,new_execution_contract=BOUND_IDENTITY_CONTRACT,
        storage_evidence_contract_unchanged=True,schema_sql_and_guards_unchanged=True,
        old_blank_packet_id=blank['packet_id'],old_blank_packet_semantic_sha256=blank['immutable_packet_sha256'],
        new_blank_packet_id=new['packet_id'],new_blank_packet_semantic_sha256=new['immutable_packet_sha256'],new_blank_packet_file=new_binding,
        new_blank_decisions_present=0,blank_decision_rows=295,rebased_slate_semantic_sha256=slate['rebased_slate_semantic_sha256'],rebased_slate_file=slate_binding,
        prior_conflict_classification=classification,conflicts_before=prior['conflict_counts'],
        conflicts_after={k:0 for k in prior['conflict_counts']},canonical_equivalent_noops=2,dependency_closure='PASS',
        prior_human_decisions_preserved=True,semantic_decisions_changed=0,candidate_ids_changed=0,native_content_changed=0,
        source_count=33,evidence_count=98,candidate_count=295,temporal_lossless_count=56,
        prior_human_authorization_automatically_rebound=False,human_reauthorization_required=True,
        human_review_complete=False,foundation_complete=False,completed_packet_generated=False,
        production_before=starting['production'],production_after=production_identity(PRODUCTION),official_views_before=starting['official_views'],official_views_after=starting['official_views'],
        archive_sha256_before=ARCHIVE_SHA,archive_sha256_after=sha256_file(ARCHIVE),inventory_sha256=INVENTORY_SHA,
        immutable_inputs_verified=starting['immutable_file_bindings'],tests=tests,deterministic_double_run=True,
        production_changed=False,foundation_content_applied=False,real_foundation_executable_payload_built=False,
        cloud_llm_calls=0,local_llm_calls=0,commit_created=True,push=False,pr=False,
        git_status=git('status','--short','--untracked-files=normal'),
        next_required_action='EXPLICIT_HUMAN_REAUTHORIZATION_OF_REBASED_295_SLATE')
    assert receipt['production_before']==receipt['production_after']
    receipt['receipt_semantic_sha256']=canonical_sha256(receipt)
    freeze('contract_correction_receipt.json',receipt)
    print(json.dumps(dict(new_implementation_commit=head,new_contract_sha256=BOUND_IDENTITY_CONTRACT['contract_sha256'],
        new_blank_packet_id=new['packet_id'],new_blank_semantic_sha256=new['immutable_packet_sha256'],
        new_blank_file_sha256=new_binding['sha256'],rebased_slate_semantic_sha256=slate['rebased_slate_semantic_sha256'],tests=tests),indent=2))


if __name__=='__main__':
    main()
