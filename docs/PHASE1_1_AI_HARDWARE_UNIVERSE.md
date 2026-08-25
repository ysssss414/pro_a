# Phase 1.1 — AI Hardware Expanded Knowledge Universe

Status: **STARTED — REQUALIFICATION GATE**

Start date: **2026-08-25**
Base: **Phase 1 frozen v0.3.0 / main**
Branch: `phase1.1/ai-hardware-universe`

## Objective

Use the Sol Pro AI Hardware foundation package as the candidate source for the Phase 1.1 / R2 expanded Node/alias universe, while preserving every Phase 1 frozen safety and maintenance contract.

This milestone is not a direct bulk-import exercise. The candidate package must first be reconciled against the actual frozen Production baseline and re-qualified through the current repository validators.

## Frozen Production baseline

From `docs/PHASE1_FREEZE.md`:

- Production SHA-256: `8bce2b47df971e527de3552ca0415160868b258c0fcd4a8f6d2f20f40a60541c`
- Nodes: 280
- Aliases: 706
- Node Relations: 177
- Current `part_of`: 170
- Retired R1 migrations: 7

No Phase 1.1 write is authorized unless the live Production precondition still matches the expected baseline or an explicitly reviewed successor baseline.

## Input package reviewed

Primary review artifact: `pro_a_ai_hardware_foundation_v2_review_20260818.xlsx`.

The package is useful as an offline candidate universe, but its own independent review explicitly classifies it as **offline staging only / not ready for direct Production import**.

Relevant V2 findings include:

1. Prior internal PASS did not establish Production-import readiness.
2. Candidate resolution was not grounded against the actual complete Production Node/alias catalog.
3. Some prior Relation support labels were manually assigned rather than validated through the current repository Relation path.
4. Cross-domain candidates were not fully isolated in the prior package and must remain quarantined.
5. Zero-evidence candidates must not be admitted merely to improve coverage.
6. Evidence Anchors are not equivalent to accepted Claims; Claim nature, attribution and time semantics still require normal pro_a processing.

Therefore the original Sol Pro package must **not** be imported as-is.

## Phase 1.1 import policy

### Node / alias

For every candidate:

1. Exact canonical-name lookup against actual Production.
2. Exact alias lookup against actual Production.
3. Primary-type compatibility check.
4. Alias collision / ambiguity check.
5. Existing-concept reuse before CREATE.
6. Model/generation/rate/configuration qualifiers remain Claim/scope unless independently justified as durable Nodes.
7. Cross-domain candidates stay quarantined for the corresponding domain review.
8. Human-gated CREATE remains mandatory.

### Relations

- `part_of` may enter structural review only after both endpoints resolve to approved Nodes.
- Non-`part_of` Relations require relation-specific Evidence and must pass the current evidence-aware analyzer / Relation validator.
- No Relation is admitted from a package-level `supported`, `ready`, or manually assigned status alone.
- No fuzzy endpoint resolution, evidence-free association, Gold-specific hardcode, type guessing, or validator weakening.

### Current View

Phase 1.1 universe expansion does not itself authorize Current View creation or modification.

## Required requalification sequence

1. **Actual-DB read-only preflight**
   - verify Production SHA / schema / counts;
   - resolve canonical names and aliases;
   - detect type conflicts and alias collisions;
   - compare existing structural and functional Relations;
   - detect self-loops, cycles where applicable, and transitive redundancy.

2. **Inventory reconciliation**
   - classify each candidate as `CREATE`, `REUSE`, `DEFER`, `REJECT`, or `CROSS_DOMAIN_QUARANTINE`;
   - retain an explicit reason and evidence pointer for every disposition.

3. **Clean approved Node package**
   - generate only after human decisions are recorded;
   - keep CREATE and REUSE separate;
   - exclude DEFER / REJECT / quarantine rows.

4. **Relation requalification**
   - resolve endpoints only against the approved Node universe;
   - submit non-structural candidates through the current Evidence-aware validator;
   - preserve rejected candidates as audit artifacts, not import payload.

5. **Controlled import**
   - explicit Production authorization;
   - SHA precondition;
   - read-only backup;
   - atomic apply;
   - import receipt;
   - idempotent rerun check;
   - exact rollback contract.

6. **Phase 1.1 freeze**
   - integrity validation;
   - final inventory and counts;
   - AI Hardware Node Baseline v1 freeze artifact.

## Current decision

`PHASE1_1_STARTED = true`

`SOL_PRO_PACKAGE_ACCEPTED_AS_STAGING_INPUT = true`

`SOL_PRO_PACKAGE_DIRECT_IMPORT_READY = false`

`PRODUCTION_WRITE_AUTHORIZED = false`

The next executable step is the actual-Production read-only reconciliation of the Sol Pro candidate Node/alias universe against the Phase 1 frozen baseline.
