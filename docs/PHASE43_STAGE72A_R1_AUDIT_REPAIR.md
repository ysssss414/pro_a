# Phase 4.3 Stage 7.2A-R1 — narrow audit repair

**Qualification: PASS.** This report qualifies code commit `658e13e11a18abe44e4b6ea654790f6220de0f8d` on Draft PR #76. The frozen base is `9179e28e73c8658b4893729a90f40166f556a0bd`; the audit-blocked implementation head was `93298cd6337df61b286d3c88ccfc07056ad99901`. The earlier pre-merge audit remains an accurate BLOCKED decision for that earlier head. No real Stage 7.2 pilot was retried.

## Repair of the confirmed blockers

| Audit blocker | R1 disposition |
| --- | --- |
| Unexpected exceptions changed Job and Run behavior | `CloudJobs.run_once` now records an allowlisted warning diagnostic and rethrows the original exception. The synthetic baseline and R1 both leave the Job `RUNNING`, leave the Source Run `EXTRACTION_PROCESSING`, and propagate `RuntimeError`. The old test expecting `RECOVERY_REQUIRED` was corrected because the frozen main code and differential replay disprove that expectation. |
| HTTP 401 downgraded to unknown | HTTP-error JSON parsing is diagnostic-only and cannot replace the original HTTP error. A mock whose `json()` raises `RuntimeError` still ends `FAILED` with public `AUTHENTICATION_ERROR`, `http_status=401`, `failure_stage=HTTP_RESPONSE`, canonical `error_class=HTTP_401`, and `retryable=false`. `HTTP_401` is the established stable auth classification in this diagnostic taxonomy. |
| Known HTTP 200 lost after recovery | A rejected result artifact contains only a validated numeric `http_status` as an optional additive field. Cold reconciliation restores that field before building the output-validation diagnostic. Normal invalid JSON, invalid model output, schema rejection, and the durable-artifact crash path all retain 200. Old artifacts without the optional field remain readable. |
| Response ID entered failed durable state without validation | Only the known `x-request-id`, `request-id`, and `x-ds-request-id` header names feed request-ID metadata. A generic completion/object `id` in a JSON body no longer becomes a request ID. Every ID entering a new failed artifact, outcome row, job row, event diagnostic, or API projection passes the same bounded `safe_request_id` validator. Valid header IDs continue to project. Tests that treated completion IDs as request IDs were corrected to supply explicit headers. |
| Synthetic secret marker reached DB, API, and artifact | `build_failure_diagnostic` remains the allowlisted event boundary. `_durable_result` now normalizes provider-supplied result identity, model, ID, finish reason, times, and latency **after** the business decision and **before** artifact and DB registration. The output-validation artifact still stores `raw_provider_output=null`. Tests scan failed DB bytes, job API projection, result artifact, and captured logs for all four required synthetic markers; the final related-test directory and full-suite JUnit also contain no marker. |
| Initial documentation claimed safety prematurely | The implementation report and receipt now identify the initial qualification as superseded by the blocked audit and this R1 repair. The earlier audit artifacts remain as historical evidence and carry an R1 follow-up reference. |

The repair does not change provider routing, endpoint, HTTP method, model selection, prompts, payload, timeout, retry budget, output schema, extraction rules, or normal success criteria. On unexpected exceptions, safe diagnostic logging is best effort and cannot replace the original exception.

## Business-state equivalence

The same nine isolated provider outcomes were run once against frozen main source and once against R1 source. Comparison fields were exception class, Job state, public `last_error`, attempt count, retry-authorized event count, and result registration. All nine matched exactly:

| Outcome | Business result on both versions |
| --- | --- |
| Success | `SUCCEEDED`; one attempt; result registered. |
| HTTP 401 | `FAILED / AUTHENTICATION_ERROR`; one attempt; no retry. |
| HTTP 429 | `FAILED / RATE_LIMITED`; two attempts; one existing-policy retry. |
| HTTP 503 | `FAILED / PROVIDER_UNAVAILABLE`; two attempts; one existing-policy retry. |
| Read timeout | `RECOVERY_REQUIRED / UNKNOWN_EXTERNAL_OUTCOME`; one attempt. |
| Invalid HTTP 200 JSON | `FAILED / PROVIDER_ERROR`; one attempt. |
| Invalid model output | `FAILED / PROVIDER_ERROR`; one attempt. |
| Output schema failure | `FAILED / OUTPUT_VALIDATION_FAILED`; one attempt; rejected result registered. |
| Unexpected provider exception | Original `RuntimeError` propagates; Job remains `RUNNING`; no retry or result. |

A separate isolated Source Run comparison used success, mapped authentication failure, and unexpected exception. All three had identical pre-7.2A and R1 Run state `EXTRACTION_PROCESSING`, corresponding Job state, public error, and exception propagation. Source Operations itself was not modified.

## Qualification evidence

- Original diagnostics matrix: **19/19 passed** after correcting the three disproved expectations (unexpected exception state, generic body ID, and HTTP 401 body-versus-header ID precedence). New R1 cases: **9/9 passed**. Together: **28/28 passed**.
- Related backend suite: **133 passed**. This includes provider/ChatLLM, CloudJobs, Stage 7 Community, Stage 7.1 Shared Core Pending, and Workbench Stage 7/8 tests.
- Full tracked-test suite: **2444 tests; 2409 passed, 2 skipped, 4 failed, 29 errors**. The 33 failed/error node IDs match the historical audit list **33/33**; every status and exception class matches; **0 new exception nodes and 0 confirmed new regressions**. The 33 are the documented private Foundation, Phase 3F, Production-binding, and ingestion-fixture prerequisites, not R1 failures.
- Frontend: **159 passed in 29 files**; TypeScript and production build passed. `compileall` and `git diff --check` passed.
- Production SHA256 before and after: `6e5a303ccee9c192c350c2550cc232649e56ffee939b7a09cd6b170cc1c8fba1`. Real Workbench SHA256 before and after: `1ff852dbe76c5fc4054c3e6f4e308b98a66f918dc3081e287b793c682a61ca44`.
- Real provider calls, Knowledge Community reads/writes, Production writes, and real Workbench writes: **0** each.

### Full-suite environment

The ignored root `config.toml` is local runtime configuration. Some historical tests call `load_config()` with no path; other hash-bound tests read private local prerequisites. Copying `config.example.toml` into the PR worktree did not reproduce that environment, and the earlier isolated worktree run raised 43 missing-config errors. The final suite ran from the historical root checkout with its existing local config and fixtures; no config or credential value was copied, printed, or committed. Live provider credential environment variables were cleared for the test process.

A test-only import hook loaded exactly the four Stage 7.2A Python modules from PR #76 (`llm`, `cloud_contract`, `provider_diagnostics`, `workbench.cloud_jobs`); unchanged modules stayed byte-identical to the historical root checkout. The root's two unrelated untracked-only test files were excluded, and the PR versions of the three changed test files were used. Pytest's fresh temporary directory was inside the configured `workspace`, as required by the ingestion fixture. An initial mixed-checkout run caused three unrelated hash/runtime-identity failures; a corrected full run removed all three. The final JUnit file is in the root checkout at `workspace/r1full6.xml` and was compared against `docs/phase43_stage7_full_suite_exception_audit.json` by node ID, status, and exception class.

**Next action:** Rerun the full Stage 7.2A pre-merge audit against the new PR #76 head. Keep PR #76 Draft and unmerged; do not retry the real Stage 7.2 pilot yet.
