# Phase 3F Stage 0 Execution Contract

Status: **Stage 0 complete; planning and contract only; implementation not started**

Generated at: `2026-09-08T00:58:39.6368042Z`

## 1. Authoritative starting baseline

Phase 3F starts from the manually merged Phase 3E.2 closure and no other Git or Production state.

```text
PR_55_HEAD = c271826ee50698073a48e45120c056bac22a98dd
PR_55_MERGE_COMMIT = 37cda6063d841875a18ed41fe5bf12efe6c1889f

PHASE3F_STARTING_GIT_BASELINE = 37cda6063d841875a18ed41fe5bf12efe6c1889f
PHASE3F_STARTING_PRODUCTION_SHA256 = 3c0007f38b136686cb1e0e73e2ad2f389983f61ae2c81679fcf5067835c4eba0

LOCAL_MAIN = 37cda6063d841875a18ed41fe5bf12efe6c1889f
ORIGIN_MAIN = 37cda6063d841875a18ed41fe5bf12efe6c1889f
PRODUCTION_INTEGRITY = ok
PRODUCTION_FK_VIOLATIONS = 0
PRODUCTION_SCHEMA_VERSION = 0.2.1
PRODUCTION_PRAGMA_USER_VERSION = 0
```

The configured Production path resolves through `AppConfig.db_path` to
`workspace/pro_a.db`; repository freeze and phase documents identify the same
file as authoritative Production. The database has `meta.schema_version=0.2.1`.
It has no separate schema-version table and its SQLite `user_version` is `0`.

Before Stage 0, no tracked file was modified. `git status --short` did list
pre-existing local runtimes, test outputs, and historical untracked artifacts.
They are not part of this contract and were left untouched.

The Phase 3E.2 post-merge receipt, Production-integrity receipt, and artifact-hash
receipt all validate. They freeze:

```text
CORE_CORRECTNESS = PASS
SAFETY_PRECISION = PASS
EXTRACTION_ROBUSTNESS = PASS
FULL_AUTOMATION_GENERALIZATION = NOT_ACCEPTED
PHASE3E2_POSTMERGE_BASELINE_FROZEN = true
PHASE3F_STARTED = false
```

`PHASE3F_STARTED=false` is the inherited pre-Stage-0 state. This document starts
and completes planning only; Phase 3F implementation remains unstarted.

## 2. Scope recovery result

No document, test, or tracked source file explicitly defines a named Phase 3F or
Stage 3F.0 implementation. The repository therefore does not authorize an
implementation merely by naming this work Phase 3F.

The existing roadmap does define the continuation boundary:

- Phase 3E.1 is the single clean-PDF operational entrypoint. It freezes the
  Source, extraction, Evidence, Claim review, Node operation review, and a
  deterministic non-executable promotion preview, then stops at
  `HUMAN_REVIEW_REQUIRED`.
- Phase 3E.2 accepts bounded correctness, safety precision, and extraction
  robustness, but does not accept unrestricted automation. Conservative REVIEW
  routing is a product guarantee, not an unfinished error to tune away.
- Phase 3D already defines and proves deterministic promotion, exact baseline
  validation, shadow qualification, rollback, and a one-time Production
  executor. Its prior authorization was exact, consumed, and non-reusable.
- `PHASE3E_OPERATIONAL_INGESTION.md` explicitly permits only a later, separately
  authorized handoff that binds human decisions and an exact executable payload
  before reusing the Phase 3D executor.
- The roadmap leaves local-model preprocessing, noisy sources, OCR/multimodal,
  schema migration, IMA live integration, and higher-level review UI as separate
  future work. Their presence in backlog is not Phase 3F authorization.

## 3. Recovered Phase 3F objective and operating model

The evidence-supported Phase 3F objective is:

> Close the narrow review-to-promotion handoff for the existing clean-source
> pipeline so that each Source can proceed only through bounded human review,
> exact deterministic payload qualification, and—if separately authorized for
> that exact Source and baseline—the existing one-time Production executor.

The correct operating model is **bounded human-reviewed production ingestion**.
It is not full automation, a new generalization campaign, or local-model
infrastructure work.

```text
existing clean Source gate
  -> existing Phase 3E extraction / Proposition IR / Evidence / admission
  -> conservative Claim REVIEW and explicit human decisions
  -> existing Node operation review; parent placement remains separate
  -> deterministic Phase 3D-compatible payload
  -> isolated shadow qualification
  -> STOP
  -> separate exact per-Source Production authorization, if later granted
  -> existing one-time executor
```

Production application is a possible terminal gate, not Stage 3F.1 authority.
Current View activation remains in the existing human Proposal/resolution path
and is not an automatic side effect of Source promotion.

## 4. In scope

- Clean, text-extractable PDFs accepted by the existing Phase 3E clean-source
  gate; no second ingestion entrypoint.
- Exact reuse of the frozen Source, extraction, partition, Evidence,
  Proposition IR, semantic admission, review, and manifest contracts.
- A deterministic handoff format that binds completed Claim decisions, Node
  operation decisions, parent-placement decisions where present, reviewer
  authority, reasons, artifact hashes, repository commit, and Production
  baseline.
- Fail-closed conversion of approved decisions into the existing Phase 3D
  promotion payload model; incomplete, ambiguous, deferred, rejected, or stale
  items remain non-executable.
- Zero-LLM replay and compatibility validation on already-frozen artifacts.
- Shadow-only application to an isolated exact Production copy, with existing
  semantic diff, integrity, FK, idempotency, rollback, and restore gates.
- A later optional per-Source authorization decision using the existing one-time
  executor without reusing any consumed authorization.

## 5. Out of scope

- Unrestricted or unattended arbitrary-source ingestion.
- Any reinterpretation of Phase 3E.2 as full-automation acceptance.
- Review-threshold weakening, acceptance-threshold changes, blanket
  REVIEW-to-KEEP conversion, or Source/broker/company-specific rules.
- A parallel ingestion framework or broad refactor of the accepted pipeline.
- Local-model or second-stage model infrastructure, learned semantic
  equivalence, or a new semantic reviewer.
- New noisy-source, scanned PDF, OCR, audio/ASR, image, chart, table-ETL, or
  multimodal capability.
- Schema `0.2.2`, `relation_evidence_links`, or any schema migration.
- Automatic Relation replay, resolution of the seven Phase 3D Node DEFERs, or
  replay of the ten rejected Relations.
- IMA live writes, browser Production writes, scheduling, bulk automation, Ask,
  RAG, embeddings, or vector search.
- Automatic Proposal, Current View, propagation, Knowledge Gap, or Research
  Question mutation.
- Any Production mutation during Stage 0, Stage 3F.1, or shadow qualification.

## 6. Inherited guarantees

Phase 3F must preserve, without weakening:

1. Atomic proposition/Claim correctness and independently updateable meaning.
2. Exact Evidence alignment, Source reconstruction, and complete provenance.
3. Claim nature and attribution preservation, including future-time and expert
   or company attribution.
4. Bounded coherence/scope repair with visible review routing.
5. Precision-first structural duplicate handling and all legitimate negative
   controls.
6. Deterministic pre-call partitioning, frozen complete piece plans, ordered
   lossless reconstruction, and frozen retry-policy propagation.
7. Narrative-first table suppression and post-binding table-origin safety.
8. Exact canonical/alias/ID resolution; ambiguity never becomes CREATE.
9. Separate approval for Node identity and structural parent placement.
10. User confirmation for new Nodes and any Current View change under the
    frozen requirements.
11. No direct LLM output, advisory recommendation, or pending review decision
    may mutate Production.
12. SQLite remains the only canonical Source of Truth.

## 7. Unresolved gaps

- There is no pre-existing Phase 3F specification; the stage names and
  decomposition below are recommendations, not recovered requirements.
- The exact completed-human-review artifact schema for Phase 3E Claim, Node,
  and parent-placement records is not yet frozen.
- Compatibility between Phase 3E.1 review artifacts and the final Phase 3D
  authorization-bound payload must be proven. A thin adapter may be needed;
  no competing pipeline is justified.
- The authority and signing semantics for each review decision must be explicit.
  Delegated AI review, if ever authorized, must remain accurately labeled and
  cannot be represented as human review or Production authorization.
- Review burden can exceed 30% on complex clean PDFs. This is accepted governed
  workload; it is not authority to change thresholds or resume Phase 3E.2 tuning.
- Every later new Source still needs its own exact Source-byte, archive,
  baseline, shadow, release, and authorization evidence.

## 8. Minimal stage decomposition and acceptance gates

### Stage 3F.0 — Scope recovery and contract freeze

This document is the entire Stage 0 deliverable. No production code is changed.

Acceptance gates:

- authoritative Git, Production, and Phase 3E.2 closure baselines match;
- explicit requirements, implied requirements, and recommendations are labeled;
- the operating model does not assume full automation;
- Production remains byte-identical and cloud LLM calls remain zero;
- document and receipt checks pass.

### Stage 3F.1 — Review-to-promotion handoff qualification

This is the smallest valid next implementation/validation stage. Use an existing
frozen Phase 3E artifact set; do not ingest a new Source and do not call a model.
First prove the format gap. Implement only the smallest deterministic adapter or
validator needed to bind completed review decisions to the existing Phase 3D
payload contract.

Acceptance gates:

- exact input hashes, Source identity, repository commit, Production identity,
  and reviewer authority are bound;
- all required Claim, Node, and parent-placement decisions are complete and
  independently validated; `PENDING`, ambiguity, `DEFER`, and `REJECT` never
  become executable;
- accepted Claims do not implicitly authorize Nodes, links, Relations, or
  Current Views;
- rerunning with identical inputs produces an identical semantic payload;
- tampering, missing artifacts, baseline drift, unsupported operations, and
  invented link roles fail closed;
- the resulting payload passes existing Phase 3D validation and shadow-only
  qualification on an isolated copy;
- Production SHA remains unchanged and cloud LLM calls are zero;
- no acceptance or review threshold changes and no Source-specific rules occur.

### Stage 3F.2 — One controlled per-Source operational qualification

Only after Stage 3F.1 passes and a separate run contract authorizes one exact new
clean Source may the existing Phase 3E entrypoint call the configured cloud
model. Human review must complete before deterministic payload generation. The
payload must pass the Stage 3F.1 handoff and isolated shadow qualification.

Acceptance gates:

- clean-source gate, deterministic partitioning, provenance, and all frozen
  correctness/safety tests pass;
- actual review burden and decisions are reported without threshold tuning;
- human decisions are exact, complete, and accurately attributed;
- the Phase 3D-compatible payload and shadow receipt pass all baseline,
  collision, diff, integrity, FK, idempotency, and rollback gates;
- Production remains unchanged; qualification grants no reusable authority.

### Stage 3F.3 — Optional exact one-time Production apply

This stage is not authorized by this contract. If separately requested after a
successful Stage 3F.2 release freeze, it must use a new immutable authorization
for the exact payload, Source, commit, database baseline, schema, archive target,
review identities, and operation counts.

Acceptance gates:

- explicit user authorization is created after release freeze and is not
  inferred from payload, review, or prior authorization;
- the existing one-time executor, fixed journal/receipt location, backup,
  allowlisted transaction, post-write semantic diff, integrity/FK checks, and
  rollback/uncertain-state rules are preserved;
- the authorization is consumed exactly once and grants no continuous or generic
  Production authority;
- no unapproved Current View, Relation, IMA, propagation, schema, or other side
  effect occurs.

## 9. Production mutation policy

Stage 0 and Stage 3F.1 are strictly read-only for Production. Stage 3F.2 is also
shadow-only. Copying the database for isolated qualification does not authorize
the configured Production file or Production archive.

Only a separately authorized Stage 3F.3 may mutate Production, and only through
the existing one-time executor. The payload is never authorization. A new Source
requires a new baseline freeze, shadow qualification, immutable authorization,
backup, transaction, receipt, post-write QA, and terminal consumption record.

## 10. LLM-call policy

- Stage 0: zero cloud/model calls.
- Stage 3F.1: zero cloud/model calls; frozen-artifact replay only.
- Stage 3F.2: cloud extraction may occur only under a separately frozen,
  cost-bounded single-Source run contract using the existing Phase 3E path.
- No LLM is permitted in review binding, payload generation, Production
  preflight, apply, rollback, or postflight.
- Local-model preprocessing/review is not authorized by this contract.

## 11. Rollback and STOP conditions

STOP before mutation or further work if any of the following occurs:

- Git main, Production SHA/schema/counts/sidecars, Source SHA, or any bound
  artifact differs from its frozen value;
- SQLite integrity is not `ok` or any FK violation exists;
- an inherited correctness, safety, partition, provenance, duplicate, or review
  negative control regresses;
- a required human decision is missing, ambiguous, stale, or inaccurately
  attributed;
- progress would require threshold weakening, Source-specific logic, a second
  pipeline, schema migration, local-model infrastructure, or another unapproved
  architectural expansion;
- the payload cannot be consumed by the existing Phase 3D boundary without
  inventing operations, links, relations, or authority;
- shadow qualification, backup identity, exact semantic diff, idempotency,
  rollback, or restore proof fails;
- no new exact Production authorization exists, or a journal is incomplete,
  failed, or uncertain.

For a live apply failure, preserve the existing Phase 3D rule: restore both the
database and newly materialized Source state from the exact backup; if exact
restoration cannot be proven, mark the journal `UNCERTAIN` and refuse automatic
retry.

## 12. Exact recommended next stage

```text
RECOMMENDED_NEXT_STAGE = PHASE3F_STAGE1_REVIEW_TO_PROMOTION_HANDOFF_QUALIFICATION
RECOMMENDED_NEXT_STAGE_OBJECTIVE = PROVE_AND_MINIMALLY_CLOSE_THE_PHASE3E_REVIEW_TO_PHASE3D_PAYLOAD_GAP_USING_FROZEN_ARTIFACTS_ZERO_LLM_AND_SHADOW_ONLY_VALIDATION
```

This stage is smaller and more reversible than running another Source, adding a
reviewer/model, or seeking Production authority. It tests the only missing
operational bridge directly identified by the existing contracts.

## 13. Evidence classification

| Classification | Evidence | Contract consequence |
|---|---|---|
| Explicit | `docs/ROADMAP.md`: no S-M authorization; further automation needs a separate architectural phase and newly frozen contract | Phase 3F cannot inherit automation acceptance |
| Explicit | `docs/PHASE3E2_GOVERNED_AUTOMATION_BOUNDARY.md` and closure receipts | Keep conservative review; do not claim full generalization |
| Explicit | `docs/PHASE3E_OPERATIONAL_INGESTION.md` | Reuse the clean-PDF path; stop at human review; later handoff may reuse Phase 3D only after exact decisions/payload freeze |
| Explicit | `docs/PHASE3D_PRODUCTION_PATH_PROMOTION.md` and `docs/PHASE3D_ONE_TIME_PRODUCTION_EXECUTOR.md` | Reuse deterministic payload, shadow, backup, transaction, receipt, and one-time authorization boundaries |
| Explicit | `docs/REQUIREMENTS_FROZEN.md` | Preserve Source/Claim/Node/View semantics, provenance, user confirmation, time, nature, and role rules |
| Explicit | `tests/test_operational_ingestion.py` | Promotion preview is non-executable and executor-incompatible; Node review reuses exact Phase 3D resolution |
| Explicit | Phase 3E.2 semantic, duplicate, and partition test modules | Preserve correctness, legitimate negative controls, and deterministic partition/retry behavior |
| Explicit | Phase 3D promotion, authorization, execution, and final-qualification tests | Fail closed on drift/tampering/unsupported operations and preserve exact one-time execution safety |
| Implied | Phase 3E ends at pending review while Phase 3D begins from bound decisions and an executable payload | The narrow missing bridge is review-to-promotion handoff qualification |
| Implied | Local-model, noisy-source, UI, IMA, schema, and Current View work remain separate backlog | They are not Phase 3F Stage 0/1 requirements |
| Recommendation | Name the first gate Stage 3F.1 and validate on existing frozen artifacts before a new Source | Smallest reversible next step; zero LLM and no Production mutation |
| Recommendation | Reserve Stage 3F.2 for one new clean Source and Stage 3F.3 for an optional one-time apply | Keeps run authorization and Production authority independent |

## Stage 0 receipt

```text
PHASE3F_STAGE0_STARTED = true
PHASE3F_STAGE0_COMPLETE = true

STARTING_GIT_BASELINE = 37cda6063d841875a18ed41fe5bf12efe6c1889f
STARTING_PRODUCTION_SHA256 = 3c0007f38b136686cb1e0e73e2ad2f389983f61ae2c81679fcf5067835c4eba0

GIT_BASELINE_VERIFIED = true
PRODUCTION_BASELINE_VERIFIED = true
PHASE3E2_CLOSURE_VERIFIED = true

EXISTING_PHASE3F_SPEC_FOUND = false
PHASE3F_OBJECTIVE = BOUNDED_HUMAN_REVIEWED_CLEAN_SOURCE_REVIEW_TO_PROMOTION_HANDOFF
PHASE3F_SCOPE_SOURCE = EXISTING_ROADMAP_PHASE3E_PHASE3D_AND_PHASE3E2_CLOSURE_WITH_LABELED_RECOMMENDATIONS

FULL_AUTOMATION_ASSUMED = false
PRODUCTION_CHANGED = false
NEW_SOURCE_INGESTED = false
CLOUD_LLM_CALLS = 0

RECOMMENDED_NEXT_STAGE = PHASE3F_STAGE1_REVIEW_TO_PROMOTION_HANDOFF_QUALIFICATION
RECOMMENDED_NEXT_STAGE_OBJECTIVE = PROVE_AND_MINIMALLY_CLOSE_THE_PHASE3E_REVIEW_TO_PHASE3D_PAYLOAD_GAP_USING_FROZEN_ARTIFACTS_ZERO_LLM_AND_SHADOW_ONLY_VALIDATION

FILES_CREATED = docs/PHASE3F_STAGE0_EXECUTION_CONTRACT.md
FILES_MODIFIED = none
TEST_RESULTS = GIT_DIFF_CHECK_PASS; NEW_DOCUMENT_WHITESPACE_CHECK_PASS; BASELINE_RECEIPT_HASH_VALIDATION_PASS; PRODUCTION_READ_ONLY_INTEGRITY_PASS

STOP_REASON = PHASE3F_STAGE0_COMPLETE_STOP_BEFORE_IMPLEMENTATION
```
