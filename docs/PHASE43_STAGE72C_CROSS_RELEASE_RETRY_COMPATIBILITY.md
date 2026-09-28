# Phase 4.3 Stage 7.2C — Bounded Cross-Release Retry Compatibility

## Result

- `PHASE43_STAGE72C_GENERIC_COMPATIBILITY = PASS`
- `ORIGINAL_STAGE72_CROSS_RELEASE_COMPATIBILITY = BLOCKED`
- Real blockers: `BLOCKED_EXECUTION_CONTRACT_CHANGED`, `BLOCKED_NATIVE_CHECKPOINT_INCOMPATIBLE`
- `REAL_RETRY_EXECUTED = false`

This stage adds an explicit, exact-scope compatibility qualification. It does not weaken the default Stage 7.2B runtime, context, configuration, prompt, Source, input, or native checkpoint gates. The real historical Run was inspected read-only and remains blocked.

## Git and scope

| Item | Value |
|---|---|
| Authoritative baseline | `origin/main = ec0497df63595fb21dca7b1a7fc91ca81c942ef8` |
| Isolated branch | `codex/phase43-stage72c-cross-release-retry-compatibility` |
| Audited implementation head | `0fbd01116100f53b832331deb865976b785a12d6` |
| Compatibility contract | `extraction-retry-cross-release-v1` |
| Target contract SHA-256 | `f725ab3cdce7dae7ddde5fb9f3dad030b364a3f99478973f2cbfc1f236f7ddee` |
| Historical Source | `SRC_C70218574FB158D7` |
| Historical Run | `SOURCE_RUN_BBADD851DA1E4526BAB9B6EBD1DBDCF0` |
| Failed Attempt | `ATTEMPT_A1998074CE7545149AE15A9B865571B8` |

The primary worktree was not cleaned, reset, stashed, switched, or used for implementation. No version bump or tag was created.

## Stage 7.2B contract audit

Stage 7.2B reconstructs the persisted `CloudProfile`, resolves the original Phase4 configuration path and Source limits from the Domain binding, recomputes the configuration digest, checks the prompt and input artifact, guards the frozen Domain/Shared Core context, requires the Job and Run runtime identities to be exact, and invokes Phase4 `_compatible` against the native `SOURCE_READY` checkpoint. Ordinary retries retain that exact behavior.

The three historical Stage 7.2B outcomes were traced as follows:

1. `RETRY_FROZEN_CONFIG_INCOMPLETE`: this was an outer error mapping, not an irrecoverable configuration gap. The persisted Job reconstructs a valid `CloudProfile`; provider, model, aliases, adapter, timeout, budgets, retry owner/policy, Source limits, original Phase4 path, semantic configuration digest, prompt and input artifact all match. The exact Domain guard then encountered runtime context drift, and `frozen_service` mapped that failure to the configuration error.
2. `PROCESSING_RUN_CONTEXT_DRIFT`: the frozen and recomputed non-runtime context basis is exact, including Source, configuration, model configuration, prompt, execution policy and Shared Core identity. The drift is in runtime identity: Git, Domain code, Phase4 processing code and aggregate runtime SHA. Later Domain assignments do not relabel the frozen Run.
3. `CODE_OR_RUNTIME_CONTRACT_INCOMPATIBLE`: the native checkpoint remains `SOURCE_READY`, but its processing-code digest, repository commit, Python version and SQLite version differ from the target runtime. No checkpoint or historical identity was rewritten.

## Compatibility model

The new `retry_compatibility_qualifications` extension is operator-prepared, additive and append-only. It is never created by startup or reads. A `QUALIFIED` record binds the exact Run, Source, failed Attempt/Job, historical runtime, target runtime, historical context, contract version/digest, canonical dimension evidence, evidence hash, result, reason and timestamp. Update and delete triggers reject mutation.

Qualification is computed from authoritative state. There is no `allow_legacy`, `ignore_runtime_sha`, `compatible=true`, manual SHA input, old-Run rewrite, current-config substitution, or checkpoint rewrite. The API schema rejects compatibility input. Runtime exceptions are accepted only through an internal token loaded from an exact database record and revalidated against the current target contract.

For broad Domain/Phase4 code-digest changes, the qualifier reads the historical Git blobs and the target files, removes comments/docstrings and the narrowly identified qualification-token call keyword, and hashes a versioned AST execution surface. That surface includes request/config identity, Job claim and one-dispatch flow, provider request/result handling, parser/output validation, extraction replay, Domain basis construction, and the complete native processing module set except the compatibility gate itself. Missing historical code or any semantic AST difference fails closed. Target code is additionally bound by the full target contract digest, so a relevant later change requires requalification.

## Dimension matrix

| Dimension | Classification | Generic | Real Run | Evidence / reason |
|---|---|---:|---:|---|
| Historical failed Run/Job/Attempt scope | EXACT_IDENTITY_REQUIRED | PASS | PASS | Relationally bound terminal `FAILED / EXTRACTION_JOBS / PROVIDER_ERROR` and known failed external outcome. |
| Source identity | EXACT_IDENTITY_REQUIRED | PASS | PASS | Source ID and stored bytes SHA-256 are exact. |
| Input artifact identity | EXACT_IDENTITY_REQUIRED | PASS | PASS | Registered artifact file, file SHA, payload SHA, Run, Source and checkpoint bindings are exact. |
| Extraction piece identity | EXACT_IDENTITY_REQUIRED | PASS | PASS | Exact `SOURCE_ANALYSIS_PIECE` Job and payload are retained. |
| Source limits | EXACT_IDENTITY_REQUIRED | PASS | PASS | Frozen `max_pdf_bytes` and `max_extraction_pieces` are recovered from the original binding. |
| Domain / Shared Core context | SEMANTIC_COMPATIBILITY_ALLOWED | PASS | PASS | Non-runtime frozen basis is exact; runtime is evaluated separately by the versioned execution surface. |
| Domain assignment revision | EXACT_IDENTITY_REQUIRED | PASS | PASS | Assigned contexts use the frozen revision; pending contexts retain their original basis. Later assignment is irrelevant to the old Run. |
| Prompt contract | EXACT_IDENTITY_REQUIRED | PASS | PASS | Persisted operation contract, prompt bundle and combined prompt digest are exact. |
| Provider | EXACT_IDENTITY_REQUIRED | PASS | PASS | Persisted Job column equals canonical frozen `CloudProfile`. |
| Requested model | EXACT_IDENTITY_REQUIRED | PASS | PASS | Exact persisted requested model. |
| Accepted model aliases | EXACT_IDENTITY_REQUIRED | PASS | PASS | Exact canonical alias list. |
| Provider adapter version | EXACT_IDENTITY_REQUIRED | PASS | PASS | Exact Job/config/runtime adapter version. |
| Timeout | EXACT_IDENTITY_REQUIRED | PASS | PASS | Exact persisted timeout. |
| Output/token/call/attempt limits | EXACT_IDENTITY_REQUIRED | PASS | PASS | `max_output_tokens`, `max_total_tokens`, `max_calls` and `max_attempts` are exact. |
| Retry owner and policy | EXACT_IDENTITY_REQUIRED | PASS | PASS | Exact persisted retry owner and policy ID; reconstruction now verifies both columns. |
| Phase4 effective config | EXACT_IDENTITY_REQUIRED | PASS | PASS | Original TOML path exists and semantic config digest equals the frozen context. |
| Native execution checkpoint | SEMANTIC_COMPATIBILITY_ALLOWED | PASS | FAIL | Synthetic compatible checkpoint passes `_compatible`; real processing code, Python and SQLite differ and native AST surface changed. |
| Execution policy | EXACT_IDENTITY_REQUIRED | PASS | PASS | Frozen execution policy is in the exact non-runtime context basis. |
| Workbench schema semantics | EXACT_IDENTITY_REQUIRED | PASS | PASS | Workbench schema version is exact (`11`). |
| Cloud Job schema semantics | EXACT_IDENTITY_REQUIRED | PASS | PASS | Cloud contract and provider adapter versions are exact. |
| Retry orchestration semantics | SEMANTIC_COMPATIBILITY_ALLOWED | PASS | PASS | Target-only versioned append-only orchestration; its code is bound by the target contract digest and focused tests. |
| Extraction parser/output contract | SEMANTIC_COMPATIBILITY_ALLOWED | PASS | FAIL | Synthetic historical/target AST surface is exact. Real historical commit lacks the later provider-diagnostics surface and cannot prove equivalence. |
| Code/runtime identity | SEMANTIC_COMPATIBILITY_ALLOWED | PASS | FAIL | Synthetic broad digests may differ only with exact semantic surface. Real Domain/Phase4 digests differ and the required cloud surface cannot be fully reconstructed. |

Every configuration sub-dimension in the machine receipt is independently represented. No missing evidence is classified as compatible.

## Generic qualification

Synthetic tests prove both exact-runtime and cross-release cases. A release with changed Git and broad code digests qualifies only when the historical/target semantic surfaces are exact. The qualified path creates a new append-only retry Job/Attempt on the same Run and reaches `HUMAN_REVIEW_REQUIRED`; the original Run, Job and Attempt facts remain unchanged. Tests fail closed for Source/input/prompt/config/provider/model/alias/adapter/budget/retry-policy/context/Shared Core/native/runtime/parser drift, missing qualification, wrong scope or runtime, evidence tampering and stale target code.

Default Stage 7.2B behavior remains strict when no exact qualification record is loaded.

## Real historical Run — read-only result

The real Run has 25 passing dimensions and three failing dimensions: code/runtime identity, extraction parser/output contract, and native execution checkpoint.

- Historical cloud runtime: `ef7fb67f6057f5c9532990aa2e692a320eadda00b5b6dc4a271d30a69fa357c2`
- Measured target cloud runtime: `122bac6d7ac3be35115600cb4c0484f1da7151b53423b48756e2fb8dec86cc11`
- Cloud semantic surface: `EXECUTION_SURFACE_UNAVAILABLE:CalledProcessError`; `provider_diagnostics.py` is absent at historical Git commit `9179e28e73c8658b4893729a90f40166f556a0bd`, so equivalence cannot be manufactured.
- Native semantic surface: `SEMANTIC_SURFACE_CHANGED`; native runtime also differs in processing code, Python and SQLite.

Therefore `ORIGINAL_STAGE72_CROSS_RELEASE_COMPATIBILITY = BLOCKED`. No qualification record or retry was written.

## Verification

| Suite | Result |
|---|---|
| Stage 7.2C + Stage 7.2B focused, final impacted rerun | `49 passed` (`24` Stage 7.2C + `25` Stage 7.2B) |
| Related Workbench/Stage7/7.1/7.2A/cloud/native selection | `149 passed, 1 skipped` |
| Current LLM/Workbench6/7.2A/7.2B/7.2C replacement set | `156 passed` |
| Full repository final historical-environment run | `2468 passed, 2 skipped, 4 failed, 29 errors` (`2503` total) |
| Historical exception reconciliation | `33/33` exact node/status/exception-class equality; `NEW_REGRESSION = 0` |
| Compileall / CLI / diff check / credential scan | PASS |

The full JUnit is local at `workspace/stage72c_full_final.xml`, SHA-256 `bdf935114b4c4d4048ee9339d127256ce0d2550366e355b058ca2b1fed182246`. It uses the frozen historical root fixture environment, replaces the stale root LLM/Workbench6 tests with current versions, and adds current Stage 7.2A/7.2B/7.2C tests. The final post-full change only expanded the new AST surface to include `run_once` and its one-dispatch helpers; all impacted Stage 7.2C/7.2B tests were rerun (49 passed).

## Real-state boundary

| Control | Before | After |
|---|---|---|
| Production SHA-256 | `6e5a303ccee9c192c350c2550cc232649e56ffee939b7a09cd6b170cc1c8fba1` | `6e5a303ccee9c192c350c2550cc232649e56ffee939b7a09cd6b170cc1c8fba1` |
| Workbench SHA-256 | `1ff852dbe76c5fc4054c3e6f4e308b98a66f918dc3081e287b793c682a61ca44` | `1ff852dbe76c5fc4054c3e6f4e308b98a66f918dc3081e287b793c682a61ca44` |
| Real compatibility extension | NOT_PREPARED | NOT_PREPARED |
| Real extraction retry extension | NOT_PREPARED | NOT_PREPARED |
| Provider / ZSXQ / Production / Workbench writes | `0` | `0` |

No WAL/SHM sidecar was created. No real provider or ZSXQ operation occurred.

## Next action

Open a Draft PR and stop for review. Any future operational activation for the real Run requires a separately authorized stage; under the current evidence it remains blocked and must not be retried.
