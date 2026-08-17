# Codex continuation brief — post-v0.2.3B.1

## 当前状态

截至 2026-08-17，v0.2.3B.1 / B.1.1 已合入 `main`。

AI Hardware Node Universe v0.1 已正式落库：256 个 active Nodes，170 条 current `part_of`，7 条 `retired_r1_migration`。该 Node Set、R1 structural graph 与冻结业务规则不得擅自修改。

Relation Evidence / Proposal / Candidate Validation 链路已经实现：

```text
LLM Relation Candidate
→ supporting Claim resolution
→ atomic Claim / Evidence validation
→ semantic validation
→ direction validation
→ pending node_relation Proposal
→ human confirmation
→ formal Relation + relation_evidence_links
```

B.1.1 已修复 passive / reverse direction、generic marker bypass 与 `C1/C2` scope integrity 问题；合并前验证基线为 213 tests passed，`compileall` 与 `git diff --check` 通过。

IMA 仍保持关闭。正式数据库、Propagation / Impact Recovery 与冻结规则未因 B.1.1 修改。

## 当前阶段

当前不是继续开发新功能，而是：

**R1 Relation Baseline Acceptance preparation**。

Codex 恢复后，默认第一任务是执行 `docs/R1_ACCEPTANCE.md`，而不是直接修改 analyzer / pipeline / prompt。

真实资料验收前必须先阅读：

1. `docs/REQUIREMENTS_FROZEN.md`
2. `README.md`
3. `docs/R1_ACCEPTANCE.md`
4. `docs/RELATION_SEMANTICS.md`
5. `docs/ROADMAP.md`
6. `src/pro_a/schema.sql`
7. `src/pro_a/analyzer.py`
8. `src/pro_a/pipeline.py`
9. `src/pro_a/propagation.py`

## 不可破坏的约束

- Raw Source immutable，AI 不得改写原始资料。
- Source 物理只存一次，多 Node 关联保存在 DB。
- 新 Node 必须 Proposal + 用户确认。
- 任何正式 Current View 变更必须 Proposal + 用户确认。
- Current View 使用 `v_YYYYMMDD[_NN]`，不覆盖历史版本。
- `part_of` 是唯一允许无 Evidence 创建的正式 Relation。
- 非 `part_of` current Relation 必须至少有 active supporting Claim。
- Relation-specific Evidence 不得由普通 Claim↔Node linkage 替代。
- LLM Relation Candidate 不得直接 formalize；必须通过程序 Evidence / semantic / direction validation，并先形成 pending Proposal。
- unresolved temporary Claim ref 不得进入 Proposal。
- `supporting_claim_refs` / `_resolved_supporting_claim_indices` 不得泄漏到 Proposal payload。
- 合法业务文本中的 `C1` / `C2` 等字符串不得被清洗或改写。
- Propagation 传播 Impact Review，不复制结论。
- 同 Batch 同 Node 只评估一次，防循环。
- IMA 是存储/RAG层，不是知识状态机的 Source of Truth；SQLite 是 Canonical Knowledge Engine。

## Codex 恢复后的默认第一任务：R1 Baseline

除非用户明确改变优先级，否则：

1. checkout / pull 最新 `main`。
2. 不修改业务代码。
3. 不 add / commit / modify 未跟踪 R1 原始资料。
4. 使用 isolated workspace / temporary database。
5. 全量或可复现分层抽样运行真实资料。
6. 对照人工 Gold Set 与 `docs/R1_ACCEPTANCE.md` 做 candidate-level audit。
7. 区分 Hard Failure、False Positive、False Negative、Conservative Reject、Ambiguous。
8. 将错误归因到 Source→Claim、Claim→Candidate、endpoint matching、validator、Proposal identity 等具体 pipeline stage。
9. 若存在任一 Hard Failure：结论 `REOPEN B.1`，只提交最小复现与诊断，不要边测边修。
10. 若 Hard Failure = 0：B.1 可 PASS；coverage / conservative rejection 问题进入 B.2 backlog。

## Hard Failure 原则

安全性错误优先于覆盖率错误。以下类型必须视为 B.1 blocker：

- reversed relation direction 被放行并形成 Proposal；
- supporting Claim 实际不支持 Relation；
- atomic Claim mapping 指向错误 child Claim；
- unresolved temp Claim ref / internal resolution field 泄漏到 Proposal；
- 合法 scope/reason 被篡改；
- 不同 scope Proposal identity 被错误合并；
- endpoint 与 Evidence 实体不一致却放行；
- negated relation 被当作正向 relation；
- R1 验收污染正式数据库或正式 Relation。

完整定义以 `docs/R1_ACCEPTANCE.md` 为准。

## 后续 backlog 原则

不要预设 B.2 必须增加 regex / syntax heuristic。

B.2 应由 R1 真实失败样本驱动。可能包括但不限于：

- Relation ontology / endpoint type compatibility；
- language / syntax coverage；
- candidate recall；
- endpoint matching；
- Claim atomicity；
- evidence disambiguation；
- reject reason taxonomy / observability。

如果问题来自 upstream LLM candidate、Node match 或 Claim extraction，不应通过放宽 Relation validator 来“修”。

其他尚未完成的 P0 / P1 见 `docs/ROADMAP.md`。

## 测试要求

任何后续代码修改至少保持：

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m compileall -q src tests

git diff --check
```

并新增对应最小回归测试。

当前最近已知基线：213 tests passed；`compileall` 与 `git diff --check` 通过。
