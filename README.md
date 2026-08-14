# pro_a v0.2.0-real-ingestion

面向长期投研的本地知识处理引擎原型。核心职责是把新资料从本地 Inbox 转换为可追溯的 Source / Claim / Knowledge Node / Current View，并通过 IMA OpenAPI 同步原始资料和正式研究成果。

v0.2.0-real-ingestion 第一阶段不改变冻结业务规则，目标是让第一份真实 Standard 投研资料具备可严格校验、可诊断、可人工验收的端到端闭环。IMA 默认保持关闭。

## 已实现

- 三种入库模式：`archive` / `standard` / `deep`
- 本地 Inbox 扫描与文件稳定检测
- SHA-256 去重、Source ID、不可变本地归档
- PDF / Word / Excel / PPT / Markdown / TXT 解析
- SQLite 状态库
- Knowledge Node、别名、关系、Source、Claim、Current View、Knowledge Gap、Research Question、Proposal、Impact Review 数据表
- 通用 OpenAI-compatible LLM 适配器（默认关闭，可接 DeepSeek 等兼容接口）
- Claim 抽取、Node 匹配/新增 Node Proposal、Evidence Pointer/Excerpt 校验
- Current View 变更分级：Minor / Material / Thesis Change
- 所有 Current View 变更都生成 Proposal，只有用户确认后才形成正式 `v_YYYYMMDD` 版本
- 同日多次正式更新自动生成 `v_YYYYMMDD_01` / `_02`
- 新 Node 必须 Proposal 确认
- Current View 确认后按“上下级 → 关联节点”的规则触发 Impact Review；未产生 View 变化则该路径停止
- Knowledge Gap 自动产生；Research Question 作为 Node Candidate，需要确认
- IMA 原始文件上传：`check_repeated_names → create_media → COS → add_knowledge`
- IMA Current View Markdown 上传
- 人类可读 Ingestion Receipt / Proposal 文件
- 41 个初始 Knowledge Node Seed 与 25 条结构 Relation Seed
- Relation Seed 名称/别名解析、幂等导入和整批错误回滚
- LLM 输出冻结枚举、Node 引用、confidence 与 Evidence excerpt 程序校验
- Receipt / `source show` 展示 Source metadata、Existing Nodes、Node/RQ Candidates、Claims、历史比对、Impact Reviews、Current View Proposals 和 Gaps

## 设计边界

`pro_a` 是逻辑知识层；IMA 是云端文档/RAG/成果承载层。原始 Source 只保存一次，不按 Node 复制。一个 Source 与多个 Node 的关系保存在 SQLite 中。

IMA v0.1 不依赖“新建知识库/新建文件夹”接口。请先在 IMA 手工创建：

1. `00_Research_Sources`：原始资料库
2. `10_Research_Outputs`：Current View / Research Output 等成果库

然后把知识库 ID（可选文件夹 ID）填入 `config.toml`。

## Windows 快速开始

推荐 Python 3.10+。

```powershell
cd pro_a_v0_1
powershell -ExecutionPolicy Bypass -File .\scripts\bootstrap.ps1
.\.venv\Scripts\pro-a.exe init
```

复制配置：

```powershell
Copy-Item .\config.example.toml .\config.toml
```

首次可导入一批已经确认的示例节点：

```powershell
.\.venv\Scripts\pro-a.exe nodes seed .\config\nodes_seed.example.csv
.\.venv\Scripts\pro-a.exe relations seed .\config\relations_seed.example.csv
```

### 配置 LLM

默认 `llm.enabled = false`，此时 Archive 模式可完整运行，Standard/Deep 会保存 Source，但把分析阶段标记为 `needs_llm`。

若使用兼容 OpenAI Chat Completions 的模型：

```powershell
$env:PROA_LLM_API_KEY="你的API Key"
```

编辑 `config.toml`：

```toml
[llm]
enabled = true
base_url = "https://api.deepseek.com"
model = "deepseek-chat"
api_key_env = "PROA_LLM_API_KEY"
```

第一轮真实 Standard 验收保持 IMA 关闭：

```toml
[ima]
enabled = false
```

把资料放入 Standard Inbox 并执行：

```powershell
Copy-Item .\sample.txt .\workspace\inbox\standard\
.\.venv\Scripts\pro-a.exe ingest --once
```

CLI 输出会包含 `source_id`、`job_id`、`receipt_path` 和完整 `audit`。随后可只读查看：

```powershell
.\.venv\Scripts\pro-a.exe source show SRC_xxx
```

Receipt 位于 `workspace/generated/receipts/<JOB_ID>.md`，包含 Source metadata、Existing Nodes、Candidate Node Proposals、Claims 与 Evidence 校验、Historical Compare、Impact Reviews、Current View Proposals、Knowledge Gaps 和 Research Question Candidates。

### 配置 IMA

在 IMA 中生成 OpenAPI Client ID / API Key 后：

```powershell
$env:IMA_OPENAPI_CLIENTID="..."
$env:IMA_OPENAPI_APIKEY="..."
```

编辑：

```toml
[ima]
enabled = true
source_kb_id = "原始资料库ID"
output_kb_id = "研究成果库ID"
```

验证：

```powershell
.\.venv\Scripts\pro-a.exe ima list-kbs
```

## 日常使用

只存档：

```text
workspace/inbox/archive/
```

正常研究材料：

```text
workspace/inbox/standard/
```

高价值、需要更深 Claim / Gap / RQ 处理：

```text
workspace/inbox/deep/
```

单次处理：

```powershell
.\.venv\Scripts\pro-a.exe ingest --once
```

持续监听：

```powershell
.\.venv\Scripts\pro-a.exe watch --interval 5
```

查看待确认项：

```powershell
.\.venv\Scripts\pro-a.exe proposals list
.\.venv\Scripts\pro-a.exe proposals show PROP_xxx
```

确认 / 拒绝：

```powershell
.\.venv\Scripts\pro-a.exe proposals accept PROP_xxx
.\.venv\Scripts\pro-a.exe proposals reject PROP_xxx --reason "证据不足"
```

正式 Current View 会写入：

```text
workspace/generated/current_views/<NODE_ID>/Current_View_v_YYYYMMDD.md
```

同一天第二次更新则是：

```text
Current_View_v_YYYYMMDD_01.md
```

## 目录

```text
workspace/
├─ inbox/
│  ├─ archive/
│  ├─ standard/
│  └─ deep/
├─ archive/                 # 本地不可变 Source 原件
├─ generated/
│  ├─ current_views/
│  └─ receipts/
├─ review/
│  └─ proposals/
├─ logs/
└─ pro_a.db
```

## 当前明确未做（后续阶段）

- GUI
- IMA 内自定义 Skill / MCP 入口
- 自动创建 IMA 知识库或文件夹
- 图片 OCR / 多模态解析
- 复杂 PDF 表格语义重建
- Claim 语义向量去重（v0.1 只有规则 + LLM 比对）
- 外部互联网研究自动回灌
- Materiality 的 Node-specific 数值阈值管理界面

这些不影响 v0.1 验证核心闭环。
