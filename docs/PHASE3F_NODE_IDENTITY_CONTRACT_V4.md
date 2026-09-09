# Phase 3F V4: identity admission is separate from Claim admission

V3's `NODE_SUPPORT_NON_EXECUTABLE` predicate applies to both CREATE and REUSE.
It requires a KEEP Claim reached through `supporting_claim_ids`. Those IDs are
derived exact-Evidence joins, not universal semantic identity authorities. The
frozen 295-row slate demonstrated 30 REUSE and 7 CREATE failures, with downstream
Alias, Claim, Relation and Baseline failures. This is the bounded correction;
the prior packet, contract and STOP remain valid historical artifacts.

## Contract layers and schema compatibility

`BOUND_IDENTITY_CONTRACT` is a new hash-bound V4 review/execution contract. It
explicitly incorporates the unchanged `BOUND_CONTRACT` V3 storage/evidence
sub-contract through `storage_evidence_contract_sha256`. The old public constants
remain V3 for historical callers; choosing V4 requires explicitly binding the new
constant in a newly frozen review packet. Old V3 packets retain their old rules.

This separation is intentional: schema 0.2.3's temporal, Claim admission and
Relation evidence guards contain the V3 hash. Their rules are not changing.
V4 identity/alias compilation is application-layer behavior and needs no new SQL,
schema version, meta marker or trigger. V4 synthetic end-to-end tests must pass
the existing guards without replacing them. Persisted Claim/evidence provenance
continues to identify its exact V3 sub-contract, while the immutable packet hash
binds the new V4 review contract and implementation. No V4 behavior is mislabeled
as V3 review behavior.

## Generic identity rules

- REUSE: exact approved target and frozen target snapshot, active valid Node,
  allowed compatible type and unambiguous identity. No supporting KEEP required.
- CREATE: nonempty canonical name, allowed type, no existing or within-packet
  canonical/NFKC/casefold collision, empty runtime target override, and at least
  one exact immutable Evidence reference with verified Source identity. Evidence
  and Source bindings are diagnostic provenance; Human CREATE supplies identity
  and type semantics. No Claim is promoted by Node identity admission.
- Direct existing references resolve independently against an active, allowed,
  identity-valid Production Node. A parallel deferred/rejected Foundation
  candidate neither deletes nor disables that existing identity.
- Candidate references require that exact candidate's CREATE or REUSE decision.
  A DEFER/REJECT/blank/missing candidate cannot be used as an active candidate.
- `supporting_claim_ids` remain unchanged, with the derived role
  `NON_BLOCKING_NODE_IDENTITY_PROVENANCE` in the new review projection.

## Alias compilation

Human `target_id` remains the exact approved semantic candidate or existing Node
reference. `identity_plan` resolves it and the frozen candidate target to the
same final runtime ID. Candidate CREATE uses the existing deterministic Node ID
algorithm; candidate REUSE uses its exact human-approved existing Node ID.
The real compiler and non-authorizing preview share this identity planner.

An ATTACH term that is NFKC/casefold-equivalent to its target's canonical name,
with no different owner, produces `ATTACH_NOOP_CANONICAL_EQUIVALENT`, zero alias
mutations and an explicit audit reason. It remains Human ATTACH. A true
cross-node collision still fails. An exact already-stored same-owner alias also
has a distinct no-op disposition; no redundant row is inserted.

## Unchanged evidence and authorization boundaries

KEEP still requires Claim qualification and, in V4, an executable subject.
KEEP_NEEDS_REVIEW/DROP are not persisted or active evidence. Every exact required
Claim-linked Relation Claim must remain qualified KEEP. Native Relations retain
the exact existing manifest and scoped SUPPORTS authority. ACCEPT Baseline
supporting Claims must still be KEEP; Baselines never become official views.

`preview_eligibility` accepts a blank packet and a separate hypothetical/rebased
slate. It does not fill human inputs, set human completion, or call a mutation or
payload builder. Returned evidence links are tagged
`PREVIEW_ONLY_NOT_AUTHORIZATION`; runtime row builders reject that tag.

`scripts/phase3f_foundation_contract_correction.py` verifies the exact local frozen
inputs, requalifies without PDF parsing, proves all-row equality, and runs the
non-authorizing preview twice. After a new bounded local commit and successful
regression it can freeze a new blank packet and separately rebased slate. The
slate preserves every old candidate ID, decision, reason and semantic target;
prior content approval is history only, not approval of the new review basis.

STOP before any completed review or real payload. A new explicit human approval
must identify the rebased slate's newly computed semantic SHA256.
