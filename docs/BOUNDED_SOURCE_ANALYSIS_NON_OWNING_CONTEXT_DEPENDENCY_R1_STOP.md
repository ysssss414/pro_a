# BOUNDED_SOURCE_ANALYSIS_NON_OWNING_CONTEXT_DEPENDENCY_R1 — STOP

`CONTEXT_DEPENDENCY_CONTRACT = NOT_QUALIFIED`

`CONTEXT_GRAPH_SEMANTIC_EDGE_AUTHORIZATION_UNPROVEN`

This is a B0 diagnostic milestone, not production implementation or a rejection
of the non-owning-context architecture in principle. Exact selector provenance
and a constrained statement transformation work for hand-authored correct edges.
They do not establish that a resolver's selected antecedent is correct or unique.
The mandatory wrong-antecedent and ambiguous-antecedent rejection gates therefore
remain unmet. Per the graph-validation STOP condition, no provider resolver or
production acceptance path was implemented.

## Provenance and scope

The independent branch `codex/pro-a-non-owning-context-dependency-r1` starts at
exact main `6e1135c4371a6a3d1b6a491a433576b3eda9efbe`.
PR #100 remains OPEN/Draft/unmerged at
`2bddb930af0e993bee39e7cd6cf5598f3e2b295c`; its three changed files are diagnostic
tests and sanitized evidence only. The public 16/1 and 8/8 fixtures were
reconstructed from diagnostic commit
`9c58aa16d578af31d28c468cafe6d2cb1ce01cd5`, not used as the branch base.
Candidate A's two STOP findings are unchanged.

All new executable code is under `tests/`. `lexical_graph_probe` explicitly
returns `semantic_authorization = UNPROVEN`, never an accepted graph. It is not
a complete hardened graph/envelope validator. Production never imports it.
No real or synthetic graph was accepted into the real Workbench.

## What was demonstrated

Final focused run: **34 passed in 8.77 seconds**. The earlier 29-test subset is
not additive. Passing tests include two explicit falsification tests; this is
not a B0 PASS or an implementation regression qualification.

| Diagnostic | Result and precise limit |
| --- | --- |
| Separate CTX namespace | CTX hashes bind version, Source SHA, piece identity, exact span/text SHA and kind; no `CTX_EV_...` alias. |
| Selector binding | Reuses unchanged Evidence binding v2; missing/ambiguous selectors and fuzzy Node names reject. No model offsets. |
| Complete graph disposition list | Exact catalog order, exactly once; omitted/duplicated dispositions reject. Structural coverage only. |
| Resolver output shape | Claims, statement, Node candidates, relations and metadata are forbidden top-level fields. |
| Locality | Cross-Source, cross-piece, self and cyclic dependencies reject in the lexical probe. |
| Projection | Only owned EV identities/text and relevant selector-only CTX projections; no foreign EV identities in the tested requests. |
| Primary refs | A direct-ref probe rejects CTX and foreign EV; production field-by-field integration was not implemented. |
| Subdivision | The target child's projection retains its dependency, while the non-target child gets none. |
| #100 truth | Both companies pass 16/1 and 8/8 synthetic aggregate → expansion → unchanged native validation, including exact canonical Claim equality and permanent ID. |
| Cross-boundary projection | Explicit hand-authored edges project across paragraph, speaker, timestamp and section labels. This does not prove those edges' semantic truth. |
| Two leakage fixtures | Selector-only requests exclude foreign capacity/date/forecast/customer facts; exact statement substitution rejects copying those facts. |
| No dependency / explicit ambiguity | Neither projects context. The probe does not prove that a resolver chose the correct disposition. |
| Wrong antecedent / ambiguous antecedents | **Unmet acceptance gate**: lexical graph checks and exact substitution cannot reject the bad edge. |

The four #100 comparisons reuse the synthetic whole-piece canonical truth for
scope and attribution. They prove compatibility of ownership and canonical
replay with a correct graph; they do **not** qualify guards for provider-written
scope, attribution, confidence, related Nodes, undeclared context use or review
projection. No broader leakage-guard PASS is claimed.

## Decisive synthetic counterexamples

```
以下产能数据仅指青松公司。
白杨公司与本次产能数据无关。
该公司现有产能为100台。
```

An incorrect graph can select target `该公司`, context `白杨公司`, and the valid
frozen Node for 白杨公司. Both selectors bind exactly, all refs are Source-local,
the graph is complete and acyclic, and the Node name matches exactly. The result
`白杨公司现有产能为100台。` reverses exactly to the owned Evidence. Nevertheless,
the Source explicitly excludes that company. Unchanged native validation also
validates the Evidence excerpt; it does not reject this referent error.

In a second fixture, `青松公司和白杨公司均参加了会议。` precedes the same pronoun
measurement. Either company substitution passes the lexical checks. An
`AMBIGUOUS_DEPENDENCY` enum alone does not prevent a resolver from incorrectly
returning `DEPENDENCY` instead.

This separates three obligations: the selector occurs; the statement changes
only by the allowed substitution; and that substitution is semantically
authorized by this Source. The first two do not prove the third. A hash,
persisted model answer, model explanation or another LLM is not that proof.
The diagnostic does not establish that no stronger deterministic contract can
work. It establishes that the examined selector/substitution contract is
insufficient for the requested hard negative gates. Ad hoc exclusion-word
filters or silently trusting resolver judgment were not installed as a fix.

## Durability architecture audit

`CONTEXT_GRAPH_DURABILITY = NOT_QUALIFIED`

`CONTEXT_GRAPH_DURABILITY_REQUIRES_SCHEMA13 = UNDETERMINED`

The existing schema12 attempt row requires a non-null extraction Segment FK.
Dispatches reference those attempts, outcomes reference dispatches, and accepted
Segment results bind those outcomes back to the same Segment. The existing
`account_series_calls` rejects a resolver identity outside the extraction plan.
These facts are checked against the actual schema generator and accounting code.
A fake Segment, negative ordinal, CloudJob reuse or hidden/free call would be
incorrect and was not used.

However, schema12 already has an immutable, hash-chained Series-level
`bounded_extraction_events` table with generic event type/body fields. Therefore
absence of dedicated resolver tables does **not** prove schema13 is mandatory.
An event-ledger design remains a possible schema12 route. It would require:

1. A new binding/execution version that makes resolver events authoritative and
   rejects old runtimes; the current loader only hash-checks these events and
   reconstructs accounting from Segment attempt rows.
2. Typed resolver request/reservation, dispatch intent, raw outcome and validated
   graph events, all bound to the Series, attempt, frozen input and artifact SHA.
3. One-shot state transitions enforced under the existing Series fence and
   writer transaction. Durable request precedes intent; intent precedes network;
   raw publication precedes graph acceptance. No Segment ownership is created.
4. Recovery of committed events/artifacts and rejection of inconsistent hashes,
   duplicates and out-of-order transitions. Intent without durable outcome must
   remain `RECOVERY_REQUIRED`, never recall; `finish_reason=length` must fail
   closed without partial graph acceptance or graph subdivision.
5. Combined resolver/extraction accounting, including unknown-output reservation,
   atomic budget reservation, and graph provenance/review projection. An event
   record without these semantics is not a qualified ledger.

These are requirements for a candidate architecture, **not implemented or
crash-tested guarantees**. The semantic STOP was reached before this route was
qualified. No schema13 requirement, schema13 tables, migration, or schema12
durability PASS is claimed. A minimal schema13 proposal would be premature until
the event-ledger alternative is evaluated; no permission to migrate is requested.

## Call and output budget

An actual existing-policy synthetic tree reaches 16 leaves, depth 4 and 31
extraction nodes. One resolver plus that tree is 32 calls. More generally, a
binary forest with R roots and L terminal leaves has `2L-R` extraction nodes;
for `1 <= R <= L <= 16`, `1 + 2L - R <= 32`. This includes truncated parents
that subdivide, provided each node is called at most once and no retry occurs.

At a **candidate** resolver ceiling no greater than 12000, worst-case liability
is `31*12000 + 12000 = 384000`, within the unchanged Series ceiling. Unknown
resolver usage must reserve its entire ceiling. A smaller custom Series budget
must still be checked before admission. No resolver profile/prompt/ceiling was
activated or asserted empirically sufficient; no output-capacity measurement
was possible without a qualified resolver contract. Arithmetic feasibility is
not current accounting support or durability qualification.

## Frozen real Source census

This is deterministic structural/lexical counting, not coreference annotation.
All reads use verified frozen Run #8 inputs; network and operator writes are
blocked. Pattern definitions and per-piece details are in the JSON evidence.

| Piece | Evidence | Existing roots | Adjacent Segment pairs | Units with pronoun/demonstrative pattern | Units with exact frozen Node mention |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1 | 77 | 5 | 4 | 25 | 23 |
| 2 | 93 | 6 | 5 | 18 | 11 |
| 3 | 83 | 6 | 5 | 19 | 25 |
| 4 | 82 | 6 | 5 | 23 | 22 |
| 5 | 52 | 4 | 3 | 17 | 8 |
| Total | 387 | 27 | 22 | 102 | 89 |

There are 118 pronoun/demonstrative pattern hits and 113 exact Node mention
spans. Four right-hand units at existing Segment boundaries contain a pronoun
pattern; no dependency is inferred from this. The lexical scans find zero
configured speaker-label or timestamp matches, 22 generic label candidates and
13 blank-line breaks. Label categories can overlap and are not semantic section
annotations. Summed per-piece Node cardinalities are not globally distinct Nodes.

## Unchanged real state and remaining gates

Main/stable remains `6e1135c4371a6a3d1b6a491a433576b3eda9efbe`; schema12 and
complete pre/post state snapshots are identical. Run #8 remains terminal
BLOCKED / BOUNDED_EXTRACTION_FAILED with one lifetime real call, no unknown
external-outcome liability, no accepted Segment, Semantic job, Review Packet,
decision or promotion. Runs #1–#7, 14 historical queued jobs, Production and
Current View are unchanged. The raw response is still rejected: 5 invalid roles,
47 foreign bindings (44 Claims + 3 Node matches), 45 distinct foreign refs.

`RUN8_MUTATED = false`; `RUN8_RAW_STILL_REJECTED = true`;
`WIRE_VALIDATOR_RELAXED = false`; `PROVIDER_CALLS = 0`;
`RUN9_CREATED = false`; `AUTHORIZATION_REQUIRED_FOR_LIVE_RUN9 = true`.

Only REFERENT_RESOLUTION was examined. No context kind is qualified for active
use. SPEAKER_ATTRIBUTION, TEMPORAL_CONTEXT and SECTION_SCOPE are deferred.
Provider resolver, durable graph acceptance, production envelope guards,
field-specific Node/relation guards, review provenance, version activation,
Stage7.2C changed-surface tests, full regressions, build/install gates and release
were not run after the semantic STOP. No claim of these gates passing is made.
Old Run #8 bindings and artifacts are never reinterpreted or made compatible.

The next contract revision must supply a machine-checkable edge-authorization
witness (possibly a strictly limited Source-local explicit-reference grammar),
or explicitly narrow the supported language and fail closed outside it. It must
still pass wrong/ambiguous antecedent tests, undeclared-use and all-field leakage
tests before durability qualification or provider work. Merely making the
resolver output durable cannot repair semantic authorization.
