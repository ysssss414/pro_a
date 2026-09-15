# Phase 4.2 release notes draft

Recommended version: **0.5.0**. The current public release is 0.4.0 and Phase 4.2
adds backward-compatible product capabilities, so a minor version is appropriate.
This draft does not change package versions, create a tag or authorize release.

Phase 4.2 adds an authenticated private-host Review Workbench around the existing
canonical read model. It persists human review, explicit Claim-to-Node
attribution, guarded promotion handoff, Current View drafts, Direct Impact
inspection, Research Explorer pages and follow-up notes in an isolated Workbench
database. Durable `cloud-inference-v1` jobs bind runtime, prompt, model and budgets,
fence workers, preserve attempt history, and fail closed on unknown external
outcomes. The clean-PDF Source Golden Path connects private upload, durable fake
provider qualification, native review packets, human review, attribution, shadow
qualification, disposable operator activation and research discovery with stable
lineage.

Release qualification is offline and uses synthetic public-safe fixtures. The web
and worker processes retain read-only canonical access and have no Production
Apply route. Coordinated Workbench backup/restore covers SQLite state and private
artifacts, verifies hashes, requires drained workers, and supports explicit path
rebinding to a new private location. The public candidate excludes private
acceptance workspaces, private Source bytes, credentials and raw provider payloads.

Known limits:

- Source upload supports non-encrypted clean PDFs with extractable text on every
  required page, up to 20 MiB; OCR, scanned/image-only and corrupt PDFs are not
  supported.
- Deployment assumes one trusted operator on a private host. Multi-tenant
  isolation, internet hardening and enterprise RBAC are not claimed.
- Workbench uses SQLite with a single durable worker deployment contract.
- The real provider implementation seam is present, but live-provider latency,
  cost, token accounting and smoke behavior have not been qualified.
- Real Production Apply remains an external privileged operator action requiring
  separate authorization. Local models remain deferred.
