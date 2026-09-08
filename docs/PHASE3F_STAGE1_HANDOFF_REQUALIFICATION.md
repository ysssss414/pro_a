# Phase 3F Stage 1 Handoff Requalification

## Scope

This stage consumes only the seven decisions in qualification review packet
`QUALIFICATION_REVIEW_PACKET_84E788062EA93B8E`. It does not review or authorize
the other 198 candidates in the 205-item operational review surface.

The output is a Phase 3D-shaped, shadow-only qualification candidate. It is not
an authorization-bound final payload and cannot be used by the Production final
apply path.

## Deterministic mapping

- A Claim decision of `KEEP` is qualification-promotable. `DROP` and
  `KEEP_NEEDS_REVIEW` remain non-promotable.
- A Node decision of `CREATE` or `REUSE` is qualification-promotable only after
  the existing Phase 3D identity checks pass. `DEFER` and `REJECT` remain
  non-promotable.
- A parent-placement decision of `CREATE` is qualification-promotable only when
  its child candidate resolves to an executable `CREATE` operation.
- No Claim-to-Node or Source-to-Node link is inferred from the qualification
  decisions.

## Safety boundary

Every persisted artifact records:

```text
REVIEW_SCOPE = PHASE3F_STAGE1_HANDOFF_QUALIFICATION_ONLY
QUALIFICATION_ONLY = true
FULL_OPERATIONAL_REVIEW_COMPLETE = false
PRODUCTION_AUTHORIZATION = false
PRODUCTION_APPLY_AUTHORIZED = false
UNSELECTED_CANDIDATES_REVIEWED = false
```

The adapter reuses the generic Phase 3D payload and pre-apply validators, applies
the candidate only to disposable shadow copies, verifies idempotent replay and
transaction rollback, and requires the Phase 3D final Production validator to
reject the candidate's non-authorization-bound document type.

The later generic full-operational handoff gap closure preserves this contract
as a compatibility wrapper. Stage 1 input validation and seven-item regression
controls remain qualification-specific, while deterministic mapping, payload
construction, and shadow qualification now delegate to the shared handoff core.

Phase 3F Stage 2 is outside this stage and remains unstarted.

## Public repository projection

Evidence-bearing packets and full promotion candidates remain untracked and
available only in the local audit workspace. The committed artifacts under
`workspace/phase3f_stage1_public_audit/` contain deterministic projections with
IDs, hashes, counts, decisions, targets, dispositions, authorization lineage,
and validation results. Statements, excerpts, report prose, human decision
prose, supporting-evidence objects, and mutation rows are omitted; hashes bind
the projections to their local full-fidelity inputs.
