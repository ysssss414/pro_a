# PRO_A_EXTRACTION_CAPACITY_R2

Result: **PASS — offline and synthetic qualification only**.

Baseline: `761b7dab7a17d5eb02c08dfb324c532a00252039`.
Branch: `codex/pro-a-extraction-capacity-r2-4k`.
Implementation: `15f5ba584e4d5893144ee319bf7cebb38574a14d`.

## Selected production policy

The only product changes are three Analyzer constants:

| Contract | Baseline | R2 |
| --- | --- | --- |
| Capacity policy | source-analysis-capacity-v1 | source-analysis-capacity-v2 |
| Hard pre-call cap | 5000 characters | 4000 characters |
| Planner | PHASE3E2SL6_PRECALL_PARTITION_V2 | PHASE3E2SL6_PRECALL_PARTITION_V3 |

The existing deterministic planner and lossless locator-aware partition algorithm
are unchanged. Production uses adaptive_retry_policy=forbid and
response_time_recovery=FORBIDDEN. No new environment override, operator knob,
response-driven split, dynamic fallback, compact schema or JSON repair is added.

`operation-output-budget-v1` remains extraction **12000 / 20000**, semantic
**8192 / 20000**. CloudProfile base output remains 8192. Semantic input headroom
remains **11808**; its boundary tests accept 11808 and reject 11809.
`structured-json-reasoning-v1` still disables thinking for both operations and
omits reasoning_effort. Adapters remain `source-analysis-piece-adapter-v2` and
`semantic-backend-adapter-v2`. Prompts, output fields/schema, Claim/evidence/
Attribution/Node rules, parsers, validators, telemetry and retry behavior are
unchanged. The extraction-piece limit is 16 and the total-job limit is 31.

## Historical live evidence

Only ordinal labels and content-free measurements are published.

| Observation | Run #5 | Run #6 |
| --- | ---: | ---: |
| First piece characters | 4828 | 4828 |
| Prompt characters | 7649 | 7649 |
| Thinking | disabled | disabled |
| Output tokens / ceiling | 8192 / 8192 | 12000 / 12000 |
| Visible content characters | 23294 | 32176 |
| Finish / parse kind | length / TRUNCATED | length / TRUNCATED |
| Reasoning tokens | null / UNKNOWN | null / UNKNOWN |

Run #6 input=6441, total=18441, cached=6272 and JSON error position=32175.
The current 4828-character first extraction piece is too large for the bounded
12000-token ceiling for this exact high-density material. This does not establish
failure for all 5k materials. R2 selects 4k for the next live validation; **4k has
not yet been proven safe by a live provider call**. Omitted reasoning usage is
never replaced with zero. Historical runs retain all original identities.

## Real Source, read-only offline plan

The immutable historical Source was parsed through the native parser, and its
semantic text was compared exactly with the ordered historical extraction inputs.
The prior 5k plan was reproduced and matched its durable checkpoint hash. Under
the authoritative production 4k constants, the same **16823 characters** produce:

| Ordinal | Source characters | User prompt characters |
| --- | ---: | ---: |
| 1 | 3595 | 6416 |
| 2 | 3783 | 6517 |
| 3 | 3556 | 6489 |
| 4 | 3791 | 7316 |
| 5 | 2098 | 4768 |

All values exactly match prior 4k qualification. Ordered reconstruction, locator
coverage and deterministic node-catalog scoping pass; omitted=0, duplicated=0.
Repeated planning produces identical artifacts and complete plan SHA. Piece and
prompt hashes remain in the frozen plan and content-free receipt. No model
response is consumed. Five pieces fit within 16 and leave **26** job slots before
semantic processing.

R2 plan SHA: `28c9866a828cb8b35cd6296b43bb273df499ff9e97b03394d5a8639f67ace1f7`.
Historical 5k plan SHA: `c3d1d2b2cfdc9062b4d8dc744127879cf3da15b63edf1692b923440f594f757b`.

Analyzer byte changes alter Phase4 processing hash, runtime identity and Run
context SHA without changing model_configuration. Independently, policy/planner/
pieces alter plan SHA, input/checkpoint hashes and job intent. Tests retain old
synthetic rows and inputs unchanged. The actual historical Run #6 context rejects
the current R2 basis with `PROCESSING_RUN_CONTEXT_DRIFT`, verified read-only.

Stage 7.2C native comparison against the exact baseline returns
`SEMANTIC_SURFACE_CHANGED`. Its cloud adapter surface remains compatible because
the wire behavior did not change. Full qualification still requires the native
checkpoint dimension; no compatibility bypass or exception was added. Run #6
cannot resume as a 4k run. No migration, backfill or retry extension was installed.

## Synthetic qualification

Edge checks cover 3999, 4000, 4001 and 8000 characters using ASCII, Chinese and
mixed text, multiple locators, oversized locators and unbroken paragraphs.
They require exact reconstruction, bounded pieces and deterministic plan identity.
The selected policy tuple is asserted together so a cap-only or version-only
production edit fails qualification.

A five-page high-density synthetic PDF creates **5 extraction jobs**, each with
40 valid Claims. Its complete plan exists before dispatch. Real adapter classes
with synthetic HTTP send extraction max_tokens=12000 and semantic max_tokens=8192,
thinking disabled, no reasoning_effort, and response_format=json_object.
Each extraction returns valid complete JSON, completion_tokens=10000,
reasoning_tokens=0 and finish_reason=stop; all results validate and persist.
Response sizes are [24561, 24584, 24657, 24657, 24657] bytes.

The **200 Claims** produce **25 semantic jobs**, giving **30 total jobs <= 31**.
The real Source's future semantic job count is not inferred from this synthetic
fixture. Semantic input budget remains 11808. The full disposable run reaches
HUMAN_REVIEW_REQUIRED with a registered Review Packet, zero Review decisions and
unchanged Production. All HTTP is synthetic. The existing synthetic truncation
at 12000 remains TRUNCATED, non-retryable, with no automatic split or fallback.
Reasoning-content persistence guards continue to pass.

## Regression and build

Final deduplicated result: **620 passed, 2 skipped** across 27 files.
This comprises 4 new R2 checks, 21 selected-capacity checks and 595 regressions.
The two skips are optional frozen Phase 3C/3D replay artifacts unavailable in the
checkout. This is not a full repository test run.

| Test file | Passed | Skipped |
| --- | ---: | ---: |
| `tests/test_claim_attribution_semantics.py` | 12 | 0 |
| `tests/test_cloud_operation_adapter_binding.py` | 24 | 0 |
| `tests/test_extraction_capacity.py` | 21 | 0 |
| `tests/test_extraction_capacity_r2.py` | 4 | 0 |
| `tests/test_llm.py` | 36 | 0 |
| `tests/test_mcp_stage0.py` | 30 | 0 |
| `tests/test_mcp_stage3.py` | 51 | 0 |
| `tests/test_operation_output_budget.py` | 25 | 0 |
| `tests/test_operational_ingestion.py` | 9 | 1 |
| `tests/test_per_piece_node_catalog.py` | 6 | 0 |
| `tests/test_phase3c_semantic_failure_repair.py` | 15 | 0 |
| `tests/test_phase3e2sl2_bounded_semantic_closure.py` | 15 | 0 |
| `tests/test_phase3e2sl6_precall_partition.py` | 10 | 0 |
| `tests/test_phase43_stage1_operator_scale.py` | 14 | 0 |
| `tests/test_phase43_stage71_shared_core_pending.py` | 14 | 0 |
| `tests/test_phase43_stage72a_provider_diagnostics.py` | 28 | 0 |
| `tests/test_phase43_stage72b_extraction_retry.py` | 25 | 0 |
| `tests/test_phase43_stage72c_retry_compatibility.py` | 35 | 0 |
| `tests/test_phase4_orchestration.py` | 40 | 1 |
| `tests/test_piece_local_evidence_provenance.py` | 11 | 0 |
| `tests/test_provider_output_failure_telemetry.py` | 43 | 0 |
| `tests/test_semantic_admission.py` | 49 | 0 |
| `tests/test_semantic_gold_replay.py` | 2 | 0 |
| `tests/test_structured_json_reasoning_policy.py` | 41 | 0 |
| `tests/test_v0_2_analyzer_validation.py` | 12 | 0 |
| `tests/test_workbench_stage6.py` | 33 | 0 |
| `tests/test_workbench_stage7.py` | 15 | 0 |

Initial checks corrected synthetic active-run coalescing setup, expanded the PDF
fixture to five pages and distinguished native-plan drift from unchanged cloud
wire semantics. Final tests pass, retaining the original density lower bound;
the final dense rerun is counted once. No product changes beyond the three
constants were needed.

Isolated PEP 517 wheel build, pip check and compileall: PASS. All **129** Python
files match byte-for-byte between source, wheel and separate candidate install.
Wheel SHA-256: `703a212d8bba3bc144aa8e61d54e5a6778867d84baefdea842cc2a6bccdaccc2`.
Exact diff audit confirms all remaining Analyzer code and all other product files
are unchanged. git diff --check and privacy checks pass. Changed files, docs,
PR body and wheel were scanned for private Source excerpts, identifiers,
filenames, private paths, credentials and reasoning sentinels.

## State and deployment boundary

Read-only before/after digests match for Source, Runs #1–#6, historical jobs,
attempts/outcomes/events, Production, every Workbench table, stable metadata and
all installed stable Python files. Attempt counts remain **0 / 2 / 1 / 1 / 1 / 1**.
Real provider calls=0; new real Runs=0; Run #7_created=false; no Stage1 bypass,
Review/Current View writes or Production Apply. Stable runtime and Tunnel remain
unchanged.

STABLE_RUNTIME_ACTIVATION_REQUIRED_AFTER_MERGE = true

LIVE_4K_12K_EXTRACTION_VALIDATION_REQUIRED_AFTER_MERGE = true

Delivery stops at a Draft PR. After merge, activation and separate live execution
authorization, the same Source requires a new Run #7: five 4k pieces, disabled
thinking, extraction 12000 and semantic 8192. If the first extraction succeeds,
continue the remaining four, then semantic and Review Packet. If the first piece
again reaches 12000 with length and visible truncated JSON, stop for a separate
extraction-output-architecture review; no automatic 3k or 16k change.
