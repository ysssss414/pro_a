# Phase 3C Correctness & Generalization Closure

Status: **CORRECTNESS / GENERALIZATION COMPLETE — Production apply not authorized**

Decision date: `2026-09-02`

## Final decision

```text
PHASE3C_GENERALIZATION_GATE = PASS
PHASE3C_CORRECTNESS_COMPLETE = true

PILOT6_SEMANTIC_GATE = PASS
PILOT6_REVIEW_AUTHORITY = USER_DELEGATED_AI_REVIEW

PILOT6_REVIEW_DENOMINATOR = 104
PILOT6_KEEP = 104
PILOT6_DROP = 0
PILOT6_TRUE_SEMANTIC_FAILURES = 0
PILOT6_TRUE_SEMANTIC_FAILURE_RATE = 0.00%
PILOT6_ATTRIBUTION_ERROR = 0

PHASE3C_COMPLETE = true
PRODUCTION_APPLY_READY = NO

PHASE3C_NEXT_GATE =
Production Path Promotion / Apply Readiness
```

The frozen semantic acceptance contract was:

```text
true semantic failure rate <= 10.00%
ATTRIBUTION_ERROR = 0
```

Pilot #6 satisfies both criteria.

## Review authority

The project owner explicitly delegated the final Pilot #6 semantic judgment to ChatGPT on `2026-09-02`.

This closure records:

```text
reviewer = ChatGPT GPT-5.6 Sol
reviewer_mode = USER_DELEGATED_AI_REVIEW
human_review_executed = false
```

This must not be represented as a human review. The delegated reviewer decision is the project owner's chosen governance authority for this gate.

The claim-level receipt is stored at:

- `artifacts/phase3c/pilot6_delegated_reviewer_signoff.json`
- `artifacts/phase3c/pilot6_delegated_reviewer_signoff.md`

## Independent Pilot #6

Pilot run:

```text
PILOT_20260902_572A6DF2
```

Independent Source SHA-256:

```text
572a6df2b583358506e2a4fb86359a07e9a1503a3507dcdd2c81a8d97c27e97a
```

Final pre-review gates:

```text
PILOT6_SOURCE_INDEPENDENCE_GATE = PASS

PILOT6_TABLE_SUPPRESSION_RUNTIME_GATE = PASS
PILOT6_TABLE_CLAIM_SAFETY_GATE = PASS

PILOT6_EVIDENCE_ARTIFACT_GATE = PASS
PILOT6_MECHANICAL_GATE = PASS
```

Population:

```text
RAW_EXTRACTED_CLAIMS = 107
TABLE_DERIVED_CLAIM_INELIGIBLE = 3
REVIEW_ELIGIBLE_CLAIMS = 104
```

Mechanical quality:

```text
Quote fidelity = 89.42%
Quote drift    = 9.62%
Source binding = 89.42%
```

Safety invariants:

```text
FALSE_NARRATIVE_SUPPRESSION_FOUND = NO
UPSTREAM_SUPPRESSION_LEAK_FOUND = NO
FALSE_TABLE_CLAIM_FILTER_FOUND = NO
```

No bounded local-subspan fallback was needed on Pilot #6.

## Frozen Phase 3C behavior

The correctness/generalization closure covers the combined frozen behavior:

1. clean-source semantic extraction contract;
2. Evidence v2;
3. deterministic Source binding;
4. bounded local-subspan repair;
5. canonical `pypdf` Source truth;
6. PyMuPDF structure sidecar;
7. `NARRATIVE_FIRST_TABLE_SUPPRESSION`;
8. precision-first `table / narrative / unknown` eligibility;
9. fail-open protected-layout and canonical-binding behavior;
10. `TABLE_DERIVED_CLAIM_SAFETY_BOUNDARY_V1`;
11. raw Claim / Evidence preservation for excluded table-derived Claims.

No Pilot #7 is required unless these correctness-relevant contracts change.

## Key product decision

Phase 3C established the default ingestion policy:

```text
NARRATIVE_FIRST_TABLE_SUPPRESSION
```

`pro_a` is a knowledge ecosystem rather than a general-purpose financial-table ETL system.

Therefore:

- narrative prose is the default semantic knowledge surface;
- authoritative table regions are excluded before semantic prompt construction where safely possible;
- raw tables and provenance remain preserved;
- pure table-derived Claims are ineligible for the default knowledge path when V1 can establish table origin deterministically;
- unknown / ambiguous cases fail open;
- no numeric-density, financial-keyword, year-column or similar semantic heuristic is used.

## Pilot progression

### Pilot #3

Noisy transcript corpus exposed a real semantic failure mode and established the noisy-source boundary. No Production write occurred.

### Pilot #4

Clean-source Evidence failures led to the bounded local-subspan repair. Mechanical repair passed, but table-heavy Claim extraction exposed a product misalignment: dense tables created large numbers of low-value Claims and table semantic errors.

### Table suppression

The Pilot #4 counterfactual classified `198 / 320` Claims as table-derived. PyMuPDF was accepted as a precision-first structural signal. The runtime implementation preserved canonical `pypdf` Source text and filtered only authoritative table spans before chunking/prompt construction.

### Pilot #5

Independent clean Source validated upstream table suppression and Evidence generalization, but a canonical-binding fail-open dense financial table produced nine table-derived Claims. This became the design corpus for `TABLE_DERIVED_CLAIM_SAFETY_BOUNDARY_V1`.

The V1 replay selected exactly the nine diagnostic table Claims and zero of the other 41 Claims.

### Pilot #6

A new independent 28-page broker research PDF exercised a different layout, dense financial tables, prose-like tables, multiple attribution sources and substantially larger Source length.

All mechanical, structure, safety and isolation gates passed. The final delegated semantic review accepted all 104 review-eligible Claims with zero attribution errors.

## Source-level review note

The Pilot #6 Source contains one internal numeric inconsistency:

- narrative: 2025 net-profit YoY growth `25.5%`;
- financial indicator table: `25.3%`.

The reviewed eligible Claim binds to the narrative value. This is classified as:

```text
SOURCE_INTERNAL_NUMERIC_INCONSISTENCY
```

not an extraction semantic failure.

## Production isolation

Across the Phase 3C acceptance work, the canonical Production database remained isolated.

Final observed Production SHA-256:

```text
581978e1c587b065a6eef9c980013af3de1a9e8a8781857385404c9f61105250
```

Final checks reported:

```text
integrity = ok
FK violations = 0
Production DB changed = NO
IMA = NO
Propagation = NO
Legacy ingestion = NO
```

Correctness closure does **not** grant Production apply authority.

## Next gate

The next stage is deliberately separate from correctness/generalization:

```text
Production Path Promotion / Apply Readiness
```

That stage should determine how the Phase 3C clean-source path is promoted into the normal controlled ingestion path, including:

- exact runtime-path promotion boundary;
- dependency/license deployment check for PyMuPDF;
- Production preconditions;
- dry-run / preview;
- backup + transaction + receipt requirements;
- canonical write eligibility;
- post-write QA;
- explicit human/user authorization before any live Production mutation.

Until that gate passes:

```text
PRODUCTION_APPLY_READY = NO
LIVE_PRODUCTION_APPLY_AUTHORIZED = false
```

## GitHub remote synchronization note

At the time this governance closure was prepared, GitHub `main` was still at:

```text
bf86a50bffa53b7fd210bb9b4b751e3f5737e8e3
```

which is the Phase 3B merge baseline. The remote default branch did not yet contain the local Phase 3C implementation; for example its `pyproject.toml` still lacked the accepted PyMuPDF runtime dependencies and no Phase 3C source files were indexed.

Therefore this governance change must **not be merged to `main` ahead of the actual Phase 3C implementation history**.

Required repository sequence:

1. push/sync the local accepted Phase 3C implementation and tests;
2. rebase this closure/governance branch onto that implementation head;
3. verify the closure receipts and implementation hashes;
4. update README / ROADMAP / CHANGELOG to Phase 3C complete;
5. merge only after repository code and closure documentation describe the same state.

This note prevents documentation from claiming capabilities that the remote code does not yet contain.
