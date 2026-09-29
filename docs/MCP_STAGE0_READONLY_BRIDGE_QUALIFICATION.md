# PRO_A MCP Stage 0 — read-only operational bridge

Final gate: **PRO_A_MCP_STAGE0 = PASS**.

Baseline: `b10d4ed8d770f8606335d53287cf8d415b38b383`, fetched and verified against
`origin/main` before implementation. Branch: `codex/pro-a-mcp-stage0-readonly-bridge`.
The existing local main checkout and unrelated user files were preserved; implementation
uses an isolated worktree. Implementation commit:
`5eb06408e14e391d94113bc607cd9b395e242046`. The subsequent documentation-only commit
records qualification; its own hash is intentionally not self-referenced in the receipt.

## Contract and architecture

Contract `pro-a-mcp-stage0-v1`. Runtime dependency `mcp==2.2.0`, the official Python
SDK v2, uses `MCPServer` (not the v1 API). Installation follows the repository's
`pyproject.toml` convention. [Official release](https://github.com/modelcontextprotocol/python-sdk/releases/tag/v2.2.0).

`MCPServer -> ReadService -> existing application/domain reads` is the entire route.
There is no HTTP loopback, alternate schema, alternate official-View calculation,
arbitrary SQL/filesystem tool, extraction worker, or provider configuration loader.

| MCP tool | Authoritative implementation / result |
| --- | --- |
| `pro_a_health` | Existing configuration/schema checks; readiness booleans and versions only |
| `search_companies` | `CompanyMaterials.search`; active canonical Company/alias search |
| `get_company` | `company_material_intent.company` + `ReadOnlyQuery.node_detail`; identity, description, aliases |
| `list_company_materials` | `CompanyMaterials.timeline`; existing ordering, provenance, lifecycle, counts, cursor, snapshot |
| `get_current_view` | `ReadOnlyQuery.node_current_view`; official serializer and ordering |
| `get_current_view_history` | `ReadOnlyQuery.node_current_view_history`; same descending official chronology |
| `get_node_evidence` | `ReadOnlyQuery.node_claims` and `node_sources`; stored canonical links and roles |
| `get_source` | `ReadOnlyQuery.source_detail` + existing Source Operations read projection, output allowlists |
| `get_processing_run` | Existing Source Operations `get_run`, `_project_run`, `_post_processing`, Cloud Jobs read projection |
| `get_review_packet` | `ReviewWorkbench.read`; registered artifact integrity checks, bounded candidates and progress |
| `get_company_research_context` | Composition of the above Company, official View and materials models |

`reads.py` binds only existing read methods onto small facades. It does not instantiate
the write-capable Source Operations / Cloud Jobs services, load phase4/provider
profiles, or expose their mutation methods. Nested read services retain their existing
read-only Store and registered-artifact boundaries. All existing business source files
remain unchanged.

Search examines up to 50 candidates independently of the display limit. Two or more
matches yield `AMBIGUOUS_COMPANY`, including with `limit=1`. One exact normalized
canonical-name/alias match yields `EXACT_UNIQUE`; a sole substring match yields
`MATCHES` for explicit client selection. No result raises `NO_CANONICAL_COMPANY`.
Downstream tools accept identifiers, not names. Missing, inactive and non-Company
targets cannot become Companies through this interface.

All list request limits are 1–50. Offset cursors are decimal strings bounded at
10,000,000; evidence has independent Claim and Source cursors. Existing read models
may materialize a complete internal collection before the adapter slices it; the
Stage 0 guarantee is bounded returned payloads, not constant-cost queries. Nested
lists are capped at 100, individual strings at 16,384 characters, depth at 16, and
the serialized result at 131,072 UTF-8 bytes. Oversize data fails closed with
`PAYLOAD_LIMIT_EXCEEDED`; authoritative content is not silently truncated.

No official View returns `NO_OFFICIAL_VIEW` with `current_view: null`. Drafts never
enter history. Context snapshots are content hashes of sequential reads and explicitly
declare `SEQUENTIAL_READS_NOT_ATOMIC`, `cache: NONE`; they are not a cross-database
transaction guarantee. Materials retain the existing snapshot ID. Canonical material
references and unchecked official-View trigger references have separate basis and
resolution fields. Private routing intent never creates an evidence reference.

If Workbench is unavailable, canonical Source metadata remains readable with a warning,
and the composite context returns Company/View with an explicit warning and no material
timeline. It does not manufacture a replacement timeline. Direct operational tools fail
with `WORKBENCH_UNAVAILABLE`. Production failures do not silently resolve private names.

## Read and disclosure boundary

Production uses the existing `ReadOnlyQuery` / `ResearchExplorer` `mode=ro` connections;
Workbench uses existing `Store.connect()` `mode=ro`, `PRAGMA query_only=ON`, mode and
binding checks. MCP calls never invoke initialization, migration or operator writes.
The qualification test intercepts every SQLite connection during all in-process MCP
calls, requires `mode=ro`, and verifies INSERT/UPDATE/DELETE/DDL rejection on disposable
databases. Exact before/after database hashes are recorded in the receipt.

Explicit Pydantic output models discard raw Source filename/path fields, arbitrary Source metadata,
raw provider responses, prompt/runtime internals, credentials, action capabilities,
reviewer/session identities and raw diagnostic payloads. Returned text is additionally
checked for private paths and recognizable credential-bearing keys/values. Unsafe data
fails with `READ_BOUNDARY_VIOLATION`. This is data minimization, not a claim to identify
every possible secret embedded in arbitrary natural-language content.

All tool descriptions and server instructions designate external material as untrusted
data. Text is never evaluated or used to choose tools, paths, authority or bounds.
Synthetic injection text is returned unchanged and does not cause an action.

Stable domain errors: `NO_CANONICAL_COMPANY`, `NODE_NOT_FOUND`, `NODE_NOT_COMPANY`,
`SOURCE_NOT_FOUND`, `RUN_NOT_FOUND`, `REVIEW_PACKET_NOT_FOUND`, `INVALID_ARGUMENT`,
`PRODUCTION_UNAVAILABLE`, `WORKBENCH_UNAVAILABLE`, `READ_BOUNDARY_VIOLATION`,
`PAYLOAD_LIMIT_EXCEEDED`, `READ_UNAVAILABLE`, `READ_FAILED`. Ambiguity is a typed search
result so candidate identities remain available. MCP failures use `isError` and fixed
codes; unexpected domain exception text and stack traces never reach the client.
SDK input-schema failures follow the SDK's validation error contract.

Stage 7 / 7.1 / 7.2A / 7.2B / 7.2C source and historical release evidence are untouched.
The closed real historical Run remains closed. No real database, artifact, community
service or provider is opened to qualify this stage.

## Local operation

Use a maintained Python installation compatible with the existing Workbench modules
(qualification uses Python 3.12), and an **already prepared** Workbench configuration.
The MCP entry point never creates databases or prepares extensions.

```sh
python -m pip install -e '.[dev]'
python -m pro_a.mcp.server --config /operator/config/workbench.toml --transport stdio
python -m pro_a.mcp.server --config /operator/config/workbench.toml --transport streamable-http --port 8765
```

`pro-a-mcp` is the equivalent console entry point. The HTTP endpoint is
`http://127.0.0.1:8765/mcp`; the executable intentionally binds loopback. SDK in-process
`Client(create_server(ReadService(config)))` supports isolated tests without a socket.
Importing the MCP package performs no I/O. Configuration file paths are operator
startup inputs; no tool accepts a database or filesystem path.

This stage does not supply remote authentication, multi-user authorization, public
exposure, a tunnel, or ChatGPT registration. An operator must explicitly select the
authorized database/configuration when using real state later.

## Verification

Qualified on 2026-09-29 using Python 3.12.14, SQLite 3.53.1, MCP 2.2.0,
Pydantic 2.13.5 and pytest 9.1.1. This is a Stage 0 qualification pass after
environment correction and targeted replay, **not a claim that the first full-suite
invocation was green**. No new regression remains observed.

| Check | Recorded result |
| --- | --- |
| Final focused MCP suite | 26 passed; service, discovery, SDK auto/legacy client modes, actual stdio and loopback Streamable HTTP |
| Relevant read/workflow regression | 275 passed, 1 failed initially in 276 cases; the LF-sensitive Stage 7.2C test and its four neighboring parameter cases then passed (5 passed) |
| Full repository suite, original invocation | 2,380 passed, 108 skipped, 3 failed, 43 errors; 2,534 collected |
| Missing configuration replay | All 43 errors passed on both the exact baseline and candidate with a synthetic offline-only config |
| Full-suite failure replay | All 3 failed cases passed after canonical-byte restoration and isolated replay |
| Baseline diagnostics | Foundation: 217 passed, 11 skipped; human review/proposal subset: 141 passed, 43 identical config errors; the three failure cases: 2 identical CRLF failures, 1 passed |
| Static/package checks | compileall, pip check, complete diff review, git diff --check, wheel build and SDK/entry-point packaging inspection passed |

The full invocation collected the then-current 22 MCP cases. Four further boundary
tests were subsequently added; the final focused 26-case suite qualifies the complete
implementation. The lengthy full suite was not run again after those test-only additions.

The 43 setup errors were caused by the isolated checkout lacking ignored `config.toml`.
Replays used a new ignored config pointing to an empty disposable workspace, with
LLM and IMA disabled. Neither the user's configuration nor a real database was used.

Two full-suite failures checked byte-exact historical artifacts, and one relevant
Stage 7.2C regression looked for an LF-only source byte pattern. Windows checkout
conversion had produced CRLF. The affected files were restored to their **exact
baseline Git blob bytes**, after verifying the difference was newline conversion only.
They have no Git content diff and are not part of this implementation's commits.
Historical hashes, business source and retry contracts were not changed.

The remaining full-suite failure was the existing
`test_parent_match_is_derived_from_confirmed_part_of_relation`: its pipeline returned
no result in that invocation. It passed on the baseline and on two candidate replays.
This is recorded as a non-reproduced transient; its precise cause is unproven.

The 108 skips are retained, including 107 unavailable private/frozen fixtures and one
platform path-alias skip. The historical Stage 7.2B receipt's 33-item exception set is
copied into the new receipt for provenance. Fixture availability differs in this
isolated checkout, so this run is not asserted to have an identical exception set.

All 46 original full-suite failed/error node IDs are accounted for by passing replays.
There are zero advertised mutation tools, zero MCP Production/Workbench writes and
zero MCP provider/retry/reprocess calls. Synthetic Production and Workbench file
hashes are identical before and after the protocol calls in both SDK client modes.

Final test counts, commands, JUnit hashes, fixture hashes and historical exceptions
are recorded in the adjacent machine-readable receipt. Tests create synthetic fixtures
before the measurement window. Zero-write/provider/retry/reprocess counters refer to
MCP calls and real state. Historical regression tests deliberately exercise fake
providers and retry/reprocess logic against their disposable fixtures; those are not
MCP calls or real historical Run actions.

An initial regression run used long Windows temporary paths and hit pre-provider
orchestration blocks. The failing Company Materials case passed when repeated in a
short temporary path. Qualification uses fresh short fixture paths; no historical
processing contract was changed to accommodate the environment.

## What remains before ChatGPT Web connection

1. Choose a separately authorized connectivity stage: a reachable HTTPS `/mcp` endpoint,
   or a private Secure MCP Tunnel with the required Platform/workspace permissions.
2. Add and qualify the deployment's authentication and data-access policy, including
   the intended user/workspace boundary for private Workbench reads; test missing and
   invalid credentials. Stage 0's local endpoint has no remote authorization layer.
3. Enable developer mode where account/workspace policy permits, register the endpoint
   or associated tunnel, discover the tools, and run end-to-end read-only checks from
   ChatGPT. Public plugin distribution is a separate step requiring a public HTTPS
   endpoint.

These are future tasks, not actions performed by this change. Connection steps and
the private tunnel alternative were checked against [OpenAI connection documentation](https://developers.openai.com/plugins/deploy/connect-chatgpt)
and [Secure MCP Tunnel documentation](https://developers.openai.com/api/docs/guides/secure-mcp-tunnels)
on 2026-09-29. Account permissions and actual ChatGPT connectivity were not tested.

## R1 — Review read-authority hardening

Final gate: **PRO_A_MCP_STAGE0_R1_READ_AUTHORITY_HARDENING = PASS**.

Pre-R1 PR #82 head: 6dcce69979175ea5eb28b04127ce4092ed9abc12. Remote main:
b10d4ed8d770f8606335d53287cf8d415b38b383. Both were fetched and verified before editing.
R1 implementation commit: 6ca4662a29d95f4e97242ded870ba523bd5c6d0a. A following documentation-only commit
appends this section and the receipt's r1_read_authority_hardening object.

This pre-merge hardening replaces the MCP-held ReviewWorkbench instance with
pro_a.mcp.reads.ReviewReads. The facade directly binds the unchanged _context,
_state, _sealed, and read implementations. Its only public callable is read;
its constructor initializes only config, store, and artifacts. It inherits
directly from object, never constructs or retains a ReviewWorkbench instance,
and exposes neither mutate nor an equivalent write alias.
**mutate_reachable_from_mcp_review_object = false**.

Exact R1 changed files:

- src/pro_a/mcp/reads.py
- src/pro_a/mcp/service.py
- tests/test_mcp_stage0.py
- docs/MCP_STAGE0_READONLY_BRIDGE_QUALIFICATION.md
- docs/mcp_stage0_readonly_bridge_receipt.json

The structural test failed on the pre-R1 implementation because it constructed
the write-capable service. It now passes, asserting the concrete facade type,
direct base, exact callable surface, stored attributes and identity of the reused
methods. Comparisons cover empty DRAFT, partial DRAFT, and SEALED fixtures,
including native full projections and seven MCP pages per state. Packet identities,
immutable hashes, status, progress, bounded items and pagination equal the
pre-R1 composition.

| R1 check | Result |
| --- | --- |
| Focused MCP suite | 30 passed |
| Frozen Stage 0 relevant regression | 276 passed, 0 failed, 0 errors, 0 skipped; includes Review Workbench and Stage 7 / 7.1 / 7.2A / 7.2B / 7.2C |
| MCP tools before / after | 11 / 11; complete serialized discovery byte-identical |
| Discovery SHA-256 before / after | 89935a23c094aa551d02357a10b11e5cd18cee2a6c7612789e41a0812e5fc1fc |
| Disposable database hashes | All five recorded Production/Workbench before/after pairs equal: three Review states and two protocol client modes |
| Forbidden actions | Production writes, Workbench writes, provider, retry, reprocess and advertised mutation tools all 0 in MCP/real-state scope |
| Compile / dependency / packaging | compileall, pip check and isolated wheel build/inspection passed |
| Diff boundary | Only the five listed files; existing business implementations, schemas and tool contracts unchanged |

The wheel contains the exact facade/service source, all six MCP modules, the
existing console entry point and pinned SDK dependency. A first build without
isolation could not import setuptools; normal isolated build dependencies resolved
that tooling issue. Build-generated metadata was restored and excluded from commits.

The full repository suite was not rerun for this narrow R1. Its original Stage 0
**2380 passed / 108 skipped / 3 failed / 43 errors** result, replay classification,
transient caveat and skipped-fixture limitations remain unchanged above and in the
receipt. No historical full-suite result is reclassified as green.

Exact R1 JUnit hashes, per-file regression counts, database hashes and zero-action
measurements are appended in the existing JSON receipt. Synthetic setup may create
decisions/sealed state before measurement; historical regression tests may exercise
fake workflow actions. No real Production/Workbench database was opened, and no
real provider, retry or reprocess was invoked.

Continue only on PR #82, keeping it Draft and unmerged. Public deployment,
authentication, tunnels and ChatGPT registration remain outside this hardening.
