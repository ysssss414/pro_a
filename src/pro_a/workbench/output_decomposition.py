"""Schema12 Series runner for full-context output batches; no new call ledger."""
from pro_a import output_decomposition as contract
from .bounded_source_analysis import BoundedSourceAnalysisRunner


class OutputDecompositionRunner(BoundedSourceAnalysisRunner):
    binding_version = contract.BINDING_VERSION
    provider_version = contract.PROVIDER_VERSION
    operation = contract.OPERATION
    provider_type = contract.OutputBatchProvider
    mode = contract.MODE
    piece_input = staticmethod(contract.piece_input)
    restore_input = staticmethod(contract.restore_input)
    segment_payload = staticmethod(contract.segment_payload)

    def projection(self, connection, run_id):
        result = BoundedSourceAnalysisRunner.projection(self, connection, run_id)
        rows = list(connection.execute('SELECT series_id FROM bounded_extraction_series WHERE processing_run_id=?', (run_id,)))
        roots = subdivisions = accepted = truncated = dispatched = unknown = 0
        for row in rows:
            _, plan, _, _ = self.ledger.read(row['series_id'])
            roots += sum(s.parent_segment_id is None for s in plan.segments)
            subdivisions += len(plan.superseded_segment_ids)
            accepted += connection.execute("SELECT count(*) FROM bounded_extraction_segments WHERE series_id=? AND state='SUCCEEDED_COMPLETE'", (row['series_id'],)).fetchone()[0]
            truncated += connection.execute("SELECT count(*) FROM bounded_extraction_outcomes o JOIN bounded_extraction_attempts a ON a.attempt_id=o.attempt_id JOIN bounded_extraction_segments s ON s.segment_id=a.segment_id WHERE s.series_id=? AND o.external_outcome='TRUNCATED'", (row['series_id'],)).fetchone()[0]
            calls = connection.execute("SELECT o.external_outcome FROM bounded_extraction_dispatches d JOIN bounded_extraction_attempts a ON a.attempt_id=d.attempt_id JOIN bounded_extraction_segments s ON s.segment_id=a.segment_id LEFT JOIN bounded_extraction_outcomes o ON o.attempt_id=a.attempt_id WHERE s.series_id=?", (row['series_id'],)).fetchall()
            dispatched += len(calls)
            unknown += sum(call['external_outcome'] in (None, 'UNKNOWN') for call in calls)
        result.update(extraction_execution_mode=contract.MODE, initial_output_batch_count=roots,
            output_batch_count=roots + 2 * subdivisions, subdivision_count=subdivisions,
            accepted_leaf_calls=accepted, truncated_parent_calls=truncated,
            reserved_attempt_count=result['provider_segment_attempt_count'],
            provider_call_count=dispatched, confirmed_provider_call_count=dispatched-unknown,
            unknown_outcome_call_count=unknown)
        return result
