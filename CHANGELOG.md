# Changelog

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
