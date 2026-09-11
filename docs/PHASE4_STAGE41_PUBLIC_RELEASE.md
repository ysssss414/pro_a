# Phase 4.1 public release projection — v0.4.0

This source projection distributes the accepted v0.4.0 incremental operational
ingestion runtime. The private acceptance baseline and public source projection
have different file-tree identities but the same canonical v0.4.0 runtime
implementation. Version equality denotes runtime release semantics, not identical
acceptance-evidence trees.

The [projection manifest](PHASE4_STAGE41_PUBLIC_PROJECTION_MANIFEST.json) binds the
private release tip, private freeze digest, public base, canonical file hashes,
omissions, synthetic replacements and public qualification results. The private
freeze remains authoritative for engineering acceptance. This document is a
distribution summary, not a replacement private freeze.

## Qualified behavior and authority

The Golden Path is clean PDF → exact Source preregistration → immutable execution,
configuration and runtime identity → controlled extraction → evidence binding →
semantic decomposition and admission → deterministic Node eligibility → parent
placement governance → native blank Phase 3F ReviewPacket and full provenance
validation → `STOPPED(HUMAN_REVIEW_REQUIRED)`.

The orchestration adapter wraps the existing engine. It preserves coarse
checkpoints, attempt ownership, bounded operational retries, resume compatibility,
immutable inputs and deterministic frozen replay. It does not make semantic
quality failures eligible for unbounded retry. A duplicate audit uses an explicit
authoritative identity allowlist. Same-Source requalification requires its existing
stage, Source, prior failed attempt and remediation binding.

Evidence qualification accepts exact or approved normalized exact matches.
Safe PDF normalization preserves meaningful numbers, units, names and token
distinctions. Bounded adjacent-page continuation requires exact ordered fragments
and, when layout recovery is needed, grounded native boundary witnesses. Explicit
`[[PAGE:N]][[PAGE:N+1]]` pointers must be ordered and well formed. Missing,
nonadjacent, reversed and ambiguous evidence fails closed. Fuzzy matching and
paraphrase do not establish evidence authority.

Every reviewable operational Node, including ResearchQuestion and DEFER items,
requires at least one qualifying deterministic Claim-grounded support path. A
qualifying Claim is review-admitted, has authoritative resolved Source evidence,
and has ADMISSIBLE or REVIEW_REQUIRED semantic status. Diagnostics distinguish
supporting, qualifying and nonqualifying Claims from operation advice and
provenance eligibility. Excluding a Node also excludes its dependent placement.
Direct extraction evidence alone confers no operational Node authority.
Previously qualified deterministic identity/name/alias/support linkage executes
unchanged; no new linkage was invented for final acceptance. Foundation V4's
separately bound identity contract remains independent and unchanged.

The blank packet conveys no completed human decisions, Production authorization,
apply authority or Current View mutation rights. Publication qualification makes
no provider calls and performs no live ingestion or Production apply.

## Acceptance lineage (private evidence retained locally)

Counts below describe historical engineering acceptance. They are not new live
runs, and overlapping regression suites must not be added together.

| Stage | Outcome and cause | Historical regression |
| --- | --- | --- |
| Gate A | PASS: adapter, bounded retry/resume, replay and native blank packet | 242 passed, 1 deselected |
| Gate B initial | Preflight FAIL: duplicate audit scanned too broadly; zero executions/calls | No live run |
| Gate B audit remediation / Retry 1 | Audit allowlist qualified; live FAIL with 5 provenance gaps, including cross-page Claims and unsupported ResearchQuestions | Audit 10 passed; post-live 72 passed, 1 deselected |
| Gate B provenance remediation | Offline PASS: ordered spans and unsupported question/dependent placement exclusion | Focused 24 passed; broader 276 passed, 1 deselected |
| Gate B Retry 2 | PASS: 182 Claims, 26 Nodes, 0 placements, 208 decisions, zero gaps | Pre 93 passed; post 192 passed, 1 deselected |
| Gate C initial | FAIL: 4 required Claim evidence gaps | Pre 75 passed; post 236 passed, 1 deselected |
| Gate C evidence remediation | Offline PASS: safe PDF wraps, adjacent continuation and ordered multi-pointers | Main 323 passed, 1 deselected; overlapping affected suites 107 passed, 1 deselected |
| Gate C Retry 1 | FAIL: all 120 Claims grounded, but one unsupported Node remained reviewable under DEFER | Pre 160 passed; guard 39 passed; post 324 passed, 1 deselected |
| Gate C Node remediation | Offline PASS: generic Claim-grounded eligibility across operational Node types | 412 passed, 1 deselected; Foundation identity subset 34 passed |
| Gate C Retry 2 | PASS: 125 Claims, 14 Nodes, 10 placements, 149 decisions, 313 blank human fields, zero gaps | Pre 412 passed, 1 deselected; overlapping guard 68 passed; post 441 passed, 1 deselected |
| Private release closure | PASS, v0.4.0; full private freeze unchanged | 1790 passed, 2 skipped, 24 deselected; 31 historical cases ignored |

The nine canonical implementation files are listed with private/public SHA256
pairs in the manifest. Evidence recovery is implemented in `corpus_pilot.py`,
operational eligibility in `production_authorization.py`, evidence propagation in
`table_claim_safety.py` and `operational_ingestion.py`, and orchestration/audit/
retry/replay/requalification in the five `phase4_*` modules. Public distribution
does not modify any of those accepted file bytes. Git attributes preserve those
bytes across platform checkouts, including the accepted mixed line endings in two
inherited modules.

The six task-specific acceptance drivers, the private freeze verifier, and the
private Phase 4 architecture/plan/Gate/freeze documents are omitted from this
projection. They bind local acceptance workspaces or historical grants and are
not ordinary reusable release interfaces. Their paths and file hashes remain in
the manifest for reconciliation; this public summary supplies their distribution
context. Original private files remain untouched.

## Synthetic evidence qualification

`tests/fixtures/phase4_gate_c_pdf_evidence.json` contains entirely invented scenes
and native layout metadata. Its four cases exercise comma wrapping, enumeration
separator wrapping, single-pointer adjacent-page continuation, and explicit
ordered two-page pointers. Opaque private candidate IDs bind mechanical classes
to their synthetic counterparts in the manifest, without reproducing evidence.
The test module also uses invented normalization examples and numeric contrasts.

The applicable public regression uses isolated synthetic data and an external
local network/Production guard. Exact results and selection are recorded in the
manifest. Existing tests requiring untracked private artifacts skip when absent.
The accepted deterministic selection also excludes 31 obsolete historical
pre-apply cases, one live-configuration fixture and 22 immediate watcher cases
whose zero-settle timestamp comparison depends on filesystem clock ordering.
No runtime rule or semantic/provenance assertion is weakened to change a result.
Phase 3F's persisted public audit integrity test remains part of the public run.

Public test setup copies `config.example.toml` to the ignored `config.toml`, with
both providers disabled. A historical Phase 3C synthetic fixture binds the fixed
SHA256 of the unchanged public-base `prompts.py` Git blob instead of the private
checkout's mixed-line-ending file identity. LF checkout is explicit; the semantic
prompt pin and runtime validator remain unchanged. An additional negative control
requires prompt file identity drift to fail closed.

The local disclosure audit compares every proposed tracked file with the frozen
Gate B/C extraction corpus. It checks raw text and decoded JSON/Python strings,
normalizes Unicode compatibility and whitespace, and detects substantial exact
spans of at least 32 normalized characters, or 16 characters containing at least
eight Han characters. The lower Chinese threshold covers shorter clauses.
Field-aware review covers shorter
evidence values, page structures and synthetic fixtures. File-type, credential
and local-path review supplements substring scanning. Source fragments remain
only in audit process memory. Public metadata follows Phase 3F's allowlisted
identity/hash/count projection model, without statements, excerpts or report prose.

## Limits and future boundary

Layout and table classification remain imperfect under the frozen policy.
REVIEW_REQUIRED semantic states remain visible: 67/182 known-domain Claims and
67/125 cross-domain Claims. Native packet validity alone is insufficient without
complete provenance eligibility. The final fresh cross-domain run did not emit
an explicit multi-pointer example; that mechanism is covered by frozen and
synthetic regression.

The accepted provider was requested as `deepseek-chat` and returned
`deepseek-flash`; that warning remains visible, without silent fallback. Provider
routing changes are deferred. The two live benchmarks were different Sources:
15 pages / 25 calls / 160206 total tokens / 208 decisions, and 20 pages / 18 calls /
122923 total tokens / 149 decisions. These describe separate runs and do not
establish an efficiency improvement.

The next authorized stage after successful projection qualification is
`PHASE4_STAGE41_GITHUB_PUBLICATION_RETRY1`. This task creates local commits only.
Phase 4.2 has not started. The agreed future post-publication action remains
`PHASE4_STAGE42_CLOUD_ONLY_PRODUCTIZATION_PLANNING`; local-model integration is
deferred.
