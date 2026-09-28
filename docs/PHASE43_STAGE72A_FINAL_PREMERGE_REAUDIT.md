# Phase 4.3 Stage 7.2A — final pre-merge re-audit

**Decision: PASS for the complete PR #76 audit target `ce81f6172f304b7e1f0a1a411a59f9993a006035`.** The provider outcome replay preserves the frozen main business behavior, while the new diagnostic paths retain useful classifications without exposing the injected private markers. PR #76 remains OPEN, Draft, and unmerged. This is a qualification decision; no real Stage 7.2 pilot was retried.

## Boundary and history

`git fetch origin` confirmed `origin/main` at `9179e28e73c8658b4893729a90f40166f556a0bd`. `gh pr view 76` confirmed OPEN, Draft, unmerged, base `main`, and head `ce81f6172f304b7e1f0a1a411a59f9993a006035`. The base-to-head diff contains four provider/CloudJobs runtime modules, three tests, and six Stage 7.2A implementation, audit, and repair documents/receipts; no routing, domain, frontend, migration, or unrelated runtime file changed. `git diff --check` passed. No rebase occurred.

The initial implementation was self-qualified at `93298cd6337df61b286d3c88ccfc07056ad99901`; the first independent pre-merge audit correctly marked **that head BLOCKED** for business drift, lost HTTP context, a secret-looking response identity, and a non-equivalent full-suite environment. The R1 code repair at `658e13e11a18abe44e4b6ea654790f6220de0f8d` has its own PASS qualification. This report independently audits the later, complete PR head, including the R1 evidence commit. It does not rewrite the earlier BLOCKED decision.

## Business-state differential replay

Fresh isolated fixture databases were created separately for frozen main and the PR head. All HTTP and transport outcomes were supplied by a stubbed `requests.post`; the success and unexpected-exception cases used offline provider doubles. Eleven identical Job outcomes were compared by final state, public error, propagated exception class, attempt count, `RETRY_AUTHORIZED` event count, and result-registration presence. **Eleven of eleven matched exactly.**

| Outcome | Business result on both versions |
| --- | --- |
| Success | `SUCCEEDED`, one attempt, result registered |
| HTTP 401, including a diagnostic JSON parser that raises unexpectedly | `FAILED / AUTHENTICATION_ERROR`, one attempt, no retry |
| HTTP 429 | `FAILED / RATE_LIMITED`, two attempts, one retry authorization |
| HTTP 503 | `FAILED / PROVIDER_UNAVAILABLE`, two attempts, one retry authorization |
| Connect timeout and read timeout | `RECOVERY_REQUIRED / UNKNOWN_EXTERNAL_OUTCOME`, one attempt each |
| Invalid HTTP 200 JSON and invalid model output | `FAILED / PROVIDER_ERROR`, one attempt each |
| HTTP 200 application output rejection | `FAILED / OUTPUT_VALIDATION_FAILED`, one attempt, rejected result registered |
| Unexpected provider exception | Original `RuntimeError` propagates; Job remains `RUNNING`, with no retry or result |

Three separate Source Run fixture replays also matched by Run state, Job state, public Job error, and exception class: success, mapped authentication failure, and unexpected exception. Each remained `EXTRACTION_PROCESSING` at the compared point; the corresponding Job outcomes were respectively `SUCCEEDED`, `FAILED / AUTHENTICATION_ERROR`, and `RUNNING` with propagated `RuntimeError`. The full-suite tests separately exercise later Run transitions.

## Original blockers and diagnostic gates

| Gate | Result and independent evidence |
| --- | --- |
| Observability only; business-state equivalence | PASS. Eleven Job and three Source Run differential cases match frozen main. Unexpected exceptions now rethrow after best-effort allowlisted logging. |
| HTTP 401 classification | PASS. The 401 parser-failure synthetic case remains `AUTHENTICATION_ERROR`, with diagnostic `HTTP_401`, `HTTP_RESPONSE`, status 401, and `retryable=false`. |
| Known HTTP context | PASS. Invalid JSON is `PROVIDER_PARSE / 200`; invalid model output is `MODEL_OUTPUT_PARSE / 200`; schema rejection is `OUTPUT_VALIDATION / 200`. A rejected durable artifact retains 200 after cold reconciliation without a second provider call. |
| Provider request ID | PASS. Only `x-request-id`, `request-id`, and `x-ds-request-id` response headers feed the request ID. Generic completion/body `id` is ignored. The validator accepts only strings in bounded recognized request-ID or UUID forms and rejects controls, whitespace, blobs, bearer/cookie/token-like values, and the injected unsafe candidate by returning `null`, without truncation. |
| Central sanitization and secret surfaces | PASS. `build_failure_diagnostic` allowlists stages, classes, status, provider error type/code, size, time, generated summary, and fingerprint before event persistence. Result metadata is normalized before artifact and DB registration; the API projection validates IDs again. Four synthetic private markers were injected into exception messages, provider type/code, request-ID candidates, response headers, nested metadata, JSON fields, and result metadata. Focused tests inspected entire synthetic state DBs (including Job rows, events, and outcomes), Job/API DTOs, result artifacts, and captured logs. A literal scan of the generated focused-test and full-suite temporary trees, replay trees, and fresh JUnit found **zero marker-bearing files**. |
| Full response body policy | PASS. HTTP and parse failures persist structural diagnostics only. Rejected result artifacts store `raw_provider_output=null` and carry no raw prompt, request/response body, Authorization, Cookie, or private source content. The only added transport field is a validated numeric HTTP status. Existing private Source/input artifacts remain governed by their pre-existing Workbench contract; the failure diagnostic does not copy them. |
| Failure taxonomy | PASS. Stages, classes, HTTP status, retryability, SHA-256 fingerprint, and generated summary remain bounded and machine readable. 401, 429, 503, transport subtypes, provider parsing, model parsing, and output validation retain distinct values; fingerprints exclude request identity, time, and content. |
| Event/API compatibility | PASS. No database migration. New event JSON fields and the Job/Run diagnostic projection are additive; `.get("diagnostic")` tolerates old events without that field. The reconciler accepts both old artifact keys and the optional validated `http_status` key. Canonical JSON and existing event hashing remain in use. |
| Success and Stage 7.1 | PASS. The fresh backend suite includes 28/28 diagnostics cases, 14/14 Shared Core Pending cases, 15/15 Stage 7 Source Operations cases, 33/33 CloudJobs Stage 6 cases, and 36/36 ChatLLM cases. These cover provider-double and fake extraction success, CloudJob completion, Run progression, `SHARED_CORE_PENDING`/`PENDING`, and the legacy `run-domain-context-v1` `DOMAIN_ACTIVATION_REQUIRED` guard. Routing code is absent from the base-to-head diff; successful offline ChatLLM/adapter paths still pass. Frontend: 159/159 tests; TypeScript and build pass. |

The committed diagnostics matrix passed **28/28** on the current head: the original 19 cases and nine R1 audit regressions. No test expectation was changed during this re-audit.

## Full repository regression environment

The fresh full Python run used the historical root checkout's ignored local `config.toml` and already present private prerequisites; no configuration or credential value was copied, printed, or committed. Live provider credential environment variables were cleared. A temporary import hook loaded precisely the four PR runtime modules (`llm`, `cloud_contract`, `provider_diagnostics`, `workbench.cloud_jobs`); unchanged modules and scripts stayed at the frozen root checkout. The three PR test files were collected explicitly, while two unrelated untracked root tests were excluded. `--import-mode=importlib` avoided duplicate module-name collection, and a fresh `--basetemp` stayed under the configured `workspace`. This fully described overlay is test-only and is not a runtime dependency.

Fresh JUnit: `workspace/reaudit_full.xml` in the local root checkout. Result: **2444 total; 2409 passed, 2 skipped, 4 failed, 29 errors**. The 33 failure/error entries match `docs/phase43_stage7_full_suite_exception_audit.json` exactly by node ID, status, and exception class: **33/33 historical matches, zero missing, zero new**. The failures remain the documented private Foundation, Phase 3F, Production-binding, and ingestion-fixture prerequisites. The previous R1 JUnit was used only to validate the comparison parser; the final decision uses the historical audit ledger and the new JUnit.

## Real-state and external-effect boundary

Production SHA-256 before and after: `6e5a303ccee9c192c350c2550cc232649e56ffee939b7a09cd6b170cc1c8fba1`. Real Workbench state SHA-256 before and after: `1ff852dbe76c5fc4054c3e6f4e308b98a66f918dc3081e287b793c682a61ca44`. Tests wrote only disposable fixture databases. Real provider calls, Knowledge Community reads, Knowledge Community writes, Production writes, and real Workbench writes were **zero**.

**Disposition:** Stage 7.2A is eligible for a separately authorized release handoff. Keep PR #76 Draft and unmerged in this audit step. Release handoff must mark it Ready, merge under repository governance, verify remote main, and close Stage 7.2A before any real Stage 7.2 pilot retry.
