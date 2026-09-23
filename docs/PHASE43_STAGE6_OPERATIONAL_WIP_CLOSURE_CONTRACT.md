# Phase 4.3 Stage 6 — Operational WIP Closure Contract

## Scope and authority

Stage 6 records lifecycle resolution for the frozen Stage 2 semiconductor Foundation population. It does not alter the original packet, the Stage 2 review audit, Production, Current Views, the Stage 4D overlay, or historical receipts. The immutable artifact contract is `phase43-stage6-lifecycle-closure-v1`; its ID is `phase43-stage2-foundation-v1`.

The authority set is fixed to population `b363748e9aa05be4d66d7ff5c3d0008e9a80df29a25741f72d60c7c32c983b51` and original immutable packet `06006a1c98247f1803dac9cdcd0f10ade5d84beddc56a12e3768e5a9e5bfc66c`. HUMAN_USER qualification supplies 105 resolutions: 76 mandatory items plus the 29-item residual sample. The remaining 169 rows close only when the two sealed AI reviews have substantive or exact agreement, no mandatory trigger, the same native decision, and no HUMAN_USER attribution.

The closure is an operational lifecycle record. Its exact resolution sources are `HUMAN_USER_QUALIFICATION` and `AI_POLICY_QUALIFICATION`. It grants no Production apply authority.

## Immutable artifact

`lifecycle_closure/phase43_stage2_foundation_v1.json` contains exactly 274 sorted, unique resolution rows. Each row binds candidate ID, candidate type, native content SHA, population SHA, original packet SHA, resolution source, native decision, follow-up status, authority, and its own logical SHA. The document has a logical closure SHA computed without its `closure_sha256` field.

The builder validates every input binding and the frozen Review A and Review B record bindings for all 274 candidates before writing. Existing output bytes must match exactly. Two clean builds must be byte-identical. `docs/phase43_stage6_lifecycle_source_manifest.json` records both the tracked aggregate file hashes and the sealed authority identities referenced by HUMAN_USER authorization; these are intentionally distinguished.

## Schema and apply path

Workbench schema 11 adds append-only `lifecycle_closure_meta` and `lifecycle_resolutions` tables. Update and delete triggers protect both tables. The official chain is schema 8→9 through `prepare_domains`, 9→10 through `prepare_stage1_scale`, and 10→11 through `prepare_stage6_lifecycle`.

`apply-stage6-lifecycle` requires an offline, drained database, the exact allowed Workbench baseline, the exact Production SHA, the validated closure, and an exact backup written before the first migration. It is idempotent for identical closure bytes and fails closed on identity or content conflict. If the original packet is registered, apply verifies the packet identity and exact candidate set before binding its artifact ID. If it is absent, `artifact_id` stays null; apply does not recreate a historical packet.

The Stage 6 implementation exists for a later operator-controlled real apply. Stage 6 qualification runs it only on an isolated byte copy.

## Capacity semantics

Schema 10 retains its existing capacity behavior. Schema 11 uses capacity contract `phase43-stage6-lifecycle-capacity-v1` and defines:

- **Native pending**: rows whose native Review projection remains pending.
- **Lifecycle closed**: immutable historical resolutions registered in schema 11.
- **Operational pending**: native pending rows with no lifecycle resolution bound to the same registered artifact and candidate.
- **Follow-up governance**: closed rows whose native result remains `DEFER` or `KEEP_NEEDS_REVIEW`.

Under schema 11, `pending_review_rows` means `operational_pending_review_rows`; `native_pending_review_rows` preserves the historical native count. Stage 1 hard and soft WIP limits use operational pending under schema 11. Pauses, incomplete projections, and the 24-hour run limit remain independent blockers. A lifecycle closure cannot suppress pending work from later packets because resolution matching requires both artifact ID and candidate ID.

Supported schema 11 queues are `operational_pending`, `lifecycle_closed`, `human_qualified`, `ai_policy_closed`, `followup_governance`, and `native_pending`. Existing queues retain their schema 10 behavior; `needs_review` and `human_required` mean operational pending under schema 11.

`GET /api/workbench/v1/operations/capacity` exposes the capacity projection. Source Operations presents current native and operational WIP separately from historical lifecycle totals. Review Workbench shows a closure banner only when the closure is bound to that registered artifact.

## Safety invariants

- Production SHA remains `6e5a303ccee9c192c350c2550cc232649e56ffee939b7a09cd6b170cc1c8fba1` during qualification.
- Real Workbench SHA remains `c28dd60c94deeb8c897c6180b9fec2366ffaef7b671a6c9b0ddf7af9047279f3` during qualification.
- Original Stage 2 packet and frozen Stage 2 evidence remain unchanged.
- Closure registration cannot create review audit events or claim new HUMAN_USER decisions.
- No provider dispatch, Source upload, processing run, Current View mutation, overlay mutation, or Production apply is part of this contract.
