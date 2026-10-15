"""Actual Windows MIC probe on disposable files; no production configuration."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import pytest

from pro_a.process_boundary import launch


@pytest.mark.skipif(os.name != 'nt', reason='P2 initial deployment uses Windows MIC')
def test_low_child_can_write_only_provisioned_state(tmp_path):
    state = tmp_path / 'state'; state.mkdir()
    canonical = tmp_path / 'canonical.db'; canonical.write_bytes(b'protected fixture')
    user = subprocess.check_output(['whoami'], text=True).strip()
    subprocess.run(['icacls', str(state), '/grant', user + ':(OI)(CI)F'], check=True, capture_output=True)
    subprocess.run(['icacls', str(state), '/setintegritylevel', '(OI)(CI)L'], check=True, capture_output=True)
    source = str(Path(__file__).resolve().parents[1] / 'src')
    script = """import json,sys
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,sys.argv[1])
from pro_a.process_boundary import require_readonly_boundary,integrity_level
target=Path(sys.argv[2]);out=Path(sys.argv[3])
proof=require_readonly_boundary(SimpleNamespace(knowledge_db=target))
try:
    target.open('r+b').close()
    raise AssertionError('WRITABLE_CANONICAL')
except PermissionError: pass
try:
    target.unlink()
    raise AssertionError('DELETABLE_CANONICAL')
except PermissionError: pass
out.write_text(json.dumps(proof))
"""
    result = state / 'result.json'
    launch([sys.executable, '-B', '-c', script, source, str(canonical), str(result)])
    for _ in range(100):
        if result.exists(): break
        time.sleep(.1)
    assert json.loads(result.read_text()) == {'scheme': 'WINDOWS_MANDATORY_INTEGRITY', 'web_integrity': 4096}
    assert canonical.read_bytes() == b'protected fixture'


def test_admission_http_shape_cannot_supply_actor_or_session():
    from pydantic import ValidationError
    from pro_a.workbench.api import AdmissionApproval
    body = {'proposal_id': 'ADMISSION_' + 'a' * 64, 'confirm': True}
    assert AdmissionApproval(**body).model_dump() == body
    for extra in ({'actor': 'operator'}, {'session_id': 'forged'}, {'principal_type': 'HUMAN_USER'}, {'confirm': 1}):
        with pytest.raises(ValidationError): AdmissionApproval(**{**body, **extra})
