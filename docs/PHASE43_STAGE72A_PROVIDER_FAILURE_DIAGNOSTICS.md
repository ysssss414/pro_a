# Phase 4.3 Stage 7.2A — Provider failure diagnostics

Status: **initial self-qualification superseded**. The implementation at
`93298cd6337df61b286d3c88ccfc07056ad99901` passed its original 19-case suite, but
the independent pre-merge audit found behavior drift and secret leakage and marked it
BLOCKED. The narrow R1 code repair at `658e13e11a18abe44e4b6ea654790f6220de0f8d`
has a separate PASS qualification in `PHASE43_STAGE72A_R1_AUDIT_REPAIR.md`.
This work was developed from `origin/main` at
`9179e28e73c8658b4893729a90f40166f556a0bd` on the separate
`codex/phase43-stage72a-provider-failure-diagnostics` branch. The blocked
Stage 7.2 pilot branch remains at `f8ab4d3380663da1f9072acd45ee0874a03fa73c`.
No real provider or Knowledge Community operation was performed.

## Existing execution path and loss point

| Stage | Implementation and exception boundary | Previous durable record / logging | Lost information |
| --- | --- | --- | --- |
| Workbench request and job creation | `source_operations.py` advances `SOURCE_READY`, registers a source analysis input, and binds a CloudJob. `CloudJobs.submit` records operation and provider profile. | Source Run and CloudJob identities, profile, and hashes. | No failure yet. |
| Routing | The existing pilot operator script `route_and_export.py` wraps ZSXQ `urllib.request.urlopen` and records the successful DeepSeek response `id` in its separate private routing receipt. | Routing receipt contains the successful request ID. | This success was outside CloudJobs and does not imply extraction failure telemetry. |
| Dispatch and transport | `CloudJobs.run_once` records dispatch intent and `CALL_POSSIBLE`, then calls `provider.invoke`. `ChatLLM.json` calls `requests.post`. | Attempt count and possible call; `ChatLLM` logs attempt number, exception class, HTTP status and retry flag without response text. | Prior failed attempts did not pass HTTP status, request ID, or transport subtype to durable job state. |
| HTTP and provider parsing | `ChatLLM.json` raises `LLMError` for HTTP, response JSON, provider envelope, and model output failures. `SourceAnalysisPieceProvider.invoke` catches it. | Adapter previously mapped to a broad `ProviderFailure.code`. | The adapter inspected status to choose a code, then discarded it and the response ID. It also used exception text to recognize transport failure. |
| Output validation | `CloudJobs.run_once` calls `validate_output`. | `OUTPUT_VALIDATION_FAILED`; a private rejected artifact previously included `raw_provider_output`. | No stage or class persisted; rejected provider output could include prompt echo or private material. |
| Persistence and Run projection | `_record_provider_failure` wrote only the code and outcome. `_project` returned `last_error`; `SourceOperations.get_run` included the job DTO. | Failed job and Run status. | No structured failure layer, HTTP status, provider code/type, or fingerprint. |

The routing request ID was retained because the pilot operator intercepted a **successful**
response before parsing it. Extraction used a different path: `ChatLLM` did not retain
request IDs from failed HTTP responses, and the adapter/CloudJobs boundary reduced the
remaining error to a code. The historical failed Run is unchanged and cannot be
retroactively classified from these new fields.

## Repair

`ChatLLM` annotates each offline or real attempt with safe structural facts:
HTTP status, a validated request ID from known response headers, bounded provider
error type/code, response content class and size, request payload byte count,
timestamps, duration, failure stage, and error class. It does not pass response
text or exception messages into the durable diagnostic. The source analysis and
semantic adapters pass these facts through `ProviderFailure` without changing
their existing code or retry mapping. Under R1, unexpected provider exceptions
propagate as before; a best-effort allowlisted warning records their diagnostic
without changing the Job or Run state.

`CloudResult` carries in-memory safe transport metadata so application output
validation failure can retain an actual HTTP 200 status and request ID without
retaining model output. `CloudJobs` builds one allowlisted diagnostic object, appends it to the existing
hash chained `PROVIDER_ATTEMPT_FAILED` event JSON, writes a recognized request ID
to the existing `cloud_attempt_outcomes` and `cloud_jobs` columns, and exposes
the latest diagnostic as `failure_diagnostic` in the job API. A failed Run's
existing `jobs` projection therefore includes it. New rejected result artifacts
set `raw_provider_output` to `null` and carry a validated HTTP status when known;
old artifact formats remain readable. The reconciler accepts a redacted rejected
artifact and retains its known HTTP status without another provider call.
No table or migration was added.

The diagnostic includes provider/model, endpoint class, operation type, job/call
and attempt identities, request ID, stage, class, HTTP status, whether a response
was received, whether request dispatch is known, retryability, timing and sizes,
provider error type/code when on the strict allowlist, booleans showing whether
the provider supplied those values even when the value was rejected, a generated safe summary,
and SHA-256 fingerprint. Fingerprints use only provider/model, operation type,
stage, class, status, and safe error type/code. They exclude source text, prompt,
response body, request ID, and timestamps. Unknown fields are `null` or `UNKNOWN`.
The known Workbench operation `SOURCE_ANALYSIS_PIECE` is `EXTRACTION`; semantic
decomposition remains `OTHER`, with its exact `operation_kind` also retained.
Routing remains a separate operator path; no routing request was executed here.

The request ID filter accepts recognized `chatcmpl-`, `req-`, `req_`, `request-`,
`request_`, or UUID forms and rejects secret-looking values. The generic JSON
completion `id` is never treated as a request ID; only known request-ID headers
feed that field. Provider error
type/code uses a finite identifier allowlist. Unsupported values become `null`
instead of persisting arbitrary provider-supplied text. The safe summary is
generated from class and status and is at most 500 characters.

## Qualification and limits

- The initial 19-case suite missed the audit's unexpected-exception and unsafe-ID paths. Its prior expectations for those paths were corrected against frozen main behavior and the R1 request-ID contract. Under R1 the 19 original cases and 9 additional audit cases pass.
- Final relevant backend suite: **133 passed**. This includes `test_llm.py`, 28 diagnostic cases, CloudJobs Stage 6, Stage 7.1 Shared Core Pending, Stage 7 Community, and Workbench Stage 7/8 tests.
- Frontend suite: **159 passed** in 29 files. TypeScript and production build passed. Frontend source was unchanged; the API addition is additive.
- `compileall` and `git diff --check` passed. The R1 full tracked-test suite ran in the historical local environment: **2409 passed, 2 skipped, 4 failed, 29 errors**. The 33 failed/error nodes exactly match the documented historical set by node ID, status, and exception class; no new regression was identified.
- The initial implementation's secret-leakage claim was disproved by the pre-merge audit. R1 tests inject four synthetic markers into headers, body IDs, provider error fields, nested exception metadata, and result metadata. The failed DB/API/artifact/log scans and final test-artifact scan found none. No failed full provider response body is persisted by the repaired paths.
- Production SHA before/after: `6e5a303ccee9c192c350c2550cc232649e56ffee939b7a09cd6b170cc1c8fba1`.
- Real Workbench SHA before/after: `1ff852dbe76c5fc4054c3e6f4e308b98a66f918dc3081e287b793c682a61ca44`.
- Real provider calls: **0**. ZSXQ reads/writes: **0 / 0**. Production writes: **0**. R1 new regression count: **0**.

R1 restores observability-only business behavior. It does not change prompts, model selection, timeout,
retry budget, output schema, or extraction rules, and it does not retry the
blocked real pilot. Any future bounded retry needs separate authorization after
review and merge of this repair.
