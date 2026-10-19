# Candidate revision lifecycle v1

This contract adds review/execution eligibility to accepted v7 candidate Origins.
It does not change Provider v7, Evidence Binding v2, source-support judgments or
Canonical permissions. The immutable Origin projection retains its original v1
entry descriptor. New review Runs use `accepted-v7-review-entry-v2` and freeze
`candidate-revision-lifecycle-v1` selections in their native candidate input.

## Objects and decisions

A logical object is scoped to Source ID/SHA, original Run/Attempt, Raw SHA and
parent observation ID. A child additionally includes its exact child ID. Raw
parents and children have different logical keys. Text similarity, timestamps,
and a child ID from a different parent are never identity. Each child depends on
its immutable Raw parent revision; invalidating that parent invalidates dependent
children, without invalidating unrelated parents.

`CandidateInputs.publish` registers available immutable proposals. Publication
does not select a version, revoke another version, or approve evidence. An
explicit initial SELECT is required before a version can enter a new review Run.
SELECT, REPLACE and REVOKE require a confirmed HUMAN_USER identity with actor and
session, a reason, an idempotency key and the exact expected lifecycle head hash.
Internal callers use the same trusted-identity convention as P1/P2; identity is
not accepted from Provider records or model advice. There is no model/MCP write
endpoint for lifecycle decisions.

| Operation | Preconditions | Effect |
|---|---|---|
| SELECT | No current revision; registered, never-invalidated target | Target ACTIVE |
| REPLACE | Expected current ACTIVE revision; registered replacement of same logical object | Old SUPERSEDED, replacement ACTIVE |
| REVOKE | Registered nonterminal target; expected current head | Target REVOKED; clear current if it was target |

SUPPORTED/UNCERTAIN and SEMANTIC_REVIEW_REQUIRED/DEFER remain support/review
states, separately represented from lifecycle state. Selecting an UNCERTAIN
proposal does not make it semantically reviewable or promotable. SUPERSEDED and
REVOKED versions are terminal. Reverting text requires a genuinely new explicit
revision identity and fresh review, never restoration of an old authorization.

Decisions are append-only Source processing events under the original accepted
Run. They record contract, operation, actor/session, reason, exact old/new refs,
expected head, resulting head and request identity. A repeated key with the exact
request returns its original decision; a different request conflicts. Replays do
not apply transitions again; their returned result describes that historical
decision, and is not a new activation or a current-state assertion. Stale expectations, cross-object replacements,
unregistered versions, unauthorized callers and terminal-state transitions fail.

## Frozen authority and concurrency

The selected revision and its activation event are frozen into each new review
Run/native input. Parallel publication leaves these bindings unchanged. Review,
advice submission, Human decisions/seals, P2 planning/approval and independent
Operator execution require every bound revision and its parent dependencies to
remain selected and ACTIVE. A changed selection cannot reuse old authority. A
packet containing any invalidated bound object fails as a whole. Independent
objects require a new explicit packet/plan and applicable approvals to proceed.

Lifecycle decisions and execution use the same SQLite state database reservation:
`BEGIN IMMEDIATE`. The Operator acquires this reservation before acquiring its
Canonical/Grant transaction, rechecks frozen selections, and holds the reservation
through the atomic Canonical and Grant commit. A decision that commits first
blocks old execution. An execution that acquires the reservation first may commit;
the decision can succeed only afterwards. No replacement may commit between
validation and Canonical commit. The lock is database-backed and cross-process;
no UI flag, process cache or early-only validation establishes eligibility.

Review write transactions likewise recheck selections while holding their state
reservation. Inference may finish after invalidation, but stale advice cannot be
registered as executable authority. Rejection does not consume a READY Grant or
insert Canonical objects. Handoff records a distinct BLOCKED result when needed.

## Compatibility and history

Historic data and evidence are immutable. Candidate reads, Advice/Seal/Plan
inspection, registered receipts and executed-history verification remain readable
after invalidation. A completed execution is not rolled back or rewritten, and
its exact replay remains zero-increment history. No deletion/correction authority
is created. v4 eligibility is unchanged. Legacy v2 packets lacking a frozen
lifecycle selection cannot establish new execution eligibility; they remain
readable and require a newly selected review Run and fresh applicable approvals.
The original v7 extraction-only stop remains unchanged.
