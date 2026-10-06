"""Overflow transaction guards and recovery use disposable schema12 only."""
import json

import pytest

from pro_a.workbench import bounded_extraction_persistence as migration
from pro_a.workbench.bounded_extraction_store import BoundedExtractionStore
from pro_a.workbench.config import BoundaryError
from pro_a.workbench.store import Store
from test_bounded_extraction_persistence import setup, no_network, reserve, complete


def truncated(ledger,segment):
    fence,aid=reserve(ledger,segment)
    ledger.record_dispatch(aid,'worker',fence)
    ledger.record_outcome(aid,'worker',fence,b'{"wire":',http_status=200,
                          finish_reason='length',output_tokens=12000,latency_ms=17.5)
    return fence,aid


@pytest.mark.parametrize('window',['subdivision_child_inserted','subdivision_parent_superseded','subdivision_committed'])
def test_overflow_atomic_crash_and_idempotency(setup,monkeypatch,window):
    config,ledger,ctx,catalog,series,plan=setup
    parent=plan.leaves[0]
    fence,aid=truncated(ledger,parent)
    def crash(name):
        if name==window:
            raise RuntimeError('SYNTHETIC_CRASH')
    monkeypatch.setattr(migration,'checkpoint',crash)
    with pytest.raises(RuntimeError,match='SYNTHETIC_CRASH'):
        ledger.subdivide_after_truncation(parent.segment_id,'worker',fence,expected_frontier_version=0)
    monkeypatch.setattr(migration,'checkpoint',lambda name:None)
    fresh=BoundedExtractionStore(config)
    assert fresh.read(series.series_id)[2]['frontier_version']==int(window=='subdivision_committed')
    children=fresh.subdivide_after_truncation(parent.segment_id,'worker',fence,expected_frontier_version=0)
    assert len(children)==2
    assert fresh.subdivide_after_truncation(parent.segment_id,'worker',fence,expected_frontier_version=0)==children
    assert fresh.read(series.series_id)[3].output_tokens==12000
    with Store(config).connect() as c:
        assert c.execute('SELECT COUNT(*) FROM bounded_extraction_segment_results').fetchone()[0]==0
        events=list(c.execute("SELECT body_json FROM bounded_extraction_events WHERE event_type='SEGMENT_OVERFLOW_SUBDIVIDED'"))
        assert len(events)==1 and json.loads(events[0][0])['attempt_id']==aid


@pytest.mark.parametrize('invalid',['undispatched','wrong_finish','accepted','stale_frontier','stale_fence','raw_tamper'])
def test_overflow_requires_durable_capacity_evidence(setup,invalid):
    config,ledger,ctx,catalog,series,plan=setup
    parent=plan.leaves[0]
    if invalid=='accepted':
        fence,aid,_=complete(ledger,ctx,catalog,series,parent)
    elif invalid=='undispatched':
        fence,aid=reserve(ledger,parent)
    elif invalid=='wrong_finish':
        fence,aid=reserve(ledger,parent)
        ledger.record_dispatch(aid,'worker',fence)
        ledger.record_outcome(aid,'worker',fence,b'{',http_status=200,finish_reason='stop')
    else:
        fence,aid=truncated(ledger,parent)
    if invalid=='raw_tamper':
        path=ledger._path(series.series_id,aid+'.raw.json')
        path.write_bytes(path.read_bytes()+b' ')
    with pytest.raises(BoundaryError):
        ledger.subdivide_after_truncation(parent.segment_id,'worker',fence+int(invalid=='stale_fence'),
                                          expected_frontier_version=int(invalid=='stale_frontier'))
    with Store(config).connect() as c:
        assert c.execute('SELECT COUNT(*) FROM bounded_extraction_segments').fetchone()[0]==1
        assert c.execute('SELECT frontier_version FROM bounded_extraction_series').fetchone()[0]==0


def test_active_runtime_closure_and_historical_surfaces():
    from pro_a.workbench.cloud_jobs import runtime_identity
    from pro_a.workbench.retry_compatibility import _execution_surface_comparison, _CLOUD_EXECUTION_SURFACE
    from pro_a.output_decomposition import contract
    value=runtime_identity('semantic-backend-adapter-v2',workbench_schema_version='12')
    assert value['whole_piece_output_decomposition']==contract()
    assert 'whole_piece_compact' not in value and 'bounded_source_analysis' not in value
    for name in ('bounded_extraction.py','evidence_binding.py','source_analysis_wire.py',
                 'bounded_source_analysis.py','workbench/bounded_source_analysis.py',
                 'workbench/bounded_extraction_store.py', 'whole_piece_compact.py', 'workbench/whole_piece_raw.py'):
        assert name in _CLOUD_EXECUTION_SURFACE
    for kind in ('cloud','native'):
        result=_execution_surface_comparison(kind,'389399712deb9d2e1cacf41ad39e147e16b5f14b')
        assert not result['compatible'] and result['reason']=='SEMANTIC_SURFACE_CHANGED'
