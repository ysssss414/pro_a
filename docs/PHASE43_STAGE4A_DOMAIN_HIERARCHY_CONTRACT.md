# Phase 4.3 Stage 4A — Domain and Hierarchy Navigation

Stage 4A adds `/industry` to the existing Research Workbench. It is a read-only presentation slice over the Production canonical hierarchy. It does not create a Node, infer an operational domain assignment, extend the ontology, or include un-applied Stage 3 proposals.

## Research Navigation Spec v1

Exactly two tracked JSON files live in `research_navigation/`: `ai_hardware.json` and `semiconductor.json`. Each has exactly these fields:

| Field | Contract |
| --- | --- |
| `contract_version` | Literal `research-navigation-v1` |
| `domain_id` | Filename and tracked Domain Pack ID; only `ai_hardware` or `semiconductor` |
| `display_name` | Safe presentation label, 1–80 characters |
| `root_node_ids` | Nonempty, unique, exact canonical Node IDs; roots must exist and be `active` |
| `hierarchy_relation` | Literal `part_of` |
| `default_max_depth` | Integer 0–8, with roots at depth 0 |
| `domain_pack` | Exact `version` and `sha256` identity from the tracked descriptor |

The SHA256 of each spec is the hash of its exact UTF-8 file bytes. The Domain Pack hash follows the existing `load_pack` identity contract. The projection validates the tracked descriptor and, when `domain_pack_registry` exists, requires an exact registered identity. A descriptor or registration never grants domain qualification, canonical identity, ingestion, or mutation authority. API responses expose lifecycle and registration status separately.

The initial roots are `NODE_20260814_164548FF` (`算力`, AI Hardware navigation) and `NODE_20260814_2CF1006E` (`半导体`, Semiconductor navigation). These are active Production Industry Nodes. AI Hardware's root is deliberately narrow: other AI Hardware concepts without a current canonical `part_of` path under `算力` are not fabricated into the tree. The domain selector is a virtual presentation grouping, not a canonical Node.

## Projection

`ResearchNavigation` reads the canonical DB with SQLite `mode=ro` and `query_only=ON`. It follows only current `part_of` edges from `to_node_id` parent to `from_node_id` child, matching the existing Node children rule. A child is not filtered by operational assignment. Node output is restricted to ID, canonical name, primary type, status, depth, child count, child presence, nested children, and any traversal anomaly. No arbitrary canonical metadata or private file path is returned.

Siblings sort by `canonical_name.casefold()` and then `node_id`. Roots retain spec order. The default depth comes from the spec; requests may set `max_depth` from 0 through 12. At most 1,000 tree entries are emitted. Depth or count truncation is explicit. A cycle, self-loop, or duplicate traversal path appears as a terminal anomaly entry. Structural responses include a deterministic `snapshot_id` hash.

Endpoints under `/api/workbench/v1/research`:

| Endpoint | Result |
| --- | --- |
| `GET /domains` | Sanitized domain labels, spec and pack identities, root summaries, safe counts |
| `GET /domains/{domain_id}/tree` | Bounded canonical hierarchy and truncation metadata |
| `GET /nodes/{node_id}/domain-context` | Navigation paths and separately labelled latest operational Node assignment |

Unknown domains and Nodes fail explicitly. A Node can appear in zero, one, or several navigation contexts without canonical duplication. Operational assignments are read-only supplementary metadata and never decide tree membership.

## UI and URL state

`/industry?domain=ai_hardware&node=<canonical Node ID>` is a two-pane Industry Explorer. Domain and selected Node are URL state, supporting refresh and Back/Forward. With no domain, it selects `ai_hardware`, then `semiconductor` if needed. With no Node, the inspector prompts for a selection. The tree panel supports expansion, selected and ancestor state, loading, empty, error, and truncation messages. Search reuses the existing deterministic Node search; a result outside the selected tree can open in the Inspector without inventing a tree location.

The right pane calls the existing Research Node API and renders the existing `ResearchPage` Node presentation through `ResearchNodeInspector`. Official Current View, Direct Impact, Claims, Sources, Relations, Research Question, Gaps, and Follow-up Notes retain their existing semantics. The classic Explorer and `/node/{id}` Research route remain available. Stage 4B structure map, Stage 4C Inspector redesign, and Stage 4D qualified overlay are excluded.
