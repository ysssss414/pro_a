# Phase 4.3 Stage 4C — Unified Research Inspector contract

Stage 4C starts from PR #67 merge `2cbb5b5616ccaeae7d395655c10297653fe99b4d`. It changes the presentation of the existing Production Node research projection. The left Domain Hierarchy, center Semantic Structure Map, and their `domain`, `node`, `map`, `depth` URL state remain authoritative.

## Data and section order

`UnifiedResearchInspector` is the shared Node presentation for `/industry` and `/node/{id}`. `ResearchNodeInspector` remains its compatibility wrapper. Industry Explorer supplies its already fetched Node Domain Context; the standalone Node page reads the same existing Domain Context endpoint. There is no new backend endpoint, schema, migration, or research meaning.

The default order is Identity; Domains / Navigation Context with separately labeled Operational assignment; Current View; Key Claims; Latest Evidence; Direct Impact and Open Gaps; Research Question; Related Sources; Relations; Research Coverage; Follow-up notes; collapsed Current View details / Workbench. The summary itself has no write action. The existing Workbench loads only when opened. Existing private, noncanonical note editing remains at the bottom. All exact Claim, Source, Relation, and Node routes remain reachable.

`Canonical Production Node` means only that the identity came from the existing Production Node endpoint. Navigation contexts come only from `navigation_contexts`; operational assignments come only from `operational_domain_assignments`. An outside-tree Node remains explicitly labeled. The inspector does not display qualified Stage 3 candidates.

## Deterministic presentation rules

The exact UTF-8 key-Claim rule identifier, without a trailing newline, is:

```text
stage4c-key-claims-v1|tier1=official-trigger-order-if-present-on-node-page|tier2=subject|tier3=context-then-related|fallback=business_date-desc,claim_id-asc|dedupe=claim_id|default=3|bounded-page-only
```

Its SHA256 is `607abc517b1f6bed3be249c83ff7d7b3ab704f3e06989bc785441eb4b4407b54`. Official `trigger_claim_ids` are shown first in their stored order when their exact Claim records are present on the bounded Node Claim page. Remaining explicit subject, then context, then related Claim links use backend `business_date` descending and Claim ID ascending. IDs are deduplicated. Labels distinguish official View evidence from deterministic role fallback. Three are visible initially; Show all reveals only returned records. An unavailable trigger is never reconstructed.

The exact UTF-8 Latest Evidence rule identifier, without a trailing newline, is:

```text
stage4c-latest-evidence-v1|explicit-node-linked-page|business_date-desc,claim_id-asc|default=3|bounded-page-only
```

Its SHA256 is `546ce14269b69af3535fcc459c231e170361a04d3e8a01305d38e0689122b575`. The existing explicit Node Claim page is sorted by its backend `business_date` and stable Claim ID. Three are initially visible, with exact Claim and Source drill-downs. Source rank appears only when a matching Source record is in the existing bounded Node Source list. There is no aggregate evidence score.

Current View displays the recorded `content_json.one_line_conclusion`, at most three recorded `core_logic`/`key_facts` items, and recorded `recent_change`, plus version/change/date metadata. It does not parse prose or generate a thesis. Direct Impact uses recorded path rows in their backend order, three initially; paths retain reason, official/staged state, relation types, and exact steps. Open Gaps contains only `open`, `reopened`, and `needs_refresh` rows, preserving backend order, three initially; resolved rows are available under Show all gaps. Related Sources preserve backend order, five initially. Relations preserve all exact statuses, summarize counts and types from returned rows, and show three initially. Research Coverage uses the existing knowledge level and counts; it is not an investment-quality rating.

## Bounded projection and empty states

The Node projection currently returns at most 20 Claims and 20 Sources. `claims.total` is the full explicit Claim count, so the Inspector reports when its selection is only from the returned page and offers the existing filtered Claim index. The existing backend computes `coverage.sources` from its bounded Source-ID list, so a full 20-Source return cannot establish that the list is complete. The Inspector then says `at least 20 (bounded)` and `20+ Sources`. Source organization is displayed only if present in the Node projection; currently it is not part of that Source row. No backend change was made for this presentation stage.

Empty cards remain visible and say exactly what is missing: no navigation context, official View, explicit Claims, recent Evidence, recorded Impact, open Gaps, Research Question, linked Sources, or recorded Relations. A new Node selection immediately hides the previous Node summary while the existing read requests complete. Loading and error states are announced.

## Authority boundary

The summary reads Production and Workbench projections only. It cannot activate, publish, promote, or apply anything. Existing Current View Workbench maintenance remains behind explicit expansion and retains its prior Workbench-only draft, validation, qualification, and receipt behavior. Existing notes remain private and noncanonical. Stage 4C does not start Stage 4D or expose qualified overlay data.
