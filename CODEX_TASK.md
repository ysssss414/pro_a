# Codex continuation brief — pro_a v0.2.0-real-ingestion

## 当前状态

v0.2.0-real-ingestion 第一阶段已补齐 Relation Seed、LLM 严格输出校验、完整 Ingestion Receipt 和只读 Source 诊断。v0.1.1 的原子状态机、幂等/stale、确定性版本排序、持久 Impact Review、程序化 Evidence Sufficiency 和 Source 模式升级继续保留。冻结业务规则未变。开始修改前先阅读：

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
1. 使用真实 LLM API 人工验收第一份 Standard 投研资料，并根据 receipt 修正 Prompt/校验兼容性。
2. 为 Standard/Deep 增加可回放的 LLM 分析任务（失败重试、幂等）。
3. Claim 语义去重/冲突候选检索，不要每次把大量历史 Claim 全量喂给模型。
4. 更完整的 Node Relation Proposal（研究关系本身也要 Evidence）。
5. Proposal “修改后接受”。
6. Knowledge Gap 生命周期命令：resolve / reopen / supersede。
7. Research Question Current Answer 自动更新与审批规则。

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
pytest -q
python -m compileall -q src tests
```

并新增对应回归测试。
