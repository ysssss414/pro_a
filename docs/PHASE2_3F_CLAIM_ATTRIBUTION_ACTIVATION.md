# Phase 2.3F — Claim Attribution Semantics & Company Entity Activation

PHASE2_3F_COMPLETE = true
PRODUCTION_WRITE_AUTHORIZED = true
ROLE_SEMANTICS_FROZEN = true
CURRENT_VIEW_CREATED = false

## Outcome

Phase 2.3E showed that eight adjudicated Claims directly assert facts about
`昀冢科技`, while MLCC is their product context. A canonical active Company Node was
therefore required. Phase 2.3F created `NODE_20260826_BC260F3E` with
`primary_type=Company`, no aliases and no inferred company metadata.

The minimal Claim-to-Node vocabulary is now frozen as:

- `subject`: the Node is the Claim's factual subject.
- `context`: the Claim is materially relevant to the Node, but the Node is not its factual subject.
- `related`: legacy/generic association not yet adjudicated as subject or context.

Link existence no longer implies primary subject. Read API Node Claims expose `link_role`, and
the Explorer Claims tab renders Subject, Context or Related from the stored database role.

## Exact authorized Production delta

- Nodes: 293 → 294 (+1 `昀冢科技` Company).
- Aliases: 737 → 737 (+0).
- Claim-to-Node links: 11 → 19 (+8 Company subject links).
- Existing MLCC roles updated: 3 `related → subject`, 8 `related → context`.
- MLCC: 11 total = 3 subject + 8 context.
- `昀冢科技`: 8 total = 8 subject.
- The explicit NO_LINK Claim remains unlinked.

Claims, Sources, Source links, Relations, Current Views, Research Questions and Knowledge Gaps
were not changed. No Company-to-MLCC Relation or Source-to-Node link was created.

## Current View implication

No Current View was created. A future MLCC Current View candidate set should begin with the
three MLCC `role=subject` Claims, not all 11 MLCC-linked Claims. The eight `role=context`
Claims must not be presented as MLCC aggregate facts. The Company has eight subject Claims,
but its Current View also remains a separate future pilot decision.

## Validation and recovery

- Production pre-SHA: `BAD76DED1584AD22B86CCD8C19B1D6205B048C30103E71BB3E3E800F1F802D54`
- Backup: `workspace\backups\pro_a_pre_phase2_3f_20260826_161932_225472.db`
- Backup SHA: `BAD76DED1584AD22B86CCD8C19B1D6205B048C30103E71BB3E3E800F1F802D54`
- Production post-SHA: `83A109D22EF08D5A230F28A341EF67CC0CA6FF5014BE7E89D7E2AB4DE8CAF895`
- Integrity check: `ok`
- Foreign-key violations: `0`
- Preserved tables changed: `false`
- Knowledge levels: `{"LEVEL_0_STRUCTURE_ONLY": 289, "LEVEL_1_SOURCE_CONNECTED": 3, "LEVEL_2_EVIDENCE_CONNECTED": 2, "LEVEL_3_CANONICAL_VIEW": 0, "LEVEL_4_RESEARCH_ACTIVE": 0}`

The write ran in one `BEGIN IMMEDIATE` transaction after an exact locked preflight. A fully
applied state is classified `ALREADY_APPLIED` and performs zero writes; any partial or
conflicting state is rejected rather than completed.

## Scope exclusions

No Claim content/status/confidence, Source link, Relation, Current View, Research Question,
Knowledge Gap or schema migration was created or changed. No LLM, RAG, embedding or generic
ontology framework was used.
