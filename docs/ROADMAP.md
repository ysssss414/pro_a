# pro_a Roadmap — post-v0.2.3B.1

Status: **working roadmap**

This roadmap organizes the next work after the Relation Candidate baseline. It does not modify frozen business rules.

## Current milestone

### Milestone R1 — Relation Baseline Acceptance

Goal: validate the current Relation Candidate pipeline on real research materials before adding more heuristics or widening recall.

Required sequence:

```text
B.1 freeze
→ build human Gold Set
→ run R1 baseline in isolated workspace
→ candidate-level audit
→ pipeline-stage error attribution
→ B.1 PASS / REOPEN decision
→ derive B.2 backlog from real failures
```

Acceptance specification: `docs/R1_ACCEPTANCE.md`.

## B.1 frozen baseline

The following capabilities are considered the baseline under test:

- Relation-specific Evidence foundation;
- pending Relation Proposal workflow;
- stale Proposal recovery;
- supporting Claim resolution;
- exact atomic Claim mapping;
- semantic Evidence validation;
- directional active/passive validation;
- rejection audit reasons;
- Proposal payload hygiene;
- scope/reason integrity and Proposal identity preservation.

Do not expand B.1 merely to improve recall unless R1 identifies a Hard Failure or a defect that breaks the safety contract.

## B.2 — to be defined by R1

B.2 is intentionally not frozen in advance.

Candidate workstreams may include:

### Relation ontology

- endpoint type compatibility matrix;
- relation inverse / redundancy rules;
- Product vs Entity granularity;
- planned / qualification / production-state semantics;
- scope identity rules.

### Candidate quality

- LLM candidate recall;
- multilingual / complex syntax coverage;
- candidate duplication / identity;
- confidence calibration.

### Endpoint resolution

- alias ambiguity;
- Product / Technology / Entity disambiguation;
- Evidence-backed endpoint match improvements.

### Claim / Evidence quality

- atomic Claim extraction;
- multi-sentence Evidence disambiguation;
- table / figure Evidence limitations;
- relation-specific Evidence traceability.

### Observability

- reject reason taxonomy;
- acceptance metrics;
- candidate-level audit export;
- reproducible R1 regression corpus.

Only R1-backed issues should be promoted into implementation tasks.

## Other P0 work after Relation acceptance

These remain important but should not interrupt R1 unless explicitly reprioritized:

1. Replayable Standard / Deep LLM analysis jobs with retry and idempotency.
2. Claim semantic deduplication and conflict-candidate retrieval without repeatedly sending large Claim history to the model.
3. Proposal “modify then accept”.
4. Knowledge Gap lifecycle: resolve / reopen / supersede.
5. ResearchQuestion Current Answer update and approval rules.

## P1 / later work

1. More reliable PDF table / chart interpretation.
2. Image multimodal parsing; OCR should not be the default path.
3. Source Updated Version / Near Duplicate detection.
4. Node-specific Materiality Threshold configuration.
5. External web Research Output ingestion.
6. Formal IMA integration acceptance.
7. GUI / higher-level review experience.

## IMA boundary

IMA remains disabled during the current acceptance stage.

IMA is expected to serve as:

- document cloud storage;
- Search / RAG;
- formal research-output carrier.

IMA is not the source of truth for knowledge state. SQLite / pro_a remains the Canonical Knowledge Engine.

## Development decision rule

When deciding whether to change code, use this order:

1. Is there a Hard Failure that can create wrong canonical knowledge?
2. If not, is the issue a safe false negative / conservative rejection?
3. Which pipeline stage actually owns the failure?
4. Is the proposed fix the smallest change at that stage?
5. Does the fix preserve existing frozen rules and safety gates?

Avoid compensating for upstream defects by weakening downstream validation.

## Documentation ownership

- `docs/REQUIREMENTS_FROZEN.md`: frozen business rules; change only with explicit user decision.
- `docs/R1_ACCEPTANCE.md`: R1 evaluation contract.
- `docs/RELATION_SEMANTICS.md`: working ontology notes; not frozen.
- `CODEX_TASK.md`: current engineering continuation brief.
- `CHANGELOG.md`: completed implementation history.
- `README.md`: current system baseline and operating overview.
