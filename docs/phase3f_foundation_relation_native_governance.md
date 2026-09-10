# Foundation Relation-native evidence governance — proposed schema 0.2.3

This supersedes the Claim-only execution preparation rule, not the original
immutable package, blank packet or historical receipts. No Production migration,
real payload, content review, commit, push or PR is authorized in this stage.

## Two explicit provenance paths

| Mode | Evidence authority | Required later content decisions |
| --- | --- | --- |
| RELATION_NATIVE | Exact immutable Evidence ID/content hash, Source ID/SHA, Relation candidate/native hash, temporal category and scope; separately frozen human role/proposition authorization manifest | Executable Node endpoints, qualified Relation and explicit CREATE/REUSE; no Claim admission requirement for this evidence path |
| CLAIM_LINKED | Exact Evidence-ID candidate joins remain unauthorized; explicit immutable cross-object rule requires confirmation of actual semantic support, not adjacency | Separate qualified Claim KEEP plus Relation CREATE/REUSE and executable endpoints |

A Relation is an evidence-bearing proposition. Do not manufacture Claims for
storage convenience or substitute a semantically adjacent Claim. The immutable
projection selects RELATION_NATIVE only for the exact separately authorized
rows; it cannot silently fall back from inadmissible Claim evidence. Where the
native mode is bound, incidental Claim joins are not execution dependencies.
Every Claim-linked path still rejects KEEP_NEEDS_REVIEW, DROP, blank and unresolved
qualification. All original native Claim/Relation/Node/Evidence content is retained.

The human evidence governance manifest is a separate artifact, sealed by canonical
SHA256 and a deterministic manifest identity. It binds the instruction fingerprint,
original packet ID/hash, immutable archive hash, exact scoped proposition, Evidence
content/hash and Source SHA. Its `authorized=true` is role authority only. Its
Relation decision and Claim content-decision fields remain blank. The original
295-row packet is untouched. No manifest row can authorize a different Relation,
Evidence record, Source bytes, temporal category, endpoint identity or scope.

The new opt-in `FOUNDATION_EXECUTION_CONTRACT_V3_RELATION_NATIVE` and manifest must
be bound into a future **new** blank packet after migration/requalification. Old
packets do not retroactively acquire new semantics. CREATE/REUSE is still required
to compile runtime rows; DEFER/REJECT/blank cannot create native evidence links.
Native SUPPORTS authorizations do not entail any Node/Relation disposition.
CONTRADICTS requires separate explicit authority, never a rejection inference.

## Bounded real authority and the individual Claim adjudication

The current human instruction supplies precisely eight native SUPPORTS rows for
five Relation candidates; no CONTRADICTS rows. The local manifest contains the
complete approved identities, hashes, propositions and scope restrictions.

For the CPO implementation variant, preserve the exact external-laser scope,
implementation_variant category, REVIEW advisory and overlapping frozen prior
DEFER. This is not the proposition that all CPO uses external lasers. The earlier
DEFER is neither overridden nor superseded. Taxonomy Evidence authority does not
approve subtype Nodes. Product-family native Evidence authority is independent
of Claim evidence-identity qualification; other Node/content gates remain intact.

The separately recorded attribute-vs-identity adjudication chooses the explicitly
named authoritative Evidence for the Claim, not a metadata heuristic. Both frozen
Evidence records remain unchanged; the non-selected record is retained as sibling
provenance. Qualification independently rechecks Source identity, excerpt/locator,
date validity and mapped nature before resolving the ambiguity. It cannot hide a
separate missing temporal identity. The Claim remains needs_review with no KEEP,
KEEP_NEEDS_REVIEW or DROP. Original qualification diagnostics remain in structured
provenance alongside the adjudication; no duplicate Claim is created.

## Proposed DDL delta from the superseded 0.2.3 proposal

No version increment: neither 0.2.3 proposal has been deployed. The prior SQL is
SUPERSEDED, identified by its exact hash in the new migration proposal/receipt.
Production remains the frozen 0.2.1 database. A synthetic DB carrying the superseded
0.2.3 contract is rejected as drift, not upgraded automatically.

- Rebuild relation_evidence_links transactionally, preserving all five existing
  column values and composite Claim-link PK semantics. Add provenance_mode,
  optional Claim FK, Evidence identity/hash, Source FK/SHA and authorization FK.
  CHECKs require a real Claim for CLAIM_LINKED; RELATION_NATIVE requires NULL
  Claim plus complete Evidence/Source/authorization provenance. Legacy inserts
  default to CLAIM_LINKED; a NULL Claim cannot masquerade as that mode.
- Amend relation_evidence_authorizations with provenance mode, optional Claim,
  exact Relation candidate, authorized proposition/scope, manifest identity and
  original packet hash. Mode CHECKs distinguish native blank content decisions
  from the separate qualified KEEP/CREATE-or-REUSE Claim-linked rule.
- Add two partial UNIQUE indexes for native link/proof identities, closing the
  SQLite composite-NULL uniqueness hole. Retain the existing three lookup indexes.
- Retain all temporal, Claim admission and baseline guards. Add native exact-binding
  admission guards and immutable link/Source-identity protections. No Claim FK is
  weakened for Claim-linked rows; native provenance instead has Source/Relation/
  authorization FKs. REPLACE, UPDATE and DELETE cannot rewrite frozen provenance.
- Retain relation_temporal_semantics unchanged in meaning: all 56 Relations retain
  their 21 categories verbatim with optional exact validity, never converted to current status/dates.
- The shared INSERT-only shadow compiler emits both link modes. The runtime
  evidence reader uses a LEFT JOIN for optional Claims and exposes native
  authorization/proposition fields; it does not invent a Claim statement.

No additional governance table is needed. The short-lived legacy table exists
only inside the migration transaction and is removed after its rows are copied.
The executor verifies preserved existing rows, constraints, exact schema/contract,
integrity and FKs before commit. Production-path/alias guards remain in place.

## Validation and next authorization

Use temporary/synthetic databases only. Required coverage includes both modes in
one shared-engine payload, native evidence without a Claim, every cross-binding
negative probe, scope containment, blank/non-executable decisions, strict Claim
admission, Claim adjudication without content review, immutable provenance, legacy
link preservation, full rollback/replay and Phase 3D / Stage 1 / Stage 2 regression.
Real tests inspect frozen identities and pure projections only; they never populate
real content decisions or compile a real payload. Original receipts remain unchanged.

After preparation passes, STOP. The next permission is an explicit authorization
to migrate the **exact frozen Production SHA** using the **final proposed SQL SHA**.
Quiesce writers, verify sidecars/integrity/FKs, capture both official View fingerprints
and take a byte-verified offline backup before any future authorized transaction.
On failure, roll back the whole transaction; after commit, restoring a verified
backup requires separate recovery authority and reconciliation of any newer writes.
No lossy downgrade that discards governance evidence is supplied.

After a separately authorized migration: freeze the new Production schema/version/
byte hash, reverify original package and Source registry, requalify against the new
schema and exact manifest, freeze a **new blank packet**, and compare all 295 native
identities and review-content hashes. Only successful requalification can establish
Human Review readiness. No final post-migration packet is generated in this stage.
