# WHOLE_PIECE_LEXICAL_TOOL_PROVIDER_CONTRACT_R1

Whole-piece Source Analysis now receives closed lexical function arguments and
validates them locally before converting to Wire V3. This addresses the two
Run #9 defect classes: missing selector occurrence and non-boolean candidate
research-value judgments. Run #9 remains a blocked historical v1 run; its raw
output is neither repaired nor reinterpreted.

DeepSeek strict Tool Calls are **FORMAT_COMPLIANCE_ASSIST**. The **LOCAL**
validator owns mechanical acceptance. Previous Responses schema and full strict
schema enforcement failures remain frozen, and full provider enforcement remains
**NOT_TRUSTED**. This implementation phase makes **zero real provider calls**.

## Contract and transport

| Surface | Identity |
| --- | --- |
| ProviderRecord | `whole-piece-source-analysis-provider-record-v1` |
| Tool schema | `whole-piece-source-analysis-tool-schema-v1` |
| Prompt | `whole-piece-lexical-tool-source-analysis-prompt-v1` |
| Adapter | `whole-piece-lexical-tool-source-analysis-adapter-v1` |
| Response | `whole-piece-lexical-tool-source-analysis-response-v1` |
| Wire | `source-analysis-wire-v3` |
| Evidence Binding | `source-analysis-evidence-binding-v2` |
| Expander | `source-analysis-wire-expander-v2` |

The transport uses the qualified DeepSeek Beta Chat Completions endpoint and
`deepseek-flash`, with thinking disabled, non-streaming output, a single strict
`emit_source_analysis` function and forced named tool choice. The output budget
remains 12000; timeout retains the frozen CloudJob value. Redirects, automatic
retries and fallback protocols are disabled. More than one choice/tool call,
the wrong function, absent arguments or non-string arguments fail closed.
Assistant text is never joined to the tool arguments. Reasoning content is not
accessed or persisted.

Every ProviderRecord root and nested object is closed and all-required. The
root contains metadata, Claims, matches, candidates, relations and references.
Schemas derive enums from authoritative constants. Only object, array, string
and enum-string features are used; numeric schema constraints are not relied on.
Local validation repeats shape checks and enforces the unchanged 100-Claim and
100-candidate bounds before conversion.

## Exact lexical and sentinel rules

| Value | Local rule |
| --- | --- |
| Boolean | Exactly `TRUE` or `FALSE`; no case folding, trimming or coercion |
| Confidence | ASCII decimal, no leading zeros except zero itself; no exponent or padding; exact Decimal range [0,1]; integer spellings preserve integers, decimal spellings preserve floats; negative spelling only for decimal signed zero; reject underflow to zero or rounding into one; no clipping |
| Occurrence | `[1-9][0-9]*`, then exact positive integer; no inferred occurrence |
| structured_json | Strict JSON object string; reject duplicate keys, malformed Unicode and nonfinite values; preserve nested JSON types and values |
| Whole Evidence | Nonempty ref, `WHOLE_UNIT`, empty selector, occurrence string `1`; produces only Wire evidence_ref |
| Subspan | Nonempty ref and selector, exact mode and explicit positive occurrence; unchanged binder resolves actual matches |
| Inactive Evidence | Empty ref, `NONE`, empty selector, occurrence string `1`; produces no Wire Evidence |

`NONE` is permitted only in inactive candidate/preserved slots. Claims and
matches cannot use it; active Event Evidence cannot use it. RAW selectors are
never normalized by this converter, and no occurrence is guessed. The prompt
prefers literal RAW selection; whole-unit fallback is allowed only when that
unit directly supports the object.

All 14 current Node Types are represented. Event, Theme and ResearchQuestion
fields have fixed slots; the primary type alone selects the active fields.
Inactive slots must contain exact empty/FALSE/NONE sentinels. Non-default
inactive content fails rather than being discarded.

Wire's preserved off-type fields remain representable. Every `_TYPE_FIELDS`
member has a fixed `{present, value}` slot. A false presence requires the exact
empty default. True presence projects the unchanged value into Wire
`preserved_fields`; active-type fields are forbidden there. Evidence values use
the same selector structure and unchanged binder. Explicit false/empty off-type
values are preserved when present, without confusing absence with supplied data.

Empty optional text/array fields remain explicit in Wire. Thirteen individually
tested optional fields produce exactly the same canonical defaults when omitted:
metadata author/organization/summary; Claim related_node_ids,
related_candidate_names and assumption; match reason; candidate aliases,
suggested_parent_node_ids, description and reason; relation reason; reference
note. No sentinel is applied to required semantic content.

## Durability and compatibility

The order remains frozen request → durable dispatch → provider → private exact
function.arguments → local JSON/record validation → deterministic Wire
conversion → unchanged Wire/Evidence expansion → immutable CloudJob result.
The private tool-raw envelope carries only the exact arguments and allowlisted
metadata. SQL/events contain hashes and linkage, never private tool arguments.
Schema12 is unchanged.

The complete parameters schema, tool name, strict flag, versions and SHA enter
the operation/runtime identity. The prompt bundle includes the tool-schema SHA.
Processing contexts inherit those identities; Stage7.2C includes the new pure
converter module in its protected execution surface. Raw recovery compares the
entire frozen operation identity and immutable request/artifact binding before
local replay, and never recalls the provider. Dispatch without durable raw
retains RECOVERY_REQUIRED.

CloudJob success still means structural/provenance acceptance. The Run remains
EXTRACTION_PROCESSING until all pieces complete and native Analyzer replay
reaches SEMANTIC_INPUT_READY. Native candidate/relation rejection remains
authoritative and is compared exactly against the canonical fixture path.
Permanent Claim identity, Claim ordering and semantic rules are unchanged.

The 4k planner, full-piece context/catalogs, one extraction call per piece,
all-piece replay timing, semantic decomposition, logical-job ceiling and Human
Review remain unchanged. General historical Wire capability is unchanged.
Runs #1–#9 remain readable; old Run #8/#9 read projections are checked exactly,
and both execution surfaces are incompatible with the new runtime.

## Qualification evidence

The companion `whole_piece_lexical_tool_provider_contract_r1_receipt.json`
records final regression counts, baseline/implementation provenance, tool schema
SHA, wheel SHA, build checks, request/output benchmarks and real-state guards.
Qualification uses synthetic tool responses and disposable Workbenches; real
SourcePiece requests are measured offline without publishing their content.

All-required output has a material size cost. Dense and mixed benchmarks must
be read together with the receipt; character/byte counts are not token estimates
and do not establish live fit. The 12000 output limit is unchanged.

`OUTPUT_DECOMPOSITION_REQUIRED = UNKNOWN_UNTIL_LIVE`

After qualified Draft PR creation, stop. Release activation and live Run #10
belong to `LEXICAL_TOOL_RELEASE_AND_LIVE_RUN10_VALIDATION` and require separate
authorization. This PR must not activate stable or create Run #10.
