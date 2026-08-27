import pytest

from pro_a.current_view_compare import (
    CurrentViewCompareValidationError,
    compare_current_views,
)


def view(
    view_id: str,
    content: dict,
    *,
    node_id: str = "NODE_1",
    status: str = "official",
    claims: list[str] | None = None,
    source_id: str | None = "SRC_1",
) -> dict:
    return {
        "view_id": view_id,
        "node_id": node_id,
        "version": f"v_{view_id}",
        "status": status,
        "change_level": "minor",
        "previous_view_id": None,
        "content_json": content,
        "trigger_claim_ids": claims or [],
        "trigger_source_id": source_id,
        "revision_date": "20260101",
        "revision_seq": 0,
    }


def test_exact_scalar_list_and_evidence_diff_preserves_contract_order():
    base = view(
        "V1",
        {
            "one_line_conclusion": "  A  ",
            "investment_implication": "Same ",
            "key_facts": ["F1", "F2", "Wording old", "  "],
            "key_watch_items": ["W1"],
        },
        claims=["C1", "C3"],
    )
    target = view(
        "V2",
        {
            "one_line_conclusion": "B",
            "investment_implication": " Same",
            "key_facts": ["F2", "F3", "Wording changed"],
            "key_watch_items": ["W1", "W2"],
        },
        claims=["C1", "C2"],
    )

    result = compare_current_views(base, target)

    assert result["scalar_changes"] == [
        {"field": "one_line_conclusion", "changed": True, "before": "A", "after": "B"},
        {"field": "investment_implication", "changed": False, "before": "Same", "after": "Same"},
    ]
    assert result["list_changes"]["key_facts"] == {
        "added": ["F3", "Wording changed"],
        "removed": ["F1", "Wording old"],
        "unchanged": ["F2"],
    }
    assert result["list_changes"]["key_watch_items"] == {
        "added": ["W2"], "removed": [], "unchanged": ["W1"]
    }
    assert result["evidence"] == {
        "added": ["C2"], "removed": ["C3"], "unchanged": ["C1"]
    }
    assert result["has_changes"] is True


def test_type_specific_list_scalar_dimension_and_unknown_json_diff():
    base = view("V1", {"type_specific": {
        "demand_drivers": ["D1"],
        "pricing": "Stable ",
        "capacity": ["Old capacity"],
        "unknown": {"a": [1, 2]},
    }})
    target = view("V2", {"type_specific": {
        "demand_drivers": ["D1", "D2"],
        "pricing": " Tight",
        "technology": ["T1"],
        "unknown": {"a": [1, 3]},
    }})

    changes = compare_current_views(base, target)["type_specific_changes"]

    assert changes["demand_drivers"] == {
        "status": "changed", "kind": "list",
        "added": ["D2"], "removed": [], "unchanged": ["D1"],
    }
    assert changes["pricing"] == {
        "status": "changed", "kind": "scalar", "changed": True,
        "before": "Stable", "after": "Tight",
    }
    assert changes["capacity"] == {
        "status": "dimension_removed", "kind": "list",
        "added": [], "removed": ["Old capacity"], "unchanged": [],
    }
    assert changes["technology"] == {
        "status": "dimension_added", "kind": "list",
        "added": ["T1"], "removed": [], "unchanged": [],
    }
    assert changes["unknown"] == {
        "status": "changed", "kind": "json", "changed": True,
        "before": {"a": [1, 2]}, "after": {"a": [1, 3]},
    }


@pytest.mark.parametrize(
    ("base_source", "target_source", "status"),
    [
        ("SRC_1", "SRC_1", "unchanged"),
        (None, "SRC_1", "added"),
        ("SRC_1", None, "removed"),
        ("SRC_1", "SRC_2", "changed"),
    ],
)
def test_trigger_source_delta_has_no_interpretation(base_source, target_source, status):
    result = compare_current_views(
        view("V1", {}, source_id=base_source),
        view("V2", {}, source_id=target_source),
    )
    assert result["trigger_source_change"] == {
        "status": status, "before": base_source, "after": target_source
    }


def test_whitespace_is_the_only_content_normalization():
    result = compare_current_views(
        view("V1", {"key_facts": ["Fact"]}),
        view("V2", {"key_facts": [" Fact ", "Fact."]}),
    )
    assert result["list_changes"]["key_facts"] == {
        "added": ["Fact."], "removed": [], "unchanged": ["Fact"]
    }


def test_compare_rejects_same_view_cross_node_and_non_official():
    with pytest.raises(CurrentViewCompareValidationError, match="different"):
        compare_current_views(view("V1", {}), view("V1", {}))
    with pytest.raises(CurrentViewCompareValidationError, match="same Node"):
        compare_current_views(view("V1", {}), view("V2", {}, node_id="NODE_2"))
    with pytest.raises(CurrentViewCompareValidationError, match="official"):
        compare_current_views(view("V1", {}, status="draft"), view("V2", {}))
