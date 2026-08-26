# pro_a Roadmap — Phase 2 Knowledge Research Surface

Status: **Phase 1 complete and frozen; Phase 1.1 complete; Phase 2.3A complete; Phase 2.3B audit complete**

## Completed — Phase 1

Phase 1 的 Source → Claim → Node / Relation Candidate → Proposal / Review → controlled Production maintenance 主链路已完成并冻结。Operational Acceptance 为 `PASS_WITH_RELATION_BACKLOG`；Relation validation operational，但 Relation generation 尚未达到 operational ready。

冻结记录见 `docs/PHASE1_FREEZE.md`，冻结业务规则见 `docs/REQUIREMENTS_FROZEN.md`。

## Completed — Phase 1.1 AI Hardware universe

Phase 1.1A 完成经人工 adjudication 的 Node、alias 与四条 structural `part_of` 扩展；Phase 1.1B 完成固定 26 条 functional Relation candidates 的 Evidence reconstruction、frozen-validator diagnosis 与人工 adjudication。

最终 Production baseline：

- Nodes：293；
- Aliases：737；
- Node Relations：181；
- current `part_of`：174；
- functional Relation import：0；
- SHA-256：`8a4247b9da2c3d6f288f8a8af8519f33673bc45b5a4327a57c50436d39dd50b4`。

Closure 见 `docs/PHASE1_1A_NODE_UNIVERSE_CLOSURE.md` 与 `docs/PHASE1_1B_FUNCTIONAL_RELATION_CLOSURE.md`。

## Started — Phase 2 Knowledge Exploration & Interaction Layer

Phase 2 在 canonical SQLite knowledge state 上建立本地交互层，顺序为：

```text
Search
→ Browse
→ Trace
→ Research
→ Ask
```

优先 deterministic knowledge interaction；`Ask` 晚于可验证的 Search / Browse / Trace / Research，不以 chatbot 作为起点。

### Phase 2.0 — kickoff documentation

状态：**complete**。README、Roadmap、continuation brief 与 Changelog 已同步到最新 Phase 1.1 closure 和 Phase 2 架构边界。

### Phase 2.1A — deterministic read-only query/API foundation

状态：**complete**。当前能力包括：

- 独立 SQLite `mode=ro` query/read model；
- stats、canonical/alias search、bounded node list；
- node detail、正确 `part_of` parent/child direction；
- current 1-hop neighborhood；
- Node → Claims → Source metadata；
- direct / Claim-linked Source provenance 与 Source dedup；
- FastAPI response models、404/422/503 contract 和本地只读启动方式；
- isolated temporary SQLite query/API regression tests。

### Phase 2.2 — Knowledge Explorer MVP

状态：**complete**。已建立独立 React + TypeScript + Vite UI，覆盖 canonical/alias Search、Node Browse、current 1-hop Cytoscape Trace、Overview / Claims / Sources 与 direct / claim provenance。UI 只消费 Phase 2.1A API，包含 debounce、stale-request abort、并行 Node 数据加载、URL selection state、empty/loading/error/retry 状态及前端单元/组件测试。

### Phase 2.3A — Knowledge Detail & Research Surface

状态：**complete**。新增 Current View、Research Question、Knowledge Gaps 与 Source Detail 的确定性只读 query/API；Explorer 增加 View / Research tabs 和右栏 Source Detail mode。Current View 复用正式 revision ordering，RQ 引用 Claim 可读解析且容忍 missing refs，Gap 保留全部状态并按研究实用性排序，Source Detail 提供 metadata、direct Node links、Source Claims 与 Claim-linked Nodes，不暴露归档路径。前端 core/knowledge 模块独立失败并继续取消 stale requests。

### Phase 2.3B — Knowledge Coverage Audit

状态：**complete (audit-only)**。新增 `src/pro_a/coverage.py` 与确定性测试，使用现有 read-only query boundary 对 Production Node / alias / hierarchy / Source / Claim / Current View / Research Question / Knowledge Gap / Relation evidence coverage 做盘点。生成 Node、Source、Claim 和 unlinked Claim 四份稳定 CSV 及正式报告 `docs/PHASE2_3B_KNOWLEDGE_COVERAGE_AUDIT.md`。本阶段没有 write API、schema 变化、自动 Claim → Node linking、LLM 调用或 Production mutation。

Production audit 结果：293 active Nodes、737 aliases、181 stored Relations（174 current `part_of`，0 current functional）、2 Sources、12 Claims、0 Claim → Node links、0 Current Views、0 RQs、0 Gaps。12 Claims 全部未链接，且只有 ambiguous review candidates；`CLAIM_NODE_ACTIVATION_READY = NO`。下一步必须是显式人工 Claim → Node adjudication review package。

### Phase 2.3C — Claim–Node Human Adjudication Package

状态：**HUMAN_REVIEW_PACKAGE_READY**。对当前全部 unlinked Claims 生成只读 Markdown/CSV 人审包；候选 Node 仅来自 Source direct link、exact canonical 和 exact alias 的可复现并集。所有 `decision` 均为 `PENDING`，不自动选择 Node、不创建 Claim → Node link、不写 Production。下一步是由人工 reviewer 完成人审表。

### Phase 2.3D — Controlled Claim–Node Activation

状态：**complete**；`PHASE2_3D_CLAIM_NODE_ACTIVATION_COMPLETE = true`。基于明确人工 adjudication，在单一事务中写入 11 条 `Claim → MLCC`、`role=related` link；电子陶瓷收入 Claim 保持 NO_LINK。Production 现有 1 个 Claim-covered Node、11 条 MLCC-linked Claims、1 条 unlinked Claim；MLCC 达到 `LEVEL_2_EVIDENCE_CONNECTED`。Claim status、Source links、Current Views、RQ、Gap 与 Relations 均未改变。

### Phase 2.3E — Entity Granularity & Claim Attribution Review

状态：**complete (read-only review)**。Production 中不存在 `昀冢科技` 的 exact canonical/alias Node；11 条 MLCC-linked Claims 分为 3 条 `MLCC_PRIMARY` 与 8 条 `COMPANY_PRIMARY_MLCC_CONTEXT`。已生成非执行型 Company Node 与 Claim attribution proposal，所有既有 MLCC links 保持不变。当前仅有 `role=related`，不足以表达 subject/context，因此 `ROLE_MODEL_SUFFICIENT = NO`、`MLCC_CURRENT_VIEW_READY = PARTIAL`；不得把 11 条 linked Claims 整体直接用于 MLCC Current View。

### Next milestone

等待显式授权的人审写入阶段：先审批 `昀冢科技` Entity Node，并冻结最小 Claim link role 语义，再新增 8 条 Company subject links、保留 MLCC links 并审查其 context role。不得由 Phase 2.3E 自动写入 Production 或生成 Current View。

## Carried backlog

- Relation Candidate generation 漏召回；
- contract-constrained functional Relation false negatives；
- Claim semantic deduplication / conflict retrieval；
- Proposal “modify then accept”；
- Knowledge Gap 与 ResearchQuestion 完整生命周期；
- 更可靠的表格、图表、多模态与 source-version 处理；
- 正式 IMA integration acceptance 与更高层 review UI。

这些 backlog 不授权修改 Phase 1 frozen contracts，也不属于 Phase 2.3A Research Surface。

## Decision rule

错误 canonical knowledge 与 unsafe acceptance 的风险优先于 coverage。不得用 fuzzy linking、evidence-free association、Gold-specific hardcode 或 validator weakening 补偿 upstream model loss。SQLite 继续是唯一 Source of Truth，Phase 2 read layer 不获得 Production write authority。
