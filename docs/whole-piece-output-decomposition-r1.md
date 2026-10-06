# SOURCE_ANALYSIS_WHOLE_PIECE_OUTPUT_DECOMPOSITION_R1

Baseline: `9562404e2b85d16394219825b8b254705026a31b` (PR #103).
Qualification in progress; this document is not a release authorization.

## Gate A: storage and semantic boundary

Schema12 stores immutable Series/Segment identities, version strings, ordered
assigned Evidence refs, parent/path/range lineage, budgets, attempt request
hashes, dispatch intents, private raw artifacts, accepted results and coverage.
Its SQL constraints do not assign a semantic-context meaning to Segment ranges.
An output Series can therefore truthfully use these structures with a new
Series, batch, policy, coverage and subdivision identity. No schema migration or
second provider-call ledger is introduced. Historical bounded identities remain
accepted with their original parsing and aggregation policy.

`EVIDENCE_SEGMENT_SEMANTIC_BOUNDARY = deprecated`. A batch range denotes
`OUTPUT_OWNERSHIP_BOUNDARY`, never `SEMANTIC_CONTEXT_BOUNDARY`. Rendering inserts
tags only around owned units in the original complete SourcePiece. Removing
those tags reconstructs its exact text, including structural markers and gaps.
Non-owned text remains present without its Evidence identifiers or a mapping.

The real frozen Source has 77/93/83/82/52 Evidence units. Its offline initial
plan is 5/6/6/6/4 batches: 27 possible physical calls, five logical extraction
jobs. Every offline request reconstructs the complete SourcePiece exactly and
contains zero foreign Evidence IDs. This proves rendering/assignment, not live
output capacity. Run #10 proves only that a single 12000-token response is
unsafe; no tokenizer conversion or future per-batch fit is inferred.

The existing policy is retained: 16 refs initially, 16 terminal leaves, depth
4, 32 calls and 384000 cumulative output-token liability per Series. With R
roots and L leaves, a binary subdivision forest has 2L-R nodes, at most 31.
The current initial plans fit the policy. Severe density may exhaust the leaf
or depth limit and must fail closed; the policy does not promise that every
Evidence unit can always be isolated. A one-ref truncation also fails closed.

## Contract and aggregation

Batch ProviderRecord keeps the qualified lexical values and adds dispositions
and candidate/source-reference ownership anchors. Anchors allocate responsibility;
they are stripped before Wire conversion and never enter canonical research
Evidence or permanent identity. Every active Evidence selection, including a
preserved Event field, is bound locally and checked against the assigned refs.

Each assigned ref has exactly one CLAIMED or NO_INDEPENDENT_CLAIM disposition.
This proves explicit consideration, not mathematical extraction completeness.
Candidates named by Claims must appear in the same batch. Relations refer only
to that batch's C1..Cn; aggregation remaps those refs by the Claim offset.
There is no cross-batch relation synthesis. Candidate duplicates must have
equal semantics; conflicting values fail. Source metadata must match exactly
across accepted leaves. Wire v3, Evidence Binding v2 and Analyzer remain the
authoritative canonical gates.

## Durability

Requests freeze before reservation/dispatch. Exact unparsed function arguments
are stored privately before response parsing and local validation. Only a
durable length outcome permits ownership subdivision. The parent outcome stays
immutable and its cost remains counted; both children read the complete source.
Malformed non-length output fails. Unknown external outcome blocks the Series
without recall or subdivision. A batch has one permitted attempt.

Physical provider calls, accepted leaves, truncated parents, subdivision and
input/cache/output usage are exposed separately from logical jobs. The Stage1
31-job limit counts SourcePiece Series plus Semantic jobs.
Reservations are reported separately from dispatched calls. Dispatched calls
without a known durable outcome remain explicit unknown-outcome liabilities;
the confirmed-call count excludes them. MCP exposes counts and usage only.

## Release boundary

Offline/synthetic qualification only. Stable/schema12 and Runs #1–#10 remain
unchanged. No provider calls, Run #11, Review action, Production or Current View
writes are authorized in this phase. Gate results, exact test counts, wheel
identity and evidence hashes will be recorded after qualification.
