# Phase 3D one-time Production executor

The Phase 3D Production executor is separate from the shadow executor. It does not weaken `assert_shadow_target` and exposes no force, unsafe, or environment-variable bypass.

The executor accepts an already-qualified candidate package plus a separate immutable authorization artifact. The payload is never treated as authorization.

## Authorization contract

An authorization artifact must use this shape, with deployment-specific values supplied only after the executor has been merged and qualified:

```json
{
  "document_type": "phase3d_production_execution_authorization",
  "authorization_version": "1",
  "authorization_id": "<unique-one-time-id>",
  "authority": "USER",
  "scope": "EXACT_PAYLOAD_ONE_TIME",
  "status": "PENDING",
  "authorization_environment": "PRODUCTION",
  "real_production_authorization": false,
  "release_commit_sha": "<exact-release-commit>",
  "payload_id": "<exact-payload-id>",
  "payload_sha256": "<exact-semantic-payload-sha256>",
  "payload_file_sha256": "<exact-payload-file-sha256>",
  "candidate_manifest_sha256": "<exact-manifest-file-sha256>",
  "expected_production_sha256": "<exact-production-pre-sha256>",
  "source_id": "<exact-source-id>",
  "source_sha256": "<exact-source-sha256>",
  "human_review_id": "<exact-human-review-id>",
  "human_review_sha256": "<exact-human-review-sha256>",
  "expected_operation_counts": {},
  "target_database_identity": {
    "resolved_path": "<configured-production-database-path>"
  },
  "target_archive_identity": {
    "resolved_root": "<configured-workspace-root>"
  },
  "authorization_consumed": false
}
```

The template is deliberately `PENDING` and is not executable. Only an explicit user decision made after release freeze may change `status` to `AUTHORIZED` and `real_production_authorization` to `true` for the exact configured target.

Qualification artifacts instead use `authorization_environment=QUALIFICATION` and `real_production_authorization=false`. The executor rejects such an artifact when its configured target resolves to the protected real Production database.

## Execution contract

The top-level executor performs this sequence:

1. Verify every candidate-manifest artifact before target access.
2. Validate authorization authority, scope, status, environment, release, payload, manifest, Source, human review, operation counts, and target identities.
3. Refuse completed, failed, incomplete, or uncertain one-time journal states.
4. Read the configured target immutably and verify its byte SHA, schema, counts, integrity, FK state, SQLite sidecars, Source/Claim absence, Node identities, and archive destination.
5. Create and verify a byte-exact non-overwriting backup.
6. Persist a `PREPARED` execution journal.
7. Stage and atomically materialize the exact Source, then persist `SOURCE_MATERIALIZED`.
8. Acquire `BEGIN IMMEDIATE`, repeat all mutation-sensitive collision and identity checks, and execute only frozen `INSERT` mutations under the narrow SQLite authorizer.
9. Persist `DB_COMMITTED`, then verify exact rows, exact table deltas, unchanged schema and REUSE Nodes, archive inventory, integrity, FK state, and sidecar absence.
10. Write an immutable receipt and persist `COMPLETE`.

Only `sources`, `claims`, `nodes`, and `node_aliases` can be mutated. Relation, link, Proposal, Current View, IMA, extraction, LLM, schema initialization, migration, and propagation paths are absent.

The immutable authorization JSON is never modified. Durable consumption is recorded in the external journal and receipt at the fixed configured-workspace location `phase3d/production-executions/<authorization-id>`. The location is not caller-selectable, so changing an invocation argument cannot replay an authorization. A second invocation of a `COMPLETE` authorization returns `AUTHORIZATION_ALREADY_CONSUMED` without opening a write transaction.

## Failure behavior

Synchronous failures after `PREPARED` retain the verified backup, remove only the exact materialized Source, restore executor-committed bytes from the backup, verify the original database and archive state, and persist `FAILED_RESTORED`. Pre-commit drift that did not come from the executor is never overwritten.

If restoration cannot be proven, the journal becomes `UNCERTAIN`; all subsequent automatic execution is refused. An interrupted `PREPARED`, `SOURCE_MATERIALIZED`, or `DB_COMMITTED` journal also refuses execution and requires explicit recovery review.

## CLI

After a separately approved real authorization exists, execution uses:

```text
python scripts/phase3d_production_execute.py \
  --candidate-dir <frozen-candidate-directory> \
  --authorization <authorization-json>
```

The CLI derives the release commit from Git, requires a clean tracked worktree, and uses the configured Production database as the protected target. It offers no production-enable or guard-disable switch.

Runtime authorization files, Source packages, database copies, backups, journals, and receipts must remain outside version control and must not be published.
