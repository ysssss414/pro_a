# Extraction quality pilots: public engineering retrospective (2026-10-16)

**Status:** retrospective only; not a production qualification, Source factual certification, or authorization to run new models. This is a deliberately redacted project engineering record. Complete source materials, model requests/responses, candidate-level evidence and scoring data remain in a separate private evidence store.

## Scope and interpretation

- **S1:** an anonymized technical Q&A source used for extraction diagnostics and protocol comparisons.
- **S2:** a distinct technical research source tested by one frozen B1 request; see the scoped result and limitations below.
- Numbers below are the reported results of local qualification and controlled calls, not an external audit. "Evidence supported" means a source passage supports the **attributed source statement**; it does not establish independent real-world truth.
- The historical extraction, later offline repairs, same-range comparisons, and newer paired experiment have different denominators. Do **not** merge their scores into a single success rate.

## S1: first live extraction and frozen benchmark

| Stage | Recorded result | Interpretation |
| --- | --- | --- |
| Initial bounded extraction | 7 of 11 output batches accepted, 7 model calls, 145,902 Tokens; blocked on **SOURCE_METADATA_CONFLICT** | No review artifact or canonical admission; remaining 4 batches were never called |
| Observation diagnostics | 248 Claim observations; 140 distinct texts; 99 complete proposition groups | High duplication; observations are not all usable knowledge |
| Frozen benchmark | 84 high-priority reference items across full source; 52 belong to processed scope | Full-source recall and processed-scope recall must be reported separately |
| Original usable high-priority recall | 38/52 (73.1%) in processed scope; 38/84 (45.2%) across source | Baseline only |
| Original unique-candidate Evidence correctness | 54/100 (54%) | Byte-valid placement was not equivalent to semantic support |
| Read-only Evidence remediation | 45/52 (86.5%) processed-scope usable recall; Evidence 60/100 (60%) | Offline counterfactual on immutable old output; not proof of better generation |
| Original semantic repetition | 148/248 (59.7%) | Offline Evidence repairs did not reduce repetition |

The first-run failures included legal Evidence references attached to unrelated propositions. Subsequent forensic work classified the errors and retained all original responses and provenance. For the tested high-value scope, information detection was high; evidence association and output selectivity caused the largest loss of usability. No failed output was converted into a source of authority merely by adjusting its locator.

## S1: controlled B1 Evidence-first validation

In two selected output scopes, **B1** used an explicit evidence-first protocol and frozen source-bound Evidence selection:

| Metric | Concurrent historical v4-style control A | Evidence-first B1 |
| --- | ---: | ---: |
| All raw Claims included in scoring | 19 | 13 |
| Valid binding **and** complete semantic support | 16/19 (84.2%) | 13/13 (100%) |
| High-priority usable recall, original scoring | 11/12 | 12/12 |
| High-priority usable recall, conservative metadata scoring | 8/12 | 9/12 |
| Question-only, no research increment | 5 | 0 |
| Whole-batch exact semantic repeats in same small comparison pool | 0 | 0 |
| Recorded total Tokens | 28,234 | 24,085 |

The B1 group achieved better binding robustness and usable coverage in these scopes. **It did not prove reduced semantic duplication in the matched small repetition pool.** The B1 run used fewer Tokens but had an approximately 18.9% **higher usage-based estimated CNY charge**, because output/caching mixes differed. Estimates were not per-request settlement statements.

One control Claim had source-supported semantics but a raw selector altered an original newline, so its native binding failed. This was counted as unusable without retroactive repair. The B1 protocol kept model-authored offsets out of primary Evidence selection. B1 also retained issues with expert-versus-company attribution labels and compound Statements.

This was a small, non-blind, combined-protocol comparison, not a causal isolation of any single Prompt/schema/context factor or a demonstration of production reliability.

## S1: B2 semantic addendum and regression

B2 added three requirements to B1: (a) better attribution of expert and company statements, (b) greater proposition atomicity, and (c) separation of questions from answers. Offline fixtures passed, but one live matched sample found:

| Same-scope metric | B1 | B2 |
| --- | ---: | ---: |
| Raw Claims | 13 | 13 |
| Individual binding validity | 13/13 | 13/13 |
| Full Evidence support, conservative-to-permissive adjudication | 12–13/13 | 12–13/13 |
| High-priority usable recall, conservative-to-permissive | 9–10/11 | 9–10/11 |
| Clearly compound Claims | 5 | 5 |
| Attribution conflicts / question-only records | 0 / 0 | 0 / 0 |
| Entire native response Schema | **PASS** | **FAIL** |

B2 introduced an extra, non-contract source-metadata field; strict local validation correctly rejected the **entire** response. The field was not silently deleted and the response was not scored as a usable batch. **B2_REGRESSION** is the engineering result, while its semantic improvement remained unproven. B1 remains the **preferred experimental candidate**, not a released default.

Both groups exposed limits around context-dependent meaning and compound Claims. No prompt revision, Schema relaxation, production integration, or further paid repeat has been authorized by this retrospective.

## S2: one cross-source B1 live validation

The separate two-page benchmark remains **29 high-priority / 16 medium-priority** items. Only the frozen single-request scope of **15 high-priority / 8 medium-priority** items was tested. Context-only items were not counted as omissions.

Exactly **one** authorized inference completed, with no retries. The unmodified v7 record passed strict Schema and native Binding validation; no forbidden fields, selectors or failed Claims were removed to obtain that result.

| Frozen-scope metric | S2 B1 result |
| --- | ---: |
| All Raw Claims / semantic record groups | 13 / 13 |
| Legal primary bindings / complete source-semantic support | 13/13 / 13/13 (100%) |
| High-priority appearance / usable / metadata-conservative usable recall | 15/15 / 15/15 / 15/15 |
| Medium-priority usable recall | 8/8 |
| Wrong Primary Evidence / severe identity or ownership violations | 0 / 0 |
| Attribution conflicts / question-only records | 0 / 0 |
| Fully duplicate Claims | 0/13 |
| Partial overlap | 1 pair, involving 2 Claims |
| Clearly compound Claims | 8/13 (61.5%) |
| WHOLE_UNIT / RAW_SUBSPAN primary selections | 13 / 0 |
| Input / output / total Tokens | 9,919 / 4,169 / 14,088 |
| Cached / uncached input Tokens | 6,400 / 3,519 |
| Tokens per usable high-priority item | 939.2 |
| Usage-based estimated charge | CNY 0.040646 |

**CROSS_SOURCE_B1_PASS** applies to the frozen hard quality gates in this single scope. Atomicity had no numerical pass threshold and remains an explicit limitation, not a silently added or waived gate. Thirteen supported records cover **23 distinct frozen reference propositions**; these counts must not be confused with thirteen atomic propositions.

The full local request count was 9,877; actual input was 42 Tokens higher and remained within the bound. Whole-unit references were individually checked for meaning, attribution, quantities, temporal and conditional qualifiers. They were not credited merely because their byte ranges resolved. Explicit question context was supported by answers, rather than promoted into facts on its own.

No new fatal failure mode was observed relative to the prior B1 samples. The existing tendency to reproduce multiple independently reviewable propositions in one answer-unit Claim persisted: **8/13** clearly compound here versus **5/13** in the prior newer S1 B1 scope. Different source content and scope prevent interpreting this as a controlled regression estimate. Total usage was 309 Tokens lower than that S1 sample; estimated cost was CNY 0.007422 lower. Per-item efficiency also uses different Gold denominators and is not a causal strategy comparison.

This is one model, one request and one scope, assessed non-blindly against a reference frozen before this source's model output. Source support is not independent factual verification. Source-specific external-processing permission was accepted from an explicit user affirmation; it was not represented as independent rights-holder verification. No formal Source Run, P0/P1/P2, semantic admission or canonical write was performed.

**B1 remains experimental, not Production Ready.** Residual blockers are proposition atomicity, broader source/batch validation, and end-to-end qualification of metadata authority, review, provenance-preserving repetition handling and governed admission. An empty known-Node catalog in this pilot did not test canonical Node matching. No B2 revision, Schema relaxation, paid repeat or production integration followed this result.

## Project decisions and next acceptance steps

1. **Do not pursue full repair of the legacy S1 Run as the principal roadmap.** Preserve all original evidence, failed coverage, immutable attempts and guard semantics.
2. **Hold B2 development and repeat spending.** Do not delete forbidden output fields or dilute the native Schema to make B2 pass.
3. **Keep B1 as the experimental quality baseline.** The first distinct-source scope passed the frozen hard gates, but before production integration expand source/batch validation and address the documented atomicity and governed end-to-end qualification gaps.
4. Source metadata authority must not be established by model voting. A valid Evidence span is insufficient without statement-level semantic support; compound and cross-context Claims require explicit scrutiny.
5. A single cross-source pass is insufficient for integration. Only after broader quality and end-to-end qualification should maintainers propose narrowly scoped integration into the governed Review/Admission workflow. P0/P1/P2 Human and independent-Operator boundaries remain authoritative.
6. Draft PRs **#134** (forensic reader) and **#135** (selective candidate admission) are intentionally pending. Neither is a shortcut around quality or governance gates.

**No merging, deployment, Production writing, release activation, or additional Provider call was performed by this document archive.**

## References to private evidence (content NOT published)

The following SHA-256 values identify the **private ZIP archive bytes**, not any original Source file or its contents. They permit an authorized operator holding the original private files to verify which local artifact backs this redacted summary. A digest alone does not establish the substantive accuracy of the enclosed report.

| Local private evidence bundle | ZIP SHA-256 |
| --- | --- |
| Baseline quality assessment | df3dded078829879a1e0a888761466cab9256460b4619e6f93922ef3fb637120 |
| Offline Evidence hardening | 819b502663eb3859e6a056752b91edd5ab2d3440a4bd8144efce2156e9966c40 |
| First B1 live scope | 9aa8f93d423b1bb968e8f510784f87e624fb634d144364d81297253ea201b0ab |
| Single-Evidence B1 live scope | f3a0c6d6c0c1c28a96092da8dc7c849852addb163cd8c2d19968e0513e2c574c |
| Matched v4/B1 comparison | 0b74822a55162b52f59e10e2e3be5f78921a7d9854886ff83267067cdccf1b4e |
| B1/B2 semantic paired experiment | cb3e2c8a23919a27ba0f6b4e5e97d9ec2db92182ef954bde0052a30e6716353a |
| S2 cross-source preparation | 8d280ee09591528c7675c513a0d06d9c17e2c1c9107329b5c5180106bee372fa |

The original PDFs, proprietary prose, Gold quote lists, exact Observations, request/response payloads, system-local paths, Source identities and provider credentials are deliberately omitted from this public repository. See [Private-evidence and public engineering archive policy](./private-evidence-public-archive-policy.md).
