# B-lite 局部 Canonical 准入 P0

开发基线：`93776ffffe7e7c2327a1722c692e9e5df1852172`。本交付仅做工程资格化；真实材料试点、生产迁移和生产 Apply 仍须另行授权。PR 保持 Draft。

## 普通使用入口

1. Source Operations 中，对已结束抽取的 Source Run 选择候选审核入口。服务从已有持久化 Attempt 读取完整 v4 响应，校验 Source、请求、配置、Raw 和 Evidence，批量建立独立 Origin；不重新抽取。
2. 单个对象字段、Evidence ownership 或实体依赖错误使该对象及其真实依赖闭包隔离。标题是否支持具体断言属于后续 Semantic 和双审判断。原 Run 的失败、Accepted Ledger 和 Coverage 保持原值。
3. 新批次进入现有 Semantic 和 Native Review。使用页面导出的完整冻结上下文，分别取得 A、B 两位独立 Reviewer 的实际意见，再分别导入。意见中的 `SUPPORTED` 表示原文支持该来源陈述及其口径，不能解释为现实真实性已被证实。
4. HUMAN_USER 独立保存 Native 决定并 Seal，再保存 Attribution 决定并 Seal。CREATE、REUSE、NO_LINK 继续服从现有实体身份和链接约束。双审意见不能代替 Human 决定。
5. 使用既有 Operational Qualification 和 Operator 的精确授权、执行及回执恢复流程。Web/MCP 没有新增 Apply 能力。相同 Source 精确复用整行，新增 Claim 以受控字段标为 `SOURCE_ASSERTION / UNVERIFIED / CLUE_ONLY`。
6. 在 MCP `get_source`、`get_node_evidence` 和 Explorer 中查询。事实时间、发表时间、接收时间分别保留，并标明展示日期的依据。Canonical 查询采用字段白名单，不导出任意 `structured_json` 或本地文件路径。

单份意见导入格式如下。SHA 与对象清单必须来自导出的冻结上下文；Reviewer 身份必须填写真实使用的人员或模型身份，不能使用示例值充当真实审核记录。

```json
{
  "slot": "A",
  "reviewer_type": "MODEL",
  "reviewer_id": "actual-reviewer-identity",
  "context_sha256": "<exported context SHA-256>",
  "items": [{
    "candidate_id": "<exported candidate ID>",
    "content_sha256": "<exported content SHA-256>",
    "judgment": "SUPPORTED",
    "reason": "<actual evidence and scope assessment>"
  }]
}
```

`reviewer_type` 支持 `MODEL`、`HUMAN_REVIEWER`；判断支持 `SUPPORTED`、`UNSUPPORTED`、`UNCERTAIN`。所有候选都必须有意见；KEEP/CREATE/REUSE 要求两份意见均支持。槽位、身份、上下文或对象版本不一致均禁止 Seal。意见一经登记不能在同一 Packet 上覆盖。

## 修订、去重与失败隔离

- “Correct an Evidence range” 允许 Human 在真实 Evidence 单元中选择精确原文范围并填写理由。浏览器把 UTF-16 选区转换为原文 Unicode codepoint 偏移；服务重新验证 ownership 和原始输入身份。包括 `预\n计` 在内的定位问题只能通过可证明的精确范围修订，原 Raw 不改写，不做模糊补字。
- 修订形成新 Packet。对象版本包含 Evidence、真实依赖版本、原观察身份和修订记录。导入意见可提供 `reuse_from`（之前的 ART handle），并只提交发生变化对象的新意见。服务仅复用同一 Reviewer、同一 Source/Canonical 基线、同一 runtime/处理范围、相同对象内容哈希的已登记意见，记录旧意见血缘。最终 Human 决定、Seal、Attribution 和 Apply 授权一律重新形成。
- 原观察身份保留 Run/Attempt、原始对象字节范围及 Raw 摘要。正式候选键绑定 Source、内容、Evidence、主体、时间和口径，排除 Attempt、输入顺序和 Packet ID。完全相同候选只晋升一次；不使用文本相似度合并。
- 已准入对象跳过；Human DROP 且 A/B 均不支持的相同候选保持关闭。受支持但暂时未准入的对象可进入后续同源批次。全部关闭时返回带理由的 `ZERO_INCREMENT`，不会新建模型调用。
- 新普通 Run 冻结 `independent-candidate-isolation-v1`，局部响应失败后继续既定预算内的无关 Segment。共享身份错误仍阻断。任何 Coverage 缺口最终仍为 FAILED；旧 Run 不自动恢复。候选子批次仍受现有 intake、job 和模型预算约束。

## 契约与迁移

| 范围 | 变化与兼容边界 |
|---|---|
| 候选输入 | `source-candidate-set-v1`；登记与每次正式使用均重新核对实际持久化 Source/Attempt/Raw/Evidence。 |
| Native / Job | 新候选使用 manifest/input schema 2；现有完整成功 v4 仍走原有 schema 1 门禁。 |
| Workbench | 保持 Schema12，复用不可变 artifacts 和既有追加事件，无新增 Workbench migration。修复 Current View / Direct Impact 的 Schema12 白名单。 |
| Canonical | 显式 `0.2.3 → 0.2.4`，新增 `admission_semantics`、`reality_support`、`current_view_use`、`admission_basis_sha256`。旧 Claim 默认 `LEGACY_UNKNOWN`，旧官方 View 原样保留。 |
| Operator | `phase42-operational-v2`；精确差异、一致性、事务、一次性授权和恢复回执沿用原引擎。旧已资格化包不得跨 runtime 自动复用。 |
| MCP | `pro-a-mcp-stage3-v2`，仍为 14 个只读工具；新增可选 B-lite 字段和 Source Claim 分页。 |

Canonical migration 为独立离线动作：

```text
python -m pro_a.admission_schema --database <db> --expected-sha256 <exact-pre-migration-sha> --backup <new-backup>
```

迁移要求原基线完全匹配、独占事务、无 WAL/SHM/journal、独立新备份，并验证 schema、完整性和外键。导入、查询和 `init_schema` 不会自动执行该迁移。此次仅迁移新建的合成数据库，未迁移真实数据库。

Schema0.2.4 的数据库触发器覆盖所有官方 Current View INSERT/UPDATE：Evidence 列表必须非空，全部引用具备受审依据 SHA、允许的支持状态和 `BASIS_ELIGIBLE`。应用侧同时拒绝 CLUE_ONLY/UNKNOWN 作为正式依据和定量 Impact 输入。历史记录默认 UNKNOWN，因此本 P0 不提供它们成为新官方 View 依据的隐式通道。

## 模块与资格化

主要新增模块是 `candidate_origin.py`、`workbench/candidate_inputs.py`、`workbench/advisory_review.py`、`admission_schema.py`。现有 Source Operations、Native 构造/校验、Review、Attribution、Qualification、Operator shadow、MCP/Explorer 和 Current View 门禁作最小接入；前端新增候选意见导入和精确范围选区控件。

G1/G2/G3 合成资格化通过：258 项定向后端测试、51 项前端测试，类型检查和生产构建通过。依赖版本绑定补强后另有 68 项复测通过，不重复计入 258。实际范围、重测原因及门禁证据见 [脱敏资格化回执](b_lite_partial_canonical_admission_p0_r1_receipt.json)。测试仅使用新建隔离数据库、合成 PDF/文本、确定性 Provider stub 和合成 Human 身份；未宣称全仓库测试通过。

## 限制与后续真实验收

本 P0 不接纳损坏 JSON 前缀，不提供通用修复、模糊定位、复杂 Relation 晋升、自动事实核验、BASIS_ELIGIBLE 授予流程或自动 View 更新。重复批次和修订仍受既有每日 intake 上限约束。匿名来源属性不会因为模型双审、重复 Attempt 或同源转载而升级为独立现实证据。

真实试点需要 HUMAN_USER 另行授权指定材料、Provider 预算、备份与 schema 准备、每批最终审核及精确 Apply。最小方案：

1. 选择一份普通匿名材料，经正常 Source Operations 获得好坏混合响应，记录原失败与 Coverage。只对原文可支持的对象完成 A/B、Human Native Seal 和 Attribution；检查合理的 CREATE/REUSE/NO_LINK。
2. 审查精确新增差异后单独授权 Apply；在 MCP/Explorer 核对 B-lite 标签、Source/Evidence 血缘和三类时间，确认未改变官方 Current View。
3. 在既有预算窗口内，对同一 Source 后续可准入对象执行第二批审核和单独 Apply；核对 Source 整行未覆盖、新增 Claim 恰好一次，再重复输入验证零增量。
4. 同时观察一个新普通 Source 的局部 Segment 失败，确认其余已预算 Segment 可继续，原失败和最终 Coverage 缺口仍保留。

工程资格化不能替代上述真实验收。此次不合并、不激活 Stable、不切换运行安装。
