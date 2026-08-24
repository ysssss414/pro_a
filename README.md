# pro_a v0.3.0 — Phase 1 frozen baseline

`pro_a` 是面向长期投研的本地 Canonical Knowledge Engine。它把研究材料维护为可追溯、可验证、可人工审批的知识状态，而不是只保存文档。

```text
Source
→ Claim
→ Existing Node Match / Candidate Node
→ Relation Candidate
→ review artifacts
→ human-approved controlled DB maintenance
```

SQLite / `pro_a` 是知识状态的 Source of Truth。IMA 仅预留为文档存储、Search/RAG 与研究成果承载层，Phase 1 保持关闭。

## Phase 1 冻结状态

冻结日期：2026-08-24。

- Production DB：`workspace/pro_a.db`
- SHA-256：`8bce2b47df971e527de3552ca0415160868b258c0fcd4a8f6d2f20f40a60541c`
- Nodes：280
- Aliases：706
- Node Relations：177（170 条 current `part_of`，7 条 retired migration）
- IMA：off
- Release version：`0.3.0`
- Phase 1 decision：`PASS_WITH_RELATION_BACKLOG`

详细冻结记录见 [`docs/PHASE1_FREEZE.md`](docs/PHASE1_FREEZE.md)。

## 已达到 operational ready

- Archive / Standard / Deep Source ingestion、SHA-256 去重与不可变归档。
- PDF / Word / Excel / PowerPoint / Markdown / TXT 基础解析。
- Claim 抽取、精确 Evidence 定位、attribution 与 atomicity 校验。
- Existing Node Match 的 canonical / alias exact-evidence contract。
- Candidate Node 与 ResearchQuestion Proposal、人工审批和审计 artifact。
- Relation Candidate 的 supporting Claim、Evidence、semantic 与 direction 程序校验。
- pending Proposal 路径；非结构 Relation 不会由模型直接 formalize。
- Production-copy / staging 上的 backup、atomic apply、receipt、幂等重跑与 rollback 工作流。
- AF-007 source survivability：单个非法 Analyzer `node_candidate` 只做局部拒绝，合法 sibling objects 保留；`Metric` 仍不是合法 Node Type。

## 已知能力边界

Relation validation 与安全拒绝链路可用，但 Relation Candidate generation 仍存在明显漏召回。Operational probes 的 2 条 exact-endpoint / exact-evidence 简单关系均未形成合法 candidate，因此：

`RELATION_EXTRACTION_OPERATIONAL_READY = false`

这属于已记录的 Relation generation / model-quality backlog，不通过放宽 Evidence、direction、identity、collision 或 Node Type 规则修复。Source / Claim / Node / review / controlled DB maintenance 主链路仍通过 Operational Acceptance。

## 冻结规则摘要

完整规则以 [`docs/REQUIREMENTS_FROZEN.md`](docs/REQUIREMENTS_FROZEN.md) 为准：

- Raw Source immutable；同一 Source 物理只存一次。
- 新 Node 与正式 Current View 变化必须 Proposal + 人工确认。
- `part_of` 是唯一允许无 Evidence 创建的正式 Relation。
- 非 `part_of` current Relation 必须有 active relation-specific supporting Claim。
- LLM Relation Candidate 必须经过程序 Evidence / semantic / direction validation。
- Existing Node Match 必须由 source 中 canonical name 或 alias 的可定位 Evidence 支持。
- Propagation 传播 Impact Review，不复制结论。
- IMA 不是知识状态机。

## Windows 快速开始

推荐 Python 3.10+：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\bootstrap.ps1
Copy-Item .\config.example.toml .\config.toml
.\.venv\Scripts\pro-a.exe init
```

Standard / Deep 分析需要项目配置允许的兼容模型，并通过环境变量提供 key；不要把 key 写入仓库：

```powershell
$env:PROA_LLM_API_KEY="..."
.\.venv\Scripts\pro-a.exe ingest --once
```

查看 Source 与 Proposal：

```powershell
.\.venv\Scripts\pro-a.exe source show SRC_xxx
.\.venv\Scripts\pro-a.exe proposals list
.\.venv\Scripts\pro-a.exe proposals show PROP_xxx
```

任何 Production mutation 都应使用明确目标、precondition SHA、独立 backup、单 transaction、receipt、post-write QA 与人工授权。默认验收/实验只在 isolated copy 或 staging 上运行。

## 后续里程碑

Phase 1.1 尚未启动。下一候选里程碑是 Expanded Knowledge Universe / R2，详见 [`docs/ROADMAP.md`](docs/ROADMAP.md)。在用户明确启动前，不修改 Phase 1 冻结规则，不自动继续 Recall/prompt 调优。
