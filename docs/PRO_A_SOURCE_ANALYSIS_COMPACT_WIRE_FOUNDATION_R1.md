# PRO_A_SOURCE_ANALYSIS_COMPACT_WIRE_FOUNDATION_R1

Foundation qualification: **PASS**. Required remote main was fetched and verified as
`e69813cc7a9d25523ab6e5d52ebcfcf8aa03daf6`.

This adds one dormant module, `src/pro_a/source_analysis_wire.py`, and offline tests.
The live Source Analysis prompt, provider adapter, CloudJobs validator, operations,
budgets, capacity, retry and native execution remain unchanged. No active module
imports the foundation. Nothing is merged or activated by this qualification.

## Architecture and versions

The basis is the completed `PRO_A_EXTRACTION_OUTPUT_ARCHITECTURE_REVIEW_R1`
report and its 74-row field matrix covering 55 declared nested fields. Its report
SHA256 is `760c2fd4941b8b8ee82e12a62b56d84dd8f4bdeffbd3fbb4cccde85015b422a8`.
The review is design evidence; its serialization projection is not a production codec.

```text
immutable SourcePiece + authoritative whole-Source SHA + frozen existing Node IDs
  -> pre-model SourceEvidenceCatalog
  -> source-analysis-wire-v2 dict
  -> strict wire/catalog validation
  -> deterministic full canonical dict
  -> existing Analyzer/native validation, merge and provenance
```

| Foundation identity | Value |
| --- | --- |
| SOURCE_ANALYSIS_WIRE_SCHEMA_VERSION | source-analysis-wire-v2 |
| SOURCE_ANALYSIS_EVIDENCE_UNIT_VERSION | source-analysis-evidence-unit-v1 |
| SOURCE_ANALYSIS_WIRE_EXPANDER_VERSION | source-analysis-wire-expander-v1 |

The strict Python validator defines the wire schema. Its public functions are
`build_source_evidence_catalog(context)`,
`validate_source_analysis_wire_v2(wire, catalog, context)` and
`expand_source_analysis_wire_v2(wire, catalog, context)`.
They have no network, DB, randomness or clock dependency. Errors are terminal
`SourceAnalysisWireError` values with source-free messages. Validation performs
no repair, quote generation, fallback, reorder or partial-output salvage.

## Evidence catalog

Frozen dataclasses retain the Source SHA, SourcePiece and known Node ID tuple.
Every frozen unit contains its reference, Source SHA, piece ID and SHA, locator,
local ordinal, hard-block ordinal, exact piece-local code-point start/end, exact
text and exact-text SHA256. Offsets index `SourcePiece.source_text`, not the PDF
binary or the entire document. The frozen plan may supply a separately verified
translation to document offsets in Stage B.

`EV_<16 uppercase hex>` hashes canonical JSON containing the unit contract,
whole-Source SHA, immutable piece ID/SHA, locator, ordinal, block, exact span and
text SHA. It does not use a Claim, provider response, model, Run, current time or
DB state. Identical sentences still have distinct ordered identities. References
are different for another piece or Source, even when their quoted text is equal.

Locator regions reuse the parser's `SOURCE_MARKER` namespace, including
PAGE/PARA/TABLE/SHEET/SLIDE and unmarked TEXT. Sentence-final punctuation,
paragraph boundaries, potential line-start speaker/label headers, represented
inline role headers and bracketed timestamp blocks determine conservative cuts.
Decimal periods, common abbreviations and initialisms are retained. Commas and
semicolons do not split conditionals. Long utterances stay whole and are bounded
by the unchanged 4000-character piece limit. A generic label is a conservative
boundary, not a certified speaker identity. Unrepresented/ambiguous prose speaker
changes and new transcript conventions require Stage B boundary qualification.

Exact text is a literal original slice, including internal whitespace and
punctuation; it is never normalized. Only boundary whitespace and parser markers
are outside selectable spans. They remain in the immutable SourcePiece and its
exact gap ranges. Reassembly of spans plus those gaps reproduces the entire
SourcePiece. Parser-error placeholders are not selectable evidence. No meaningful
represented Source characters are omitted or reordered.

The validator regenerates the complete catalog from the trusted immutable
context and requires equality, integer spans/ordinals and unique references.
Corrupt hashes/text/offsets, duplicates, reordering, foreign pieces/Sources and
unknown references fail. R1 accepts exactly one string evidence_ref per Claim;
arrays, generated excerpts/pointers and model offsets are unsupported. It never
concatenates disconnected units.

## Wire fields and expansion

The required root fields are `wire_version`, `source_metadata` and `claims`.
The four other canonical families may omit empty arrays. Claims and Node
candidates retain the existing 100-object bounded Cloud contract.

| Object | Required wire values | Sparse/default treatment |
| --- | --- | --- |
| Metadata | title, publication_time, source_rank, source_origin_type | author/organization/summary default to empty only; supplied values retained |
| Claim | statement, nature, evidence_ref, attributed_to, fact_time, scope, confidence, novelty_level | derive C1..Cn by array order; default empty links, assumption and structured; absence status means current |
| Node match | node_id, role, confidence, evidence_ref | empty reason may be absent |
| Common Node candidate | canonical_name, primary_type, confidence, independent_research_value, maintenance_rationale | empty aliases, parents, description and reason may be absent; candidate_kind derives from type |
| Event candidate | common fields plus is_discrete_event, event_time, evidence_ref | preserve the actual admission judgment; native quality gates still decide eligibility |
| Theme candidate | common fields plus long_term_research_value, cross_source_or_node_value | preserve both judgments without inferred True values |
| ResearchQuestion candidate | common fields plus question, importance, what_would_change_my_mind | preserve formulation/importance/falsification and supplied common judgments |
| Relation | from_node_id, relation_type, to_node_id, scope, supporting_claim_refs, confidence | only empty reason may be absent; valid unique C ordinals required; part_of forbidden |
| Source reference | title, relation_type | only empty note may be absent |

Nature, attribution, fact_time, scope, confidence and novelty remain explicit,
including explicit unknown strings. Non-current status and nonempty optional
values survive unchanged. Structured remains the existing open JSON object:
nonempty company data and recursive JSON extensions are preserved; non-JSON and
nonfinite values fail. Unknown properties on wire schema objects are rejected.

There is one deliberate compatibility field: Node `preserved_fields`. Current
canonical dictionaries can retain nonempty off-type fields; the existing dense
fixture does so. A discriminator must not discard those values. This explicit,
strictly typed container accepts only the known type-specific fields that do not
belong to the selected variant, with evidence_ref replacing any nonempty quote.
Expansion restores their original canonical positions. It cannot override common
or applicable subtype fields, invent new extensions or bypass native quality.
Direct subtype-field mismatches remain invalid. Ordinary normal candidates emit
none of the eight irrelevant defaults.

Expansion restores all six canonical families, 15 Claim fields and 18 Node
candidate fields. Evidence pointers are `[[locator]]`, or TEXT for unmarked text;
quotes are exactly the selected unit's retained text. The validator checks all
provided existing Node IDs against the frozen context and candidate links against
the response's candidate names. Existing native validators still decide active
endpoints, literal-name evidence, relation direction/negation/direct support,
attribution, candidate quality and evidence fidelity.

Metadata remains per-piece with unchanged first-piece merge semantics. No
once-per-Source metadata operation or other model pass is introduced.

## Exact canonical equivalence and identity

The representability contract is intentionally narrower than permissive legacy
dict acceptance: complete canonical field presence, ordinal C references, one
exact available unit per quote, and that unit's authoritative pointer. Unsupported
old extensions, arbitrary provider-proposed pointers or quotes shorter than a
catalog unit cannot be silently converted. No shipping canonical-to-wire encoder
exists; the inverse fixture builder is test-only.

For representable fixtures, all six families are equal as complete dictionaries,
including every semantic/optional value and array order. Minified sorted-key UTF-8
JSON is byte-equivalent across repeated expansion. Returned objects do not share
mutable defaults or references with inputs. This compares values, not just counts.

Tests use the actual `Analyzer.analyze_source(..., adaptive_retry_policy="forbid")`
entry point with an in-memory frozen response, plus its existing canonical
validator. They compare merge results, accepted/rejected Nodes and relations,
piece origins and `build_claim_record` results. Deterministic permanent Claim IDs
use the unchanged operational formula: Source SHA, Claim index and the entire
validated Claim excluding origin_* fields. Paired inputs produce identical IDs.
Invalid Event/Theme judgments and reversed relations retain the same native
rejections. No weaker parallel semantic validator was added.

Fixtures cover 40 dense Claims, shared/distinct units, Chinese/English/numbers,
fact/data/company guidance/attributed expert judgment, conditional uncertainty,
all four Node variants, matches, relations, references and nonempty nested
structured data. Edge fixtures cover repeated text under equal/different locators,
speaker/timestamp boundaries, paragraphs, empty lines, long utterances, commas,
semicolons, punctuation variants, questions/answers and exact occurrence selection.

## Reproducible serialized size gate

Run the focused test `test_dense_40_claim_size_gate`, or call the test helper
`size_benchmark()` with `src` and `tests` on the Python path. It invokes only the
existing synthetic data function, never `provider.invoke()`.

The R2-derived 40-Claim fixture uses authoritative PARA pointers and ordinal Claim
refs while retaining all legacy Node values. These explicit changes make it
representable; it is not claimed to be the identical earlier review projection.
All measurements use minified UTF-8 JSON with ensure_ascii=False and sorted keys.
The actual wire version and 19-character EV identifiers are included.

| Representation | Characters | UTF-8 bytes |
| --- | ---: | ---: |
| Full canonical/verbose | 22574 | 22574 |
| Sparse, quote-retaining measurement projection | 18715 | 18715 |
| Valid compact evidence-reference wire | 14758 | 14758 |
| Expanded canonical | 22574 | 22574 |

Reduction is **34.6239%**, passing the **>=30%** gate. Sequential ablations account
exactly for 7816 saved characters/bytes: C-reference derivation 711; Claim
quote/pointer replacement 3913; Node sparse variants/reference conversion 217;
remaining defaults/root omission net of version overhead 2975. Categories are
order-dependent ablations, not independent percentages to double-count.

The quote-retaining sparse row is a measurement projection, not a valid V2 response.
No reliable tokenizer was used and no token estimate is claimed. Catalog storage
and future input annotation are outside response sizes. Real 12k completion fit,
model evidence selection and latency remain unqualified.

## Dormancy, compatibility and future Stage B

All 129 existing package Python files match the exact baseline checkout bytes.
Cloud/native Stage 7.2C execution surfaces both report `SEMANTIC_SURFACE_EXACT`.
The new foundation is outside active imports and protected execution closures;
no compatibility exception was added. A future commit changes repository metadata,
but this task does not change the installed stable runtime identity.

The active contract remains capacity-v2 / cap4000 / PRECALL_PARTITION_V3,
operation-output-budget-v1, extraction12000/20000, semantic8192/20000 with input11808,
structured-json-reasoning-v1 / disabled thinking, extraction adapter-v2 and semantic
adapter-v2. Limits remain 16 extraction pieces and 31 total jobs.

`SOURCE_ANALYSIS_COMPACT_WIRE_LIVE_BINDING_R1` would separately need a
source-analysis-piece-v2 operation, new prompt and adapter versions, frozen
wire/evidence/expander identities, catalog/context hashes, raw-wire/canonical
durability and exact native replay routing. Generate catalogs from the original
frozen SourcePiece before annotations; keep annotated provider rendering separate
from SourcePiece.prompt_text to avoid an evidence-ID/prompt-ID dependency cycle.
Reuse the existing Source plan and evidence provenance rather than a parallel
knowledge evidence system. Any newly active module must enter execution closure.
Historical outputs must never be reinterpreted under V2.

Source Analysis evidence_ref is pre-Claim and SourcePiece-bound. Semantic
evidence_unit_id remains post-Claim and parent-Claim-bound; its existing IDs,
build_evidence_units and derived_evidence_unit_id are unchanged. No semantic-unit
algorithm or batching changes are part of the foundation.

Exact quote representability and unrecognized transcript boundaries need explicit
qualification before live binding. Further live validation and Run 8 remain
separate stages, with no fallback to old wire, larger ceilings or adaptive splits.

## Tests, packaging and real state

Focused tests: **61 passed**. The 17 requested existing regression files:
**445 passed, 1 skipped**. The skipped test is
`test_known_fixture_end_to_end_semantic_equivalence`: its frozen Phase 3C/3D replay
artifacts are unavailable in the isolated checkout. Full-repository green is not
claimed.

Compileall over src/tests, pip check and isolated PEP 517 wheel build passed.
All **130** source/wheel/isolated-installed package Python files are byte-identical.
The wheel was installed with pip --target into private qualification storage;
the stable environment was untouched. Git diff --check and the privacy scan passed.
Public changes contain synthetic fixtures only and no credentials/private paths.

Read-only before/after snapshots preserve Source, all Workbench table digests,
Production, schema/count/hash checks, stable metadata and its 129 Python files.
Runs 1-7 and their attempt counts `0/2/1/1/1/1/1` are unchanged. No intake bypass,
Review mutation, Current View mutation, Production Apply or real Run occurred.

```text
LIVE_PROVIDER_WIRE_UNCHANGED = true
REAL_PROVIDER_CALLS = 0
RUN_8_CREATED = false
NEW_CLOUD_OPERATION_KINDS = 0
FOUNDATION_ADDED_CLOUD_JOBS = 0
PRODUCTION_WRITES = 0
WORKBENCH_WRITES = 0
```

The machine-readable receipt records implementation identity, benchmark, packaging,
test results and unchanged-state gates. Stop after the requested Draft PR. No merge
or stable activation is authorized by this foundation task.
