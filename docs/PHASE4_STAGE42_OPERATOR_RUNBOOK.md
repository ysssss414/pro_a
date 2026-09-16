# Phase 4.2 private-host operator runbook

This runbook covers the Phase 4.2 Workbench release candidate. It assumes one
trusted operator on a private host. Authentication, Origin checks, CSRF checks and
registered-artifact access are enforced, but this is not an internet-facing,
multi-tenant or enterprise-RBAC deployment.

## Supported environment and path preflight

Use Python 3.10 or newer, Node.js 22 LTS with npm, SQLite on a local filesystem,
and a short local workspace path. On Windows, keep the workspace root at or below
96 characters and the configured artifact root at or below 127 characters; avoid
reparse points, symlinks and hard links in configured
storage. Before initialization or startup, run:

```powershell
python -m pro_a.workbench --config .\workbench.toml preflight
```

The preflight reserves 112 characters for generated artifact descendants and
fails when the estimated path exceeds the conservative 240-character legacy
Windows limit. Move the installation and its private stores to a shorter root,
update `workbench.toml`, and rerun the command if it fails. Do not shorten or edit
registered artifact paths inside the database.

## Installation

From a clean checkout:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
Set-Location .\frontend
npm ci
npm run build
Set-Location ..
```

Runtime installation may omit `[dev]`. Provider credentials are not needed to
install, initialize, start, browse existing research, or run deterministic DEMO
acceptance. Keep `.venv`, `frontend/node_modules`, `frontend/dist`,
`workbench.toml`, and every private store untracked.

Copy `workbench.example.toml` to an ignored operator-owned path. Configure three
separate locations: an existing canonical knowledge database, a Workbench state
database, and a private artifact root. The service must have read access to the
canonical database and write access only to Workbench state and artifacts. The
web process and worker must not have canonical Production write permission.

## Schema preparation

The canonical knowledge schema is `0.2.3`. Workbench schema `8` is separate.
Startup never creates or migrates either database. For a new Workbench, initialize
schema 1 and perform every explicit, stopped-writer migration in order:

```powershell
python -m pro_a.workbench --config .\workbench.toml init
python -m pro_a.workbench --config .\workbench.toml prepare-review
python -m pro_a.workbench --config .\workbench.toml prepare-attribution
python -m pro_a.workbench --config .\workbench.toml prepare-current-view
python -m pro_a.workbench --config .\workbench.toml prepare-impact
python -m pro_a.workbench --config .\workbench.toml prepare-research
python -m pro_a.workbench --config .\workbench.toml prepare-cloud-jobs
python -m pro_a.workbench --config .\workbench.toml prepare-source-operations
```

Each migration accepts only its immediate predecessor and creates an exact
database backup before changing schema. Existing schema 8 installations require
no startup migration. Back up the coordinated state before an upgrade; never use
the legacy `schema.sql` as a Workbench or canonical `0.2.3` bootstrap substitute.

## Startup and shutdown

Set a high-entropy session token in the environment named by
`session_token_env`. The value is never placed in configuration or backup
manifests. Start the backend on loopback:

```powershell
$env:PRO_A_WORKBENCH_TOKEN = Read-Host -MaskInput
python -m pro_a.workbench --config .\workbench.toml serve --phase4-config .\config.toml
```

Start the already-built frontend with the deployment's private static-file
server, or use `npm run dev` from `frontend` for a loopback operator session. The
configured browser Origin must match exactly. Direct fresh-session routes for
Node, Claim, Source, Current View and processing detail remain authenticated.

The durable job service is the only provider execution seam. DEMO acceptance can
run `run-fake-cloud-job` and `run-fake-source-operation`; those commands reject
PRIVATE mode. A live deployment must inject the existing real adapter into the
worker under a separate, operator-owned process. The real Source-analysis and
semantic-decomposition adapters have each passed one bounded live-provider call
through the durable job path. This establishes integration readiness only; live
latency/cost SLOs and full live Golden Path quality remain unqualified.

For shutdown, stop new uploads, wait until no Source run or cloud job is queued or
running, stop the worker, then stop the backend. A `RECOVERY_REQUIRED` item is a
durable manual state and does not block a drained backup.

## Provider configuration

The currently qualified live configuration resolves `provider=deepseek` from
`https://api.deepseek.com` and requests `model=deepseek-flash`. Operator-owned
worker profiles must bind those exact identities; no model fallback is qualified.
Credentials belong only in the provider backend's
environment or secret store; do not put them in TOML, logs, job payloads or backup
archives. `cloud-inference-v1` binds the request, accepted model aliases,
`semantic-backend-adapter-v1` or `source-analysis-piece-adapter-v1`, timeout,
call/token budgets, retry owner, prompt hash
and runtime identity before dispatch. The job system owns bounded retries; the
HTTP service and provider SDK must not add independent retries. Without provider
identity or credentials, research and existing Workbench pages remain available,
while cloud submission/execution fails closed or stays unavailable.

## Source Golden Path

The supported upload contract is a private, valid, non-encrypted clean PDF of at
most 20 MiB with extractable text on every required page. OCR, scanned or
image-only PDFs, encrypted PDFs and corrupt PDFs are unsupported. Upload through
the authenticated Source screen, follow processing, complete the native human
review, seal explicit attribution, inspect shadow qualification and predicted
diff, and then use the separate disposable operator activation flow when needed.

The browser has no Production Apply route. Real Production activation remains a
privileged external operator action that requires a separate exact authorization,
baseline, backup, single transaction and receipt. The web process and durable
worker cannot perform it.

## HUMAN_REVIEW_REQUIRED and RECOVERY_REQUIRED

`HUMAN_REVIEW_REQUIRED` is the successful stop before a human decision. Review
every item, preserve the immutable packet binding, seal the review, complete
explicit Claim-to-Node attribution, and inspect qualification before any external
operator action.

`RECOVERY_REQUIRED` means a provider call may have occurred without a provable
durable outcome. Do not retry or resubmit. Stop the worker, preserve the database
and artifact root, inspect the job attempt/events and provider request identity,
reconcile a durable result only when exact evidence exists, and leave the item
manual otherwise. Proven pre-dispatch loss may be requeued by the existing
reconciler; an unknown external outcome may not.

## Coordinated backup

Backups cover the Workbench SQLite database plus the complete private artifact
root, including uploaded Sources, registered native packets, result artifacts and
lineage. Review, attribution, View draft, attention, follow-up note and job states
are in SQLite. The manifest contains hashes and portable configuration metadata,
never secrets or absolute paths.

Drain and stop the HTTP service and workers, then run:

```powershell
python -m pro_a.workbench --config .\workbench.toml backup --output <backup-root>\phase42-backup
```

The command rejects queued/running work, takes an exclusive SQLite writer lock,
copies state and artifacts, validates integrity, hashes every file, and creates
the destination only when complete. It also checks the temporary backup path plus
the longest stored artifact against the 240-character Windows limit before copy;
choose a shorter backup root if it reports `PATH_LENGTH_UNSAFE`. Store the
resulting private directory with operator-controlled access.

## Restore drill and recovery

Restore requires a new empty state path and artifact root plus an existing,
compatible canonical `0.2.3` database. The canonical file may be a disposable
read-only copy for a drill. Create a new ignored `workbench.toml` with those paths,
then run:

```powershell
python -m pro_a.workbench --config .\restore\workbench.toml restore --backup <backup-root>\phase42-backup
python -m pro_a.workbench --config .\restore\workbench.toml preflight
python -m pro_a.workbench --config .\restore\workbench.toml serve --phase4-config .\restore\config.toml
```

Restore verifies all hashes, rejects non-empty destinations, rebinds the copied
Workbench metadata to the new canonical and artifact paths, and validates SQLite
integrity and foreign keys. It never writes the canonical database. After startup,
verify uploaded Source resolution, registered packet and lineage, sealed review,
attribution, job/events, Current View and Direct Impact pages, and follow-up notes.
Keep the original backup until this inspection passes.
