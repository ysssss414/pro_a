# Foundation execution contract closure — preparation only

Historical Claim-only preparation: its evidence-path rule is superseded by
`phase3f_foundation_relation_native_governance.md`. The old packet, receipt and SQL
artifact remain unchanged; the new proposal has a separately frozen SQL/contract hash.

This is not Production migration authorization, Human Review, or permission to
build a real executable foundation payload. No commit, push or PR is part of this
stage. The prior immutable blank packet and STOP receipt remain unchanged.

## Opt-in authority; no retroactive reinterpretation

The existing packet schema remains version 1. A **new** packet must explicitly
bind `FOUNDATION_EXECUTION_CONTRACT_V2` and its canonical SHA256. Old packets do
not acquire new KEEP or Relation semantics when code changes. The shared
foundation compiler still emits Phase 3D payload version 1, using the unchanged
INSERT-only shadow engine, baseline checks, diff, replay and rollback.

| Human Claim decision | Runtime admission | Persisted by this adapter | Active Relation evidence |
| --- | --- | --- | --- |
| KEEP, qualification passed | needs_review → current, explicitly authorized | Yes | Yes |
| KEEP, unresolved individual exception | Blocked pending qualification | No | No |
| KEEP_NEEDS_REVIEW | Remains needs_review in review artifact | No, preserves existing adapter behavior | No |
| DROP | No promotion | No | No |
| Blank | Incomplete review | No | No |

KEEP preserves the complete original structured provenance and adds an admission
receipt containing pre-review status, admitted status, reviewer/reason, immutable
packet hash, candidate content hash and contract hash. Native status, nature,
attribution, time and qualification diagnostics are never overwritten. The two
individual exceptions are not promoted by a blanket status conversion or a batch.

The legacy SQL date columns are NOT NULL. A qualified Claim's native null date
uses the existing empty-string SQL sentinel, never an inferred date. Its original
null is retained in both native structured provenance and the admission receipt's
pre-review time fields. This storage-only conversion does not qualify a Claim
with unresolved temporal identity; qualification must pass first.

## Temporal semantics are a separate normalized dimension

`project_temporal` discovers categories from input, never a handwritten category
allowlist. It copies `temporal_status` verbatim, without date parsing, case
folding, or mapping suffixes to validity bounds. It separately preserves optional
native validity fields and whether each was supplied (including explicit null).
Runtime validity is populated only from those exact values; absence is not a date.

The proposed normalized `relation_temporal_semantics` row is keyed by the existing
Relation ID and stores category, supplied flags, projection/contract hashes and
structured provenance. Existing Relation identity remains
`(from_node_id, relation_type, to_node_id, scope)`; no relation vocabulary changes.

`node_relations.status='categorical'` is an explicit **lifecycle marker**, not a
replacement temporal meaning. The runtime meaning is the pair of this marker
and the verbatim category plus supported validity. A category-aware caller uses
`categorical_relations`; it must not discard the category or assume currentness.
Legacy `status='current'` selectors deliberately do not treat future, scoped or
timeless categorical assertions as unqualified current edges. This is fail-closed
forward compatibility, not a mapping of all categories to identical time meaning.
No automatic temporal activation, inference engine or noisy-source pipeline is
implemented. Existing current Relations and official Views remain unchanged.

CREATE persists the exact temporal row. REUSE requires an exact existing Relation
identity and a matching categorical projection; it cannot silently relabel a
legacy current edge. A changed temporal interpretation requires requalification.
part_of cycle safety remains part_of-specific and conservative.

## Explicit evidence-link governance

1. Immutable Relation Evidence IDs are source provenance.
2. Equality of an Evidence ID with a Claim's frozen Evidence record creates a
   deterministic **candidate**, bound to Relation/Claim native hashes, Evidence
   record hash, Source ID/SHA and package SHA. It has no human authorization.
3. Shared ID alone assigns no SUPPORTS/CONTRADICTS role. The new immutable Relation
   review row explicitly states that CREATE/REUSE confirms **all listed links**
   as SUPPORTS unless a link has an explicit frozen source role annotation.
4. The Relation decision and every required Claim's separate qualified KEEP are
   required. If the reviewer cannot confirm every listed link, DEFER/REJECT is
   the lawful non-executable outcome. No subset is silently omitted.
5. CONTRADICTS requires an explicit frozen role annotation identifying Claim and
   Evidence IDs and the same exact join, plus human confirmation. REJECT never
   implies CONTRADICTS. Conflicting/unmatched explicit annotations fail closed.
6. Normalized authorization rows preserve each Evidence record's provenance and
   the cross-object decision authority. Existing `relation_evidence_links`
   aggregates authorized proofs by `(relation_id, claim_id, evidence_role)`.

A Relation with no exact Claim-backed candidate is **not solved** by this rule.
It remains execution-blocked until a separately governed explicit Claim/Evidence
binding is supplied and requalified. A reviewer cannot invent that binding merely
by choosing CREATE. This preparation must enumerate such records, not pretend
the future schema closes a missing semantic-authority gap.

## Proposed schema 0.2.3

The forward proposal accepts the frozen 0.2.1 layout and the repository 0.2.2
layout. It is additive to existing data and deliberately not wired into automatic
`Database.init_schema`. Prepared 0.2.3 databases are verified and left byte-identical
by that initializer rather than downgraded to 0.2.2 or subjected to legacy backfills.

| Object | Change |
| --- | --- |
| relation_evidence_links | Add missing canonical 0.2.2 table; retain composite PK, role/status CHECKs and FKs. Existing legacy evidence_claim_id support semantics retain the existing 0.2.2 backfill rule, not a package-join heuristic. |
| relation_temporal_semantics | New 1:1 Relation table; exact category, validity-supplied flags, hashes, native provenance; FK RESTRICT; immutable projection. |
| relation_evidence_authorizations | New normalized per-Evidence proof/authorization table; role and decision CHECKs; Source/Claim/Relation FKs; unique proof identity; immutable provenance. |
| Three indexes | Category/Relation lookup; Relation/Claim/role authority lookup; Claim/status evidence lookup. |
| Governance triggers | Require current KEEP admission and matching packet/reviewer/contract/source identity; forbid unauthorized active links and role substitution; preserve temporal semantics and immutable authorization/projection rows, including REPLACE attacks. |
| Baseline guards | Separate exact namespace; no overwrite of any existing View; no official predecessor, implicit baseline predecessor or sequence; original baseline artifact status; immutable INSERT-only identity. |
| meta | schema_version=0.2.3 and exact foundation execution contract SHA. |

No current_views columns or official ordering rules change. No dedicated baseline
table is needed. Every baseline uses `version='baseline_'||view_id`, a reserved
BASELINE_ identity, null predecessor, sequence zero, and the original
`handoff_baseline_not_production_current_view` status in provenance. Other statuses
cannot enter that namespace. Independent later baselines remain independent;
supersession is **not implemented or inferred**. Any future supersession requires
an explicit separately governed lineage contract, not Current View sequencing.

The SQL exporter produces exact DDL. The only provided migration executor is
**synthetic-only**, refuses the configured Production path and hardlink aliases,
checks the expected byte baseline and source version, and executes DDL in one
transaction. Do not use the exported SQL to bypass those preflight checks.
Only a future explicitly authorized Production run may use the prepared plan.

## Rollback and requalification procedure

Before a future migration: resolve outstanding semantic-authority gates, obtain
explicit authorization for the exact migration SQL hash and Production SHA,
quiesce writers, verify no sidecars and integrity/FKs, and take an offline
byte-verified backup. The two existing official Views must be fingerprinted.

On pre-commit error: ROLLBACK the whole schema transaction, including meta and
legacy backfill. After commit: restore the verified offline backup only under
separate recovery authority and with writers stopped. A downgrade script that
drops new governance data is deliberately not supplied. If new writes occurred,
stop and reconcile/export them before considering backup restore.

After an authorized successful migration:

1. Verify preserved existing rows, official View fingerprints, integrity and FKs.
2. Freeze the new Production schema/version/byte SHA; never substitute a synthetic DB.
3. Reverify immutable archive, inventory, qualification and Source registry bindings.
4. Use `requalified_objects` to regenerate execution/review projections; preserve
   every native semantic object and stable candidate ID.
5. Reconcile CREATE/REUSE targets and all unresolved evidence dependencies against
   the new frozen baseline; do not relax individual Claim exception gates.
6. Build a **new blank packet**, binding the new Production SHA and exact opt-in
   contract. Its packet identity also includes those new bindings.
7. `compare_review_objects` verifies all candidate IDs and distinguishes unchanged
   native semantics from changed review/authority content. Unchanged content keeps
   its hash; new admission notices, temporal/link rules and baseline provenance
   receive changed content hashes. A global contract change still requires a new
   review even when an individual native object is identical.
8. Require exactly the complete review universe, no omitted objects and no human
   decisions; validate deterministic rerun and per-object diff.
9. Declare Human Review readiness only when every gate for that new packet has
   actually passed. There are currently no decisions to transfer.

This stage stops before step 1's actual Production mutation. Missing exact
Claim/Evidence bindings take precedence over requesting migration execution.
