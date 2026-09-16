# Phase 4.2 Stage 4 direct-impact contract

Stage 4 projects only paths backed by canonical rows: Source→Claim, Claim→explicit
`claim_node_links`, Node→latest official View, Claim→latest official View citation,
recorded Claim contradiction/update relations, and recorded relation evidence. A
categorical or historical relation may be shown for provenance, but is marked as
non-current. Dates and ingestion order never create a relationship.

The projection uses one read transaction for all knowledge rows and one read
transaction for Workbench drafts/state. Results are not cached. The snapshot ID is
the SHA-256 of the exact canonical and staged rows used by the projection, so a new
official View, changed explicit attribution, Claim relation, relation status, or
staged draft deterministically changes the ID.

Human outcomes reuse the existing `NO_CHANGE`, `MINOR`, `MATERIAL`, and `THESIS`
vocabulary. They are actor-recorded attention outcomes in the Workbench database;
they are not canonical facts, scores, recommendations, or authorization to change
a Current View.

## Performance gate declared before qualification

On the retained synthetic fixture of at least 100 Sources, 500 Claims, 300 explicit
Claim→Node links, and 20 official Views:

- Impact list (50 Sources): p95 ≤ 250 ms and at most 9 semantic SQL statements.
- Impact item detail: p95 ≤ 100 ms and at most 9 semantic SQL statements.
- reverse Claim→View: p95 ≤ 100 ms and at most 10 semantic SQL statements.
- Source→Claim→Node→View: p95 ≤ 100 ms and at most 9 semantic SQL statements.

Each benchmark uses at least 30 measured iterations after warm-up. These local
interactive thresholds leave ample UI budget while preventing N+1 query growth.
