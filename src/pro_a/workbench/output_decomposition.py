"""Schema12 Series runner for full-context output batches; no new call ledger."""
from functools import partial
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

    def __init__(self, service, *, binding_version=None):
        super().__init__(service)
        self.binding_version = binding_version or contract.BINDING_VERSION
        self.provider_version = contract.contract(binding_version=self.binding_version)['provider_version']
        self.piece_input = partial(contract.piece_input, binding_version=self.binding_version)
        if self.binding_version == contract.b1.BINDING:
            frozen = service.jobs.current_runtime()['b1_request_settings']['context']
            self.piece_input = partial(contract.piece_input, binding_version=self.binding_version,
                                       b1_request_context=frozen, b1_counter_version=service.jobs.current_runtime()['b1_request_settings'].get('counter_version'))

    def inputs(self, run):
        bindings = super().inputs(run)
        frozen = run['runtime_identity']['whole_piece_output_decomposition']
        if any(contract.contract(binding_version=value['binding_version'], counter_version=value.get('b1_counter_version', contract.b1.COUNTER)) != frozen
               for value, _, _, _ in bindings):
            raise ValueError('OUTPUT_RUN_BINDING_MISMATCH')
        if frozen['binding_version'] == contract.b1.BINDING:
            expected = run['runtime_identity']['b1_request_settings']['context']
            if len(bindings) != 1 or bindings[0][0].get('b1_request_context') != expected:
                raise ValueError('B1_CONTEXT_RUNTIME_MISMATCH')
            scope = run['runtime_identity']['b1_request_settings'].get('source_scope')
            if bindings[0][0]['native'].get('source_scope') != scope:
                raise ValueError('B1_SCOPE_RUNTIME_MISMATCH')
        return bindings

    def projection(self, connection, run_id):
        result = BoundedSourceAnalysisRunner.projection(self, connection, run_id)
        rows = list(connection.execute('SELECT series_id FROM bounded_extraction_series WHERE processing_run_id=?', (run_id,)))
        roots = subdivisions = accepted = truncated = dispatched = unknown = 0
        b1_scope = False
        for row in rows:
            series, plan, _, _ = self.ledger.read(row['series_id'])
            b1_scope = b1_scope or series.series_version == contract.b1.SERIES
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
        if b1_scope:
            result['assigned_coverage_status'] = result['coverage_status']
            result['coverage_scope'] = 'B1_FROZEN_ASSIGNED_ONLY'
            result['source_coverage_status'] = 'NOT_ESTABLISHED'
            if result['coverage_status'] == 'COMPLETE':
                result['coverage_status'] = 'PARTIAL'
        return result
