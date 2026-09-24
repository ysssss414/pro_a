# Phase 4.3 Stage 7.1 — joint pre-merge audit

**Result: PASS.** Audited implementation commit `99de853e5b187de0b11918ddd113f82e24e3bee7` against `ac6853335ce8fb8a10d9c74015bafe4a4579bd61`. PR #74 was Open, Draft, unmerged, based on `main`, and pointed at the audited implementation commit. Remote `main`, local `main`, the fork point, and the PR base all matched the frozen base. This audit does not authorize merge, Ready for Review, release, Domain activation, real intake, or Production Apply.

## Scope and boundary

The base-to-implementation diff contains 21 text files: six additions and 15 modifications. The additions are the Stage 7.1 contract, qualification documents, v2 processing context, and focused Python/frontend tests. The modifications are the Community and Source intake paths, frozen-context projections, provider guard, and relevant frontend/API tests and views. There are no deletions, migrations, binary files, database files, snapshots, browser session files, temporary files, or secret files in that diff. `git diff --check` passed. The repository has unrelated pre-existing untracked local material; none is included in this audit commit.

The only audit repair is one sentence in `PHASE43_STAGE71_QUALIFICATION.md`: the original text claimed its receipt recorded Draft PR metadata, but that receipt has no PR fields. It now points to this audit receipt for PR verification. No implementation code was changed.

## Contract-to-execution trace

| Clause | Execution path | Test and observed evidence |
| --- | --- | --- |
| B1 no Domain assignment | `Domains.basis` creates v2 scope when Source assignment is absent (`src/pro_a/workbench/domains.py:184`); Community import does not call `assign` without an explicit Domain (`src/pro_a/community_material.py:331`). | `tests/test_phase43_stage71_shared_core_pending.py` asserts zero assignment rows; isolated Community preview/import used zero registry entries. |
| B2 no Domain Pack | v2 scope uses an empty pack list (`src/pro_a/workbench/domains.py:207`); validation requires it (`src/pro_a/processing_context.py:36`). | Focused tests and synthetic browser fixture start and finish with zero registered Packs. |
| B3 no primary Domain | The v2 scope serializes `primary_domain: null` and validates that value (`src/pro_a/processing_context.py:36`). | Focused context assertions at `tests/test_phase43_stage71_shared_core_pending.py:51`; browser shows “Pending,” not an activated Domain. |
| B4 no assignment row | `Domains.basis` selects the explicit pending basis from absent assignment; Community import only assigns when `primary_domain` is supplied (`src/pro_a/community_material.py:356`). | Focused SQL assertion and qualification receipt's zero assignment counts. |
| B5 bounded Shared Core processing | `SourceOperations.start` binds v2 to the durable Run (`src/pro_a/workbench/source_operations.py:416`); `CloudJobs._preflight` accepts validated v2 while retaining provider identity, runtime, prompt, configuration, and budget checks (`src/pro_a/workbench/cloud_jobs.py:616`). | Focused fake and non-network double tests; both isolated browser flows completed using `DeterministicFakeProvider`. |
| B6 Human Review stop | Source orchestration transitions only on `STOPPED` with `HUMAN_REVIEW_REQUIRED` (`src/pro_a/workbench/source_operations.py:1086`). | Focused test and both isolated UI flows reached `HUMAN_REVIEW_REQUIRED`. |
| B7 no automatic Production promotion | `SourceOperations.advance_once` ends at Review; the review and attribution steps remain separate (`src/pro_a/workbench/source_operations.py:1086`). | Real Production hash identical before and after; synthetic UI ends at Review. |
| B8 no automatic Domain assignment | `Domains.assign` is an explicit operator path; Community import calls it only with supplied registered Domain (`src/pro_a/community_material.py:333`, `:356`). | Zero assignment rows in pending tests; late assignment test requires explicit call. |
| B9 no automatic Pack creation | Pending basis uses the fixed Shared Core identity and never invokes `Domains.register` (`src/pro_a/workbench/domains.py:184`, `src/pro_a/processing_context.py:19`). | Zero Pack registry in tests and real Workbench; late-assignment fixture registers a Pack explicitly. |
| B10 no arbitrary fallback Domain | v2 validation requires `SHARED_CORE_PENDING`, `PENDING`, null primary, and empty packs; assigned v1 requires revision > 0, primary Domain, and nonempty packs (`src/pro_a/processing_context.py:36`, `src/pro_a/run_context.py:17`). | Ten corrupt-context variants rejected; Stage 1 Domain projection reads frozen context (`src/pro_a/workbench/stage1_scale.py:332`). |

## Frozen semantics and identities

The historical `run-domain-context-v1` validator remains unchanged: positive assignment revision, primary Domain in a nonempty sorted Pack composition, and `OFFLINE_REPLAY_ONLY` (`src/pro_a/run_context.py:17`, `:37`). Its fake-provider path passed; its nonfake path still raises `DOMAIN_ACTIVATION_REQUIRED` at `src/pro_a/workbench/cloud_jobs.py:616`. The v2 branch follows the existing provider identity, prompt, runtime, configuration, and budget checks. Stage 7.1 does not activate a Domain Pack or introduce a network provider.

The `run-processing-context-v2` basis explicitly serializes `SHARED_CORE_PENDING`, `PENDING`, null primary, empty packs, and `LIVE_SHARED_CORE_BOUNDED`. `processing_context.create_context` hashes the canonical basis as `resume_sha256` and the canonical context body as `context_sha256` (`src/pro_a/processing_context.py:60`). `Domains.bind_run` stores the context through the existing schema 11 binding table. `Domains.guard` branches by the frozen contract version and rebuilds the pending basis without adopting a later Source assignment (`src/pro_a/workbench/domains.py:259`). `Domains.bind_packet` binds the Review packet SHA to the context SHA (`:282`). Source, Review, Company Materials, and Stage 1 Domain filters project the frozen Run context, so an old Review page cannot acquire the current Source Domain by display-time lookup (`src/pro_a/workbench/source_operations.py:1133`, `src/pro_a/workbench/review_workbench.py:220`, `src/pro_a/company_materials.py:92`, `src/pro_a/workbench/stage1_scale.py:332`).

The recomputed Shared Core SHA-256 was `7393c58ffd981a60bcfec38615b10621def6d972d914f47971548cb6437fd87d` on two independent evaluations. Its canonical object includes the two operation contracts, canonical Node/Relation enums and Claim–Node roles, and the SHA-256 of the source and semantic evidence-rule files (`src/pro_a/processing_context.py:19`). Canonical JSON sorting excludes map/set iteration drift. No clock, process ID, temporary ID, SQLite row ID, or machine path enters the identity. Code-file bytes are intentionally identity-bearing; a changed checkout byte sequence fails the frozen-context check instead of silently reusing an old identity.

The disposable late-assignment test froze a pending Run at revision 0, assigned a Domain at revision 1, and reread the old context and Review packet. Context, context SHA, resume SHA, packet SHA, processing scope, pending basis, and Stage 1 Domain filtering stayed unchanged. An assigned-basis second Run without `reprocess_reason` was rejected; with the explicit reason it created a new v1 Run. An additional pause → assignment → resume probe advanced the old Run after assignment using the local fake provider. It reached `HUMAN_REVIEW_REQUIRED` with its original v2 context and resume identity. The qualification receipt records the original before/after context, resume, and packet hashes.

Provider prompts receive only the Source-local payload (`src/pro_a/workbench/cloud_jobs.py`); Community summary and Company intent remain checkpoint metadata, not evidence authority. No live provider, real ZSXQ, real Source/Run creation, Production write, or Workbench mutation was performed in this audit. All browser and provider exercises used a disposable synthetic fixture and a local deterministic fake provider.

## Verification

| Check | Audited result |
| --- | --- |
| Focused Stage 7.1 Python | 14 passed |
| Related backend Python | 263 passed |
| Frontend | 159 passed in 29 files |
| TypeScript and frontend build | PASS |
| Python `compileall` | PASS |
| Full repository Python | 2391 passed, 6 skipped, 4 failed, 29 errors |
| Historical exception equivalence | 33/33 exact node IDs, statuses, and exception classes; zero added or missing |
| Base/implementation diff checks | PASS |

The full-suite exit code is nonzero because of the same 33 audited historical/environment exceptions in `phase43_stage7_full_suite_exception_audit.json`. This audit parsed the new JUnit output and compared every exceptional node ID, status, and exception class. The four failures and 29 errors have the same membership and classes; no new regression was observed. The prior qualification receipt has the same full-suite counts. No historical test debt was changed.

The isolated browser acceptance was repeated with a synthetic Company, synthetic Community ZIP, synthetic PDF, zero registered Packs, and a local fake provider. At 1920×1080, Community preview selected “Shared Core — Domain pending”; import and Run ended at `HUMAN_REVIEW_REQUIRED`, with `Processing Scope = Shared Core` and `Domain Assignment = Pending`. The document and body scroll widths were both 1920. At 1366×768, generic PDF intake displayed the pending explanation, ended at `HUMAN_REVIEW_REQUIRED`, and showed Pending; document and body scroll widths were both 1366. Local Playwright snapshots were captured under `.playwright-cli/` for these synthetic pages; the machine receipt records the route/state/viewport checks without adding browser session files to Git.

Read-only real-state checks before and after matched: Production SHA-256 `6e5a303ccee9c192c350c2550cc232649e56ffee939b7a09cd6b170cc1c8fba1`; Workbench SHA-256 `f8cf49f5a4d0ed54ffb4f57bea051f0481a44d35adcd4d8f84eadeecb07b46e9`. Workbench schema is 11, Pack count 0, Source count 0, Run count 0, WIP `OPEN`, operational pending 0, and historical closed 274. The hashes and counts exclude the disposable synthetic fixture.

The Stage 7.1 diff and these audit documents contain no API key, real token, cookie, authorization header value, private material, real Community content, provider payload, database dump, credential, or browser session state. The added `s`-repeated session token and `csrf` values in tests are synthetic literals; CSRF and token identifiers in code are field names. No `.env`, archive, screenshot, log, or binary is added to the PR diff.

## Gate disposition

| Gate | Result |
| --- | --- |
| GIT_BOUNDARY | PASS |
| CONTRACT_IMPLEMENTATION_ALIGNMENT | PASS |
| V1_BACKWARD_COMPATIBILITY | PASS |
| V2_SHARED_CORE_SEMANTICS | PASS |
| SHARED_CORE_IDENTITY | PASS |
| POST_ASSIGNMENT_IMMUTABILITY | PASS |
| RESUME_DETERMINISM | PASS |
| REVIEW_PACKET_DETERMINISM | PASS |
| PROVIDER_BOUNDARY | PASS |
| WRITE_ISOLATION | PASS |
| REAL_STATE_IMMUTABILITY | PASS |
| REGRESSION_EQUIVALENCE | PASS |
| BROWSER_EVIDENCE | PASS |
| SECRET_SCAN | PASS |
| DOCUMENTATION_ACCURACY | PASS |

**Final:** `PHASE43_STAGE71_JOINT_PREMERGE_AUDIT = PASS`. PR #74 remains Draft/Open/unmerged. The next action is the separately authorized Stage 7.1 release handoff, where a human may mark PR #74 Ready for Review and perform merge/release closure.
