# Phase 4.3 Stage 7.2B — Final pre-merge re-audit

**PHASE43_STAGE72B_FINAL_PREMERGE_REAUDIT = PASS**

**ORIGINAL_STAGE72_REAL_RUN_RETRY_READINESS = BLOCKED_RUNTIME_INCOMPATIBLE**

These are separate gates. The generic same-Run retry capability is eligible for release handoff; the old real Stage7.2 Run is not eligible for retry after release. Its cross-release compatibility belongs to a separate Stage7.2C.

## Audited boundary

Base `4c1c98a1dc4bc85f807c5817ab9fd5a9058378bd`; exact audit target `d2c732f8a46cbd806f6dd85411dc94f96657a797`; PR #78 OPEN / DRAFT / UNMERGED / MERGEABLE, four commits and twelve changed files at audit start. Fetch confirmed no head/base drift. No application source or tracked test changed during this re-audit.

R1 range `61c794df26893362f08cc712035b6da60bb1ada4`..`d2c732f8a46cbd806f6dd85411dc94f96657a797` changes six files: one added validation line in extraction_retry.py, the Unicode test file and four documentation files. Runtime identity, CloudJobs dispatch, state/lineage, provider, schema and reprocess implementations have no R1 change. The final evidence commit is documentation only: this report/receipt and the explicit global-idempotency contract clarification previously held locally. Prior BLOCKED audit artifacts remain unchanged and local.

## Complete gate matrix

Implementation was reread and compared against the full PR diff. The following results are backed by fresh executions at the target, not merely the earlier qualification summary.

| Gate | Result | Implementation and verification |
| --- | --- | --- |
| git_boundary | PASS | Fetched main/base/target match; PR OPEN/DRAFT/UNMERGED/MERGEABLE, four commits and twelve files at target. |
| r1_diff_scope | PASS | 61c794d..d2c732f: one added service predicate, one Unicode test file and four documentation files; no other application source change. |
| unicode_single_line_validation | PASS | extraction_retry.py:129-137; LF/CR/VT/FF/NEL/LS/PS plus C0/DEL rejected by fresh R1 matrix and original independent Unicode reproductions. |
| service_level_validation | PASS | Direct retry_failed_extraction calls bypass Pydantic and return INVALID_RETRY_REASON/status422 for embedded Unicode separators. |
| api_level_validation | PASS | Authenticated actual endpoint returns HTTP422/INVALID_RETRY_REASON for NEL/LS/PS; the former U+2028 HTTP200 path now fails closed. |
| invalid_reason_no_write | PASS | Each invalid matrix entry compares exact Run/Job/Attempt/retry/Run-event/Job-event rows plus dispatches/outcomes; all unchanged. |
| valid_unicode_reason | PASS | Eight accepted API cases retain exact Chinese/English/mixed/digits/punctuation/fullwidth/internal U+3000/emoji/1000-character strings in storage and direct-service duplicates. |
| retry_reason_security_regression | PASS | Fresh service+API audit covers Bearer, api_key=, apikey=, token=, cookie=, authorization=, all rejected without writes; R1 matrix retains controls/trim/markup. |
| contract_implementation_alignment | PASS | Complete Stage72B state, frozen identity, transaction, lineage, dispatch and reprocess contract mapped to fresh tests below; Unicode blocker closed. |
| run_attempt_model | PASS | Frozen Run identity and current projection are distinct; acceptance changes FAILED projection to EXTRACTION_PROCESSING with append-only event, without replacing the Run. |
| original_attempt_immutability | PASS | Original cloud_jobs/cloud_attempts/dispatches/outcomes/job-events and Run event prefix remain identical on success, failure and retry-of-retry. |
| retry_acceptance_atomicity | PASS | BEGIN IMMEDIATE includes lookup/checks/Job/lineage/events/projection. Four injected SQL boundary failures reach their targets and roll back complete table snapshots. |
| retry_lineage | PASS | Append-only extraction_retries links Run/root Job/new Job/reserved attempt/parent/reason/key/context. UPDATE/DELETE rejected; original binding preserved. |
| attempt_numbering | PASS | Terminal-parent number+1 inside the transaction, with UNIQUE(root_job_id,attempt_number); independent 1->2->3 reconstruction plus concurrent request tests. |
| idempotency_semantics | PASS | Database-global key lookup and UNIQUE constraint deliberately identify command intent; same intent returns prior identity, changed reason or other existing Run conflicts. Contract clarification included. |
| concurrent_retry_protection | PASS | Same-key threads share one reservation/Job; different-key threads for one parent allow one acceptance and RETRY_ALREADY_IN_PROGRESS. |
| retry_eligibility | PASS | FAILED/EXTRACTION_JOBS/PROVIDER_ERROR and latest effective terminal FAILED/KNOWN_FAILURE required; successful/review/acquisition/security/context/unknown/nonlatest/other Run/lease/queued/running cases reject. |
| retry_vs_reprocess_separation | PASS | Retry keeps Source/Run count and run_id; start(reprocess_reason) creates a different Run and retains its separate basis rules. |
| no_reacquisition | PASS | Success test forbids HTTP acquisition, Source upload and native start_execution; immutable Source/input/checkpoint reused without Community/ZSXQ access. |
| no_rerouting | PASS | frozen_cloud/frozen_service reconstruct persisted profile and original context; no current model or Domain selection replaces the frozen values. |
| frozen_execution_semantics | PASS | Original source/input hashes, context, Shared Core, provider/model/aliases/limits, prompt/runtime/config and SOURCE_READY native checkpoint guarded; changed native config/runtime rejects. |
| runtime_identity_change | PASS | Including extraction_retry.py in domain_code_sha256 protects orchestration/authorization semantics. Two fresh processes at target produce identical verified runtime digests. |
| normal_execution_regression | PASS | No-retry paths retain original service/bindings and ordinary policy. Fresh full Workbench/Stage0 Domain/Stage71 pending execution checks retain only the historical exception set. |
| retry_dispatch_identity | PASS | Independent audit equates reserved ID/number, CloudRequest, persisted cloud_attempts and dispatch event; local Job attempt_count=1 vs lineage number2/3. |
| one_dispatch_per_retry | PASS | HTTP503/retryable=true double causes one dispatch per explicit Job and terminal failure; next dispatch requires another explicit command. |
| successful_retry_continuation | PASS | One extraction retry plus one separate downstream semantic double reaches review packet/HUMAN_REVIEW_REQUIRED on the same Run. |
| stage72a_regression | PASS | Fresh diagnostic suite and retry failure assertions preserve stage/class/status/validated request ID/retryable/fingerprint/summary and secret/body protections. |
| stage71_context_immutability | PASS | Later Source Domain assignment leaves the original pending Run context/Shared Core SHA unchanged; current cloud drift cannot replace frozen request identity. |
| schema_extension | PASS | Explicit private operator prepare only; real schema9/10/11 fixtures retain metadata/history, missing-extension reads work, prepare idempotent, FK clean, backup/restore and append-only triggers pass. |
| api_security | PASS | Authentication, Origin, CSRF, strict extra-forbid and no provider/model/Source/Domain/runtime/prompt/context overrides verified; Unicode service guard is reached through actual HTTP endpoint. |
| historical_runtime_gate_unchanged | PASS | R1 touches no compatibility implementation; current synthetic runtime/config drift tests still reject. Historical isolated-copy finding preserved without new real-Run acceptance or override. |
| real_state_immutability | PASS | Fresh before/after Production and Workbench hashes identical; all mutated databases are synthetic fixtures. |
| documentation_accuracy | PASS | Initial qualification PASS, first audit BLOCKED, R1 PASS and historical runtime BLOCKED retained. Current final generic PASS has no implication of historical retry readiness. |

## Contract → executed test mapping

The main tests are `tests/test_phase43_stage72b_extraction_retry.py` and `tests/test_phase43_stage72b_unicode_reason.py`. Independent audit scripts below are ignored local files under the root checkout's workspace, imported against the exact worktree source.

| Clause / concern | Executed evidence |
| --- | --- |
| unicode_and_no_write | tests/test_phase43_stage72b_unicode_reason.py (10 cases; 55 service inputs and 55 API inputs, 8 valid reasons) |
| same_run_and_immutability | test_success_same_run_context_history_and_no_acquisition_routing; test_failure_diagnostics_no_auto_retry_and_retry_of_retry |
| atomicity | workspace/test_stage72b_premerge_audit.py::test_acceptance_fault_rollback[before_retry_insert,after_job_insert,after_retry_insert,before_projection] |
| lineage_and_dispatch | test_dispatch_identity_and_lineage_reconstruction; test_schema_additive_idempotent_and_lineage_append_only |
| idempotency_concurrency | test_database_global_key_scope_and_wrong_existing_run; test_duplicate_and_active_guard; test_concurrent_commands_allocate_once[True,False] |
| eligibility | test_unsupported_run_states_rejected; test_additional_eligibility[lease,queued,running,successful,unknown_outcome,nonlatest]; wrong-existing-Run audit |
| frozen_identity | test_frozen_cloud_configuration_and_later_domain_assignment; test_missing_frozen_configuration_fails_closed; test_direct_worker_uses_frozen_profile_and_blocks_source_drift; test_runtime_drift_is_not_silently_overridden |
| reprocess | test_retry_and_reprocess_are_separate; ordinary Stage7/Stage71 reprocess tests in full JUnit |
| schema_and_api | test_extension_missing_reads_and_real_schema_versions[9,10,11]; test_extension_backup_restore_preserves_lineage; original and independent API auth/Origin/CSRF/override tests |
| credentials | workspace/test_stage72b_final_security.py::test_credential_spellings_no_write[service,api] |
| diagnostics_and_normal_execution | Full JUnit Stage72A, Stage71, Workbench, lifecycle/reprocess, Stage0 Domain and LLM tests |

### Unicode and API blocker closure

The service's `splitlines() != [retry_reason]` predicate rejects rather than normalizes. LF/CR/VT/FF/NEL/LS/PS, including standalone/trailing forms, return INVALID_RETRY_REASON/status422; actual authenticated API calls for NEL/LS/PS return HTTP422. The original U+2028 HTTP200 reproducer now passes its expected-422 assertion.

For every invalid matrix entry, Run/Job/Attempt/retry/event rows and counts are identical before/after. The matrix includes all C0 controls, DEL, trim/markup and credential forms. Additional independent service/API cases explicitly cover `apikey=` as well as `api_key=`, Bearer, token, cookie and authorization. Empty/overlong API strings retain the existing Pydantic 422 boundary. Valid Chinese, English, mixed text, digits, ordinary/fullwidth punctuation, internal U+3000 and emoji remain unchanged in accepted responses/storage. No ASCII-only restriction or internal replacement is introduced.

### State, transaction and immutable history

Run identity is frozen; Run state is a current projection backed by append-only events. Retry moves the same Run projection from FAILED to EXTRACTION_PROCESSING and then FAILED or HUMAN_REVIEW_REQUIRED. The prior failed Attempt and its Job/dispatch/outcome/event records remain identical.

One BEGIN IMMEDIATE covers global key lookup, eligibility, active-work checks, frozen checks, new Job/reservation/events and projection update. Store.connect commits only after successful return. Faults before retry insertion, after Job insertion, after retry insertion and before projection update each leave all table snapshots unchanged: no orphan Job/reservation/event or partial projection survives.

The pending lineage reserves a new attempt ID; cloud_attempts is populated at dispatch intent with that same ID. Root/parent links reconstruct 1→2→3; the transaction derives the next number from the terminal parent and enforces uniqueness. A retry Job's local attempt_count=1 is independent from lineage number2/3; request and event identities match. UPDATE and DELETE of lineage are forbidden.

Idempotency keys deliberately have Workbench-database scope. Same key/same intent returns the same reservation even after completion; changed reason or another existing Run conflicts. Concurrent same-key requests allocate once; different keys for the same failed parent permit one acceptance. The explicit contract clarification is included in this audit evidence commit without changing implementation.

### Frozen execution and dispatch

Complete stored provider/model/aliases/timeout/token/budget identity is reconstructed and compared to its hash/columns/context. Original source profile/native configuration references remain digest guarded. Source/input bytes, context/Shared Core, prompt/runtime and SOURCE_READY native checkpoint must validate; current operator cloud changes and later Domain assignment do not replace old execution semantics.

Retry reuses original immutable Source/artifacts. The success test guards HTTP acquisition, upload and native start_execution. One explicit command authorizes at most one extraction dispatch, including HTTP503/retryable=true. Successful retry makes one extraction call and one distinct downstream semantic call through doubles, then creates the review packet on the same Run. Reprocess remains a separate new-Run command.

## Runtime identity and the historical Run

Hashing extraction_retry.py is consistent with the existing conservative orchestration identity: that module controls frozen context reconstruction, effective Job selection and acceptance authorization. The preexisting domain_code_sha256 already includes source_operations/cloud_jobs/artifacts. This changes identities for normal as well as retry Runs on schema9/10/11; schema7/8 lack that domain hash, while the existing Git component still changes with commits. Ordinary no-retry execution retains original service/Job behavior, confirmed by full regression.

Two independent processes loading the exact target computed identical valid runtime identities. No database was opened by this identity check. Identity values are explicitly scoped:

| Observation | Runtime SHA |
| --- | --- |
| Frozen historical real Run | `ef7fb67f6057f5c9532990aa2e692a320eadda00b5b6dc4a271d30a69fa357c2` |
| Current code during the first audit at `61c794df26893362f08cc712035b6da60bb1ada4` | `f7181953f6bd4e3126cb7184c598f4d0d2742670521cef1d71232cc58cbedd35` |
| Current code at this audit target `d2c732f8a46cbd806f6dd85411dc94f96657a797` | `90266971ab3da1030324e2492a6f324dfd6064e43458cd4791745b50dec61367` |

The first audit's f718… value is a historical code snapshot, not the identity of the repaired target. A subsequent documentation commit also changes the preexisting Git component; the receipt's current identity is bound to the audit target, not an unmeasured later commit. No old runtime/context value or native checkpoint is rewritten.

The first actual isolated-copy compatibility probe returned RETRY_FROZEN_CONFIG_INCOMPLETE; its independent context/native checks reported PROCESSING_RUN_CONTEXT_DRIFT and CODE_OR_RUNTIME_CONTRACT_INCOMPATIBLE. Those findings remain preserved. This re-audit does not repeat historical acceptance or try to make it pass. R1 diff plus fresh synthetic runtime/config rejection tests establish unchanged gates; the current target identity still differs from the frozen old identity. Historical readiness remains **BLOCKED_RUNTIME_INCOMPATIBLE**, independently of generic PASS.

## Schema, diagnostics and security

The extension is private operator-only, explicit/additive/idempotent, with no startup migration. Actual schema9/10/11 fixtures exercise missing-extension read paths, unchanged historical rows/version metadata, clean foreign_key_check, repeated preparation and coordinated backup/restore with append-only lineage retained. Real Workbench preparation is prohibited and was not performed.

Fresh Stage72A tests retain validated failure-stage/class/status/request ID/retryability/fingerprint/summary and no-secret/no-body persistence behavior. Stage71 tests and the frozen-cloud/later-assignment retry test retain original Shared Core Pending context. Auth/Origin/CSRF, strict Pydantic extra-forbid and Source/provider/model/prompt/Domain/runtime/context override rejection remain enforced.

## Fresh regression results

- Exact-target focused suite: **58 passed** (25 retry + 10 Unicode + 21 independent audit + 2 credential-spelling cases).
- Related Workbench/lifecycle/Stage7/Stage71/Stage72A/LLM selection: **294 passed** in the full run.
- Full repository: **2444 passed, 2 skipped, 4 failed, 29 errors** (2479 cases).
- Historical exceptions: **33 exact matches by node/status/exception class**, zero missing, **zero new regression**. Historical failures/errors are retained as exceptions, not described as passed.
- Production build and compileall: **PASS, exit 0**. Frontend tests were not rerun because no frontend code changed.

The full suite uses the established historical fixture environment: root fixture paths/config are retained and a test-only import hook loads current changed modules. Credential variables are cleared. Current Stage72A/Stage72B/R1 tests are collected from the worktree; two unrelated preexisting untracked root tests are excluded. The separate focused suite loads the entire exact worktree source with explicit pytest configuration. No application source or tracked test was edited during this audit.

## Real-state protection

| Database | Before | After |
| --- | --- | --- |
| Production | `6e5a303ccee9c192c350c2550cc232649e56ffee939b7a09cd6b170cc1c8fba1` | `6e5a303ccee9c192c350c2550cc232649e56ffee939b7a09cd6b170cc1c8fba1` |
| Workbench | `1ff852dbe76c5fc4054c3e6f4e308b98a66f918dc3081e287b793c682a61ca44` | `1ff852dbe76c5fc4054c3e6f4e308b98a66f918dc3081e287b793c682a61ca44` |

Real provider/DeepSeek calls, ZSXQ reads/downloads/writes, Production writes and real Workbench writes are all **0**. No real retry/preparation, acquisition, Domain assignment/pack registration, Claim approval, Production Apply, mark-ready or merge occurs in this audit. All test mutations use disposable synthetic state.

## Documentation history and evidence

The audited documents retain: initial qualification PASS → first audit BLOCKED (Unicode B1) → R1 repair PASS → this final generic re-audit PASS. Historical real Run readiness stays runtime BLOCKED throughout. The first BLOCKED report/receipt remain byte-identical to the hashes recorded by R1. No qualification document is relabeled to erase its historical scope.

Evidence paths are relative to the root checkout; audit-only scripts/logs remain local. The receipt records per-gate evidence, source hashes, complete exception identities, and both historical/current runtime snapshots. No private material body or credential is included.

| Evidence | SHA-256 |
| --- | --- |
| `workspace/stage72b_final_full.xml` | `a9c7282fd84cb14c309edd0cc9925b75df59677bed7c526f65a24a553238eb57` |
| `workspace/stage72b_final_full.log` | `dd950f12f1b315d21bff2b63fcbb9c5a79b6499aacb8018a9454bba58c32c42a` |
| `workspace/stage72b_final_focus.xml` | `b62c2d593dfe87f32e0d9ba50f48e4d412f0de11b0767d8ea35a4743c225f8fe` |
| `workspace/stage72b_final_focus.log` | `f8248aa308260c69ca1945e75b10810b67e75c73694d696ac5cf5be9ebff37c1` |
| `workspace/stage72b_final_build.log` | `75936883d90e6c74f1318b3788a5c8f68a76a2a76f1ce0bd2efda085e22fe4a7` |
| `workspace/stage72b_final_runtime_identity.json` | `4d4576d60cfe6213f86adb28871789fe6241deebe14cc7688dc26327e44c5879` |
| `workspace/stage72b_final_runtime_identity_repeat.json` | `4d4576d60cfe6213f86adb28871789fe6241deebe14cc7688dc26327e44c5879` |
| `workspace/stage72b_final_runtime.py` | `438a5fb10a40bd46dd5dd25f3b5db87bd1759f8f20a2c3ff90cc4c64dd3dcedb` |
| `workspace/test_stage72b_premerge_audit.py` | `10e903a9b4689434bb19e8d2023c7f8dd238fa7ef9d78fe899faab77071b69af` |
| `workspace/test_stage72b_final_security.py` | `d28ac78bd1668b04ef1b4d98d176edd73ae3e385290acccfbeb9c1467e5be872` |
| `workspace/stage72b_env/sitecustomize.py` | `25133d3129c05734fc23d3d0157e5218e3e2e5a720fba31f0aebb4ec2e440766` |

## Handoff

One documentation-only evidence commit is authorized after PASS and pushed to the existing PR branch. Keep PR #78 OPEN / DRAFT / UNMERGED during this step. The final commit SHA and remote state are verified after push and reported separately.

NEXT_ACTION = Stage 7.2B generic same-Run retry capability is eligible for release handoff. Mark PR #78 Ready, merge it under repository governance, verify remote main, and complete Stage 7.2B release closure in a separate step. Keep the original Stage 7.2 real Run classified as BLOCKED_RUNTIME_INCOMPATIBLE. Do not retry that historical Run after release; address cross-release retry compatibility in a separate Stage 7.2C.
