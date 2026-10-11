"""Read-only architecture probes; no Workbench or provider execution."""
import sqlite3

import pytest

from pro_a.bounded_extraction import (BoundedExtractionError, SegmentCallAccounting,
    account_series_calls, subdivide_extraction_plan, SeriesBudget, SEGMENT_OUTPUT_CEILING)
from pro_a.workbench.bounded_extraction_persistence import _schema
from test_bounded_extraction import fixture


def test_schema12_attempts_require_real_extraction_segment():
    with sqlite3.connect(':memory:') as connection:
        _schema(connection)
        columns = {r[1]: r for r in connection.execute('PRAGMA table_info(bounded_extraction_attempts)')}
        assert columns['segment_id'][3] == 1  # NOT NULL
        foreign = list(connection.execute('PRAGMA foreign_key_list(bounded_extraction_attempts)'))
        assert any(row[2:5] == ('bounded_extraction_segments', 'segment_id', 'segment_id') for row in foreign)
        # Events are Series-scoped and extensible; absence of a dedicated table
        # alone does NOT prove schema13 is mandatory.
        events = {r[1] for r in connection.execute('PRAGMA table_info(bounded_extraction_events)')}
        assert {'series_id', 'event_type', 'body_json', 'event_sha256'} <= events
        assert 'segment_id' not in events


def test_current_accounting_rejects_non_segment_resolver_identity():
    _, _, series, plan = fixture(16)
    resolver = SegmentCallAccounting('CONTEXT_RESOLUTION', 'ATTEMPT_CTX', None,
        None, None, None, None, None, None, None, 'UNKNOWN')
    with pytest.raises(BoundedExtractionError, match='INVALID_CALL_IDENTITY'):
        account_series_calls(series, plan, (resolver,))


def test_actual_full_tree_plus_one_resolver_fits_unchanged_budget():
    _, _, series, plan = fixture(16)
    while any(len(s.assigned_evidence_refs) > 1 for s in plan.leaves):
        segment = next(s for s in plan.leaves if len(s.assigned_evidence_refs) > 1)
        plan = subdivide_extraction_plan(series, plan, segment.segment_id)
    assert len(plan.leaves) == 16 and len(plan.segments) == 31
    assert max(s.subdivision_depth for s in plan.segments) == 4
    assert 1 + len(plan.segments) == SeriesBudget().max_provider_calls == 32
    assert (1 + len(plan.segments)) * SEGMENT_OUTPUT_CEILING == SeriesBudget().max_cumulative_output_tokens == 384000
    # This is arithmetic feasibility, not a claim that current accounting
    # supports the additional operation (the preceding test proves it does not).
    for root_count in range(1, 17):
        assert 1 + (2 * 16 - root_count) <= 32
