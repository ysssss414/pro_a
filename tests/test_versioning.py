from datetime import datetime

from pro_a.ids import dated_version


def test_dated_version():
    dt = datetime(2026, 8, 13, 15, 0)
    assert dated_version([], dt) == "v_20260813"
    assert dated_version(["v_20260813"], dt) == "v_20260813_01"
    assert dated_version(["v_20260813", "v_20260813_01", "v_20260813_02"], dt) == "v_20260813_03"
