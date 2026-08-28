# Phase 2.7C — Human Proposal Resolution & Direct Current View Activation

Acceptance date: 2026-08-28. Status: **complete**. Implementation, automated tests, isolated-copy lifecycle, Playwright browser smoke, and the final live Production read-only audit passed.

```text
LIVE_PRODUCTION_RESOLUTION_APPLY_AUTHORIZED = false
```

## Scope and boundary

This phase starts from `main` at `ac326a963924a0781b3c587b11d1d4bfb674eeca`, including the Phase 2.7B merge, on branch `phase2/human-proposal-resolution`. It adds an independent resolver for an explicit human decision over a pending `current_view_change` Proposal. The resolver does not instantiate or call `ProposalManager`, `PropagationManager`, Impact Recovery, IMA, LLM, side-effect jobs, markdown materialization, or `write_official_view_file`.

The browser remains a read-only review surface. It can draft and download a local resolution JSON file only. There is no POST, PUT, PATCH, or DELETE route for proposals, and no browser action performs a canonical write. Canonical resolution is an explicit CLI operation with the configured database identity; this acceptance never invoked that operation against live Production.

## Resolution artifact contract

`src/pro_a/human_proposal_resolution.py` accepts only a finite JSON object with exactly these keys:

```json
{
  "document_type": "human_view_proposal_resolution",
  "schema_version": "1",
  "status": "READY",
  "proposal_id": "PROP_...",
  "action": "ACCEPT",
  "reason": "A nonempty human reason",
  "proposal_snapshot": {
    "proposal_type": "current_view_change",
    "target_node_id": "NODE_...",
    "created_at": "...",
    "payload": {"...": "exact stored Proposal payload"}
  }
}
```

The stored snapshot is compared structurally against the current Proposal. Missing, extra, duplicate, malformed, nonfinite, legacy, or changed snapshot fields fail closed. A terminal Proposal accepts only the exact same action, reason, snapshot, and stored resolution metadata; a different terminal decision is blocked as `PROPOSAL_RESOLUTION_CONFLICT`.

The resolver repeats the 2.7A/2.7B canonical, target freshness, candidate Claim-role, Subject Evidence, actual-content-change, and frozen Current View gates. ACCEPT requires `canonical_alignment=CURRENT`; REJECT is allowed when the review target has become stale. No automatic rebase or content rewrite occurs.

## Transaction and write authority

The narrow SQLite authorizer and one `BEGIN IMMEDIATE` transaction enforce:

- ACCEPT: one direct `INSERT current_views` through `create_official_view_record`, followed by `UPDATE proposals` of only `status`, `result_json`, and `resolved_at`;
- REJECT: only that `UPDATE proposals`;
- no changes to `payload_json`, the Proposal `reason`, `source_impact_id`, or `propagation_batch_id`;
- no writes to Nodes, Claims, Sources, relations, impact/audit tables, side-effect jobs, IMA objects, Gaps, RQs, processing jobs, or schema metadata;
- no generated Current View Markdown file and no `path` in stored result metadata.

ACCEPT stores `result_json.human_resolution` with the complete artifact and resolution reason, plus the direct View ID/version and `activation_scope=DIRECT_VIEW_ONLY`. REJECT stores the same human provenance with `activation_scope=NO_VIEW_CREATED`. Exact replay is idempotent and creates no second View. Backup failure or any other pre-commit failure rolls back the transaction. A post-commit receipt failure reports `RESOLUTION_COMMITTED_RECEIPT_FAILED` with Proposal ID, action, and backup location; it does not claim rollback.

View version, revision date/sequence, previous View identity, and latest ordering come from `create_official_view_record` and the existing Current View contract, including multiple revisions on the same day. Canonical activation complete; filesystem materialization deferred.

## CLI and read API

The explicit entry point is:

```powershell
$env:PYTHONPATH = (Resolve-Path src).Path
& .codex-phase26b-venv/Scripts/python.exe scripts/phase2_7c_proposal_resolution.py preview --resolution path/to/resolution.json
& .codex-phase26b-venv/Scripts/python.exe scripts/phase2_7c_proposal_resolution.py apply-production --resolution path/to/resolution.json
```

`preview` is read-only. `apply-production` is an explicit configured-Production authority and was not run against the live database in this phase.

`GET /api/view-proposals?status=pending|accepted|rejected` exposes each valid state. Detail includes the exact proposal snapshot, terminal resolution metadata, the original target View alignment, and (for ACCEPT) the newly activated direct View ID/version. Terminal rows with invalid resolution provenance or a mismatched official View are excluded from both list and detail. The API remains GET-only.

## Isolated Production-copy acceptance

`workspace/phase2_7c_acceptance_20260828/copy_lifecycle.py` created two fresh isolated SQLite copies from the audited Production baseline. Each copy first used the real 2.7B gateway to create a pending Proposal and then used the real 2.7C CLI.

| Isolated path | Proposal count | Current Views | Result |
|---|---:|---:|---|
| ACCEPT | 11 → 12 → 12 | 2 → 3 | direct official View, no propagation or Markdown |
| REJECT | 11 → 12 → 12 | 2 → 2 | terminal rejection, no View |

The ACCEPT copy preserved all rows outside `proposals` and `current_views`; the REJECT copy preserved all rows outside `proposals`. Both passed integrity and foreign-key checks and left the live Production database untouched. The accepted Proposal is `PROP_20260828_3894867B`; its direct official View is `VIEW_20260828_25D4D004` (`v_20260828`). The rejected Proposal is `PROP_20260828_54AE966D`. These are synthetic, isolated-copy fixtures, not live human authorization. Exact replay, conflict, stale, malformed artifact, authorizer, trigger, rollback, receipt, API, and runtime-manager guard cases are covered by `tests/test_human_proposal_resolution.py`.

## Verification

| Gate | Result |
|---|---|
| Full backend pytest | **657 passed**; existing Starlette/httpx deprecation warning |
| Phase 2.7C targeted backend | **75 passed** |
| Phase 2.7B / 2.7A regressions | **89 / 109 passed**; combined targeted run **273 passed** |
| Frontend | **11 files / 56 tests passed** |
| Frontend `tsc --noEmit && vite build` | **PASS**; existing >500 kB chunk warning |
| Compileall (`src tests scripts`) | **PASS** |
| ACCEPT / REJECT isolated-copy lifecycle | **PASS** |
| Live Production preview/read-only audit | **PASS**; no resolution apply |
| Playwright Edge browser smoke | **PASS** — live empty queue; isolated pending export, accepted history/View navigation, rejected history |

Browser acceptance used only GET requests. Local ACCEPT export re-fetched the pending Proposal detail and downloaded the exact READY snapshot; read-only CLI PREVIEW against that isolated pending copy returned `PREVIEW_VALID`. No exported browser artifact was applied. Accepted history opened the exact new official View version; rejected history displayed no View creation. Neither terminal state exposed resolution controls. All four browser pages had zero console errors and warnings. Development StrictMode cancelled initial GETs; their replacements returned 200.

Evidence remains local and uncommitted under `workspace/phase2_7c_acceptance_20260828/` (test logs, `production_pre.json`, `production_post.json`, lifecycle receipts, and `browser_final_result.json`). Five screenshots under `output/playwright/phase27c-closure/` were visually reviewed. The dedicated Edge session and all eight temporary API/Vite listeners were closed before the final audit. Both resolved-copy SHA values still match their resolution receipts; the pending-copy SHA still matches its pre-resolution backup.

Live Production was read before and after with the existing read-only audit. SHA-256 remained:

```text
581978e1c587b065a6eef9c980013af3de1a9e8a8781857385404c9f61105250
```

All table counts remained identical, read from the live database before and after acceptance:

```json
{
  "claim_node_links": 19, "claim_relations": 0, "claims": 12,
  "current_views": 2, "ima_objects": 0, "impact_attempt_audit": 0,
  "impact_reviews": 0, "knowledge_gaps": 0, "meta": 1,
  "node_aliases": 737, "node_relations": 181, "nodes": 294,
  "processing_jobs": 5, "proposals": 11, "research_questions": 0,
  "side_effect_jobs": 2, "source_node_links": 3, "source_relations": 0,
  "sources": 2
}
```

Integrity is `ok`, foreign-key violations are `0`, and no WAL/SHM/journal sidecars exist. The live Human View Proposal pending queue remains empty.

## Deferred and stop boundary

Proposal modification/revision, browser writes, propagation, Impact Recovery, IMA/LLM, Gap/RQ lifecycle, semantic Claim deduplication, Relation generation, canonical content-quality expansion, and Evidence-quality metadata remain deferred. Phase 2.7D is a technical handoff only and is not started or authorized by this phase.

```text
DEFER_PROPOSAL_MODIFY = true
DEFER_PROPAGATION = true
DEFER_CURRENT_VIEW_FILE_MATERIALIZATION = true
DEFER_IMA_SYNC = true
DEFER_BROWSER_PRODUCTION_WRITE = true
DEFER_CANONICAL_CONTENT_DEDUP = true
DEFER_EVIDENCE_BOUNDARY_CONTENT_QUALITY = true
DEFER_EVIDENCE_QUALITY_METADATA = true
```
