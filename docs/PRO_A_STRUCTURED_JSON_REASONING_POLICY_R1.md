# Structured JSON reasoning policy R1

Baseline: `7d34055477a1997888db1c7315ab0d59becc17a0`.

Implementation commit: `b7ec404d8c6eaa9eec2693ca75beb238c8cdbf7c`.

`PRO_A_STRUCTURED_JSON_REASONING_POLICY_R1 = PASS`.

## Motivation and evidence boundary

The fourth real qualification Run failed on a 4828-character Source piece and a
7649-character user prompt. Durable telemetry records HTTP 200, requested and
reported model `deepseek-flash`, 6465 input tokens, 8192 output tokens against an
8192 output limit, 14657 total tokens, and 2432 cached tokens. The result was
`TRUNCATED`, `finish_reason=length`, `content_length=0`, invalid JSON syntax,
error position 0, and `retryable=false`.

Historical reasoning-token usage was **not retained**. These observations do not
prove that visible final JSON requires more than 8192 tokens, and do not prove
`reasoning_tokens=8192`. Exhaustion of the completion budget during reasoning is
the motivating hypothesis, not a retrospective measurement. No historical
telemetry is backfilled.

DeepSeek's [Chat Completions contract](https://api-docs.deepseek.com/api/create-chat-completion/)
and [Thinking Mode guide](https://api-docs.deepseek.com/guides/thinking_mode/)
document thinking enabled by default, the explicit `thinking.type=disabled`
control, a separate reasoning-content response field, and an optional reasoning
token breakdown. R1 uses only the explicit thinking toggle and sends no
`reasoning_effort` field. Official documentation was checked during qualification.

## Frozen operation policy

The single policy is `structured-json-reasoning-v1`, with thinking mode
`disabled`. Constants live alongside existing application constants; there is no
environment flag, per-request operator option, or mutable policy table.

| Operation | Thinking | Adapter |
|---|---|---|
| SOURCE_ANALYSIS_PIECE | disabled | source-analysis-piece-adapter-v2 |
| SEMANTIC_DECOMPOSITION | disabled | semantic-backend-adapter-v2 |

Each `operation_contract` includes `thinking_policy_version` and `thinking_mode`.
CloudJobs already freezes the complete contract in `prompt_json`, the submission
intent, and the request identity. The new fields consequently participate in
`intent_sha256` and each job's frozen request without duplicating mutable state.
Prompt-text hashes remain unchanged. A focused test changes only the policy
version and verifies a different intent while the existing job row remains exact.

Before dispatch, both real providers require the frozen version, mode and adapter
identity to match. Extraction explicitly supplies the keyword to ChatLLM; the
semantic ChatLLM backend declares and supplies the same mode. A backend without
an explicit compatible policy fails closed. Mismatch returns bounded
`PROVIDER_REASONING_POLICY_MISMATCH` with `NOT_DISPATCHED` and no retry.

`ChatLLM.json(system, user, *, thinking_mode=None)` retains the previous request
payload when unspecified. The only supported explicit mode is `disabled`, which
adds exactly `"thinking": {"type": "disabled"}`. Other modes fail before dispatch.
This does not globally select a reasoning policy for unrelated model callers.
The Phase 4 execution wrapper forwards the optional keyword unchanged; its
transport retry policy, event ownership and attempt counts remain unchanged.

## Numeric telemetry and privacy

Only `usage.completion_tokens_details.reasoning_tokens` is read for the new
telemetry. The count must have exact integer type (bool is rejected), be within
0 through 10000000 inclusive, and not exceed a valid completion-token count.
Malformed, absent or inconsistent counts become null; an omitted field is not
invented as zero. `CloudResult` additionally rejects invalid explicit counts and
requires all usage counts to be null for UNKNOWN usage. KNOWN usage still allows
a null reasoning breakdown.

Failure diagnostics add this field to the existing content-free allowlist.
The count does not enter the error fingerprint. Successful attempts retain it
in the private result artifact's `usage` and the hash-chained
`PROVIDER_ATTEMPT_COMPLETED` event. Artifact reconciliation validates the optional
count and preserves it in the completion event without another provider call.
Existing artifacts without a breakdown remain readable as null. No Workbench
schema migration or new database column is introduced.

`message.reasoning_content` is never accessed, copied, hashed, measured, logged,
or persisted. No reasoning prefix, suffix, excerpt, tail or parser message is
retained. HTTP/envelope exceptions now omit raw response bodies because those
bodies may contain reasoning text. Failure classification, retry decisions,
JSON parsing, and final-content handling remain unchanged.

## Preserved contracts and compatibility

- Capacity: `source-analysis-capacity-v1`, 5000 characters.
- Planner: `PHASE3E2SL6_PRECALL_PARTITION_V2`.
- Output/total budgets: 8192/20000 for both operations.
- Limits: 16 extraction pieces and 31 total jobs.
- Source and semantic prompt text, JSON-object response format, temperature,
  timeouts, parser permissiveness, semantic batching and retry ownership remain unchanged.
- No adaptive split, 4k fallback, output-budget increase, or Stage 1 bypass.

The v2 adapter identities distinguish the new wire semantics. Old v1 profiles
and frozen jobs are not silently normalized: unsupported reconstruction fails
closed while retaining the original persisted identity. Stage 7.2C comparisons
against the exact baseline fail on both cloud and native execution surfaces with
`SEMANTIC_SURFACE_CHANGED`. No compatibility exception is added for a historical
Run, including the fourth Run.

## Offline qualification

**41 focused tests passed**. Required and related regressions: **526 passed, 2 skipped, 0 failed**. In total, **567 distinct passed**. Skip reasons are recorded in the [sanitized JSON receipt](pro_a_structured_json_reasoning_policy_r1_receipt.json).

The initial required/related matrix had 524 passes, two failures and two skips.
Both failures exposed the missing Phase 4 wrapper keyword forwarding. After the
repair, all focused policy, ChatLLM and Phase 4 tests were rerun: 117 passed and
one private-fixture test skipped. The counts above use the latest result per
test and do not double-count reruns. The two remaining skips require unavailable
private frozen workflow/semantic qualification fixtures.

The focused suite covers both exact wire payloads; unchanged generic requests;
strict nullable token validation; counts 0, 1, 25, completion-token equality and
invalid bounds/types; frozen intent and policy mismatch; historical v1 rejection;
and crash recovery without an extra provider call. A synthetic truncation has
8192 reasoning tokens, 8192 completion tokens, empty final content and `length`;
it validates telemetry handling without asserting that the historical Run had
this breakdown.

The full disposable SourceOperations flow uses the real extraction and semantic
adapter classes with synthetic HTTP responses. Both requests carry disabled
thinking and no reasoning effort, and both durable results/events record zero
reasoning tokens. The flow reaches one registered Review Packet and
`HUMAN_REVIEW_REQUIRED`, with no Review decision and no Production mutation.
Tests scan Workbench tables, cloud events, result artifacts, public job DTOs,
captured logs and a generated qualification receipt for an in-memory reasoning
sentinel. Valid final JSON continues through the normal pipeline.

Build qualification checks the isolated PEP 517 wheel, all packaged Python bytes
against source and isolated installation, policy/adapter identities, dependency
consistency, compileall, and protected code surfaces. The final JSON receipt
records exact counts and any unavailable-fixture skips. No full-repository test
success is claimed unless actually executed.

## Real-state and deployment boundary

Read-only before/after snapshots match exactly: Source identity and bytes; all four historical Runs and their job/attempt/outcome/event digests; every Workbench table digest; Production and Workbench integrity, schema, row counts, file hashes and sizes; and stable runtime metadata. Historical attempts remain **0 / 2 / 1 / 1**. The fourth Run remains failed, with its later pieces uncalled.

No real provider call, new Run, historical retry/backfill, Review decision/seal,
Attribution or Current View mutation, Production Apply, or retry extension is
part of this stage. Private Source text, prompts, real identifiers, filenames,
paths and credentials are excluded from publication.

`STABLE_RUNTIME_ACTIVATION_REQUIRED_AFTER_MERGE = true`

`LIVE_NON_THINKING_VALIDATION_REQUIRED_AFTER_MERGE = true`

Publication stops at a Draft PR. The stable runtime is not activated or restarted.
A later authorized operation must merge and activate first, then use the existing
Source in a new Run to measure reasoning tokens, completion tokens, content length
and finish reason with real DeepSeek. This stage makes no live-success claim.
