# Phase 4.3 Stage 6 Qualification

## Result

`PHASE43_STAGE6_OPERATIONAL_WIP_CLOSURE = PASS`

Stage 6 introduces an immutable lifecycle closure sidecar and schema 11 capacity semantics. It keeps Human review, Human qualification, AI policy qualification, lifecycle closure, and Production apply as distinct authorities. The real Production and Workbench databases stayed byte-identical throughout qualification.

## Baseline and authority

| Check | Qualified value | Result |
|---|---:|---:|
| Stage 5 frozen baseline | `9807589fe423d911a070d80cc4b66c46b78440d7` | PASS |
| Implementation commit | `08d025a94747dbd03c987feb57d962479fd0992b` | PASS |
| Production SHA256 | `6e5a303ccee9c192c350c2550cc232649e56ffee939b7a09cd6b170cc1c8fba1` | PASS |
| Real Workbench SHA256 / schema | `c28dd60c94deeb8c897c6180b9fec2366ffaef7b671a6c9b0ddf7af9047279f3` / 8 | PASS |
| Stage 4D logical overlay SHA256 | `aa917e07895d7912e5bfe9c41763af3fbd705127a6fd797e858f1bef2816bfb5` | PASS |
| Stage 2 population | 274 / `b363748e9aa05be4d66d7ff5c3d0008e9a80df29a25741f72d60c7c32c983b51` | PASS |
| Original immutable packet | `06006a1c98247f1803dac9cdcd0f10ade5d84beddc56a12e3768e5a9e5bfc66c` | PASS |
| HUMAN_USER authorization | `23fa6c94d55caf7ef8cfc3291528d3d41a06948460b852d7418c68f572bf014f` | PASS |
| Review A / Review B | `9e5735f73a039c58b598ba48d1d78d5bf434c22a8ce6c15e464f22c8aa5f9edf` / `f32d03eaf14494486a7d0dc89e2f20ccbe9ad950a69b1d80d0b16fb37ebdb08f` | PASS |
| Reconciliation / residual sample | `3631ead5334528a174a97683105fe5a1125b6e90fe9748f92c787be9c6b58b9b` / `44051e472043f12bb416e7947d4f67a0f16d8785a4154d963e96726bbaed09a3` | PASS |

The original packet, existing Review audit, frozen receipts, and Stage 4D overlay were unchanged.

## Lifecycle closure

Contract `phase43-stage6-lifecycle-closure-v1` produced closure `2516386da0e629102b60362553a0c63420df69f45fdd02e888757cd87ccf4feb`. Two independent builds emitted the same file SHA256 `27d35bef0aad703b98336f8d53508b5ba9c60c5930bc43e034fdd6760ccbadfd` and matched the tracked artifact byte for byte.

| Resolution source | Rows | Meaning |
|---|---:|---|
| `HUMAN_USER_QUALIFICATION` | 105 | Exact existing Human decisions: 76 mandatory and 29 residual sample items |
| `AI_POLICY_QUALIFICATION` | 169 | Frozen dual-review policy outcome with no Human item attribution |
| Total | 274 | Historical lifecycle population |

All 169 AI policy rows have positive Review A, Review B, reconciliation, risk-routing, and sample-expansion evidence. Unresolved rows and unresolved substantive A/B disagreements are zero. Forty closed rows remain visible for follow-up governance. The closure grants no Production authority.

## Isolated real-copy acceptance

The isolated copy began at real Workbench SHA `c28dd60c94deeb8c897c6180b9fec2366ffaef7b671a6c9b0ddf7af9047279f3` and schema 8. The official migrations completed 8→9→10→11, followed by closure registration. Foreign-key violations were zero and `integrity_check` returned `ok`. A queued-job fixture on a second disposable schema 10 copy proved that the active-work drain guard fails closed.

The historical Stage 2 packet is absent from this real baseline, so the closure was truthfully registered with `artifact_id = null`; no historical packet was imported or fabricated.

| Capacity field | Result |
|---|---:|
| Current native pending | 0 |
| Historical lifecycle resolved | 274 |
| Current operational pending | 0 |
| Unprojected packets | 0 |
| WIP state | OPEN |
| New intake allowed | true |
| Exact `require_stage1_intake()` | PASS |
| Idempotent replay | ALREADY_APPLIED |

The copy's actual post-apply SHA was `2076f8a264aa2359ba272d1e1866c2e5df78758f34400a65b9e63959d399065b`. This is recorded as copy evidence only. The plan does not predict the future real database byte SHA because the official migrations contain timestamps.

## Compatibility and tests

- Stage 6 focused: 4 passed, covering deterministic authority, schema 11 immutability, OPEN/SOFT_WARNING/HARD_STOP arithmetic, future and mixed packet behavior, Review queues, idempotence, Source start, and Company timeline.
- Relevant backend regression: 224 passed, covering Stage 1, Stage 2, Stage 4D, Stage 5, Source Operations, Domains, Cloud Jobs, Review, Attribution, Current View, Company Materials, and Research navigation.
- Full frontend: 28 files and 153 tests passed with two workers.
- TypeScript, Vite build, Python compileall, and `git diff --check`: PASS.
- Browser acceptance: Source Operations and Research loaded at schema 11; 1920×1080 and 1366×768 had no horizontal overflow.
- Stage 3 and Stage 4A–4D continuity: 58 checks passed. One historical Stage 3 branch-identity sentinel rejected the Stage 6 branch as designed because that frozen script requires `codex/phase43-stage3-cross-domain-resolution`; Production remained byte-identical.

A separate full-repository run reached 2,373 passed and 6 skipped, with 4 failures and 29 setup errors in pre-existing private-input and historical-baseline audits. Those audits require unavailable or different frozen inputs. They are recorded for transparency and are outside the relevant Stage 6 gate; the complete Stage 6 regression set passed independently.

## Safety and privacy

Production writes, Current View writes, official view activations, real Workbench mutations, real migrations, real lifecycle applies, Source uploads, processing runs, and provider calls were all zero. Production stayed `6e5a303ccee9c192c350c2550cc232649e56ffee939b7a09cd6b170cc1c8fba1` and real Workbench stayed `c28dd60c94deeb8c897c6180b9fec2366ffaef7b671a6c9b0ddf7af9047279f3` before and after qualification.

The targeted scan of all tracked Stage 6 files found zero local absolute paths, private source paths, private artifact paths, provider payloads, or false aggregate Human claims.

## Acceptance gates

| Gate | Result | Evidence |
|---|---:|---|
| A — Baseline | PASS | Stage 5, Production, Workbench, and overlay identities exact |
| B — Frozen authority | PASS | 274 population, 105 Human, 169 AI policy; all frozen hashes exact |
| C — Closure correctness | PASS | 274/274 resolved; zero missing, duplicate, or fabricated attribution |
| D — Original history | PASS | Packet, Review audit, and frozen receipts unchanged |
| E — Schema | PASS | Copy 8→9→10→11; FK and integrity PASS |
| F — Capacity | PASS | Historical registry 274; current native 0 and operational 0; unrelated WIP tests PASS |
| G — Intake | PASS | Exact intake guard PASS; WIP, pause, run-window, and projection guards retained |
| H — Stage 5 compatibility | PASS | Source Operations, Company Material, Attribution, and timeline tests PASS |
| I — UI truthfulness | PASS | Native, operational, Human, and AI policy totals are distinct |
| J — Regression | PASS | 224 backend and 153 frontend tests plus build/static gates |
| K — Real data safety | PASS | Production and real Workbench byte-identical; no real execution |
| L — Scope | PASS | No Production, Current View, requalification, overlay, connector, or real Workbench apply |

## Readiness

`READY_FOR_REAL_APPLY = true`

`REAL_STAGE6_APPLY_EXECUTED = false`

The operator plan is `docs/phase43_stage6_real_apply_plan.json`. After PR and release closure, obtain explicit HUMAN_USER authorization before executing it against the real Workbench.
