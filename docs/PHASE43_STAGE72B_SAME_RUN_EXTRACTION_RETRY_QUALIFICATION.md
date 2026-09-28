# Phase 4.3 Stage 7.2B — Qualification

**PASS for same-Run retry orchestration on qualified frozen runtime/configuration.** Real Pilot retry remains prohibited and its cross-release runtime compatibility is not qualified by this result.

## Scope and implementation

Baseline: `4c1c98a1dc4bc85f807c5817ab9fd5a9058378bd`. Branch: `codex/phase43-stage72b-same-run-extraction-retry`. Implementation head: `a38c1fcee7c372bcbc4475e2b398b13516b5d523`; this report and receipt are subsequent evidence.

One additive append-only retry-lineage table and explicit migration command; authenticated/CSRF-protected POST and service command; transactional eligibility/idempotency/concurrency; existing provider path with frozen execution settings and a one-dispatch guard; effective extraction Job selection; complete Run detail/list attempt accounting. The frozen context and old Job/attempt/call/event records stay unchanged. Provider adapter, request format, prompt, parser and diagnostic semantics are unchanged.

Pending retry acceptance reserves its ID; `cloud_attempts` is written only at dispatch intent. Native checkpoint replay and ordinary downstream semantic processing reach HUMAN_REVIEW_REQUIRED in the synthetic success case. Synthetic failure persists Stage 7.2A diagnostics and stops even with retryable=true. Attempt 3 requires another explicit command.

## Qualification matrix

All tests use disposable local Sources/DBs and non-network provider doubles.

| Case | Result | Test in test_phase43_stage72b_extraction_retry.py |
| --- | --- | --- |
| Q1 | PASS | `test_success_same_run_context_history_and_no_acquisition_routing` |
| Q2 | PASS | `test_success_same_run_context_history_and_no_acquisition_routing` |
| Q3 | PASS | `test_frozen_cloud_configuration_and_later_domain_assignment` |
| Q4 | PASS | `test_success_same_run_context_history_and_no_acquisition_routing` |
| Q5 | PASS | `test_success_same_run_context_history_and_no_acquisition_routing` |
| Q6 | PASS | `test_success_same_run_context_history_and_no_acquisition_routing` |
| Q7 | PASS | `test_success_same_run_context_history_and_no_acquisition_routing` |
| Q8 | PASS | `test_failure_diagnostics_no_auto_retry_and_retry_of_retry` |
| Q9 | PASS | `test_duplicate_and_active_guard` |
| Q10 | PASS | `test_concurrent_commands_allocate_once` |
| Q11 | PASS | `test_invalid_reason_rejected` |
| Q12 | PASS | `test_unsupported_run_states_rejected` |
| Q13 | PASS | `test_other_run_attempt_and_active_job_rejected` |
| Q14 | PASS | `test_frozen_cloud_configuration_and_later_domain_assignment` |
| Q15 | PASS | `test_frozen_cloud_configuration_and_later_domain_assignment` |
| Q16 | PASS | `test_retry_and_reprocess_are_separate` |
| Q17 | PASS | `test_failure_diagnostics_no_auto_retry_and_retry_of_retry` |

Additional cases cover API forbidden overrides/authentication/CSRF, additive idempotent migration, append-only lineage, changed native configuration, runtime incompatibility and Source byte drift before dispatch. Success guards forbid HTTP acquisition and native source registration from being repeated. The only success provider operations are extraction and existing downstream semantic processing; no routing operation exists on this path.

## Verification results

- Focused: 25 passed; full JUnit also includes all 25 cases.
- Related Workbench/lifecycle/Stage 7/7.1/7.2A/LLM selection: 294 passed in the full run.
- Full repository: 2434 passed, 2 skipped, 4 failed, 29 errors (2469 total).
- Historical ledger: exactly 33 matches by node, status and exception class; no missing exception and no new regression.
- Frontend: 159 passed in 29 files. TypeScript/production build: PASS. Compileall: PASS.
- Projection and explicit diagnostic class/request-ID assertions were also run separately and passed.

Local JUnit: `workspace/stage72b_full_final.xml` in the root checkout, SHA-256 `fe0185f3ee78241e2ca0717dae84a2837aa9dd9f0b400aad23f02561ccf671f2`. Compare reference: `docs/phase43_stage7_full_suite_exception_audit.json`. Existing failures/errors are retained as exceptions, not described as passed tests.

The full run uses the established historical local fixture environment. A temporary test-only hook loads the current changed runtime modules; unchanged code/scripts remain in the root checkout. Provider credential environment variables are cleared. No configuration or credential is copied or committed. The two unrelated untracked root tests are excluded. Current Stage 7.2A tests and Stage 7.2B tests are explicitly collected with importlib mode; temporary fixture files stay under configured workspace.

Early targeted runs exposed test-fixture assumptions (invalid Run SUCCEEDED enum, comment-only config edits, OS read-only synthetic PDF) which were corrected. An isolated-worktree lifecycle check also saw the known LF/CRLF fixture-byte issue; the final historical-environment run resolves that difference. An early full run was stopped to finish retry statistics; only the completed final JUnit supports this qualification.

## Real-state immutability

| Database | Before | After |
| --- | --- | --- |
| Production | `6e5a303ccee9c192c350c2550cc232649e56ffee939b7a09cd6b170cc1c8fba1` | `6e5a303ccee9c192c350c2550cc232649e56ffee939b7a09cd6b170cc1c8fba1` |
| Workbench | `1ff852dbe76c5fc4054c3e6f4e308b98a66f918dc3081e287b793c682a61ca44` | `1ff852dbe76c5fc4054c3e6f4e308b98a66f918dc3081e287b793c682a61ca44` |

Real provider calls, ZSXQ reads/downloads/writes, Production writes and real Workbench writes are all zero. No real schema migration, Source/Run/attempt edit, Domain assignment, review approval or Pilot retry occurred. The prior failed attempt remains intact.

## Compatibility limit and handoff

Current cloud profile drift is handled with complete frozen values. Missing/changed native TOML cannot be reconstructed from its digest and blocks. Existing Git/code/native runtime guards remain strict. The real Stage 7.2 Run's previously observed runtime mismatch is **not bypassed**; synthetic PASS must not be interpreted as permission or proof that the old real Run can execute on this release. Any runtime compatibility work requires a separate reviewed scope and pre-call proof.

Perform a separate pre-merge audit of Stage 7.2B. Do not merge and do not retry the real Stage 7.2 pilot yet.
