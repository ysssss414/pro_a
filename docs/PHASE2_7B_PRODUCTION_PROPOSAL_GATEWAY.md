# Phase 2.7B — Controlled Production Proposal Gateway & Read-Only Review

Date: 2026-08-28. Status: **complete**.

Production write path implemented and isolated-copy validated. No live Production Proposal was created during Phase 2.7B acceptance.

```text
LIVE_PRODUCTION_PROPOSAL_APPLY_AUTHORIZED = false
PHASE2_7A_BEHAVIOR_CHANGED = false
SCHEMA_CHANGE = NO
```

## Objective and pre-implementation audit

The boundary is READY Human Impact Review → deterministic PREPARE → explicit human content edit → configured Production pending Proposal → read-only review. This phase does not activate a Current View.

Fetched `origin`, fast-forwarded `main`, and created `phase2/production-proposal-gateway` from `ac04a15a11949935849c229821206df01d9764ca`. This is the Phase 2.7A PR #35 merge commit; the tracked tree was clean. Historical untracked files, environments and acceptance artifacts were retained.

Audited the roadmap, Phase 2.6B/2.7A/2.4A/2.4B documents, intake, database, ProposalManager, query/API, constants, frozen Current View validation, comparator and Explorer's View/Compare/Source/Human Impact Review surfaces before implementation. The requested `PHASE2_5B_DETERMINISTIC_HISTORICAL_COMPARE.md` does not exist; the repository's authoritative document is `PHASE2_5B_CURRENT_VIEW_COMPARE.md`.

Findings:

- `submit_review(..., isolated=True)` explicitly denies the configured Production path, including the same physical file. Keep that boundary; do not add an `isolated=False` authority switch.
- `Database.add_proposal(..., _conn=conn)` supports the caller's transaction for this nonlegacy proposal and already initializes pending status, empty resolved time, `{}` result and empty legacy identifiers. No schema change is needed.
- `ProposalManager.accept()` is outside this boundary: it initializes runtime managers, creates official Views, changes statuses and can execute propagation/file/IMA side effects. Neither gateway nor read model calls or instantiates it.
- There was no existing Proposal read endpoint. Reuse `ReadOnlyQuery`'s `mode=ro` / `query_only` connection.
- Reuse `storage.sha256_file` / `write_json` and workspace backup conventions. Existing ingestion receipts are domain-specific, and `write_proposal` emits acceptance instructions; neither is appropriate for this pending-only receipt.

## Architecture and Production authority

`human_review_intake.py` now exposes small internal transaction helpers for the existing validation, pending lookup and insertion. Both the old isolated submit and the new `production_proposal_gateway.py` call the same helpers. The frozen validator and the prior isolated authorization remain unchanged.

The dedicated CLI requires an explicit subcommand:

```powershell
python scripts/phase2_7b_proposal_gateway.py preview --draft <file>
python scripts/phase2_7b_proposal_gateway.py apply-production --draft <file>
```

Use the project's configured Python environment with `src` importable. Both commands load the current working directory's `config.toml`; there is no `--db`, caller-supplied database path, config override, or default write action. Invoke from the intended project root. Isolated acceptance uses a separate directory with its own config pointing only to the copy. It does not authorize the real project database.

`preview` uses a read-only snapshot, creates no backup/receipt and is never a reusable permission token. **Do not run real Production `apply-production` without a separately approved real human review and edited artifact. No such authorization was present in this task.**

### Write contract and stale gates

APPLY uses one `BEGIN IMMEDIATE` transaction. Before INSERT it revalidates the READY v1 handoff, Source identity, active Node identity/name/type, latest official View ID/version, exact candidate Claim ID/role snapshot, selected roles and Primary Claim eligibility against current SQLite state. It also validates the immutable draft envelope, deterministic actual content change and frozen Current View content contract.

Primary Evidence must be subject evidence with eligible status. Context stays context; related and unresolved `needs_review` Claims cannot become Primary. Metadata-only edits fail actual-change validation. MINOR, MATERIAL and THESIS do not authorize automatic rewriting or evidence selection. An exact prepared NO_CHANGE receipt returns `NO_PROPOSAL` without INSERT, backup or receipt file creation.

Stable errors are inherited from intake, including `STALE_TARGET_VIEW`, `CANDIDATE_EVIDENCE_CHANGED`, `INELIGIBLE_EVIDENCE`, identity errors, unchanged-content errors and `PENDING_PROPOSAL_CONFLICT`. No auto-rebase, remapping or role upgrade occurs.

The only permitted business mutation is:

```text
INSERT proposals
proposal_type = current_view_change
status = pending
payload.human_review_handoff = valid Phase 2.6B/2.7A provenance
propagation_batch_id = ""
source_impact_id = ""
resolved_at = ""
result_json = "{}"
```

A narrow SQLite authorizer permits reads, transaction operations, integrity/FK checks and direct `INSERT main.proposals`. It denies UPDATE/DELETE, other table INSERTs, trigger writes, schema/attachment changes, write PRAGMAs and extension loading. It is not a general permissions framework. Validation and the existing insert helper enforce proposal type, payload and pending status.

### Idempotency, backup and receipt

The same handoff and exact payload return the existing pending ID with `created=false`. A different payload for that handoff blocks; it never overwrites or merges. `BEGIN IMMEDIATE` serializes concurrent exact submissions. Failures before/during insertion roll back canonical mutation.

For a new proposal, create an exclusive timestamped backup under `workspace/backups` before INSERT. A separate read-only SQLite connection performs an online backup while the writer holds its reserved lock; backing up the writer's active transaction can deadlock. Backup integrity/FK and pre-write row equivalence are verified in acceptance. SQLite backup file headers need not be byte-identical to the source.

After commit, a JSON receipt under `workspace/generated/receipts` records timestamp, resolved configured DB path, pre/post file SHA-256, backup location, proposal ID, created flag, target Node/View ID/version, decision, trigger Source, Evidence Claim IDs, integrity and FK results. Exact duplicates create no second proposal or backup; their receipt has `created=false` and an empty backup location.

Receipt/hash I/O failure after commit is explicitly reported as `PROPOSAL_COMMITTED_RECEIPT_FAILED` (CLI exit 3), with the known pending proposal ID; it is not reported as a rollback. Other blocked CLI errors exit 2. Receipt/backup artifacts are local and excluded from git.

## Read-only Review contract

Only two GET endpoints are added:

```text
GET /api/view-proposals?limit=50&offset=0
GET /api/view-proposals/{proposal_id}
```

The list contains pending `current_view_change` rows with valid frozen human provenance, matching payload identity and empty legacy identifiers. Malformed payloads, unrelated types and historical legacy proposals are excluded before pagination. Ordering is `created_at DESC, proposal_id DESC`. No old row is migrated, relabeled or mutated. Missing/ineligible detail identities return 404.

Summary/detail expose public Node, Source, proposal and target View metadata, decision/reason, Thesis fields, proposed content, selected Primary/Context Evidence and original candidate role snapshot. They do not expose archive paths, receipt paths or database paths.

The detail's BASE is the proposal's stored previous official View ID/version, not whichever View is now latest. TARGET is plain proposed content, never a fabricated official View record. A pure `compare_view_content` helper shares Phase 2.5B semantics: trimmed exact scalars, exact list added/removed/unchanged and deterministic `type_specific` structure. The historical official-to-official comparator keeps its existing checks and evidence/source comparison.

### Computed canonical alignment

| State | Meaning |
| --- | --- |
| `CURRENT` | The handoff still matches canonical state and selected Primary eligibility. |
| `STALE_TARGET_VIEW` | Target official ID/version no longer matches the latest official View. |
| `CANDIDATE_EVIDENCE_CHANGED` | The exact candidate Claim-role snapshot changed. |
| `EVIDENCE_INELIGIBLE` | Selected evidence is no longer eligible. |
| Other stable intake identity codes | Source/Node is missing, inactive or changed. |

This is computed at read time. A stale row still has DB status `pending`; reading never updates status or rebases content. If its original official BASE is unavailable, detail returns no BASE/diff and the UI explains why.

### Explorer

The default Explorer remains available; `Human View Proposals` opens a separate small review surface. It provides list loading/error/empty states, bounded pagination, selection with abort/late-response guards, content diff, reason/Thesis, Evidence roles/status/attribution, snapshot details and Source navigation.

The selected item explicitly displays `PENDING — NOT OFFICIAL CURRENT VIEW` and `No acceptance action in Phase 2.7B`. The queue correctly shows `No pending Human View Proposals` on real Production. There are no Accept, Approve & Activate, Reject, Modify, Save, Submit, Rebase or Generate with AI controls, including disabled placeholders. All new client calls are GET.

## Acceptance results

| Gate | Result |
| --- | --- |
| Phase 2.7B targeted backend | 89 passed |
| Existing Phase 2.7A regressions | 109 passed |
| Full pytest | 582 passed |
| Frontend | 10 files / 49 tests passed |
| Frontend build | Passed (`tsc --noEmit && vite build`) |
| Compileall | Passed for `src tests scripts` |
| Production-copy write smoke | Passed; exactly one pending insertion |
| Real Production preview / stale rejection / GET smoke | Passed; no live APPLY |
| Edge browser smoke / visual check | Passed; Production empty queue, copy detail and Source navigation |

Backend coverage includes decisions, shape/canonical/stale/role/status/actual-change/frozen-content gates, exact/conflicting/concurrent submissions, injected rollback, backup and post-commit receipt failure, narrow authorizer/trigger/schema boundaries, unchanged non-Proposal tables, legacy exclusion, stable pagination, GET-only API and computed stale states. Existing runtime guards fail any acceptance/propagation/recovery/IMA/LLM or official View call.

Frontend coverage includes MINOR/MATERIAL/THESIS, reason/Thesis, pending/nonofficial labels, before/proposed content, Evidence, Source navigation, stale/missing/error states, aborted requests and absence of mutation controls/requests. The preexisting Starlette test-client deprecation and Vite >500 kB chunk warning remain; dependencies were not changed.

Windows used the verified Python 3.12.13 environment, isolated TEMP/TMP plus fresh pytest basetemp and `-p no:cacheprovider`, and `npm.cmd`. Browser smoke reused installed Edge with cached Playwright CLI. Network records contain only GET; development StrictMode aborts were followed by successful 200 responses. Browser console error count was zero. Screenshots were visually inspected; owned smoke sessions/services were stopped.

### Isolated Production-copy write

`ISOLATED_PRODUCTION_COPY = true`. A read-only online backup of Production was used with an isolated config. The synthetic edited artifact explicitly states that it is only an acceptance fixture, not an approved human decision and not authorized for live APPLY.

The actual CLI gateway path created `PROP_20260828_E3A0D54E` in the copy only: Proposal count 11 → 12, pending, unresolved, empty result/legacy identifiers. All non-Proposal tables stayed row-equivalent; the pre-insert backup matched the copy's prior rows. Query/API returned one CURRENT proposal with actual content diff, consumed successfully by the real frontend. No official View or side effect was created. Fixtures also explicitly cover unchanged `relation_evidence_links`; the existing Production schema has no such table and was not migrated.

Local, uncommitted evidence is in `workspace/phase2_7b_acceptance_20260828/` (audit, test logs, copy, receipt, pre/post JSON, network records) and `output/playwright/phase27b-closure/` (screenshots).

### Real Production invariants

Real Production was used only for preview and reads. Before and after SHA-256 are both:

```text
581978e1c587b065a6eef9c980013af3de1a9e8a8781857385404c9f61105250
```

Actual counts were queried, not assumed from historical numbers:

| Table | Pre | Post |
| --- | ---: | ---: |
| claim_node_links | 19 | 19 |
| claim_relations | 0 | 0 |
| claims | 12 | 12 |
| current_views | 2 | 2 |
| ima_objects | 0 | 0 |
| impact_attempt_audit | 0 | 0 |
| impact_reviews | 0 | 0 |
| knowledge_gaps | 0 | 0 |
| meta | 1 | 1 |
| node_aliases | 737 | 737 |
| node_relations | 181 | 181 |
| nodes | 294 | 294 |
| processing_jobs | 5 | 5 |
| proposals | 11 | 11 |
| research_questions | 0 | 0 |
| side_effect_jobs | 2 | 2 |
| source_node_links | 3 | 3 |
| source_relations | 0 | 0 |
| sources | 2 | 2 |

Both integrity checks are `ok`, FK violations are 0, and no WAL/SHM/journal sidecars are present. Human-review pending queue count remains 0. No live Production Proposal was created.

## Deferred scope and stop boundary

```text
DEFER_PROPOSAL_MODIFY = true
DEFER_PROPOSAL_ACCEPTANCE = true
DEFER_CANONICAL_CONTENT_DEDUP = true
DEFER_EVIDENCE_BOUNDARY_CONTENT_QUALITY = true
DEFER_EVIDENCE_QUALITY_METADATA = true
```

Proposal modify/revision/supersede, reject/accept, official View activation, propagation, Impact Recovery and browser writes remain deferred. So do Claim semantic dedup, Relation generation, RQ/Gap lifecycle, IMA integration and LLM/RAG Ask. The roadmap's Proposal “modify then accept” backlog remains open.

Phase 2.7C is technically ready for a separate scoped request, but is neither started nor authorized here. Stop after delivery of the Phase 2.7B Draft PR.
