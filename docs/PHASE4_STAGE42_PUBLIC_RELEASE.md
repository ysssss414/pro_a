# Phase 4.2 public release projection — v0.5.0

Version **0.5.0** packages the qualified Phase 4.2 private-host research
Workbench. This projection is requalified before publication; it does not itself
authorize a push, pull request, merge, tag, GitHub Release or Production Apply.

## Product scope

- Persistent Review Workbench with durable, conflict-safe human review and
  atomic sealing.
- Explicit Claim–Node attribution and a guarded operational promotion handoff.
- Current View Workbench with governed drafts and separate privileged activation.
- Direct Impact / Evidence Change inspection.
- Research / Explorer integration, stable Node/Claim/Source routing, Coverage,
  Research Question and Gap navigation, and noncanonical follow-up notes.
- Durable `cloud-inference-v1` jobs with idempotent submission, worker fencing,
  bound prompt/runtime/model/budgets, attempt history and fail-closed recovery for
  unknown external outcomes.
- Private clean-PDF upload and the operator Golden Path through native review,
  attribution, qualification and disposable activation drills.
- Coordinated Workbench backup/restore with hashes, drained-worker checks and
  explicit path rebinding for a restored private host.

The Workbench keeps its SQLite state and private artifacts separate from the
canonical knowledge database. Browser and worker processes have read-only
canonical access. Real Production Apply remains an external privileged operation
that needs a separate exact authorization, baseline, backup, transaction and
receipt.

## Provider qualification

The currently qualified path is `provider=deepseek` with
`model=deepseek-flash`. The real Source-analysis and semantic-decomposition
adapters were each validated through the durable cloud-job path using a bounded
live-provider smoke. Provider request identifiers, job identifiers, prompts,
payloads, private Source identity and private smoke artifacts are excluded from
this public projection.

Both real adapter calls completed and passed durable output validation. A later
synthetic-fixture review-packet step stopped with `BLOCKED_EMPTY_CANDIDATE_SET`;
this is a non-blocking fixture outcome after the provider contracts had passed.
It does not qualify a complete live Source upload → cloud extraction → review
packet → human review → attribution → Production path.

## Deployment and operating limits

- Source upload accepts clean, non-encrypted PDFs with extractable text on every
  required page, with a maximum size of **20 MiB**.
- OCR, scanned/image-only PDFs, encrypted PDFs and corrupt PDFs are unsupported.
- Deployment assumes one trusted operator on a private host, SQLite and one
  durable worker. Multi-tenant SaaS and enterprise RBAC are not qualified.
- Local models remain deferred.
- Live-provider latency SLOs and cost SLOs are unqualified.
- Full live Golden Path quality is unqualified.
- Real Production Apply is not qualified or authorized by this release.

The public source projection contains only sanitized source, tests,
documentation and public manifests. Private Workbench databases, Source files,
runtime artifacts, credentials, raw provider payloads, request IDs, receipts and
backup archives remain outside the tracked tree.
