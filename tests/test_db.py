from pathlib import Path

from pro_a.db import Database


def test_node_alias_and_relation(tmp_path: Path):
    db = Database(tmp_path / "x.db")
    db.init_schema()
    a = db.add_node("EML", "Technology", ["电吸收调制激光器"])
    b = db.add_node("光模块", "Segment")
    assert db.find_node_by_name_or_alias("电吸收调制激光器")["node_id"] == a
    db.add_relation(a, "part_of", b)
    neighbors = db.neighbors(a)
    assert neighbors["structural"][0]["other_node_id"] == b
