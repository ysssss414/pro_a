"""Build synthetic immutable history in the actual previous installed release."""
from copy import deepcopy
from dataclasses import asdict
import json
from pathlib import Path
import sys

import pytest

from pro_a.repository_identity import repository_commit
from test_bounded_only_resume import topology, resume
from test_lossless_recovery import qualified, authorize
from test_lossless_aggregate import synthetic_authority
from pro_a.workbench.lossless_recovery import assessment
from series_binding_helpers import Transport, rows, synthetic_providers


class PlanPatch:
    def __init__(self, patch):
        self.patch = patch

    def setenv(self, *args):
        self.patch.setenv(*args)

    def setattr(self, name, value):
        if name == 'pro_a.workbench.source_operations.plan_external_source_analysis':
            original = value
            def value(*args, **kwargs):
                plan = original(*args, **kwargs)
                for piece in plan['pieces']:
                    piece['scoped_node_catalog'] = [{'node_id': 'NODE_SYNTHETIC', 'canonical_name': 'Synthetic Company', 'primary_type': 'Company'}]
                return plan
        self.patch.setattr(name, value)


class HistoricalOutput(Transport):
    def __init__(self, first_series):
        super().__init__(mode='sparse')
        self.first_series = first_series

    def __call__(self, *args, **kwargs):
        response = super().__call__(*args, **kwargs)
        function = response.value['choices'][0]['message']['tool_calls'][0]['function']
        record = json.loads(function['arguments'])
        if self.first_series:
            record['claims'] = [deepcopy(record['claims'][0]) for _ in range(30 if len(self.calls) == 5 else 29)]
            for i, claim in enumerate(record['claims']):
                claim['statement'] += ' Synthetic observation ' + str(i)
            record['source_metadata']['author'] = 'SYNTHETIC_AUTHOR_' + str(len(self.calls))
            record['source_metadata']['summary'] = 'SYNTHETIC_SUMMARY_' + str(len(self.calls))
        elif len(self.calls) == 2:
            selection = {**record['claims'][0]['evidence'], 'selection_mode': 'RAW_SUBSPAN', 'selector': 'ABSENT_SYNTHETIC_LITERAL'}
            record['claims'] = [deepcopy(record['claims'][0]) for _ in range(26)]
            for i, claim in enumerate(record['claims']):
                claim.update(statement='Synthetic rejected observation ' + str(i), evidence=deepcopy(selection))
            from pro_a.source_analysis_wire import NODE_MATCH_ROLES
            record['node_matches'] = [{'node_id': 'NODE_SYNTHETIC', 'role': NODE_MATCH_ROLES[0], 'confidence': '0.9',
                'reason': 'Synthetic selector rejection', 'evidence': deepcopy(selection)} for _ in range(5)]
        function['arguments'] = json.dumps(record)
        return response


def build(root):
    assert repository_commit() == '3cb834fd98f137883f79248292eb23305cce7235'
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr('requests.sessions.Session.request', lambda *a, **k: (_ for _ in ()).throw(AssertionError('NETWORK_FORBIDDEN')))
        value = topology(root, PlanPatch(patch), accepted_retry=False)
        with synthetic_providers(value, HistoricalOutput(True)) as providers:
            resume(value, providers, key='synthetic-original-five', ceiling=5)
        service, run_id = value['service'], value['run_id']
        bindings = service.output_batches.inputs(service.get_run(run_id))
        with service.store.connect() as c:
            proof = assessment(service, c, run_id, bindings)
        value['resolution'] = synthetic_authority(proof['authority_scope'])
        token = qualified(value)
        authorize(value, token)
        assert len(service.output_batches.ledger.aggregate(bindings[0][3].series_id)['observation_ledger']['observations']) == 146
        with synthetic_providers(value, HistoricalOutput(False)) as providers:
            resume(value, providers, key='synthetic-six-seven', ceiling=2)
            assert len(providers['WHOLE_PIECE_OUTPUT_BATCH'].transport.calls) == 2
        assert len(rows(value, 'bounded_extraction_segment_results')) == 6
        assert service.get_run(run_id)['error']['code'] == 'BOUNDED_EXTRACTION_FAILED'
        failed = [a for a in rows(value, 'bounded_extraction_attempts') if a['attempt_id'] not in {r['attempt_id'] for r in rows(value, 'bounded_extraction_segment_results')}]
        assert len(failed) == 1
        return {'config': asdict(value['config']), 'run_id': run_id, 'failed_attempt_id': failed[0]['attempt_id'],
            'phase4_config': str(value['phase4_config']), 'resolution': value['resolution']}


if __name__ == '__main__':
    root = Path(sys.argv[1]).resolve()
    root.mkdir(parents=True, exist_ok=True)
    result = build(root)
    (root/'fixture.json').write_text(json.dumps(result, default=str), encoding='utf-8')
