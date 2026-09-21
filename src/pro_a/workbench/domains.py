"""Workbench-only domain assignment and immutable run/packet companions."""
from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path

from pro_a.cloud_contract import operation_contract
from pro_a.config import load_config
from pro_a.domain_packs import canonical, compose, digest, fields, load_pack, read_json, require, text
from pro_a.run_context import freeze_context, guard_resume, validate_context
from .config import checked_path
from .review_store import schema_version
from .store import Store

TABLES = {
    'domain_pack_registry': '''domain_id TEXT NOT NULL, version TEXT NOT NULL, sha256 TEXT NOT NULL,
        root TEXT NOT NULL, PRIMARY KEY(domain_id,version)''',
    'domain_assignments': '''object_type TEXT NOT NULL CHECK(object_type IN ('Source','Node','RQ')),
        object_id TEXT NOT NULL, revision INTEGER NOT NULL, primary_domain TEXT NOT NULL,
        packs_json TEXT NOT NULL, actor TEXT NOT NULL, reason TEXT NOT NULL, created_at TEXT NOT NULL,
        PRIMARY KEY(object_type,object_id,revision)''',
    'domain_run_bindings': '''processing_run_id TEXT PRIMARY KEY REFERENCES source_processing_runs(processing_run_id),
        resume_sha256 TEXT NOT NULL, context_sha256 TEXT NOT NULL, artifact_relative TEXT UNIQUE NOT NULL,
        file_sha256 TEXT NOT NULL, config_path TEXT NOT NULL''',
    'domain_packet_bindings': '''artifact_id TEXT PRIMARY KEY REFERENCES registered_packets(artifact_id),
        processing_run_id TEXT UNIQUE NOT NULL REFERENCES domain_run_bindings(processing_run_id),
        packet_sha256 TEXT NOT NULL, context_sha256 TEXT NOT NULL, companion_relative TEXT NOT NULL,
        companion_sha256 TEXT NOT NULL''',
    'domain_activation_receipts': '''domain_id TEXT NOT NULL, version TEXT NOT NULL, sha256 TEXT NOT NULL,
        receipt_sha256 TEXT PRIMARY KEY, receipt_json TEXT NOT NULL''',
}


def now():
    return datetime.now(timezone.utc).isoformat()


def _write(path, content):
    path = checked_path(path, missing=True)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        require(path.read_bytes() == content, 'DOMAIN_ARTIFACT_CONFLICT')
    else:
        with path.open('xb') as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())


def prepare_domains(config):
    """Explicit offline v8 -> v9 migration. No startup migration or canonical writes."""
    config.validate()
    path = checked_path(config.state_db)
    backup = path.with_name(path.name + '.stage7-backup')
    receipt_path = path.with_name(path.name + '.stage43-migration.json')
    for suffix in ('-wal', '-shm', '-journal'):
        require(not path.with_name(path.name + suffix).exists(), 'DOMAIN_MIGRATION_REQUIRES_OFFLINE')
    with Store(config).connect(operator_write=True) as connection:
        if schema_version(connection) in ('9', '10'):
            return {'status': 'ALREADY_PREPARED', 'schema_version': schema_version(connection)}
        require(schema_version(connection) == '8', 'SOURCE_OPERATIONS_SCHEMA_REQUIRED')
        connection.execute('BEGIN EXCLUSIVE')
        require(not connection.execute("SELECT 1 FROM cloud_jobs WHERE state IN ('QUEUED','RUNNING')").fetchone()
                and not connection.execute("SELECT 1 FROM source_processing_runs WHERE state NOT IN ('HUMAN_REVIEW_REQUIRED','FAILED','BLOCKED')").fetchone(),
                'DOMAIN_MIGRATION_REQUIRES_DRAIN')
        before = path.read_bytes()
        _write(backup, before)
        for table, columns in TABLES.items():
            connection.execute(f'CREATE TABLE {table}({columns})')
            for action in ('UPDATE', 'DELETE'):
                connection.execute(f"CREATE TRIGGER {table}_{action.lower()}_forbidden BEFORE {action} ON {table} BEGIN SELECT RAISE(ABORT,'APPEND_ONLY'); END")
        connection.execute('ALTER TABLE source_processing_runs ADD COLUMN domain_context_required INTEGER NOT NULL DEFAULT 0 CHECK(domain_context_required IN (0,1))')
        connection.execute("CREATE TRIGGER source_domain_marker_immutable BEFORE UPDATE OF domain_context_required ON source_processing_runs BEGIN SELECT RAISE(ABORT,'IMMUTABLE_CONTEXT_MARKER'); END")
        connection.execute("UPDATE workbench_meta SET value='9' WHERE key='schema_version'")
        require(not connection.execute('PRAGMA foreign_key_check').fetchall(), 'DOMAIN_MIGRATION_FOREIGN_KEYS')
    receipt = {'schema_version': '9', 'status': 'DOMAIN_SCHEMA_PREPARED',
               'backup_sha256': hashlib.sha256(before).hexdigest(),
               'migrated_sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
    _write(receipt_path, canonical(receipt).encode('utf-8'))
    return receipt


def rollback_domains(config):
    """Exact offline rollback before use; changed state requires the full backup/restore workflow."""
    config.validate()
    path = checked_path(config.state_db)
    receipt = read_json(path.with_name(path.name + '.stage43-migration.json'))
    fields(receipt, 'schema_version status backup_sha256 migrated_sha256')
    backup = checked_path(path.with_name(path.name + '.stage7-backup'))
    for suffix in ('-wal', '-shm', '-journal'):
        require(not path.with_name(path.name + suffix).exists(), 'DOMAIN_MIGRATION_REQUIRES_OFFLINE')
    require(hashlib.sha256(backup.read_bytes()).hexdigest() == receipt['backup_sha256'], 'DOMAIN_BACKUP_CORRUPT')
    with Store(config).connect(operator_write=True) as connection:
        connection.execute('BEGIN EXCLUSIVE')
        require(schema_version(connection) in ('9', '10'), 'DOMAIN_SCHEMA_REQUIRED')
        require(hashlib.sha256(path.read_bytes()).hexdigest() == receipt['migrated_sha256'], 'DOMAIN_ROLLBACK_STATE_CHANGED')
    path.write_bytes(backup.read_bytes())
    return {'status': 'ROLLED_BACK', 'schema_version': '8', 'sha256': receipt['backup_sha256']}


def config_digest(path, source_limits):
    effective = asdict(load_config(path))
    effective.pop('config_path')
    effective['workspace']['root'] = str(effective['workspace']['root'].resolve())
    return digest({'phase4': effective, 'source_limits': source_limits})


def prompt_digest():
    return digest([operation_contract(op) for op in ('SOURCE_ANALYSIS_PIECE', 'SEMANTIC_DECOMPOSITION')])


class Domains:
    def __init__(self, config):
        self.config = config
        self.store = Store(config)

    def register(self, root):
        pack = load_pack(root)
        with self.store.connect(operator_write=True) as connection:
            require(schema_version(connection) in ('9', '10'), 'DOMAIN_SCHEMA_REQUIRED')
            connection.execute('BEGIN IMMEDIATE')
            identity = pack.identity
            prior = connection.execute('SELECT * FROM domain_pack_registry WHERE domain_id=? AND version=?',
                                       (identity['domain_id'], identity['version'])).fetchone()
            if prior:
                require(prior['sha256'] == pack.sha256, 'DOMAIN_VERSION_IMMUTABLE')
            else:
                connection.execute('INSERT INTO domain_pack_registry VALUES(?,?,?,?)',
                                   (identity['domain_id'], identity['version'], pack.sha256, str(pack.root)))
        return identity

    @staticmethod
    def packs(connection, identities):
        result = []
        for identity in identities:
            fields(identity, 'domain_id version sha256')
            row = connection.execute('SELECT * FROM domain_pack_registry WHERE domain_id=? AND version=?',
                                     (identity['domain_id'], identity['version'])).fetchone()
            require(row is not None and row['sha256'] == identity['sha256'], 'DOMAIN_PACK_NOT_REGISTERED')
            pack = load_pack(Path(row['root']))
            require(pack.identity == identity, 'DOMAIN_PACK_DRIFT')
            result.append(pack)
        return result

    def assign(self, object_type, object_id, *, primary_domain, packs, actor, reason, expected_revision):
        require(object_type in ('Source', 'Node', 'RQ'))
        text(object_id, 200)
        text(actor, 200)
        text(reason)
        require(type(expected_revision) is int and expected_revision >= 0)
        with self.store.connect(operator_write=True) as connection:
            require(schema_version(connection) in ('9', '10'), 'DOMAIN_SCHEMA_REQUIRED')
            connection.execute('BEGIN IMMEDIATE')
            combined = compose(self.packs(connection, packs), primary_domain)
            require(combined['disposition'] == 'READY', 'DOMAIN_COMPOSITION_REQUIRES_REVIEW')
            if object_type == 'Source':
                require(connection.execute('SELECT 1 FROM private_sources WHERE source_id=?', (object_id,)).fetchone(), 'SOURCE_NOT_FOUND')
            else:
                from pro_a.query import ReadOnlyQuery
                with ReadOnlyQuery(self.config.knowledge_db).connect() as knowledge:
                    table, key = ('nodes', 'node_id') if object_type == 'Node' else ('research_questions', 'rq_id')
                    require(knowledge.execute(f'SELECT 1 FROM {table} WHERE {key}=?', (object_id,)).fetchone(), 'DOMAIN_OBJECT_NOT_FOUND')
            prior = self.assignment(connection, object_type, object_id)
            revision = prior['revision'] if prior else 0
            require(revision == expected_revision, 'DOMAIN_ASSIGNMENT_STALE')
            identities = canonical(combined['packs'])
            if prior and prior['primary_domain'] == primary_domain and prior['packs_json'] == identities:
                return dict(prior)
            connection.execute('INSERT INTO domain_assignments VALUES(?,?,?,?,?,?,?,?)',
                               (object_type, object_id, revision + 1, primary_domain, identities, actor, reason, now()))
            return dict(self.assignment(connection, object_type, object_id))

    @staticmethod
    def assignment(connection, object_type, object_id, revision=None):
        condition = ' AND revision=?' if revision is not None else ''
        args = (object_type, object_id, revision) if revision is not None else (object_type, object_id)
        return connection.execute('SELECT * FROM domain_assignments WHERE object_type=? AND object_id=?' + condition + ' ORDER BY revision DESC LIMIT 1', args).fetchone()

    def basis(self, connection, source, runtime, profile, cloud_profile, *, revision=None):
        assignment = self.assignment(connection, 'Source', source['source_id'], revision)
        require(assignment is not None, 'DOMAIN_ASSIGNMENT_REQUIRED')
        combined = compose(self.packs(connection, json.loads(assignment['packs_json'])), assignment['primary_domain'])
        require(combined['disposition'] == 'READY', 'DOMAIN_COMPOSITION_REQUIRES_REVIEW')
        limits = {'max_pdf_bytes': profile.max_pdf_bytes, 'max_extraction_pieces': profile.max_extraction_pieces}
        return {'source_id': source['source_id'], 'source_sha256': source['source_sha256'],
                'input_artifact_id': source['storage_artifact_id'],
                'scope_sha256': digest({'validation': json.loads(source['validation_json']), 'source_limits': limits}),
                'assignment_revision': assignment['revision'],
                'composition': {key: combined[key] for key in ('primary_domain', 'packs', 'sha256')},
                'runtime': runtime, 'prompt_sha256': prompt_digest(),
                'config_sha256': config_digest(profile.phase4_config_path, limits),
                'model_configuration': cloud_profile.public_identity(), 'execution_policy': 'OFFLINE_REPLAY_ONLY'}

    def bind_run(self, connection, run_id, basis, profile, created_at, reason):
        assignment = self.assignment(connection, 'Source', basis['source_id'], basis['assignment_revision'])
        context = freeze_context(basis, run_id=run_id, created_at=created_at, actor=assignment['actor'],
                                 reason=reason or assignment['reason'])
        relative = 'domain-contexts/' + digest(run_id)[:24] + '.json'
        content = canonical(context).encode('utf-8')
        _write(self.config.artifact_root / relative, content)
        profile_ref = canonical({'path': str(profile.phase4_config_path.resolve()),
                                 'max_pdf_bytes': profile.max_pdf_bytes,
                                 'max_extraction_pieces': profile.max_extraction_pieces})
        connection.execute('INSERT INTO domain_run_bindings VALUES(?,?,?,?,?,?)',
                           (run_id, context['resume_sha256'], context['context_sha256'], relative,
                            hashlib.sha256(content).hexdigest(), profile_ref))
        return context

    def read(self, run_id, *, connection=None):
        if connection is None:
            with self.store.connect() as current:
                return self.read(run_id, connection=current)
        if schema_version(connection) not in ('9', '10'):
            return None
        run = connection.execute('SELECT * FROM source_processing_runs WHERE processing_run_id=?', (run_id,)).fetchone()
        require(run is not None, 'PROCESSING_RUN_NOT_FOUND')
        row = connection.execute('SELECT * FROM domain_run_bindings WHERE processing_run_id=?', (run_id,)).fetchone()
        if not run['domain_context_required']:
            require(row is None, 'LEGACY_CONTEXT_CONFLICT')
            return None
        require(row is not None, 'FROZEN_CONTEXT_MISSING')
        from .artifacts import Artifacts
        path = Artifacts(self.config).resolve(row['artifact_relative'])
        require(hashlib.sha256(path.read_bytes()).hexdigest() == row['file_sha256'], 'FROZEN_CONTEXT_CORRUPT')
        value = validate_context(read_json(path))
        require(value['context_sha256'] == row['context_sha256'] and value['resume_sha256'] == row['resume_sha256']
                and value['run_id'] == run_id and value['basis']['source_id'] == run['source_id'], 'FROZEN_CONTEXT_BINDING_MISMATCH')
        return value

    def guard(self, run_id, jobs, profile=None):
        with self.store.connect() as connection:
            frozen = self.read(run_id, connection=connection)
            if frozen is None:
                return None
            run = connection.execute('SELECT * FROM source_processing_runs WHERE processing_run_id=?', (run_id,)).fetchone()
            source = connection.execute('SELECT * FROM private_sources WHERE source_id=?', (run['source_id'],)).fetchone()
            binding = connection.execute('SELECT * FROM domain_run_bindings WHERE processing_run_id=?', (run_id,)).fetchone()
            if profile is None:
                from .source_operations import SourceProfile
                value = json.loads(binding['config_path'])
                profile = SourceProfile(Path(value['path']), value['max_pdf_bytes'], value['max_extraction_pieces'])
            # Later assignment events do not relabel or invalidate the old frozen run.
            current = self.basis(connection, source, jobs.current_runtime(), profile, jobs.profile,
                                 revision=frozen['basis']['assignment_revision'])
            guard_resume(frozen, current)
            return {'contract_version': 'run-domain-context-v1', 'context_sha256': frozen['context_sha256'],
                    'artifact_relative': binding['artifact_relative']}

    def bind_packet(self, run_id, artifact_id):
        context = self.read(run_id)
        if context is None:
            return
        with self.store.connect(operator_write=True) as connection:
            row = connection.execute('SELECT packet_sha256 FROM registered_packets WHERE artifact_id=?', (artifact_id,)).fetchone()
            body = {'contract_version': 'domain-review-companion-v1', 'processing_run_id': run_id,
                    'artifact_id': artifact_id, 'packet_sha256': row['packet_sha256'],
                    'context_sha256': context['context_sha256']}
            content = canonical(body).encode('utf-8')
            relative = 'domain-review/' + artifact_id + '.json'
            _write(self.config.artifact_root / relative, content)
            connection.execute('INSERT INTO domain_packet_bindings VALUES(?,?,?,?,?,?)',
                               (artifact_id, run_id, row['packet_sha256'], context['context_sha256'], relative,
                                hashlib.sha256(content).hexdigest()))

    def validate_packet(self, artifact_id):
        with self.store.connect() as connection:
            if schema_version(connection) not in ('9', '10'):
                return
            run = connection.execute('SELECT * FROM source_processing_runs WHERE packet_artifact_id=?', (artifact_id,)).fetchone()
            binding = connection.execute('SELECT * FROM domain_packet_bindings WHERE artifact_id=?', (artifact_id,)).fetchone()
            if binding is None:
                require(run is None or not run['domain_context_required'], 'DOMAIN_PACKET_COMPANION_MISSING')
                return
            context = self.read(binding['processing_run_id'], connection=connection)
            require(context is not None and binding['context_sha256'] == context['context_sha256'], 'DOMAIN_PACKET_CONTEXT_MISMATCH')
            from .artifacts import Artifacts
            path = Artifacts(self.config).resolve(binding['companion_relative'])
            require(hashlib.sha256(path.read_bytes()).hexdigest() == binding['companion_sha256'], 'DOMAIN_PACKET_COMPANION_CORRUPT')
            value = read_json(path)
            fields(value, 'contract_version processing_run_id artifact_id packet_sha256 context_sha256')
            require(value == {'contract_version': 'domain-review-companion-v1',
                              'processing_run_id': binding['processing_run_id'], 'artifact_id': artifact_id,
                              'packet_sha256': binding['packet_sha256'], 'context_sha256': context['context_sha256']}, 'DOMAIN_PACKET_COMPANION_CORRUPT')
            packet = connection.execute('SELECT * FROM registered_packets WHERE artifact_id=?', (artifact_id,)).fetchone()
            require(packet['packet_sha256'] == value['packet_sha256'], 'DOMAIN_PACKET_HASH_MISMATCH')
