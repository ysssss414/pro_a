"""Offline synthetic structural metrics; not a Provider success-rate experiment.

Run from checkout with dev dependencies: python scripts/measure_node_intent_complexity.py
"""
import copy
import json
from pathlib import Path
import statistics
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tests')]
from pro_a import output_provider_record_v4 as v4, output_provider_record_v5 as v5
from pro_a import node_candidate_intent as nodes
from pro_a.constants import NODE_TYPES
from test_provider_record_v4 import records
from node_intent_helpers import from_valid_v4


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def members(value):
    if isinstance(value, dict): return len(value) + sum(members(v) for v in value.values())
    if isinstance(value, list): return sum(members(v) for v in value)
    return 0


def branching(value):
    if isinstance(value, dict):
        children = [branching(v) for v in value.values()]
        return (int('anyOf' in value) + sum(n for n, _ in children),
                len(value.get('anyOf', [])) + sum(n for _, n in children))
    if isinstance(value, list):
        children = [branching(v) for v in value]
        return sum(n for n, _ in children), sum(n for _, n in children)
    return 0, 0


def samples():
    _, _, _, mixed = records()
    yield 'mixed', mixed
    for primary in sorted(NODE_TYPES):
        record = copy.deepcopy(mixed)
        node = copy.deepcopy(next((n for n in mixed['node_candidates'] if n['primary_type'] == primary), mixed['node_candidates'][0]))
        node['primary_type'] = primary
        record['node_candidates'] = [node]
        for claim in record['claims']: claim['related_candidate_names'] = [node['canonical_name']]
        yield primary, record


def measured(normalizer, values, repetitions=40):
    times = []
    for _ in range(repetitions):
        start = time.perf_counter_ns()
        for value in values: normalizer(value)
        times.append((time.perf_counter_ns() - start) / len(values) / 1000)
    return round(statistics.median(times), 3)


def measure():
    cases = []; old_texts = []; new_texts = []; candidates = []
    for name, old in samples():
        new = from_valid_v4(old); old_text = encoded(old); new_text = encoded(new)
        assert v4.normalize_record(old_text) == v5.normalize_record(new_text)
        old_texts.append(old_text); new_texts.append(new_text); candidates.extend(new['node_candidates'])
        cases.append({'sample': name, 'candidate_count': len(old['node_candidates']), 'normalized_semantic_parity': True,
            'v4': {'response_characters': len(old_text), 'response_utf8_bytes': len(old_text.encode()),
                   'candidate_top_level_fields': [len(n) for n in old['node_candidates']],
                   'candidate_all_object_members': [members(n) for n in old['node_candidates']]},
            'v5': {'response_characters': len(new_text), 'response_utf8_bytes': len(new_text.encode()),
                   'candidate_top_level_fields': [len(n) for n in new['node_candidates']],
                   'candidate_all_object_members': [members(n) for n in new['node_candidates']]}})
    schemas = {}
    for name, schema in (('v4', v4.record_schema()), ('v5', v5.record_schema())):
        branches, alternatives = branching(schema); node = schema['properties']['node_candidates']['items']
        schemas[name] = {'characters': len(encoded(schema)), 'utf8_bytes': len(encoded(schema).encode()),
                        'candidate_schema_utf8_bytes': len(encoded(node).encode()),
                        'anyof_nodes': branches, 'anyof_alternatives': alternatives}
    return {'measurement': 'OFFLINE_SYNTHETIC_STRUCTURE_ONLY', 'real_provider_calls': 0,
        'schemas': schemas, 'samples': cases,
        'totals': {version: {key: sum(c[version][key] for c in cases)
                   for key in ('response_characters', 'response_utf8_bytes')} for version in ('v4', 'v5')},
        'median_microseconds': {'v4_normalize_per_record': measured(v4.normalize_record, old_texts),
            'v5_normalize_per_record': measured(v5.normalize_record, new_texts),
            'v5_compile_per_candidate': measured(nodes.compile_candidate, candidates)},
        'timing_repetitions': 40, 'semantic_information_preserved': True,
        'provider_success_rate_measured': False}


if __name__ == '__main__':
    print(json.dumps(measure(), ensure_ascii=False, indent=2))
