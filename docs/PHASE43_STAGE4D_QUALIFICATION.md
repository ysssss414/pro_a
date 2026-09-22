# Phase 4.3 Stage 4D — Qualified overlay qualification

**Result: PASS for the read-only Stage 4D presentation scope.** The branch `codex/phase43-stage4d-qualified-overlay` began clean at the frozen Stage 4C baseline `a86a4005835dd50f55b076914fa4fe202508a458`; local `main`, `origin/main`, HEAD, and branch parent matched it. Pre-existing untracked material was left untouched. The [overlay contract](PHASE43_STAGE4D_QUALIFIED_OVERLAY_CONTRACT.md), [source manifest](phase43_stage4d_overlay_source_manifest.json), [endpoint classification](phase43_stage4d_endpoint_authority.json), and portable [overlay](../research_overlay/phase43_stage3_cross_domain_v1.json) define the authorized result.

## Frozen authority and projection

The builder bound the Stage 3 population `207f4f57f78f0fe0034a3bb17edd38cc911a21cd322ea753ac02edc41a70babb`, completed decisions file `34f91757f881e26f87502e1ae096ec24b8e207d85ba218d5be8179867940ef52`, review file `2ec173f05215e9d62323ff1cde07108fbcf5eab1afcaf6a020ee438875f04a92`, automated resolution `4ee619c8d597f6ffcacb357efd7eddce750b1a2bc6fe3a21c7a9a78f182f4065`, and final Stage 3 receipt. It checked all 100 exact HUMAN_USER decisions, parent-item hashes, candidate-content hashes, and active REUSE targets. The Stage 2 HUMAN_USER authorization SHA is `23fa6c94d55caf7ef8cfc3291528d3d41a06948460b852d7418c68f572bf014f`; the frozen Semiconductor package SHA is `131421d3bbe3b968a1c72ee6e3767cfad6141a0cdaea1850ba30cccbd3932918`. The 17 Stage 2 endpoint-support IDs and 26 remaining relation-scoped reference IDs independently matched the user's exact frozen sets.

| Decision or presentation class | Verified count |
| --- | ---: |
| Stage 3 identity REUSE / CREATE / DEFER / REJECT | 19 / 12 / 14 / 1 |
| Unique active canonical REUSE targets | 19 |
| Stage 2 HUMAN_USER CREATE endpoint-support identities | 17 |
| Stage 3 relation CREATE / DEFER | 38 / 16 |
| Qualified relations with full identity authority / reference backing | 17 / 21 |
| Relation endpoint occurrences / unique references | 76 / 26 |
| Unresolved or ambiguous endpoints / unrenderable relations | 0 / 0 |

The canonical sanitized overlay SHA256 is `aa917e07895d7912e5bfe9c41763af3fbd705127a6fd797e858f1bef2816bfb5`. Two separate builder processes emitted byte-identical overlay, endpoint classification, and manifest files; the overlay file SHA256 was `d3ebb8662c0259e911ea7946d527fed249bc6ca44c2445c4a912d45b93ba722d`. Replay adds no duplicate identity or relation and changes no existing qualified identity. The API exposes the overlay SHA and fails closed on bound Production, source-authority, file, or projection drift.

Representative frozen records: `SC-CN-0032` REUSE annotates exactly one existing canonical Advanced Packaging Node, `NODE_20260817_4452D283`. `SC-CN-0033` Chiplet is a Stage 3 Qualified identity with no Production ID or Official Current View. `SC-RL-0027` is a HUMAN_USER-qualified `uses` relation from Stage 2 Qualified `SC-CN-0034` Czochralski Crystal Growth to relation-scoped `SC-CN-0024` Polysilicon; its reference endpoint has no independent identity qualification. Deferred `OBS_656B35D110452867` (2.5D integration) appears in governance and not in the map. Sixteen deferred relations and the one rejected identity also create no graph element.

## Verification

| Check | Result |
| --- | --- |
| Stage 4D focused builder, map, drift, authenticated API tests | 4 passed |
| Relevant backend navigation, map, Current View API, Stage 2/3 integrity and Stage 4D tests | 79 passed; 3 deselected |
| Complete frontend suite, including Stage 4A/4B/4C and Stage 4D components | 145 passed in 26 files (`--maxWorkers=2`) |
| TypeScript and frontend production build | PASS; existing bundle-size advisory only |
| Python compileall and Git diff check | PASS |
| Determinism and idempotent builder replay | PASS; three output file hashes matched |
| Public Stage 4D JSON path/payload scan | PASS; zero local/private path or provider payload matches |

Two inherited Stage 3 tests pin the old Stage 3 branch and cannot run on the authorized Stage 4D branch. The third deselected Stage 2 test reruns immutable qualification output generation, outside the frozen Stage 4D scope. All other selected backend tests passed. The frontend test initially exposed a race between default-domain initialization and an immediate Knowledge Layer click; the domain effect now reads the current URL before applying its default, and the focused and full suites pass.

Real local-browser acceptance used the frozen read-only Production overlay. At **1366×768** and **1920×1080**, document scroll width equaled viewport width. The browser exercised canonical default, Qualified toggle, map visual states, Stage 2 and Stage 3 Qualified Inspectors, exact qualified relation and dotted endpoint-reference detail, canonical REUSE provenance, qualified search, deferred/rejected governance counts, hierarchy, relationship, Focus depth 3, domain switch, refresh, deep links, Back, and Forward. The right Inspector scrolled independently. The real Stage 2 deep link rendered one qualified identity, one endpoint reference, and one qualified `uses` relation; clicking its edge showed both endpoint authority classes. Reference detail did not launch a research Inspector or create URL selection. The existing 327 active Production Nodes and 174 current Relations retained canonical presentation.

## Safety and gates

Production SHA256 before/after remained `6e5a303ccee9c192c350c2550cc232649e56ffee939b7a09cd6b170cc1c8fba1`. Real Workbench SHA256 before/after remained `c28dd60c94deeb8c897c6180b9fec2366ffaef7b671a6c9b0ddf7af9047279f3`. No Production write, Apply, official View activation, Current View write, real Workbench mutation, provider call, Source ingestion, raw PDF call, cloud job, or web research was executed. The unchanged frozen WIP state is `HARD_STOP`, 274 pending review rows, and new intake disabled. Stage 5 was not started.

| Gate | Result | Basis |
| --- | --- | --- |
| A — Baseline | PASS | Exact Stage 4C SHA, clean tracked start, correct branch parent |
| B — Stage 3 authority | PASS | Exact source hashes, 100 HUMAN_USER decision bindings and expected counts |
| C — Identity overlay | PASS | 19 REUSE annotations, 12 Stage 3 CREATE, 17 bounded Stage 2 support; DEFER/REJECT excluded |
| D — Relation overlay | PASS | 38/38 renderable, 17 full identity / 21 reference-backed, exact frozen direction/type/scope, no deferred edge |
| E — Endpoint safety | PASS | 26 distinct non-identity references, excluded from search/hierarchy/Inspector/Focus root |
| F — Map integration | PASS | Canonical default, bounded hierarchy/relationship/focus, mixed traversal and explicit states |
| G — Inspector | PASS | Canonical Inspector retained, Qualified Inspector, REUSE provenance and qualified edge authority detail |
| H — Governance | PASS | 14 deferred identities, 16 deferred relations, one rejected identity; graph ineligible |
| I — Determinism | PASS | Two byte-identical builds, stable overlay SHA, deterministic map snapshot |
| J — Regression | PASS | 145 frontend, 79 backend, TypeScript, build, compileall and diff check |
| K — Privacy / Production | PASS | Both real database hashes unchanged; public projection contains no local/private path |
| L — Scope | PASS | No promotion, requalification, new ontology/domain, provider/ingestion or Stage 5 |

Next action: pre-merge audit of the Draft PR. Any further product stage requires HUMAN_USER direction after Stage 4D closure.
