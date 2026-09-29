# Cloud operation adapter binding R1

`PRO_A_CLOUD_OPERATION_ADAPTER_BINDING_R1 = PASS`

Implementation commit: `1f98099d05dd6475dc70a3a0626f9b88483d4d14`.

## Problem and baseline

The required remote main was exactly
`1966c24d37644d02c9c0c3496725a177ab437106`; PRs #85 and #86 were merged.
The existing Stage 3 MCP runtime stayed online and was not upgraded or restarted.

Read-only inspection of the exact historical Smoke 01 Run confirmed:

- The uploaded Source bytes retained their immutable identity.
- The Run was `BLOCKED / EXTRACTION_JOBS / PROVIDER_CONTRACT_MISMATCH`.
- Two `SOURCE_ANALYSIS_PIECE` jobs incorrectly froze
  `semantic-backend-adapter-v1`, with provider `deepseek` and model
  `deepseek-flash`.
- Both jobs had zero attempts; no provider outcome or Review Packet existed.

Before implementation, a disposable schema-11 Shared Core fixture reproduced this
exact mismatch using the real `SourceAnalysisPieceProvider`. Native submission,
frozen identity and preflight were exercised; both provider invocation and network
counts remained zero. Baseline reproduction: **1 passed**.

The root cause was the single adapter default on `CloudProfile`: submission
copied it into every operation's durable row. Extraction needs a different adapter
from semantic decomposition. Also, `SourceOperations` forwarded one supplied
provider instance to whichever stage was active. Neither the DeepSeek model nor
the credential caused the observed pre-dispatch failure.

## Operation identity and routing

The cloud-contract layer owns the authoritative mapping:

| Operation | Required real adapter |
| --- | --- |
| `SOURCE_ANALYSIS_PIECE` | `source-analysis-piece-adapter-v1` |
| `SEMANTIC_DECOMPOSITION` | `semantic-backend-adapter-v1` |

`adapter_version_for_operation` rejects unknown operations.
`operation_contract` publishes this required adapter alongside the existing
prompt and validator identities. New live jobs persist that operation-specific
adapter. Preflight verifies the frozen adapter against the operation requirement
and compares the supplied provider identity and adapter exactly. A wrong adapter
is still `PROVIDER_CONTRACT_MISMATCH` before invocation.

`SourceOperations.advance_once(provider=...)` accepts a narrow mapping from
operation kind to adapter instance. Each queued job selects only its own key;
a missing entry raises `PROVIDER_OPERATION_UNAVAILABLE`, with no fallback.
The existing single-provider calling form remains supported and subject to the
same exact durable preflight; it cannot substitute one real adapter for another.

`build_source_providers(llm_config, cloud_profile)` constructs both existing
adapters for the qualified `deepseek / deepseek-flash` configuration. It validates
the enabled configuration, provider/base-URL identity, model and credential
environment-reference name. Construction reads no credential value and performs
no network call. The private TOML is unchanged. In-memory transport timeout and
output limits come from the frozen cloud policy, with transport retries disabled;
the durable job worker remains the retry owner.

Operator integration after merge/activation:

```python
profile = CloudProfile.from_environment()
providers = build_source_providers(load_config(phase4_config).llm, profile)
service = SourceOperations(workbench_config, SourceProfile(phase4_config), profile)
service.advance_once(
    worker_id=worker_id,
    processing_run_id=run_id,
    provider=providers,
)
```

This example is construction/routing documentation, not authorization to resume
the real historical Run.

## CloudProfile compatibility rule

The legacy `CloudProfile.provider_adapter_version` field remains in its public
policy identity and positional constructor for compatibility. For live execution
it accepts only the existing semantic-family marker; it is **not** an override of
the adapter required by an operation. New live extraction jobs cannot inherit
that marker as their frozen job adapter.

The pre-existing explicit offline fixture pair
`DETERMINISTIC_FAKE / deterministic-fake-v1` retains its exact synthetic adapter
contract for legacy regression fixtures. It cannot be selected as a DeepSeek
adapter or as a wildcard. The new hard E2E gate uses both real adapter classes and
real operation-specific identities, with only HTTP transport responses replaced.

## Hashes, runtime and historical compatibility

- `configuration_sha256` remains the hash of provider execution policy. The
  required per-operation adapter is not a second mutable profile choice.
- `operation_contract` / frozen `prompt_json` now include the required adapter.
  `prompt_sha256` still hashes prompt text only; the text did not change.
- Runtime identity includes the complete operation-to-adapter mapping. Changing
  a required adapter changes `runtime_sha256` and the job's `intent_sha256`.
  The intent also binds the full operation contract.
- Exact frozen fields, event-chain verification, provider matching, runtime and
  configuration guards remain enforced.
- Retry reconstruction verifies the frozen row's adapter against its operation,
  while reconstructing the original provider policy from the original JSON.
  Retry creation copies the original adapter and other frozen fields; it does
  not replace them using a new default.
- Stage 7.2C computes target runtime from the reconstructed policy identity,
  not from an operation-specific row field. Its execution-surface dependency
  manifest includes the new binding method. This repair is a semantic change,
  not a metadata-only compatible release of the pre-repair execution contract.

The metadata-drift regression fixture snapshots the source that actually created
its disposable Run, so it models metadata-only release drift even during local
development. A separate regression explicitly proves the pre-binding baseline's
cloud execution surface is incompatible. Adversarial surface tests still reject
runtime/provider/configuration changes.

## Qualification

The hard single-Run regression gate registers one synthetic PDF Source, starts one
Shared Core Run and uses the normal durable job machinery through:

`SOURCE_ANALYSIS_PIECE → SEMANTIC_DECOMPOSITION → HUMAN_REVIEW_REQUIRED`.

It uses actual Source-analysis and semantic adapters with deterministic HTTP
responses, distinct prompts and validators, the same DeepSeek/model identity,
and exactly one registered Review Packet. SQLite authorizer measurements and
Production-byte comparisons protect the disposable Production database.
Synthetic credential values are checked absent from generated JSON artifacts.

Focused tests cover both mismatch directions, unknown operation/adapter, wrong
provider, frozen model/config/runtime drift, missing routes, deterministic identity,
adapter changes changing new identity, constructor preflight, retry copying,
historical bad adapter rejection and compatibility-token non-bypass.

Final qualification: **24 focused passed**; required regressions, after the
Stage 7.2C fixture update, aggregate to **332 passed / 1 skipped / 0 failed**.
The initial regression invocation had 330 passes and two compatibility-assumption
failures; the complete updated Stage 7.2C replay passed all 33 tests (57 with the
focused tests). The remaining 299 required regressions passed unchanged. The
single skip is the unavailable private frozen orchestration replay fixture.

Compileall, pip check, isolated PEP 517 wheel build, all 129 Python-file byte
comparisons, installed-wheel no-network provider construction and diff checks
passed. Wheel SHA-256:
`8a5338d6d817f5da1435b5bd53026a5bc4df9e00b202a1a733e5e429e9699983`.

The durable E2E ran from the versioned source checkout; installed-wheel checks
cover source identity and no-network adapter construction.

Counts, replay provenance and build checks are recorded in the accompanying
[receipt](pro_a_cloud_operation_adapter_binding_r1_receipt.json).

No full-repository green claim is made. The historical Stage 0 full-suite result
remains **2380 passed, 108 skipped, 3 failed, 43 errors**, with all **46** original
failures/errors passing targeted replays. Those historical records are unchanged.

## Real-state and deployment boundaries

Only read-only inspection was performed against the real Workbench and Production.
The real historical Source, Run, jobs and database evidence are compared before
and after qualification: the full row digest and both databases remained identical.
Their IDs, document text and private configuration paths
are excluded from this public evidence.

The historical Run must remain blocked, with its original wrong adapter frozen,
zero provider calls, no retry and no packet. This repair does not rescue or rewrite
it. No real Review decision, seal, Attribution, Current View or Production mutation
is authorized here.

`STABLE_RUNTIME_ACTIVATION_REQUIRED_AFTER_MERGE = true`.

After merge and activation, resuming the material workflow requires **NEW RUN
REQUIRED**, using the same already-uploaded Source and an explicit reprocess
reason under separate operator authorization. No re-upload is needed. That future
operation, live-provider quality/cost qualification and stable-runtime activation
are outside this repair task.
