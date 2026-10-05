# Installed runtime repository identity R1 — candidate qualification

The installed stable wheel could not obtain repository provenance because phase4
ran Git in the installation tree. Git was available; failures occurred both from
a source CWD and outside it. The source checkout succeeded with its own Git
metadata. `ROOT_CAUSE = RUNTIME_GIT_METADATA_DEPENDENCY`.

This separate repair is based on main `389399712deb9d2e1cacf41ad39e147e16b5f14b`.
Implementation head: `eb94e42bf6f4baeeabac0949f8cf4e278ca3c1b0`.
The [candidate receipt](installed_runtime_repository_identity_r1_candidate.json)
records actual artifact identities and qualification results. Merge and stable
activation remain pending at this evidence revision; this is not a final release PASS.

## Contract and implementation

One resolver anchors source identity to the actual pro_a source checkout, clears
caller Git overrides, and requires the checkout's own Git metadata and tracked
project files. Installed wheels read a three-field packaged identity containing
the identity contract, repository, and canonical 40-character source commit.
Runtime wheel resolution calls no Git, requires no network, and never discovers
an enclosing repository. Exact schema/repository/version checks and wheel RECORD
SHA256/size verification reject missing, malformed, or modified identity.
RECORD integrity is local installation integrity, not a cryptographic signature
against an attacker replacing both the artifact and its distribution RECORD.

The existing setuptools PEP 517 hook resolves HEAD before copying source, refuses
dirty tracked source and untracked package source, rechecks identity afterwards,
and compares complete source/build Python inventories before writing metadata.
Generated egg-info is placed under build/ because the repository tracks historical
egg-info. Builds leave tracked state clean. No dependency or package version changes.

The phase4 runtime retains its six fields. Cloud identity continues to derive
from it. Operational ingestion's duplicate Git probe now uses the same authority
and preserves its existing explicit unavailable error. The new resolver's source
bytes enter PROCESSING_MODULES, so actual helper drift remains protected.
Frozen historical identities and production retry/compatibility guards are unchanged.
Two historical test expectations account for the new protected helper: comparisons
between older releases use their original module set; an older native execution
surface missing the new dependency fails closed. No compatibility exception is added.

## Qualification

All ten requested identity gates passed, including a real isolated PEP 517 wheel,
independent non-editable target install, unavailable Git, an unrelated enclosing
Git HEAD, six actual installed metadata corruption/missing/tampering cases, and
an actual dirty tracked PEP 517 build refusal. All 135 source/wheel/installed Python
files are byte-for-byte identical; packaged metadata is checked separately.
The complete source and installed phase4/cloud identities match in the same
Python 3.13.14 / SQLite 3.50.4 / dependency environment. pip check and compile/import pass.

Relevant regressions finish at **408 passed, 1 skipped, 0 failed**, aggregated by
unique testcase across the initial run and affected reruns; this is not a single
full-suite run. Initial failures were two historical fixture assumptions and two
MCP child import failures in the temporary environment. The former were corrected
in tests; the latter were resolved by source PYTHONPATH for HTTP and a qualified
wheel install in the temporary venv for stdio. The receipt retains each run's counts.

Candidate read-only snapshots are identical: schema11, target source Runs 1–7,
the earlier other-source run (eight global runs), Production, all Current Views,
review tables, provider history, frozen source hashes and artifact inventory.
The target Run 8 is absent. Provider calls/liability from this task are zero.
No migration, live extraction, or original release activation gate was performed.

## PR 96 and release handoff

PR 96 stays OPEN / Draft / unmerged at its original head. A read-only merge-tree
check against the repair finds a conflict only in
`tests/test_phase43_stage72c_retry_compatibility.py`; no production-source conflict
was reported. PR 96 integration tests are not claimed because its test conflict
requires separate authorized resolution. This does not block the independent repair.

Before repair merge, rebuild and requalify the wheel from the exact PR head,
verify unchanged base/diff/state, and follow the existing merge-commit convention.
Stable activation must use only the exact merged main, retain rollback wheel,
distribution metadata, runtime manifest and dependency state, and reinstall only
pro-a. Final release evidence must confirm real installed identities, read-only
health and complete business-state equality. PR 96 remains untouched, and its
original Gates A–D remain paused throughout this repair.
