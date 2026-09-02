# Phase 3C - Controlled Live Corpus Expansion Pilot

Status: **IN PROGRESS - Pilot #2 Gate A complete; Pilot #2 Human Extraction Review remains gated**

Phase 3C introduces a pilot-safe path for the first real corpus expansion. It is deliberately separate from the legacy `IngestionPipeline.process_file` path because legacy ingestion continues after extraction into Source/Node links, Claim/Node links, Node and Relation Proposals, historical Claim comparison, impacts, Current View Proposals, Knowledge Gaps, Research Questions, and IMA sync.

## Architecture

The Stage 1 path is:

```text
explicit Source file
    -> Phase 3A parser and diagnostics
    -> current frozen Analyzer and configured real LLM
    -> non-canonical extraction bundle
    -> Human Extraction Review draft
    -> STOP
```

The Analyzer runs against an isolated backup of the configured Production SQLite database so its existing Node/Alias matching context is preserved without opening Production for writes. Stage 1 does not initialize or call the legacy ingestion, propagation, proposal, impact-recovery, or IMA managers. Node matches, Node candidates, Relation candidates, and rejected outputs are retained as `OBSERVATIONAL_NON_CANONICAL` data only.

The extraction bundle is `phase3c_extraction_bundle` schema version `1` with status `EXTRACTED_REVIEW_REQUIRED`. It stores Source identity, SHA-256, parser diagnostics, proposed metadata, Claims, Evidence excerpts and locators, Analyzer observations, and available model usage. It never stores the full parsed Source text or raw LLM responses. Proposed Source and Claim IDs are generated once and remain frozen.

## Extract-once / review / apply contract

The Human Extraction Review is `phase3c_extraction_review` schema version `1`. It is initially `DRAFT`, has `PENDING` metadata approval, and has `PENDING` decision for every Claim. Its single `extraction_bundle_sha256` binds the review to the exact extraction bundle. Review may change only the limited Source metadata fields `title`, `source_rank`, `origin_type`, `author`, `organization`, and `publication_time`.

Claim content is immutable during review. Decisions are limited to:

- `KEEP`: accept only when `evidence_validated` is exactly true;
- `DROP`: do not insert the Claim;
- `KEEP_NEEDS_REVIEW`: retain the Claim with canonical status `needs_review`.

Future apply consumes the exact READY review and exact bound bundle. It never reruns the LLM, Node matching, Candidate extraction, Relation extraction, historical comparison, impacts, or IMA. Apply is fail-closed for the configured Production database and is tested only against an explicitly supplied isolated Production copy.

## Controlled apply authority

The future apply path uses the existing archive directory layout but copies the user Source file rather than moving or deleting it. The filesystem/SQLite boundary is explicit: archive copy failure produces zero DB mutation; a newly created unreferenced archive copy is cleaned up if the DB transaction fails; a receipt failure after commit reports `CORPUS_APPLY_COMMITTED_RECEIPT_FAILED` and does not claim rollback.

The SQLite authorizer permits only the required `INSERT` operations on `sources`, `claims`, and `processing_jobs`, plus the narrow processing-job update action. It denies Node, Alias, Relation, link, Proposal, View, Gap, Research Question, Impact, side-effect, and IMA table writes. Exact successful replay is idempotent; a same-SHA mismatch is `SOURCE_APPLY_CONFLICT`.

## Stage 1 TGV pilot

This pilot is limited to the explicitly provided `TGV玻璃专家交流.pdf` and runs with `analysis_mode=deep` using the existing configured model, prompt, Analyzer, retry, and validation contracts. `光互连研究方法与框架20260819.pdf` is intentionally **NOT RUN** and remains reserved for a later noisy-transcript robustness pilot.

Runtime artifacts are written below the gitignored `workspace/phase3c/` directory:

```text
extraction_bundle.json
extraction_review_draft.json
stage1_review.md
stage1_metrics.json
extraction_bundle_stage1_1_rebound.json
extraction_review_stage1_1_draft.json
stage1_1_review.md
stage1_1_metrics.json
stage1_2_human_decisions.json
extraction_review_stage1_2_ready.json
stage1_2_review.md
stage1_2_metrics.json
stage1_3_diagnostic_decisions.json
stage1_3_evidence_scope_diagnostic.json
stage1_3_evidence_scope_report.md
stage1_3_metrics.json
stage1_4_evidence_contract_v2.json
stage1_4_review_simulation.md
stage1_4_metrics.json
evidence_contract_v2_draft.json
evidence_review_surface.md
pilot2_metrics.json
pilot1_vs_pilot2_pre_review_comparison.json
pilot1_vs_pilot2_pre_review_comparison.md
```

The Markdown review is the human handoff surface. It includes Source summary, parse quality, model/call summary, Claim Evidence excerpts and page locators, observational Node and Relation output counts, rejected output counts, and `PENDING` review decisions. Metrics report Claim and locator counts, Node/Relation observations, and only token values actually exposed by the LLM instrumentation; otherwise token fields are `NOT_AVAILABLE`.

No transcript wording is automatically corrected. Deterministic QA may flag replacement characters, ambiguous or unresolved locators, partial parsing, `needs_review` Claims, and the need to inspect names, technical terms, dates, numbers, and changing statements against the PDF text layer. These are human review flags, not factual corrections.

## Stage 1 acceptance results - 2026-08-28

The single authorized TGV run passed. The PDF had 8 pages, 8 non-empty parsed units, no parse errors, and source SHA-256 `387d641f2e00c969b3f5d037f0f53b06bf537ac394271bb8d33ced6275b21376`. The configured request model was `deepseek-chat`; the response model was `deepseek-v4-flash`; instrumentation recorded 4 LLM calls, 86,442 prompt tokens, 52,739 completion tokens, and 139,181 total tokens.

The bundle contains 53 Claims: 7 Evidence-valid and 46 `needs_review`. Deterministic locators were resolved for 7 Claims, ambiguous for 0, and unresolved for 46. Analyzer observations retained 6 existing Node matches, 1 Node candidate (quality-eligible), 0 accepted Relation candidates, and 4 rejected Relation candidates. All Evidence locator checks and the no-full-Source-text bundle check passed. Review status remains `DRAFT` with all Claim decisions `PENDING`.

The live Production DB remained byte-identical: pre/post SHA-256 was `581978e1c587b065a6eef9c980013af3de1a9e8a8781857385404c9f61105250`; all 19 table counts were unchanged; integrity was `ok`; and foreign-key violations were `0`. Production apply was tested only on an isolated copy. IMA calls and writes were `0`; the second PDF was not run. The run remains `PHASE3C_STAGE1_COMPLETE = true` and `PHASE3C_COMPLETE = false`.

## Stage 1.1 Evidence locator binding repair - 2026-08-31

Stage 1.1 is a deterministic replay over the preserved `extraction_bundle.json` and the same Source PDF. It does not rerun extraction, prompts, the Analyzer, an LLM, Node/Relation matching, the legacy pipeline, Production apply, governance writers, or IMA. The original extraction bundle is an immutable input; the repaired state is written to separately named Stage 1.1 artifacts.

The root cause was PDF text-layout variance, not a general evidence-quality failure. `pypdf` introduced page-line whitespace between Han text and ASCII terms, before punctuation and parentheses, and inside the line-wrapped numeric range `12-15`. The original locator collapsed whitespace to one space, so these layout artifacts still prevented exact page-substring matching. In one case the model-carried page pointer was one page late even though the Evidence text exactly matched another page after safe layout normalization. Two other excerpts genuinely span adjacent page boundaries, so no single `PAGE:n` contains the full excerpt.

The resolver hierarchy is fail-closed:

1. verify a strict `[[PAGE:n]]` provenance pointer against that page by exact comparison;
2. search every page by raw exact substring;
3. search every page by existing canonical exact substring;
4. search every page by PDF-normalized exact substring;
5. return `ambiguous` if the same comparison copy matches multiple pages, or `unresolved` if no single page contains it.

A provenance mismatch never forces a locator; it falls through to global exact search and remains recorded in locator metadata. An excerpt found only across two adjacent pages is labeled `cross_page_span` and remains unresolved rather than inventing a single-page locator.

Normalization is limited to transient comparison copies. It applies Unicode NFKC, Markdown unescape, whitespace collapse, removal of layout whitespace adjacent to Han characters, whitespace normalization around an existing ASCII hyphen, conservative Chinese/ASCII punctuation equivalence, removal of layout whitespace next to punctuation/parentheses, and terminal sentence-punctuation tolerance. Raw Claim/Evidence text, pointers, metadata, Claim IDs, Node/Relation observations and candidate IDs are never rewritten. The resolver does not use fuzzy distance, token similarity, embeddings, semantic matching, paraphrase acceptance, or LLM judgment.

Replay command:

```powershell
python scripts/phase3c_corpus_pilot.py --config config.toml rebind-stage1_1 --bundle workspace/phase3c/PILOT_20260828_C963D115/extraction_bundle.json --source-file "<same TGV Source PDF>" --output-dir workspace/phase3c/PILOT_20260828_C963D115
```

The before/after result was:

| Metric | Stage 1 | Stage 1.1 |
|---|---:|---:|
| Claims | 53 | 53 |
| Evidence-valid | 7 | 51 |
| `needs_review` | 46 | 2 |
| Locator resolved | 7 | 51 |
| Locator ambiguous | 0 | 0 |
| Locator unresolved | 46 | 2 |
| LLM calls added | - | 0 |

The 48/53 resolution target was met. Match methods were 4 provenance raw exact, 32 provenance PDF-normalized exact, 3 global raw exact, and 12 global PDF-normalized exact. The remaining Claims `CLM_20260828_7AD540A4` and `CLM_20260828_827D8C7C` each match only across adjacent page pairs (`PAGE:3`/`PAGE:4` and `PAGE:7`/`PAGE:8`); both remain Evidence-unvalidated and `needs_review`.

The Stage 1.1 draft is bound to the exact rebound bundle and all human decisions remain `PENDING`. Claim IDs, raw Claim content, and all observational Node/Relation payloads are unchanged. Replay LLM calls and added tokens were `0`. The original Stage 1 extraction usage remains recorded as 4 calls and 86,442 / 52,739 / 139,181 prompt / completion / total tokens. The original bundle remained byte-identical. Production pre/post SHA-256 remained `581978e1c587b065a6eef9c980013af3de1a9e8a8781857385404c9f61105250`, all 19 table counts were unchanged, integrity was `ok`, and foreign-key violations were `0`. IMA and governance writes were `0`; the second PDF and Production/IMA apply gates remain untouched.

## Stage 1.2 Human Extraction Review closure - 2026-08-31

Stage 1.2 reviewed all 53 Claim/Evidence pairs against the immutable Stage 1.1 rebound bundle and the eight rendered PDF pages. It reused review schema v1 decisions only: `KEEP`, `DROP`, and `KEEP_NEEDS_REVIEW`. The contract has no safe corrected-Claim or correction-history representation, so material compound-Claim, scope, subject, object, certainty, and speaker-attribution defects were `DROP`; no Claim or Evidence text was edited.

The completed result is 34 `KEEP`, 17 `DROP`, 2 `KEEP_NEEDS_REVIEW`, and 0 `PENDING`. The two retained review-required Claims are the known exact adjacent-page spans: `CLM_20260828_7AD540A4` on `PAGE:3`/`PAGE:4` and `CLM_20260828_827D8C7C` on `PAGE:7`/`PAGE:8`. Their locator status remains `cross_page_span`; no single-page locator was invented. Every decision has an explicit rationale, and the READY artifact remains bound to the exact Stage 1.1 bundle.

Confidence was audited but not changed. Analyzer confidence is the formal validation-gated value: failed Evidence location sets it to `0.0`, while the original extraction value remains in `validation.model_confidence`. Confidence is not a schema-v1 review admission field, and Claim content including confidence is immutable during review. The 46 formal zero-confidence values therefore remain conservative and auditable; no scores were fabricated or restored.

Source metadata (`TGV玻璃专家交流.pdf`, `UNRANKED`, `unknown`, empty author/organization/publication time) is explicitly accepted as incomplete. The controlled apply contract can preserve these empty/default values, so no metadata was inferred. Node and Relation observations remain non-canonical and unadjudicated.

The review is complete but not Production-apply-ready. The Stage 1.2 artifact records `production_apply_ready=false`, and review validation blocks preview/apply while either retained Claim lacks a single deterministic PAGE locator. Resolving that narrow Evidence-contract blocker, or explicitly dropping those Claims in a later human decision, requires a separate gate. Stage 1.2 made 0 LLM, Production, IMA, propagation, legacy-pipeline, or governance calls/writes. Production remained byte-identical at SHA-256 `581978e1c587b065a6eef9c980013af3de1a9e8a8781857385404c9f61105250`, integrity `ok`, and zero foreign-key violations.

## Stage 1.3 Evidence scope and Claim atomicity diagnostic - 2026-08-31

Stage 1.3 diagnoses the 17 Stage 1.2 `DROP` Claims without changing their decisions. It distinguishes genuine semantic extraction failures from false rejection caused by an evidence excerpt that omits an immediately adjacent subject, object, antecedent, or scope. The immutable extracted Evidence remains separate from diagnostic-only supporting context. No longer excerpt silently replaces it.

The bounded-context policy permits the same parsed page and a 500-character normalized radius around the located Evidence. An adjacent page is permitted only at the immediate page boundary. Every selected context span must bind deterministically to its declared page; distant pages, corpus-wide search, embeddings, external knowledge, and semantic retrieval are forbidden. Semantic classifications are explicit local decision inputs; runtime code only validates bindings, coverage, taxonomy consistency, immutability, and deterministic aggregation.

All 17 DROP Claims were classified. Primary reasons are 3 `TRUE_OVERREACH`, 11 `CONTEXT_INSUFFICIENT`, 1 `ATTRIBUTION_ERROR`, 1 `CONDITIONALITY_LOSS`, 1 `SCOPE_ERROR`, and 0 `OTHER`. Diagnostic dispositions are 4 `GENUINE_EXTRACTION_FAILURE`, 11 `RECOVERABLE_WITH_BOUNDED_CONTEXT`, 1 `ATTRIBUTION_FAILURE`, 1 `CONDITIONALITY_FAILURE`, and 0 `UNRESOLVED`. Seven Claims have an independent atomicity issue. A recoverable diagnostic does not change `DROP` to `KEEP` and does not make the Claim Production-ready.

The strict current-contract KEEP rate is 34/53 (64.15%). After counting the 11 bounded-context recoverable Claims and the 2 verified semantically complete cross-page Claims, the context-adjusted semantically supportable rate is 47/53 (88.68%). The remaining semantic extraction failure rate is 6/53 (11.32%). These rates deliberately separate current contract acceptance from underlying semantic extraction quality.

Both cross-page Claims were verified against rendered pages and parsed text. `CLM_20260828_7AD540A4` is an exact ordered span across `PAGE:3`/`PAGE:4`; `CLM_20260828_827D8C7C` is an exact ordered span across `PAGE:7`/`PAGE:8`. Both have complete semantic support and retain `KEEP_NEEDS_REVIEW`. No single-page locator was forced.

Pilot #1 does not support keeping Option A (one excerpt / one PAGE) as the sole representation: it caused 11 bounded-context false rejections and cannot represent the 2 exact cross-page quotations. The minimum Stage 1.4 design should combine Option B (immutable excerpt plus bounded supporting context and context locators) with Option C (ordered exact Evidence spans for adjacent-page quotations). This is a recommendation only; Stage 1.3 does not alter the canonical Evidence or Production schema.

A narrow extraction-prompt change is also recommended for genuine failures only: Claim atomicity and unsupported-clause control, attribution preservation, conditional-branch preservation, and prevention of unrecoverable scope invention. A broad prompt rewrite is not supported because most DROP Claims were evidence-scope failures. The next gate is `Stage 1.4 Evidence Contract + Extraction Prompt Minimal Repair`; Pilot #2 remains unexecuted until that separate gate is authorized.

Stage 1.2 decisions, stable Claim IDs, raw Claim text, and raw Evidence remained unchanged. Stage 1.3 added 0 LLM/DeepSeek calls and invoked no Production write, schema change, IMA, propagation, legacy pipeline, or governance action. Production remained byte-identical with integrity `ok`, zero foreign-key violations, and unchanged table counts.

## Stage 1.4 Evidence Support Contract v2 and prompt repair - 2026-08-31

Stage 1.4 implements Evidence Support Contract v2 only in Phase 3C replay and review artifacts. It leaves the original Evidence excerpt immutable, supplements it with the minimum deterministic bounded context when needed, and represents exact adjacent-page support as independently located ordered spans. Context is limited to the Stage 1.3 same-page or immediate-boundary 500-character policy; it cannot use distant retrieval, embeddings, an LLM, external knowledge, or source-title inference. Cross-page support preserves each page locator and exact span text and never creates a fake aggregate `PAGE` locator.

The deterministic replay evaluated all 53 Pilot #1 Claims without changing Stage 1.2 history. Results were 47 `SUPPORTED`, 6 `UNSUPPORTED`, and 0 `BLOCKED`: 34 `EXCERPT_ONLY`, 11 `BOUNDED_CONTEXT`, 2 `ORDERED_SPANS`, and 6 `NONE`. All 11 context-recoverable Claims became representable, both known cross-page Claims became representable, and all 6 semantic failures remained unsupported. The v2 support rate is 47/53 (88.68%); 13 Claims require expanded evidence review, including 2 cross-page reviews.

The extraction prompt received only four failure-driven clarifications: Claim atomicity and unsupported-clause control, attribution preservation, conditional-branch preservation, and scope-invention prevention. Deterministic prompt fixtures validate those instructions; no LLM or DeepSeek call and no TGV or Pilot #2 extraction was run. This stage does not change the canonical Claim/Evidence schema, Production database or APIs, and it performs no Production, IMA, propagation, legacy-pipeline, or governance write. Evidence Contract v2 remains an artifact-level simulation and is not a Production admission contract. The next gate is `Pilot #2 Real Extraction Authorization`.

## Pilot #2 independent real extraction - 2026-08-31

The single authorized Pilot #2 run processed `光互连研究方法与框架20260819.pdf` as `PILOT_20260831_DEA82C1F`. The 11-page PDF produced 11 non-empty parsed units, no parse errors, and 9,964 extracted non-whitespace characters. The Stage 1.4 prompt was frozen before extraction at SHA-256 `a9c639085a36217d96edcef2a4637ecfe19d215559d25c3c81c03998e26c3c80`. One logical `deepseek-chat` call completed with response model `deepseek-v4-flash`, using 25,123 prompt, 14,659 completion, and 39,782 total tokens.

The non-canonical bundle contains 29 Claims. Deterministic locator replay and Evidence Contract v2 mechanics bound 20 Claims to one page and 2 Claims to exact ordered adjacent-page spans (`PAGE:8`/`PAGE:9` and `PAGE:10`/`PAGE:11`); 0 are ambiguous and 7 remain unresolved. Bounded local context candidates are available for the 20 single-page Claims. All 29 Human decisions remain `PENDING`; no semantic `SUPPORTED`/`UNSUPPORTED` decision or KEEP/DROP review was performed.

The pre-review comparison is mechanics-and-economics only and makes no quality verdict. Pilot #2 semantic acceptance, failure, atomicity, attribution, conditionality, scope, and review-burden metrics remain `PENDING_HUMAN_REVIEW`. Analyzer Node/Relation outputs remain observational and non-canonical. Production stayed byte-identical, and no Production, IMA, propagation, legacy-pipeline, or governance action ran.

## Pilot #2 Gate A — Evidence Quote Fidelity & Locator Triage - 2026-08-31

Gate A deterministically audited all 29 Claims without rerunning DeepSeek, changing the prompt, changing raw Claim/Evidence content, or making any Human KEEP/DROP decision. The fidelity result is 1 `EXACT_SOURCE_MATCH`, 19 `LAYOUT_NORMALIZED_EXACT_MATCH`, 2 `EXACT_ORDERED_CROSS_PAGE_SPAN`, 0 `PROVENANCE_MISMATCH_RECOVERED`, 7 `QUOTE_DRIFT`, and 0 `UNRESOLVED_SOURCE_BINDING`. The deterministic bound remains 22/29 (75.86%); the 7 unresolved items are all explained as quote drift with no mechanical-only recovery. The quote contract issue flag is true, and the narrow repair category recommended is `evidence_quote_verbatim_preservation`; this is a Gate A recommendation only and has not changed the prompt.

The two cross-page Claims were reconfirmed as exact ordered spans: `CLM_20260831_89CE1154` on `PAGE:8`/`PAGE:9` and `CLM_20260831_B1769E98` on `PAGE:10`/`PAGE:11`. All Human decisions remain `PENDING`, raw Claim/Evidence/IDs and prior artifacts remain unchanged, and the next gate is `Pilot #2 Human Extraction Review`.

## Pilot #2 Human Extraction Review and generalization evaluation - 2026-08-31

The formal two-axis review closed all 29 decisions: 5 `KEEP`, 10 `DROP`, 14 `KEEP_NEEDS_REVIEW`, and 0 `PENDING`. Semantic support is 19 `SUPPORTED`, 10 `UNSUPPORTED`, and 0 `AMBIGUOUS`, for a 65.52% support rate and 34.48% true semantic failure rate. Evidence admissibility remains independent: 10 current-contract, 6 v2 bounded-context, 2 v2 ordered-span, 7 quote-drift-blocked, and 4 source-ambiguity-blocked cases. The strict current-contract KEEP rate is 17.24%.

Six of the seven quote-drift Claims are semantically supported despite their unfaithful stored quotation; one is independently unsupported because the final Claim changed a company delivery subject into a speaker. This confirms `evidence_quote_verbatim_preservation` as a separate repair requirement. The review also found a systematic deterministic attribution-normalization defect: several final Claims replaced `公司` with `发言人`, changing the entity that owns production, packaging, inventory, or order-completion capabilities. Primary failure counts are 8 attribution, 1 conditionality, and 1 technical-term inference; secondary tagging raises attribution involvement to 9 Claims and entity inference to 2 Claims.

Atomicity issues occur in 13/29 Claims, with 7 material atomicity failures. Relative to Pilot #1's 11.32% semantic failure and 13.21% atomicity rates, this is a descriptive material regression; no statistical significance is claimed from the 29-Claim sample. The generalization verdict is `FAIL`, and the next gate is `Pilot #2 Semantic Failure Repair`. The review did not modify the prompt, rerun extraction, repair quote drift, change canonical schemas, or write Production/IMA/governance state.

## Pilot #2 Gate B — Semantic Failure Repair - 2026-08-31

Gate B traced the dominant attribution failures to deterministic post-processing rather than to the raw model wording alone. After Claim validation, company-scoped statements missing the attributed party were rewritten by replacing the first `公司` with the attribution subject or by prefixing that subject. With `attributed_to=发言人（研究员）`, this changed business subjects such as `龙头公司` and `大陆公司` into `龙头发言人` and `大陆发言人`. The unsafe statement replacement/prefix path has been removed; attribution remains required where applicable but is stored separately and cannot overwrite the statement's grammatical subject.

The extraction prompt received six narrowly observed repairs: verbatim continuous Evidence excerpts, one independently reviewable proposition per Claim with splits across subjects/time/certainty/evidence spans, attribution/subject separation, preservation of conditional modifiers on their original proposition, prohibition on unsupported entity identity inference, and prohibition on domain-knowledge correction of noisy technical terms. The deterministic Evidence resolver was not weakened: exact source text, approved layout-only normalization, and exact ordered adjacent-page spans remain admissible, while lexical cleanup, deleted or inserted words, removed speaker/timestamp boundaries, entity substitution, and technical-term substitution remain rejected.

Across the ten historical UNSUPPORTED Claims, the safely attributable primary failure paths are 8 deterministic post-processing, 1 primarily model extraction, and 1 mixed. The historical verdict remains `FAIL`, semantic failure remains 34.48%, and atomicity issues remain 44.83%; Gate B does not create a new quality rate. The 29 historical Claims, Evidence excerpts, IDs, Gate A results, and Human Review decisions remain immutable. No LLM call, Pilot #2 rerun, Pilot #3 run, schema migration, Production write, IMA, propagation, or legacy-pipeline action occurred. A new real extraction requires the separate `Pilot #2 Controlled Re-extraction Authorization` gate.

## Pilot #2 Controlled Re-extraction Human Review - 2026-08-31

The authorized same-Source controlled re-extraction produced 51 Claims and was reviewed without another LLM call or rerun. Human decisions are 28 `KEEP`, 6 `DROP`, 17 `KEEP_NEEDS_REVIEW`, and 0 `PENDING`; semantic outcomes are 44 `SUPPORTED`, 6 `UNSUPPORTED`, and 1 `AMBIGUOUS`. Relative to historical Pilot #2, true semantic failure improved from 34.48% to 11.76%, material atomicity failure from 24.14% to 7.84%, attribution involvement from 9 dimensions to 0, and quote drift from 24.14% to 11.76%. The old deterministic company-to-speaker mutation did not recur.

The result is `PASS_WITH_REMAINING_REPAIR`, not independent generalization. The six residual semantic failures are 2 conditionality losses, 2 entity inferences, 1 scope widening, and 1 technical-term inference. Six quote drifts remain semantically non-material but increase review cost. Eight exact Evidence excerpts were recovered from model PAGE-pointer mismatches; seven are semantically supported and one has an independent scope failure. No historical artifact, Production state, or canonical schema changed.

## Pilot #2 Gate C — Residual Semantic Guardrails and Evidence Provenance Hardening - 2026-08-31

Gate C applies only static future-facing hardening. The extraction prompt now more explicitly preserves modality on the exact proposition, forbids noisy entity and technical-term expansion from observational or external knowledge, prevents subject/object/domain scope widening, and treats different uncertainty, entity identity, or Evidence scope as a strong split signal without optimizing for maximum Claim count. The successful Gate B attribution rule remains unchanged.

At Phase 3C artifact level, model Evidence is a proposed quotation until deterministic validation succeeds. Exact source, approved layout-only, or exact ordered adjacent-page binding yields validated source-bound Evidence; quote drift remains fail-closed with no canonical-ready Evidence and no automatic nearest-region replacement. Evidence Contract v2 remains artifact-level and does not change canonical or Production schemas.

Model PAGE provenance is explicitly non-authoritative: `model_page_pointer` is retained as a diagnostic hint, while parsed source provenance plus deterministic exact binding supplies the authoritative artifact locator. Pointer mismatch is tracked separately as `MODEL_PAGE_POINTER_ERROR` and is not a semantic failure when Evidence binds exactly elsewhere. Claim-grain monitoring records quote fidelity 45/51 (88.24%), quote drift 6/51 (11.76%), model pointer accuracy 35/45 (77.78%), and deterministic locator recovery 8/8 (100%). These metrics remain separate from semantic support; no composite score or new extraction quality rate is claimed.

Gate C performed no LLM call, Pilot #2 rerun, Pilot #3, Production/IMA/propagation/legacy-pipeline action, or canonical migration. Independent generalization is `NOT_YET_PERFORMED`; after static and regression acceptance, the next gate is `Independent Generalization Pilot Authorization`, which is not executed automatically.

## Acceptance boundary

Stage 1 completes only when the single real TGV extraction succeeds, Evidence excerpts remain exact-match validated, review artifacts are written, legacy side effects and IMA calls are absent, the controlled apply path passes on an isolated Production copy, the real Production DB remains byte-identical with unchanged table counts and valid integrity/FK checks, the second PDF remains untouched, and the Phase 3A/3B/full regression gates pass.

```text
PHASE3C_STAGE1_COMPLETE = true
PHASE3C_STAGE1_1_COMPLETE = true
PHASE3C_STAGE1_2_COMPLETE = true
PHASE3C_STAGE1_3_COMPLETE = true
PHASE3C_STAGE1_4_COMPLETE = true
PHASE3C_COMPLETE = false
REAL_LLM_EXTRACTION_AUTHORIZED = true
LIVE_PRODUCTION_CORPUS_APPLY_AUTHORIZED = false
LIVE_IMA_WRITE_AUTHORIZED = false
HUMAN_EXTRACTION_REVIEW_REQUIRED = true
PRODUCTION_APPLY_READY = NO
PHASE3C_PILOT2_EXTRACTION_COMPLETE = true
PHASE3C_PILOT2_GATE_A_COMPLETE = true
PHASE3C_PILOT2_HUMAN_REVIEW_COMPLETE = true
PHASE3C_PILOT2_GATE_B_COMPLETE = true
PHASE3C_PILOT2_REEXTRACTION_COMPLETE = true
PHASE3C_PILOT2_REEXTRACTION_HUMAN_REVIEW_COMPLETE = true
PHASE3C_PILOT2_GATE_C_COMPLETE = true
PHASE3C_NEXT_GATE = Independent Generalization Pilot Authorization
```

The detailed Stage 1 metrics and paths are reported at runtime and are not copied into tracked documentation as real Claim/Evidence content.
