# Historical receipt continuity and frozen-package preflight

This change permits registered historical execution receipts to remain readable after subsequent registered INSERT-only Operator transactions. Backend changes are confined to the historical read path in `operational_qualification.py`; the existing Attribution UI also displays the precise verification scope instead of unconditional VERIFIED text. It does not authorize execution, modify the Operator, migrate databases, or replace frozen packages.

## Verification scope

Every requested receipt retains its immutable ID/SHA, registry identity, envelope/Artifact binding, Native and Attribution seals, original Runtime, adapter/Operator entry versions, EXECUTED/COMMITTED status, original predicted Post-State, mutation counts, touched tables/keys and materialized source SHA checks. Inserted and unchanged rows must exactly match current Canonical objects and authorized mutations.

The reader follows registered receipts whose envelopes' Pre-State hashes match the preceding receipt's Post-State, ending at the current Canonical logical-state hash. Each successor independently passes the same sealed-package and receipt checks. Ambiguous successors fail closed. Complete chains additionally verify each exact INSERT delta against both registered state commitments using temporary in-memory row-set cancellation. These derived row sets are only algebraic checks, **not historical snapshots or newly manufactured evidence**; no missing transition is inferred from the database.

The trust boundary remains the existing append-only Workbench registrations produced by privileged Operator reconciliation, validated against their immutable bindings and sealed review artifacts. This is not an external signature/notarization system and does not claim protection against an administrator coherently rewriting every trusted database, seal and source. It introduces no substitute ledger or global event system.

Results:

| Result | Meaning |
|---|---|
| `HISTORICAL_EXECUTION_CHAIN_VERIFIED` | Registered executions and exact deltas connect the original Post-State to the current state. |
| `HISTORICAL_STATE_PROOF_INCOMPLETE` | Receipt integrity and current affected objects pass, but registered evidence cannot establish the full subsequent evolution. `receipt_integrity` separately reports `HISTORICAL_RECEIPT_INTEGRITY_VERIFIED`; the legacy `historical_read_verified` flag is false. |
| Exception | Immutable identity, binding, source, object, committed delta, ambiguity or recovery condition fails. No verified result is returned. |

Unexplained unrelated Canonical changes are not labelled legitimate. Changed/deleted affected rows fail; unrelated changes with no proof return incomplete. A missing intermediate registration never becomes a fabricated bridge. Real pending journal/WAL/SHM recovery conditions still raise `RECOVERY_REQUIRED`. Historical read results always keep execution authorization false.

`reconcile_registered` now returns the explicit proof status instead of generic `VERIFIED`; its receipt payload is unchanged. MCP and Workbench qualification projections include `history_verification`. Existing fully verified reads retain `EXECUTED_RECEIPT_VERIFIED`. No receipt body or stored status is rewritten.

## Frozen package and release order

Current Stable/Main is `05499b9b1376ab042a9c90bfe76b59c074e9f3c2`. Changes to the historical qualification module change `runtime_identity()`. A package frozen under this Stable must not be executed under the new candidate Runtime.

Choose **path A**: prepare and review this Draft PR; retain the current Stable; obtain separate human authorization for the frozen package; recheck Runtime, baseline, immutable IDs and Ledger immediately before any authorized execution; execute and reconcile under that original Runtime; then separately approve and release this history fix. New packages use the new Runtime. Do not begin another Apply before its predecessor's committed receipt has been reconciled and registered.

Path B is unavailable in the existing package contract: registration is one immutable package per Artifact, and `qualify` validates the already-registered envelope against the current Runtime. There is no independent successor-package qualification/approval API. Do not delete its registry entry, edit Runtime hashes, overwrite envelopes, reseal user decisions or weaken guards to force B. Such a workflow would require separate design and authorization.

Read-only preflight is explicitly distinct from `EXECUTION_NOT_AUTHORIZED` and `EXECUTION_ELIGIBILITY_NOT_YET_RECHECKED`. No test or preflight result grants execution authority.

## Recovery and rollback

This Draft PR makes no deployment or real data changes. The original Stable wheel, environment, configuration and launchers remain the immediate rollback reference. A later rollback may restore code only; never restore an old database over newer records or delete/reinterpret single-review history. Old code may again refuse historical receipts after later Applies, so use a separately qualified read-only audit rather than weaken execution guards.

If a future authorized transaction fails before commit, retain evidence and establish rollback/baseline state before retrying. If commit may have happened, stop and inspect the existing consumed Grant and receipt; never reset consumption, re-register or repeat inserts. Use the authorized recovery/reconciliation path under its original Runtime while that committed Post-State is still current. This change intentionally does not loosen writable `Operator.reconcile`: recovery after later unregistered transitions remains outside scope.

## Reproduction and tests

The new public-safe fixture creates independent source documents and blank native packets against each preceding Canonical baseline, then uses real Native/Attribution seals, qualification, Operator registration, atomic execute and reconciliation on disposable databases. It does not forge successful receipt hashes. The original version succeeds for receipts 1 and 2 individually but raises `RECOVERY_REQUIRED` when rereading receipt 1 after Apply 2.

Run `tests/test_operational_history_continuity.py` for two/three transactions, restart/idempotent reads, Runtime upgrade, missing evidence, rehashed receipt/envelope tampering, forged skipped transition, current object/source drift and post-commit recovery. Related coverage is in `test_historical_operational_read.py` (opt-in private isolated snapshot), `test_workbench_stage2.py`, `test_workbench_stage2_guards.py`, `test_single_model_review.py`, `test_candidate_advice_submission.py`, and `test_evidence_binding.py`. Private snapshots and deployment-specific receipts stay outside Git.
