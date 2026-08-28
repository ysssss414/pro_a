# pro_a Roadmap — Source Expansion & External Knowledge Integration

Status: **Phase 1 complete and frozen; Phase 1.1 complete; Phase 2 complete; Phase 3A complete; Phase 3B complete**

Next: **Phase 3C — Controlled Live Corpus Expansion Pilot: ready for planning; not authorized.**

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

## Completed — Phase 2 Knowledge Exploration & Interaction Layer

Phase 2 在 canonical SQLite knowledge state 上建立本地交互层，顺序为：

```text
Search
→ Browse
→ Trace
→ Research
→ Ask
```

收口依据：Search = complete；Browse = complete；Trace = complete；Research = complete；Human Current View maintenance workflow = complete（含 2.7A–2.7C 的人工 review → Proposal → resolution / direct official View activation）。

**Ask = deferred，不是取消。**

Ask is intentionally deferred until corpus breadth and Source coverage improve.
Building an answer layer over the current very small Production corpus would not
provide meaningful retrieval/answer quality validation.

`DEFER_ASK_UNTIL_CORPUS_EXPANSION = true`。以下保留 Phase 2 各子阶段的历史验收记录；其历史 handoff 不构成新的阶段授权。

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

### Phase 2.3F — Claim Attribution Semantics & Company Entity Activation

状态：**complete**。冻结 `subject / context / related` 最小 Claim → Node role 合同；原子创建 `昀冢科技` Company Node（0 aliases），新增 8 条 Company subject links，并将 MLCC 的 3 条 primary Claims 标为 subject、8 条 Company-primary Claims 标为 context。Node Claims API 与 Explorer Claims tab 已显示数据库 role。Production 为 294 Nodes、737 Aliases、19 Claim links；MLCC 为 3 subject + 8 context，昀冢科技为 8 subject；没有创建 Current View、Relation、RQ、Gap 或 Source link。

### Phase 2.4A — Subject-Aware Current View Pilot

状态：**complete (artifact-only pilot)**。仅对 MLCC 与昀冢科技生成两个与正式 `current_view_change` payload 兼容的离线 Proposal。所有 direct factual support 必须来自目标 Node 的 `role=subject` Claim；MLCC 的 8 条 Company Claims 只作为 `CONTEXT_ONLY`，`related` 不得作为直接证据。MLCC 使用 3 条 primary Claims；昀冢科技的 8 条 subject Claims 中 6 条进入 primary Evidence，2 条 `needs_review` 只保留为 unresolved。两个 proposal 均通过 frozen Current View 内容校验、traceability 与 scope-overreach gate，但因证据均来自单一 B-rank secondary Source 且尚未人审，两个 Node 和模型 verdict 均为 `PARTIAL`。Production byte-identical，Current Views 与 Current View Proposals 均保持 0。

### Phase 2.4B — Human-Approved Current View Activation

状态：**complete**。基于显式人工批准，原子激活 MLCC 与昀冢科技两个 official Current Views；Production 共有 2 个 official Views，SQLite 继续是唯一 canonical Source of Truth。激活有 precondition SHA、backup、transaction、receipt 和 post-write QA，未自动扩展到其他 Node。

### Phase 2.4C — Current View IA Refinement

状态：**complete**；`GENERALIZATION_READY = YES`。Explorer 以共享的 Company/Product presentation helper 渲染 structured `content_json`，提供 evidence boundary、Evidence Claim count、Source action 与治理 metadata，默认不暴露 raw Claim IDs。Product dimension keys 使用人类可读标签；MLCC canonical 重复价格事实仅通过窄且确定性的 presentation rule 避免重复，canonical 内容未改。`DEFER_CANONICAL_CONTENT_DEDUP = true`、`DEFER_EVIDENCE_BOUNDARY_CONTENT_QUALITY = true`、`DEFER_EVIDENCE_QUALITY_METADATA = true` 保持不变。

### Phase 2.5A — Current View History & Version Navigation

状态：**complete**。新增 official-only、Node-scoped、read-only Current View history query/API，严格复用 `CURRENT_VIEW_ORDER`，并复用现有 serializer 对 malformed `content_json` 和 Claim ID JSON 安全 fallback。Explorer 默认显示 latest official View；单版本显示 `Initial View / No previous revision`，多版本可选择任意历史版本并继续复用相同 Company/Product presentation、governance metadata、Evidence count 和 Source action。隔离 SQLite fixture 覆盖 0/1/3 official revisions、previous chain、same-day revision sequence、draft exclusion、malformed JSON、404 与 empty history；没有 schema、write API 或 Production 数据变化。

### Phase 2.5B — Deterministic Historical Compare

状态：**complete**。新增独立 pure comparator 与 official-only、same-Node、read-only BASE → TARGET compare API；scalar 仅 trim 后 exact before/after，list 使用 exact item added/removed/unchanged 并保持来源顺序，`type_specific` 按 canonical key 做 list/scalar/JSON structural diff。Evidence 使用 record `trigger_claim_ids`，可解析 Claim/Source metadata，missing ref 保留 unresolved；Trigger Source 仅报告状态。Explorer 在既有版本导航内提供 Compare mode、Product 中文维度标签、Evidence delta 与治理 metadata；单个 initial View 明确显示 `No previous revision to compare`。不包含 LLM、semantic/fuzzy matching、投资方向解释、Current View mutation、schema 或 Production 数据变化。

### Phase 2.6A — Direct Impact Candidate Discovery

状态：**complete**。新增 Source/Claim 级 deterministic、read-only discovery，仅沿 `Source → Claim → claim_node_links → active Node → latest official Current View` 发现人工 review candidates。候选按 Node 去重并保留全部 Claims 与 `subject/context/related` roles；无 official View 的 active linked Nodes 单列，inactive Node 与 draft View 不进入候选。Source Detail 增加克制的 Potential Current View Impact panel 与 Open View 导航；不判断 change need、level、方向或强弱，不生成 Proposal，不做 Relation/parent/child propagation。Production browser smoke 基于真实 2 Sources / 12 Claims / 2 Views 通过。

### Phase 2.6B — Human Impact Review Surface

状态：**complete**。在 2.6A deterministic candidates 上增加右栏 Human Impact Review。用户可对 Source → Candidate Node → latest official Current View 形成 `NO_CHANGE`、`MINOR`、`MATERIAL` 或 `THESIS` 判断；Subject / Context / Related attribution boundary 与 Primary Evidence eligibility 保持冻结，Reason 和 Thesis structured reason 做最小确定性校验。Draft 只写浏览器 localStorage，并可导出 `NON-CANONICAL HANDOFF ARTIFACT` JSON；target View 与 candidate Claim-role snapshot 发生变化时阻止 READY export。该阶段不写 `impact_reviews`、Proposal、Current View 或 Production DB，不调用 propagation / recovery / LLM。真实 FastAPI + frontend Production smoke、384 项 pytest、前端 9 文件 / 37 测试、build 和 compileall 均通过，Production 前后 SHA 完全一致；分支已推送并创建 Draft PR #34。详见 `docs/PHASE2_6B_HUMAN_IMPACT_REVIEW.md`。

### Phase 2.7A — Controlled Human Review Intake / View Proposal

状态：**complete**。新增独立文件 intake：严格验证 Phase 2.6B READY v1 export，PREPARE 只读重验 Source / active Node / latest official View / exact Claim-role snapshot；NO_CHANGE 生成无写入 receipt，其余 decision 原样复制目标 View 为 non-canonical draft。SUBMIT 要求人工实际内容修改，通过现有 deterministic compare helpers 与 frozen Current View validator，并在同一事务内重复 stale/eligibility gates、执行 exact idempotency/conflict 检查，仅在显式 isolated DB 中创建 pending `current_view_change` Proposal。Human provenance 保存在 `payload_json.human_review_handoff`，legacy identifiers 保持空。109 项隔离测试、493 项完整 pytest、前端 9 文件 / 37 测试、build、compileall 与 15 项真实 Production 只读 smoke 均通过；Production 前后 SHA 和全部表计数不变。详见 `docs/PHASE2_7A_HUMAN_REVIEW_INTAKE.md`。

本阶段严格止于 pending Proposal；Production Proposal write 未授权。没有 acceptance UI、official View creation、propagation/recovery、impact queue write、IMA/LLM、Gap/RQ、自动改写或评分。三个既有 content/evidence defer 保持不变；后续行为须另行明确授权。

### Phase 2.7B — Controlled Production Proposal Gateway & Read-Only Review

状态：**complete**。复用 2.7A transaction-safe validation/idempotency helpers，新增显式 configured Production `preview` / `apply-production` CLI；单一事务内重验 canonical/stale/Evidence/actual-change/frozen-content gates，通过窄 SQLite authorizer 仅允许 pending `current_view_change` INSERT。保留 2.7A isolated boundary，写前 SQLite backup、写后 receipt 和 pending conflict protection；无 schema 或 validator 变化。

新增仅 GET 的 Human View Proposal queue/detail、原目标 official View → proposed content 确定性 diff 与 computed canonical alignment，Explorer 提供明确 nonofficial/pending、无 acceptance action 的只读 review surface，历史 legacy Proposals 不进入队列。89 项 2.7B、109 项 2.7A、582 项完整 pytest、前端 10 文件 / 49 测试、build、compileall、Production-copy 写入与真实 Production 只读浏览器验收均通过。

**Production write path implemented and isolated-copy validated. No live Production Proposal was created during Phase 2.7B acceptance.** `LIVE_PRODUCTION_PROPOSAL_APPLY_AUTHORIZED = false`；Production 前后 SHA 和全部表计数不变。Proposal modify/revision/reject/accept、official View activation、propagation/recovery、browser write API 与三个既有 content/evidence defer 继续保留；Phase 2.7C 未开展。详见 `docs/PHASE2_7B_PRODUCTION_PROPOSAL_GATEWAY.md`。

### Phase 2.7C — Human Proposal Resolution & Direct Current View Activation

状态：**complete**。新增独立 `human_proposal_resolution` resolver 与严格 v1 `ACCEPT`/`REJECT` resolution artifact。Resolver 在单一事务内重复 2.7A/2.7B canonical、stale、candidate-role、Subject Evidence、actual-change 与 frozen-content gates；ACCEPT 只直接插入一个 official `current_views` row 并更新 Proposal，REJECT 只更新 Proposal。`result_json.human_resolution` 保留完整 artifact、reason 与 terminal metadata；exact replay 幂等，冲突终态阻断。未调用 Proposal/Propagation/Recovery/IMA/LLM manager，不写 side-effect、Impact、Gap、RQ、Markdown 或 schema。

Read-only API 现在按 `pending/accepted/rejected` 暴露 Proposal history 与可验证的 resolution metadata；Explorer 仅允许本地草拟/导出 resolution JSON，ACCEPT stale 时阻断，REJECT 仍可导出；没有浏览器写 API。两个 fresh Production copies 已用真实 2.7B gateway → 2.7C CLI 验证 ACCEPT（Proposals 11→12→12，Views 2→3）与 REJECT（11→12→12，Views 2→2）；ACCEPT 除 proposals/current_views 外全部行不变，REJECT 除 proposals 外全部行不变。完整 pytest 657、2.7C 联合后端 273、前端 11 文件 / 56 测试、build、compileall 和 live Production read-only pre/post audit 通过；live Production SHA/全部表计数不变。Playwright Edge 验证真实空队列、隔离副本本地 artifact 导出、ACCEPT 历史及准确 official View 导航、REJECT 历史，只有 GET 请求，控制台零错误。`LIVE_PRODUCTION_RESOLUTION_APPLY_AUTHORIZED = false`；Phase 2.7D 未开展。详见 `docs/PHASE2_7C_HUMAN_PROPOSAL_RESOLUTION.md`。

`LIVE_PRODUCTION_RESOLUTION_APPLY_AUTHORIZED = false`。历史 Phase 2.7D 技术 handoff 未开始、未授权；Phase 2 已总体收口，当前路线转入 Source 扩张。

## Phase 3 — Source Expansion & External Knowledge Integration

### Phase 3A — Multi-format Source Ingestion Operational Acceptance (PDF-first)

状态：**complete**。复用所有既有 parser，新增 backward-compatible diagnostics API，明确 standard/deep parse-before-consume 与 empty-extraction fail-closed 合同；PDF 页错误保留稳定标记并允许有有效文本的 partial extraction。archive、SHA duplicate 与 archive → standard → deep 的既有升级语义不变。

新增 locator-aware 主分块和 deterministic normalized-exact Evidence locator；歧义不选择首个命中，已有 pointer 不覆盖。diagnostics 与既有 Source metadata 合并，receipt 和只读 Source Detail 可观察；Explorer 显示格式、解析质量、partial warning 和 Evidence 定位。没有 schema、LLM extraction contract、frozen validator、IMA semantics 或 Production 变化。

验收：265 项联合 targeted、731 项完整 pytest、前端 11 文件 / 66 项测试、build、compileall 通过；四种 PDF/Office 格式完成隔离 standard/deep 真实 pipeline smoke。Edge 只读浏览器验收和六张截图检查通过；Production 实际 pre/post SHA、全部表计数相同，integrity `ok`，FK 违规 0。详见 `docs/PHASE3A_MULTIFORMAT_INGESTION_ACCEPTANCE.md`。

### Phase 3B — IMA Integration Operational Acceptance

状态：**complete**。IMA Source sync path implemented and simulator-validated. No live IMA mutation was performed during Phase 3B acceptance.

复用现有 IMA client、media type/size preflight、COS SDK 和 `ima_objects` mapping；新增 Source 原件专用 deterministic preflight、stable identity、local idempotency、column-level mapping write guard、阶段诊断、same-name unresolved protection 和 remote/local uncertainty reservation。IMA 失败不影响 canonical Source ingestion；Source Detail / Explorer 只读显示 Synced / Not synced / Needs reconciliation，Mutation 仅保留给显式 `sync-production-source` CLI。

隔离测试覆盖 HTTP/COS simulator、PDF 与 Office full sync、全部 Phase 3A 文件格式 preflight、safe retry 与 uncertain retry blocking、mapping ID 稳定性、pipeline outage/same-name continuation、API/Explorer GET-only observability。没有 schema、Claim/Node/Relation/Current View/Proposal/Propagation 变化。

`LIVE_IMA_WRITE_AUTHORIZED = false`；`LIVE_IMA_READONLY_PROBE_AUTHORIZED = false`。Phase 3C Controlled Live Corpus Expansion Pilot 仅 ready for planning，不授权执行。

### Later — not started

Scanned PDF / image / multimodal、source-version handling、table/chart extraction quality 留待后续。Phase 3A 不授权 OCR、vision model、RAG、Ask/chatbot、embedding/vector DB、PDF viewer 或 schema migration。

```text
DEFER_ASK_UNTIL_CORPUS_EXPANSION = true
DEFER_SCANNED_PDF_OCR = true
DEFER_IMAGE_MULTIMODAL = true
DEFER_PDF_TABLE_STRUCTURE_EXTRACTION = true
DEFER_CHART_EXTRACTION = true
DEFER_LIVE_IMA_SYNC = true
DEFER_PROPOSAL_MODIFY = true
DEFER_PROPAGATION = true
DEFER_CURRENT_VIEW_FILE_MATERIALIZATION = true
DEFER_BROWSER_PRODUCTION_WRITE = true
DEFER_CANONICAL_CONTENT_DEDUP = true
DEFER_EVIDENCE_BOUNDARY_CONTENT_QUALITY = true
DEFER_EVIDENCE_QUALITY_METADATA = true
```

## Carried backlog

- Relation Candidate generation 漏召回；
- contract-constrained functional Relation false negatives；
- Claim semantic deduplication / conflict retrieval；
- Proposal “modify then accept”；
- Knowledge Gap 与 ResearchQuestion 完整生命周期；
- 更可靠的表格、图表、多模态与 source-version 处理；
- 正式 IMA integration acceptance 与更高层 review UI。

这些 backlog 不授权修改 Phase 1 frozen contracts，也不属于 Phase 3A 验收范围。

## Decision rule

错误 canonical knowledge 与 unsafe acceptance 的风险优先于 coverage。不得用 fuzzy linking、evidence-free association、Gold-specific hardcode 或 validator weakening 补偿 upstream model loss。SQLite 继续是唯一 Source of Truth，Phase 2 read layer 不获得 Production write authority。
