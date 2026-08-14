from __future__ import annotations

import csv
from pathlib import Path

import pytest

from pro_a.cli import main
from pro_a.constants import NODE_TYPES
from pro_a.db import Database

from stability_helpers import make_config


def test_example_node_seed_uses_only_frozen_node_types():
    seed_path = Path(__file__).parents[1] / "config" / "nodes_seed.example.csv"
    with seed_path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))

    assert len(rows) == 41
    assert {row["primary_type"] for row in rows} <= set(NODE_TYPES)


def test_example_graph_seed_creates_expected_counts_and_is_idempotent(tmp_path: Path):
    project_root = Path(__file__).parents[1]
    db = Database(tmp_path / "graph.db")
    db.init_schema()

    assert db.seed_nodes_csv(project_root / "config" / "nodes_seed.example.csv") == 41
    assert db.seed_relations_csv(project_root / "config" / "relations_seed.example.csv") == 25
    assert db.seed_nodes_csv(project_root / "config" / "nodes_seed.example.csv") == 0
    assert db.seed_relations_csv(project_root / "config" / "relations_seed.example.csv") == 0
    assert db.one("SELECT COUNT(*) AS n FROM nodes")["n"] == 41
    assert db.one("SELECT COUNT(*) AS n FROM node_relations")["n"] == 25


def test_relation_seed_resolves_alias_and_is_idempotent(tmp_path: Path):
    db = Database(tmp_path / "relations.db")
    db.init_schema()
    eml_id = db.add_node("EML", "Technology", ["电吸收调制激光器"])
    module_id = db.add_node("光模块", "Segment")
    csv_path = tmp_path / "relations.csv"
    csv_path.write_text(
        "from_name,relation_type,to_name,scope\n"
        "电吸收调制激光器,part_of,光模块,技术归属\n",
        encoding="utf-8",
    )

    assert db.seed_relations_csv(csv_path) == 1
    assert db.seed_relations_csv(csv_path) == 0
    relation = db.one("SELECT * FROM node_relations")
    assert relation["from_node_id"] == eml_id
    assert relation["to_node_id"] == module_id
    assert relation["relation_type"] == "part_of"
    assert relation["scope"] == "技术归属"


def test_relation_seed_missing_node_rolls_back_entire_file(tmp_path: Path):
    db = Database(tmp_path / "relations.db")
    db.init_schema()
    db.add_node("EML", "Technology")
    db.add_node("光模块", "Segment")
    csv_path = tmp_path / "relations.csv"
    csv_path.write_text(
        "from_name,relation_type,to_name,scope\n"
        "EML,part_of,光模块,\n"
        "不存在节点,related_to,光模块,\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match=r"row 3.*不存在节点"):
        db.seed_relations_csv(csv_path)

    assert db.one("SELECT COUNT(*) AS n FROM node_relations")["n"] == 0


def test_relation_seed_rejects_non_frozen_relation_type(tmp_path: Path):
    db = Database(tmp_path / "relations.db")
    db.init_schema()
    db.add_node("EML", "Technology")
    db.add_node("光模块", "Segment")
    csv_path = tmp_path / "relations.csv"
    csv_path.write_text(
        "from_name,relation_type,to_name,scope\n"
        "EML,belongs_to,光模块,\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match=r"row 2.*belongs_to"):
        db.seed_relations_csv(csv_path)


def test_relations_seed_cli_reports_new_count(tmp_path: Path, capsys):
    cfg, db = make_config(tmp_path)
    db.add_node("EML", "Technology", ["电吸收调制激光器"])
    db.add_node("光模块", "Segment")
    csv_path = tmp_path / "relations.csv"
    csv_path.write_text(
        "from_name,relation_type,to_name,scope\n"
        "电吸收调制激光器,part_of,光模块,\n",
        encoding="utf-8",
    )

    main(["--config", str(cfg.config_path), "relations", "seed", str(csv_path)])
    assert "Seeded 1 new relations" in capsys.readouterr().out
    assert db.one("SELECT COUNT(*) AS n FROM node_relations")["n"] == 1
