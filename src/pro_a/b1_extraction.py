"""Opt-in B1 request policy; existing v7 compiler and durable ledger stay authoritative."""
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile

from .config import tomllib
from .evidence_binding import identity, validate_catalog

VERSION = 'b1-evidence-first-request-v1'
BINDING = 'b1-evidence-first-output-binding-v1'
SERIES = 'b1-evidence-first-output-series-v1'
BATCH = 'b1-evidence-first-output-batch-v1'
CONTEXT = 'b1-reviewed-context-v1'
COUNTER = 'deepseek-v41-complete-request-counter-v1'
SYSTEM_SHA256 = '61caec45852846bd428e05e635b456774ee8243d4326ae32987be3695193ffa8'
COMPONENTS = ('counter_exe', 'counter_source', 'counter_manifest', 'counter_lock', 'tokenizer')
RECIPE_COMMIT = '8cadfede7063c896b944e7bae05daa3549ae97ea'
QUALIFIED_COMPONENTS = {
    'counter_exe': '192628af6ad57f5fd8bf6654fe497434d46ec90c6d9a944c808addd8602cd840',
    'counter_source': 'fdae68f65e2583ccf73291269e0dbe74f17ae17b28882b7851c75a209075b328',
    'counter_manifest': '5d293073273a4ae9ab2939da44fcdf4abf5827a75b23b6b4c93202fea5b992dd',
    'counter_lock': '4d35b6b866a554ca249b68d06437976b3ce062a6380155efae3f4ffe63b91ce2',
    'tokenizer': '81f64d1248a68ce3663e07ab3ee48b851e5df0e32d27cb98e4c9a268151e8d99'}


def require(value, code):
    if not value:
        raise ValueError(code)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def system():
    data = (Path(__file__).parent / 'resources/B1_EVIDENCE_FIRST_SYSTEM_V1.txt').read_bytes()
    require(hashlib.sha256(data).hexdigest() == SYSTEM_SHA256, 'B1_PROMPT_VERSION_DRIFT')
    return data.decode('utf8')


def policy():
    return {'version': VERSION, 'system_prompt_sha256': SYSTEM_SHA256,
        'context_version': CONTEXT, 'counter_version': COUNTER,
        'counter_components_sha256': identity(QUALIFIED_COMPONENTS),
        'max_input_tokens': 14000, 'local_input_ceiling': 13000,
        'max_output_tokens': 12000, 'max_total_tokens': 26000,
        'max_calls': 1, 'automatic_retry': False, 'automatic_subdivision': False,
        'completion_boundary': 'STOP_AFTER_BOUNDED_EXTRACTION',
        'semantic_registration_allowed': False, 'canonical_permission': False}


def response_violation(metadata):
    """Local qualification diagnosis; never rewrites the actual server metadata."""
    if metadata.get('provider_reported_model') != 'deepseek-flash':
        return 'B1_MODEL_IDENTITY_DRIFT'
    counts = [metadata.get(k) for k in ('input_tokens', 'output_tokens', 'total_tokens')]
    if any(type(v) is not int for v in counts):
        return 'B1_USAGE_REQUIRED'
    if counts[0] > 14000 or counts[1] > 12000 or counts[2] > 26000 or counts[0] + counts[1] != counts[2]:
        return 'B1_BUDGET_VIOLATION'
    return None


def load_settings(config_path):
    """Explicit local Operator config. Unknown keys fail; references are hash-pinned."""
    root = Path(config_path).resolve().parent
    with Path(config_path).open('rb') as stream:
        value = tomllib.load(stream).get('b1', {})
    require(set(value) == {'context_file', 'context_sha256', 'counter_identity_file',
                          'counter_identity_sha256'}, 'B1_SETTINGS_REQUIRED')
    context_path = root / value['context_file']
    require(sha(context_path) == value['context_sha256'], 'B1_CONTEXT_FILE_DRIFT')
    counter_path = root / value['counter_identity_file']
    require(sha(counter_path) == value['counter_identity_sha256'], 'B1_COUNTER_IDENTITY_DRIFT')
    context = json.loads(context_path.read_text(encoding='utf-8-sig'))
    require(type(context) is dict and set(context) == {'version', 'source_sha256',
        'piece_sha256', 'assigned_evidence_refs', 'closure', 'source_metadata_reference'}
        and context['version'] == CONTEXT, 'B1_CONTEXT_INVALID')
    require(type(context['source_metadata_reference']) is dict, 'B1_METADATA_REFERENCE_REQUIRED')
    return {'context': context, 'context_file_sha256': value['context_sha256'],
            'counter_identity_sha256': value['counter_identity_sha256']}


def validate_context(value, catalog, context):
    validate_catalog(catalog, context)
    require(value['version'] == CONTEXT and value['source_sha256'] == context.source_sha256
        and value['piece_sha256'] == context.piece.source_sha256, 'B1_SOURCE_PIECE_DRIFT')
    require(value['source_metadata_reference'].get('source_sha256') == context.source_sha256,
            'B1_METADATA_SOURCE_DRIFT')
    assigned, closure = value['assigned_evidence_refs'], value['closure']
    universe = {u.evidence_ref for u in catalog.units}
    require(type(assigned) is list and 1 <= len(assigned) <= 16
        and len(set(assigned)) == len(assigned) and set(assigned) <= universe
        and assigned == [u.evidence_ref for u in catalog.units if u.evidence_ref in assigned],
        'B1_ASSIGNED_INVALID')
    require(type(closure) is dict and set(closure) == set(assigned)
        and all(type(refs) is list and len(set(refs)) == len(refs) and set(refs) <= universe
                for refs in closure.values()), 'B1_CONTEXT_CLOSURE_INCOMPLETE')


def regions(value, catalog, context, segment):
    from .output_provider_record_v7 import source_regions
    validate_context(value, catalog, context)
    require(list(segment.assigned_evidence_refs) == value['assigned_evidence_refs'],
            'B1_ASSIGNED_DRIFT')
    visible = set(value['assigned_evidence_refs']) | {r for refs in value['closure'].values() for r in refs}
    return [r for r in source_regions(catalog, context, segment) if r.get('evidence_ref') in visible]


def render(value, context, catalog, series, segment, payload):
    """Change only the explicitly versioned B1 request; preserve native input privately."""
    frozen = value['b1_request_context']
    visible = regions(frozen, catalog, context, segment)
    target = payload['target']
    user = {'assigned_evidence_refs': list(segment.assigned_evidence_refs),
        'evaluation_only': False,
        'metadata_policy': 'Preserve source-supported metadata; unresolved variants are review-required, never authority.',
        'piece_sha256': context.piece.source_sha256,
        'scoped_node_catalog': value['native']['scoped_node_catalog'],
        'source_metadata_reference': frozen['source_metadata_reference'],
        'source_regions': visible, 'source_sha256': context.source_sha256,
        'formal_execution': {'processing_run_id': series.processing_run_id,
            'source_piece_id': series.source_piece_id, 'series_sha256': series.series_sha256,
            'segment_sha256': segment.segment_sha256, 'request_contract_sha256': identity(target),
            'context_sha256': identity(frozen)}}
    payload['request']['messages'] = [{'role': 'system', 'content': system()},
        {'role': 'user', 'content': json.dumps(user, ensure_ascii=False)}]
    return payload


def validate_record(content, value, catalog, context, segment):
    """Location/visibility checks only. Entailment and source truth still need review."""
    from . import output_provider_record_v7 as v7
    record = v7.lexical.parse_object(content)
    v7.lexical.validate_shape(record, v7.record_schema())
    visible = {r['evidence_ref'] for r in regions(value, catalog, context, segment)}
    for family in ('claims', 'node_matches'):
        for obj in record[family]:
            require(obj.get('evidence_pointer', '') == '', 'B1_MODEL_POINTER_FORBIDDEN')
    for claim in record['claims']:
        for dependency in claim['research_review']['context_dependencies']:
            _, bound = v7.resolve_intent(dependency['evidence'], catalog, context)
            require(bound.evidence_ref in visible, 'B1_CONTEXT_DEPENDENCY_NOT_VISIBLE')


class LocalCounter:
    """Qualified local V4.1 executable, never a network token service."""
    def __init__(self, config_path):
        load_settings(config_path)
        with Path(config_path).open('rb') as stream:
            settings = tomllib.load(stream)['b1']
        self.path = Path(config_path).resolve().parent / settings['counter_identity_file']
        self.expected_sha256 = settings['counter_identity_sha256']
        self.manifest = json.loads(self.path.read_text(encoding='utf-8-sig'))
        require(self.manifest['recipe_commit'] == RECIPE_COMMIT
            and {k: self.manifest[k]['sha256'] for k in COMPONENTS} == QUALIFIED_COMPONENTS,
            'B1_COUNTER_NOT_QUALIFIED')
        self.identity = {'version': COUNTER, 'manifest_sha256': self.expected_sha256,
            'components': {k: self.manifest[k]['sha256'] for k in COMPONENTS},
            'recipe_commit': self.manifest['recipe_commit'], 'server_exact_usage': False}
        self.verify()

    def verify(self):
        require(sha(self.path) == self.expected_sha256, 'B1_COUNTER_IDENTITY_DRIFT')
        for key in COMPONENTS:
            require(sha(self.manifest[key]['path']) == self.manifest[key]['sha256'], 'B1_COUNTER_COMPONENT_DRIFT')

    def preflight(self, request):
        self.verify()
        require(request['model'] == 'deepseek-flash' and request['max_tokens'] == 12000,
                'B1_REQUEST_BUDGET_DRIFT')
        executable = Path(self.manifest['counter_exe']['path'])
        runtime = executable.parents[3]
        env = {k: os.environ[k] for k in ('SystemRoot', 'WINDIR', 'TEMP', 'TMP', 'PATH',
               'USERPROFILE', 'LOCALAPPDATA', 'APPDATA') if k in os.environ}
        env['PATH'] = os.pathsep.join((str(runtime/'rust/bin'), str(runtime/'w64devkit/bin'), env.get('PATH', '')))
        with tempfile.TemporaryDirectory(prefix='pro-a-b1-counter-') as directory:
            root = Path(directory)
            request_path = root/'request.json'
            request_path.write_text(json.dumps(request, ensure_ascii=False), encoding='utf8')
            output = root/'result'
            result = subprocess.run([str(executable), str(request_path), self.manifest['tokenizer']['path'], str(output)],
                env=env, capture_output=True, timeout=60)
            require(result.returncode == 0, 'B1_COUNTER_FAILED')
            counted = json.loads((output/'local-token-count.json').read_text(encoding='utf8'))
            rendered = (output/'rendered-prompt.txt').read_text(encoding='utf8')
            require(counted['encoder'] == 'DeepseekV41Encoding'
                and all(m['content'] in rendered for m in request['messages']), 'B1_COUNTER_TEMPLATE_MISMATCH')
            tool = json.loads(rendered.split('### Available Tool Schemas\n\n', 1)[1].split('\n\nYou MUST strictly follow', 1)[0])
            require(tool['parameters'] == request['tools'][0]['function']['parameters']
                and tool['name'] == request['tools'][0]['function']['name'], 'B1_COUNTER_SCHEMA_MISMATCH')
            count = counted['input_tokens']
        require(type(count) is int and 0 < count <= 13000, 'B1_INPUT_PREFLIGHT_EXCEEDED')
        return {'version': COUNTER, 'request_sha256': identity(request),
            'counter_identity': copy.deepcopy(self.identity), 'input_tokens': count,
            'reserved_input_tokens': 14000, 'reserved_output_tokens': 12000,
            'reserved_total_tokens': 26000, 'server_exact_usage': False,
            'budget_reservation_authority': False}  # Amounts require the existing durable Attempt reservation.
