# Phase 4.2 Stage 1: persistent native human review

Stage 1 builds on the accepted Stage 0 application boundary. Decisions belong to
the isolated Workbench database. Knowledge, registered blank packets and execution
inventories remain read-only. Completion and sealing create no qualification,
promotion package or Production authority.

## Operator preparation

Use the Stage 0 configuration, initialization and registration procedure. For a
fresh synthetic example, run `python tests/workbench_fixture.py workspace/stage1-demo
--node-profile create` on one line, then initialize and register the generated
packet as described in `PHASE4_STAGE42_STAGE0_WORKBENCH.md`. Stop the application
and other Workbench writers before the explicit migration:

```powershell
python -m pro_a.workbench --config workspace/stage1-demo/workbench.toml prepare-review
python -m pro_a.workbench --config workspace/stage1-demo/workbench.toml serve
```

`prepare-review` creates a flushed, exclusive `.stage0-backup` sibling before
transactionally upgrading Workbench schema 1 to 2. Registry bindings are retained.
An incompatible existing backup blocks migration. Repeating a successful migration
returns `ALREADY_PREPARED`. Startup does not migrate either database. Schema 1 still
supports the Stage 0 read view; review mutations require explicit preparation.
The service account now needs write access to the Workbench database and its
SQLite journal directory, while knowledge and execution files need only read access.
Stage 0 private/demo, origin, cookie, CSRF and registered-handle boundaries continue
to apply. Sessions expire on application restart; sign in again to restore the review.

## Human workflow

Open `/?surface=review`, enter a reviewer name, inspect evidence and choose an
explicit native decision and reason. The first successful save binds that reviewer
to the review. Native suggestions are displayed but never selected automatically.
Claim KEEP/DROP/KEEP_NEEDS_REVIEW, Node CREATE/REUSE/DEFER/REJECT and Parent Placement
CREATE/DEFER/REJECT are enabled only when the existing native validator accepts the
action. REUSE requires the exact unique native target. Aliases remain immutable
Node identity; excluded functional relations have no decision controls.

Queues and counts are projections of the frozen packet and saved overlay, never
another persisted truth. Required/native review rows exclude the separately counted
audit-only relation inventory. Completed means a valid explicit human decision,
including deferred/nonpromotable decisions. Ctrl+Enter saves the displayed decision.
Use Next item or select a queue; inspect saved reasons and append-only audit history.

Every mutation carries the packet basis, expected packet-wide revision and operation
ID. A stale tab receives `REVISION_CONFLICT`; attempted input remains visible beside
the refreshed authoritative state until explicit retry. Identical replay returns the
original response without another audit event. A different request with the same ID
fails. Keep an uncertain operation's identity when retrying a network or server error.
Packet-wide revisions intentionally also conflict when tabs edit different items.

Undo applies once to an item's most recent Save and records a new event. It restores
that Save's previous state without deleting history. Losing child Node CREATE clears
dependent Parent CREATE in the same transaction and appends DEPENDENCY_INVALIDATED.
The parent returns to Needs Review; restoring the child does not silently restore a
parent decision. Sealed reviews cannot be undone or reopened.

## Completion, sealing and storage recovery

Validate completion uses the unchanged native completion validator over a separate
copy containing only explicit saved human inputs. Partial decision checks reuse its
native human-input rules; they never substitute for full row/accounting validation.
After validation, inspect the packet, revision, counts, warnings and nonpromotable
rows, enter a seal reason and explicitly confirm review-only sealing.

The completed JSON packet and native completion receipt are immutable BLOB objects
in `sealed_review_artifacts`, each identified by kind and SHA-256. They are outside
the execution inventory and separate from the original packet. Both objects, the
seal event, operation result and SEALED status commit in one SQLite transaction
with synchronous FULL. There is no second filesystem publication step and no HTTP
raw-packet export. The sealed read response contains object IDs/hashes and the safe
native validation receipt. KEEP_NEEDS_REVIEW remains deferred/nonpromotable.

Append-only database triggers protect audit, operation receipts and sealed objects;
sealed state and decisions cannot be updated. Reads replay the audit and compare it
with current state, operation identities and revision. Sealed objects are rehashed
and checked against native validation. Detected inconsistency yields RECOVERY_REQUIRED;
the application does not invent repairs. SQLite rolls back an interrupted transaction
on restart using only the isolated Workbench writable handle. Preserve the database
and its journal together during recovery; ordinary durable-storage guarantees depend
on the host filesystem honoring SQLite's flushes. Do not copy an active DB alone.

No Stage 2 artifact is produced. A future attribution/qualification handoff requires
separate authorization. This stage supports one trusted operator, not a multi-user
authorization service, and does not defend against privileged host database editing.

## API and checks

`GET /api/workbench/v1/reviews/{registered_handle}` returns native detail plus queues,
capabilities, progress, revision and audit. POST suffixes `/decisions`, `/undo`,
`/validate`, `/seal` require the existing authenticated origin/CSRF boundary.
`GET .../sealed` returns the immutable result projection. Stage 0 review-packet GETs
and Explorer GETs retain their contracts. No endpoint accepts filesystem paths.

Regression coverage lives in `tests/test_workbench_stage1.py`, the retained Stage 0
tests, and `frontend/src/PersistentReview.test.tsx`. Process-crash cases use a separate
synthetic-only worker. Acceptance receipts, browser captures and exported synthetic
objects belong in ignored workspace evidence, never the public candidate tree.
