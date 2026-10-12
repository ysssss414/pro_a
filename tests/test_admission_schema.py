"""Offline migration and purpose constraints, using a new synthetic database."""
import json
import sqlite3

import pytest

from pro_a.admission_schema import migrate, require_schema
from pro_a.db import Database
from pro_a.foundation_schema_preparation import apply_synthetic_migration
from pro_a.production_promotion import PromotionError, sha256_file


def test_explicit_migration_preserves_history_and_guards_every_sql_write(tmp_path):
    path = tmp_path / 'synthetic.sqlite3'
    db = Database(path)
    db.init_schema()
    with db.connect() as c:
        c.execute("INSERT INTO nodes(node_id,canonical_name,primary_type,created_at,updated_at) VALUES('N','Synthetic','Entity','t','t')")
        c.execute("INSERT INTO sources(source_id,title,original_name,archived_path,sha256,ingestion_mode,ingested_at) VALUES('S','Synthetic','synthetic','synthetic','abc','local','t')")
        c.execute("INSERT INTO claims(claim_id,statement,nature,ingestion_time,source_id,created_at) VALUES('C','Synthetic legacy fact','fact','t','S','t')")
        c.execute("INSERT INTO current_views(view_id,node_id,version,change_level,content_md,content_json,created_at) VALUES('V','N','1','initial','Historical official view','{}','t')")
        before_view = dict(c.execute('SELECT * FROM current_views').fetchone())
        before_claim = dict(c.execute('SELECT * FROM claims').fetchone())
    apply_synthetic_migration(path, configured_production_path=tmp_path / 'unused-production', expected_sha256=sha256_file(path))
    before = path.read_bytes()
    with pytest.raises(PromotionError, match='BASELINE_MISMATCH'):
        migrate(path, expected_sha256='0' * 64, backup_path=tmp_path / 'wrong-backup', configured_production_path=path)
    assert path.read_bytes() == before
    receipt = migrate(path, expected_sha256=sha256_file(path), backup_path=tmp_path / 'backup.sqlite3', configured_production_path=path)
    assert receipt['schema_version'] == '0.2.4'
    assert (tmp_path / 'backup.sqlite3').read_bytes() == before
    frozen = path.read_bytes()
    db.init_schema()
    assert path.read_bytes() == frozen
    with db.connect() as c:
        require_schema(c)
        claim = dict(c.execute('SELECT * FROM claims').fetchone())
        assert all(claim[k] == v for k, v in before_claim.items())
        assert claim['admission_semantics'] == claim['reality_support'] == claim['current_view_use'] == 'LEGACY_UNKNOWN'
        assert before_view == dict(c.execute('SELECT * FROM current_views').fetchone())
        for evidence in ([], ['C'], ['MISSING']):
            with pytest.raises(sqlite3.IntegrityError, match='CURRENT_VIEW_REVIEWED_BASIS_REQUIRED'):
                c.execute("INSERT INTO current_views(view_id,node_id,version,change_level,content_md,content_json,created_at) VALUES('V2','N','2','initial','new',?,'t')",
                          (json.dumps({'evidence_claim_ids': evidence}),))
        with pytest.raises(sqlite3.IntegrityError, match='CURRENT_VIEW_REVIEWED_BASIS_REQUIRED'):
            c.execute("UPDATE current_views SET content_md='replacement' WHERE view_id='V'")
        c.execute("INSERT INTO current_views(view_id,node_id,version,status,change_level,content_md,created_at) VALUES('D','N','2','draft','initial','draft','t')")
        with pytest.raises(sqlite3.IntegrityError, match='CURRENT_VIEW_REVIEWED_BASIS_REQUIRED'):
            c.execute("UPDATE current_views SET status='official' WHERE view_id='D'")
        with pytest.raises(sqlite3.IntegrityError):
            c.execute("UPDATE claims SET reality_support='PROVIDER_VERIFIED' WHERE claim_id='C'")
        c.execute('DROP TRIGGER admission_view_insert')
        with pytest.raises(PromotionError, match='GUARD_DRIFT'):
            require_schema(c)


def test_unverified_attempts_and_reviewers_cannot_supply_independent_reality_support():
    from pro_a.propagation import PropagationManager
    from pro_a.analyzer import Analyzer
    source = {'claim_id': 'C_SYNTHETIC', 'source_id': 'SOURCE_SYNTHETIC',
              'admission_semantics': 'SOURCE_ASSERTION', 'reality_support': 'UNVERIFIED',
              'current_view_use': 'CLUE_ONLY', 'admission_basis_sha256': 'a' * 64}
    attempts = [{**source, 'attempt_id': 'ATTEMPT_' + str(i), 'reviewer_id': 'MODEL_' + str(i)} for i in range(2)]
    repost = {**source, 'source_id': 'REPOST_SYNTHETIC', 'underlying_source_id': 'SOURCE_SYNTHETIC'}
    primary = {**source, 'underlying_source_id': 'SOURCE_SYNTHETIC'}
    assert len({PropagationManager._independence_key(c) for c in attempts}) == 1
    assert PropagationManager._independence_key(primary) == PropagationManager._independence_key(repost)
    # These guards must reject before consulting a model or elevated thresholds.
    for level in ('initial', 'minor', 'material', 'thesis'):
        assert PropagationManager._programmatic_evidence_sufficiency(None, level, attempts, {}) == (
            False, 'CURRENT_VIEW_REVIEWED_BASIS_REQUIRED')
    with pytest.raises(ValueError, match='IMPACT_REVIEWED_BASIS_REQUIRED'):
        Analyzer.review_impact(None, {}, '', attempts, {})
