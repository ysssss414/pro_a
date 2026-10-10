# Evidence Intent semantic and span qualification R1

Stage: `EVIDENCE_INTENT_SEMANTIC_AND_SPAN_QUALIFICATION_OFFLINE`.
Base: Draft PR #121, `a634b4fc0b311c0bad47da7bb421b6999e89cc47`.
Stable remains `3e2e690690d0b847cef3fc455b41ee47e52bcd14`, schema12,
default ProviderRecord v4. No release, merge, real Run or real call is authorized.

This stage extends the previous experiment through the existing internal
Operator. Evidence location and execution ownership are deterministic;
research support remains subject to Human Review. Unproved language relations
are explicitly recorded rather than treated as machine-certified facts.

## Gate A: complete span representation

ProviderRecord v7 uses a closed strict-tool schema without `anyOf`. Each
Evidence Intent has five strings:

```json
{
  "kind": "UNIT_SELECTION",
  "unit_anchor": "<frozen unit anchor>",
  "selection_mode": "RAW_SUBSPAN",
  "quote": "<exact source substring>",
  "occurrence": "2"
}
```

`WHOLE_UNIT` requires an empty quote and occurrence `1`. Both subspan modes
require an explicit positive occurrence. `NORMALIZED_SUBSPAN` invokes the
unchanged v2 normalization/provenance rules. Overlapping matches count exactly
as v2 counts them. A repeated string across units requires the explicit unit
anchor; a repeated string inside that unit requires its occurrence. No first
match, mode fallback, quote enlargement or missing-occurrence default is used.

`EXACT_QUOTE` is a convenience with empty unit anchor, RAW mode and occurrence
`1`. It requires exactly one literal occurrence in the entire SourcePiece and
containment in exactly one catalog unit. It rejects repetitions, missing text
and spans crossing units. This convenience does not restrict UNIT_SELECTION.

The completeness argument is constructive. For every valid v2 selection in a
verified current-leaf unit, that unit's anchor identifies the same Evidence ref.
WHOLE maps to the same whole-unit selection. An explicit RAW/NORMALIZED mode,
unchanged quote and explicit occurrence map to precisely the same v2 arguments.
For a legacy implicit mode or omitted unique occurrence, the equivalent new
input explicitly names its resolved mode and occurrence; the new compiler
never infers these values from a response or converts historical records.
Arbitrary native Claim pointers remain separate from location and are preserved.
Therefore the resolver, raw origin, binding hash, Wire fields and native Claim
input remain identical. Permanent IDs use that unchanged native input, not the
new anchor, review metadata, series or protocol identity.

Qualification enumerates every substring and valid occurrence in small RAW
and normalized synthetic units, including overlapping repeats, full-width
characters, NFKC expansion, Markdown escaping and whitespace collapse. Each
pair compares the full binding (including pointer and hashes), Segment Wire
and native projection. Existing v2 cases for unsupported normalization remain
rejections. The finite corpus checks the direct mapping; it is not presented as
an enumeration of all possible natural-language source text.

No legal v2 selection is excluded within the validated unit/current-leaf scope.
Foreign primary Evidence is intentionally outside the ownership contract.
Evidence Binding v2 and historical ProviderRecord v1–v6 are unchanged.

## Gate B: review representation and authority

Every Claim includes `research_review` with `context_dependencies` and
`review_reasons`. Each dependency gives an Evidence Intent, a declared
relationship (`ANAPHORA`, `TEMPORAL_INHERITANCE`, `ATTRIBUTION`, `CONDITION`,
or `BACKGROUND`) and an explanation. Its source span, locator and binding are
validated against the same authoritative SourcePiece catalog. Context may
belong to another leaf but cannot become primary Evidence, Candidate support
or an implicit cross-Segment Claim.

The separate review attachment reports:

| State | Meaning |
| --- | --- |
| `LOCATION_VERIFIED` | Exact selected source span and current primary ownership passed. |
| `CONTEXT_DEPENDENCY_DECLARED` | The model explicitly declared a validated context location; its relationship remains unproved. |
| `SEMANTIC_REVIEW_REQUIRED` | Human Review remains necessary for research judgment. Every emitted Claim receives this state. |
| `UNRESOLVED_EVIDENCE` | A unique valid location or current primary owner cannot be established; compilation fails closed. |

`EVIDENCE_LOCATION_PASS` never means `SEMANTIC_TRUTH_CONFIRMED`. Neither a
dependency declaration nor a model-provided reason grants semantic authority.
Node Match, Candidate and Relation paths also remain listed for research
review. The compiler does not alter Canonical statement, nature, status,
attribution, time, scope, conditions or numeric values to make them pass.

Synthetic analogues cover Claim14 at Unit18 in its real owner, Claim8 context
dependence, Claim11 temporal inheritance, PR100's 16/17 and subdivided 8/9
boundaries, and PR101's excluded/wrong subject and ambiguous antecedents.
The tests deliberately include correct quotations with false numbers, dropped
conditions, wrong attribution and inverted negation. Location may pass in
these examples; truth remains `NOT_ESTABLISHED`. These are demonstrations of
the authorization limit, not false-positive semantic success claims.

No general NLI, antecedent resolver, graph service, second model, automatic
routing, Claim rewriting or specialized Retry is introduced. The previous
private forensic findings remain unchanged; historical responses are never
fed through the new protocol, repaired or readmitted.

## Gate C: existing Operator and ledger

The explicit internal `output_qualification.start(..., record_version=v7.VERSION)`
selects binding v6, Provider v8, tool schema/record/prompt/response v7 and
output Series/Batch v6. The new Operator qualification identity is v2; existing
v5/v6 qualification identities remain v1. Ordinary production remains v4.

The path is `SourceOperations → OutputDecompositionRunner → Bounded Ledger`.
Existing standard intake, domain, identity, configuration, reservation, budget
and bounded-resume guards remain active. Version selection comes from frozen
Run/Series/Attempt identities and never from response shape. The new compiler
is included in runtime code fingerprints and execution dependencies.

The request preserves the original frozen research user prompt verbatim,
including filename/mode and its research fields; the original semantic system
prompt is retained. It also carries the complete Scoped Node Catalog, native
input and SourcePiece metadata, Source/Series/Segment identities and exact
Assigned/Context text, anchors, refs, locators and spans. Metadata avoids
repeating all native Source text fields; the full original prompt and explicit
regions are both retained. The qualification uses a nonempty two-Node catalog
with names, types and aliases, rather than an IDs-only or empty-catalog check.
Provider/model, 24k output ceiling, Series budget and no-automatic-retry policy
retain the existing qualified values. Actual input/output token costs are
`NOT_OBSERVED`; preserving the original request adds input overhead that must
be measured in the separately authorized live stage.

New results pass Intent compilation, unchanged Evidence Binding v2, v6
Candidate support-set ownership and existing Wire/native validation. Bounded
`Accepted` means a structurally complete extraction result. It does not certify
semantic truth or grant Canonical/Production permission. Invalid locations,
refs, schema values, unsupported Candidates or foreign primary ownership
cannot enter accepted results. No partial failure is silently discarded.

Schema12 persists the review as a separate immutable `<segment>.review.json`.
The ordinary result artifact contains only a hash/path reference outside the
SegmentWireResult and its Wire; the existing accepted receipt/event chain seals
that reference. The attachment carries protocol, Source binding provenance,
series/segment/result identities, `NON_AUTHORITATIVE_RESEARCH_REVIEW`,
`NOT_ESTABLISHED` and `canonical_permission=false`. Reading verifies its hash,
identity and authority boundary. No schema13 migration or Canonical field is
needed. A publication-crash test recovers from the same durable Raw without a
new attempt/call, preserves the original attachment bytes, and rejects a
subsequently corrupted attachment.

The formal Fake Provider Run exercises RAW, NORMALIZED and WHOLE bindings,
all research families, Candidate support provenance, durable results and
review attachments. A child process rebuilds the same frozen execution
identity and finishes the remaining leaf through a one-call bounded resume.
The Run stops at Bounded Extraction complete, with zero Semantic Jobs and no
changes to its synthetic knowledge database. Ordinary v4 and explicit v5/v6
paths retain their existing behavior. Invalid-result cases stop after one
fake response with durable Raw and zero accepted results.

## Validation receipt

`STAGE_RESULT=OFFLINE_QUALIFICATION_PASS`. All three gates pass within the
location/ownership and non-authoritative review boundary described above.
The final runs passed **42 focused source checks, 87 related regressions and
41 isolated installed-package checks**, with zero final failures/errors.
Gate A/B's initial 20 checks passed before formal integration began.

The isolated package is built from code commit
`d0af7357f8fc179f5637168b522bdd58cebadcbc`; Wheel SHA256 is
`6b8f60c334687d10fc6214ed8e2cdedbc6f893dca48342e9a2f4e743bb7f263d`.
All 164 packaged Python/SQL source files match Git and installed bytes.
Follow-up report/receipt commits change documentation only. No-Git identity,
dependency consistency, checkout denial and installed v7/default-v4 Operator
checks passed. Historical identity vectors are also checked in the installation.

An initial wider installed-test round was interrupted; no complete result is
claimed. Windows left its child worker running, causing temporary-directory
locks in a subsequent round. Only identified task workers were stopped. The
final selected installed suite passed in a fresh short directory using the
same wheel, with no application-code change to accommodate those errors.

Final source-gate and isolated-wheel counts, commit identity and integrity
results are recorded in the companion machine-readable receipt. The isolated
installation reuses the existing candidate environment and smoke harness;
it does not replace or activate Stable. Installed tests deny source-checkout
fallback and external networking, including process restart.

Focused tests and related regressions are used; the unrelated large Run13
topology suite is not repeated. Temporary artifact paths use a short D-drive
directory to avoid the existing Windows path-length limit. Public changes
contain only code, synthetic tests and this sanitized report. Private Source,
Raw, requests, credentials and integrity inventories remain local.

`REAL_PROVIDER_CALLS=0; NEW_REAL_RUNS=0; SEMANTIC_JOBS=0; PRODUCTION_WRITES=0;
CURRENT_VIEW_WRITES=0`. PR #121 stays Draft, open and unmerged. Further live
qualification requires a separate authorization; no production-stability or
real-provider schema acceptance is inferred from Fake Provider tests.

`NEXT_STAGE=EVIDENCE_INTENT_RELEASE_AND_BOUNDED_LIVE_QUALIFICATION`.
