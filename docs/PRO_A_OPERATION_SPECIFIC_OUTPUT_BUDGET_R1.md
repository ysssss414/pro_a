# PRO_A_OPERATION_SPECIFIC_OUTPUT_BUDGET_R1

Result: **PASS — synthetic/offline qualification only**.

Baseline: `232b05fbbf32c7648876ec1fb58c94e0374c3bc1`. Branch: `codex/pro-a-operation-specific-output-budget-r1`.
Implementation: `06fba3a07310549dbc134e3f852f74cb86619905`.

## Policy and implementation

`operation-output-budget-v1` freezes this production mapping:

| Operation | max_output_tokens | max_total_tokens |
| --- | ---: | ---: |
| SOURCE_ANALYSIS_PIECE | 12000 | 20000 |
| SEMANTIC_DECOMPOSITION | 8192 | 20000 |

`cloud_contract.budget_for_operation` is the single authoritative resolver. The
existing CloudProfile base/default output stays 8192 and total stays 20000.
The resolver retains the existing profile total argument for bounded synthetic
profiles; no production total, reservation semantics, environment setting, or
operator-selectable output policy is introduced.

Computed policy version and both effective budgets enter `public_identity()`
before its configuration digest. They therefore freeze into model_configuration,
run context, job intent and idempotency identity. A budget-only mutation changes
those identities while leaving an existing job unchanged. Both strict context
validators accept the additive pair; historical contexts retain their original
shape and hash. Resume drift is rejected without backfill.

CloudJobs.submit resolves the operation budget into the existing job columns.
CloudRequest, budget_identity and output reservation retain that exact value.
Preflight checks frozen configuration and row budgets, and both existing adapters
retain strict provider-config/request equality before dispatch. Source provider
construction gives extraction and semantic distinct ChatLLM output limits,
with unchanged timeout, model, credentials and max_retries=0.

Semantic batching explicitly resolves SEMANTIC_DECOMPOSITION, retaining
20000 - 8192 = **11808** input tokens. Boundary fixtures accept 8001, 11807 and
11808 and reject 11809. Claim batching implementation and size caps are unchanged.

Frozen reconstruction validates each row against its operation budget while
reconstructing the original base profile at 8192. Extraction 12000 and semantic
8192 reconstruct successfully; extraction 11999/12001, semantic 8191/8193 and
total-budget drift fail closed. Historical v2 extraction at 8192 is rejected as
`RETRY_FROZEN_CONFIG_INCOMPLETE`, never upgraded to the new mapping.
Stage 7.2C cloud comparison against the exact baseline returns
`SEMANTIC_SURFACE_CHANGED`; no compatibility exception was added.

## Preserved contracts

- Extraction cap 5000; `source-analysis-capacity-v1`;
  `PHASE3E2SL6_PRECALL_PARTITION_V2`.
- `structured-json-reasoning-v1`: thinking disabled for both operations,
  reasoning_effort absent, response_format json_object unchanged.
- Adapters `source-analysis-piece-adapter-v2` and `semantic-backend-adapter-v2`.
- Prompts, parser, output classification, provider telemetry, retry policy,
  retry owner/count and same-Run semantics unchanged; no schema migration.
- Existing budget accounting is preserved. Output above total fails before
  dispatch for either operation. Cumulative reservation at the exact remaining
  boundary succeeds; one token above it returns BUDGET_EXCEEDED before dispatch.
- All existing adapter contract functions and reservation/failure-persistence
  functions compare unchanged to baseline. No adaptive split or fallback.

## Historical Run #5 evidence

Only ordinal labels are published; private identifiers and content remain local.
Extraction ordinal 1 had 4828 Source characters and 7649 prompt characters.
HTTP 200 / deepseek-flash; thinking.type=disabled; reasoning_effort not sent.
Usage: input 6441, output **8192 / 8192**, total 14633, cached 0.
Reasoning tokens were omitted: **null / UNKNOWN**, never inferred as zero.
Visible content length was 23294; finish_reason=length; parse kind=TRUNCATED;
JSON error position=23290.

Visible final JSON was generated and hit the frozen 8192 completion ceiling in
this exact non-thinking extraction attempt. This does not establish universal
5k failure. Observed-call arithmetic 6441 + 12000 = 18441 is below 20000;
it is context for testing, not a change to accounting or a live success claim.
Run #5 remains failed historical evidence at its original 8192 ceiling.

## Synthetic end-to-end evidence

A disposable synthetic PDF flows through the unchanged deterministic 5k planner,
real SourceAnalysisPieceProvider, synthetic HTTP, real SemanticBackendProvider,
and Review Packet registration to HUMAN_REVIEW_REQUIRED. The extraction response
has valid JSON, finish_reason=stop, completion_tokens=10000 and explicit synthetic
reasoning_tokens=0. It validates and persists normally under its 12000 ceiling.
Semantic sends 8192; every structured request disables thinking and omits effort.
All job totals remain 20000. Review decisions are zero and Production bytes remain
unchanged. A reasoning-content sentinel is absent from durable/public surfaces.

The dense capacity E2E also passes with multiple extraction/semantic jobs and
unchanged planning. At the new ceiling, synthetic completion_tokens=12000 with
finish_reason=length remains TRUNCATED and non-retryable. All eight established
output-failure classifications and unknown-usage handling pass regression.
These responses verify transport, accounting and orchestration only; they do not
prove live DeepSeek extraction succeeds at 10000 or 12000 tokens.

## Qualification

Final deduplicated result: **781 passed, 2 skipped** across 26 files:
25 focused plus 756 regression passes. This is not a full repository test run.
Tests remove real provider credential environment inputs and install an external
requests guard; successful HTTP responses use synthetic transports.

| Test file | Passed | Skipped |
| --- | ---: | ---: |
| `tests/test_cloud_operation_adapter_binding.py` | 24 | 0 |
| `tests/test_extraction_capacity.py` | 21 | 0 |
| `tests/test_llm.py` | 36 | 0 |
| `tests/test_mcp_stage0.py` | 30 | 0 |
| `tests/test_mcp_stage3.py` | 51 | 0 |
| `tests/test_operation_output_budget.py` | 25 | 0 |
| `tests/test_operational_ingestion.py` | 9 | 1 |
| `tests/test_per_piece_node_catalog.py` | 6 | 0 |
| `tests/test_phase3c_semantic_failure_repair.py` | 15 | 0 |
| `tests/test_phase3e2sl2_bounded_semantic_closure.py` | 15 | 0 |
| `tests/test_phase3e2sl6_precall_partition.py` | 10 | 0 |
| `tests/test_phase43_stage0.py` | 171 | 0 |
| `tests/test_phase43_stage1_operator_scale.py` | 14 | 0 |
| `tests/test_phase43_stage3_cross_domain.py` | 18 | 0 |
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
| `tests/test_workbench_stage6.py` | 33 | 0 |
| `tests/test_workbench_stage7.py` | 15 | 0 |

The two skips are existing optional frozen Phase 3C/3D replay fixtures unavailable
in this checkout. Initial focused checks identified context allowlists and a
disposable fixture mismatch, which were repaired. Test-launch argument/import
issues were corrected. The initial contract matrix had 21 telemetry failures
because its old wire assertion expected 8192 for extraction. After updating that
single assertion, all 43 telemetry cases passed; final totals count them once.

Isolated PEP 517 wheel build, candidate pip check and compileall: PASS.
All **129** Python files match byte-for-byte across source, wheel and independent
candidate installation. Wheel SHA-256: `e42818bda78097b5eea9c78caf1ccb78ac9da6d6d8acac52b21d5f9d0142feb4`.
Protected prompts/parser/planner/retry/telemetry files and existing adapter
functions were compared against baseline. git diff --check and publication
privacy checks pass. Private Source excerpts (whitespace-normalized 32-character
windows), identifiers, filenames, paths, credential patterns and reasoning
sentinels were scanned in changed files, public evidence, PR body and wheel.

## Real-state and deployment boundary

Read-only before/after snapshots match for Source, Runs #1–#5, jobs, attempts,
outcomes, events, every Workbench table, Production and stable runtime metadata.
Historical attempt counts remain **0 / 2 / 1 / 1 / 1**.
Real provider calls=0; new real Runs=0; Run #6_created=false;
Production writes=0; real Workbench writes=0; no Review/Current View mutation or
Production Apply. No historical configuration or attempt was rewritten.

STABLE_RUNTIME_ACTIVATION_REQUIRED_AFTER_MERGE = true

LIVE_12K_EXTRACTION_VALIDATION_REQUIRED_AFTER_MERGE = true

Delivery ends at a Draft PR. No merge, stable activation, Tunnel restart or live
call is part of this qualification. After merge and activation, a separately
authorized new Run #6 can test the same Source and 5k pieces using extraction
12000 and semantic 8192. If its first extraction succeeds, continue through the
remaining pieces and semantic to Review Packet. If it again reaches 12000 with
length and visible truncated JSON, stop; no automatic 16000 increase.
