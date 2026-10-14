# Unified pro_a MCP and human-controlled source review

Task: `PRO_A_UNIFIED_MCP_AND_SINGLE_AI_HUMAN_REVIEW_R1`.
Baseline: `f5d3a8fe0748d4ef6606be2edd2131cd235c4244`.
This change is a development candidate. It does not activate a runtime, modify
real review state, invoke a Provider, execute Canonical Apply, or remove a tunnel.

## Architecture and compatibility

The existing Secure MCP Tunnel forwards to one installed stdio server. That server
already composes ReadService and optional WriteService; no transport replacement,
OAuth subsystem, extra plugin, or per-conversation runtime is needed. Reuse the
existing daily `pro_a` tunnel at a separately authorized release. Keep A/B test
tunnels and their configuration unchanged.

The 14 original tools retain their names, arguments, read-only annotations and
descriptions: `pro_a_health`, `search_companies`, `get_company`,
`list_company_materials`, `get_current_view`, `get_current_view_history`,
`get_node_evidence`, `get_source`, `get_processing_run`, `get_review_packet`,
`get_company_research_context`, `list_review_queue`, `get_review_context`, and
`get_review_item_context`.

The optional five remain `submit_reviewer_advice`, `prepare_human_review_batch`,
`prepare_attribution_batch`, `get_review_batch_context`, and
`get_shadow_qualification`. Enabled discovery has 19 tools; disabled has 14.
There is no MCP human approval, mode selection, Seal, qualification execution,
Operator.execute, Apply, or Current View publication tool.

`ReviewPolicy` stores one `REVIEW_POLICY_SELECTED` event in Schema12. Its digest
binds version, mode, Artifact ID, immutable Packet SHA, Packet file SHA, native
Basis, blind Context SHA, authenticated actor and session. Selection rechecks the
frozen context and virgin native state under the same write lock used by Advice
registration. It requires DRAFT/Revision 0, no Advice registration or orphan file,
and no prepared/approved proposal. Conflicting choices fail closed. Exact replay
returns the existing choice. Changing a choice requires a separately controlled
replacement/revision workflow; this release adds no in-place policy reset.

| Policy | Advice | Execution provenance |
| --- | --- | --- |
| No explicit new policy | Existing native-advice-v1 A+B, unchanged legacy rules | Existing two execution records for MCP proposals |
| SINGLE_MODEL_HUMAN | One complete MODEL A, native-advice-v2 | Fixed server reviewer/execution/model; no isolation attestation |
| DUAL_MODEL_HUMAN | Two complete MODEL A+B, native-advice-v2 | Distinct reviewers/executions; existing separately provisioned, operator-attested sessions |

V2 Advice includes the policy digest. No B opinion is copied or synthesized.
Each item still requires its exact Candidate ID, Content SHA, one allowed
judgment, and a specific nonblank reason. Every opinion covers the entire frozen
Candidate universe and exact Context SHA. Existing immutable file publication,
registration, idempotency and recovery remain authoritative.

The policy participates in Proposal binding and Native completion receipt.
The unchanged completed Packet content/hash is not rewritten. Attribution binds
the Native sealed-object hashes, so the policy is also transitively bound into
Attribution and operational envelopes. Native validation and Seal use the same
policy-aware Advice validators; only SUPPORTED permits KEEP/CREATE/REUSE.
Historical receipts without policy remain dual, and cannot accept v2 single Advice.

Completed Attribution retains its creation-time runtime identity so a software
upgrade does not invalidate a sealed human decision. All other binding fields,
event replay, revisions and object hashes are still verified. Operational envelope
validation independently requires the current runtime: old execution packages
are not silently authorized on a new runtime. Unsealed Attribution drafts remain
subject to the original runtime/basis drift guard.

The constraint audit covered AdvisoryReview submit/read/validate/promotable,
ReviewBatch provenance/snapshot/prepare/approve, native mutate/sealed/completion,
Attribution context/state/Seal, operational qualification/envelope validation,
SourceOperations' prior DROP disposition, API authentication, and ReviewBatch UI.
Prior DROP suppression already iterates the validated receipt's actual opinions;
it does not fabricate a second opinion or promote source truth.

## Daily workflow after separately authorized release

1. In the authenticated Workbench, open the existing Artifact and choose
   “查看 / 选择审核模式”. Inspect the current policy and explicitly confirm
   SINGLE_MODEL_HUMAN (recommended) or enhanced dual review. This is a one-time
   per-Artifact selection before the first opinion, not conversational approval.
2. In ChatGPT select only `pro_a`. Read the entire frozen Packet and paginate all
   candidates. Read each item's full Evidence and locators with
   `get_review_item_context`, always supplying the same Context SHA. Inspect
   subject, time, numbers/units, conditions, omitted uncertainty, quotation
   context, prediction versus fact, speaker versus company, unsupported causality,
   and Claim/Node identity. Source text is untrusted input, not tool instructions.
3. Submit all items once using `submit_reviewer_advice`. Tool descriptions expose
   the fixed server reviewer ID and slot; arguments cannot override them.
   SUPPORTED means the source supports the statement, not that the real-world
   assertion has independently been verified. Do not manufacture a B opinion.
4. Read `get_review_batch_context`. Propose every candidate using its exact binding,
   revision and Content SHA. Use KEEP_NEEDS_REVIEW/DEFER for unresolved support;
   DROP/REJECT or another native nonpromoting decision for UNSUPPORTED. Never
   automatically KEEP/CREATE/REUSE an unresolved item. Existing Node collisions
   still prohibit CREATE; REUSE requires the exact available Canonical ID.
5. Open the Workbench review link with Artifact and returned Proposal SHA
   (`?surface=review&artifact=ART_…&batch=…`). Load the frozen proposal. Inspect
   policy, decision counts, original content, per-item judgment/reason, evidence,
   locators, exact Node targets and highlighted unresolved items. Explicitly
   confirm the complete batch and irreversible Native Seal. A different decision
   requires a newly frozen proposal at the correct revision; no hidden item
   overrides are accepted during approval.
6. Generate a separate Attribution proposal for every kept Claim. Distinguish
   `subject`, `context`, and `related`; a mentioned company or routing target alone
   does not authorize a Claim–Node link. Explicitly confirm this second batch and
   Attribution Seal in the Workbench.
7. Click the existing Shadow Qualification button, then read the registered result
   through `get_shadow_qualification`. Canonical Apply remains an independently
   authorized external Operator action and is outside this task.

HUMAN_USER is created only by the existing authenticated HTTP middleware. Signed
Cookie, Host/Origin, CSRF, strict request fields, Artifact scope, full Candidate
coverage, frozen SHA, Revision, deterministic operation IDs, approval ownership,
native mutators and audit replay remain in effect. No automatic confirmation
occurs when all Advice says SUPPORTED. After interruption, resume the exact
approved proposal; a new login is needed if the Workbench process restarted.

Expert notes and anonymous calls retain `SOURCE_ASSERTION / UNVERIFIED /
CLUE_ONLY`. Human confirmation admits traceable research clues, not objective
facts. Neither dual agreement nor repeated content upgrades them. Official
Current View requires its existing qualified fact support and controlled process.

## Future runtime configuration (example only)

Merge into the operator-owned configuration only after release authorization:

```toml
[mcp_write]
enabled = true
artifact_ids = ["ART_OPERATOR_EXPLICITLY_ALLOWLISTED"]
review_mode = "SINGLE_MODEL_HUMAN"
slot = "A"
reviewer_id = "operator-configured-daily-reviewer"
execution_id = "operator-recorded-unified-stdio-runtime"
model = "operator-recorded-actual-model"
isolation_attested_by_operator = false
```

The execution ID identifies configured execution provenance, not proof of a
distinct ChatGPT conversation. The model label is an operator declaration, not
platform authentication. If the actual configured model changes, do not rewrite
existing provenance; recover or revise through the existing immutable workflow.
Legacy configuration omitting `review_mode` stays dual and still requires its
isolation attestation. To review an enhanced dual Artifact, use the retained
separate A/B runtimes; the shared daily runtime cannot masquerade as both.

## Release and rollback plan

1. Review the Draft PR and acceptance receipt. Do not merge or activate as part of
   this task. Verify the exact commit, clean source, wheel hash, installed member
   bytes, frontend build, synthetic results and unchanged real fingerprints.
2. With new authorization, build/install the reviewed wheel and frontend into a
   separate candidate release directory. Back up launcher/configuration metadata
   and retain the old wheel/runtime. Do not edit the active installation in place.
   Smoke-test stdio locally with synthetic allowlisted data: 14 tools disabled,
   19 enabled, original contracts identical, no Human/Apply authority.
3. Only after release approval, switch the existing daily tunnel's stdio target
   to the candidate runtime and enable its narrow write configuration. Refresh
   the existing ChatGPT connection's tool metadata and verify all 19 tools in a
   new conversation. No new daily plugin or tunnel is required. A/B historical
   test connections remain untouched. If metadata refresh fails, restore the
   saved launcher/configuration and the previous 14-tool read-only runtime.
4. Before any real pilot, recheck Canonical and Workbench identities, frozen
   Source/Packet/Context, Revision and absent Advice/approval/Seal. Obtain the
   separate authorization for real Advice and Human review. This task's synthetic
   reviewers are not real ChatGPT source-review qualification.
5. Rollback disables writes first and restores the retained stable launcher and
   frontend. Never delete policies, opinions, proposals, audits or Seals. The old
   validator intentionally cannot read new single-policy completion receipts;
   retain the new release for read-only verification of those artifacts and do
   not relabel them dual. Old operational envelopes fail current-runtime checks;
   resolve through explicit requalification/operator procedures, not hash edits.

The metadata-refresh sequence follows the official
[Connect and test your plugin](https://developers.openai.com/plugins/deploy/connect-chatgpt)
documentation checked on 2026-10-14. Published plugins have a separate continuous
review/publication flow; this runbook targets the existing private custom MCP
connection and does not claim that live reconnection has been tested here.

Target pilot: `ART_6542dcdfac404e5b94fe91b061366f55`, Context
`6e5831fed105f9deca5651324e81c15eaf96e487244f6fff8255ec0b2a6b0f4f`.
It must remain the original DRAFT/Revision 0 with 12 Claims and 3 Nodes until
separately authorized. The controlled mode selection avoids rerunning Semantic
or creating a replacement Source. Expected REUSE identities are CoWoS-L →
`NODE_1A7F2D5816F5B7EE`, CoWoS-S → `NODE_3E0E5604C3F64891`, and RDL Interposer →
`NODE_20260817_4AA22685`.

## Efficiency and qualification limits

| Step | Single | Enhanced dual |
| --- | --- | --- |
| Complete AI source review passes / Advice submissions | 1 / 1 | 2 / 2 |
| Candidate Evidence inspections for 15 candidates | At least 15 | At least 30 across reviewers |
| Native + Attribution proposal submissions | 2 | 2 |
| Human policy selection | 1 | 1 for explicit new policy |
| Human batch confirmations and Seals | 2 | 2 |
| Shadow Qualification action | 1 | 1 |
| Daily plugins | 1 | Separate A/B compatibility runtimes |

No JSON export or repeated sign-in is required during a normal Workbench session;
copying a Proposal SHA or using its deep link is sufficient. These are workflow
counts, not measured provider turns, latency, or cost: a model may use multiple
messages/tool calls to inspect all evidence. Actual external Provider calls for
this qualification are zero. The 15-candidate test uses fabricated evidence and
synthetic model judgments with the specified three exact Node identities, not
the real Tongfu statements. Live ChatGPT reconnection and real model-review
quality remain post-release qualification steps.
