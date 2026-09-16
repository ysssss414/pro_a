# Phase 4.2 Stage 0: native Review reads

Based on public `v0.4.0` (`766c304d6a90f5ddf8873c2c8fb430ca3ac7846c`).
Stage 0 displays registered, validated native **blank** operational review packets.
The only new HTTP POST establishes an operator session. Registration is an operator
command. Review decisions, drafts, completion, uploads, model execution and promotion
are unavailable.

## Local synthetic walkthrough

Use the existing Python environment with the project installed and the frontend's
locked dependencies (`npm ci`). No model credentials are needed. From the repository
root, create a fresh, ignored fixture directory:

```powershell
python tests/workbench_fixture.py workspace/stage0-demo
python -m pro_a.workbench --config workspace/stage0-demo/workbench.toml init
python -m pro_a.workbench --config workspace/stage0-demo/workbench.toml register --packet EXEC_SYNTHETIC_STAGE0/review/packet.json --run EXEC_SYNTHETIC_STAGE0/engine
$env:PRO_A_WORKBENCH_TOKEN = python -c "import secrets; print(secrets.token_urlsafe(32))"
python -m pro_a.workbench --config workspace/stage0-demo/workbench.toml serve
```

In another terminal, run `npm run dev` from `frontend`. Open
`http://127.0.0.1:5173/?surface=review` and enter the operator session token from
the server environment. Keep the token private. It is never stored in a URL or
browser localStorage. The fixture contains one Claim, one Node with an immutable
alias, one Parent Placement and one excluded functional relation. It contains
only synthetic text, with paragraph/section metadata and intentionally absent
page metadata.

The fixture builder first creates a disposable legacy schema with `Database`,
then explicitly invokes the existing **test-only** `apply_synthetic_migration`
using the fresh database's hash and a distinct forbidden Production target.
It validates schema 0.2.3 before marking the fixture `SYNTHETIC_PUBLIC_SAFE`.
This preparation is confined to the test helper; application startup never calls
`Database.init_schema`, a migration, a model or a Production executor.

## Private configuration and operator registration

Copy `workbench.example.toml` into an ignored location and set the three dedicated
paths. Relative paths resolve against the TOML file. Knowledge schema 0.2.3 and
its exact Foundation execution contract must already exist. Missing, legacy,
unknown or drifted schema fails closed. Stage 0 does not prepare Production.

The Workbench state database is separate from the knowledge database and artifact
tree. Its independent schema version is `1`, with only `workbench_meta` and
`registered_packets`. `init` is explicit and idempotent; it refuses incompatible
state. Future state migrations must be explicit and must preserve the pinned
mode/root bindings. Back up the state database before such migrations.

`init` writes `.workbench-mode.json` in the artifact root, outside execution roots.
`register` accepts only root-relative packet and native run/engine paths. It
references existing bytes, storing a random registered handle, native identity,
packet file hash and file inventory. Re-registering the identical input returns
the same handle. It never creates a completed packet or rewrites an execution.
Existing completed packets are not accepted by this Stage 0 command.

Keep artifact directories and configuration operator-owned. The web process needs
read access to artifacts, state and knowledge; operator registration needs write
access only to Workbench state. Use OS permissions to grant only those accesses
when running separate service/operator accounts. This implementation enforces
actual `file:...?mode=ro` connections plus `query_only=ON` for **every web SQLite
connection**, including the composed Explorer API. An application read cannot
upgrade its SQLite connection by switching `query_only` off.

The registry checks lexical traversal, Windows reparse points/junctions, symlinks
and hardlinks before native validation. It hashes the packet and full native run
tree, validates through unchanged `validate_blank_review_packet`, then checks the
inventory again. Every list/detail read repeats those checks against registration.
Changed or unavailable inputs produce a fixed error rather than stale evidence.
The supported deployment trusts the host's operator and filesystem ownership;
these checks are not a sandbox against a privileged local process concurrently
replacing files or editing application code.

## Session and deployment boundary

Use the new `python -m pro_a.workbench ... serve` entry point for Workbench.
The legacy Explorer entry point retains its existing local GET behavior and does
not serve this session boundary. Do not publish the legacy server as Workbench.

All routes on the new application, including Explorer GETs and API documentation,
require an operator session. Login additionally requires the configured Origin and
a secret of 32–512 characters; generate it randomly. The signed session identifies
the operator and mode, expires after eight hours, and is invalidated on server
restart. Cookies are HttpOnly and SameSite Strict, and Secure in remote mode.
Responses are non-cacheable. No cross-origin access is enabled.

Host must match the configured origin authority. Any supplied Origin must match
exactly. Unsafe HTTP methods also require Origin and the session's CSRF token in
`X-CSRF-Token`; login is the sole CSRF-token exception because it requires the
operator credential. There are currently no review writes, even with a valid CSRF
token. Future writes must stay inside this middleware. No users, roles or SSO are
introduced.

Local mode still requires authentication and rejects non-loopback clients and
non-loopback launch hosts. Remote mode requires an HTTPS origin. Serve the built
React app and proxy `/api` through a private HTTPS host, preserving Host/Origin.
Keep the backend bound to loopback (the default); do not expose the plaintext
backend port. Forwarded headers are disabled. TLS/proxy provisioning is outside
Stage 0 and was not deployed by acceptance.

`DEMO` requires an explicitly marked synthetic knowledge database, a DEMO artifact
root and native `SYNTHETIC_TEXT` sources. `PRIVATE` rejects the synthetic DB marker.
The state DB pins both mode and configured roots; changing a mode or borrowing
another installation's state/root fails closed. Operators must never relabel
private content as synthetic. These markers enforce configuration separation;
they cannot determine whether arbitrary prose is confidential.

## Read contract and validation

The read API is under `/api/workbench/v1`: `GET /session`, `GET /review-packets`
and `GET /review-packets/{artifact_id}`. `POST /session` logs in. There is no HTTP
registration, arbitrary file reader or mutation route.

The projection includes native counts, item IDs/types, all native item content,
content hashes, allowed decisions, decision effects and the complete excluded
relation inventory. Claims retain KEEP/DROP/KEEP_NEEDS_REVIEW semantics; Nodes
retain CREATE/REUSE/DEFER/REJECT; Parent Placements retain their native dependency
metadata. Missing metadata is displayed as absent. Alias review is not invented.
The UI exposes exact evidence text only within the authenticated configured mode.

Source filename/location, repository refs, Production baseline details and raw
artifact envelopes are not DTO fields. Unsupported sensitive fields inside native
content cause registration/read rejection rather than silently dropping evidence.
Errors never serialize input objects, private paths or native exception details.
No Source file download or PDF rendering is implemented; this is packet inspection.

Run the Stage 0 suite and relevant public regression slices:

```text
python -m pytest -q tests/test_workbench_stage0.py
python -m pytest -q tests/test_api.py tests/test_query.py tests/test_phase3f_review_completion.py tests/test_phase4_orchestration.py tests/test_foundation_schema_migration.py tests/test_foundation_native_evidence.py tests/test_phase3f_public_sanitization.py
npm test -- --run
npm run build
```

Frontend commands run from `frontend`. Stage 0 uses its own public-safe native blank
fixture; historical private-fixture skips are reported separately and never count
as Stage 0 coverage. Acceptance reports, browser captures, local configs, state
and generated packets stay in ignored `workspace/` directories. Stage 1 requires
separate authorization.
