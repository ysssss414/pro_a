# Semantic Intent / Deterministic Compiler R1 and R1.1

Stage: `PROVIDER_SEMANTIC_INTENT_DETERMINISTIC_COMPILER_R1`.
Base release: `26c3be797cbd502a6773332e014ae8a19473a349`.

## Read-only failure diagnosis

The latest Run16 failure was reproduced from the durable Attempt, its events,
immutable raw response and frozen request. Workbench was freshly checked at 10
calls, 8 accepted results, 18 never-dispatched segments and one failed segment.
No historical data or authorization was changed.

The response contains 12 Node Candidates. The following zero-based candidates
omit the required common field `ownership_evidence_ref`:

| Candidate indices | Declared primary_type | Defect |
| --- | --- | --- |
| 2, 3, 4, 5 | Company | Missing ownership_evidence_ref |
| 7 | Technology | Missing ownership_evidence_ref |
| 8, 11 | Product | Missing ownership_evidence_ref |
| 9 | Material | Missing ownership_evidence_ref |
| 10 | Equipment | Missing ownership_evidence_ref |

No additional missing fields, extra fields, type mismatches, illegal enums or
nested preserved-selection schema errors were found. The earliest local gate is
`output_provider_record_v4.validate_shape()`, at candidate 2. Its branch exception
handling hides the nine individual required-field errors behind
`INVALID_PROVIDER_VARIANT_BRANCH`.

Draft 2020-12 JSON Schema validation rejects the same original response against
the **actual frozen tool parameters**. These parameters equal the v4 local
schema. The frozen request has `strict=true`, named `emit_source_analysis` tool
choice, thinking disabled, and ProviderRecord v4. Its existing schema identity is
`bfed5e705202ad9c39947421bb8f9481a282b69e9330ff7663afeea10ba7b2e4`.
The prior dispatch boundary verified that the submitted request matched the
frozen request identity. HTTP 200 and `tool_calls` did not imply schema validity.

This is a captured response-contract violation, not an observed local/standard
schema disagreement. It does not establish why the upstream strict constraint
was violated. The existing v4 `anyOf` walker requires exactly one match, whereas
JSON Schema requires at least one; the four frozen branches have disjoint
`primary_type` enums, so that distinction cannot cause this failure. No v4
acceptance rule was changed. The compiler cannot infer the missing ownership
and continues to reject this omission.

`provider_record_diagnostics.diagnose_shape(record, frozen_schema)` is an
independent read-only diagnostic API using the dev `jsonschema` dependency. It
returns paths, reason codes, missing/extra fields and type names; it omits
instance values and validator messages. Unknown property names are redacted.
For a declared Node type it reports that branch's causes. It neither normalizes
nor admits the response. It was checked against the actual frozen failure and
synthetic missing/extra/type/enum/nested-selection cases. Raw, Source text,
credentials and private artifact paths are excluded from this report.

## Interface and version contract

`node_candidate_intent.compile_candidate(intent)` is a pure function:

`node-candidate-intent-v1 -> normalized NodeCandidate`.

All Node types share one closed object shape: the existing common fields
(`primary_type`, `canonical_name`, aliases, description, reason, confidence,
independent research value, maintenance rationale, suggested parents and explicit
ownership Evidence), plus three arrays:

| Array | Entry | Authoritative field set |
| --- | --- | --- |
| boolean_properties | `{field, value}`; TRUE/FALSE lexical value | `_BOOL_FIELDS` |
| text_properties | `{field, value}`; text | `_TYPE_FIELDS - _BOOL_FIELDS - {evidence_ref}` |
| evidence_properties | `{field, value}`; existing Evidence Selection | `{evidence_ref}` |

The protocol version is bound once in the execution contract; it is not another
model-generated field on each Candidate. `_NODE_VARIANTS` selects required active
properties. Every explicitly supplied inactive property is placed losslessly in
`preserved_fields`, including FALSE, empty text and nested Evidence Selection.
Missing active properties, duplicate names, unknown fields, wrong types and
invalid lexical selections fail. No business judgment, ownership reference,
Candidate/Claim link or Evidence is invented. No values are dropped as defaults.

Claims, Matches, Relations and Source References retain the existing lexical
boundary. The output remains `normalized-extraction-analysis-record-v1` and is
admitted by the existing Evidence Binding v2, ownership, Claim linkage, Wire v3
and Native Analyzer rules. Compiler success confers no Canonical authority.
`MATERIALITY_WEIGHTED_SELECTIVE_EXTRACTION` remains unchanged; complete unique
acknowledgements do not require a Claim for every Evidence unit.

| Explicit new identity | Value |
| --- | --- |
| ProviderRecord | whole-piece-output-batch-provider-record-v5 |
| Tool schema | whole-piece-output-batch-tool-schema-v5 |
| Node intent | node-candidate-intent-v1 |
| Encoding | deepseek-output-batch-semantic-intent-encoding-v1 |
| Binding | whole-piece-output-decomposition-binding-v4 |
| Provider adapter | whole-piece-output-batch-lexical-tool-provider-v6 |
| Series / batch | whole-piece-output-series-v4 / whole-piece-output-batch-v4 |

The default binding and default ProviderRecord remain v4. New callers explicitly
select `output.INTENT_BINDING_VERSION` in `piece_input` / `contract` and
`OutputBatchProvider`, or construct the corresponding new Series. Segment payloads
then bind the v5 schema, prompt, output ceiling and compiler version. The existing
Ledger reserves the version in the Attempt and routes acceptance from that
frozen version, never from response shape. New v5 Series reject v1-v4 overrides;
old Series reject v5. Existing v1-v4 accepted or failed raw is not upgraded.
There is no new Ledger, retry engine, aggregate engine, default profile switch,
or historical recovery authorization.

## Strict Tool support and remaining risks

The generated v5 schema uses only closed objects with all properties required,
arrays, strings and enums. This matches the subset documented in the
[DeepSeek Strict Tool guide](https://api-docs.deepseek.com/guides/tool_calls/).
The existing Beta endpoint, strict function, named tool choice and disabled
thinking configuration are retained; the
[API reference](https://api-docs.deepseek.com/api/create-chat-completion/)
documents the thinking-mode restriction on named tool choice.

No real server request was made to qualify v5. Documentation and JSON Schema
validity are not proof of server acceptance or generation reliability. Removing
the Candidate `anyOf` branches moves type-dependent required-property checks to
the compiler. Property omissions, duplicates, incorrect types and unsupported
Evidence still fail locally. In particular, the latest Run16 missing-ownership
failure would remain invalid. Fake Provider success proves integration mechanics,
not research recall, semantic quality, Evidence validity rates or real success rate.

## Offline complexity measurements

Run with dev dependencies: `python scripts/measure_node_intent_complexity.py`.
The same 15 legal synthetic records cover every Node type plus mixed output.
All normalize to identical records. JSON is compact, sorted and UTF-8; timing is
the median of 40 batch repetitions on the operator host and is informational.

| Metric | v4 | v5 |
| --- | ---: | ---: |
| Full Provider Schema bytes | 12,435 | 5,938 |
| Candidate schema bytes | 8,488 | 1,991 |
| anyOf nodes / alternatives | 1 / 4 | 0 / 0 |
| Total response characters | 49,895 | 49,845 |
| Total response UTF-8 bytes | 56,197 | 56,147 |
| Normalize median microseconds / record | 3,338.483 | 3,380.373 |
| Compiler median microseconds / Candidate | n/a | 300.189 |

| Sample type | Top-level fields v4 -> v5 | All emitted object members v4 -> v5 |
| --- | --- | --- |
| Entity with explicit preserved data | 13 -> 13 | 23 -> 23 |
| Event | 16 -> 13 | 20 -> 23 |
| Theme | 15 -> 13 | 15 -> 17 |
| ResearchQuestion | 16 -> 13 | 16 -> 19 |

Schema bytes decrease by about 52.25%; Candidate schema bytes by 76.54%.
Total response bytes decrease only 0.09%. The mixed sample grows from 5,342 to
5,407 bytes, because named property entries add nested members. Thus the measured
benefit is a uniform physical shape and fewer schema alternatives, not a general
reduction in response fields/tokens or demonstrated Provider success improvement.
Compilation preserves required semantic information and adds local processing.

## Validation scope

- New compiler/diagnostic tests: **53 passed**. They cover all Node types, mixed
  order, normalized/Wire/Binding/Claim identity and downstream Analyzer equality,
  explicit false/empty/cross-type data, semantic omissions and invalid inputs,
  historical version rejection, and existing released synthetic result identities.
- Fake transport -> v5 -> compiler -> normalized record -> Evidence/ownership ->
  Wire -> existing durable Segment Ledger passes. Production remains unchanged
  and no Semantic job is created in the disposable fixture.
- Directly related regression scope: **868 passed, 3 failed** across lexical/v4,
  selective extraction, output decomposition/durability, Claim linkage, bounded
  extraction/persistence, Wire and Evidence Binding tests.
- All three failures were separately reproduced on unmodified release
  `26c3be797cbd502a6773332e014ae8a19473a349`: two old v3 fixture/default-version
  assertions in `test_selective_provider_neutral_extraction.py`, and the known
  fail-closed compatibility reason assertion in `test_source_analysis_wire.py`.
  They are not counted as passes. This is scoped validation, not a full-suite PASS.
- A fresh-process comparison against the actual released installed package found
  identical v1-v4 synthetic schemas, existing contracts, Series/Segment identities,
  payloads and results. Unchanged old core files remain untouched. No compatibility
  token for historical recovery is issued by this work.

No real Provider calls, historical mutations, Semantic registration, Production or
Current View writes, merge, release or stable activation are authorized here.
The next separately authorized stage is
`SEMANTIC_INTENT_COMPILER_RELEASE_AND_BOUNDED_LIVE_QUALIFICATION`, with finite
real samples and measurements of format acceptance, Evidence validity, material
information recall, cost and end-to-end usability.

## R1.1 — Ownership provenance and Operator wiring

Stage: `SEMANTIC_INTENT_OPERATOR_WIRING_AND_OWNERSHIP_R1`.
This section supersedes the R1 next-stage recommendation above. The original
v4/v5 schemas, prompts, normalization behavior and historical Raw remain frozen.

### Observed root cause and limits

The nine missing-ownership Candidates in the latest failed Run16 response were
examined offline against the frozen SourcePiece, Segment and authoritative
Evidence catalog. Only exact normalized canonical-name references in
`Claim.related_candidate_names` and the Candidate's explicit active/preserved
Evidence Selections count as support. Alias similarity, descriptions, proposed
parents, mentions in free text and the first assigned Evidence do not count.

| Class | Candidates |
| --- | ---: |
| Provable through explicit Candidate–Claim–Evidence relationships | 0 |
| Provable through the Candidate's own valid Evidence Selection | 0 |
| Multiple explicit Evidence sources requiring resolution | 0 |
| No explicit support relationship or own Evidence Selection | 9 |

The unsupported zero-based indices are 2, 3, 4, 5, 7, 8, 9, 10 and 11. Their
types are four Company, one Technology, two Product, one Material and one
Equipment. **Unresolved count: 9. Historical lossless repair coverage: 0/9.**
This is missing semantic provenance, not merely repeated execution metadata.
No source text, candidate names, private identifiers or credentials are published.
The diagnostic never normalized, accepted, edited or retried the historical Raw.

The minimum model input still required is an explicit relationship from a
supported Claim to the Candidate, or a valid Candidate Evidence Selection. A
Candidate need not cause a new Claim to be invented. Existing `evidence_properties`
can carry its direct support independently of Claims. Adding a scalar ownership
ID without semantic support is not a repair.

### V6 deterministic rule

V5 continues to require explicit scalar ownership. New ProviderRecord v6 removes
only the Candidate scalar `ownership_evidence_ref`; source references retain
their existing explicit ownership field. V6 has distinct schema, encoding,
prompt, adapter, binding, Series and Batch identities:

| Identity | Version |
| --- | --- |
| ProviderRecord / tool schema | v6 / v6 |
| Encoding | deepseek-output-batch-semantic-intent-encoding-v2 |
| Binding | whole-piece-output-decomposition-binding-v5 |
| Provider adapter | whole-piece-output-batch-lexical-tool-provider-v7 |
| Series / Batch | whole-piece-output-series-v5 / whole-piece-output-batch-v5 |
| Provenance | candidate-support-set-ownership-v1 |

For each Candidate, enumerate every explicit incoming Claim reference, retaining
its Claim index and reference index, and every direct Evidence property. Resolve
every Selection with `resolve_evidence_binding_v2` against the frozen catalog and
context. One invalid or foreign source rejects the whole response; a valid
alternative never masks an invalid support. Empty support also rejects the whole
response without dropping the Candidate.

Ownership is a **set-to-Segment proof**, not a chosen representative Evidence.
The full nonempty set of validated supporting Evidence must be contained in the
current Segment's assigned set. Thus multiple Evidence units are unambiguous
for execution when they all belong to that same Segment. Sources spanning
Segments are rejected. Sorted unique Evidence refs provide deterministic set
serialization; original support paths, selection values and binding hashes
remain in original relationship order. No lowest-ID, earliest-unit, majority or
first-wins Evidence is selected. No semantic source is silently discarded.

The existing Wire validator still gates all families, node semantics, references
and Evidence. Candidate/property/Claim order and explicit false/empty values are
preserved. `ownership_provenance` is persisted beside the accepted Segment result,
bound to provider-record, Series, Segment and result hashes. The existing result
artifact hash, append-only ledger record and event chain protect the proof. The
Wire and aggregate retain their existing formats; older result artifacts omit
this field and retain their exact identities. Recompiling the same frozen Raw
and inputs reproduces both result and provenance.

### Internal execution entry

`pro_a.workbench.output_qualification` provides `start`, `providers`, `advance`
and `resume` for an internal Operator. `start` accepts only explicit v5 or v6
protocol identity and a validated reason/idempotency key, then uses the normal
Source start transaction, intake/capacity checks and domain/config binding.
It grants no run-window, historical-runtime, config or Evidence bypass.

The selected contract and a stop-after-bounded qualification identity are frozen
into `runtime_json` and its digest before the Run and domain context are created.
The Runner uses that binding for SourcePiece inputs, Series, payloads and provider
adapter checks. Reconstruction uses the frozen config path and digest, frozen
CloudProfile and selected binding, then compares the entire recomputed current
runtime with the frozen runtime. Compiler and Operator source bytes are included
in the runtime code digest and compatibility dependency inventory.

`providers` reconstructs the frozen worker before calling `build_source_providers`
with its exact output binding. `advance` processes normal durable Segment work;
`resume` uses the existing fenced, call-limited bounded resume path. Both stop
before Semantic registration. Ordinary workers exclude qualification Runs, and
ordinary production intake/provider construction still defaults to v4. There
are no new Web/MCP request fields or endpoints. Read/replay of v4 stays supported;
cross-release execution still requires the existing compatibility proof and is
not silently authorized by selecting v5/v6.

### R1.1 verification

The new tests exercise synthetic PDF upload and standard Run creation through
the Operator entry, actual provider construction with Fake Transport, v5/v6
Series/schema/Attempt identity, durable acceptance, and continued processing in
a fresh subprocess. V6 also resumes through the existing bounded-only entry.
They compare frozen runtime, deterministic replay, provenance, old artifact
bytes, append-only event/result rows, and unchanged Production bytes; no Semantic
jobs are registered. They cover unsupported, forged and cross-Segment support,
wrong v5 ownership, Candidate-only support, config drift, v4 restart routing and
compiler-code identity coverage. Final test counts are recorded in the PR receipt.

The observed Run16 omission remains unresolved. Engineering routing can be
qualified offline, but this report does **not** declare the ownership root cause
fixed or claim real-provider schema/format/Evidence success rates. Real Provider
calls and Production/Current View writes remain zero; no release, merge or Stable
activation is performed. The proposed next stage remains
`SEMANTIC_INTENT_COMPILER_RELEASE_AND_BOUNDED_LIVE_QUALIFICATION`, pending an
explicit decision on the unresolved semantic-input requirement and separate
authorization for a very small number of real calls.
