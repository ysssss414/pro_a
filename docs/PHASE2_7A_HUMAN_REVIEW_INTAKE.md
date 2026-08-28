# Phase 2.7A — Controlled Human Review Intake / View Proposal

Acceptance date: 2026-08-28. Implementation and all acceptance gates below passed.

`PRODUCTION_PROPOSAL_WRITE_AUTHORIZED = false`

## Architecture audit

The implementation starts from `main` at
`fd58e9f6f0b22f54908637d54a10f2dcb55b6ff9` (Phase 2.6B PR #34).
`git pull --ff-only origin main` confirmed the latest remote main; main had no
configured upstream, so the remote/ref were explicit. The tracked tree was clean.
No reset occurred. Historical untracked files and the Python 3.12 environment
were retained, unstaged. Working branch: `phase2/human-review-intake`.

The following existing contracts were read before implementation:

| Contract/source | Finding and reuse |
|---|---|
| `PHASE2_6B_HUMAN_IMPACT_REVIEW.md`, `frontend/src/humanImpactReview.ts` | Export document type is `human_impact_review`, schema version is the **string** `"1"`, status must be `READY`. UI decisions are uppercase, but exported decisions are **lowercase** `no_change/minor/material/thesis`. |
| `PHASE2_4A_CURRENT_VIEW_PILOT.md`, `current_view_pilot.py` | Subject-only direct support, context metadata, unresolved needs_review, attributed guidance/judgment. Reuse `_validate_frozen_content_contract`; do not reuse the initial-pilot-only no-previous-View gate for replacements. |
| `PHASE2_4B_CURRENT_VIEW_ACTIVATION.md`, `current_view.py` | Activation/official record creation are separate, prohibited paths. Existing official content is only copied for editing. |
| `PHASE2_5B_CURRENT_VIEW_COMPARE.md`, `current_view_compare.py` | Reuse scalar/list/type-specific value comparators and field constants. Do not pretend the noncanonical draft is an official record to bypass the public historical comparator's official-only precondition. |
| `db.py`, `query.py`, `constants.py` | Reuse `CURRENT_VIEW_ORDER` and source candidate discovery; Proposal type remains `current_view_change`, levels remain `initial/minor/material/thesis`. `initial` is never selected by this intake. |
| `proposals.py` | `ProposalManager.accept()` creates official Views, starts propagation, and queues/runs side effects. It must never be called here. The existing pending persistence boundary is `Database.add_proposal`. |

No schema column or second database Proposal schema is introduced. The only
existing source change is an optional caller-owned `_conn` in `add_proposal`:
it requires an active transaction, `current_view_change`, and empty legacy
identifiers. Existing callers, relation handling, legacy impact deduplication,
acceptance, and validators retain their previous behavior.

## Review → Proposal contract

```text
READY human_impact_review JSON
  → PREPARE: strict artifact + canonical-state validation (read-only)
  → NO_CHANGE receipt OR noncanonical draft containing existing Proposal payload
  → explicit human edit of payload.proposed_current_view
  → SUBMIT: repeat validation + actual-change + frozen content validation
  → exactly one pending current_view_change Proposal in an isolated DB
  → STOP
```

`src/pro_a/human_review_intake.py` is the dedicated boundary. No new browser/API
write endpoint is added. `scripts/intake_phase2_7a.py` provides the file entry point.

The complete v1 export shape is required, including Source display metadata,
Node ID/name/type, target ID/version, decision/reason, selected Primary/Context
IDs, the candidate Claim-role snapshot, the three Thesis fields, and
`evidence_sufficiency = NOT_EVALUATED`. Unknown/missing keys, wrong types,
duplicate IDs/JSON keys, malformed JSON, nonfinite numbers, unknown decisions,
and DRAFT/STALE artifacts fail. No case conversion, trimming of saved identities,
field repair, rebase, migration, or snapshot refresh is performed.

Every reason must contain non-whitespace text. Change decisions require Primary
Evidence. Thesis additionally requires all of `invalidated_core_assumption`,
`logic_chain_failure`, and `conclusion_change` to contain text.

### PREPARE and NO_CHANGE

PREPARE uses SQLite `mode=ro`, `query_only=ON`, and one read snapshot. It checks:

- Source existence and agreement of the two artifact Source IDs;
- Node existence, active status, exact canonical name/type;
- latest **official** target ID/version using `CURRENT_VIEW_ORDER`;
- exact candidate Claim ID/role pairs using the existing candidate query;
- selected Evidence membership, current Node role, and Primary eligibility.

Candidate equality is order-independent, but never semantic/fuzzy. A change in
target produces `STALE_TARGET_VIEW`; a changed Claim ID/role snapshot produces
`CANDIDATE_EVIDENCE_CHANGED`. Missing/inactive identities and invalid selections
have explicit blocking errors.

`no_change` yields `status=INTAKE_VALID`, `action=NO_PROPOSAL`, `canonical=false`.
It is a local receipt, not an unchanged-content Proposal; SUBMIT rejects it.

Other decisions produce a file wrapper with the labels `HUMAN EDIT REQUIRED`,
`NOT CANONICAL`, and `NOT A PRODUCTION PROPOSAL`. Its `payload` retains the
existing keys:

| Key | Value |
|---|---|
| `node_id` | Reviewed Node |
| `previous_view_id`, `previous_version` | Exact target official View |
| `change_level` | `minor`, `material`, or `thesis`, without reclassification |
| `trigger_source_id` | Reviewed Source |
| `evidence_claim_ids` | Selected Primary IDs only |
| `proposed_current_view` | Deep copy of the exact target `content_json` |
| `human_review_handoff` | Validated full v1 exported Review, including reason, selections, snapshot and Thesis fields |

PREPARE never rewrites from the reason or inserts/removes citations. Consequently,
an existing official View can be a valid editing basis without being immediately
submittable. A smaller Primary selection can require human revision of content
and citations. The frozen validator is not relaxed to accept legacy content.

### Evidence and human-edit gates

Primary must be a current exact candidate with `role=subject`. Status comparison
uses the 2.6B trim/lowercase convention. The intake fails closed to the active
statuses `current`, `pending_verification`, and `disputed`; it does not score them.
The frontend explicitly excludes `needs_review/invalidated/superseded`; intake
also refuses terminal `updated/expired` and unknown statuses instead of treating
an unrecognized status as writable evidence. The frontend and frozen validators
are unchanged.

Selected Context must still have `role=context` and remains exclusively in
handoff metadata. Related stays association metadata, never Primary. Content
Evidence IDs must equal selected Primary IDs. Mixed valid/invalid citations,
unknown `CLM_...` refs, and non-primary references in direct content are blocked.
An existing subject `needs_review` Claim may be cited only in an individual
`assumptions_to_verify` or `knowledge_gaps` item explicitly marked `needs_review`.
Another item's unresolved label cannot authorize that item. No Gap/RQ is created.

Only `payload.proposed_current_view` is editable within the draft envelope. Other
payload keys/labels/legacy identifiers must match the validated handoff. Content
metadata outside the existing editable View fields must remain unchanged; no
Evidence profile/scoring metadata is synthesized.

The actual-change gate uses the existing Phase 2.5B scalar, list, and
`type_specific` comparison helpers. Whitespace-only scalar changes, list order
or duplicates, Evidence ID ordering, and `recent_change` alone do **not** satisfy
it. The blocking error is `CHANGE_DECISION_WITHOUT_VIEW_CHANGE`. No automatic
change summary is generated.

The edited content must then pass the **unchanged** pilot frozen content helper
using only selected eligible Subject Claims. This preserves citation, numeric
scope, attribution, Product dimensions and single-company scope checks. The
helper invokes pure quality methods on an uninitialized `PropagationManager`;
its constructor, execution, evidence scoring and persistence methods are not run.
This is frozen validator reuse, not propagation execution or an Evidence-quality
evaluation. Semantic correctness beyond that contract remains deferred.

### SUBMIT, idempotency and isolation

SUBMIT requires an existing explicitly isolated SQLite fixture/copy. It rejects
the configured Production DB before opening a writable connection, including
resolved aliases and hard links. Run from the project root with the trusted
`config.toml`; the guard protects that configured Production identity. It is not
a replacement for OS permissions or signed human authorization.

Within a single `BEGIN IMMEDIATE`, SUBMIT repeats **all** canonical/eligibility
gates, validates the immutable envelope and edited content, checks pending
Proposals, then uses `Database.add_proposal(..., _conn=conn)`. This prevents a
canonical writer or concurrent submit from interleaving between validation and
INSERT. Any failure rolls back the transaction.

Exact Review/payload equality is structural JSON equality: object key order and
file formatting do not matter; strings and array order remain exact. Candidate
order independence for stale detection does not turn differently ordered handoff
artifacts into a semantic identity. Repeating the exact Review/content returns
the existing pending Proposal with `created=false`, including concurrent calls.
The same Review with different pending content yields `PENDING_PROPOSAL_CONFLICT`;
no silent merge or duplicate insertion occurs. Freshness/quality checks still
run before returning an existing Proposal.

The stored Proposal has `proposal_type=current_view_change`, `status=pending`,
and `propagation_batch_id=source_impact_id=""`. Human identity never uses legacy
`source_impact_id`, timestamps, browser storage keys, or a new schema column.
The handoff is provenance, not proof of who edited the file or Production consent.

No acceptance, official View creation/mutation, legacy queue write, recovery,
propagation, relation recursion, side-effect job, IMA, LLM/RAG, Gap/RQ, semantic
deduplication, or automatic content rewriting is part of this boundary.

## Controlled CLI

Run in the repository root with the already verified Python 3.12 environment;
dependency versions are unchanged. The commands below are usage examples, not
authorization to submit smoke exports to Production.

```powershell
$env:PYTHONPATH = (Resolve-Path src).Path

# Production read-only PREPARE is allowed. Output must be a new .json file.
& .codex-phase26b-venv/Scripts/python.exe scripts/intake_phase2_7a.py prepare `
  --db workspace/pro_a.db --review path/to/review.json --output path/to/draft.json

# Manually edit only payload.proposed_current_view in the draft.
# SUBMIT requires an explicitly isolated fixture/copy, never workspace/pro_a.db.
& .codex-phase26b-venv/Scripts/python.exe scripts/intake_phase2_7a.py submit `
  --isolated-db path/to/isolated.db --draft path/to/draft.json
```

PREPARE writes a local JSON artifact exclusively (no overwriting existing files).
SUBMIT prints the pending Proposal ID and `created` flag. Errors print a structured
`BLOCKED` result to stderr and exit 2. There is no `accept`, Production override,
or downstream-execution option.

## Acceptance evidence

All INSERT correctness tests use deterministic temporary SQLite fixtures. They
reuse the frozen pilot's synthetic Claim evidence, not Production data. Autouse
execution guards forbid manager constructors, acceptance, propagation, recovery,
official View/file creation and Evidence scoring. A SQLite authorizer additionally
proves the sole successful runtime write is `INSERT proposals`. Full table-row
snapshots verify every other table remains unchanged; failure and repeat paths
also preserve rows/bytes. Injected post-INSERT failure rolls back.

| Required coverage | Result |
|---|---|
| A–F: NO_CHANGE, PREPARE, human edit, minor/material/thesis and provenance | PASS |
| G–M: target/snapshot stale, roles, removed/ineligible selected Evidence | PASS at PREPARE and SUBMIT |
| N–O: exact repeat/concurrent repeat, conflicting pending content | PASS |
| P–S: pending only, unchanged Views/impact/audit/side effects, no runtime execution | PASS |
| Strict malformed/duplicate JSON, schema/type/decision/Thesis validation | PASS |
| Frozen citation/attribution/numeric scope/Product/scope-overreach rejection | PASS |
| Production path/hardlink denial, exclusive CLI output, rollback | PASS |

| Regression | Result |
|---|---|
| Targeted `tests/test_human_review_intake.py` | **109 passed** |
| Full pytest | **493 passed**, one existing Starlette deprecation warning |
| Compileall (`src tests scripts`) | **PASS** |
| Frontend `npm.cmd test -- --run` | **9 files / 37 passed** |
| Frontend `npm.cmd run build` | **PASS** |

Backend tests ran under the previously verified Python **3.12.13** environment
with a fresh workspace-local pytest base directory and `-p no:cacheprovider`.
The full run includes existing local tests; historical untracked files were not
staged. The Starlette warning was not bypassed by changing dependencies.

### Production read-only smoke

15 cases passed against `SRC_20260814_F6E1EFAD`:

- MLCC `NODE_20260817_DABE52FE`, View `VIEW_20260826_6662B69A`, `v_20260826`:
  11 candidate Claims; all four prior 2.6B smoke exports passed PREPARE/NO_CHANGE.
- 昀冢科技 `NODE_20260826_BC260F3E`, View `VIEW_20260826_99D621B2`, `v_20260826`:
  8 subject candidates, 6 eligible Primary and 2 needs_review. Four explicitly
  nonauthoritative v1 acceptance fixtures passed PREPARE/NO_CHANGE.
- ID/version and Claim ID/role stale variants, context Primary and needs_review
  Primary were rejected without changing canonical state. Actual CLI PREPARE
  also passed. **Production SUBMIT was not invoked.**

These smoke artifacts are validation inputs, not user-approved knowledge
decisions. None was applied. Acceptance logs/artifacts remain local under
`workspace/phase2_7a_acceptance_20260828/` and are not committed.

| Production invariant | Before | Final after regression |
|---|---:|---:|
| Nodes | 294 | 294 |
| Claims | 12 | 12 |
| Sources | 2 | 2 |
| Proposals | 11 | 11 |
| Current Views | 2 | 2 |
| impact_reviews | 0 | 0 |
| impact_attempt_audit | 0 | 0 |
| side_effect_jobs | 2 | 2 |
| Knowledge Gaps / Research Questions | 0 / 0 | 0 / 0 |

All table counts, including tables not listed above, were read from SQLite and
remain unchanged. The preexisting two side-effect jobs were neither created nor
executed by intake. Integrity is `ok`, foreign-key violations are `0`, and no
database sidecar exists.

Production pre-SHA, post-smoke SHA and final post-regression SHA (SHA-256) are identical:

```text
581978e1c587b065a6eef9c980013af3de1a9e8a8781857385404c9f61105250
```

The final read-only audit rechecked all table counts, integrity, foreign keys,
SHA and sidecar absence after the full regression. `Production DB changed = NO`.
Frozen schema, validator, comparator, acceptance, propagation/recovery, frontend
and dependency files were also verified unchanged.

## Continuing boundaries

```text
DEFER_CANONICAL_CONTENT_DEDUP = true
DEFER_EVIDENCE_BOUNDARY_CONTENT_QUALITY = true
DEFER_EVIDENCE_QUALITY_METADATA = true
```

No subsequent acceptance UI, Current View activation or Production write has
been authorized or implemented by this phase.
