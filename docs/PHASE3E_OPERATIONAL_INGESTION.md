# Phase 3E Operational Clean-Source Ingestion

Status: **Stage 3E.1 implemented; B0 parent-placement governance decoupled; clean PDF only; stops at human review**

## Start a run

From the repository root:

```text
python scripts/phase3e_ingest.py <new-clean-source.pdf>
```

The command accepts only a clean, text-extractable PDF. A partial, empty, image-only, OCR-heavy, or otherwise non-clean PDF fails the clean-source gate and is deferred; it is not silently routed through a weaker parser or the legacy ingestion pipeline.

The configured cloud extraction model is used for a new run. The exact parsed model JSON and normalized `SourceAnalysis` are frozen before deterministic downstream processing. Unit and replay qualification may instead provide `--frozen-extraction <bundle.json>`; that option imports exact frozen extraction bytes and does not call an LLM.

## Runtime artifacts

Runs are written outside Git under:

```text
workspace/ingestion/INGEST_<source-sha-prefix>/
    source/
    run_manifest.json
    extraction/
    evidence/
    review/
    promotion/
    receipts/
```

A custom `--run-dir` must either be under the configured workspace or outside the Git repository.

The Source is copied byte-for-byte into `source/` immediately, re-hashed, and used for every later stage. The manifest binds the run and Source identities, parser/prompt/model configuration identities, repository commit, read-only Production baseline, stage status, and exact hash/size inventory of every runtime artifact. It contains no API key.

Every initial chunk and recursive truncation child independently scopes the unchanged active-Node prompt catalog against that exact model-visible Source piece. A Node record is included when its normalized canonical name or an alias occurs in the normalized piece; an empty scoped catalog remains a valid extraction call. The raw call record preserves piece provenance plus `full_prompt_catalog_count`, `scoped_node_catalog_count`, and the compact `scoped_node_ids` inventory, including for failed or truncated calls.

The stable operator-facing review artifacts are:

```text
review/claim_review.json
review/claim_review.md
review/node_operation_review.json
review/node_operation_review.md
promotion/promotion_preview.json
promotion/promotion_summary.md
```

The Claim review includes exact Evidence binding, table eligibility, deterministic semantic-guard results, an advisory `KEEP` / `DROP` / `REVIEW` recommendation, and a `PENDING` human decision. The Node review includes supporting review-admitted Claim IDs and Evidence, exact Production resolution, collision diagnostics, an advisory `CREATE` / `REUSE` / `DEFER` / `REJECT` suggestion, and a `PENDING` human decision. Extracted `suggested_parent_node_ids` remain visible but are labeled `PARENT PLACEMENT SUGGESTION`, `SEPARATE HUMAN REVIEW REQUIRED`, and `NOT AUTHORIZED BY NODE CREATE`. Evidence-backed semantic Relation observations remain in audit artifacts and are excluded from promotion.

## Parent-placement governance

Approving Node identity does not approve taxonomy placement. Accepting a `new_node` Proposal creates or reuses the Node and preserves its governed Source/Claim links, but never creates `child --part_of--> parent`. Each distinct advisory parent ID instead creates an independently reviewable pending Proposal with type:

```text
node_parent_placement
```

Its normalized payload is:

```text
child_node_id
parent_node_id
origin_new_node_proposal_id
origin_candidate_name
suggestion_reason
suggestion_source = MODEL_ADVISORY
```

Only explicit acceptance of that parent-placement Proposal can create the formal `part_of` Relation. Acceptance revalidates the accepted origin, active endpoints, non-self placement, absence of an existing or transitively redundant placement, and cycle safety. Rejection changes only the structural Proposal: the active Node and its Source/Claim links remain intact. No synthetic Claim or Relation Evidence is created.

The evidence-backed `node_relation` Proposal remains separate: it still requires supporting Claims and does not support `part_of`. Historical accepted Nodes and Relations are not rewritten. Existing pending `new_node` Proposals use the decoupled behavior when later accepted.

## Resume

Resume a run without depending on the original external PDF path:

```text
python scripts/phase3e_ingest.py --resume --run-dir <run-directory>
```

Resume re-hashes the frozen Source and the complete manifest inventory, verifies the current Production identity still matches the run baseline, and continues after the last completed stage. It does not repeat a completed LLM extraction. Any missing, modified, or additional runtime artifact, or a changed Production baseline, fails closed.

For controlled diagnosis, `--stop-after` accepts `source`, `extraction`, `evidence`, `claim-review`, `node-review`, or `promotion-preview`.

## Human-review and Production boundary

A normal successful run ends with:

```text
RUN_STATUS = HUMAN_REVIEW_REQUIRED
CLAIM_REVIEW = <path>
NODE_REVIEW = <path>
PROMOTION_PREVIEW = <path>
```

The promotion preview is deliberately non-executable. It separately lists Node CREATE/REUSE suggestions and parent-placement suggestions, never counts a parent suggestion as an automatically executable Relation, contains no intended mutation list, leaves all human decisions pending, and sets both `executable` and `production_apply_authorized` to false. The Phase 3D Production executor rejects it.

Stage 3E.1 does not bind human decisions, generate a Production authorization artifact, initialize or migrate the Production schema, create a Production backup, materialize the Production archive, invoke IMA, or call the Production executor. Production access is immutable/read-only. A later, separately authorized handoff may reuse the Phase 3D executor after human decisions and an exact executable payload have been frozen.
