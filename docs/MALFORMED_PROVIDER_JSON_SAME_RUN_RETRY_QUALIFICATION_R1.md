# Malformed Provider JSON Same-Run Retry Qualification R1

Status: **PASS**

This stage qualifies one operator-authorized retry of a durable provider tool-arguments JSON syntax failure. It does not execute the live Run #13 retry.

## Design

The implementation reuses the Stage 7.2B retry entrypoint, schema-12 bounded extraction ledger, deterministic Attempt identity, SQLite writer serialization, fencing, immutable raw envelopes, and reconciliation logic. It reuses the Stage 7.2C runtime/context/native compatibility token. No schema or second retry engine was added.

Eligibility is an explicit whitelist: the original call must have a durable HTTP-200, non-truncated `tool_calls` outcome; its strict UTF-8 body must fail `json.loads` with `JSONDecodeError`; the target Segment must have failed at the provider structured-output parsing boundary; and no target result, Series aggregate, Semantic Job, runtime/config/context drift, or ledger corruption may exist. Valid JSON that fails Claim linkage, Evidence Binding, selector, ownership, or another semantic contract remains non-retryable.

Authorization creates deterministic Attempt 2 with the exact original request, provider configuration, budget identity, Run, Series, Segment, SourcePiece, Evidence assignment, ownership, prompt, and frozen context. The append-only Series event records `MALFORMED_PROVIDER_JSON`, the original Attempt, original raw SHA, parser telemetry, idempotency key, and compatibility qualification identity. Attempt 1 and its raw/outcome/failure events are never changed.

There is no JSON repair, tolerant parser, prompt rewrite, subdivision fallback, automatic provider call, or third Attempt. A second malformed response fails closed.

## Recovery and compatibility

Synthetic fault injection covers crashes after retry reservation, dispatch durability, raw durability, outcome durability, and result acceptance. Raw/outcome/result recovery reconciles existing durable state without recalling the provider. The result-accepted window now closes the already accepted Segment exactly once.

The stable-to-implementation Run #13 path was assessed read-only with network access prohibited and `persist=false`. Both cloud and native execution surfaces were `SEMANTIC_SURFACE_EXACT`; the result was `ALL_REQUIRED_DIMENSIONS_COMPATIBLE`. Semantic/context/config/runtime/surface drift cases fail closed.

## Qualification boundary

- Focused retry tests: 19 passed.
- Required related tests: 336 unique tests passed, zero failures.
- Build: compileall, pip check, isolated PEP 517 wheel, 142-file source/wheel/install byte equality, and no-Git runtime identity all passed.
- Real provider calls: 0.
- Run #13 calls: 2 before and 2 after.
- Run #13 remains BLOCKED; Run #14 does not exist.
- Workbench, Production, Current View, private artifacts, and original raw hashes are unchanged.

Draft PR: https://github.com/ysssss414/pro_a/pull/107

PR #106 remains an independent forensic-only Draft and is not required by this implementation.
