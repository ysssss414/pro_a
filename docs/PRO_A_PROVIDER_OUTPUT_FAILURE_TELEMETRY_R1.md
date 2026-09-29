# Provider output failure telemetry R1

Baseline: `5eb9d6bedd97a615a5ef56e143840e17aa8ba6ad`.

## Problem and resulting behavior

An HTTP-200 completion could fail after receipt while its durable diagnostic only
recorded `MODEL_OUTPUT_PARSE / OUTPUT_PARSE_ERROR`. `ChatLLM.json` already recorded
finish reason, response model, token usage, content length/hash and syntax metadata
in memory. `SourceAnalysisPieceProvider` and `_llm_provider_failure` passed that
dictionary onward, but `build_failure_diagnostic` discarded those fields and the
failure outcome insert left existing usage/finish columns empty.

Future failures preserve strictly validated, content-free metadata. For example,
`finish_reason=length` now records `output_parse_kind=TRUNCATED`, while a failed
JSON parse with `finish_reason=stop` records `MALFORMED_JSON`. Both still fail with
their previous error and retryability; neither output is repaired or accepted.

Cached token counts were not previously extracted by this ChatLLM path. It now
records DeepSeek `prompt_cache_hit_tokens`, or standard
`prompt_tokens_details.cached_tokens` when the DeepSeek field is absent.

## Safe diagnostic contract

New fields are available for `MODEL_OUTPUT_PARSE`; other stages receive null output
fields and retain their established stage/class and retryability.

| Field | Validation |
|---|---|
| finish_reason | stop, length, content_filter, insufficient_system_resource, tool_calls, function_call; other values null |
| response_model | Existing safe identifier validation, including sensitive marker rejection |
| prompt_tokens, completion_tokens, total_tokens, cached_tokens | Exact integer type, 0 through 10,000,000; booleans excluded |
| content_length | Exact integer, 0 through 100,000,000 |
| content_sha256 | Exactly 64 lowercase hexadecimal characters |
| raw_response_syntactically_parseable | Boolean only |
| raw_response_json_error_position | Exact integer, 0 through 100,000,000 and at most valid content_length when present |
| output_parse_kind | The explicit enumeration below; invalid values null |

Invalid strings are never truncated into accepted values. Free-form parser error
messages are excluded. The content hash is computed only from model output;
credentials are not hashed.

`output_parse_kind` is assigned directly in the existing authoritative ChatLLM
branches: `TRUNCATED`, `MALFORMED_JSON`, `NON_OBJECT_JSON`, `EMPTY_CONTENT`,
`CONTENT_FILTER`, `INSUFFICIENT_SYSTEM_RESOURCE`, `TOOL_CALLS`, and
`UNEXPECTED_FINISH_REASON`. Arbitrary provider finish text is discarded; an
unexpected reason remains identifiable by its safe subtype. No exception-string
parsing is used to assign the subtype.

## Persistence and fingerprint

The existing `PROVIDER_ATTEMPT_FAILED` diagnostic object carries the additive safe
fields. There is no schema migration, new table, or historical backfill.

The existing `cloud_attempt_outcomes` columns receive safe model, finish reason and
latency, plus `usage_status=KNOWN` only when all three required input/output/total
counts pass validation. Otherwise the outcome remains UNKNOWN with null counts.
Cached usage is optional; an invalid cached value does not invalidate valid required
counts. The event can retain individually valid counts even when complete outcome
usage is unknown. Existing cloud job state transitions, budget reservations and
retry decisions are unchanged.

The fingerprint includes safe output subtype and finish reason when available.
TRUNCATED and MALFORMED_JSON now differ. It excludes output hash/length, parser
position, request ID and timestamps, so the same failure class clusters across
different content. Failures without the new categorical metadata retain the prior
fingerprint input. Historical event bytes are not rewritten.

## Privacy and unchanged behavior

Failure persistence excludes raw model content, prefixes/suffixes, content_tail,
raw provider bodies/JSON, prompt or Source text, evidence excerpts, exception
messages, authorization headers, cookies and secrets. Existing transient exception
and attempt objects are not copied into durable records. Synthetic privacy tests
inspect all Workbench table values, events/outcomes, artifacts, a qualification
receipt and captured logs; injected private-output sentinels are absent.

`_extract_json` is unchanged, including its existing fence and surrounding-prose
handling. No JSON repair, new retry, retryability change, prompt change, routing
change, output budget change, chunking change or SourceOperations/Review/Production
workflow change is included. The extraction budget remains 8192 and
`FROZEN_ACCEPTANCE_INITIAL_MAX_CHARS` remains 10000. Existing successful dual-adapter
processing and Review packet registration are covered by regression tests.

## Qualification

The adjacent JSON receipt records final test counts, wheel verification and gates.
Focused tests cover all eight subtypes, known/missing/invalid usage, cached counts,
strict numeric/hash/enum boundaries, privacy, fingerprint grouping and non-output
failure classification (including HTTP 401/403/429/500/503, transport, response
schema and response JSON errors).

Required regression files:

- tests/test_llm.py
- tests/test_workbench_stage6.py
- tests/test_workbench_stage7.py
- tests/test_phase43_stage72a_provider_diagnostics.py
- tests/test_phase43_stage72b_extraction_retry.py
- tests/test_phase43_stage72c_retry_compatibility.py
- tests/test_cloud_operation_adapter_binding.py
- tests/test_mcp_stage0.py
- tests/test_mcp_stage3.py
- tests/test_phase43_stage71_shared_core_pending.py

Additional gates: compileall, pip check, isolated PEP 517 wheel build, all 129
packaged Python files byte-matched to working source, protected-code comparison,
diff whitespace check and publication privacy scan. This is a targeted regression
matrix, not a claim that the full repository suite ran.

Real database inspection uses read-only connections. Before/after integrity,
schema/row-count fingerprints, DB file hashes/sizes, both historical Run rows,
failed job rows, attempts and outcomes must match. Existing attempts remain two;
no telemetry is retroactively fabricated. Private identifiers and operator paths
are retained only in local uncommitted evidence.

## Runtime and recovery boundary

Stage 7.2C comparison against the baseline returns `SEMANTIC_SURFACE_CHANGED` for
both native and cloud execution surfaces. This is an execution-surface change;
there is no compatibility bypass or historical runtime-SHA rewrite. Any future
recovery needs its own authorization and qualification; a new Run after merge and
activation is preferred unless separately proven compatible. No real retry or new
Run is performed by this change.

`STABLE_RUNTIME_ACTIVATION_REQUIRED_AFTER_MERGE = true`.

The feature branch is not installed in the stable runtime. No Tunnel restart,
ChatGPT app recreation, real provider call, retry-extension installation, or real
processing is part of this qualification. Publication stops at a Draft PR.
