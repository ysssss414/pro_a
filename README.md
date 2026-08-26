# pro_a v0.3.0 — Phase 2 Knowledge Explorer

`pro_a` 是面向长期投研的本地 Canonical Knowledge Engine。SQLite / `workspace/pro_a.db` 仍是唯一 canonical knowledge Source of Truth；Phase 2 在其上增加确定性、只读的知识探索入口，不替换 Phase 1 的知识生产与人工治理流程。

## 当前状态

Phase 1 已完成并冻结，Phase 1.1 已完成：

- AI Hardware expanded Node universe：complete；
- functional Relation requalification：complete；
- functional Relation import count：0；
- Production：293 Nodes / 737 Aliases / 181 Node Relations；
- current `part_of`：174；
- Production SHA-256：`8a4247b9da2c3d6f288f8a8af8519f33673bc45b5a4327a57c50436d39dd50b4`。

正式 closure 见：

- [`docs/PHASE1_FREEZE.md`](docs/PHASE1_FREEZE.md)
- [`docs/PHASE1_1A_NODE_UNIVERSE_CLOSURE.md`](docs/PHASE1_1A_NODE_UNIVERSE_CLOSURE.md)
- [`docs/PHASE1_1B_FUNCTIONAL_RELATION_CLOSURE.md`](docs/PHASE1_1B_FUNCTIONAL_RELATION_CLOSURE.md)

Phase 2 — **Knowledge Exploration & Interaction Layer** 已启动；Phase 2.2 Knowledge Explorer MVP 已完成。目标顺序为：

```text
Search
→ Browse
→ Trace
→ Research
→ Ask
```

当前优先建立 deterministic knowledge interaction，不先做 chatbot、RAG 或自然语言查询。

## Phase 2.1A read-only architecture

```text
Browser / future UI
        ↓
Read-only HTTP API
        ↓
Query / Read Model
        ↓
workspace/pro_a.db
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
```

Node search 只做 canonical name / alias 的确定性子串匹配；alias 命中仍返回 canonical Node。Node list 和 search 的单次请求上限均为 100。Neighborhood 固定为 current Relations、1 hop。Claim response 直接附 Source metadata；Node Sources 同时覆盖 direct link 与 Claim link，并按 Source 去重保留 provenance。

## Knowledge Explorer MVP

`frontend/` 提供独立 React + TypeScript + Vite 浏览器应用，所有知识数据只通过上述 read API 获取。桌面界面固定为三栏：

```text
Search results | current 1-hop graph | Overview / Claims / Sources
```

Search 支持 canonical name 与 alias、250 ms debounce 和 stale-request abort；Cytoscape 图保留 Relation 方向并支持点击邻居继续聚焦。Node 详情展示 aliases、parents / children、incoming / outgoing Relations；Claims 展示 Evidence 与 Source metadata；Sources 按 Source 去重并展示 direct / claim provenance。选择状态写入 `?node=`，可直接恢复；API 不可用时显示可重试状态，不进入白屏。

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

Standard / Deep ingestion 仍使用现有 CLI 和冻结契约。任何 Production mutation 继续要求明确目标、precondition SHA、独立 backup、单 transaction、receipt、post-write QA 与人工授权。

## 当前边界

当前 Explorer 是 desktop-first 的本地 MVP，没有 write API、auth、recursive graph traversal、FTS/vector search、embedding、RAG、chatbot 或 schema migration。图固定为所选 Node 的 current 1-hop，生产数据若没有 Node-linked Claim，Claims 页会如实为空。Relation generation backlog 保持原状；不得通过放宽 Evidence、direction、identity、collision 或 Node Type 规则修复。

后续里程碑和冻结规则分别见 [`docs/ROADMAP.md`](docs/ROADMAP.md) 与 [`docs/REQUIREMENTS_FROZEN.md`](docs/REQUIREMENTS_FROZEN.md)。
