# PRO_A MCP Stage 2 — Stable Windows local runtime

```text
PRO_A_MCP_STAGE2_STABLE_LOCAL_RUNTIME = PASS
local_stable_stdio = PASS
AUTO_START = DEFERRED
```

The fixed Windows runtime passed local read-only smoke, native managed startup,
control-plane polling, human ChatGPT Web health, clean stop/loss, and recovery
from a fresh Windows PowerShell. The managed process remained healthy after its
launching shell exited. The final human Web call again confirmed both databases
readable, schema 11, read-only true and the exact 11 capabilities.

Auto-start is a separate deferred gate: proxy availability at user logon is not
qualified. This record does not claim reboot, unattended or always-on availability.

## Baseline and preserved authority

Fetched remote `main` exactly matched
`93d4e80490c8618d5719fe5cd7a875f61dcc5e05`, containing Stage 0 PR #82 and Stage 1
PR #83. Work is isolated on `codex/pro-a-mcp-stage2-stable-local-runtime`.
The remote SHA was rechecked before publication and still matched.
No application or MCP business code changes. Contract remains
`pro-a-mcp-stage0-v1`, with exactly 11 read-only tools and no mutation tool.

Discovery SHA-256:
`89935a23c094aa551d02357a10b11e5cd18cee2a6c7612789e41a0812e5fc1fc`.
The complete inventory and sanitized evidence are in the
[JSON receipt](mcp_stage2_stable_local_runtime_receipt.json).

## Stable installation

Machine inspection found an operator-installed Windows Python 3.13 and an existing
fixed tools directory containing tunnel-client. A dedicated sibling runtime was
created outside Git repositories, temporary worktrees, Codex visualizations and
Codex runtime caches. Existing private Workbench configuration and both database
locations were retained unchanged.

```text
operator tools directory/
  tunnel-client/tunnel-client.exe
  pro-a-mcp/
    .venv/
    wheels/
    requirements.lock.txt
    wheel-sha256.json
    runtime-metadata.json
    runtime-settings.json
    start-pro-a-mcp.ps1
    status-pro-a-mcp.ps1
    stop-pro-a-mcp.ps1
    start/status/stop-pro-a-mcp.cmd
    Set-ProARuntimeSecret.ps1
    secrets/runtime-api-key.txt  (operator saved; contents not inspected)
```

| Component | Verified value |
| --- | --- |
| Python | 3.13.14, normal operator-installed Windows Python |
| pro_a | 0.5.1, non-editable wheel |
| MCP SDK | 2.2.0 |
| SQLite | 3.50.4 |
| tunnel-client | 0.0.15+a390c168ff1b2d14e73a95991c186c6aba3ff5a0 |
| Source identity | Exact required main commit above |

The wheel was built from the qualified checkout, not copied from its virtualenv.
All 127 packaged application files were compared with the exact Git commit,
normalizing only checkout CRLF line endings. Wheel SHA-256:
`db38223ec714576a41c5666202940f9c9c99463a377971d2c5954548c8e7ef82`.
`pip check` passed. All 59 application/dependency wheels are retained with hashes;
an offline, ignore-installed dry-run resolved the complete locked installation.
This verifies artifact completeness, not a second independently installed runtime.

Rebuild with the same installed Python and the retained wheels into a new empty
environment, then repeat qualification before switching an active runtime:

```powershell
py -3.13 -m venv <NEW_RUNTIME>/.venv
<NEW_RUNTIME>/.venv/Scripts/python.exe -m pip install --no-index --find-links <WHEELS> -r <LOCK_FILE> pro-a==0.5.1
```

Verify wheel hashes against `wheel-sha256.json` before installation. Runtime
metadata records every installed version. Python or package updates require the
same discovery/read/transport checks; no automatic package updater was added.

## Stable command and completed real-state checks

```text
<STABLE_PYTHON> -B -m pro_a.mcp.server --config <EXISTING_PRIVATE_WORKBENCH_CONFIG> --transport stdio
```

This exact command shape ran from the stable runtime directory using its installed
wheel. Production/Workbench were readable, Workbench schema was 11, and
`read_only=true`. Health, search, Company, official Current View, materials and
research context all succeeded. Canonical smoke target remained 昀冢科技,
`NODE_20260826_BC260F3E`; official View remained `VIEW_20260826_99D621B2`.
The context retained one canonical and one private material and the existing
canonical/private and unvalidated-trigger warnings.

The direct run was followed by a separate local measurement wrapper loading the
same installed package. It counted and denied write-capable SQLite connections,
SQL mutations, provider calls, retry/reprocess and Review mutation entry points.
Every counter remained zero. This temporary measurement wrapper is not part of
the stable MCP command.

Both databases passed read-only `integrity_check`; schema/row-count fingerprints
and database hashes matched before and after both local runs. Journal mode was
DELETE and neither WAL nor SHM was present in these windows. Production hash:
`6e5a303ccee9c192c350c2550cc232649e56ffee939b7a09cd6b170cc1c8fba1`;
Workbench hash:
`1ff852dbe76c5fc4054c3e6f4e308b98a66f918dc3081e287b793c682a61ca44`.
This is bounded observation, not continuous host-wide write monitoring. With
concurrent writers or WAL, use consistent read-only logical snapshots and explain
changes rather than asserting byte stability.

## Secret, proxy and managed runtime

Actual v0.0.15 CLI help was inspected for `runtimes`, `connect`, `status`, `stop`
and `run`. It supports runtime-key references using `env:` or `file:` and native
managed lifecycle. No credential-manager integration was assumed.

The chosen persistent key reference is an operator-private file outside Git.
A local setup script prompts for the existing key through hidden input. Before
writing, it disables inherited directory ACLs and grants the current operator SID
only; the file inherits that ACL. The agent does not execute the input step,
read the resulting secret, print its value, or rotate the key. The operator saved
the existing key. Metadata-only checks verified that the
file exists and is nonempty, its access rules grant only the current operator,
and its parent directory disables inherited access rules. No key contents were
read or hashed. The original Set-Acl operation failed under Windows PowerShell
with SeSecurityPrivilege; the helper now persists only the DACL through
DirectoryInfo.SetAccessControl. This was verified under non-administrator
Windows PowerShell 5.1 before the operator retried successfully.

Automatic approval review rejected the attempted whole-profile parse because the
old profile could contain a literal credential. The command did not execute and
was not retried through another reader. The existing Stage 1 `pro-a-local` profile
is preserved. The operator supplied
the non-secret Tunnel ID, and native alias `pro-a-local` now uses the separate
`pro-a-stable` profile generated in the stable runtime. Its known file reference
and stable Python command were verified without reading the secret file.

Windows has an enabled credential-free loopback HTTP proxy. Its address is saved
in machine-local `runtime-settings.json`, alongside the non-secret Tunnel ID
and the existing private Workbench config path. This local file is not committed.
The start helper passes the proxy through
the supported `CONTROL_PLANE_HTTP_PROXY` for the native runtime launch and restores
the caller's previous proxy environment afterward. No global/MCP HTTP proxy is
configured; MCP remains local stdio. Detailed health verified the control-plane
proxy route as healthy and the MCP route as direct. Successful poll timestamps
advanced with zero consecutive failures.

Native alias `pro-a-local` was registered against the existing Tunnel ID using
`--tunnel-id`, the stable command, the separate generated profile and the private
file reference. No admin Tunnel creation or credential rotation was performed.
Initial native status reported `process_running=true`, `healthy=true`, `ready=true`.
The native `control_plane_poll_health` summary reports `unknown` with reason
`no live admin UI system snapshot`; this value is preserved, not relabeled green.
The supported detailed loopback health endpoint separately reported control-plane
`status=ok`, active polling, advancing `last_success`, and zero consecutive failures.
The status helper shows both sources. Cloudflared is disabled.

The operator's fresh ChatGPT Web health response confirmed pro_a 0.5.1, both DBs
readable, contract `pro-a-mcp-stage0-v1`, schema 11, read-only true and the exact
11-tool inventory. Source is `HUMAN_OPERATOR_CHATGPT`; no exact call timestamp or
raw authenticated trace was supplied. Same-child MCP telemetry remained
`not_observed`, so no independent call/discovery trace is inferred from it.

The native stop helper then completed. Process/health/readiness became false and
a process query found zero tunnel-client processes. The operator then reported
two fresh `pro_a_health` timeouts, explicitly
without reusing the prior success. These are transport attempts, not Source
processing retry/reprocess calls.

A fresh non-profile Windows PowerShell 5.1 then restored the runtime using the
stable `.cmd` launcher, with `CONTROL_PLANE_API_KEY`, `OPENAI_API_KEY` and
`CONTROL_PLANE_HTTP_PROXY` absent in that qualification shell. Process/health/
readiness returned true and detailed polling succeeded. The launching shell
exited; the native runtime remained healthy. No virtualenv was rebuilt and no key
was retrieved again. The native lifecycle serializes the same generated profile;
its final content hash matches initial, but its mtime changes. This is not a claim
that native `connect` never writes profile metadata.

The first alias-only restart failed before launch because v0.0.15 still requires
an explicit MCP target. The helper was corrected to supply fixed pro_a module,
transport and saved operator paths/identity. Windows PowerShell quoting was also
corrected and the exact original generated profile bytes were recovered. A repeat
start preserved the same running managed process. These implementation checks are
preserved in the receipt; the operator need not reconstruct any CLI parameters.

The final read-only DB integrity/schema/count/hash checks match the initial Stage 2
snapshots, including a recheck after the final human recovery response. The operator
confirmed a new successful `pro_a_health` call after restart: both databases
readable, schema 11, read-only true, pro_a 0.5.1 and all 11 original capabilities.
This completes the stop/loss/restart/recovery gate with human Web evidence.

## Operator workflow and qualification result

Small fixed-purpose helpers under `scripts/mcp` are also installed beside the
stable runtime. From that directory:

```powershell
.\start-pro-a-mcp.cmd
.\status-pro-a-mcp.cmd
.\stop-pro-a-mcp.cmd
```

The fixed-purpose `.cmd` launchers invoke Windows PowerShell with `-NoProfile`
and process-scoped `RemoteSigned`, addressing this host's observed default script
restriction without changing permanent execution policy. When calling repository
`.ps1` copies, pass `-RuntimeRoot <STABLE_RUNTIME_ROOT>`.
The helpers invoke native `runtimes connect/status/stop` for the fixed alias
and inspect the detailed loopback health endpoint. Start runs from the stable
directory and restores the caller's location and proxy environment afterward.
They do not expose a general command runner. Syntax validation passed; start
correctly failed before launch while the private key file was absent.

Machine-local `runtime-settings.json` contains only these setup fields and is
saved as UTF-8 with BOM for Windows PowerShell 5.1 non-ASCII path handling:

```json
{
  "control_plane_http_proxy": "<CREDENTIAL_FREE_HTTP_PROXY_URL>",
  "tunnel_id": "<EXISTING_TUNNEL_ID>",
  "workbench_config": "<EXISTING_PRIVATE_WORKBENCH_CONFIG>"
}
```

| Gate | Result / evidence |
| --- | --- |
| Exact baseline, wheel source and 11-tool discovery | PASS, automated |
| Real local health/search/View/context | PASS, automated |
| Native process/health/readiness | PASS, structured status |
| Actual control-plane polling | PASS, detailed health; native summary remains unknown |
| Initial Web and final recovery health | PASS, human operator |
| Clean stop and fresh Web loss | PASS, native stop + two human-reported timeouts |
| New shell without key/proxy environment setup | PASS, automated Windows PowerShell 5.1 |
| Runtime survives launching-shell exit | PASS, automated |
| Repeated start without duplicate process | PASS, automated |
| Read-only integrity and forbidden action counters | PASS, bounded local audit/snapshots + human Web observations |
| User-logon auto-start | DEFERRED |

All six forbidden counters are zero: Production writes, Workbench writes, provider
calls, processing retry, reprocess and advertised mutation tools. Evidence scope
is explicit in the receipt; no continuous remote/host-wide action trace is claimed.
Application tests were not rerun for these operational launchers and documentation;
validation exercised the installed wheel, actual native lifecycle and real reads.

Only the six operational launchers and these two sanitized documents enter Git.
Private key/config/profile/settings, wheels, virtualenv and transient logs stay
outside the change. After the PASS gate, review the complete diff and scan it for
credentials/private paths, then commit, push and create a Draft PR; never merge.
Commit SHA and PR URL are reported externally after publication.

No browser automation was attempted. Human Web evidence is explicitly acceptable.
Auto-start is separately deferred because proxy readiness at Windows user logon
has not been qualified; no Windows service, scheduled task or administrator
requirement was added. Proxy availability at login remains
unqualified. PC, Python installation, local proxy, native Tunnel process, private
config and databases must remain available. Sleep/reboot/unattended availability
is not claimed.

The outbound connection and running-client dependency follow OpenAI's
[Secure MCP Tunnel documentation](https://developers.openai.com/api/docs/guides/secure-mcp-tunnels);
exact lifecycle and reference syntax above come from the installed CLI help.
