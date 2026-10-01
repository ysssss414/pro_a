# Installed runtime repository identity R1 — release qualification

**INSTALLED_RUNTIME_REPOSITORY_IDENTITY_R1 = PASS.** Repair [PR #97](https://github.com/ysssss414/pro_a/pull/97)
is merged and its exact main wheel is active in the real non-editable stable
installation. Real phase4/cloud identities, no-Git execution, local read-only MCP
and connected-app health passed. All audited business state is unchanged.
The [JSON receipt](installed_runtime_repository_identity_r1_release_receipt.json)
records exact identities, separate test runs, activation attempts and safety checks.

## Provenance and artifacts

| Item | Exact identity |
| --- | --- |
| Pre-repair main | `389399712deb9d2e1cacf41ad39e147e16b5f14b` |
| Implementation head | `eb94e42bf6f4baeeabac0949f8cf4e278ca3c1b0` |
| Candidate evidence / audited repair PR head | `cc717bb4f130f6601766d0d1f957f75f9408bcc3` |
| Repair merge / final remote main / installed commit | `7c0a06a0850f3b7a3f0eba80becc9185e91b10c0` |
| Final wheel SHA256 | `e9b50070865f862b62259c7b128eea689788e97cea33029cbb7e3a07ee67fcaa` |
| Packaged identity SHA256 | `cf6772bad67dc3504ecd18012a93b4497a3a68eb72bd947e77029b86321ab500` |
| Processing code SHA256 | `cfd6e95cf37563f1a8fff774d09d2839f11284404f111b1e3e1835f82ad9519b` |
| Real schema11 cloud runtime SHA256 | `7d364037d463a923948c0efe5087568a03e4be2d8a7021c9c8d57f31bff0ed29` |

Packaged identity is exactly `pro-a-build-repository-identity-v1`, repository
`ysssss414/pro_a`, commit `7c0a06a0850f3b7a3f0eba80becc9185e91b10c0`. Python 3.13.14, SQLite 3.50.4,
pro-a 0.5.1 and MCP 2.2.0 remain unchanged. All 60 installed
distribution versions are identical before and after; only pro-a was reinstalled.
The final evidence commit is reported in the handoff to avoid a self-referential SHA.
It is on a separate evidence-only branch and is not installed or merged into main.

## Root cause, design and verification

`ROOT_CAUSE = RUNTIME_GIT_METADATA_DEPENDENCY`. The old stable installation ran Git
from its installation tree and failed with exit 128 even though Git was available
and regardless of process CWD. The genuine source checkout succeeded using Git metadata.

One resolver now anchors source mode to the package's own tracked pro_a checkout.
The zero-dependency setuptools PEP 517 hook freezes its exact clean HEAD into
three-field wheel metadata, refuses dirty tracked source/untracked package source,
rechecks source state and compares complete source/build Python inventories.
Generated egg-info is moved under build/ to preserve tracked historical egg-info.
Installed mode validates contract, repository, canonical 40-hex commit and RECORD
SHA256/size; missing, malformed and modified identities fail closed without Git
or enclosing-repository fallback. RECORD verification is installation integrity,
not a signature against replacement of both metadata and RECORD.

The phase4 runtime retains its six-field shape. Operational ingestion delegates
its old Git probe to the same authority; cloud identity still derives from phase4.
The resolver bytes enter the existing processing hash and protected native surface.
Frozen historical records and production retry/runtime guards are unchanged;
there is no new compatibility exception or rewritten historical context.

Actual isolated PEP 517 builds from both the exact audited PR head and merged main
passed independent non-editable installation. All **135 source/wheel/installed
Python files are byte-for-byte identical**. Extra packaged identity is checked
separately. Complete phase4/cloud runtime equality passed under the same environment.
Tests covered absent Git, unrelated enclosing HEAD, missing metadata, corrupted
JSON, wrong version/repository, invalid commit, and valid-commit tampering.
An actual dirty tracked PEP 517 build was refused with no wheel. pip check and
compile/import passed. Runtime probes called no Git or network and opened no
business database.

Relevant regressions finish at **408 passed, 1 skipped, 0 failed**, aggregated by
unique testcase across the initial run and affected reruns. Initial run: 403 pass,
1 skip, 4 fail; corrected/affected rerun: 83 pass, 1 fail; final stdio rerun: 1 pass.
The two historical test fixture expectations account for the newly protected helper
without changing production compatibility logic. Temporary HTTP/stdin import issues
were resolved by environment setup and an independent candidate-wheel install.
No single full-repository-green or PR 96 integration-green claim is made.
GitHub had no status checks for repair PR #97; local qualification is recorded explicitly.

## Stable activation, rollback and read-only health

Before mutation, the real snapshot was frozen at schema11. Rollback saved the
previous release wheel, all installed package bytes, distribution metadata,
entry scripts, runtime metadata, lock, manifest and dependency state. The previous
wheel `218007fb0fa37d2783da31a5378e579ee7db6196973ff84c5faab1ef4845472c` exactly matched all 129 installed
Python files. The older wheel-cache entry was not the active release artifact;
the correct release-directory wheel was found and verified. Existing wheel cache
and its manifest remain unchanged.

Existing managed stop/start helpers performed the deployment. Only pro-a was
reinstalled with no dependencies or index. Its actual stable imported package
matches the final wheel byte-for-byte. Its phase4 and cloud identities equal the
merged-main qualification even with Git subprocesses prohibited and PATH empty.
Settings, private configuration, lock, six helpers and secret-file stat metadata
remain unchanged. The secret's contents were neither read nor hashed. No Tunnel
or connection was recreated.

The first activation automatically rolled back and restarted successfully because
the broader MCP smoke script encountered an existing research-context boundary
rejection. The complete snapshot after rollback equals the pre-activation snapshot.
`get_company_research_context` returned `READ_BOUNDARY_VIOLATION` on both the original
stable wheel and independently installed merged-main wheel. No business/read
boundary code was changed. Final verification preserves that baseline fail-closed
result explicitly; it does **not** claim research-context success.

Final installed guarded stdio passed health, company search, Current View and Review
queue reads, with exactly 14 read-only tools and unchanged old-11 definitions.
The queue is empty. All seven provider/write/retry/reprocess/review counters are zero.
Actual connected-app `pro_a_health` also passed: schema11, readable Production and
Workbench, read_only=true and all 14 capabilities. Native runtime is running,
healthy and ready; detailed polling is `ok`/`polling`, consecutive failures zero,
last success `2026-09-30T23:56:51.2562821Z`. Its separate summary
remains `unknown` with reason `no live admin UI system snapshot`; this is preserved.
These observations qualify the bounded read windows, not unattended uptime.

Rollback remains available. A subsequent rollback uses the verified old wheel,
restores saved runtime metadata and restarts through the same helpers, then
rechecks package bytes, dependencies, identities/health and business snapshots.
An automatic rollback was actually exercised during attempt one; final attempt
completed without rollback. The final stable runtime remains on the repair merge.

## Real-state immutability

Pre/post comparison is exact for both complete database snapshots: file hashes,
sizes/identities, schemas, every table's row fingerprint and counts, all frozen Run
contexts, Current Views, Review state, provider history, source file checks,
artifact inventory and configuration hashes. Integrity checks are ok, foreign-key
violations zero, and no WAL/SHM/journal appeared.

Production SHA256: `6e5a303ccee9c192c350c2550cc232649e56ffee939b7a09cd6b170cc1c8fba1`.
Workbench SHA256: `0114861af73d616f1a732ee0f16252514052bfc59c997f3480fc3c4ec411da8d`.
Artifact inventory SHA256: `c492a2bf2ff87e0695a49bb037838afb9f74a170d46cc4e2952b50d310b61ec7` (36 files).
There are seven target-source Runs and one earlier other-source Run; eight global
records do not mean target Run 8 exists. Target Run 8 is absent. Historical target
attempt counts remain 0/2/1/1/1/1/1. Provider calls and liability from this task are
zero. No real migration, live bounded extraction, review/Production/Current View
write or original release Gate A–D was performed.

## PR 96 and minimum delta requalification

[PR #96](https://github.com/ysssss414/pro_a/pull/96) remains **OPEN / Draft / unmerged**,
untouched at `e63608e303725db20541ff7d57fb62b584f6fa75`. GitHub reports
`CONFLICTING` / `DIRTY`; its reported base-ref OID remains the pre-repair main,
while the current main is the repair merge and is not an ancestor of the #96 head.
Read-only merge-tree confirms one conflict:
`tests/test_phase43_stage72c_retry_compatibility.py`. No production-source conflict
was reported. The nonconflicting tree naturally inherits setup.py, the identity
resolver and phase4 bytes exactly from repaired main. The tree has an unresolved
test conflict and is not claimed runnable or qualified. PR 96 was not modified.

Minimum work before its separate Gate A resumption:

1. Resolve only the Stage7.2C test-fixture conflict in a separately authorized PR 96 update; preserve the new identity tests and fail-closed native dependency checks. Pin a new candidate head and repair-main base.
2. On the resolved candidate tree rerun test_repository_identity, test_phase4_orchestration, test_workbench_stage7, test_phase43_stage72c_retry_compatibility, test_mcp_stage0 and test_mcp_stage3. Include processing-context/cloud/native runtime guard coverage and reject historical resume drift without any new exception.
3. Rerun test_source_analysis_series_binding and test_source_analysis_series_recovery, plus directly shared test_cloud_operation_adapter_binding, test_bounded_extraction_persistence and test_phase43_stage72b_extraction_retry. Use disposable fixtures and synthetic HTTP; no provider call or real migration.
4. Rebuild a clean isolated PEP 517 wheel from the new exact candidate head; independently install it and repeat inventory/raw Python byte comparisons, RECORD identity integrity, no-Git/unrelated-parent resolution and full source/installed phase4/cloud equality. Recompute processing/context/native/cloud hashes and do not reuse the old PR 96 artifact or receipt.
5. When a separate task resumes Gate A, repeat exact head/base/diff and current stable identity/health plus real schema11/target Runs 1–7/Production/Current View/review/provider-history/Run 8 absence snapshots. Do not infer permission for Gates B–D, migration or Run 8 from this receipt.

The repair's PASS removes the installed repository-identity blocker. The PR 96
test conflict remains a separately reported preparation requirement. The following
handoff flag permits resuming the separate Gate A task; no original gate is started here.

```text
INSTALLED_RUNTIME_REPOSITORY_IDENTITY_R1 = PASS
STABLE_INSTALLED_REPOSITORY_IDENTITY = VERIFIED
REAL_WORKBENCH_SCHEMA = 11
PROVIDER_CALLS = 0
RUN8_CREATED = false
PR96_MERGED = false
RESUME_SOURCE_ANALYSIS_COMPACT_WIRE_RELEASE_ACTIVATION_GATE_A = true
```
