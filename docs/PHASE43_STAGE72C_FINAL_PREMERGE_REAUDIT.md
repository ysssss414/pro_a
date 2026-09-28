# Phase 4.3 Stage 7.2C — Final Pre-Merge Re-Audit

## Result

- `PHASE43_STAGE72C_FINAL_PREMERGE_TECHNICAL_REAUDIT = PASS`
- `PHASE43_STAGE72C_FINAL_PREMERGE_REAUDIT = PASS`
- `PHASE43_STAGE72C_R1_EXECUTION_SURFACE_CLOSURE = PASS`
- `GENERIC_CROSS_RELEASE_COMPATIBILITY = PASS`
- `ORIGINAL_STAGE72_CROSS_RELEASE_COMPATIBILITY = BLOCKED`
- Preserved blockers: `BLOCKED_EXECUTION_CONTRACT_CHANGED`, `BLOCKED_NATIVE_CHECKPOINT_INCOMPATIBLE`
- `HISTORICAL_RUNTIME_GATE_PRESERVED = true`
- `PR_DESCRIPTION_ACCURACY = PASS`

This record persists the independent final technical re-audit. It does not replace or rewrite the original Stage 7.2C qualification or the R1 evidence, and it does not authorize activation or retry of the historical real Run.

## Chronology

1. The initial Stage 7.2C generic qualification passed at implementation commit `0fbd01116100f53b832331deb865976b785a12d6`, with evidence committed at `dfea7e93e216615b8a1d5bded298ad7c6d0b1a21`.
2. Draft PR review identified that the semantic execution surface was not transitively dependency-closed.
3. Before repair, R1 reproduced two real-source false positives through the actual surface-manifest path: one in `CloudJobs._preflight` and one in `SourceOperations._advance_claimed`.
4. Commit `7aaa0c0352a31c344742d623d062bf4f77644004` closed the execution surface and replaced broad normalization with narrow, fail-closed normalization.
5. R1 requalification passed and was recorded at `2aab5b97b600173f389dd0df3081880fa0ae6dc7`, with evidence clarification at `c7df80aebe9aca9c9473c5599fb803bf4e09320d`.
6. The independent final pre-merge technical re-audit validated R1 and passed without requiring another code repair.

## R1 closure validated

The Cloud execution roots are:

- `workbench/cloud_jobs.py::CloudJobs.run_once`
- `workbench/source_operations.py::SourceOperations._advance_claimed`

The native execution root is:

- `phase4_orchestration.py::resume_execution`

Every direct selected `self` helper and local module-function dependency must be represented. An unrepresented dependency fails closed with `EXECUTION_SURFACE_DEPENDENCY_UNCLOSED`; it is not treated as compatible. The final audit validated both Cloud and native dependency closure and the adversarial transitive-drift class.

Normalization is limited to enumerated file, selector, callee, occurrence-count, and exact statement-sequence bindings. Renamed, changed, additional, or ambiguous plumbing is not normalized and therefore changes the surface or fails closed.

The generic cross-release qualification was revalidated as `PASS`. The historical real Run was not reclassified: its Cloud execution contract remains unprovable and its native checkpoint remains incompatible, so the exact historical blockers remain authoritative.

## Git and source freeze

| Item | Value |
|---|---|
| Authoritative base | `origin/main = ec0497df63595fb21dca7b1a7fc91ca81c942ef8` |
| Branch | `codex/phase43-stage72c-cross-release-retry-compatibility` |
| Audited PR HEAD before this evidence-only commit | `c7df80aebe9aca9c9473c5599fb803bf4e09320d` |
| R1 repair commit | `7aaa0c0352a31c344742d623d062bf4f77644004` |
| `src` tree at R1 and audited HEAD | `cf7ae40b5605c60bdd3a5dd7ebc214cc254a3259` |
| `tests` tree at R1 and audited HEAD | `d4f8be2f7526ec6742d154c05d7f688d37e05400` |
| Application source changed after R1 | `false` |
| Test source changed after R1 | `false` |

The only changes after the R1 repair and before this record were R1 documentation/evidence. This final persistence change is also documentation/evidence only. Because neither application nor test source changed, the qualified R1 test evidence remains applicable and no new full-suite run was required.

## Qualified verification evidence

| Suite / check | Result |
|---|---|
| Stage 7.2B + Stage 7.2C focused | `58 passed` |
| Expanded related matrix | `166 passed` |
| Full historical-environment repository | `2477 passed, 2 skipped, 4 failed, 29 errors` (`2512` total) |
| Historical exception reconciliation | `33/33` exact node/status/exception-class set match |
| New regression | `0` |
| Full JUnit SHA-256 | `e8ddfc6b12e23e2354d0c824e6b2653ba026acc9fe245af07554cec8c5b2bbc6` |
| Compileall / CLI / JSON and compatibility-contract evidence / diff check / credential scan | PASS |

The 33 non-passing historical exceptions match the frozen Stage 7.2B baseline exactly. They are not new regressions.

## Historical real-state boundary

| Control | Before | After |
|---|---|---|
| Production SHA-256 | `6e5a303ccee9c192c350c2550cc232649e56ffee939b7a09cd6b170cc1c8fba1` | `6e5a303ccee9c192c350c2550cc232649e56ffee939b7a09cd6b170cc1c8fba1` |
| Workbench SHA-256 | `1ff852dbe76c5fc4054c3e6f4e308b98a66f918dc3081e287b793c682a61ca44` | `1ff852dbe76c5fc4054c3e6f4e308b98a66f918dc3081e287b793c682a61ca44` |
| Real Workbench compatibility extension | NOT PREPARED | NOT PREPARED |
| Real extraction-retry extension | NOT PREPARED | NOT PREPARED |
| Real retry / provider calls / Production writes / Workbench writes | `0` | `0` |
| Real ZSXQ reads / downloads / writes | `0 / 0 / 0` | `0 / 0 / 0` |

No real qualification record, extension activation, retry, provider call, external read/download/write, Production write, or Workbench write occurred.

## PR pre-merge controls

PR #80 remains `OPEN / DRAFT / UNMERGED`. The audited GitHub state reported `MERGEABLE / CLEAN`, zero unresolved review threads, no status checks, no repository rulesets, and no branch protection on `main`. Its description now records the initial qualification, discovered weakness, two false-positive reproductions, R1 repair and requalification, execution roots, fail-closed dependency rule, narrow normalization, current test figures, historical blocked result, and all three evidence layers.

Evidence lineage:

- Original: `docs/PHASE43_STAGE72C_CROSS_RELEASE_RETRY_COMPATIBILITY.md`
- R1: `docs/PHASE43_STAGE72C_R1_EXECUTION_SURFACE_CLOSURE.md`
- Final: `docs/PHASE43_STAGE72C_FINAL_PREMERGE_REAUDIT.md`

## Next action

`NEXT_ACTION = READY_AND_RELEASE_HANDOFF`

That is a handoff only. This step intentionally does not mark PR #80 Ready and does not merge it.
