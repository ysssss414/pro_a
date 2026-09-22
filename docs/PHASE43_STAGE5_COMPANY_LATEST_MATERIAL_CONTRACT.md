# Phase 4.3 Stage 5 — Company Latest Material Contract

Contract versions: `company-material-intent-v1` and `company-material-timeline-v1`.
The frozen parent is `714ee990672018811fd93cb614b0ff12b8bf2571` (Stage 4D).

## Company Material Intent

An intent is private Workbench routing context attached to an existing Source processing run. Its exact fields are `target_company_node_id`, `material_kind`, `source_channel`, `material_date`, and `operator_title`. The target must be an active Production `Company` node, resolved by exact node ID. The date is an optional valid ISO calendar date supplied by the operator; the title is an optional bounded display label. Required enumerations are defined in `company_material_intent.py` and their canonical hashes are recorded in the qualification receipt. The normalized five-field object receives a deterministic canonical SHA-256.

`POST /source-operations/{source_id}/process` accepts the optional intent. A run without one follows the existing generic path. For a Company run, `COMPANY_MATERIAL_INTENT_BOUND` is appended before `PROCESSING_QUEUED`. The binding is part of the immutable event stream, processing projection, and durable cloud checkpoints. Retry with the same idempotency key requires identical Source and intent. A later run for the same Source may not change the target or intent metadata. Resume checks checkpoint identity against the bound event and stops on drift. No Workbench schema migration is used for intent.

The target is offered to Attribution with authority `COMPANY_MATERIAL_OPERATOR_TARGET`, once per node ID. It is a selectable candidate, never an automatic Claim–Node link. Review, human Attribution, qualification, and external activation keep their existing gates. The operator intent is excluded from provider prompt evidence and does not change a Claim's semantic content.

## Trust boundary

| Source channel | Operational display policy |
| --- | --- |
| `company_official`, `exchange_official` | `PRIMARY_OFFICIAL` |
| `broker_research` | `SECONDARY_RESEARCH` |
| `media` | `SECONDARY_MEDIA` |
| `knowledge_community` | `LOW_TRUST_CLUE_ONLY` |
| `user_upload`, `other` | `UNCLASSIFIED` |

The policy labels workflow context only. They do not assign Source Rank, confidence, Claim validity, or Current View status. Knowledge Community remains a clue-only channel. Stage 5 does not implement a Knowledge Planet connector; a future adapter must enter through the existing private clean PDF Source boundary and the same human gates.

## Company timeline and research boundary

`GET /research/companies/{node_id}/materials` merges private intent runs and canonical Sources by exact Source ID, with one row per Source. Before activation, the intent can associate a private material with its target Company. After activation, Company association requires an explicit canonical `source_node_link` or a Claim–Node link for that Source; operator intent alone cannot establish canonical association. Canonical Source title, publication time, ingestion time, Claim count, and linked nodes take precedence, while intent kind, channel, date, and lineage retain their own provenance. The result is deterministically sorted, paginated, and snapshot hashed. Read paths open Production and Workbench in query-only mode.

Private rows can show uploaded/processing, human review, Attribution, or qualified-unapplied state. Their Claim and impact counts are withheld until canonical activation. Canonical rows count the Source's actual Claims and linked nodes. The impact count comes from canonical Source Impact candidates; it is not a causal impact claim and never updates Current View. Company Inspector exposes the timeline, Source Operations, Review, canonical Source, affected Product/Industry nodes, and the existing Current View route. Non-Company inspectors retain their existing behavior.

The API and UI do not expose private storage paths, private artifact paths, or provider payloads. Real acceptance uses read-only Production and Workbench access; synthetic fixtures own all uploads, provider calls, reviews, Attribution decisions, and qualification writes.
