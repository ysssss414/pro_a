# Terminal queue migration repair and PR96 delta qualification

`TERMINAL_RUN_ORPHANED_QUEUED_JOB_MIGRATION_R1 = PASS`.
`PR96_DELTA_REQUALIFICATION = PASS`.
The [sanitized receipt](pr96_terminal_queue_delta_requalification_r1_receipt.json)
records exact identities, separate test attempts, copied-real-state proofs and safety checks.

Repair [PR98](https://github.com/ysssss414/pro_a/pull/98) is merged. Implementation
`63fcb2df8a838561aded1f41f8e5dc03d47f731f`; candidate evidence/audited PR head
`a51170ff7e9bcfea2539c3771cad30132a760790`; merge/exact main
`9106307ff867af2a53186f5424bb88cec0b73f74`. Its 32 focused and 437 other related
cases qualify (469 unique selected): initial 467 passed/2 failed, all 3 affected
reruns passed. No historical qualification was rewritten and no full-repository
or GitHub-CI green claim is made. The candidate receipt preserves all 14 allowlisted
job classifications and the unchanged strict lifecycle/earlier migration guards.

PR96 reconciliation merge `93e90cfb6ba250d9a28309f1a73099ae0d691ca2` has exact parents
original evidence `e63608e303725db20541ff7d57fb62b584f6fa75` and new main above.
Original implementation `b8cd7e676eb584028804914e07652807b28a6881` remains an ancestor.
Old local `bd8fda2e5e85ff0de8cf24443214fe6d965189be` is not an ancestor and was not pushed.
No rebase, squash or history rewrite. The two conflicts are test fixture semantics:
combine anchored identity with the historical missing-module loader; retain frozen
legacy history generation and truly RUNNING lease blocking. New queued/retry
fixture modes never enable schema11 intake in the current bounded runtime.

The initial delta stopped at a legacy schema11 Stage7.1 live fixture (378 passed,
one failed, one pre-existing private-workflow skip). Live fixtures now prepare
schema12 and use the existing bounded synthetic HTTP provider. The community
fixture names its synthetic candidate in evidence; low-trust, domain, history and
provider-shape assertions remain. A real read-only compatibility gap was found:
community domain listing required schema11 despite unchanged domain tables at12.
Only that whitelist now accepts11/12; three API cases verify schema10 rejection
and no DB writes. Runtime workers, scheduling and provider execution guards were
not relaxed. This addition is on PR96 history, separate from the merged migration repair.

The next attempt stopped after 436 passed, one failed and the same existing skip:
conflict integration had incorrectly changed the native output-telemetry test's
reason to CalledProcessError. The historical missing-module loader instead returns
a changed surface. The original PR96 SEMANTIC_SURFACE_CHANGED assertion was restored;
compatible remains false. No production retry guard changed for this correction.
The complete Stage7.2C module and all remaining modules were then rerun: 163 passed.

Final 19-module delta qualification: 583 unique cases passed,
one existing skip, all 584 collected node IDs covered. Results are aggregated from
the second stopped run and affected/completion run; this is not a claim of one
all-green full matrix invocation. Both raw attempts are retained in the receipt.
The skipped private frozen workflow is unavailable in this
isolated environment; its original skip condition is unchanged. Stage7.1 focused
run: 17 passed. Qualified code head: `91caa2d63e140f63ab65e38e1ca36562c61a451f`.
Compileall, pip check, isolated PEP517, all 137 source/wheel/independent-install
Python byte comparisons, complete schema12 phase4/cloud identity, absent Git,
unrelated parent repository and all malformed/tampered identity cases pass.
After this evidence-only commit, the exact final PR head wheel is rebuilt and
independently reverified; final metadata/head hashes are recorded in the handoff.

Both source and actual independently installed wheel migrate a fresh exact copy
of real Workbench 11→12, classifying exactly 14 pristine queued historical jobs.
All 44 old tables/rows remain exact except schema_version; all old schema objects
remain exact; eight new bounded tables are empty. Backup equals original DB bytes,
idempotence passes, strict operational guard still blocks and nine terminal/global
normal scheduler probes never invoke any CloudJob worker/provider. Original
Production/artifact paths are only validated read-only to preserve exact metadata
bindings; non-copy SQLite writes are forbidden by the qualification harness.

Real Workbench stays11, stable stays exact #97 `7c0a06a0850f3b7a3f0eba80becc9185e91b10c0`.
All 14 jobs/IDs/timestamps/prompts/configs/bindings/attempt counts, all historical
Runs/events/attempts/outcomes, Production, all Current Views and artifacts remain
unchanged. Target Runs1–7 plus one older other-source Run remain; target Run8 is
absent. Provider calls/liability0; no real migration, stable activation or backfill.
Snapshot SHA256 remains `eaeeaa475069f97e4510b3740c4a5530f3052831d0f4ff867b3eda4417459aae`.
Prior READ_BOUNDARY_VIOLATION persists. Actual stable guarded local MCP health/
discovery passes with14 tools,21 read-only connections and all mutation/provider
counters 0. Connected-app health is unavailable because its tunnel client is
offline; no runtime/service/config mutation was performed to reconnect it.

PR96 remains Draft/unmerged. Gate A has not been entered. The separate original
release activation task may resume from its qualified reconciliation; this repair
does not authorize any real migration/activation/provider call or Run8.
