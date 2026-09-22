# Phase 4.3 Stage 5 qualification

**Result: PASS.** Implementation commit: `d7fa01642f3c4f4160a8905d7569b9056ad97322` on `codex/phase43-stage5-company-latest-material`. The branch began at frozen Stage 4D commit `714ee990672018811fd93cb614b0ff12b8bf2571`, matching local `main` and `origin/main`, with no tracked or staged changes. The contract and machine-readable receipt are adjacent to this document.

## Contract and vertical flow

`company-material-intent-v1` validates an exact active Production Company ID, explicit material kind and source channel, optional operator date/title, and a deterministic SHA. The immutable `COMPANY_MATERIAL_INTENT_BOUND` event precedes processing. Existing Source idempotency and runtime gates remain in force, with target and metadata conflicts blocked. Durable cloud checkpoints bind the same intent and reject drift. Generic Source runs continue without intent.

The disposable synthetic clean PDF ran through the existing worker with two deterministic fake provider calls, native packet, human Review seal, explicit Claim–Company Attribution seal, and qualification to `AWAITING_OPERATOR_ACTION`. No Claim link was made from intent alone. The operator target was available to Attribution with explicit provenance even though extraction proposed a different Company. The provider's semantic payload contained only Source-local evidence, not the operator target. Qualification did not apply to real Production.

The Company timeline displayed private processing and qualified-unapplied states. A synthetic canonical Source with explicit Company and Product links merged by Source ID into one activated row with canonical title, one Claim, two linked Nodes, and zero Current View impact candidates. A separate test proved that a Source canonically linked to a different Company disappears from the original operator target's timeline. The real read-only Company page displayed one canonical Source with 12 Claims, five linked Nodes, and two potential Current View impact candidates. Its existing Current View remained unchanged. `knowledge_community` displayed `LOW_TRUST_CLUE_ONLY`; no Source Rank or confidence was inferred.

## Verification

| Check | Result |
| --- | --- |
| Stage 5 focused backend contract, HTTP, canonical boundary, fake vertical flow | 6 passed |
| Source Operations Stage 7 regression | 15 passed |
| Broad Stage 4D, research, Current View, Attribution, and Workbench backend regression | 80 passed |
| Current View / Source Impact regression | 28 passed |
| Complete frontend suite, including Stage 4A–4D surfaces | 150 passed in 28 files |
| TypeScript, Vite production build, Python compileall, staged diff check | PASS |
| Synthetic browser at 1920×1080 and 1366×768 | Company timeline, prefill, private/canonical states, upload duplicate handling, return route; no horizontal overflow |
| Real read-only browser Company and Source | Canonical material, Current View, Product/Industry links, impact count and Source Direct Impact route visible |

Browser acceptance used the disposable fixture under `stage5_browser_fixture`. Its synthetic navigation-context panel reports unavailable because the fixture does not include the later navigation context setup; the real Company smoke loaded that panel normally. This fixture detail did not affect Stage 5 material APIs or navigation.

## Real data and governance

Production SHA-256 before/after: `6e5a303ccee9c192c350c2550cc232649e56ffee939b7a09cd6b170cc1c8fba1`. Real Workbench SHA-256 before/after: `c28dd60c94deeb8c897c6180b9fec2366ffaef7b671a6c9b0ddf7af9047279f3`. Stage 4D logical overlay SHA-256 remained `aa917e07895d7912e5bfe9c41763af3fbd705127a6fd797e858f1bef2816bfb5`. Real Production and Workbench writes, real uploads/runs/reviews/Attribution mutations, real provider calls, Apply, official View activations, and Current View writes were all zero. The frozen Stage 4D governance receipt records `HARD_STOP`, 274 pending review rows, and new intake disabled. The real Workbench file is schema 8, so that Stage 1 governance state is cited from the frozen receipt, not recomputed from this file. No gate was bypassed.

| Gate | Result | Evidence |
| --- | --- | --- |
| A — Baseline | PASS | Exact frozen parent, clean tracked start, expected Production and overlay hashes |
| B — Intent contract | PASS | Validation, deterministic SHA, event order, idempotency/conflict tests |
| C — Source Operations | PASS | Generic and Company runs, checkpoint binding, Stage 7 regression |
| D — Human Attribution | PASS | Operator target candidate, explicit human decisions, no automatic Claim link |
| E — Company timeline | PASS | Private, qualified-unapplied, canonical merge, exact association, deterministic snapshot |
| F — Research integration | PASS | Company, Source, Claims, Product/Industry links, impact and Current View routes |
| G — Trust boundary | PASS | Explicit channel policies, clue warning, no rank/confidence/Current View inference |
| H — UI | PASS | Both required viewports, usable material and operations pages, no overflow |
| I — Regression | PASS | Backend suites, complete frontend suite, TypeScript/build/compileall |
| J — Real data safety | PASS | Production and Workbench byte-identical, zero real mutations |
| K — Privacy | PASS | Staged path/payload scan found no local or private storage path or provider payload leakage |
| L — Scope | PASS | No Production Apply, ontology redesign, connector, OCR, new domain or earlier-stage requalification |

The attached JSON receipt records the exact contract enum hashes, synthetic identities, snapshots, test counts, and safety values.
