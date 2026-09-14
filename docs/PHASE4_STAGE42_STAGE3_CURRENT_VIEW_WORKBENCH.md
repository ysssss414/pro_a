# Phase 4.2 Stage 3: Current View Workbench

Stage 3 adds an operator-facing product layer to the existing canonical Current View
domain. It does not replace canonical `current_views`, ordering, structured comparison,
revision identity or frozen quality validation. The browser reads canonical knowledge
through the existing read-only connection, persists drafts in the isolated Workbench
database, and can only prepare an immutable package for a separate operator.

The machine contract is `PHASE4_STAGE42_STAGE3_VIEW_CONTRACT.json`. Its activation
adapter is `phase42-view-v1` and its separately privileged entry point is
`phase42-view-operator-v1`. This is a new, narrow capability because Stage 2
`phase42-operational-v1` excludes Current View mutation. The Stage 2 adapter and its
sealed attribution sidecar remain unchanged.

## Official, prior, baseline and draft states

The authoritative official selection is the existing `CURRENT_VIEW_ORDER`:
`revision_date DESC, revision_seq DESC, view_id DESC`, restricted to
`status='official'`. Timestamp alone is not used. The predecessor is resolved from the
selected View's exact `previous_view_id`; an adjacent history row or a newer baseline
cannot replace it. Baseline/projection rows remain separately labelled and excluded
from official history.

The Workbench displays the selected official View, its version, change level,
activation date, predecessor, structured logic and recorded change reason. It also
shows immutable official history, the exact existing structured comparison with the
predecessor, uncertainty fields, evidence roles and business-date freshness. Missing
dates remain `unknown`; ingestion time is never substituted. A missing historical
citation stays visible as `EVIDENCE_NOT_FOUND`.

Drafts are separate server-side objects. They bind the Node, exact official baseline
or `NO_EXISTING_VIEW`, evidence basis, reviewer, reason and a monotonically increasing
revision. Save and validation events are append-only and operation IDs are idempotent.
If the official View or any Claim/role/Source-hash evidence basis changes, the draft is
`STALE`; there is no implicit rebase. The UI always labels official, draft, prior and
baseline state independently.

Evidence cards expose the Claim statement and identity, Claim–Node role, evidence
excerpt and locator, Claim status, Source identity, Source rank and freshness basis.
They link to the existing Claim list and Source detail. Only canonical `subject` links
are primary eligible. `context` remains context-only and `related` remains supporting
only. Qualification verifies the complete primary/context evidence basis again.

## Bounded maintenance and validation

Updates require an existing exact official baseline and produce an immutable new
revision with that View as predecessor. Initial Views require `NO_EXISTING_VIEW`, an
active `Company` or `Product`, eligible primary evidence and the same frozen Current
View content validator used by the canonical domain. Other Node types are read-only in
this stage. If an official View appears before initial activation, execution stops with
`INITIAL_VIEW_RACE` or `BASELINE_STALE`; the package is never converted to an update.

The structured draft retains one-line conclusion, logic, facts, disagreements,
assumptions, investment implication, risks, gaps, watch items, recent change,
evidence IDs and type-specific content. Validation checks exact Node/baseline identity,
required content, citations, evidence existence and primary-role eligibility. Exact
deterministic equality with the official View returns `NO_EFFECTIVE_CHANGE` and cannot
create a revision.

Run the explicit Workbench schema 3→4 preparation only while Workbench writers are
stopped:

```text
python -m pro_a.workbench --config workspace/demo/workbench.toml prepare-current-view
```

Preparation flushes a `.stage2-backup`, verifies that all Stage 1 sealed BLOBs and
Stage 2 attribution/package/receipt rows are byte-for-byte preserved, then adds
append-only View draft, event, activation-package and receipt tables. Startup never
migrates the Workbench or knowledge database. Stage 1 and Stage 2 services accept
schema 4 without changing their semantics.

The bounded HTTP contracts are:

```text
GET  /api/workbench/v1/current-views/{node_id}
PUT  /api/workbench/v1/current-views/{node_id}/draft
POST /api/workbench/v1/current-views/{node_id}/validate
POST /api/workbench/v1/current-views/{node_id}/qualify
POST /api/workbench/v1/current-views/{node_id}/reconcile
```

They use the existing authenticated session, origin/host/CSRF controls and generic
Explorer GET application. There is no activate or Apply route. Qualification returns
a package ID, safe exact predicted diff and `EXTERNAL_OPERATOR_REQUIRED`; it does not
return writer credentials or call the operator.

## External View operator

The operator configuration binds the same Workbench configuration and an isolated
ledger outside Workbench state and artifacts:

```toml
[view_operator]
workbench_config = "workbench.toml"
ledger = "view-operator/ledger.sqlite3"
```

Use only a disposable canonical target for Stage 3 qualification:

```text
python -m pro_a.view_operator --config workspace/demo/view-operator.toml init
python -m pro_a.view_operator --config workspace/demo/view-operator.toml inspect --package VIEWPACKAGE_ID
python -m pro_a.view_operator --config workspace/demo/view-operator.toml register --package VIEWPACKAGE_ID --confirm VIEWPACKAGE_ID
python -m pro_a.view_operator --config workspace/demo/view-operator.toml execute --package VIEWPACKAGE_ID --confirm VIEWPACKAGE_ID
python -m pro_a.view_operator --config workspace/demo/view-operator.toml reconcile --package VIEWPACKAGE_ID
```

The operator accepts only a registered package ID and exact full-ID confirmation. It
revalidates adapter/contract/runtime versions, target file identity, the complete
canonical baseline, Node and predecessor state, draft revision, frozen quality result,
evidence roles and Source hashes, and the exact predicted post-state. HTTP request
context rejects the privileged module before any writable connection, and the HTTP
application never imports or spawns it.

Execution attaches the pinned disposable target and ledger in one `BEGIN IMMEDIATE`
transaction with DELETE journal mode and synchronous FULL. The SQLite authorizer
permits exactly one `INSERT` into canonical `current_views`; UPDATE, DELETE, schema
mutation, triggers and every other canonical table are denied. Foreign keys, complete
post-state and the hash of all unrelated tables must match the package before the
consumed grant and immutable receipt commit atomically.

Precommit failure rolls back the View and leaves the grant reusable with an auditable
failure event. An uncertain or postcommit export failure returns `RECOVERY_REQUIRED`;
reconciliation verifies the consumed ledger receipt and canonical post-state before
exporting/registering the same receipt. A consumed package cannot run twice. The web
can verify only a receipt already registered by the operator and then reload the new
official View.

Acceptance uses deterministic synthetic Company update, Company initial and Product
initial fixtures. It includes ambiguous ordering, exact predecessor, baseline
exclusion, broken citation, stale/race, no-change, unsupported type, evidence-role,
package forgery, HTTP guard, rollback/recovery, concurrency, browser and Explorer GET
cases. Live cloud/local models and real Production activation are outside Stage 3.
