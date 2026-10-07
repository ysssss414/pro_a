# Run14 truncation subdivision recovery qualification

This candidate adds an explicit, zero-provider-call operator for a durable
bounded-only truncation stop. It does not release the candidate, recover the
real Run14, retry a provider, or enter Semantic. Real Run14 remains blocked with
two calls; Run13 remains unchanged with four calls.

## Capacity policy

Run14's first 16-ref Segment succeeded. Its second 16-ref Segment returned
HTTP 200 with 12000 output tokens, finish_reason `length`, and incomplete tool
arguments. Capacity evidence is confirmed; another root-cause investigation
is unnecessary. Output density differs between Segments, so a global 8-ref
policy is not justified.

Initial Evidence ownership remains 16 refs and the per-call ceiling remains
12000. Only a confirmed truncation permits deterministic midpoint subdivision:
16 to 8 plus 8, then 8 to 4 plus 4 after another explicit recovery if necessary.
Existing depth, leaf, provider-call and cumulative liability limits remain
authoritative. No Claim-count cap or new materiality scoring is introduced.
The materiality-weighted selective extraction objective is unchanged.

## Explicit operator

`SourceOperations.recover_truncated_bounded_extraction` accepts a Run ID,
root Attempt ID, worker ID, idempotency key and bounded sanitized reason.
Its contract is `bounded-truncation-recovery-operator-v1`: exactly one
subdivision, zero provider calls, no retry, no replan and no Semantic work.
It is not an HTTP, frontend or public MCP surface.

Eligibility requires the unique active failed provider leaf of a Run blocked
by bounded-only execution. The hash-bound durable outcome must be TRUNCATED,
with a length finish and no accepted parent result. Malformed JSON under a
normal finish, invalid semantic output, unknown transport outcomes, arbitrary
blocked states, manual upstream blocks and already-registered Semantic work
cannot authorize this action. Partial JSON is never parsed or repaired.

Each reopen candidate is individually proved to have no Attempt, dispatch,
bound raw or result. Its verified failure-event chain must belong to the same
bounded-only stop, with the root Series failure or a later upstream Series
failure. Unrelated per-Segment failure/claim history is rejected. Accepted
successes and actual failed provider leaves are never reopened.

## Atomic frontier and immutable history

One immediate SQLite transaction contains authorization, fenced ownership,
the inherited `BoundedExtractionStore.subdivide_after_truncation` call,
upstream reopening and Run restoration. A transaction-only store wrapper
supplies that connection; it adds no subdivision algorithm or guard bypass.
Both existing engine and pure midpoint planner remain unchanged.

The action appends `TRUNCATION_RECOVERY_AUTHORIZED`,
`TRUNCATED_PARENT_SUBDIVIDED` and `UPSTREAM_FAIL_CLOSED_REOPENED` evidence.
Old failure events, Attempts, outcomes, raw and accepted results are retained.
The parent becomes SUPERSEDED_BY_CHILDREN; two children become PLANNED; proven
upstream leaves become PLANNED without a dispatch. Original parent calls and
12000-token liability are not refunded. The entire pending frontier is checked
against each frozen Series budget before mutation.

Same-key replay returns the same result without extra children or events.
A different key for an already recovered parent fails ALREADY_RECOVERED.
Concurrent workers serialize under the existing transaction/fence authority.
Hard-process crash tests cover authorization, child insertion, parent
supersession, frontier increment, upstream reopening, before Run restoration
and after the committed action. Recovery observes a complete pre-state or a
complete committed state, never a partial frontier.

## Separate bounded execution and compatibility

The operator restores EXTRACTION_PROCESSING at
WHOLE_PIECE_OUTPUT_DECOMPOSITION and returns without dispatch. A later,
separately authorized `resume_bounded_extraction_only` action executes children
and reopened leaves, not the accepted root or superseded parent. Its contract
still prohibits automatic retry and new subdivision, stops at the first new
failure, and may aggregate all-success extraction without registering Semantic.

Stage 7.2C is reused with a distinct explicit truncation-recovery qualification
scope. Default malformed-JSON retry eligibility is not widened. A changed
runtime requires a validated exact-Run/Attempt/context/target-contract token;
the complete new operator source is bound by that contract digest. The
persisted qualification and durable recovery lineage allow subsequent
bounded-only continuation, without granting a generic runtime override.
Real Run14 compatibility is assessed read-only against current installed
stable. No claim that an unactivated release identity has already passed its
future live release gate is made.

## Offline evidence and stage boundary

Synthetic qualification uses the five-Series topology: one accepted root,
one truncated root and 25 unattempted upstream fail-closed roots. The recovered
frontier has 28 active leaves: the original success, two new 8-ref children and
25 reopened roots, with 27 pending leaves. Deterministic fake execution checks
coverage with zero-Claim child outputs, aggregation, no redispatch, full
SourcePiece/scoped-node preservation and the Semantic stop. Ownership annotation
markers may differ; the complete underlying SourcePiece may not.

A disposable private copy of the real state independently proves the same
child IDs and per-leaf provenance. Only its location binding is rebased; no
frozen semantic identity or historical response is rewritten. Real Workbench,
artifact tree, Run14, Run13, Production and Current View are compared before
and after by hashes and invariants. Private copies and raw never enter Git.

Schema remains 12. There is no merge, activation, real recovery or live call
in this stage. The next stage is
RUN14_R2_TRUNCATION_SUBDIVISION_RECOVERY_RELEASE_AND_LIVE_R1, with fresh exact
release identity and real compatibility gates before any actual recovery or
bounded-only provider execution.
