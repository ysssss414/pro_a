# Bounded-only resume operator boundary R1

Qualification only. No activation or live resume is authorized by this document.
Baseline: `1d700d95cc394174120ae55144660c769b4efc51`; Workbench schema12 is unchanged.
The forensic-only Draft PR #106 is not a dependency.

## Explicit operator surface

`SourceOperations.resume_bounded_extraction_only(run_id, *, worker_id,
idempotency_key, max_new_calls, provider=None)` uses
`bounded-only-resume-operator-boundary-v1`.

It consumes only the durable frozen Series/Segment frontier. It does not bind,
create, partition or plan extraction work. Completed results, including an accepted
explicit retry result, are reused. Each step uses the existing bounded runner,
reservation, dispatch, raw persistence, authoritative parser/validators,
reconciliation, accounting and aggregate implementation.

New subdivision and automatic retry are forbidden. Existing frozen child trees
remain executable. A truncated outcome is persisted and stops execution; it never
creates children. Any provider/validation failure stops later dispatches. An
unresolved dispatched Attempt is reconciled before new dispatch, never recalled.
An unknown outcome enters the existing recovery-required semantics.

The action ceiling is the minimum of the requested ceiling and pending work
that actually requires new dispatch. Frozen Series call/output budgets are checked
independently and cannot be raised. Already reserved work is not charged a second
reservation. A zero-call ceiling still permits recovery and aggregate completion.

## Durability and pause point

The existing Run lease/fence serializes operator actions. The authorization event
binds the action key, original call count, ceiling, boundary contract and frozen
frontier identity. A repeated key cannot increase its ceiling. Interrupted actions
continue from immutable ledger evidence; finished duplicate actions do not dispatch.

The existing runner finalizes each Series using its normal authoritative aggregate
and coverage checks. Once all Series are complete, the boundary writes exactly one
`BOUNDED_EXTRACTION_COMPLETE` event and sets the Run stage to that value while
retaining the legal `EXTRACTION_PROCESSING` state. Semantic input registration,
jobs, queue writes, execution and Review creation do not occur in this boundary.
Pre-existing Semantic job registration is rejected before any dispatch/checkpoint,
including a historical full-orchestration crash before its Run-state transition.

Completion is a normal checkpoint, not a fake failure or exception. Repeating the
boundary after completion reports `ALREADY_BOUNDED_COMPLETE` (or returns the cached
completed action) with no planner/provider/Semantic calls. Later explicitly invoking
the existing full orchestration can continue to Semantic registration exactly once.
The full orchestration entrypoint and its default subdivision behavior are unchanged.
There is no environment flag, startup hook, background resumer or auto-retry hook.

## Validation-only root check

The ledger plan validator no longer invokes `initial_extraction_plan`. It checks
persisted root count/order directly; the existing deterministic Segment identity,
range, Evidence, child-tree and terminal coverage checks remain authoritative.
This avoids planning during reads, recovery and aggregation without relaxing the
accepted plan topology. No Wire/provider/research contract version is bumped.

## Cross-release qualification

`assess_bounded_resume_compatibility(config, run_id, persist=False)` reuses Stage7.2C
against the historical malformed Attempt and its unique accepted explicit retry.
Its scope requires exact durable lineage, accepted Attempt2 and no Semantic jobs.
The default malformed-retry qualification scope remains unchanged; this assessment
does not authorize another retry. Future release operators must persist a fresh
exact-target qualification before live cross-release execution.

Semantic-surface normalization accepts only the exact root-validator equivalence
and explicit subdivision-policy plumbing whose ordinary default remains `True`.
Policy/default/validation mutations are rejected. The complete target-only operator
module is included in the target compatibility contract digest.

## Offline gates

The synthetic Run13 topology has five Series, 27 Segments, two already accepted
results (the second has immutable malformed Attempt1 and accepted retry Attempt2),
and 25 pending Segments. Tests install planner, new-subdivision and Semantic
registration tripwires. They cover ordered pending execution, first failure,
truncation, malformed JSON, transport/HTTP, shape/linkage/ownership, accounting,
budgets, existing child trees, serial/concurrent actions, all crash boundaries,
hard process death and fresh-process zero-recall recovery, last-Segment completion,
repeat-after-complete, later full continuation and compatibility drift rejection.

The actual Run13 must remain at three provider calls, two completed Segments and
25 pending Segments throughout qualification. No Production/Current View/Semantic
write, Review action or Run14 creation is permitted.

Next stage, only after qualification: `BOUNDED_ONLY_RESUME_OPERATOR_RELEASE_AND_LIVE_RUN13_R1`.

## Measured qualification evidence

```text
QUALIFICATION_GATES = PASS
BASELINE_STABLE_SHA = 1d700d95cc394174120ae55144660c769b4efc51
IMPLEMENTATION_SHA = 4fdab717355998be569332508f97a904757c05e9
SCHEMA = 12 / UNCHANGED
FOCUSED_TESTS = 45 passed (42 main + 3 capacity gates)
RELATED_TESTS = 663 passed (582 core + 81 MCP)
UNEXPECTED_ACCEPTANCE_FAILURES = 0
COMPILEALL = PASS
PIP_CHECK = PASS
BUILD = PASS / ISOLATED_PEP517
WHEEL_SHA256 = 9aa0c2507f0dbde626cac02f6c22d0e948350a074cfec6e3ab9df35fc8c3ac98
SOURCE_WHEEL_INSTALL_BYTE_EQUALITY = PASS / 143 Python files
NO_GIT_RUNTIME = PASS
RUN13_CROSS_RELEASE_COMPATIBILITY = QUALIFIED / persist=false
CLOUD_EXECUTION_SURFACE = SEMANTIC_SURFACE_EXACT
NATIVE_EXECUTION_SURFACE = SEMANTIC_SURFACE_EXACT
REAL_PROVIDER_CALLS = 0
RUN13_PROVIDER_CALLS = 3 / UNCHANGED
RUN13_COMPLETED_SEGMENTS = 2 / UNCHANGED
RUN13_PENDING_SEGMENTS = 25 / UNCHANGED
WORKBENCH_SHA256 = 8d0eefd10a3da482aac71dc95da941c451bdc3a6caa2277adf9874fc361daf6d
PRODUCTION_SHA256 = 6e5a303ccee9c192c350c2550cc232649e56ffee939b7a09cd6b170cc1c8fba1
PRODUCTION_WRITES = 0
CURRENT_VIEW_WRITES = 0
SEMANTIC_WRITES = 0
REVIEW_ACTIONS = 0
RUN14_CREATED = false
PRIVACY_SCAN = PASS
STABLE_ACTIVATED = false
```

The final PR head may add only this qualification receipt to the implementation;
runtime and test bytes must remain identical to the qualified implementation.
The wheel is a private operator build artifact and is not committed.

All 81 MCP cases have passing evidence from the existing environments: 79 run
with repo Python plus read-only SDK path loading, and two transport cases run
with installed SDK Python plus the existing pytest path. No package installation,
environment cleanup or stable-runtime change was performed. Historical subprocess
fixtures therefore retain their existing pytest-capable interpreter.

Initial long-path fixture failures were rerun in short isolated fixture directories;
no runtime path-handling changes were made. Historical missing-runner surface
classification remains fail-closed as `SEMANTIC_SURFACE_CHANGED`.

The real-state proof compares every Workbench table row hash (including counters),
schema/integrity, original Attempts/outcomes/raw hashes, private artifact manifest,
native checkpoint manifest, Production bytes and Current View manifest. All are
unchanged. The actual historical Run13 assessment and stable-to-implementation
surface comparison both pass. No qualification record was written to real state.

Dependency manifests, provider configuration/prompt/schema, Wire, Evidence Binding,
Claim linkage, ownership/coverage, analyzer, aggregate and Semantic/Review/Production/
Current View research contracts are unchanged. PR #106 remains forensic-only,
open Draft and not merged; it is not a runtime dependency.
