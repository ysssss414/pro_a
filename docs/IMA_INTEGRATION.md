# IMA Source Integration — operational contract

## Boundary and configuration

IMA is an external mirror and reading surface. SQLite remains the canonical knowledge store. An IMA outage must not invalidate an ingested Source, its Claims, Node links or analysis.

Phase 3B operationalizes **Source original → IMA Source KB**, reusing `IMAConfig`, `IMAClient`, the existing media rules and `ima_objects`. No new schema, knowledge semantics, scheduler, remote cleanup or reconciliation automation is introduced.

**Current View → IMA is deferred.** Its legacy path depends on Markdown materialization, which remains deferred. Do not invoke `ProposalManager.accept`, side-effect jobs, propagation or View materialization for Source sync. Legacy Current View code is unchanged; its same-name handling is not covered by the new Source contract.

Use existing `[ima]` settings: `enabled`, `upload_originals`, `source_kb_id` and optional `source_folder_id`. Choose the KB/folder explicitly. Credentials continue to come only from environment variables `IMA_OPENAPI_CLIENTID` and `IMA_OPENAPI_APIKEY`. Do not put their values in TOML, SQLite, receipts, logs, screenshots or Git. Preflight returns availability, never values. Source Detail only receives target KB context and does not read credential properties.

`IMAClient.call()` converts timeout, connection failure, HTTP errors/redirects, invalid JSON, nonzero IMA codes and malformed envelopes into `IMAError`. Upstream bodies, error messages, headers and exception text are never included. Redirects are not followed with credential headers. COS exceptions are replaced with fixed messages. Temporary COS credentials are used only in memory; COS keys/credentials are not returned by upload or persisted in mappings/receipts. `IMAError` preserves `str(error)` compatibility and adds `code`, `stage`, known `media_id` and `remote_state_uncertain`.

## Deterministic local preview

`preview_source_sync(cfg, source_id)` performs no HTTP/COS/LLM calls or database writes. It reads Source/mapping identity in one read-only SQLite transaction and uses `IMAClient._media_type` / `_preflight`; there is no second extension/size/MIME implementation.

| Preflight status | Meaning |
|---|---|
| `READY` | All configuration, Source and archived-file checks pass |
| `DISABLED` | IMA disabled |
| `CREDENTIALS_MISSING` | Environment credentials unavailable |
| `UPLOAD_ORIGINALS_DISABLED` | Source-original upload disabled |
| `SOURCE_KB_NOT_CONFIGURED` | Source KB missing |
| `SOURCE_NOT_FOUND` | No local Source |
| `ARCHIVE_FILE_MISSING` | Archived original unavailable or not a file |
| `UNSUPPORTED_MEDIA_TYPE` | Extension absent from existing IMA mapping |
| `FILE_TOO_LARGE` | Existing IMA limit exceeded |
| `LOCAL_DATABASE_UNAVAILABLE` | DB unreadable; this operation never initializes it |

Configuration/Source/file checks run in the listed order. Preview returns Source ID/original name/stable title, available media type/file size, target KB/folder, folder-configured boolean, local mapping status, mapping snapshots and `would_upload`. No archive path or credential is returned. This is not a remote authentication, permission, quota or connectivity test.

IMA media support and Phase 3A parser support are separate. Legacy Office/image/audio extensions can have IMA mappings without parser support. Existing limits remain 10 MiB for spreadsheet/Markdown/text/XMind media, 30 MiB for images and 200 MiB otherwise. No OCR, image interpretation or table reconstruction is added.

## Identity and local consistency

Mapping identity: `(local_object_type='source', local_object_id=source_id, ima_kb_id=configured Source KB)`. Remote title: **`[SRC_xxx] original_filename`**, independent of the mutable analyzed Source title.

Before any remote call, the shared gate checks all Source mappings, including other KBs. Nonempty Source media/KB fields and exactly one consistent `synced` mapping with the same nonempty media ID yield `IDEMPOTENT`: zero remote calls, duplicate checks and DB writes. This local result does not require credentials or the archived file to remain available. It does not assert the remote object still exists; remote deletion detection is not implemented.

Partial Source fields, media/KB mismatches, another configured KB, multiple mappings, `synced` with empty media ID, and unknown/inconsistent legacy states yield `LOCAL_MAPPING_CONFLICT`. Nothing is overwritten or automatically repaired. Folder is not part of the unique identity; changing the configured folder does not move an already mapped object.

A remote duplicate name without valid local mapping yields **`REMOTE_NAME_EXISTS_UNRESOLVED`**, persisted as `name_conflict_unresolved` with empty media ID. Source IMA fields stay unchanged. A title containing the Source ID is not proof of remote identity. Source upload attempts always check duplicate names; the legacy `skip_same_name=false` switch cannot bypass Source safety.

## Persisted states and retry boundary

| `ima_objects.status` | Meaning | Another upload allowed? |
|---|---|---|
| `synced` | Complete upload plus atomic local mapping/Source commit, nonempty media ID | No; local idempotent result |
| `sync_failed` | Proven failure before remote creation, empty media ID | Explicit later invocation may retry |
| `remote_state_uncertain` | Reserved/in-flight, interrupted, or creation may have happened | No; reconcile first |
| `name_conflict_unresolved` | Remote name exists without verified media identity | No; reconcile first |

Existing rows are updated, not replaced; safe failure → success retains `mapping_id`. `synced_at` is populated only on success; failure timestamps/stages belong to receipts. Known media IDs can remain on uncertain mappings but are never copied to `sources` before full success.

### Remote/local atomicity

SQLite and IMA/COS cannot share an atomic transaction. There is no distributed rollback.

1. Repeat local gates under `BEGIN IMMEDIATE`. Commit an `ima_objects` reservation with `remote_state_uncertain` **before any remote call**, releasing the writer lock before network work. Concurrent calls see the reservation and stop.
2. Execute duplicate check → create media → COS upload → add knowledge. Persist the known create-media ID before COS. Validate create-media fields (`media_id`, bucket, region, COS key, temporary credentials) before the SDK call. Missing fields yield `CREATE_MEDIA_INVALID_RESPONSE` and uncertainty, without COS continuation.
3. After success, update mapping and only `sources.ima_media_id/ima_kb_id` in one transaction, after checking reservation/Source identity has not changed. The final nonempty media ID can come from add-knowledge or validated create-media output.
4. A duplicate-check failure can replace the reservation with `sync_failed`. Any create-media request failure, including timeout or invalid response with no known ID, is conservatively uncertain. COS/add-knowledge failure and final local commit failure are also uncertain. No automatic upload retry occurs.

A process dying even before creation leaves a conservative reservation requiring reconciliation. Final commit failure leaves the earlier reservation/known ID intact, preventing another create-media call. Unreadable storage yields `mapping_after=null`, not an invented mapping. Concurrent mapping changes stop the operation without repair/overwrite.

Diagnostic stages: `preflight`, `duplicate_check`, `create_media`, `cos_upload`, `add_knowledge`, `local_mapping_commit`. A recorded remote stage means it was entered, not that the server applied it.

## Explicit standalone CLI and receipts

Run from the repository with its Python environment and `src` on `PYTHONPATH` (or installed package):

```powershell
python scripts/phase3b_ima_sync.py preview-source --source-id SRC_xxx
# Only after separate live authorization:
python scripts/phase3b_ima_sync.py sync-production-source --source-id SRC_xxx
```

No action defaults to upload. Neither command accepts `--db` or `--config`; both use `load_config().db_path`. Isolated acceptance invokes the internal operation with a temporary config, never a caller-proclaimed Production DB. This CLI never calls `init_schema`, the general CLI `_ctx`, migrations or ingestion jobs.

A column-level SQLite authorizer permits only INSERT `ima_objects`, updates to its integration result fields (not mapping/object/KB identity), and UPDATE of the two Source IMA columns. Deletes, schema changes, attachments, trigger side effects and all knowledge/Proposal/Impact/View/job writes are denied.

Each operation writes a separate `generated/receipts/phase3b_*.json`: timestamp, operation, Source/original identity, target KB/folder, preflight, mapping before/after, attempted remote stages, classification, known media ID and final status. Preview can write this artifact, never SQLite/remote state. An initial receipt is written before upload; an unwritable receipt directory prevents remote work. An initial artifact left after interruption is not completion evidence. Final receipt failure reports `SYNC_RECEIPT_WRITE_FAILED` without claiming committed sync rollback. If configuration/receipt storage itself is unavailable, CLI emits a fixed local-operation error; no artifact can be guaranteed on unwritable storage.

Exit 0 means ready preview or synced/idempotent; disabled, failed, unresolved, uncertain and receipt-error outcomes exit 2.

## Pipeline and Explorer

Existing ingestion `_sync_source_to_ima` delegates after archival/Source insertion. Existing ingestion configuration still governs this path; keep ingestion/watch processes disabled during unapproved live exercises. Exact-SHA duplicates and mode upgrades remain `not_reuploaded` and do not retry IMA.

IMA failure/uncertainty/name conflict leaves canonical ingestion valid and adds a warning. Same-name warning: `IMA remote name exists but local media identity is unresolved.` Stable receipt `ima_status`: `disabled`, `synced`, `failed`, `remote_state_uncertain`, `name_conflict_unresolved`, `not_reuploaded`. No exception stacks enter normal receipts.

Source Detail exposes only computed `ima_sync` status, target-configured and mapped booleans, and a fixed message. No remote probing, media/COS keys, credentials, archive path or raw mapping is returned. Explicit test DBs can receive target context separately; normal API startup obtains it from existing config. Explorer's small **IMA** section displays **Synced**, **Not synced**, or **Needs reconciliation**. No Sync/Retry/Delete/Credentials controls or browser IMA write endpoint exist.

## Live rollout and reconciliation limits

Phase 3B is simulator acceptance only. Neither live writes nor live read-only IMA probes were authorized or performed. Simulator success does not validate actual permissions, remote response shapes, SDK/cloud connectivity, quota or remote visibility.

Before a separately authorized live pilot: select one Source/KB/folder, confirm credentials locally without printing them, stop unrelated ingestion/watch processes, save a DB backup, inspect preview/mapping consistency, then explicitly approve the one-Source remote/local write. Review the receipt and independently verify remote visibility via an authorized read/UI check. Do not broaden the corpus, delete remote objects, clear uncertain mappings, or restore an old DB and retry upload as a shortcut: DB restoration cannot undo remote creation.

Uncertain/conflicting identities require operator reconciliation with remote evidence before separately governed repair. Phase 3B provides no repair/reset/lookup/deletion command and never guesses media IDs. Phase 3C — Controlled Live Corpus Expansion Pilot is ready for planning only, not execution.

`DEFER_CURRENT_VIEW_IMA_SYNC = true`; `DEFER_CURRENT_VIEW_FILE_MATERIALIZATION = true`.
