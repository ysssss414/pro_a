# R2_PROVIDER_NODE_VARIANT_ENCODING_V4_QUALIFICATION_R1

Baseline: `d44ce7b48dfccaf685ad0175b11e77c85d6b8824`. Offline qualification only; no merge, activation, real Provider call, or new real Run.

## Encoding and unchanged research contract

The v3 Node object required eight type fields plus eight fixed preserved slots for every primary type. Its inactive defaults and presence switches created independent opportunities for invalid output. V4 uses four mutually exclusive `anyOf` branches, discriminated by disjoint `primary_type` enums: Event, Theme, ResearchQuestion, and all remaining existing Node types. Each branch has only common fields and its active type fields. Every object is closed and all declared properties are required. There is no `oneOf`, conditional schema, discriminator keyword, or optional property.

Three required arrays encode explicitly present inactive data: `preserved_boolean_fields`, `preserved_text_fields`, and `preserved_evidence_fields`. Every entry is a closed `{field, value}` object. Names are restricted to existing `_TYPE_FIELDS`; duplicates, active fields, invalid types and invalid Evidence fail closed. Empty arrays mean absence. Explicit false and empty text remain present. Evidence is projected through the existing lexical selection converter and unchanged Evidence Binding validation. No value is inferred, discarded, moved from an illegal slot, or repaired.

The independent v4 decoder parses strictly, checks the unique branch, validates sparse preserved entries, then projects to `normalized-extraction-analysis-record-v1`. Candidate array order is retained; no type grouping, sorting, or ordinal is introduced. The non-Node families reuse unchanged lexical primitives. Wire v3, Evidence Binding v2, Claim identity, canonical expansion, materiality-weighted selective extraction and `VALIDATED_CLAIM_EVIDENCE` remain unchanged. Execution coverage still does not require a Claim per Evidence unit. Existing 24,000 / 384,000 / 16 budgets and existing lexical array limits remain unchanged; no new Claim limit is introduced.

V4 rejects duplicate canonical Candidate identities (the existing normalized-name identity) at its own entry point. Historical v3 and Wire validators are unchanged. Candidate references must still resolve within the same response; no missing Candidate is created and no invalid reference is dropped.

## Version routing

| Contract | Frozen v3, 24k | New v4 |
|---|---|---|
| Provider record | `whole-piece-output-batch-provider-record-v3` | `whole-piece-output-batch-provider-record-v4` |
| Tool schema | `whole-piece-output-batch-tool-schema-v3` | `whole-piece-output-batch-tool-schema-v4` |
| Encoding | `deepseek-output-batch-lexical-encoding-v3` | `deepseek-output-batch-lexical-encoding-v4` |
| Binding | `whole-piece-output-decomposition-binding-v2` | `whole-piece-output-decomposition-binding-v3` |
| Provider | `whole-piece-output-batch-lexical-tool-provider-v4` | `whole-piece-output-batch-lexical-tool-provider-v5` |
| Prompt / response | v3 / v3 | v4 / v4 |
| Series / Batch | v2 / v2 | v3 / v3 |

Persisted Series and Attempt identities select the decoder; response shape never selects a fallback. Series v1/v2 keep their frozen contract, schema, prompt, budget and identity. Earlier ProviderRecord v1/v2 explicit readers remain available. A v4 record cannot be used with a frozen v3 Series, and historical invalid raw is never converted to v4. New clean Runs select the new contract.

Additional changes are direct version-routing dependencies: the runtime and execution-surface inventories include the new decoder; historical Provider configuration reconstruction uses the frozen Series binding; the existing strict regeneration diagnostic is explicitly pinned to v3. Its v2 Series restriction, eligibility, one-new-attempt limit, authorization, and guidance are unchanged. No compatibility normalization rule is relaxed. Historical strict tests explicitly create their original v2/v3 fixtures.

Frozen contract digests match the released baseline byte for byte:

- Binding v1: `ba5acd58fa4fd90d2e0c854d6aafecd0652e78ec77a4bbee0073e2fd008e9e25`.
- Binding v2: `6f3fec2048ed3ac61e4266160ff84cc9fabb9c060b87bf689ce9b5356699a6ff`.

## Offline evidence

Synthetic legal v3/v4 fixtures cover all four branches, all Other types, mixed Candidate order, every legal preserved field, explicit false/empty presence, absent preserved fields, and same-response multi-Candidate references. Assertions compare normalized records and their hashes, Wire, Evidence-derived dispositions, canonical expansion, linkage and ordering. Execution identifiers intentionally differ between versioned Series; repeated projection within either version is deterministic. The test-only v3-to-v4 fixture builder accepts only already-valid synthetic v3; production has no migration or repair path.

Negative cases reject wrong branches, missing active fields, extra inactive fields, duplicate or active preserved names, invalid booleans, invalid/foreign Evidence, unknown Candidate references, duplicate Candidate identities, malformed nested values, unsupported fields, incorrect preserved types and illegal NONE Evidence. Synthetic clean-run tests exercise transport, two output batches, aggregation and ownership. Simulated server schema rejection and an old-v3 response stop after one call without fallback, continuing other Segments, or entering Semantic.

Real Run15 was read only: Attempt 1 and Attempt 2 still raise `NONDEFAULT_INACTIVE_VARIANT` through the explicit historical v3 reader. Both raw hashes, accepted result, all actual database tables and artifact inventories, Production, Current View and stable installation remain unchanged. Neither raw was reparsed as v4; no Attempt 3 was created. Raw content and private Source material are excluded from this repository.

Source qualification: **354 passed**, with **0 unresolved unexpected failures**: 37 v4 tests, 28 frozen strict-recovery tests, 143 output/ownership/linkage/capacity tests, 78 ledger/retry tests, and 68 compatibility/execution-surface tests. Previously failing iteration cases were rerun on the fixed commit and passed.

The single known baseline assertion remains separately reproduced: `test_operation_output_budget.py::test_baseline_cloud_execution_surface_fails_closed` expects `SEMANTIC_SURFACE_CHANGED`, but receives `EXECUTION_SURFACE_UNAVAILABLE:RetryCompatibilityError`; both paths reject execution. It is not counted as a passing test or a new regression.

The final Draft-head packaging gate builds from an exact Git-tree checkout, compares every tracked blob and all wheel/installed Python and SQL bytes, installs only into an isolated environment, checks dependencies and compilation, and runs installed-only smoke with checkout access denied plus a no-Git identity check. It repeats the v4 suite and frozen strict-recovery suite against the installed wheel. Final-head build/smoke/privacy results and the wheel digest accompany the Draft PR receipt. Publication is blocked unless these gates pass. Privacy scanning includes the public diff, wheel, receipts, credentials and private historical raw/source fragments.

## Complexity comparison

Compact UTF-8 JSON measurements use the same legal mixed synthetic research record.

| Measure | v3 | v4 |
|---|---:|---:|
| Tool parameters schema bytes | 7,814 | 12,435 |
| Required Event fields | 19 | 16 |
| Required Theme fields | 19 | 15 |
| Required ResearchQuestion fields | 19 | 16 |
| Required Other fields | 19 | 13 |
| Unrelated required primary type slots | 5 / 6 / 5 / 8 | **0 for every branch** |
| Preserved representation when absent | 8 fixed present/value slots | 3 empty arrays |
| Synthetic record bytes | 7,657 | 5,342 |

The schema grows because each branch repeats its closed common structure. This trades schema size for fewer unrelated response obligations. Projection remains linear in record size with four constant branch checks. Explicit presence and unchanged downstream validation prevent semantic loss; shorter responses alone are not the acceptance criterion.

## Provider boundary and stop

DeepSeek documents `anyOf`, closed objects, and all properties required in its strict tool subset: [official Tool Calls documentation](https://api-docs.deepseek.com/guides/tool_calls/). Local schema checks cover that subset. **LIVE_SERVER_ACCEPTANCE = NOT_TESTED.** Local and simulated tests do not establish online schema acceptance or improved live generation accuracy.

Real Provider calls in this stage: **0**. Run13/14/15 call counts remain **4 / 3 / 3**. Schema12, real Run states, stable runtime, Review, Semantic, Production and Current View are unchanged. No cleanup was performed. PR106 remains Draft and unmerged.

Deliver only an open Draft PR, then STOP. Any later release/live work requires the separate stage `R2_PROVIDER_NODE_VARIANT_ENCODING_V4_RELEASE_AND_CLEAN_RUN16_R1`. Its first live request must establish server acceptance of the released schema; rejection must stop with request/response audit retained, without fallback or relaxing strictness. No Run16 is created here.
