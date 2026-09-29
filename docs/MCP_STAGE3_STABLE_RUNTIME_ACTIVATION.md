# Stage 3 stable runtime activation

`PRO_A_MCP_STAGE3_STABLE_RUNTIME_ACTIVATION = PASS`

Local activation, automated qualification and required HUMAN_OPERATOR_CHATGPT
health and queue acceptance passed. The existing managed runtime remains online.
The [machine-readable receipt](mcp_stage3_stable_runtime_activation_receipt.json)
preserves the initial tool-exposure block and the subsequent successful queue
calls, together with final runtime and database checks.

## Baseline and artifact

- Exact fetched main: `6229f7dc7e23f5cdd996a6d3b63df6d91750fabd`.
- PR #85 merged at `2026-09-29T06:15:29Z` with that merge commit.
- Evidence branch: `codex/pro-a-mcp-stage3-runtime-activation`.
- Previous stable source: `93d4e80490c8618d5719fe5cd7a875f61dcc5e05`.
- Old installed MCP discovery was verified through actual stdio: contract
  `pro-a-mcp-stage0-v1`, exactly 11 tools, Production/Workbench readable, schema 11.
- A fresh wheel was built from `git archive` of the exact merged commit. Its SHA-256
  is `f688b4c36d902e5e4f3f800084eb3d879fa4cd2f70f60f78956548379fb45433`.
- Candidate and installed stable package source both match all 129 archived Python
  source files byte-for-byte. Installation is a non-editable wheel.

Stable versions: Python **3.13.14**, pro_a **0.5.1**, MCP SDK **2.2.0**, SQLite
**3.50.4**. The MCP contract is **`pro-a-mcp-stage3-v1`**. All previous installed
dependency versions remain unchanged; candidate and stable `pip check` passed.

## Isolated qualification and activation

Before changing the stable installation, a separate Python 3.13 candidate venv
was created with the existing pinned dependencies from the operator's offline
wheel cache. The newly built wheel was installed and verified there first.

Candidate and upgraded stable installations each successfully called:

1. `pro_a_health`
2. `search_companies`
3. `get_current_view`
4. `get_company_research_context`
5. `list_review_queue`

Both report readable Production and Workbench, Workbench schema 11,
`read_only=true`, the Stage 3 contract, and 14 capabilities. The real queue is
`REAL_REVIEW_QUEUE_EMPTY`; no packet was created, imported or registered.

After candidate PASS, the existing managed runtime was cleanly stopped. Its old
wheel, installed distribution metadata, runtime metadata, dependency lock and
wheel manifest were backed up in the operator-owned runtime rollback directory.
Only pro_a was reinstalled, using `--force-reinstall --no-deps --no-index`.
Installed source identity and dependencies were verified before the existing
`start-pro-a-mcp.cmd` restarted the managed runtime. The existing
`status-pro-a-mcp.cmd` supplied health evidence.

The secret file was neither read nor hashed by the agent; its size and modification
metadata remained unchanged. Existing helpers pass its existing file reference
to the native client for authentication. Runtime settings, private Workbench
configuration, dependency lock and all six helpers retained identical hashes.
Thus the existing Tunnel ID, control-plane proxy and config reference were
preserved. No new Tunnel or ChatGPT app was created. No business code was edited.

## Discovery and health

The upgraded stable installation actually exposes exactly these 14 tools:

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

All tools retain read-only/non-destructive annotations. The old 11 definitions
match the pre-upgrade stable discovery byte-equivalently. Existing-11 hash:
`89935a23c094aa551d02357a10b11e5cd18cee2a6c7612789e41a0812e5fc1fc`.
Full-14 hash:
`dceb6c5820e16960eb23f7b02cd107d1244212e7c546a34fe6365dcab6463f49`.
Serialization matches the merged Stage 3 receipt.

All four native status samples show `process_running=true`, `healthy=true`,
`ready=true`. Detailed control-plane status is `ok`, state is `polling`, and
`consecutive_failures=0`. `last_success` advanced from
`2026-09-29T06:26:53.2662907Z` through `2026-09-29T06:27:54.3890686Z`
to `2026-09-29T06:42:06.6391984Z`, then `2026-09-29T06:48:56.2947861Z`.
The native summary still says `unknown` with reason `no live admin UI system
snapshot`; it is preserved honestly rather than rewritten. Native MCP telemetry
also remains `not_observed`, with a running child. Installed-package local stdio
verification is distinct from hosted ChatGPT discovery and queue verification.

The official [Secure MCP Tunnel guide](https://developers.openai.com/api/docs/guides/secure-mcp-tunnels)
describes the running-client dependency and local health surfaces. The managed
runtime stays running for the human acceptance step.

## Safety and rollback

Baseline, candidate and stable read windows all retained identical database
integrity checks, schema fingerprints, row-count fingerprints, file hashes and
sizes. No WAL/SHM/journal appeared. Production SHA-256:
`6e5a303ccee9c192c350c2550cc232649e56ffee939b7a09cd6b170cc1c8fba1`.
Workbench SHA-256:
`1ff852dbe76c5fc4054c3e6f4e308b98a66f918dc3081e287b793c682a61ca44`.

All seven forbidden-action counters are zero: Production writes, Workbench writes,
provider calls, retry, reprocess, Review mutation, advertised mutation tools.
Read windows enforce `mode=ro`, `query_only` and a write-denying SQLite authorizer;
provider and mutation entry points are guarded. These are measured local MCP
windows, not a continuous host-wide trace. Human Web health passed by operator
report, as did both Web queue calls. Local checks after Web health and again
after final human acceptance passed all five read calls, actual 14-tool discovery
and compatibility, with unchanged database snapshots and all seven counters zero.

Rollback is available without changing secrets or connection settings. The old
wheel SHA-256 is
`db38223ec714576a41c5666202940f9c9c99463a377971d2c5954548c8e7ef82`.
The operator-owned `rollback/stage3-6229f7dc` directory retains the wheel and old
metadata. To roll back, cleanly stop, reinstall that verified wheel with
`--force-reinstall --no-deps --no-index`, restore prior runtime metadata, then start
with the existing helper and recheck local/Web health. Rollback was not executed.

No new application regression suite was run for this deployment-only operation.
Merged Stage 3 retains its 51 focused and 329 required regression passes; this
activation qualifies the built and installed merged artifact. Sleep, reboot,
proxy availability at login and unattended uptime remain unqualified.

## Human acceptance and publication

The first HUMAN_OPERATOR_CHATGPT attempt supplied a successful actual current
health result: Stage 3 contract, 14 capabilities, readable Production and
Workbench, schema 11, pro_a 0.5.1 and `read_only=true`. No historical health result
was substituted. However, the operator reported that the current conversation
exposed only 11 tools and omitted all three Stage 3 tools. `list_review_queue`
was not invoked in that attempt. This initial block remains in the receipt.

Installed-package discovery was reconfirmed as 14 tools. The operator was given
the official [Refresh metadata instructions](https://developers.openai.com/plugins/deploy/connect-chatgpt#refresh-metadata):
refresh the existing connection, then start a new conversation. No Tunnel or app
was recreated. Stale client metadata was suspected; exact UI actions were not
independently observed.

The operator subsequently reported actual successful `list_review_queue` calls:

| Queue | Review packets | Next cursor | Read only |
| --- | ---: | --- | --- |
| `needs_review` | 0 | `null` | `true` |
| `all` | 0 | `null` | `true` |

Both results were reported as current live calls, without historical substitution.
This is accepted HUMAN_OPERATOR_CHATGPT evidence under the task's human gate.
Web health and queue acceptance are now PASS. No real packet was created.

The final local check after human acceptance again passed actual 14-tool discovery,
old-11 compatibility and all five read calls. Runtime status at
`2026-09-29T06:49:03.6696777Z` was running/healthy/ready, detailed polling was
`ok`/`polling`, and consecutive failures were zero. Database integrity, schema,
row-count fingerprints, sizes and hashes remained identical to the baseline;
all seven guarded counters remained zero.

Only these two sanitized evidence files are submitted on
`codex/pro-a-mcp-stage3-runtime-activation` in a Draft PR against main. The evidence
commit SHA and PR URL are reported in the final handoff. No business code is
changed and no merge is performed. The existing managed runtime stays online.
