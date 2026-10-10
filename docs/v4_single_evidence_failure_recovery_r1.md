# V4 single Evidence failure recovery qualification

This internal Operator path reserves one independent Attempt 2 after exactly one
original v4 Claim or Node Match selector fails with `EVIDENCE_SELECTOR_NOT_FOUND`.
It reuses the existing same-Batch retry transaction and bounded ledger. The
normal malformed-JSON retry remains restricted to its original failure family.
Historical strict recovery and lossless Evidence regeneration retain all their
original population, prior-grant, and compatibility requirements.

## Scope and identity

- Internal method: `SourceOperations.authorize_single_evidence_retry`.
- Policy: `v4-single-evidence-same-batch-retry-v1`.
- Authorization event: `V4_SINGLE_EVIDENCE_RETRY_AUTHORIZED`.
- Authorization reserves one Attempt 2 and **dispatches zero calls**.
- Source, SourcePiece, Catalog, assigned Evidence, Series, Segment, original
  request, Provider configuration, model, Schema, and budget identity remain
  exact. No additional guidance or modified prompt is necessary.
- Original Attempt, Outcome, Raw, and existing events remain append-only.
- Only proven never-attempted leaves are reopened after fail-closed termination.
  Existing accepted results are preserved. No subdivision or replanning occurs.
- A second failure is terminal for this policy. Exact idempotent replay returns
  the existing reservation; conflicting authorization cannot reserve Attempt 3.
- Default v4, Evidence Binding v2, schema12, and public Web/MCP routes are unchanged.

The independent diagnostic does not infer semantic truth or repair an invalid
record. A new complete response must satisfy every existing Segment acceptance
gate. Quarantine or independently located original objects are never accepted.

## Cross-release qualification

An old frozen Run cannot use a new runtime merely because the Operator exists.
`assess_bounded_retry_compatibility(..., bounded_single_evidence_retry=True)` checks
the exact failed Attempt, immutable HTTP-200 tool Raw, frozen input/prompt,
configuration, full execution-surface manifests, non-runtime Context, and native
checkpoint. A qualification event binds the precise old and target identities.

The lossless runtime fingerprint may differ only in three qualified Operator
files: extraction retry, compatibility qualification, and SourceOperations.
All aggregate/replay protocol fields and other module hashes remain exact.
SourceOperations execution methods are separately compared using the existing
AST manifest. Target qualification hashes bind the complete Operator source.
Changes to aggregate meaning, validators, Provider contracts, model, Context,
or native execution remain incompatible.

## Explicit execution sequence

1. On the exact installed candidate release, assess with `persist=False` and
   review the concrete Source/Run/Attempt identities and budget.
2. After separate HUMAN_USER authorization, persist qualification and invoke the
   internal authorization method. This creates Attempt 2 without dispatch.
3. Reconstruct the frozen worker and Provider configuration. Execute the existing
   bounded-only resume with an explicit call ceiling and first-failure stop.
   It forbids subdivision and stops before Semantic registration.
4. Only after complete accepted Coverage, freeze the actual Semantic batch budget
   and obtain separate authorization. Continue the existing default v4 native
   path to formal Review Packet.
5. MCP dual review, HUMAN_USER decisions, Seal, and Production Promotion retain
   their existing independent authorization requirements.

For a four-leaf Source with its first Attempt failed, completion needs at most
four new Extraction calls: Attempt 2 plus three untouched leaves. The additional
maximum output reservation is 96,000 tokens. These are reservations, not a
prediction of actual usage. The failed call still counts against Series budgets.
Semantic calls depend on the actual accepted parent Claims and frozen batching;
they are not included in the Extraction authorization.

## Qualification evidence

`tests/test_v4_single_evidence_retry.py` uses generated synthetic PDF text and
local transports through the normal v4 adapters and native Workbench pipeline.
It covers four-leaf Coverage, immutable failed lineage, exact Attempt 2 identity,
restart, second-failure stop, concurrency/idempotency, invalid scope, and formal
Semantic/Review Packet continuation. The cross-release case creates its failed
fixture using the actual installed baseline interpreter; it never invents an old
Git/runtime identity or prior historical recovery grant.

Qualification completed: all six new focused tests and all nineteen existing
malformed-JSON retry regression cases passed. The original missing-runtime
regression was repaired and its exact case rerun; failed or interrupted earlier
runs are not counted as passes. Cross-release qualification and native continuation
used the installed baseline dependency versions; dependency drift remains blocked.
Both same-release and actual-baseline cross-release fixtures reached a registered
formal Review Packet after four accepted leaves, without changing the synthetic
Production database. These are synthetic results, not real accepted research.

This policy does not improve or certify a future model response. It permits one
explicit fresh complete response with unchanged input, prompt and strict gates;
that response may fail again and then must stop.

All real Source, Raw, request, response, local paths, and operational receipts
remain outside this document and the public Git commit. This qualification does
not authorize a real retry, merge, Stable activation, Semantic execution, review
decision, or Promotion.
