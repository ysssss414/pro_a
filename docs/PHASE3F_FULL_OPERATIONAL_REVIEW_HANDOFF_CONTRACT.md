# Phase 3F Full Operational Review Handoff Contract

## Why this contract exists

The original Stage 1 adapter intentionally accepted only its frozen seven-item
qualification packet. Its document identity, candidate set, review boundary,
and safety assertions were qualification-specific, so accepting a completed
generic operational packet through that adapter would have weakened its
historical guarantees.

The full-operational path therefore adds a generic input contract while sharing
one deterministic mapping and Phase 3D payload-construction core with the Stage
1 compatibility wrapper. It does not add a second review schema or fork the
Phase 3D payload schema.

## Supported inputs and shared core

- The full-operational entry point accepts only a completed
  `phase3f_operational_review_packet` at schema version `1`. It reuses the
  authoritative validation in `phase3f_review_completion.py` and verifies the
  completion receipt, human authorization, candidate hashes, Source/run
  lineage, repository commit, and current Production baseline.
- The Stage 1 wrapper continues to accept only the historical qualification
  document and retains `qualification_only = true`,
  `full_operational_review_complete = false`, and its exact seven-candidate
  regression checks.
- Both entry points delegate mapping, Phase 3D payload construction, mutation
  construction, safety validation, and shadow qualification to the same core.
  Source IDs, run IDs, candidate IDs, and candidate counts are inputs, not
  constants in the generic core.

## Decision and accounting semantics

Only `KEEP` Claims may be executable. `DROP` and `KEEP_NEEDS_REVIEW` Claims are
non-promotable. Only valid `CREATE` or exactly resolved `REUSE` Node decisions
may be executable; `DEFER` and `REJECT` are non-executable. A reviewed
parent-placement `CREATE` is executable only when its child operation and both
endpoints pass the existing structural checks. Aliases remain part of the
approved Node identity and must correspond exactly to authorized executable
Node mutations.

Every reviewed Claim, Node, and governed parent-placement candidate has exactly
one deterministic mapping record. A promotion-authorizing human decision that
fails an existing Phase 3D gate is retained as blocked with an exact reason; it
is never forced into the payload. No Claim-to-Node or Source-to-Node link is
inferred, and no unsupported object type or mutation is admitted.

## Qualification and Production boundary

A completed operational review authorizes only local promotion qualification.
Every generic payload and receipt requires:

```text
FULL_OPERATIONAL_REVIEW_COMPLETE = true
PRODUCTION_AUTHORIZATION = false
PRODUCTION_APPLY_AUTHORIZED = false
QUALIFIED_EXECUTION_TARGET = SHADOW_ONLY_QUALIFICATION
```

The handoff runs the existing Phase 3D payload and executable-operation
validators. The existing final Production validator must reject this
non-authorization-bound payload. Apply, replay, rollback, and restore checks run
only against disposable exact Production copies, and the configured Production
database must remain byte-identical.

## Public and local artifacts

Committed tests use synthetic statements, aliases, IDs, hashes, and decisions.
Source documents, real excerpts, completed source-bearing packets, complete
payloads, and human-review prose remain only in ignored local workspace paths.
The generic command prints only status, deterministic IDs and hashes, counts,
and safety results.

## Stage 2 status

Local acceptance of a real completed Stage 2 packet proves that this generic
contract is operational; it does not complete Stage 2. After this contract is
merged into `main`, Stage 2 final qualification must be rerun from the merged
baseline before any later stage can begin.
