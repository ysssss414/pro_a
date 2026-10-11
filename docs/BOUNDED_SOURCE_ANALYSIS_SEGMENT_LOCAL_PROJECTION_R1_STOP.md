# BOUNDED_SOURCE_ANALYSIS_SEGMENT_LOCAL_PROJECTION_R1 — STOP

`BLOCKER = SEGMENT_BOUNDARY_SEMANTIC_LOSS`

The required boundary-sensitive qualification fails before implementation.
Strict local input and unchanged ordinal segmentation/aggregation cannot preserve
the synthetic canonical truth below. User instructions sections 32, 33 and 42
explicitly require STOP. No production code, prompt, validator, planner, schema,
runtime guard or stable installation changed.

## Reproducible evidence

Diagnostic commit: `9c58aa16d578af31d28c468cafe6d2cb1ce01cd5`.

`tests/test_segment_local_semantic_boundary.py`: **4 passed in 2.17 seconds**.
These tests pass by reproducing the blocker; they do not qualify a new provider
projection. All text, Nodes and canonical truth are synthetic. Network requests
and model calls are forbidden in the fixture.

The tests use the unchanged native SourcePiece planner, Evidence catalog, default
16-ref Segment planner, subdivision, Node scoping, Wire expansion, coverage,
aggregation and native output validator. The local-input audit oracle implements
only the requested exact first-unit-start / last-unit-end interval and existing
`scope_node_catalog` filter; it is not a shipped prompt renderer.

The critical adjacent sentences share a paragraph, locator and Evidence block:

```
以下产能数据仅指青松公司。
该公司现有产能为100台。
```

The explicitly defined whole-piece truth is “青松公司现有产能为100台。” Resolving
the sole antecedent uses immediately adjacent Source discourse, not external
knowledge. A paired source changes only the company to “白杨公司”; its truth must
identify that other company. Both complete-source canonical fixtures pass the
unchanged Wire expansion and native validation with exact measurement Evidence.

| Diagnostic | Observed result |
| --- | --- |
| Both sentences in one 16-ref Segment | Local input retains company and measurement, Node subset retains company, and aggregate/native Claim values match truth. |
| Sentences at refs 16 / 17 | Default leaves are 16 / 1. First has company but no measurement; second has measurement but no company and an empty Node subset. |
| Sentences at refs 8 / 9 of a 16-ref parent | Parent has both. Unchanged 8 / 8 subdivision separates the necessary subject context. |
| Unresolved-subject output | Context-only dispositions can close coverage while omitting the expected Claim. Keeping “该公司” instead remains unresolved after aggregation/native validation and changes permanent Claim identity. |

In the paired sources, the second Segment's semantic text and Node subset are
identical while required company-specific truths differ. Source/Series/Segment/
Evidence hashes differ: this is **not** a claim that request bytes are identical.
Opaque hashes are provenance, not permitted company-name context. Neither leaf
has the complete subject-plus-measurement information. The existing aggregator
concatenates Claims; native replay validates supplied Claims without rewriting
their subject from other Segment content.

This is a structural counterexample to canonical equivalence, not a live model
experiment. No claim is made that this dependency was measured in the private
real Source. The requested synthetic correctness gate already fails.

## Run 8 and current release

Main/stable remains `6e1135c4371a6a3d1b6a491a433576b3eda9efbe`, schema 12.
Existing `segment_payload` still sends the full annotated SourcePiece and frozen
piece-scoped Node catalog:

`ROOT_CAUSE = FULL_SOURCEPIECE_VISIBLE_TO_EACH_SEGMENT`

Run 8 raw replay remains rejected, without acceptance or mutation:

- Invalid role occurrences: **5**, one distinct value (public classification only).
- Out-of-Segment Evidence bindings: **47** (44 Claims, 3 Node matches).
- Distinct out-of-Segment Evidence refs: **45**.
- `RUN8_RAW_RESPONSE_STILL_REJECTED = true`.

Before/after real-state snapshots are byte-identical. Run 8 remains
`BLOCKED / BOUNDED_EXTRACTION_FAILED`; prompt/raw artifacts and frozen identities
are unchanged. Runs 1–7, all 14 historical queued jobs, Production and Current View
remain exact. No new provider liability, decisions, promotion, Semantic jobs or
Review Packet were created.

## Release gates

`BOUNDED_SOURCE_ANALYSIS_SEGMENT_LOCAL_PROJECTION_R1 = STOP`

`WIRE_VALIDATOR_RELAXED = false`

`AUTOMATIC_OUTPUT_REPAIR = false`

`RUN8_MUTATED = false`

`PROVIDER_CALLS = 0` (this stage; Run 8 lifetime remains 1)

`RUN9_CREATED = false`

`SEGMENT_LOCAL_PROJECTION_RELEASED = false`

`AUTHORIZATION_REQUIRED_FOR_LIVE_RUN9 = true`

Prompt remains v1. Production projection implementation, role constant extraction,
prompt v2, 27 real Segment v2 metrics, foreign-Evidence/Node absence qualification,
full regression matrix, compile/build/wheel qualification, merge and deployment
are **NOT RUN** after mandatory STOP. The Draft PR contains only diagnostic tests
and sanitized evidence. No new implementation SHA or wheel SHA is claimed.

## Minimum next scope

Define and qualify segmentation/ownership or cross-Segment synthesis that
preserves adjacent Source-local dependencies before retrying strict projection.
Both initial grouping and subdivision need a defined treatment. Semantic grouping,
deterministic overlap ownership and post-Segment synthesis require separate
evaluation; none is selected or implemented here. No halo, foreign Evidence
exposure, validator relaxation, retry, Run 8 rewrite or schema13 was introduced.
Run 9 is not ready solely upon authorization: this correctness blocker must first
be resolved and the replacement contract qualified.
