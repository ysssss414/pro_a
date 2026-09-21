# Phase 4.3 Stage 2 structured Foundation qualification

The qualified Web-Pro package imports into the existing Foundation candidate
model and shared Stage 1 Review Workbench without PDF extraction or provider
calls. Two disposable Workbenches each contain the same 274 candidate objects;
replay retains one registered packet and adds no candidates. Production and both
baseline copies retain their original byte SHA-256.

This report supersedes the abandoned raw-PDF interpretation. The previous five
untracked preflight artifacts remain untouched and outside this evidence chain.
The current machine-readable outcome is
`phase43_stage2_web_pro_backfill_results.json`; its regression and Git fields
remain explicit until their checks finish.

| Candidate group | Shared-core result |
|---|---|
| Sources | 20 physical / 21 logical slots; 17 prospective new identities, 3 reused, 0 collisions |
| Nodes | 19 shared baseline identities reused, 98 prospective creates, 44 review, 0 defer, 2 reject |
| Aliases | 30 review, 0 collisions |
| Claims | 19 acceptable; all 19 retain Source and evidence binding |
| Relations | 54 review; 41 native evidence records retained |
| Views | 8 baseline candidates retained; 0 current-view candidates activated |

CREATE is a proposed operation only. All 274 objects, including two rejected
Nodes retained for audit, remain candidate artifacts. No canonical Source,
Node, Claim, alias or relation row was inserted. Cross-domain reuse evidence
binds all 19 Node candidates to the existing shared canonical/alias catalog;
there is no semiconductor identity namespace. Private evidence contains the
exact matched identifiers; public evidence contains its digest and counts.

The adapter preserves 6,069 primary candidate fields: 319 DIRECT_MAPPING,
416 NORMALIZED_MAPPING and 5,334 REVIEW_REQUIRED. The last category retains
upstream and unmapped fields as native review context instead of silently
extending canonical columns. Every primary raw object was compared to its
input row, and every original package file remains archived with its hash.
Supplemental evidence, review references, coverage, maps and view Markdown
remain candidate context. No source text or private package row is in Git.

The 54 relation candidates lack an explicit confidence field, so all require
review. Of these, 13 also require evidence review, 14 have relation/endpoint
ambiguity, 22 require parent/causal review and 4 exert ontology pressure.
Reasons overlap; they are not disjoint object counts. No relation became
canonical merely because upstream classified it acceptable.

There are 234 mandatory human exceptions: 98 prospective Node creates, 44
ambiguous Nodes, 30 aliases, 54 relations and 8 baseline views. The remaining
40 objects are the residual review universe. A deterministic, hash-ordered
10-item sample recommends 5 reused Nodes, 4 acceptable Claims and 1 rejected
Node. The private human handoff provides 25-item mandatory pages, exact native
packet bindings and the sample. Human decisions remain blank.

The shared projection has 274 pending rows and correctly reports HARD_STOP
above the existing 200-row limit; subsequent new intake is blocked. This is
post-import backpressure, not a failed import. The ordinary 3-run rolling
24-hour limit remains unchanged, with zero Source runs or cloud jobs consumed.
The Workbench shows candidates through its existing bounded read projection;
native Foundation decisions require the existing packet workflow. The
operational Source-review save/seal API is blocked for this mode. No human
qualification or Production-entry approval is claimed.

Validation includes focused import/identity/evidence/replay tests, Stage 0/1
regressions, the authorized frozen 120-case Gold integrity/binding regression,
the full backend suite, frontend tests/build and compileall. The frontend was
tested in an isolated mirror whose 63 tracked files and package lock match the
worktree. Backend fixture setup needed the documented public `config.toml`
example and write access to this isolated worktree's disposable workspace;
initial setup failures were not counted as passing results.

The final full backend run uses an isolated Python environment with the same
local dependencies available to subprocesses, plus the system Temp volume for
fixtures. Earlier attempts exposed missing child-process dependencies and a
pre-existing immediate-file timestamp race on the D: volume (a synthetic probe
observed file age as low as -0.000000238 seconds). Volume relocation alone did
not eliminate the race. The two affected legacy test modules now explicitly set
their immediate-write synthetic input timestamps in the past before scanning, so they test
ingestion semantics with stable input. No product behavior, existing test
assertion, raw-source pipeline or qualification truth was changed; the earlier
failed XML is retained privately.

Both affected modules and the child-process crash recovery cases passed a
93-test focused rerun before the final full regression.

The frozen Gold validator checks the authorized manifest/outcome hashes and
exact 120 case bindings; it does not rerun hidden truth or claim a new semantic
Gold adjudication. No hidden qualification truth was read or used as a target.
No Stage 0/1 frozen artifact, Gold artifact, domain pack, canonical schema,
ordinary operator limit, Production byte or Stage 3 behavior was changed.

The private q2 contract binds the final runtime. Earlier q is retained only as
a superseded development qualification: the final PRIVATE/DEMO guard caused
a fresh freeze and new q2/a and q2/b imports, not an in-place frozen-run resume.

Production SHA-256 before and after:
`6e5a303ccee9c192c350c2550cc232649e56ffee939b7a09cd6b170cc1c8fba1`.
