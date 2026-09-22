# Phase 4.3 Stage 4C — Unified Research Inspector qualification

**Result: PASS for the Stage 4C display scope.** The frozen Stage 4B baseline is PR #67 merge `2cbb5b5616ccaeae7d395655c10297653fe99b4d`. Local and remote `main` matched that SHA, tracked and staged changes were zero at start, and `codex/phase43-stage4c-unified-research-inspector` was created directly from it. Qualified implementation commit: `8233dc6e2a862412faa86d9bc066e5aa869e159f` (sole parent: the frozen baseline). Pre-existing untracked material was preserved without recursive inspection or cleanup.

The [Inspector contract](PHASE43_STAGE4C_UNIFIED_RESEARCH_INSPECTOR_CONTRACT.md) fixes section order, selection rules, bounds, empty states, and write boundaries. Industry Explorer and standalone `/node/{id}` use the same `UnifiedResearchInspector` through the retained `ResearchNodeInspector` wrapper. The existing Node and Domain Context endpoints are reused; `BACKEND_DATA_CONTRACT_CHANGED = false`. Current View Workbench is lazily mounted behind a collapsed detail section, and private follow-up notes remain available at the bottom. No Stage 3 qualified overlay is shown.

## Representative real Production Nodes

The richest practical active canonical Node is **MLCC** (`NODE_20260817_DABE52FE`): the read-only Production projection contains 1 official Current View, 11 explicitly linked Claims, 1 Source, and 22 recorded Direct Impact paths. No active Node has a richer combination of View and Claim coverage in the current Production database; the other official-View Node has 8 linked Claims. MLCC has no navigation context, operational assignment, Knowledge Gap, Research Question, Relation, or note, and the UI says so. This selection reflects actual coverage rather than screenshot appearance.

| MLCC Inspector section | Real result |
| --- | --- |
| Identity | Product, active canonical Production Node |
| Navigation contexts / operational assignments | 0 / 0; outside selected navigation tree |
| Current View | `v_20260826`, compact official conclusion and three recorded supporting items |
| Key Claims / Latest Evidence | 3 / 3 initially visible from 11 exact linked Claims |
| Direct Impact / Open Gaps | 3 of 22 paths initially visible / 0 unresolved |
| Research Question / Sources / Relations / Notes | none / 1 / 0 / 0 |
| Research coverage | `LEVEL_3_CANONICAL_VIEW` |

The sparse active canonical Node is **HBM Manufacturing** (`NODE_20260817_DC2545C0`), `LEVEL_0_STRUCTURE_ONLY`. It has no navigation context, official View, Claim, Evidence, Impact, Gap, Question, Source, Relation, or note. All corresponding empty states rendered in the real browser at 1366×768. The AI Hardware root `NODE_20260814_164548FF` separately supplied three recorded `part_of` Relations for the live Relation and map checks.

## Verification

| Check | Result |
| --- | --- |
| Stage 4C pure selection and component tests | 8 passed |
| Industry Explorer and Research Explorer component regressions | 6 + 6 passed |
| Complete frontend suite | 142 passed in 25 files with `--maxWorkers=2` |
| Relevant backend Research, navigation, structure map, Workbench and Current View API regressions | 124 passed |
| Applicable Stage 3 auxiliary tests | 43 passed; 1 older branch-pinned test deselected |
| TypeScript, production build, Python compileall, staged diff check | PASS |

The default highly concurrent Vitest invocation twice hit an existing one-second asynchronous wait under load (once in Research Explorer, once in unrelated Durable Jobs). The touched Research Explorer and Industry Explorer asynchronous assertions now allow five seconds without changing their behavioral checks. The complete suite passed with two workers; no test or gate was skipped. The Stage 3 deselection is the unchanged test that pins an older branch name and is inapplicable on the authorized Stage 4C branch.

Real browser acceptance used only the existing local Production and Workbench data. At **1920×1080**, the Inspector was 572 pixels wide; at **1366×768**, it was 400 pixels wide. In both cases the document scroll width equaled viewport width. At 1366, Direct Impact and Open Gaps stacked vertically. The right Inspector independently scrolled to its bottom (scroll top and maximum both 796 pixels on the sparse Node). The browser exercised domain switch, hierarchy Node selection, real Cytoscape Node and Relation-edge clicks, all three map modes, Focus depth 3, empty relation filter, Fit/Reset, search selection outside the tree, exact Claim/Source/Relation routes, standalone Node summary, Back/Forward, refresh, and rich/sparse Inspector content. Tree expansion was covered by Industry Explorer component tests. MLCC's compact official View was visible with maintenance collapsed; opening details displayed the existing official information without Save, Validate, Qualify, Reconcile, or Note writes.

## Safety, limitations, and gates

Production SHA256 before/after: `6e5a303ccee9c192c350c2550cc232649e56ffee939b7a09cd6b170cc1c8fba1`. Real Workbench SHA256 before/after: `c28dd60c94deeb8c897c6180b9fec2366ffaef7b671a6c9b0ddf7af9047279f3`. No Production write, real Workbench mutation, Apply, official View activation, Current View write, provider call, Source ingestion, raw PDF call, or cloud job was executed. The byte-identical Workbench DB retains the frozen Stage 3 WIP state `HARD_STOP`, 274 pending review rows, and `NEW_INTAKE_ALLOWED = false`.

The existing Node endpoint returns at most 20 Claims and 20 Sources. Its `claims.total` is complete, but its `coverage.sources` currently reflects a bounded Source-ID list. The Inspector explicitly marks a full 20-Source page as `at least 20 (bounded)` and never claims completeness. Source organization is absent from the current Node Source row and appears only if supplied. These are known read-projection limits, with no new backend semantics introduced.

| Gate | Result | Evidence |
| --- | --- | --- |
| A — Baseline | PASS | Exact frozen merge, clean tracked start, direct branch parent |
| B — Stage 4A/4B | PASS | Specs and semantic hash unchanged; tree, map modes, URL state and interactions exercised |
| C — Data truthfulness | PASS | Existing projections only; role and trigger labels explicit; no generated or inferred research |
| D — Summary correctness | PASS | Deterministic helper tests, exact View fields, bounds, gaps, relation counts |
| E — Navigation | PASS | Real Claim, Source, Relation, Node routes and Back/Forward |
| F — Current View boundary | PASS | Compact default, Workbench collapsed/lazy, official details read-only during acceptance |
| G — Sparse data | PASS | Real MLCC rich projection and HBM Manufacturing empty states |
| H — Usability | PASS | 1920 and 1366, independent scroll, stacked pair, no document overflow |
| I — Regression | PASS | 142 frontend, 124 backend, 43 auxiliary, TypeScript, build, compileall |
| J — Privacy | PASS | Tracked/public Stage 4C diff has zero local/private path matches |
| K — Production/Workbench | PASS | Both database SHA256 values unchanged, zero executed mutations |
| L — Scope | PASS | No Stage 4D, qualified overlay, ontology/domain change, provider or ingestion |

Next action: pre-merge audit of the Stage 4C Draft PR. Stage 4D begins only if the human user authorizes it after Stage 4C closure.
