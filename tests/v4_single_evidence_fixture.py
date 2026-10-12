"""Synthetic v4 failure produced by an actual interpreter, including old Stable."""
from dataclasses import asdict
import json
from pathlib import Path
import sys

from pro_a import output_decomposition as output
if __name__ == '__main__':
    # Test libraries only; pro_a remains the actual old installed package.
    sys.path.append(sys.argv[3])
from series_binding_helpers import Transport, rows, synthetic_providers
import test_cloud_operation_adapter_binding as base


class SingleSelectorTransport(Transport):
    def __init__(self, fail_on=(1,), *, errors=1):
        super().__init__()
        self.fail_on, self.errors = fail_on, errors

    def __call__(self, *a, **k):
        response = super().__call__(*a, **k)
        if len(self.calls) in self.fail_on:
            function = response.value['choices'][0]['message']['tool_calls'][0]['function']
            record = json.loads(function['arguments'])
            for index in range(7, 7 + self.errors):
                record['claims'][index]['evidence'].update(selection_mode='RAW_SUBSPAN',
                    selector='ABSENT_SYNTHETIC_SELECTOR', occurrence='1')
            function['arguments'] = json.dumps(record)
        return response


def synthetic_case(root, monkeypatch):
    import pymupdf
    root.mkdir(parents=True, exist_ok=True)
    path = root/'synthetic-v4.pdf'
    doc = pymupdf.open()
    page = doc.new_page(width=900, height=1400)
    text = '\n'.join(f'Synthetic Company product {i:03d} has capacity {i+1} units.' for i in range(51))
    page.insert_text((30,30),text,fontsize=10)
    doc.save(path); doc.close()
    monkeypatch.setattr(base,'clean_pdf',lambda *a, **k:path)
    value = base.setup_run(root,monkeypatch)
    bindings = value['service'].output_batches.inputs(value['service'].get_run(value['run_id']))
    assert len(bindings) == 1
    _, plan, _, _ = value['service'].output_batches.ledger.read(bindings[0][3].series_id)
    assert len(plan.leaves) == 4 and bindings[0][3].series_version == output.contract()['series']
    return value


def fail_once(value):
    transport = SingleSelectorTransport()
    with synthetic_providers(value,transport) as providers:
        result = value['service'].resume_bounded_extraction_only(value['run_id'],worker_id='synthetic-failure',
            idempotency_key='synthetic-first-failure',max_new_calls=4,provider=providers)
    assert result['run']['state'] == 'BLOCKED' and len(transport.calls) == 1
    return rows(value,'bounded_extraction_attempts')[0]


if __name__ == '__main__':
    import pytest
    root = Path(sys.argv[1]).resolve()
    assert root.name.startswith('synthetic-'), 'SYNTHETIC_DIRECTORY_REQUIRED'
    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr('requests.sessions.Session.request',lambda *a, **k: (_ for _ in ()).throw(AssertionError('REAL_NETWORK_FORBIDDEN')))
        value = synthetic_case(root,monkeypatch)
        attempt = fail_once(value)
        runtime = value['service'].get_run(value['run_id'])['runtime_identity']
        assert runtime['git_sha'] == sys.argv[2], 'EXACT_RELEASE_IDENTITY_REQUIRED'
        (root/'fixture.json').write_text(json.dumps({'config':asdict(value['config']),
            'run_id':value['run_id'],'failed_attempt_id':attempt['attempt_id'],
            'historical_runtime':runtime},default=str),encoding='utf-8')
    print(json.dumps({'fixture':'SYNTHETIC_ONLY','runtime':runtime['git_sha'],'segments':4,'fake_calls':1}))
