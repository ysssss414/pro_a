# Phase 3B — IMA Integration Operational Acceptance

Date: **2026-08-28**. Status: **complete**.

## Scope and baseline

Phase 3B operationalizes the existing `IMAClient` for **Source original → IMA Source KB**. It does not implement a new client and does not alter canonical knowledge semantics. Current View upload/materialization remains deferred; Proposal acceptance, side-effect jobs, propagation and browser mutation remain outside this phase.

The work branch is `phase3/ima-integration-acceptance`, based on main containing Phase 3A merge `5c4a547e63016a05e4b7c0b84482b0e1f4284729`. Production was read only before and after acceptance. Baseline and post-audit were computed from `load_config().db_path`, without hardcoded row-count assertions:

| Check | Before and after |
|---|---|
| SHA-256 | `581978e1c587b065a6eef9c980013af3de1a9e8a8781857385404c9f61105250` |
| Tables / counts | 19 tables; all counts identical |
| `ima_objects` | 0 rows; contents identical |
| Source IMA fields | 2 Sources; both media/KB fields empty before and after |
| SQLite checks | integrity `ok`; foreign-key violations `0`; no `-wal`, `-shm` or `-journal` sidecars |

The real IMA API was not called. No `create_media`, COS upload, `add_knowledge`, duplicate-name probe, KB listing or other IMA read/write was authorized. Production Source Detail GET smoke was run with `IMAClient.call` blocked and returned only safe status fields.

## Architecture audit and frozen contracts

The audit covered `docs/IMA_INTEGRATION.md`, Phase 3A acceptance, Roadmap, frozen requirements, IMA/config/pipeline/database/schema/storage/receipts/query/API/CLI, the example config and project metadata. Existing `MEDIA_TYPES`, `SIZE_LIMITS`, `_media_type`, `_preflight`, duplicate check, create-media, COS SDK and add-knowledge are reused. Existing tables and fields are sufficient; no migration was required.

The following are unchanged: schema, Claim/Node/Relation contracts, Current View contract and validators, parser/LLM extraction, evidence matching, Proposal/Human Review, Current View materialization, propagation, direct-impact behavior and ingestion job semantics. A final AST/file audit confirmed unchanged frozen modules and all pipeline methods other than the IMA delegate and its warning branch.

## Preflight, identity and states

`preview_source_sync` is deterministic and performs zero remote calls, LLM calls or DB writes. It checks, in order, enabled state, credential availability, `upload_originals`, Source KB, Source existence, archived original, existing IMA media type and existing size limit. It reports stable statuses: `READY`, `DISABLED`, `CREDENTIALS_MISSING`, `UPLOAD_ORIGINALS_DISABLED`, `SOURCE_KB_NOT_CONFIGURED`, `SOURCE_NOT_FOUND`, `ARCHIVE_FILE_MISSING`, `UNSUPPORTED_MEDIA_TYPE`, `FILE_TOO_LARGE` and `LOCAL_DATABASE_UNAVAILABLE`.

Source identity is `local_object_type=source`, `local_object_id=source_id`, configured Source KB, with stable remote title `[SRC_xxx] original_filename`. It never uses the mutable analyzed Source title. The parser format contract and IMA media contract remain separate.

Before any remote request, a local consistency gate checks every mapping for that Source. A nonempty Source media/KB pair, one matching `ima_objects` row with `status=synced`, and the same nonempty media ID returns `IDEMPOTENT` with zero remote calls and zero DB writes. Partial fields, multiple/mismatched KB mappings, mismatched media IDs, `synced` empty media and unknown states return `LOCAL_MAPPING_CONFLICT` and are never auto-fixed.

The small persisted state set is:

- `synced`: complete remote chain and local commit, always nonempty media ID;
- `sync_failed`: failure proven before remote creation, retryable by an explicit later call;
- `remote_state_uncertain`: a reservation, interruption or post-create failure requiring reconciliation;
- `name_conflict_unresolved`: same remote name without verified media identity, always empty media ID.

A same-name response is never treated as synced, even when the title contains the Source ID. Source fields remain unchanged. `ima_objects` rows are updated in place or inserted only when missing; `mapping_id` survives safe retry.

## Stages and failure model

The observable stages are `preflight`, `duplicate_check`, `create_media`, `cos_upload`, `add_knowledge` and `local_mapping_commit`. `IMAError` keeps string compatibility while carrying a stable code, stage, known media ID and uncertainty bit. HTTP timeout/connection failures, HTTP errors, invalid JSON, nonzero IMA codes and missing response data are sanitized fixed errors. No client ID, API key, COS secret, token, header, body or upstream exception is included.

`create_media` must return a nonempty media ID, bucket, region, COS key and all temporary credentials before COS is attempted. Add-knowledge must return a nonempty media ID or the validated create ID. A failed duplicate check is a known pre-mutation failure. After create-media is entered, including unknown timeout outcomes, the state is conservatively uncertain. COS, add-knowledge and local commit failures are uncertain; no blind retry is scheduled.

Remote IMA/COS mutation and SQLite cannot form one distributed transaction. The manager commits an `remote_state_uncertain` reservation before remote work, records a known media ID before COS, then commits Source IMA fields and mapping success atomically only after all stages complete. A concurrent invocation sees the reservation and stops. If the final commit fails, the reservation/known ID remains and prevents a duplicate upload. There is no distributed rollback claim.

## CLI, write authority and receipts

The only standalone operations are:

```powershell
python scripts/phase3b_ima_sync.py preview-source --source-id SRC_xxx
python scripts/phase3b_ima_sync.py sync-production-source --source-id SRC_xxx
```

Neither accepts `--db` or `--config`; the explicit Production operation uses `load_config().db_path`. Preview writes only its local operation receipt. The sync operation is the explicit authority for a standalone Production integration-metadata mutation. No default command uploads, and the CLI does not initialize schema or create processing jobs.

The SQLite authorizer permits only Source `ima_media_id`/`ima_kb_id` updates and integration-field INSERT/UPDATE on `ima_objects`. It denies canonical tables, titles/ranks/metadata/status/modes, jobs, proposals, Views, impacts, relations, schema changes, attachments, deletes and trigger side effects. Existing pipeline ingestion delegates to the shared helper and keeps canonical ingestion successful when IMA fails.

Every operation creates a separate JSON receipt with timestamp, operation, Source/original identity, target KB/folder, preflight, mapping before/after, attempted stages, result classification, known nonsecret media ID and final status. It never records archive paths, credentials, headers or COS fields. An initial receipt is written before remote work; a receipt write failure never claims rollback of a completed remote/local operation.

## Read-only observability

Source Detail adds an allowlisted `ima_sync` object containing status, target configured, mapped and a fixed message. Explorer adds a compact IMA section with only **Synced**, **Not synced** or **Needs reconciliation**. No credentials, local archive path, media/COS key, remote probe or write endpoint is exposed. All browser requests in the isolated run were GET; there are no IMA POST/PUT/PATCH/DELETE routes or Sync/Retry/Delete controls.

## Simulator and acceptance evidence

The test-only HTTP/COS simulator is in-process and generated at runtime; no real credential, cloud fixture or runtime artifact is committed. It covers success, timeout, connection failure, HTTP 400/500, invalid JSON, nonzero code, missing data, malformed create responses and COS behavior. Mapping tests cover idempotency, all consistency conflicts, unresolved same-name, stage failures, safe retry, uncertain retry blocking, interruption, concurrent reservation, final commit failure, stable mapping ID and authorizer denial.

The real pipeline was exercised in isolated SQLite workspaces with the existing Phase 3A generated fixtures. PDF and DOCX completed full sync chains; TXT, Markdown, XLSX and PPTX were preflighted or exercised through failure states. Pipeline IMA outage and same-name paths still produced valid analyzed Sources, claims and receipts with warnings. No LLM, real model, real IMA or propagation was used.

Verification completed:

- targeted Phase 3B/Phase 3A/pipeline/query/API tests: **234 passed** in the final targeted run;
- full pytest: **841 passed**, one pre-existing Starlette/httpx deprecation warning;
- frontend tests: **72 passed**;
- frontend build: passed (existing Vite >500 kB advisory only);
- Python compileall: passed;
- Edge browser: six Source states rendered; screenshots visually inspected; console errors/warnings 0; 30 API requests recorded, all GET (8 expected React effect cancellations).

## Rollout limits and handoff

This is simulator-validated operational readiness, not live authorization. The following are fixed for this phase:

```text
LIVE_IMA_WRITE_AUTHORIZED = false
LIVE_IMA_READONLY_PROBE_AUTHORIZED = false
DEFER_CURRENT_VIEW_IMA_SYNC = true
DEFER_CURRENT_VIEW_FILE_MATERIALIZATION = true
DEFER_SCANNED_PDF_OCR = true
DEFER_IMAGE_MULTIMODAL = true
DEFER_PDF_TABLE_STRUCTURE_EXTRACTION = true
DEFER_CHART_EXTRACTION = true
DEFER_ASK_UNTIL_CORPUS_EXPANSION = true
DEFER_PROPOSAL_MODIFY = true
DEFER_PROPAGATION = true
DEFER_BROWSER_PRODUCTION_WRITE = true
DEFER_CANONICAL_CONTENT_DEDUP = true
DEFER_EVIDENCE_BOUNDARY_CONTENT_QUALITY = true
DEFER_EVIDENCE_QUALITY_METADATA = true
```

An uncertain mapping needs operator reconciliation against an authorized remote view before a separately governed repair. No reset, delete, lookup or repair command is provided. A future Phase 3C Controlled Live Corpus Expansion Pilot is ready for planning only; it is not authorized or started.
