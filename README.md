# pro_a v0.3.0 — Phase 3 Source Expansion

`pro_a` 是面向长期投研的本地 Canonical Knowledge Engine。SQLite / `<production-db>` 仍是唯一 canonical knowledge Source of Truth；Phase 2 在其上增加确定性、只读的知识探索入口，不替换 Phase 1 的知识生产与人工治理流程。

## 当前状态

**Phase 1 complete and frozen; Phase 1.1 complete; Phase 2 complete; Phase 3A complete; Phase 3B complete; Phase 3C complete; Phase 3D complete; Phase 3E.1 complete.** Phase 3E.1 已将 clean-PDF extraction、Evidence/table/semantic admission、Claim/Node review 与 non-executable promotion preview 串成单一可恢复命令。正常运行停在 `HUMAN_REVIEW_REQUIRED`；Production authorization/apply 仍保持独立且未授权。

Phase 1 已完成并冻结，Phase 1.1 已完成。以下为 Phase 1 frozen baseline（不是当前 Production 状态）：

- AI Hardware expanded Node universe：complete；
- functional Relation requalification：complete；
- functional Relation import count：0；
- Production：293 Nodes / 737 Aliases / 181 Node Relations；
- current `part_of`：174；
- Phase 1 exact Production byte identity：保存在本地受控 evidence 中。

正式 closure 见：

- [`docs/PHASE1_FREEZE.md`](docs/PHASE1_FREEZE.md)
- [`docs/PHASE1_1A_NODE_UNIVERSE_CLOSURE.md`](docs/PHASE1_1A_NODE_UNIVERSE_CLOSURE.md)
- [`docs/PHASE1_1B_FUNCTIONAL_RELATION_CLOSURE.md`](docs/PHASE1_1B_FUNCTIONAL_RELATION_CLOSURE.md)
- [`docs/PHASE3C_CORRECTNESS_CLOSURE.md`](docs/PHASE3C_CORRECTNESS_CLOSURE.md)
- [`docs/PHASE3D_PRODUCTION_PATH_PROMOTION.md`](docs/PHASE3D_PRODUCTION_PATH_PROMOTION.md)
- [`docs/PHASE3E_OPERATIONAL_INGESTION.md`](docs/PHASE3E_OPERATIONAL_INGESTION.md)

当前 Production baseline 为 schema `0.2.1`：302 Nodes、745 aliases、181 Node Relations、3 Sources、116 Claims、19 Claim–Node links、3 Source–Node links、2 个 official Current Views。Phase 2 的 deterministic read surfaces 与 Phase 3 的 controlled Source expansion 路径均保留原边界。

Phase 2 — **Knowledge Exploration & Interaction Layer** 已收口：Search、Browse、Trace、Research 与 Human Current View maintenance workflow 均 complete。原目标顺序为：

```text
Search
→ Browse
→ Trace
→ Research
→ Ask
```

`Ask` 保留但延后，`DEFER_ASK_UNTIL_CORPUS_EXPANSION = true`。当前 Production corpus 很小，需先扩充 Source 覆盖，才能有意义地检验 retrieval / answer quality；这不是取消 Ask。

## Phase 3A — Multi-format Source Ingestion Operational Acceptance

复用已有 TXT / MD / Markdown / CSV、PDF（pypdf）、DOCX、XLSX / XLSM、PPTX parsers。`parse_source(path)` 仍返回 `(text, source_type)`；新 diagnostics API 记录格式、parser、定位方案、文本/空白/错误单元及提取字符数。standard/deep 对空提取返回 `PARSE_TEXT_EMPTY`，在 LLM 与 Inbox 消费之前失败；部分 PDF 页失败但仍有文本时继续分析并给出告警。archive 仍不要求解析。

主 Source 分块优先保持 page / paragraph / table-row / sheet-row / slide 边界，超长单元遵守原字符上限拆分。Evidence locator 复用既有 normalized exact canonicalization，确定性标记 resolved / ambiguous / unresolved，写入 `structured_json.validation.source_locator`；不覆盖 `evidence_pointer`。解析诊断合并到 `sources.metadata_json`，与 analysis quality / Source references 共存。

Explorer Source Detail 增加 **Source Format / Parse Quality**，Claim Evidence 显示页/段落/表格行/工作表行/幻灯片定位。只读 API 使用字段白名单，不暴露归档路径或任意 metadata。没有文件下载、PDF viewer、OCR 或 schema migration。

四种 PDF/Office 格式均完成真实 `process_file` 的隔离 standard/deep 验收，模型使用 deterministic stub；Production 与 IMA 均未改变。完整合同、限制和验收证据见 [`docs/PHASE3A_MULTIFORMAT_INGESTION_ACCEPTANCE.md`](docs/PHASE3A_MULTIFORMAT_INGESTION_ACCEPTANCE.md)。

## Phase 3C — Controlled Live Corpus Expansion Correctness Closure

Phase 3C 建立并验证了 clean-source corpus expansion 的 non-canonical correctness path。关键冻结行为包括：

- Evidence v2 与 deterministic Source binding；
- bounded local-subspan repair，保持原 Evidence / Claim 不变；
- canonical PDF Source truth 继续使用 `pypdf`；
- PyMuPDF 仅作为 PDF structure/layout sidecar；
- `NARRATIVE_FIRST_TABLE_SUPPRESSION`：authoritative table span 在 semantic chunk/prompt 前排除；
- `table / narrative / unknown` precision-first、fail-open eligibility；
- `TABLE_DERIVED_CLAIM_SAFETY_BOUNDARY_V1`：post-binding 只依据 authoritative Evidence + native table geometry 判定 origin eligibility；
- raw table-derived Claims / Evidence 继续保留供审计，不作为 semantic failure 删除。

Independent Pilot #6：107 raw Claims → 3 `TABLE_DERIVED_CLAIM_INELIGIBLE` → 104 review-eligible Claims；Source independence、table suppression、table-claim safety、Evidence artifact、mechanical gate 全部 PASS；delegated semantic review 为 104 KEEP / 0 DROP、true semantic failure 0.00%、`ATTRIBUTION_ERROR = 0`。Production SQLite 全程 byte-identical，integrity `ok`，FK violations `0`；精确 byte identity 保存在本地 evidence 中。

Phase 3C correctness/generalization 因此关闭；其 artifacts 与 review decisions 随后由 Phase 3D promotion contract 绑定，而非直接获得 Production write authority：

```text
PHASE3C_COMPLETE = true
PHASE3C_HANDOFF_TO_PHASE3D = complete
```

详见 [`docs/PHASE3C_CORRECTNESS_CLOSURE.md`](docs/PHASE3C_CORRECTNESS_CLOSURE.md)。

## Phase 3D — Production Path Promotion Closure

Phase 3D 建立并验证了 deterministic promotion payload、exact multi-artifact admission convergence、Source provenance/materialization contract、`CREATE` / `REUSE` / `DEFER` / `REJECT` operation layer、human Node authorization、Phase 1-style collision/baseline validation、shadow qualification、rollback/restore qualification、dedicated one-time executor、immutable authorization artifact 与 durable journal/receipt consumption state。已授权的 frozen payload 对 exact baseline 成功执行一次；授权随后终止，不能重用于其他 payload、baseline、Source 或后续 ingest。

公开文档仅冻结 schema、计数、操作边界和结论。精确 Production byte identity、Source 原件、authorization、journal、receipt、backup 及运行时路径继续保存在本地受控证据中。7 个 Node DEFER 与 10 个 Relation REJECT 均未执行；schema `0.2.2` / `relation_evidence_links`、noisy Source / audio / ASR、local-model preprocessing、IMA live integration 和更高层 review UI 都是独立 backlog。

Phase 3E.1 Operational New-Source Ingestion 已提供 `python scripts/phase3e_ingest.py <pdf>`：冻结 exact Source 后复用 Phase 3C/3D correctness 与 review primitives，生成 Claim/Node review package 及 non-executable promotion preview，并停止等待 human review。Fresh clean-source pilot 属于 Phase 3E.2，不在本阶段自动执行。详见 [`docs/PHASE3E_OPERATIONAL_INGESTION.md`](docs/PHASE3E_OPERATIONAL_INGESTION.md) 与 [`docs/ROADMAP.md`](docs/ROADMAP.md)。

## Phase 2.1A read-only architecture

```text
Browser / Explorer UI
        ↓
Read-only HTTP API
        ↓
Query / Read Model
        ↓
<production-db>
```

Phase 1 知识生产路径保持不变：

```text
Source
→ Claim
→ Node / Relation Candidate
→ Proposal / Review
→ controlled Production maintenance
```

新的 query layer 使用 SQLite URI `mode=ro` 并启用 `query_only`，不复用会 commit 的 `Database.connect()`，也不调用 ingestion、proposal acceptance 或 Production mutation workflow。

## Read API

已提供：

```text
GET /api/health
GET /api/stats
GET /api/nodes
GET /api/nodes/search?q=
GET /api/nodes/{node_id}
GET /api/nodes/{node_id}/neighbors
GET /api/nodes/{node_id}/claims
GET /api/nodes/{node_id}/sources
GET /api/nodes/{node_id}/current-view
GET /api/nodes/{node_id}/current-view-history
GET /api/nodes/{node_id}/current-view-compare?base_view_id=&target_view_id=
GET /api/nodes/{node_id}/research-question
GET /api/nodes/{node_id}/knowledge-gaps
GET /api/sources/{source_id}
GET /api/sources/{source_id}/impact-candidates
GET /api/claims/{claim_id}/impact-candidates
```

Node search 只做 canonical name / alias 的确定性子串匹配；alias 命中仍返回 canonical Node。Node list 和 search 的单次请求上限均为 100。Neighborhood 固定为 current Relations、1 hop。Claim response 直接附 Source metadata；Node Sources 同时覆盖 direct link 与 Claim link，并按 Source 去重保留 provenance。Current View latest 与 history 均只读取 official Views 并复用同一正式 revision ordering；compare 仅允许同 Node 的 official BASE → TARGET，并对 structured content、Evidence references 与 Trigger Source 做 exact deterministic diff。Impact discovery 只沿 Source/Claim 的 canonical `claim_node_links` 找到 active Node 的 latest official View，按 Node 去重、保留 roles/Claims，并单列无 View 的 linked Nodes。Human Impact Review 复用 existing Current View presentation，只在浏览器保存 non-canonical draft，并在 target View / candidate Claim-role snapshot stale 时阻止 JSON export；不增加 write API。Research Question 解析 supporting/opposing Claims；Knowledge Gaps 保留全部真实状态；Source Detail 只返回 metadata 与 structured knowledge links，不暴露本地归档路径。

## Knowledge Explorer MVP

`frontend/` 提供独立 React + TypeScript + Vite 浏览器应用，所有知识数据只通过上述 read API 获取。桌面界面固定为三栏：

```text
Search results | current 1-hop graph | Overview / View / Research / Claims / Sources
```

Search 支持 canonical name 与 alias、250 ms debounce 和 stale-request abort；Cytoscape 图保留 Relation 方向并支持点击邻居继续聚焦。View 使用 `content_json` 的共享 Company/Product structured presentation，并保留 `content_md` fallback、版本导航与 compact governance/evidence metadata；单版本明确标识 initial/no previous revision，多版本默认 latest 并可选择历史 official View 或进入 BASE → TARGET Compare mode，查看 exact added/removed/changed 内容与 Evidence delta。Research 展示 Research Question、Current Answer、key variables、supporting/opposing Claims、falsifier 与 Knowledge Gaps。Sources 可进入右栏 Source Detail，查看 metadata、linked Nodes 和 Source Claims；Potential Current View Impact 仅显示直接 Claim attribution candidates、聚合 Claim count/roles 与 Open View，不做影响判断。每个有 official View 的 candidate 可进入 Human Impact Review，按冻结 role boundary 展示 Source、Existing View、New Evidence、Decision、Reason，并 local save/export non-canonical JSON。Core 与 knowledge modules 独立失败，单个 Research 或 impact endpoint 错误不会清空正常 Source/Node 内容；选择状态写入 `?node=`，API 不可用时显示可重试状态。

## Windows 快速开始

推荐 Python 3.10+：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\bootstrap.ps1
Copy-Item .\config.example.toml .\config.toml
.\.venv\Scripts\pro-a.exe init
```

启动只读 API：

```powershell
.\.venv\Scripts\python.exe -m pro_a.api --config .\config.toml
```

默认只监听 `127.0.0.1:8000`。该启动路径只读取已存在的数据库，不创建 schema 或 workspace。保持该终端运行，再开一个终端启动 UI：

```powershell
Set-Location .\frontend
npm install
npm run dev
```

打开 `http://127.0.0.1:5173`。开发服务器将 `/api` 代理到 `http://127.0.0.1:8000`；如需覆盖 API 地址，可设置 `VITE_API_BASE_URL`。

Standard / Deep legacy ingestion 仍使用既有 CLI 和 frozen contracts。Phase 3D 的成功 apply 仅证明一个 exact、一次性 promotion；任何新 Production mutation 仍要求独立的明确目标、baseline precondition、backup、single transaction、receipt、post-write QA 与显式用户授权。

## 当前边界

当前 Explorer 是 desktop-first、本地只读的投研知识终端，没有 write API、auth、recursive graph traversal、FTS/vector search、embedding、RAG、chatbot、raw file serving 或 schema migration。Current View Compare 只做 exact structured diff；impact discovery 只发现 direct candidates；Human Impact Review 只保存 browser-local non-canonical draft 并导出 handoff JSON。三者均不包含 semantic/fuzzy/LLM interpretation、自动影响方向或 change-level 判断、Proposal、Current View mutation 或 propagation。图固定为所选 Node 的 current 1-hop；Production 若没有 Current View、Research Question、Knowledge Gap 或 Node-linked Claim，界面会如实显示空态。Relation generation backlog 保持原状；不得通过放宽 Evidence、direction、identity、collision 或 Node Type 规则修复。

Phase 3D closure 不把 Explorer、legacy ingestion、IMA 或未来 Source 变为 Production write-enabled。PyMuPDF licensing/deployment、可重复 operational ingestion、schema migration 与各 backlog 均须作为独立阶段重新验证和授权。

后续里程碑和冻结规则分别见 [`docs/ROADMAP.md`](docs/ROADMAP.md) 与 [`docs/REQUIREMENTS_FROZEN.md`](docs/REQUIREMENTS_FROZEN.md)。
