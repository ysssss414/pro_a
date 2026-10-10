# V6 Evidence Binding offline architecture review R1

Stage: `V6_EVIDENCE_BINDING_OFFLINE_ARCHITECTURE_REVIEW`.
Released baseline: `3e2e690690d0b847cef3fc455b41ee47e52bcd14`, schema12,
default ProviderRecord v4, explicit existing Operator v6.

The location/ownership prototype passes its offline boundary tests. It does
**not** qualify automatic semantic authorization or a new formal Run protocol.
Keep complete SourcePiece context, prefer Assigned Evidence, and stop integration
at a non-canonical binding candidate. No release, activation, real call or real
Run creation occurs in this stage.

## P0: immutable real failure, sanitized findings

The original v6 response remains unchanged: server strict schema and standard
JSON Schema passed; 14 Claims, 13 valid Claim bindings, three valid Node Match
bindings, zero Candidates and zero Accepted Segments. Only one prior-stage real
call occurred. This stage makes zero calls and never repairs/readmits that Raw.

| Required question | Read-only finding |
| --- | --- |
| Does Claim 14's selector exist in the complete SourcePiece? | Yes, character-for-character, including the original whitespace. The selector itself is valid. |
| How many matching Evidence Units? | One raw occurrence in one Evidence Unit. |
| Is it unique, including normalization? | One raw and one normalized candidate, at the same raw span. No repeat or normalization ambiguity was observed for this selector. This is a case-specific result. |
| Which Segment actually owns it? | Evidence Unit 18 belongs to the second initial leaf. The supplied ID identifies a question in Unit 16, owned by the first leaf. |
| Is question + answer necessary for the stated fact? | The answer explicitly names the subjects and both measurements. This particular proposition does not require question-derived subject substitution. General speaker attribution still uses Source context. |
| Can the true owner represent it without changing the fact? | Yes in the existing representation: the same statement can cite the explicit answer in its own leaf. This is a representability finding, not permission to edit or accept the old response. |
| Do the other 13 valid bindings establish semantic support? | No. Their literal and normalized locations are unique and local, but exact binding does not establish entailment, attribution or context edges. See below. |

Classification: `EVIDENCE_ID_SELECTOR_MISMATCH` plus
`SUPPORT_OUTSIDE_ASSIGNED_SEGMENT`. This is not an invalid source-wide selector,
not a server schema rejection, and not an ownership-Candidate failure. Neither
the question nor an arbitrary default Evidence may replace the real support.

All remaining 13 selections bind locally. Two require particular context review:
Claim 8 expands an anaphoric circumstance using the previous Unit; Claim 11 has a
temporal continuation whose referent is in the previous Unit. Claim 2 also uses
a plausible OCR interpretation rather than literal letter identity. Other
statements retain inspected forecast/conditional markers, but industry scope
and speaker attribution depend on source-wide context. No claim-level automatic
semantic PASS is inferred from these observations.

The comparable Run16 result uses the same frozen SourcePiece and the same
Assigned Evidence set: five old Node Matches versus three new, with three shared,
two old-only and no new-only identities. Two shared matches have direct literal
subject/technology anchors. The other shared match cites a broad heading while
its reason asserts a specific material; the narrow anchor alone does not prove
that reason in either version. The two old-only matches likewise use broad
anchors for narrower technical reasons. Fewer matches therefore do not establish
quality loss. These are single matched artifacts, not statistical success-rate
or cost comparisons; other Run16 batches are not substituted into this comparison.

Private Source, selectors, IDs, requests, responses and detailed judgments stay
outside Git. Before/after capture verifies every protected table, historical
artifact, installed package, runtime metadata, Production and Current View.

## P1: architecture comparison

| Property | A: Assigned Evidence first | B: source-wide anchor with automatic routing |
| --- | --- | --- |
| Complete semantic context | Retained once, partitioned into explicit ASSIGNED and CONTEXT regions. | Also required; removing it repeats PR100's information-loss counterexample. |
| Precise location | Program-issued whole-Unit anchor or an independently located exact quote. No independent model ID/selector/occurrence triple. | The same exact location diagnostic is possible. |
| Foreign support | Explicit unresolved error naming the true owning leaf; no acceptance or scheduling. True owner may generate a new response. | Location alone cannot authorize transfer, duplication, or acceptance. |
| Repeated text | Whole-Unit anchor identifies an explicit original location; quote ambiguity fails closed. | The same ambiguity must fail closed; never choose the first occurrence. |
| Q/A at 16/17 or subdivision 8/9 | Owner still sees the complete question context; Claim intent and answer excerpt remain unchanged. Referent authorization is a separate unresolved gate. | Routing does not prove that a question establishes the subject of an answer. |
| Durable cost | No inbox, extra call or schema migration in the prototype. | Automatic routing requires durable pending intents, frozen destination/frontier, budget reservation, deduplication, coverage and restart semantics. These are not qualified. |

Select **A for the offline prototype**, using source-wide exact lookup only to
detect ambiguity and foreign support. Do not implement B's global scheduler.
The baseline budget/ledger is Segment-owned. A transfer after the destination has
already completed would require reopening it, a budgeted extra dispatch, or an
unresolved observation. A transfer before completion can duplicate a separately
generated Claim. An empty destination acknowledgment is not proof that the
transferred fact is covered. No duplicate suppression or Canonical reordering
rule is proven here. Existing schema12 can store some generic Series events;
that does not itself prove a suitable inbox or a need for schema13.

Primary historical counterexamples were inspected directly:

- [PR100](https://github.com/ysssss414/pro_a/pull/100), diagnostic HEAD
  `2bddb930af0e993bee39e7cd6cf5598f3e2b295c`: at Unit16/17 and subdivision8/9,
  identical answer-only input can have different company truth in its preceding
  context. Strict segment-local projection loses meaning/identity. An unresolved
  generic statement is not an equivalent Canonical fact.
- [PR101](https://github.com/ysssss414/pro_a/pull/101), diagnostic HEAD
  `c38e49d44a1354acb40efd636842b3ab95315e74`: exact selectors, allowed Node IDs
  and exact name substitution can all pass while selecting an explicitly
  excluded company, or one of two ambiguous antecedents. Lexical checks do not
  authorize a semantic edge. Neither draft's STOP is converted into a PASS.

## P2: implemented, explicit offline protocol

`pro_a.evidence_intent_prototype` defines distinct identities:
`evidence-intent-offline-prototype-v1` and
`evidence-intent-offline-tool-schema-v1`. They are **not** advertised as a frozen
ProviderRecord v7 or added to Run/Operator selection.

The complete SourcePiece is partitioned into ordered regions. Concatenating
their text recreates the original exactly. ASSIGNED regions contain a
program-issued anchor; CONTEXT regions expose text without an eligible anchor.
No source text is removed to enforce ownership.

Each Evidence intent is one closed `{kind, value}` object:

- `UNIT_ANCHOR`: the exact immutable catalog Unit, not a guessed default.
- `EXACT_QUOTE`: a nonempty literal substring. The program searches the complete
  original SourcePiece, including overlapping repeats. Exactly one occurrence
  must fit exactly one verified Unit, which must be assigned to the active leaf.

No fuzzy or normalized matching, name replacement, first-match selection,
automatic routing, or failed-Claim deletion occurs. Missing, repeated,
multi-Unit and foreign quotes stop compilation. Whole-Unit anchors can distinguish
identical complete Units because they bind their original positions. Ambiguous
repeated subspans are **not** automatically enlarged into whole-Unit excerpts.
They remain unresolved. Full parity for every historical legal occurrence-based
or NORMALIZED_SUBSPAN selection is therefore **not qualified** by this prototype.
This limitation blocks general replacement of v6; it is not a relaxation of
Evidence Binding v2.

Only new explicitly versioned synthetic records enter this compiler. It validates
the original plan/catalog/active leaf through the existing coverage checks,
derives a v6-shaped internal record, then calls the unchanged v6 compiler and
Evidence Binding v2. Candidate Claim links, direct Evidence properties, all
support relationships, Node Match membership and local Relation Claim references
still pass the existing validators. Research fields, ordering, explicit values
and existing canonical pointer metadata are preserved. Original intents and
derived selections/bindings remain in the replay proof.

The return is `NON_CANONICAL_BINDING_CANDIDATE`, with
`semantic_authorization=NOT_ESTABLISHED` and `segment_accepted=false`.
It has no formal Run entry, ledger write, network call or admission method.
The existing v6 durable path rejects this new Raw instead of shape-routing it
into v6. The synthetic review-envelope persistence/restart exercise is test-only;
no quarantine subsystem is added to the application.

### Deterministic proof and its limit

Given the frozen catalog and leaf, each successful exact intent determines one
raw span, one Unit and one owner. Existing binding hashes and v6 support-set
provenance make the result replayable. Repeating compilation in a fresh process
reproduces request target, result and proof. For legal unique RAW_SUBSPAN and
WHOLE_UNIT representations of the same full excerpt, canonical projection,
native analyzer output and permanent Claim identity agree. Binding mode hashes
need not agree: they encode different selections, not different facts.

The excluded-subject, ambiguous-antecedent and wrong-measurement counterexamples
also produce valid **locations**. They never acquire semantic authority or
Accepted status. The fake model and synthetic expectations are not truth
oracles. Existing semantic guards identify some conflicts; lack of a demonstrated
conflict is not a general entailment proof. No new referent validator is claimed.

The model still must supply statement, subject/scope, attribution, modality,
conditions, Candidate support links and local Relation support. Where the primary
excerpt has an anaphoric or temporal dependency, the minimum missing research
input is explicit context-support intent and the proposed semantic relationship,
or an unresolved status. Model-provided relationships themselves require
independent review/qualified authorization. A deterministic compiler cannot infer
an excluded or ambiguous antecedent from offsets. This stage does not implement
that authorization layer or label model-supplied metadata authoritative.

### NON_CANONICAL / QUARANTINED observations

A separate quarantined observation could preserve valid portions and failed
diagnostics for research review. It must retain complete original Raw and its
identity, failed-object indexes, frozen context, and explicit incomplete status;
it cannot close coverage, count as a Segment Accepted, or feed Semantic admission
as an accepted aggregate. The existing accepted-leaf observation path does not
qualify partial failed responses. This is useful follow-up scope, but not needed
for the location proof and not implemented here. The prototype already retains
all input when rejecting; it never selectively drops the bad Claim.

## Verification and resources

`tests/test_evidence_intent_prototype.py`: 22 tests pass, covering all ten requested
case categories. Positive tests prove representation/binding; semantic
counterexamples prove the lack of authorization, not automatic semantic success.
Fake tool response -> standard JSON Schema -> new intent compiler -> existing v6
compiler -> Evidence/Wire -> native/permanent identity checks and a fresh-process
review-envelope replay are exercised. A separate schema12 synthetic ledger test
proves that the frozen runtime rejects the new protocol with zero Accepted
Segments, zero Semantic jobs and unchanged synthetic Production.

Focused related regression: **98 passed**. After the final anchor uniqueness
check, the 22 prototype tests passed again. Isolated installed wheel checks:
**39 passed**, with checkout access denied, independent no-Git identity validation,
and Git/wheel/installed equality for 163 source/SQL files. The candidate package
was built from code commit `c1367dea00b84ad8bfcbaa1b7992bd3601e11b43`; only this
report/receipt changes after that build. Package details are in the companion
receipt. A larger regression attempt was stopped during the unrelated historical
Run13 full-topology case; no completed result is claimed for that attempt.
Tests use existing D-drive environments and synthetic fixtures. No additional
worktree, schema migration or disk cleanup is performed.

For the real frozen input, read-only request-size inspection found the new user
payload plus strict schema character count at **93.8%** of the original v6 pair.
This is **not an equivalent complete research request comparison**: the prototype
envelope carries known Node IDs, while the existing request also carries the
scoped Node catalog and fuller frozen-target metadata. A formal request must
retain the original research catalog, rather than interpret its omission as a
cost saving. System prompting/tokenizer effects are also excluded. No Token/cost
saving or full cost gate is proven. Actual Provider acceptance, output richness
and Token changes are `NOT_OBSERVED`. The binding compiler requires zero added
calls; complete request-context/cost parity remains integration qualification.

Stable stays at the released baseline. Exact protected-state comparison and
sealed request/Raw/HTTP hash checks pass; schema12 integrity/foreign-key checks
pass. No old Raw is compiled with the prototype or readmitted.

## Decision

`STAGE_RESULT = OFFLINE_BINDING_PROTOTYPE_PASS; FORMAL_INTEGRATION_STOP`

This is a useful location/ownership experiment, not a complete semantic repair.
Keep A's interface direction. Before a formal new protocol is integrated, qualify
context-dependent semantic authorization, the unresolved repeated/normalized
span representation, and complete-source coverage without silent duplication or
loss. Preserve all v1-v6 identities and default v4. B's automatic ownership
routing remains unqualified. No bounded live run is authorized by this result.

`REAL_PROVIDER_CALLS = 0`; `NEW_REAL_RUNS = 0`; `SEMANTIC_JOBS = 0`;
`PRODUCTION_WRITES = 0`; `CURRENT_VIEW_WRITES = 0`.

`NEXT_STAGE = EVIDENCE_INTENT_SEMANTIC_AND_SPAN_QUALIFICATION_OFFLINE`
