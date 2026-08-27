# Phase 2.6A — Direct Impact Candidate Discovery

## Closure status

`PHASE2_6A_COMPLETE = true`

Phase 2.6A adds deterministic, read-only discovery of existing Current Views that are directly linked to a Source or Claim through canonical Claim attribution. It discovers candidates for human review only. It does not decide whether a View should change, assign impact strength or direction, create a Proposal, mutate a Current View, or propagate across Relations.

## Deterministic contract

The only eligible path is:

```text
Source → Claim → claim_node_links → active Node → latest official Current View
```

- Existing `subject`, `context`, and `related` roles are preserved exactly; they are not converted to scores.
- A candidate requires an active Node and at least one official Current View.
- Active linked Nodes without an official View are returned separately as `linked_nodes_without_current_view`.
- Inactive Nodes are excluded even when a linked Claim and Current View exist.
- Draft and other non-official Views are never review targets.
- Multiple Claims linked to the same Node produce one Node candidate. Every linked Claim and every distinct role is retained.
- The latest official View is selected with the existing `CURRENT_VIEW_ORDER`: `revision_date DESC, revision_seq DESC, view_id DESC`.
- Candidate order is deterministic: role order `subject`, `context`, `related`, followed by case-insensitive canonical name, canonical name, and Node ID. This is an ordering rule only, not an impact judgment.
- Claims within a candidate use the same role order followed by Claim ID.

No fuzzy matching, LLM relevance, embedding, vector search, semantic similarity, inferred association, Relation traversal, parent/child expansion, or recursive propagation is used.

## Shared read model and API

`ReadOnlyQuery._impact_candidates_for_claims()` owns the shared Source/Claim discovery semantics. The public read models are:

```text
source_impact_candidates(source_id)
claim_impact_candidates(claim_id)
```

The read API exposes:

```text
GET /api/sources/{source_id}/impact-candidates
GET /api/claims/{claim_id}/impact-candidates
```

Missing Sources and Claims return 404. An existing Source with no Claims, or Claims with no canonical Node links, returns 200 with empty candidate arrays. The API retains canonical Claim IDs for traceability, while the default impact presentation does not display them.

Connections remain SQLite URI `mode=ro` with `query_only=ON`. No write endpoint, schema change, or backend write-path change was introduced.

## Explorer behavior

The existing Source Detail now contains a compact `Potential Current View Impact` section:

- candidate count as `Views to review`;
- Node canonical name and type;
- aggregate linked Claim count;
- preserved attribution roles;
- latest official View version and revision date;
- `Open View`, which selects the candidate Node and enters the existing View tab;
- a separate `Linked Nodes without Current View` section when applicable;
- `No directly linked Current Views` for the empty state.

The panel does not copy Current View content, show raw Claim IDs, or use interpretive impact language. Its request lifecycle is isolated from normal Source metadata and Claims: endpoint failure leaves Source Detail usable, and switching Sources clears/aborts stale impact state.

## Isolated fixture acceptance

The temporary SQLite fixture covers:

- Source without Claims;
- Source Claims without Claim–Node links;
- one linked active Node without a View;
- multiple Claims and multiple roles aggregated into one Node candidate;
- one Source linked to multiple Nodes across subject/context/related roles;
- multiple official revisions with the existing latest ordering;
- a newer draft that must not replace the latest official View;
- a draft-only Node classified as no-View;
- an inactive linked Node excluded from both result groups;
- missing Source and Claim 404 contracts;
- Source-level and Claim-level reuse of the same helper;
- byte-identical fixture SHA and unchanged `sqlite_master` before/after discovery.

Frontend tests cover multiple candidates, aggregate Claim count, role presentation, no-View Nodes, empty state, hidden raw impact IDs, endpoint failure isolation, stale Source response cancellation, typed API paths, and direct Open View navigation into the selected Node's View tab.

## Production acceptance

The real Production database contains 2 Sources, 12 Claims, and 2 Current Views. Browser smoke against the existing research Source returned two deduplicated candidates derived only from canonical attribution:

- MLCC — Product — 11 linked Claims — roles `subject`, `context`;
- 昀冢科技 — Company — 8 linked Claims — role `subject`.

Both candidates referenced official `v_20260826`. The default impact panel showed no raw Claim IDs. `Open View` navigated to the existing 昀冢科技 Company View with the View tab selected. Browser console reported 0 errors and 0 warnings; the impact endpoint returned 200. The panel's visual layout passed headed-browser inspection.

## Acceptance

```text
Source impact discovery = PASS
Claim impact discovery = PASS
Claim attribution reuse = PASS
Candidate Node dedup = PASS
Role preservation = PASS
Latest official View selection = PASS
No-View linked Node classification = PASS
Impact API = PASS
Source Detail UI = PASS
Open View navigation = PASS

Frontend tests = PASS (8 files / 27 tests)
Frontend build = PASS (existing bundle-size warning is non-blocking)
Full pytest = PASS (384 passed; 1 existing StarletteDeprecationWarning is non-blocking)
Compileall = PASS
Production browser smoke = PASS

Schema changed = NO
Write API added = NO
Backend write path changed = NO
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

Impact adjudication, no-change/minor/material/thesis decisions, Current View Proposal or mutation, graph propagation, automatic Research Question or Knowledge Gap updates, semantic relevance, evidence scoring, LLM summary, RAG, chatbot, and IMA remain outside Phase 2.6A.

`PHASE2_6B_READY = YES`

Phase 2.6B may define a human review surface only after separate authorization. Phase 2.7 controlled propagation / View Proposal is not authorized.
