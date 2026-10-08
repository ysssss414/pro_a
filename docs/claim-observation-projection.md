# Lossless observations and Native projection qualification

The existing Analyzer merges normalized equal statements. Its output is a Native
projection, not a lossless representation of all accepted observations. This
additive, offline contract preserves the original observations independently and
blocks unresolved projection groups before Semantic admission. It does not
change the Analyzer, permanent Claim IDs, ProviderRecord, Evidence Binding,
historical checkpoints, schema12, or any existing runtime dispatch path.

## Contracts and trusted inputs

`claim-observation-ledger-v1` consumes a complete, verified bounded Series and its
immutable accepted Segment results. It calls existing coverage, Wire and Evidence
validation. Each Observation ID binds the run, Source identity, SourcePiece,
Series, Segment result hash, local ordinal, original Claim payload hash and
Evidence identity. Original results, full Claim payloads, resolved Evidence,
expanded fields and referenced Candidates remain in the private artifact. Equal
Claims retain separate Observation IDs. Serialization round trips preserve the
artifact and its identity.

`native-claim-observation-projection-v1` consumes the actual full Analyzer result
for that SourcePiece. Every `_relation_claim_refs` ordinal must match exactly the
original Observation population. Missing, extra, duplicated or incompatible
references stop with `STOP_PROJECTION_MAPPING_AMBIGUOUS`; no fuzzy correspondence
or model inference is permitted. Atomic splits outside this qualified one-piece
topology also stop. The projection explicitly declares itself nonauthoritative.

The caller must verify accepted result hashes and the frozen Native output's
provenance before constructing artifacts. Content hashes detect drift; they are
not signatures or substitute runtime authorization. No cross-release override is
issued. The qualification uses the existing Analyzer, record builder, quote and
Evidence preparation, and Semantic input builder in a disposable private copy.

## Field comparison and admission

Statement collisions are compared using every expanded Claim field except its
local ordinal and Evidence excerpt/pointer, plus referenced Candidate payloads.
This includes attribution, time, scope, nature, status, novelty, structured
fields, Node/Candidate references, confidence and assumptions. Evidence is
compared by its existing binding identity. Comparison is exact and conservative.

| Classification | Observation treatment | Admission |
| --- | --- | --- |
| Single Observation | Preserve original | Eligible for existing preflight |
| EXACT_DUPLICATE | Preserve every identity and original payload | Eligible for existing preflight |
| SAME_ASSERTION_MULTIPLE_EVIDENCE | Preserve every Evidence variant | BLOCKED_PENDING_REVIEW |
| NON_EQUIVALENT_OBSERVATIONS | Preserve every differing field | BLOCKED_PENDING_REVIEW |
| Insufficient/ambiguous correspondence | Do not invent a mapping | STOP_PROJECTION_MAPPING_AMBIGUOUS |

Unknown/insufficient Evidence cannot become an exact duplicate: existing Evidence
validation rejects it before ledger construction. This version does not turn a
failed binding into an admitted `UNRESOLVED` record. Such records require a future
explicit unresolved-input contract. Successful qualification may have zero
UNRESOLVED groups; different Evidence still blocks without a merge decision.

`observation-semantic-admission-v1` binds existing permanent Claim records using
their deterministic ID formula and `claim_index`, then binds exact Semantic input
payloads. It does not remint Claim IDs or match rewritten statements heuristically.
`guard_semantic_inputs` must succeed before using a selected input set; it checks
identities, complete group bindings, exact payloads, uniqueness and admission.
Changing a status flag cannot authorize a blocked group. Eligibility is only for
existing downstream checks, not Production or Review approval.

`semantic_capacity_preflight` guards the eligible subset and calls the existing
`partition_semantic_claims`, retaining the existing parent, token and Job limits.
Its report includes excluded parents and does not claim the full Run fits when
unopened Segments or unresolved groups remain. Token overflow raises the existing
error; Job overflow is explicitly reported. No Semantic jobs are created.

## Private review and future integration

`private_review_artifact` contains the complete Ledger and Projection, including
every original field and Evidence variant, and no applied decisions. Persist it
using the existing serialized-writer `write_once` mechanism, retain its hash in
the caller's audit record, and verify it on reload. It is a readable private
review object, not a public counter or a second Source database.

Future retain/split/merge/defer decisions require a separate append-only contract
binding the exact group identity, all Observation IDs, reviewer and reason. This
stage implements no decisions and changes no Review or Production state.

The module is deliberately not activated for historical Runs. The next stage must
integrate and identity-bind the guard before any Semantic registration/dispatch,
alongside metadata authority, bounded lossless aggregation and explicit recovery.
Existing runtime checks are not claimed equivalent to that future integration.
Public qualification receipts contain only counts, contract versions and hashes;
raw Claims, Source metadata and private artifact contents must remain local.

## Qualification result

The private first-Series replay preserved 146 of 146 observations and mapped all
of them onto 102 unchanged Native projections. All 34 collision groups were
NON_EQUIVALENT_OBSERVATIONS and individually failed admission. The remaining 68
projections passed the existing record, quote/Evidence and Semantic input path;
the budget predictor produced 9 Semantic batches, or 14 total logical Jobs with
5 Extraction Series. Input budget was 11,808; largest batch upper bound was
10,297. This is an eligible-subset result, not a full-Run capacity guarantee.

Focused and related source regressions passed 267 tests. The historical runtime
surface assertion is reported separately: the unchanged baseline and candidate
both return `EXECUTION_SURFACE_UNAVAILABLE:RetryCompatibilityError` where that
assertion expects `SEMANTIC_SURFACE_CHANGED`. It is not a new passing check and is
not counted as a new regression. Installed/package results belong in the final
qualification receipt.
