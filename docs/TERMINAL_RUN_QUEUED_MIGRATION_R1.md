# Terminal Run queued history — offline schema12 migration

Candidate qualification passed; task PASS requires the independent repair PR merge.
Implementation: `63fcb2df8a838561aded1f41f8e5dc03d47f731f`; base: `7c0a06a0850f3b7a3f0eba80becc9185e91b10c0`.
The [sanitized receipt](terminal_run_queued_migration_r1_candidate_receipt.json)
contains per-job classifications, exact-copy results, test run counts and wheel identities.

The schema12 migration reused lifecycle's global QUEUED/RUNNING guard. Its new
read-only predicate permits only pristine queued Source jobs with unique and
consistent Run/input ownership, ended FAILED/BLOCKED/HUMAN_REVIEW_REQUIRED parents,
no leases, attempts, results, usage, execution events, or accepted retry lineage.
RUNNING, recovery jobs, active Runs, unbound/inconsistent queues and broken FKs block.
RECOVERY_REQUIRED parents never qualify a queued waiver. The existing no-job Run
drain rule and bounded-series/segment drain checks remain intact.

The shared lifecycle guard remains byte-identical, as do domains, stage1 and all
runtime worker/scheduler files. Its callers are both prepare_stage6_lifecycle
checks, apply_lifecycle_closure, apply_stage6_plan and previously schema12 _drained;
only that last caller now uses migration-specific classification. Old schema8→9,
9→10 and 10→11 migrations still reject queued work. Backup, transaction/offline
guards, additive schema, receipt and idempotence contracts are unchanged.

All 14 real QUEUED jobs are bound to five ended FAILED Runs, never called, with
zero leases/fences/reservations/attempts/dispatches/outcomes/results/retry rows.
Normal PRIVATE dispatch goes through SourceOperations, whose selector excludes
terminal Runs before choosing jobs. Nine exact-copy probes (global plus all eight
historical Runs) return None without any CloudJob worker or provider invocation.
The low-level CloudJobs.run_once/_claim API itself has no parent-state guard:
arbitrary direct operator calls are outside this normal scheduler proof. It is
unchanged. The standalone fake CloudJob CLI rejects PRIVATE mode, and the API has
no independent CloudJob worker endpoint. No runtime-drift exception is used.
Accepted retry events/lineage fail closed; explicit reprocess creates another Run.

Qualification: 32 focused cases and 437 other related cases (469 unique selected).
The first related run had 467 passes and two failures; the canonical-byte fixture
and genuinely-active-work fixture corrections passed all three affected reruns.
The receipt preserves those separate raw counts. No full-repository green claim.
The matrix covers active queues, RUNNING with active/FAILED parents, clean FAILED,
BLOCKED and HUMAN_REVIEW_REQUIRED history, recovery/unknown liability, attempts,
dispatches/outcomes/results/orphan evidence, unbound jobs, live accepted retry,
leases/fences/counters/identity mismatch, old strict migrations and no CloudJobs.

An exact copied real schema11 DB migrates to12 with exactly14 queued waivers,
44 old tables retained, all old rows unchanged except schema_version, all old SQL
definitions unchanged and exactly eight new empty bounded tables. Backup matches
the original DB SHA256 `0114861af73d616f1a732ee0f16252514052bfc59c997f3480fc3c4ec411da8d`.
Idempotence passes. Exact original metadata bindings are retained: existing
Production/artifact validation reads original paths; a connection guard forbids
all SQLite writes outside the copy. Original DB and artifact hashes stay exact.
The committed tests/qualify_terminal_run_queued_migration.py replays this check
with explicit --workbench-config, --package-path and a fresh --output directory.

Compileall, pip check, isolated PEP517 wheel, all135 source/wheel/install Python
byte comparisons, full phase4/cloud identity equality, no Git/unrelated parent,
six malformed/tampered metadata fail-closed cases and privacy/diff review pass.
Stable remains #97/schema11; provider calls/liability0, Run8 absent. Real migration
and stable activation are deferred to the separate release task. PR96 is not merged.
