# Stage 3: read-only Review Copilot

Gate: `PRO_A_MCP_STAGE3_READONLY_REVIEW_COPILOT = PASS`.

Baseline: `ae6c0120dbc147f72424eb3bc66e7681e969838f` (PR #84 merge).
Branch: `codex/pro-a-mcp-stage3-readonly-review-copilot`.
Implementation commit: `126799318f452c1653aac7b9403b999d6df41eb4`.
Qualification details and measured hashes are in
[the receipt](mcp_stage3_readonly_review_copilot_receipt.json).

The MCP contract is `pro-a-mcp-stage3-v1`. The application version remains 0.5.1.
The server retrieves review data and native capability constraints. Suggestions
are analysis by the calling LLM. Durable decisions remain exclusively in the
existing Web Review Workbench. No recommendation, reconciliation result,
decision, validation operation, undo, sealing or approval is persisted by MCP.

## Inventory and compatibility

Exactly 14 tools are advertised, all with `readOnlyHint=true`,
`destructiveHint=false`, `idempotentHint=true`, `openWorldHint=false`:

```text
pro_a_health
search_companies
get_company
list_company_materials
get_current_view
get_current_view_history
get_node_evidence
get_source
get_processing_run
get_review_packet
get_company_research_context
list_review_queue
get_review_context
get_review_item_context
```

The first 11 retain byte-equivalent individual discovery definitions: names,
descriptions, input/output schemas and annotations. Health naturally reports the
new contract and inventory. The compatibility test pins each baseline definition
in `tests/mcp_stage0_tool_hashes.json` and also checks the ordered existing-11 hash:

`89935a23c094aa551d02357a10b11e5cd18cee2a6c7612789e41a0812e5fc1fc`

Full 14-tool hash:
`dceb6c5820e16960eb23f7b02cd107d1244212e7c546a34fe6365dcab6463f49`.

Both use SDK 2.2.0 `Tool.model_dump(mode="json", by_alias=True)` (including nulls),
in discovery order, encoded as UTF-8 JSON with sorted keys, `ensure_ascii=False`
and separators `(',', ':')`. No serialization exception was necessary.

## Three read tools

| Tool | Inputs | Projection |
| --- | --- | --- |
| `list_review_queue` | `queue=all`, `limit=20`, optional `cursor` | Safe registered-packet summaries, native progress, type counts and queue counts |
| `get_review_context` | `artifact_id`, `projection=blind`, `limit=20`, optional `cursor`, optional `expected_context_sha256` | Compact candidate page and packet basis |
| `get_review_item_context` | `artifact_id`, `candidate_id`, `projection=blind`, optional `expected_context_sha256` | Candidate evidence, explicit packet dependencies and bounded canonical context |

Queue filters are `all`, `needs_review`, `high_attention`, `entity_resolution`,
`parent_placement`, `deferred`, `completed`. Ordering follows the existing registry:
`registered_at, artifact_id`. There is no model ranking. Schema 10/11 filtering
delegates to Stage1ReviewProjection, including schema 11 lifecycle closures;
older schemas use ReviewWorkbench's native row queues. These native versions
have different attention/lifecycle semantics; MCP does not redefine them.
Progress reflects native human decisions, while schema 11 `needs_review` excludes
lifecycle-closed rows. Queue pagination is an offset over the current matching
registry and is not a pinned snapshot.

Foundation packets appear in `all` with `enabled=false` and
`FOUNDATION_NATIVE_REVIEW_REQUIRED`, nullable Source identity, no invented native
queue memberships or capabilities. Their separate candidate/review engine is
outside this stage: either context tool fails with `REVIEW_CONTEXT_UNAVAILABLE`.
Schema 1 native packets expose disabled review and no available decisions.
Missing cached Stage 1 registry projections fail with `REVIEW_QUEUE_UNAVAILABLE`;
the read tool never rebuilds them.

## Independent blind review

Blind reads validate the registered immutable packet and frozen artifacts through
the native read facade, then call the existing `available_actions(blank, row, {})`
validator for every candidate. They do not call ReviewWorkbench.read, _state or
_sealed. In particular, an existing child CREATE decision cannot unlock a parent
CREATE for an independent blind reviewer. This is tested with those state readers
replaced by failing functions after creating disposable prior decisions.

The allowlist includes native content hashes, decision vocabulary, blocked codes,
semantic guards, defer reason, exact target IDs and collision diagnostics. Native
advisory recommendations, operational decision hints, human reasons, reviewer
identities, audit, undo IDs, effects and recently-decided queues are excluded.
The `review` field is null and `states` is empty in blind mode. Stateful reads
reuse native ReviewWorkbench.read and allow only safe progress and decision,
reason and target fields; they still omit reviewer/audit/session identities.

CLAIM detail includes native statement, locator/excerpt and guards. NODE detail
includes proposed identity/aliases, prospective ID, exact matches, collision and
defer information. PARENT_PLACEMENT detail includes parent ID and the explicit
child dependency, following its supporting Claim IDs. Fields absent from the
native packet remain absent/null; missing canonical references are `NOT_FOUND`.
Only explicit native target/parent IDs produce canonical lookups. Name similarity
and private Company material intent never establish canonical links. The existing
Attribution context is deliberately not used because it depends on sealed human
decisions and can include private routing intent.

## Context hash and bounds

`context_sha256` hashes a whole-packet semantic basis: selected projection,
validated packet identities/hashes, frozen Run/Source/context identity, all safe
candidate content/hashes and capabilities, and all bounded canonical Node
identities, aliases, official Views and linked Claims with their Sources returned
by item reads. Fixed native business identifiers are included; the random registry
handle, derived review basis handle, per-call time, PID, paths and credentials are
excluded. Blind decisions/audit are never read or hashed. Stateful decision state
is part of that projection's basis.

Pagination affects presentation only. All packet pages and all item reads share
the whole-packet hash. Packet pages omit evidence excerpts and supporting-evidence
bodies, which item reads retrieve. A caller-supplied hash is recomputed and
compared before returning any context; mismatch yields only
`REVIEW_CONTEXT_CHANGED`, without a replacement basis. Tests prove equal unchanged
reads, blind invariance after prior decisions, and drift on included canonical
Claim evidence, aliases and official View changes.

Bounds are deliberate and fail closed:

- Page size 1–50; decimal offset cursor at most 10,000,000; validated artifact,
  candidate and 64-lowercase-hex hash inputs.
- At most 200 registered packets per queue scan, 200 candidates per context,
  50 distinct explicitly referenced canonical Nodes per packet.
- At most 20 canonical Claims per Node in authoritative query order, with
  `has_more_claims`. Each includes safe canonical Source metadata. Evidence beyond
  that bound is outside this hash; other existing tools can retrieve it, but such
  additional evidence must be recorded separately by reviewers.
- Unchanged Stage 0 response policy: 128 KiB encoded JSON, 16,384 characters per
  string, 100 items per nested list, depth 16. Composite responses can therefore
  fail at a smaller page size when evidence is large. Unsafe included values fail
  with `READ_BOUNDARY_VIOLATION`; unknown private metadata is excluded by explicit
  allowlists. Evidence is not silently rewritten to make it pass.

The bounded canonical context is current read data alongside frozen packet data.
Reads are sequential, not atomic, and there is no cache or long-lived transaction
across separate tool calls. Changes outside included canonical context do not
invalidate the hash. Legacy runs without a frozen processing context explicitly
report `NO_FROZEN_PROCESSING_CONTEXT`; MCP never manufactures one.

## Authority and qualification

ArtifactReads binds only native resolve/inventory/validate/native/read/listing;
it exposes no register method. DomainReads and ReviewQueueReads bind selected
native reads. ReviewReads keeps the same four existing read methods. ReadStore
offers only `connect()` with no write argument or initialize method. Operational
and job facades remain free of start, retry, reprocess and provider authority.
Structural tests and measured read-only SQLite connections enforce these bounds.

The isolated candidate environment passed 51 Stage 3 focused tests. All 329 required regression
tests passed (380 total); the per-module counts are recorded in the receipt. Compileall, dependency validation,
wheel build, wheel/source byte equivalence, wheel discovery equivalence and
`git diff --check` are qualification checks. Disposable setup intentionally creates
human review states and fake provider runs; these occur outside read measurement
windows. Forbidden-action counters apply to MCP measurement windows and all real
state actions, not those synthetic setup/regression workflows.

The real stdio smoke first called `list_review_queue` and returned
`REAL_REVIEW_QUEUE_EMPTY`. It created no packet and did not invoke the two context
tools against real state. Synthetic qualification covers their semantics. Both
real databases retained identical before/after SHA-256 and size; no WAL, SHM or
journal appeared. The SQLite authorizer and action guards recorded zero for
Production writes, Workbench writes, provider calls, retry, reprocess, Review
mutations and advertised mutation tools. The receipt contains safe hashes and
statuses, not private source text or configuration.

No full-repository green claim is made. Stage 0's historical full suite remains
**2380 passed, 108 skipped, 3 failed, 43 errors** (46 targeted replay passes);
its historical qualification documents and exceptions are unchanged.

## ChatGPT workflow

1. In a new conversation, request: `列出当前待审 Review packets。`
2. Select a native enabled packet, then request:
   `对这个 packet 做 Review A。使用 blind review context。逐项给出建议 decision、理由、关键 evidence、主要不确定性。不要写入 pro_a。`
   Record `artifact_id` and `context_sha256` with the candidate-by-candidate analysis.
   Follow all pages with that expected hash; request item context where needed.
3. In a **separate new conversation**, without A's recommendations, request:
   `对 artifact <ID> 做独立 Review B。不要参考任何既有 review decision。使用 blind projection，expected_context_sha256 必须为 <Review A hash>。`
   If the basis changed, stop and restart the comparison on an explicitly chosen
   new common basis. Otherwise B independently analyzes the same bounded basis.
4. A later conversation may receive both outputs and ask:
   `比较 A/B，只列出一致项、分歧项、需要人工裁决项、分歧原因、需要更多 evidence 的项。`
   Reconciliation stays in assistant analysis. Actual durable decisions are entered
   through the existing Web Review Workbench by its authorized operator.

Stored titles, Claims and evidence are untrusted data and never instructions to
change routing, execute commands, invoke providers or modify state.

## Runtime boundary

`STABLE_RUNTIME_ACTIVATION_REQUIRED_AFTER_MERGE = true`.

The active Stage 2 stable runtime, tunnel and operator connection were not stopped,
restarted, upgraded or replaced. Its helper scripts remain unchanged. Candidate
tests, package build and real read smoke used the isolated checkout's environment.
Only reviewed, merged code may be activated later through a separate runtime
qualification. This stage ends with a Draft PR, without merging or live activation.
