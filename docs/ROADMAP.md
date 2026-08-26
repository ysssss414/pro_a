# pro_a Roadmap — Phase 2 Knowledge Explorer

Status: **Phase 1 complete and frozen; Phase 1.1 complete; Phase 2.2 complete**

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

### Next recommended milestone — Phase 2.3 Provenance & Knowledge Detail

在 Phase 2.2 review/merge 后，深化 Evidence / Source provenance 与 Knowledge Detail 的审阅体验。继续保持 API-only read boundary、current 1-hop 上限和 Production read-only；该候选里程碑不自动授权 write path、chatbot、vector DB、recursive graph traversal 或 frozen contract 变更。

## Carried backlog

- Relation Candidate generation 漏召回；
- contract-constrained functional Relation false negatives；
- Claim semantic deduplication / conflict retrieval；
- Proposal “modify then accept”；
- Knowledge Gap 与 ResearchQuestion 完整生命周期；
- 更可靠的表格、图表、多模态与 source-version 处理；
- 正式 IMA integration acceptance 与更高层 review UI。

这些 backlog 不授权修改 Phase 1 frozen contracts，也不属于 Phase 2.2 Explorer MVP。

## Decision rule

错误 canonical knowledge 与 unsafe acceptance 的风险优先于 coverage。不得用 fuzzy linking、evidence-free association、Gold-specific hardcode 或 validator weakening 补偿 upstream model loss。SQLite 继续是唯一 Source of Truth，Phase 2 read layer 不获得 Production write authority。
