"""Bounded run projections retain ledger validation without write authority."""
import hashlib

import pytest

from pro_a.mcp.errors import BridgeError
from pro_a.mcp.service import ReadService
from pro_a.workbench.bounded_extraction_store import BoundedExtractionStore
from pro_a.workbench.bounded_source_analysis import BoundedSourceAnalysisRunner
from pro_a.workbench.source_operations import SourceOperations
from pro_a.workbench.store import Store
from series_binding_helpers import case, providers, start, advance, finish, Transport


def snapshot(config):
    paths = [config.state_db, config.knowledge_db, *config.artifact_root.rglob('*')]
    return {str(path): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in paths if path.is_file()}


def forbidden(*args, **kwargs):
    raise AssertionError('WRITE_OR_PROVIDER_DURING_MCP_READ')


@pytest.mark.parametrize('state', ['planned', 'partial', 'subdivided', 'complete', 'failed', 'unknown'])
def test_bounded_projection_matches_native_without_actions(tmp_path, monkeypatch, state):
    value = case(tmp_path)
    mode = {'subdivided': 'truncated', 'failed': 'malformed', 'unknown': 'unknown'}.get(state)
    provider, transport = providers(value, monkeypatch, Transport(mode=mode))
    source, run_id = start(value, tmp_path)
    advance(value, run_id, provider)
    if state == 'complete':
        finish(value, run_id, provider)
    elif state != 'planned':
        advance(value, run_id, provider)
    expected = value['service'].get_run(run_id)
    before = snapshot(value['config'])
    calls = len(transport.calls)
    connect = Store.connect

    def readonly(store, *, operator_write=False):
        assert operator_write is False
        return connect(store)

    monkeypatch.setattr(Store, 'connect', readonly)
    for cls in (SourceOperations, BoundedSourceAnalysisRunner, BoundedExtractionStore):
        monkeypatch.setattr(cls, '__init__', forbidden)
    monkeypatch.setattr('requests.post', forbidden)
    monkeypatch.setattr(SourceOperations, 'advance_once', forbidden)
    monkeypatch.setattr(BoundedExtractionStore, 'reserve_attempt', forbidden)
    bridge = ReadService(value['config'])
    assert bridge.operations.get_run(run_id) == expected
    projected = bridge.get_processing_run(run_id)
    assert projected == bridge._run_projection(expected)
    assert bridge.get_source(source['source_id']).latest_run == projected
    assert snapshot(value['config']) == before
    assert len(transport.calls) == calls
    bounded = bridge.operations.bounded
    for obj in (bounded, bounded.ledger, bounded.ledger.store):
        assert type(obj).__bases__ == (object,)
        for method in ('start', 'advance', 'create', 'finalize', 'reserve_attempt', 'recover_attempt'):
            assert not hasattr(obj, method)
    with pytest.raises(TypeError):
        bounded.ledger.store.connect(operator_write=True)


@pytest.mark.parametrize('tamper', ['event', 'artifact'])
def test_bounded_read_rejects_tampering_without_repair(tmp_path, monkeypatch, tamper):
    value = case(tmp_path)
    provider, _ = providers(value, monkeypatch)
    source, run_id = start(value, tmp_path)
    advance(value, run_id, provider)
    advance(value, run_id, provider)
    if tamper == 'event':
        with Store(value['config']).connect(operator_write=True) as connection:
            # Corrupt the disposable fixture after removing its append-only trigger.
            triggers = connection.execute("SELECT name FROM sqlite_master WHERE type='trigger' AND tbl_name='bounded_extraction_events'").fetchall()
            for row in triggers:
                connection.execute('DROP TRIGGER "' + row[0] + '"')
            connection.execute("UPDATE bounded_extraction_events SET event_sha256=? WHERE sequence=1", ('0' * 64,))
    else:
        path = next(value['config'].artifact_root.glob('bounded-extraction/*/*.raw.json'))
        path.write_bytes(b'corrupt synthetic outcome')
    before = snapshot(value['config'])
    bridge = ReadService(value['config'])
    for read, key in ((bridge.get_processing_run, run_id), (bridge.get_source, source['source_id'])):
        with pytest.raises(BridgeError, match='READ_BOUNDARY_VIOLATION'):
            read(key)
    assert snapshot(value['config']) == before
