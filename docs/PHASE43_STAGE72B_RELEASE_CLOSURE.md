# Phase 4.3 Stage 7.2B — Release handoff and closure

**Closure finding: PASS when these exact closure artifacts are persisted and verified on remote main through the dedicated closure PR.** Implementation release is verified; evidence persistence is pending until that condition is met. This follows the Stage7.1/7.2A closure convention.

## Code release and activation

- CODE_RELEASE = ACTIVE_ON_MAIN
- GENERIC_STAGE72B_CAPABILITY = RELEASED
- REAL_WORKBENCH_EXTENSION = NOT_PREPARED
- OPERATIONAL_ACTIVATION = DEFERRED
- ORIGINAL_STAGE72_REAL_RUN_RETRY_READINESS = BLOCKED_RUNTIME_INCOMPATIBLE

Stage7.2B releases explicit same-Run extraction retry for Runs whose frozen runtime/context/configuration satisfy the existing compatibility checks. A compatible failed Run can receive a new Attempt/Job while preserving its original execution history. Historical Runs do not automatically gain cross-release compatibility.

The additive extraction_retries extension is intentionally not activated on the real Workbench. Activation requires a later explicitly authorized operational stage. This deferred activation is a valid code-release closure and does not establish real retry readiness.

## Git identity and governance

| Identity | SHA |
| --- | --- |
| Audited base / merge first parent | `4c1c98a1dc4bc85f807c5817ab9fd5a9058378bd` |
| Initial implementation | `a38c1fcee7c372bcbc4475e2b398b13516b5d523` |
| Initial qualification / first BLOCKED audit head | `61c794df26893362f08cc712035b6da60bb1ada4` |
| R1 repair code | `54547523952256e37e9a7f3f7d0310e39c4a2db9` |
| R1 qualification / final audit target | `d2c732f8a46cbd806f6dd85411dc94f96657a797` |
| Final re-audit evidence / merged PR head | `402dc30ba03ebe2c7457fe8dafb9bc4109b4205d` |
| PR78 merge / main after implementation release | `505ba2be8463ddc00e85bf2ad7253cd42dbdcb7b` |

PR #78 merged at `2026-09-28T04:53:00Z` and was reread as MERGED, non-Draft, with the exact audited head. A fresh fetch verified both merge parents, all implementation/R1/audit ancestors, and exact tree equality with the qualified head. Its 14-file scope contains only Stage7.2B source, tests and documentation; audited source hashes remain unchanged. No private Community body, credential, DB dump or configuration secret was added.

The stale PR body was replaced before Ready with the R1/final re-audit PASS results, current test counts, historical exceptions and separate operational limits. The published body was compared to the prepared text. Metadata refresh did not change the head.

GitHub reported no branch protection or applicable rules, required reviews/checks, unresolved conversations or merge queue requirement. After Ready, the head/base remained frozen, status was CLEAN/MERGEABLE, and both checks and workflow runs were empty. A final read and --match-head-commit guard preceded merge. No administrative bypass was used. Merge commits match preceding Phase4.x PRs, including implementation #76 and closure #77.

## Capability and qualification

Read-only code inspection plus exact audited-source/tree equality verifies retry_failed_extraction, the private operator prepare-extraction-retries command, authenticated/Origin/CSRF-protected strict retry API, retry-lineage projections, and CloudJobs dispatch handling on main.

The capability retains same Run, new Attempt/Job, immutable original Attempt history, append-only lineage, explicit Unicode single-line reason, database-global idempotency and serialized concurrency protection. Frozen Source/Run/Shared Core/provider/model/prompt/runtime/configuration/native-checkpoint checks remain mandatory. Retry performs no reacquisition, rerouting or new Run creation. Each explicit retry permits at most one extraction dispatch, even for retryable provider errors. Reprocess remains a separate new-Run operation.

The final audit's **58 focused passes**, **294 related passes**, and full repository **2444 passed / 2 skipped / 4 failed / 29 errors** are inherited without a new test run during closure. All 33 exceptions match the historical ledger exactly by node/status/exception class; NEW_REGRESSION = 0. Build and compileall passed. Runtime and tracked tests did not change after that audit; no new required CI check arose during handoff.

Historical documents retain initial qualification PASS → first pre-merge audit BLOCKED → R1 PASS → final pre-merge re-audit PASS. The original historical BLOCKED audit files remain local and unchanged; committed R1/final audit records preserve their result and hashes.

## Historical runtime gate

Original Source `SRC_C70218574FB158D7`, Run `SOURCE_RUN_BBADD851DA1E4526BAB9B6EBD1DBDCF0`, remains **BLOCKED_RUNTIME_INCOMPATIBLE**.

| Runtime observation | SHA-256 |
| --- | --- |
| Frozen historical real Run | `ef7fb67f6057f5c9532990aa2e692a320eadda00b5b6dc4a271d30a69fa357c2` |
| Final audit target d2c732f | `90266971ab3da1030324e2492a6f324dfd6064e43458cd4791745b50dec61367` |
| Released implementation merge 505ba2b | `9b96ebf4a9d68367e4aca0bc3abc25a9f81171ede84761396a24e8d90d5d146f` |

The released value was computed from the verified merge source, using schema11 and stage72-deepseek-dual-v1, without opening the Workbench or calling a provider. The existing Git component means a later documentation merge has another identity; this table scopes the measured value to implementation release.

The preserved blockers are RETRY_FROZEN_CONFIG_INCOMPLETE, PROCESSING_RUN_CONTEXT_DRIFT, and CODE_OR_RUNTIME_CONTRACT_INCOMPATIBLE. Closure verifies the unchanged audited guards; it does not repeat the historical acceptance probe. No override, old-runtime backfill, SHA bypass, Run rewrite or native checkpoint rewrite occurs.

## Real-state verification

| State | Before and after SHA-256 |
| --- | --- |
| Production | `6e5a303ccee9c192c350c2550cc232649e56ffee939b7a09cd6b170cc1c8fba1` |
| Workbench | `1ff852dbe76c5fc4054c3e6f4e308b98a66f918dc3081e287b793c682a61ca44` |

Fresh byte hashes match the frozen values. A SQLite immutable read-only sqlite_master query confirms extraction_retries is absent; no live WAL was present. All provider/DeepSeek calls, ZSXQ reads/downloads/writes, Production and real Workbench writes, and real retry commands are zero. No real Attempt/Job, acquisition, Domain assignment/pack registration, Claim approval or Production Apply occurs.

## Evidence persistence and final verification

This report and receipt are the only changes on `codex/phase43-stage72b-release-closure`, based on verified implementation main. They must be pushed, reviewed under current repository rules and merged through a dedicated closure PR; never directly pushed to main. Final closure PASS requires a fresh fetch proving exact artifact blobs and the implementation/R1/audit/closure ancestors are reachable from remote main.

The final remote main SHA is the closure PR's actual merge commit and is recorded in that PR's metadata and the final verification/handoff output. The receipt includes an explicit null plus a machine-readable resolution rule until that future merge exists. It does not mislabel the implementation SHA as final main or invent a self-referential future commit. The closure PR body is updated with observed evidence commit, merge SHA and final remote main after verification.

## Version and local main

VERSION_ACTION = NO_VERSION_BUMP; TAG_ACTION = NO_TAG, following Phase4.3 substage policy and prior closure. No release tag is created.

LOCAL_MAIN_SYNC = DEFERRED_WORKTREE_BOUNDARY. Local main is `9179e28e73c8658b4893729a90f40166f556a0bd` in the primary worktree, which contains preexisting untracked/private files and local configuration. This task preserves that working state; it does not claim local main is synchronized. After preserving/reviewing that worktree, the PowerShell fast-forward commands are:

```powershell
Set-Location -LiteralPath 'D:/ej/材料/codex/get_knowledge/pro_a_v0_1'
git switch main
git pull --ff-only origin main
```

## Stop boundary

NEXT_ACTION = STOP Stage 7.2B. The generic same-Run retry capability is released, but the original Stage 7.2 real Run remains BLOCKED_RUNTIME_INCOMPATIBLE and the real Workbench extraction-retry extension remains intentionally unprepared. In a separately authorized Stage 7.2C, qualify bounded cross-release retry compatibility without weakening or bypassing frozen runtime/context gates.
