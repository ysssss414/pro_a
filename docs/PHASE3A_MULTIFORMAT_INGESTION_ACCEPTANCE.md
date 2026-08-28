# Phase 3A — Multi-format Source Ingestion Operational Acceptance (PDF-first)

Date: **2026-08-28**. Status: **complete**.

Baseline main: `3da39ee09abcbbc9e30b17f2a8e6f7cd29ad1669` (PR #37 / Phase 2.7C merge). `git switch main`, `git fetch origin`, `git pull --ff-only origin main`, status/log and ancestor checks completed before implementation. One pull encountered a TLS handshake failure and an authorization attempt timed out; a retry succeeded without disabling certificate validation. Work branch: `phase3/multiformat-ingestion-acceptance`.

This is operational acceptance of existing parsers, not a new PDF parser or a semantic-contract redesign.

## Phase 2 closure

**Phase 2 Knowledge Exploration & Interaction Layer = complete.**

| Capability | Closure |
|---|---|
| Search | complete |
| Browse | complete |
| Trace | complete |
| Research | complete |
| Human Current View maintenance workflow | complete, through Phase 2.7C |
| Ask | deferred, not cancelled |

Ask is intentionally deferred until corpus breadth and Source coverage improve.
Building an answer layer over the current very small Production corpus would not
provide meaningful retrieval/answer quality validation.

`DEFER_ASK_UNTIL_CORPUS_EXPANSION = true`.

## Architecture audit before implementation

| Audited files / surface | Baseline and decision |
|---|---|
| `src/pro_a/parsers.py` | TXT/MD/Markdown/CSV, pypdf PDF, python-docx DOCX, openpyxl XLSX/XLSM and python-pptx PPTX already existed. Reuse extraction loops and their markers; retain `(text, source_type)` callers. |
| `src/pro_a/pipeline.py` | `process_file` creates a running job, checks exact SHA, parses standard/deep before moving/removing the Inbox copy, archives originals, optionally uploads them, then analyzes. Archive skips parsing. Failed parsing records a failed job without creating a Source. Preserve these branches. |
| Duplicate / upgrade | Same/lower analyzed mode consumes an incoming duplicate without analysis. Archive → standard → deep reuses the Source/original and follows existing reanalysis semantics; higher-mode reanalysis may append Claims. Do not introduce content or Claim dedup. |
| `src/pro_a/analyzer.py` | Main chunking used `chunk_text`; truncation recovery recursively split with the same helper. Evidence uses NFKC + Markdown unescape + whitespace normalization followed by exact substring matching against full Source text. Keep the validator and recovery intact; add a separate locator resolver. |
| `src/pro_a/prompts.py`, `src/pro_a/llm.py` | Existing extraction fields, output-truncation category and bounded recovery/retry behavior remain unchanged. No prompt or LLM client changes. |
| `src/pro_a/audit.py`, `src/pro_a/receipts.py` | Source audit already reads metadata and Claim validation. Extend receipt summaries, not the audit model; do not store parsed full text in receipts. |
| `src/pro_a/storage.py` | Original is moved to dated archive with Source ID prefix and original extension. Preserve bytes and path contract. |
| `src/pro_a/ima.py` | Upload takes archived `Path`, derives type/MIME/size and then uses existing upload flow. All accepted formats already map to IMA media types. No IMA implementation changes. |
| `src/pro_a/db.py`, `schema.sql` | Existing `sources.metadata_json`, `claims.structured_json` and `processing_jobs` suffice. No migrations or schema edits. |
| `src/pro_a/query.py`, `src/pro_a/api.py` | Read model uses SQLite `mode=ro` + `query_only`; Source Detail explicitly selects fields without local paths. Add typed allowlisted diagnostics and locators, never arbitrary metadata serialization. |
| `src/pro_a/config.py` | Existing workspace root, char limit, LLM/IMA switches and receipt settings suffice; no new settings. |
| `tests/`, `tests/fixtures/` | Reuse `stability_helpers.make_config`, existing validation/ingestion tests and temporary SQLite. New format fixtures are generated, not user materials or committed binaries. |
| README, Roadmap, `REQUIREMENTS_FROZEN.md`, `PHASE1_FREEZE.md` | Phase 1 semantic boundaries are fixed. Add Phase 2 closure and Phase 3 planning without modifying frozen documents. |

Before edits, 16 existing archive/pipeline/Analyzer tests passed. Final AST comparison confirmed unchanged Evidence canonicalization, exact matching, Claim/Relation validators, atomicity normalization and nested truncation recovery. Frozen documents, schema, DB, prompts, LLM, IMA, storage and config files have no diff. Historical untracked files were retained and excluded from the commit.

## Parse diagnostics contract

`parse_source_with_diagnostics(path) -> ParsedSource(text, source_type, diagnostics)` wraps the existing parser implementations. `parse_source(path) -> tuple[str, str]` remains the compatibility entrypoint. Direct parser functions still return text.

| Field | Definition |
|---|---|
| `format` | Lowercase file extension; XLSM stays `xlsm` here while `source_type` remains `xlsx`. |
| `parser` | Stable library identifier, without runtime version or exception message. |
| `locator_scheme` | Format-specific scheme; no artificial text page numbers. |
| `file_size` | Original file bytes. |
| `unit_type` | `document`, `page`, `paragraph_or_table_row`, `row`, or `slide`. |
| `total_units` | Units visited by the existing extraction loops. DOCX counts paragraphs plus table rows; XLSX counts iterated rows across all sheets. Table/sheet header markers are not extra content units. |
| `text_units` | Units with at least one non-whitespace payload character. |
| `error_units` | PDF page extraction exceptions. Other parser exceptions still fail the parse. |
| `empty_units` | `total_units - text_units - error_units`. Blank units are distinct from failed units. |
| `extracted_chars` | Non-whitespace payload characters, excluding generated locator markers, table cell separators and diagnostic error markers. |
| `empty_extraction` | Extracted payload character count is zero. |
| `partial_parse` | At least one page failed and at least one unit has valid text. Blank pages alone do not imply a partial parse. |
| `image_only_or_no_extractable_text` | PDF has pages but no extracted payload text. It does **not** establish that the PDF is scanned. |

No timestamps, local paths, credentials, raw page text or unstable exception messages enter diagnostics. XLSX workbooks are closed after reading.

### PDF quality and mode behavior

- Continue using pypdf. Successful pages retain `[[PAGE:n]]` and their text. Page exceptions retain their page marker plus stable `[PAGE_PARSE_ERROR]`, and increment `error_units`.
- A partial PDF with some valid text can continue through standard/deep; metadata and receipt carry diagnostics and warnings.
- Any standard/deep empty extraction fails with `PARSE_TEXT_EMPTY` **before LLM, Source creation or Inbox consumption**. A failed upgrade preserves the existing archived Source. File-level parser exceptions likewise retain the Inbox request and record failure.
- PDF pages with zero text produce the warning `No extractable text; OCR/multimodal parsing required.` OCR is not implemented. Zero-page PDFs also fail closed, without claiming image-only content.
- `archive` does not parse or require extractable text. No diagnostics are fabricated for archive or legacy Sources. Exact duplicates are not reparsed; standard/deep duplicate receipts reuse available stored diagnostics.
- Successfully parsed Sources without an available LLM retain diagnostics and `needs_llm` status under the existing lifecycle. The broader ingestion pipeline is not made into a new all-or-nothing transaction framework.

## Format support matrix

| Extensions | `source_type` | Parser | Locator scheme / example | Acceptance |
|---|---|---|---|---|
| `.txt` | `txt` | builtin.text | TEXT | extraction, diagnostics, exact locator and chunks |
| `.md`, `.markdown` | `md`, `markdown` | builtin.text | TEXT | same; old unmarked chunk semantics retained |
| `.csv` | `csv` | builtin.text | TEXT | plain decoded text, not reconstructed tables |
| `.pdf` | `pdf` | pypdf | PAGE / `PAGE:3` | real generated PDF, page-error mocks, standard/deep smoke |
| `.docx` | `docx` | python-docx | PARA / TABLE / `TABLE:1:ROW:2` | generated paragraphs/rows, standard/deep smoke |
| `.xlsx`, `.xlsm` | `xlsx` | openpyxl | SHEET / ROW / `SHEET:Capacity:ROW:3` | multiple sheets/rows, XLSM extension compatibility; XLSX standard/deep smoke |
| `.pptx` | `pptx` | python-pptx | SLIDE / `SLIDE:2` | multiple slides/text shapes, standard/deep smoke |

Legacy `.doc/.xls/.ppt` remain unsupported by the parsers. No new runtime dependencies were added. Tiny PDF fixtures use the existing pypdf writer with an ASCII text stream; page errors use mocks. Office fixtures are built dynamically in temporary directories with existing dependencies. No large or real Source files are committed.

## Locator and chunking contract

Existing deterministic, human-readable markers remain unchanged:

```text
[[PAGE:n]]
[[PARA:n]]
[[TABLE:n]]
[[TABLE:n:ROW:n]]
[[SHEET:name]]
[[SHEET:name:ROW:n]]
[[SLIDE:n]]
```

`chunk_source_text` greedily packs complete locator units within `max_chunk_chars`. An oversized unit falls back to newline/character splitting; it does not repeat markers or duplicate content. The newline immediately after a marker is not chosen as a soft split that needlessly separates the marker from its body. The PDF leading separator stays with its first page when the limit permits, avoiding a whitespace-only initial prompt for an oversized first page. Concatenating all chunks reconstructs the original text exactly and in order. A limit smaller than a complete marker fails explicitly instead of breaking the marker or exceeding the configured limit. The limit is still a Source-character limit, not a tokenizer or total prompt-token budget.

Unmarked text delegates to the original `chunk_text`. Analyzer main Source chunking uses the new helper; output-truncation recovery still uses the original helper with its existing recursion bounds. Recovery can split text internally; deterministic Evidence location always uses the **full Source**, not a fragment or LLM-supplied pointer.

## Deterministic Evidence location

`resolve_evidence_locator(full_text, evidence_excerpt)` uses the existing `canonicalize_text` normalization and exact substring membership within marker-free units. It never calls a model, uses fuzzy/semantic matching, changes the Evidence verdict, or selects the first of several unit matches.

| Match | Stored value under `structured_json.validation.source_locator` |
|---|---|
| Exactly one locator unit | `{"status":"resolved","locator":"PAGE:3"}` |
| Multiple units | `{"status":"ambiguous","locators":["PAGE:1","PAGE:3"]}` in Source order |
| No unit match, empty excerpt or excerpt spanning units | `{"status":"unresolved"}` |
| Exact unmarked text | `{"status":"resolved","locator":"TEXT"}` without invented line/page number |

Repeated occurrences in the same unit still resolve to that unit. The page-error marker is not Evidence payload for locator resolution. All existing `claims.evidence_pointer` values, including empty ones, remain untouched. Locator status describes position, not truth, evidence sufficiency or semantic quality. Frozen Claim/Node/Relation/Current View/Proposal contracts and the existing Evidence validator remain unchanged.

## Persistence, receipts and read surface

Source diagnostics are merged into `sources.metadata_json.parse_diagnostics`, preserving other top-level metadata. The analysis update retains the diagnostics alongside `summary`, `analysis_quality` and `source_references_unresolved`. No Source text column or new schema is introduced.

Standard/deep receipts include `source_type`, `parse_diagnostics`, and `parse_warnings`, including failures when parsing yielded empty-text diagnostics. Existing Source audit/Claim excerpts remain; the full parsed Source text is not added to receipts. Local receipts retain their existing local path contract; the browser API does not expose those paths.

Source Detail returns typed, allowlisted diagnostic fields and derived warnings, plus Claim locators. Node Claims also expose the same locator read field. Arbitrary metadata, exception text, paths, IMA credentials and unrelated structured fields are excluded. Malformed/legacy diagnostics produce `null` rather than a false success summary; absent locators are not invented.

Explorer adds a compact **Source Format / Parse Quality** section and shared Evidence locator labels: Page, Paragraph, Table/Row, Sheet/Row, Slide or Text document. Ambiguous and unresolved states remain explicit. Existing pointers remain visible in Node Claims. There is no PDF viewer, file download, annotation or write API.

## Isolated operational acceptance

`tests/test_multiformat_ingestion.py` calls the real `IngestionPipeline.process_file` in temporary workspaces and isolated SQLite databases, using a deterministic LLM stub and guards against real network, IMA upload and ChatLLM calls.

For PDF, DOCX, XLSX and PPTX, **both standard and deep** verify Source creation/type/status, diagnostics persistence alongside existing metadata, valid and invalid Evidence handling, locator persistence, unchanged model pointer, receipt content, done job, original archive SHA/extension and pure IMA preflight compatibility. No Node/Proposal/View is manufactured by these smoke cases.

Failure tests cover empty PDFs in both modes, unsupported extension, corrupt PDF, parser exception, partial PDF, and failed empty-PDF upgrade. They verify retained incoming bytes, no false analyzed Source, failed job details, no orphan canonical rows and zero FK violations. Duplicate tests cover same/lower mode and archive → standard → deep, preserving existing reanalysis behavior and metadata. Long mixed-locator fixtures verify complete exact text coverage, deterministic ordering, marker preservation and bounded oversized splits. Existing frozen validator/truncation tests continue to pass.

| Verification | Result |
|---|---|
| New parser tests | 41 passed |
| New isolated ingestion / recovery tests | 21 passed |
| Combined targeted parser, pipeline, Analyzer, LLM, Relation, query/API regression | **265 passed** |
| Full workspace pytest | **731 passed**, one existing Starlette/httpx deprecation warning |
| Frontend | **11 files / 66 tests passed** |
| Frontend build | PASS, existing >500 kB bundle warning |
| Compileall (`src tests scripts`) | PASS |
| Edge browser checks | PDF, DOCX, XLSX, PPTX and partial PDF PASS; six screenshots visually inspected |

Windows used the existing Python 3.12.13 environment, isolated TEMP/TMP, fresh pytest `--basetemp`, `-p no:cacheprovider`, and `npm.cmd`. Full workspace pytest includes pre-existing local tests; historical untracked files are not part of this change.

Browser data came from a separate generated fixture DB, with explicitly synthetic navigation links; no Production copy or user material was ingested. Only GET requests were recorded. Development StrictMode aborted initial impact requests and their replacements returned 200. Console errors/warnings were 0, no viewport overflow was observed, and the dedicated browser/API/Vite processes were closed. The empty-text display is component-tested; failed empty PDFs correctly have no new Source Detail row.

Local uncommitted evidence: `workspace/phase3a_acceptance_20260828/` (baseline/post audits, targeted/full/frontend logs, browser fixtures and request/console logs) and `output/playwright/phase3a/` (six screenshots).

## Production invariants

`LIVE_PRODUCTION_MULTIFORMAT_INGEST_AUTHORIZED = false`. Actual configured Production was inspected only through SQLite `mode=ro` + `query_only`. No Source/Claim/Node link/Proposal/Current View/processing job was inserted. No archive, downloads or other user material was selected for acceptance.

Pre-SHA and post-SHA, read from the actual DB, are identical:

```text
581978e1c587b065a6eef9c980013af3de1a9e8a8781857385404c9f61105250
```

All **19 table counts** were measured before and after and are identical:

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

Integrity check: `ok`; foreign-key violations: `0`; WAL/SHM/journal sidecars: none. These are measured values, not hard-coded acceptance assumptions.

## Known limitations and Phase 3B handoff

Extraction fidelity is still that of the existing libraries: PDF reading order/table layout is not reconstructed; DOCX retains its existing paragraphs-then-tables order; XLSX `data_only` reads cached values and does not calculate formulas; PPTX reads supported text shapes, not images/charts/notes. Blank units and valid-looking text do not prove complete document coverage. Locator stability is within this Source representation, not a cross-version content identity. Reserved marker-like lines in Source content are not a new escaping/versioning system.

The archived original retains its extension and bytes and remains an input to the existing IMA upload contract. Only local media-type/MIME/size preflight was exercised. `LIVE_IMA_SYNC_AUTHORIZED = false`; no `create_media`, COS upload, `add_knowledge` or KB mutation occurred. IMA client/retry/scheduler semantics were not changed.

**Phase 3B — IMA Integration Operational Acceptance: ready for planning; not authorized.** A real newly authorized Source and separately scoped integration acceptance must be supplied later. Stop after the Phase 3A Draft PR; do not start Phase 3B.

```text
PHASE3A_COMPLETE = true
PHASE2_COMPLETE = true
SCHEMA_CHANGE = NO
LLM_EXTRACTION_CONTRACT_CHANGE = NO
FROZEN_VALIDATOR_CHANGE = NO
LIVE_PRODUCTION_MULTIFORMAT_INGEST_AUTHORIZED = false
LIVE_IMA_SYNC_AUTHORIZED = false
DEFER_ASK_UNTIL_CORPUS_EXPANSION = true
DEFER_SCANNED_PDF_OCR = true
DEFER_IMAGE_MULTIMODAL = true
DEFER_PDF_TABLE_STRUCTURE_EXTRACTION = true
DEFER_CHART_EXTRACTION = true
DEFER_LIVE_IMA_SYNC = true
DEFER_PROPOSAL_MODIFY = true
DEFER_PROPAGATION = true
DEFER_CURRENT_VIEW_FILE_MATERIALIZATION = true
DEFER_BROWSER_PRODUCTION_WRITE = true
DEFER_CANONICAL_CONTENT_DEDUP = true
DEFER_EVIDENCE_BOUNDARY_CONTENT_QUALITY = true
DEFER_EVIDENCE_QUALITY_METADATA = true
PHASE3B_READY = YES
```
