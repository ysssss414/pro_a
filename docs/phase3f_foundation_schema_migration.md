# Phase 3F schema 0.2.3 migration and deterministic requalification

This runbook executes only the explicit, two-hash human authorization. It never
decides Foundation content, creates a promotion payload, applies candidates,
calls an LLM, pushes, or opens a PR. Stop after a new immutable blank packet and
the Human Review readiness report. Foundation COMPLETE remains false.

## Immutable execution identities

Old Production SHA256: `3c0007f38b136686cb1e0e73e2ad2f389983f61ae2c81679fcf5067835c4eba0`

SQL SHA256: `17d0706380a4ba57c78081b9aeb37141115564b2f8210671194358d338b8e4f0`

Canonical SQL: `src/pro_a/migrations/foundation_0_2_3_relation_native.sql`.
Its Git attribute is `-text`; verify both filesystem bytes and committed blob.
Do not regenerate the SQL. The old PREPARE ONLY comment is intentionally retained
as part of the authorized bytes; this run's explicit human authorization is a
separate immutable input, not an edit to the SQL.

## Bounded implementation scope

Include the Foundation contract, native Evidence, schema preparation/migration,
requalification and blank packet adapter; their directly associated tests/docs;
the SQL and its single-file Git attribute; Baseline guard module; and the small
existing integration diffs in db, current_view, coverage, proposals,
production_promotion and phase3f_operational_handoff. Those integration diffs
prevent implicit downgrade, isolate historical Baselines from official Current
Views and bind the governed adapter to the shared validator. They are Foundation
dependencies, not unrelated historical work. Do not include Stage 2 scripts,
workspace outputs, source documents, virtual environments or unrelated artifacts.

Inspect the exact diff, test, then create exactly one local implementation commit
whose parent is `4ecc36450d1ec8551bd0a6aa65475f60a0b7c68f` on
`codex/phase3f-foundation-complete-baseline`. Record remaining worktree entries.
Do not stage the entire tree or push.

The first implementation freeze `591ed09f8e7e770601945eaeb75f060b5f3eeee3`
stopped before writable Production: its preflight reader remained open and blocked
the subsequent OS handle probe. The user explicitly authorized fixing closure,
adding the integration regression, refreezing and retrying the same two-hash
migration. Amend the unpushed local implementation commit (same parent); retain
the prior SHA and every STOP artifact in the audit trail. Resumed artifacts go in
`workspace/phase3f_foundation_schema_migration/resumed_connection_closure`, never
overwrite the parent directory's frozen failed-run artifacts.

## Transaction and recovery

The CLI phases are `preflight`, `rehearse`, `migrate`, `requalify` in
`scripts/phase3f_foundation_schema_migration.py`. Run rehearsal and tests before
the implementation commit. Migrate checks parent/commit, clean bounded files,
the committed SQL blob, Production path/config/hash/schema/integrity/FKs,
sidecars, two official fingerprints, immutable corpus/manifest/old blank packets.
An exclusive Windows read-handle probe must succeed before opening writable
Production. Do not start the application or any background writer during this
bounded operation. BEGIN IMMEDIATE then reserves the sole writer and rechecks
the byte identity before backup or DDL. Concurrent writer lock errors stop.

Use contextlib.closing for every runbook read-only connection: sqlite3's own
context manager does not close it. The integration regression runs full old-baseline
preflight then the actual OS exclusive-handle check with automatic GC disabled.
It must pass without gc.collect, handle-probe bypass or writable Production.

Only DELETE journal with absent sidecars is accepted; no checkpoint or journal
normalization is needed or performed. Copy the unchanged bytes under the write
reservation, flush/fsync, then reopen the backup read-only and verify hash,
integrity, FKs and semantic fingerprints. Preserve the recovery artifact.

Parse the exact authorized file with sqlite3.complete_statement so trigger
bodies are not split. Execute its original transaction envelope and statements.
Before executing its COMMIT, require every reviewed table/index/trigger,
integrity/FKs and exact legacy semantic preservation. Only the reviewed meta
changes, legacy Evidence backfill and empty new governance tables may differ.
All native active links remain absent; the eight authorities stay in the frozen
manifest, not runtime rows requiring undecided Relations.

On a pre-commit failure, ROLLBACK and verify old byte/schema identity; STOP, no
retry or automatic repair. A post-commit failure also stops and retains the
backup; no automatic restore may discard newer writes. Failure injection tests
cover first DDL, table rebuild, guards and final pre-COMMIT positions.

## Requalification and readiness

Hash Source PDFs only; reuse frozen parsing/provenance and exact archive inventory.
Re-resolve Node/Alias/endpoints against the frozen migrated snapshot. Recheck all
Claim immutable fields, Source, Evidence identity/excerpt/locator, nature and
supplied dates; preserve Claim0066's individual temporal exception and no KEEP.
Apply only the previously frozen Claim0067 identity adjudication. Verify all 56
temporal projections and the native/Claim-linked routes. The CPO proposition
remains some external-laser implementations; historical R1F_0041 DEFER remains.
Validate all nine historical Baselines under installed immutable guards.

Generate a new blank packet only after deterministic qualification passes. Bind
new Production/schema, implementation commit, exact SQL, manifest and original
archive/inventory; preserve the old packet. Compare all 295 native hashes,
projection hashes, target resolutions and qualifications. The 67 Claim admission
contracts and 56 Relation evidence/temporal review contracts are explicitly
classified REVIEW_SEMANTICS_CHANGED, not silently called unchanged. The other
172 rows are SEMANTICALLY_UNCHANGED_REQUALIFIED. All native content must match.
Expected explained contract changes do not imply content changes or acceptance.

Claim0066 is not an unexplained mechanical failure: it remains a visible individual
review exception, excluded from the 66 batchable Claims, with KEEP blocked until
proper temporal qualification. No date is invented. Readiness means humans may
make governed decisions (including non-executable dispositions), not that all
candidates can be promoted. Final readiness additionally requires the full
regression suite and unchanged frozen post-migration Production/inputs.
