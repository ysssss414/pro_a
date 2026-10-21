"""Server metadata stays immutable when local B1 qualification rejects a response."""
import pytest

from pro_a import output_decomposition as output
from test_b1_formal_contract import integration_fixture, AssignedTransport, entry, rows, offline


@pytest.mark.parametrize('reason', ['budget', 'model'])
def test_known_response_rejection_preserves_finish_usage_raw_and_zero_acceptance(tmp_path, monkeypatch, reason):
    value, run, _ = integration_fixture(tmp_path, monkeypatch)
    service, rid = value['service'], run['processing_run_id']
    before = value['config'].knowledge_db.read_bytes()
    run = entry.advance(service, rid, worker_id='response-test-worker')
    worker = entry.frozen_worker(service, rid)
    _, _, catalog, series = worker.output_batches.inputs(run)[0]
    segment = worker.output_batches.ledger.read(series.series_id)[1].leaves[0]
    class Drift(AssignedTransport):
        def __call__(self, *args, **kwargs):
            response = super().__call__(*args, **kwargs)
            if reason == 'budget':
                response.value['usage'].update(prompt_tokens=14001, total_tokens=14051)
            else:
                response.value['model'] = 'UNQUALIFIED_MODEL'
            return response
    transport = Drift(); transport.catalog, transport.segment = catalog, segment
    providers = entry.providers(service, rid); providers[output.OPERATION].transport = transport
    result = entry.advance(service, rid, worker_id='response-test-worker', provider=providers)
    assert result['state'] == 'BLOCKED' and len(transport.calls) == 1
    outcome = rows(value, 'bounded_extraction_outcomes')[0]
    assert outcome['external_outcome'] == 'SUCCEEDED' and outcome['finish_reason'] == 'tool_calls'
    assert outcome['classification'] == ('B1_BUDGET_VIOLATION' if reason == 'budget' else 'B1_MODEL_IDENTITY_DRIFT')
    assert outcome['input_tokens'] == (14001 if reason == 'budget' else 100)
    assert rows(value, 'bounded_extraction_segment_results') == []
    assert worker.output_batches.ledger._path(series.series_id, outcome['attempt_id'] + '.raw.json').exists()
    assert entry.advance(service, rid, worker_id='response-test-worker', provider=providers) is None
    assert len(transport.calls) == 1 and value['config'].knowledge_db.read_bytes() == before
