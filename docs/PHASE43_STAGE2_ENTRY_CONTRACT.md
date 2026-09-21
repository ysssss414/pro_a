# Phase 4.3 Stage 2 Entry Contract

## Identity

- Stage: **Phase 4.3 Stage 2**
- Name: **SEMICONDUCTOR_FOUNDATION_INGESTION**
- Entry branch: `codex/phase43-stage2-semiconductor-foundation-ingestion`
- Frozen predecessor baseline: `8e07cc2b7270ac08cb4166b5f62b4dc76f396f35`
- Predecessor closure: PR #63, Phase 4.3 Stage 1 `OPERATOR_SCALE_AND_BOUNDED_PIPELINE`
- Entry date: 2026-09-21

## Objective

Run the first real semiconductor Foundation ingestion on the Phase 4.3 shared-core architecture using the semiconductor domain pack, while preserving one canonical Source / Node / Claim / Relation identity model across domains.

Stage 2 is intended to prove that the multi-domain operating foundation built in Stages 0-1 can process a real semiconductor Foundation corpus without introducing a semiconductor-only parallel data model.

## Planned input boundary

The intended corpus is the previously prepared semiconductor Foundation backfill set (`semiconductor_foundation_backfill_web_pro_v1`, 17 documents plus its qualification/receipt material). Raw/private corpus bytes remain outside the public repository unless already represented by an approved public projection.

## Required semantic behavior

- Reuse the shared core and declarative semiconductor domain pack.
- Preserve canonical Node / Source / Claim identity across industries.
- Reuse existing entity-resolution operations: `REUSE`, `CREATE`, `REVIEW`, `DEFER`, `REJECT`.
- Allow cross-industry reuse of an existing canonical Node when identity is the same.
- Preserve evidence binding and source provenance.
- Route ambiguous identity, relation, evidence, and low-confidence cases through the Stage 1 Review Workbench / bounded review controls.
- Freeze effective pack, prompt, runtime, configuration, and model identity for each real run.

## Carry-forward operating constraints

Stage 1 bounded-operator controls remain authoritative unless Stage 2 explicitly re-qualifies a limit:

- one Source per run;
- no more than three runs per rolling 24 hours;
- review page 25 default / 100 maximum;
- pending WIP soft warning above 100 and hard stop above 200;
- semantic parent cap 8 plus token bound;
- no more than 31 durable jobs per Source run;
- single worker concurrency.

## Hard boundaries

- Cloud-only; no local-model dependency.
- No Production apply or Production mutation.
- No silent schema or ontology extension.
- No rewriting of Stage 0/1 frozen evidence.
- No hidden holdout / qualification truth used during ordinary execution.
- No raw/private corpus material committed merely to make Stage 2 runnable.
- No Stage 3 work.

## Entry status

```text
PHASE43_STAGE2_ENTRY_OPEN = true
STAGE1_FROZEN_BASELINE_MATCH = true
STAGE2_IMPLEMENTATION_STARTED = false
STAGE2_REAL_INGESTION_EXECUTED = false
PRODUCTION_APPLY_AUTHORIZED = false
STAGE3_STARTED = false
```

The next Stage 2 action is to freeze the exact real-corpus admission/qualification contract and acceptance gates against this entry baseline before the first real semiconductor Foundation ingestion.
