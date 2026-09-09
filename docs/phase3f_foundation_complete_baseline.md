# Phase 3F complete foundation review contract

The foundation is Sources + Claims + global Nodes + independent Aliases +
Relations + frozen Baseline Views. None is an implicit Current View candidate.
This contract does not extract Sources, call a model, decide real reviews, or
authorize Production writes.

## Authority and accounting

`phase3f_foundation_baseline_review_packet`, schema 1, binds the immutable
archive identity, normalized inventory identity, qualification receipt,
materialization registry, Git/Production identities, all candidate content,
and an exact candidate manifest. Its package-derived ID is not an INGEST run.
The immutable packet hash excludes only explicitly enumerated human fields.
Completed review must be checked against the separately retained blank packet.
Rehashing changed candidates is not an authorized review operation.

Every Claim retains its original Source ID. Source identity is byte SHA256,
not the filename. The Source files, archive, and qualification receipt are
rehashed before handoff and by Phase 3D validation, including replay validation.
The registry is not a substitute for the actual local files.

All five candidate classes receive one disposition. KEEP_NEEDS_REVIEW, DROP,
DEFER and REJECT are explicit non-executable outcomes, not missing objects.
Executable choices with unresolved dependencies fail closed; the compiler does
not silently replace them with DEFER. A global Node is represented once across
all Sources. Node support refers to exact candidate Claim IDs. Alias ATTACH is
an independent human decision bound to the final CREATE/REUSE identity.

Claim-only batches use the established immutable candidate-ID list and
candidate-content-binding hash pattern, grouped per exact Source and capped at
20. Expansion verifies the packet identity, both batch hashes, reviewer, decision,
reason, and non-overlap with individual decisions. Exceptions are never batched.
The pre-existing Stage 2 batch implementation is local/untracked; this public
module does not import that file or require it to be committed.

## Shared handoff and Relation safety

`build_handoff_core` dispatches by immutable review document type. Existing
Stage 1/2 paths remain unchanged; the foundation path accepts 1..N Sources.
The output remains `phase3d_promotion_payload`, payload version `1`, with an
explicit `phase3f_complete_foundation_v1` adapter profile. It is not a second
promotion engine. `apply_payload_to_shadow` still owns schema and byte-baseline
checks, the INSERT-only transaction, full semantic diff, replay, and rollback.

The new profile validates by deterministic recompilation: intended mutations,
all operation arrays and the complete disposition mapping must equal the
review-derived projection. Its referenced Production snapshot is compared with
the execution connection. Unrelated mutation tables and forged official views
cannot be added by recomputing the payload hash. Legacy adapters retain their
existing allowlist and part_of-only boundary.

Relation identity is `(from_node_id, relation_type, to_node_id, scope)` across
all existing statuses. REUSE requires the exact frozen existing row and exact
human-selected relation ID. Canonical RELATION_TYPES are not extended.
Scope, explicit validity bounds, confidence, status and evidence are preserved.
part_of gets its established cycle and transitive-redundancy checks; other
types do not inherit those checks. General self-loops and invalid confidence
are rejected under existing relation contracts. Each active Evidence link
requires an executable Claim in an existing active-evidence status and an
explicit supports/contradicts role. No role is guessed from co-occurrence.

Package-specific categorical temporal labels are not automatically `current`.
Without an accepted lossless runtime projection, that exact Relation remains
reviewable but CREATE/REUSE is blocked. Evidence-ID joins may be displayed as
review context; they do not invent explicit Claim-to-Relation evidence roles.
These are candidate-specific execution gaps, not removal of Relation review.

## Current View read/write census

This census covers repository `current_views` references, including direct SQL
and callers of the official-view APIs. Arbitrary diagnostic SQL is not an
official-view API.

| Path | Boundary / treatment |
| --- | --- |
| `current_view.create_official_view_record` | Previous view already official-only; revision MAX now official-only. INSERT stays official and human-governed. |
| `db.current_view`, `db.versions` | Official selector preserved; versions enumeration now official-only. |
| `db._migrate_0_1_to_0_1_1` | Legacy revision backfill skips baseline rows, preserving frozen metadata. |
| `query.node_current_view`, history | Both explicitly select official rows. |
| `query.node_current_view_compare` / `compare_current_views` | ID lookup followed by mandatory official-only comparator validation. |
| `query` node/source impact projections | Latest-view CTE explicitly filters official. |
| `proposals` previous-view selection | Already official-only. |
| `proposals._view_for_side_effect` | Now requires official before file writing or external sync. |
| `human_review_intake` | Latest view explicitly official-only. |
| `human_proposal_resolution` | Accepted result must resolve an official view; narrow write authorizer preserved. |
| `view_proposal_review` | Exact ID/node/version lookup requires official status. |
| `propagation` | Latest version explicitly official-only. |
| `coverage` | Official coverage already filtered; official Claim-reference census now filtered. Physical orphan checks intentionally retain all rows. |
| `cli` | Current View count explicitly official-only. |
| `current_view_pilot` | Official selection already filtered; separate physical/official audit totals intentionally differ. |
| `claim_attribution_semantics`, `claim_node_activation`, `corpus_pilot` | Physical-table audit/snapshot accounting, not official selection or view creation. |
| `phase3f_operational_handoff` | Legacy view-write prohibition unchanged; new profile admits only validated frozen baseline inserts. |
| `config`, `storage`, file render/write helpers | No new selector; official side effects pass through the guarded caller. |

## Baseline storage and deployment preconditions

The preferred physical representation is `current_views.status='baseline'`,
but **not on an unprepared database**. Baseline identity uses a `baseline_`
version namespace; it has no official predecessor or accepted proposal, and
revision_seq is zero. Original Markdown is copied exactly. Original JSON
(including absence), Source/Claim references, as-of date and package/content
hashes are retained in the provenance envelope, not summarized.

`baseline_views.install_baseline_guards` is an **explicit schema preparation
operation**, not called by Database.init_schema, handoff, or promotion. It is
used only on disposable synthetic databases in this qualification. Exact guard
SQL is checked before baseline handoff/application. The guards reject updates,
deletes (including Node cascades), INSERT OR REPLACE, promotion to official,
and using a baseline as an official predecessor. No existing official-view
authorization is weakened.

The frozen Production schema lacks both these guards and, where applicable,
the repository's relation_evidence_links table. A separately authorized schema
deployment and fresh baseline qualification are required before actual
foundation execution. Do not initialize, migrate or silently repair Production
to satisfy handoff. A schema change invalidates the old Production-bound packet;
it must be requalified, and prior human decisions must not be carried forward
without explicit reauthorization against the new immutable packet.

The storage design passes synthetic isolation with these explicit preconditions.
No dedicated baseline_views table is required by the tested design. If an
installation cannot enforce these guards and official selectors, baseline
execution stays blocked; do not fall back to official insertion.

## Future incremental lifecycle

Foundation baseline → incremental expert/meeting Source → new Claims → global
Node reuse/create → Relation confirm/create/contradict/change → impact evaluation
→ Current View proposal → explicit human Current View resolution.

With no official Current View, accepted Baseline Views MAY be separately supplied
as immutable prior context. `baseline_reference` returns those references; it
does not elect a Current View. With an official Current View, the previous
official view remains the version predecessor and the Baseline remains historical
reference. Future expert Sources must never mutate the Baseline. This PR does
not implement the future noisy-source pipeline, automatic impact work, or model
generation.

## Qualification scope

Public fixtures cover three Sources, multiple Claims, CREATE/REUSE Nodes,
independent Aliases, part_of/supplies/depends_on/competes_with, exact Relation
REUSE, supports/contradicts Evidence, and a frozen Baseline. Tests use the shared
Phase 3D validator and disposable apply/diff/replay/rollback. Negative tests
exercise identity, provenance, human completeness, hash drift, schema readiness,
temporal loss, dependencies, authority, and immutable/official isolation.

Real Source/package text and real review artifacts remain under ignored
`workspace/`. Public commits contain only generic code, tests and this contract.
Blank review readiness is not execution readiness or Production authorization.
