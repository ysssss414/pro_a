# Phase 4.3 Stage 4A — Qualification

**Result: PASS for the read-only Stage 4A navigation scope.** The starting and frozen remote baseline is `3e1f063135c90c031875762d1e77e3e72cf1a212` (PR #65 merge). Local `main` was safely fast-forwarded to that commit; the Stage 4A branch was created from it. Tracked and staged changes were zero before implementation. Pre-existing untracked material remained in place and was not recursively inventoried, copied, or cleaned.

The qualified implementation commit is `a6b0127fa056c571744055ebdee900f4ecab252b`; its sole parent is the frozen baseline. The machine-readable receipt binds this code commit. The subsequent documentation commit does not change implementation behavior.

## Root selection and pack identity

| Navigation domain | Exact active Production root | Visible Nodes | Maximum depth | Truncated | Tracked Domain Pack |
| --- | --- | ---: | ---: | --- | --- |
| AI Hardware | `NODE_20260814_164548FF` (`算力`, Industry) | 4 | 1 | No | `ai_hardware` v1.0.0, SHA256 `2b287b6e7e0e95585b1f466c8481053544e3bbc92e5d8a17e180c5cdd4a5ade2` |
| Semiconductor | `NODE_20260814_2CF1006E` (`半导体`, Industry) | 5 | 2 | No | `semiconductor` v1.0.0, SHA256 `d7e3b2a81353aa51d150b7858b931546cde1358c7fbcf559e4ef08d094c849c4` |

Both roots were verified `active` in Production. The canonical child rule is current `part_of`, child `from_node_id` to parent `to_node_id`. `算力` has three immediate current children. `半导体` has three immediate children, and `封装` has `CoWoS` underneath. The `AI算力` Theme has no current children; other AI Hardware segments remain disconnected from `算力` in current Production. They were not inserted into this tree by name, operational assignment, or un-applied Stage 3 proposals. Thus the AI Hardware navigation slice is intentionally sparse and does not claim a complete industry taxonomy.

The local Workbench state is schema **8** and has no `domain_pack_registry`. Both tracked Domain Pack descriptors have lifecycle **PROPOSED**, with no qualification references. Stage 4A binds their exact descriptor identities in its independent presentation specs and reports `domain_pack_registered=false` and `domain_pack_lifecycle=PROPOSED`. No operational qualification or assignment is inferred. If a registry is present in a later Workbench, the read projection verifies its identity and rejects drift. No Domain Pack or Workbench metadata was modified.

The exact spec format, hierarchy semantics, API fields, limits, and UI URL contract are in [PHASE43_STAGE4A_DOMAIN_HIERARCHY_CONTRACT.md](PHASE43_STAGE4A_DOMAIN_HIERARCHY_CONTRACT.md). Spec SHA256 values are `5c63310e2bf2775a7c0d8222f91ec921f0e1056023181ccbd305ff7aacfcfe9e` (AI Hardware) and `2322cd60e5522782c3f9d1e2aafd7c2a87dd0967f4d2b5661aa086c212af0263` (Semiconductor).

## Verification

| Check | Result |
| --- | --- |
| Stage 4A projection and API focused tests | 8 passed |
| Stage 4A focused, Research Explorer, Workbench Stage 0, Domain Pack Stage 0, and canonical API regression | 212 passed after the final registry-row adjustment |
| Stage 3 auxiliary regression applicable on Stage 4A branch | 51 passed, 1 branch-pinned test deselected |
| Frontend full suite | 129 passed across 22 files |
| TypeScript and frontend production build | Passed (`npm run build`) |
| Python `compileall src/pro_a` | Passed |
| `git diff --check` | Passed |

One auxiliary Stage 3 test, `test_production_immutable_during_read_only_binding_when_available`, explicitly requires the current branch name to be `codex/phase43-stage3-cross-domain-resolution`. It fails with `branch drift` on the intentionally new Stage 4A branch. The test was kept unchanged. The remaining Stage 3 tests passed with that branch-specific case deselected. This is not a Stage 4A behavior failure.

Real browser acceptance used the existing local Workbench API and Vite app. At **1920×1080** and **1366×768**, the Industry Explorer rendered without document horizontal overflow. Domain switching, branch expansion, node selection, Inspector update, deep-link refresh, Back/Forward, classic Explorer, and the existing `/node/{id}` route were verified. The selected CoWoS path expanded correctly after refresh and Forward. At 1366×768 the Inspector had a 570-pixel viewport and 1,798-pixel content; scrolling reached the bottom. Production contains only 4 and 5 Nodes in these slices, so long-tree scrolling was stress checked with disposable DOM-only copies in the browser: scroll height 16,605 pixels, scroll top 16,214 pixels, document width 1,366 pixels. Reload restored the real canonical tree. The only browser console error was the expected initial unauthenticated session response (401), before local sign-in.

## Safety and gates

Production SHA256 before and after: `6e5a303ccee9c192c350c2550cc232649e56ffee939b7a09cd6b170cc1c8fba1`. Workbench state DB SHA256 before and after: `c28dd60c94deeb8c897c6180b9fec2366ffaef7b671a6c9b0ddf7af9047279f3`. All Stage 4A DB access used read-only SQLite connections. Observed Production writes, Workbench mutations, Apply executions, Official View activations, Current View writes, provider calls, Source ingestion calls, and cloud jobs: **0**. The frozen Stage 3 receipt reports WIP `HARD_STOP`, 274 pending review rows; Stage 4A did not modify that state.

| Gate | Result | Evidence |
| --- | --- | --- |
| A — Baseline | PASS | Exact PR #65 merge and branch parent |
| B — Existing Web preservation | PASS | Existing Research and classic Explorer tests and browser paths |
| C — Spec integrity | PASS | Strict schema, active roots, exact tracked descriptor SHA binding; proposed lifecycle disclosed |
| D — Hierarchy | PASS | Current `part_of`, deterministic sort, depth/node bounds, cycle and duplicate path tests |
| E — Domain semantics | PASS | Navigation paths separate from operational assignment; no inferred membership |
| F — Research integration | PASS | Existing Node presentation reused; deep links and classic Node route verified |
| G — UI usability | PASS | Desktop browser interactions, independent scrolling, no horizontal overflow |
| H — Regression | PASS | Applicable suites, TypeScript, build, compileall; Stage 3 branch-pinned case N/A |
| I — Privacy | PASS | Safe field allowlists and API/path leakage checks |
| J — Production | PASS | Byte-exact SHA, read-only connections, no Apply or activation |
| K — Workbench | PASS | Byte-exact SHA; metadata and WIP untouched |
| L — Scope | PASS | No Stage 4B, 4C, 4D, or industry expansion |

Next: pre-merge audit of the Stage 4A Draft PR. The human user decides whether to close Stage 4A and begin Stage 4B.
