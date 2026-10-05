# SOURCE_ANALYSIS_WHOLE_PIECE_COMPACT_FIRST_R1

Qualification status and immutable build/PR references are recorded in the companion JSON receipt. This change is a candidate release; it does not activate the installed runtime or execute a real Source run.

## Final qualification

`SOURCE_ANALYSIS_WHOLE_PIECE_COMPACT_FIRST_R1 = PASS`. Gates A–E passed in order. The consolidated required regression scope finished with **825 passed, zero failures, zero skips**. This is the defined qualification scope, not a claim that every repository test was run.

Implementation commit: `59624d9e0113b907e0619c2de82b6097db7bf25b`.

The isolated PEP517 wheel has SHA256 `30825c9a4b9d52173755d49fecc04a9c860e59c8381fa9e7390d6dfccea30def`. All **139 Python files** are byte-identical across source, wheel, and isolated installation. `pip check`, source/installed `compileall`, installed repository identity, and runtime operation with Git forbidden passed. The installed identity points to the implementation commit above. Stable was not installed or activated by this task.

The companion [JSON receipt](SOURCE_ANALYSIS_WHOLE_PIECE_COMPACT_FIRST_R1.receipt.json) records the test-evidence hashes, prompt/adapter identity, offline metrics, and safety hashes. The Draft PR body and final publication receipt bind the evidence commit and exact PR head, avoiding a self-referential commit hash in this document.

## Architecture and representation

New schema12 Source runs use one `SOURCE_ANALYSIS_PIECE` CloudJob per complete frozen SourcePiece. The existing `source-analysis-capacity-v2` / `PHASE3E2SL6_PRECALL_PARTITION_V3` planner remains unchanged. Every request contains the entire annotated SourcePiece, deterministic Evidence catalog, and original scoped Node catalog. The response envelope has exactly one field, `wire`.

The representation reuses `source-analysis-wire-v3`, `source-analysis-evidence-binding-v2`, and `source-analysis-wire-expander-v2`. V3 retains canonical Evidence pointers and existing candidate fields; no Wire v4 is introduced. Whole units and exact raw/normalized selectors expand through existing strict provenance validation. Unknown Nodes, foreign Evidence, corrupt catalogs, invalid enums, ambiguous selectors, and unauthorized fields fail closed. Provider-specific fields never enter permanent Claim identity.

`node_matches[].role` is exactly `primary` or `related`. Prompt enums are generated from the same constants used by validation. Case changes, whitespace, entity types, and business-role substitutions are rejected.

The 16-ref partition and Segment ownership/disposition machinery are retired from new extraction execution. No dependency graph, Context namespace, automatic subdivision, verbose fallback, or bounded-Segment fallback is created. Machine checks establish provenance and structural validity; they do not prove natural-language antecedents. Native Analyzer validation, canonical replay, and explicit Human Review retain their existing roles.

## Runtime contract

| Property | Value |
| --- | --- |
| Operation | `SOURCE_ANALYSIS_PIECE` |
| Response | `whole-piece-compact-source-analysis-response-v1` |
| Prompt | `whole-piece-compact-source-analysis-prompt-v1` |
| Adapter | `whole-piece-compact-source-analysis-adapter-v1` |
| Provider/model | DeepSeek / `deepseek-flash` |
| Output ceiling | 12000 tokens |
| Thinking | disabled |
| Extraction calls/attempts per job | 1 / 1 |
| Automatic extraction retry | false |
| Workbench schema | 12, unchanged |

The new response, prompt, adapter, operation validator, source modules, and raw persistence module participate in runtime/dependency identity. Historical bounded runs remain readable through their existing projection. Their frozen prompt/adapter identities are reconstructed for inspection, without treating them as current. SourceOperations and Stage7.2C continue to reject incompatible execution surfaces. A failed new extraction requires explicit future reprocessing; it cannot use the old retry API.

## Raw-before-parse durability and schema decision

Schema12 already has private artifact storage, immutable dispatch/request identity, and an append-only hash-linked CloudJob event stream. These are sufficient; no migration or schema13 is introduced, and historical outcome/result tables retain their existing meanings.

1. The provider adapter parses only the HTTP wrapper and returns exact `message.content` as a string, plus allowlisted telemetry.
2. While holding the current job fence and writer transaction, persistence verifies attempt/job/request/dispatch linkage. A private raw envelope records the exact content, UTF-8 byte count, SHA256, and sanitized provider metadata.
3. A temporary file is flushed and fsynced, atomically published at the deterministic attempt path, and hash-checked. POSIX additionally fsyncs its directory. `WHOLE_PIECE_RAW_DURABLE` records only safe linkage/hashes/counts in the existing event chain.
4. Only after the raw transaction commits does JSON/Wire/Evidence/canonical validation run. Canonical artifacts and outcomes use the existing durable result lifecycle.
5. Recovery validates the frozen input/request and private raw envelope, restores an event missing after a process crash, and replays validation without a provider call. A mismatching existing event, missing committed raw, or corrupt artifact fails closed.

A dispatch with no reliable raw artifact remains an unknown external outcome; it never authorizes automatic re-dispatch. An abandoned reserved attempt consumes the one-attempt budget. Known provider failure, invalid output, and `finish_reason=length` also cannot retry. Length termination records `TRUNCATED` / `WHOLE_PIECE_COMPACT_OUTPUT_LIMIT`; the partial body is retained privately and is not parsed as canonical output.

Qualification covers process interruption, including an actual child-process exit after file publication but before event commit, followed by a fresh interpreter recovery. It does not claim a Windows power-loss/filesystem durability guarantee beyond the documented file flush and atomic publication behavior.

Raw model content is absent from SQL events/outcomes, public projections, MCP, logs, exception text, and committed evidence. Only the authorized private raw artifact contains the exact content. `reasoning_content` is never read or persisted.

## Qualification design

Gates were executed in order: A architecture equivalence; B dormant render/parse/enum contract; C durable execution binding; D offline/synthetic regression; E isolated build qualification. Final gate results and test counts are in the receipt.

- Dense 40-Claim and mixed native fixtures compare complete canonical objects, Analyzer results, Claim order/permanent IDs, Node/candidate/relation behavior, and Source metadata.
- Reconstructed diagnostic fixtures use full 16/1 and 8/8 layouts and both company antecedents. They recover the corresponding 青松/白杨 capacity statement without a dependency graph. The ambiguous antecedent fixture explicitly proves representation/provenance only.
- Binding tests include whole Evidence, raw and normalized subspans, duplicate occurrences, ambiguous/missing occurrence, foreign refs, wrong SourcePiece, catalog corruption, unknown Nodes, Event/candidate/node-match Evidence, and relation references.
- Synthetic HTTP exercises complete request visibility, strict envelope/enum checks, safe telemetry, known/unknown failure, truncation, invalid JSON, no retry, two-worker fencing, input/raw corruption, and private read-only MCP projection.
- Crash cases cover claim, dispatch intent, pre-network dispatch, response receipt, pre-raw publication, raw publication before event commit, raw durability, pre-canonical publication, canonical publication, and pre-terminal update. Fresh-instance and fresh-process recovery cannot recall the provider.
- Required regressions cover Wire/binding/Analyzer, compact foundation, capacity, budgets, adapters, CloudJobs, failure diagnostics/telemetry, SourceOperations, Stage7.2B/C, semantic admission/batching, operator scale, MCP stages 0/3, and historical bounded read projection.

Historical bounded fixtures are produced by the exact baseline main in disposable local repositories, then inspected under the candidate code. Neither diagnostic PR's production code is imported. Tests use synthetic transports and disposable databases; the real Source is read only.

## Logical-job budget

Existing semantic partitioning remains authoritative, with at most eight parent Claims per batch and its existing input-token constraints. The total counts extraction jobs plus semantic jobs once, with a ceiling of 31.

For five extraction pieces, qualified synthetic inputs produce: 200 Claims → 25 semantic jobs → 30 total; 208 → 26 → 31; 209 → 27 → 32 and rejection; 500 → 63 → 68 and rejection. A separate dense canonical-checkpoint test verifies rejection before any semantic job is submitted. These are synthetic budget cases, not estimates of the real Source's future Claim count.

## Offline real Source and response sizes

The companion receipt records all five frozen SourcePiece prompt character/UTF-8 sizes, Evidence counts, scoped Node counts, and corresponding old Segment prompt sizes. Expected initial extraction calls change from 27 to 5. No provider call is used to obtain these measurements.

| Piece | Source chars | Evidence | Scoped Nodes | New prompt chars / bytes | Old calls | Old prompt sum chars / bytes |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 3595 | 77 | 6 | 16883 / 29349 | 5 | 84391 / 146871 |
| 2 | 3783 | 93 | 5 | 17672 / 30398 | 6 | 106017 / 182553 |
| 3 | 3556 | 83 | 7 | 17214 / 29474 | 6 | 103039 / 176779 |
| 4 | 3791 | 82 | 11 | 17998 / 30442 | 6 | 107720 / 182564 |
| 5 | 2098 | 52 | 5 | 14160 / 24128 | 4 | 56400 / 96392 |
| Total | 16823 | 387 | — | 83927 / 143791 | 27 | 457567 / 785159 |

Prompt measurements concatenate the system and user messages with one newline; JSON transport framing is excluded. Old totals sum repeated requests, whereas each new piece is sent once. The new call count is five.

| Dense 40-Claim representation | Characters | UTF-8 bytes |
| --- | ---: | ---: |
| Equivalent canonical response | 22574 | 22574 |
| Whole-piece compact V3 envelope | 16047 | 16047 |
| Legacy Segment responses, summed | 20086 | 20086 |

Whole-piece V3 reduces this canonical response by 28.9138%. The three legacy Segment responses are 7880, 7887, and 4319 bytes. The earlier V2 diagnostic figure of 14758 characters omitted V3 fidelity fields and is not substituted for this measurement. No unqualified token conversion is used.

Prompt/character measurements do not establish real output fit. 12000 remains the current operational ceiling, not a proven optimal hard limit. Output decomposition remains deferred and `UNKNOWN_UNTIL_LIVE`.

## Real-state boundary

The installed stable runtime remains baseline `6e1135c4371a6a3d1b6a491a433576b3eda9efbe`; its recorded wheel SHA256 is `61035a5823abf425b5dc1001d314822c35fb11c2a5996ec414da104e66e15f62`. Run #8 remains blocked with its one historical attempt (`stop`, 6685 output tokens, 18129.2764 ms). The schema remains 12, Source run count remains eight, and 14 queued jobs remain unchanged.

Before/after database byte hashes and complete table snapshots protect historical runs, reviews, promotions, Production, and Current View. Real provider calls, Run #9 creation, Production writes, and Current View writes are zero. PR #100 and PR #101 remain Draft/unmerged. The task boundary is qualification plus a new Draft PR, with no merge or stable activation.

Next stage, only after review and explicit release/live authorization: `WHOLE_PIECE_COMPACT_RELEASE_AND_LIVE_RUN9_VALIDATION`.
