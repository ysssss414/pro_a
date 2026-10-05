"""Historical bounded execution is readable but cannot enter the new binding."""
import pytest

from historical_bounded_fixture import BASELINE, historical_bounded_case
from pro_a.workbench.source_operations import SourceOperationError
from test_mcp_bounded_reads import snapshot
from test_phase43_stage6_lifecycle import _schema11
from test_workbench_stage7 import clean_pdf, upload
from series_binding_helpers import rows


def test_schema11_new_run_fails_without_mutation(tmp_path):
    value, _ = _schema11(tmp_path)
    source = upload(value, clean_pdf(tmp_path))
    before = value['config'].state_db.read_bytes()
    with pytest.raises(SourceOperationError, match='BOUNDED_SCHEMA_REQUIRED'):
        value['service'].start(source['source_id'], idempotency_key='schema11-must-fail-0001')
    assert value['config'].state_db.read_bytes() == before
    assert not rows(value, 'source_processing_runs')


@pytest.mark.parametrize('state', ['planned', 'partial', 'subdivided'])
def test_historical_bounded_binding_rejects_new_execution_without_mutation(tmp_path, monkeypatch, state):
    value = historical_bounded_case(tmp_path, state)
    service, run_id = value['service'], value['run_id']
    run = service.get_run(run_id)
    assert run['runtime_identity'].get('bounded_source_analysis')
    before = snapshot(value['config'])
    monkeypatch.setattr('requests.post', lambda *a, **k: pytest.fail('PROVIDER_FORBIDDEN'))
    with pytest.raises(SourceOperationError, match='HISTORICAL_EXTRACTION_RUNTIME_INCOMPATIBLE'):
        service._advance_claimed(run_id, None, 'synthetic-historical-guard')
    assert service.get_run(run_id) == run
    assert snapshot(value['config']) == before


def test_whole_piece_cloud_surface_is_incompatible_with_bounded_baseline():
    from pro_a.workbench.retry_compatibility import _execution_surface_comparison
    result = _execution_surface_comparison('cloud', BASELINE)
    assert result['compatible'] is False
