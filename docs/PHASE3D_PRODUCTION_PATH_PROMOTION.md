# Phase 3D — Production Path Promotion / Apply Readiness

Status: **Stage 3D.0 + 3D.1 + 3D.2 complete; STOP gate active; Production apply not authorized**

Inspection date: `2026-09-02` (Asia/Shanghai)

This document freezes the post-Phase-3C baseline, preserves the Stage 3D.0/3D.1 mutation-path census and promotion contract, and records the completed Stage 3D.2 deterministic payload and shadow-apply qualification. Stage 3D.2 did not migrate or change Production and does not authorize a Production write.

```text
PHASE3D_STARTED = true
PHASE3D_STAGE3D2_IMPLEMENTATION_STARTED = true
PRODUCTION_CHANGED = NO
PRODUCTION_APPLY_ATTEMPTED = false
```

## 1. Baseline

### 1.1 Repository

The checkout was inspected without reset, merge, rebase, or checkout. A non-worktree-changing `git fetch --no-tags origin main` was used after `git ls-remote` showed that the local remote-tracking ref was stale.

```text
BRANCH = phase3c/correctness-generalization-closure
HEAD = 089f813a48417fc41e9f70a45f4ce9f91f806b5d
WORKTREE_STATUS = DIRTY: pre-existing untracked files/directories; no tracked modification at inspection start
REMOTE_MAIN_SHA = f6a9ecb55a53052656fb6ecb8ac95aea2d7e956d
LOCAL_MAIN_SHA = bf86a50bffa53b7fd210bb9b4b751e3f5737e8e3
```

Local `main` and remote `main` are **not aligned**. Local `main` is seven commits behind remote `main` and has no local-only commits. Current `HEAD` is an ancestor of remote `main` and is six commits behind it. No local branch pointer or worktree was advanced.

The relevant remote closure chain is:

```text
089f813 feat: close Phase 3C correctness and generalization
38ec912 docs: record Phase 3C correctness closure
da9e8e0 artifacts: add Pilot 6 delegated reviewer receipt
212bca4 artifacts: add machine-readable Pilot 6 review receipt
8d2205f docs: mark Phase 3C correctness complete
8bb575b Merge PR #42 (Phase 3C implementation)
f6a9ecb Merge PR #43 (Phase 3C closure)
```

The only tree differences from current `HEAD` to remote `main` are `README.md`, the two Pilot 6 signoff artifacts, and `docs/PHASE3C_CORRECTNESS_CLOSURE.md`. The blobs for the relevant code and tests under `src/`, `scripts/`, and `tests/` are identical. Thus the Phase 3C implementation at `089f813` is the implementation on remote `main`; `f6a9ecb` is the complete implementation-plus-governance closure.

Pre-existing untracked material includes local runtime directories plus Phase 1.1 orchestration scripts such as `scripts/run_phase1_1_ai_hardware_production_import.py` and `scripts/run_phase1_1_ai_hardware_finalization.py`. They were inspected as historical evidence but were not changed or treated as portable tracked runtime code.

### 1.2 Phase 3C closure mechanisms

The current code contains the expected Production-relevant correctness mechanisms:

| Mechanism | Current location | Verification |
|---|---|---|
| Exact/layout-safe Evidence validation and locator binding | `src/pro_a/analyzer.py`, `src/pro_a/corpus_pilot.py` | Claims carry validation state; unresolved Evidence becomes `needs_review`; exact/rebound/cross-page handling is tested. |
| Bounded local-subspan handling | `src/pro_a/corpus_pilot.py` (`build_bounded_local_subspan` and Stage 1.3/1.4 helpers) | Bounded, same-page, exact contiguous context; no fuzzy or invented context. |
| Narrative-first table suppression | `src/pro_a/parsers.py`, `src/pro_a/pdf_layout.py` | `extract_pilot_source` calls `semantic_eligible_source_text` before Analyzer chunking while retaining canonical Source text. |
| Post-binding table Claim safety | `src/pro_a/table_claim_safety.py` | `TABLE_DERIVED_CLAIM_SAFETY_BOUNDARY_V1` separates eligible and table-derived ineligible Claim IDs without mutating raw Claims. |
| Source/Evidence provenance | `src/pro_a/corpus_pilot.py` | Bundle Source identity/SHA/parser diagnostics plus per-Claim `evidence_pointer`, `evidence_excerpt`, locator validation, and `phase3c_evidence`. |
| Candidate validation | `src/pro_a/analyzer.py`, `src/pro_a/pipeline.py` | Node quality checks; exact existing-node validation; relation endpoint/evidence/semantic checks; rejected observations retained. |
| Semantic admission guards | `src/pro_a/semantic_admission.py`, replayed by `src/pro_a/pilot3_semantic_admission_replay.py` | Generic question-premise, precision-token, number/time, and subject/scope guards. They are replay tooling, not a unified generic promotion artifact. |
| Clean-source generalization gate | `scripts/phase3c_pilot6.py`, remote-main Pilot 6 receipts | 107 raw Claims, 3 table-derived ineligible, 104 reviewed/kept, zero true semantic failures and zero attribution errors. |

The noisy-transcript boundary is unchanged and is not a blocker for this stage.

## 2. Production baseline

Production was read through a SQLite URI using `mode=ro&immutable=1` and `PRAGMA query_only=ON`. No application `Database` helper, migration, checkpoint, vacuum, or write-capable command was used.

```text
PRODUCTION_PATH = D:\ej\材料\codex\get_knowledge\pro_a_v0_1\workspace\pro_a.db
PRODUCTION_SHA256 = 581978e1c587b065a6eef9c980013af3de1a9e8a8781857385404c9f61105250
PRODUCTION_SCHEMA_VERSION = 0.2.1
PRODUCTION_SCHEMA_SHA256 = 7ed86feec81b96bf5e91fd015bb1244d0e55946ae178ab73dee53a309f3ab496
PRODUCTION_NODE_COUNT = 294
PRODUCTION_ALIAS_COUNT = 737
PRODUCTION_RELATION_COUNT = 181
PRODUCTION_FK_VIOLATIONS = 0
PRODUCTION_INTEGRITY = ok
```

Relation state is 174 `current` plus 7 `retired_r1_migration`. Production has no `relation_evidence_links` table because it is still schema `0.2.1`; current code's `Database.init_schema()` targets `0.2.2` and would create/backfill that table. That migration was **not** run.

Stable table counts:

| Table | Count | Material state |
|---|---:|---|
| `meta` | 1 | `schema_version=0.2.1` |
| `nodes` | 294 | 294 active |
| `node_aliases` | 737 | alias key is `COLLATE NOCASE` unique |
| `node_relations` | 181 | 174 current; 7 retired |
| `sources` | 2 | 1 analyzed; 1 archived |
| `source_relations` | 0 | — |
| `source_node_links` | 3 | — |
| `claims` | 12 | 10 current; 2 needs review |
| `claim_node_links` | 19 | 11 subject; 8 context |
| `claim_relations` | 0 | — |
| `current_views` | 2 | 2 official |
| `proposals` | 11 | 2 accepted; 9 pending |
| `knowledge_gaps` | 0 | — |
| `research_questions` | 0 | — |
| `impact_reviews` | 0 | — |
| `impact_attempt_audit` | 0 | — |
| `side_effect_jobs` | 2 | 2 done |
| `ima_objects` | 0 | — |
| `processing_jobs` | 5 | 2 done; 2 duplicate; 1 failed |

SQLite sidecars at inspection time:

```text
pro_a.db-wal = ABSENT
pro_a.db-shm = ABSENT
pro_a.db-journal = ABSENT
```

## 3. Current extraction-to-write architecture

### 3.1 Actual Phase 3C path

```text
Source file
  -> parse_source_with_diagnostics(include_semantic_segments=True)
  -> canonical Source text + PyMuPDF layout sidecar
  -> semantic_eligible_source_text (table regions excluded before prompt)
  -> Analyzer + LLM on isolated Production copy
  -> validated SourceAnalysis
  -> hash-bound phase3c_extraction_bundle (non-canonical observations)
  -> Evidence rebound / bounded-context artifacts
  -> table Claim safety boundary
  -> Pilot-specific review/signoff
  -> STOP
```

The generic bundle's built-in controlled apply is narrower:

```text
phase3c_extraction_bundle + READY phase3c_extraction_review
  -> validate_review
  -> isolated-DB-only authorizer
  -> INSERT sources, accepted claims, processing_jobs
```

It explicitly blocks `cfg.db_path`, writes no Nodes/aliases/relations/links/proposals, and therefore is not a Production promotion path.

### 3.2 Structure census

| Structure | Defined in | Created by | Validated by | Current downstream consumer |
|---|---|---|---|---|
| `SourceAnalysis` | `src/pro_a/analyzer.py` dataclass | `Analyzer.analyze_source` | `_validate_source_output` | Legacy `IngestionPipeline`; Phase 3C bundle builder |
| Source/document bundle record | `src/pro_a/corpus_pilot.py` | `extract_pilot_source` | source SHA duplicate gate, parser diagnostics, bundle hash binding | Review artifacts and isolated Source/Claim apply |
| Canonical-shaped Claim record | `src/pro_a/pipeline.py::build_claim_record` | `_claim_bundle_record` or legacy `_insert_claims` | Analyzer schema/Evidence validation; deterministic Source locator | Phase 3C review; legacy claim insert; isolated apply |
| Evidence/provenance record | Claim fields plus `validation` and `phase3c_evidence` in `src/pro_a/corpus_pilot.py` | Analyzer + `phase3c_evidence_provenance_contract` | exact/layout-only locator, ordered spans, bounded local subspan | Evidence review/gates; stored in Claim `structured_json` by isolated apply |
| Existing Node match | `SourceAnalysis.node_matches` | LLM response, normalized by Analyzer | known active ID, confidence, exact Evidence, canonical/alias present in Evidence | Observational in Phase 3C; direct Source/Claim links in legacy pipeline |
| Node Candidate | `SourceAnalysis.node_candidates` | LLM response, normalized by Analyzer | type/schema/confidence and `_candidate_quality`; candidate Claim backfill in legacy path | Observational in Phase 3C; legacy REUSE/link or pending `new_node` Proposal |
| Relation Candidate | `SourceAnalysis.relation_candidates` | LLM response | existing endpoints, direction/semantic markers, relation-specific Evidence, accepted Claim refs | Observational in Phase 3C; pending `node_relation` Proposal in legacy path |
| Generic extraction review | `phase3c_extraction_review` in `src/pro_a/corpus_pilot.py` | `_build_review_draft`, then Stage 1.2 closure | `validate_review`; bundle hash, immutable Claim projection, explicit decisions | Isolated Source/Claim apply |
| Table admission decision | `src/pro_a/table_claim_safety.py` V1 result | Pilot 6 finalization | authoritative locator + canonical binding + unique word geometry + protected/narrative checks | Pilot-specific eligible set and audit; not consumed by generic apply |
| Semantic admission result | `src/pro_a/semantic_admission.py` | Pilot 3 replay tooling | deterministic guard aggregation | Gate/replay evidence; not carried as a uniform generic bundle field |
| Pilot 6 final review | `artifacts/phase3c/pilot6_delegated_reviewer_signoff.json` on remote `main` | delegated review closure | exact run/source/review-surface identity and claim list | Governance closure only; no importer consumes it |
| Phase 1 CREATE/REUSE/excluded rows | Phase 1 package CSV/JSON artifacts | Phase 1 adjudication/finalization scripts | manifest, identity, collision, endpoint, exclusion gates | One-time B.2C / Phase 1.1 apply scripts |

No Phase 3C structure currently assigns formal `CREATE`, `REUSE`, `UPDATE`, `DEFER`, or `REJECT` operations to Node/Relation observations. `KEEP`/`DROP` applies to Claims, `quality_eligible` is an Analyzer quality signal, and `review_eligible` is table-safety eligibility; none is a Production mutation decision.

### 3.3 Accepted Pilot 6 artifact incompatibility

The accepted Pilot 6 result is not one generic READY review:

- `extraction_bundle_stage1_1_rebound.json`: 107 rebound Claims;
- `pilot6_table_claim_safety_boundary.json`: 104 review-eligible IDs and 3 ineligible IDs;
- remote-main delegated-review signoff: 104 `KEEP` decisions;
- generic `extraction_review_draft.json`: still `DRAFT`, contains all 107 Claims, and is not the signoff artifact.

`validate_review()` cannot consume that combination. Passing the original draft fails readiness; converting all 107 to `KEEP` would re-admit the three table-derived Claims; omitting them changes the required all-claims projection. A deterministic adapter must bind these exact inputs before any apply path exists.

## 4. Mutation path census

### 4.1 Main paths

| Path | Purpose/input | Mutation target | Deterministic | Production capable / used | Safety gates | Phase 3D reuse |
|---|---|---|---|---|---|---|
| `pro-a ingest/watch` -> `IngestionPipeline.process_file` | Source files plus live LLM output | Sources, Claims, links, source relations, Proposals, impacts, gaps, jobs, IMA metadata; later views | Partial | Yes / historically used | Analyzer validation, evidence downgrades, candidate quality, relation Proposal validation | **No** as apply path |
| `pro-a` context -> `Database.init_schema` | Every CLI command, including nominal reads | Schema/meta and migration backfills | Yes | Yes / unknown | SQLite transaction only; no baseline authorization | **No**; explicit hazard on schema 0.2.1 Production |
| `nodes add/seed`, `relations add/seed/add-evidence/propose` | CLI arguments/CSV | Nodes, aliases, relations, relation Evidence, Proposals | Partial | Yes / historically used | Types/FKs; current non-`part_of` Evidence; relation Proposal revalidation | Validator pieces only |
| `ProposalManager.accept/reject` + propagation/impact recovery | Pending DB Proposal | Nodes, aliases, relations, Evidence links, links, questions, views, Proposals, impacts, jobs | Partial | Yes / used (accepted proposals/views exist) | Pending/stale checks; atomic relation/view accept; relation revalidation | Relation validator only; not the apply engine |
| `apply_production_reviewed_bundle` | Exact bundle + READY review | Isolated copy: Source, kept Claims, processing job | Partial (apply time/IDs frozen partly) | **No**; configured Production blocked / tested | Bundle hash, immutable Claims, decisions, Source SHA, write authorizer, transaction, idempotency | **Partial** for Source/Claim row mapping |
| B.2C `apply_b2c_approved.py` | Frozen manifest plus approved CSVs | Explicit isolated or Production DB: Nodes, aliases, approved `part_of` | Yes | Yes / mechanism proven; current package stale and one-time | manifest/hash/schema/count/auth token, CREATE/alias collision, REUSE, endpoints/cycles, exclusions, FK/integrity, semantic diff | **Partial**; frozen package cannot be reused unchanged |
| Phase 1.1 `run_phase1_1_ai_hardware_finalization.py` | Hard-coded clean package | Isolated Production copy: Nodes, aliases, `part_of` | Yes | No Production authority / used for qualification | deterministic IDs, exact resolution, exclusion, table diffs, idempotency, rollback drill | **Partial**; local untracked, package-specific |
| Phase 1.1 `run_phase1_1_ai_hardware_production_import.py` | Same qualified package and one-time constants | Configured Production: Nodes, aliases, `part_of` | Yes | Yes / used once 2026-08-25 | SHA/schema/count/sidecar gates, fresh resolution, backup, transaction, post-QA, idempotent rerun, rollback copy, receipt | **Partial**; untracked and authorization consumed |
| `claim_node_activation.activate_database` (Phase 2.3D) | Frozen CSV and hard-coded Claim/Node allowlist | Claim-Node links | Yes | Yes / used once | read-only preflight, backup, locked exact state, transaction, post-diff, receipt | No; scope-specific, pattern reference only |
| `claim_attribution_semantics.activate_database` (Phase 2.3F) | Frozen hard-coded attribution matrix | One Node and Claim-Node roles/links | Yes | Yes / used once | exact identities/state, backup, transaction, preserved-table snapshots, idempotency | No; scope-specific |
| `scripts/activate_phase2_4b.py` | Frozen Current View artifact | Proposals, current views, side-effect jobs | Partial | Yes / used once | identity/content checks and backup; then generic ProposalManager | No |
| Phase 2.7B `production_proposal_gateway.apply_production` | Human-edited Current View draft | Configured Production `proposals` only | Yes for bound draft | Yes / used and tested | exact canonical state, backup, narrow authorizer, transaction, FK/integrity, idempotency, receipt | No for Node promotion; safety pattern reusable |
| Phase 2.7C `human_proposal_resolution.resolve_production` | Exact human resolution | Configured Production Proposal and optionally Current View | Yes for bound artifact | Yes / used/tested | exact snapshot, evidence/content gates, backup, narrow authorizer, transaction, FK/integrity, receipt | No for Node promotion; safety pattern reusable |
| Phase 3B `sync_production_source` | Existing Source ID plus external IMA operation | Production IMA fields/objects and remote IMA | Partial | Yes / explicitly invoked only | configured target, durable uncertain state, narrow authorizer, receipts | No; must remain disabled during promotion |
| Test/isolated helpers (`submit_review`, `resolve_isolated`, fixtures) | Review artifacts and fixture DBs | Explicit non-Production DBs | Yes/partial | No | samefile/configured-Production guards | Tests only |

The FastAPI surface in `src/pro_a/api.py` contains GET/read-only routes only. It is not a mutation path.

### 4.2 Direct database service surface

`src/pro_a/db.py` is a write-capable repository, not a read-only model. Its public mutation surface includes schema initialization/migrations, arbitrary `execute`, Node/alias add/seed, Relation/Evidence add/seed/propose, and generic Proposal insertion. `src/pro_a/pipeline.py`, `src/pro_a/proposals.py`, `src/pro_a/propagation.py`, and `src/pro_a/impact_recovery.py` compose those methods into wider mutation flows.

This surface is Production-capable whenever constructed with `cfg.db_path`. It does not enforce a promotion-payload boundary, Production SHA, backup, or audit receipt globally.

## 5. Phase 1 infrastructure reuse matrix

The strongest proof is the Phase 1.1A receipt: 13 CREATE, 5 REUSE, 31 aliases, and 4 structural Relations applied atomically; exact rerun was a no-op; isolated rollback restored the pre-write bytes; integrity and FK checks passed. The mechanisms are valuable, but the production scripts are frozen one-off orchestration, not parameterized library code.

| Capability | Existing implementation | Location | Proven/used previously | Reusable unchanged | Needs adapter | Needs replacement |
|---|---|---|---|---|---|---|
| Baseline/hash validation | Exact DB SHA and package manifest SHA gates | B.2C apply; Phase 1.1 prewrite gate | Yes | No | Yes | No |
| Schema/version verification | `schema_identity`, schema SHA, exact baseline counts | B.2C apply; Phase 1.1 finalization/import | Yes | No | Yes | No |
| Backup | SQLite/read-only or byte-copy backup with SHA check | Phase 1.1 production import; Phase 2 gateways | Yes | No | Yes | No |
| Payload/manifest validation | File inventory, byte/hash checks, exact row counts and decisions | B.2C and Phase 1.1 manifests | Yes | No | Yes | No |
| Deterministic row generation | Stable Node/Relation IDs and canonical serialization | Phase 1.1 finalization; B.2C `relation_id` | Yes | No | Yes | No |
| CREATE collision detection | Exact canonical, alias, SQLite NOCASE, NFKC/casefold checks | B.2C/Phase 1.1 preflight and locked write gate | Yes | No | Yes | No |
| Alias collision detection | Production and package-internal owner maps | B.2C/Phase 1.1 | Yes | No | Yes | No |
| REUSE resolution | Exact canonical/alias to one active, type-compatible ID | B.2C/Phase 1.1 | Yes | No | Yes | No |
| Relation endpoint validation | Exact IDs, self-loop/duplicate/cycle/redundancy checks | B.2C/Phase 1.1 structural gates | Yes | No | Yes | No |
| DEFER/REJECT exclusion | Separate excluded inventory plus absence checks before/after | B.2C/Phase 1.1 | Yes | No | Yes | No |
| FK validation | `PRAGMA foreign_key_check` in and after transaction | Both import generations | Yes | Yes as a primitive | Yes for payload engine | No |
| Integrity checks | `PRAGMA integrity_check` pre/in/post apply | Both import generations | Yes | Yes as a primitive | Yes for orchestration | No |
| Post-apply count/table checks | Semantic snapshots and exact allowed deltas | B.2C/Phase 1.1 | Yes | No | Yes | No |
| Rollback/restore procedure | rollback-on-exception plus byte-exact restore drill on copy | Phase 1.1 qualification/import | Yes | No | Yes | No |
| Audit artifacts | manifest, fresh resolution, qualification, receipt, semantic diffs | B.2C/Phase 1.1 package directories | Yes | No | Yes | No |

Concrete incompatibilities preventing unchanged reuse:

1. Both import generations bind historical package paths, filenames, SHAs, exact counts, and expected deltas.
2. The newer Phase 1.1 scripts are untracked local files; importing them would make Stage 3D non-portable.
3. Phase 1 payloads contain Nodes, aliases, REUSE mappings, excluded candidates, and structural `part_of`; they do not consume Phase 3C Source/Claim/Evidence/admission artifacts or non-structural Relation Evidence.
4. Production has advanced from the frozen Phase 1 SHAs and counts, so the old manifests correctly fail closed.
5. There is no Phase 1 `UPDATE` contract.

The correct reuse is a thin tracked adapter plus a generalized form of the proven validators/apply sequence, not execution or copying of a consumed one-time importer.

## 6. Identified bypasses and risks

These are census findings only; no fix was made.

1. **Legacy LLM-to-canonical path.** `IngestionPipeline.process_file` sends Analyzer results directly to Source/Claim/link writes. Invalid Evidence is downgraded to `needs_review`, but the Claim itself is still inserted. LLM-selected exact Node matches can create canonical Source/Claim links without a promotion review.
2. **Phase 3C table boundary is bypassed by legacy ingestion.** The Phase 3C path asks for semantic segments and passes `semantic_eligible_source_text` to Analyzer. The legacy pipeline parses normally and analyzes full `parsed.text`; it does not invoke the V1 post-binding table Claim safety boundary. Table-suppressed/ineligible content can therefore re-enter through legacy ingestion.
3. **Semantic admission artifacts are not a generic write gate.** The generic legacy and isolated apply paths do not require a stored `evaluate_semantic_admission` result or Pilot 6 signoff.
4. **Automatic candidate REUSE/linking.** `_create_node_proposal` calls `find_node_by_name_or_alias`; an exact hit bypasses the Proposal and immediately writes Claim/Source links. This is deterministic under the unique alias index, but it ignores a formal admission/review operation.
5. **New-Node acceptance trusts a mutable Proposal payload.** `ProposalManager._accept_new_node` checks primary type but does not re-run Phase 3C Evidence/table/admission gates. Its Node, parent Relation, link, and Proposal-status writes span multiple transactions, so it is not an atomic import engine.
6. **Collision policy differs from Phase 1.** `Database.add_node` deduplicates only `(canonical_name, primary_type)` and uses `INSERT OR IGNORE` for aliases. A same canonical under another type or an alias owned by another Node can produce a created Node with a silently skipped alias. Phase 1 globally blocks those cases.
7. **Direct admin paths bypass promotion governance.** CLI Node/Relation seed/add and generic `Database.execute` can write without a deterministic promotion payload, baseline hash, backup, or receipt.
8. **Nominal CLI reads can migrate.** `_ctx()` always calls `db.init_schema()`. Against current Production this would change schema `0.2.1` to `0.2.2`, including relation-Evidence backfill, before commands such as `status` run.
9. **Relation writes have multiple policies.** Phase 1 imports only approved structural `part_of`; generic direct add permits `part_of` without Evidence; current non-structural Relations require a supporting Claim; legacy Analyzer creates pending Proposals. There is no one promotion-level policy.
10. **Proven importer provenance is insufficient for Phase 3D.** Phase 1 receipts preserve decision artifacts but final Node/Relation rows have no direct source/evidence/admission foreign key. A Phase 3D payload must keep the audit chain even if the current DB schema stores part of it only in the receipt.
11. **Review status mismatch.** The Pilot 6 signoff and table boundary are not accepted by generic `validate_review`, so there is no safe current way to express the 104 admitted Claims without either losing three exclusions or changing the immutable projection.

No observed path silently converts an ambiguous Phase 1 resolution into CREATE; the mature Phase 1 gates fail closed. The risk is that the legacy pipeline uses a separate, weaker operation model.

## 7. Draft Promotion Contract

### 7.1 Boundary and core rule

```text
LLM / extraction output
  -> immutable Phase 3C artifacts
  -> validated candidate + explicit review/admission decisions
  -> deterministic Phase 3D promotion payload
  -> read-only pre-write validator against an exact DB baseline
  -> allowlisted transactional apply engine
  -> shadow DB (Stage 3D.2)
  -> STOP and separate Production authorization gate
```

**LLM-generated output must never directly mutate Production.** The apply engine accepts only a validated, deterministic promotion payload. It must not call an LLM, rerun extraction, resolve names fuzzily, infer missing operations, or convert ambiguity into CREATE.

### 7.2 Common eligibility rules

Every executable operation must:

- bind the exact extraction bundle, Evidence/boundary artifacts, admission/review artifact, repository commit, Production SHA, schema version/hash, and source SHA;
- retain a stable candidate/Claim identity and the decision that authorized the operation;
- use only exact canonical/alias/ID resolution and require one active target where resolution is needed;
- carry final intended row values, including stable IDs and a frozen timestamp, so apply does not reinterpret candidate content;
- include Evidence/provenance references sufficient to audit the mutation without the raw LLM response;
- exclude any table-derived ineligible Claim from executable mutations;
- fail the entire preflight on stale baselines, collisions, ambiguous targets, unsupported operations, or unexpected table deltas.

### 7.3 Operation semantics

#### CREATE

- Required: operation/candidate ID, deterministic new object ID, canonical identity, object type, exact aliases, final row values, Evidence/Claim refs, admission state, reviewer decision and reason.
- Eligible only after Phase 3C Evidence/table/semantic gates and explicit human or recorded delegated review approve creation.
- Any exact, NOCASE, normalized, alias, ID, or package-internal collision blocks preflight. A collision does not become REUSE automatically.
- It may enter the executable payload only as `APPROVED`.
- Exact replay of the same ID and content is a no-op; same ID or identity with different content is a conflict.

#### REUSE

- Required: candidate ID, resolved target ID, expected canonical/type/status, exact match mechanism and term, Evidence/Claim refs, admission/review decision, and any separately approved link/alias mutations.
- Target must resolve to exactly one active, type-compatible object both at build and locked write preflight.
- Zero or multiple targets becomes `DEFER`; it never becomes CREATE.
- Initial Production promotion requires explicit review even for exact REUSE.
- REUSE itself inserts no Node. Exact already-present approved links/aliases are idempotent; target drift or a conflicting alias blocks the payload.

#### UPDATE

- Required: candidate ID, deterministic target ID, expected pre-state semantic hash/version, explicit field allowlist and before/after values, Evidence/Claim refs, reason, and reviewer identity.
- Target identity must be unique and unchanged. Any baseline or field drift blocks.
- Human review is mandatory.
- The initial Stage 3D.2 engine must reject executable UPDATE because no proven Phase 1 UPDATE contract exists. UPDATE remains representable for audit but cannot enter an initial apply payload.
- Future exact replay may be a no-op only when the full after-state matches.

#### DEFER

- Required: candidate ID, proposed identity, Evidence/provenance refs, reason code, ambiguity/unmet-gate details, and review state.
- Used for ambiguous/zero resolution, missing Evidence, unsupported initial operations, or insufficient review.
- Never enters executable mutations or row generation. Repeated artifact generation is stable and auditable.

#### REJECT

- Required: candidate ID, proposed identity, Evidence/provenance refs, explicit reason, decision authority, and decision time/receipt.
- Used for a terminal negative decision for this run. It is retained in audit inventory only.
- Never enters executable mutations. Reconsideration requires a new reviewed payload/version rather than editing the old receipt.

### 7.4 Relation-specific rules

- Final `source_node_id` and `target_node_id` must already exist uniquely or be deterministic CREATE IDs in the same payload; apply performs no name resolution.
- Relation CREATE requires a deterministic relation ID, type, scope, status, endpoint operations, and supporting admitted Claim/Evidence refs. Non-`part_of` requires at least one active admitted supporting Claim.
- An existing exact relation is not silently reused. The builder must emit reviewed `REUSE` with its existing relation ID, or preflight fails a CREATE collision.
- Self-relations, missing/inactive endpoints, duplicates, `part_of` cycles, and unexpected transitive redundancy fail preflight according to the Phase 1 rules.
- On Production schema `0.2.1`, non-structural Relation promotion is blocked because the current Evidence-link persistence table is absent. Stage 3D.2 must fail closed rather than migrate the shadow implicitly.

### 7.5 Minimum deterministic payload schema

Recommended logical shape (field names may be finalized in Stage 3D.2):

```json
{
  "document_type": "phase3d_promotion_payload",
  "payload_version": "1",
  "payload_id": "PROMO_...",
  "payload_hash": "sha256-of-canonical-semantic-body",
  "metadata": {
    "source_run_id": "PILOT_...",
    "repository_commit": "...",
    "production_sha256": "...",
    "production_schema_version": "0.2.1",
    "production_schema_sha256": "...",
    "production_counts": {},
    "frozen_timestamp": "...",
    "input_artifacts": [{"role": "...", "sha256": "..."}]
  },
  "sources": [],
  "evidence": [],
  "claims": [],
  "node_operations": [],
  "relation_operations": [],
  "excluded_operations": [],
  "intended_mutations": [],
  "audit": {"admission": [], "reviewers": [], "reasons": []}
}
```

Minimum Source fields: proposed/final Source ID, source SHA, original name/type, reviewed metadata, parser/layout policy references, archive-copy intent, final DB fields, and source artifact hashes.

Minimum Claim fields: Claim/candidate ID, final canonical Claim fields, Source ID, Evidence pointer/excerpt, authoritative locator/spans, `phase3c_evidence`, table eligibility, semantic/admission state, review decision, confidence/status, and final intended Claim row.

Minimum Node operation fields: operation, operation/candidate ID, proposed deterministic Node ID for CREATE, canonical name/type/description, aliases, resolved target ID and expected target identity for REUSE/UPDATE, Claim/Evidence refs, admission/review state, reason, and exact intended rows/links.

Minimum Relation operation fields: operation, operation/candidate ID, deterministic or resolved relation ID, type/scope/status, final source/target Node IDs, endpoint resolution receipts, supporting Claim/Evidence refs, admission/review state, reason, and exact intended relation/Evidence-link rows.

Audit fields must identify the source artifacts and hashes, decision authority (`HUMAN_REVIEW` or accurately named delegated mode), reasons, validation versions/results, and exclusions. A creation timestamp may be recorded, but the semantic payload hash must cover a frozen value; rerunning a builder must not change the semantic body merely because wall time changed.

The payload must be inspectable without the raw LLM response. The raw Source remains outside the payload and is bound by SHA.

## 8. Production-specific gap classification

### P0 — blocks safe apply now

1. **No converged validated input.** The accepted 104 Pilot 6 Claims are represented by multiple differently shaped artifacts that `validate_review` cannot consume as one exact admitted set.
2. **No operation decision layer.** Phase 3C observations do not carry reviewed CREATE/REUSE/UPDATE/DEFER/REJECT decisions or locked target resolution.
3. **No generic Production-capable payload consumer.** The Phase 3C apply is isolated Source/Claim-only; the proven Phase 1 engines are historical package-specific scripts and cannot consume Phase 3C provenance or current baselines.

Consequently, a safe Production apply cannot be attempted from the current repository state.

### P1 — required before an initial controlled Production promotion

1. Generalize the Phase 1 preflight/transaction/postflight sequence into tracked, payload-driven code with a configured-Production hard block during Stage 3D.2.
2. Bind table eligibility, Evidence/admission, and exact review decisions into every executable Claim/Node/Relation operation; preserve the full audit chain in the payload/receipt.
3. Resolve the `0.2.1` Production versus `0.2.2` code contract explicitly. Do not let `pro-a` implicitly migrate it. Initial Stage 3D.2 should pin `0.2.1` and reject non-structural Relation writes.
4. Bring the Phase 1 identity/collision policy into the promotion validator; do not use `Database.add_node`/`find_node_by_name_or_alias` as the apply collision authority.
5. Add exact Production SHA/schema/count/sidecar gates, SQLite backup, one transaction, allowed-table semantic diff, FK/integrity checks, idempotent replay, rollback drill on a copy, and receipts to the new shadow path.
6. Define a human-review handoff for node/relation operations. Delegated AI review must remain accurately labeled and must not be represented as human review.

### P2 — useful hardening after the first shadow path

- Factor shared canonical snapshot/diff/identity helpers into a small tracked module after the first adapter is proven, avoiding a broad refactor of frozen scripts.
- Add a narrow SQLite authorizer in addition to Phase 1 semantic-diff checks.
- Add package signature/cryptography only if an existing operational requirement appears; SHA-bound canonical JSON is sufficient for the first controlled path.
- Add UPDATE implementation only with its own field allowlist, pre-state hash, rollback, and tests.

### BACKLOG

- Noisy transcript robustness and corrections.
- IMA, propagation, Current View, Knowledge Gap, and Research Question side effects after promotion.
- Automatic promotion, scheduling, fuzzy/entity-semantic matching, and bulk table ETL.
- Non-structural Relation apply until schema/Evidence-link migration is separately authorized and tested.

## 9. Minimum Stage 3D.2 plan

Stage 3D.2 should be shadow-only and should not alter the closed extraction path.

```text
exact Phase 3C artifact set
  -> promotion adapter (bind hashes and decisions; emit exclusions)
  -> generalized Phase 1 preflight
  -> SQLite backup copy of exact current Production
  -> single-transaction shadow apply
  -> semantic diff / integrity / FK / idempotency / rollback receipt
  -> verify configured Production SHA unchanged
  -> STOP
```

Initial executable scope should be CREATE and REUSE for Sources, admitted Claims, Nodes, aliases, and deterministic links. DEFER/REJECT remain audit-only. UPDATE and non-structural Relation operations must fail closed. Structural `part_of` may be supported only if explicitly reviewed and the Phase 1 cycle/redundancy gates pass.

```text
FILES_TO_CHANGE =
  docs/PHASE3D_PRODUCTION_PATH_PROMOTION.md (record Stage 3D.2 results only)

FILES_TO_REUSE_UNCHANGED =
  src/pro_a/corpus_pilot.py (bundle hashing/Claim row mapping/Evidence artifacts)
  src/pro_a/table_claim_safety.py
  src/pro_a/semantic_admission.py
  src/pro_a/storage.py
  src/pro_a/config.py (read configured identity only; no Database initialization)

NEW_FILES_IF_ANY =
  src/pro_a/production_promotion.py
  scripts/phase3d_promotion.py
  tests/test_production_promotion.py

TESTS_TO_ADD =
  exact multi-artifact hash binding and 104/107 eligibility convergence
  deterministic payload/hash/IDs and explicit operation validation
  ambiguous/zero REUSE -> DEFER; never CREATE
  CREATE/alias/ID collision and target-drift failures
  DEFER/REJECT exclusion; UPDATE/non-structural Relation rejection
  current Production SHA/schema/count/sidecar preflight on read-only input
  exact allowed-table shadow delta, FK/integrity, injected rollback
  exact idempotent replay and conflicting replay failure
  backup/restore drill on shadow files
  configured Production samefile/path hard block and pre/post byte hash equality

TESTS_TO_REUSE =
  tests/test_corpus_pilot.py::{
    test_review_gates_require_exact_bundle_and_safe_claim_decisions,
    test_controlled_apply_isolated_copy_is_idempotent_and_writes_only_allowed_tables,
    test_apply_blocks_configured_production_database
  }
  tests/test_pdf_table_suppression.py
  tests/test_table_claim_safety.py
  tests/test_semantic_admission.py
  tests/test_relation_proposals.py
  tests/test_relation_evidence.py
  Phase 1.1 qualification/Production receipts as historical acceptance fixtures, not executable input
```

Do not change the legacy pipeline, generic ProposalManager, schema, Production config, or Phase 3C extraction algorithms in Stage 3D.2.

## 10. STOP-gate result

```text
PHASE3D_STARTED = true

PHASE3D_BASELINE_FROZEN = true
PHASE3D_PRODUCTION_PATH_CENSUS_COMPLETE = true
PHASE3D_PHASE1_REUSE_CENSUS_COMPLETE = true
PHASE3D_PROMOTION_CONTRACT_DRAFTED = true
PHASE3D_GAP_ANALYSIS_COMPLETE = true
PHASE3D_STAGE3D2_PLAN_READY = true

PHASE3D_STAGE3D2_IMPLEMENTATION_STARTED = false

PRODUCTION_CHANGED = NO
PRODUCTION_APPLY_ATTEMPTED = false
```

P0 blockers exist: there is no converged admitted artifact, formal operation-decision layer, or generic current-baseline apply consumer. Stop here.

```text
RECOMMENDED_NEXT_ACTION =
Create Stage 3D.2 from remote main f6a9ecb as a tracked, shadow-only promotion adapter and generalized Phase 1 validator/apply path; bind the exact Phase 3C artifacts, support initial CREATE/REUSE only, verify on an exact current Production copy, and retain an unconditional configured-Production write block.
```

## 11. Stage 3D.2 implementation and qualification

Stage 3D.2 was implemented on `phase3d/shadow-promotion-adapter`, starting from the verified remote-main closure baseline:

```text
BASE_SHA = f6a9ecb55a53052656fb6ecb8ac95aea2d7e956d
REMOTE_MAIN_ADVANCED = NO
```

The current checkout's pre-existing untracked files were preserved. No Phase 3C extraction algorithm, legacy ingestion path, schema, Proposal/Current View path, IMA path, or historical Phase 1 importer was changed.

### 11.1 Tracked implementation

- `src/pro_a/production_promotion.py` implements exact artifact convergence, canonical payload hashing, deterministic IDs, explicit operation semantics, Phase 1-style identity/collision checks, immutable read-only Production identity checks, the configured-Production hard block, shadow copy/apply, semantic table diff, FK/integrity verification, replay, rollback, restore, and qualification receipts.
- `scripts/phase3d_promotion.py` is the explicit Pilot 6 shadow qualification entry point.
- `tests/test_production_promotion.py` covers artifact tampering/coverage, determinism, operation decisions, collisions/drift, Production blocking, allowed-table deltas, replay conflict, rollback, restore, and absence of implicit schema initialization.
- This document records the qualification result. The Stage 3D.0/3D.1 census above remains historical.

The implementation never imports or constructs `Database` in its apply path and never calls `Database.init_schema()`. Production identity is read through `mode=ro&immutable=1` plus `query_only=ON`. The apply function always compares resolved paths and `samefile` identity against configured Production; there is no override parameter.

### 11.2 Payload contract actually implemented

The payload contains the required top-level fields:

```text
document_type
payload_version
payload_id
payload_hash
metadata
sources
evidence
claims
node_operations
relation_operations
excluded_operations
intended_mutations
audit
```

`payload_hash` is SHA-256 over canonical JSON after removing only `payload_id` and `payload_hash`; `payload_id` is deterministically derived from that hash. The frozen Source/Claim ingestion timestamps come from the bound bundle, so wall time does not affect the semantic body. Receipt time is outside the semantic payload.

Metadata binds the repository baseline, Production byte SHA, schema version, schema SHA, every baseline table count, Source SHA, all four input artifact roles/hashes, and the delegated signoff's review-surface identity. The generic 107-Claim review is explicitly verified as `DRAFT` with 107 `PENDING` decisions and is never used as authority. Every Claim links to a deterministic Evidence record and retains its immutable Claim projection, table decision, reviewer decision, executable state, and exact intended row where executable.

Stage 3D.2 standardizes the schema digest on the proven Phase 1 algorithm: canonical JSON over `type,name,tbl_name,sql` for every non-SQLite `sqlite_master` object, ordered by type/name. That algorithm yields:

```text
PRODUCTION_SCHEMA_SHA256_PHASE1_CANONICAL = 1732ae65db9b56bed1c98a99824ab8e71f9fe65d5fa3cb52eb393f407e107ac2
```

The different `7ed86f...` value in the Stage 3D.0 census used its inspection-time schema projection. The Production byte SHA, schema version, tables, counts, integrity, and FK state did not change; payload generation and apply use the now-explicit Phase 1 canonical algorithm consistently.

### 11.3 Exact artifact convergence

The adapter binds these byte hashes before interpreting content:

| Role | SHA-256 |
|---|---|
| `phase3c_rebound_bundle` | `1e94c5db8a67dd556a617fb13dcca9f4fc54e3d5cf51810c7f9b722b82ccc02f` |
| `table_claim_safety_boundary` | `3fa68e26c0580657c4c26040ac6c0ea870d416e9d251b8f74cad9f12ff301121` |
| `delegated_reviewer_signoff` | `b5ac42cc44dcc54f02321a643ef399d621a88667a7153da0ee06c954783012d5` |
| `generic_extraction_review_draft` | `28de1f878905910b6bc9fa50ee75b27bedc829737643073abfaa8f2e02f56411` |

It then proves identical run/Source identity, exact Claim coverage/order, unique Claim IDs, immutable Evidence excerpts, unchanged raw Claim projection, an exact eligible/ineligible partition, the signed 104-Claim review surface, 104 `KEEP` decisions, and zero semantic/attribution failures.

```text
RAW_CLAIMS = 107
TABLE_INELIGIBLE_CLAIMS = 3
ADMITTED_CLAIMS = 104
EXECUTABLE_CLAIMS = 104
```

The three audit-only exclusions remain exactly:

```text
CLM_20260902_35679678
CLM_20260902_438AEFC8
CLM_20260902_22A043B8
```

No generic 107-Claim review was rewritten or promoted to READY.

### 11.4 Executable versus deferred operations

The accepted Claim review authorizes the Source and 104 Claims only. It does not authorize Node or Relation mutations.

```text
SOURCE_CREATE = 1
CLAIM_CREATE = 104

NODE_CREATE = 0
NODE_REUSE = 0
NODE_DEFER = 26
NODE_REJECT = 32

RELATION_CREATE = 0
RELATION_REUSE = 0
RELATION_DEFER = 0
RELATION_REJECT = 10
```

The 26 Node deferrals are the six accepted existing-node observations plus 20 Node Candidates without explicit Node-operation review. The 32 Node rejections and ten Relation rejections preserve Phase 3C validation outcomes as audit-only records. `UPDATE` is representable but never executable. Non-`part_of` Relation execution, automatic/fuzzy resolution, and all side-effect categories remain hard-blocked.

The generic operation helper proves explicit reviewed `CREATE` and exact reviewed `REUSE`; zero/multiple resolution deterministically becomes `DEFER`. Locked preflight checks Node ID, canonical, alias, SQLite NOCASE, Unicode NFKC/casefold, package-internal collisions, target activity/type, and target drift. Structural `part_of` validation includes exact endpoints, self/duplicate/cycle/redundancy gates, but Pilot 6 contains no reviewed executable Relation.

### 11.5 Shadow apply, replay, and rollback qualification

Qualification output is under:

```text
workspace/phase3d/STAGE3D2_QUALIFICATION_F6A9ECB_V2/
```

The exact Production file was copied before any write-capable shadow connection was opened. The shadow stayed on schema `0.2.1`; no schema initialization or migration ran. All 105 intended inserts ran in one transaction under a narrow authorizer. Postflight proved the exact semantic delta:

```text
PAYLOAD_ID = PROMO_2938849C91722C57
PAYLOAD_SHA256 = 2938849c91722c578b11c18bf6056d46d906d4c1839707da3ae10f473c6a647d

SHADOW_PRE_SHA256 = 581978e1c587b065a6eef9c980013af3de1a9e8a8781857385404c9f61105250
SHADOW_POST_SHA256 = 5fb927ea5dd89ed6ed9794165165554ad2ea24c0621b30cc4055d8e80aac1187
CHANGED_TABLES = sources:+1/-0, claims:+104/-0
SHADOW_FK_VIOLATIONS = 0
SHADOW_INTEGRITY = ok
```

The identical payload replay returned `ALREADY_APPLIED` with no table delta. A conflicting replay test changed one intended Claim and correctly failed instead of reconciling it.

The transaction rollback drill injected a failure after the second insert and proved the post-failure semantic snapshot equal to the pre-apply snapshot. The restore drill copied the pre-apply backup over a disposable applied shadow and recovered the exact pre-SHA, semantic snapshot, `integrity=ok`, and zero FK violations.

### 11.6 Production integrity proof

Production preflight and postflight were both immutable/read-only. The configured database was never passed to the write-capable path.

```text
PRODUCTION_PRE_SHA256 = 581978e1c587b065a6eef9c980013af3de1a9e8a8781857385404c9f61105250
PRODUCTION_POST_SHA256 = 581978e1c587b065a6eef9c980013af3de1a9e8a8781857385404c9f61105250
PRODUCTION_SIDECARS_PRE = absent
PRODUCTION_SIDECARS_POST = absent
PRODUCTION_INTEGRITY = ok
PRODUCTION_FK_VIOLATIONS = 0
PRODUCTION_CHANGED = NO
PRODUCTION_APPLY_ATTEMPTED = false
```

### 11.7 Validation

```text
Stage 3D.2 focused tests = 22 passed, 1 skipped
  skipped = Windows symlink creation unavailable; resolved-path/samefile guards passed
Reused Phase 3C/semantic/relation safety tests = 78 passed
Full pytest = 1055 passed, 1 skipped
Frontend tests = not run; no backend API contract changed
compileall = PASS
git diff --check equivalent for the four untracked Stage 3D files = PASS
```

### 11.8 Remaining blockers and STOP gate

Stage 3D.2 proves the deterministic adapter and shadow engine, but it does not grant Production authority. The remaining blockers for a later Production authorization gate are:

1. The frozen acceptance directory does not contain the original Source PDF. The payload records `archive_materialization=REQUIRED_BEFORE_PRODUCTION_APPLY`; a later gate must bind an available file at the exact Source SHA and prove archive materialization before inserting a Production Source row.
2. No explicit Node/Relation operation review exists for Pilot 6, so all otherwise accepted Node observations/candidates remain `DEFER`; rejected observations remain `REJECT`.
3. Production is still schema `0.2.1`; schema migration and non-structural Relation Evidence persistence remain separate, unauthorized work.
4. Production authorization, operator identity, backup retention, and a live apply switch are deliberately absent. The Stage 3D.2 hard block cannot be disabled.

```text
PHASE3D_STAGE3D2_COMPLETE = true
PHASE3D_ARTIFACT_CONVERGENCE_PASS = true
PHASE3D_PROMOTION_PAYLOAD_PASS = true
PHASE3D_OPERATION_GATE_PASS = true
PHASE3D_SHADOW_PREFLIGHT_PASS = true
PHASE3D_SHADOW_APPLY_PASS = true
PHASE3D_SHADOW_POSTFLIGHT_PASS = true
PHASE3D_IDEMPOTENCY_PASS = true
PHASE3D_ROLLBACK_DRILL_PASS = true

PRODUCTION_CHANGED = NO
PRODUCTION_APPLY_ATTEMPTED = false
```

Recommended next gate: design a separately authorized Stage 3D.3 Production-authorization package that first resolves the Source archive-materialization blocker and obtains explicit Node/Relation operation review. Do not enable or attempt Production apply until that gate is independently approved and qualified.
