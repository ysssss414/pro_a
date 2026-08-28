from __future__ import annotations

from typing import Any


SCALAR_FIELDS = (
    "one_line_conclusion",
    "investment_implication",
)

LIST_FIELDS = (
    "core_logic",
    "key_facts",
    "core_disagreements",
    "assumptions_to_verify",
    "major_risks",
    "knowledge_gaps",
    "key_watch_items",
)


class CurrentViewCompareValidationError(ValueError):
    """The requested Current View pair cannot be compared safely."""


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _stable_unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))


def _content_items(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return _stable_unique([
        item.strip()
        for item in value
        if isinstance(item, str) and item.strip()
    ])


def _claim_refs(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return _stable_unique([
        item for item in value if isinstance(item, str) and item
    ])


def _list_delta(base: list[str], target: list[str]) -> dict[str, list[str]]:
    base_set = set(base)
    target_set = set(target)
    return {
        "added": [item for item in target if item not in base_set],
        "removed": [item for item in base if item not in target_set],
        "unchanged": [item for item in target if item in base_set],
    }


def _scalar_delta(base: Any, target: Any) -> dict[str, Any]:
    before = _text(base)
    after = _text(target)
    return {
        "changed": before != after,
        "before": before,
        "after": after,
    }


def _is_string_list(value: Any) -> bool:
    return isinstance(value, list) and all(isinstance(item, str) for item in value)


def _dimension_delta(
    base_exists: bool,
    base_value: Any,
    target_exists: bool,
    target_value: Any,
) -> dict[str, Any]:
    if not base_exists:
        status = "dimension_added"
    elif not target_exists:
        status = "dimension_removed"
    else:
        status = "unchanged" if base_value == target_value else "changed"

    if (not base_exists or _is_string_list(base_value)) and (
        not target_exists or _is_string_list(target_value)
    ):
        delta = _list_delta(
            _content_items(base_value) if base_exists else [],
            _content_items(target_value) if target_exists else [],
        )
        if base_exists and target_exists:
            status = "changed" if delta["added"] or delta["removed"] else "unchanged"
        return {"status": status, "kind": "list", **delta}

    if (not base_exists or isinstance(base_value, str)) and (
        not target_exists or isinstance(target_value, str)
    ):
        before = _text(base_value) if base_exists else None
        after = _text(target_value) if target_exists else None
        if base_exists and target_exists:
            status = "changed" if before != after else "unchanged"
        return {
            "status": status,
            "kind": "scalar",
            "changed": before != after,
            "before": before,
            "after": after,
        }

    before = base_value if base_exists else None
    after = target_value if target_exists else None
    if base_exists and target_exists:
        status = "changed" if before != after else "unchanged"
    return {
        "status": status,
        "kind": "json",
        "changed": before != after,
        "before": before,
        "after": after,
    }


def _type_specific_delta(base: Any, target: Any) -> dict[str, dict[str, Any]]:
    base_dimensions = base if isinstance(base, dict) else {}
    target_dimensions = target if isinstance(target, dict) else {}
    keys = sorted(set(base_dimensions) | set(target_dimensions))
    return {
        key: _dimension_delta(
            key in base_dimensions,
            base_dimensions.get(key),
            key in target_dimensions,
            target_dimensions.get(key),
        )
        for key in keys
    }


def _source_delta(base: Any, target: Any) -> dict[str, Any]:
    before = base if isinstance(base, str) and base else None
    after = target if isinstance(target, str) and target else None
    if before == after:
        status = "unchanged"
    elif before is None:
        status = "added"
    elif after is None:
        status = "removed"
    else:
        status = "changed"
    return {"status": status, "before": before, "after": after}


def _view_metadata(view: dict[str, Any], *, target: bool = False) -> dict[str, Any]:
    result = {
        "view_id": view.get("view_id"),
        "version": view.get("version"),
        "revision_date": view.get("revision_date"),
        "revision_seq": view.get("revision_seq"),
        "change_level": view.get("change_level"),
    }
    if target:
        content = view.get("content_json")
        result["previous_view_id"] = view.get("previous_view_id")
        result["recent_change"] = _text(
            content.get("recent_change") if isinstance(content, dict) else None
        )
    return result


def compare_view_content(base_content: Any, target_content: Any) -> dict[str, Any]:
    """Pure content diff; neither value is represented as an official View record."""
    base_content = base_content if isinstance(base_content, dict) else {}
    target_content = target_content if isinstance(target_content, dict) else {}

    scalar_changes = [
        {"field": field, **_scalar_delta(base_content.get(field), target_content.get(field))}
        for field in SCALAR_FIELDS
    ]
    list_changes = {
        field: _list_delta(
            _content_items(base_content.get(field)),
            _content_items(target_content.get(field)),
        )
        for field in LIST_FIELDS
    }
    type_specific_changes = _type_specific_delta(
        base_content.get("type_specific"),
        target_content.get("type_specific"),
    )
    return {
        "scalar_changes": scalar_changes,
        "list_changes": list_changes,
        "type_specific_changes": type_specific_changes,
        "has_changes": (
            any(change["changed"] for change in scalar_changes)
            or any(change["added"] or change["removed"] for change in list_changes.values())
            or any(change["status"] != "unchanged" for change in type_specific_changes.values())
        ),
    }


def compare_current_views(
    base_view: dict[str, Any],
    target_view: dict[str, Any],
) -> dict[str, Any]:
    """Compare BASE → TARGET using exact structured Current View values only."""
    if base_view.get("status") != "official" or target_view.get("status") != "official":
        raise CurrentViewCompareValidationError("Only official Current Views can be compared")
    if base_view.get("node_id") != target_view.get("node_id"):
        raise CurrentViewCompareValidationError("Current Views must belong to the same Node")
    if base_view.get("view_id") == target_view.get("view_id"):
        raise CurrentViewCompareValidationError("Base and target Current Views must be different")

    content_diff = compare_view_content(base_view.get("content_json"), target_view.get("content_json"))
    evidence = _list_delta(
        _claim_refs(base_view.get("trigger_claim_ids")),
        _claim_refs(target_view.get("trigger_claim_ids")),
    )
    trigger_source_change = _source_delta(
        base_view.get("trigger_source_id"),
        target_view.get("trigger_source_id"),
    )
    has_changes = (
        content_diff["has_changes"]
        or bool(evidence["added"] or evidence["removed"])
        or trigger_source_change["status"] != "unchanged"
    )
    return {
        "node_id": base_view.get("node_id"),
        "base": _view_metadata(base_view),
        "target": _view_metadata(target_view, target=True),
        **content_diff,
        "evidence": evidence,
        "trigger_source_change": trigger_source_change,
        "has_changes": has_changes,
    }
