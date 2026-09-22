# Phase 4.3 Stage 4B — Semantic Structure Map contract

## Boundary and endpoint

`GET /api/workbench/v1/research/domains/{domain_id}/structure-map` is an authenticated, read-only Research endpoint. It accepts `mode=hierarchy|relationship|focus`, optional `node_id`, and `depth=1|2|3` only for Focus. With no explicit mode it selects Hierarchy when no Node is selected and Relationship when a Node is selected. Relationship and Focus require an active canonical Node. Unknown domains, modes, inactive or missing Nodes, and invalid depth fail closed. The endpoint uses the two unchanged Stage 4A navigation specs; it does not change canonical identity or operational domain assignments.

Every map reads the Production SQLite database using `mode=ro` and `PRAGMA query_only=ON`. Only `status='active'` Nodes connected by `status='current'` Relations are eligible. Relations retain their exact `relation_id`, `from_node_id`, `to_node_id`, `relation_type`, `status`, `scope`, and `confidence`. Path-like scope text is redacted. No private Source location or arbitrary Node metadata is returned. The Stage 3 qualified but unapplied candidates are outside this endpoint.

## Modes and traversal

| Mode | Selection | Projection |
| --- | --- | --- |
| Hierarchy | Optional | Stage 4A bounded navigation tree using current `part_of`, with exact matching canonical Relation IDs. Root-to-selected path is marked; arrow direction remains child → parent. |
| Relationship | Required | All direct current canonical Relations incident to the selected Node, with active endpoints. Default and only depth is one hop. |
| Focus | Required | Breadth-first neighborhood of current canonical Relations in either traversal direction; default depth 2, maximum 3. Distances are from the selected Node. It shows existing edges among reached Nodes and does not infer transitive edges. |

Map output is bounded to **80 Nodes** and **160 Relations**. Candidate Nodes sort by `(distance, canonical_name.casefold(), node_id)`; edges sort by `(minimum endpoint distance, relation_type, from_node_id, to_node_id, relation_id)`. Limits select a deterministic prefix and report `truncated` with `max_nodes` or `max_edges`; Hierarchy also carries Stage 4A tree truncation reasons. Traversal has visited Node tracking, and output has one visual Node per canonical ID and one edge per canonical Relation ID. The response contains safe Node fields (`node_id`, name, type, status, distance, selection, navigation-context flag/depth, selected-path flag), safe Relation fields, counts, available types, limits, reasons, and a SHA256 `snapshot_id` over the complete structural result.

The `in_navigation_context` flag means present in the selected Stage 4A bounded canonical tree. A related Node outside that tree remains visible in Relationship/Focus with a dashed visual border and a truthful label; relation visibility never creates domain membership or operational assignment.

## Presentation-only semantic grouping

| Group | Exact canonical relation types |
| --- | --- |
| Structure | `part_of` |
| Supply / Flow | `upstream_of`, `supplies`, `produces`, `uses`, `applied_in` |
| Dependency / Influence | `depends_on`, `constrains`, `drives`, `benefits_from`, `exposed_to`, `regulated_by`, `validates`, `invalidates` |
| Competition / Substitution | `substitutes`, `competes_with` |
| General Association | `related_to` |

The mapping is explicit in `SEMANTIC_GROUPS`, with SHA256 `95ce62199e1643f25fe771280fd037a923954fdb0aa6179413887b5cca5bcebd`. Unknown canonical relation types fail closed. The filter buttons act only on the client presentation; the API result is unchanged. Every visible edge keeps its canonical relation label and arrow. The legend explains line treatments as well as group names.

## Web behavior

`/industry` keeps the Stage 4A Domain/Hierarchy panel and the existing `ResearchNodeInspector`, adding a central `SemanticStructureMap`. The desktop grid gives approximately 22% to navigation, 47% to the map, and 31% to the Inspector. Each pane is independently bounded; the tree and Inspector scroll independently. Cytoscape uses deterministic preset positions: Hierarchy top-down, Relationship with a selected center and direct neighbors, Focus in distance-based columns. Fit changes only viewport framing; Reset restores the initial preset. Node and Relation indices provide keyboard-reachable equivalents to canvas interactions. A map Node click selects its exact canonical ID and updates the URL, hierarchy highlight when present, map, and Inspector. An edge click reveals bounded relation details and opens the existing `/relation/{id}` route.

URL state contains `domain`, `node`, optional `map`, and optional Focus `depth`; refresh and browser history restore it. No Node defaults to Hierarchy; selecting a Node without an explicit map mode defaults to Relationship. Domain switching clears the selected Node. The Stage 4A search and outside-tree context message remain available.

## Current data limits

At qualification, Production has 327 Nodes and 174 **current** Relations, all `part_of`. Existing non-current categorical Relations remain visible in the Research Inspector but are not silently mixed into Stage 4B maps. The AI Hardware and Semiconductor navigation trees contain 4 and 5 Nodes respectively. Their sparse structure is displayed as recorded. Domain Pack descriptors remain `PROPOSED` and the local Workbench schema 8 lacks `domain_pack_registry`, as disclosed in Stage 4A. Stage 4C Inspector redesign and Stage 4D qualified overlay are out of scope.
