# Phase 4.3 Stage 3 automated qualification

`PHASE43_STAGE3_CROSS_DOMAIN_RESOLUTION = PASS` for the automated Stage 3 scope. `FINAL_HUMAN_QUALIFICATION = PENDING`. This result freezes candidate resolution and a portable review handoff. It performs no canonical promotion, new Source intake, provider call, raw-PDF ingestion, Production apply, or Official View activation.

## Frozen inputs and population

| Input | Identity |
| --- | --- |
| Git baseline | `main = origin/main = 690fc4f26e02607fb54a48053cf8faf6775621c3` at Stage 3 entry |
| AI Hardware canonical input | read-only `workspace/pro_a.db`; SHA-256 `6e5a303ccee9c192c350c2550cc232649e56ffee939b7a09cd6b170cc1c8fba1`; 327 shared canonical Nodes |
| Semiconductor qualified input | private `semiconductor_foundation_backfill_web_pro_v1`; package SHA-256 `131421d3bbe3b968a1c72ee6e3767cfad6141a0cdaea1850ba30cccbd3932918`; 47 files, 163 Node candidates |
| Stage 2 frozen packet | immutable SHA-256 `06006a1c98247f1803dac9cdcd0f10ade5d84beddc56a12e3768e5a9e5bfc66c`, reproduced with the Stage 2 contract's original repository commit |
| Stage 2 HUMAN_USER authorization | 105 exact content-hash bindings validated; the other 169 Stage 2 objects remain without HUMAN_USER attribution |
| Stage 3 comparison population | 46 frozen cross-domain rows, including 43 admitted Node candidates and 3 unadmitted observations; population SHA-256 `207f4f57f78f0fe0034a3bb17edd38cc911a21cd322ea753ac02edc41a70babb` |

The local Production DB and structured input were discovered from Stage 2 receipts, the importer, and the Phase 1.1 import receipt. No private structured input is committed. The Stage 3 artifact store is ignored at `workspace/phase4_stage43_stage3_cross_domain_resolution/qualified_v3/`; it contains the full candidate resolution, evidence-bound review population, and review handoff in `a` and `b`.

## Automated results

| Identity outcome | Count |
| --- | ---: |
| `REUSE_CANONICAL` | 16 |
| `CREATE_NEW_CANONICAL` | 4 |
| `KEEP_DOMAIN_SPECIFIC` | 0 |
| `DEFER` | 25 |
| `REJECT` | 1 |

One exact identity collision/type conflict and two historical quarantine cases remain held. All 46 rows retain the source comparison, candidate reason, catalog retrieval, and target or deferral rationale. `CREATE_NEW_CANONICAL` is a candidate proposal and grants no canonical write authority.

| Relation outcome | Count |
| --- | ---: |
| `REUSE_RELATION` | 0 |
| `CREATE_RELATION` | 38 |
| `KEEP_DOMAIN_SPECIFIC_RELATION` | 0 |
| `DEFER_RELATION` | 16 |
| `REJECT_RELATION` | 0 |

All 54 relation candidates have exactly one outcome and retain native evidence and temporal projection. Two apparent duplicate edges were deferred because their canonical temporal sidecars are `vendor_scoped_2025` while the new candidates are `categorical_source_scoped`. Four ontology-pressure relations are deferred. `CREATE_RELATION` is a candidate proposal requiring human review; no edge was written.

All 19 Claim candidates retain exact Source/hash/evidence and fact/publication time fields. Cross-source leakage is 0. The 100 Stage 3 comparison/relation items are frozen in the review handoff with blank Stage 3 human decisions; all 100 are marked human-required. Existing Stage 2 Workbench WIP remains 274 / `HARD_STOP`, and Stage 3 does not enter the new-intake path. Stage 2 aliases and other objects remain in their original review population, with no Stage 3 alias write or ownership reassignment.

## Gates A–L

| Gate | Result | Evidence |
| --- | --- | --- |
| A Baseline | PASS | Exact Stage 2 packet and 105 human content bindings; Production SHA unchanged. |
| B Input Integrity | PASS | Qualified package inventory and read-only canonical SHA verified; 46-row population hash frozen. |
| C Identity Candidate Retrieval | PASS | Shared canonical/alias catalog lookup, sorted candidate IDs, inspectable reasons; focused tests. |
| D Canonical Resolution | PASS | Exactly one allowed outcome for every comparison row; no silent merge. |
| E Cross-Domain Evidence | PASS | Claim and Source provenance plus temporal fields retained; cross-source leakage 0. |
| F Relation Reconciliation | PASS | All 54 outcomes classified; endpoint/type/scope and temporal-sidecar compatibility checked. |
| G Collision Safety | PASS | Alias owners unchanged; type conflict and quarantine deferred; no canonical registry fork. |
| H Determinism | PASS | Two independent processes produced byte-identical `resolution.json`, `review_population.json`, and `review_handoff.md`. Structural SHA-256 in both: `c1a9150cf43020d293232328316472ae0451efcb160bc7efecec71cafd845113`. |
| I Idempotency | PASS | Replay added 0 files and changed 0 frozen artifacts. |
| J Review Governance | PASS | 100/100 Stage 3 items in portable frozen handoff, no Stage 3 HUMAN_USER decisions, no Workbench intake. |
| K Regression | PASS | Stage 0/1/2 focused regressions; frozen Gold 120/120; clean-checkout backend 2254 passed / 93 skipped; final Stage 3 focused 18/18; compileall PASS. |
| L Production | PASS | SHA before/after `6e5a303ccee9c192c350c2550cc232649e56ffee939b7a09cd6b170cc1c8fba1`; writes 0, apply false, Official View activations 0. |

The clean backend regression checkout intentionally lacked the historical private Phase 3F audit bundle, so 93 tests followed their existing skip rules. The canonical workspace's partial historical Phase 3F bundle causes its strict private-audit prerequisite test to fail because `schema-migration-task.txt` is missing; no private file was invented or deleted. Stage 3's real qualification ran separately in the canonical workspace against its complete Stage 2 input and read-only Production DB. Frontend code was not touched; frontend tests/build were not required for this runtime scope and were not rerun.

The Stage 2 frozen presentation regression exposed one missing final LF in the previously committed public Markdown. The exact frozen byte SHA was restored, and three self-hashed Stage 2 public review files now use LF checkout on Windows. Their decisions, content, and frozen authority remain unchanged.

Next action: Stage 3 AI double review and bounded HUMAN_USER qualification. Stage 4 has not started.
