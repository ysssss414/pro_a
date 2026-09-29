# PRO_A MCP Stage 1 — Secure Tunnel / ChatGPT read-only smoke

```text
initial_gate = BLOCKED_TUNNEL_AUTH
operator_continuation = COMPLETED
final_gate = PRO_A_MCP_STAGE1_SECURE_TUNNEL_CHATGPT_READONLY_SMOKE = PASS
```

This closes the completed qualification using the operator's real ChatGPT Web
observations and an independent local recheck. **It does not claim the Tunnel is
online now:** at 2026-09-29 04:11:05 UTC no `tunnel-client` process remained, and the
existing local health/readiness endpoints refused connections. The operator must
restore the existing runtime before a fresh Web read. This continuation neither
stopped nor restarted it.

Baseline remote `main`: `29fc3469525027cd676449d8fecbf953559e94df`, independently
verified before evidence writing. Branch:
`codex/pro-a-mcp-stage1-secure-tunnel-closure`. Only this report and its
[JSON receipt](mcp_stage1_secure_tunnel_chatgpt_smoke_receipt.json) change.
Runtime business code, real Production/Workbench, private configuration and the
existing Tunnel profile remain unchanged.

## Evidence provenance and preserved chronology

| Source | Scope |
| --- | --- |
| `LOCAL_AUTOMATED` | Original local real-state stdio qualification and audit |
| `HUMAN_OPERATOR_TUNNEL` | Operator-reported Tunnel setup, doctor, polling/network and stop/restart |
| `HUMAN_OPERATOR_CHATGPT` | Operator-reported authenticated Web smokes A–E and fresh loss/recovery requests |
| `CURRENT_READONLY_RECHECK` | Current local discovery, four reads, file/audit checks, process/endpoints and remote-main check |

The original local qualification ran at 2026-09-29 02:21:30–02:21:31 UTC.
Its six local calls passed, but remote qualification correctly stopped at
`BLOCKED_TUNNEL_AUTH`: no operator Tunnel identity/runtime credential was available,
and Web A–E, connection loss and recovery were `NOT_RUN`.

That historical result is retained. The receipt's `initial_qualification` contains
the entire original parsed `stage1-status.json`, including its original BLOCKED
gate, `NOT_RUN` fields, browser-runtime limitation, counters and publication
restriction. The original private files are unmodified:

- Original status SHA-256:
  `14d7e9226b2ff4c6913cafb37c15b4ffac5c44d1eb1c499985eb184acabda40b`.
- Original handoff SHA-256:
  `ffc5cdd24c0d1d28512a82f23510252ed48be0f8d9d373d6c3c1a10df0f37bb4`.

The subsequent operator continuation was supplied in this task on 2026-09-29.
Its source hash is retained in the receipt; raw text and private filesystem
locations are not committed. Exact human observation times and browser tool-call
traces were not supplied. No current browser automation was used or required.
The current local recheck does not replace those human observations.

## Operator Tunnel continuation

Source: `HUMAN_OPERATOR_TUNNEL`; result: **PASS**.

The operator created `pro-a-local`, associated it with the intended ChatGPT
workspace, supplied a runtime key with Tunnels Read + Use through
`CONTROL_PLANE_API_KEY`, installed Windows tunnel-client v0.0.15, and created the
`pro-a-local` profile from `sample_mcp_stdio_local` with the real local stdio command.
`doctor --profile pro-a-local --explain` returned `RESULT ok`. The runtime reached
Health `live`, Ready `ready`, and connected logs; the developer-mode pro_a app
was created successfully.

No key value was accessed by this continuation. The exact Tunnel ID, proxy
address, credentials, profile/config contents and absolute user paths are omitted.
The operator alias identifies the connection in public evidence.

## Human ChatGPT Web smoke

Source for every row: `HUMAN_OPERATOR_CHATGPT`. These are accepted operator
observations, not automated browser test results.

| Smoke | Observed result | Gate |
| --- | --- | --- |
| A — health | `pro_a` 0.5.1; contract `pro-a-mcp-stage0-v1`; Production/Workbench readable; schema 11; `read_only=true`; 11 capabilities | PASS |
| B — Company resolution | 昀冢科技; `NODE_20260826_BC260F3E`; active Company; `EXACT_UNIQUE` | PASS |
| C — official Current View | `VIEW_20260826_99D621B2` retrieved; no draft represented as official | PASS |
| D — research context | Official View used as baseline; canonical evidence authoritative; community material private/low-trust; failed extraction not promoted into facts; unresolved information described as unknown | PASS |
| E — unsupported write | ChatGPT explained the MCP is read-only; no Current View write tool existed; no write attempted or performed | PASS |

Prompt equivalents and structured observations are in the receipt. The D prompt
explicitly required canonical/private separation and no pro_a modification.
E's refusal is the expected successful outcome. Exact selected-tool traces,
unnecessary-call counts and missed-tool counts are not inferred.

## Connection loss and recovery

Sources: `HUMAN_OPERATOR_TUNNEL` for stop/restart and
`HUMAN_OPERATOR_CHATGPT` for the fresh requests; both gates: **PASS**.

After the operator stopped `tunnel-client`, a fresh health request produced two
read timeouts. ChatGPT reported that current availability could not be confirmed,
without presenting a cached/stale response as a fresh read; no write occurred.
These were transport read attempts, not processing retry/reprocess actions.

After the operator restarted the runtime, a new health request immediately
recovered: Production/Workbench readable, schema 11, read-only true.

```text
PC / tunnel-client / local MCP unavailable
=> ChatGPT cannot perform a fresh pro_a read.

Runtime restored
=> ChatGPT access recovers.
```

This continuation did not repeat the stop/restart test or make another authenticated
Web request. The currently stopped runtime is recorded separately from the
operator's successful recovery observation.

## Network requirement and operating notes

Source: `HUMAN_OPERATOR_TUNNEL`.

The first attempt had green local health/readiness but polling logged
`poll transport failed (network_error)`. The operator found that direct
`api.openai.com:443` failed while the Windows user proxy was active and tunnel-client
was initially in direct mode. Supplying the required local HTTP proxy through
`CONTROL_PLANE_HTTP_PROXY` resolved connectivity, after which app creation succeeded.
This proxy is an operational requirement for this operator network.
No proxy credentials or address are recorded.

For future reads, keep the operator's existing private profile, environment and
runtime available. The existing `doctor --profile pro-a-local --explain` and
`run --profile pro-a-local` operational flow can be used locally when restoring it;
this report does not create or replace the profile. The verified local server
uses Python 3.12.14, pro_a 0.5.1 and MCP 2.2.0. Its portable command shape is
`python -B -m pro_a.mcp.server --config <PRIVATE_WORKBENCH_CONFIG> --transport stdio`;
the actual interpreter and config paths stay private.

Local readiness alone is insufficient to establish control-plane polling or a
successful Web call. OpenAI's [Secure MCP Tunnel documentation](https://developers.openai.com/api/docs/guides/secure-mcp-tunnels)
describes the outbound connection and dependency on a running client; the network
failure and proxy resolution above are operator evidence for this host.

## Independent current read-only recheck

Source: `CURRENT_READONLY_RECHECK`; local stdio gate: **PASS**.
Window: 2026-09-29 04:09:50–04:09:56 UTC.

A separate measured stdio session used the existing Stage 0 server and real
PRIVATE Workbench configuration. The local-only measurement wrapper counted and
denied write-capable SQLite connections/SQL mutations, provider, retry, reprocess
and review-mutation entry points. No production business file was edited.

Exactly these 11 tools were discovered:

1. `pro_a_health`
2. `search_companies`
3. `get_company`
4. `list_company_materials`
5. `get_current_view`
6. `get_current_view_history`
7. `get_node_evidence`
8. `get_source`
9. `get_processing_run`
10. `get_review_packet`
11. `get_company_research_context`

All 11 have `readOnlyHint=true`, `destructiveHint=false`,
`idempotentHint=true`, `openWorldHint=false`. No mutation tool is advertised.
Serialized discovery SHA-256 remains
`89935a23c094aa551d02357a10b11e5cd18cee2a6c7612789e41a0812e5fc1fc`,
matching the frozen Stage 0/R1 and initial Stage 1 inventory.

The four current calls succeeded: health, search, official Current View and company
research context. Company/View IDs match the human observations. Context returned
one canonical and one private material, the latter still `FAILED`, plus seven
evidence references. Warnings remain
`PRIVATE_MATERIAL_IS_NOT_CANONICAL_EVIDENCE` and
`OFFICIAL_VIEW_TRIGGER_REFERENCES_NOT_REVALIDATED`.
Context consistency remains `SEQUENTIAL_READS_NOT_ATOMIC`.

All 23 monitored files (Production database/sidecars, Workbench directory, private
artifacts and config) retained their hashes/size/mtime; directory entries were
also compared. No database journal/WAL/SHM was present. Both database hashes
also equal the original pre-continuation local qualification:

| Database | SHA-256 before = after = original qualification |
| --- | --- |
| Production | `6e5a303ccee9c192c350c2550cc232649e56ffee939b7a09cd6b170cc1c8fba1` |
| Workbench | `1ff852dbe76c5fc4054c3e6f4e308b98a66f918dc3081e287b793c682a61ca44` |

The current endpoint probes could not connect, including a direct host-context
recheck at 04:10:29 UTC (`ConnectionRefusedError`, 10061). A process query at
04:11:05 UTC confirmed zero tunnel-client processes. An earlier process/listener
observation had found it running. No assertion of current end-to-end availability
or current control-plane health is made. The process was not changed by this task.

## Final values and action scope

All nine completed-qualification values are `true`:
`chatgpt_web_callable`, `tunnel_runtime_verified`, `real_company_search`,
`real_current_view_read`, `real_company_research_context`,
`canonical_private_separation`, `unsupported_write_correctly_rejected`,
`connection_loss_verified`, `recovery_verified`.
The receipt maps each value to its evidence sources. The first two are historical
qualification conclusions, not the currently stopped runtime's online status.

| Counter | Value |
| --- | --- |
| `production_writes` | 0 |
| `workbench_writes` | 0 |
| `provider_calls` | 0 |
| `retry_calls` | 0 |
| `reprocess_calls` | 0 |
| `advertised_mutation_tools` | 0 |

Scope: original/current measured local MCP calls and the operator-reported Web
qualification. Current wrapper maxima are zero for database-write attempts,
non-read-only connections, provider, retry, reprocess and review mutation calls.
Human remote no-write behavior is attested, with matching database snapshots as
additional evidence; there is no continuous remote/host-wide write trace.
Documentation, private measurement files and Tunnel transport/logging are outside
these Production/Workbench action counters.

## Limits and publication boundary

- Current runtime is stopped; fresh Web access requires the operator to restore
  the existing runtime, proxy and local MCP dependencies.
- This does not qualify an always-on Windows service, unattended startup or
  availability after PC shutdown/sleep/network loss.
- Human Web observations have no attached raw transcript or per-call remote audit.
  Their provenance and unprovided timestamps remain explicit.
- The interface remains read-only. Failed private material is not established fact,
  and official trigger references are not revalidated by the context call.
- This private developer connection does not establish public distribution or
  broader multi-user authorization/security penetration qualification.

Only the two requested sanitized evidence documents are committed. Initial
artifacts and runtime code remain unchanged; no config, key, exact Tunnel ID,
user-home path, raw credential-bearing log or temporary helper is included.
Publication is an authorized commit/push and **Draft PR against main, without merge**;
commit SHA and PR URL are reported after publication rather than self-embedded.
