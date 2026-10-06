# OUTPUT_DECOMPOSITION_CLAIM_DISPOSITION_LINKAGE_R1

Offline qualification: PASS. This change replaces the provider's redundant disposition enum with explicit local Claim linkage. The local validator requires exact set equality and derives the existing internal disposition. Dynamic linkage is enforced locally; strict Tool schema remains FORMAT_COMPLIANCE_ASSIST.

- Exact remote main / frozen stable baseline: `99d9abcbc876669277438c203195a38652921404`.
- Implementation: `57a7442a7ccab576d045ef5d71d11234988e4117`.
- Qualified wheel SHA-256: `beb064126e87ddfdb811fe75be3b0e868e53c844b8eaf088bf6f2e639c82d521`.
- 1,416 distinct tests passed across 32 files. This is the requested related scope, not a full repository run.
- No real provider calls, Run #13, release activation, Production/Current View writes, Review actions, schema migration or additional cleanup.

## Root cause and frozen historical regression

`ROOT_CAUSE = REDUNDANT_PROVIDER_DISPOSITION_STATE`. Run #12 produced 13 Claims and 16 dispositions (14 CLAIMED, 2 NO_INDEPENDENT_CLAIM). One CLAIMED entry had no actual Claim using its Evidence. The original fail-closed validator was correct.

Read-only replay of the exact durable private raw returned `CLAIM_DISPOSITION_MISMATCH` under released v1 and `INVALID_PROVIDER_RECORD_SHAPE` under v2. The raw artifact SHA remains `a0a19ba8221e5f8325cd4d1c5bc1e7c900b3302cdd516f447fbd69674ff4aef9`. No raw text, selectors, private Source or Evidence IDs are published.

Run #12 remains BLOCKED: one provider call, 4,212 output tokens, no truncation, retry, subdivision, unknown external outcome, native replay, Semantic or Review Packet. `RUN12_FIRST_BATCH_12000_HEADROOM = true` describes only that Batch. The capacity of all 27 initial Batches remains unqualified live; output decomposition remains required. The ceiling remains 12,000.

## Acceptance and unchanged semantics

Each owned Evidence ref must appear exactly once in `dispositions`, now with `claim_refs: array[string]`. Empty means no actual Claim. C refs are assigned by Claim array order. References must be unique, valid local C1..Cn, and exactly equal as a set to Claims whose fixed EvidenceSelection uses that Evidence. Order is immaterial. Missing, duplicate, foreign, malformed, nonexistent, cross-Evidence, omitted and extra references fail closed.

Claim Evidence is validated through the existing deterministic binder before deriving any disposition. Only Claims contribute: candidates, Event candidates, preserved candidate Evidence, matches and Source references do not. Multiple Claims per Evidence remain valid. Linkage records are stripped before Wire and never enter research values or permanent identity.

The schema12 ledger stores the same internal EvidenceDisposition and complete ordered coverage. Its immutable Series identity binds SourcePiece, catalog, processing run, Wire, ownership policy and budgets; provider response format is not a Series identity field. Binding, Series, Batch, coverage, subdivision and ownership-policy v1 identities therefore remain. The provider contract, frozen target, operation prompt bundle and runtime surface carry the new versions. No historical v1 response is reinterpreted.

- `provider_record_version`: `whole-piece-output-batch-provider-record-v2`
- `tool_schema_version`: `whole-piece-output-batch-tool-schema-v2`
- `prompt_version`: `whole-piece-output-batch-lexical-tool-prompt-v2`
- `response_version`: `whole-piece-output-batch-response-v2`
- `adapter_version`: `whole-piece-output-batch-lexical-tool-provider-v2`
- `claim_linkage_policy`: `whole-piece-output-claim-linkage-v1`
- `system_prompt_sha256`: `4083dcb879420ca01d868b2138580f52cfeeef263ac9d8f1bbfcd687dabce11b`
- `tool_schema_sha256`: `ffe6fbbba3b4db8e857a6c538c59f5dfb9689da8aabb1b02ced0c2539ca304d7`
- `prompt_bundle_sha256`: `794281be83604a0facc5dfd098474f1f6754d5eb4b12be59975d6a0b194a17a6`

Complete SourcePiece context, owned tags only, 16-ref batching, full-context subdivision, raw-before-parse, no same-Batch retry, unknown-outcome handling, canonical aggregation, Wire V3, Evidence Binding v2, native Analyzer and logical-job accounting remain unchanged. Runtime comparisons against actual Runs #8–#12 all return SEMANTIC_SURFACE_CHANGED. Runs #1–#12 retain identical read-only MCP projections.

## Qualification evidence

47 focused tests cover exact linkage, multi-Claim and order equivalence, seven non-Claim families, invalid Claim Evidence before derivation, old mismatch rejection, v2 empty linkage, six v1/v2 internal/aggregate comparisons and invalid-linkage durable recovery. Existing whole-piece fixtures verify exact canonical Wire, native Analyzer and permanent Claim identity, including candidates, matches, relations and Source references. Durability tests revalidate v2 from raw in a fresh process, reject bad linkage without recall and preserve length-only multi-level subdivision, immutable raw, fencing and cost accounting.

The first related run passed 1,259 tests, then a fresh-process recovery fixture was blocked by RUNTIME_DRIFT: its parent cached the baseline Git SHA before the implementation commit, while its child saw the new commit. A read-only fixture audit confirmed BLOCKED_RUNTIME_DRIFT. With HEAD held fixed, the failed test and 53 not-yet-executed tests passed (54/54). No production or test gate was changed to accommodate this qualification-process error. Counts below are unique passing tests; the initial failure is retained in the JSON receipt.

| Test file | Passed |
| --- | ---: |
| `tests/test_bounded_extraction.py` | 98 |
| `tests/test_bounded_extraction_latency.py` | 23 |
| `tests/test_bounded_extraction_persistence.py` | 36 |
| `tests/test_bounded_extraction_recovery.py` | 23 |
| `tests/test_cloud_operation_adapter_binding.py` | 24 |
| `tests/test_evidence_binding.py` | 31 |
| `tests/test_extraction_capacity.py` | 21 |
| `tests/test_extraction_capacity_r2.py` | 4 |
| `tests/test_lexical_tool_adapter.py` | 19 |
| `tests/test_lexical_tool_qualification.py` | 46 |
| `tests/test_mcp_bounded_reads.py` | 8 |
| `tests/test_mcp_stage0.py` | 30 |
| `tests/test_mcp_stage3.py` | 51 |
| `tests/test_operation_output_budget.py` | 25 |
| `tests/test_output_claim_linkage.py` | 47 |
| `tests/test_output_decomposition.py` | 36 |
| `tests/test_output_decomposition_durability.py` | 20 |
| `tests/test_phase43_stage1_operator_scale.py` | 14 |
| `tests/test_phase43_stage72a_provider_diagnostics.py` | 28 |
| `tests/test_phase43_stage72b_extraction_retry.py` | 25 |
| `tests/test_phase43_stage72b_unicode_reason.py` | 10 |
| `tests/test_phase43_stage72c_retry_compatibility.py` | 35 |
| `tests/test_provider_output_failure_telemetry.py` | 43 |
| `tests/test_provider_record_json.py` | 25 |
| `tests/test_semantic_admission.py` | 49 |
| `tests/test_source_analysis_provider_record.py` | 467 |
| `tests/test_source_analysis_wire.py` | 61 |
| `tests/test_v0_2_analyzer_validation.py` | 12 |
| `tests/test_whole_piece_compact.py` | 33 |
| `tests/test_whole_piece_execution.py` | 24 |
| `tests/test_workbench_stage6.py` | 33 |
| `tests/test_workbench_stage7.py` | 15 |

Isolated PEP517 wheel, compileall, pip check, 142 source/wheel/install Python files with exact byte equality, installed repository identity and no-Git runtime: PASS. Privacy scan: PASS (7 changed files, 501 private comparison features, including Source fragments, names, configuration secrets and local paths). Git diff whitespace check: PASS.

## Size measurements (no token estimates)

System prompt: 7,423 → 7,620 chars (+197), 14,629 → 14,948 UTF-8 bytes (+319). Tool schema: 7,876 → 7,857 UTF-8 bytes (−19). Both measured using exact compact JSON serialization for structured values.

| Owned refs | Claims/ref | v1 argument bytes | v2 argument bytes | Delta |
| ---: | ---: | ---: | ---: | ---: |
| 16 | 1 | 8408 | 8351 | -57 |
| 16 | 4 | 29759 | 29990 | +231 |
| 8 | 4 | 14995 | 15106 | +111 |
| 4 | 4 | 7639 | 7690 | +51 |
| 1 | 4 | 2122 | 2133 | +11 |

Comparable dense outputs shrink monotonically with ownership subdivision. These synthetic byte measurements establish neither live token consumption nor a guarantee that every Batch fits.

The real Source was read offline: 5 logical Series, 27 initial Batches (5/6/6/6/4). Every request reconstructs the exact complete SourcePiece, preserves all foreign context text and exposes zero foreign selectable Evidence IDs. Full per-Batch v1/v2 chars/bytes are in the JSON receipt.

| Piece | Evidence units | Batches | Full context chars | v2 request byte range |
| ---: | ---: | ---: | ---: | ---: |
| 1 | 77 | 5 | 3595 | 37126–37330 |
| 2 | 93 | 6 | 3783 | 37470–37674 |
| 3 | 83 | 6 | 3556 | 36330–37214 |
| 4 | 82 | 6 | 3791 | 37345–38297 |
| 5 | 52 | 4 | 2098 | 32297–33113 |

## Safety and next stage

The JSON receipt records unchanged Workbench, Production, artifacts, Current View, historical projections, stable metadata and prior cleanup receipt hashes. Stable stays `99d9abcbc876669277438c203195a38652921404`, schema stays 12, historical queued jobs remain unchanged, Run #13 is absent. The frozen cleanup receipt is preserved; this phase performs no additional cleanup.

The evidence commit and Draft PR head are recorded in the PR description and final receipt after this document is committed. Do not merge or activate this Draft PR as part of this stage.

`NEXT_STAGE = CLAIM_DISPOSITION_LINKAGE_RELEASE_AND_LIVE_RUN13_VALIDATION`

`AUTHORIZATION_REQUIRED_FOR_LIVE_RUN13 = true`
