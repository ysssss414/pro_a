# Phase 4.2 Stage 4: Changes & Impact

Stage 4 adds a synchronous read projection that routes recorded Source changes to
directly affected Claims, explicitly attributed Nodes, latest official Current
Views, staged View drafts, recorded Claim contradictions/updates, and recorded
relation evidence. Every item includes its exact path, relationship vocabulary,
attribution role, evidence references, status/temporal metadata, and snapshot ID.

The projection never follows a generic graph edge. It does not match names, aliases,
paragraphs, industries, parents, or co-occurrence. It does not calculate relevance,
materiality, financial effects, sentiment, or investment conclusions. Inactive Nodes
and categorical/historical relations are visible only as labelled provenance and are
not current Impact targets. Missing dates remain `unknown`; `updates` and
`contradicts` are displayed only when the corresponding canonical Claim relation is
present.

## Snapshot and storage boundary

All knowledge rows for a response are read inside one SQLite read transaction with
`query_only=ON`. Workbench drafts and attention rows use a separate Workbench read
transaction. No Impact result cache is stored. The response hashes the exact
knowledge and staged rows, while each item carries a stable per-Source snapshot ID
for optimistic attention-state writes. A changed official View or staged evidence
dependency therefore makes an earlier human outcome `STALE`.

Schema 5 adds only `impact_attention_states` and append-only
`impact_attention_events` to the isolated Workbench database. The existing human
outcomes `NO_CHANGE`, `MINOR`, `MATERIAL`, and `THESIS` are retained as operator
attention outcomes. They do not authorize or change Production knowledge.

Prepare the Workbench schema explicitly while Workbench writers are stopped:

```console
python -m pro_a.workbench --config workspace/demo/workbench.toml prepare-impact
```

The migration requires schema 4, writes a byte-exact `.stage3-backup`, and is
idempotent. Earlier review, attribution, and Current View services accept schema 5
without changing their contracts.

## API

Authenticated, no-store Workbench routes are:

```text
GET /api/workbench/v1/impact/changes
GET /api/workbench/v1/impact/item/{impact_id}
PUT /api/workbench/v1/impact/item/{impact_id}/attention
GET /api/workbench/v1/sources/{source_id}/impact
GET /api/workbench/v1/claims/{claim_id}/impact
GET /api/workbench/v1/nodes/{node_id}/impact
GET /api/workbench/v1/views/{view_id}/evidence-impact
```

The only mutation records Workbench attention state with CSRF, exact snapshot,
revision, operation identity, reviewer, and reason checks. There is no web endpoint
for Production Apply, View activation, automatic draft creation, or canonical
Impact persistence.

The browser surface is `?surface=impact`. It separates Changes, Directly Affected,
Official Views, Staged View Work, Evidence Paths, Contradictions / Temporal, and
Attention State. Claim IDs remain visible in the path; Stage 4 retains the existing
limitation that Explorer has no stable single-Claim URL.

The performance thresholds and their pre-measurement rationale are frozen in
`docs/phase42_stage4_direct_impact_contract.md`.
