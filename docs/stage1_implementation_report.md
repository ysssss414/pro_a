# Phase 4.3 Stage 1 implementation report

Stage 1 `OPERATOR_SCALE_AND_BOUNDED_PIPELINE` is implemented and locally accepted. The implementation stays inside the authorized boundary: Workbench-only schema/projection changes, bounded SQLite reads and queues, deterministic batching, catalog lookup correction, and prompt/schema alignment. It performs no Production apply/write, no live provider call, no Stage 2 work, and no ontology extension.

## Result

All ten acceptance gates pass. The final Python suite completed with 2162 passed, 93 skipped, and two third-party deprecation warnings. The frontend suite completed with 124 passed across 21 files; TypeScript and the production Vite build passed. Python `compileall` passed.

The authorized frozen gold regression passed 120/120 using only the frozen manifest and qualification binding manifest. No hidden acceptance truth was read. The frozen manifest, gold freeze receipt, Stage 1 entry re-evaluation, and qualification binding hashes remain unchanged.

Production SHA-256 before and after validation is `6e5a303ccee9c192c350c2550cc232649e56ffee939b7a09cd6b170cc1c8fba1`. No Production apply or migration was executed.

The authorized explicit staging attempt was blocked because Git could not create the linked-worktree `index.lock`. Per the task boundary, no elevation or retry was attempted, so no commit, push, or Draft PR was created.

## Implemented contracts

### Review projection and WIP

Workbench schema v10 adds a rebuildable, explicitly non-authoritative review projection. Native packet and append-only review audit remain authoritative. List reads use deterministic priority keys, keyset cursors bound to a projection snapshot, page size 25 by default and 100 maximum, domain/type/queue filters, and on-demand item detail. Review mutations refresh affected projection state in the same SQLite transaction, so expected-revision enforcement and cursor invalidation prevent lost updates and stale-page reuse.

The projection records explainable attention dimensions in this priority order: recovery/integrity block, identity collision, official-view impact, evidence warning, new-node creation, parent/relation ambiguity, domain novelty, low-confidence bucket, then stable source/native identity tie-breakers.

Global pending WIP is soft-warning above 100 and hard-stop above 200. A hard stop, an unprojected review packet, or an explicit operator pause defers nonessential provider dispatch. Resume is rejected until the soft envelope is restored and every review packet has a projection.

### Catalog and bounded reads

Node search uses NFKC/casefold normalization and deterministic ranks: exact canonical, exact alias, canonical substring, alias substring. Keyset continuation is tied to the normalized query and optional type filter. Results are deduplicated by canonical node identity, and exact matches cannot be lost behind a fixed 500-row pre-truncation.

Analyzer catalog inventory and source-local matching now scan the complete active catalog in bounded pages. Alias loading is batched per page. Coverage projection, source list, and source run history use bounded SQL pages. Source list pages batch their latest-run and usage summaries in a fixed query count, while full job/review/domain context remains on the on-demand detail endpoint; source summaries no longer expand every historical run.

### Prompt and deterministic semantic batches

The source-analysis prompt derives its deterministic Node Type list from the canonical `NODE_TYPES` constant and now includes `Company`. Unsupported or incorrectly cased values continue to fail closed through existing validation; the ontology/schema was not expanded.

Semantic decomposition partitions parents deterministically at no more than eight per batch and also respects the configured input-token envelope. An individually oversized parent fails explicitly. Durable source processing persists one job per batch, enforces at most 31 total jobs per run, and reconstructs in original parent order only after exact parent/evidence identity checks. Missing, duplicate, reordered, or evidence-altered results fail closed.

Historical Pilot 3 prompt pins were not rewritten. Its tests replay the historical prompt identity explicitly and verify that the current Stage 1 prompt is rejected by that retired workflow.

### Frozen operating limits

| Limit | Frozen value / behavior |
| --- | --- |
| Sources per run | 1 |
| Runs per rolling 24 hours | 3 |
| Review page | 25 default, 100 maximum |
| Pending WIP | soft warning >100, hard stop >200 |
| Semantic parents per batch | 8 maximum plus token bound |
| Jobs per source run | 31 maximum |
| Worker concurrency | 1 |
| Operator envelope | 60 cases / 60 minutes nominal; 75-minute guardrail |

No portable worker-utilization percentage was available, so this report does not claim a fabricated `<=70%` load measurement. Capacity evidence instead records bounded concurrency, hard backpressure, retry/stop contracts, request timings, SQL statement counts, query plans, and traced memory.

## Performance evidence

The disposable offline benchmark uses a real v10 Workbench projection, four-domain row distribution, 3 warmups, and 30 timed reads per scale. At 100/1,000/10,000 rows, list p95 was 18.448/18.991/32.181ms. Detail p95 was 17.679ms. The 10,000-row full 100-page traversal took 4632.474ms with 680,811 peak traced bytes and no duplicate or missing identity. The common pending queue plan uses `stage1_review_pending_page`.

Catalog validation returned 602 unique matches, with the exact canonical and exact alias results first; complete continuation took 103.076ms. Semantic partition reconstruction passed for 1/8/9/40/120 parents. Full measurements are in `docs/stage1_performance_report.json`.

## Validation commands

- `python -m pytest -q tests/test_phase43_stage1_operator_scale.py`
- `python -m pytest -q --basetemp=.p`
- `npm test -- --run --maxWorkers=1`
- `npm run build`
- `python -m compileall -q src scripts/benchmark_phase43_stage1.py scripts/validate_phase43_stage1_gold.py`
- `python scripts/benchmark_phase43_stage1.py --output docs/stage1_performance_report.json`
- `python scripts/validate_phase43_stage1_gold.py <frozen manifest> <qualification binding>`

The benchmark and gold validator use disposable/local read-only evidence only. Generated fixture data, local governance workspaces, private corpus material, frontend dependencies, and caches are not part of the Git change.
