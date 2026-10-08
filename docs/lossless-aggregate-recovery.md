# Lossless Aggregate recovery (offline qualification)

This target-only path preserves accepted Segment outputs across a source metadata
conflict. It is an explicit execution-contract change, not a claim of semantic
equivalence with the historical runtime. Schema remains 12. The historical
Analyzer, Wire validation, ProviderRecord v4, extraction policy and Semantic
budgets are unchanged.

## Authority and retention

`source-metadata-authority-resolution-v1` binds the Source identity, all frozen
SourcePieces and Series, original accepted result SHAs, every field's evidence,
and the explicit operator decision. Title, publication time, author, organization,
rank and origin require that decision. Verified documentary evidence creates
candidates; repeated model values never create authority. The summary remains an
unresolved provisional projection. All original summary variants remain in the
immutable Segment results and Aggregate components.

Synthetic test decisions are engineering fixtures, not permission to authorize a
live Source. A real unresolved author or origin must stop at
`NEEDS_HUMAN_RESOLUTION`.

`lossless-sourcepiece-aggregate-v2` validates every original Segment with the
existing 100-Claim/100-Candidate limits. Its finite composite capacity is 100 times
the frozen leaf count, within the Series budget. It preserves all original result
documents, Evidence bindings, local ordinals and Candidate payloads in the existing
`claim-observation-ledger-v1`. Replay Claim and Relation references use ordered
global ordinals. Conflicting Candidate definitions fail closed.

The immutable Aggregate is reconstructed from accepted results whenever read.
The replay input is the validated expansion, not an oversized object submitted to
the historical single-Segment Wire validator.

## Native projection and admission

`lossless-sourcepiece-native-replay-v1` feeds the unchanged Analyzer. Native may
merge identical statements while retaining only the first Claim's other fields.
That output is explicitly non-authoritative. The Source-wide ledger manifest
retains the independent Series ledgers and every Observation ID, including across
SourcePiece merges. Unsupported mappings stop with
`STOP_PROJECTION_MAPPING_AMBIGUOUS`.

The integration persists the complete private Review and admission artifacts,
including their Aggregate, Observation, Native and Semantic identities, before
running `guard_semantic_inputs`. Publication validates the worker fence and Native
checkpoint. No Review decision is applied. Any blocked projection prevents all
Semantic registration for the recovered Source. There is no implicit eligible-only
registration path.

An eligible subset can be examined offline with the existing partitioner. Its
capacity result does not qualify the full Source. Limits remain 31 Stage 1 jobs
and 8 parents per Semantic batch, including all logical extraction Series.

## Explicit recovery

`SourceOperations.authorize_lossless_aggregate_recovery` consumes a formal
resolution and an independently constructed target qualification token. The
`bounded-lossless-aggregate-recovery-v1` scope requires a blocked metadata-conflict
Run, five intact accepted results, exactly 22 never-dispatched leaves across the
remaining four failed Series, zero unknown outcomes and zero Semantic jobs.

Qualification verifies frozen Source/Context, ProviderRecord v4 request/raw/result
identity chains, leases, budgets, failure events, Source-ready Native checkpoint,
and the lossless accepted Aggregate. It compares exact historical Git blobs and
the complete target Python/SQL manifest. Historical Native/research files must
remain byte-identical. A closed inventory permits only the target integration
modules to differ; no AST normalization broadens historical equivalence.

The writer transaction binds the authority artifacts and target contract,
aggregates the accepted five, advances fences, reopens the proven 22, and appends
recovery events. It never calls a Provider, creates an Attempt, replans, retries,
subdivides, registers Semantic work or edits an existing accepted result/failure
event. The original runtime record remains intact; the target authorization is
separate append-only evidence.

Retries with the identical idempotency key, resolution and reason return the
committed result. Conflicting retries fail closed. Concurrent operators share the
existing SQLite writer lock; a lock timeout has no authorization effect and may
be retried explicitly with the same key. Artifact publication before a rollback
is deterministic and is verified on retry, never overwritten with different
content.

After recovery, existing bounded-only execution can process the pending leaves.
The frozen target qualification is restored and revalidated from its immutable
artifact, including installed package bytes, without requiring Git for each
resume. Initial qualification still requires independently readable historical
Git evidence. An unrelated Run or a changed target package cannot inherit it.

This stage does not merge, activate, authorize real metadata, recover a real Run,
execute Providers, make Review decisions, or admit Production data.
