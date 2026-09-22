# Phase 4.3 Stage 4D — Qualified overlay contract

Stage 4D is a read-only presentation of frozen HUMAN_USER decisions. The default Industry Explorer remains the Production canonical layer. The optional `Canonical + Qualified` layer adds qualified identities, qualified relations, and visibly separate relation endpoint references. It does not Apply any decision or change Production, the real Workbench, Current Views, or Direct Impact.

## Authority and binding

The builder `scripts/build_phase43_stage4d_overlay.py` verifies the exact Production SHA, Stage 2 HUMAN_USER authorization and candidate packet, Stage 3 population, review population, automated resolution, completed decisions, and final receipt before emitting portable data. It checks all 100 Stage 3 decisions against their frozen parent item and candidate content hashes, exact HUMAN_USER reviewer, and expected 46 identity / 54 relation decisions. Stage 2 endpoint support requires an exact SC-CN ID, HUMAN_USER `CREATE`, and matching native candidate content hashes in the frozen Stage 2 packet. The source manifest records these hashes and the builder and overlay file SHA. The API fails closed when its Production, authority files, overlay file, or canonical overlay SHA differs from the bound value.

Endpoint precedence for each of the 76 occurrences in 38 `CREATE_RELATION` decisions is:

1. An explicit active Production Node ID in the frozen endpoint (`production_canonical`).
2. The later Stage 3 HUMAN_USER identity decision: exact REUSE target or `qualified-stage3:<SC-CN-ID>` (`stage3_human_identity`).
3. An exact Stage 2 HUMAN_USER endpoint-support decision: `qualified-stage2:<SC-CN-ID>` (`stage2_human_identity`).
4. The exact remaining frozen endpoint of a HUMAN_USER-qualified relation: `endpoint-ref:<SC-CN-ID>` (`relation_scoped_reference`).

No name matching or inferred identity resolution is permitted. A conflicting Stage 2/3 DEFER or REJECT, missing/inactive REUSE target, unknown endpoint, ambiguous reference label, or duplicate current Production relation fails the build. The machine-readable [endpoint authority classification](phase43_stage4d_endpoint_authority.json) records each relation ID, endpoint side, candidate ref, authority, decision, visual ID, and source artifact SHA. It has 76 endpoint occurrences, including 29 reference occurrences representing 26 unique frozen candidate refs. The same ref uses one visual anchor across exact relations; this is reference deduplication, never canonical promotion.

## Knowledge states and eligibility

| State | Identity authority | Visual ID | Research selection |
| --- | --- | --- | --- |
| Canonical | Current Production | `canonical:<NODE-ID>` | Existing UnifiedResearchInspector and Stage 4A tree |
| Qualified Stage 3 identity | Stage 3 HUMAN_USER `CREATE_NEW_CANONICAL` | `qualified-stage3:<SC-CN-ID>` | QualifiedResearchInspector; no Production ID or Current View |
| Qualified Stage 2 support identity | Stage 2 HUMAN_USER `CREATE`, only when used by one of the 38 relations | `qualified-stage2:<SC-CN-ID>` | QualifiedResearchInspector; no Production ID or Current View |
| Relation Endpoint Reference | Qualified relation endpoint only; identity not independently qualified | `endpoint-ref:<SC-CN-ID>` | Bounded relation detail only; never Inspector or Focus root |
| Deferred / Rejected | HUMAN_USER governance decision | No graph visual ID | Governance only; research and map ineligible |

Stage 3 `REUSE_CANONICAL` adds provenance to its exact existing canonical target; it creates no second Node. The overlay has 19 REUSE decisions and 19 unique active targets, 12 Stage 3 CREATE identities, 17 Stage 2 endpoint-support identities, 14 deferred identities, and one rejected identity. Stage 2 support is an endpoint slice, not general Stage 2 expansion. Stage 3 authority takes precedence when an ID exists in both decision sets.

An endpoint reference has `identity_qualified=false`, `research_eligible=false`, `canonical_eligible=false`, `search_eligible=false`, `hierarchy_eligible=false`, `current_view_eligible=false`, and `direct_impact_eligible=false`; it is a relation anchor only. It appears in Relationship and Focus maps only when an exact qualified edge needs it. It is excluded from the Stage 4A tree and qualified `part_of` hierarchy. The UI uses a dotted outline and explicit “Endpoint Reference” wording, shows how many visible qualified relations use it, and cannot place it in the `node` or `qualified` URL selection. A path through it is marked `contains_relation_scoped_reference=true` and adds no inferred edge.

## Relation and map rules

All 38 qualified CREATE_RELATION decisions render with exact frozen direction, type, scope and endpoint authority; 17 have full identity authority and 21 use at least one reference. Sixteen DEFER_RELATION decisions create no graph edge. Canonical edges remain distinct. Qualified map nodes expose exactly one applicable identity key (`canonical_node_id`, `qualified_candidate_id`, or `endpoint_reference_id`). Qualified edges expose endpoint authority for both ends and qualification provenance. Solid canonical nodes/edges, dashed qualified identities/edges, and dotted endpoint references are distinguished by line style and text as well as color.

Qualified hierarchy is rooted in the selected Stage 4A canonical navigation tree and adds only qualified `part_of` edges whose identity-qualified endpoints connect to that tree. Qualified objects outside that root are discoverable through search/governance but are not given false domain membership. Relationship and Focus maps may cross domain navigation boundaries through exact qualified relations and mark nodes outside the selected navigation context. Map bounds remain 80 nodes, 160 edges, and Focus depth 1–3. Ordered results and `snapshot_id` are deterministic.

## Inspector, search, URL, and governance

Canonical selection keeps UnifiedResearchInspector, optionally showing Stage 3 REUSE provenance. Qualified identity selection uses QualifiedResearchInspector with HUMAN_USER decision, source population/package SHA, candidate content SHA, decision artifact SHA, frozen evidence, incident qualified relations, and an explicit absent Current View. Qualified edge detail shows relation ID, direction, type, scope, the two endpoint authority classes, Production Applied = No, evidence, and frozen provenance. Reference detail contains only its frozen label/ref/type and relation context; it never offers Current View, Claims, Direct Impact, aliases, or a canonical route.

Canonical search is unchanged in default mode. Overlay search merges canonical results with the 12 Stage 3 CREATE and 17 Stage 2 endpoint-support identities, labels their qualification stage, and deduplicates REUSE into the canonical target. Endpoint references and deferred/rejected records are excluded. Governance lists deferred/rejected identities and relations separately from the 26 endpoint references; deferred/rejected details say they are not research eligible and absent from the semantic graph.

The URL stores `domain`, `map`, `depth`, `overlay`, and exactly one of `node` or `qualified`; Back, Forward, refresh, and deep links restore the selection and matching Inspector. Default `overlay` is canonical. Selecting a canonical Node clears `qualified`, and selecting a qualified identity clears `node`.

## Privacy and mutation boundary

The portable overlay contains an allowlisted, bounded projection of frozen labels, reasons and evidence. It contains no local/private artifact path, provider payload, or new source ingest. The builder creates the overlay and public classification/manifest files only. Runtime endpoints read Production through read-only connections and never call Apply, Workbench mutation, Current View activation, Source ingestion, providers, or cloud jobs. Stage 3 HUMAN_USER decisions and Stage 2 HUMAN_USER authorization are immutable inputs. Stage 5 is outside this contract.
