# RUN15 strict same-run recovery operator qualification

Stage: `RUN15_STRICT_SAME_RUN_RECOVERY_OPERATOR_QUALIFICATION_R1`.
Baseline main and stable runtime: `d7cf753d59a528f458bcb38d8b0386cb7df10198`.
Workbench schema remains 12. This stage ends with an open Draft PR; release,
activation and live recovery require the separate next stage.

## Recovery boundary

`SourceOperations.authorize_strict_same_run_recovery` implements
`bounded-strict-same-run-output-recovery-v1`. It accepts an exact Run, failed
Attempt, idempotency key, worker and operator reason. Authorization makes zero
provider calls and creates at most one new Attempt, numbered 2. It never plans
new Series, subdivides, starts Semantic, or admits an old failed record.

Eligibility requires a BLOCKED / BOUNDED_ONLY_RESUME /
BOUNDED_EXTRACTION_FAILED Run, output Series v2, 24k leaves, the frozen 384k
Series liability limit and 16 initial refs. There must be exactly one accepted
Segment and one actually attempted failed Segment; no downstream Semantic work
may exist. Attempt 1 must have a durable successful external outcome, HTTP 200,
tool_calls finish and fewer than 24k output tokens. Its original record must
reproduce NONDEFAULT_INACTIVE_VARIANT together with invalid same-response
candidate references. Evidence bindings, ownership, lexical primitives, local
Node/Claim references and the original failure event chain are checked separately.

Truncation, unknown outcomes, transport failures, other invalid-response
families, accepted targets, second Attempts, Semantic registration, frozen
configuration drift and historical record/Series formats fail closed.
The default Output Series `reserve_attempt` restriction to Attempt 1 remains.
Malformed-JSON retry authorization is separate and retains its original request
identity and eligibility rules.

## Independent request identity

Attempt 1, its request, original prompt and raw envelope are immutable.
Attempt 2 has a separate prompt artifact and deterministic request identity under
`strict-provider-lexical-regeneration-v1`.

The new payload retains every original message and its complete SourcePiece and
Evidence context. It adds a fixed user instruction containing format rules,
error classes and a safe field path. It freezes the regeneration version, new
request SHA, new prompt SHA, original request SHA and frozen context SHA.
It carries no failed response or provider-generated correction text.

The instruction requires exact inactive defaults, existing preserved_fields
rules, references to candidates in this response, no cross-Segment candidates,
selective materiality and no fabricated Claims or Evidence. The provider must
independently regenerate a complete response. The local code never clears
inactive slots, drops invalid references, moves fields, creates candidates or
submits a transformed failed record.

The existing ProviderRecord validator, normalized record, Wire, Evidence
binding, Claim identity, extraction objective and local acceptance remain
byte-identical to the baseline. A newly generated invalid record still fails
those validators.

## Transaction, frontier and budget

Authorization uses the existing ledger and an IMMEDIATE transaction. Source
and bounded authorization events bind the original failure, accepted result,
new request, frozen context and each proven unattempted leaf. The transaction
reserves Attempt 2, charges one call and 24k liability, advances fences, reopens
the target and only proven upstream fail-closed unattempted leaves, and restores
the bounded extraction Run state. Accepted Segment rows remain untouched.

The failed call is never refunded. Assessment also proves that the frozen
remaining frontier fits each original Series budget. Insufficient capacity
returns `STOP_STRICT_RECOVERY_BUDGET_INSUFFICIENT`; no ceiling is raised.

Identical authorization keys return the same Attempt. Conflicting keys/reasons
and additional authorizations are rejected. Concurrent workers serialize on the
transaction. Crashes after authorization, reservation and frontier reopening
roll back SQL; a deterministic orphan prompt can be reused only with identical
bytes. A crash after commit returns the durable authorization on recovery.

Bounded-only continuation consumes the exact durable grant, verifies its
separate prompt and request, skips the accepted Segment and Attempt 1, and uses
the existing dispatch/outcome ledger to prevent recalling Attempt 2. Unknown
outcomes require recovery. The first new invalid response stops continuation;
there is no automatic third Attempt or subdivision. Full success produces the
existing Series aggregates and stops before Semantic.

## Historical release compatibility

`assess_strict_recovery_compatibility` is an independent opt-in scope of the
released compatibility mechanism. Qualification binds this exact Run, failed
Attempt, raw SHA, context, provider configuration, new request/prompt identities
and target recovery contract. Its durable token is required on runtime drift.

Installed targets read immutable historical Git blobs through the explicit
historical repository argument. They do not import the historical checkout.
Cloud and native research surfaces must compare as equivalent. Only the exact
new dispatch/identity plumbing and the strict module's runtime inventory entry
are normalized for the cloud comparison; their full bytes are bound in the
target compatibility contract. Modified provider, acceptance, budget or research
code remains a changed surface. Missing or ambiguous history fails closed.
The persisted token can be consumed without Git after qualification.

## Offline evidence

The real Workbench supplies the failed Attempt and never-called count read-only.
The observed topology is five frozen Series and 27 leaves: one accepted, one
failed and 25 never called. The count is derived from Attempts, rather than
assumed by the recovery operator or qualification harness.

The original failed body still rejects at
`node_candidates[0].cross_source_or_node_value`. Its 32 violations comprise
22 NONDEFAULT_INACTIVE_VARIANT, two ACTIVE_FIELD_IN_PRESERVED_SLOT and eight
UNKNOWN_LOCAL_CANDIDATE findings. The diagnostic does not repair the body.

Private disposable-copy qualification preserves every original Attempt,
dispatch, outcome, accepted result and artifact. Exact historical compatibility
is persisted only in the copy. Authorization makes zero calls; 26 subsequent
fake calls cover the one new Attempt and derived unattempted frontier. Legitimate
empty selective responses pass the unchanged validators; all five Series
aggregate with no Semantic or Production change. Fake results are not evidence
that a real provider will produce a compliant response.

Focused tests cover complete continuation, invalid new variants/references,
excluded failure families, accepted targets, unproven frontier, idempotency,
concurrent workers, budget exhaustion, source/context drift, four fresh-process
crash windows, cross-release exact scope, prompt tampering, unknown Attempt 2
and absence of public HTTP/frontend/MCP authorization exposure. Related targeted
regressions cover the existing ledger, malformed retry, output acceptance and
capacity, bounded-only continuation, historical surface validation and
truncation recovery.

The exact final Git tree is built as a noneditable wheel. Git, wheel and isolated
installed Python/SQL bytes are compared; installed smoke denies source-checkout
access and separately exercises no-Git runtime identity. Public changes and
wheel contents are scanned for private source/raw/prompt fragments, credentials
and local runtime paths. Durable local receipts record actual test counts,
wheel/commit identities and unchanged real-state snapshots.

One known baseline assertion is reported separately:
`test_operation_output_budget.py::test_baseline_cloud_execution_surface_fails_closed`.
It expects SEMANTIC_SURFACE_CHANGED where historical missing execution code
currently produces EXECUTION_SURFACE_UNAVAILABLE:RetryCompatibilityError.
Both outcomes reject compatibility; this pre-existing assertion is not counted
as a newly passing test or used to hide unexpected failures.

## Blind identical-prompt retry risk

`BLIND_IDENTICAL_PROMPT_RETRY_RISK = PERSISTENT_ENCODING_FAILURE_POSSIBLE`.
The original syntax is valid, so its 32 contract violations may recur when the
same prompt is repeated. The versioned format-only instruction addresses those
rules explicitly, without changing materiality or Evidence criteria. Offline
fake acceptance supplies no real success-rate estimate. A second real failure
must stop; no third Attempt is authorized.

Real provider calls remain zero in this stage. Run15/14/13 retain their original
2/3/4 calls and real state, Production, Current View and stable runtime remain
unchanged. PR #106 remains open, Draft and unmerged.

Next stage: `RUN15_STRICT_SAME_RUN_RECOVERY_RELEASE_AND_LIVE_R1`.
