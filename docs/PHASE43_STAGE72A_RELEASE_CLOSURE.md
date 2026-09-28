# Phase 4.3 Stage 7.2A — release closure

**Closure finding: PASS when this report and its receipt are persisted to remote main through the dedicated closure PR.** Before that merge, implementation release verification is complete and evidence persistence is pending. This record closes Safe Provider Failure Diagnostics only. The original real DeepSeek extraction failure has not been shown to be solved; the released capability makes a future authorized attempt diagnosable with safe structured metadata.

## Release identity and governance

The 2026-09-28 handoff fetched origin and verified the exact frozen base and PR #76 head. The PR was OPEN, Draft, unmerged, and mergeable. Its 15-file diff contained four diagnostic/provider runtime modules, three tests, and eight qualification/audit documents. The last commit added only the two final re-audit evidence files; the audited runtime and tests were unchanged. No private pilot material, credentials, configuration secrets, database dump, or provider response body was added.

GitHub reported no branch protection, no applicable branch rules, no required review decision, no unresolved review conversations, and no status checks. The applicable rules contained no merge queue requirement. After Ready for Review, PR #76 was OPEN with `draft=false`, the same head/base, CLEAN/MERGEABLE status, and no check or workflow run. It was merged without administrative bypass, using the merge-commit convention demonstrated by PRs #70–#75 and a head-match guard.

| Identity | SHA |
| --- | --- |
| Audited base / merge first parent | `9179e28e73c8658b4893729a90f40166f556a0bd` |
| Initial diagnostic code | `25c4d51170b69455be6fc08c5e9e203f27be86b6` |
| Initial qualification / originally blocked audit head | `93298cd6337df61b286d3c88ccfc07056ad99901` |
| R1 repair code | `658e13e11a18abe44e4b6ea654790f6220de0f8d` |
| R1 qualification / final re-audit target | `ce81f6172f304b7e1f0a1a411a59f9993a006035` |
| Final re-audit evidence / actual merged PR head | `b6beee5b9ebfc17ff3061a55421abc407be1ebc0` |
| PR #76 merge / remote main at closure preparation | `bc40a9d1c2827fa78ebac8b10ea6a295719cf897` |

PR #76 merged at `2026-09-28T01:21:12Z` and was re-read as MERGED, non-Draft, with the expected final head. A post-merge fetch verified both merge parents, all five implementation/qualification/audit ancestors above, and exact tree equality between the merged head and remote main. Thus the merge introduced no unqualified code. The main SHA in this document and receipt is the point-in-time value after PR #76; the subsequent evidence-only closure PR advances main.

The initial pre-merge BLOCKED decision remains preserved for its original head. R1 repair qualification and final re-audit PASS remain separate historical records. This closure does not replace those records.

## Released capability and qualification

Merged main contains the exact qualified support for `failure_stage`, `error_class`, actual `http_status`, validated `provider_request_id`, `retryable`, `error_fingerprint`, and generated `safe_error_summary`. HTTP 401 retains authentication classification, `HTTP_RESPONSE`, and the original Job/Run behavior. HTTP 200 remains 200 through later provider JSON parsing, model output parsing, application validation failure, and rejected-result recovery.

The final re-audit established business equivalence using eleven Job and three Source Run differential scenarios against frozen main. Unexpected exceptions propagate as before; retry decisions, public errors, completion criteria, and Run behavior preserve the existing contract. Diagnostic metadata does not determine the business outcome.

Known request-ID headers pass through bounded validation; generic response IDs and unsafe candidates are excluded. Central allowlists constrain external diagnostic values before new event/result persistence. Failure diagnostics and rejected provider result artifacts do not copy full prompts, request/response bodies, private source text, Authorization, API keys, cookies, sessions, or unsafe request IDs. Existing private Source/input artifacts retain their pre-existing Workbench contract. The final re-audit's DB, API, artifact, and log sentinel checks all passed.

No DB migration was introduced. Old event JSON and artifact formats remain readable; the new diagnostic fields are additive. Successful calls and Stage 7.1 `SHARED_CORE_PENDING` / `PENDING` semantics are preserved. The historical `run-domain-context-v1` nonfake-provider path still requires Domain activation where its existing contract requires it.

The frozen final qualification is 19/19 existing plus 9/9 audit-regression diagnostic cases, 2409 passed / 2 skipped / 4 failed / 29 errors in the full backend suite, and 159/159 frontend tests with TypeScript/build PASS. All 33 backend exceptions matched the historical ledger by node, status, and exception class; `NEW_REGRESSION = 0`. These are inherited qualified results, not a claim that the suite was rerun during closure. Exact merged-tree equality and the absence of new required checks make the existing qualification applicable.

## Real state and release limits

Actual file hashes were measured before handoff and after implementation merge/closure verification:

| State | Before and after SHA-256 |
| --- | --- |
| Production | `6e5a303ccee9c192c350c2550cc232649e56ffee939b7a09cd6b170cc1c8fba1` |
| Real Workbench | `1ff852dbe76c5fc4054c3e6f4e308b98a66f918dc3081e287b793c682a61ca44` |

Real provider calls, real ZSXQ reads/writes, Production writes, and real Workbench writes were zero. The existing pilot Source/Run was not modified or retried. No Source/Run creation, Domain assignment/registration, Claim approval, Production Apply, Current View, or Direct Impact action occurred.

`VERSION_ACTION = NO_VERSION_BUMP`; `TAG_ACTION = NO_TAG`. This follows the Phase 4.3 substage convention and Stage 7.1 closure precedent. Project metadata stays at the established `0.5.1` release; no per-substage version or tag is introduced.

## Evidence persistence and stop boundary

This report and `phase43_stage72a_release_closure_receipt.json` are the only changes on `codex/phase43-stage72a-release-closure`, created from verified post-PR-#76 main. They must be merged through a separate PR under repository governance. Full closure becomes effective only after a fresh remote fetch verifies the closure commit and both exact files on main alongside the implementation, R1 repair, and final re-audit evidence. This condition avoids claiming that branch-only evidence has closed the release.

After that verification, stop Stage 7.2A. A separately authorized step may perform exactly one bounded retry of the existing blocked Stage 7.2 Source/Run, using the same material and `SHARED_CORE_PENDING` basis. It must not reacquire community material, create a new Source, assign a Domain, approve Claims, or write Production.
