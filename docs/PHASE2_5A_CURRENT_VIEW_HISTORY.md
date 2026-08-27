# Phase 2.5A — Current View History & Version Navigation

## Closure status

`PHASE2_5A_COMPLETE = true`

Phase 2.5A adds deterministic, read-only access to official Current View history and lightweight version navigation. It does not implement historical diff or interpretation.

## Architecture

- Schema change: **NO**. Existing `current_views` fields are sufficient; no history table was added.
- Read model: `ReadOnlyQuery.node_current_view_history()` selects one `node_id`, filters `status='official'`, and orders by the shared `CURRENT_VIEW_ORDER`.
- Serialization: latest and history endpoints reuse one serializer. Malformed `content_json` falls back to `{}` and malformed Claim ID JSON falls back to `[]`.
- API: `GET /api/nodes/{node_id}/current-view-history` returns `{ "node_id": "...", "views": [...] }`; missing Node is 404 and an existing Node without an official View returns `views=[]`.
- Compatibility: `GET /api/nodes/{node_id}/current-view` retains its existing response and latest-selection behavior.
- Write boundary: no backend write path or write endpoint was added.

## Explorer behavior

- The first history item remains the default latest official View.
- One version displays `Initial View` and `No previous revision` without an empty timeline.
- Multiple versions use a compact selector and render the selected version through the existing Company/Product `currentViewPresentation` helper.
- Version, change level, revision date, governance metadata, Evidence Claim count, and valid Source action follow the selected version.
- Raw Claim IDs remain hidden by default.
- Node-switch abort and selected-version reset prevent stale history from a previous Node from being displayed.

## Isolated fixture acceptance

The temporary SQLite history fixture covers:

- a Node with zero Views;
- a Node with one initial official View;
- a Node with three chained official revisions;
- shared `revision_date` with `revision_seq` ordering;
- latest, middle, and oldest historical reads;
- malformed `content_json` and Claim ID JSON fallback;
- draft exclusion;
- missing-Node 404 versus empty history;
- byte-identical database state before and after read queries.

## Acceptance

```text
History read model = PASS
History API = PASS
Official-only ordering = PASS
Current-view endpoint compatibility = PASS
Version navigation = PASS
Initial state = PASS
Multi-version isolated fixture = PASS
Company/Product shared presentation = PASS
Stale request protection = PASS

Frontend tests = PASS (8 files / 21 tests)
Frontend build = PASS (existing bundle-size warning is non-blocking)
Full pytest = PASS (367 passed; 1 existing StarletteDeprecationWarning is non-blocking)
Compileall = PASS
Production browser smoke = PASS (MLCC and 昀冢科技; 0 console errors)

Schema changed = NO
Backend write path changed = NO
Write API added = NO
Production DB changed = NO
Production pre-SHA = 581978E1C587B065A6EEF9C980013AF3DE1A9E8A8781857385404C9F61105250
Production post-SHA = 581978E1C587B065A6EEF9C980013AF3DE1A9E8A8781857385404C9F61105250
SQLite integrity_check = ok
Foreign-key violations = 0
```

## Deferred

```text
DEFER_CANONICAL_CONTENT_DEDUP = true
DEFER_EVIDENCE_BOUNDARY_CONTENT_QUALITY = true
DEFER_EVIDENCE_QUALITY_METADATA = true
```

Chatbot/Ask, RAG, vector search, embeddings, recursive graph, write API, automatic Current View mutation, evidence-driven propagation, Impact Review UI, IMA integration, and all Phase 2.5B compare/diff behavior remain outside this phase.

`PHASE2_5B_READY = YES`
