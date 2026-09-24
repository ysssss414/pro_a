# Phase 4.3 Stage 7.2A — pre-merge audit of PR #76

**Decision: BLOCKED.** The proposed repair cannot be certified as observability only or secret safe. PR #76 must remain Draft and unmerged. This audit made no live provider call, Knowledge Community read or write, Production write, or real Workbench write.

## Frozen boundary and root cause

- `origin/main` is `9179e28e73c8658b4893729a90f40166f556a0bd`; the branch head is `93298cd6337df61b286d3c88ccfc07056ad99901`. PR #76 was verified OPEN, Draft, unmerged, and based on `main` at the start of the audit. The branch diff contains only the seven Stage 7.2A implementation, test, and report paths. `git diff --check origin/main..HEAD` passed. No rebase or PR state change was made.
- The pilot operator's separate routing script reads the successful HTTP response and saves its response `id` in its routing receipt. Extraction instead goes through Source Operations, CloudJobs, `SourceAnalysisPieceProvider`, `ChatLLM.json`, and back through `ProviderFailure`. Before this branch, `ChatLLM` and the adapter reduced failed calls to a broad failure code; `_record_provider_failure` persisted that code, and the job/Run projection exposed it without HTTP status, failure layer, or provider request ID. This claimed loss point is verified from code, independently of the implementation report.

## Blocking findings

1. **Execution semantics changed.** `CloudJobs.run_once` now catches every `Exception` from `provider.invoke` (`src/pro_a/workbench/cloud_jobs.py:974`) and turns it into `UNKNOWN_PROVIDER_ERROR`/`RECOVERY_REQUIRED`. The frozen baseline propagated an unexpected `RuntimeError` and left that isolated test job `RUNNING`; the branch returned `RECOVERY_REQUIRED` and stored `UNKNOWN_EXTERNAL_OUTCOME`. An isolated synthetic differential replay produced these exact states. This changes the Run state machine, rather than merely recording metadata.
2. **A deterministic HTTP 401 can be reclassified.** The new diagnostic extraction calls `resp.json()` on HTTP error responses (`src/pro_a/llm.py:295,307`) and catches only `ValueError`. A synthetic HTTP 401 response whose JSON method raises `RuntimeError` produced `FAILED`/`AUTHENTICATION_ERROR` on baseline main but `RECOVERY_REQUIRED`/`UNKNOWN_EXTERNAL_OUTCOME` on this branch. The actual HTTP 401, stage, and auth classification are lost. This also disproves the blanket observability-only claim.
3. **Known HTTP 200 is lost during recovery.** Normal output validation failure carries a transport diagnostic, but the durable result artifact does not contain it (`src/pro_a/workbench/cloud_jobs.py:827`). After a synthetic `after_result_artifact_durable` fault and cold reconciliation, the failed job's diagnostic had `failure_stage=OUTPUT_VALIDATION`, `http_status=null`, and the request ID, although the mocked provider response was HTTP 200. Reconciliation rebuilds the diagnostic from the artifact without HTTP metadata (`src/pro_a/workbench/cloud_jobs.py:1146`).
4. **A secret-looking response ID reaches failed durable state.** `safe_request_id` rejects such values for the diagnostic, but the successful `ChatLLM` response ID path takes `data.id` without that filter (`src/pro_a/llm.py:343`). A synthetic HTTP 200 with an invalid application output and a secret-looking `id` placed that marker in the failed job's database row, API projection, and rejected artifact; the diagnostic's own ID was null. The same legacy result-ID leak was reproducible on baseline main, so it is not counted as a newly introduced behavior regression. It nevertheless violates this audit's no-secret-in-DB/API/artifact gate and the implementation report's broader secret-leakage assertion.
5. **The full-suite historical exception set did not match.** The isolated worktree lacks the local `config.toml`: 43 errors were `FileNotFoundError: Config not found: config.toml`. Two failures were a frozen-input hash mismatch and a byte-level LF/CRLF mismatch. The historical 33 exception node IDs were skipped in this run; the current 45 failing/error node IDs had no overlap with them. These differences cannot be certified as historical exceptions. The missing configuration is an environment limitation, not evidence that the 43 errors came from Stage 7.2A code. Python's WindowsApps-backed launcher became inaccessible after the full run, so a separate `compileall` rerun was unavailable; the implementation receipt records an earlier compileall pass.

The differential replays used only isolated fixture databases and mocked providers. The two confirmed **new behavior regressions** are items 1 and 2. Items 3 and 4 are unmet safety and diagnostic requirements. No real failed Run was retried.

## Gate results

| Gate | Result | Evidence or limit |
| --- | --- | --- |
| Git boundary | PASS | Frozen SHAs and seven-path diff verified; PR remained Draft. |
| Root cause | PASS | Routing and extraction paths, normalization, persistence, and API projection traced. |
| Observability only | BLOCKED | Unexpected-exception and HTTP 401 differential replays changed terminal behavior. |
| Failure taxonomy | BLOCKED | HTTP 401 can become an unknown provider error when diagnostic JSON parsing raises unexpectedly. |
| Failure stage | BLOCKED | The same HTTP 401 can be recorded as `UNKNOWN` rather than `HTTP_RESPONSE`; routing remains outside CloudJobs. |
| HTTP status semantics | BLOCKED | Known 401 can be lost; known 200 is lost across durable-artifact reconciliation. No synthetic timeout status was fabricated. |
| Provider request ID | BLOCKED | Diagnostic filter is bounded, but the result-ID path can persist a secret-looking value on failure. Transport failures did not fabricate an ID. |
| Retryable semantics | PASS | Existing adapter mapping and automatic retry budget are unchanged for handled failures; 502/504 remain non-retryable under the existing contract. The diagnostic field does not itself schedule a retry. |
| Error fingerprint | PASS | Canonical allowlisted classification fields only; repeated synthetic classification matched, while a changed class/status changed the digest. Request ID, time, and content are excluded. |
| Safe error summary | PASS | Generated from bounded class/status values rather than provider text. |
| Secret leakage | BLOCKED | Synthetic marker reached failed DB/API/artifact through result ID. |
| Full response body policy | PASS | Changed failure-event diagnostics are allowlisted; rejected result output is null, including recovery artifacts. The separate result-ID leak remains a blocked field-level exposure. |
| Event JSON compatibility | PASS | New diagnostic is additive; old events without it project as null, with no schema migration or backfill. |
| Success path regression | PASS | Existing synthetic routing/extraction, CloudJob completion, and request-ID success tests pass; no success was falsely marked failed in the tested cases. |
| Stage 7.1 regression | PASS | The 14 Shared Core Pending tests in the related suite pass, including legacy domain-activation behavior. |
| Synthetic matrix | PASS | 19/19 committed diagnostic cases pass; the audit's additional edge cases expose the blockers above. |
| Real-state immutability | PASS | Both actual DB SHA256 values match before and after. |
| Documentation accuracy | BLOCKED | The implementation report's observability-only, secret-leakage, and zero-regression claims exceed the verified behavior. |

## Test and state evidence

- Full backend run in the isolated PR worktree: **2282 passed, 108 skipped, 2 failed, 43 errors** (2435 total; JUnit `w/a72r.xml` under the main checkout's ignored audit scratch directory). The 19 diagnostic cases and the complete 124-case related backend selection passed inside this run. Historical reference: **2391 passed, 6 skipped, 4 failed, 29 errors**, with 33 documented exceptions. Exact node-ID intersection: **0/33**; historical exception-set match: **false**. The current 45 exceptions are not counted as confirmed Stage 7.2A regressions without equivalent test inputs.
- Frontend: **159 passed across 29 files**; TypeScript and production build passed. The temporary `node_modules` junction was removed after verification. `git diff --check` passed.
- Production database SHA256 before/after: `6e5a303ccee9c192c350c2550cc232649e56ffee939b7a09cd6b170cc1c8fba1`.
- Real Workbench state SHA256 before/after: `1ff852dbe76c5fc4054c3e6f4e308b98a66f918dc3081e287b793c682a61ca44`.
- Real provider calls: **0**. Real Knowledge Community reads/writes: **0/0**. Production writes: **0**. Real Workbench writes: **0**.

**Next action:** Stop. Resolve only the listed Stage 7.2A audit blockers and rerun the relevant isolated replays plus an equivalent full-suite comparison. Do not retry the real pilot, mark PR #76 Ready, or merge it on this evidence.

## Subsequent R1 disposition

The historical BLOCKED decision above applies to head `93298cd6337df61b286d3c88ccfc07056ad99901`. Narrow code commit `658e13e11a18abe44e4b6ea654790f6220de0f8d` addresses these findings. Its separate qualification is recorded in `PHASE43_STAGE72A_R1_AUDIT_REPAIR.md` and `phase43_stage72a_r1_audit_repair_receipt.json`: nine business-state scenarios and three Source Run scenarios matched frozen main, the expanded diagnostics matrix passed 28/28, and the final full suite matched all 33 historical exception nodes by node ID, status, and class with no new exception node. This follow-up does not retroactively turn the original head's audit into PASS. PR #76 still needs a full pre-merge audit against its new head.
