# Bounded extraction durable persistence R1

Required and verified baseline: `27fd74d31bdf48f6684a71904b10de5d391820c3`.
Branch: `codex/pro-a-bounded-extraction-durable-persistence-r1`.
The accompanying JSON receipt records the qualification results and implementation commit.

`MULTI_SEGMENT_SERIES_RECOMMENDED = true`. One immutable SourcePiece owns one
logical ExtractionSeries. Ordered evidence ranges belong to system-created
Segments; provider attempts belong to those Segments. Input partitioning remains
independent of output capacity. No model continuation cursor is used.

## Scope and activation boundary

This adds an explicitly invoked Workbench migration and a dormant Python ledger.
SOURCE_ANALYSIS_PIECE remains schema v1, adapter v2, on its existing verbose
canonical provider path. SourceOperations, native replay and provider dispatch do
not import or instantiate the new ledger. Existing operation ceilings remain
12000 for extraction and 8192 for semantic decomposition. Global SourcePiece
policy and MAX_STAGE1_JOBS_PER_RUN=31 remain unchanged.

The real Workbench stays schema 11. No real migration, provider request, Run 8,
Production write, Apply, stable installation or activation is part of this stage.
Historical Runs 1–7 receive no backfill and retain attempt counts 0/2/1/1/1/1/1.

## Explicit v11 → v12 migration

Call `prepare_bounded_extraction_persistence(config)` only in an offline,
drained activation procedure. Importing the package does not migrate anything.
The function checks Workbench/Production/artifact isolation, rejects WAL, SHM and
journal sidecars, and uses the existing terminal Processing Run policy. QUEUED or
RUNNING cloud jobs, nonterminal runs, or active bounded Series/Segments block it.
Partially prepared v11 schemas fail closed rather than receiving repair/backfill.

Under a SQLite EXCLUSIVE transaction, the exact original database bytes are
published once as `.stage-bounded-extraction-v12-backup`, flushed, fsynced and
hash-verified before DDL. A differing existing backup is a conflict. All new
tables, constraints, triggers and the version update are one transaction.
Foreign-key and integrity checks run before commit. A failure after the identity
tables rolls back all DDL and leaves v11 logically unchanged with the exact
backup retained. Old table contents change only at workbench_meta.schema_version.

An immutable, sanitized `.stage-bounded-extraction-v12-migration.json` receipt
binds the backup hash and version transition. Receipt publication also holds the
writer lock. A drained second invocation returns ALREADY_PREPARED without changing
database bytes; it can finish publishing a receipt after a migration commit.
No Production database connection is opened for writing.

## Tables and identities

| Table | Authority |
| --- | --- |
| bounded_extraction_series | Frozen Foundation series identity, input hashes, budget, frontier, coordinator lease/fence and cumulative reservations |
| bounded_extraction_segments | Frozen ranges, refs, lineage, stable paths, hashes and per-call ceiling; operational lease/fence/state |
| bounded_extraction_attempts | Segment-specific attempt number and immutable request/configuration/budget identity |
| bounded_extraction_dispatches | One immutable marker granting at most one dispatch permission per attempt |
| bounded_extraction_outcomes | One immutable transport outcome and private raw artifact binding per attempt |
| bounded_extraction_segment_results | One accepted COMPLETE or SUBDIVISION_REQUIRED result per Segment |
| bounded_extraction_series_results | One immutable coverage/ordered-result/aggregate/final identity per Series |
| bounded_extraction_events | Series-scoped, sequential hash chain with content-free lifecycle data |

Series and Segment semantic columns come directly from their frozen Foundation
dataclasses. Budget and ref tuples use canonical JSON in SQL; no Source text is
stored. Global Source SHA, Piece ID/SHA, prompt SHA and universe SHA bind the input.
The eight new tables do not reuse cloud_attempts, cloud_attempt_dispatches,
cloud_attempt_outcomes, cloud_job_results or source_processing_jobs meanings.
Processing Run identity is frozen but deliberately not coupled to a live parent
job foreign key until the binding stage.

Series/Segment identity UPDATE and DELETE triggers forbid semantic mutation.
Attempts, dispatches, outcomes, accepted results, final results and events reject
all UPDATE/DELETE. A result insert trigger requires its attempt to belong to the
same Segment. Primary/unique constraints enforce one attempt number per Segment,
one outcome per attempt, one accepted result per Segment and one final result per
Series. Reads reconstruct Foundation identity/lineage and verify record hashes,
artifact hashes, the event chain, reservations and final coverage bindings.
Corruption is rejected without rewriting or normalizing stored data.

## State, ownership and attempts

Series states: OPEN, SUCCEEDED_COMPLETE, FAILED, RECOVERY_REQUIRED.
Segment states: PLANNED, RUNNING, SUCCEEDED_COMPLETE, SUBDIVISION_REQUIRED,
SUPERSEDED_BY_CHILDREN, FAILED, RECOVERY_REQUIRED.

Claiming PLANNED moves it to RUNNING. Every claim/reclaim increments the persisted
fence and sets a lease. An unexpired lease cannot be claimed again. Reservation,
dispatch, outcome recording, acceptance, closure and subdivision all check the
current owner, fence and lease inside BEGIN IMMEDIATE. Finalization checks the
Series coordinator lease/fence. Process-local locks have no authority.

`reserve_attempt` takes an explicit attempt number. Repeating a reservation with
the same number and frozen request identity returns that attempt. A new retry
requires the preceding outcome to be known and the Segment to have failed
validation/transport acceptance. Its request, configuration, assigned evidence
and semantic inputs cannot change. REPROCESS requires a new Processing Run;
SUBDIVISION creates new deterministic Segments under the same Series.

`record_dispatch` returns true exactly once. **Only that true return grants a
future caller permission to call a provider.** False is an idempotent observation,
never permission to send again. This module contains no network executor.

No marker means the reserved attempt has not been dispatched by this API. A
marker without a durable outcome/artifact is externally unknown; reconciliation
marks Segment and Series RECOVERY_REQUIRED, preserves liability and returns
UNKNOWN_EXTERNAL_OUTCOME. Automatic retries are forbidden. This stage provides
no operator override for unknown outcomes. A known outcome pending validation
does not authorize a replacement call either.

## Private raw outcome contract

Artifacts live below the configured private artifact root at
`bounded-extraction/<series-id>/<attempt-id>.raw.json`. Generated identifiers and
single-component names are validated; checked_path rejects traversal, links and
reparse points. Existing identical bytes are reusable; differing bytes produce
ARTIFACT_CONFLICT. Cooperating writers hold the Workbench writer transaction while
publishing. A temporary file is exclusively created, flushed and fsynced before
publication; final bytes are hash-verified. POSIX also fsyncs the directory.

The private `bounded-private-raw-v1` envelope contains exact body bytes encoded
as base64, body/envelope hashes, attempt/request identity, HTTP status, an optional
safe provider request ID, finish reason and usage fields. These are the complete
transport metadata allowlist; arbitrary headers, errors and authentication values
are not accepted. No raw body is placed in SQL, public events, MCP or Review.

Required ordering is implemented as: envelope publication → flush/fsync → hash
verification → outcome DB commit → body parse/coverage validation. A raw artifact
without a DB row is read from its deterministic path, its envelope/body/request
identities verified, and the same outcome registered. No provider call occurs.

The synthetic body protocol is exactly `{wire, dispositions}`. It exercises the
existing Wire v3 plus the Foundation disposition contract; it is not a new live
prompt or provider adapter. Every assigned ref must have exactly one disposition
consistent with the Claims. Malformed JSON, invalid Wire or missing coverage
fails safely after raw durability. A length finish always rejects acceptance,
even if the body parses. No partial Claims are salvaged. Only a valid Foundation
result with explicit SUBDIVISION_REQUIRED dispositions permits subdivision.
Outcome classification records transport status; validation failure is a separate
safe lifecycle event and Segment state.

## Subdivision, budget and coverage

Subdivision checks the active leaf, accepted SUBDIVISION_REQUIRED result,
Segment fence and expected Series frontier version. The pure Foundation midpoint
operation supplies both child IDs/ranges. Both children, parent supersession,
frontier increment and events commit together. A repeated request observes the
same pair without another increment. Stale expected versions cannot change the
frontier. SourcePiece identity, global chunk policy and the 12000 ceiling never
change.

The default Series budget is 32 calls and 384000 cumulative output tokens.
For every reserved attempt a, define L(a) = known valid output tokens, otherwise
12000. The invariant is:

`provider_call_reservations = count(all attempts)`

`output_liability = sum(L(a) for all attempts)`

A reservation atomically checks count+1 and liability+12000 against the frozen
Series budget before inserting the attempt. Outcomes replace only their own
12000 liability with known actual output. Cached input is a subset of input and
is not added again to totals. Unknown external outcomes or invalid usage retain
12000. Retries and superseded parents remain in the ledger; children share the
same envelope. Budget exhaustion stops before a new reservation/dispatch.

Finalization requires all active leaves to be SUCCEEDED_COMPLETE with accepted
COMPLETE results, no unresolved reserved/dispatched attempt, no unknown external
outcome, an OPEN Series, current coordinator ownership and matching frontier.
Foundation aggregation independently revalidates complete coverage with zero
missing/duplicate refs. The immutable private aggregate contains the Wire,
coverage inputs and ordered leaf result hashes. The final row binds coverage SHA,
Foundation aggregate Wire identity, artifact path/hash and final result SHA.
There is no canonical persistence or active replay integration in this stage.

## Qualification and compatibility

Crash tests reconstruct a fresh ledger after every injected failure:

| Window | Recovery evidence |
| --- | --- |
| A: attempt committed, no dispatch | Same reserved attempt; no increment |
| B: marker, no raw/outcome | RECOVERY_REQUIRED; no redispatch; 12000 retained |
| C: raw durable, no outcome row | Exact artifact reconciled without recall |
| D: outcome committed, no accepted result | Parse/validate that durable body |
| E: accepted result, state not advanced | Idempotent closure, one result |
| F: first child insert / supersession / after commit | Old frontier or parent plus both children; no single-child visibility |
| G: aggregate durable, no final row | Reuse identical aggregate; one final result |

Window C additionally runs in a subprocess terminated with `os._exit(73)`, without
Python cleanup handlers. This qualifies abrupt process termination, not machine
power loss, external filesystem mutation or a platform-specific directory flush
guarantee on Windows. Incomplete unpublished temporary files have no ledger
authority. Two fresh SQLite clients race claim, reserve, dispatch, acceptance,
subdivision and finalization. Losers either receive a safe conflict or observe
the unique existing result. Stale Segment and Series fences are rejected.

Schema acceptance was audited across Store, every prepare function, artifacts,
attribution, Review, research, domains, SourceOperations, cloud runtime identity,
Stage1 capacity/projections, lifecycle closure, extraction retry, retry
compatibility and MCP review context. V12 retains v11 lifecycle filtering; it
does not fall back to pre-lifecycle behavior. Older migration source-version and
rollback gates stay narrow because those operations are not valid v12 downgrades.
The synthetic v12 E2E executes the existing fake-provider SourceOperations/cloud
path, creates a Review packet, reads it through MCP, checks capacity, and proves
all bounded tables remain empty. V11 behavior is also exercised.

Stage 7.2C against the exact baseline: cloud is incompatible with
SEMANTIC_SURFACE_CHANGED; native is compatible with SEMANTIC_SURFACE_EXACT.
No compatibility exception was added. The older Wire foundation and capacity R2
tests' cloud equality assertions now assert this explicit fail-closed boundary.
Native equality alone does not authorize historical cloud retries.

The receipt gives exact focused/regression test counts, build results, privacy
scan and real-state comparisons. This is a selected regression matrix, not a
claim that the entire repository suite ran. External provider networking is
blocked during qualification; loopback is permitted for Windows asyncio and
local protocol tests. All supplied provider bytes are synthetic.

Qualification: 59 new focused cases passed. Of 689 selected regression cases,
686 passed initially; the two superseded cloud-equality assertions and one
CRLF-converted byte-frozen fixture check passed targeted rechecks after correction.
The fixture was restored to its exact baseline Git blob without a content diff.
No unresolved failure or skipped case remains in this selected matrix. Compileall,
pip check, isolated PEP517 build, and source/wheel/isolated-install equality for
all 134 packaged Python files passed. All 26 proposed public files passed the
real Source excerpt/filename, credential and private-path privacy scans.

`REAL_WORKBENCH_V12_MIGRATION_REQUIRED_BEFORE_LIVE_BINDING = true`

`NEXT_STAGE = SOURCE_ANALYSIS_COMPACT_WIRE_SERIES_BINDING_R1`

Delivery is a Draft PR only. No merge, real migration or activation is authorized
by this stage.
