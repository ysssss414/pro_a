# Phase 3F Stage 1 — Operational Review Completion Contract

Status: **INPUT PACKET READY; HUMAN COMPLETION REQUIRED**

Stage: `PHASE3F_STAGE1_REVIEW_COMPLETION_INPUT_GATE`

This is an input and authorization-preparation gate. It does not implement the
Phase 3E-to-Phase 3D handoff, make review decisions, authorize a payload, or
authorize Production.

## 1. Exact review universe

The authoritative packet is
`workspace/phase3f_stage1_review_completion/operational_review_packet.json`.
It is bound to:

```text
RUN_ID = INGEST_2644CBDB2693D5E0
SOURCE_ID = SRC_1D42C19206AE3622
SOURCE_SHA256 = 2644cbdb2693d5e0ed3b9f13761123e268bfeae76ad1ebb04bb89416cba44c85
PRODUCTION_SHA256 = 3c0007f38b136686cb1e0e73e2ad2f389983f61ae2c81679fcf5067835c4eba0
```

The packet binds the exact file and semantic hashes of the operational run
manifest, Evidence-bound extraction bundle, Claim review, Node-operation
review, non-executable promotion preview, and frozen Source PDF. The packet is
stale if any of those inputs changes.

The decision rows are:

```text
CLAIMS_REQUIRING_DECISION = 121
NODES_REQUIRING_DECISION = 77
ALIASES_REQUIRING_DECISION = 0
RELATIONS_REQUIRING_DECISION = 7
TOTAL_OPERATIONAL_DECISIONS_REQUIRED = 205
```

The seven Relation rows are the actual separately governed parent-placement
suggestions in the Phase 3E preview. Ninety-seven proposed aliases are frozen
inside their Node candidates and are not separate decision rows. A Node
`CREATE` decision accepts that exact immutable identity and alias set; if it is
not acceptable, the reviewer must choose `DEFER` or `REJECT`. The 31 Phase 3E
non-structural Relation observations are already validation-rejected,
audit-only, and excluded from this human decision universe.

S-L6 evaluation gold is intentionally omitted. It is not operational
authorization.

## 2. Human-editable fields

Only these JSON fields may be edited:

1. `human_completion.reviewer` — required non-empty human reviewer identifier;
2. every Claim record's `human_input.decision` and `human_input.reason`;
3. every Node record's `human_input.decision`, `human_input.reason`, and, only
   for `REUSE`, `human_input.target_node_id`; and
4. every parent-placement record's `human_input.decision` and
   `human_input.reason`.

Whitespace-only or padded values are invalid. No field may be added, removed,
renamed, or edited outside these locations, and no decision-record array may be
reordered. JSON object-key order is immaterial. In particular, the run, Source,
Production baseline, artifact hashes, candidate IDs, candidate content,
Evidence, provenance, advisory recommendations, collision diagnostics, allowed
values, packet ID, and immutable packet hash are immutable.

The Markdown view at
`workspace/phase3f_stage1_review_completion/operational_review_view.md` is for
reading only. Editing it does not complete the authoritative packet.

## 3. Allowed decisions

### Claim

Allowed values are the existing Phase 3C Claim review vocabulary:

| Decision | Phase 3F promotion effect | Required additional input |
|---|---|---|
| `KEEP` | Promotion-authorizing only after all later Evidence, provenance, handoff, and Phase 3D validation gates pass | Non-empty reason |
| `DROP` | Non-promotable | Non-empty reason |
| `KEEP_NEEDS_REVIEW` | Deferred and non-promotable in this handoff attempt | Non-empty reason |

An advisory `KEEP`, `DROP`, or `REVIEW` value in the frozen Phase 3E artifact is
not a human decision and is not copied into the editable field.

### Node

Allowed values are the accepted Phase 3D human Node-operation vocabulary:

| Decision | Phase 3F promotion effect | Required additional input |
|---|---|---|
| `CREATE` | Promotion-authorizing only after later Claim-support and Phase 3D collision checks pass | Non-empty reason; frozen prospective Node ID and exact aliases must remain collision-free |
| `REUSE` | Promotion-authorizing only for the exact unique active compatible frozen target | Non-empty reason and exact `target_node_id` |
| `DEFER` | Deferred and non-promotable | Non-empty reason; target must remain blank |
| `REJECT` | Non-promotable | Non-empty reason; target must remain blank |

For `REUSE`, `target_node_id` must equal the sole
`exact_production_resolution.candidate_target_node_ids` value frozen in that
record. The validator never fuzzy-matches, remaps, or invents a target. A
non-`REUSE` decision with a target is invalid.

### Parent-placement Relation

Allowed values use the existing Phase 3D structural operation vocabulary that
is applicable to these new `part_of` suggestions:

| Decision | Phase 3F promotion effect | Required additional input |
|---|---|---|
| `CREATE` | Promotion-authorizing only if the linked Node decision is also `CREATE` | Non-empty reason; immutable child and parent endpoints |
| `DEFER` | Deferred and non-promotable | Non-empty reason |
| `REJECT` | Non-promotable | Non-empty reason |

`REUSE` is not an allowed value for these seven records because the frozen
surface provides prospective child Nodes and no exact existing Relation target
or Relation ID. No non-structural Relation is reopened.

## 4. Completion validation

The deterministic validator checks packet structure, duplicate JSON keys,
schema and packet identity, exact frozen artifact hashes, candidate universe,
candidate IDs, all immutable fields, allowed decision values, reasons, Node
reuse targets, CREATE collision diagnostics, parent-placement endpoint shape,
and full decision completeness. It does not decide whether semantic content is
correct and never generates a missing decision.

Run the blank-packet check before review:

```powershell
python scripts/phase3f_review_completion.py validate-blank
```

After an identified human reviewer has completed all 205 decision rows, run:

```powershell
python scripts/phase3f_review_completion.py validate-completed
```

Use the repository's available Python executable if `python` is not on `PATH`.
Successful completed validation returns a deterministic completion hash and
decision counts. The result remains non-executable and explicitly sets
`production_apply_authorized` to false.

## 5. Fail-closed invalidation rules

Validation fails if any of the following occurs:

- a mandatory decision, reason, or reviewer is blank;
- a decision is unknown or is valid only for a different candidate type;
- a Node `REUSE` target is absent, malformed, non-unique, or differs from the
  exact frozen target;
- a target is supplied for any non-`REUSE` Node decision;
- a Node `CREATE` uses an invalid prospective ID or frozen collision
  diagnostics already show a collision;
- a parent-placement `CREATE` is paired with a linked Node decision other than
  `CREATE`, has a malformed endpoint, or is a self-loop;
- a candidate ID is malformed, duplicated, absent from, or added to the frozen
  candidate universe;
- immutable candidate content, Evidence, provenance, allowed decisions,
  summaries, or safety flags are altered;
- packet, run, Source, review, or artifact identities disagree;
- any authoritative input file hash/size differs from the run manifest or the
  packet binding;
- an input decision is copied from another candidate or run by changing
  immutable identity fields; or
- an extra/missing field or duplicate JSON key is present.

Evaluation gold, extraction success, recommendations, and empty decisions are
never approval. The validator has no LLM, database-write, migration, shadow
apply, Production apply, or review-generation behavior.

## 6. Next action

`NEXT_REQUIRED_ACTION = HUMAN_COMPLETION_OF_OPERATIONAL_REVIEW_PACKET`

Do not repeat Stage 1 handoff qualification until a human supplies all required
operational decisions and the completed packet passes this validator.
