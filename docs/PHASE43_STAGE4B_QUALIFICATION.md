# Phase 4.3 Stage 4B — Semantic Structure Map qualification

**Result: PASS for the Stage 4B read-only scope.** The frozen Stage 4A baseline is PR #66 merge `d602addbb3c24d3889025b1219bbe6d746a3299b`. Local `main` was verified as an ancestor and advanced to that exact commit without checking it out. The Stage 4B branch was created from it with zero tracked or staged modifications. Pre-existing untracked material remained in place and was not recursively inventoried or cleaned. Qualified implementation commit: `8dfdf9da230435d4913527c54a525e0921998b75` (sole parent: frozen baseline).

The endpoint, traversal, group mapping, bounds, layout, and URL behavior are specified in [PHASE43_STAGE4B_SEMANTIC_STRUCTURE_MAP_CONTRACT.md](PHASE43_STAGE4B_SEMANTIC_STRUCTURE_MAP_CONTRACT.md). The two Stage 4A navigation specs were unchanged: AI Hardware SHA256 `5c63310e2bf2775a7c0d8222f91ec921f0e1056023181ccbd305ff7aacfcfe9e`; Semiconductor SHA256 `2322cd60e5522782c3f9d1e2aafd7c2a87dd0967f4d2b5661aa086c212af0263`. The presentation-only semantic grouping SHA256 is `95ce62199e1643f25fe771280fd037a923954fdb0aa6179413887b5cca5bcebd`.

## Representative current Production maps

The defensible representatives are the two exact Stage 4A active navigation roots. Counts include only active Nodes and current canonical Relations; all maps are untruncated. `Focus` below uses depth 2.

| Navigation root | Hierarchy Nodes / Relations | Relationship Nodes / Relations | Focus depth 2 Nodes / Relations |
| --- | ---: | ---: | ---: |
| AI Hardware: `NODE_20260814_164548FF` (`算力`) | 4 / 3 | 4 / 3 | 4 / 3 |
| Semiconductor: `NODE_20260814_2CF1006E` (`半导体`) | 5 / 4 | 4 / 3 | 5 / 4 |

Every map is byte-stable for identical inputs and exposes its own snapshot ID in the machine-readable receipt. Production has **327 active Nodes and 174 current Relations**; all 174 current Relations are `part_of`. Existing categorical Relations visible in the Research Inspector are deliberately absent from the default Stage 4B maps. Thus Supply / Flow, Dependency, Competition, and Related filters can truthfully yield an empty view on current Production. The Stage 3 qualified candidates remain unapplied and are not displayed as canonical.

## Verification

| Check | Result |
| --- | --- |
| Stage 4B focused projection and authenticated API tests | 4 passed within the relevant backend suite |
| Stage 4A navigation, Research Explorer, Workbench API, canonical API, and Stage 4B combined backend regression | 215 passed |
| Applicable Stage 3 auxiliary regression | 43 passed; 1 branch-pinned test deselected |
| Frontend complete suite | 133 passed in 23 files |
| TypeScript and Vite production build | PASS |
| Python compileall and staged diff whitespace check | PASS |

The deselected Stage 3 test `test_production_immutable_during_read_only_binding_when_available` hardcodes the Stage 3 branch name. It fails with `branch drift` on any subsequent phase branch. It was preserved unchanged; all applicable Stage 3 tests passed.

Real local-browser acceptance used the existing Workbench API and Vite application. At **1920×1080**, the three pane widths were 406 / 867 / 572 pixels. At **1366×768**, they were 284 / 606 / 400 pixels. Both had document scroll width equal to viewport width. The browser exercised both domain selectors, tree expansion, all three modes, Focus depth 3, relation filters and empty-filter state, actual Cytoscape Node and edge clicks, bounded relation detail and existing Relation route, Fit / Reset, search selection outside the navigation tree, Research Inspector updates, refresh, Back / Forward, and deep links. The Inspector independently scrolled to 1,547 of 1,548 pixels at 1366 width. Current trees are short, so left-pane stress used disposable DOM-only copies: tree scroll height 10,004 pixels, client height 391 pixels, scroll top 3,000 pixels, and document width 1,366 pixels. Reload restored the canonical tree. Existing `/research` and classic Explorer routes rendered; the latter retained `GraphPanel`. No post-sign-in browser console errors remained.

## Safety and gates

Production SHA256 before and after: `6e5a303ccee9c192c350c2550cc232649e56ffee939b7a09cd6b170cc1c8fba1`. Workbench DB SHA256 before and after: `c28dd60c94deeb8c897c6180b9fec2366ffaef7b671a6c9b0ddf7af9047279f3`. Production writes, Workbench mutations, Apply executions, Official View activations, Current View writes, provider calls, Source ingestion, raw PDF calls, and cloud jobs: **0**. The frozen Stage 3 receipt reports WIP `HARD_STOP` and 274 pending review rows; the byte-identical Workbench DB confirms Stage 4B left that state unchanged.

| Gate | Result | Evidence |
| --- | --- | --- |
| A — Baseline | PASS | Exact PR #66 merge, clean tracked start, direct branch parent |
| B — Stage 4A preservation | PASS | Specs unchanged; domain tree, search, URL domain/Node state and Inspector retained |
| C — Canonical correctness | PASS | Active/current filters, exact Relation IDs and stored edge direction; no inferred edge |
| D — Three modes | PASS | Hierarchy, direct Relationship, and bounded Focus tested and browser exercised |
| E — Bounds and determinism | PASS | 80 Nodes, 160 Relations, Focus depth 3; cycle, duplicates, truncation, snapshot tests |
| F — Domain truthfulness | PASS | Navigation membership separate; outside-tree Node labeled; no assignment inferred |
| G — Frontend integration | PASS | Three panes; Cytoscape Node/edge clicks; Inspector reuse; URL mode/depth |
| H — Visual usability | PASS | 1920 and 1366, deterministic preset layout, independent scroll, no horizontal overflow |
| I — Regression | PASS | Applicable backend/frontend suites, TypeScript, build, compileall |
| J — Privacy | PASS | Scope path redaction and tracked/public artifact path checks |
| K — Production / Workbench | PASS | Byte-identical DBs, read-only projection, no Apply or View activation |
| L — Scope | PASS | No Stage 4C/4D, overlay, new domain, ontology change, or provider |

Next: pre-merge audit of the Stage 4B Draft PR. After Stage 4B is closed, the human user decides whether to begin Stage 4C.
