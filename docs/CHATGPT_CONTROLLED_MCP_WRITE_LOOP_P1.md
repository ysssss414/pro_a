# ChatGPT controlled MCP review write and human approval bridge

P1 implements an opt-in review entry point, using Schema12 and the existing native
Advice, ReviewWorkbench, Attribution and Qualification contracts. It does not
activate a real runtime, migrate a database or expose Canonical Apply.

## Trust decision (G1)

The deployed launchers use a managed Secure MCP Tunnel with a local stdio child.
The tunnel authenticates its connection to the OpenAI control plane; the current
pro_a tool handlers receive no verified end-user identity or signed, parameter-bound
human-approval receipt. We therefore cannot turn conversational approval into
HUMAN_USER authority.

Official documentation inspected on 2026-10-13:

- [Secure MCP Tunnel](https://developers.openai.com/api/docs/guides/secure-mcp-tunnels): outbound forwarding to a configured stdio/HTTP target; tunnel permissions and application identity are separate concerns.
- [Authentication](https://developers.openai.com/plugins/build/auth): application resource servers must validate OAuth tokens, including issuer, audience, expiry and scopes. This is not implemented by the existing stdio service.
- [MCP approvals](https://developers.openai.com/api/docs/guides/tools-connectors-mcp): API approval requests bind a tool call and arguments. This does not establish that the current local server receives a verifiable HUMAN_USER approval receipt.
- [Refresh metadata](https://developers.openai.com/plugins/deploy/connect-chatgpt): custom MCP changes require server deployment/restart, connection Refresh, metadata verification and a new conversation. Authentication changes may require a new linking flow. Published plugins have a separate review flow. No connection or plugin was refreshed in this task.

P1 uses the existing Workbench login token, signed HttpOnly SameSite Cookie,
Origin/Host validation and CSRF protection. Only authenticated HTTP middleware
creates the HUMAN_USER principal. The batch endpoint accepts a frozen proposal
hash and explicit confirmation, never an actor, session, token, items override or
principal_type. Existing local Python authority is unchanged.

## MCP surface (G2–G5)

The original `pro-a-mcp-stage3-v2` 14 tools, schemas, descriptions and read-only
annotations are unchanged, including when the extension is enabled. The separate
WriteService adds:

| Tool | Effect |
| --- | --- |
| `submit_reviewer_advice` | Register one complete MODEL opinion with AdvisoryReview.submit; read its durable file and registration immediately |
| `prepare_human_review_batch` | Store an immutable Native proposal; no Human Decision |
| `prepare_attribution_batch` | Store an immutable Attribution proposal; no Attribution decision |
| `get_review_batch_context` | Read the full bound Native or Attribution preparation context after both advice submissions |
| `get_shadow_qualification` | Read a paginated projection of an already registered, dual-Seal qualification; never execute qualification or Apply |

Three tools are annotated as writes and two as reads. A batch is limited to 100
items and the existing MCP payload/text limits. Larger inputs fail closed. There
is no background model invocation, external Provider call or model budget spend.

Enablement is absent by default. A separately provisioned local stdio instance
requires Schema12, valid existing Workbench bindings, explicit enablement, an
Artifact allowlist and a fixed Reviewer slot/execution/model binding. HTTP writes
are rejected by the CLI. Model-supplied reviewer_id/slot must match local policy;
the model cannot choose another execution identity. Example configuration for
future operator setup (not an activation instruction):

```toml
[mcp_write]
enabled = false
artifact_ids = ["ART_00000000000000000000000000000000"]
slot = "A"
reviewer_id = "reviewer-A"
execution_id = "separate-chat-A"
model = "operator-recorded-actual-model"
isolation_attested_by_operator = false
```

Provision B separately with its own slot, reviewer and execution ID. Both must
use the same frozen context. B must not be given A's transcript or conclusions.
The operator must actually verify this separation before attesting it. Distinct
IDs alone do not prove independent model reasoning. P1 records
`OPERATOR_ATTESTED_SEPARATE_SESSION_NOT_PLATFORM_PROVEN`; it does not claim
platform-certified model identity, automatic isolated ChatGPT model execution or
real ChatGPT end-to-end qualification. Separate real ChatGPT sessions can submit
structured opinions directly without exporting JSON files, once an operator has
explicitly authorized and provisioned those isolated runtimes.

## Human workflow

1. Reviewers A and B read the same blind `get_review_context` / item evidence and
   call `submit_reviewer_advice` in their respective sessions. Each opinion is
   immutable and covers every candidate/content hash. Duplicate exact submissions
   reuse native registration; conflicting submissions fail.
2. The synthesis session reads `get_review_batch_context(kind="native")`. Pass
   its exact `binding` and `revision`, all candidates/content hashes, decisions,
   reasons and precise Node REUSE IDs to `prepare_human_review_batch`.
3. HUMAN_USER signs in to the existing Workbench Review page. Open the Artifact
   and enter the returned Proposal SHA-256 in “Frozen batch approval”. A deep link
   may use `?surface=review&artifact=ART_…&batch=…` (loading remains explicit).
   The page shows decision counts, A/B disagreements and reasons, candidate
   evidence, entity targets, binding identities and irreversible Seal effects.
4. One checkbox and approval click authorizes the exact complete Native proposal
   and Native Seal. All decisions and the Seal call the original native mutator.
   KEEP/CREATE/REUSE require A and B both SUPPORTED. Native pending/drop/reuse
   semantics and validators remain authoritative.
5. Read `get_review_batch_context(kind="attribution")`, then propose every kept
   claim via `prepare_attribution_batch`. Use only exact available Node IDs and
   `subject`, `context`, `related` roles; routing, titles and name similarity are
   not association evidence. The same Workbench page confirms the complete
   Attribution proposal and Attribution Seal.
6. The post-Seal page button invokes the existing authenticated Workbench
   `/attribution/{artifact_id}/qualify` endpoint. ChatGPT then reads
   `get_shadow_qualification`; pagination exposes the complete safe difference,
   INSERT/UNCHANGED, counts, envelope/baseline/diff identities, withheld-column
   hashes and B-lite governance values. Registered execution receipts are labeled
   unverified here; this endpoint does not invent Operator verification.

Native/Attribution context, Packet bytes, Content SHA, basis and revision are
bound to the proposal. The server rechecks the binding during execution. There
is no silently refreshed proposal and no write to the original packet.

## Durability and concurrency

`MCP_ADVICE_CONTEXT`, `MCP_BATCH_PREPARED` and `MCP_BATCH_APPROVED` use the existing
append-only Source processing event mechanism. No schema migration is added.
An approval records the authenticated actor/session and proposal hash before
execution. Each decision and Seal uses a deterministic operation ID derived from
the proposal hash and step, and the native expected revision.

The batch is deliberately a sequence of native transactions, not an atomic bulk
transaction. An interruption preserves the approved proposal and committed
operations. A new Workbench process requires login again and resumes only those
exact operation IDs/requests using the durable original audit identity. Concurrent
replays converge through native idempotency; conflicting edits or another plan
cause revision/binding failure. An error never returns a successful batch receipt.

## Qualification and limits

`tests/test_mcp_controlled_write.py` includes the required 12-candidate fixture:
11 Claims + 1 exact Node REUSE; 9 supported agreements + 3 B-UNCERTAIN
disagreements; 8 KEEP / 3 KEEP_NEEDS_REVIEW / 1 REUSE; 7 NO_LINK / 1 LINK(context).
Two separate Python reviewer simulator processes see only the same frozen
evidence, and submit through separate actual MCP SDK client/server sessions.
These are synthetic reviewers, not real model calls.

The suite checks immutable opinions, missing execution provenance, same-execution
rejection, no Human writes before authentication, CSRF/extra-field rejection,
Packet/Context/Basis/Revision/Content drift, unsupported promotion, illegal Node
IDs/roles, partial-write recovery after application restart, concurrent replay,
safe disclosure, and unchanged synthetic Canonical bytes. Operator.execute is
tripwired. Original 14-tool read-only tests and native Advice tests remain intact.

This is a development Draft PR, not a production activation receipt. Real runtime
configuration, installed package, Workbench, Canonical, Provider and Source
processing are not mutation targets. Existing read-only deployment remains in
place. Real ChatGPT account permissions, two-session independence and reconnect
behavior must be qualified separately before a future activation.

P2 remains narrowly scoped: exact-envelope approval bound to a verified human,
an expiring single-use authorization consumed only by the independent local
Operator, and a read-only MCP receipt reconciliation entry point. No remote SQL,
Operator.execute or Canonical Apply tool is added in P1.
