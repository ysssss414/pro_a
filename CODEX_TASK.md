# Codex continuation brief — Phase 1 frozen

## Current state

Phase 1 于 2026-08-24 完成并冻结。当前 release version 为 `0.3.0`，Production baseline 为：

- `workspace/pro_a.db`
- SHA-256 `8bce2b47df971e527de3552ca0415160868b258c0fcd4a8f6d2f20f40a60541c`
- 280 Nodes / 706 Aliases / 177 Node Relations
- IMA off

run_007 已 PASS；Operational Acceptance 为 `PASS_WITH_RELATION_BACKLOG`，且 `READY_FOR_PHASE1_FREEZE = true`。

## Default continuation behavior

Phase 1.1 未启动。除非用户明确给出新任务，不继续 prompt/Recall 优化、不启动 R2、不写 Production、不启用 IMA。

恢复工作时先读：

1. `docs/PHASE1_FREEZE.md`
2. `docs/REQUIREMENTS_FROZEN.md`
3. `README.md`
4. `docs/ROADMAP.md`
5. 与用户明确任务直接相关的 final artifact

不要重新做 B.2B–B.2F、run_006/run_007 或 Operational forensic analysis。

## Retained Phase 1 fix

AF-007 deterministic sub-object isolation 是唯一 Phase 1 closure production-code change：非法 `Metric` 或 malformed `node_candidate` 仅局部 reject，同一 Analyzer response 的合法 Claims、Node Matches、Relation Candidates 与 sibling candidates 继续处理。Metric type rule、不猜类型与其他 frozen validators 保持不变。

## Known backlog

- `RELATION_EXTRACTION_OPERATIONAL_READY = false`：Relation validation operational，但 generation 漏召回。
- `NM-002` / `NM-005`：`MODEL_QUALITY_BACKLOG`；受控 prompt variants 均 NO-GO。
- `NM-001` / `NM-006`：contract-constrained。
- `RJ-009` / `PD-002` / `HW-001`：Phase 1 不再修复。

不得用 exact-match fallback、fuzzy linking、evidence-free linkage、Gold-specific hardcode 或 direction/evidence gate weakening 处理这些 backlog。

## Production mutation contract

任何 Production write 都需要新的明确人类授权，并至少包含 absolute target、precondition SHA、独立 backup、单 transaction、deterministic QA、正式 receipt、post-write SHA 与 rollback plan。默认诊断和验收只读 Production，并在 isolated copy / staging 上操作。
