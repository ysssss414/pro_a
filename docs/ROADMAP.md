# pro_a Roadmap — post-Phase 1 freeze

Status: **Phase 1 complete and frozen; Phase 1.1 not started**

## Completed milestone — Phase 1

Phase 1 已在 2026-08-24 完成：

```text
R1 baseline acceptance
→ B.2 loss attribution and inventory reconciliation
→ approved B.2C Production Node import
→ AF-007 deterministic source-survivability fix
→ B.2E/B.2E.1 recall decisions
→ B.2F final regression
→ run_007
→ Operational Acceptance
→ Phase 1 freeze
```

最终状态：

- Production：280 Nodes / 706 Aliases / 177 Node Relations；
- run_007：PASS，无新系统性 safety blocker；
- Operational Acceptance：`PASS_WITH_RELATION_BACKLOG`；
- Source / Claim / Node review / controlled DB maintenance 工作流可用；
- Relation validation operational，Relation generation 尚未达到 operational ready；
- IMA off；冻结业务规则未改变。

冻结记录见 `docs/PHASE1_FREEZE.md`，历史验收规范保留在 `docs/R1_ACCEPTANCE.md`。

## Known backlog carried forward

- Relation Candidate generation 漏召回；Operational exact probes 0/2。
- `NM-002` atomic Claim extraction 与 `NM-005` direction generation：`MODEL_QUALITY_BACKLOG`。
- `NM-001` 与 `NM-006`：contract-constrained false negatives。
- `RJ-009` / `PD-002` / `HW-001`：Phase 1 不再修复。
- Claim semantic deduplication / conflict retrieval。
- Proposal “modify then accept”。
- Knowledge Gap resolve / reopen / supersede 与 ResearchQuestion Current Answer 生命周期。
- 更可靠的表格、图表、多模态与 source-version 处理。
- 正式 IMA integration acceptance 与更高层 review UI。

这些 backlog 不构成已冻结 Phase 1 的追补开发授权。

## Next candidate milestone — Phase 1.1 / R2

Phase 1.1 尚未开始，需用户另行授权。候选目标是 **Expanded Knowledge Universe / R2**：

1. 以独立的新材料集扩展 Node/alias universe；
2. 继续使用 human-gated inventory reconciliation 与 controlled import；
3. 设计 R2 Gold / operational probes，避免复用 Phase 1 prompt-tuning cases；
4. 在不放宽 frozen validators 的前提下评估 Relation generation 的 operational usefulness；
5. 如需 prompt/model 改动，先做受控实验，再进入 targeted regression；
6. Production mutation 继续要求显式授权、SHA precondition、backup、atomic apply、receipt 与 rollback contract。

## Decision rule

优先级保持：错误 canonical knowledge 与 unsafe acceptance 高于 coverage。不得用 fuzzy linking、evidence-free association、Gold-specific hardcode 或 validator weakening 补偿 upstream model loss。

## Documentation ownership

- `docs/PHASE1_FREEZE.md`：Phase 1 release closure 与 artifact pointers。
- `docs/REQUIREMENTS_FROZEN.md`：冻结业务规则；仅在用户明确决策后修改。
- `docs/R1_ACCEPTANCE.md`：历史 R1 acceptance contract 与完成状态。
- `docs/RELATION_SEMANTICS.md`：Relation working semantics；本次 freeze 未修改。
- `CODEX_TASK.md`：当前 continuation brief。
- `CHANGELOG.md`：完成历史。
