# Phase 4.3 Stage 0: domain pack and run context foundation

Stage 0 adds declarative domain metadata to the existing Source / CloudJobs /
Review Workbench flow. A multi-domain Source retains one canonical identity and
one extraction run. A changed pack, prompt, effective configuration, runtime or
model cannot silently resume a frozen run.

The implementation baseline is v0.5.1 (`d27297f33a9f36d7d14b050a98070b5b0e8a4d15`).
The planning baseline is v0.5.0 (`650495b74349427499f78437384db89c2cc5fddf`).
The intervening changes are frontend scrolling, its tests and release metadata;
no canonical schema, backend persistence or provider contract changed.

## Contracts

- `domain-pack-v1`: `domains/<domain>/pack.json`, identity `(domain_id, version)`,
  supported major version 1; registry entries pin the content digest permanently.
- `domain-composition-v1`: sorted pack identities, explicit primary routing owner,
  shared canonical identity scope, union of supported core node/relation types.
  Contradictory normalization or relation endpoint declarations yield `DEFER`;
  assignment rejects that composition until explicitly resolved.
- `run-domain-context-v1`: immutable private run companion. `resume_sha256` hashes
  the execution basis; `context_sha256` additionally binds run ID, actor, reason
  and timestamp. Thus identical effective input is reusable without removing
  each run's audit identity.
- `domain-review-companion-v1`: packet digest, processing run ID and context digest.

The pack loader rejects unknown/missing fields, duplicate JSON keys, nonfinite
JSON, unsupported contract/major versions, canonical ontology extensions,
file hash mismatches, missing/unlisted files, executable file types, path traversal,
links/reparse points and hardlinks. Only inventoried JSON, text and Markdown
files are allowed. Individual files are bounded to 1 MiB. Hint references are
bounded to 2,000 characters per pack and 4,000 per composition. Declaration
collections use deterministic ordering. Plain metadata cannot change the system
prompt, evidence rules, attribution roles, review thresholds or direct Impact paths.

The reference fields cover prompt/profile, source, admission, review, entity and
relation policy. Lifecycle metadata is descriptive; it is never an activation
receipt or permission to call a provider. `claim_pattern_hints` must currently be
empty because the shared core has no public enum/hook for it. Prompt references
are frozen metadata; this stage does not inject pack text into existing prompts.
The actual unchanged source/semantic prompt bundles are separately hashed, and
actual per-piece user prompts remain bound by the existing input artifact hashes.

## Explicit operational migration

Workbench schema 8 remains supported with its existing behavior. Web startup
never migrates it. The operator can explicitly prepare schema 9 in a disposable,
offline Workbench after draining pending Source/cloud jobs:

```text
python -m pro_a.workbench --config <disposable-workbench.toml> prepare-domains
```

This creates append-only pack registry, assignment, run binding, packet binding
and future activation-receipt tables. It adds an immutable context-required marker
to Source runs. Existing runs retain marker 0 and are displayed as
`LEGACY_NO_DOMAIN_CONTEXT`; their old keys, artifacts and sealed review bytes are
not backfilled or rewritten. Existing schema 1–8 readers and preparation commands
accept the additive schema 9.

Migration produces an exact `.stage7-backup` plus a `.stage43-migration.json`
receipt alongside the operational database. `rollback-domains` restores those
exact schema-8 bytes only while schema-9 state is untouched. After use, it rejects
rollback: retain the audit data and use the existing offline backup/restore
workflow. Migration refuses active work or SQLite WAL/journal sidecars. Operator
commands must run while the service/worker is stopped. No deployed Workbench or
canonical database is migrated as part of this implementation.

## Assign and inspect

Register each reviewed descriptor, then assign all domains in one event:

```text
python -m pro_a.workbench --config <disposable-workbench.toml> register-domain --pack domains/ai_hardware
python -m pro_a.workbench --config <disposable-workbench.toml> register-domain --pack domains/semiconductor
python -m pro_a.workbench --config <disposable-workbench.toml> assign-domains --assignment <assignment.json>
```

An assignment JSON contains `object_type` (`Source`, `Node`, or `RQ`), `object_id`,
`primary_domain`, `packs` (the exact identity objects returned by registration),
`actor`, `reason`, and `expected_revision` (0 for a first assignment). It must target
an existing object. Concurrent stale revisions fail; identical assignments reuse
the current revision. Assignment is operational metadata and never adds a
canonical entity, alias, Claim link, relation or View. The existing Source API
starts processing after assignment; no new frontend workflow is required.

On schema 9, a new Source run requires explicit assignment. Its immutable basis
binds Source bytes and storage artifact ID, validated complete-text scope, source
limits, assignment revision, all pack digests, core prompt identity, effective
configuration digest, runtime/code revision and cloud model/budget identity.
Configuration values and source payloads are not copied into the context.

Equivalent processing requests reuse the existing run, retaining the established
explicit failed/blocked retry policy. Reusing an idempotency key with a different
basis fails. A new basis requires a new key and explicit reprocess reason.
Changing assignment later does not relabel old results: an old run continues to
check its original assignment revision. Missing/corrupt packs or companions fail
closed. A restart reloads registry/companion bindings. Existing canonical Source
reprocessing remains blocked by the original Production-identity guard.

Source input checkpoints carry a versioned domain reference. Existing strict
input, CloudRequest and native run envelopes keep their field sets. Both Source
advancement and direct cloud-job dispatch recheck the bound context. The native
packet remains unchanged; a separate companion binds its hash, and the existing
Artifacts reader verifies that companion before review/attribution/qualification.
Historical review reading checks frozen bytes, without requiring today's pack to
reinterpret the old sealed result.

## Scope and validation

All schema-9 domain runs in this stage have `OFFLINE_REPLAY_ONLY` execution policy.
Only the existing deterministic fake provider can dispatch them. Real-provider
activation and industry qualification require subsequent explicit authorization;
a pack's `ACTIVE` label cannot bypass this boundary. Schema-8 behavior remains
available for existing qualified AI Hardware operation.

The four initial descriptors are non-private compatibility/configuration fixtures
with lifecycle `PROPOSED`. No semiconductor, robotics or commercial-space
qualification has started. The 120 case slots (core 24 plus four domains × 24)
are executable **specification inventory checks**, with 12 positive/12 negative
slots per group and six reserved holdout slots. Expected outcomes, source hashes
and reviewers are intentionally pending. These checks do not establish semantic
accuracy, human gold, holdout qualification or real-provider quality.

Tests cover strict pack validation, deterministic composition/hash, all five
resume drift axes, Source de-duplication, key conflict/new-run requirements,
restart, actual fake-provider Source-to-review flow, packet tampering, migration
and exact rollback, and preservation of existing sealed reviews. Full backend
regression and the existing frontend tests/build are required before submission.
Only disposable test databases and synthetic inputs are used. No canonical
0.2.3 change, Production Apply, live provider call, industry-specific pipeline,
new model dependency or additional infrastructure is part of Stage 0.

Stage 1 batching, catalog/prompt fixes, review scale UI and load qualification
remain outside this change. Stop after the Stage 0 Draft PR; do not merge or
start Stage 1 without explicit authorization.
## Historical Foundation audit portability

Public checkout tests do not require a copied private Foundation authority bundle.
The historical requalification test uses the existing local artifact locators.
When neither the bundle nor an explicit request is present, it reports
`historical private Foundation baseline is not configured in this checkout` as
SKIP, not PASS. `RUN_PRIVATE_FOUNDATION_AUDIT=true` forces prerequisite validation.
Any detected partial authority also requires validation, even when that variable
is false. Invalid values, missing inputs, corrupt artifacts and all original
DB/hash/branch/commit/authorization mismatches fail; no exception becomes SKIP.

The historical runbook and its GC-disabled subprocess body remain unchanged.
Public synthetic tests cover contract validation, fail-closed discovery, archive
hash rejection, original audit dispatch and deterministic read-handle closure on
normal and exception paths. Dispatch tests do not claim a real historical audit.
Previously recorded STOP results remain in the ignored local qualification
report history. Git attributes preserve exact pack bytes across platforms, so
checkout line-ending conversion cannot invalidate the declared file hashes.
