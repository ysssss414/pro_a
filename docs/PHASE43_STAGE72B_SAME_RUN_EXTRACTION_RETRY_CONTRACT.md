# Phase 4.3 Stage 7.2B — Same-Run explicit extraction retry

## State model

`source_processing_runs` is a current projection, updated by `_transition` and backed by append-only, hash-chained `source_processing_events`. A terminal failed **attempt** is immutable; a failed **Run projection** can change after an explicit retry command. Its processing identity and `domain_run_bindings` do not change.

The new command writes one `EXPLICIT_EXTRACTION_RETRY_ACCEPTED` Run event and transitions the current projection from `FAILED / EXTRACTION_JOBS / PROVIDER_ERROR` to `EXTRACTION_PROCESSING / EXTRACTION_JOBS`. The event records the new attempt/job and its parent. Old Job rows, attempts, dispatches, outcomes and Job events are neither updated nor deleted.

## Operator/API contract

Service: `SourceOperations.retry_failed_extraction(run_id, failed_attempt_id, retry_reason=..., idempotency_key=...)`.

HTTP: `POST /api/workbench/v1/source-operations/runs/{run_id}/attempts/{attempt_id}/retry` (authenticated session, Origin and CSRF controls apply).

Request contains only `retry_reason` and `idempotency_key`. Extra fields, including Source, context, Domain, provider, model and prompt overrides, are rejected. The reason must be 1–1,000 characters of trimmed single-line plain text. Controls, markup delimiters, and recognizable credential/header assignments are rejected. The reason is operator metadata, never appended to a prompt or provider request.

The response contains the immutable `retry` lineage, the new `job`, and `duplicate`. Acceptance queues execution; it does **not** call a provider. Reading, refreshing, starting the application or scheduling ordinary work does not create a retry command.

## Eligibility and frozen execution

Only an existing latest, terminal `FAILED / KNOWN_FAILURE / PROVIDER_ERROR` attempt for the effective `SOURCE_ANALYSIS_PIECE` Job of a `FAILED / EXTRACTION_JOBS / PROVIDER_ERROR` Run is supported. Uncertain external outcomes, security, acquisition, identity/context, persistence, successful and other failure stages are ineligible. A Run lease, active Run state, or queued/running Job prevents another retry.

Source bytes, the registered immutable input, the bound Run context, current prompt contract and the native execution checkpoint must validate before acceptance. Source bytes and input/context are checked again before dispatch. The original local PDF and input artifact are referenced; no Source, Run, private material copy, acquisition or routing operation is created.

The new Job copies the complete persisted provider/model/timeout/token/budget/prompt/runtime/configuration and checkpoint identities. An execution service reconstructed from those frozen settings performs the existing pipeline, even if the operator's **current cloud profile** has changed. A later Source Domain assignment does not relabel a pending-context Run.

Frozen native configuration is stored as a semantic digest plus its original local file reference. If the file is missing or its effective configuration changed, it cannot be reconstructed from the digest: return `RETRY_FROZEN_CONFIG_INCOMPLETE`, with no new Job/attempt. Comment-only TOML changes are not semantic drift.

**Runtime compatibility stays strict.** No current Git/code identity is substituted into old context, and no runtime override is introduced. Incompatible runtime/native checkpoint identity fails before acceptance. This stage qualifies retry orchestration; it does not supply a cross-release runtime compatibility proof. In particular, the real Stage 7.2 Run has a previously observed runtime difference from released main. This implementation alone does not certify that Run as dispatch-ready. Its frozen material/context hashes can be valid while its runtime gate remains blocked.

## Additive schema and lineage

Explicit offline command: `python -m pro_a.workbench --config <isolated-config> prepare-extraction-retries`.

This installs one additive extension table, `extraction_retries`, on existing domain-capable schema 9/10/11. Existing version metadata, rows, columns and triggers are unchanged. No startup migration occurs; an unprepared database returns `RETRY_SCHEMA_REQUIRED`. Repeating preparation returns `ALREADY_PREPARED`. The table has UPDATE/DELETE rejection triggers and foreign keys to Run, root Job, new Job and parent cloud attempt.

Each row holds:

| Field | Meaning |
| --- | --- |
| processing_run_id | Original Run |
| root_job_id | Original extraction slot's Job |
| job_id | New Job, unique |
| attempt_id | New reserved execution identity, unique |
| retry_of_attempt_id | Previous failed cloud attempt, unique |
| attempt_number | Next number in this extraction slot's lineage |
| retry_reason | Bounded operator input |
| trigger_type | EXPLICIT_RETRY |
| idempotency_key | Unique request identity |
| context_sha256 | Original frozen Run context |
| created_at | Acceptance timestamp |

There is no historical-row backfill: old attempts have no extension row. A pending attempt is represented by this reservation and its QUEUED Job. `cloud_attempts` remains the existing dispatch-intent ledger: its row is inserted with the **reserved ID and lineage number** when the single provider request is prepared. Thus accepting a command does not falsely record that a network call happened. Per-Job `attempt_count` remains a local call budget counter; the lineage/request `attempt_number` is 2, then 3, etc.

The original `source_processing_jobs` binding remains immutable. Execution resolves the latest retry for that extraction slot. Other successful extraction slots are reused. Detailed Run projection retains all historical Jobs and exposes the retry lineage separately.

## Atomicity and idempotency

`BEGIN IMMEDIATE` covers duplicate lookup, eligibility, frozen-input checks, new Job insertion, attempt reservation, events and Run projection update. A rejected request rolls back all writes. Unique constraints cover idempotency key, parent attempt, Job, attempt ID and `(root_job_id, attempt_number)`.

Same key + same Run + same failed attempt + same reason returns the same reservation/Job, including after completion. Reusing a key for different intent returns `IDEMPOTENCY_CONFLICT`. Concurrent different keys for the same parent yield one retry and `RETRY_ALREADY_IN_PROGRESS` for the other. Sequence derives from the terminal parent under the write transaction, not an unprotected row count.

## Execution and outcomes

One accepted command authorizes at most one extraction dispatch. Existing CloudJobs request building, provider invocation, validation, persistence, and Stage 7.2A diagnostics are reused. Explicit retry lineage prevents the ordinary Job failure handler from looping, even when diagnostic `retryable=true`; frozen provider policy values themselves remain unchanged. No adapter, HTTP format, parser, output schema or diagnostic semantics change.

Success is replayed through existing extraction, Claim/Evidence and semantic processing to `HUMAN_REVIEW_REQUIRED`. Any normal downstream semantic calls are distinct from extraction and must fit the separately authorized execution budget; qualification uses doubles for both. This capability does not grant a future real Pilot extra provider calls.

Known provider failure records a new failed attempt and diagnostic, and the Run projection returns to FAILED. Another retry requires the newly failed attempt, a new explicit reason/key, and all eligibility checks again. Unknown outcome and crash reconciliation retain existing conservative behavior; no extra extraction attempt is automatically authorized.

`start(..., reprocess_reason=...)` remains a separate operation creating a new Run, potentially with a new Domain/config basis. Retry never invokes it.

## Real-state boundary

Qualification uses synthetic Sources/Runs, temporary databases and provider doubles. No migration or retry command may run against the real Stage 7.2 Workbench in this stage. Real provider/ZSXQ calls and Production writes are zero. Real Production and Workbench byte hashes must match before and after.

After qualification, a separate pre-merge audit, merge and release closure are required. A later real retry requires separate authorization and fresh frozen-runtime/config eligibility checks.
