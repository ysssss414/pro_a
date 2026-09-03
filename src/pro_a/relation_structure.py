from __future__ import annotations

from collections.abc import Iterable


def directed_path_exists(
    edges: Iterable[tuple[str, str]], start: str, destination: str,
) -> bool:
    """Return whether destination is reachable from start in a directed graph."""
    graph: dict[str, set[str]] = {}
    for source_id, target_id in edges:
        graph.setdefault(source_id, set()).add(target_id)
    pending = [start]
    seen: set[str] = set()
    while pending:
        current = pending.pop()
        if current == destination:
            return True
        if current in seen:
            continue
        seen.add(current)
        pending.extend(graph.get(current, ()))
    return False
