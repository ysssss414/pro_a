# PRO_A_BOUNDED_EXTRACTION_FOUNDATION_R1

Result: **PASS — dormant foundation only.** Baseline: `68be680831aeeb0e3e3f198fb986ac6da8bae1d3`, remotely fetched and verified on 2026-09-30. Branch: `codex/pro-a-bounded-extraction-foundation-r1`.

**MULTI_SEGMENT_SERIES_RECOMMENDED = true.** One immutable SourcePiece owns one logical ExtractionSeries; its system-assigned output Segments do not become additional Stage1 logical jobs. Closed leaf Wire objects aggregate before a single canonical SourceAnalysis expansion. Output subdivision leaves SourcePiece identity, the global 4000 hard cap and the 12000 per-call ceiling unchanged. This stage has no provider, worker, persistence, migration or live binding.

**COMPACT_WIRE_COST_TARGET = NOT_MET:** explicit legacy pointer preservation reduces the dense-40 saving to **28.9537%**, below the preferred 30% target. The task explicitly makes correctness mandatory and this cost target nonblocking.

## Contracts and dormant boundary

Only two product modules and two test modules are added. All 690 baseline tracked files and all 130 baseline Python modules remain byte-identical. No active module imports the new foundation. The installed stable runtime remains `e69813cc7a9d25523ab6e5d52ebcfcf8aa03daf6`, with its 129 Python files unchanged.

| Contract | Identity |
| --- | --- |
| Series | `bounded-extraction-series-v1` |
| Segment | `bounded-extraction-segment-v1` |
| Coverage | `bounded-extraction-coverage-v1` |
| Subdivision | `bounded-extraction-subdivision-v1` |
| Task/sizing policy | `bounded-extraction-policy-v1` |
| Evidence binding | `source-analysis-evidence-binding-v2` |
| Prepared compact Wire | `source-analysis-wire-v3` |
| Prepared expander | `source-analysis-wire-expander-v2` |

The merged `source-analysis-wire-v2`, `source-analysis-evidence-unit-v1` and `source-analysis-wire-expander-v1` retain their existing meaning and implementation. The new binder uses the unchanged V1 parent catalog. The new V3 projector reuses V2's strict field/type/enum/reference/cap validation, then reconstructs selected Evidence and preserves explicit pointers. It does not call a model or annotate native provenance itself.

| Live surface | Unchanged qualified value |
| --- | --- |
| Capacity / hard cap | `source-analysis-capacity-v2` / 4000 |
| Initial Source planner | `PHASE3E2SL6_PRECALL_PARTITION_V3` |
| Extraction operation / adapter | `source-analysis-piece-v1` / `source-analysis-piece-adapter-v2` |
| Extraction budget | 12000 output / 20000 current job total |
| Semantic budget / input allowance | 8192 / 20000 / 11808 |
| Thinking | disabled |
| Stage1 logical job ceiling | 31 |
| Active cloud/native compatibility | both `SEMANTIC_SURFACE_EXACT` against required baseline |

## Evidence binding correction

`evidence_pointer` is an explicit canonical provider/legacy field. It is preserved byte-for-byte, including a pointer that differs from the selected unit's locator. `source_locator` is deterministic validation/provenance; the existing native `build_claim_record` path derives `structured.validation.source_locator` separately. The new expander does not substitute a parent locator for the pointer.

Provider selection fields are `evidence_ref`, optional `evidence_selector`, optional `evidence_occurrence`, optional explicit `evidence_mode`, and explicit Claim `evidence_pointer`. Offsets are never accepted from the model. `EvidenceBinding` is frozen and contains system-computed raw spans, parent locator, raw slice SHA, canonical excerpt, explicit pointer and binding SHA.

| Mode | Reconstruction |
| --- | --- |
| WHOLE_UNIT | No selector; exact unchanged parent text |
| RAW_SUBSPAN | All exact overlapping matches inside that parent, ordered by source start; unique match or explicit 1-based occurrence selects the exact raw slice |
| NORMALIZED_SUBSPAN | Only native NFKC → authorized Markdown unescape → whitespace collapse. System origin mapping selects an exact contiguous raw slice; native canonicalization of that slice reproduces the existing canonical excerpt |

Absent an explicit mode, raw exact matching takes precedence over normalized matching. For multiple valid candidates, occurrence is required; there is no fallback to the first match. Occurrence 1 on a unique candidate is valid, but out-of-range, zero, negative, boolean, non-integer, null, or occurrence without selector fails. Empty selectors, missing subspan selectors, foreign refs, model offsets, parent-crossing/non-contiguous selectors and fuzzy matching also fail.

Normalization mappings are verified against the native canonicalizer. This stage deliberately rejects nonseparable NFKC composition mapping, partial compatibility expansions whose raw slice canonicalizes to a different value, and any unsupported normalization. It adds no PDF-specific normalization profile. Exact raw selection remains usable even where normalized mapping is unsupported.

The independently re-executed authoritative census is:

| Binding outcome | Native-valid Claims |
| --- | ---: |
| WHOLE_UNIT | 206 |
| RAW_SUBSPAN, unique | 8 |
| RAW_SUBSPAN, repeated with explicit occurrence | 2 |
| NORMALIZED_SUBSPAN | 1 |
| Total excerpt representability | **217 / 217** |
| Explicit pointer equality | **217 / 217** |
| Canonical excerpt equality | **217 / 217** |
| Entire native canonical Claim equality | **217 / 217** |
| Existing deterministic Claim ID equality | **217 / 217** |

Both repeated selectors were qualified with occurrence 1 and occurrence 2, selecting distinct raw spans and reproducing the same existing quote. The fixture qualification explicitly supplies occurrence; it does not infer which historical occurrence the legacy quote meant. No real-material Claim output is available to make such an inference.

The census uses the shipped binder, reconstructs the original canonical Evidence fields in otherwise unchanged native fixtures, revalidates them through the original native validator, and evaluates the existing Claim ID formula. It does not claim that minimal legacy test dicts are all complete Wire V3 objects. Complete dense/mixed canonical fixtures separately round-trip through Wire V3 and native analysis, preserving all canonical values/IDs. A dense 40-Claim golden also reconstructs identically through three output Segments, including reverse completion order. V3 selector/occurrence and normalized bindings are tested through complete series aggregation and canonical expansion.

## Series, Segment, coverage and subdivision

`ExtractionSeries` binds Processing Run identity, global Source SHA, immutable Piece ID/content/prompt hashes, ordered eligible refs, Evidence universe SHA, Wire/task/output policy identities, frozen budget, deterministic ID and SHA. Exactly one logical job is represented, irrespective of the number of child calls. Reprocessing changes Processing Run/series identity; retry attempts do not.

`ExtractionSegment` binds series, parent ID, depth, stable root/branch path, half-open range, ordered assigned refs/ref SHA, Wire identity, unchanged max_output_tokens=12000, ID and SHA. Parent identity plus subdivision version plus child range produces identical children on replay. Neither timestamps nor provider attempt IDs enter these identities. Catalog, Segment, plan and result identities are verified before acceptance; model results cannot alter assignment.

`ExtractionPlan` retains parents and children with an immutable `SUPERSEDED_BY_CHILDREN` set. Midpoint subdivision never splits an Evidence unit and never mutates a parent's assignment. Children are `[lo, floor((lo+hi)/2))` and `[floor((lo+hi)/2), hi)`. Superseded parent output is rejected during aggregation; only active terminal leaves contribute.

Each assigned ref receives exactly one of `CLAIMED`, `NO_INDEPENDENT_CLAIM`, `CONTEXT_ONLY`, `SUBDIVISION_REQUIRED`. A `CLAIMED` ref must actually appear on one or more local Claims. Other complete dispositions have zero Claims for that ref. All evidence-bearing Wire contributions must use assigned refs. A candidate alone does not satisfy a `CLAIMED` disposition. `SUBDIVISION_REQUIRED` keeps the entire Segment incomplete; no parent-prefix salvage occurs.

For complete leaves, assignment equals the disjoint union of claimed/no-independent/context refs, with exactly one disposition per assigned ref. Series coverage reports eligible refs, terminal assignment refs, closed refs, missing refs and duplicate terminal assignments. Complete series have missing=0 and duplicate terminal assignment=0. Missing results, missing/duplicate disposition, foreign support, duplicate accepted result, bad lineage and altered hashes fail closed.

These are **structural** coverage contracts. No-independent/context dispositions do not mean the text has no value and do not prove semantic exhaustiveness. Expansion is followed by existing native semantic/evidence/attribution/quality/relation gates in a future binding. The dormant foundation itself performs no provider dispatch or native persistence and never declares a real run successful.

`RETRY` keeps the same Segment and assignment with a distinct attempt identity. `SUBDIVISION` creates narrower child Segments in the same series. `REPROCESS` creates a new Processing Run/series. No natural-language or opaque continuation cursor exists; assignment and ordering are system-owned.

## Initial sizing and bounded termination

Frozen architecture policy: **16 ordered refs per initial Segment, 16 maximum terminal leaves, depth 4, 32 maximum charged provider calls, 384000 cumulative output-token liability**. These are dormant limits, not live configuration or spending authorization. The cumulative value is 32 × the existing 12000 ceiling and is an architecture-level series safety bound, not a document-tuned output target. Input/total-token admission and monetary/run budgets remain Stage B work.

Sixteen-ref roots need at most four midpoint levels to reach singletons. A forest with `r` initial roots and at most `L=16` leaves generates at most `2L-r ≤ 31` Segment nodes; 32 calls allow that structural bound plus at least one additional attempt when the full one-root tree is used. Retry and failed/subdivided calls still consume this independent budget. Larger input universes can be assigned across initial roots; they are not guaranteed to fit the worst-case single-ref leaf budget.

The fixed policy was simulated across counts 1–64 and eight structural types. It completes the singleton subdivision tree for ≤16 refs; greater worst-case singleton demands stop at the leaf bound. It is deliberately finite. Initial root count exceeding 16, exhausted depth/leaves, or a single Evidence unit that still requires subdivision fails with `EXTRACTION_DENSITY_EXCEEDS_BOUNDED_POLICY`. There is no further Source/global budget tuning.

| Generalization type | chars | refs | initial Segments |
| --- | ---: | ---: | ---: |
| Expert interview | 324 | 24 | 2 |
| Earnings Q&A | 780 | 20 | 2 |
| Dense technical transcript | 1632 | 24 | 2 |
| Company announcement | 680 | 20 | 2 |
| Broker report | 730 | 20 | 2 |
| CSV/table-heavy | 608 | 1 | 1 |
| Sparse filing | 348 | 12 | 1 |
| Chinese/English mixed | 1188 | 54 | 4 |

CSV's one parent unit is intentional: existing V1 boundaries are preserved. A dense single unit can exceed the output ceiling and terminate explicitly; ref count is not a provider-token estimator. No fixture or real Source output fit is inferred from characters or these structural simulations.

Read-only simulation of `SRC_A26BB38BD619C3BC` verified unchanged Pieces and V1 units, then created deterministic virtual series/assignments without a new real run:

| Piece | chars | refs | initial Segments | assignment sizes |
| --- | ---: | ---: | ---: | --- |
| 1 | 3595 | 77 | 5 | 16,16,16,16,13 |
| 2 | 3783 | 93 | 6 | 16,16,16,16,16,13 |
| 3 | 3556 | 83 | 6 | 16,16,16,16,16,3 |
| 4 | 3791 | 82 | 6 | 16,16,16,16,16,2 |
| 5 | 2098 | 52 | 4 | 16,16,16,4 |

That is five logical jobs and 27 planned provider Segments, with zero dispatched calls. Subdivision need, completed extraction, real Claim representability and real output tokens remain **UNOBSERVED**. The policy was chosen from the structural bound, not to obtain those real counts.

## Compact aggregation and accounting

Aggregate active leaves by source range, preserving each saved Wire's within-Segment model order. Do not reorder individual Claims by Evidence ref because that can change existing Claim indices/IDs. Remap Segment-local `C1..Cn` to series-global canonical ordinals before expansion. Local supporting refs must exist in that Segment; cross-Segment provider relation refs are rejected. Cross-Segment relation inference is explicitly deferred; no additional model pass is added.

Node matches and references retain ordered concatenation. Node candidates use the existing native name key `normalize_ws(canonical_name).lower()`: candidates with equal semantic fields deduplicate by first occurrence, retaining its Evidence. Different supporting refs/selectors alone may corroborate that same proposal; all their refs remain range-validated and in saved leaf Wire. Different semantic content under the same key fails `NODE_CANDIDATE_CONFLICT` instead of fuzzy or silent merging. Remaining native quality/merge gates stay authoritative. Metadata uses the first nonempty metadata object in ordered leaves, matching native merge behavior; no new consensus or metadata call is introduced.

The aggregate keeps ordered leaf result hashes, a coverage certificate, canonical serialized compact content and aggregate SHA. It is not concatenated raw JSON fragments. Then V3 expansion produces one canonical SourceAnalysis for the original Piece; permanent Sources are never created per Segment. Existing 100-Claim/100-candidate aggregate validation caps remain: per-Segment caps do not bypass them. Arbitrary future model outputs or different segmentation policies are not claimed to produce identical Claim IDs; replay of the same saved results and qualified goldens is deterministic.

`SegmentCallAccounting` and `SeriesCallAccounting` define provider call count, per-call input/output/total/cached tokens, latency, request ID, finish reason, raw Wire hash and Segment outcome. Every distinct attempt is counted, including truncated parents and failures. Cached usage is not added a second time. Unknown usage remains null and each unknown output incurs a conservative 12000 liability against the cumulative bound. Duplicate attempts and invalid usage fail. These pure contracts do not implement provider retries, billing, dispatch recovery or persistence.

| Dense-40 format | chars | UTF-8 bytes | reduction vs canonical |
| --- | ---: | ---: | ---: |
| Canonical verbose | 22574 | 22574 | — |
| Unchanged Foundation Wire V2 | 14758 | 14758 | 34.6239% |
| Corrected future Wire V3 | 16038 | 16038 | **28.9537%** |

All 40 Claims in this benchmark select whole units; selector and occurrence are optional and therefore absent. Their encoding/expansion is qualified separately on subspan/repeated/normalized fixtures and the census; no mandatory placeholder fields are omitted from the measurement. Retaining explicit pointers adds 1280 chars/bytes. These are serialization measurements, not provider-token or price estimates.

## Stage B persistence recommendation

**Preferred: A — new versioned Workbench child Segment ledger tables, with immutable private raw/result artifacts.** Only the series parent binds to the existing Stage1 logical job; child records and attempts are independently accounted.

| Option | Decision |
| --- | --- |
| A: new series/Segment/attempt/outcome/event tables | **Selected.** Explicit transactions support frontier/lineage, uniqueness, worker fences and reservations without changing the meaning of legacy attempts |
| B: immutable Segment artifacts with minimal DB index | Not preferred. Artifacts are necessary, but a minimal index still needs transactional frontier, concurrency and reservation state; rebuilding this coordination from artifacts risks becoming an implicit ledger |
| C: reuse current attempts/results as output Segments | Rejected where it conflates retry attempts and distinct output ranges, overwrites parent results or mechanically consumes Stage1 jobs. Existing mechanics may be reused, not their incompatible row meanings |

Stage B needs a reviewed additive schema migration, series and Segment leases/fences, unique `(segment_id, attempt_number)` and accepted-result constraints, atomic parent supersession plus two-child insertion, and a transactional frontier version. Persist exact raw Wire/response bytes privately before parse/validation; distinguish byte SHA from this foundation's parsed canonical Wire SHA. Malformed/truncated bodies remain private audit data and never become accepted results.

Crash recovery verifies artifact/request/series/range hashes and replays deterministic registration without another call when a raw result is durable. Unknown external outcomes require explicit recovery and retained conservative liability; no assumed provider exactly-once guarantee. Stale workers cannot accept output after supersession or closure. Accounting includes all failed/retry/subdivision calls; concurrent dispatch reserves future input/total/output liability atomically. Finalization closes every terminal ref and registers one immutable aggregate/canonical result exactly once. These database/dispatch/fsync behaviors are recommendations, not implemented or crash-qualified here.

## Qualification and state

Focused tests include new Evidence binding and bounded series modules plus unchanged Wire V2: **190 passed**. Required remaining regression matrix: **414 passed**. Independent authoritative corpus rerun: **348 passed, 1 skipped**, yielding exactly 217 native-valid observations. The skipped historical E2E fixture is unavailable in the isolated checkout; the available complete 217-observation corpus was still reproduced. No full-repository green claim is made.

The required regression modules cover analyzer validation, Piece provenance, attribution, relations, corpus, Gate C, PDF generalization, capacity R1/R2, operation budgets, Stage7.2C and MCP Stage0/3. Synthetic scenarios A–I cover one/two initial Segment success, parent/nested subdivision, singleton/policy exhaustion, duplicate assignment, missing disposition, retry-vs-subdivision-vs-reprocess identity, and serialized deterministic replay. That replay simulation does not stand in for an actual worker crash test.

`compileall`, `pip check`, isolated PEP517 build and isolated wheel install passed. All **132** packaged Python files match source/wheel/install byte-for-byte. All **130** baseline Python files remain unchanged. Generated build/egg-info changes were removed/restored; they are not part of the diff. Active cloud and native AST closures are both `SEMANTIC_SURFACE_EXACT`. No compatibility exception exists.

Before/after read-only checks protect Source bytes/registration, Production and every Workbench table, stable metadata/129 installed files, and all seven historical Runs with attempt counts **0 / 2 / 1 / 1 / 1 / 1 / 1**. `REAL_PROVIDER_CALLS=0`, `NEW_REAL_RUNS=0`, `RUN_8_CREATED=false`, review writes=0, Current View writes=0, Production Apply=0. No DB migration or stable activation occurred. Diff/privacy checks cover code, synthetic tests and these sanitized evidence files.

Implementation/evidence commit SHAs and Draft PR are provided in the final handoff; the receipt binds the implementation SHA and qualification hashes. Do not merge or activate as part of this task.

`NEXT_STAGE_1 = BOUNDED_EXTRACTION_DURABLE_PERSISTENCE_R1` → `NEXT_STAGE_2 = SOURCE_ANALYSIS_COMPACT_WIRE_SERIES_BINDING_R1` → synthetic full E2E. Only after separate merge/activation and live authorization: `LIVE_BOUNDED_EXTRACTION_RUN8_VALIDATION`. None of those stages is implemented here.
