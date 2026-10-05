"""Generate immutable bounded history using the exact pre-whole-piece baseline."""
from io import BytesIO
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile

from pro_a.workbench.config import WorkbenchConfig
from pro_a.workbench.cloud_jobs import CloudProfile
from pro_a.workbench.source_operations import SourceOperations, SourceProfile

BASELINE = '6e1135c4371a6a3d1b6a491a433576b3eda9efbe'
SEED = r'''
import json,sys,requests,socket,os
from dataclasses import asdict
from pathlib import Path
from unittest.mock import patch
from series_binding_helpers import case,providers,start,advance,finish,Transport
def forbidden(*a,**k):raise AssertionError('NETWORK_FORBIDDEN')
requests.sessions.Session.request=forbidden
connect=socket.socket.connect
def local_only(sock,address):
 if isinstance(address,tuple) and address[0] in ('127.0.0.1','::1'):return connect(sock,address)
 forbidden()
socket.socket.connect=local_only
root,state=Path(sys.argv[1]),sys.argv[2]
value=case(root)
class Patch:
 def setenv(self,key,value):os.environ[key]=value
mode={'subdivided':'truncated','failed':'malformed','unknown':'unknown'}.get(state)
provider,transport=providers(value,Patch(),Transport(mode=mode))
source,run_id=start(value,root)
advance(value,run_id,provider)
if state=='complete':finish(value,run_id,provider)
elif state!='planned':advance(value,run_id,provider)
result={'config':asdict(value['config']),'source':source,'run_id':run_id,
        'phase4_config':str(value['phase4_config']),'calls':len(transport.calls)}
(root/'history.json').write_text(json.dumps(result,default=str),encoding='utf-8')
'''


def historical_bounded_case(root, state):
    checkout = Path(__file__).resolve().parents[1]
    runtime = root / 'bounded-runtime'
    runtime.mkdir(parents=True)
    archive = subprocess.check_output(['git', 'archive', BASELINE, 'src/pro_a', 'tests', 'pyproject.toml'], cwd=checkout)
    with tarfile.open(fileobj=BytesIO(archive)) as tar:
        tar.extractall(runtime, filter='data')
    common = subprocess.check_output(['git', 'rev-parse', '--path-format=absolute', '--git-common-dir'],
                                    cwd=checkout, text=True, encoding='utf-8').strip()
    subprocess.run(['git', 'init', '--quiet', str(runtime)], check=True, capture_output=True)
    (runtime / '.git/objects/info/alternates').write_bytes(((Path(common) / 'objects').as_posix() + '\n').encode())
    subprocess.run(['git', 'update-ref', 'HEAD', BASELINE], cwd=runtime, check=True, capture_output=True)
    subprocess.run(['git', 'read-tree', BASELINE], cwd=runtime, check=True, capture_output=True)
    data = root / 'history'
    data.mkdir()
    environment = {**os.environ, 'PYTHONPATH': os.pathsep.join((str(runtime/'src'), str(runtime/'tests'))),
                   'PYTHONDONTWRITEBYTECODE': '1'}
    seeded = subprocess.run([sys.executable, '-c', SEED, str(data), state], cwd=runtime, env=environment,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    assert seeded.returncode == 0, seeded.stderr.decode('utf-8', errors='replace')
    value = json.loads((data/'history.json').read_text(encoding='utf-8'))
    cfg = value['config']
    for name in ('knowledge_db', 'state_db', 'artifact_root'):
        cfg[name] = Path(cfg[name])
    value['config'] = WorkbenchConfig(**cfg)
    value['phase4_config'] = Path(value['phase4_config'])
    value['source_profile'] = SourceProfile(value['phase4_config'])
    value['cloud_profile'] = CloudProfile.demo()
    value['service'] = SourceOperations(value['config'], value['source_profile'], value['cloud_profile'])
    return value
