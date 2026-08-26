# Phase 2.3B Knowledge Coverage Audit

- Audit date: **2026-08-26**
- Scope: read-only Knowledge coverage audit of the canonical Production database
- Database: `workspace/pro_a.db`
- Production pre-SHA-256: `8a4247b9da2c3d6f288f8a8af8519f33673bc45b5a4327a57c50436d39dd50b4`
- Production post-SHA-256: `8a4247b9da2c3d6f288f8a8af8519f33673bc45b5a4327a57c50436d39dd50b4`
- `PRODUCTION_DB_CHANGED = false`

## Executive summary

The canonical Node universe is structurally populated but the research evidence layer is not yet activated. Production has 293 active Nodes and 737 aliases, but only 3 Nodes have a direct Source link, no Node has a Claim link, and there are no Current Views, Research Questions, or Knowledge Gaps. The current graph contains 181 stored Relations, of which 174 are current `part_of` Relations and none is a current functional Relation.

The largest bottleneck is the missing Claim → Node activation layer. All 12 Claims are attached to one Source with a broad three-Node direct Source context, yet all 12 have zero `claim_node_links`. Five Claims contain an exact canonical and alias mention of the same `MLCC` Node, but that Node is not one of the Source's three direct linked Nodes. Under the frozen exact-identity and human-review contract this is an ambiguous review signal, not a safe automatic link.

`CLAIM_NODE_ACTIVATION_READY = NO`. The next action is one human review package for the 12 unlinked Claims: adjudicate each Claim's Node scope, retain the evidence excerpt, and only then use the existing controlled Claim → Node maintenance path. No link was inferred or written by this audit.

Secondary recommendations are to improve direct Source-link evidence excerpts/validation and to defer Current View / RQ / Gap creation until Claim-to-Node adjudication is complete.

## Audit method and safety boundary

`src/pro_a/coverage.py` opens SQLite through the existing `ReadOnlyQuery` boundary (`mode=ro` plus `PRAGMA query_only=ON`). The module reads current production rows, emits deterministic CSVs, and never calls `Database.connect()`, `init_schema()`, ingestion, Proposal acceptance, or an LLM. Canonical and alias matching is exact only; ASCII tokens use alphanumeric boundaries, so a short token such as `AI` cannot match `RAIL`. Non-ASCII names use literal exact substring matching. No fuzzy matching, document-level co-occurrence, or auto-linking is performed.

`part_of` direction follows the frozen semantics: child/from → parent/to. Accordingly, `parent_count` and `part_of_out_count` count outgoing `part_of` edges; `child_count` and `part_of_in_count` count incoming edges.

## Node universe and structure

| Metric | Count | % of active Nodes |
|---|---:|---:|
| Total Nodes | 293 | 100.0% |
| Active Nodes | 293 | 100.0% |
| Inactive Nodes | 0 | 0.0% |
| Nodes with aliases | 273 | 93.2% |
| Nodes without aliases | 20 | 6.8% |
| Nodes with any current Relation | 203 | 69.3% |
| Completely isolated Nodes | 89 | 30.4% |
| Roots with no parent | 119 | 40.6% |
| Leaves with no child | 252 | 86.0% |

There are 737 aliases, 181 stored Node Relations, 174 current Relations, and 7 non-current Relations. All 174 current Relations are `part_of`; current functional Relation count is 0. The current hierarchy has maximum depth 3 and no detected cycle.

### Mutually exclusive knowledge level

The highest achieved level is assigned once per active Node:

| Level | Count | % |
|---|---:|---:|
| `LEVEL_4_RESEARCH_ACTIVE` | 0 | 0.0% |
| `LEVEL_3_CANONICAL_VIEW` | 0 | 0.0% |
| `LEVEL_2_EVIDENCE_CONNECTED` | 0 | 0.0% |
| `LEVEL_1_SOURCE_CONNECTED` | 3 | 1.0% |
| `LEVEL_0_STRUCTURE_ONLY` | 290 | 99.0% |

`LEVEL_0` includes Nodes that have only aliases/hierarchy and Nodes that are completely isolated. The latter are separately reported above.

## Per-Node coverage

| Coverage surface | Nodes covered | % of active Nodes |
|---|---:|---:|
| Direct Source | 3 | 1.0% |
| Claim | 0 | 0.0% |
| Current View | 0 | 0.0% |
| Research Question | 0 | 0.0% |
| Knowledge Gap | 0 | 0.0% |
| Current functional Relation | 0 | 0.0% |

The machine-readable `node_coverage.csv` contains the required per-Node counts for aliases, parents, children, direct Sources, Claims, Current Views, RQs, Gaps, `part_of` direction and functional Relations. Type coverage is also included in the audit summary: Application 2, Entity 14, Equipment 23, Event 1, Industry 8, Material 37, Product 121, Segment 37, Standard 5, Technology 43, Theme 2. Only Industry, Segment and Theme currently have one Source-linked Node each; all other types have zero direct Source coverage.

## Source coverage

| Source | Direct Node links | Claims | Claim-linked Claims | Unlinked Claims |
|---|---:|---:|---:|---:|
| `SRC_20260813_87A71E82` | 0 | 0 | 0 | 0 |
| `SRC_20260814_F6E1EFAD` | 3 | 12 | 0 | 12 |

All 12 Claims have an existing Source, and all 12 inherit a three-Node direct Source context. None of the 3 `source_node_links` has a non-empty evidence excerpt or validation JSON. This broad, unaudited Source context is not sufficient to activate Claim links.

## Claim coverage and deterministic review signals

- Claims: **12**.
- Claims with an evidence pointer: **12/12**.
- Claims with an evidence excerpt: **12/12**.
- Claim → Node links: **0**.
- Relation evidence links: **0**.
- Current View trigger references: **0**; RQ references: **0**; Gap references: **0**.
- Unlinked Claims: **12/12**.

Claim-level deterministic labels and buckets are:

| Signal / bucket | Claims |
|---|---:|
| `SOURCE_HAS_MULTIPLE_NODES` | 12 |
| `EXACT_CANONICAL_MENTION` | 5 |
| `EXACT_ALIAS_MENTION` | 5 |
| `MULTIPLE_EXACT_NODE_MENTIONS` | 0 |
| `SOURCE_HAS_SINGLE_NODE` | 0 |
| `SOURCE_HAS_NO_NODE` | 0 |
| `NO_DETERMINISTIC_NODE_SIGNAL` | 0 |
| `HIGH_SIGNAL_REVIEW_CANDIDATE` | 0 |
| `AMBIGUOUS_REVIEW_CANDIDATE` | 12 |
| `NO_SAFE_SIGNAL` | 0 |

The 5 canonical and 5 alias counts refer to Claim rows, not link writes; they are the same five Claims mentioning `MLCC` in canonical/alias form. The exact matches do not agree with the Source's three direct Nodes, so they remain ambiguous. No Claim contains multiple exact Node mentions in this Production snapshot. `unlinked_claims.csv` preserves every unlinked Claim's Source metadata, statement, evidence pointer/excerpt, nature, status, confidence, direct Source-linked Node IDs and canonical names, exact-match signals and review bucket.

## Reachability and relation evidence

The Source → Claim layer is complete for the 12 stored Claims, and the Source → direct Node context is present for all 12. The Claim → Node layer is empty, so no Claim reaches a Node through an explicit Claim link. There are no orphan Current View, Research Question or Knowledge Gap rows. Because every current Relation is structural `part_of`, current functional evidence support/contradiction counts are both zero; the 7 non-current stored Relations are excluded from the current graph coverage.

## Activation decision

`CLAIM_NODE_ACTIVATION_READY = NO`.

The decision is based on the frozen rules: evidence text and exact identity signals can nominate human review, but a broad Source context or an exact mention cannot silently create a Claim → Node link. Production has zero explicit Claim → Node links and zero high-signal candidates where a single Source Node and exact Claim mention agree. The correct next step is a review package, not automatic activation.

## Outputs

- Audit implementation: `src/pro_a/coverage.py`
- Deterministic tests: `tests/test_coverage.py`
- Machine-readable outputs: `artifacts/phase2_3b/node_coverage.csv`, `artifacts/phase2_3b/source_coverage.csv`, `artifacts/phase2_3b/claim_coverage.csv`, `artifacts/phase2_3b/unlinked_claims.csv`

The four CSVs are generated in stable order and contain no archived filesystem paths or raw document payloads.

## Verification

- Phase 2.3B deterministic tests: **4 passed**.
- Full repository pytest under the host's local temporary-directory runner: **323 passed; 2 unrelated pre-existing failures** in the Phase 1.1 unknown-node offline replay test (`test_unknown_node_only_does_not_fail_source_or_create_downstream_objects`). No coverage test failed.
- `compileall` for `src` and `tests`: **pass**.
- `git diff --check`: **pass** for tracked edits.
- Production `PRAGMA integrity_check`: **ok**; `PRAGMA foreign_key_check`: **0** rows.
