"""Declarative domain packs; no executable hooks or canonical identity changes."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re

from .constants import NODE_TYPES, RELATION_TYPES
from .workbench.config import BoundaryError, checked_path

CONTRACT_VERSION = 'domain-pack-v1'
CAPABILITIES = {'shared_core', 'core_floor', 'existing_direct_paths_only'}
MAX_BYTES = 1024 * 1024
FIELDS = set('contract_version domain_id version display_name description compatibility supported_node_types supported_relations relation_policies parent_placement_rules normalization_candidates technical_identifiers claim_pattern_hints source_analysis_hints semantic_decomposition admission_policy current_view_hints impact_policy coverage_dimensions acceptance_fixtures known_limitations file_inventory references lifecycle configuration'.split())
SECTIONS = set('one_line_conclusion core_logic key_facts core_disagreements assumptions_to_verify investment_implication major_risks knowledge_gaps key_watch_items recent_change'.split())


def require(condition, code='DOMAIN_PACK_INVALID'):
    if not condition:
        raise BoundaryError(code)


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode('utf-8')).hexdigest()


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, 'DUPLICATE_JSON_KEY')
        result[key] = value
    return result


def read_json(path):
    content = checked_path(Path(path)).read_bytes()
    require(len(content) <= MAX_BYTES, 'DOMAIN_FILE_TOO_LARGE')
    try:
        return json.loads(content.decode('utf-8'), object_pairs_hook=_pairs,
                          parse_constant=lambda _: require(False, 'NONFINITE_JSON'))
    except (UnicodeError, ValueError) as error:
        if isinstance(error, BoundaryError):
            raise
        raise BoundaryError('DOMAIN_JSON_INVALID') from None


def fields(value, expected):
    require(isinstance(value, dict) and set(value) == set(expected.split()))


def text(value, limit=1000):
    require(isinstance(value, str) and 0 < len(value) <= limit and value == value.strip())


def unique(value, allowed=None):
    require(isinstance(value, list) and all(isinstance(x, str) for x in value))
    require(len(value) == len(set(value)))
    if allowed is not None:
        require(set(value) <= set(allowed))


def sha(value):
    require(isinstance(value, str) and re.fullmatch('[0-9a-f]{64}', value) is not None)


def relative(root, name):
    require(isinstance(name, str) and bool(name) and '\\' not in name and ':' not in name
            and not name.startswith('/') and all(p not in ('', '.', '..') and not p.endswith((' ', '.')) for p in name.split('/')),
            'DOMAIN_PATH_UNSAFE')
    path = checked_path(root / name)
    require(path.is_relative_to(root) and path.is_file(), 'DOMAIN_PATH_UNSAFE')
    return path


@dataclass(frozen=True)
class DomainPack:
    root: Path
    serialized: str
    sha256: str

    @property
    def manifest(self):
        return json.loads(self.serialized)

    @property
    def identity(self):
        value = self.manifest
        return {'domain_id': value['domain_id'], 'version': value['version'], 'sha256': self.sha256}


def load_pack(root: Path) -> DomainPack:
    root = checked_path(Path(root))
    value = read_json(root / 'pack.json')
    require(isinstance(value, dict) and set(value) == FIELDS, 'DOMAIN_FIELDS_INVALID')
    require(value['contract_version'] == CONTRACT_VERSION, 'DOMAIN_VERSION_UNSUPPORTED')
    require(isinstance(value['domain_id'], str) and re.fullmatch('[a-z][a-z0-9_]{1,47}', value['domain_id']))
    require(isinstance(value['version'], str) and re.fullmatch(r'1\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)', value['version']), 'DOMAIN_VERSION_UNSUPPORTED')
    text(value['display_name'], 80)
    text(value['description'])
    fields(value['compatibility'], 'canonical_schema core_capabilities fixture_suite_version')
    require(value['compatibility']['canonical_schema'] == '0.2.3', 'CANONICAL_SCHEMA_UNSUPPORTED')
    unique(value['compatibility']['core_capabilities'], CAPABILITIES)
    require(value['compatibility']['fixture_suite_version'] == 'phase43-fixtures-v1')
    for key, allowed in [('supported_node_types', NODE_TYPES), ('supported_relations', RELATION_TYPES)]:
        unique(value[key], allowed)
    fields(value['lifecycle'], 'state qualification_refs')
    require(value['lifecycle']['state'] in ('PROPOSED', 'CONFIG_QUALIFIED', 'CORPUS_REVIEWED', 'OPERATIONAL_READY', 'ACTIVE'))
    unique(value['lifecycle']['qualification_refs'])
    # A descriptor never grants activation or provider permission.
    fields(value['configuration'], 'source_class')
    require(value['configuration']['source_class'] == 'PRIVATE_CLEAN_PDF')
    require(value['semantic_decomposition'] == {'mode': 'shared_core_only'})
    require(value['impact_policy'] == {'mode': 'existing_direct_paths_only'})
    fields(value['admission_policy'], 'mode additional_review_tags')
    require(value['admission_policy']['mode'] == 'core_floor')
    unique(value['admission_policy']['additional_review_tags'])
    unique(value['known_limitations'])
    require(value['known_limitations'])
    inventory = value['file_inventory']
    require(isinstance(inventory, list))
    files = {}
    for item in inventory:
        fields(item, 'path sha256')
        sha(item['sha256'])
        path = relative(root, item['path'])
        require(path.suffix in ('.json', '.txt', '.md'), 'DOMAIN_FILE_TYPE_FORBIDDEN')
        require(item['path'] not in files and item['path'] != 'pack.json')
        content = path.read_bytes()
        require(len(content) <= MAX_BYTES, 'DOMAIN_FILE_TOO_LARGE')
        require(hashlib.sha256(content).hexdigest() == item['sha256'], 'DOMAIN_FILE_HASH_MISMATCH')
        files[item['path']] = item['sha256']
    actual = set()
    for path in root.rglob('*'):
        checked_path(path)
        if path.is_file() and path != root / 'pack.json':
            actual.add(path.relative_to(root).as_posix())
    require(actual == set(files), 'DOMAIN_INVENTORY_MISMATCH')

    def ref(name):
        require(isinstance(name, str) and name in files, 'DOMAIN_REFERENCE_MISSING')

    fields(value['references'], 'prompt_profile source_policy admission_policy review_policy entity_policy relation_policy')
    for name in value['references'].values():
        ref(name)
    fields(value['source_analysis_hints'], 'terminology_ref examples_ref max_chars')
    hints = value['source_analysis_hints']
    require(type(hints['max_chars']) is int and 0 <= hints['max_chars'] <= 2000)
    for key in ('terminology_ref', 'examples_ref'):
        ref(hints[key])
        require(len(relative(root, hints[key]).read_text(encoding='utf-8')) <= hints['max_chars'], 'DOMAIN_HINT_TOO_LONG')
    for key in ('relation_policies', 'parent_placement_rules', 'normalization_candidates',
                'technical_identifiers', 'claim_pattern_hints', 'coverage_dimensions', 'acceptance_fixtures'):
        require(isinstance(value[key], list))
    for row in value['relation_policies']:
        fields(row, 'relation_type from_types to_types scope_required temporal_review_required examples_ref')
        require(row['relation_type'] in value['supported_relations'])
        unique(row['from_types'], value['supported_node_types'])
        unique(row['to_types'], value['supported_node_types'])
        require(row['scope_required'] is True and row['temporal_review_required'] is True)
        ref(row['examples_ref'])
    for row in value['parent_placement_rules']:
        fields(row, 'child_types parent_types taxonomy_ref require_explicit_review')
        unique(row['child_types'], value['supported_node_types'])
        unique(row['parent_types'], value['supported_node_types'])
        require(row['require_explicit_review'] is True)
        ref(row['taxonomy_ref'])
    for row in value['normalization_candidates']:
        fields(row, 'surface preferred_label node_type ambiguity_group source_local_equivalence_required')
        for key in ('surface', 'preferred_label', 'ambiguity_group'):
            text(row[key], 200)
        require(row['node_type'] in value['supported_node_types'] and row['source_local_equivalence_required'] is True)
    for row in value['technical_identifiers']:
        fields(row, 'literal class case_sensitive negative_examples_ref')
        text(row['literal'], 100)
        text(row['class'], 80)
        require(type(row['case_sensitive']) is bool)
        ref(row['negative_examples_ref'])
    # No core pattern-hint enum exists yet. Reject nonempty declarations instead of inventing one.
    require(not value['claim_pattern_hints'], 'CORE_PATTERN_HINT_UNSUPPORTED')
    require(isinstance(value['current_view_hints'], dict) and set(value['current_view_hints']) <= {'Company', 'Product'})
    for sections in value['current_view_hints'].values():
        require(isinstance(sections, dict) and set(sections) <= SECTIONS)
        for hints_list in sections.values():
            unique(hints_list)
            for hint in hints_list:
                text(hint, 200)
    for row in value['coverage_dimensions']:
        fields(row, 'id label target_registry_ref freshness_policy_ref')
        text(row['id'], 80)
        text(row['label'], 80)
        ref(row['target_registry_ref'])
        ref(row['freshness_policy_ref'])
    for row in value['acceptance_fixtures']:
        fields(row, 'path sha256 suite_version expected_schema_version')
        ref(row['path'])
        require(row['sha256'] == files[row['path']])
        require(row['suite_version'] == 'phase43-fixtures-v1' and row['expected_schema_version'] == 'fixture-spec-v1')
    # All record collections are sets of declarations, independent of their order.
    for key, rows in value.items():
        if isinstance(rows, list):
            require(len({canonical(row) for row in rows}) == len(rows))
            value[key] = sorted(rows, key=canonical)
    def normalize(item):
        if isinstance(item, dict):
            return {key: normalize(child) for key, child in item.items()}
        if isinstance(item, list):
            return sorted((normalize(child) for child in item), key=canonical)
        return item
    value = normalize(value)
    return DomainPack(root, canonical(value), digest(value))


def compose(packs, primary_domain):
    require(packs, 'DOMAIN_ASSIGNMENT_REQUIRED')
    ordered = sorted(packs, key=lambda pack: pack.identity['domain_id'])
    ids = [pack.identity['domain_id'] for pack in ordered]
    require(len(ids) == len(set(ids)) and primary_domain in ids, 'DOMAIN_COMPOSITION_INVALID')
    require(sum(pack.manifest['source_analysis_hints']['max_chars'] for pack in ordered) <= 4000,
            'DOMAIN_COMBINED_HINT_TOO_LONG')
    normalization, relations, conflicts = {}, {}, set()
    for pack in ordered:
        for row in pack.manifest['normalization_candidates']:
            key = row['surface']
            meaning = (row['preferred_label'], row['node_type'])
            if key in normalization and normalization[key] != meaning:
                conflicts.add('NORMALIZATION:' + key)
            normalization[key] = meaning
        for row in pack.manifest['relation_policies']:
            key = row['relation_type']
            meaning = (tuple(sorted(row['from_types'])), tuple(sorted(row['to_types'])))
            if key in relations and relations[key] != meaning:
                conflicts.add('RELATION:' + key)
            relations[key] = meaning
    body = {'contract_version': 'domain-composition-v1', 'primary_domain': primary_domain,
            'packs': [pack.identity for pack in ordered],
            'supported_node_types': sorted(set().union(*(set(p.manifest['supported_node_types']) for p in ordered))),
            'supported_relations': sorted(set().union(*(set(p.manifest['supported_relations']) for p in ordered))),
            'conflicts': sorted(conflicts), 'disposition': 'DEFER' if conflicts else 'READY',
            'admission_mode': 'core_floor', 'identity_scope': 'GLOBAL_CANONICAL'}
    return {**body, 'sha256': digest(body)}