# Extraction capacity R1

Baseline: `bc151f3131dd6e9343937f3c5db9ddb7ed8e748a`.

Implementation commit: `93100dbf6aaeffa6423f983b10473aa732b7ba96`.

`PRO_A_EXTRACTION_CAPACITY_R1 = PASS`

## Problem and selected policy

A real extraction attempt returned HTTP 200 with durable
`output_parse_kind=TRUNCATED`, `finish_reason=length`, known output usage
**8192 / 8192**, and `retryable=false`. Its Source piece contained 9817 characters
and its user prompt contained 13027 characters. This proves that the previous
10,000-character bounded policy is insufficient for this material under the
existing output budget. It does not establish a universal input/output ratio.

R1 selects **5000 characters** as the hard initial cap for the existing
`adaptive_retry_policy="forbid"` path. The effective cap remains the minimum of
the existing configured chunk size and this hard cap. No environment override,
per-request capacity option, or three-mode production framework is added.

The only application change is in Analyzer: the selected constant, the planner
version, and an explicit capacity-policy version in the hashed plan artifact.

- Capacity policy: `source-analysis-capacity-v1`.
- Planner: `PHASE3E2SL6_PRECALL_PARTITION_V2`.
- `FROZEN_ACCEPTANCE_INITIAL_MAX_CHARS = 5000`.
- `CloudProfile.max_output_tokens = 8192`, unchanged for both operations.
- `CloudProfile.max_total_tokens = 20000`, unchanged.
- Extraction limit: 16 pieces; total SourceOperations limit: 31 jobs, unchanged.
- Response-driven repartition remains forbidden. Truncation is not retryable.

## Private offline candidate study

The study reused the existing immutable SOURCE_READY PDF. Native parsing and
semantic-eligible-text selection exactly reproduced the previously frozen,
ordered extraction inputs: **16,823 characters**. The real Source, all three
historical Runs, and both databases were opened read-only. No provider was called.
Only aggregate and ordered size metrics are published; private material,
filenames, paths, Source/Run/job identities and prompt text are excluded.

| Candidate cap | Pieces / call proxy | Ordered piece characters | Min / max / mean | Remaining jobs out of 31 |
|---|---:|---|---|---:|
| 4000 | 5 | 3595, 3783, 3556, 3791, 2098 | 2098 / 3791 / 3364.60 | 26 |
| **5000** | **4** | **4828, 4989, 4908, 2098** | **2098 / 4989 / 4205.75** | **27** |
| 6000 | 4 | 4828, 4989, 4908, 2098 | 2098 / 4989 / 4205.75 | 27 |

| Candidate cap | Ordered user-prompt characters | Max / mean prompt characters | Total user-prompt characters | Scoped catalog counts |
|---|---|---|---:|---|
| 4000 | 6416, 6517, 6489, 7316, 4768 | 7316 / 6301.20 | 31506 | 6, 5, 7, 11, 5 |
| **5000** | **7649, 8199, 8664, 4768** | **8664 / 7320.00** | **29280** | **6, 9, 13, 5** |
| 6000 | 7649, 8199, 8664, 4768 | 8664 / 7320.00 | 29280 | 6, 9, 13, 5 |

All candidates pass exact ordered reconstruction, zero omitted/duplicated
characters, repeated plan identity, stable locator mapping, deterministic catalog
scoping, and the 16-piece limit. Every piece is within its candidate cap. Planning
finishes before any hypothetical model call and consumes no model result.
Candidate caps are substituted only inside the offline qualification process;
the selected production policy was then replayed independently without a cap
override and reproduced the four expected pieces.

| Candidate cap | Unique locators covered | Locator units split | Pieces with continuation fragments | Average / maximum locators per piece |
|---|---:|---:|---:|---|
| 4000 | 14 | 0 | 0 | 2.8 / 3 |
| 5000 | 14 | 0 | 0 | 3.5 / 4 |
| 6000 | 14 | 0 | 0 | 3.5 / 4 |

Locator coverage counts distinct native locator units. A unit is split when it
intersects multiple pieces; a continuation piece intersects a locator already
present in an earlier piece. These are structural proxies, not model-quality
measurements. The 4k candidate creates more boundaries between intact units, even
though none of the candidates cuts a unit in this Source.

## Trade-off and selection

The 5k hard ceiling is about 49% below the empirically failing 9817-character
piece. It provides a stricter ceiling than 6k without additional calls for this
Source: native locator boundaries make the 5k and 6k partitions identical.
The 4k policy has the smallest permitted input size but needs five calls instead
of four (**25% more**) and 31,506 user-prompt characters instead of 29,280
(about **7.6% more**). Its smaller local context is visible in the lower locator
count per piece. No subjective extraction-quality gain is inferred.

Relative to the previous two-piece 10k plan, the deterministic extraction-call
proxies are **2.5x / 2x / 2x** for 4k / 5k / 6k. These count planned pieces, not
transport retries. Prompt-character totals are an input-size proxy, not tokens
or dollar cost; repeated system prompts also contribute to actual request cost.

All three candidates pass the structural gates. The specified priority therefore
selects 5k: full coverage, a meaningful reduction from the failing piece size,
limited call overhead, intact locator units, and comfortable extraction capacity
(4 of 16 pieces). The remaining **27 jobs** are headroom, not a prediction of
real semantic job count. The 6k candidate has the least conservative hard ceiling
of the three and no observed efficiency advantage here. It is not selected.

**No live DeepSeek evidence exists for 4k, 5k, or 6k.** This engineering default
is a target for the next separately authorized live qualification. This stage
does not prove 5k safe, 6k unsafe, or 4k incapable of truncation.

## Frozen identity and cross-release boundary

The plan continues to freeze effective cap, ordered piece identities and hashes,
prompt hashes, locator coverage, planner version, and the complete plan hash.
`partition_policy.capacity_policy_version` is included in that hash.

Analyzer is already a Phase 4 processing-code dependency, so its change propagates
through `processing_code_sha256`, cloud `runtime_sha256`, and the frozen run
context. The complete plan hash is carried by each durable extraction payload
and native checkpoint, and thus its registered input/job identity. Tests check
these bindings before synthetic transport runs and compare the subsequently
persisted plan with that pre-call plan.

The existing configuration and CloudProfile digests remain unchanged. The cap
is a versioned code policy, so duplicating it as a mutable config setting would
weaken the single-default design. Tests prove runtime/context identity changes
and reject a changed runtime basis through `PROCESSING_RUN_CONTEXT_DRIFT`.

Stage 7.2C comparison against the exact baseline reports:

- Native execution surface: **`SEMANTIC_SURFACE_CHANGED`**, incompatible.
- Frozen-piece cloud dispatch surface: **`SEMANTIC_SURFACE_EXACT`**; dispatch of
  an already-registered piece is unchanged.

Stage 7.2C requires both checks. The native Analyzer dependency therefore fails
closed, with no compatibility exception. Historical plans, Runs and telemetry
are not rewritten, relabeled, backfilled, or retried.

## Synthetic and regression qualification

The selected-cap disposable E2E uses one generated PDF and one Processing Run,
actual SourceAnalysisPieceProvider and SemanticBackendProvider classes, and
synthetic HTTP responses. It preserves native parsing/planning, durable input
registration, cloud job identity and preflight, result validation, semantic
partitioning, and Review Packet registration.

The completed run has **4 extraction jobs + 20 semantic jobs = 24 jobs**, ending
at `HUMAN_REVIEW_REQUIRED` with one registered Review Packet. Each extraction
response contains 40 valid Claims (160 total), with serialized JSON sizes
**24561, 24584, 24657, 24657 bytes**. Both operations retain an 8192 output budget;
all jobs retain the 20000 total budget and pass durable validation. There are no
external provider calls or Review decisions, and disposable Production bytes
remain unchanged. Synthetic usage counters are test metadata, not a model-token
estimate; this stress fixture does not establish live generation capacity.

An initial 240-Claim stress fixture exceeded the unchanged 31-job limit and was
correctly blocked. The final 160-Claim fixture stays within that existing bound;
neither the job budget nor semantic batching was changed. Final tests use short
disposable paths. This finding is preserved rather than claiming that the initial
stress run passed.

Final qualification: **31 focused passed**; **505 required/related regressions passed, 2 skipped, 0 failed**; the final persisted-plan/adapter assertion replay passed once more (already included in the 31 distinct focused tests). **536 distinct passed, 2 skipped**. The two skips are pre-existing unavailable frozen/private fixtures, detailed in the [JSON receipt](pro_a_extraction_capacity_r1_receipt.json). Compileall, pip check, isolated PEP 517 wheel build, all 129 packaged/source/installed Python byte comparisons, and diff whitespace checks passed.
The focused suite covers the candidate matrix; cap-1/cap/cap+1/2-cap boundaries;
Chinese, ASCII and mixed text; unbroken paragraphs; oversized and multiple
locators; plan/version/runtime/context identity; and the dense dual-adapter E2E.
Required regressions include native orchestration, Workbench, Stage 7.1, provider
diagnostics/telemetry, retry compatibility, adapter binding, MCP Stage 0/3, and
analyzer/parser/provenance tests. No full-repository green claim is made.

## Real-state and deployment boundary

Publication review passed: no private Source excerpts (including whitespace-normalized
32-character windows), real identifiers, private filenames/paths, or credential
patterns were found in the proposed files. Remote main was fetched again and
still matched the required baseline before committing.

Final before/after real-state checks **match exactly**: Source bytes; all three historical
Run/job/attempt/outcome/event digests; every Workbench table digest; database
integrity, schema, row counts, hashes and sizes; and stable runtime metadata.
Historical attempt counts remain **0 / 2 / 1**. The third Run's second extraction
job remains uncalled; it still has no Review Packet. No real new Run, retry,
provider call, Review/Current View write, Production write or retry extension is
authorized or performed.

`STABLE_RUNTIME_ACTIVATION_REQUIRED_AFTER_MERGE = true`

`LIVE_PROVIDER_CAPACITY_VALIDATION_REQUIRED_AFTER_MERGE = true`

This feature is not installed in the live stable runtime. No Tunnel restart or
ChatGPT app recreation is part of this task. Publication stops at a Draft PR.
A future authorized operation must merge and activate first, then reuse the
existing Source in a new Run and qualify the selected cap with real DeepSeek.
Another truncation would require a separate design decision; there is no hidden
post-response split or automatic capacity increase.
