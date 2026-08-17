# pro_a — post-v0.2.3B.1 baseline

面向长期投研的本地知识处理引擎。核心目标不是“存文档”，而是持续维护可追溯、可验证、可更新的知识状态：

```text
Source
→ Claim
→ Knowledge Node
→ Current View
→ 新 Evidence 持续更新认知
```

SQLite / pro_a 是 Canonical Knowledge Engine；IMA 未来仅承担文档云存储、Search/RAG 与正式研究成果承载。IMA 当前默认关闭。

## 当前基线

截至 2026-08-17，v0.2.3B.1 / B.1.1 已完成并合入 `main`。

当前已验证的 Relation 链路：

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

当前 Relation Candidate baseline 的核心安全性质：

- 非结构 Relation 不可绕过 Evidence gate。
- supporting Claim 必须可解析为真实持久化 Claim。
- atomic split 后只允许唯一支持该 Relation 的 child Claim 进入 Evidence。
- directional Relation 对主动/被动方向进行程序校验；明显 reversed direction 必须拒绝。
- `supporting_claim_refs` 与 `_resolved_supporting_claim_indices` 不进入 Proposal payload。
- 合法业务文本中的 `C1` / `C2` 不再被清洗或改写。
- 不同 scope（例如 `C1 stepping` / `C2 stepping`）保持不同 Proposal identity。
- Proposal 仍须人工确认；系统不得自动 formalize 非结构 Relation。

B.1.1 合并前基线验证：`213 passed`，`compileall` 通过，`git diff --check` 通过。

下一阶段不是继续增加启发式规则，而是先执行真实资料 R1 baseline acceptance。详见 `docs/R1_ACCEPTANCE.md`。

## 已实现

### Source / ingestion

- `archive` / `standard` / `deep` 三种入库模式。
- 本地 Inbox 扫描与文件稳定检测。
- SHA-256 去重、Source ID、不可变本地归档。
- PDF / Word / Excel / PPT / Markdown / TXT 基础解析。
- 失败处理保留 Source、processing job 与 receipt。
- Source 物理只存一次，多 Node 关联保存在 SQLite。

### Claim / Evidence

- Claim 抽取与 Evidence Pointer / Excerpt 校验。
- Unicode NFKC、Markdown 转义还原、空白标准化后的精确 Evidence 匹配。
- Claim `attributed_to` 与公司主体确定性约束。
- Actual / Guidance 等原子化处理。
- Evidence 无法定位时自动降级为 `needs_review`。

### Knowledge Node

- 冻结 Primary Type：Industry / Segment / Technology / Product / Material / Equipment / Entity / Application / Standard / Policy / Theme / Event / ResearchQuestion。
- 新 Node 必须 Proposal + 人工确认。
- Candidate Node 独立研究价值门槛。
- Existing Node Match 必须有 canonical name / alias Evidence。
- 父级 / 祖先仅由已确认 `part_of` 推导。
- AI Hardware Node Universe v0.1 当前正式状态：256 active Nodes、170 条 current `part_of`、7 条 `retired_r1_migration`。

### Relation / Relation Evidence

- `relation_evidence_links` 支持一条 Relation 累积多个 supports / contradicts Claims。
- `part_of` 是唯一允许无 Evidence 创建的正式 Relation。
- 非 `part_of` current Relation 必须至少有 active supporting Claim。
- Relation seed 仅允许 `part_of`。
- 手工 Relation Proposal 支持显式 supporting Claim。
- LLM 可生成 Relation Candidate，但程序必须进行 Evidence / semantic / direction validation 后才允许创建 pending Proposal。
- stale Relation Proposal recovery 与 Proposal identity 处理已实现。

### Current View / propagation

- Current View 采用不可覆盖的日期版本：`v_YYYYMMDD[_NN]`。
- 所有正式 Current View 变化必须 Proposal + 人工确认。
- Minor / Material / Thesis Change 分级。
- Material / Thesis 存在 Evidence Sufficiency 程序门槛。
- Initial Current View 支持单一 Source，但执行 Evidence Scope Constraint。
- Target-Node-centric、attribution、Claim ID、Company→Industry scope 等程序校验。
- `key_facts` 与 Judgment-backed `core_logic` 分离。
- Product Current View 支持 applications / demand drivers / supply capacity / pricing / major suppliers / product evolution。
- Current View 确认后按“上下/结构关系优先，再相关关系”触发 Impact Review；目标 View 无需变化则停止该路径。
- Impact Review 持久化、retry、stale recovery 与确定性质量门槛已实现。

### Gap / Research Question

- Knowledge Gap 可自动产生。
- ResearchQuestion 属于新 Node，必须人工确认。
- Gap 完整生命周期与 RQ Current Answer 自动更新仍属于后续工作。

## 冻结设计边界

冻结业务规则以 `docs/REQUIREMENTS_FROZEN.md` 为准，本文不覆盖或修改冻结规则。

关键边界：

- Raw Source immutable。
- 新 Node 必须人工确认。
- 正式 Current View 变化必须人工确认。
- 非 `part_of` Relation 必须有 Relation-specific supporting Evidence。
- Propagation 传播 Impact Review，不复制结论。
- SQLite 是知识状态 Source of Truth；IMA 不是知识状态机。
- IMA 当前保持关闭，除非另行明确启动集成验收。

## Windows 快速开始

推荐 Python 3.10+。

```powershell
cd pro_a_v0_1
powershell -ExecutionPolicy Bypass -File .\scripts\bootstrap.ps1
.\.venv\Scripts\pro-a.exe init
Copy-Item .\config.example.toml .\config.toml
```

Standard / Deep 使用兼容 OpenAI Chat Completions 的模型时，例如 DeepSeek：

```powershell
$env:PROA_LLM_API_KEY="..."
```

```toml
[llm]
enabled = true
base_url = "https://api.deepseek.com"
model = "deepseek-chat"
api_key_env = "PROA_LLM_API_KEY"

[ima]
enabled = false
```

单次入库：

```powershell
.\.venv\Scripts\pro-a.exe ingest --once
```

查看 Source 审计：

```powershell
.\.venv\Scripts\pro-a.exe source show SRC_xxx
```

查看 / 审批 Proposal：

```powershell
.\.venv\Scripts\pro-a.exe proposals list
.\.venv\Scripts\pro-a.exe proposals show PROP_xxx
.\.venv\Scripts\pro-a.exe proposals accept PROP_xxx
.\.venv\Scripts\pro-a.exe proposals reject PROP_xxx --reason "证据不足"
```

人工提出 Relation：

```powershell
.\.venv\Scripts\pro-a.exe relations propose NODE_A uses NODE_B `
  --scope "Rubin" `
  --evidence-claim-id CLM_1 `
  --confidence 0.9 `
  --reason "Rubin GPU explicitly uses HBM4"
```

## 当前开发阶段

当前阶段：**post-v0.2.3B.1 / R1 preparation**。

开发顺序：

```text
B.1 freeze
→ R1 Gold Set
→ R1 baseline acceptance
→ pipeline-stage error attribution
→ 决定 B.1 PASS / REOPEN
→ 由真实失败样本生成 B.2 backlog
```

安全性错误优先级高于覆盖率问题：错误 Relation 被正式化的风险高于复杂关系被保守拒绝的风险。

详见：

- `docs/REQUIREMENTS_FROZEN.md` — 冻结业务规则
- `docs/R1_ACCEPTANCE.md` — R1 验收方法与 Hard Failure 定义
- `docs/RELATION_SEMANTICS.md` — Relation working semantics（未冻结）
- `docs/ROADMAP.md` — 当前路线与 backlog 组织方式
- `CODEX_TASK.md` — Codex 恢复后 continuation brief

## 当前明确未完成

- R1 真实资料 Relation baseline acceptance。
- Relation ontology / type compatibility 的最终冻结矩阵。
- Claim 语义去重 / 冲突候选检索。
- Proposal “修改后接受”。
- Knowledge Gap resolve / reopen / supersede 生命周期。
- ResearchQuestion Current Answer 自动更新与审批。
- 更可靠的 PDF 表格 / 图表解析与图片多模态解析。
- Source Updated Version / Near Duplicate 完整识别。
- Node-specific Materiality Threshold。
- 外部互联网 Research Output 回灌。
- 正式 IMA 集成验收。
- GUI。
