# Selective provider neutral extraction contract R2 qualification

`SELECTIVE_PROVIDER_NEUTRAL_EXTRACTION_CONTRACT_R2 = PASS` for the implementation and offline acceptance scope below. This is not a release, real Run13 resolution or live provider authorization.

Baseline stable is `8f16ee18a5c7c28917971beb2852773408aae454`; implementation is `17d67bdffc4fe8a702085ab12de918244f529233`. Qualified source tree: `179845f538c60d9b2cd73634d31bd180e9fdfc2c`. The final PR closure adds qualification documentation and a test-only correction of an obsolete R1 compatibility expectation; runtime source remains exactly the implementation tree.

## Acceptance evidence

The 14-file acceptance scope contains 950 unique test nodes: 38 new R2 focused tests and 912 related tests. Final node outcomes are all PASS, with zero unexpected final failures. Coverage includes output decomposition, historical Claim linkage, bounded-only resume, malformed JSON retry, Stage7.2B/7.2C, bounded persistence/recovery, provider diagnostics, provider record normalization and whole-piece compact, including the corrected whole-piece compact assertion.

The complete fixed-runtime run produced 949 passed and one stale test failure: `test_stable_to_boundary_semantic_surface_exact[cloud]` still expected the old R1 exact cloud surface. R2 intentionally changes that surface. The corrected test verifies cloud `SEMANTIC_SURFACE_CHANGED` and native `SEMANTIC_SURFACE_EXACT`; both corrected nodes passed in a fresh replay. Final coverage is 948 unchanged passed nodes plus these two corrected passed nodes, not a claimed second complete all-green run. Original logs are retained locally. The comparator, execution-surface exclusions and recovery authorization were not relaxed to satisfy this test.

Earlier development diagnostics were superseded, not counted as acceptance: a metadata-only retry fixture incorrectly referenced a pre-V3 release; a new durable-routing fixture lacked a prompt parent directory; and the new module-fingerprint test initially hooked `Path.read_bytes` instead of the actual `sha256_file` interface. Corrected fixtures and both new acceptance-module fingerprint tests pass. These fixes do not authorize stable-v2 to R2 continuation.

Tests used synthetic transports and an external-socket tripwire, with existing MCP dependencies reused in the test process. The repo .venv/MCP historical environment issue remains non-blocking for this scope; no project-environment cleanup or repair was included.

## Contract and equivalence

Active candidate record: `whole-piece-output-batch-provider-record-v3`. Neutral IR: `normalized-extraction-analysis-record-v1`. Adapter encoding: `deepseek-output-batch-lexical-encoding-v3`.

Validated Claim Evidence is the sole local linkage source. Exact acknowledgements fail closed for missing, duplicate, foreign, invented and extra-field inputs. Sixteen acknowledgements and zero Claims is legal. Every emitted Claim still needs valid Evidence and ownership; no importance score, minimum Claim count or raw-fact exhaustiveness target is introduced.

DeepSeek lexical and fake native adapters produce identical normalized records and, for equivalent qualified content, exact Wire, local dispositions, permanent identities, aggregate results and native analyzer results. Structured JSON is an object and booleans/confidence are native types before the neutral boundary. Telemetry is excluded. No second real provider or local model is implemented.

Real frozen Run12 v1 raw remains rejected as `CLAIM_DISPOSITION_MISMATCH`; Run13 v2 malformed raw remains syntax-rejected; the 44-Claim Run13 root remains `FAILED / CLAIM_LINKAGE_MISMATCH`. The NEW-v3, non-authoritative counterfactual uses the same 44 valid Claims/Evidence and 16 acknowledgements and passes native validation and fake-native equivalence. Counterfactual Wire SHA256: `8daa88640d9b48f41d904136b0b92ae8a3a882ae75d41a31d44536e8871d7b10`; result SHA256: `61043d4f9c19cfb79a87132fac2614f6ebecb0806a2e1c994b4424b9473057b0`. No real result is created.

Canonical accepted research values are equivalent in qualified cases. Wire, Evidence Binding, canonical Claim identity/schema, aggregation and analyzer modules are unchanged. The selective semantic prompt and provider response/tool-schema contract intentionally change. Actual stable-to-implementation assessment is cloud changed / native exact; no read-only assessment is persisted as an execution authorization. A real fresh Run13 R2 Attempt remains execution UNQUALIFIED pending a version-aware root resolution operator.

## Size evidence

Compact serialization gives identical chars and UTF-8 bytes for these ASCII coverage members. Array measurements are kept separate from whole-member measurements; the longer acknowledgement field name costs 13 bytes. No token estimate is made.

| Coverage shape | V2 array | V3 array | Whole-member bytes saved |
|---|---:|---:|---:|
| Real failed 16 Evidence / 44 Claims, 42 declared links | 1112 | 625 | 474 |
| Correct 44 links using the real Claim distribution | 1124 | 625 | 486 |
| Balanced synthetic 16 Evidence / 44 Claims | 1120 | 625 | 482 |
| Synthetic 16 Evidence / 16 Claims | 952 | 625 | 314 |
| Synthetic 16 Evidence / zero Claims | 881 | 625 | 243 |

Ordinary historical successful batches have 937 and 923-byte V2 arrays, versus 625-byte acknowledgements. Batch size, token budget, subdivision and production provider/model/endpoint are unchanged. Claim-linkage-mismatch retry is not added.

## Build, privacy and real-state boundary

Isolated PEP517 build and disposable no-Git wheel staging PASS. All 145 packaged Python files equal the qualified source bytes; compilation, repository identity and V3/neutral-boundary import checks pass. Wheel SHA256: `b4d785f5a2dc20a185a35d285f404619a06011cbcecb41819b23b996cf2bd59e`. This wheel is not installed or activated as stable.

Privacy scan compares public changes and PR text against private Source, raw, frozen inputs, prompts and credentials, without exporting private contents. Local scripts, inventories, databases, raw copies and stage logs are not PR publication material.

Schema12 and real Run13 remain unchanged: BLOCKED/BOUNDED_ONLY_RESUME, four provider calls, two completed Segments, one actual root failure and 24 unattempted upstream-fail-closed Segments. New real provider calls, Attempts/raw/results, Semantic/Production/Current View writes, review actions and Run14 creation are all zero. Workbench SHA256 before/after: `65b587e6762ebc589b7d693e96b1c4099184d2aead20d4531510ee068a4e74fa`. Production SHA256: `6e5a303ccee9c192c350c2550cc232649e56ffee939b7a09cd6b170cc1c8fba1`.

Local project hygiene is separate and excluded from this runtime PR. No tracked repository deletion, remote branch deletion or stable activation occurs. Keep the PR OPEN/DRAFT/NOT_MERGED. Next stage: `RUN13_R2_ROOT_RECOVERY_AND_UPSTREAM_REOPEN_QUALIFICATION_R1`, still qualification-only, not live recovery.
