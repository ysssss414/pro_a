# R1 Relation Baseline Acceptance

## Completion status — 2026-08-24

R1 and the Phase 1 follow-on acceptance sequence are complete and frozen. The final release decision is `PASS_WITH_RELATION_BACKLOG`; run_007 passed without a new systemic safety blocker, and Operational Acceptance verified Source / Claim / Node review plus controlled staging maintenance. Relation validation remains operational while Relation Candidate generation remains backlog.

Final pointers:

- `docs/PHASE1_FREEZE.md`
- `workspace/r1_acceptance/run_007/RUN_007_RESULT.json`
- `workspace/r1_acceptance/phase1_operational_acceptance_20260824_attempt_003/PHASE1_OPERATIONAL_ACCEPTANCE.json`

The specification below is retained unchanged as the historical R1 evaluation contract.

Status: **acceptance specification**

This document defines how to evaluate the post-v0.2.3B.1 Relation Candidate pipeline on real research material. It does not change frozen business rules.

## Purpose

R1 answers one question:

> Can the current Relation Candidate → Evidence Validation → Proposal pipeline be trusted on real materials without silently formalizing unsupported knowledge?

R1 is an acceptance exercise, not a development loop. Do not tune heuristics while evaluating the baseline.

## Baseline under test

```text
Source
→ Claim
→ Relation Candidate
→ supporting Claim resolution
→ atomic Claim / Evidence validation
→ semantic validation
→ direction validation
→ pending Relation Proposal
```

No R1 run may automatically accept a Proposal or create a formal non-structural Relation.

## Isolation requirements

R1 must use an isolated workspace and temporary database.

Forbidden during acceptance:

- modify the production `pro_a.db`;
- modify formal Current Views;
- formally create Nodes or Relations;
- accept pending Proposals;
- trigger production Propagation / Impact Recovery side effects;
- enable IMA;
- modify R1 raw source files.

## Dataset inventory

Before running the baseline, record:

- number of files;
- file types;
- approximate text volume;
- Chinese / English mix;
- source-type mix such as filings, research reports, expert notes, company communications and industry material;
- major research domains represented;
- whether tables, figures or other parser-sensitive content are material to the sample.

Prefer full-corpus execution when practical. If sampling is required, use a reproducible stratified sample and document the selection rule.

## Gold Set

A human Gold Set should be created independently of pro_a output for a representative subset of the R1 corpus.

Each expected relation record should contain at least:

- source identifier;
- evidence excerpt;
- expected atomic Claim, when relevant;
- expected `from_node`;
- expected `relation_type`;
- expected `to_node`;
- expected scope;
- expected direction;
- whether a Proposal should be created;
- whether conservative rejection is acceptable;
- notes on ambiguity.

The Gold Set is the reference for measuring both precision and recall.

## Candidate-level audit table

For every generated or materially expected relation, capture:

| Field | Description |
|---|---|
| source | Source identifier / filename |
| evidence | Evidence excerpt |
| claim | Supporting atomic Claim |
| from_node | Candidate source endpoint |
| relation_type | Candidate Relation type |
| to_node | Candidate target endpoint |
| scope | Candidate scope |
| validator_result | accepted / rejected |
| reject_reason | Program reject reason |
| supporting_claim_ids | Persistent Evidence Claims |
| manual_assessment | PASS / FALSE_POSITIVE / FALSE_NEGATIVE / CONSERVATIVE_REJECT / AMBIGUOUS |
| error_class | Pipeline-stage attribution |
| notes | Human notes |

## Manual assessment classes

### PASS

The system behavior matches the human Gold Set and Evidence supports the resulting Proposal.

### FALSE_POSITIVE

The system creates or accepts a candidate that the Evidence does not support, or represents the wrong endpoints / relation / direction / scope.

### FALSE_NEGATIVE

A clear, useful and structurally valid relation exists in the material, but no valid Proposal is produced.

### CONSERVATIVE_REJECT

The material carries some relation meaning, but the current validator rejects it because the syntax, attribution or endpoint structure is too complex to determine safely. The rejection is safe even if recall suffers.

### AMBIGUOUS

A human reviewer cannot uniquely determine the intended formal relation from the available Evidence alone.

## Hard Failures

Any Hard Failure reopens B.1.

### H1 — reversed direction accepted

A directional Relation is accepted in the opposite direction from the Evidence.

### H2 — unsupported Evidence accepted

`supporting_claim_ids` point to Claims that do not actually support the Relation.

### H3 — wrong atomic child mapping

After Claim splitting, the Relation is mapped to the wrong child Claim.

### H4 — unresolved/internal Claim reference leakage

Temporary or internal resolution data such as unresolved refs, `supporting_claim_refs`, or `_resolved_supporting_claim_indices` enters the Proposal payload.

### H5 — business text mutation

Legitimate source text such as `C1`, `C2`, stepping names, product generations or other identifiers is rewritten or stripped from Relation scope / reason.

### H6 — Proposal identity collision

Different scopes or otherwise distinct Relation Proposals are incorrectly merged as one identity.

### H7 — endpoint mismatch accepted

The formalized endpoints are not the entities supported by the Evidence.

### H8 — negated relation accepted

A negated or explicitly absent relation is accepted as a positive relation.

### H9 — unsafe relation-type substitution

The Evidence supports one relation type but the system accepts a materially different relation type that changes knowledge meaning.

### H10 — acceptance environment contamination

R1 modifies the production database, production Relations / Current Views, R1 raw source files, or enables IMA.

## Reject reason attribution

A rejected candidate must be attributed to the correct stage whenever possible:

A. correct safe rejection;
B. conservative but safe rejection;
C. Relation validator defect;
D. upstream LLM candidate defect;
E. endpoint / Node match defect;
F. Claim extraction / atomicity defect;
G. parser / Evidence extraction defect;
H. ontology ambiguity.

Do not treat every rejection as a validator problem.

## Missing relation analysis

For clear expected relations, identify where the loss occurs:

```text
Source → Claim not extracted
Claim → Relation Candidate not proposed
Candidate endpoint not matched
Candidate rejected by validator
Proposal identity / persistence issue
Other
```

Initial focus relation types:

- `part_of`
- `upstream_of`
- `supplies`
- `produces`
- `uses`
- `applied_in`
- `substitutes`
- `regulated_by`

## Acceptance decision

### Runtime Validity Gate

Runtime Validity answers whether the measurement infrastructure and execution are
trustworthy. It does not grade whether model output is semantically correct.

Terminal, fully audited semantic failures remain scoreable. These include Relation
Candidate and Node Match rejection, zero valid Relations, and Impact validation
failure after all configured repair rounds have actually executed. Attribution,
Evidence, direction, unsupported-entity and required-field failures are semantic
measurement outcomes when they have an explicit terminal state.

Runtime Validity fails only when execution cannot reliably determine the model
outcome, including transport exhaustion, parser/runtime crash, unresolved retry,
missing audit or raw observability, code drift, Gold leakage, database or Source
mutation, persistence/state-machine failure, or another unclassified execution
failure. A configured recovery path that did not actually execute is also an
infrastructure blocker.

This classification does not reduce Relation, Evidence or Impact validation rules,
and does not increase the configured number of repair rounds.

### REOPEN B.1

If **Hard Failure > 0**.

Required output:

- minimal reproducible case for each Hard Failure class;
- pipeline-stage attribution;
- no implementation fix during the baseline run.

### B.1 PASS with B.2 backlog

If Hard Failure = 0 but there are meaningful recall, language coverage, endpoint matching, ontology or conservative rejection issues.

These issues become B.2 backlog candidates.

### B.1 PASS — baseline accepted

If Hard Failure = 0 and no material quality problem is observed beyond acceptable conservative loss.

## Reporting

The final R1 report should contain:

1. corpus inventory;
2. full-corpus vs sampling rule;
3. Sources processed;
4. Claims extracted;
5. Relation Candidates generated;
6. candidates accepted / rejected;
7. pending Proposals generated;
8. reject reason distribution;
9. PASS / FP / FN / Conservative Reject / Ambiguous counts;
10. Hard Failure count and detailed cases;
11. false-positive case list;
12. false-negative case list;
13. conservative-rejection case list;
14. error attribution by pipeline stage;
15. decision: `B.1 PASS` or `REOPEN B.1`;
16. candidate B.2 backlog;
17. confirmation that production DB / IMA / R1 source files were untouched.

## Priority principle

**Safety errors dominate coverage errors.**

A wrong relation that can enter the Canonical Knowledge Engine is a blocker. A complex but valid relation that is conservatively rejected is a coverage problem and, absent other failures, belongs in B.2.
