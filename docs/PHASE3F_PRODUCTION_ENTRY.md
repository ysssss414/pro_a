# Foundation Production entry

`production_execution.execute_foundation_payload` is the top-level API for both
`ExecutionTargetMode.SHADOW` (default) and `ExecutionTargetMode.PRODUCTION`.
The existing Phase 3D single-source `execute_authorized_production` API and its
candidate/materialization contract remain unchanged; Foundation must use its
explicit adapter, not a fabricated Phase 3D candidate package.

The immutable payload's builder commit remains its original content binding.
`execution_commit` binds the separately qualified entry implementation. Do not
recompile with another builder commit, reseal the payload, or replace Envelope V2
to record an execution qualification. New qualifications are external receipts.

## Common path

Both modes call exactly:

1. `foundation_production_entry.execute`: actual payload file SHA, caller-supplied
   `PayloadVerificationBasis`, separately supplied completed artifact bytes,
   existing `foundation_payload_envelope` three-way verification;
2. payload qualification receipt and exact predicted-diff byte verification;
3. mode-specific target/authorization selection;
4. `production_execution.validate_supported_mutations`: explicit Foundation
   contracts plus unchanged native payload verification;
5. immutable read-only schema/baseline, replay and full predicted-row verification;
6. schema-derived FK dependency validation of the frozen insert order;
7. exact offline backup, then `production_promotion._apply_verified_payload`;
8. unchanged row dispatcher `_insert_mutation`, FK-enabled transaction,
   locked schema/byte/snapshot revalidation and pre-commit predicted-row check;
9. identical post-state/diff checks, with existing governed recovery on failure.

`apply_payload_to_shadow` retains its unconditional configured-Production path
guard and uses the same `_apply_verified_payload` primitive. No second Foundation
mutation engine is maintained. The primitive is internal, not an authorization
API: use one of the guarded public entries, never call it to bypass target checks.

## Five-table extension

The Foundation branch adds only `node_relations`, `relation_temporal_semantics`,
`relation_evidence_authorizations`, `relation_evidence_links`, and `current_views`
to the existing four-table set. `FOUNDATION_COLUMNS` and `FOUNDATION_KEYS` declare
exact per-table columns and allowed keys. Only INSERT is supported, exact native
compiled rows are required, and duplicate mutation keys are rejected. Foundation
current_views mutations must be historical baseline records, not official views.

The schema fingerprint and existing schema-0.2.3 guards remain mandatory. PK,
UNIQUE, FK and immutable-row triggers remain enabled. No migrations or semantic
projections run in the executor. `validate_insert_dependencies` checks each
non-null FK against an existing parent or exactly one earlier inserted parent;
missing parents, cycles or out-of-order dependencies fail. It never sorts or
rewrites the immutable mutation objects. Replay/diff/rollback cover all tables.

## External authority and receipts

A `QualificationReference` supplies actual receipt bytes/path plus independently
trusted ID, semantic SHA and file SHA. Receipt semantic hashing removes only the
receipt's ID and semantic-SHA fields; canonical JSON uses sorted keys,
ensure_ascii=False and compact comma/colon separators. Qualification gates,
payload/core/completed/envelope/baseline and predicted-diff bindings are checked.

PRODUCTION additionally requires a `ProductionAuthorization` supplied by the
trusted HUMAN-authority caller and a new Production Entry Qualification Receipt.
Its scope is EXACT_PAYLOAD_ONE_TIME, with exact payload, both receipt identities,
completed artifact identity, pre-apply DB SHA/schema, old builder commit, current
entry commit and Envelope V2 SHA. `execution_bindings` is a comparison projection,
not an authorization factory. A payload or self-hashed receipt alone never grants
Production permission. The embedding application must populate this context only
from explicit human authorization; a boolean or mode switch is insufficient.

The configured and authorized resolved Production paths must be identical.
SHADOW rejects that path and same-file hardlink/symlink aliases. All envelope and
authorization failures precede writable DB open. The current adapter-fix stage
provides neither actual Production permission nor a substitute entry receipt;
tests use public temporary databases and synthetic external authorization only.

## One-time execution and recovery

Production uses `foundation-executions/<authorization_id>/execution_journal.json`
beside its configured DB, with a validated authorization ID and exact pre-apply
backup. Any existing execution directory blocks reuse before writable open,
including a failed/incomplete attempt. Completion/failure is recorded separately
from immutable qualification receipts. Shadow permits the established
ALREADY_APPLIED no-op after checking the entire predicted post-state.

On a transaction error, SQLite rollback is verified against the original backup
identity. On a known committed post-check failure, the existing
`production_execution._restore_after_failure` helper restores the verified exact
backup only if the target still matches the observed executor post-commit hash.
Unknown external drift fails closed rather than overwriting an unrecognized DB.
No retry occurs. Foundation has no new Source archive materialization; existing
immutable Source paths remain as compiled. Backup and journal artifacts are
retained. Production failure injection is forbidden; shadow injection is for
qualification only.
