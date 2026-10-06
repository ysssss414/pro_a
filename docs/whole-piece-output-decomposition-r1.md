# SOURCE_ANALYSIS_WHOLE_PIECE_OUTPUT_DECOMPOSITION_R1

Baseline: `9562404e2b85d16394219825b8b254705026a31b` (PR #103).
Gates A–E PASS. Offline implementation qualification only; no release or live-run authorization.

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
writes are authorized in this phase. The companion qualification JSON records the exact tests, build, contracts,
offline request sizes, benchmarks and safety hashes.

## Qualification receipt

Implementation: `4c1d8cb6ccd239b06502c05f882b32b1bd74d322`. Wheel SHA256: `6c4e1fcb14a814197edd3bceadd642b27f8660aff28c62f99ab738828ef79b68`.

1369 unique scoped tests passed across 31 files, zero outstanding failures/skips. This is not a full repository run.

Compileall, pip check, isolated PEP517 wheel, 142-file source/wheel/install byte equality, installed repository identity, no-Git runtime, privacy scan and diff check passed.

| Piece | Evidence | Initial owned-ref counts | Full context chars | Prompt chars | Prompt UTF-8 bytes |
|---|---:|---|---:|---|---|
| 1 | 77 | 16/16/16/16/13 | 3595 | 14654–14852 | 27944–28142 |
| 2 | 93 | 16/16/16/16/16/13 | 3783 | 14755–14953 | 28305–28503 |
| 3 | 83 | 16/16/16/16/16/3 | 3556 | 14067–14925 | 27151–28009 |
| 4 | 82 | 16/16/16/16/16/2 | 3791 | 14828–15752 | 28096–29020 |
| 5 | 52 | 16/16/16/4 | 2098 | 12412–13204 | 23204–23996 |

Every batch has zero selectable foreign Evidence IDs. Exact per-batch request chars/bytes and foreign context counts are in the companion JSON.

| Owned refs | Claims/ref | Argument chars | UTF-8 bytes |
|---:|---:|---:|---:|
| 16 | 1 | 8987 | 9411 |
| 16 | 4 | 28061 | 29733 |
| 8 | 1 | 4614 | 4830 |
| 8 | 4 | 14142 | 14982 |
| 4 | 1 | 2443 | 2555 |
| 4 | 4 | 7207 | 7631 |
| 1 | 1 | 817 | 851 |
| 1 | 4 | 2008 | 2120 |

No token conversion is estimated. Counts prove smaller serialized responsibility for these comparable fixtures only.

Runs #1–#10 and all 22 queued jobs remain unchanged; the original 14 historical queued jobs are included. Runs #8/#9/#10 remain incompatible with the new execution surface. All safety write/call counts refer to the real environment; test fixtures are disposable.

`NEXT_STAGE = OUTPUT_DECOMPOSITION_RELEASE_AND_LIVE_RUN11_VALIDATION`

`AUTHORIZATION_REQUIRED_FOR_LIVE_RUN11 = true`
