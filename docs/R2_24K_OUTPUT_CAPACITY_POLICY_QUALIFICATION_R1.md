# R2 24k output capacity policy qualification

Stage: `R2_24K_OUTPUT_CAPACITY_POLICY_QUALIFICATION_R1`.
Baseline: released/main `3c72ae2380d81712fb134195b601b97efd33ded8`.
This candidate requires a new processing Run. Qualification is offline; it does
not merge, activate, create a real Run, or call a real provider.

## Application policy

New R2 output batches use a 24,000-token maximum, with 16 initial Evidence refs.
The Series cumulative liability limit remains 384,000 tokens, independent of
the per-call ceiling. The limits of 32 provider calls, four subdivision levels,
and 16 leaf Segments remain unchanged. The cap is a maximum, not an output target.
There is no automatic escalation, global batch reduction, or Claim count cap.

Deterministic midpoint subdivision retains the parent's actual or reserved
liability and requires budget for both children using their frozen ceilings.
Reservation checks enforce both call count and cumulative liability. Exhausted
subdivision capacity fails closed with
`EXTRACTION_DENSITY_EXCEEDS_BOUNDED_POLICY`; an over-budget reservation raises
`SERIES_BUDGET_EXCEEDED`. A worst-case 31-call tree need not fit the risk budget.

## Execution identity and historical compatibility

| Capacity identity | Historical 12k | New 24k |
| --- | --- | --- |
| Output budget | operation-output-budget-v1 | operation-output-budget-v2 |
| Input binding | whole-piece-output-decomposition-binding-v1 | whole-piece-output-decomposition-binding-v2 |
| Series | whole-piece-output-series-v1 | whole-piece-output-series-v2 |
| Segment | whole-piece-output-batch-v1 | whole-piece-output-batch-v2 |
| Provider adapter | whole-piece-output-batch-lexical-tool-provider-v3 | whole-piece-output-batch-lexical-tool-provider-v4 |

Historical input restoration, Segment validation, request reconstruction, raw
outcome interpretation, and liability accounting select the frozen version.
The new adapter rejects a historical 12k request before dispatch. Historical
Runs require explicit reprocessing into a new Run to use 24k; identity fields
and frozen artifacts are never rewritten.

The retired `SOURCE_ANALYSIS_PIECE` and bounded-extraction-v1 families retain
their original 12k contracts and `operation-output-budget-v1`. The current R2
output-batch execution uses the new policy. This preserves exact historical
Cloud contracts without changing the unrelated Semantic operation budget.

Research semantics are unchanged: materiality-weighted selective extraction,
normalized AnalysisRecord, Evidence Binding, Wire, Claim identity and semantics,
Analyzer, provider record, encoding, tool schema, and prompt objectives.
Changing capacity changes execution identity for the same Source and Evidence;
it does not change those Source/Evidence identities or research semantics.
Database schema remains 12, with no SQL or migration changes.

## Provider capability

The DeepSeek adapter freezes a qualified output capability of 393,216 tokens.
Official documentation checked on 2026-10-08 supports `deepseek-flash` and a
384K maximum output range. The application requests exactly 24,000 tokens.
Capability remains adapter configuration; the provider-neutral research core
does not contain the provider maximum. An insufficient qualified capability
raises `PROVIDER_OUTPUT_CAPABILITY_INSUFFICIENT`; it never downgrades the request.
No online `/models` dependency is introduced.

Sources: [Create chat completion](https://api-docs.deepseek.com/api/create-chat-completion/),
[Models and pricing](https://api-docs.deepseek.com/quick_start/pricing/).
Thinking disabled, strict tool encoding, and existing retry behavior remain.

## Qualification evidence

The capacity suite covers exact configuration/request boundaries at 23,999,
24,000, and 24,001; insufficient adapter capability; valid 18k tool output;
24k `length` truncation without partial parsing; and malformed 13k tool output
classified as malformed provider JSON rather than capacity exhaustion.

Both pure accounting and durable reservation tests cover 360k, exactly 384k,
and atomic rejection above 384k. A 24k truncated parent retains liability when
splitting into two children; insufficient budget rejects the subdivision.

Golden synthetic vectors captured from the released baseline verify exact
historical Series, Segment, frozen input, payload, and request hashes. New
identities are deterministic and differ for the same immutable Source, while
Source, Evidence and research contract identities agree. A forged in-place
binding upgrade is rejected.

Required regression scopes include output decomposition, bounded extraction
and persistence, truncation recovery, bounded-only resume, provider configuration,
operation budgets, retry and cross-release compatibility, R2 provider neutrality,
qualification run-window bypass, resources, and repository identity. Build
qualification uses an exact Git commit tree, Python/SQL byte comparisons against
the wheel and installation, installed-only smoke with checkout access denied,
no-Git checks, and a private-fragment/credential scan. Concrete local counts,
commit and wheel hashes are recorded in the sanitized stage receipt.

Runtime `12000` classification: the named legacy capacity constant is historical
output policy; the community-material character limit is unrelated. Historical
tests and raw expectations retain 12k. Current output requests and accounting
use contract or frozen Segment ceilings instead of scattered numeric literals.

## Run14 and release boundary

Run14 remains a `LIVE_CAPACITY_VALIDATION_RUN`: a 16-ref parent and its explicit
8-ref child each reached 12k with `finish_reason=length`. Run14 has three provider
calls; Run13 has four. This stage preserves their rows and private artifacts,
production, Current View, Review and Semantic state. It performs no Run14 8-to-4
recovery and no in-place 24k upgrade. Both historical truncations remain truncated.

After qualification and Draft PR creation, stop. The next separately authorized
stage is `R2_24K_OUTPUT_CAPACITY_RELEASE_AND_CLEAN_RUN15_R1`: release first, then
explicit qualification-only reprocess of the immutable Source into a clean Run.
Actual Run IDs remain system-generated. Production's 3/24h guard and the
qualification-only bypass are unchanged.
