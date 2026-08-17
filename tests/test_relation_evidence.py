from __future__ import annotations

import json
from pathlib import Path

import pytest

from pro_a.cli import main
from pro_a.db import Database, now_iso

from stability_helpers import add_source_and_claim, make_config


def add_claim(db: Database, claim_id: str, node_id: str) -> None:
    add_source_and_claim(
        db,
        source_id=f"SRC_{claim_id}",
        claim_id=claim_id,
        node_id=node_id,
        source_rank="A",
        origin_type="primary",
        confidence=0.90,
    )


def relation_nodes(db: Database) -> tuple[str, str]:
    return (
        db.add_node("Relation From", "Product"),
        db.add_node("Relation To", "Application"),
    )


def test_new_database_initializes_relation_evidence_schema(tmp_path: Path):
    db = Database(tmp_path / "relations.db")
    db.init_schema()

    assert db.one("SELECT value FROM meta WHERE key='schema_version'")["value"] == "0.2.2"
    assert db.one(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='relation_evidence_links'"
    )
    assert {row["name"] for row in db.all("PRAGMA table_info(relation_evidence_links)")} == {
        "relation_id", "claim_id", "evidence_role", "status", "created_at",
    }


def test_part_of_can_be_created_without_evidence(tmp_path: Path):
    db = Database(tmp_path / "relations.db")
    db.init_schema()
    from_node_id, to_node_id = relation_nodes(db)

    relation_id = db.add_relation(from_node_id, "part_of", to_node_id)

    assert db.one("SELECT relation_type,status FROM node_relations WHERE relation_id=?", (relation_id,)) == {
        "relation_type": "part_of",
        "status": "current",
    }
    assert db.relation_evidence(relation_id) == []


def test_non_structural_current_relation_requires_supporting_claim(tmp_path: Path):
    db = Database(tmp_path / "relations.db")
    db.init_schema()
    from_node_id, to_node_id = relation_nodes(db)

    with pytest.raises(ValueError, match="supporting Claim"):
        db.add_relation(from_node_id, "uses", to_node_id)

    assert db.one("SELECT COUNT(*) AS n FROM node_relations")["n"] == 0


def test_relation_rejects_unknown_evidence_claim(tmp_path: Path):
    db = Database(tmp_path / "relations.db")
    db.init_schema()
    from_node_id, to_node_id = relation_nodes(db)

    with pytest.raises(ValueError, match="Unknown evidence Claim: CLM_MISSING"):
        db.add_relation(
            from_node_id,
            "uses",
            to_node_id,
            evidence_claim_id="CLM_MISSING",
        )

    assert db.one("SELECT COUNT(*) AS n FROM node_relations")["n"] == 0


def test_supporting_claim_creates_non_structural_relation_and_link(tmp_path: Path):
    db = Database(tmp_path / "relations.db")
    db.init_schema()
    from_node_id, to_node_id = relation_nodes(db)
    add_claim(db, "CLM_SUPPORT_1", from_node_id)

    relation_id = db.add_relation(
        from_node_id,
        "uses",
        to_node_id,
        evidence_claim_id="CLM_SUPPORT_1",
        scope="AI hardware",
        confidence=0.80,
    )

    relation = db.one("SELECT * FROM node_relations WHERE relation_id=?", (relation_id,))
    assert relation["evidence_claim_id"] == "CLM_SUPPORT_1"
    assert db.relation_evidence(relation_id) == [
        {
            "relation_id": relation_id,
            "claim_id": "CLM_SUPPORT_1",
            "evidence_role": "supports",
            "evidence_status": "active",
            "evidence_created_at": relation["created_at"],
            "source_id": "SRC_CLM_SUPPORT_1",
            "statement": "claim CLM_SUPPORT_1",
            "status": "current",
            "confidence": 0.90,
        }
    ]


def test_existing_relation_accumulates_supporting_claims_without_duplication(tmp_path: Path):
    db = Database(tmp_path / "relations.db")
    db.init_schema()
    from_node_id, to_node_id = relation_nodes(db)
    add_claim(db, "CLM_SUPPORT_1", from_node_id)
    add_claim(db, "CLM_SUPPORT_2", from_node_id)

    first_id = db.add_relation(
        from_node_id, "uses", to_node_id, evidence_claim_id="CLM_SUPPORT_1"
    )
    second_id = db.add_relation(
        from_node_id, "uses", to_node_id, evidence_claim_id="CLM_SUPPORT_2"
    )

    assert second_id == first_id
    assert db.one("SELECT COUNT(*) AS n FROM node_relations")["n"] == 1
    assert [item["claim_id"] for item in db.relation_evidence(first_id)] == [
        "CLM_SUPPORT_1", "CLM_SUPPORT_2",
    ]


def test_repeated_relation_evidence_attach_is_idempotent(tmp_path: Path):
    db = Database(tmp_path / "relations.db")
    db.init_schema()
    from_node_id, to_node_id = relation_nodes(db)
    add_claim(db, "CLM_SUPPORT_1", from_node_id)
    relation_id = db.add_relation(
        from_node_id, "uses", to_node_id, evidence_claim_id="CLM_SUPPORT_1"
    )

    assert db.add_relation_evidence(relation_id, "CLM_SUPPORT_1") is False
    assert db.one("SELECT COUNT(*) AS n FROM relation_evidence_links")["n"] == 1


def test_contradictory_evidence_does_not_retire_relation(tmp_path: Path):
    db = Database(tmp_path / "relations.db")
    db.init_schema()
    from_node_id, to_node_id = relation_nodes(db)
    add_claim(db, "CLM_SUPPORT_1", from_node_id)
    add_claim(db, "CLM_CONTRADICT_1", from_node_id)
    relation_id = db.add_relation(
        from_node_id, "uses", to_node_id, evidence_claim_id="CLM_SUPPORT_1"
    )

    assert db.add_relation_evidence(
        relation_id, "CLM_CONTRADICT_1", evidence_role="contradicts"
    ) is True

    assert db.one("SELECT status FROM node_relations WHERE relation_id=?", (relation_id,)) == {
        "status": "current"
    }
    assert [(item["claim_id"], item["evidence_role"]) for item in db.relation_evidence(relation_id)] == [
        ("CLM_CONTRADICT_1", "contradicts"),
        ("CLM_SUPPORT_1", "supports"),
    ]


def test_legacy_evidence_claim_is_backfilled_idempotently(tmp_path: Path):
    db = Database(tmp_path / "legacy.db")
    db.init_schema()
    from_node_id, to_node_id = relation_nodes(db)
    add_claim(db, "CLM_LEGACY", from_node_id)
    db.execute("DROP TABLE relation_evidence_links")
    db.execute(
        """INSERT INTO node_relations(
           relation_id,from_node_id,relation_type,to_node_id,scope,status,evidence_claim_id,created_at
           ) VALUES(?,?,?,?,?,?,?,?)""",
        (
            "REL_LEGACY",
            from_node_id,
            "uses",
            to_node_id,
            "legacy",
            "current",
            "CLM_LEGACY",
            now_iso(),
        ),
    )
    db.execute("UPDATE meta SET value='0.2.1' WHERE key='schema_version'")

    db.init_schema()
    db.init_schema()

    assert db.one("SELECT value FROM meta WHERE key='schema_version'")["value"] == "0.2.2"
    assert db.all("SELECT relation_id,claim_id,evidence_role,status FROM relation_evidence_links") == [
        {
            "relation_id": "REL_LEGACY",
            "claim_id": "CLM_LEGACY",
            "evidence_role": "supports",
            "status": "active",
        }
    ]


def test_relation_cli_add_evidence_and_show(tmp_path: Path, capsys):
    cfg, db = make_config(tmp_path)
    from_node_id, to_node_id = relation_nodes(db)
    add_claim(db, "CLM_SUPPORT_1", from_node_id)
    add_claim(db, "CLM_CONTRADICT_1", from_node_id)

    main([
        "--config", str(cfg.config_path),
        "relations", "add", from_node_id, "uses", to_node_id,
        "--scope", "AI hardware",
        "--evidence-claim-id", "CLM_SUPPORT_1",
    ])
    relation_id = capsys.readouterr().out.strip()

    main([
        "--config", str(cfg.config_path),
        "relations", "add-evidence", relation_id, "CLM_CONTRADICT_1",
        "--role", "contradicts",
    ])
    capsys.readouterr()
    main(["--config", str(cfg.config_path), "relations", "show", relation_id])
    shown = json.loads(capsys.readouterr().out)

    assert {"scope", "status", "valid_from", "valid_to", "confidence"} <= set(
        shown["relation"]
    )
    assert shown["relation"]["scope"] == "AI hardware"
    assert shown["relation"]["status"] == "current"
    assert shown["from_node"]["node_id"] == from_node_id
    assert shown["to_node"]["node_id"] == to_node_id
    assert {(item["claim_id"], item["evidence_role"]) for item in shown["evidence_claims"]} == {
        ("CLM_SUPPORT_1", "supports"),
        ("CLM_CONTRADICT_1", "contradicts"),
    }
    assert all(
        {"source_id", "statement", "status", "confidence"} <= set(item)
        for item in shown["evidence_claims"]
    )
