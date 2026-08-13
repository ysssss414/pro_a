# Changelog

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
