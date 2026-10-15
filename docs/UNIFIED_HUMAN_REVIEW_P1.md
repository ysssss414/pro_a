# Unified human review P1

P1 lets a logged-in human inspect and freeze Native and Claim–Node Attribution decisions in one Workbench workflow. One approval authorizes both native seals. It does not authorize Canonical promotion, register an Operator Grant, or call a model. The prior separate workflow remains available for historical records.

## Contract and shared validators

`UnifiedReview` coordinates existing `ReviewWorkbench`, `ReviewBatch`, and `Attribution` services. `ReviewBatch.validate_native` contains the existing native batch validator, without a second implementation. `Attribution.universe` is shared between draft preview and sealed context. The public `Attribution.context` still requires `NATIVE_REVIEW_NOT_SEALED` to be satisfied; previews cannot pretend to be sealed artifacts.

The proposal freezes the Packet/file/basis/Context identities, formal Review Policy, registered AI Advice and execution provenance, complete Native decisions, prospective accepted Claim and Node universe, every Attribution outcome/scope/role/reason, current Runtime identity and step order. Its SHA-256 is deterministic. KEEP creates an Attribution obligation; KEEP_NEEDS_REVIEW and DROP do not. Only qualifying CREATE/REUSE Nodes and an existing controlled Company Material Intent target enter the target universe. Company intent does not automatically create a link. NO_LINK and DEFER remain explicit choices. Unsupported AI judgments and CREATE collisions still use the unchanged validators.

## Human workflow

1. Select Review Policy under its existing rules before Advice. Complete the required model review through the P0 engine.
2. Enter **统一人工审核** from Review. Inspect each candidate's evidence and advice, and enter Native decisions and reasons.
3. Prevalidate Native decisions. The resulting target list is derived from this draft, not a prior sealed Packet.
4. Review every KEEP Claim's Attribution outcome. Select exact Node IDs and roles or explicitly choose NO_LINK/DEFER. Changing Native invalidates the dependent local Attribution draft.
5. Freeze the complete plan, inspect all frozen decisions, and confirm once.
6. The Workbench persists Native decisions/seal and then Attribution decisions/seal. Machine continuations always use the same approved SHA. No Operator action is started.

## Persistence and recovery

No schema migration is needed. Schema12 source-processing events hold `UNIFIED_REVIEW_PREPARED`, `UNIFIED_REVIEW_APPROVED`, `UNIFIED_REVIEW_RESUMED` and `UNIFIED_REVIEW_COMPLETED`. Existing native operation/audit tables and sealed artifacts remain the authoritative review products. The completed coordinator event references their exact object IDs and hashes.

Approval ownership is acquired with `BEGIN IMMEDIATE`. Competing proposals cannot acquire the same review. Both existing mutation entry points check the durable unified owner inside their write transaction, preventing legacy pages and legacy batches from inserting unapproved decisions after unified approval. Each authorized stage/step has an operation ID derived from the full proposal identity; mismatched replay fingerprints fail closed. Recovery uses the original reviewer and approval session for native operation identity, while a new login's resume request is separately audited.

The HTTP endpoint executes a bounded number of new steps per request. React continues the same frozen approval until both seals are complete. Lost responses are handled by reloading the same proposal; the user can resume without approving another plan. Completed operations are retained and verified, never rolled back or cleared automatically. An interrupted Native seal cannot cause Attribution to be regenerated from different decisions.

Runtime, Context or identity drift stops execution. Do not deploy or roll back across an unfinished approval: first resume under its exact qualified Runtime or preserve it for explicit recovery investigation. A code rollback must never restore an older Canonical database over successful production knowledge. Existing completed artifacts remain readable through the historical contracts.

## HTTP boundary

Routes are under `/api/workbench/v1/reviews/{artifact_id}/unified`:

- `GET /`: current bound context, advice and proposal references.
- `POST /preview`: validate complete prospective Native decisions and derive Attribution universe; no persistence.
- `POST /proposals`: validate and freeze the complete plan; no human approval or seal.
- `GET /proposals/{sha}`: read the immutable proposal and durable execution status.
- `POST /approval`: confirm or continue exactly that approved proposal, using the server's authenticated HUMAN_USER identity.

The existing signed cookie, CSRF, Host and Origin protections apply. Clients cannot supply an actor, session, principal type or replacement decisions in an approval request. MCP gains no approval tool and retains its existing tool contracts. P1 does not combine the separate Policy selection with final plan approval.

## Qualification

Tests use isolated databases and mock Advice. They cover single/dual policy, exact universes, bad identities/roles/hashes, Context drift, missing Candidates, non-SUPPORTED admission, zero KEEP, deferred targets, interruptions across both stages, replay, conflicts and authenticated HTTP requests. React tests cover edits, dependent draft invalidation, frozen-hash approval and lost-response recovery. Private historical Packet copies are used for actual Workbench HTTP/browser tests; no private source or production credential belongs in this repository.

P2 remains separate: no second production confirmation or automated Operator execution is implemented here.
