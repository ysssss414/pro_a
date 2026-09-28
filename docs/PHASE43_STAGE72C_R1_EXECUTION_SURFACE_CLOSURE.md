# Phase 4.3 Stage 7.2C R1 — Execution-Surface Closure

## Result

- `PHASE43_STAGE72C_R1_EXECUTION_SURFACE_CLOSURE = PASS`
- `PHASE43_STAGE72C_GENERIC_COMPATIBILITY = PASS`
- `ORIGINAL_STAGE72_CROSS_RELEASE_COMPATIBILITY = BLOCKED`
- Preserved real blockers: `BLOCKED_EXECUTION_CONTRACT_CHANGED`, `BLOCKED_NATIVE_CHECKPOINT_INCOMPATIBLE`
- `REAL_RETRY_EXECUTED = false`
- PR #80 remains `OPEN / DRAFT / UNMERGED`.

R1 closes the Stage 7.2C semantic AST surface around the actual retry execution path. It does not prepare either real extension, persist a real qualification, retry the historical Run, relax an exact identity gate, or alter historical facts.

## Chronology and audit target

| Item | Value |
|---|---|
| Authoritative baseline | `origin/main = ec0497df63595fb21dca7b1a7fc91ca81c942ef8` |
| Branch | `codex/phase43-stage72c-cross-release-retry-compatibility` |
| Original implementation commit | `0fbd01116100f53b832331deb865976b785a12d6` |
| Prior PR head / evidence commit | `dfea7e93e216615b8a1d5bded298ad7c6d0b1a21` |
| R1 repair commit | `7aaa0c0352a31c344742d623d062bf4f77644004` |
| Compatibility contract | `extraction-retry-cross-release-v1` |
| R1 target contract SHA-256 | `ba75a8afd2630d3d407a704606259272434545561eb1965e2716ff5b128dbbeb` |

## Reproduced pre-fix false positive

Before changing the implementation, two adversarial tests mutated real source text and invoked `_surface_manifest`; neither monkeypatched `_execution_surface_comparison`.

1. `CloudJobs._preflight`: `PROMPT_IDENTITY_MISMATCH` was changed to a bypass identity.
2. `SourceOperations._advance_claimed`: `BLOCKED_EMPTY_EXTRACTION_PLAN` was changed to a bypass identity.

Both tests failed as intended because the pre-fix surface retained the same semantic surface SHA-256, `2786587d90c1a90ec486297dcf13bae8a7f6d3778c13cd6cb9a4fc4f3e9c6648`, across the behavioral mutation. This is the concrete false-positive reproducer that motivated R1.

## Closed surface manifest

### Cloud roots

- `workbench/cloud_jobs.py::CloudJobs.run_once`
- `workbench/source_operations.py::SourceOperations._advance_claimed`

The selected transitive/critical dependencies now include:

- the full `cloud_contract.py`, `provider_diagnostics.py`, `domain_packs.py`, `run_context.py`, and `workbench/artifacts.py` files;
- `Domains.guard`, `read`, `basis`, `pending_basis`, `assignment`, `packs`, `config_digest`, and `prompt_digest`;
- `CloudJobs._preflight`, `_native_identity`, `_input_payload`, `current_runtime`, event-chain verification, claim/fence/dispatch, durable result, artifact registration, terminal/fault handling, projection, and every direct `self` helper reachable from `run_once`;
- `SourceOperations.__init__`, context/input/job binding, transition/event, pending Job execution, extraction/semantic replay, native-root/checkpoint continuation, packet copy/registration, Run projection, and every direct `self` helper reachable from `_advance_claimed`;
- the relevant `CloudProfile` and `SourceProfile` validation/configuration identity helpers.

### Native root

- `phase4_orchestration.py::resume_execution`

The native surface includes every non-orchestration module in `PROCESSING_MODULES` in full. The orchestration selection is dependency-closed over `_compatible`, `_advance`, `_configuration`, `_inventory`, `_commit`, `_result`, `_emit`, `_review`, `_runtime`, `_now`, and `_publish`.

Every selected class method's direct `self.<helper>` call and every selected module function's direct local-function call must itself be selected. A missing dependency raises `EXECUTION_SURFACE_DEPENDENCY_UNCLOSED`; it is never treated as compatible. An adversarial `self._unrepresented_authorizer()` insertion verifies this fail-closed behavior.

For the generic pre-extension comparison, the closed manifests are exact:

| Surface | `origin/main` | R1 target | Result |
|---|---|---|---|
| Cloud | `9baf711de7694a02c324ac5f700225e636e02d5090cff844f0346173b8728df2` | `9baf711de7694a02c324ac5f700225e636e02d5090cff844f0346173b8728df2` | EXACT |
| Native | `8d2be1aa08d7dab92cab2b03e295b03b2d33248726109c9bac71efc2a6541b1b` | `8d2be1aa08d7dab92cab2b03e295b03b2d33248726109c9bac71efc2a6541b1b` | EXACT |

### Explicit exclusions

- `workbench/extraction_retry.py` is target-only authorization and immutable retry-copy construction. It did not exist in the historical execution and is bound by the exact target contract digest and focused end-to-end tests.
- `workbench/retry_compatibility.py` is the target-only evidence validator/token issuer. Its exact call-site plumbing is normalized, while its complete target bytes are bound by the target contract digest.
- New-Run intake, initial Job submission/registration, operator recovery/reconciliation, and HTTP/CLI presentation are outside the two retry execution roots. They cannot authorize compatibility, and relevant target files remain included in the target contract digest.

## Narrow normalization

The old global rule that removed every keyword named `runtime_compatibility` is gone.

R1 normalizes only enumerated file/selector/callee combinations, with exact expected occurrence counts. It also replaces only the exact known compatibility-plumbing statement sequences in `CloudJobs._preflight`, `Domains.guard`, `SourceOperations._advance_claimed`, and native `_compatible`, plus the exact token signatures/assignments and `resume_execution` forwarding call. A renamed guard, changed branch, changed call keyword, extra matching call, or ambiguous sequence is not normalized and makes the surface change or fail closed.

Qualification-level adversarial tests mutate each of `_preflight`, `Domains.guard`, `_advance_claimed`, `_compatible`, and `resume_execution` through the real loader/manifest/comparison path. Every mutation returns `BLOCKED` with the appropriate execution-contract or native-checkpoint blocker.

## Positive cross-release behavior

The existing positive test remains intact. A synthetic release with broad Cloud/Native code-digest drift qualifies only when the dependency-closed semantic surfaces are exact. The exact-scope qualification creates a new append-only retry Job/Attempt, performs one extraction call and one separate semantic call, and reaches `HUMAN_REVIEW_REQUIRED` on the same Run without changing original Run/Job/Attempt facts.

## Real historical Run — read-only requalification

The real assessment used `persist=False` against:

- Source `SRC_C70218574FB158D7`
- Run `SOURCE_RUN_BBADD851DA1E4526BAB9B6EBD1DBDCF0`
- failed Attempt `ATTEMPT_A1998074CE7545149AE15A9B865571B8`

Result: 28 dimensions, 25 PASS and three FAIL (`code_runtime_identity`, `native_execution_checkpoint`, `extraction_parser_output_contract`).

- Target runtime SHA-256: `2983aafa9c3fd93b1e32b161a65ae95535b14730a2cd2f93a633049da08b1c42`
- Cloud surface: `EXECUTION_SURFACE_UNAVAILABLE:CalledProcessError`; the historical commit still lacks a required file, so equivalence remains unprovable.
- Native surface: `SEMANTIC_SURFACE_CHANGED`
- Historical native surface SHA-256: `f2160149ebdbfa6f219b5acc5b27893749fc65d4cb9e92248892c8a36d848ff1`
- Target native surface SHA-256: `8d2be1aa08d7dab92cab2b03e295b03b2d33248726109c9bac71efc2a6541b1b`

No record was returned or written. Both real extensions remain unprepared; no WAL/SHM sidecar was created.

## Verification

| Suite / check | Result |
|---|---|
| Pre-fix adversarial reproducer | `2 failed` as expected; both exposed unchanged surface SHA |
| Stage 7.2C focused | `33 passed` |
| Final Stage 7.2B + Stage 7.2C | `58 passed` (`25 + 33`) |
| Expanded related Domain/Cloud/native/Stage7/7.1/7.2A/Unicode selection | `166 passed` |
| Full historical-environment repository | `2477 passed, 2 skipped, 4 failed, 29 errors` (`2512` total) |
| Historical exception reconciliation | `33/33` exact node/status/exception-class equality; `NEW_REGRESSION = 0` |
| Full JUnit SHA-256 | `e8ddfc6b12e23e2354d0c824e6b2653ba026acc9fe245af07554cec8c5b2bbc6` |
| Compileall / CLI help / JSON-contract match / diff check / credential scan | PASS |

The full-suite total increased by nine from 2503 to 2512; all nine new R1 cases passed. The first two full-suite attempts were discarded because the test-only import environment omitted helper/root source paths; the corrected final run above is the evidence run. An initial isolated-worktree related selection exposed only a CRLF/LF closure-fixture mismatch; the final related run used the same root fixture/current overlay as the full suite and passed all 166 cases.

## Real-state boundary

| Control | Before | After |
|---|---|---|
| Production SHA-256 | `6e5a303ccee9c192c350c2550cc232649e56ffee939b7a09cd6b170cc1c8fba1` | `6e5a303ccee9c192c350c2550cc232649e56ffee939b7a09cd6b170cc1c8fba1` |
| Workbench SHA-256 | `1ff852dbe76c5fc4054c3e6f4e308b98a66f918dc3081e287b793c682a61ca44` | `1ff852dbe76c5fc4054c3e6f4e308b98a66f918dc3081e287b793c682a61ca44` |
| Real compatibility extension | NOT_PREPARED | NOT_PREPARED |
| Real extraction-retry extension | NOT_PREPARED | NOT_PREPARED |
| Qualification record / retry / provider / ZSXQ / Production / Workbench writes | `0` | `0` |

## Next action

Keep PR #80 Draft and unmerged. Stop for final premerge re-audit. The original Stage 7.2 real Run remains blocked and must not be retried.
