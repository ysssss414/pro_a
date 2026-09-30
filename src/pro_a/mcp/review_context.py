"""Read composition, not a review engine: native validation owns every capability."""
from collections import Counter
import json

from pro_a.production_promotion import canonical_sha256
from pro_a.workbench.foundation_import import is_foundation
from pro_a.workbench.review_workbench import GROUPS, available_actions

from .errors import BridgeError, check_payload
from .reads import DomainReads, ReviewQueueReads
from . import review_schemas as r
from . import schemas as s

MAX_PACKETS = 200
MAX_CANDIDATES = 200
MAX_CANONICAL_NODES = 50
CANONICAL_CLAIMS = 20
QUEUES = ("needs_review", "high_attention", "entity_resolution", "parent_placement", "deferred", "completed")


def queue(service, selected, limit, offset):
    version = service._workbench()
    # Bound native validation work as well as the eventual response.
    with service.reviews.store.connect() as connection:
        columns = {row[1] for row in connection.execute('PRAGMA table_info(registered_packets)')}
        where = " WHERE artifact_kind='REVIEW_PACKET'" if 'artifact_kind' in columns else ''
        count = connection.execute('SELECT COUNT(*) FROM registered_packets' + where).fetchone()[0]
    if count > MAX_PACKETS:
        raise BridgeError("PAYLOAD_LIMIT_EXCEEDED")
    headers = service.reviews.artifacts.listing()
    if len(headers) != count:
        # Never rebuild a missing Stage 1 projection from a read endpoint.
        raise BridgeError("REVIEW_QUEUE_UNAVAILABLE")
    packets = []
    for header in headers:
        raw = service.reviews.read(header["artifact_id"])
        review = raw["review"]
        counts = {name: 0 for name in QUEUES}
        if review["enabled"]:
            if version in ("10", "11", "12"):
                # Preserve native scale/lifecycle filtering, including schema 11 closures.
                projection = ReviewQueueReads(service.config)
                counts = {name: projection.page(raw["artifact_id"], queue=name, limit=1)["filtered_total"]
                          for name in QUEUES}
            else:
                counts = {name: sum(name in row["queues"] for row in review["rows"]) for name in QUEUES}
        matches = [name for name in QUEUES if counts[name]]
        if selected != "all" and selected not in matches:
            continue
        packets.append(r.QueuePacket.model_validate({**raw, "candidate_type_counts": dict(Counter(
            row["candidate_type"] for row in raw["items"])), "queue_counts": counts, "matching_queues": matches}))
    return r.ReviewQueue(queue=selected, items=packets[offset:offset + limit], limit=limit,
                         next_cursor=str(offset + limit) if offset + limit < len(packets) else None)


def frozen_run(service, dto, version):
    result = r.FrozenRun(run_id=dto["run_id"])
    if version not in ("8", "9", "10", "11", "12"):
        return result
    with service.reviews.store.connect() as connection:
        rows = connection.execute('''SELECT processing_run_id,source_id,runtime_json
            FROM source_processing_runs WHERE packet_artifact_id=?''', (dto["artifact_id"],)).fetchall()
        if len(rows) > 1:
            raise BridgeError("REVIEW_CONTEXT_UNAVAILABLE")
        if rows:
            row = rows[0]
            if row["source_id"] != dto["source"]["source_id"]:
                raise BridgeError("READ_BOUNDARY_VIOLATION")
            context = DomainReads(service.config).read(row["processing_run_id"], connection=connection) or {}
            runtime = json.loads(row["runtime_json"])
            result.processing_run_id = row["processing_run_id"]
            result.frozen_context = s.FrozenContext(contract_version=context.get("contract_version"),
                context_sha256=context.get("context_sha256"), runtime_sha256=runtime.get("runtime_sha256"))
    return result


def canonical_node(service, node_id):
    raw = service.query.node_detail(node_id)
    if raw is None:
        return r.CanonicalNode(node_id=node_id, resolution="NOT_FOUND")
    claims = service.query.node_claims(node_id)
    view = service.query.node_current_view(node_id)
    result = r.CanonicalNode(node_id=node_id, resolution="CANONICAL", identity=raw, aliases=raw["aliases"],
        current_view=s.CurrentView(node_id=node_id, status="OFFICIAL" if view else "NO_OFFICIAL_VIEW", current_view=view),
        claims=claims[:CANONICAL_CLAIMS], has_more_claims=len(claims) > CANONICAL_CLAIMS)
    check_payload(result)
    return result


def basis(service, artifact_id, projection, expected):
    version = service._workbench()
    service._production()
    blank, _, dto, _ = service.reviews._context(artifact_id)
    if is_foundation(blank):
        # Foundation has its own native review authority and candidate vocabulary.
        raise BridgeError("REVIEW_CONTEXT_UNAVAILABLE")
    native = [row for group in GROUPS for row in blank[group]]
    if len(native) > MAX_CANDIDATES:
        raise BridgeError("PAYLOAD_LIMIT_EXCEEDED")
    enabled = version != "1"
    stateful = service.reviews.read(artifact_id)["review"] if projection == "stateful" else None
    states = {row["candidate_id"]: row for row in (stateful or {}).get("rows", [])}
    candidates = []
    for row in native:
        content = r.CandidateContent.model_validate(row["content"])
        if row["candidate_type"] not in ("CLAIM", "NODE", "PARENT_PLACEMENT"):
            raise BridgeError("REVIEW_CONTEXT_UNAVAILABLE")
        # Critical: no stateful read or capability post-filtering on the blind path.
        capability = (states[row["candidate_id"]] if projection == "stateful" and enabled else
                      available_actions(blank, row, {}) if enabled else
                      {"available_decisions": [], "blocked_decisions": {}})
        node_ids = set(content.exact_production_resolution.candidate_target_node_ids
                       if content.exact_production_resolution else [])
        if content.parent_node_id:
            node_ids.add(content.parent_node_id)
        supporting = set(content.supporting_claim_ids)
        if content.child_node_candidate_id:
            supporting.add(content.child_node_candidate_id)
        candidate = r.Candidate(candidate_id=row["candidate_id"], candidate_type=row["candidate_type"],
            content_sha256=row["content_sha256"], content=content, allowed_decisions=row["allowed_decisions"],
            available_decisions=capability["available_decisions"], blocked_decisions=capability["blocked_decisions"],
            canonical_node_ids=sorted(node_ids), supporting_candidate_ids=sorted(supporting))
        check_payload(candidate)
        candidates.append(candidate)
    ids = sorted({ref for candidate in candidates for ref in candidate.canonical_node_ids})
    if len(ids) > MAX_CANONICAL_NODES:
        raise BridgeError("PAYLOAD_LIMIT_EXCEEDED")
    nodes = {node_id: canonical_node(service, node_id) for node_id in ids}
    source = r.PacketSource.model_validate(dto["source"])
    canonical = service.query.source_detail(source.source_id)
    if canonical:
        source.canonical = s.SourceMetadata.model_validate(canonical)
    run = frozen_run(service, dto, version)
    identity = r.ContextIdentity.model_validate({**dto, "projection": projection, "context_sha256": "",
        "review_enabled": enabled, "disabled_reason": None if enabled else "REVIEW_SCHEMA_REQUIRED",
        "source": source, "run": run,
        "review": stateful, "states": {key: value["state"] for key, value in states.items() if value["state"]},
        "warnings": (["NO_FROZEN_PROCESSING_CONTEXT"] if not run.frozen_context.context_sha256 else [])})
    check_payload(identity)
    # Whole packet scope: pagination only changes presentation. Item reads compute
    # the same basis, including all bounded canonical evidence shown by either tool.
    semantic = identity.model_dump(mode="json", exclude={"artifact_id", "context_sha256"})
    if semantic["review"]:
        semantic["review"].pop("basis_id", None)  # incorporates random registry handle
    identity.context_sha256 = canonical_sha256({"identity": semantic,
        "candidates": [item.model_dump(mode="json") for item in candidates],
        "canonical_nodes": [nodes[key].model_dump(mode="json") for key in ids]})
    if expected is not None and expected != identity.context_sha256:
        raise BridgeError("REVIEW_CONTEXT_CHANGED")
    return identity, candidates, nodes


def packet_context(service, artifact_id, projection, limit, offset, expected):
    identity, candidates, nodes = basis(service, artifact_id, projection, expected)
    page = candidates[offset:offset + limit]
    compact = [item.model_copy(update={"content": item.content.model_copy(update={
        "evidence_excerpt": None, "supporting_evidence": []})}) for item in page]
    refs = {node_id for item in page for node_id in item.canonical_node_ids}
    return r.ReviewContext(**identity.model_dump(), items=compact,
        canonical_identities=[nodes[key].identity for key in sorted(refs) if nodes[key].identity],
        total_candidates=len(candidates), limit=limit,
        next_cursor=str(offset + limit) if offset + limit < len(candidates) else None)


def item_context(service, artifact_id, candidate_id, projection, expected):
    identity, candidates, nodes = basis(service, artifact_id, projection, expected)
    by_id = {item.candidate_id: item for item in candidates}
    if candidate_id not in by_id:
        raise BridgeError("REVIEW_CANDIDATE_NOT_FOUND")
    item = by_id[candidate_id]
    # Follow only explicit packet support/dependency IDs, with a visited set.
    related = set()
    pending = list(item.supporting_candidate_ids)
    while pending:
        key = pending.pop()
        if key in by_id and key != candidate_id and key not in related:
            related.add(key)
            pending.extend(by_id[key].supporting_candidate_ids)
    supporting = [candidate for candidate in candidates if candidate.candidate_id in related]
    refs = {key for candidate in [item, *supporting] for key in candidate.canonical_node_ids}
    return r.ReviewItemContext(**identity.model_dump(), item=item, supporting_candidates=supporting,
                              canonical_nodes=[nodes[key] for key in sorted(refs)])
