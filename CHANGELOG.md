# Changelog

## Phase 2.2 Knowledge Explorer MVP — 2026-08-26

- Added a standalone React + TypeScript + Vite frontend backed only by the Phase 2.1A read API, with a local `/api` development proxy and no backend or schema change.
- Added canonical/alias search with 250 ms debounce and stale-request cancellation, parallel Node selection loading, and restorable `?node=` URL state.
- Added a desktop-first three-column explorer: Search results, directed current 1-hop Cytoscape graph, and Overview / Claims / Sources detail tabs.
- Added Claim Evidence/Source rendering and deduplicated direct/claim Source provenance, plus explicit initial, loading, empty, unavailable and retry states.
- Added typed API client coverage and Vitest/React Testing Library tests for search, graph direction, detail/provenance, offline behavior and StrictMode URL restoration.
- Verified the real browser flow against the local API, including EML search, Node selection, graph-neighbor focus and direct Source provenance. Production remained read-only.

## Phase 2.0 / Phase 2.1A — 2026-08-25

- Synchronized README, Roadmap and continuation state: Phase 1 complete/frozen; Phase 1.1 AI Hardware Node universe and functional Relation requalification complete; Production at 293 Nodes / 737 Aliases / 181 Relations / 174 current `part_of`; functional Relation import count 0.
- Started Phase 2 — Knowledge Exploration & Interaction Layer with the ordered objective `Search → Browse → Trace → Research → Ask`; deterministic interaction precedes chatbot work.
- Added an isolated SQLite read model using URI `mode=ro` plus `query_only`; the HTTP path does not reuse the commit/migration-oriented Phase 1 `Database` connection.
- Added bounded canonical/alias search, node list/detail, correct `part_of` parent/child direction, current 1-hop neighbors, Node Claims with Source metadata, and deduplicated direct/Claim Source provenance.
- Added a FastAPI application with explicit Pydantic response models, local-only default binding, health/stats and Node exploration endpoints, plus 404/422/503 behavior.
- Added deterministic query/API tests backed only by isolated temporary SQLite fixtures. No schema, ingestion, validator, proposal, governance or Production mutation contract changed.

## Phase 1 Freeze — 2026-08-24

- Release version advanced to `0.3.0`: local canonical knowledge engine for long-term research.
- B.2C human-approved Production import added 24 Nodes and 2 aliases; frozen Production is 280 Nodes / 706 Aliases / 177 Node Relations at SHA-256 `8bce2b47df971e527de3552ca0415160868b258c0fcd4a8f6d2f20f40a60541c`.
- Retained the AF-007 deterministic Analyzer sub-object isolation fix and run_006 regression fixture: invalid `Metric` or malformed Node Candidates are locally rejected while valid sibling objects survive; Metric remains unsupported.
- Exact-match fallback and B.2E.1 prompt variants were NO-GO. `NM-002` / `NM-005` remain model-quality backlog; frozen Evidence, direction, identity, collision and Node Type rules were not relaxed.
- B.2F passed 100 targeted and 283 full tests. run_007 completed 10/10 Sources with no new safety blocker or false-positive accepted Relation and confirmed AF-007 source survivability.
- Operational Acceptance completed 3/3 new materials; Source / Claim / Node review and staging maintenance backup/apply/receipt/idempotency/rollback passed.
- Final decision is `PASS_WITH_RELATION_BACKLOG`: Relation validation is operational, but both exact Operational relation probes were omitted by candidate generation, so `RELATION_EXTRACTION_OPERATIONAL_READY = false`.
- Added the Phase 1 freeze record, synchronized release documentation and preserved the final acceptance/recovery evidence chain. This closure made 0 Production writes, 0 LLM/API calls and 0 IMA calls.

## post-v0.2.3B.1 baseline — 2026-08-17

- Relation Candidate Evidence Validation 收口完成并合入 `main`。
- Relation Candidate 必须先解析 supporting Claim，再进行 Evidence / atomic Claim / semantic / direction validation，之后才允许生成 pending `node_relation` Proposal。
- directional Relation 新增主动/被动与 reversed direction 程序校验；`uses` / `supplies` / `produces` 的明显英文被动错误方向必须拒绝，复杂中文被动语义优先保守拒绝。
- generic `marker_between` 不再绕过 reversed detection；reversed 状态优先于 supported。
- Relation Evidence mapping 强化为精确 atomic Claim 支持，不允许无关 child Claim 进入 supporting evidence。
- 临时 Claim refs 只用于内部解析；`supporting_claim_refs` 与 `_resolved_supporting_claim_indices` 不进入 Proposal payload。
- 停止对 Relation `scope` / `reason` 中 `C\d+` 文本进行正则清洗，合法业务文本如 `C1 stepping` / `C2 stepping` 原样保留。
- 不同 scope 保持不同 Proposal identity，避免错误合并。
- B.1.1 合并前验证：213 tests passed；`compileall` 与 `git diff --check` 通过。
- 未修改 schema、冻结业务规则、Propagation / Impact Recovery、正式数据库或 IMA；R1 原始目录未纳入提交。

## v0.2.3B Relation Candidate / Proposal validation — 2026-08-17

- 建立非结构 Relation 的统一 pending Proposal 路径，Relation 不再由模型输出直接 formalize。
- Proposal acceptance 强制执行 Relation-specific Evidence gate；非 `part_of` Relation 必须至少有 active supporting Claim。
- 增加 stale Relation Proposal recovery 与幂等处理。
- Relation Candidate 从 LLM 输出进入程序验证链：endpoint / relation type / supporting Claim resolution / Evidence / semantic / direction。
- 不允许 unresolved temporary Claim reference 创建 Proposal。
- rejected relation candidates 与原因进入审计输出，支持后续真实资料 R1 验收。

## v0.2.3 Relation Evidence / Impact Recovery — 2026-08-14 to 2026-08-17

- `relation_evidence_links` 成为 Relation-specific Evidence 基础，一条 Relation 可累积多个 supports / contradicts Claims。
- 保留 legacy `node_relations.evidence_claim_id` 并做兼容迁移 / backfill。
- `part_of` 可无 Evidence；其他 current Relation 必须有 active supporting Evidence。
- contradicts Evidence 只记录冲突，不自动 retire Relation。
- Relation seed 仅允许 `part_of`，不能绕过 Evidence gate。
- New Node acceptance 不会把 `related_node_ids` 自动 formalize 为 `related_to`。
- Impact Recovery 增加 deterministic quality gates、stale / retry 恢复与审计，冻结 Propagation 规则保持不变。

## 0.2.2.1 — 2026-08-14

- 强化程序化 `evidence_scope`、Actual / Guidance 原子拆分、公司主体 attribution mapping 与 Current View 确定性排序。
- 单一公司 Evidence 不得外推为行业 / 产品整体结论；Initial Current View 继续执行 Target-Node-centric 与 Evidence Scope Constraint。
- Product Applications 与 type-specific Evidence 校验增强。
- 清理重复查询与无效残留，不改变冻结业务规则或 v0.1.1 稳定性状态机。

## 0.2.2 — 2026-08-14

- Initial Current View 允许单一 Source，同时执行 Evidence Scope Constraint；Proposal 记录 Source 数量、底层独立 Source 数量、Source Rank 与 primary/secondary 分布。
- Current View 程序校验强制保留 company guidance、expert judgment、broker forecast、market rumor 的实际 attribution 主体及 Claim ID。
- 单一公司 Evidence 不得直接外推行业/产品整体结论；one-line、core logic、investment implication、risks 与 watch items 必须保持 Target-Node-centric。
- `key_facts` 仅接受事实、数据和明确公司指引；Product Current View 支持 applications、demand drivers、supply capacity、pricing、major suppliers、product evolution 六类 type-specific Evidence。
- Product type-specific 支持字符串或带 Claim ID / attribution 的结构化审计项。
- 使用同一份昀冢科技 MLCC Standard 样本在全新 workspace 完成真实 DeepSeek Initial Proposal 回归；IMA 继续关闭，冻结业务规则与稳定性状态机未变。

## 0.2.1 — 2026-08-14

- Candidate Node 增加独立研究价值门槛；Event 必须是有明确时间的离散事件，Theme 必须具有长期且跨 Source/Node 的价值。
- Existing Node Match 必须提供可定位 Evidence；父级/祖先 Node 改由已确认的 `part_of` 关系推导。
- Claim 增加 `attributed_to`，公司级经营信息必须在 statement 中显式写出公司主体。
- Evidence 校验统一为 Unicode NFKC、Markdown 转义还原和空白标准化后的精确子串匹配，并保留标准化审计信息。
- Candidate Node Proposal 对当前 Source 的全部 validated Claims 进行二次相关性回填，接受后关联完整 Claim 集并触发 Initial Current View Impact Review。
- 未启用 IMA，未扩展 OCR/PDF、Gap/RQ 生命周期或修改稳定性状态机与冻结规则。

## 0.2.0 — 2026-08-14

- 增加初始 Relation Seed 与 `pro-a relations seed <csv_path>`，支持名称/别名解析、事务回滚和重复导入幂等。
- Standard/Deep Analyzer 对冻结 Node Type、Claim nature/status/novelty、Change Level、Node 引用和 confidence 实施程序校验。
- Evidence excerpt 无法在解析文本定位时，Claim 自动降为 `needs_review` 且正式 confidence 归零，保留模型原始 confidence 供审计。
- Ingestion Receipt 扩展为 Source、Nodes、Claims、历史比对、Impact Review、Proposal、Gap/RQ 的完整审计摘要。
- 增加只读诊断命令 `pro-a source show <source_id>`。
- LLM 校验失败保留原始 Source、Source ID、失败 processing job 和失败 receipt。
- 未启用真实 IMA，不修改冻结业务规则。

## 0.1.1 — 2026-08-13

- Current View Proposal 原子接受、stale 检查与重复接受幂等。
- Current View 增加确定性的日期和 revision sequence 排序。
- Impact Review 按 Batch、Node、目标 Current View 版本持久化并支持 retry。
- Material / Thesis Evidence Sufficiency 增加程序化门槛。
- Archive Source 可复用原 Source 升级为 Standard / Deep 分析。
- 解析失败保留 Inbox 请求；入库存在失败项时 CLI 返回非零退出码。
- Schema 从 0.1 自动迁移至 0.1.1。

## 0.1.0 — 2026-08-13

- 初始原型。
- Source / Claim / Node / Current View 四对象模型。
- Archive / Standard / Deep Inbox。
- 日期型 Current View 版本。
- Node 与 Current View Proposal 审批。
- Knowledge Gap / Research Question 数据结构。
- 上下级优先、关联节点后续的 Impact Propagation 骨架。
- IMA 文件上传 Adapter。
- SQLite schema 与 Windows CLI。
