# pro_a 冻结需求规则（v0.1 基线）

## 1. 四对象模型

- **Source**：原始资料，永远保留，不被 AI 改写。
- **Claim**：可验证、引用、更新、冲突或证伪的最小陈述。
- **Knowledge Node**：值得长期独立研究、反复关联资料、维护 Current View 的研究对象。
- **Current View**：某 Node 在某一日期的正式认知快照。

物理 Source 只存一份；一个 Source / Claim 可以关联多个 Node。

## 2. Node Types

`Industry / Segment / Technology / Product / Material / Equipment / Entity / Company / Application / Standard / Policy / Theme / Event / ResearchQuestion`

一个 Node 只有一个 Primary Type。Type 表达“是什么”；关系表达“处于哪里”。

新 Node 必须用户确认后才能正式创建。

Phase 2.3F 明确确认 `Company` 为 canonical Node Type；这是一项人工授权的最小合同扩展，不改变其他 Node Type。

## 2.1 Claim → Node attribution roles

`subject / context / related`

- `subject`：Node 是 Claim 的事实主体；
- `context`：Claim 与 Node 实质相关，但 Node 不是事实主体；
- `related`：legacy / generic association，尚未完成人工 subject/context adjudication。

Claim → Node link 存在不等于该 Node 是 Claim 的 primary subject。后续 Current View candidate 应优先使用目标 Node 的 `role=subject` Claims；`context` Claims 不得直接写成该 Node 自身或行业整体事实。

Current View direct factual evidence MUST use `role=subject`. `role=context` is context-only and MUST NOT directly support Node-own factual assertions. `role=related` MUST NOT directly support Current View facts until adjudicated. `needs_review` Claims MUST NOT be primary Current View evidence. `expert_judgment` MUST remain attributed. `company_guidance` MUST preserve company attribution and future-time semantics.

## 3. Node Relations

标准关系：

- `part_of`
- `upstream_of`
- `supplies`
- `produces`
- `uses`
- `applied_in`
- `substitutes`
- `depends_on`
- `constrains`
- `drives`
- `competes_with`
- `benefits_from`
- `exposed_to`
- `regulated_by`
- `validates`
- `invalidates`
- `related_to`

`part_of` 属于结构关系；其他研究关系原则上需要 Evidence。

## 4. 三个时间

- Fact/Event Time：事实发生或预测对应时间。
- Publication Time：资料发布时间。
- Ingestion Time：进入知识库时间。

不得混用。

## 5. Claim Nature

- `fact`
- `data`
- `company_guidance`
- `expert_judgment`
- `broker_forecast`
- `market_rumor`
- `user_judgment`
- `ai_inference`

来源等级与单条 Claim 可信度分开记录。

## 6. Claim 冲突

旧信息不因新信息自动删除。Claim 之间允许：

- `supports`
- `contradicts`
- `updates`
- `replaces`
- `invalidates`

先进行 Scope Normalization，再判断冲突。

## 7. Current View 版本

正式版本：`v_YYYYMMDD`。

同日多次正式变更：`v_YYYYMMDD_01`、`_02`……

旧版本永不覆盖。

## 8. Current View 变更等级

### Minor
只改变 L3 证据层，不改变 L2/L1。

### Material
至少一个 L2 关键子判断实质改变，但 L1 核心结论、核心逻辑链和投资方向仍成立。

### Thesis Change
L1 核心结论、核心逻辑链或投资方向至少一项反转或失效。

### Evidence Sufficiency
- Material：一条直接高可信 Primary Evidence，或两条以上相互独立且较高可信 Evidence，或核心假设被实际结果直接验证/证伪。
- Thesis：一条决定性 Primary Evidence，或至少两条独立高质量 Evidence；且必须解释“核心假设失效 → 逻辑链失效 → 最终结论改变”。
- 单条低可信 Claim 原则上不能支撑 Material/Thesis。

**任何 Current View 变更都必须用户确认。**

## 9. Propagation

正式确认 Current View 变化后：

1. 沿当前 Node 向上/向下进行 Impact Review，直到某路径不改变被传播 Node 的 Current View。
2. 再向关联 Node 传播，直到不改变被传播 Node 的 Current View。
3. 关联 Node 若正式改变 Current View，重复 1、2。
4. 传播的是 Impact Review，不是结论复制。
5. 同一 Evidence/Change Batch 中，同一 Node 同一版本只评估一次，防循环。
6. 未经用户确认的 Proposed Current View 不向外传播。

## 10. Knowledge Gap

可自动创建，不需要用户确认。

触发：
- 核心假设未经验证；
- Claims 冲突无法解释；
- 重要字段缺可靠数据；
- Evidence 过时；
- 可能影响结论但证据不足。

状态：`open / resolved / no_longer_relevant / superseded / reopened / needs_refresh`。

## 11. Research Question

重要 Knowledge Gap 可升级为 ResearchQuestion Candidate；由于它是 Node，必须用户确认。

应维护：Question、Current Answer、支持/反对 Evidence、关键变量、Confidence、What Would Change My Mind、状态。

## 12. Ingestion Modes

用户通过投放目录主动选择：

- `archive`：保存 Source + IMA 原件，不进行 Claim/Current View 分析。
- `standard`：Source → Node → Claim → 历史 Claim 比对 → Current View Impact Review。
- `deep`：在 Standard 基础上要求更完整的定量、供需、格局、技术、假设、风险和 RQ/Gap 识别。

## 13. 必须用户确认

仅两大类：

1. 新增 Node（含 ResearchQuestion）。
2. 新 Claim / 传播影响要求改变任何关联 Node 的 Current View。

其他低风险结构化处理可自动执行并保留审计记录。
