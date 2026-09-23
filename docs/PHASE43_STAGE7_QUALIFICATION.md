# Phase 4.3 Stage 7 Qualification

## Result

`PHASE43_STAGE7_KNOWLEDGE_COMMUNITY_ADAPTER = PASS`

Gate J uses the revised criterion: relevant regressions must pass, and the mandatory full-repository diagnostic must show no new Stage 7 regression. The raw full Python suite is not all green. Its 33 historical/environment exceptions were audited individually and reproduced against the exact pre-Stage7 source baseline. The qualification receipt is [phase43_stage7_qualification_receipt.json](phase43_stage7_qualification_receipt.json); the item-level evidence is [phase43_stage7_full_suite_exception_audit.json](phase43_stage7_full_suite_exception_audit.json).

## Baselines and functional acceptance

The pro_a parent is `c93da477e739a2357403dd536b22e4b8ff8da2dc`; the zsxq parent is `56666b06fd5e72484301b53b5020961721bb49e9`. The shared `zsxq-pro-a-community-export-v1` contract SHA256 is `6a3e2dc77287d426b8afda46df9fed24b6188e27df16946a8e88b59d91d66d48` in both repositories.

The synthetic ZSXQ fixture has 3 in-range topics, exports 2 reportable topics, and omits 1 unrelated topic. The ZIP and Chinese PDF are byte deterministic. AI routing summaries and impacts do not enter raw Evidence. The bundle SHA is `4b83f78292314df321b93667283271b41591e1bbfa753c22673daaf86f8b1ce8`, ZIP SHA is `3ce2d324b8ce7a7ef271283f6058556b78b71298dc775fed891c570f4055391b`, and PDF SHA is `6a5ce7b8d6052c25c0b3a482d5ff32b1a16ef631f1ae3f9d435ab5cfbf92a53b`.

The disposable schema 11 fixture proves authenticated preview has no Source write; explicit import registers one private Source and starts processing; duplicate import is safe; another Company target conflicts; Community, Company intent, and queue events are ordered and bound to cloud-input checkpoints. The fake provider reaches Human Review, human Attribution, and `qualified_unapplied`. Company timeline shows the private Community material. No automatic claim link or Production apply occurs. Browser acceptance passed at 1920×1080 and 1366×768, including independent pane scrolling and the Industry map footer.

## Full Repository Diagnostic Context

The required full Python run completed with **2377 passed, 6 skipped, 4 failed, and 29 errors**. Stage 6's frozen diagnostic was **2373 passed, 6 skipped, 4 failed, and 29 errors**. Equal counts alone were not used as evidence. A JUnit XML inventory identified each of the 33 current exceptions. A `git archive` of the exact `c93da477` pre-Stage7 commit supplied isolated Python source while tests used the same installed dependencies and existing local inputs. A control run of those exact 33 nodeids reproduced **33/33 matching nodeid, status, and error-message fingerprints**. No private input was copied and neither branch was reset or switched.

| Historical/environment class | Items | Exact basis |
|---|---:|---|
| Private Foundation prerequisite | 10 | The frozen test requires a private migration instruction before its body or `inputs` fixture can run. |
| Phase 3F Production binding | 21 | Frozen packet and handoff checks require the historical exact Production SHA. |
| Old ingestion fixture | 1 | The frozen Phase 3C/3D replay fails the unchanged normalized local-context check on the pre-Stage7 source too. |
| Stage 3 branch sentinel | 1 | The frozen script requires `codex/phase43-stage3-cross-domain-resolution`, as already recorded by Stage 6. |

All 33 failing test files and their direct fixture files are unchanged by Stage 7. Their traceback modules are unchanged by Stage 7; changed runtime traceback overlap is zero. The baseline control and the frozen test contracts establish that each exception occurs independently of the Stage 7 code path. `NEW_STAGE7_REGRESSIONS = 0` and `UNRESOLVED_DIAGNOSTIC_EXCEPTIONS = 0`. The truthful classification is `PASS_WITH_PRE_EXISTING_NON_GATING_FAILURES`, not a claim that raw full-repository pytest passed.

## Relevant regression and changed modules

The full-suite JUnit run includes 238 passing, zero-failing cases in the Stage 7, Stage 4D, Stage 5, Stage 6, Workbench/Source Operations, Review, Attribution, Current View, Direct Impact, Company Materials, Cloud Jobs, and Research Explorer test files. This includes 3 focused Stage 7, 4 Stage 4D, 6 Stage 5, 4 Stage 6 lifecycle, 109 Human Review intake, 33 Workbench Stage 6, and 15 Workbench Stage 7 cases. The separate Stage 5/Source Operations focused run passed 21 tests. No relevant exception was waived.

| Changed runtime Python module | Focused coverage | Result |
|---|---|---|
| `src/pro_a/community_material.py` | Stage 7 ZIP validation, Chinese PDF, preview, and schema 11 import tests | PASS |
| `src/pro_a/workbench/api.py` | Stage 7 authenticated preview/import and existing API/Workbench regression | PASS |
| `src/pro_a/workbench/source_operations.py` | Stage 7 dedupe, event order, lineage/checkpoint, fake provider; Stage 5/6 Source Operations regression | PASS |

Changed runtime module test coverage is **3/3 (100%)**. ZSXQ's full suite passed **11/11**. The frontend full suite passed **155/155 in 28 files**, and TypeScript, frontend build, Python compileall, and staged diff checks passed.

## Real-state safety

Read-only checks before and after qualification found canonical Production SHA `6e5a303ccee9c192c350c2550cc232649e56ffee939b7a09cd6b170cc1c8fba1` and real Workbench schema 11 SHA `f8cf49f5a4d0ed54ffb4f57bea051f0481a44d35adcd4d8f84eadeecb07b46e9`. The Stage 4D overlay logical SHA remains `aa917e07895d7912e5bfe9c41763af3fbd705127a6fd797e858f1bef2816bfb5`. WIP is OPEN, new intake is allowed, operational pending is zero, and historical lifecycle closure remains 274 (105 Human, 169 AI policy).

Real Workbench mutations, real Community imports, real pro_a provider calls, real ZSXQ calls, real DeepSeek calls, and Production applies were all zero.

## Acceptance gates

| Gate | Result | Evidence |
|---|---:|---|
| A — Frozen parents | PASS | Both exact parent commits retained; no reset or rebase |
| B — Export contract | PASS | Shared contract SHA matches; raw Evidence and routing separated |
| C — ZSXQ export | PASS | 3 input, 2 exported, 1 unrelated omitted; deterministic ZIP |
| D — pro_a validation/PDF | PASS | Strict ZIP, Chinese text, deterministic PDF, sensitive-content checks |
| E — Source and Company | PASS | Explicit schema 11 import, dedupe, target conflict, private timeline |
| F — Lineage/checkpoint | PASS | Event order, Community SHA checkpoint, provenance binding |
| G — Human authority | PASS | Fake provider, Review, Attribution, qualified unapplied |
| H — UI/browser | PASS | Authenticated flow, both viewports, pane scrolling, map footer |
| I — Contract/compatibility | PASS | Cross-repo SHA, Stage 4D/5/6 and relevant Workbench tests |
| J — Regression | PASS | 238 relevant backend cases, 155 frontend; 33/33 audited historical diagnostic exceptions; no new regression |
| K — Real-state safety | PASS | Production and Workbench SHAs exact; zero real calls/imports/mutations |
| L — Scope/delivery boundary | PASS | No real import, Production Apply, merge, or Ready action |
