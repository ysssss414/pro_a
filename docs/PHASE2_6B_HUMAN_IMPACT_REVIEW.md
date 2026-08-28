# Phase 2.6B — Human Impact Review Surface

## Status

`PHASE2_6B_COMPLETE = true` — technical acceptance, implementation commit, branch push, and Draft PR verification passed.

This phase adds a local-only, non-canonical review surface on top of the deterministic Phase 2.6A Source → Claim → Node → Current View candidates. It records a human handoff artifact in browser `localStorage` and exports JSON from the browser. It does not write Production knowledge.

Branch: `phase2/human-impact-review`

Base: `9967328` — merged Phase 2.6A commit (PR #33).

Implementation commit: `928f033cf741a7b92bac2d7197f104869b4498d6` — `feat: add human impact review surface`.

Draft PR: [#34 — Phase 2.6B: Human Impact Review](https://github.com/ysssss414/pro_a/pull/34), verified `OPEN`, `isDraft=true`, base `main`, head `phase2/human-impact-review`. The pushed implementation SHA matched the local commit before closing acceptance. This follow-up changes acceptance documentation only.

## Mandatory architecture audit

The legacy impact pipeline is present:

```text
LEGACY_IMPACT_PIPELINE_PRESENT = true
```

The existing schema and code include `impact_reviews`, `impact_attempt_audit`, `PropagationManager`, `run_batch()`, `ImpactRecoveryService`, proposal creation, and Current View acceptance paths. The legacy queue can process `pending`, `deferred`, `retry`, and `needs_llm` states. Human Review deliberately does not reuse that queue.

```text
WRITE_IMPACT_REVIEWS = false
CALL_PROPAGATION_MANAGER = false
CREATE_PROPOSAL = false
```

No backend endpoint or schema change is required: Phase 2.6A read APIs already provide the Source, candidate Node, Claim-role snapshot, and latest official View identity. The review surface fetches the existing read-only Node Current View endpoint for the full target content.

## Frozen review contract

The UI offers exactly four human decisions:

```text
NO_CHANGE | MINOR | MATERIAL | THESIS
```

The initial decision is empty; no automatic classification, recommendation, score, direction, or preselection is performed. `MINOR`, `MATERIAL`, and `THESIS` require at least one eligible `subject` Claim. `context` and `related` Claims cannot be selected as Primary Evidence. `needs_review`, invalidated, and superseded Claims are not Primary Evidence eligible.

The UI keeps the frozen attribution boundary visible:

- Subject Claims are direct candidate Evidence and may be selected as Primary when eligible.
- Context Claims are marked `Context only` and can only be selected as Context Evidence.
- Related Claims are marked `Association only` and cannot become Primary Evidence.

`reason.trim().length > 0` is required for every READY artifact. `THESIS` additionally requires `invalidated_core_assumption`, `logic_chain_failure`, and `conclusion_change`. Material and Thesis governance reminders are displayed, but `evidence_sufficiency` remains `NOT_EVALUATED`; no evaluator is reimplemented.

## Local draft and export

Drafts are stored only in browser `localStorage` under a key containing:

```text
source_id + node_id + target_view_id
```

The surface explicitly labels every draft `Local draft — not canonical`. A draft stores the original exact Claim ID/role snapshot, target official View ID/version, decision, reason, selected evidence, Thesis structured reason, and local status (`DRAFT`, `READY`, or `STALE`).

`STALE TARGET VIEW` is raised when the latest official View ID/version differs from the draft target. `CANDIDATE EVIDENCE CHANGED` is raised when the exact Claim ID/role snapshot differs. Either condition blocks READY export; there is no automatic migration or fuzzy comparison. Opening the target View saves the current local state first so it can be recovered when the review is reopened.

`Export Review JSON` creates a browser download only. The artifact is a deterministic `human_impact_review` JSON handoff with `schema_version = "1"`, `status = "READY"`, source and Node identity, target official View identity, lowercase decision, reason, selected evidence, original candidate Claim-role snapshot, Thesis fields, and `evidence_sufficiency = "NOT_EVALUATED"`.

```text
NON-CANONICAL HANDOFF ARTIFACT
```

The export is not an accepted Proposal, official Current View, Production impact review, Source of Truth record, or propagation instruction. Phase 2.7A intake is not implemented or authorized.

## Verification fixture

The isolated frontend contract fixture covers:

- Case A: reasoned `NO_CHANGE` is READY without Primary Evidence;
- Case B: `MINOR` is blocked without eligible Subject Evidence and READY with one;
- Case C: `MATERIAL` shows governance-only sufficiency and remains `NOT_EVALUATED`;
- Case D: `THESIS` requires all three structured reason fields;
- Case E: context-only candidates can close with `NO_CHANGE`, but not a change-level READY artifact;
- Case F: changed target View is `STALE` and cannot export;
- Case G: changed Claim role is `CANDIDATE EVIDENCE CHANGED` and cannot export;
- Case H: local drafts for different Source/Node/View keys do not overwrite one another.

Component coverage verifies the Source Detail entry, empty decision, role labels, disabled Primary selection boundary, local save, and browser-side export path.

## Production safety

The review surface has no write API and no Production DB connection. It does not call `PropagationManager`, `ImpactRecoveryService`, Proposal creation, Current View creation/acceptance, Gap/RQ generation, traversal, semantic matching, LLM, RAG, or IMA. Production SHA and read-only SQLite integrity checks remain acceptance gates.

## Deferred and prohibited

```text
DEFER_CANONICAL_CONTENT_DEDUP = true
DEFER_EVIDENCE_BOUNDARY_CONTENT_QUALITY = true
DEFER_EVIDENCE_QUALITY_METADATA = true
```

Still prohibited in this phase: Current View mutation, Proposal intake, Production `impact_reviews` writes, automatic change classification, Evidence sufficiency evaluation, propagation, parent/child or related-node recursion, automatic Gap/RQ generation, semantic matching, LLM/RAG/chatbot/IMA work, and Phase 2.7A.

## Acceptance block

Validated on 2026-08-28 against the real Production database and existing FastAPI API. All required technical and Git publication gates passed; the PR remains Draft.

```text
Human Review Surface = PASS
Decision contract = PASS
Claim role boundary = PASS
Primary Evidence selection = PASS
Local draft = PASS
Review export = PASS
Target View stale protection = PASS
Candidate Evidence stale protection = PASS
Legacy pipeline isolation = PASS

Frontend tests = PASS (9 files / 37 tests; repeated after smoke)
Frontend build = PASS (repeated after smoke)
Full pytest = PASS (384 passed, 1 warning, 93.63 seconds)
Compileall = PASS (src, tests, scripts)
Production browser smoke = PASS

Backend changed = NO
Schema changed = NO
Write API added = NO
impact_reviews changed = NO
Proposals changed = NO
Current Views changed = NO
Production DB changed = NO

Production pre-SHA = 581978E1C587B065A6EEF9C980013AF3DE1A9E8A8781857385404C9F61105250
Production post-SHA = 581978E1C587B065A6EEF9C980013AF3DE1A9E8A8781857385404C9F61105250
Integrity check = ok (before and after)
Foreign-key violations = 0 (before and after)

PHASE2_7A_READY = YES
```

### Recovered test environment

Python executable: `.codex-phase26b-venv/Scripts/python.exe` in the repository, using Python **3.12.13**. The original `.venv` Python 3.13 executable no longer exists. The temporary environment reuses all **38 dependency versions** recorded in the original `.venv` distribution metadata; no project dependency definition or application code was changed for recovery. `pip check` reports no broken requirements. The temporary environment remains untracked and excluded from staging.

Full pytest used the existing `tests` collection (including the unchanged historical untracked `tests/test_direct_impact_candidates.py`, which was not staged), an explicit fresh workspace basetemp, workspace-local `TEMP`/`TMP`, and no cache provider:

```powershell
$env:PYTHONPATH = (Resolve-Path src).Path
$env:TEMP = (Resolve-Path workspace/phase2_6b_acceptance_20260828/temp).Path
$env:TMP = $env:TEMP
& ./.codex-phase26b-venv/Scripts/python.exe -m pytest -q -p no:cacheprovider --basetemp=workspace/phase2_6b_acceptance_20260828/pytest_tmp_01
& ./.codex-phase26b-venv/Scripts/python.exe -m compileall -q src tests scripts
```

The one pytest warning is the existing Starlette `httpx` TestClient deprecation. The frontend production build retains the non-blocking bundle-size warning. Neither warning was worked around by changing dependencies or production code.

### Real Production browser evidence

The existing `python -m pro_a.api --config config.toml` served the actual `workspace/pro_a.db` on `127.0.0.1:8000`; Vite ran with `npm.cmd run dev -- --host 127.0.0.1 --port 5176 --strictPort`. Port 5173 was occupied and its existing process was left untouched. An isolated Playwright Edge session entered through Explorer search → MLCC Knowledge Detail → Sources → Open Source → Review Impact. No fixture response or modified API response was used.

- Source: `SRC_20260814_F6E1EFAD`; 12 existing Claims.
- MLCC: `NODE_20260817_DABE52FE`, target `VIEW_20260826_6662B69A`, version `v_20260826`; 3 Subject and 8 Context Claims. Context-only selection could not satisfy the Primary Evidence requirement.
- 昀冢科技: `NODE_20260826_BC260F3E`, target `VIEW_20260826_99D621B2`, version `v_20260826`; 8 Subject Claims, including 2 `needs_review` Claims with disabled Primary selection. These official candidates have no Related Claims; the frozen Related boundary remains covered by the contract fixture and implementation audit.
- All four decisions produced actual browser downloads. Parsed JSON was checked against the real Source, Node, target View ID/version, exact candidate Claim ID/role snapshot, selected Primary/Context IDs, reason, and `NOT_EVALUATED` sufficiency. Thesis additionally required and exported all three structured fields.
- Saved drafts survived reload; unsaved edits did not replace saved drafts. Open Current View saved the local draft before navigation. Company and MLCC drafts occupied separate keys and did not overwrite each other.
- Stale tests changed only localStorage draft snapshots: target version, target identity (including old-key fallback), candidate Claim identity, and candidate role. After reload through the same legal entry path, each compared against fresh unmodified Production API responses, displayed the expected warning, saved only local `STALE` status, and disabled export. No target or evidence snapshot was silently rebased; restoring the original local snapshot returned to READY. These checks do not mutate Production or assert continuous background refresh.
- The browser recorded **174 real API GET requests** across 14 distinct endpoints, **0 non-read request attempts**, **0 console errors**, **0 page exceptions**, and **0 HTTP errors**. A browser network guard rejected non-GET/HEAD requests if attempted; none were attempted. No legacy propagation, recovery, Proposal, or impact-review endpoint was called.

The SQLite checks used `mode=ro` plus `PRAGMA query_only=ON`. Counts remained 294 Nodes, 12 Claims, 2 Sources, 2 Current Views, 11 Proposals, and 0 impact reviews; no SQLite sidecar files appeared. Exact file SHA equality establishes that existing rows and schema remained unchanged.

Local acceptance evidence is retained outside staging in `workspace/phase2_6b_acceptance_20260828/` (environment snapshot, pytest/build logs, and DB audit JSON) and `output/playwright/phase26b-closure/` (browser audit, four downloaded JSON artifacts, scripts, and screenshots). Historical untracked files were not changed or staged.

Phase 2.7A remains planned; readiness after closure is not authorization to implement it.
