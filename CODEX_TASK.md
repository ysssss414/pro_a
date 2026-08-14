# Codex continuation brief — pro_a v0.2.2.1-current-view-fix-and-cleanup

## 当前状态

v0.2.2.1 已在 v0.2.2 基础上增加程序化 `evidence_scope`、单一公司确定性行业主句拦截、Actual/Guidance 原子拆分、公司实际价格 nature 修正、Product Applications 显式 Evidence 校验，以及完整公司主体 attribution mapping；Current View 确定性排序和 pending New Node 查询已收敛为单一实现。v0.1.1 稳定性状态机、历史 migration 和冻结业务规则均保留。

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
- IMA 是存储/RAG层，不是知识状态机的 Source of Truth；SQLite 是 v0.1 的逻辑状态源。

## 后续优先事项

P0：
1. 为 Standard/Deep 增加可回放的 LLM 分析任务（失败重试、幂等）。
2. Claim 语义去重/冲突候选检索，不要每次把大量历史 Claim 全量喂给模型。
3. 更完整的 Node Relation Proposal（研究关系本身也要 Evidence）。
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
