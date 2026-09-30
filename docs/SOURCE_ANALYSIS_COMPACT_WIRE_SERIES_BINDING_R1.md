# SOURCE_ANALYSIS_COMPACT_WIRE_SERIES_BINDING_R1

Status: **PASS**. Baseline: `389399712deb9d2e1cacf41ad39e147e16b5f14b`.

Branch: `codex/pro-a-source-analysis-compact-wire-series-binding-r1`. Implementation commit: `b8cd7e676eb584028804914e07652807b28a6881`.

Qualification uses disposable schema12 Workbenches, synthetic HTTP, and an external-network prohibition. The real Workbench remains schema11. No live provider call, real migration, stable activation, Run #8, merge, or real review/Production/Current View mutation occurred.

## Execution and identity

One immutable native SourcePiece owns one ExtractionSeries. Ordered Segment calls are children in the bounded ledger, with no extraction CloudJob or source_processing_jobs row for new Runs. Semantic decomposition continues through semantic-backend-adapter-v2 CloudJobs with 8192/20000 and an 11808 input budget.

The SourcePiece artifact includes its native input, scoped Node catalog, original native prompt SHA, initial plan SHA, context, complete Evidence catalog, Source SHA, ordinal and Series identity. An immutable source_cloud_inputs SOURCE_ANALYSIS_INPUT and content-free BOUNDED_EXTRACTION_SERIES_BOUND event bind Run, ordinal, input artifact, SourcePiece and Series. Missing or tampered frozen inputs fail before artifact recreation, attempt reservation or provider dispatch. There is no new table, column, or schema13.

New Runs require schema12 and fail BOUNDED_SCHEMA_REQUIRED on schema11. Legacy source-analysis-piece-v1/source-analysis-piece-adapter-v2 identities and historical artifacts remain readable. No historical backfill, migration into Series, release compatibility exception, or new legacy SourceOperations execution is used.

| Contract | Version |
|---|---|
| binding_version | `bounded-source-analysis-series-binding-v1` |
| provider_version | `bounded-source-analysis-segment-provider-v1` |
| prompt_version | `bounded-source-analysis-segment-prompt-v1` |
| response_version | `bounded-source-analysis-response-v1` |
| series | `bounded-extraction-series-v1` |
| segment | `bounded-extraction-segment-v1` |
| coverage | `bounded-extraction-coverage-v1` |
| subdivision | `bounded-extraction-subdivision-v1` |
| evidence_binding | `source-analysis-evidence-binding-v2` |
| wire | `source-analysis-wire-v3` |
| expander | `source-analysis-wire-expander-v2` |

The active provider, prompt, runner, Foundation, Evidence binding, Wire, expander, store and persistence modules enter runtime/processing context and Stage7.2C execution hashes. Against the exact baseline, cloud and native surfaces independently report SEMANTIC_SURFACE_CHANGED. Native changes arise from immutable planning payload additions; native prompt bytes, SourcePiece sizing and planner remain unchanged. Historical frozen contexts are readable; resume guards still compare the current protected identity.

## Provider prompt, raw durability and recovery

The bounded system prompt preserves the complete native SOURCE_ANALYSIS_SYSTEM semantic rules and adds the explicit Wire/disposition protocol. Native SOURCE_ANALYSIS_SYSTEM/SOURCE_ANALYSIS_USER and SourcePiece.prompt_text remain unchanged. The separate provider user prompt renders the complete immutable SourcePiece once with deterministic Evidence annotations, the assigned refs and scoped Nodes. It does not duplicate exact Evidence text in another catalog.

The real BoundedSourceAnalysisSegmentProvider calls DeepSeek Chat Completions for deepseek-flash with thinking disabled, json_object, max_tokens=12000 and max_retries=0. Qualification substitutes synthetic HTTP. The adapter parses only the HTTP wrapper and returns exact message.content UTF-8 bytes plus allowlisted telemetry; Wire JSON parsing occurs after the private raw artifact is durable. No reasoning_content is inspected, measured, hashed, persisted, logged, or returned. Numeric reasoning_tokens may be retained. The unrestricted HTTP wrapper is never durable.

An immutable private prompt/request projection and its SHA are written before attempt reservation and dispatch. Each Segment attempt freezes request/configuration identities. The scheduler selects SourcePiece ordinal, Evidence range start, then stable path and makes at most one bounded provider call per SourceOperations.advance_once. Semantic scheduling keeps its existing behavior. Fresh SourceOperations, store and provider instances continue from the durable frontier.

A valid all-ref SUBDIVISION_REQUIRED response has no partial Claims and is accepted before normal deterministic subdivision. A finish_reason=length response remains an immutable TRUNCATED transport outcome and has no accepted Segment result. subdivide_after_truncation checks the active leaf, owner/fence, frontier, latest durable dispatched attempt, raw/outcome hashes, finish_reason and absence of an accepted result before atomically creating narrower children and superseding only that parent. SEGMENT_OVERFLOW_SUBDIVIDED records safe IDs, outcome SHA, children and frontier. Parent cost remains accounted.

A one-ref/depth/leaf/budget limit yields EXTRACTION_DENSITY_EXCEEDS_BOUNDED_POLICY: Series and unfinished Segment failure plus a safe event are durable before the Run becomes BLOCKED. Later uncalled Series are also closed, leaving no OPEN Series behind the terminal Run. Fresh instances recover a durable FAILED or RECOVERY_REQUIRED ledger state after a crash before the Run transition. Malformed stop fails closed without automatic retry/subdivision. Unknown external outcome retains liability, enters RECOVERY_REQUIRED with an explicit manual-recovery flag and never re-calls the provider. The old retry_failed_extraction action explicitly rejects bounded Runs as Series-owned. Retry, subdivision and explicit reprocess remain distinct.

Every assigned ref has exactly one disposition, and Claims may reference only assigned refs. All terminal ranges close the entire frozen Evidence universe before aggregate Wire, expander-v2 canonical expansion and original-native-user-prompt-SHA replay. Provider prompt replay is rejected without fallback. Foundation ordering, candidate deduplication and C-ref remapping preserve canonical values and native Claim identity; Segment IDs never enter permanent Claim IDs.

## Budgets and synthetic qualification

Global policy remains source-analysis-capacity-v2, 4000 chars, PHASE3E2SL6_PRECALL_PARTITION_V3, initially 16 refs per Segment, 12000 per call, extraction total configuration 20000, max 32 calls/384000 output liability per Series, max 16 leaves and max subdivision depth 4. Stage1 logical jobs count Series plus Semantic jobs, independently of Segment attempts. Safe Run projection reports Series, leaves, provider attempts, coverage and bounded usage; existing usage is explicitly scoped to Semantic CloudJobs.

| Synthetic scenario | Series | Segment calls | Semantic jobs | Overflow events | Review packets |
|---|---:|---:|---:|---:|---:|
| one_series | 1 | 3 | 5 | 0 | 1 |
| multi_piece_full_packet | 3 | 13 | 2 | 1 | 1 |
| dense_accounting | 5 | 14 | 25 | 0 | 0 |
| dense_200_claim_e2e | 5 | 15 | 25 | 0 | 1 |

The multi-piece PDF uses the real bounded and real semantic adapters with synthetic HTTP, performs overflow subdivision, completes native replay and reaches HUMAN_REVIEW_REQUIRED with packet_id/packet_artifact_id and zero decisions. MCP health, queue, review context and item context are functional and leave database/artifact hashes unchanged; bounded raw artifacts are absent from responses.

The dense accounting fixture independently completes more than five Segment calls across five Series and binds 25 valid synthetic Semantic batches: 30/31 logical jobs. It is an accounting fixture, not a full 200-Claim native replay claim. A separate preserved 200-Claim capacity E2E executes native replay, Semantic jobs and Review Packet through the new Series path. No token-fit guarantee is made.

## Real Source offline structural simulation

Source SRC_A26BB38BD619C3BC was read only. Native piece chars remain 3595/3783/3556/3791/2098; Evidence counts are 77/93/83/82/52; initial Segment counts are 5/6/6/6/4. This is 27 initial provider calls across five logical Series, with zero executed calls. Additional subdivision may be required; 27 calls are not claimed sufficient.

| Piece | Segment ordinal | Assigned refs | Provider prompt chars | UTF-8 bytes | Native prompt chars | Annotation overhead chars | Scoped Nodes | Source occurrences |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 1 | 16 | 9509 | 15593 | 6416 | 3311 | 6 | 1 |
| 1 | 2 | 16 | 9509 | 15593 | 6416 | 3311 | 6 | 1 |
| 1 | 3 | 16 | 9509 | 15593 | 6416 | 3311 | 6 | 1 |
| 1 | 4 | 16 | 9509 | 15593 | 6416 | 3311 | 6 | 1 |
| 1 | 5 | 13 | 9440 | 15524 | 6416 | 3311 | 6 | 1 |
| 2 | 1 | 16 | 10298 | 16642 | 6517 | 3999 | 5 | 1 |
| 2 | 2 | 16 | 10298 | 16642 | 6517 | 3999 | 5 | 1 |
| 2 | 3 | 16 | 10298 | 16642 | 6517 | 3999 | 5 | 1 |
| 2 | 4 | 16 | 10298 | 16642 | 6517 | 3999 | 5 | 1 |
| 2 | 5 | 16 | 10298 | 16642 | 6517 | 3999 | 5 | 1 |
| 2 | 6 | 13 | 10229 | 16573 | 6517 | 3999 | 5 | 1 |
| 3 | 1 | 16 | 9840 | 15718 | 6489 | 3569 | 7 | 1 |
| 3 | 2 | 16 | 9840 | 15718 | 6489 | 3569 | 7 | 1 |
| 3 | 3 | 16 | 9840 | 15718 | 6489 | 3569 | 7 | 1 |
| 3 | 4 | 16 | 9840 | 15718 | 6489 | 3569 | 7 | 1 |
| 3 | 5 | 16 | 9840 | 15718 | 6489 | 3569 | 7 | 1 |
| 3 | 6 | 3 | 9541 | 15419 | 6489 | 3569 | 7 | 1 |
| 4 | 1 | 16 | 10624 | 16686 | 7316 | 3526 | 11 | 1 |
| 4 | 2 | 16 | 10624 | 16686 | 7316 | 3526 | 11 | 1 |
| 4 | 3 | 16 | 10624 | 16686 | 7316 | 3526 | 11 | 1 |
| 4 | 4 | 16 | 10624 | 16686 | 7316 | 3526 | 11 | 1 |
| 4 | 5 | 16 | 10624 | 16686 | 7316 | 3526 | 11 | 1 |
| 4 | 6 | 2 | 10302 | 16364 | 7316 | 3526 | 11 | 1 |
| 5 | 1 | 16 | 6786 | 10372 | 4768 | 2236 | 5 | 1 |
| 5 | 2 | 16 | 6786 | 10372 | 4768 | 2236 | 5 | 1 |
| 5 | 3 | 16 | 6786 | 10372 | 4768 | 2236 | 5 | 1 |
| 5 | 4 | 4 | 6510 | 10096 | 4768 | 2236 | 5 | 1 |

Prompt metrics count the provider user prompt; the separately frozen system prompt preserves native semantics. Annotation stripping reconstructs the exact SourcePiece, and the complete annotated SourcePiece occurs exactly once. No real Source excerpt, filename, selector, prompt content, raw output or private artifact path appears in this report or receipt.

## Cost opportunities and validation

The exact compact V3 benchmark remains canonical 22574 chars versus compact 16038 chars, reduction 28.9537%. COMPACT_WIRE_COST_TARGET=NOT_MET; the <30% reduction does not block correctness. Range-only Evidence rendering, stable-prefix/provider prompt caching, context halos, density-aware initial sizing and local-model execution are deferred cost opportunities; none alters this stage’s correctness or policy.

The specified matrix passed before the final frozen-input guard: **885 passed, 2 skipped, 0 failed, 0 errors**, including the two focused modules and all 26 required regression modules. The final guard and its missing/tampered-input tests were then verified by rerunning all nine affected modules: **215 passed, 0 skipped, 0 failed, 0 errors**; the final two focused modules include **27 passing cases**. These overlapping runs are reported separately. No full-repository-green claim is made. Original test functions and parameter matrix sizes are preserved; fixtures/assertions were migrated individually. Frozen baseline subprocesses generate synthetic historical records only; the active runtime audits them and rejects old retry qualification.

compileall, pip check, isolated PEP517 build/install and byte comparison of all 136 source/wheel/installed Python files passed. Git diff whitespace check, privacy scan and before/after safety snapshots passed. Historical Runs #1–#7, Source, Production, real schema11 Workbench and all 129 stable installed Python files remain unchanged. Historical attempt counts remain 0/2/1/1/1/1/1.

## Deployment boundary

This handoff permits a new Draft PR only. After merge, real Workbench v12 migration is required; stable runtime activation follows migration; live bounded Run #8 validation remains required. None is performed by this qualification.

REAL_WORKBENCH_V12_MIGRATION_REQUIRED_AFTER_MERGE=true

STABLE_RUNTIME_ACTIVATION_REQUIRED_AFTER_MIGRATION=true

LIVE_BOUNDED_EXTRACTION_RUN8_VALIDATION_REQUIRED=true

[Sanitized machine-readable receipt](source_analysis_compact_wire_series_binding_r1_receipt.json).
