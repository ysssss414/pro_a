# Qualification run window override

An engineering operator may explicitly reprocess an existing Source for qualification without the production three-Runs-per-24-hours limit. Production intake remains subject to the unchanged limit. This override does not alter extraction, retry, subdivision, research or promotion semantics.

## Operator boundary

`SourceOperations.start_qualification_reprocess` requires a registered Source with processing history, a new idempotency key, a nonempty reprocess reason and a sanitized qualification reason of at most 1000 characters. The ordinary `start` signature has no override argument. HTTP request models, frontend clients and public MCP tools do not expose the qualification method or its parameters.

The private shared creation path passes `bypass_run_window=True` only for this explicit operator action. Schema, Source validity, context, idempotency, recovery, reprocess, intake pause, review WIP and incomplete-review-projection guards still apply. The override is `RUN_WINDOW_ONLY`, not a general force mode. First intake of a newly registered Source is not permitted through this path.

## Durable audit and capacity

Creation appends `STAGE1_RUN_WINDOW_BYPASS` in the same transaction as the Run and its existing context/events. Its payload contains the Run ID, Source ID, qualification reason, policy version, normal limit, observed window count, scope, creation timestamp and `created_under_qualification_window_bypass=true`. It contains no Source content. Audit failure rolls back creation. Same-key replay returns the same Run without another event; changing the qualification reason under that key is an idempotency conflict. Different concurrent keys retain the existing equivalent-active-Run duplicate behavior.

`stage1_capacity` remains unchanged: it counts qualification Runs as real Runs and continues to report `new_intake_allowed=false` when production capacity is exhausted. Run-window override audit and production capacity are separate concepts.

The cross-release execution manifest binds the shared creation helper, the qualification entrypoint and the Stage1 guard. An older release without these dependencies fails closed; this registration does not authorize historical response reinterpretation or old-Run recovery. Changes to the qualification reason guard or intake limit change the execution surface, and other unregistered creation dependencies remain rejected.

## Qualification scope

Focused disposable tests cover normal and HTTP rejection, restricted operator creation, pause/WIP/projection guards, invalid reasons, unregistered or unprocessed Source misuse, atomic audit, serial/concurrent idempotency and absence of public exposure. All test provider traffic is forbidden. Live validation requires explicit authorization, uses a clean R2 Run with a durable zero-call plan checkpoint, then one bounded-only action. The first failure stops execution without retry or new subdivision; complete success aggregates through the existing path and stops before Semantic.

Schema remains 12. Evidence Binding, Wire, Claim identity, R2 provider contract, aggregation, analyzer, Production and Current View are unchanged. Historical Run #13 is not recovered or reinterpreted.
