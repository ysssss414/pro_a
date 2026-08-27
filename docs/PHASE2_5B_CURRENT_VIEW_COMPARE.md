# Phase 2.5B — Deterministic Current View Historical Compare

## Closure status

`PHASE2_5B_COMPLETE = true`

Phase 2.5B adds an exact, read-only BASE → TARGET comparison for two official Current Views of the same Node. It does not use an LLM, fuzzy matching, semantic similarity, embeddings, edit-distance heuristics, or generated change interpretation.

## Deterministic contract

- `src/pro_a/current_view_compare.py` is a pure comparator independent of the API handler.
- BASE and TARGET must be different official Views of the same Node. The query layer additionally requires BASE to be older than TARGET using `(revision_date, revision_seq, view_id)` consistent with `CURRENT_VIEW_ORDER`; it never silently reverses a pair.
- `one_line_conclusion` and `investment_implication` use trim-only scalar before/after comparison.
- `core_logic`, `key_facts`, `core_disagreements`, `assumptions_to_verify`, `major_risks`, `knowledge_gaps`, and `key_watch_items` use exact trimmed item equality. Added items retain TARGET order, removed items retain BASE order, and unchanged items retain TARGET order.
- `type_specific` compares canonical dimension keys. String lists use the same exact list contract, strings use exact scalar comparison, and other JSON values use structural equality with raw before/after values.
- `recent_change` is returned only as stored TARGET metadata. The comparator does not generate or substitute a change explanation.
- Stored `change_level` is returned as governance metadata and is never recomputed or interpreted.

## Evidence and Source delta

- Evidence delta uses `current_views.trigger_claim_ids`, not `content_json.evidence_claim_ids`.
- Claim IDs are compared exactly. Added, removed, and unchanged references preserve their contract order.
- The read model deterministically resolves available Claims to statement, status, confidence, Source title, and Source rank.
- Missing Claim references remain in the response with `resolved=false`; they are never silently dropped.
- The default UI shows counts and Claim statement / Source metadata, not raw Claim IDs.
- `trigger_source_id` reports only `added`, `removed`, `changed`, or `unchanged`; no meaning is inferred.

## Read API

```text
GET /api/nodes/{node_id}/current-view-compare
    ?base_view_id=...
    &target_view_id=...
```

The endpoint returns governance metadata, scalar changes, exact list changes, `type_specific` changes, resolved Evidence delta, Trigger Source status, and `has_changes`. Missing Nodes and Views return 404. Same-View, cross-Node, non-official, and reversed pairs return 422. Malformed `content_json` reuses the Phase 2.5A safe `{}` fallback. The connection remains SQLite `mode=ro` with `query_only=ON`; no write endpoint or Production write path was added.

Existing latest and history endpoints remain compatible:

```text
GET /api/nodes/{node_id}/current-view
GET /api/nodes/{node_id}/current-view-history
```

## Explorer behavior

- Compare remains inside the existing Current View version navigation rather than a separate page.
- With at least two revisions, `Compare with previous` defaults TARGET to the selected View and BASE to a valid official `previous_view_id`.
- If that link is absent or invalid, the UI explicitly falls back to the immediately older official revision in history ordering.
- BASE and TARGET selectors expose only chronological BASE → TARGET combinations; reversed selection is blocked rather than silently corrected.
- Presentation shows changed scalar before/after values, exact added/removed list items, Product dimensions through the existing Chinese label mapping, Evidence counts/details, and stored governance metadata.
- Added/removed styles describe membership changes only; they do not encode bullish/bearish meaning.
- API failure remains inside Compare mode, and `Exit Compare` restores the normal Current View. Switching Nodes clears stale compare state.
- A single initial View displays `No previous revision to compare` and does not render a Compare control or empty diff card.

## Isolated fixture acceptance

The temporary SQLite compare fixture covers zero, one, and three official revisions. V1 → V2 validates scalar changes, exact added/removed/unchanged list ordering, Product dimension list changes, Evidence additions, Claim/Source resolution, and unchanged Trigger Source. V2 → V3 validates removals, dimension removal, Trigger Source change, unresolved Claim preservation, and malformed `content_json` fallback.

Invalid pair tests cover identical Views, reversed chronology, another Node, draft/non-official Views, missing Views, and missing Nodes. A SHA-256 before/after assertion verifies that compare queries leave the fixture byte-identical.

## Acceptance

```text
Deterministic comparator = PASS
Scalar diff = PASS
List diff = PASS
Type-specific diff = PASS
Evidence delta = PASS
Claim resolution = PASS
Trigger Source delta = PASS
Official-only = PASS
Same-node enforcement = PASS
Chronological BASE → TARGET enforcement = PASS
Compare API = PASS
Compare UI = PASS
Initial no-history state = PASS
Multi-version fixture = PASS

Frontend tests = PASS (8 files / 23 tests)
Frontend build = PASS (existing bundle-size warning is non-blocking)
Full pytest = PASS (379 passed; 1 existing StarletteDeprecationWarning is non-blocking)
Compileall = PASS
Production browser smoke = PASS (MLCC and 昀冢科技; initial/no-previous state; 0 console errors)

Schema changed = NO
Write API added = NO
Backend write path changed = NO
Production DB changed = NO
Production pre-SHA = 581978E1C587B065A6EEF9C980013AF3DE1A9E8A8781857385404C9F61105250
Production post-SHA = 581978E1C587B065A6EEF9C980013AF3DE1A9E8A8781857385404C9F61105250
Official Current Views = 2
SQLite integrity_check = ok
Foreign-key violations = 0
```

Production has no multi-version Current View history, so it was not mutated to fabricate a compare case. Browser smoke instead verifies that MLCC and 昀冢科技 retain their existing Current Views, Evidence counts, and Source action while showing an accurate initial/no-previous state.

## Deferred

```text
DEFER_CANONICAL_CONTENT_DEDUP = true
DEFER_EVIDENCE_BOUNDARY_CONTENT_QUALITY = true
DEFER_EVIDENCE_QUALITY_METADATA = true
```

AI change summary, semantic matching, Evidence strength scoring, thesis interpretation, automatic `change_level` classification, Current View mutation, proposal generation, Impact Review, propagation, RAG, Ask/chatbot, IMA, and vector search remain outside Phase 2.5B.

`NEXT_PHASE_READY = YES`
