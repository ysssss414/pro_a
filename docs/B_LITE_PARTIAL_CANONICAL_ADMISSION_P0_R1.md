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
python -m pro_a.admission_schema --workbench-config <config> --database <configured-canonical-db> --expected-sha256 <exact-pre-migration-sha> --backup <new-backup>
```

迁移要求原基线完全匹配、独占事务、无 WAL/SHM/journal、独立新备份，并验证 schema、完整性和外键。导入、查询和 `init_schema` 不会自动执行该迁移。初次工程资格化仅迁移合成数据库；本轮发布预检另验证了真实库的隔离副本，正式 Production 迁移始终为 0。

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

## 发布前定向审查 R1

审查起点为 PR #125 的 `94bf6c010c8f47b41dcde055510d5a434a1b2a4d`；远端和本地一致，没有覆盖其他提交。前述 258/51 项为该提交的既有资格化，本轮复测结果独立记录于回执的 `release_preflight`，未重复计数。

本轮仅修复两个产品缺陷：

- 迁移原先直接写备份后就修改源库，缺少 flush/fsync、完整字节校验及可靠发布。现在复用既有迁移的离线字节复制方式，先写独占 `.pending`、flush/fsync、校验 SHA，再发布完整备份并复核，最后执行 DDL。Windows 使用不覆盖目的文件的 [MoveFileExW / WRITE_THROUGH](https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-movefileexw)，POSIX 同步父目录。迁移锁期间竞争写入者被拒绝；只接受 DELETE journal，源完整性/外键先验检查，显式 `synchronous=EXTRA`，异常回滚并验证旧字节。目标必须匹配 Workbench 配置中的 Canonical 路径，路径祖先链接/硬链接与已有备份/中间文件均拒绝。
- Current View 基线摘要原先写死 `0.2.3`，现在绑定实际 Canonical schema。Runtime 已包含所改文件，旧资格化包不能借用新 runtime。

| 审查项 | 结论 | 证据与限制 |
|---|---|---|
| MIGRATION_AND_BACKUP | PASS | 合成故障测试及真实 Canonical 隔离副本迁移/恢复通过；正式迁移为 0。 |
| CURRENT_VIEW_COMPATIBILITY | PASS_WITH_EXPLICIT_LIMITATION | 历史读取/比较、Schema12 草稿入口保留；迁移后所有无 BASIS_ELIGIBLE 依据的正式更新冻结，详见下文。 |
| RUN_CAPACITY_AND_DERIVED_ADMISSION | PASS_WITH_EXPLICIT_LIMITATION | 原抽取 + 两批 Candidate 正好占 3 Runs；零增量不新建 Run。未调整额度。 |
| ORIGIN_REVIEW_PROMOTION_INTEGRITY | PASS | 新 Origin、修订依赖、双审、Human/Seal/Attribution 及精确 Apply 的合成正反向回归。 |
| SOURCE_REUSE_AND_IDEMPOTENCY | PASS | 同源两批整行复用、跨批次去重、重复零增量及 Operator 冲突/崩溃恢复聚焦回归。 |
| B_LITE_QUERY_AND_USAGE_GUARDS | PASS | MCP/Explorer 的 B-lite 标签、Current View 和定量 Impact 拒绝边界；仍为只读 MCP。 |

### 真实副本与正式迁移边界

仅通过只读文件句柄复制配置指向的真实库，复制期间禁止其他句柄写入/删除；未用 SQLite 打开原库。副本迁移 `0.2.3 → 0.2.4` 前后逐表比较所有历史字段和关系，保留 327 Node、208 Relation、36 Source、159 Claim、3 Current View（2 official、1 baseline）。全部历史 Claim 治理字段为 LEGACY_UNKNOWN。完整性为 ok、外键违例为 0；备份恢复到第三个独立文件后与迁移前 SHA 完全一致。

对副本的全部 327 节点、36 Source 做 Query/MCP/隔离 Schema12 Workbench 读取，副本数据库字节未变。真实库没有同节点的多版本 official 历史，故版本比较由本轮合成历史用例验证，不宣称该项在真实多版本数据上通过。私有副本、路径和详细记录仅留在本地忽略目录；公开回执只有摘要。

正式迁移前必须独立批准目标配置、精确 SHA 和新备份位置，停止全部相关服务/写入者，并确认 DELETE journal、无 WAL/SHM/journal、目录可写且空间足够。路径/摘要/schema 不符、任一 sidecar 或 `.pending` 存在、备份冲突、无法独占、短写/同步/完整性失败，全部停止；不得删除正式 sidecar 后重试。

异常返回且旧字节验证通过时，源库未迁移；完整备份保留供核查。进程/系统骤停留下的 `.pending` 不是恢复凭证，不得重命名冒充备份。若出现 `B_LITE_MIGRATION_RECOVERY_REQUIRED`、热 journal 或提交结果不明，先停止服务、保留现场，不能自动重试。人工恢复需再次授权：核对完整备份等于批准的迁移前 SHA，在另一个隔离文件上恢复并验证完整性/外键和历史行，再决定是否替换正式目标。不得用旧备份覆盖迁移后已产生的新知识。测试覆盖进程可模拟故障和恢复，不声称验证物理掉电、硬件失效或网络文件系统持久性。

### Current View 的确切冻结范围

0.2.4 中没有可供普通用户授予 BASIS_ELIGIBLE 的工作流，因此迁移的 159 条历史 Claim 和新 CLUE_ONLY Claim 都不能作为新的官方依据。已有 2 个 official View 原样可读，但它们的普通更新同样被冻结；这不是只限制新 B-lite Claim。`initial/minor/material/thesis` 无例外，直接 SQL UPDATE（包括仅修改官方记录元数据）、Proposal 接受和 View Operator 也受同一触发器约束。草稿保存、历史阅读、既有版本比较可用；质量验证/资格化不会把不合格依据放行。未迁移 0.2.3 的原维护路径有回归，但不能用“不迁移”代替本 P0 的发布条件。

本轮不自动放行旧证据，不新增勾选豁免或 P1 核验流程。HUMAN_USER 发布审核必须明确接受这一业务冻结；如果当前业务要求继续正式维护 View，则不得按本 P0 发布，需另行批准最小受控用途审核工作。定量 Impact 同样排除 CLUE_ONLY/UNKNOWN；Direct Impact 仍可展示历史引用关系，展示不构成新增事实采信。

### 首份材料的实际额度与授权顺序

| 操作 | Run 额度 | 实际工作 |
|---|---:|---|
| 上传/注册新 Source | 0 | 本地材料登记；点击处理后才创建 Run。 |
| 原抽取 Run | 1 | 冻结预算内的抽取调用；完整成功路径还含 Semantic。 |
| Candidate 第一/第二批 | 各 1 | 准备阶段不调用 Provider、不增加抽取 Attempt；推进时仍产生受预算约束的 Semantic Job 和 Review Packet。 |
| Packet 中的 A/B、Human、Seal/Attribution | 0 | 不新建 Source Run；独立外部 Reviewer 使用及费用需在真实授权中明确。 |
| 精确重复、全部关闭后的零增量 | 0 | 不创建新 Run、Job、Packet，也不再次抽取。 |

普通窗口为空、WIP/暂停/队列保护允许时，原抽取 + 第一批 + 第二批 + 零增量可在正常 3 Runs/rolling 24h 内完成。进一步修订或新材料须等待窗口释放；已有其他 Run 会占用同一额度。Candidate 额度未与新材料分离，作为本 P0 明确的日常容量限制保留，未提高任何 Provider 上限。既有 Semantic 每批最多 8 个 parent、每 Run 最多 31 Job、单 worker、WIP soft 100/hard 200 及暂停保护继续适用。

`start_qualification_intake` 是工程内部显式入口，包含原 Run 在内最多 10 Runs/24h；不是浏览器或 MCP 授权，也没有 Candidate 的资格化额度入口。旧 `start_qualification_reprocess` 仅对已有抽取历史显式重处理，原有逻辑没有同样的 10 次硬上限；不能把它解释为日常无限授权或用于绕开 Candidate 窗口。本次均未使用真实资格化额度。首份试点无需此例外，窗口不足时优先等待；任何工程例外必须另列具体 Run/材料/预算批准。

最短真实试点顺序：① 独立批准发布/合并和安装切换，核对新版本；② 独立批准 Production 备份及显式迁移，并接受上述 View 冻结；③ 指定一份匿名材料，批准抽取、Semantic、Reviewer 预算并检查可用窗口；④ 正常处理和候选批次，分别取得 A/B 实际意见；⑤ HUMAN_USER 决定与 Native Seal、Attribution；⑥ 对该批精确差异单独批准 Apply；⑦ MCP/Explorer 核对来源、用途和日期；⑧ 在窗口允许时对同一 Source 第二批再次审核、单独批准 Apply，再做零增量核对。本次不执行上述真实动作，也不扩展到批量材料运行。
