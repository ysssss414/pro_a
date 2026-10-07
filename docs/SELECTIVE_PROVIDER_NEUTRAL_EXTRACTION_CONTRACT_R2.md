# Selective provider neutral extraction contract R2

R2 makes validated Claim Evidence the single source of Claim linkage, retains exact execution coverage, and separates provider encoding from normalized research acceptance. DeepSeek remains the only production extraction provider. This qualification does not release or activate R2, recover Run13, implement upstream reopening, or authorize a provider call.

## Product objective and coverage

The extraction objective is `MATERIALITY_WEIGHTED_SELECTIVE_EXTRACTION`, not exhaustive document ETL. Read the complete frozen SourcePiece and all assigned Evidence, but emit only research-worthy information with incremental or verification value. Prioritize quantitative facts, capacity, shipment, orders, customers, suppliers, price, ASP, cost, margin, certification, product specifications, timelines, management guidance, material strategic changes, risks, contradictions, novelty, thesis-changing information and monitoring points.

Generic marketing, boilerplate, repeated background, low-value detail, already represented duplicates, trivial statements and unsupported inference do not require durable Claims. No materiality score, importance enum, minimum Claim count or new research-schema field is introduced. Attribution, uncertainty, local Source resolution, atomic propositions, no hallucination and authoritative Evidence rules remain in force.

| Product invariant | Required |
|---|---|
| Execution coverage | true |
| Claim per Evidence | false |
| Valid Evidence for every emitted Claim | true |
| Raw fact recall 100 percent | false |

Future quality assessment prioritizes `MATERIAL_INFORMATION_RECALL`, `CRITICAL_FACT_RECALL`, `CLAIM_PRECISION`, `NOVELTY_YIELD`, `EVIDENCE_VALIDITY` and `THESIS_RELEVANCE`, not raw-fact exhaustiveness. These are quality objectives, not newly implemented scoring machinery. Sixteen acknowledged Evidence units with zero Claims is a valid complete execution result. Coverage must not create pressure to inflate Claims.

## Provider record and authoritative acceptance

The v3 provider record replaces `dispositions[].claim_refs` with `evidence_acknowledgements`. Each item is a closed object containing only `evidence_ref`. Every frozen assigned Evidence must appear exactly once. Missing, duplicate, foreign and invented references fail closed. The provider does not return Claim counts, disposition enums or a second Claim-to-Evidence mapping.

```json
{"evidence_acknowledgements":[{"evidence_ref":"EV_SYNTHETIC"}]}
```

Acknowledgement means the Evidence entered this Batch's processing responsibility and was considered. It does not require a Claim or prove the model's internal cognition, exhaustive recall or research correctness. Claim linkage is independently and completely expressed by each emitted Claim's validated EvidenceSelection.

The local sequence is normalization, Evidence Binding v2, ownership validation, deterministic Evidence-to-local-C-index mapping, local `CLAIMED`/`NO_INDEPENDENT_CLAIM`, then the existing Segment/Wire gates. Empty Claim groups remain `NO_INDEPENDENT_CLAIM`. Other families retain their existing active Evidence, ownership, Node ID and semantic validation. Relation `supporting_claim_refs` is retained: it expresses relation support, not redundant Evidence bookkeeping.

Acknowledgements and the normalized-record version are removed before Wire. Candidate/source-reference ownership anchors remain execution-only and are stripped after validation. None of these fields enters permanent Claim identity, canonical research value or Current View. EvidenceDisposition, accepted Segment result, Wire v3, Evidence Binding v2, native analyzer and aggregate semantics remain equivalent to correctly self-consistent v2 inputs.

## Provider neutral boundary

```text
Provider transport and encoding
  -> adapter normalization
  -> normalized AnalysisRecord
  -> authoritative local Evidence and ownership validation
  -> unchanged Wire and research core
```

`extraction_analysis_record.record_to_result` accepts a native dictionary using existing normalized Wire field types. Its closed outer fields are `analysis_record_version`, `source_metadata`, `claims`, `node_matches`, `node_candidates`, `relation_candidates`, `source_references` and `evidence_acknowledgements`. Claim EvidenceSelection uses the existing flattened normalized fields: `evidence_ref` and optional `evidence_mode`, `evidence_selector`, `evidence_occurrence`. There is no new alternative Evidence schema.

Claims contain `structured: object`, not `structured_json: string`. Confidence is a native finite number; applicable boolean fields are native booleans. Existing Wire validation is authoritative for normalized object shape and type. No coercion, tolerant parser, repair, altered selectors or fabricated Evidence is introduced. Telemetry, endpoint, model, HTTP status, request ID, usage, latency, finish reason, tool calls and thinking settings are excluded from the research IR.

`output_decomposition.normalize_record` is the current DeepSeek lexical adapter. It decodes strict JSON, nested structured JSON, lexical booleans, numeric confidence and lexical EvidenceSelection before crossing into the normalized core. All DeepSeek request/response mechanics remain on this adapter side, including endpoint, strict tool schema, tool choice, `deepseek-flash`, thinking disabled and finish mapping. Endpoint, production model, temperature 0.1, 12000 output tokens and tool-call mode are not migrated in R2.

Semantic and encoding instructions have separate versions and hashes. The semantic contract contains the selection objective, Evidence rules and canonical semantics, without model/provider identity. The encoding contract identifies the DeepSeek lexical representation and its instructions. The existing aggregate operation/execution identity continues to bind both; the durable provider/model/config identity is not removed.

Adding a provider or local model must require only adapter/model-profile work, not modifications to Evidence Binding, Wire, Claim semantic schema, bounded ledger semantics, aggregation or Current View. Requiring a research-core change is `PROVIDER_ABSTRACTION_FAILURE`. This is an acceptance rule, not a promise that every future provider has already been integrated. The synthetic `FakeNativeJsonAdapter` directly supplies normalized data and qualifies the existing core without a second real provider.

## Historical contract isolation

Frozen v1/v2 validators remain in `output_decomposition_legacy`, solely for original-contract acceptance and offline history qualification. They do not normalize old failure into success. The production default is v3; a v1/v2 record presented as v3 is rejected by its closed schema. Contract selection is explicit and bound to the Attempt, never guessed from response fields.

New output Attempts include `provider_record_version` in the existing immutable `request_json` identity. No database migration is needed. Original unversioned Attempts resolve their contract from the immutable prompt artifact, checking its SHA against the original request before dispatching the frozen validator. `_load` reconstructs each historical request with its original field presence. This is narrow contract-version routing, not a ledger rewrite or a new retry engine. Event history, attempt sequencing, call accounting, original raw hashes and admission guards remain.

Run12 v1 raw still rejects with `CLAIM_DISPOSITION_MISMATCH`. Run13 malformed JSON remains syntax-rejected; its JSON-valid 44-Claim raw still rejects under v2 with `CLAIM_LINKAGE_MISMATCH`. Only a separately constructed NEW v3 counterfactual may pass with the same Claims/Evidence and exact acknowledgements, without real Attempt creation or persistence. Its label is `NON_AUTHORITATIVE_NEW_V3_COUNTERFACTUAL`. Historical raw is not admitted or reinterpreted.

## Equivalence and compatibility scope

Qualification includes 16 Evidence/0 Claims, 16 Evidence/16 Claims, 16 Evidence/44 Claims with zero and multiple Claim groups, low density, multiple Segments, canonical family ownership, exact acknowledgement rejection cases, invalid selectors, native types, telemetry exclusion, permanent identities, aggregate results and native analyzer equivalence. Fake native and DeepSeek lexical normalization produce the same normalized record and internal results for equivalent semantic content.

Deleting the provider self-consistency checksum is an intentional admission-contract change. It preserves authoritative Evidence binding and exact acknowledgement coverage, not the redundant checksum itself. Selective materiality instructions also have a new semantic prompt identity. The unchanged canonical research schema and equal internal results do not imply the frozen prompt or entire execution surface is exact.

| Stable to R2 dimension | Assessment |
|---|---|
| Canonical research fields and accepted-result semantics | Equivalent in qualified cases |
| Evidence Binding, Wire, identities, aggregation, analyzer | Unchanged |
| Provider response and tool schema | Changed v2 to v3 |
| Semantic selection prompt | Explicit selective objective added; identity changed |
| Historical response reinterpretation | Prohibited |
| Existing exact-surface continuation authorization | Does not authorize R2 |
| Real Run13 fresh Attempt under R2 | Structurally feasible but execution UNQUALIFIED |

Stage7.2C must continue to fail closed for real contract/execution drift. R2 adds the new acceptance modules to its execution dependency inventory, not an exclusion or relaxed comparator. Switching provider/model is an execution identity change; it is not automatically canonical research-semantic drift. Actual normalized semantic, prompt-semantic, Evidence or canonical rules must still be compared independently. No blanket provider-change compatibility exemption is implemented.

## Output size qualification

Measure actual chars and UTF-8 bytes, using the same compact serialization for coverage arrays, and separately report literal spans when applicable. The previous Run13 failed raw's 42 declared links used 1112 compact bytes; sixteen acknowledgement items use 625 compact bytes, a 487-byte array reduction. The new longer outer field name costs 13 additional bytes relative to `dispositions`, so the corresponding whole member reduction is 474 bytes under identical serialization. Correct synthetic 44-link v2 control uses 1124 array bytes, a 499-byte array or 486-byte member reduction. No token estimate or model-capacity claim follows from those measurements.

The ordinary prior successful batches' coverage arrays used 937 and 923 bytes versus 625 acknowledgements. The local machine receipt records both chars and bytes. No batch-size, 16-ref ownership policy or subdivision change is introduced: the current failure had no truncation.

## Future root recovery and upstream reopening

Run13 remains BLOCKED/BOUNDED_ONLY_RESUME, with four provider calls, two completed Segments, one actual new provider-response failure and 24 upstream-fail-closed unattempted Segments. Existing bounded-only resume does not clear FAILED execution projections; existing malformed retry does not authorize a JSON-valid linkage mismatch or a changed v3 request. R2 does not extend either operator.

The next qualified operator should bind the actual root failure event/Attempt/raw SHA, same Run and frozen plan, new protocol/request identity, explicit resolution authorization, fencing, idempotency and unchanged budgets. A fresh valid v3 response may create a new accepted root result while retaining the original failed Attempt/raw. A provider-contract-changing new Attempt requires distinct request identity and a scoped continuation policy; it cannot bypass existing same-request lineage checks.

Only after that root result is durable may an explicit transaction append reopen authorization/history and change execution projections for the 24 proven never-called fail-close leaves to executable. Preserve Segment IDs, frozen plan, two completed results and old failure events; no planner/replan, no historical deletion, no calls during reopening, and attempt_count stays zero until actual dispatch. Subsequent bounded execution needs a new explicit action key and ceiling; it must not reuse the old 25-call action. Cross-release, serial/concurrent idempotency, crash recovery, event linkage, budget, no redispatch and no Semantic qualification precede any live authority.

`NEXT_STAGE=RUN13_R2_ROOT_RECOVERY_AND_UPSTREAM_REOPEN_QUALIFICATION_R1`. That stage handles release preparation and root/reopen qualification, still without live recovery. Local hygiene is a separate local-only sidecar and is excluded from this runtime PR. Tracked historical repository content is audited, not deleted.
