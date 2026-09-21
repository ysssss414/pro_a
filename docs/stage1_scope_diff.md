# Phase 4.3 Stage 1 scope diff

## In scope and implemented

- Added explicit offline Workbench v9-to-v10 preparation/rollback for a rebuildable review projection, its indexes, and operator intake control. The canonical knowledge database is never opened for write by this migration.
- Added bounded review list/detail APIs with deterministic priority, stable snapshot/keyset cursors, queue/type/domain filtering, and transactional projection refresh after native review mutations.
- Added frozen intake/WIP/run/job/worker limits, explicit pause/resume, hard-stop dispatch backpressure, single-worker claim enforcement, and bounded source run history.
- Added exact-before-substring canonical/alias search with complete deterministic continuation and bounded catalog iteration for Analyzer and operational ingestion.
- Replaced full coverage materialization with bounded SQL projections.
- Aligned the source prompt Node Type enum with the existing canonical schema, including `Company`, without adding any ontology value.
- Added deterministic semantic partitioning by eight-parent and token boundaries, durable per-batch jobs, exact ordered reconstruction, and evidence/source identity checks.
- Added offline benchmark and frozen-gold validation tools plus Stage 1-focused regression coverage.

## Existing contracts preserved

- Shared Node, Source, Claim, Relation, and canonical identity remain global across domain packs.
- Domain packs remain declarative; they do not create domain-scoped duplicate Nodes.
- Native packets and append-only human review audit remain authoritative; the Stage 1 projection is explicitly non-authoritative and rebuildable.
- Existing Stage 0 run context, pack identity, prompt/model/config provenance, Phase 4.2 application boundaries, retry semantics, and canonical schemas remain in force.
- Historical Pilot 3 prompt identities remain frozen and reject the Stage 1 prompt fail-closed.

## Explicitly not changed

- No Stage 2 implementation or industry corpus onboarding.
- No real semiconductor Foundation ingestion.
- No Production write, apply, or migration.
- No live model/provider call.
- No hidden holdout truth access.
- No ontology/schema extension or weakening.
- No automatic substring/fuzzy/semantic canonical linking.
- No PostgreSQL, Redis, Celery, Kafka, distributed scheduler, graph, or vector infrastructure.
- No merge, tag, or release.
- No governance workspace, private corpus, review sandbox, virtual environment, dependency tree, cache, or benchmark fixture is included in Git.
