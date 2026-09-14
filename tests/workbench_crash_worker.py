"""Synthetic subprocess crash probe, used only by Stage 1 acceptance tests."""
import json
import os
from pathlib import Path
import sys

from pro_a.workbench.config import WorkbenchConfig
from pro_a.workbench.review_workbench import ReviewWorkbench

payload = json.loads(Path(sys.argv[1]).read_text())
raw = payload['config']
for key in ('knowledge_db', 'state_db', 'artifact_root'):
    raw[key] = Path(raw[key])
service = ReviewWorkbench(WorkbenchConfig(**raw))
publish = service._publish

def crash_after_publish(connection, handle, kind, value):
    result = publish(connection, handle, kind, value)
    if kind == payload['crash_after']:
        os._exit(73)
    return result

service._publish = crash_after_publish
service.mutate(payload['handle'], 'seal', payload['request'], payload['identity'])
raise RuntimeError('Crash probe did not reach the intended publication point')
