# Codex continuation brief — pro_a v0.2.2.1 Relation Evidence Foundation

## 当前状态

AI Hardware Node Universe v0.1 已正式落库：256 个 active Nodes，EML 为 Product，170 条 current `part_of`，7 条 `retired_r1_migration`。后续不得修改该 Node Set、R1 structural graph 或冻结业务规则，也不得自动导入 functional relation candidates。

Relation Evidence Foundation 已实现：schema `0.2.2` 新增 `relation_evidence_links`；保留 legacy `node_relations.evidence_claim_id` 并幂等 backfill；一个 Relation 可累积多个 supports/contradicts Claims。`part_of` 可无 Evidence，其他正式 current Relation 必须有真实 supporting Claim；contradicts 不自动 retire Relation；relation seed 仅允许 `part_of`。

New Node acceptance 不会将 `related_node_ids` 自动正式化为 `related_to`；`related_claim_ids` 只保留为 Claim↔Node linkage，不作为 Relation-specific Evidence。`suggested_parent_node_ids` 的 `part_of` 行为保持不变。非结构 Relation 仍须通过明确的 Relation 创建路径及 supporting Claim gate，不新增 Relation Proposal、证据自动选择或自动审批逻辑。

此前 v0.2.2.1 的程序化 `evidence_scope`、单一公司确定性行业主句拦截、Actual/Guidance 原子拆分、公司主体 attribution mapping、Current View 确定性排序及 impact recovery 均保留。v0.1.1 稳定性状态机、历史 migration 和冻结业务规则未改变。

同一份昀冢科技 MLCC Standard 样本已在全新 workspace 真实复跑：Source 为 B 级 secondary，14 条 Claims 均通过 Evidence 校验，MLCC 关联 13 条 Claims；DeepSeek 的多次 Initial View 输出因 attribution、Applications、single-company scope 或 target-centric 风险不合规而被程序拦截，同一 Impact Review 持久化为 `retry`，未创建半合规 Current View Proposal。后续若处理该问题，不得通过放宽硬校验强行生成 Proposal。开始修改前先阅读：

1. `docs/REQUIREMENTS_FROZEN.md`
2. `README.md`
3. `src/pro_a/schema.sql`
4. `src/pro_a/pipeline.py`
5. `src/pro_a/propagation.py`

## 不可破坏的约束

- 原始 Source 不被 AI 改写。
- 新 Node 必须 Proposal + 用户确认。
- 任何 Current View 变更必须 Proposal + 用户确认。
- Current View 版本使用 `v_YYYYMMDD[_NN]`，不覆盖旧版。
- Source 物理只存一次，多 Node 关联保存在 DB。
- Propagation 传播 Impact Review，不复制结论。
- 同 Batch 同 Node 只评估一次，防循环。
- `part_of` 是唯一允许无 Evidence 创建的正式 Relation。
- 非 `part_of` current Relation 必须至少有一个 active supporting Claim；contradicts 只记录证据，不自动改变 Relation 状态。
- Relation seed 只能写入 `part_of`，不得绕过 Evidence gate。
- IMA 是存储/RAG层，不是知识状态机的 Source of Truth；SQLite 是 v0.1 的逻辑状态源。

## 后续优先事项

P0：
1. 为 Standard/Deep 增加可回放的 LLM 分析任务（失败重试、幂等）。
2. Claim 语义去重/冲突候选检索，不要每次把大量历史 Claim 全量喂给模型。
3. 更完整的 Node Relation Proposal（研究关系本身也要 Evidence；不得自动审批）。
4. Proposal “修改后接受”。
5. Knowledge Gap 生命周期命令：resolve / reopen / supersede。
6. Research Question Current Answer 自动更新与审批规则。

真实 IMA 集成尚未开始，不应在第一份 Standard 资料人工验收前自行启用。

P1：
1. PDF 表格/图表更可靠解析。
2. 图片多模态解析（避免 OCR 作为默认方案）。
3. Source Updated Version / Near Duplicate 更完整识别。
4. Node-specific Materiality Threshold 配置。
5. 外部互联网 Research Output 回灌。

## 测试要求

每次修改至少保持：

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m compileall -q src tests
```

并新增对应回归测试。

当前基线：105 tests passed；`compileall` 与 `git diff --check` 通过。
