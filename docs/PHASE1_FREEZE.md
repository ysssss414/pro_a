# Phase 1 Freeze / Release Closure

- Freeze date: **2026-08-24**
- Release version: **0.3.0**
- Intended tag: **v0.3.0** (not created)
- Final code commit: **PENDING — represented by the `freeze Phase 1 baseline` release commit and Draft PR; no post-commit file mutation**

## Frozen capability

The Phase 1 local canonical knowledge workflow is operational for:

```text
Source
→ evidence-backed Claim
→ Existing Node Match / Candidate Node
→ human review artifacts
→ explicitly approved, controlled DB maintenance
```

The maintenance contract was verified on an isolated Production copy: backup, apply, receipt, idempotent rerun and exact rollback all passed. Production was not written during run_007, Operational Acceptance or this freeze closure.

## Production baseline

- Absolute path at freeze: `D:\ej\材料\codex\get_knowledge\pro_a_v0_1\workspace\pro_a.db`
- SHA-256: `8bce2b47df971e527de3552ca0415160868b258c0fcd4a8f6d2f20f40a60541c`
- Nodes: 280
- Aliases: 706
- Node Relations: 177
- Current `part_of`: 170
- Retired R1 migrations: 7
- Freeze backup: `workspace/r1_acceptance/phase1_freeze_20260824/backup/pro_a_phase1_freeze_8bce2b47df971e52.db`
- Freeze backup SHA-256: `8bce2b47df971e527de3552ca0415160868b258c0fcd4a8f6d2f20f40a60541c`

The earlier pre-B.2C Production recovery backup remains beside the B.2C import receipt; a byte-identical redundant root copy was removed from active paths.

## Final acceptance evidence

### run_007

- Sources/cases terminal: 10/10
- API calls: 119
- Claims: 626; evidence-valid Claims: 560
- direct Node Matches: 61; rejected matches: 437
- legal / rejected Relation Candidates: 0 / 95
- Gold accepted / false-positive / expected: 0 / 0 / 130
- AF-007 source terminal rejection: absent; fix effective
- Decision: `RUN_007_PASS = true`

Pointers:

- `workspace/r1_acceptance/run_007/RUN_007_RESULT.json`
- `workspace/r1_acceptance/run_007/RUN_007_PHASE1_GATE.md`

### Operational Acceptance

- Materials completed: 3/3
- Claims: 163; evidence-valid: 155
- Manual Claim sample: 12/12 usable and evidence-backed
- Direct Existing Node Matches: 17; obvious identity errors: 0
- New Node proposals: 5 ResearchQuestions
- Staging change: `PCB层数增长趋势`
- Staging backup/apply/receipt/idempotency/rollback: PASS
- Production writes: 0
- Decision: `PASS_WITH_RELATION_BACKLOG`

Pointers:

- `workspace/r1_acceptance/phase1_operational_acceptance_20260824_attempt_003/PHASE1_OPERATIONAL_ACCEPTANCE.json`
- `workspace/r1_acceptance/phase1_operational_acceptance_20260824_attempt_003/PHASE1_FINAL_GATE.md`
- `workspace/r1_acceptance/phase1_operational_acceptance_20260824_attempt_003/STAGING_MAINTENANCE_SIMULATION.json`
- `workspace/r1_acceptance/phase1_operational_acceptance_20260824_attempt_003/staging_maintenance_backup/accepted_receipt_PROP_20260824_BF5EF1AE.md`

`PHASE1_FINAL_GATE.md` SHA-256: `22ad5683c2bfe612a9f356d362da29277b20a1e767b6eed497056d8375d6eb6e`

### Earlier closure chain

- run_006 baseline: `workspace/r1_acceptance/run_006/`
- B.2C Production import receipt and recovery backup: `workspace/r1_acceptance/b2c_production_import_20260819/`
- B.2C final qualified inventory/package: `pro_a_r1_node_import_package_B2C_FINAL_QUALIFIED_20260819/`
- B.2D diagnosis: `workspace/r1_acceptance/b2d_resolved_positive_recall_preparation_20260819/`
- B.2E decision: `workspace/r1_acceptance/b2e_deterministic_recall_recovery_20260819/`
- B.2E.1 decision: `workspace/r1_acceptance/b2e1_controlled_model_experiments_20260824/`
- B.2F final regression: `workspace/r1_acceptance/b2f_phase1_final_regression_20260824/`

## Capability boundary and backlog

Relation-specific Evidence, semantic validation, direction validation, safe rejection and Proposal hygiene are operational. Relation Candidate generation is not yet operationally reliable: both preselected exact-endpoint/evidence Operational probes failed to produce a legal candidate.

`RELATION_EXTRACTION_OPERATIONAL_READY = false`

Known model-quality and contract-constrained false negatives remain documented backlog. They do not permit fuzzy linking, evidence-free association, Gold-specific hardcode, type guessing or validator weakening.

## Frozen rules and integrations

- `docs/REQUIREMENTS_FROZEN.md`: unchanged.
- Evidence, direction, existing-node, collision and Metric Node Type contracts: unchanged.
- `docs/RELATION_SEMANTICS.md`: no ontology change in this closure.
- `docs/IMA_INTEGRATION.md`: unchanged; IMA remains off.
- Gold and run_006 frozen inputs: unchanged.
- Phase 1 closure LLM/API calls: 0.
- Phase 1 closure IMA calls: 0.

## Next milestone

Phase 1.1 / Expanded Knowledge Universe / R2 is a future candidate milestone and **has not started**. It requires separate user authorization.
