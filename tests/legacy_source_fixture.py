"""Build synthetic history in the frozen legacy runtime, then open it read-only.

The active bounded runtime never starts a legacy extraction Run. The isolated
baseline subprocess is solely a fixture generator for history/audit regression.
"""
from io import BytesIO
import json
from pathlib import Path
import os
import subprocess
import sys
import tarfile

from pro_a.workbench.config import WorkbenchConfig
from pro_a.workbench.cloud_jobs import CloudProfile
from pro_a.workbench.source_operations import SourceOperations, SourceProfile

BASELINE='389399712deb9d2e1cacf41ad39e147e16b5f14b'

SEED=r'''
from dataclasses import asdict
import json,sys,sqlite3
import requests,socket
def forbidden(*args,**kwargs):raise AssertionError('EXTERNAL_NETWORK_FORBIDDEN')
requests.sessions.Session.request=forbidden
connect=socket.socket.connect
def local_only(sock,address):
 if isinstance(address,tuple) and address[0] in ('127.0.0.1','::1'):return connect(sock,address)
 forbidden()
socket.socket.connect=local_only
from pathlib import Path
from test_phase43_stage6_lifecycle import _schema11
from test_workbench_stage7 import clean_pdf,upload
from pro_a.cloud_contract import DeterministicFakeProvider,ProviderFailure
if sys.argv[3]=='11':
 value,_=_schema11(Path(sys.argv[1]))
 from pro_a.workbench.extraction_retry import prepare_extraction_retries
 prepare_extraction_retries(value['config'])
else:
 from workbench_stage7_fixture import stage7_fixture
 from pro_a.workbench.domains import prepare_domains
 value=stage7_fixture(Path(sys.argv[1]))
 prepare_domains(value['config'])
 if sys.argv[3]=='10':
  from pro_a.workbench.stage1_scale import prepare_stage1_scale
  prepare_stage1_scale(value['config'])
if sys.argv[4]=='1':
 from pro_a.workbench.cloud_jobs import CloudProfile
 from pro_a.workbench.source_operations import SourceOperations
 value['cloud_profile']=CloudProfile('deepseek','deepseek-flash')
 value['service']=SourceOperations(value['config'],value['source_profile'],value['cloud_profile'])
service=value['service']
intent={}
if sys.argv[2]=='review_intent':
 with sqlite3.connect(value['config'].knowledge_db) as c:
  c.execute("INSERT INTO nodes(node_id,canonical_name,primary_type,description,status,created_at,updated_at) VALUES('NODE_PRIVATE_INTENT','Private intent company','Company','','active','2026-01-01','2026-01-01')")
 intent={'company_material_intent':{'target_company_node_id':'NODE_PRIVATE_INTENT','material_kind':'other',
          'source_channel':'user_upload','material_date':None,'operator_title':'Private intent title'}}
source=upload(value,clean_pdf(Path(sys.argv[1])))
run_id=service.start(source['source_id'],idempotency_key='frozen-legacy-fixture-0001',**intent)['run']['processing_run_id']
service.advance_once(worker_id='legacy-fixture',processing_run_id=run_id)
class Failure:
 provider_identity='deepseek' if sys.argv[4]=='1' else 'DETERMINISTIC_FAKE'
 adapter_version='source-analysis-piece-adapter-v2' if sys.argv[4]=='1' else 'deterministic-fake-v1'
 def invoke(self,request):
  raise ProviderFailure('PROVIDER_ERROR',external_outcome='KNOWN_FAILURE',retryable=False,
        diagnostic={'failure_stage':'HTTP_RESPONSE','error_class':'HTTP_503','http_status':503,
                    'provider_request_id':'req-stage72b-503'})
if sys.argv[2] in ('review','review_intent'):
 for _ in range(2):service.advance_once(worker_id='legacy-fixture',processing_run_id=run_id,provider=DeterministicFakeProvider())
elif sys.argv[2]!='queued':service.advance_once(worker_id='legacy-fixture',processing_run_id=run_id,provider=Failure())
if sys.argv[2] in ('lineage','live_retry'):
 with service.store.connect() as c:
  first=c.execute('SELECT attempt_id FROM cloud_attempts').fetchone()[0]
 service.retry_failed_extraction(run_id,first,retry_reason='Explicit synthetic legacy lineage',idempotency_key='legacy-lineage-fixture-0001')
 if sys.argv[2]=='lineage':service.advance_once(worker_id='legacy-fixture',processing_run_id=run_id,provider=Failure())
qualification=None
if sys.argv[2]=='qualified':
 from pro_a.workbench.retry_compatibility import prepare_retry_compatibility,assess_retry_compatibility
 prepare_retry_compatibility(value['config'])
 with service.store.connect() as c:first=c.execute('SELECT attempt_id FROM cloud_attempts').fetchone()[0]
 qualification=assess_retry_compatibility(value['config'],run_id,first,persist=True)
 assert qualification['status']=='QUALIFIED'
with service.store.connect() as c:
 job=dict(c.execute("SELECT * FROM cloud_jobs WHERE operation_kind='SOURCE_ANALYSIS_PIECE'").fetchone())
 attempt=c.execute('SELECT * FROM cloud_attempts WHERE job_id=?',(job['job_id'],)).fetchone()
result={'config':asdict(value['config']),'source':source,'run_id':run_id,'qualification':qualification,
        'job_id':job['job_id'],'attempt_id':attempt['attempt_id'] if attempt else None,
        'phase4_config':str(value['phase4_config'])}
Path(sys.argv[1],'history.json').write_text(json.dumps(result,default=str),encoding='utf-8')
'''


def historical_case(root,state='failed',schema='11',deepseek=False):
    checkout=Path(__file__).resolve().parents[1]
    runtime=root/'legacy-runtime'
    runtime.mkdir(parents=True)
    archive=subprocess.check_output(['git','archive',BASELINE,'src/pro_a'],cwd=checkout)
    with tarfile.open(fileobj=BytesIO(archive)) as tar:
        tar.extractall(runtime,filter='data')
    # Give the archived code its exact historical Git identity without copying or
    # mutating the shared object database; alternates only read baseline objects.
    common=subprocess.check_output(['git','rev-parse','--path-format=absolute','--git-common-dir'],cwd=checkout,text=True,encoding='utf-8').strip()
    subprocess.run(['git','init','--quiet',str(runtime)],check=True,capture_output=True)
    alternates=runtime/'.git/objects/info/alternates'
    alternates.write_bytes(((Path(common)/'objects').as_posix()+'\n').encode('utf-8'))
    subprocess.run(['git','update-ref','HEAD',BASELINE],cwd=runtime,check=True,capture_output=True)
    data_root=root/'historical'
    data_root.mkdir()
    environment={**os.environ,'PYTHONPATH':os.pathsep.join((str(runtime/'src'),str(checkout/'tests'))),
                 'PYTHONDONTWRITEBYTECODE':'1'}
    seeded=subprocess.run([sys.executable,'-c',SEED,str(data_root),state,schema,str(int(deepseek))],cwd=runtime,env=environment,
                          stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    assert seeded.returncode==0,seeded.stderr.decode('utf-8',errors='replace')
    value=json.loads((data_root/'history.json').read_text(encoding='utf-8'))
    config=value['config']
    for key in ('knowledge_db','state_db','artifact_root'):
        config[key]=Path(config[key])
    value['config']=WorkbenchConfig(**config)
    value['phase4_config']=Path(value['phase4_config'])
    value['source_profile']=SourceProfile(value['phase4_config'])
    value['cloud_profile']=CloudProfile.demo()
    value['service']=SourceOperations(value['config'],value['source_profile'],value['cloud_profile'])
    return value
