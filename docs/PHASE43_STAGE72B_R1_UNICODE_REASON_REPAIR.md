# Phase 4.3 Stage 7.2B-R1 — Unicode single-line reason repair

**PHASE43_STAGE72B_R1_UNICODE_REASON_REPAIR = PASS**

This qualification repairs B1 from the pre-merge audit. The historical audit at `61c794df26893362f08cc712035b6da60bb1ada4` remains **BLOCKED**. A fresh full pre-merge audit of the new PR head is still required. Historical real Run readiness remains **BLOCKED_RUNTIME_INCOMPATIBLE**.

## Boundary and implementation

- Base: `4c1c98a1dc4bc85f807c5817ab9fd5a9058378bd`; initial frozen PR head: `61c794df26893362f08cc712035b6da60bb1ada4`.
- Repair implementation commit: `54547523952256e37e9a7f3f7d0310e39c4a2db9`; this report/receipt are in a following documentation commit.
- PR #78 remains OPEN / DRAFT / UNMERGED. Fetch verified the expected head and base before edits.
- Application source diff: exactly one added validation predicate in `src/pro_a/workbench/extraction_retry.py`; no other runtime source changed.
- The new predicate requires `retry_reason.splitlines() == [retry_reason]`. It is deterministic, locale-independent, Unicode-aware, and does not normalize or replace operator text. It runs in the service before opening a write transaction. Existing Pydantic strict/extra-forbid/min-max behavior and API error handler are retained.
- Existing C0, DEL, trim, markup and credential-like checks remain intact. Internal U+3000 and emoji are valid; leading/trailing U+3000 remains invalid under the existing trim contract.

## Executed validation matrix

`tests/test_phase43_stage72b_unicode_reason.py` adds ten test cases, with the invalid matrices checked entry by entry against real service/API calls on synthetic failed Runs.

| Coverage | Result |
| --- | --- |
| LF, CR, VT, FF, every C0 code point and DEL | PASS |
| U+0085 NEL, U+2028 LS, U+2029 PS inside text | PASS |
| NEL/LS/PS alone and trailing; CRLF | PASS |
| Service rejection | PASS: INVALID_RETRY_REASON, status 422 |
| Authenticated retry endpoint | PASS: HTTP 422 with INVALID_RETRY_REASON for 53 service-bound cases |
| Empty and 1001-character API inputs | PASS: existing Pydantic HTTP 422 boundary |
| Every invalid request leaves exact state rows unchanged | PASS: 55 service inputs and 55 API inputs |
| Bearer, api_key=, token=, cookie=, authorization= | PASS: rejected |
| English, Chinese, mixed language, digits, ordinary/fullwidth punctuation | PASS |
| Internal U+3000 + emoji; 1000-character reason | PASS |
| Exact Unicode text identity across API/service/database | PASS; no normalization |

For each invalid input, snapshots compare Run rows, cloud_jobs, cloud_attempts, extraction_retries, Run events, Job events, dispatches and outcomes. Equality proves counts and existing rows are unchanged. Each valid case accepts once through the actual endpoint, then returns the same reservation through direct-service idempotency. Its text is preserved in storage. No retry provider dispatch occurs in these input tests.

## Retry and safety regressions

Exact worktree source: **56 passed** = 25 existing Stage72B retry + 10 R1 Unicode + 21 previous independent audit cases. The prior three Unicode service failures and one HTTP failure now pass.

Existing checks retain same Run/new Attempt, original attempt and context immutability, Shared Core context, unchanged raw Source, no new Run/acquisition/routing, idempotency/concurrency, successful continuation, failed retry diagnostics and retry/reprocess separation. The independent audit additionally verifies transaction fault rollback, lineage identity/numbering, eligibility, API controls and backup/restore. Synthetic provider doubles cover execution; no real provider is invoked.

Related full-suite selection: **294 passed**, covering Workbench/API, lifecycle/reprocess, Stage7/Stage71, Stage72A diagnostics and LLM cases.

Full repository: **{'PASSED': 2444, 'SKIPPED': 2, 'FAILED': 4, 'ERROR': 29}**, 2479 total. Exactly **33 historical exceptions** match by node, status and exception class, with **0 new regression** and no missing historical exception. These historical failures/errors remain exceptions; they are not reported as passed tests. Ten new Unicode test cases account for the increased pass count.

Compileall: **PASS (exit 0)**. Frontend was not rerun because the repair changes only backend reason validation and backend tests/documentation.

The full suite retains the established historical root fixture/config environment and uses a test-only import overlay for current changed modules. Credentials are cleared and no secret/config is copied. Only two unrelated preexisting untracked root tests are excluded. The focused suite independently uses the entire worktree source with explicit worktree pytest configuration. Source bytes are bound by hashes in the receipt; test runs precede the implementation commit, with no code changes after verification began.

## Historical runtime gate — preserved

No runtime identity, frozen configuration, context guard, native compatibility, schema, migration, provider or reprocess implementation is changed. Static diff verifies the original frozen_cloud/frozen_service/runtime/native logic remains unchanged; the existing synthetic runtime/config drift tests still reject incompatible retry.

The earlier exact-head isolated-copy probe observed:

- Old runtime SHA: `ef7fb67f6057f5c9532990aa2e692a320eadda00b5b6dc4a271d30a69fa357c2`.
- Then-current runtime SHA at `61c794df26893362f08cc712035b6da60bb1ada4`: `f7181953f6bd4e3126cb7184c598f4d0d2742670521cef1d71232cc58cbedd35`.
- Acceptance: RETRY_FROZEN_CONFIG_INCOMPLETE; context: PROCESSING_RUN_CONTEXT_DRIFT; native: CODE_OR_RUNTIME_CONTRACT_INCOMPATIBLE.

These are historical observations, not a claimed current repaired-head runtime SHA. A code/commit change naturally affects the existing runtime hash calculation; no identity algorithm or frozen historical value is altered. R1 does not rerun the real-state compatibility probe or grant a compatibility override. The previous BLOCKED report/receipt are preserved byte-for-byte, and readiness remains **BLOCKED_RUNTIME_INCOMPATIBLE**.

## Real state

| Database | Before | After |
| --- | --- | --- |
| Production | `6e5a303ccee9c192c350c2550cc232649e56ffee939b7a09cd6b170cc1c8fba1` | `6e5a303ccee9c192c350c2550cc232649e56ffee939b7a09cd6b170cc1c8fba1` |
| Workbench | `1ff852dbe76c5fc4054c3e6f4e308b98a66f918dc3081e287b793c682a61ca44` | `1ff852dbe76c5fc4054c3e6f4e308b98a66f918dc3081e287b793c682a61ca44` |

REAL_PROVIDER_CALLS = 0; REAL_ZSXQ_READS/DOWNLOADS/WRITES = 0; PRODUCTION_WRITES = 0; REAL_WORKBENCH_WRITES = 0. All test mutations use disposable synthetic databases. No real retry, preparation, migration or approval occurred.

## Evidence and handoff

The existing local BLOCKED audit report/receipt and previous global-idempotency documentation clarification are preserved outside the narrow R1 commits. R1 changes the service predicate, adds Unicode tests, clarifies single-line semantics, and records qualification. It does not rewrite the historical audit outcome.

Paths below are relative to the root checkout; local JUnit/logs and the prior independent audit script remain uncommitted evidence.

| Evidence | SHA-256 |
| --- | --- |
| `workspace/stage72b_r1_full.xml` | `32d4b2cd78c9cbb98b555ad2b2244bc9aeeeb2140f19de3514f9bd1ebf458c30` |
| `workspace/stage72b_r1_full.log` | `1d9c7d62c75ddaadc3aace77a7e744c93748f61288105f74e40473b5a140d8f4` |
| `workspace/stage72b_r1_focus.xml` | `3cd26407658283648c87e1c0a477fa60611e5554894903ede3bec9f0948b78da` |
| `workspace/stage72b_r1_focus.log` | `ea52a939cfdb95258e7a7a1cd96e3ea97976a062f9be0d7b07fb1efc96cef75c` |
| `workspace/test_stage72b_premerge_audit.py` | `10e903a9b4689434bb19e8d2023c7f8dd238fa7ef9d78fe899faab77071b69af` |
| `workspace/stage72b_env/sitecustomize.py` | `25133d3129c05734fc23d3d0157e5218e3e2e5a720fba31f0aebb4ec2e440766` |

NEXT_ACTION = Re-run the full Stage 7.2B pre-merge audit against the new PR #78 head. Keep the historical real Stage 7.2 Run classified as BLOCKED_RUNTIME_INCOMPATIBLE; do not attempt to fix or bypass that incompatibility in this stage.
