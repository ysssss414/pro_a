# HUMAN_QUALIFICATION_PACKET_SELF_CONTAINED

本文件包含冻结的 105 项完整审核条目，无需 HTML、分页文件或本地文件链接。所有 SYSTEM_RECOMMENDED_DECISION 仅为本轮展示层辅助建议；不会替代、改写 A/B 结论、冻结风险集合或任何 HUMAN_USER 决策。

| Section | Items | Purpose |
| --- | ---: | --- |
| A | 31 | AI substantially agrees, but frozen risk rules still require human review |
| B | 45 | Review A/B substantive disagreement |
| C | 29 | Sampling Regime B residual qualification |

冻结总体：274；原 HUMAN_REQUIRED：234；必审：76；抽样：29（27 随机核心 + 2 域覆盖补充）。总体 SHA256：`b363748e9aa05be4d66d7ff5c3d0008e9a80df29a25741f72d60c7c32c983b51`。

冻结 seed：`b2c61c6d67fd29f4e1105905de7afc1fd2c63291573b189136f8d23b7d244642`。Residual N=198。Regime B 参数：10% 错误检测情景、95% 发现目标、核心下限20；发现任何实质抽样错误均须按原规则失败/扩审。没有重新抽样。

原始双审包 SHA256：`ac721ae49241cade45224a4fad9020ea7d70407df00be1809a8663f2fa756bb3`；原对账 SHA256：`3631ead5334528a174a97683105fe5a1125b6e90fe9748f92c787be9c6b58b9b`；原样本 SHA256：`44051e472043f12bb416e7947d4f67a0f16d8785a4154d963e96726bbaed09a3`。

阅读约定：CURRENT_NATIVE_OPERATION 是冻结入库提议或 UNDECIDED，并非人类已批准操作；CURRENT_STATUS 保留原分类。SC-CN 是未必已建立的候选身份，NODE_ 是目录身份。下文目标名称/类型均来自冻结候选或 canonical 快照。

原生词汇映射：ACCEPT_OWNER <ID> = ATTACH（仅别名）；KEEP_AS_BASELINE_CANDIDATE = ACCEPT（仅基线交接）；关系使用 CREATE/REUSE/DEFER/REJECT；Claim 暂缓使用 KEEP_NEEDS_REVIEW。所有选项未勾选。正式 Node CREATE、别名写入、关系建边、Production apply 与 Official View 激活均未执行；官方激活不在普通选项内。

风险词典：R01=A/B实质分歧；R02=低或必要UNKNOWN置信度；R03=证据缺口；R04=实质命题歧义；R05=身份冲突；R06=跨域身份冲突；R07=新增高影响Node；R08=实质关系歧义；R09=因果命题歧义；R10=时间矛盾；R11=重大Current View变更；R12=重大Direct Impact变更；R13=本体/类型映射问题；R14=政策不变量违反。TRUE 或必要 UNKNOWN 不因 AI 一致而免审。盲审记录中的 R01=UNKNOWN 只表示当时尚未比较；最终路由以原冻结 reconciliation 为准。

证据约定：Source 原始身份、物理哈希、页/节与 Evidence ID 均在每项内给出；原文为有界节选，[…] 表示省略，不是完整原文。支持事实与缺口由原 A/B 理由共同呈现；未读取原始 PDF、没有补充检索或引入新事实。来源年代、预测和当前事实不可互换。

七项原生操作冲突（点击跳转）：[SC-AL-0009](#sc-al-0009)；[SC-CL-0019](#sc-cl-0019)；[SC-CN-0015](#sc-cn-0015)；[SC-CN-0028](#sc-cn-0028)；[SC-CN-0050](#sc-cn-0050)；[SC-CN-0093](#sc-cn-0093)；[SC-CN-0122](#sc-cn-0122)。

WIP=274/HARD_STOP；NEW_INTAKE_ALLOWED=false；最终人类资格=PENDING。

## SECTION A — Consensus Mandatory Human Review

31 items

<a id="sc-bv-0001"></a>
### 001 · SC-BV-0001 · 半导体设计与设计使能

- **ITEM_NUMBER** = 1
- **ITEM_ID** = SC-BV-0001
- **OBJECT_TYPE** = baseline_views
- **DOMAIN** = semiconductor
- **CURRENT_NATIVE_OPERATION** = UNDECIDED（没有已填写的人类原生决定）
- **CURRENT_STATUS** = REVIEW
- **WHY_IN_HUMAN_PACKET** = VIEW_ACTIVATION_REQUIRES_SEPARATE_GOVERNANCE
- **RISK_RULES** = 基线视图独立治理必审；R02–R14无TRUE/必要UNKNOWN命中
- **MANDATORY_TRIGGER** = VIEW_ACTIVATION_REQUIRES_SEPARATE_GOVERNANCE
- **SAMPLE_STATUS** = NOT_SAMPLED
- **SAMPLED_FOR_QUALITY_CONTROL** = false

- **SOURCE_ID / SOURCE_NAME** = SC-PHYS-7E064380CA686D9F / SRC_5AF7599EF3DE9C6D / Explaining Common Chip Terms
Source provenance：Intel；publication=2026-03-09；edition=；as_of=2026-03-09；source SHA256=`7e064380ca686d9f00c235f15c007523e89e4a0ffb7e9a22f435218c06799d05`。
- **SOURCE_ID / SOURCE_NAME** = SC-PHYS-AC86A7FEB4F6ADB5 / SRC_689680B30C113F1B / The Growing Challenge of Semiconductor Design Leadership
Source provenance：Semiconductor Industry Association (SIA) / Boston Consulting Group (BCG)；publication=2022-11；edition=；as_of=2022-11；source SHA256=`ac86a7feb4f6adb52e488086f9281c1f409bd72baecb6bdbed72a0efa3856666`。

**CANDIDATE_SUMMARY**

- 不确定性：本轮没有详细signoff/DFM的可用定义；IP和经营模式节点仍需类型审查。
- 核心结论：设计采用多阶段协作；EDA工具、可复用IP、PDK与制造过程兼容性分别承担不同职责。；Exhibit3明确给出layout中的routing/mask generation及基于仿真的功能/时序验证。；Intel把PDK解释为服务于特定process node的设计信息；节点名称不能直接理解为单一物理尺寸。
- 概述：半导体设计与设计使能
- 状态：CANDIDATE_HANDOFF_ONLY
- 节点：SC-CN-0020
- Planned native target：NODE_63D3FFF5A5A14739 → SC-CN-0020 / Semiconductor Design / Technology；这是候选映射，不是已存在或获批准的目录对象。
- Candidate target：SC-CN-0020 = Semiconductor Design；type=Technology；frozen status=CREATE；仍须目标自身授权。

**AI REVIEW A**

- recommendation：ACCEPT_WITH_REVIEW_NOTE；native_decision：ACCEPT
- proposed operation / canonical target：ACCEPT；目标: SC-CN-0020 [Semiconductor Design]；范围/说明: CANDIDATE_HANDOFF_ONLY; source-scoped cross-year technical baseline; no official activation
- confidence：MEDIUM
- reason：三条结构结论分别有设计流程/PDK 协作、Exhibit3 和 Intel 定义支持，保留 IP 类型及 signoff 缺口；catalog 无同目标旧基线，仅接受交付文本，激活仍待人工。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-7BF90F70A09B7369, SC-EV-6FF6BB080099D1E2, SC-EV-73E156B2F86976F1, SC-EV-3372E0A59571A7A8, SC-EV-0C635A3097DA01EF, SC-EV-A7155A1FD4102457, SC-EV-3F0EC598BF78F3BE, SC-EV-822974FB05D75D67

**AI REVIEW B**

- recommendation：ACCEPT_WITH_REVIEW_NOTE；native_decision：ACCEPT
- proposed operation / canonical target：ACCEPT；目标: SC-CN-0020 [Semiconductor Design]；范围/说明: CANDIDATE_HANDOFF_ONLY; 半导体设计与设计使能; no official activation
- confidence：MEDIUM
- reason：三个结构结论分别由设计阶段、EDA/IP/PDK及Intel节点说明支持，已核Exhibit3；与目录三份现有视图目标无重复，接受交接基线而非正式激活。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-7BF90F70A09B7369, SC-EV-6FF6BB080099D1E2, SC-EV-73E156B2F86976F1, SC-EV-3372E0A59571A7A8, SC-EV-0C635A3097DA01EF, SC-EV-A7155A1FD4102457, SC-EV-3F0EC598BF78F3BE, SC-EV-822974FB05D75D67

**A/B RECONCILIATION**

- frozen status：A_B_SUBSTANTIVE_AGREEMENT
- 实质分歧：无；措辞、附注或不改变风险路由的置信度差异不改原冻结一致结论。

**EVIDENCE SUMMARY**

- Supporting facts：下列有来源的节选支持本项讨论的对象/命题；支持范围及未解决条件已在上方 A/B reason 中逐项说明。
- SC-EV-0C635A3097DA01EF / SC-PHYS-AC86A7FEB4F6ADB5 / PDF p.8 / Integrated circuit design / Layout / printed p.6 / Exhibit 3；excerpt SHA256=`49bc7a28b803ddea6756377f8ea25ea0d0289b80d9f515f03f97cebe1d6af455`。
  > Layout: Routing and mask generation
- SC-EV-3372E0A59571A7A8 / SC-PHYS-AC86A7FEB4F6ADB5 / PDF p.28 / Design and front-end wafer fabrication / printed p.26；excerpt SHA256=`ec8a497765e2866b5eec4ecfe2a0105213050c6981426ba04cd46f10cfa84e06`。
  > Design engineers and wafer fabrication engineers use PDKs—essentially documentation of fabri- cation processes—and work together to debug design features and verify that manufacturing processes and chip designs are compatible.
- SC-EV-3F0EC598BF78F3BE / SC-PHYS-7E064380CA686D9F / PDF p.5 / Process Nodes and PDKs / printed p.NOT_KNOWN_OR_UNNUMBERED；excerpt SHA256=`db51b1f1b4fb2125c728906ffa1d0c27a06c98ada75bb0715185b347234f90bc`。
  > A process design kit, or PDK, is a set of specifications, guidelines and tools to design a chip using a specific process node.
- SC-EV-6FF6BB080099D1E2 / SC-PHYS-AC86A7FEB4F6ADB5 / PDF p.7 / Design Is Complex and Includes Multiple Different Types of Firms and Activities / printed p.5；excerpt SHA256=`9da9a2377834d759f2de42083bcaa3f4fe5058e8a692338d19c2d69126d80626`。
  > Designers will often use existing, reusable architectural building blocks (core IP) to simplify and accelerate creation of the overall design. In all cases, designers use highly advanced EDA software to automate the design process and ensure that chip designs can be manufactured on distinct and often proprietary fabrication processes.
- SC-EV-73E156B2F86976F1 / SC-PHYS-AC86A7FEB4F6ADB5 / PDF p.27 / Electronic Design Automation (EDA) and Core IP / printed p.25；excerpt SHA256=`90fa4c7132b45faac51c8dbe99df2a144e6fb7c9a6026ef36e5c19b30ea75185`。
  > Design Tools. Such tools are enabled for a specific foundry, technology node, and process design kit (PDK).
- SC-EV-7BF90F70A09B7369 / SC-PHYS-AC86A7FEB4F6ADB5 / PDF p.7 / Design Is Complex and Includes Multiple Different Types of Firms and Activities / printed p.5；excerpt SHA256=`bb7a8c0baae4bad3cc8541ea8e20c7ffe75a1694eb4dbd3592d7b7c436e25ada`。
  > Semiconductor design involves two types of activities: hard­ware design and software development work. Hard- ware design is a multistep process encompassing product definition and specification, system design, integrated circuit design, and post-silicon validation.
- SC-EV-822974FB05D75D67 / SC-PHYS-7E064380CA686D9F / PDF p.5 / Process Nodes and PDKs / printed p.NOT_KNOWN_OR_UNNUMBERED；excerpt SHA256=`6893db69461ee4efde307c2866f75b09e9dc0cb3e2f8a3860595fb0c99e258ee`。
  > In the past, process node names were based on physical measurements in micrometers or nanometers (like 0.13 microns or 45 nanometers), but current names are closer to representations of each node’s increase in density and/or performance.
- SC-EV-A7155A1FD4102457 / SC-PHYS-AC86A7FEB4F6ADB5 / PDF p.8 / Design stages / Verification / printed p.6 / Exhibit 3；excerpt SHA256=`dbfa8018449e4100f86a44c0134a2ba1f92186078f4d812d2873b10f85353d98`。
  > Verification engineers verify design functionality and timing through simulation
- Conflicting evidence：冻结 A/B 未报告本限定范围内的未解决实质证据冲突；不等于完整文献已穷尽。

- **SYSTEM_RECOMMENDED_DECISION** = KEEP_AS_BASELINE_CANDIDATE
推荐理由（非人工裁决）：双方仅支持保留这份有来源的基线候选；建议采纳候选文本，保留原不确定性。此选项映射原生 ACCEPT，仅用于基线交接，绝不包含 Official View 激活。

HUMAN_USER_DECISION = [PENDING]

OPTIONS:

- [ ] KEEP_AS_BASELINE_CANDIDATE（原生 ACCEPT；不激活官方 View）
- [ ] DEFER
- [ ] REJECT

---

<a id="sc-bv-0002"></a>
### 002 · SC-BV-0002 · 起始硅晶圆与材料状态

- **ITEM_NUMBER** = 2
- **ITEM_ID** = SC-BV-0002
- **OBJECT_TYPE** = baseline_views
- **DOMAIN** = semiconductor
- **CURRENT_NATIVE_OPERATION** = UNDECIDED（没有已填写的人类原生决定）
- **CURRENT_STATUS** = REVIEW
- **WHY_IN_HUMAN_PACKET** = VIEW_ACTIVATION_REQUIRES_SEPARATE_GOVERNANCE
- **RISK_RULES** = 基线视图独立治理必审；R02–R14无TRUE/必要UNKNOWN命中
- **MANDATORY_TRIGGER** = VIEW_ACTIVATION_REQUIRES_SEPARATE_GOVERNANCE
- **SAMPLE_STATUS** = NOT_SAMPLED
- **SAMPLED_FOR_QUALITY_CONTROL** = false

- **SOURCE_ID / SOURCE_NAME** = SC-PHYS-9E9CEFC24043585C / SRC_8442AD30618C9A2D / Production Processes
Source provenance：SUMCO Corporation；publication=；edition=；as_of=；source SHA256=`9e9cefc24043585c1c5a484340dcf49aa0725b341467942d3d4c34be0da8aee6`。

**CANDIDATE_SUMMARY**

- 不确定性：SUMCO未给出版日期；不能把网页抓取时间充作事实日期。SOI与既有身份英文复数映射尚未授权。
- 核心结论：SUMCO的单晶硅锭拉制以高质量多晶硅为原料；CZ、MCZ/FZ是所述方法，不应把特定供应商流程当全部配方。；切片、研磨、化学去损伤和镜面抛光属于起始晶圆成形；切硅锭与成品wafer dicing分开。；外延晶圆描述包括外延炉和SiCl4/SiHCl3；退火晶圆、SOI有各自工艺描述，身份边界保留待审。
- 概述：起始硅晶圆与材料状态
- 状态：CANDIDATE_HANDOFF_ONLY
- 节点：SC-CN-0025
- Planned native target：NODE_B96F04EBB6D1FD0A → SC-CN-0025 / Silicon Wafer / Material；这是候选映射，不是已存在或获批准的目录对象。
- Candidate target：SC-CN-0025 = Silicon Wafer；type=Material；frozen status=CREATE；仍须目标自身授权。

**AI REVIEW A**

- recommendation：ACCEPT_WITH_REVIEW_NOTE；native_decision：ACCEPT
- proposed operation / canonical target：ACCEPT；目标: SC-CN-0025 [Silicon Wafer]；范围/说明: CANDIDATE_HANDOFF_ONLY; source-scoped cross-year technical baseline; no official activation
- confidence：MEDIUM
- reason：SUMCO 原料、生长、成形和特殊处理链与摘录一致，明确供应商限定及 undated；SOI 复用可在后续身份治理处理，基线不创建新材料身份也不激活。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-3BE221EFD700F965, SC-EV-C7BD218505458FDB, SC-EV-F238C2DB2FE11AB8, SC-EV-44BA70339AC36BAC, SC-EV-59686E8EF98436C8, SC-EV-3B7A003A9F1CA2BB, SC-EV-FD093A8B2A6553C4, SC-EV-574D5C0F2C499255, SC-EV-B0A9AF87FF9B65B0, SC-EV-CFBF2B108331D342

**AI REVIEW B**

- recommendation：ACCEPT_WITH_REVIEW_NOTE；native_decision：ACCEPT
- proposed operation / canonical target：ACCEPT；目标: SC-CN-0025 [Silicon Wafer]；范围/说明: CANDIDATE_HANDOFF_ONLY; 起始硅晶圆与材料状态; no official activation
- confidence：MEDIUM
- reason：SUMCO原料/成形/外延退火SOI三组工艺证据对应结论，未注明日期显式保留；身份疑问列为边界，无现有同目标视图重复。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-3BE221EFD700F965, SC-EV-C7BD218505458FDB, SC-EV-F238C2DB2FE11AB8, SC-EV-44BA70339AC36BAC, SC-EV-59686E8EF98436C8, SC-EV-3B7A003A9F1CA2BB, SC-EV-FD093A8B2A6553C4, SC-EV-574D5C0F2C499255, SC-EV-B0A9AF87FF9B65B0, SC-EV-CFBF2B108331D342

**A/B RECONCILIATION**

- frozen status：A_B_SUBSTANTIVE_AGREEMENT
- 实质分歧：无；措辞、附注或不改变风险路由的置信度差异不改原冻结一致结论。

**EVIDENCE SUMMARY**

- Supporting facts：下列有来源的节选支持本项讨论的对象/命题；支持范围及未解决条件已在上方 A/B reason 中逐项说明。
- SC-EV-3B7A003A9F1CA2BB / SC-PHYS-9E9CEFC24043585C / PDF p.4 / Wafer forming process / Etching / printed p.NOT_KNOWN_OR_UNNUMBERED；excerpt SHA256=`c141ea45a45cc1382dc2fdefac9840964f746b34469313dd7ae354cbd9fef6c3`。
  > Mechanical damage to the wafer surface resulting from the earlier steps is removed by chemical etching.
- SC-EV-3BE221EFD700F965 / SC-PHYS-9E9CEFC24043585C / PDF p.2 / Monocrystalline pulling process / printed p.NOT_KNOWN_OR_UNNUMBERED；excerpt SHA256=`f2a1f5fd0055ec8e3500d40754ed50d70d52dad829317164794bd41622d18e97`。
  > The monocrystalline ingots that make up the silicon wafer are manufactured using high-quality polysilicon as the raw material.
- SC-EV-44BA70339AC36BAC / SC-PHYS-9E9CEFC24043585C / PDF p.3 / Wafer forming process / Slicing / printed p.NOT_KNOWN_OR_UNNUMBERED；excerpt SHA256=`b0459439e180ff79671cd9239d84ea6970682c6a613f324b5ec9d75a8786654b`。
  > Based on the resistivity desired by the customer, the ingot is then cut into slices of around 1mm thickness, using an inner- diameter saw or wire saw, to form the wafers.
- SC-EV-574D5C0F2C499255 / SC-PHYS-9E9CEFC24043585C / PDF p.5 / Specialized processing / Epitaxial Wafers / printed p.NOT_KNOWN_OR_UNNUMBERED；excerpt SHA256=`05a7510d15a9807f50dcd0d6dee327bf1eb6a76b6d21d1371ceeaa903e645f76`。
  > Polished wafers are heated to around 1200℃ in an epitaxial furnace. Vaporized silicon tetrachloride (SiCl4) and trichlorosilane (SiHCl3) are circulated in the furnace, causing vapor phase (epitaxial) growth of a monocrystalline silicon film on the wafer surface.
- SC-EV-59686E8EF98436C8 / SC-PHYS-9E9CEFC24043585C / PDF p.4 / Wafer forming process / Lapping / printed p.NOT_KNOWN_OR_UNNUMBERED；excerpt SHA256=`613f013c46d172e638702427a7a295ccde9f3d40ec6d44103042ccb6e2cec5de`。
  > The sliced wafers are polished by alumina abrasive in a lapping machine to the desired thickness, while improving the surface parallelism.
- SC-EV-B0A9AF87FF9B65B0 / SC-PHYS-9E9CEFC24043585C / PDF p.6 / Specialized processing / Annealed Wafers / printed p.NOT_KNOWN_OR_UNNUMBERED；excerpt SHA256=`767ea134e24883643a5e4a6af769da47d7b49995846f1d7cb7d4d057275af248`。
  > A polished wafer undergoes high-temperature annealing in an atmosphere of hydrogen or argon. As this process removes oxygen near the wafer surface, the resulting wafer has improved crystal perfection.
- SC-EV-C7BD218505458FDB / SC-PHYS-9E9CEFC24043585C / PDF p.2 / Monocrystalline pulling process / Flow of CZ process / printed p.NOT_KNOWN_OR_UNNUMBERED；excerpt SHA256=`912c3479df08fa552a86cfa9d75db0cd77828331ac18b369220ec498e0515be2`。
  > The monocrystalline silicon ingots from which silicon wafers are created are manufactured by a technique called the CZ (Czochralski) crystal growth process.
- SC-EV-CFBF2B108331D342 / SC-PHYS-9E9CEFC24043585C / PDF p.7 / Specialized processing / Silicon-On-Insulator Wafers / printed p.NOT_KNOWN_OR_UNNUMBERED；excerpt SHA256=`973c0b33097e15d7dcd639b15644dd35e787154e1d9936e11cb1d2d0d9df1b39`。
  > An oxide layer is formed for one or both of the handle wafer and the active wafer on which semiconductor devices will be built. The two wafers are then bonded together by annealing. Next the active wafer is ground and polished to the desired thickness.
- SC-EV-F238C2DB2FE11AB8 / SC-PHYS-9E9CEFC24043585C / PDF p.2 / Other processes can be used on request / printed p.NOT_KNOWN_OR_UNNUMBERED；excerpt SHA256=`56baf358ae35e7baacba41885c904571d0103652acef18198fdb4fc7ee98a8e6`。
  > In response to customer needs, we also make use of the MCZ (Magnetic field applied Czochralski) technique, applying a strong magnetic field, or the FZ (Float- Zone) technique whereby monocrystalline ingots are made at low oxygen levels without using a quartz crucible.
- SC-EV-FD093A8B2A6553C4 / SC-PHYS-9E9CEFC24043585C / PDF p.4 / Wafer forming process / Polishing / printed p.NOT_KNOWN_OR_UNNUMBERED；excerpt SHA256=`a70a51eb8052e9f65809af0fab05039d4211551626cb8a85121594e6ea3362f6`。
  > The wafer surfaces are made perfectly flat and given a mirror finish by means of mechano-chemical polishing using colloidal silica.
- Conflicting evidence：冻结 A/B 未报告本限定范围内的未解决实质证据冲突；不等于完整文献已穷尽。

- **SYSTEM_RECOMMENDED_DECISION** = KEEP_AS_BASELINE_CANDIDATE
推荐理由（非人工裁决）：双方仅支持保留这份有来源的基线候选；建议采纳候选文本，保留原不确定性。此选项映射原生 ACCEPT，仅用于基线交接，绝不包含 Official View 激活。

HUMAN_USER_DECISION = [PENDING]

OPTIONS:

- [ ] KEEP_AS_BASELINE_CANDIDATE（原生 ACCEPT；不激活官方 View）
- [ ] DEFER
- [ ] REJECT

---

<a id="sc-bv-0003"></a>
### 003 · SC-BV-0003 · 晶圆制造：工序、工具、材料分离

- **ITEM_NUMBER** = 3
- **ITEM_ID** = SC-BV-0003
- **OBJECT_TYPE** = baseline_views
- **DOMAIN** = semiconductor
- **CURRENT_NATIVE_OPERATION** = UNDECIDED（没有已填写的人类原生决定）
- **CURRENT_STATUS** = REVIEW
- **WHY_IN_HUMAN_PACKET** = VIEW_ACTIVATION_REQUIRES_SEPARATE_GOVERNANCE
- **RISK_RULES** = 基线视图独立治理必审；R02–R14无TRUE/必要UNKNOWN命中
- **MANDATORY_TRIGGER** = VIEW_ACTIVATION_REQUIRES_SEPARATE_GOVERNANCE
- **SAMPLE_STATUS** = NOT_SAMPLED
- **SAMPLED_FOR_QUALITY_CONTROL** = false

- **SOURCE_ID / SOURCE_NAME** = SC-PHYS-B33C40EBCB5756F7 / SRC_1DD38DEB69830E97 / Strengthening the Global Semiconductor Supply Chain in an Uncertain Era
Source provenance：Semiconductor Industry Association (SIA) / Boston Consulting Group (BCG)；publication=2021-04；edition=；as_of=2021-04；source SHA256=`b33c40ebcb5756f76e887ba2664f97736252e68ba7bfbedc2d628ce2d7cbc08d`。
- **SOURCE_ID / SOURCE_NAME** = SC-PHYS-C5B6DC633E156218 / SRC_AC29CFEE56F74F5B / Testimony of the Semiconductor Industry Association before the Senate Committee on Environment & Public Works (March 4, 2026)
Source provenance：Semiconductor Industry Association (SIA)；publication=2026-03-04；edition=；as_of=2026-03-04；source SHA256=`c5b6dc633e156218eb950f2dee88f43fbdcc4fc1744a5924f12b977f5cb7df71`。

**CANDIDATE_SUMMARY**

- 不确定性：MEOL、完整工艺recipe及多个前端设备族缺覆盖；不能据工序顺序建立upstream_of。
- 核心结论：晶圆FEOL/BEOL制造与独立的assembly/test/packaging operations不同；不把BEOL改作封测别名。；光刻使用光刻胶、掩模与曝光系统；CMP使用slurry和pad，这些是使用关系而非结构归属。；晶圆制造需要化学品输送、洁净环境、废水处理和排气治理；本包只保留技术描述，不带政策论证。
- 概述：晶圆制造：工序、工具、材料分离
- 状态：CANDIDATE_HANDOFF_ONLY
- 节点：SC-CN-0021
- Planned native target：NODE_C7C6BD126DAA8EA7 → SC-CN-0021 / Wafer Fabrication / Technology；这是候选映射，不是已存在或获批准的目录对象。
- Candidate target：SC-CN-0021 = Wafer Fabrication；type=Technology；frozen status=CREATE；仍须目标自身授权。

**AI REVIEW A**

- recommendation：ACCEPT_WITH_REVIEW_NOTE；native_decision：ACCEPT
- proposed operation / canonical target：ACCEPT；目标: SC-CN-0021 [Wafer Fabrication]；范围/说明: CANDIDATE_HANDOFF_ONLY; source-scoped cross-year technical baseline; no official activation
- confidence：MEDIUM
- reason：已看 Figure3，FEOL/BEOL 与 assembly/test 分离正确；光刻/CMP 使用关系和设施描述有对应证据，缺 recipe/MEOL 已披露，无同目标旧视图。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-A05B9807213F3DF1, SC-EV-79EA49E93CAF7F64, SC-EV-30ECB7A5649A64DC, SC-EV-B569E06E885DA787, SC-EV-67EC75515BB09180, SC-EV-E1426DD81060C643, SC-EV-3AC8C4181A8977F9, SC-EV-DEEF5988AF3E27FE, SC-EV-37D8E37F58E96AEA, SC-EV-6D361D680E26A1C9

**AI REVIEW B**

- recommendation：ACCEPT_WITH_REVIEW_NOTE；native_decision：ACCEPT
- proposed operation / canonical target：ACCEPT；目标: SC-CN-0021 [Wafer Fabrication]；范围/说明: CANDIDATE_HANDOFF_ONLY; 晶圆制造：工序、工具、材料分离; no official activation
- confidence：MEDIUM
- reason：已核SIA图3的FEOL、BEOL与assembly/test分列；光刻/CMP工具材料及厂务描述有直接证据，未作政策或完整recipe结论。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-A05B9807213F3DF1, SC-EV-79EA49E93CAF7F64, SC-EV-30ECB7A5649A64DC, SC-EV-B569E06E885DA787, SC-EV-67EC75515BB09180, SC-EV-E1426DD81060C643, SC-EV-3AC8C4181A8977F9, SC-EV-DEEF5988AF3E27FE, SC-EV-37D8E37F58E96AEA, SC-EV-6D361D680E26A1C9

**A/B RECONCILIATION**

- frozen status：A_B_SUBSTANTIVE_AGREEMENT
- 实质分歧：无；措辞、附注或不改变风险路由的置信度差异不改原冻结一致结论。

**EVIDENCE SUMMARY**

- Supporting facts：下列有来源的节选支持本项讨论的对象/命题；支持范围及未解决条件已在上方 A/B reason 中逐项说明。
- SC-EV-30ECB7A5649A64DC / SC-PHYS-C5B6DC633E156218 / PDF p.5 / II / Back-End Fabrication / Metallization / printed p.5；excerpt SHA256=`d6a39a41013572a9d37dcb4c73163c05252d55a2ba42d53bb571d3a1f8ac5214`。
  > Metallization: Prior processing steps prepare the device for metallization, which creates the electrical interconnections between all transistors on the wafer. Following completion of the front end, individual devices are interconnected on the "back end" using a series of alternating metal depositions and dielectric films, each with their respective patterning.
- SC-EV-37D8E37F58E96AEA / SC-PHYS-C5B6DC633E156218 / PDF p.8 / III.B / Technical waste treatment description only / printed p.8；excerpt SHA256=`43d849e0db0f62b53a464fa4387fb84b593f92cd78c51d864d17a530e26421a0`。
  > Semiconductor fabs control environmental releases by implementing strict controls including wastewater collection and treatment, waste management systems, and air emissions abatement.
- SC-EV-3AC8C4181A8977F9 / SC-PHYS-C5B6DC633E156218 / PDF p.7 / III.B / Technical clean-environment descriptions only / printed p.7；excerpt SHA256=`8b189360baacb8fb0254999e55435d8384dca456f2b973ade76c8ea768c6602b`。
  > The highly controlled systems in a fab include enclosed processes, automation, and chemical delivery systems. The entire process is conducted in a tightly controlled clean room environment, where there are specific controls on temperature, humidity, and air purity.
- SC-EV-67EC75515BB09180 / SC-PHYS-C5B6DC633E156218 / PDF p.4 / II / Front-End Fabrication / Photolithography / printed p.4；excerpt SHA256=`d49de79df3fb0e595282e9746bcd100459e0a41920f737ed1446f4908192c3a1`。
  > A stepper or scanner (using deep ultraviolet or extreme ultraviolet light) aligns the wafer to a glass photomask and projects intense light through the mask or reticle, exposing the photoresist with the pattern.
- SC-EV-6D361D680E26A1C9 / SC-PHYS-C5B6DC633E156218 / PDF p.8 / III.B / Technical exhaust/abatement description only / printed p.8；excerpt SHA256=`9770f17dcba2eb09d1b826f5aab4d96641e56bd9078e17f8ef490b11c6324970`。
  > Fab exhaust systems remove chemical vapors and heat from process tools. Acids and bases are routed to centralized scrubbers, while volatile organic compounds are abated via centralized thermal, catalytic, or plasma oxidizers which may be equipped to concentrate contaminants prior to abatement.
- SC-EV-79EA49E93CAF7F64 / SC-PHYS-C5B6DC633E156218 / PDF p.4 / II / manufacturing process overview / printed p.4 / Figure 3；excerpt SHA256=`89a542845a4ecc9dfc626b49fc7337eccdadca4d317b03cdd058d4aac201e306`。
  > Back End of Line (BEOL) Fab Manufacturing Process Steps
- SC-EV-A05B9807213F3DF1 / SC-PHYS-C5B6DC633E156218 / PDF p.4 / II / manufacturing process overview / printed p.4 / Figure 3；excerpt SHA256=`c8c02800299a79cb17caba1f2173878ecee34e3d637e732dbbb5f2bfe9fb1a5d`。
  > Front End of Line (FEOL) Fab Manufacturing Process Steps
- SC-EV-B569E06E885DA787 / SC-PHYS-B33C40EBCB5756F7 / PDF p.22 / Materials / printed p.22；excerpt SHA256=`1a71c29703324c17eb2fceb7db5e6ab4eca23efc24c6f283384d56f8117883b4`。
  > Photoresist: A special material that undergoes a chemical reaction upon exposure to light. Silicon wafers are covered with a photoresist layer, which is imprinted with the patterns contained in the photomask during the lithography process.
- SC-EV-DEEF5988AF3E27FE / SC-PHYS-C5B6DC633E156218 / PDF p.8 / III.B / Technical chemical-delivery description only / printed p.8；excerpt SHA256=`5d41c8865eaf1f177831a22a1560a8c6aa44cb77e7e95090786debf71b02d615`。
  > Chemicals are stored and delivered into the manufacturing area using automated chemical delivery systems that prevent personnel exposure and ensure limited human interface.
- SC-EV-E1426DD81060C643 / SC-PHYS-C5B6DC633E156218 / PDF p.5 / II / Back-End Fabrication / CMP / printed p.5；excerpt SHA256=`35b1994c551b3073ed773b253b0c157a5498ed77e2343c093908bd4df7185ea2`。
  > Chemical Mechanical Planarization (CMP): Between many deposition and metallization layers throughout the back-end process, chemical mechanical planarization (CMP) uses chemical and physical forces to create a microscopically flat surface for each successive layer of circuit features. A polishing pad with a liquid chemical called a “slurry” polishes the wafer surface until the desired nanometer topography is achieved on the uppermost exposed layer.
- Conflicting evidence：冻结 A/B 未报告本限定范围内的未解决实质证据冲突；不等于完整文献已穷尽。

- **SYSTEM_RECOMMENDED_DECISION** = KEEP_AS_BASELINE_CANDIDATE
推荐理由（非人工裁决）：双方仅支持保留这份有来源的基线候选；建议采纳候选文本，保留原不确定性。此选项映射原生 ACCEPT，仅用于基线交接，绝不包含 Official View 激活。

HUMAN_USER_DECISION = [PENDING]

OPTIONS:

- [ ] KEEP_AS_BASELINE_CANDIDATE（原生 ACCEPT；不激活官方 View）
- [ ] DEFER
- [ ] REJECT

---

<a id="sc-bv-0004"></a>
### 004 · SC-BV-0004 · 光刻与图形化

- **ITEM_NUMBER** = 4
- **ITEM_ID** = SC-BV-0004
- **OBJECT_TYPE** = baseline_views
- **DOMAIN** = semiconductor
- **CURRENT_NATIVE_OPERATION** = UNDECIDED（没有已填写的人类原生决定）
- **CURRENT_STATUS** = REVIEW
- **WHY_IN_HUMAN_PACKET** = VIEW_ACTIVATION_REQUIRES_SEPARATE_GOVERNANCE
- **RISK_RULES** = 基线视图独立治理必审；R02–R14无TRUE/必要UNKNOWN命中
- **MANDATORY_TRIGGER** = VIEW_ACTIVATION_REQUIRES_SEPARATE_GOVERNANCE
- **SAMPLE_STATUS** = NOT_SAMPLED
- **SAMPLED_FOR_QUALITY_CONTROL** = false

- **SOURCE_ID / SOURCE_NAME** = SC-PHYS-318D85A127B5B6DF / SRC_FFD94DB31A0E9C0A / 2025 IRDS — Lithography and Patterning
Source provenance：IEEE International Roadmap for Devices and Systems (IRDS)；publication=；edition=2025；as_of=2025；source SHA256=`318d85a127b5b6dfa7b3c1330ae20b18d63660a1fa8c8bdfdd7b478844e145ed`。
- **SOURCE_ID / SOURCE_NAME** = SC-PHYS-87B4665C30781057 / SRC_ADCEE4236B19B5F2 / Six Crucial Steps in Semiconductor Manufacturing
Source provenance：ASML；publication=2023-10-04；edition=；as_of=2023-10-04；source SHA256=`87b4665c3078105792ca70f18964c938976b72f2dcf0d19379b034d5d6f205f9`。
- **SOURCE_ID / SOURCE_NAME** = SC-PHYS-B33C40EBCB5756F7 / SRC_1DD38DEB69830E97 / Strengthening the Global Semiconductor Supply Chain in an Uncertain Era
Source provenance：Semiconductor Industry Association (SIA) / Boston Consulting Group (BCG)；publication=2021-04；edition=；as_of=2021-04；source SHA256=`b33c40ebcb5756f76e887ba2664f97736252e68ba7bfbedc2d628ce2d7cbc08d`。

**CANDIDATE_SUMMARY**

- 不确定性：缺失的2024 Excel路线表未推断；High-NA节点粒度和scanner/stepper设备层次待审。
- 核心结论：光刻胶、掩模、曝光工具是不同研究对象；正负光刻胶保留材料分支粒度审查。；2025版IRDS对高NA EUV首次生产使用的2027判断是预测，不是2026现状。；CAR/MOR的使用描述限定于来源所述范围；DSA图形修整保留potential_solution。；封装光刻中的硅与RDL中介层为产品分类；interposer定义与package substrate不同。
- 概述：光刻与图形化
- 状态：CANDIDATE_HANDOFF_ONLY
- 节点：SC-CN-0056
- Planned native target：NODE_D71397E38AE45F20 → SC-CN-0056 / Photolithography / Technology；这是候选映射，不是已存在或获批准的目录对象。
- Candidate target：SC-CN-0056 = Photolithography；type=Technology；frozen status=CREATE；仍须目标自身授权。

**AI REVIEW A**

- recommendation：ACCEPT_WITH_REVIEW_NOTE；native_decision：ACCEPT
- proposed operation / canonical target：ACCEPT；目标: SC-CN-0056 [Photolithography]；范围/说明: CANDIDATE_HANDOFF_ONLY; source-scoped cross-year technical baseline; no official activation
- confidence：MEDIUM
- reason：基线区分光刻材料/掩模/设备与中介层产品，2027 high-NA 为预测、DSA 为潜力，范围及未覆盖路线表明确；仅保留候选交付状态。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-B569E06E885DA787, SC-EV-9393F2354C64C727, SC-EV-5A701F864F4A7C10, SC-EV-8647894434AD8431, SC-EV-6931BFF731D8EB70, SC-EV-2CCA00E79D91DD12, SC-EV-B8DFBCC7175C23E6, SC-EV-55BA223EDE3A8F9F, SC-EV-34A6DFF0912F7884

**AI REVIEW B**

- recommendation：ACCEPT_WITH_REVIEW_NOTE；native_decision：ACCEPT
- proposed operation / canonical target：ACCEPT；目标: SC-CN-0056 [Photolithography]；范围/说明: CANDIDATE_HANDOFF_ONLY; 光刻与图形化; no official activation
- confidence：MEDIUM
- reason：材料/工具分工、2027高NA预测、CAR/MOR历史采用及DSA潜在性均保留原范围；中介层分类非载板同义，视图不替代身份裁定。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-B569E06E885DA787, SC-EV-9393F2354C64C727, SC-EV-5A701F864F4A7C10, SC-EV-8647894434AD8431, SC-EV-6931BFF731D8EB70, SC-EV-2CCA00E79D91DD12, SC-EV-B8DFBCC7175C23E6, SC-EV-55BA223EDE3A8F9F, SC-EV-34A6DFF0912F7884

**A/B RECONCILIATION**

- frozen status：A_B_SUBSTANTIVE_AGREEMENT
- 实质分歧：无；措辞、附注或不改变风险路由的置信度差异不改原冻结一致结论。

**EVIDENCE SUMMARY**

- Supporting facts：下列有来源的节选支持本项讨论的对象/命题；支持范围及未解决条件已在上方 A/B reason 中逐项说明。
- SC-EV-2CCA00E79D91DD12 / SC-PHYS-318D85A127B5B6DF / PDF p.17 / EUV Resist Materials / printed p.12；excerpt SHA256=`bc095b935738e34224f2f6e6414ede5e7910cf5ebec73265c08f007fc60c14aa`。
  > Currently, the EUV used in manufacturing is at 0.33NA and chemically amplified materials are in use for most EUV levels in production and metal oxide resists are used for some memory levels.
- SC-EV-34A6DFF0912F7884 / SC-PHYS-318D85A127B5B6DF / PDF p.21 / Packaging Lithography / printed p.16；excerpt SHA256=`45c78889be7aa2eb01dfd36255dc02d7e151432ffaf12cb6bd126a2593ea447b`。
  > This roadmap focuses on two types of interposer products. 1) Silicon interposers and silicon bridge interposers—This type uses fine re-distribution layers (RDLs) on silicon substrate formed by BEOL processes for fine pitch interconnections. 2) Organic interposers and RDL interposers—This type has RDLs only in organic layers for die-to-die interconnections.
- SC-EV-55BA223EDE3A8F9F / SC-PHYS-318D85A127B5B6DF / PDF p.21 / Packaging Lithography / printed p.16；excerpt SHA256=`9ac08ea2ffa05a5d23f978a2abc0efadf8673d327b374759bd424f32b7e760c9`。
  > Interposers are defined as intermediate substrates to realize interconnections between multiple dies and or to transform pitches between dice and a package substrate.
- SC-EV-5A701F864F4A7C10 / SC-PHYS-87B4665C30781057 / PDF p.3 / Photoresist coating / printed p.NOT_KNOWN_OR_UNNUMBERED；excerpt SHA256=`84bcee264567f16580c6ce836ec8196d35f33a68fb4e58e4d03d437f28587b07`。
  > The wafer is then covered with a light-sensitive coating called 'photoresist', or 'resist' for short. There are two types of resist: positive and negative.
- SC-EV-6931BFF731D8EB70 / SC-PHYS-318D85A127B5B6DF / PDF p.6 / Executive Summary / high-NA EUV / printed p.1；excerpt SHA256=`bb45531be695d54a8ecbebbddd925b87bcee72414544a2109989fd496ef66f88`。
  > EUV exposure tools with a numerical aperture (NA) of 0.55 started being delivered to customers at the end of 2023. They are now in use at multiple sites and multiple customers. First production use of such tools is projected for 2027.
- SC-EV-8647894434AD8431 / SC-PHYS-87B4665C30781057 / PDF p.3 / Photoresist coating / printed p.NOT_KNOWN_OR_UNNUMBERED；excerpt SHA256=`b691a92ed2feb5169823c356cff9e0c055521de1fac952671ab38f481da43a6b`。
  > With positive resist, the areas exposed to ultraviolet light change their structure and are made more soluble – ready for etching and deposition. The opposite is true for negative resist, where areas hit by light polymerize, meaning they become stronger and more difficult to dissolve.
- SC-EV-9393F2354C64C727 / SC-PHYS-B33C40EBCB5756F7 / PDF p.22 / Materials / printed p.22；excerpt SHA256=`def2d7634fa4482f5819e198a1df17516c435020372e9c614ece45c4d72a317b`。
  > Photomask: A plate covered with patterns used in the lithography process. The patterns consist of opaque and clear areas that prevent or allow light through.
- SC-EV-B569E06E885DA787 / SC-PHYS-B33C40EBCB5756F7 / PDF p.22 / Materials / printed p.22；excerpt SHA256=`1a71c29703324c17eb2fceb7db5e6ab4eca23efc24c6f283384d56f8117883b4`。
  > Photoresist: A special material that undergoes a chemical reaction upon exposure to light. Silicon wafers are covered with a photoresist layer, which is imprinted with the patterns contained in the photomask during the lithography process.
- SC-EV-B8DFBCC7175C23E6 / SC-PHYS-318D85A127B5B6DF / PDF p.20 / Patterning alternatives / DSA / printed p.15；excerpt SHA256=`cc3617267c9c48e986aa9bfdb48b535c64efabd62b87d490268d1ae018606a40`。
  > DSA (directed self-assembly) pattern rectification is potentially a way to get rid of stochastic defects and reduce LER while exposing at a relatively low EUV dose.
- Conflicting evidence：冻结 A/B 未报告本限定范围内的未解决实质证据冲突；不等于完整文献已穷尽。

- **SYSTEM_RECOMMENDED_DECISION** = KEEP_AS_BASELINE_CANDIDATE
推荐理由（非人工裁决）：双方仅支持保留这份有来源的基线候选；建议采纳候选文本，保留原不确定性。此选项映射原生 ACCEPT，仅用于基线交接，绝不包含 Official View 激活。

HUMAN_USER_DECISION = [PENDING]

OPTIONS:

- [ ] KEEP_AS_BASELINE_CANDIDATE（原生 ACCEPT；不激活官方 View）
- [ ] DEFER
- [ ] REJECT

---

<a id="sc-bv-0005"></a>
### 005 · SC-BV-0005 · 存储器分类与历史架构

- **ITEM_NUMBER** = 5
- **ITEM_ID** = SC-BV-0005
- **OBJECT_TYPE** = baseline_views
- **DOMAIN** = semiconductor
- **CURRENT_NATIVE_OPERATION** = UNDECIDED（没有已填写的人类原生决定）
- **CURRENT_STATUS** = REVIEW
- **WHY_IN_HUMAN_PACKET** = VIEW_ACTIVATION_REQUIRES_SEPARATE_GOVERNANCE
- **RISK_RULES** = 基线视图独立治理必审；R02–R14无TRUE/必要UNKNOWN命中
- **MANDATORY_TRIGGER** = VIEW_ACTIVATION_REQUIRES_SEPARATE_GOVERNANCE
- **SAMPLE_STATUS** = NOT_SAMPLED
- **SAMPLED_FOR_QUALITY_CONTROL** = false

- **SOURCE_ID / SOURCE_NAME** = SC-PHYS-49A1D3B42E458985 / SRC_96EC545507C25F9F / 2024 IRDS — More Moore
Source provenance：IEEE International Roadmap for Devices and Systems (IRDS)；publication=；edition=2024；as_of=2024；source SHA256=`49a1d3b42e45898555490e602170876e22d1ccf8d7c17711e436d8db36322fa6`。
- **SOURCE_ID / SOURCE_NAME** = SC-PHYS-54CABB8879E180A7 / SRC_0C4EF3703421D29B / 2020 IRDS — Packaging Integration
Source provenance：IEEE International Roadmap for Devices and Systems (IRDS)；publication=；edition=2020；as_of=2020；source SHA256=`54cabb8879e180a7a0363e8964cb2d28735eff03ecee6a45905cd54f06eae5e2`。
- **SOURCE_ID / SOURCE_NAME** = SC-PHYS-B33C40EBCB5756F7 / SRC_1DD38DEB69830E97 / Strengthening the Global Semiconductor Supply Chain in an Uncertain Era
Source provenance：Semiconductor Industry Association (SIA) / Boston Consulting Group (BCG)；publication=2021-04；edition=；as_of=2021-04；source SHA256=`b33c40ebcb5756f76e887ba2664f97736252e68ba7bfbedc2d628ce2d7cbc08d`。

**CANDIDATE_SUMMARY**

- 不确定性：SRAM、EEPROM未在本轮候选化；DRAM不是新增Server DRAM别名；2020性能数字未扩展为2026事实。
- 核心结论：非易失性存储分为Flash与非电荷存储体系；NOR/NAND属于Flash类别，但NAND身份历史隔离仍然有效。；FeRAM、MRAM、PCRAM、ReRAM在该IRDS中作为emerging memories讨论；不得把研发语态泛化为当前量产。；DRAM是通用存储器对象，不自动等同现有Server DRAM或HBM；2020 IRDS的HBM堆叠使用TSV传输die间数据。
- 概述：存储器分类与历史架构
- 状态：CANDIDATE_HANDOFF_ONLY
- 节点：SC-CN-0009
- Planned native target：NODE_CD6598B7D56BCC1A → SC-CN-0009 / Semiconductor Memory / Segment；这是候选映射，不是已存在或获批准的目录对象。
- Candidate target：SC-CN-0009 = Semiconductor Memory；type=Segment；frozen status=CREATE；仍须目标自身授权。

**AI REVIEW A**

- recommendation：ACCEPT_WITH_REVIEW_NOTE；native_decision：ACCEPT
- proposed operation / canonical target：ACCEPT；目标: SC-CN-0009 [Semiconductor Memory]；范围/说明: CANDIDATE_HANDOFF_ONLY; source-scoped cross-year technical baseline; no official activation
- confidence：MEDIUM
- reason：IRDS 分类与 emerging 语态保留，HBM-TSV 关系片段足以支持使用命题；DRAM 未展开全称、NAND 隔离仍保留，不把宽窄对象并为一体。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-288A875770100378, SC-EV-02E262518094E12D, SC-EV-9F7D3244A0780DEA, SC-EV-EFC0887512104389, SC-EV-B87D40867DB6A731

**AI REVIEW B**

- recommendation：ACCEPT_WITH_REVIEW_NOTE；native_decision：ACCEPT
- proposed operation / canonical target：ACCEPT；目标: SC-CN-0009 [Semiconductor Memory]；范围/说明: CANDIDATE_HANDOFF_ONLY; 存储器分类与历史架构; no official activation
- confidence：MEDIUM
- reason：Flash及非电荷存储分类与2020 HBM架构有对应证据；NAND隔离和DRAM宽窄边界明确保留，不把历史数据当当前生产结论。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-288A875770100378, SC-EV-02E262518094E12D, SC-EV-9F7D3244A0780DEA, SC-EV-EFC0887512104389, SC-EV-B87D40867DB6A731

**A/B RECONCILIATION**

- frozen status：A_B_SUBSTANTIVE_AGREEMENT
- 实质分歧：无；措辞、附注或不改变风险路由的置信度差异不改原冻结一致结论。

**EVIDENCE SUMMARY**

- Supporting facts：下列有来源的节选支持本项讨论的对象/命题；支持范围及未解决条件已在上方 A/B reason 中逐项说明。
- SC-EV-02E262518094E12D / SC-PHYS-49A1D3B42E458985 / PDF p.29 / 5.3 Emerging Memories / printed p.24；excerpt SHA256=`192798edc20a9c38bce046badc29ae4d3fa27b103dbb302fcf164428f2da7377`。
  > several non-conventional non-volatile memories that are not based on charge storage, so-called resistive or capacitive memories (ferroelectric or FeRAM, magnetic or MRAM, phase-change or PCRAM, and resistive or ReRAM), are being developed and form the category often called “emerging” memories.
- SC-EV-288A875770100378 / SC-PHYS-49A1D3B42E458985 / PDF p.27 / 5 Nonvolatile Memory / printed p.22；excerpt SHA256=`0d6eee3a3851d1bf15c3869444bf496d00cde00a9ff7f0fedfae6be103233f5a`。
  > Nonvolatile memory may be divided into two large categories—Flash memories (NAND Flash and NOR Flash), and non-charge-based-storage memories.
- SC-EV-9F7D3244A0780DEA / SC-PHYS-B33C40EBCB5756F7 / PDF p.9 / Memory / printed p.9；excerpt SHA256=`3e0f10608491e28b4ca65b393efba69601bbd0ab43166ecfceffb1f812be69b2`。
  > DRAM is used to store the data or program code needed by a computer processor to function.
- SC-EV-B87D40867DB6A731 / SC-PHYS-54CABB8879E180A7 / PDF p.16 / 3D Stacks / HBM / printed p.10；excerpt SHA256=`08809a2754f81176219a810708799c3dd5af455ee806a05714afa9da3102dcba`。
  > Because of the large array of TSVs available in HBM stacks to transfer data between individual die (e.g., a controller at the base topped by 4-8 DRAM die)
- SC-EV-EFC0887512104389 / SC-PHYS-54CABB8879E180A7 / PDF p.16 / 3D Stacks / HBM / printed p.10；excerpt SHA256=`d9cddb60890e78a2e295a82cfaaf5bfcaa51109c055e8b64bf17ccb2d28667f4`。
  > Under these conditions new high bandwidth memories (HBM) have been optimized for 3D die stacking (Figure PI-6).
- Conflicting evidence：冻结 A/B 未报告本限定范围内的未解决实质证据冲突；不等于完整文献已穷尽。

- **SYSTEM_RECOMMENDED_DECISION** = KEEP_AS_BASELINE_CANDIDATE
推荐理由（非人工裁决）：双方仅支持保留这份有来源的基线候选；建议采纳候选文本，保留原不确定性。此选项映射原生 ACCEPT，仅用于基线交接，绝不包含 Official View 激活。

HUMAN_USER_DECISION = [PENDING]

OPTIONS:

- [ ] KEEP_AS_BASELINE_CANDIDATE（原生 ACCEPT；不激活官方 View）
- [ ] DEFER
- [ ] REJECT

---

<a id="sc-bv-0006"></a>
### 006 · SC-BV-0006 · 计量、检测与良率反馈

- **ITEM_NUMBER** = 6
- **ITEM_ID** = SC-BV-0006
- **OBJECT_TYPE** = baseline_views
- **DOMAIN** = semiconductor
- **CURRENT_NATIVE_OPERATION** = UNDECIDED（没有已填写的人类原生决定）
- **CURRENT_STATUS** = REVIEW
- **WHY_IN_HUMAN_PACKET** = VIEW_ACTIVATION_REQUIRES_SEPARATE_GOVERNANCE
- **RISK_RULES** = 基线视图独立治理必审；R02–R14无TRUE/必要UNKNOWN命中
- **MANDATORY_TRIGGER** = VIEW_ACTIVATION_REQUIRES_SEPARATE_GOVERNANCE
- **SAMPLE_STATUS** = NOT_SAMPLED
- **SAMPLED_FOR_QUALITY_CONTROL** = false

- **SOURCE_ID / SOURCE_NAME** = SC-PHYS-AA294FCF8FEDE75B / SRC_08CC764E9C0DCB61 / 2025 IRDS — Yield Enhancement and Advanced Manufacturing & Contamination Control
Source provenance：IEEE International Roadmap for Devices and Systems (IRDS)；publication=；edition=2025；as_of=2025；source SHA256=`aa294fcf8fede75be6e2c23c6ec75a6f3504538dceb87eb51edda0134526b34b`。
- **SOURCE_ID / SOURCE_NAME** = SC-PHYS-AEDD7CB34D12EF15 / SRC_ECAE5FF71F5DE095 / 2024 IRDS — Metrology
Source provenance：IEEE International Roadmap for Devices and Systems (IRDS)；publication=；edition=2024；as_of=2024；source SHA256=`aedd7cb34d12ef15b799ed9a0f6326840a4551ddc7c6600732c6ae82ab6e93b6`。

**CANDIDATE_SUMMARY**

- 不确定性：具体工具分类与生产检出能力未全面覆盖；SECC同文命名差异进入review。
- 核心结论：计量范围包括CD、套刻、3D/HAR、材料及互连测量；方法与仪器不是同一类型。；Hybrid Metrology指互补分析方法的组合，不是Hybrid Bonding。；传统良率管理以inline inspection建立缺陷反馈并关联yield/test fails；良率变化不能只归因单一污染项。；UPW可作为末道清洗输入，同时也可能是污染来源；材料在不同上下文的角色应分列。
- 概述：计量、检测与良率反馈
- 状态：CANDIDATE_HANDOFF_ONLY
- 节点：SC-CN-0115
- Candidate target：SC-CN-0115 = Semiconductor Metrology；type=Technology；frozen status=REVIEW；仍须目标自身授权。

**AI REVIEW A**

- recommendation：ACCEPT_WITH_REVIEW_NOTE；native_decision：ACCEPT
- proposed operation / canonical target：ACCEPT；目标: SC-CN-0115 [Semiconductor Metrology]；范围/说明: CANDIDATE_HANDOFF_ONLY; source-scoped cross-year technical baseline; no official activation
- confidence：MEDIUM
- reason：计量范围、互补测量策略、良率多因素及 UPW 双重角色各有支持；与 Hybrid Bonding/仪器类型分离，目标为待建立 0115，无既有视图覆盖。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-4AAF8C92F8CF20F0, SC-EV-636FA1109B62DEE2, SC-EV-6C7601C6EFF1962D, SC-EV-ACA3759FAA03DC4E, SC-EV-D5DC766A624FE286

**AI REVIEW B**

- recommendation：ACCEPT_WITH_REVIEW_NOTE；native_decision：ACCEPT
- proposed operation / canonical target：ACCEPT；目标: SC-CN-0115 [Semiconductor Metrology]；范围/说明: CANDIDATE_HANDOFF_ONLY; 计量、检测与良率反馈; no official activation
- confidence：MEDIUM
- reason：CD/overlay范围、互补计量策略、inline反馈及UPW两种角色均有证据；未单因归责良率，目标为SC-CN-0115候选，正式节点/视图仍待授权。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-4AAF8C92F8CF20F0, SC-EV-636FA1109B62DEE2, SC-EV-6C7601C6EFF1962D, SC-EV-ACA3759FAA03DC4E, SC-EV-D5DC766A624FE286

**A/B RECONCILIATION**

- frozen status：A_B_SUBSTANTIVE_AGREEMENT
- 实质分歧：无；措辞、附注或不改变风险路由的置信度差异不改原冻结一致结论。

**EVIDENCE SUMMARY**

- Supporting facts：下列有来源的节选支持本项讨论的对象/命题；支持范围及未解决条件已在上方 A/B reason 中逐项说明。
- SC-EV-4AAF8C92F8CF20F0 / SC-PHYS-AEDD7CB34D12EF15 / PDF p.10 / 2 Scope of Report / printed p.5；excerpt SHA256=`af82e9c1a8a297ea881710d07f9ed44ac480b56343dc94fc86d048319549176d`。
  > The scope includes metrology for critical dimensions (CDs), microscopy for 3D and high aspect ratio (HAR) pattern measurements, overlay measurements, lithography metrology, front-end processes metrology, on-chip interconnect metrology, inter- and intra-die interconnect metrology, materials characterization, metrology for emerging materials and devices, reference materials, and outside systems connectivity needs and challenges.
- SC-EV-636FA1109B62DEE2 / SC-PHYS-AEDD7CB34D12EF15 / PDF p.15 / Microscopy / Hybrid Metrology / printed p.10；excerpt SHA256=`5322859303bd3982bac67714fbe3b94f761c8335692c65ee9bc0c001da60cad9`。
  > Hybrid or combined metrology is an important measurement strategy for extending the applicability of current microscopes and other metrology tools [11]. Statistical and combinatorial methods have been used to allow complementary analysis techniques to be applied to the same area, utilizing the best measurement attributes of each technique [12].
- SC-EV-6C7601C6EFF1962D / SC-PHYS-AA294FCF8FEDE75B / PDF p.28 / Characterization, Inspection and Analysis / printed p.23；excerpt SHA256=`3b678cebf3c40bfae6c9d3550275d484867c743db9d0b520382011687103deba`。
  > Traditional yield management focuses on adequate inline inspection capabilities to detect and control all relevant defect types to set up short feedback loops as well as enable correlation to yield and test fails.
- SC-EV-ACA3759FAA03DC4E / SC-PHYS-AA294FCF8FEDE75B / PDF p.6 / 1 Introduction / printed p.1；excerpt SHA256=`a9094fe506388f7963abe5e1b6b8647c8fbd843a3a2f8cd39bd63d864672fe70`。
  > During the manufacturing of integrated circuits yield loss is caused, for example, by defects, faults, process variations, and design.
- SC-EV-D5DC766A624FE286 / SC-PHYS-AA294FCF8FEDE75B / PDF p.10 / Yield / contamination and reliability / printed p.5；excerpt SHA256=`ff768898a46776020b696413561ea02021ef29b2b95effb5f042d0f6ab7857e1`。
  > Typical sources of contamination are from airborne sources and ultrapure water used in last cleaning steps of the Si channel before oxide and high-k dielectric (e.g. HfO2) deposition.
- Conflicting evidence：冻结 A/B 未报告本限定范围内的未解决实质证据冲突；不等于完整文献已穷尽。

- **SYSTEM_RECOMMENDED_DECISION** = KEEP_AS_BASELINE_CANDIDATE
推荐理由（非人工裁决）：双方仅支持保留这份有来源的基线候选；建议采纳候选文本，保留原不确定性。此选项映射原生 ACCEPT，仅用于基线交接，绝不包含 Official View 激活。

HUMAN_USER_DECISION = [PENDING]

OPTIONS:

- [ ] KEEP_AS_BASELINE_CANDIDATE（原生 ACCEPT；不激活官方 View）
- [ ] DEFER
- [ ] REJECT

---

<a id="sc-bv-0007"></a>
### 007 · SC-BV-0007 · 工厂集成与制造控制

- **ITEM_NUMBER** = 7
- **ITEM_ID** = SC-BV-0007
- **OBJECT_TYPE** = baseline_views
- **DOMAIN** = semiconductor
- **CURRENT_NATIVE_OPERATION** = UNDECIDED（没有已填写的人类原生决定）
- **CURRENT_STATUS** = REVIEW
- **WHY_IN_HUMAN_PACKET** = VIEW_ACTIVATION_REQUIRES_SEPARATE_GOVERNANCE
- **RISK_RULES** = 基线视图独立治理必审；R02–R14无TRUE/必要UNKNOWN命中
- **MANDATORY_TRIGGER** = VIEW_ACTIVATION_REQUIRES_SEPARATE_GOVERNANCE
- **SAMPLE_STATUS** = NOT_SAMPLED
- **SAMPLED_FOR_QUALITY_CONTROL** = false

- **SOURCE_ID / SOURCE_NAME** = SC-PHYS-4FA7140313FB3AF8 / SRC_15959FA40D6E85A4 / 2023 IRDS — Factory Integration
Source provenance：IEEE International Roadmap for Devices and Systems (IRDS)；publication=；edition=2023；as_of=2023；source SHA256=`4fa7140313fb3af883127c329599c4d8e6f4b9abfbe0976f4e8102ebe8c2587d`。
- **SOURCE_ID / SOURCE_NAME** = SC-PHYS-C5B6DC633E156218 / SRC_AC29CFEE56F74F5B / Testimony of the Semiconductor Industry Association before the Senate Committee on Environment & Public Works (March 4, 2026)
Source provenance：Semiconductor Industry Association (SIA)；publication=2026-03-04；edition=；as_of=2026-03-04；source SHA256=`c5b6dc633e156218eb950f2dee88f43fbdcc4fc1744a5924f12b977f5cb7df71`。

**CANDIDATE_SUMMARY**

- 不确定性：AMHS/FICS系统类型与边界待审；2023路线图无法支持2026工厂当前渗透率。
- 核心结论：IRDS Factory Integration的scope同时涉及前后端微电子制造，不是某一家fab的已部署系统清单。；FICS覆盖硬件/软件、制造执行、决策支持、调度、设备与搬运控制及过程控制。；AMHS与SPC相关表述含需求和未来普及方向，应保留路线图时态。；设施层的化学品输送、排气治理、废水处理可形成有界技术对象；不把政策安全承诺混入。
- 概述：工厂集成与制造控制
- 状态：CANDIDATE_HANDOFF_ONLY
- 节点：SC-CN-0123
- Planned native target：NODE_0087FF33E12373CF → SC-CN-0123 / Factory Integration / Technology；这是候选映射，不是已存在或获批准的目录对象。
- Candidate target：SC-CN-0123 = Factory Integration；type=Technology；frozen status=CREATE；仍须目标自身授权。

**AI REVIEW A**

- recommendation：ACCEPT_WITH_REVIEW_NOTE；native_decision：ACCEPT
- proposed operation / canonical target：ACCEPT；目标: SC-CN-0123 [Factory Integration]；范围/说明: CANDIDATE_HANDOFF_ONLY; source-scoped cross-year technical baseline; no official activation
- confidence：MEDIUM
- reason：FI/FICS 的报告范围和 AMHS/SPC 的需求/将来时被保留，设施仅为技术对象；不声称 2026 实际渗透率，未解决系统别名仍保留治理。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-974C6AC2C5C6BE20, SC-EV-05E04AAA8644BBA6, SC-EV-60435D5F04954369, SC-EV-5AD108049A3B22F4, SC-EV-DEEF5988AF3E27FE, SC-EV-6D361D680E26A1C9, SC-EV-37D8E37F58E96AEA

**AI REVIEW B**

- recommendation：ACCEPT_WITH_REVIEW_NOTE；native_decision：ACCEPT
- proposed operation / canonical target：ACCEPT；目标: SC-CN-0123 [Factory Integration]；范围/说明: CANDIDATE_HANDOFF_ONLY; 工厂集成与制造控制; no official activation
- confidence：MEDIUM
- reason：FI/FICS系统范围及AMHS/SPC未来要求与原文相符，设施技术另有来源支持；AMHS未完成身份定义已披露，不声称2026渗透率。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-974C6AC2C5C6BE20, SC-EV-05E04AAA8644BBA6, SC-EV-60435D5F04954369, SC-EV-5AD108049A3B22F4, SC-EV-DEEF5988AF3E27FE, SC-EV-6D361D680E26A1C9, SC-EV-37D8E37F58E96AEA

**A/B RECONCILIATION**

- frozen status：A_B_SUBSTANTIVE_AGREEMENT
- 实质分歧：无；措辞、附注或不改变风险路由的置信度差异不改原冻结一致结论。

**EVIDENCE SUMMARY**

- Supporting facts：下列有来源的节选支持本项讨论的对象/命题；支持范围及未解决条件已在上方 A/B reason 中逐项说明。
- SC-EV-05E04AAA8644BBA6 / SC-PHYS-4FA7140313FB3AF8 / PDF p.27 / 5.5.1 Factory Information and Control Systems / Scope / printed p.21；excerpt SHA256=`1d5827116248957d54ed15cc666aefad50ee86780bb816df369b32498e9685c6`。
  > The scope of FICS includes computer hardware and software, manufacturing execution, decision support systems, factory scheduling, control of equipment and material handling systems, and process control.
- SC-EV-37D8E37F58E96AEA / SC-PHYS-C5B6DC633E156218 / PDF p.8 / III.B / Technical waste treatment description only / printed p.8；excerpt SHA256=`43d849e0db0f62b53a464fa4387fb84b593f92cd78c51d864d17a530e26421a0`。
  > Semiconductor fabs control environmental releases by implementing strict controls including wastewater collection and treatment, waste management systems, and air emissions abatement.
- SC-EV-5AD108049A3B22F4 / SC-PHYS-4FA7140313FB3AF8 / PDF p.28 / 5.5 Factory Information and Control Systems / Process Control / printed p.22；excerpt SHA256=`63e83ee232bada758173e67f3cd9d0bba13eb290c674e7450ca20b1922b8447d`。
  > including R2R control, fault detection (FD), fault classification (FC), fault prediction (FP) and statistical process control (SPC) will become more pervasive and an integral part of FICS solutions.
- SC-EV-60435D5F04954369 / SC-PHYS-4FA7140313FB3AF8 / PDF p.27 / 5.4 Material Handling / printed p.21；excerpt SHA256=`c88951455ed96a5adaa7e8bd50efc2b4b46c4eb7a0ee7f787df729b669f69e81`。
  > AMHS must have acceptable return on investment (ROI) and must interface directly with all inline (i.e., used in normal process flow) production and metrology equipment. AMHS must deliver material in a timely fashion to support critical equipment in order to minimize wait time waste.
- SC-EV-6D361D680E26A1C9 / SC-PHYS-C5B6DC633E156218 / PDF p.8 / III.B / Technical exhaust/abatement description only / printed p.8；excerpt SHA256=`9770f17dcba2eb09d1b826f5aab4d96641e56bd9078e17f8ef490b11c6324970`。
  > Fab exhaust systems remove chemical vapors and heat from process tools. Acids and bases are routed to centralized scrubbers, while volatile organic compounds are abated via centralized thermal, catalytic, or plasma oxidizers which may be equipped to concentrate contaminants prior to abatement.
- SC-EV-974C6AC2C5C6BE20 / SC-PHYS-4FA7140313FB3AF8 / PDF p.13 / 2.1 Introduction / Scope of Report / printed p.7；excerpt SHA256=`5781c6a6304cfd68ff6ef3799bd16be6b2f824042abe3c2e8d91f4220903e8c1`。
  > FI’s scope is microelectronic manufacturing or fabrication in front-end and back-end.
- SC-EV-DEEF5988AF3E27FE / SC-PHYS-C5B6DC633E156218 / PDF p.8 / III.B / Technical chemical-delivery description only / printed p.8；excerpt SHA256=`5d41c8865eaf1f177831a22a1560a8c6aa44cb77e7e95090786debf71b02d615`。
  > Chemicals are stored and delivered into the manufacturing area using automated chemical delivery systems that prevent personnel exposure and ensure limited human interface.
- Conflicting evidence：冻结 A/B 未报告本限定范围内的未解决实质证据冲突；不等于完整文献已穷尽。

- **SYSTEM_RECOMMENDED_DECISION** = KEEP_AS_BASELINE_CANDIDATE
推荐理由（非人工裁决）：双方仅支持保留这份有来源的基线候选；建议采纳候选文本，保留原不确定性。此选项映射原生 ACCEPT，仅用于基线交接，绝不包含 Official View 激活。

HUMAN_USER_DECISION = [PENDING]

OPTIONS:

- [ ] KEEP_AS_BASELINE_CANDIDATE（原生 ACCEPT；不激活官方 View）
- [ ] DEFER
- [ ] REJECT

---

<a id="sc-bv-0008"></a>
### 008 · SC-BV-0008 · 先进封装与跨域既有身份

- **ITEM_NUMBER** = 8
- **ITEM_ID** = SC-BV-0008
- **OBJECT_TYPE** = baseline_views
- **DOMAIN** = semiconductor
- **CURRENT_NATIVE_OPERATION** = UNDECIDED（没有已填写的人类原生决定）
- **CURRENT_STATUS** = REVIEW
- **WHY_IN_HUMAN_PACKET** = VIEW_ACTIVATION_REQUIRES_SEPARATE_GOVERNANCE
- **RISK_RULES** = 基线视图独立治理必审；R02–R14无TRUE/必要UNKNOWN命中
- **MANDATORY_TRIGGER** = VIEW_ACTIVATION_REQUIRES_SEPARATE_GOVERNANCE
- **SAMPLE_STATUS** = NOT_SAMPLED
- **SAMPLED_FOR_QUALITY_CONTROL** = false

- **SOURCE_ID / SOURCE_NAME** = SC-PHYS-2E34AF6DD70E8C2C / SRC_944238EE8104A292 / 2025 HIR — Materials and Interfaces for Advanced Packaging, Rev 0.9
Source provenance：IEEE Electronics Packaging Society — Heterogeneous Integration Roadmap；publication=2026-03；edition=2025 Rev 0.9；as_of=2026-03；source SHA256=`2e34af6dd70e8c2c5de2aaabec15837693d1322abc0bb5820475188cd028a3f2`。
- **SOURCE_ID / SOURCE_NAME** = SC-PHYS-3FB7AE4AD972AA2B / F018b / TSMC 2025 Annual Report
Source provenance：TSMC；publication=；edition=；as_of=2025；source SHA256=`3fb7ae4ad972aa2bc6e45bb36635152ad89d52f4a7165f389bcb94eeb54a6abd`。
- **SOURCE_ID / SOURCE_NAME** = SC-PHYS-86EB13C30D0C5406 / F017 / UCIe 3.0 Specification White Paper
Source provenance：UCIe Consortium；publication=；edition=；as_of=；source SHA256=`86eb13c30d0c5406b647a50107bc5c82ddfa5b4cf7aa36ab959cbe50d8a1ef19`。
- **SOURCE_ID / SOURCE_NAME** = SC-PHYS-911B414A2AF8F41B / F018 / TSMC Business Overview 2024
Source provenance：TSMC；publication=；edition=；as_of=2024；source SHA256=`911b414a2af8f41b91b3a3e3afbccd300582d380748959541b7c60ff68e5bb92`。

**CANDIDATE_SUMMARY**

- 不确定性：3DFabric伞形品牌、物理chiplet与Chiplet Architecture、通用载板/PIC边界继续审查；基线不覆盖当前市场状态。
- 核心结论：CoWoS-S/R/L、SoIC复用本次Context Pack的现有身份；TSMC文献支持的家族定义不自动成为通用行业taxonomy。；Hybrid Bonding结合金属—金属与介质—介质界面；Underfill是encapsulant类别的一部分，不与全部EMC材料自动等同。；2024与2025报告中的CoWoS-L历史状态，以及更大reticle产品的2026预期分别保留。；UCIe 3.0白皮书支持版本能力描述，不支持凭空生成规范条款或部署状态。；RDL介质与热界面材料存在电学/热学/机械协同约束；图中的玻璃与金刚石候选不因此解除历史治理。
- 概述：先进封装与跨域既有身份
- 状态：CANDIDATE_HANDOFF_ONLY
- 节点：NODE_20260817_4452D283
- Canonical state：NODE_20260817_4452D283 = Advanced Packaging；type=Segment；status=active。

**AI REVIEW A**

- recommendation：ACCEPT_WITH_REVIEW_NOTE；native_decision：ACCEPT
- proposed operation / canonical target：ACCEPT；目标: NODE_20260817_4452D283 [Advanced Packaging]；范围/说明: CANDIDATE_HANDOFF_ONLY; source-scoped cross-year technical baseline; no official activation
- confidence：MEDIUM
- reason：既有 CoWoS/SoIC/UCIe 核心复用正确，历史投产与新尺寸预测区分；图1和 TIM 条件支持协同约束，玻璃/金刚石治理未解除，且无现有 Advanced Packaging 官方视图被覆盖。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-A5D5D8057F31DBE3, SC-EV-BE1EFC0405668731, SC-EV-444CA37AE04D85CF, SC-EV-2BD04E0EEBBAD758, SC-EV-98C39E1AB621ADE6, SC-EV-25E1F286A1FC489C, SC-EV-E2297FB1F53EF6D7, SC-EV-710553EE46C8AF97, SC-EV-6142D3B803848285, SC-EV-56A84BBF8CA0648F, SC-EV-3032F6F70575E525, SC-EV-0649533B13177719, SC-EV-7FF5E762CAC4DB05, SC-EV-6C7A98013D4B2FCF

**AI REVIEW B**

- recommendation：ACCEPT_WITH_REVIEW_NOTE；native_decision：ACCEPT
- proposed operation / canonical target：ACCEPT；目标: NODE_20260817_4452D283 [Advanced Packaging]；范围/说明: CANDIDATE_HANDOFF_ONLY; 先进封装与跨域既有身份; no official activation
- confidence：MEDIUM
- reason：CoWoS家族/SoIC既有ID、2024历史与2026产品预期分别保留；HIR图1及TIM约束支持技术基线，UCIe白皮书不冒充规范或部署证明，历史隔离不解除。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-A5D5D8057F31DBE3, SC-EV-BE1EFC0405668731, SC-EV-444CA37AE04D85CF, SC-EV-2BD04E0EEBBAD758, SC-EV-98C39E1AB621ADE6, SC-EV-25E1F286A1FC489C, SC-EV-E2297FB1F53EF6D7, SC-EV-710553EE46C8AF97, SC-EV-6142D3B803848285, SC-EV-56A84BBF8CA0648F, SC-EV-3032F6F70575E525, SC-EV-0649533B13177719, SC-EV-7FF5E762CAC4DB05, SC-EV-6C7A98013D4B2FCF

**A/B RECONCILIATION**

- frozen status：A_B_SUBSTANTIVE_AGREEMENT
- 实质分歧：无；措辞、附注或不改变风险路由的置信度差异不改原冻结一致结论。

**EVIDENCE SUMMARY**

- Supporting facts：下列有来源的节选支持本项讨论的对象/命题；支持范围及未解决条件已在上方 A/B reason 中逐项说明。
- SC-EV-0649533B13177719 / SC-PHYS-2E34AF6DD70E8C2C / PDF p.17 / 2.3.1.1 Package Cooling / printed p.17；excerpt SHA256=`33478c15ac3fd1ffb0703de9cfc44926ea9b6be20a3d0ee295b060bbc88f2da3`。
  > The thermal interface materials (TIM1 & TIM2) need to be chosen for better thermal conductivity while meeting bond line thickness (BLT), mechanical integrity, integrability, reliability, contact coverage, and non-uniformity.
- SC-EV-25E1F286A1FC489C / SC-PHYS-2E34AF6DD70E8C2C / PDF p.25 / 2.4.1 Materials for Reliability / printed p.25；excerpt SHA256=`0745944e06e79c14a947eca75375705e21cce1e75f0e2115d99c4237d0db400e`。
  > Encapsulant materials, including underfill and mold compounds, are vital for ensuring package reliability. They provide electrical isolation for the chip and interconnects, protect against mechanical damage and environmental contamination, and help distribute thermomechanical stresses during reliability testing and use conditions.
- SC-EV-2BD04E0EEBBAD758 / SC-PHYS-3FB7AE4AD972AA2B / PDF p.53 / TSMC 3DFabric / SoIC / printed p.102-103 (two-page spreads; obey section restriction)；excerpt SHA256=`c46bdd54287cd332e7e09cb98bd0c82bb5620c2ef13c0bbec45cabc0e4673b5c`。
  > TSMC-SoIC® Chip-on-Wafer (CoW) 3D vertical integration solution offers high-density interconnect for chiplet architecture for HPC products. 3nm system on integrated chip (SoIC) stacking technology successfully entered volume production in 2025.
- SC-EV-3032F6F70575E525 / SC-PHYS-2E34AF6DD70E8C2C / PDF p.4 / 2.1.1 Technology / Systems Focus / printed p.4；excerpt SHA256=`12a6e5cd73acc8a501d4752cb5dc538447cf15d444d925d7c0ab4eac75927856`。
  > Redistribution layer (RDL) dielectrics have become a central technology bottleneck for advanced semiconductor packaging as system performance increasingly depends on package-level interconnects rather than on-device wiring alone.
- SC-EV-444CA37AE04D85CF / SC-PHYS-3FB7AE4AD972AA2B / PDF p.53 / TSMC 3DFabric / CoWoS-L / printed p.102-103 (two-page spreads; obey section restriction)；excerpt SHA256=`c8aef7aff3d29e5522a4e84f806c18303cc6c5804edc421952a53202d3f237a1`。
  > CoWoS®-L advanced packaging service enables larger HPC products by combining Chip on Wafer on Substrate with RDL-based interposer, higher density embedded local silicon interconnect (LSI), eDTC, and the integration of diverse embedded chips.
- SC-EV-56A84BBF8CA0648F / SC-PHYS-86EB13C30D0C5406 / PDF p.3 / Support for Continuous Transmission Protocols / printed p.NOT_KNOWN_OR_UNNUMBERED；excerpt SHA256=`1637022dad6a5c7b777a7e1ed784de7eb66eb2666bb3e227fa66b66def0f06b2`。
  > UCIe 3.0 supports continuous transmission protocols by running the link at the same data rate as data generation and consumption.
- SC-EV-6142D3B803848285 / SC-PHYS-86EB13C30D0C5406 / PDF p.1 / Introduction / printed p.NOT_KNOWN_OR_UNNUMBERED；excerpt SHA256=`4ff7320b3a814e37fb8f6245aef96451e17cd71e9b37ba1265deb974ae7e62c7`。
  > UCIe has emerged as the leading standard for chiplet interconnects, providing a uniﬁed framework for communication between diverse chiplets from multiple sources.
- SC-EV-6C7A98013D4B2FCF / SC-PHYS-2E34AF6DD70E8C2C / PDF p.20 / 2.3.2 3DIC Chip Stack Materials / printed p.20；excerpt SHA256=`f0087eeaa8c597c7a7247a67a8be7f1a33bffbdb2f58350ad5c513f4fe01fb41`。
  > For BSPDN, swapping the Si handler with a high k material like SiC or diamond would need 300mm wafers that can be processed through the fab.
- SC-EV-710553EE46C8AF97 / SC-PHYS-3FB7AE4AD972AA2B / PDF p.53 / TSMC 3DFabric / CoWoS-L / printed p.102-103 (two-page spreads; obey section restriction)；excerpt SHA256=`6e6be75b6a53ee0066e5980aff0ac89b3eeb600b1dbff1be0944757afd5e4e9f`。
  > This technology entered its second year of volume production in 2025 and is currently being adopted by multiple products featuring larger reticle interposer size, which are expected to start volume production in 2026.
- SC-EV-7FF5E762CAC4DB05 / SC-PHYS-2E34AF6DD70E8C2C / PDF p.2 / Overview of key materials and interfaces / printed p.2 / Figure 1；excerpt SHA256=`97c137bbc0f7a3ffb1d3bf72d677a7edf0929eb70f89e5f546c6d94f85b46f7d`。
  > Glass Core Substrate
- SC-EV-98C39E1AB621ADE6 / SC-PHYS-2E34AF6DD70E8C2C / PDF p.12 / 2.2.3.3 Hybrid Bonding Materials and Processes / printed p.12；excerpt SHA256=`44eaf7fce089024753f93cf8d7dff7fb654689eb986237001b9629bd5587c776`。
  > Hybrid bonding combines metal–metal (typically Cu–Cu) and dielectric–dielectric (e.g., SiO₂, SiCN, polymer) interfaces, enabling simultaneous electrical and mechanical connections at sub-micron pitches.
- SC-EV-A5D5D8057F31DBE3 / SC-PHYS-3FB7AE4AD972AA2B / PDF p.53 / TSMC 3DFabric / CoWoS-S / printed p.102-103 (two-page spreads; obey section restriction)；excerpt SHA256=`1ee0e58c09585bf92677e57e8bbb17bf6f7f18b4c5754477744e11491e64746e`。
  > CoWoS® with silicon interposer (CoWoS®-S) advanced packaging service features high interconnect routing density and embedded deep trench capacitor (eDTC) and has been in volume production for several years.
- SC-EV-BE1EFC0405668731 / SC-PHYS-3FB7AE4AD972AA2B / PDF p.53 / TSMC 3DFabric / CoWoS-R / printed p.102-103 (two-page spreads; obey section restriction)；excerpt SHA256=`44ebdfbacad4f0528034996f5dd8911aa1cd61bddb0c3ca1ccaef233889f89a7`。
  > CoWoS® with redistribution layer interposer (CoWoS®-R) advanced packaging service, featuring multiple redistribution layers (RDL) to enable product design simplicity, supports larger HPC products. This technology entered its third year of volume production in 2025.
- SC-EV-E2297FB1F53EF6D7 / SC-PHYS-911B414A2AF8F41B / PDF p.9 / Technology Leadership / advanced packaging / printed p.014-017 (two-page spreads; obey section restriction)；excerpt SHA256=`095e01bf2a8ce5bf92c41bc1282afd9fcf3b50704cc16a257dbe07e3c37dff19`。
  > CoWoS®-L technology, combining Chip on Wafer on Substrate with RDL-based interposer and embedded local silicon interconnect (LSI), started volume production in 2024.
- Conflicting evidence：冻结 A/B 未报告本限定范围内的未解决实质证据冲突；不等于完整文献已穷尽。

- **SYSTEM_RECOMMENDED_DECISION** = KEEP_AS_BASELINE_CANDIDATE
推荐理由（非人工裁决）：双方仅支持保留这份有来源的基线候选；建议采纳候选文本，保留原不确定性。此选项映射原生 ACCEPT，仅用于基线交接，绝不包含 Official View 激活。

HUMAN_USER_DECISION = [PENDING]

OPTIONS:

- [ ] KEEP_AS_BASELINE_CANDIDATE（原生 ACCEPT；不激活官方 View）
- [ ] DEFER
- [ ] REJECT

---

<a id="sc-cl-0017"></a>
### 009 · SC-CL-0017 · UCIe 3.0白皮书描述fast throttle热限制协调机制。

- **ITEM_NUMBER** = 9
- **ITEM_ID** = SC-CL-0017
- **OBJECT_TYPE** = claims
- **DOMAIN** = semiconductor
- **CURRENT_NATIVE_OPERATION** = UNDECIDED（没有已填写的人类原生决定）
- **CURRENT_STATUS** = ACCEPTABLE
- **WHY_IN_HUMAN_PACKET** = R02；R03；R04；R08；REVIEWER_UNRESOLVED_HUMAN_REQUIRED
- **RISK_RULES** = R02 低或必要UNKNOWN置信度；R03 证据缺口；R04 实质命题歧义；R08 实质关系歧义
- **MANDATORY_TRIGGER** = R02；R03；R04；R08；REVIEWER_UNRESOLVED_HUMAN_REQUIRED
- **SAMPLE_STATUS** = NOT_SAMPLED
- **SAMPLED_FOR_QUALITY_CONTROL** = false

- **SOURCE_ID / SOURCE_NAME** = SC-PHYS-86EB13C30D0C5406 / F017 / UCIe 3.0 Specification White Paper
Source provenance：UCIe Consortium；publication=；edition=；as_of=；source SHA256=`86eb13c30d0c5406b647a50107bc5c82ddfa5b4cf7aa36ab959cbe50d8a1ef19`。

**CANDIDATE_SUMMARY**

- 主体：Universal Chiplet Interconnect Express
- 主体 ID：NODE_20260817_2E3D3BE2
- 命题：UCIe 3.0白皮书描述fast throttle热限制协调机制。
- 性质：fact
- 时间类别：specification_capability
- 范围：Mechanism description, not a measured deployment
- Canonical state：NODE_20260817_2E3D3BE2 = Universal Chiplet Interconnect Express；type=Standard；status=active。

**AI REVIEW A**

- recommendation：HUMAN_REQUIRED；native_decision：KEEP_NEEDS_REVIEW
- proposed operation / canonical target：KEEP_NEEDS_REVIEW；目标: NODE_20260817_2E3D3BE2 [Universal Chiplet Interconnect Express]；范围/说明: Mechanism description, not a measured deployment
- confidence：LOW
- reason：绑定段只列 fast throttle/emergency shutdown 两种机制，未说明 thermal-limit 协调对象；标题也未补足热归因，需补该语义证据。
- evidence assessment：INSUFFICIENT；Evidence IDs：SC-EV-DFE62C6B1376FB40

**AI REVIEW B**

- recommendation：HUMAN_REQUIRED；native_decision：KEEP_NEEDS_REVIEW
- proposed operation / canonical target：KEEP_NEEDS_REVIEW；目标: NODE_20260817_2E3D3BE2 [Universal Chiplet Interconnect Express]；范围/说明: Mechanism description, not a measured deployment
- confidence：LOW
- reason：摘录及标题只列fast throttle和emergency shutdown两项，未解释热限制或协调过程；中文增加热限制协调语义，需更完整的冻结证据。
- evidence assessment：INSUFFICIENT；Evidence IDs：SC-EV-DFE62C6B1376FB40

**A/B RECONCILIATION**

- frozen status：A_B_SUBSTANTIVE_AGREEMENT
- 实质分歧：无；措辞、附注或不改变风险路由的置信度差异不改原冻结一致结论。

**EVIDENCE SUMMARY**

- Supporting facts：下列有来源的节选支持本项讨论的对象/命题；支持范围及未解决条件已在上方 A/B reason 中逐项说明。
- SC-EV-DFE62C6B1376FB40 / SC-PHYS-86EB13C30D0C5406 / PDF p.5 / Fast Throttle and Emergency Shutdown / printed p.NOT_KNOWN_OR_UNNUMBERED；excerpt SHA256=`0f639162ff821535eac08ca9e6e2d7c6d8dc9a3f35650d2b6eebd068f66668cb`。
  > The solution provided in UCIe 3.0 involves two key mechanisms: fast throttle and emergency shutdown.
- Conflicting evidence / unresolved scope：上述 A/B 理由和差异列出已记录的冲突或缺口；未补造反证，也未因省略原文而解除冻结风险。

- **SYSTEM_RECOMMENDED_DECISION** = KEEP_NEEDS_REVIEW
推荐理由（非人工裁决）：双方均建议保留待审，条件或关系含义仍有缺口；优先保留来源与明确待审状态，不将其升级为无保留事实。

HUMAN_USER_DECISION = [PENDING]

OPTIONS:

- [ ] KEEP
- [ ] DROP
- [ ] KEEP_NEEDS_REVIEW

---

<a id="sc-cl-0018"></a>
### 010 · SC-CL-0018 · UCIe 3.0白皮书描述emergency shutdown热限制协调机制。

- **ITEM_NUMBER** = 10
- **ITEM_ID** = SC-CL-0018
- **OBJECT_TYPE** = claims
- **DOMAIN** = semiconductor
- **CURRENT_NATIVE_OPERATION** = UNDECIDED（没有已填写的人类原生决定）
- **CURRENT_STATUS** = ACCEPTABLE
- **WHY_IN_HUMAN_PACKET** = R02；R03；R04；R08；REVIEWER_UNRESOLVED_HUMAN_REQUIRED
- **RISK_RULES** = R02 低或必要UNKNOWN置信度；R03 证据缺口；R04 实质命题歧义；R08 实质关系歧义
- **MANDATORY_TRIGGER** = R02；R03；R04；R08；REVIEWER_UNRESOLVED_HUMAN_REQUIRED
- **SAMPLE_STATUS** = NOT_SAMPLED
- **SAMPLED_FOR_QUALITY_CONTROL** = false

- **SOURCE_ID / SOURCE_NAME** = SC-PHYS-86EB13C30D0C5406 / F017 / UCIe 3.0 Specification White Paper
Source provenance：UCIe Consortium；publication=；edition=；as_of=；source SHA256=`86eb13c30d0c5406b647a50107bc5c82ddfa5b4cf7aa36ab959cbe50d8a1ef19`。

**CANDIDATE_SUMMARY**

- 主体：Universal Chiplet Interconnect Express
- 主体 ID：NODE_20260817_2E3D3BE2
- 命题：UCIe 3.0白皮书描述emergency shutdown热限制协调机制。
- 性质：fact
- 时间类别：specification_capability
- 范围：Separate atomic mechanism; no full normative specification available
- Canonical state：NODE_20260817_2E3D3BE2 = Universal Chiplet Interconnect Express；type=Standard；status=active。

**AI REVIEW A**

- recommendation：HUMAN_REQUIRED；native_decision：KEEP_NEEDS_REVIEW
- proposed operation / canonical target：KEEP_NEEDS_REVIEW；目标: NODE_20260817_2E3D3BE2 [Universal Chiplet Interconnect Express]；范围/说明: Separate atomic mechanism; no full normative specification available
- confidence：LOW
- reason：原文确认 emergency shutdown 名称，但同段不足证明限定为热限制协调；与 fast throttle 分立正确，热语义仍需支持。
- evidence assessment：INSUFFICIENT；Evidence IDs：SC-EV-DFE62C6B1376FB40

**AI REVIEW B**

- recommendation：HUMAN_REQUIRED；native_decision：KEEP_NEEDS_REVIEW
- proposed operation / canonical target：KEEP_NEEDS_REVIEW；目标: NODE_20260817_2E3D3BE2 [Universal Chiplet Interconnect Express]；范围/说明: Separate atomic mechanism; no full normative specification available
- confidence：LOW
- reason：原文仅列emergency shutdown名称，未直接说明热限制协调机制；虽3.0版本清楚，功能目的与机制细节不足，保留待审。
- evidence assessment：INSUFFICIENT；Evidence IDs：SC-EV-DFE62C6B1376FB40

**A/B RECONCILIATION**

- frozen status：A_B_SUBSTANTIVE_AGREEMENT
- 实质分歧：无；措辞、附注或不改变风险路由的置信度差异不改原冻结一致结论。

**EVIDENCE SUMMARY**

- Supporting facts：下列有来源的节选支持本项讨论的对象/命题；支持范围及未解决条件已在上方 A/B reason 中逐项说明。
- SC-EV-DFE62C6B1376FB40 / SC-PHYS-86EB13C30D0C5406 / PDF p.5 / Fast Throttle and Emergency Shutdown / printed p.NOT_KNOWN_OR_UNNUMBERED；excerpt SHA256=`0f639162ff821535eac08ca9e6e2d7c6d8dc9a3f35650d2b6eebd068f66668cb`。
  > The solution provided in UCIe 3.0 involves two key mechanisms: fast throttle and emergency shutdown.
- Conflicting evidence / unresolved scope：上述 A/B 理由和差异列出已记录的冲突或缺口；未补造反证，也未因省略原文而解除冻结风险。

- **SYSTEM_RECOMMENDED_DECISION** = KEEP_NEEDS_REVIEW
推荐理由（非人工裁决）：双方均建议保留待审，条件或关系含义仍有缺口；优先保留来源与明确待审状态，不将其升级为无保留事实。

HUMAN_USER_DECISION = [PENDING]

OPTIONS:

- [ ] KEEP
- [ ] DROP
- [ ] KEEP_NEEDS_REVIEW

---

<a id="sc-cn-0004"></a>
### 011 · SC-CN-0004 · Integrated Circuits

- **ITEM_NUMBER** = 11
- **ITEM_ID** = SC-CN-0004
- **OBJECT_TYPE** = nodes
- **DOMAIN** = 00_industry_structure
- **CURRENT_NATIVE_OPERATION** = CREATE NODE_1D7323F4CB07233F
- **CURRENT_STATUS** = CREATE
- **WHY_IN_HUMAN_PACKET** = R07；REVIEWER_UNRESOLVED_HUMAN_REQUIRED
- **RISK_RULES** = R07 新增高影响Node
- **MANDATORY_TRIGGER** = R07；REVIEWER_UNRESOLVED_HUMAN_REQUIRED
- **SAMPLE_STATUS** = NOT_SAMPLED
- **SAMPLED_FOR_QUALITY_CONTROL** = false

- **SOURCE_ID / SOURCE_NAME** = SC-PHYS-04A42FFC3F71A42F / SRC_1640D08BDF90458F / Making Semiconductors: The Highly Complex and Global Chip Research, Design, and Manufacturing Process
Source provenance：Semiconductor Industry Association (SIA)；publication=2019；edition=；as_of=2019；source SHA256=`04a42ffc3f71a42fa9b996240618874bb7fff21404e93cdb1e7bf53318938c26`。

**CANDIDATE_SUMMARY**

- Node 类型：Product
- 名称：Integrated Circuits
- 已有身份：NODE_1D7323F4CB07233F
- 边界说明：Source支持可复用的持久研究对象，未命中现有规范名或已登记别名。
- Planned native target：NODE_1D7323F4CB07233F → SC-CN-0004 / Integrated Circuits / Product；这是候选映射，不是已存在或获批准的目录对象。

**AI REVIEW A**

- recommendation：HUMAN_REQUIRED；native_decision：CREATE
- proposed operation / canonical target：CREATE；范围/说明: IDENTITY_RECOMMENDATION_ONLY; Integrated Circuits / Product; no canonical mutation
- confidence：HIGH
- reason：SIA 明确集成电路与分立器件的边界，catalog 无同等总类；作为数字/模拟分类关系的关键父对象，新建会建立结构锚点。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-AC855AD6CD7AF8B7

**AI REVIEW B**

- recommendation：HUMAN_REQUIRED；native_decision：CREATE
- proposed operation / canonical target：CREATE；范围/说明: IDENTITY_ONLY; 00_industry_structure; Integrated Circuits; Product
- confidence：HIGH
- reason：IC被直接定义为复杂半导体产品；目录无同名对象。将承接SC-RL-0001/0002分类父节点和0005根路径，是新增结构锚点。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-AC855AD6CD7AF8B7

**A/B RECONCILIATION**

- frozen status：A_B_SUBSTANTIVE_AGREEMENT
- 实质分歧：无；措辞、附注或不改变风险路由的置信度差异不改原冻结一致结论。

**EVIDENCE SUMMARY**

- Supporting facts：下列有来源的节选支持本项讨论的对象/命题；支持范围及未解决条件已在上方 A/B reason 中逐项说明。
- SC-EV-AC855AD6CD7AF8B7 / SC-PHYS-04A42FFC3F71A42F / PDF p.1 / Types of Semiconductors / printed p.NOT_KNOWN_OR_UNNUMBERED；excerpt SHA256=`d484b8abeba761b06e948458bf52c006ba7d1aadb85f133c21622c3a8636181a`。
  > Integrated circuits (ICs) are sophisticated semiconductors that often contain billions of transistors and perform high-level functions, while discretes often contain fewer transistors and perform simpler functions.
- Conflicting evidence：冻结 A/B 未报告本限定范围内的未解决实质证据冲突；不等于完整文献已穷尽。

- **SYSTEM_RECOMMENDED_DECISION** = CREATE
推荐理由（非人工裁决）：双方支持该独立身份，同时一致要求结构性高影响的人类审查；建议确认原候选 CREATE 方向及其图谱影响，尚不授权执行。

HUMAN_USER_DECISION = [PENDING]

OPTIONS:

- [ ] CREATE
- [ ] REUSE <NODE_ID>
- [ ] DEFER
- [ ] REJECT

---

<a id="sc-cn-0006"></a>
### 012 · SC-CN-0006 · Digital Semiconductors

- **ITEM_NUMBER** = 12
- **ITEM_ID** = SC-CN-0006
- **OBJECT_TYPE** = nodes
- **DOMAIN** = 00_industry_structure
- **CURRENT_NATIVE_OPERATION** = CREATE NODE_9D05271E8992A20F
- **CURRENT_STATUS** = CREATE
- **WHY_IN_HUMAN_PACKET** = R07；REVIEWER_UNRESOLVED_HUMAN_REQUIRED
- **RISK_RULES** = R07 新增高影响Node
- **MANDATORY_TRIGGER** = R07；REVIEWER_UNRESOLVED_HUMAN_REQUIRED
- **SAMPLE_STATUS** = NOT_SAMPLED
- **SAMPLED_FOR_QUALITY_CONTROL** = false

- **SOURCE_ID / SOURCE_NAME** = SC-PHYS-04A42FFC3F71A42F / SRC_1640D08BDF90458F / Making Semiconductors: The Highly Complex and Global Chip Research, Design, and Manufacturing Process
Source provenance：Semiconductor Industry Association (SIA)；publication=2019；edition=；as_of=2019；source SHA256=`04a42ffc3f71a42fa9b996240618874bb7fff21404e93cdb1e7bf53318938c26`。

**CANDIDATE_SUMMARY**

- Node 类型：Segment
- 名称：Digital Semiconductors
- 已有身份：NODE_9D05271E8992A20F
- 边界说明：Source支持可复用的持久研究对象，未命中现有规范名或已登记别名。
- Planned native target：NODE_9D05271E8992A20F → SC-CN-0006 / Digital Semiconductors / Segment；这是候选映射，不是已存在或获批准的目录对象。

**AI REVIEW A**

- recommendation：HUMAN_REQUIRED；native_decision：CREATE
- proposed operation / canonical target：CREATE；范围/说明: IDENTITY_RECOMMENDATION_ONLY; Digital Semiconductors / Segment; no canonical mutation
- confidence：HIGH
- reason：SIA 明确数字半导体处理二进制且含存储及逻辑；新节点是本批分类关系的关键上层锚点，非 AI Compute Silicon 的同义词。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-086DB7864B530FA0

**AI REVIEW B**

- recommendation：HUMAN_REQUIRED；native_decision：CREATE
- proposed operation / canonical target：CREATE；范围/说明: IDENTITY_ONLY; 00_industry_structure; Digital Semiconductors; Segment
- confidence：HIGH
- reason：SIA明确数字类别及其存储/逻辑子类；SC-RL-0003/0004依赖该分类锚点，需结构性人审。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-086DB7864B530FA0

**A/B RECONCILIATION**

- frozen status：A_B_SUBSTANTIVE_AGREEMENT
- 实质分歧：无；措辞、附注或不改变风险路由的置信度差异不改原冻结一致结论。

**EVIDENCE SUMMARY**

- Supporting facts：下列有来源的节选支持本项讨论的对象/命题；支持范围及未解决条件已在上方 A/B reason 中逐项说明。
- SC-EV-086DB7864B530FA0 / SC-PHYS-04A42FFC3F71A42F / PDF p.1 / Types of Semiconductors / printed p.NOT_KNOWN_OR_UNNUMBERED；excerpt SHA256=`de70cc3f209d1d690acd93eb476001bba1cc790fb80c8683d1bf9cc013d15cfe`。
  > Within ICs are digital semiconductors, which process binary information used by computers, and analog semiconductors, which regulate “real world” conditions such as temperature, speed, sound, and electrical current. Within the digital category are memory products, micro-components (including microprocessors and microcontrollers) and logic products.
- Conflicting evidence：冻结 A/B 未报告本限定范围内的未解决实质证据冲突；不等于完整文献已穷尽。

- **SYSTEM_RECOMMENDED_DECISION** = CREATE
推荐理由（非人工裁决）：双方支持该独立身份，同时一致要求结构性高影响的人类审查；建议确认原候选 CREATE 方向及其图谱影响，尚不授权执行。

HUMAN_USER_DECISION = [PENDING]

OPTIONS:

- [ ] CREATE
- [ ] REUSE <NODE_ID>
- [ ] DEFER
- [ ] REJECT

---

<a id="sc-cn-0009"></a>
### 013 · SC-CN-0009 · Semiconductor Memory

- **ITEM_NUMBER** = 13
- **ITEM_ID** = SC-CN-0009
- **OBJECT_TYPE** = nodes
- **DOMAIN** = 00_industry_structure
- **CURRENT_NATIVE_OPERATION** = CREATE NODE_CD6598B7D56BCC1A
- **CURRENT_STATUS** = CREATE
- **WHY_IN_HUMAN_PACKET** = R07；REVIEWER_UNRESOLVED_HUMAN_REQUIRED
- **RISK_RULES** = R07 新增高影响Node
- **MANDATORY_TRIGGER** = R07；REVIEWER_UNRESOLVED_HUMAN_REQUIRED
- **SAMPLE_STATUS** = NOT_SAMPLED
- **SAMPLED_FOR_QUALITY_CONTROL** = false

- **SOURCE_ID / SOURCE_NAME** = SC-PHYS-04A42FFC3F71A42F / SRC_1640D08BDF90458F / Making Semiconductors: The Highly Complex and Global Chip Research, Design, and Manufacturing Process
Source provenance：Semiconductor Industry Association (SIA)；publication=2019；edition=；as_of=2019；source SHA256=`04a42ffc3f71a42fa9b996240618874bb7fff21404e93cdb1e7bf53318938c26`。
- **SOURCE_ID / SOURCE_NAME** = SC-PHYS-B33C40EBCB5756F7 / SRC_1DD38DEB69830E97 / Strengthening the Global Semiconductor Supply Chain in an Uncertain Era
Source provenance：Semiconductor Industry Association (SIA) / Boston Consulting Group (BCG)；publication=2021-04；edition=；as_of=2021-04；source SHA256=`b33c40ebcb5756f76e887ba2664f97736252e68ba7bfbedc2d628ce2d7cbc08d`。

**CANDIDATE_SUMMARY**

- Node 类型：Segment
- 名称：Semiconductor Memory
- 已有身份：NODE_CD6598B7D56BCC1A
- 边界说明：Source支持可复用的持久研究对象，未命中现有规范名或已登记别名。
- Planned native target：NODE_CD6598B7D56BCC1A → SC-CN-0009 / Semiconductor Memory / Segment；这是候选映射，不是已存在或获批准的目录对象。

**AI REVIEW A**

- recommendation：HUMAN_REQUIRED；native_decision：CREATE
- proposed operation / canonical target：CREATE；范围/说明: IDENTITY_RECOMMENDATION_ONLY; Semiconductor Memory / Segment; no canonical mutation
- confidence：HIGH
- reason：DRAM/NAND 证据显示持久存储器门类，较现有 Server DRAM/HBM/NOR 广；新总类将承接这些存储身份的分类依赖。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-9F7D3244A0780DEA, SC-EV-80E21D50198799F6

**AI REVIEW B**

- recommendation：HUMAN_REQUIRED；native_decision：CREATE
- proposed operation / canonical target：CREATE；范围/说明: IDENTITY_ONLY; 00_industry_structure; Semiconductor Memory; Segment
- confidence：HIGH
- reason：DRAM/NAND证据及SIA存储类别支持总存储板块；SC-BV-0005和SC-RL-0003以它为结构目标，不能并入Server DRAM。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-9F7D3244A0780DEA, SC-EV-80E21D50198799F6, SC-EV-086DB7864B530FA0

**A/B RECONCILIATION**

- frozen status：A_B_SUBSTANTIVE_AGREEMENT
- 实质分歧：无；措辞、附注或不改变风险路由的置信度差异不改原冻结一致结论。

**EVIDENCE SUMMARY**

- Supporting facts：下列有来源的节选支持本项讨论的对象/命题；支持范围及未解决条件已在上方 A/B reason 中逐项说明。
- SC-EV-086DB7864B530FA0 / SC-PHYS-04A42FFC3F71A42F / PDF p.1 / Types of Semiconductors / printed p.NOT_KNOWN_OR_UNNUMBERED；excerpt SHA256=`de70cc3f209d1d690acd93eb476001bba1cc790fb80c8683d1bf9cc013d15cfe`。
  > Within ICs are digital semiconductors, which process binary information used by computers, and analog semiconductors, which regulate “real world” conditions such as temperature, speed, sound, and electrical current. Within the digital category are memory products, micro-components (including microprocessors and microcontrollers) and logic products.
- SC-EV-80E21D50198799F6 / SC-PHYS-B33C40EBCB5756F7 / PDF p.9 / Memory / printed p.9；excerpt SHA256=`5d250912604a223b65441507e56872c55e6a67e2cba3ec6abef008dd36fe42e1`。
  > NAND is the most common type of flash memory. Unlike DRAM, it does not need power to retain data, so it is used for permanent storage.
- SC-EV-9F7D3244A0780DEA / SC-PHYS-B33C40EBCB5756F7 / PDF p.9 / Memory / printed p.9；excerpt SHA256=`3e0f10608491e28b4ca65b393efba69601bbd0ab43166ecfceffb1f812be69b2`。
  > DRAM is used to store the data or program code needed by a computer processor to function.
- Conflicting evidence：冻结 A/B 未报告本限定范围内的未解决实质证据冲突；不等于完整文献已穷尽。

- **SYSTEM_RECOMMENDED_DECISION** = CREATE
推荐理由（非人工裁决）：双方支持该独立身份，同时一致要求结构性高影响的人类审查；建议确认原候选 CREATE 方向及其图谱影响，尚不授权执行。

HUMAN_USER_DECISION = [PENDING]

OPTIONS:

- [ ] CREATE
- [ ] REUSE <NODE_ID>
- [ ] DEFER
- [ ] REJECT

---

<a id="sc-cn-0014"></a>
### 014 · SC-CN-0014 · Electronic Design Automation

- **ITEM_NUMBER** = 14
- **ITEM_ID** = SC-CN-0014
- **OBJECT_TYPE** = nodes
- **DOMAIN** = 00_industry_structure
- **CURRENT_NATIVE_OPERATION** = CREATE NODE_5C930EA3C5BEEEB1
- **CURRENT_STATUS** = CREATE
- **WHY_IN_HUMAN_PACKET** = R07；REVIEWER_UNRESOLVED_HUMAN_REQUIRED
- **RISK_RULES** = R07 新增高影响Node
- **MANDATORY_TRIGGER** = R07；REVIEWER_UNRESOLVED_HUMAN_REQUIRED
- **SAMPLE_STATUS** = NOT_SAMPLED
- **SAMPLED_FOR_QUALITY_CONTROL** = false

- **SOURCE_ID / SOURCE_NAME** = SC-PHYS-AC86A7FEB4F6ADB5 / SRC_689680B30C113F1B / The Growing Challenge of Semiconductor Design Leadership
Source provenance：Semiconductor Industry Association (SIA) / Boston Consulting Group (BCG)；publication=2022-11；edition=；as_of=2022-11；source SHA256=`ac86a7feb4f6adb52e488086f9281c1f409bd72baecb6bdbed72a0efa3856666`。
- **SOURCE_ID / SOURCE_NAME** = SC-PHYS-B33C40EBCB5756F7 / SRC_1DD38DEB69830E97 / Strengthening the Global Semiconductor Supply Chain in an Uncertain Era
Source provenance：Semiconductor Industry Association (SIA) / Boston Consulting Group (BCG)；publication=2021-04；edition=；as_of=2021-04；source SHA256=`b33c40ebcb5756f76e887ba2664f97736252e68ba7bfbedc2d628ce2d7cbc08d`。

**CANDIDATE_SUMMARY**

- Node 类型：Technology
- 名称：Electronic Design Automation
- 已有身份：NODE_5C930EA3C5BEEEB1
- 边界说明：技术/工具体系；不与提供该体系的软件供应商经营分类混为同一身份。
- Planned native target：NODE_5C930EA3C5BEEEB1 → SC-CN-0014 / Electronic Design Automation / Technology；这是候选映射，不是已存在或获批准的目录对象。

**AI REVIEW A**

- recommendation：HUMAN_REQUIRED；native_decision：CREATE
- proposed operation / canonical target：CREATE；范围/说明: IDENTITY_RECOMMENDATION_ONLY; Electronic Design Automation / Technology; no canonical mutation
- confidence：HIGH
- reason：两来源区分 EDA 软件设计自动化与供应商，Technology 合理；它支撑设计流程、PDK/IP 协作关系和设计基线，是设计使能锚点。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-01DDAE404737D380, SC-EV-6FF6BB080099D1E2

**AI REVIEW B**

- recommendation：HUMAN_REQUIRED；native_decision：CREATE
- proposed operation / canonical target：CREATE；范围/说明: IDENTITY_ONLY; 00_industry_structure; Electronic Design Automation; Technology
- confidence：HIGH
- reason：EDA全称及设计自动化软件职责明确；SC-BV-0001核心设计使能依赖此技术锚点，不将EDA供应商本身建为同一节点。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-01DDAE404737D380, SC-EV-6FF6BB080099D1E2

**A/B RECONCILIATION**

- frozen status：A_B_SUBSTANTIVE_AGREEMENT
- 实质分歧：无；措辞、附注或不改变风险路由的置信度差异不改原冻结一致结论。

**EVIDENCE SUMMARY**

- Supporting facts：下列有来源的节选支持本项讨论的对象/命题；支持范围及未解决条件已在上方 A/B reason 中逐项说明。
- SC-EV-01DDAE404737D380 / SC-PHYS-B33C40EBCB5756F7 / PDF p.19 / Electronic design automation (EDA) / printed p.19；excerpt SHA256=`66ae4b3340bfe72c6a698ece2f0f8a1208d9bab4510fde4f2d2bd8c510247296`。
  > At the design stage, electronic design automation (EDA) companies provide sophisticated software and services to support designing semiconductors, including outsourced design of specialized application specific integrated circuits (ASICs).
- SC-EV-6FF6BB080099D1E2 / SC-PHYS-AC86A7FEB4F6ADB5 / PDF p.7 / Design Is Complex and Includes Multiple Different Types of Firms and Activities / printed p.5；excerpt SHA256=`9da9a2377834d759f2de42083bcaa3f4fe5058e8a692338d19c2d69126d80626`。
  > Designers will often use existing, reusable architectural building blocks (core IP) to simplify and accelerate creation of the overall design. In all cases, designers use highly advanced EDA software to automate the design process and ensure that chip designs can be manufactured on distinct and often proprietary fabrication processes.
- Conflicting evidence：冻结 A/B 未报告本限定范围内的未解决实质证据冲突；不等于完整文献已穷尽。

- **SYSTEM_RECOMMENDED_DECISION** = CREATE
推荐理由（非人工裁决）：双方支持该独立身份，同时一致要求结构性高影响的人类审查；建议确认原候选 CREATE 方向及其图谱影响，尚不授权执行。

HUMAN_USER_DECISION = [PENDING]

OPTIONS:

- [ ] CREATE
- [ ] REUSE <NODE_ID>
- [ ] DEFER
- [ ] REJECT

---

<a id="sc-cn-0020"></a>
### 015 · SC-CN-0020 · Semiconductor Design

- **ITEM_NUMBER** = 15
- **ITEM_ID** = SC-CN-0020
- **OBJECT_TYPE** = nodes
- **DOMAIN** = 01_design_enablement
- **CURRENT_NATIVE_OPERATION** = CREATE NODE_63D3FFF5A5A14739
- **CURRENT_STATUS** = CREATE
- **WHY_IN_HUMAN_PACKET** = R07；REVIEWER_UNRESOLVED_HUMAN_REQUIRED
- **RISK_RULES** = R07 新增高影响Node
- **MANDATORY_TRIGGER** = R07；REVIEWER_UNRESOLVED_HUMAN_REQUIRED
- **SAMPLE_STATUS** = NOT_SAMPLED
- **SAMPLED_FOR_QUALITY_CONTROL** = false

- **SOURCE_ID / SOURCE_NAME** = SC-PHYS-AC86A7FEB4F6ADB5 / SRC_689680B30C113F1B / The Growing Challenge of Semiconductor Design Leadership
Source provenance：Semiconductor Industry Association (SIA) / Boston Consulting Group (BCG)；publication=2022-11；edition=；as_of=2022-11；source SHA256=`ac86a7feb4f6adb52e488086f9281c1f409bd72baecb6bdbed72a0efa3856666`。
- **SOURCE_ID / SOURCE_NAME** = SC-PHYS-B33C40EBCB5756F7 / SRC_1DD38DEB69830E97 / Strengthening the Global Semiconductor Supply Chain in an Uncertain Era
Source provenance：Semiconductor Industry Association (SIA) / Boston Consulting Group (BCG)；publication=2021-04；edition=；as_of=2021-04；source SHA256=`b33c40ebcb5756f76e887ba2664f97736252e68ba7bfbedc2d628ce2d7cbc08d`。

**CANDIDATE_SUMMARY**

- Node 类型：Technology
- 名称：Semiconductor Design
- 已有身份：NODE_63D3FFF5A5A14739
- 边界说明：Source支持可复用的持久研究对象，未命中现有规范名或已登记别名。
- Planned native target：NODE_63D3FFF5A5A14739 → SC-CN-0020 / Semiconductor Design / Technology；这是候选映射，不是已存在或获批准的目录对象。

**AI REVIEW A**

- recommendation：HUMAN_REQUIRED；native_decision：CREATE
- proposed operation / canonical target：CREATE；范围/说明: IDENTITY_RECOMMENDATION_ONLY; Semiconductor Design / Technology; no canonical mutation
- confidence：HIGH
- reason：原文将设计分硬件设计和软件开发，提供持续流程身份；新节点为设计基线和 EDA/PDK 关系的中心依赖。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-7BF90F70A09B7369, SC-EV-A3F7F03ADBFC93FA

**AI REVIEW B**

- recommendation：HUMAN_REQUIRED；native_decision：CREATE
- proposed operation / canonical target：CREATE；范围/说明: IDENTITY_ONLY; 01_design_enablement; Semiconductor Design; Technology
- confidence：HIGH
- reason：多阶段硬件设计与软件活动直接支持Technology；SC-BV-0001以此为中心，设计验证关系也依赖它，属于结构锚点。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-7BF90F70A09B7369, SC-EV-A3F7F03ADBFC93FA

**A/B RECONCILIATION**

- frozen status：A_B_SUBSTANTIVE_AGREEMENT
- 实质分歧：无；措辞、附注或不改变风险路由的置信度差异不改原冻结一致结论。

**EVIDENCE SUMMARY**

- Supporting facts：下列有来源的节选支持本项讨论的对象/命题；支持范围及未解决条件已在上方 A/B reason 中逐项说明。
- SC-EV-7BF90F70A09B7369 / SC-PHYS-AC86A7FEB4F6ADB5 / PDF p.7 / Design Is Complex and Includes Multiple Different Types of Firms and Activities / printed p.5；excerpt SHA256=`bb7a8c0baae4bad3cc8541ea8e20c7ffe75a1694eb4dbd3592d7b7c436e25ada`。
  > Semiconductor design involves two types of activities: hard­ware design and software development work. Hard- ware design is a multistep process encompassing product definition and specification, system design, integrated circuit design, and post-silicon validation.
- SC-EV-A3F7F03ADBFC93FA / SC-PHYS-B33C40EBCB5756F7 / PDF p.15 / Chip design / printed p.15；excerpt SHA256=`825b33a85d774a7ab69972637becaa26d4ee8c96c8793c355720a0513fb40544`。
  > Design relies on highly advanced electronic design automation (EDA) software and reusable architectural building blocks (“IP cores”), and in some cases also outsourced chip design services provided by specialized technology suppliers.
- Conflicting evidence：冻结 A/B 未报告本限定范围内的未解决实质证据冲突；不等于完整文献已穷尽。

- **SYSTEM_RECOMMENDED_DECISION** = CREATE
推荐理由（非人工裁决）：双方支持该独立身份，同时一致要求结构性高影响的人类审查；建议确认原候选 CREATE 方向及其图谱影响，尚不授权执行。

HUMAN_USER_DECISION = [PENDING]

OPTIONS:

- [ ] CREATE
- [ ] REUSE <NODE_ID>
- [ ] DEFER
- [ ] REJECT

---

<a id="sc-cn-0021"></a>
### 016 · SC-CN-0021 · Wafer Fabrication

- **ITEM_NUMBER** = 16
- **ITEM_ID** = SC-CN-0021
- **OBJECT_TYPE** = nodes
- **DOMAIN** = 00_industry_structure
- **CURRENT_NATIVE_OPERATION** = CREATE NODE_C7C6BD126DAA8EA7
- **CURRENT_STATUS** = CREATE
- **WHY_IN_HUMAN_PACKET** = R07；REVIEWER_UNRESOLVED_HUMAN_REQUIRED
- **RISK_RULES** = R07 新增高影响Node
- **MANDATORY_TRIGGER** = R07；REVIEWER_UNRESOLVED_HUMAN_REQUIRED
- **SAMPLE_STATUS** = NOT_SAMPLED
- **SAMPLED_FOR_QUALITY_CONTROL** = false

- **SOURCE_ID / SOURCE_NAME** = SC-PHYS-B33C40EBCB5756F7 / SRC_1DD38DEB69830E97 / Strengthening the Global Semiconductor Supply Chain in an Uncertain Era
Source provenance：Semiconductor Industry Association (SIA) / Boston Consulting Group (BCG)；publication=2021-04；edition=；as_of=2021-04；source SHA256=`b33c40ebcb5756f76e887ba2664f97736252e68ba7bfbedc2d628ce2d7cbc08d`。
- **SOURCE_ID / SOURCE_NAME** = SC-PHYS-C5B6DC633E156218 / SRC_AC29CFEE56F74F5B / Testimony of the Semiconductor Industry Association before the Senate Committee on Environment & Public Works (March 4, 2026)
Source provenance：Semiconductor Industry Association (SIA)；publication=2026-03-04；edition=；as_of=2026-03-04；source SHA256=`c5b6dc633e156218eb950f2dee88f43fbdcc4fc1744a5924f12b977f5cb7df71`。

**CANDIDATE_SUMMARY**

- Node 类型：Technology
- 名称：Wafer Fabrication
- 已有身份：NODE_C7C6BD126DAA8EA7
- 边界说明：晶圆制造流程，含晶体管形成和晶圆互连；不是制造厂商本身。
- Planned native target：NODE_C7C6BD126DAA8EA7 → SC-CN-0021 / Wafer Fabrication / Technology；这是候选映射，不是已存在或获批准的目录对象。

**AI REVIEW A**

- recommendation：HUMAN_REQUIRED；native_decision：CREATE
- proposed operation / canonical target：CREATE；范围/说明: IDENTITY_RECOMMENDATION_ONLY; Wafer Fabrication / Technology; no canonical mutation
- confidence：HIGH
- reason：fab 将设计印到晶圆及后段金属互连均属制造流程，非代工公司；是前后道关系和制造基线共同锚点。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-07279E1F10D9E07A, SC-EV-30ECB7A5649A64DC

**AI REVIEW B**

- recommendation：HUMAN_REQUIRED；native_decision：CREATE
- proposed operation / canonical target：CREATE；范围/说明: IDENTITY_ONLY; 00_industry_structure; Wafer Fabrication; Technology
- confidence：HIGH
- reason：从设计到晶圆电路及金属互连的工艺有证据；SC-BV-0003以此统摄FEOL/BEOL，不可误作Foundry企业。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-07279E1F10D9E07A, SC-EV-30ECB7A5649A64DC

**A/B RECONCILIATION**

- frozen status：A_B_SUBSTANTIVE_AGREEMENT
- 实质分歧：无；措辞、附注或不改变风险路由的置信度差异不改原冻结一致结论。

**EVIDENCE SUMMARY**

- Supporting facts：下列有来源的节选支持本项讨论的对象/命题；支持范围及未解决条件已在上方 A/B reason 中逐项说明。
- SC-EV-07279E1F10D9E07A / SC-PHYS-B33C40EBCB5756F7 / PDF p.16 / Wafer fabrication (front end manufacturing) / printed p.16；excerpt SHA256=`db735094daa467487d926b5f5d92d20bab5c211fabb9b251798e759d161d3732`。
  > Highly specialized semiconductor manufacturing facilities, typically called “fabs”, print the nanometer- scale integrated circuits from the chip design into silicon wafers.
- SC-EV-30ECB7A5649A64DC / SC-PHYS-C5B6DC633E156218 / PDF p.5 / II / Back-End Fabrication / Metallization / printed p.5；excerpt SHA256=`d6a39a41013572a9d37dcb4c73163c05252d55a2ba42d53bb571d3a1f8ac5214`。
  > Metallization: Prior processing steps prepare the device for metallization, which creates the electrical interconnections between all transistors on the wafer. Following completion of the front end, individual devices are interconnected on the "back end" using a series of alternating metal depositions and dielectric films, each with their respective patterning.
- Conflicting evidence：冻结 A/B 未报告本限定范围内的未解决实质证据冲突；不等于完整文献已穷尽。

- **SYSTEM_RECOMMENDED_DECISION** = CREATE
推荐理由（非人工裁决）：双方支持该独立身份，同时一致要求结构性高影响的人类审查；建议确认原候选 CREATE 方向及其图谱影响，尚不授权执行。

HUMAN_USER_DECISION = [PENDING]

OPTIONS:

- [ ] CREATE
- [ ] REUSE <NODE_ID>
- [ ] DEFER
- [ ] REJECT

---

<a id="sc-cn-0022"></a>
### 017 · SC-CN-0022 · Process Design Kit

- **ITEM_NUMBER** = 17
- **ITEM_ID** = SC-CN-0022
- **OBJECT_TYPE** = nodes
- **DOMAIN** = 01_design_enablement
- **CURRENT_NATIVE_OPERATION** = CREATE NODE_4BB09801D57A983C
- **CURRENT_STATUS** = CREATE
- **WHY_IN_HUMAN_PACKET** = R07；REVIEWER_UNRESOLVED_HUMAN_REQUIRED
- **RISK_RULES** = R07 新增高影响Node
- **MANDATORY_TRIGGER** = R07；REVIEWER_UNRESOLVED_HUMAN_REQUIRED
- **SAMPLE_STATUS** = NOT_SAMPLED
- **SAMPLED_FOR_QUALITY_CONTROL** = false

- **SOURCE_ID / SOURCE_NAME** = SC-PHYS-7E064380CA686D9F / SRC_5AF7599EF3DE9C6D / Explaining Common Chip Terms
Source provenance：Intel；publication=2026-03-09；edition=；as_of=2026-03-09；source SHA256=`7e064380ca686d9f00c235f15c007523e89e4a0ffb7e9a22f435218c06799d05`。
- **SOURCE_ID / SOURCE_NAME** = SC-PHYS-AC86A7FEB4F6ADB5 / SRC_689680B30C113F1B / The Growing Challenge of Semiconductor Design Leadership
Source provenance：Semiconductor Industry Association (SIA) / Boston Consulting Group (BCG)；publication=2022-11；edition=；as_of=2022-11；source SHA256=`ac86a7feb4f6adb52e488086f9281c1f409bd72baecb6bdbed72a0efa3856666`。

**CANDIDATE_SUMMARY**

- Node 类型：Product
- 名称：Process Design Kit
- 已有身份：NODE_4BB09801D57A983C
- 边界说明：Source支持可复用的持久研究对象，未命中现有规范名或已登记别名。
- Planned native target：NODE_4BB09801D57A983C → SC-CN-0022 / Process Design Kit / Product；这是候选映射，不是已存在或获批准的目录对象。

**AI REVIEW A**

- recommendation：HUMAN_REQUIRED；native_decision：CREATE
- proposed operation / canonical target：CREATE；范围/说明: IDENTITY_RECOMMENDATION_ONLY; Process Design Kit / Product; no canonical mutation
- confidence：HIGH
- reason：PDK 被直接定义为特定工艺的规格、指南与工具集合，Product 合理；它连接设计与制造兼容性，影响关键依赖。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-3F0EC598BF78F3BE, SC-EV-73E156B2F86976F1, SC-EV-3372E0A59571A7A8

**AI REVIEW B**

- recommendation：HUMAN_REQUIRED；native_decision：CREATE
- proposed operation / canonical target：CREATE；范围/说明: IDENTITY_ONLY; 01_design_enablement; Process Design Kit; Product
- confidence：HIGH
- reason：PDK明确定义为特定工艺节点设计规格、指南与工具组合；SC-BV-0001的设计制造兼容性依赖该Product锚点。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-3F0EC598BF78F3BE, SC-EV-73E156B2F86976F1, SC-EV-3372E0A59571A7A8

**A/B RECONCILIATION**

- frozen status：A_B_SUBSTANTIVE_AGREEMENT
- 实质分歧：无；措辞、附注或不改变风险路由的置信度差异不改原冻结一致结论。

**EVIDENCE SUMMARY**

- Supporting facts：下列有来源的节选支持本项讨论的对象/命题；支持范围及未解决条件已在上方 A/B reason 中逐项说明。
- SC-EV-3372E0A59571A7A8 / SC-PHYS-AC86A7FEB4F6ADB5 / PDF p.28 / Design and front-end wafer fabrication / printed p.26；excerpt SHA256=`ec8a497765e2866b5eec4ecfe2a0105213050c6981426ba04cd46f10cfa84e06`。
  > Design engineers and wafer fabrication engineers use PDKs—essentially documentation of fabri- cation processes—and work together to debug design features and verify that manufacturing processes and chip designs are compatible.
- SC-EV-3F0EC598BF78F3BE / SC-PHYS-7E064380CA686D9F / PDF p.5 / Process Nodes and PDKs / printed p.NOT_KNOWN_OR_UNNUMBERED；excerpt SHA256=`db51b1f1b4fb2125c728906ffa1d0c27a06c98ada75bb0715185b347234f90bc`。
  > A process design kit, or PDK, is a set of specifications, guidelines and tools to design a chip using a specific process node.
- SC-EV-73E156B2F86976F1 / SC-PHYS-AC86A7FEB4F6ADB5 / PDF p.27 / Electronic Design Automation (EDA) and Core IP / printed p.25；excerpt SHA256=`90fa4c7132b45faac51c8dbe99df2a144e6fb7c9a6026ef36e5c19b30ea75185`。
  > Design Tools. Such tools are enabled for a specific foundry, technology node, and process design kit (PDK).
- Conflicting evidence：冻结 A/B 未报告本限定范围内的未解决实质证据冲突；不等于完整文献已穷尽。

- **SYSTEM_RECOMMENDED_DECISION** = CREATE
推荐理由（非人工裁决）：双方支持该独立身份，同时一致要求结构性高影响的人类审查；建议确认原候选 CREATE 方向及其图谱影响，尚不授权执行。

HUMAN_USER_DECISION = [PENDING]

OPTIONS:

- [ ] CREATE
- [ ] REUSE <NODE_ID>
- [ ] DEFER
- [ ] REJECT

---

<a id="sc-cn-0025"></a>
### 018 · SC-CN-0025 · Silicon Wafer

- **ITEM_NUMBER** = 18
- **ITEM_ID** = SC-CN-0025
- **OBJECT_TYPE** = nodes
- **DOMAIN** = 00_industry_structure
- **CURRENT_NATIVE_OPERATION** = CREATE NODE_B96F04EBB6D1FD0A
- **CURRENT_STATUS** = CREATE
- **WHY_IN_HUMAN_PACKET** = R07；REVIEWER_UNRESOLVED_HUMAN_REQUIRED
- **RISK_RULES** = R07 新增高影响Node
- **MANDATORY_TRIGGER** = R07；REVIEWER_UNRESOLVED_HUMAN_REQUIRED
- **SAMPLE_STATUS** = NOT_SAMPLED
- **SAMPLED_FOR_QUALITY_CONTROL** = false

- **SOURCE_ID / SOURCE_NAME** = SC-PHYS-9E9CEFC24043585C / SRC_8442AD30618C9A2D / Production Processes
Source provenance：SUMCO Corporation；publication=；edition=；as_of=；source SHA256=`9e9cefc24043585c1c5a484340dcf49aa0725b341467942d3d4c34be0da8aee6`。
- **SOURCE_ID / SOURCE_NAME** = SC-PHYS-B33C40EBCB5756F7 / SRC_1DD38DEB69830E97 / Strengthening the Global Semiconductor Supply Chain in an Uncertain Era
Source provenance：Semiconductor Industry Association (SIA) / Boston Consulting Group (BCG)；publication=2021-04；edition=；as_of=2021-04；source SHA256=`b33c40ebcb5756f76e887ba2664f97736252e68ba7bfbedc2d628ce2d7cbc08d`。

**CANDIDATE_SUMMARY**

- Node 类型：Material
- 名称：Silicon Wafer
- 已有身份：NODE_B96F04EBB6D1FD0A
- 边界说明：起始晶圆材料；晶圆上的成品芯片和封装载板不是同一身份。
- Planned native target：NODE_B96F04EBB6D1FD0A → SC-CN-0025 / Silicon Wafer / Material；这是候选映射，不是已存在或获批准的目录对象。

**AI REVIEW A**

- recommendation：HUMAN_REQUIRED；native_decision：CREATE
- proposed operation / canonical target：CREATE；范围/说明: IDENTITY_RECOMMENDATION_ONLY; Silicon Wafer / Material; no canonical mutation
- confidence：HIGH
- reason：从晶锭切片至电路加工的起始硅片与成品 die 不同，亦比 SOI Wafer 广；它是硅片基线及生长/加工链关键材料锚点。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-A47357C4422D938D, SC-EV-3BE221EFD700F965

**AI REVIEW B**

- recommendation：HUMAN_REQUIRED；native_decision：CREATE
- proposed operation / canonical target：CREATE；范围/说明: IDENTITY_ONLY; 00_industry_structure; Silicon Wafer; Material
- confidence：HIGH
- reason：硅锭切片、清洗抛光形成起始晶圆，区别SOI与成品芯片；SC-BV-0002及SC-RL-0052依赖此材料锚点。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-A47357C4422D938D, SC-EV-3BE221EFD700F965

**A/B RECONCILIATION**

- frozen status：A_B_SUBSTANTIVE_AGREEMENT
- 实质分歧：无；措辞、附注或不改变风险路由的置信度差异不改原冻结一致结论。

**EVIDENCE SUMMARY**

- Supporting facts：下列有来源的节选支持本项讨论的对象/命题；支持范围及未解决条件已在上方 A/B reason 中逐项说明。
- SC-EV-3BE221EFD700F965 / SC-PHYS-9E9CEFC24043585C / PDF p.2 / Monocrystalline pulling process / printed p.NOT_KNOWN_OR_UNNUMBERED；excerpt SHA256=`f2a1f5fd0055ec8e3500d40754ed50d70d52dad829317164794bd41622d18e97`。
  > The monocrystalline ingots that make up the silicon wafer are manufactured using high-quality polysilicon as the raw material.
- SC-EV-A47357C4422D938D / SC-PHYS-B33C40EBCB5756F7 / PDF p.22 / Materials / printed p.22；excerpt SHA256=`efc40de6a98c3e8656d7f4bd947e6c8030fec720a67237d6661f5ffbf73ffc02`。
  > Silicon wafers: Polysilicon is melted, formed into single crystal ingots which are then sliced into wafers, cleaned, polished, and oxidized in preparation for circuit imprinting within fabrication facilities.
- Conflicting evidence：冻结 A/B 未报告本限定范围内的未解决实质证据冲突；不等于完整文献已穷尽。

- **SYSTEM_RECOMMENDED_DECISION** = CREATE
推荐理由（非人工裁决）：双方支持该独立身份，同时一致要求结构性高影响的人类审查；建议确认原候选 CREATE 方向及其图谱影响，尚不授权执行。

HUMAN_USER_DECISION = [PENDING]

OPTIONS:

- [ ] CREATE
- [ ] REUSE <NODE_ID>
- [ ] DEFER
- [ ] REJECT

---

<a id="sc-cn-0029"></a>
### 019 · SC-CN-0029 · Process Node

- **ITEM_NUMBER** = 19
- **ITEM_ID** = SC-CN-0029
- **OBJECT_TYPE** = nodes
- **DOMAIN** = 01_design_enablement
- **CURRENT_NATIVE_OPERATION** = UNDECIDED（没有已填写的人类原生决定）
- **CURRENT_STATUS** = REVIEW
- **WHY_IN_HUMAN_PACKET** = R07；REVIEWER_UNRESOLVED_HUMAN_REQUIRED
- **RISK_RULES** = R07 新增高影响Node
- **MANDATORY_TRIGGER** = R07；REVIEWER_UNRESOLVED_HUMAN_REQUIRED
- **SAMPLE_STATUS** = NOT_SAMPLED
- **SAMPLED_FOR_QUALITY_CONTROL** = false

- **SOURCE_ID / SOURCE_NAME** = SC-PHYS-7E064380CA686D9F / SRC_5AF7599EF3DE9C6D / Explaining Common Chip Terms
Source provenance：Intel；publication=2026-03-09；edition=；as_of=2026-03-09；source SHA256=`7e064380ca686d9f00c235f15c007523e89e4a0ffb7e9a22f435218c06799d05`。

**CANDIDATE_SUMMARY**

- Node 类型：Technology
- 名称：Process Node
- 边界说明：通用工艺平台概念建议保留；技术代际具体数值作属性，不另建节点。

**AI REVIEW A**

- recommendation：HUMAN_REQUIRED；native_decision：CREATE
- proposed operation / canonical target：CREATE；范围/说明: IDENTITY_RECOMMENDATION_ONLY; Process Node / Technology; no canonical mutation
- confidence：HIGH
- reason：Intel 明确定义 process node 为物理架构与制造配方，Technology 可承载，数值节点名只作属性；PDK 和性能评价依赖此工艺平台锚点。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-B48A62388C18EE85, SC-EV-822974FB05D75D67

**AI REVIEW B**

- recommendation：HUMAN_REQUIRED；native_decision：CREATE
- proposed operation / canonical target：CREATE；范围/说明: IDENTITY_ONLY; 01_design_enablement; Process Node; Technology
- confidence：HIGH
- reason：Intel把process node定义为架构、互连和工序方案；PDK及SC-BV-0001直接依赖此工艺平台概念，不能用某纳米数字替代。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-B48A62388C18EE85, SC-EV-822974FB05D75D67

**A/B RECONCILIATION**

- frozen status：A_B_SUBSTANTIVE_AGREEMENT
- 实质分歧：无；措辞、附注或不改变风险路由的置信度差异不改原冻结一致结论。

**EVIDENCE SUMMARY**

- Supporting facts：下列有来源的节选支持本项讨论的对象/命题；支持范围及未解决条件已在上方 A/B reason 中逐项说明。
- SC-EV-822974FB05D75D67 / SC-PHYS-7E064380CA686D9F / PDF p.5 / Process Nodes and PDKs / printed p.NOT_KNOWN_OR_UNNUMBERED；excerpt SHA256=`6893db69461ee4efde307c2866f75b09e9dc0cb3e2f8a3860595fb0c99e258ee`。
  > In the past, process node names were based on physical measurements in micrometers or nanometers (like 0.13 microns or 45 nanometers), but current names are closer to representations of each node’s increase in density and/or performance.
- SC-EV-B48A62388C18EE85 / SC-PHYS-7E064380CA686D9F / PDF p.4 / Process Nodes and PDKs / printed p.NOT_KNOWN_OR_UNNUMBERED；excerpt SHA256=`b6f88a33aaf0e54c2c89f67cced173f8b1f520b540ff4092bca5334c9d6fe60e`。
  > The recipe and list of ingredients used in semiconductor fabrication is called a process node. A node specifies the physical architecture of the components – most notably the transistors and the wiring that connects them, called interconnects – and the thousands of steps to build them.
- Conflicting evidence：冻结 A/B 未报告本限定范围内的未解决实质证据冲突；不等于完整文献已穷尽。

- **SYSTEM_RECOMMENDED_DECISION** = CREATE
推荐理由（非人工裁决）：双方支持该独立身份，同时一致要求结构性高影响的人类审查；建议确认原候选 CREATE 方向及其图谱影响，尚不授权执行。

HUMAN_USER_DECISION = [PENDING]

OPTIONS:

- [ ] CREATE
- [ ] REUSE <NODE_ID>
- [ ] DEFER
- [ ] REJECT

---

<a id="sc-cn-0052"></a>
### 020 · SC-CN-0052 · Photoresist

- **ITEM_NUMBER** = 20
- **ITEM_ID** = SC-CN-0052
- **OBJECT_TYPE** = nodes
- **DOMAIN** = 00_industry_structure
- **CURRENT_NATIVE_OPERATION** = UNDECIDED（没有已填写的人类原生决定）
- **CURRENT_STATUS** = REVIEW
- **WHY_IN_HUMAN_PACKET** = R07；REVIEWER_UNRESOLVED_HUMAN_REQUIRED
- **RISK_RULES** = R07 新增高影响Node
- **MANDATORY_TRIGGER** = R07；REVIEWER_UNRESOLVED_HUMAN_REQUIRED
- **SAMPLE_STATUS** = NOT_SAMPLED
- **SAMPLED_FOR_QUALITY_CONTROL** = false

- **SOURCE_ID / SOURCE_NAME** = SC-PHYS-87B4665C30781057 / SRC_ADCEE4236B19B5F2 / Six Crucial Steps in Semiconductor Manufacturing
Source provenance：ASML；publication=2023-10-04；edition=；as_of=2023-10-04；source SHA256=`87b4665c3078105792ca70f18964c938976b72f2dcf0d19379b034d5d6f205f9`。
- **SOURCE_ID / SOURCE_NAME** = SC-PHYS-B33C40EBCB5756F7 / SRC_1DD38DEB69830E97 / Strengthening the Global Semiconductor Supply Chain in an Uncertain Era
Source provenance：Semiconductor Industry Association (SIA) / Boston Consulting Group (BCG)；publication=2021-04；edition=；as_of=2021-04；source SHA256=`b33c40ebcb5756f76e887ba2664f97736252e68ba7bfbedc2d628ce2d7cbc08d`。

**CANDIDATE_SUMMARY**

- Node 类型：Material
- 名称：Photoresist
- 备选身份：NODE_20260817_D33CCFC0
- 边界说明：通用光刻胶；不同于 Advanced Packaging Photoresist，也不同于 Photoresist Resin 组分。
- Canonical state：NODE_20260817_D33CCFC0 = Advanced Packaging Photoresist；type=Material；status=active。

**AI REVIEW A**

- recommendation：HUMAN_REQUIRED；native_decision：CREATE
- proposed operation / canonical target：CREATE；范围/说明: IDENTITY_RECOMMENDATION_ONLY; Photoresist / Material; no canonical mutation
- confidence：HIGH
- reason：两来源给出光敏涂层总类，区别先进封装光刻胶子类和 Photoresist Resin 组分；承接光刻/正负胶分类依赖的材料锚点。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-B569E06E885DA787, SC-EV-5A701F864F4A7C10

**AI REVIEW B**

- recommendation：HUMAN_REQUIRED；native_decision：CREATE
- proposed operation / canonical target：CREATE；范围/说明: IDENTITY_ONLY; 00_industry_structure; Photoresist; Material
- confidence：HIGH
- reason：通用光敏抗蚀材料直接定义，明显大于先进封装光刻胶且不是树脂组分；SC-RL-0015/0016及0035依赖其材料父层。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-B569E06E885DA787, SC-EV-5A701F864F4A7C10

**A/B RECONCILIATION**

- frozen status：A_B_SUBSTANTIVE_AGREEMENT
- 实质分歧：无；措辞、附注或不改变风险路由的置信度差异不改原冻结一致结论。

**EVIDENCE SUMMARY**

- Supporting facts：下列有来源的节选支持本项讨论的对象/命题；支持范围及未解决条件已在上方 A/B reason 中逐项说明。
- SC-EV-5A701F864F4A7C10 / SC-PHYS-87B4665C30781057 / PDF p.3 / Photoresist coating / printed p.NOT_KNOWN_OR_UNNUMBERED；excerpt SHA256=`84bcee264567f16580c6ce836ec8196d35f33a68fb4e58e4d03d437f28587b07`。
  > The wafer is then covered with a light-sensitive coating called 'photoresist', or 'resist' for short. There are two types of resist: positive and negative.
- SC-EV-B569E06E885DA787 / SC-PHYS-B33C40EBCB5756F7 / PDF p.22 / Materials / printed p.22；excerpt SHA256=`1a71c29703324c17eb2fceb7db5e6ab4eca23efc24c6f283384d56f8117883b4`。
  > Photoresist: A special material that undergoes a chemical reaction upon exposure to light. Silicon wafers are covered with a photoresist layer, which is imprinted with the patterns contained in the photomask during the lithography process.
- Conflicting evidence：冻结 A/B 未报告本限定范围内的未解决实质证据冲突；不等于完整文献已穷尽。

- **SYSTEM_RECOMMENDED_DECISION** = CREATE
推荐理由（非人工裁决）：双方支持该独立身份，同时一致要求结构性高影响的人类审查；建议确认原候选 CREATE 方向及其图谱影响，尚不授权执行。

HUMAN_USER_DECISION = [PENDING]

OPTIONS:

- [ ] CREATE
- [ ] REUSE <NODE_ID>
- [ ] DEFER
- [ ] REJECT

---

<a id="sc-cn-0056"></a>
### 021 · SC-CN-0056 · Photolithography

- **ITEM_NUMBER** = 21
- **ITEM_ID** = SC-CN-0056
- **OBJECT_TYPE** = nodes
- **DOMAIN** = 03_fab_process_equipment
- **CURRENT_NATIVE_OPERATION** = CREATE NODE_D71397E38AE45F20
- **CURRENT_STATUS** = CREATE
- **WHY_IN_HUMAN_PACKET** = R07；REVIEWER_UNRESOLVED_HUMAN_REQUIRED
- **RISK_RULES** = R07 新增高影响Node
- **MANDATORY_TRIGGER** = R07；REVIEWER_UNRESOLVED_HUMAN_REQUIRED
- **SAMPLE_STATUS** = NOT_SAMPLED
- **SAMPLED_FOR_QUALITY_CONTROL** = false

- **SOURCE_ID / SOURCE_NAME** = SC-PHYS-87B4665C30781057 / SRC_ADCEE4236B19B5F2 / Six Crucial Steps in Semiconductor Manufacturing
Source provenance：ASML；publication=2023-10-04；edition=；as_of=2023-10-04；source SHA256=`87b4665c3078105792ca70f18964c938976b72f2dcf0d19379b034d5d6f205f9`。
- **SOURCE_ID / SOURCE_NAME** = SC-PHYS-C5B6DC633E156218 / SRC_AC29CFEE56F74F5B / Testimony of the Semiconductor Industry Association before the Senate Committee on Environment & Public Works (March 4, 2026)
Source provenance：Semiconductor Industry Association (SIA)；publication=2026-03-04；edition=；as_of=2026-03-04；source SHA256=`c5b6dc633e156218eb950f2dee88f43fbdcc4fc1744a5924f12b977f5cb7df71`。

**CANDIDATE_SUMMARY**

- Node 类型：Technology
- 名称：Photolithography
- 已有身份：NODE_D71397E38AE45F20
- 边界说明：Source支持可复用的持久研究对象，未命中现有规范名或已登记别名。
- Planned native target：NODE_D71397E38AE45F20 → SC-CN-0056 / Photolithography / Technology；这是候选映射，不是已存在或获批准的目录对象。

**AI REVIEW A**

- recommendation：HUMAN_REQUIRED；native_decision：CREATE
- proposed operation / canonical target：CREATE；范围/说明: IDENTITY_RECOMMENDATION_ONLY; Photolithography / Technology; no canonical mutation
- confidence：HIGH
- reason：光源经 mask/reticle 在胶层成像的流程直接可见，区别设备身份；该节点是光刻基线与材料/设备关系的技术锚点。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-67EC75515BB09180, SC-EV-FD3B14BF5F4E693A

**AI REVIEW B**

- recommendation：HUMAN_REQUIRED；native_decision：CREATE
- proposed operation / canonical target：CREATE；范围/说明: IDENTITY_ONLY; 03_fab_process_equipment; Photolithography; Technology
- confidence：HIGH
- reason：曝光通过掩模把图形投射至胶层，工艺身份明确；SC-BV-0004与0035/0036工具材料路径以此为中心。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-67EC75515BB09180, SC-EV-FD3B14BF5F4E693A

**A/B RECONCILIATION**

- frozen status：A_B_SUBSTANTIVE_AGREEMENT
- 实质分歧：无；措辞、附注或不改变风险路由的置信度差异不改原冻结一致结论。

**EVIDENCE SUMMARY**

- Supporting facts：下列有来源的节选支持本项讨论的对象/命题；支持范围及未解决条件已在上方 A/B reason 中逐项说明。
- SC-EV-67EC75515BB09180 / SC-PHYS-C5B6DC633E156218 / PDF p.4 / II / Front-End Fabrication / Photolithography / printed p.4；excerpt SHA256=`d49de79df3fb0e595282e9746bcd100459e0a41920f737ed1446f4908192c3a1`。
  > A stepper or scanner (using deep ultraviolet or extreme ultraviolet light) aligns the wafer to a glass photomask and projects intense light through the mask or reticle, exposing the photoresist with the pattern.
- SC-EV-FD3B14BF5F4E693A / SC-PHYS-87B4665C30781057 / PDF p.3 / Lithography / printed p.NOT_KNOWN_OR_UNNUMBERED；excerpt SHA256=`21298139f48fcf329096f3f7d90d4751ff5497922f91c3a74665ff867615183f`。
  > Light is projected onto the wafer through the 'reticle', which holds the blueprint of the pattern to be printed. The system's optics (lenses in a DUV system and mirrors in an EUV system) shrink and focus the pattern onto the resist layer.
- Conflicting evidence：冻结 A/B 未报告本限定范围内的未解决实质证据冲突；不等于完整文献已穷尽。

- **SYSTEM_RECOMMENDED_DECISION** = CREATE
推荐理由（非人工裁决）：双方支持该独立身份，同时一致要求结构性高影响的人类审查；建议确认原候选 CREATE 方向及其图谱影响，尚不授权执行。

HUMAN_USER_DECISION = [PENDING]

OPTIONS:

- [ ] CREATE
- [ ] REUSE <NODE_ID>
- [ ] DEFER
- [ ] REJECT

---

<a id="sc-cn-0060"></a>
### 022 · SC-CN-0060 · Etching

- **ITEM_NUMBER** = 22
- **ITEM_ID** = SC-CN-0060
- **OBJECT_TYPE** = nodes
- **DOMAIN** = 03_fab_process_equipment
- **CURRENT_NATIVE_OPERATION** = CREATE NODE_7FDCA2B3859210F3
- **CURRENT_STATUS** = CREATE
- **WHY_IN_HUMAN_PACKET** = R07；REVIEWER_UNRESOLVED_HUMAN_REQUIRED
- **RISK_RULES** = R07 新增高影响Node
- **MANDATORY_TRIGGER** = R07；REVIEWER_UNRESOLVED_HUMAN_REQUIRED
- **SAMPLE_STATUS** = NOT_SAMPLED
- **SAMPLED_FOR_QUALITY_CONTROL** = false

- **SOURCE_ID / SOURCE_NAME** = SC-PHYS-87B4665C30781057 / SRC_ADCEE4236B19B5F2 / Six Crucial Steps in Semiconductor Manufacturing
Source provenance：ASML；publication=2023-10-04；edition=；as_of=2023-10-04；source SHA256=`87b4665c3078105792ca70f18964c938976b72f2dcf0d19379b034d5d6f205f9`。
- **SOURCE_ID / SOURCE_NAME** = SC-PHYS-C5B6DC633E156218 / SRC_AC29CFEE56F74F5B / Testimony of the Semiconductor Industry Association before the Senate Committee on Environment & Public Works (March 4, 2026)
Source provenance：Semiconductor Industry Association (SIA)；publication=2026-03-04；edition=；as_of=2026-03-04；source SHA256=`c5b6dc633e156218eb950f2dee88f43fbdcc4fc1744a5924f12b977f5cb7df71`。

**CANDIDATE_SUMMARY**

- Node 类型：Technology
- 名称：Etching
- 已有身份：NODE_7FDCA2B3859210F3
- 边界说明：本批工业芯片刻蚀总工艺；起始晶圆损伤腐蚀需独立scope。
- Planned native target：NODE_7FDCA2B3859210F3 → SC-CN-0060 / Etching / Technology；这是候选映射，不是已存在或获批准的目录对象。

**AI REVIEW A**

- recommendation：HUMAN_REQUIRED；native_decision：CREATE
- proposed operation / canonical target：CREATE；范围/说明: IDENTITY_RECOMMENDATION_ONLY; Etching / Technology; no canonical mutation
- confidence：HIGH
- reason：两来源支持光刻后材料去除总工艺；新 Etching 总类组织干湿流程及化学材料依赖，不与 TSV Deep Silicon Etch Equipment 混同。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-F4124019AED7B2C6, SC-EV-26A3AD09365A5C99

**AI REVIEW B**

- recommendation：HUMAN_REQUIRED；native_decision：CREATE
- proposed operation / canonical target：CREATE；范围/说明: IDENTITY_ONLY; 03_fab_process_equipment; Etching; Technology
- confidence：HIGH
- reason：原文同时定义干湿刻蚀，总工艺与两子类相区分；SC-RL-0013/0014依赖其层级父节点。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-F4124019AED7B2C6, SC-EV-26A3AD09365A5C99

**A/B RECONCILIATION**

- frozen status：A_B_SUBSTANTIVE_AGREEMENT
- 实质分歧：无；措辞、附注或不改变风险路由的置信度差异不改原冻结一致结论。

**EVIDENCE SUMMARY**

- Supporting facts：下列有来源的节选支持本项讨论的对象/命题；支持范围及未解决条件已在上方 A/B reason 中逐项说明。
- SC-EV-26A3AD09365A5C99 / SC-PHYS-C5B6DC633E156218 / PDF p.4 / II / Front-End Fabrication / Etching / printed p.4；excerpt SHA256=`05aef6dddc56a416494e6660c923999e77588107e3cc9b98efa4b7121f60bc1b`。
  > The wafer is then exposed to a chemical wet solution or plasma so that areas not covered by the hardened photoresist are etched away. Wet etching uses solutions of acids such as sulfuric, hydrochloric, phosphoric, and hydrofluoric, as well as bases such as ammonium hydroxide, or oxidizers such as hydrogen peroxide.
- SC-EV-F4124019AED7B2C6 / SC-PHYS-87B4665C30781057 / PDF p.5 / Etch / printed p.NOT_KNOWN_OR_UNNUMBERED；excerpt SHA256=`02fec2f77dbbe325687492c55adca4474054844b65aa709378a742455cdbae7a`。
  > As with resist, there are two types of etch: 'wet' and 'dry'. Dry etching uses gases to define the exposed pattern on the wafer. Wet etching uses chemical baths to wash the wafer.
- Conflicting evidence：冻结 A/B 未报告本限定范围内的未解决实质证据冲突；不等于完整文献已穷尽。

- **SYSTEM_RECOMMENDED_DECISION** = CREATE
推荐理由（非人工裁决）：双方支持该独立身份，同时一致要求结构性高影响的人类审查；建议确认原候选 CREATE 方向及其图谱影响，尚不授权执行。

HUMAN_USER_DECISION = [PENDING]

OPTIONS:

- [ ] CREATE
- [ ] REUSE <NODE_ID>
- [ ] DEFER
- [ ] REJECT

---

<a id="sc-cn-0072"></a>
### 023 · SC-CN-0072 · Chemical Mechanical Planarization

- **ITEM_NUMBER** = 23
- **ITEM_ID** = SC-CN-0072
- **OBJECT_TYPE** = nodes
- **DOMAIN** = 03_fab_process_equipment
- **CURRENT_NATIVE_OPERATION** = CREATE NODE_D350AEDB638F3572
- **CURRENT_STATUS** = CREATE
- **WHY_IN_HUMAN_PACKET** = R07；REVIEWER_UNRESOLVED_HUMAN_REQUIRED
- **RISK_RULES** = R07 新增高影响Node
- **MANDATORY_TRIGGER** = R07；REVIEWER_UNRESOLVED_HUMAN_REQUIRED
- **SAMPLE_STATUS** = NOT_SAMPLED
- **SAMPLED_FOR_QUALITY_CONTROL** = false

- **SOURCE_ID / SOURCE_NAME** = SC-PHYS-B33C40EBCB5756F7 / SRC_1DD38DEB69830E97 / Strengthening the Global Semiconductor Supply Chain in an Uncertain Era
Source provenance：Semiconductor Industry Association (SIA) / Boston Consulting Group (BCG)；publication=2021-04；edition=；as_of=2021-04；source SHA256=`b33c40ebcb5756f76e887ba2664f97736252e68ba7bfbedc2d628ce2d7cbc08d`。
- **SOURCE_ID / SOURCE_NAME** = SC-PHYS-C5B6DC633E156218 / SRC_AC29CFEE56F74F5B / Testimony of the Semiconductor Industry Association before the Senate Committee on Environment & Public Works (March 4, 2026)
Source provenance：Semiconductor Industry Association (SIA)；publication=2026-03-04；edition=；as_of=2026-03-04；source SHA256=`c5b6dc633e156218eb950f2dee88f43fbdcc4fc1744a5924f12b977f5cb7df71`。

**CANDIDATE_SUMMARY**

- Node 类型：Technology
- 名称：Chemical Mechanical Planarization
- 已有身份：NODE_D350AEDB638F3572
- 边界说明：Source支持可复用的持久研究对象，未命中现有规范名或已登记别名。
- Planned native target：NODE_D350AEDB638F3572 → SC-CN-0072 / Chemical Mechanical Planarization / Technology；这是候选映射，不是已存在或获批准的目录对象。

**AI REVIEW A**

- recommendation：HUMAN_REQUIRED；native_decision：CREATE
- proposed operation / canonical target：CREATE；范围/说明: IDENTITY_RECOMMENDATION_ONLY; Chemical Mechanical Planarization / Technology; no canonical mutation
- confidence：HIGH
- reason：CMP 定义和逐层平坦化机制清楚，不能等同已有 Advanced Packaging CMP Equipment；它支撑浆料/垫/制造流程关键依赖。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-E1426DD81060C643, SC-EV-AC0F07D293403E3F

**AI REVIEW B**

- recommendation：HUMAN_REQUIRED；native_decision：CREATE
- proposed operation / canonical target：CREATE；范围/说明: IDENTITY_ONLY; 03_fab_process_equipment; Chemical Mechanical Planarization; Technology
- confidence：HIGH
- reason：CMP有明确全称与化学物理平坦化过程；SC-RL-0038/0039以此区分slurry和pad，不能复用CMP设备身份。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-E1426DD81060C643, SC-EV-AC0F07D293403E3F

**A/B RECONCILIATION**

- frozen status：A_B_SUBSTANTIVE_AGREEMENT
- 实质分歧：无；措辞、附注或不改变风险路由的置信度差异不改原冻结一致结论。

**EVIDENCE SUMMARY**

- Supporting facts：下列有来源的节选支持本项讨论的对象/命题；支持范围及未解决条件已在上方 A/B reason 中逐项说明。
- SC-EV-AC0F07D293403E3F / SC-PHYS-B33C40EBCB5756F7 / PDF p.22 / Materials / printed p.22；excerpt SHA256=`ea77f5c7e0a3d498990812dddae5bcb8d8499c223d56d919533e339b9714c01f`。
  > Chemical Mechanical Planarization (CMP) slurries: Materials used for polishing the surface of the wafer after the film deposition step to provide a flat surface.
- SC-EV-E1426DD81060C643 / SC-PHYS-C5B6DC633E156218 / PDF p.5 / II / Back-End Fabrication / CMP / printed p.5；excerpt SHA256=`35b1994c551b3073ed773b253b0c157a5498ed77e2343c093908bd4df7185ea2`。
  > Chemical Mechanical Planarization (CMP): Between many deposition and metallization layers throughout the back-end process, chemical mechanical planarization (CMP) uses chemical and physical forces to create a microscopically flat surface for each successive layer of circuit features. A polishing pad with a liquid chemical called a “slurry” polishes the wafer surface until the desired nanometer topography is achieved on the uppermost exposed layer.
- Conflicting evidence：冻结 A/B 未报告本限定范围内的未解决实质证据冲突；不等于完整文献已穷尽。

- **SYSTEM_RECOMMENDED_DECISION** = CREATE
推荐理由（非人工裁决）：双方支持该独立身份，同时一致要求结构性高影响的人类审查；建议确认原候选 CREATE 方向及其图谱影响，尚不授权执行。

HUMAN_USER_DECISION = [PENDING]

OPTIONS:

- [ ] CREATE
- [ ] REUSE <NODE_ID>
- [ ] DEFER
- [ ] REJECT

---

<a id="sc-cn-0094"></a>
### 024 · SC-CN-0094 · FinFET

- **ITEM_NUMBER** = 24
- **ITEM_ID** = SC-CN-0094
- **OBJECT_TYPE** = nodes
- **DOMAIN** = 04_device_scaling_memory
- **CURRENT_NATIVE_OPERATION** = CREATE NODE_C082D7A3DD4FF090
- **CURRENT_STATUS** = CREATE
- **WHY_IN_HUMAN_PACKET** = R07；REVIEWER_UNRESOLVED_HUMAN_REQUIRED
- **RISK_RULES** = R07 新增高影响Node
- **MANDATORY_TRIGGER** = R07；REVIEWER_UNRESOLVED_HUMAN_REQUIRED
- **SAMPLE_STATUS** = NOT_SAMPLED
- **SAMPLED_FOR_QUALITY_CONTROL** = false

- **SOURCE_ID / SOURCE_NAME** = SC-PHYS-49A1D3B42E458985 / SRC_96EC545507C25F9F / 2024 IRDS — More Moore
Source provenance：IEEE International Roadmap for Devices and Systems (IRDS)；publication=；edition=2024；as_of=2024；source SHA256=`49a1d3b42e45898555490e602170876e22d1ccf8d7c17711e436d8db36322fa6`。

**CANDIDATE_SUMMARY**

- Node 类型：Technology
- 名称：FinFET
- 已有身份：NODE_C082D7A3DD4FF090
- 边界说明：器件结构族，不等同具体工艺节点；Source中的演进年份不作当前状态。
- Planned native target：NODE_C082D7A3DD4FF090 → SC-CN-0094 / FinFET / Technology；这是候选映射，不是已存在或获批准的目录对象。

**AI REVIEW A**

- recommendation：HUMAN_REQUIRED；native_decision：CREATE
- proposed operation / canonical target：CREATE；范围/说明: IDENTITY_RECOMMENDATION_ONLY; FinFET / Technology; no canonical mutation
- confidence：HIGH
- reason：IRDS 明确 FinFET 器件架构身份，年份只是路线图语境；承接演进与 GAA 预测的关键技术依赖，需结构锚点审核。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-19830FDE957518FD

**AI REVIEW B**

- recommendation：HUMAN_REQUIRED；native_decision：CREATE
- proposed operation / canonical target：CREATE；范围/说明: IDENTITY_ONLY; 04_device_scaling_memory; FinFET; Technology
- confidence：HIGH
- reason：FinFET被直接称器件架构，区别任何具体工艺代际；SC-CL-0001路线图归属依赖该关键技术锚点。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-19830FDE957518FD

**A/B RECONCILIATION**

- frozen status：A_B_SUBSTANTIVE_AGREEMENT
- 实质分歧：无；措辞、附注或不改变风险路由的置信度差异不改原冻结一致结论。

**EVIDENCE SUMMARY**

- Supporting facts：下列有来源的节选支持本项讨论的对象/命题；支持范围及未解决条件已在上方 A/B reason 中逐项说明。
- SC-EV-19830FDE957518FD / SC-PHYS-49A1D3B42E458985 / PDF p.14 / 4.2 Performance Boosters / printed p.9；excerpt SHA256=`1100f9816944d063c22c62b8752fecc2315c33c30d4dcec9cc01ed9a4812701b`。
  > FinFET has remained as the key device architecture that could sustain scaling until 2025.
- Conflicting evidence：冻结 A/B 未报告本限定范围内的未解决实质证据冲突；不等于完整文献已穷尽。

- **SYSTEM_RECOMMENDED_DECISION** = CREATE
推荐理由（非人工裁决）：双方支持该独立身份，同时一致要求结构性高影响的人类审查；建议确认原候选 CREATE 方向及其图谱影响，尚不授权执行。

HUMAN_USER_DECISION = [PENDING]

OPTIONS:

- [ ] CREATE
- [ ] REUSE <NODE_ID>
- [ ] DEFER
- [ ] REJECT

---

<a id="sc-cn-0100"></a>
### 025 · SC-CN-0100 · Nonvolatile Memory

- **ITEM_NUMBER** = 25
- **ITEM_ID** = SC-CN-0100
- **OBJECT_TYPE** = nodes
- **DOMAIN** = 04_device_scaling_memory
- **CURRENT_NATIVE_OPERATION** = CREATE NODE_00C120377853665C
- **CURRENT_STATUS** = CREATE
- **WHY_IN_HUMAN_PACKET** = R07；REVIEWER_UNRESOLVED_HUMAN_REQUIRED
- **RISK_RULES** = R07 新增高影响Node
- **MANDATORY_TRIGGER** = R07；REVIEWER_UNRESOLVED_HUMAN_REQUIRED
- **SAMPLE_STATUS** = NOT_SAMPLED
- **SAMPLED_FOR_QUALITY_CONTROL** = false

- **SOURCE_ID / SOURCE_NAME** = SC-PHYS-49A1D3B42E458985 / SRC_96EC545507C25F9F / 2024 IRDS — More Moore
Source provenance：IEEE International Roadmap for Devices and Systems (IRDS)；publication=；edition=2024；as_of=2024；source SHA256=`49a1d3b42e45898555490e602170876e22d1ccf8d7c17711e436d8db36322fa6`。

**CANDIDATE_SUMMARY**

- Node 类型：Segment
- 名称：Nonvolatile Memory
- 已有身份：NODE_00C120377853665C
- 边界说明：Source支持可复用的持久研究对象，未命中现有规范名或已登记别名。
- Planned native target：NODE_00C120377853665C → SC-CN-0100 / Nonvolatile Memory / Segment；这是候选映射，不是已存在或获批准的目录对象。

**AI REVIEW A**

- recommendation：HUMAN_REQUIRED；native_decision：CREATE
- proposed operation / canonical target：CREATE；范围/说明: IDENTITY_RECOMMENDATION_ONLY; Nonvolatile Memory / Segment; no canonical mutation
- confidence：HIGH
- reason：IRDS 明列非易失存储的 Flash/非电荷存储分类，较 NOR Flash 广；新分类锚点会组织既有 NOR 与新增存储关系。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-288A875770100378

**AI REVIEW B**

- recommendation：HUMAN_REQUIRED；native_decision：CREATE
- proposed operation / canonical target：CREATE；范围/说明: IDENTITY_ONLY; 04_device_scaling_memory; Nonvolatile Memory; Segment
- confidence：HIGH
- reason：非易失存储的Flash/非电荷分支分类明确；SC-RL-0006及0009至0012依赖新的分类父层。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-288A875770100378

**A/B RECONCILIATION**

- frozen status：A_B_SUBSTANTIVE_AGREEMENT
- 实质分歧：无；措辞、附注或不改变风险路由的置信度差异不改原冻结一致结论。

**EVIDENCE SUMMARY**

- Supporting facts：下列有来源的节选支持本项讨论的对象/命题；支持范围及未解决条件已在上方 A/B reason 中逐项说明。
- SC-EV-288A875770100378 / SC-PHYS-49A1D3B42E458985 / PDF p.27 / 5 Nonvolatile Memory / printed p.22；excerpt SHA256=`0d6eee3a3851d1bf15c3869444bf496d00cde00a9ff7f0fedfae6be103233f5a`。
  > Nonvolatile memory may be divided into two large categories—Flash memories (NAND Flash and NOR Flash), and non-charge-based-storage memories.
- Conflicting evidence：冻结 A/B 未报告本限定范围内的未解决实质证据冲突；不等于完整文献已穷尽。

- **SYSTEM_RECOMMENDED_DECISION** = CREATE
推荐理由（非人工裁决）：双方支持该独立身份，同时一致要求结构性高影响的人类审查；建议确认原候选 CREATE 方向及其图谱影响，尚不授权执行。

HUMAN_USER_DECISION = [PENDING]

OPTIONS:

- [ ] CREATE
- [ ] REUSE <NODE_ID>
- [ ] DEFER
- [ ] REJECT

---

<a id="sc-cn-0101"></a>
### 026 · SC-CN-0101 · Flash Memory

- **ITEM_NUMBER** = 26
- **ITEM_ID** = SC-CN-0101
- **OBJECT_TYPE** = nodes
- **DOMAIN** = 04_device_scaling_memory
- **CURRENT_NATIVE_OPERATION** = CREATE NODE_72FEF7A4F79F7EE7
- **CURRENT_STATUS** = CREATE
- **WHY_IN_HUMAN_PACKET** = R07；REVIEWER_UNRESOLVED_HUMAN_REQUIRED
- **RISK_RULES** = R07 新增高影响Node
- **MANDATORY_TRIGGER** = R07；REVIEWER_UNRESOLVED_HUMAN_REQUIRED
- **SAMPLE_STATUS** = NOT_SAMPLED
- **SAMPLED_FOR_QUALITY_CONTROL** = false

- **SOURCE_ID / SOURCE_NAME** = SC-PHYS-49A1D3B42E458985 / SRC_96EC545507C25F9F / 2024 IRDS — More Moore
Source provenance：IEEE International Roadmap for Devices and Systems (IRDS)；publication=；edition=2024；as_of=2024；source SHA256=`49a1d3b42e45898555490e602170876e22d1ccf8d7c17711e436d8db36322fa6`。

**CANDIDATE_SUMMARY**

- Node 类型：Product
- 名称：Flash Memory
- 已有身份：NODE_72FEF7A4F79F7EE7
- 边界说明：Source支持可复用的持久研究对象，未命中现有规范名或已登记别名。
- Planned native target：NODE_72FEF7A4F79F7EE7 → SC-CN-0101 / Flash Memory / Product；这是候选映射，不是已存在或获批准的目录对象。

**AI REVIEW A**

- recommendation：HUMAN_REQUIRED；native_decision：CREATE
- proposed operation / canonical target：CREATE；范围/说明: IDENTITY_RECOMMENDATION_ONLY; Flash Memory / Product; no canonical mutation
- confidence：HIGH
- reason：Flash 包含 NAND 和 NOR 的父产品族明确，不能复用 NOR；新建将建立已有 NOR 的上层依赖结构。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-288A875770100378

**AI REVIEW B**

- recommendation：HUMAN_REQUIRED；native_decision：CREATE
- proposed operation / canonical target：CREATE；范围/说明: IDENTITY_ONLY; 04_device_scaling_memory; Flash Memory; Product
- confidence：HIGH
- reason：Flash原文包含NAND与NOR，目录NOR仅子类；SC-RL-0007将现有NOR关联新父节点，结构影响明确。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-288A875770100378

**A/B RECONCILIATION**

- frozen status：A_B_SUBSTANTIVE_AGREEMENT
- 实质分歧：无；措辞、附注或不改变风险路由的置信度差异不改原冻结一致结论。

**EVIDENCE SUMMARY**

- Supporting facts：下列有来源的节选支持本项讨论的对象/命题；支持范围及未解决条件已在上方 A/B reason 中逐项说明。
- SC-EV-288A875770100378 / SC-PHYS-49A1D3B42E458985 / PDF p.27 / 5 Nonvolatile Memory / printed p.22；excerpt SHA256=`0d6eee3a3851d1bf15c3869444bf496d00cde00a9ff7f0fedfae6be103233f5a`。
  > Nonvolatile memory may be divided into two large categories—Flash memories (NAND Flash and NOR Flash), and non-charge-based-storage memories.
- Conflicting evidence：冻结 A/B 未报告本限定范围内的未解决实质证据冲突；不等于完整文献已穷尽。

- **SYSTEM_RECOMMENDED_DECISION** = CREATE
推荐理由（非人工裁决）：双方支持该独立身份，同时一致要求结构性高影响的人类审查；建议确认原候选 CREATE 方向及其图谱影响，尚不授权执行。

HUMAN_USER_DECISION = [PENDING]

OPTIONS:

- [ ] CREATE
- [ ] REUSE <NODE_ID>
- [ ] DEFER
- [ ] REJECT

---

<a id="sc-cn-0107"></a>
### 027 · SC-CN-0107 · EUV Lithography

- **ITEM_NUMBER** = 27
- **ITEM_ID** = SC-CN-0107
- **OBJECT_TYPE** = nodes
- **DOMAIN** = 05_lithography_patterning
- **CURRENT_NATIVE_OPERATION** = CREATE NODE_FFD2607342B3B752
- **CURRENT_STATUS** = CREATE
- **WHY_IN_HUMAN_PACKET** = R07；REVIEWER_UNRESOLVED_HUMAN_REQUIRED
- **RISK_RULES** = R07 新增高影响Node
- **MANDATORY_TRIGGER** = R07；REVIEWER_UNRESOLVED_HUMAN_REQUIRED
- **SAMPLE_STATUS** = NOT_SAMPLED
- **SAMPLED_FOR_QUALITY_CONTROL** = false

- **SOURCE_ID / SOURCE_NAME** = SC-PHYS-318D85A127B5B6DF / SRC_FFD94DB31A0E9C0A / 2025 IRDS — Lithography and Patterning
Source provenance：IEEE International Roadmap for Devices and Systems (IRDS)；publication=；edition=2025；as_of=2025；source SHA256=`318d85a127b5b6dfa7b3c1330ae20b18d63660a1fa8c8bdfdd7b478844e145ed`。

**CANDIDATE_SUMMARY**

- Node 类型：Technology
- 名称：EUV Lithography
- 已有身份：NODE_FFD2607342B3B752
- 边界说明：光刻技术，不等同具体EUV scanner设备。
- Planned native target：NODE_FFD2607342B3B752 → SC-CN-0107 / EUV Lithography / Technology；这是候选映射，不是已存在或获批准的目录对象。

**AI REVIEW A**

- recommendation：HUMAN_REQUIRED；native_decision：CREATE
- proposed operation / canonical target：CREATE；范围/说明: IDENTITY_RECOMMENDATION_ONLY; EUV Lithography / Technology; no canonical mutation
- confidence：HIGH
- reason：IRDS EUV 材料段确认生产用 EUV 工艺存在，Technology 不等于 scanner；是 high-NA 演进和光刻基线的关键依赖。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-2CCA00E79D91DD12

**AI REVIEW B**

- recommendation：HUMAN_REQUIRED；native_decision：CREATE
- proposed operation / canonical target：CREATE；范围/说明: IDENTITY_ONLY; 05_lithography_patterning; EUV Lithography; Technology
- confidence：HIGH
- reason：EUV制造技术有0.33NA材料语境支持，区别scanner设备；SC-CL-0002和光刻基线以其承载代际范围，需关键技术锚点人审。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-2CCA00E79D91DD12

**A/B RECONCILIATION**

- frozen status：A_B_SUBSTANTIVE_AGREEMENT
- 实质分歧：无；措辞、附注或不改变风险路由的置信度差异不改原冻结一致结论。

**EVIDENCE SUMMARY**

- Supporting facts：下列有来源的节选支持本项讨论的对象/命题；支持范围及未解决条件已在上方 A/B reason 中逐项说明。
- SC-EV-2CCA00E79D91DD12 / SC-PHYS-318D85A127B5B6DF / PDF p.17 / EUV Resist Materials / printed p.12；excerpt SHA256=`bc095b935738e34224f2f6e6414ede5e7910cf5ebec73265c08f007fc60c14aa`。
  > Currently, the EUV used in manufacturing is at 0.33NA and chemically amplified materials are in use for most EUV levels in production and metal oxide resists are used for some memory levels.
- Conflicting evidence：冻结 A/B 未报告本限定范围内的未解决实质证据冲突；不等于完整文献已穷尽。

- **SYSTEM_RECOMMENDED_DECISION** = CREATE
推荐理由（非人工裁决）：双方支持该独立身份，同时一致要求结构性高影响的人类审查；建议确认原候选 CREATE 方向及其图谱影响，尚不授权执行。

HUMAN_USER_DECISION = [PENDING]

OPTIONS:

- [ ] CREATE
- [ ] REUSE <NODE_ID>
- [ ] DEFER
- [ ] REJECT

---

<a id="sc-cn-0112"></a>
### 028 · SC-CN-0112 · Interposer

- **ITEM_NUMBER** = 28
- **ITEM_ID** = SC-CN-0112
- **OBJECT_TYPE** = nodes
- **DOMAIN** = 05_lithography_patterning
- **CURRENT_NATIVE_OPERATION** = CREATE NODE_C37B83D6D0B8A843
- **CURRENT_STATUS** = CREATE
- **WHY_IN_HUMAN_PACKET** = R07；REVIEWER_UNRESOLVED_HUMAN_REQUIRED
- **RISK_RULES** = R07 新增高影响Node
- **MANDATORY_TRIGGER** = R07；REVIEWER_UNRESOLVED_HUMAN_REQUIRED
- **SAMPLE_STATUS** = NOT_SAMPLED
- **SAMPLED_FOR_QUALITY_CONTROL** = false

- **SOURCE_ID / SOURCE_NAME** = SC-PHYS-318D85A127B5B6DF / SRC_FFD94DB31A0E9C0A / 2025 IRDS — Lithography and Patterning
Source provenance：IEEE International Roadmap for Devices and Systems (IRDS)；publication=；edition=2025；as_of=2025；source SHA256=`318d85a127b5b6dfa7b3c1330ae20b18d63660a1fa8c8bdfdd7b478844e145ed`。

**CANDIDATE_SUMMARY**

- Node 类型：Product
- 名称：Interposer
- 已有身份：NODE_C37B83D6D0B8A843
- 边界说明：中间互连/节距转换基板，非Package Substrate的同义词。
- Planned native target：NODE_C37B83D6D0B8A843 → SC-CN-0112 / Interposer / Product；这是候选映射，不是已存在或获批准的目录对象。

**AI REVIEW A**

- recommendation：HUMAN_REQUIRED；native_decision：CREATE
- proposed operation / canonical target：CREATE；范围/说明: IDENTITY_RECOMMENDATION_ONLY; Interposer / Product; no canonical mutation
- confidence：HIGH
- reason：interposer 定义为 die 间互连/节距转换中间基板，与 package substrate 不同；是既有 Silicon/RDL Interposer 的共同结构锚点。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-55BA223EDE3A8F9F

**AI REVIEW B**

- recommendation：HUMAN_REQUIRED；native_decision：CREATE
- proposed operation / canonical target：CREATE；范围/说明: IDENTITY_ONLY; 05_lithography_patterning; Interposer; Product
- confidence：HIGH
- reason：interposer为中间互连/节距转换基板，有直接定义；SC-RL-0017/0018让既有硅/RDL中介层依赖新父层。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-55BA223EDE3A8F9F

**A/B RECONCILIATION**

- frozen status：A_B_SUBSTANTIVE_AGREEMENT
- 实质分歧：无；措辞、附注或不改变风险路由的置信度差异不改原冻结一致结论。

**EVIDENCE SUMMARY**

- Supporting facts：下列有来源的节选支持本项讨论的对象/命题；支持范围及未解决条件已在上方 A/B reason 中逐项说明。
- SC-EV-55BA223EDE3A8F9F / SC-PHYS-318D85A127B5B6DF / PDF p.21 / Packaging Lithography / printed p.16；excerpt SHA256=`9ac08ea2ffa05a5d23f978a2abc0efadf8673d327b374759bd424f32b7e760c9`。
  > Interposers are defined as intermediate substrates to realize interconnections between multiple dies and or to transform pitches between dice and a package substrate.
- Conflicting evidence：冻结 A/B 未报告本限定范围内的未解决实质证据冲突；不等于完整文献已穷尽。

- **SYSTEM_RECOMMENDED_DECISION** = CREATE
推荐理由（非人工裁决）：双方支持该独立身份，同时一致要求结构性高影响的人类审查；建议确认原候选 CREATE 方向及其图谱影响，尚不授权执行。

HUMAN_USER_DECISION = [PENDING]

OPTIONS:

- [ ] CREATE
- [ ] REUSE <NODE_ID>
- [ ] DEFER
- [ ] REJECT

---

<a id="sc-cn-0115"></a>
### 029 · SC-CN-0115 · Semiconductor Metrology

- **ITEM_NUMBER** = 29
- **ITEM_ID** = SC-CN-0115
- **OBJECT_TYPE** = nodes
- **DOMAIN** = 06_metrology_yield_factory
- **CURRENT_NATIVE_OPERATION** = UNDECIDED（没有已填写的人类原生决定）
- **CURRENT_STATUS** = REVIEW
- **WHY_IN_HUMAN_PACKET** = R07；REVIEWER_UNRESOLVED_HUMAN_REQUIRED
- **RISK_RULES** = R07 新增高影响Node
- **MANDATORY_TRIGGER** = R07；REVIEWER_UNRESOLVED_HUMAN_REQUIRED
- **SAMPLE_STATUS** = NOT_SAMPLED
- **SAMPLED_FOR_QUALITY_CONTROL** = false

- **SOURCE_ID / SOURCE_NAME** = SC-PHYS-AEDD7CB34D12EF15 / SRC_ECAE5FF71F5DE095 / 2024 IRDS — Metrology
Source provenance：IEEE International Roadmap for Devices and Systems (IRDS)；publication=；edition=2024；as_of=2024；source SHA256=`aedd7cb34d12ef15b799ed9a0f6326840a4551ddc7c6600732c6ae82ab6e93b6`。
- **SOURCE_ID / SOURCE_NAME** = SC-PHYS-B33C40EBCB5756F7 / SRC_1DD38DEB69830E97 / Strengthening the Global Semiconductor Supply Chain in an Uncertain Era
Source provenance：Semiconductor Industry Association (SIA) / Boston Consulting Group (BCG)；publication=2021-04；edition=；as_of=2021-04；source SHA256=`b33c40ebcb5756f76e887ba2664f97736252e68ba7bfbedc2d628ce2d7cbc08d`。

**CANDIDATE_SUMMARY**

- Node 类型：Technology
- 名称：Semiconductor Metrology
- 备选身份：NODE_20260817_DA450C32
- 边界说明：测量方法/功能域；不与半导体计量Equipment混型。
- Canonical state：NODE_20260817_DA450C32 = Advanced Packaging 3D Metrology Equipment；type=Equipment；status=active。

**AI REVIEW A**

- recommendation：HUMAN_REQUIRED；native_decision：CREATE
- proposed operation / canonical target：CREATE；范围/说明: IDENTITY_RECOMMENDATION_ONLY; Semiconductor Metrology / Technology; no canonical mutation
- confidence：HIGH
- reason：IRDS 测量方法范围和制造过程控制共同支持 metrology 技术总类，区别已有 Advanced Packaging 3D Metrology Equipment；该总类是计量基线依赖。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-4AAF8C92F8CF20F0, SC-EV-8641CA42AE8B686A

**AI REVIEW B**

- recommendation：HUMAN_REQUIRED；native_decision：CREATE
- proposed operation / canonical target：CREATE；范围/说明: IDENTITY_ONLY; 06_metrology_yield_factory; Semiconductor Metrology; Technology
- confidence：HIGH
- reason：计量方法范围含CD/overlay/材料/互连而非仪器型号；SC-BV-0006以此为中心，不能复用先进封装3D计量设备。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-4AAF8C92F8CF20F0, SC-EV-8641CA42AE8B686A

**A/B RECONCILIATION**

- frozen status：A_B_SUBSTANTIVE_AGREEMENT
- 实质分歧：无；措辞、附注或不改变风险路由的置信度差异不改原冻结一致结论。

**EVIDENCE SUMMARY**

- Supporting facts：下列有来源的节选支持本项讨论的对象/命题；支持范围及未解决条件已在上方 A/B reason 中逐项说明。
- SC-EV-4AAF8C92F8CF20F0 / SC-PHYS-AEDD7CB34D12EF15 / PDF p.10 / 2 Scope of Report / printed p.5；excerpt SHA256=`af82e9c1a8a297ea881710d07f9ed44ac480b56343dc94fc86d048319549176d`。
  > The scope includes metrology for critical dimensions (CDs), microscopy for 3D and high aspect ratio (HAR) pattern measurements, overlay measurements, lithography metrology, front-end processes metrology, on-chip interconnect metrology, inter- and intra-die interconnect metrology, materials characterization, metrology for emerging materials and devices, reference materials, and outside systems connectivity needs and challenges.
- SC-EV-8641CA42AE8B686A / SC-PHYS-B33C40EBCB5756F7 / PDF p.20 / Wafer processing and testing equipment / printed p.20；excerpt SHA256=`8ce3bc60a878c18c9e30876678457fc8625ab1910d0f9191e74aa8b9bc0ab4ca`。
  > Strict metrology and inspection processes using specialized equipment are therefore established at critical points of the semiconductor manufacturing process to ensure that a certain yield can be confirmed and maintained.
- Conflicting evidence：冻结 A/B 未报告本限定范围内的未解决实质证据冲突；不等于完整文献已穷尽。

- **SYSTEM_RECOMMENDED_DECISION** = CREATE
推荐理由（非人工裁决）：双方支持该独立身份，同时一致要求结构性高影响的人类审查；建议确认原候选 CREATE 方向及其图谱影响，尚不授权执行。

HUMAN_USER_DECISION = [PENDING]

OPTIONS:

- [ ] CREATE
- [ ] REUSE <NODE_ID>
- [ ] DEFER
- [ ] REJECT

---

<a id="sc-cn-0123"></a>
### 030 · SC-CN-0123 · Factory Integration

- **ITEM_NUMBER** = 30
- **ITEM_ID** = SC-CN-0123
- **OBJECT_TYPE** = nodes
- **DOMAIN** = 06_metrology_yield_factory
- **CURRENT_NATIVE_OPERATION** = CREATE NODE_0087FF33E12373CF
- **CURRENT_STATUS** = CREATE
- **WHY_IN_HUMAN_PACKET** = R07；REVIEWER_UNRESOLVED_HUMAN_REQUIRED
- **RISK_RULES** = R07 新增高影响Node
- **MANDATORY_TRIGGER** = R07；REVIEWER_UNRESOLVED_HUMAN_REQUIRED
- **SAMPLE_STATUS** = NOT_SAMPLED
- **SAMPLED_FOR_QUALITY_CONTROL** = false

- **SOURCE_ID / SOURCE_NAME** = SC-PHYS-4FA7140313FB3AF8 / SRC_15959FA40D6E85A4 / 2023 IRDS — Factory Integration
Source provenance：IEEE International Roadmap for Devices and Systems (IRDS)；publication=；edition=2023；as_of=2023；source SHA256=`4fa7140313fb3af883127c329599c4d8e6f4b9abfbe0976f4e8102ebe8c2587d`。

**CANDIDATE_SUMMARY**

- Node 类型：Technology
- 名称：Factory Integration
- 已有身份：NODE_0087FF33E12373CF
- 边界说明：IRDS晶圆/封装工厂系统集成，不等同具体Fab设施。
- Planned native target：NODE_0087FF33E12373CF → SC-CN-0123 / Factory Integration / Technology；这是候选映射，不是已存在或获批准的目录对象。

**AI REVIEW A**

- recommendation：HUMAN_REQUIRED；native_decision：CREATE
- proposed operation / canonical target：CREATE；范围/说明: IDENTITY_RECOMMENDATION_ONLY; Factory Integration / Technology; no canonical mutation
- confidence：HIGH
- reason：结合已核验来源标题 Factory Integration、FI scope 和工厂基线，身份锁定前后端制造系统集成；它组织 FICS/搬运/设施范围，是关键基线锚点。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-974C6AC2C5C6BE20

**AI REVIEW B**

- recommendation：HUMAN_REQUIRED；native_decision：CREATE
- proposed operation / canonical target：CREATE；范围/说明: IDENTITY_ONLY; 06_metrology_yield_factory; Factory Integration; Technology
- confidence：HIGH
- reason：FI范围为前后端微电子制造的系统集成，SC-BV-0007及其FICS控制框架依赖此结构锚点，不是具体厂房。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-974C6AC2C5C6BE20

**A/B RECONCILIATION**

- frozen status：A_B_SUBSTANTIVE_AGREEMENT
- 实质分歧：无；措辞、附注或不改变风险路由的置信度差异不改原冻结一致结论。

**EVIDENCE SUMMARY**

- Supporting facts：下列有来源的节选支持本项讨论的对象/命题；支持范围及未解决条件已在上方 A/B reason 中逐项说明。
- SC-EV-974C6AC2C5C6BE20 / SC-PHYS-4FA7140313FB3AF8 / PDF p.13 / 2.1 Introduction / Scope of Report / printed p.7；excerpt SHA256=`5781c6a6304cfd68ff6ef3799bd16be6b2f824042abe3c2e8d91f4220903e8c1`。
  > FI’s scope is microelectronic manufacturing or fabrication in front-end and back-end.
- Conflicting evidence：冻结 A/B 未报告本限定范围内的未解决实质证据冲突；不等于完整文献已穷尽。

- **SYSTEM_RECOMMENDED_DECISION** = CREATE
推荐理由（非人工裁决）：双方支持该独立身份，同时一致要求结构性高影响的人类审查；建议确认原候选 CREATE 方向及其图谱影响，尚不授权执行。

HUMAN_USER_DECISION = [PENDING]

OPTIONS:

- [ ] CREATE
- [ ] REUSE <NODE_ID>
- [ ] DEFER
- [ ] REJECT

---

<a id="sc-cn-0125"></a>
### 031 · SC-CN-0125 · Factory Information and Control System

- **ITEM_NUMBER** = 31
- **ITEM_ID** = SC-CN-0125
- **OBJECT_TYPE** = nodes
- **DOMAIN** = 06_metrology_yield_factory
- **CURRENT_NATIVE_OPERATION** = UNDECIDED（没有已填写的人类原生决定）
- **CURRENT_STATUS** = REVIEW
- **WHY_IN_HUMAN_PACKET** = R07；REVIEWER_UNRESOLVED_HUMAN_REQUIRED
- **RISK_RULES** = R07 新增高影响Node
- **MANDATORY_TRIGGER** = R07；REVIEWER_UNRESOLVED_HUMAN_REQUIRED
- **SAMPLE_STATUS** = NOT_SAMPLED
- **SAMPLED_FOR_QUALITY_CONTROL** = false

- **SOURCE_ID / SOURCE_NAME** = SC-PHYS-4FA7140313FB3AF8 / SRC_15959FA40D6E85A4 / 2023 IRDS — Factory Integration
Source provenance：IEEE International Roadmap for Devices and Systems (IRDS)；publication=；edition=2023；as_of=2023；source SHA256=`4fa7140313fb3af883127c329599c4d8e6f4b9abfbe0976f4e8102ebe8c2587d`。

**CANDIDATE_SUMMARY**

- Node 类型：Technology
- 名称：Factory Information and Control System
- 边界说明：软件/硬件/执行/控制的组合；Technology vs Product范围需审。

**AI REVIEW A**

- recommendation：HUMAN_REQUIRED；native_decision：CREATE
- proposed operation / canonical target：CREATE；范围/说明: IDENTITY_RECOMMENDATION_ONLY; Factory Information and Control System / Technology; no canonical mutation
- confidence：HIGH
- reason：小节及原文定义 FICS 为硬件软件、执行调度及过程控制组合，Technology 系统表达成立；是工厂集成基线与控制方法依赖的系统锚点。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-05E04AAA8644BBA6

**AI REVIEW B**

- recommendation：HUMAN_REQUIRED；native_decision：CREATE
- proposed operation / canonical target：CREATE；范围/说明: IDENTITY_ONLY; 06_metrology_yield_factory; Factory Information and Control System; Technology
- confidence：HIGH
- reason：FICS章节全称与硬软件/执行/调度/控制范围明确，可作系统技术架构；SC-BV-0007及SC-CL-0006的SPC集成解释依赖它。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-05E04AAA8644BBA6

**A/B RECONCILIATION**

- frozen status：A_B_SUBSTANTIVE_AGREEMENT
- 实质分歧：无；措辞、附注或不改变风险路由的置信度差异不改原冻结一致结论。

**EVIDENCE SUMMARY**

- Supporting facts：下列有来源的节选支持本项讨论的对象/命题；支持范围及未解决条件已在上方 A/B reason 中逐项说明。
- SC-EV-05E04AAA8644BBA6 / SC-PHYS-4FA7140313FB3AF8 / PDF p.27 / 5.5.1 Factory Information and Control Systems / Scope / printed p.21；excerpt SHA256=`1d5827116248957d54ed15cc666aefad50ee86780bb816df369b32498e9685c6`。
  > The scope of FICS includes computer hardware and software, manufacturing execution, decision support systems, factory scheduling, control of equipment and material handling systems, and process control.
- Conflicting evidence：冻结 A/B 未报告本限定范围内的未解决实质证据冲突；不等于完整文献已穷尽。

- **SYSTEM_RECOMMENDED_DECISION** = CREATE
推荐理由（非人工裁决）：双方支持该独立身份，同时一致要求结构性高影响的人类审查；建议确认原候选 CREATE 方向及其图谱影响，尚不授权执行。

HUMAN_USER_DECISION = [PENDING]

OPTIONS:

- [ ] CREATE
- [ ] REUSE <NODE_ID>
- [ ] DEFER
- [ ] REJECT

---

## SECTION B — A/B Substantive Disagreements

45 items

<a id="sc-al-0001"></a>
### 032 · SC-AL-0001 · DRAM

- **ITEM_NUMBER** = 32
- **ITEM_ID** = SC-AL-0001
- **OBJECT_TYPE** = aliases
- **DOMAIN** = semiconductor
- **CURRENT_NATIVE_OPERATION** = UNDECIDED（没有已填写的人类原生决定）
- **CURRENT_STATUS** = REVIEW
- **WHY_IN_HUMAN_PACKET** = R01_A_B_DISAGREEMENT；R02；R03；R04；R05；REVIEWER_UNRESOLVED_HUMAN_REQUIRED
- **RISK_RULES** = R01 A/B实质分歧；R02 低或必要UNKNOWN置信度；R03 证据缺口；R04 实质命题歧义；R05 身份冲突
- **MANDATORY_TRIGGER** = R01_A_B_DISAGREEMENT；R02；R03；R04；R05；REVIEWER_UNRESOLVED_HUMAN_REQUIRED
- **SAMPLE_STATUS** = NOT_SAMPLED
- **SAMPLED_FOR_QUALITY_CONTROL** = false

- **SOURCE_ID / SOURCE_NAME** = SC-PHYS-B33C40EBCB5756F7 / SRC_1DD38DEB69830E97 / Strengthening the Global Semiconductor Supply Chain in an Uncertain Era
Source provenance：Semiconductor Industry Association (SIA) / Boston Consulting Group (BCG)；publication=2021-04；edition=；as_of=2021-04；source SHA256=`b33c40ebcb5756f76e887ba2664f97736252e68ba7bfbedc2d628ce2d7cbc08d`。

**CANDIDATE_SUMMARY**

- 别名：DRAM
- 已占用所有者：[]
- 提议所有者：SC-CN-0010
- 提议所有者名称：Dynamic Random-Access Memory
- Candidate target：SC-CN-0010 = Dynamic Random-Access Memory；type=Product；frozen status=REVIEW；仍须目标自身授权。

**AI REVIEW A**

- recommendation：HUMAN_REQUIRED；native_decision：DEFER
- proposed operation / canonical target：DEFER；目标: SC-CN-0010 [Dynamic Random-Access Memory]；范围/说明: SEMICONDUCTOR_SOURCE_SCOPED_ALIAS_RECOMMENDATION; owner remains candidate until separately authorized
- confidence：LOW
- reason：仅见 DRAM 及其用途，无全称展开；owner 0010 的全称身份仍未解决，暂缓附加以免用缩写反证自己。
- evidence assessment：INSUFFICIENT；Evidence IDs：SC-EV-9F7D3244A0780DEA
- 必要置信度缺口：entity_resolution_clarity=LOW；evidence_directness=LOW；unit_scope_completeness=UNKNOWN

**AI REVIEW B**

- recommendation：HUMAN_REQUIRED；native_decision：DEFER
- proposed operation / canonical target：DEFER；目标: SC-CN-0010 [Dynamic Random-Access Memory]；范围/说明: ALIAS_IDENTITY_ONLY; DRAM -> Dynamic Random-Access Memory
- confidence：LOW
- reason：DRAM字面存在，但全称映射未在冻结摘录定义；SC-CN-0010规范身份本次仍暂缓，不能挂到Server DRAM代替。
- evidence assessment：INSUFFICIENT；Evidence IDs：SC-EV-9F7D3244A0780DEA
- 必要置信度缺口：entity_resolution_clarity=UNKNOWN；evidence_directness=LOW；unit_scope_completeness=LOW

**A/B RECONCILIATION**

- frozen status：A_B_DISAGREEMENT
- **DISAGREEMENT_TYPE** = 风险判定分歧 R05
- **NATIVE_OPERATION_CONFLICT** = false
- R05 身份冲突：A=FALSE；B=UNKNOWN。A依据：完整 327 节点及 760 别名目录中，未发现本建议产生的身份冲突；明确共享核心者复用。 B依据：规范身份或候选所有者定义未完备：（具体证据与边界见本项该审查者 reason）

**EVIDENCE SUMMARY**

- Supporting facts：下列有来源的节选支持本项讨论的对象/命题；支持范围及未解决条件已在上方 A/B reason 中逐项说明。
- SC-EV-9F7D3244A0780DEA / SC-PHYS-B33C40EBCB5756F7 / PDF p.9 / Memory / printed p.9；excerpt SHA256=`3e0f10608491e28b4ca65b393efba69601bbd0ab43166ecfceffb1f812be69b2`。
  > DRAM is used to store the data or program code needed by a computer processor to function.
- Conflicting evidence / unresolved scope：上述 A/B 理由和差异列出已记录的冲突或缺口；未补造反证，也未因省略原文而解除冻结风险。

- **SYSTEM_RECOMMENDED_DECISION** = DEFER
推荐理由（非人工裁决）：双方均建议暂缓；风险标签或置信度差异没有补齐身份/类型/证据缺口。优先保留候选等待人工澄清，不强制选择新的目标、关系类型或对象边界。

HUMAN_USER_DECISION = [PENDING]

OPTIONS:

- [ ] ACCEPT_OWNER <NODE_ID 或已确认候选 ID>（原生 ATTACH）
- [ ] DEFER
- [ ] REJECT

---

<a id="sc-al-0009"></a>
### 033 · SC-AL-0009 · Reticle

- **ITEM_NUMBER** = 33
- **ITEM_ID** = SC-AL-0009
- **OBJECT_TYPE** = aliases
- **DOMAIN** = semiconductor
- **CURRENT_NATIVE_OPERATION** = UNDECIDED（没有已填写的人类原生决定）
- **CURRENT_STATUS** = REVIEW
- **WHY_IN_HUMAN_PACKET** = R01_A_B_DISAGREEMENT；R02；R04；REVIEWER_UNRESOLVED_HUMAN_REQUIRED
- **RISK_RULES** = R01 A/B实质分歧；R02 低或必要UNKNOWN置信度；R04 实质命题歧义
- **MANDATORY_TRIGGER** = R01_A_B_DISAGREEMENT；R02；R04；REVIEWER_UNRESOLVED_HUMAN_REQUIRED
- **SAMPLE_STATUS** = NOT_SAMPLED
- **SAMPLED_FOR_QUALITY_CONTROL** = false

- **SOURCE_ID / SOURCE_NAME** = SC-PHYS-87B4665C30781057 / SRC_ADCEE4236B19B5F2 / Six Crucial Steps in Semiconductor Manufacturing
Source provenance：ASML；publication=2023-10-04；edition=；as_of=2023-10-04；source SHA256=`87b4665c3078105792ca70f18964c938976b72f2dcf0d19379b034d5d6f205f9`。
- **SOURCE_ID / SOURCE_NAME** = SC-PHYS-B33C40EBCB5756F7 / SRC_1DD38DEB69830E97 / Strengthening the Global Semiconductor Supply Chain in an Uncertain Era
Source provenance：Semiconductor Industry Association (SIA) / Boston Consulting Group (BCG)；publication=2021-04；edition=；as_of=2021-04；source SHA256=`b33c40ebcb5756f76e887ba2664f97736252e68ba7bfbedc2d628ce2d7cbc08d`。
- **SOURCE_ID / SOURCE_NAME** = SC-PHYS-C5B6DC633E156218 / SRC_AC29CFEE56F74F5B / Testimony of the Semiconductor Industry Association before the Senate Committee on Environment & Public Works (March 4, 2026)
Source provenance：Semiconductor Industry Association (SIA)；publication=2026-03-04；edition=；as_of=2026-03-04；source SHA256=`c5b6dc633e156218eb950f2dee88f43fbdcc4fc1744a5924f12b977f5cb7df71`。

**CANDIDATE_SUMMARY**

- 别名：Reticle
- 已占用所有者：[]
- 提议所有者：SC-CN-0053
- 提议所有者名称：Photomask
- Planned native target：NODE_72297BCF151CC0EF → SC-CN-0053 / Photomask / Product；这是候选映射，不是已存在或获批准的目录对象。
- Candidate target：SC-CN-0053 = Photomask；type=Product；frozen status=CREATE；仍须目标自身授权。

**AI REVIEW A**

- recommendation：HUMAN_REQUIRED；native_decision：DEFER
- proposed operation / canonical target：DEFER；目标: SC-CN-0053 [Photomask]；范围/说明: SEMICONDUCTOR_SOURCE_SCOPED_ALIAS_RECOMMENDATION; owner remains candidate until separately authorized
- confidence：LOW
- reason：两段描述 photomask/reticle 有相同成像职责，却未明确所有场景互为同义；reticle 可为投影掩模子类，owner 0053 的无范围 alias 需审。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-9393F2354C64C727, SC-EV-FD3B14BF5F4E693A
- 必要置信度缺口：entity_resolution_clarity=LOW；outcome_completeness=LOW

**AI REVIEW B**

- recommendation：ACCEPT_WITH_REVIEW_NOTE；native_decision：ATTACH
- proposed operation / canonical target：ATTACH；目标: SC-CN-0053 [Photomask]；范围/说明: ALIAS_IDENTITY_ONLY; Reticle -> Photomask; optical lithography mask/reticle context
- confidence：MEDIUM
- reason：Photomask定义及SIA光刻段mask or reticle支持光学曝光语境同物；alias限定该语境，不推广所有mask，目标候选待建档。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-9393F2354C64C727, SC-EV-FD3B14BF5F4E693A, SC-EV-67EC75515BB09180

**A/B RECONCILIATION**

- frozen status：A_B_DISAGREEMENT
- **DISAGREEMENT_TYPE** = DEFER vs ATTACH；ACCEPT/NOTE vs HUMAN_REQUIRED；风险判定分歧 R02；风险判定分歧 R04；必要置信度判定分歧
- **NATIVE_OPERATION_CONFLICT** = true
- 原生操作：A=DEFER；B=ATTACH
- 推荐路由：A=HUMAN_REQUIRED；B=ACCEPT_WITH_REVIEW_NOTE
- R02 低或必要UNKNOWN置信度：A=TRUE；B=FALSE。A依据：按 LOW > UNKNOWN > MEDIUM > HIGH 聚合，本条为 LOW。 B依据：九维按LOW > 必要UNKNOWN > MEDIUM > HIGH聚合为MEDIUM。
- R04 实质命题歧义：A=TRUE；B=FALSE。A依据：（具体证据与边界见本项该审查者 reason） B依据：在明确范围下未见两个会改变本次推荐的证据解释；（具体证据与边界见本项该审查者 reason）
- 聚合置信度：A=LOW；B=MEDIUM

**EVIDENCE SUMMARY**

- Supporting facts：下列有来源的节选支持本项讨论的对象/命题；支持范围及未解决条件已在上方 A/B reason 中逐项说明。
- SC-EV-67EC75515BB09180 / SC-PHYS-C5B6DC633E156218 / PDF p.4 / II / Front-End Fabrication / Photolithography / printed p.4；excerpt SHA256=`d49de79df3fb0e595282e9746bcd100459e0a41920f737ed1446f4908192c3a1`。
  > A stepper or scanner (using deep ultraviolet or extreme ultraviolet light) aligns the wafer to a glass photomask and projects intense light through the mask or reticle, exposing the photoresist with the pattern.
- SC-EV-9393F2354C64C727 / SC-PHYS-B33C40EBCB5756F7 / PDF p.22 / Materials / printed p.22；excerpt SHA256=`def2d7634fa4482f5819e198a1df17516c435020372e9c614ece45c4d72a317b`。
  > Photomask: A plate covered with patterns used in the lithography process. The patterns consist of opaque and clear areas that prevent or allow light through.
- SC-EV-FD3B14BF5F4E693A / SC-PHYS-87B4665C30781057 / PDF p.3 / Lithography / printed p.NOT_KNOWN_OR_UNNUMBERED；excerpt SHA256=`21298139f48fcf329096f3f7d90d4751ff5497922f91c3a74665ff867615183f`。
  > Light is projected onto the wafer through the 'reticle', which holds the blueprint of the pattern to be printed. The system's optics (lenses in a DUV system and mirrors in an EUV system) shrink and focus the pattern onto the resist layer.
- Conflicting evidence / unresolved scope：上述 A/B 理由和差异列出已记录的冲突或缺口；未补造反证，也未因省略原文而解除冻结风险。

- **SYSTEM_RECOMMENDED_DECISION** = DEFER
推荐理由（非人工裁决）：优先暂缓：B 的接受依赖光学曝光范围限定，A 指出未证明所有场景的全局同义；当前别名 ATTACH 不能靠说明文字自动实施范围约束。请先明确 Reticle 与 Photomask 的身份边界。

HUMAN_USER_DECISION = [PENDING]

OPTIONS:

- [ ] ACCEPT_OWNER <NODE_ID 或已确认候选 ID>（原生 ATTACH）
- [ ] DEFER
- [ ] REJECT

---

<a id="sc-al-0013"></a>
### 034 · SC-AL-0013 · CFET

- **ITEM_NUMBER** = 34
- **ITEM_ID** = SC-AL-0013
- **OBJECT_TYPE** = aliases
- **DOMAIN** = semiconductor
- **CURRENT_NATIVE_OPERATION** = UNDECIDED（没有已填写的人类原生决定）
- **CURRENT_STATUS** = REVIEW
- **WHY_IN_HUMAN_PACKET** = R01_A_B_DISAGREEMENT；R02；R03；R04；R05；REVIEWER_UNRESOLVED_HUMAN_REQUIRED
- **RISK_RULES** = R01 A/B实质分歧；R02 低或必要UNKNOWN置信度；R03 证据缺口；R04 实质命题歧义；R05 身份冲突
- **MANDATORY_TRIGGER** = R01_A_B_DISAGREEMENT；R02；R03；R04；R05；REVIEWER_UNRESOLVED_HUMAN_REQUIRED
- **SAMPLE_STATUS** = NOT_SAMPLED
- **SAMPLED_FOR_QUALITY_CONTROL** = false

- **SOURCE_ID / SOURCE_NAME** = SC-PHYS-49A1D3B42E458985 / SRC_96EC545507C25F9F / 2024 IRDS — More Moore
Source provenance：IEEE International Roadmap for Devices and Systems (IRDS)；publication=；edition=2024；as_of=2024；source SHA256=`49a1d3b42e45898555490e602170876e22d1ccf8d7c17711e436d8db36322fa6`。

**CANDIDATE_SUMMARY**

- 别名：CFET
- 已占用所有者：[]
- 提议所有者：SC-CN-0096
- 提议所有者名称：Complementary FET
- Candidate target：SC-CN-0096 = Complementary FET；type=Technology；frozen status=REVIEW；仍须目标自身授权。

**AI REVIEW A**

- recommendation：HUMAN_REQUIRED；native_decision：DEFER
- proposed operation / canonical target：DEFER；目标: SC-CN-0096 [Complementary FET]；范围/说明: SEMICONDUCTOR_SOURCE_SCOPED_ALIAS_RECOMMENDATION; owner remains candidate until separately authorized
- confidence：LOW
- reason：CFET 原文没有 Complementary FET 全称，目标 0096 的全称身份亦未解决，不能自动建立等价。
- evidence assessment：INSUFFICIENT；Evidence IDs：SC-EV-5DB96B503421ADF4
- 必要置信度缺口：entity_resolution_clarity=LOW；evidence_directness=LOW；unit_scope_completeness=UNKNOWN

**AI REVIEW B**

- recommendation：HUMAN_REQUIRED；native_decision：DEFER
- proposed operation / canonical target：DEFER；目标: SC-CN-0096 [Complementary FET]；范围/说明: ALIAS_IDENTITY_ONLY; CFET -> Complementary FET
- confidence：LOW
- reason：原文仅CFET与上下堆叠NMOS/PMOS，未展开Complementary FET；目标SC-CN-0096也未通过身份定义。
- evidence assessment：INSUFFICIENT；Evidence IDs：SC-EV-5DB96B503421ADF4
- 必要置信度缺口：entity_resolution_clarity=UNKNOWN；evidence_directness=LOW；unit_scope_completeness=LOW

**A/B RECONCILIATION**

- frozen status：A_B_DISAGREEMENT
- **DISAGREEMENT_TYPE** = 风险判定分歧 R05
- **NATIVE_OPERATION_CONFLICT** = false
- R05 身份冲突：A=FALSE；B=UNKNOWN。A依据：完整 327 节点及 760 别名目录中，未发现本建议产生的身份冲突；明确共享核心者复用。 B依据：规范身份或候选所有者定义未完备：（具体证据与边界见本项该审查者 reason）

**EVIDENCE SUMMARY**

- Supporting facts：下列有来源的节选支持本项讨论的对象/命题；支持范围及未解决条件已在上方 A/B reason 中逐项说明。
- SC-EV-5DB96B503421ADF4 / SC-PHYS-49A1D3B42E458985 / PDF p.13 / 4.1 Logic Scaling / printed p.8；excerpt SHA256=`453673c2ec42f990646a1741519fe09b68d2d3e7aa96c47e497f6edb2a4303a6`。
  > Early generation of 3D VLSI is expected to start with CFET in 2031 where NMOS and PMOS are placed on top of each other.
- Conflicting evidence / unresolved scope：上述 A/B 理由和差异列出已记录的冲突或缺口；未补造反证，也未因省略原文而解除冻结风险。

- **SYSTEM_RECOMMENDED_DECISION** = DEFER
推荐理由（非人工裁决）：双方均建议暂缓；风险标签或置信度差异没有补齐身份/类型/证据缺口。优先保留候选等待人工澄清，不强制选择新的目标、关系类型或对象边界。

HUMAN_USER_DECISION = [PENDING]

OPTIONS:

- [ ] ACCEPT_OWNER <NODE_ID 或已确认候选 ID>（原生 ATTACH）
- [ ] DEFER
- [ ] REJECT

---

<a id="sc-al-0021"></a>
### 035 · SC-AL-0021 · SECC

- **ITEM_NUMBER** = 35
- **ITEM_ID** = SC-AL-0021
- **OBJECT_TYPE** = aliases
- **DOMAIN** = semiconductor
- **CURRENT_NATIVE_OPERATION** = UNDECIDED（没有已填写的人类原生决定）
- **CURRENT_STATUS** = REVIEW
- **WHY_IN_HUMAN_PACKET** = R01_A_B_DISAGREEMENT；R02；R04；R05；REVIEWER_UNRESOLVED_HUMAN_REQUIRED
- **RISK_RULES** = R01 A/B实质分歧；R02 低或必要UNKNOWN置信度；R04 实质命题歧义；R05 身份冲突
- **MANDATORY_TRIGGER** = R01_A_B_DISAGREEMENT；R02；R04；R05；REVIEWER_UNRESOLVED_HUMAN_REQUIRED
- **SAMPLE_STATUS** = NOT_SAMPLED
- **SAMPLED_FOR_QUALITY_CONTROL** = false

- **SOURCE_ID / SOURCE_NAME** = SC-PHYS-AA294FCF8FEDE75B / SRC_08CC764E9C0DCB61 / 2025 IRDS — Yield Enhancement and Advanced Manufacturing & Contamination Control
Source provenance：IEEE International Roadmap for Devices and Systems (IRDS)；publication=；edition=2025；as_of=2025；source SHA256=`aa294fcf8fede75be6e2c23c6ec75a6f3504538dceb87eb51edda0134526b34b`。

**CANDIDATE_SUMMARY**

- 别名：SECC
- 已占用所有者：[]
- 提议所有者：SC-CN-0121
- 提议所有者名称：Substrate Environment Contamination Control
- Candidate target：SC-CN-0121 = Substrate Environment Contamination Control；type=Technology；frozen status=REVIEW；仍须目标自身授权。

**AI REVIEW A**

- recommendation：HUMAN_REQUIRED；native_decision：DEFER
- proposed operation / canonical target：DEFER；目标: SC-CN-0121 [Substrate Environment Contamination Control]；范围/说明: SEMICONDUCTOR_SOURCE_SCOPED_ALIAS_RECOMMENDATION; owner remains candidate until separately authorized
- confidence：LOW
- reason：SECC 的 Substrate 全称在绑定段确实展开，但 0121 同文 Surface/Substrate 的范围冲突仍未解除，暂缓 owner 归属。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-33944F5B66F30C99
- 必要置信度缺口：entity_resolution_clarity=LOW；outcome_completeness=LOW

**AI REVIEW B**

- recommendation：HUMAN_REQUIRED；native_decision：DEFER
- proposed operation / canonical target：DEFER；目标: SC-CN-0121 [Substrate Environment Contamination Control]；范围/说明: ALIAS_IDENTITY_ONLY; SECC -> Substrate Environment Contamination Control
- confidence：HIGH
- reason：SECC与Substrate Environment直接对应，但同文Surface命名差异未解；暂缓对目标候选的唯一范围绑定。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-33944F5B66F30C99

**A/B RECONCILIATION**

- frozen status：A_B_DISAGREEMENT
- **DISAGREEMENT_TYPE** = 风险判定分歧 R02；风险判定分歧 R05；必要置信度判定分歧
- **NATIVE_OPERATION_CONFLICT** = false
- R02 低或必要UNKNOWN置信度：A=TRUE；B=FALSE。A依据：按 LOW > UNKNOWN > MEDIUM > HIGH 聚合，本条为 LOW。 B依据：九维按LOW > 必要UNKNOWN > MEDIUM > HIGH聚合为HIGH。
- R05 身份冲突：A=FALSE；B=TRUE。A依据：完整 327 节点及 760 别名目录中，未发现本建议产生的身份冲突；明确共享核心者复用。 B依据：不同身份或范围解释尚未收敛：（具体证据与边界见本项该审查者 reason）
- 聚合置信度：A=LOW；B=HIGH

**EVIDENCE SUMMARY**

- Supporting facts：下列有来源的节选支持本项讨论的对象/命题；支持范围及未解决条件已在上方 A/B reason 中逐项说明。
- SC-EV-33944F5B66F30C99 / SC-PHYS-AA294FCF8FEDE75B / PDF p.7 / 1 Introduction / focus topics / printed p.2；excerpt SHA256=`5cb56877909616c6ceb1d8f4e3dcb89dda3912d1252683b2668e313ad2297b25`。
  > The YE chapter has two focus topics: “Substrate Environment Contamination Control” (SECC) and “Characterization, Inspection and Analysis (CIA)”.
- Conflicting evidence / unresolved scope：上述 A/B 理由和差异列出已记录的冲突或缺口；未补造反证，也未因省略原文而解除冻结风险。

- **SYSTEM_RECOMMENDED_DECISION** = DEFER
推荐理由（非人工裁决）：双方均建议暂缓；风险标签或置信度差异没有补齐身份/类型/证据缺口。优先保留候选等待人工澄清，不强制选择新的目标、关系类型或对象边界。

HUMAN_USER_DECISION = [PENDING]

OPTIONS:

- [ ] ACCEPT_OWNER <NODE_ID 或已确认候选 ID>（原生 ATTACH）
- [ ] DEFER
- [ ] REJECT

---

<a id="sc-al-0022"></a>
### 036 · SC-AL-0022 · AMC

- **ITEM_NUMBER** = 36
- **ITEM_ID** = SC-AL-0022
- **OBJECT_TYPE** = aliases
- **DOMAIN** = semiconductor
- **CURRENT_NATIVE_OPERATION** = UNDECIDED（没有已填写的人类原生决定）
- **CURRENT_STATUS** = REVIEW
- **WHY_IN_HUMAN_PACKET** = R01_A_B_DISAGREEMENT；R02；R04；R05；R13；REVIEWER_UNRESOLVED_HUMAN_REQUIRED
- **RISK_RULES** = R01 A/B实质分歧；R02 低或必要UNKNOWN置信度；R04 实质命题歧义；R05 身份冲突；R13 本体/类型映射问题
- **MANDATORY_TRIGGER** = R01_A_B_DISAGREEMENT；R02；R04；R05；R13；REVIEWER_UNRESOLVED_HUMAN_REQUIRED
- **SAMPLE_STATUS** = NOT_SAMPLED
- **SAMPLED_FOR_QUALITY_CONTROL** = false

- **SOURCE_ID / SOURCE_NAME** = SC-PHYS-AA294FCF8FEDE75B / SRC_08CC764E9C0DCB61 / 2025 IRDS — Yield Enhancement and Advanced Manufacturing & Contamination Control
Source provenance：IEEE International Roadmap for Devices and Systems (IRDS)；publication=；edition=2025；as_of=2025；source SHA256=`aa294fcf8fede75be6e2c23c6ec75a6f3504538dceb87eb51edda0134526b34b`。

**CANDIDATE_SUMMARY**

- 别名：AMC
- 已占用所有者：[]
- 提议所有者：SC-CN-0122
- 提议所有者名称：Airborne Molecular Contamination
- Candidate target：SC-CN-0122 = Airborne Molecular Contamination；type=ResearchQuestion；frozen status=REVIEW；仍须目标自身授权。

**AI REVIEW A**

- recommendation：HUMAN_REQUIRED；native_decision：DEFER
- proposed operation / canonical target：DEFER；目标: SC-CN-0122 [Airborne Molecular Contamination]；范围/说明: SEMICONDUCTOR_SOURCE_SCOPED_ALIAS_RECOMMENDATION; owner remains candidate until separately authorized
- confidence：LOW
- reason：AMC/airborne molecular contamination 等价直接，但 0122 作为 ResearchQuestion 的身份类型未解决，先保留候选依赖。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-CFE0706D8027F87E
- 必要置信度缺口：entity_resolution_clarity=LOW；outcome_completeness=LOW

**AI REVIEW B**

- recommendation：HUMAN_REQUIRED；native_decision：DEFER
- proposed operation / canonical target：DEFER；目标: SC-CN-0122 [Airborne Molecular Contamination]；范围/说明: ALIAS_IDENTITY_ONLY; AMC -> Airborne Molecular Contamination
- confidence：UNKNOWN
- reason：AMC全称有直接支持，但目标被提为ResearchQuestion而实际是污染类别；须先解决所有者类型，不能直接附着。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-CFE0706D8027F87E
- 必要置信度缺口：entity_resolution_clarity=UNKNOWN；rubric_applicability_clarity=UNKNOWN

**A/B RECONCILIATION**

- frozen status：A_B_DISAGREEMENT
- **DISAGREEMENT_TYPE** = 风险判定分歧 R02；风险判定分歧 R04；风险判定分歧 R05；风险判定分歧 R13；必要置信度判定分歧
- **NATIVE_OPERATION_CONFLICT** = false
- R02 低或必要UNKNOWN置信度：A=TRUE；B=UNKNOWN。A依据：按 LOW > UNKNOWN > MEDIUM > HIGH 聚合，本条为 LOW。 B依据：九维按LOW > 必要UNKNOWN > MEDIUM > HIGH聚合为UNKNOWN。
- R04 实质命题歧义：A=TRUE；B=FALSE。A依据：（具体证据与边界见本项该审查者 reason） B依据：在明确范围下未见两个会改变本次推荐的证据解释；（具体证据与边界见本项该审查者 reason）
- R05 身份冲突：A=FALSE；B=UNKNOWN。A依据：完整 327 节点及 760 别名目录中，未发现本建议产生的身份冲突；明确共享核心者复用。 B依据：对象或关系端点的必要类型尚未统一：（具体证据与边界见本项该审查者 reason）
- R13 本体/类型映射问题：A=FALSE；B=TRUE。A依据：使用原对象可选原生决定及既有类型体系，未引入新 ontology 类型。 B依据：现有类型/关系映射存在未解决的表示问题：（具体证据与边界见本项该审查者 reason）
- 聚合置信度：A=LOW；B=UNKNOWN

**EVIDENCE SUMMARY**

- Supporting facts：下列有来源的节选支持本项讨论的对象/命题；支持范围及未解决条件已在上方 A/B reason 中逐项说明。
- SC-EV-CFE0706D8027F87E / SC-PHYS-AA294FCF8FEDE75B / PDF p.31 / Surface Environment Control / AMC / printed p.26；excerpt SHA256=`59c02bbf94cb4593118027bd89af5a81f8df85e3a43322f5cc313eb6c6196574`。
  > Airborne molecular contamination (AMC)— Fugitive emissions from chemicals used in wafer processing and inadequate exhaust are the main sources of AMC.
- Conflicting evidence / unresolved scope：上述 A/B 理由和差异列出已记录的冲突或缺口；未补造反证，也未因省略原文而解除冻结风险。

- **SYSTEM_RECOMMENDED_DECISION** = DEFER
推荐理由（非人工裁决）：双方均建议暂缓；风险标签或置信度差异没有补齐身份/类型/证据缺口。优先保留候选等待人工澄清，不强制选择新的目标、关系类型或对象边界。

HUMAN_USER_DECISION = [PENDING]

OPTIONS:

- [ ] ACCEPT_OWNER <NODE_ID 或已确认候选 ID>（原生 ATTACH）
- [ ] DEFER
- [ ] REJECT

---

<a id="sc-al-0023"></a>
### 037 · SC-AL-0023 · AMHS

- **ITEM_NUMBER** = 37
- **ITEM_ID** = SC-AL-0023
- **OBJECT_TYPE** = aliases
- **DOMAIN** = semiconductor
- **CURRENT_NATIVE_OPERATION** = UNDECIDED（没有已填写的人类原生决定）
- **CURRENT_STATUS** = REVIEW
- **WHY_IN_HUMAN_PACKET** = R01_A_B_DISAGREEMENT；R02；R03；R04；R05；REVIEWER_UNRESOLVED_HUMAN_REQUIRED
- **RISK_RULES** = R01 A/B实质分歧；R02 低或必要UNKNOWN置信度；R03 证据缺口；R04 实质命题歧义；R05 身份冲突
- **MANDATORY_TRIGGER** = R01_A_B_DISAGREEMENT；R02；R03；R04；R05；REVIEWER_UNRESOLVED_HUMAN_REQUIRED
- **SAMPLE_STATUS** = NOT_SAMPLED
- **SAMPLED_FOR_QUALITY_CONTROL** = false

- **SOURCE_ID / SOURCE_NAME** = SC-PHYS-4FA7140313FB3AF8 / SRC_15959FA40D6E85A4 / 2023 IRDS — Factory Integration
Source provenance：IEEE International Roadmap for Devices and Systems (IRDS)；publication=；edition=2023；as_of=2023；source SHA256=`4fa7140313fb3af883127c329599c4d8e6f4b9abfbe0976f4e8102ebe8c2587d`。

**CANDIDATE_SUMMARY**

- 别名：AMHS
- 已占用所有者：[]
- 提议所有者：SC-CN-0124
- 提议所有者名称：Automated Material Handling System
- Candidate target：SC-CN-0124 = Automated Material Handling System；type=Equipment；frozen status=REVIEW；仍须目标自身授权。

**AI REVIEW A**

- recommendation：HUMAN_REQUIRED；native_decision：DEFER
- proposed operation / canonical target：DEFER；目标: SC-CN-0124 [Automated Material Handling System]；范围/说明: SEMICONDUCTOR_SOURCE_SCOPED_ALIAS_RECOMMENDATION; owner remains candidate until separately authorized
- confidence：LOW
- reason：AMHS 只有功能要求，没有全称展开；owner 0124 的身份依据不足，暂缓附加。
- evidence assessment：INSUFFICIENT；Evidence IDs：SC-EV-60435D5F04954369
- 必要置信度缺口：entity_resolution_clarity=LOW；evidence_directness=LOW；unit_scope_completeness=UNKNOWN

**AI REVIEW B**

- recommendation：HUMAN_REQUIRED；native_decision：DEFER
- proposed operation / canonical target：DEFER；目标: SC-CN-0124 [Automated Material Handling System]；范围/说明: ALIAS_IDENTITY_ONLY; AMHS -> Automated Material Handling System
- confidence：LOW
- reason：AMHS词项及物料搬运功能明确，但未出现候选全称；所有者规范身份仍待证据映射。
- evidence assessment：INSUFFICIENT；Evidence IDs：SC-EV-60435D5F04954369
- 必要置信度缺口：entity_resolution_clarity=UNKNOWN；evidence_directness=LOW；unit_scope_completeness=LOW

**A/B RECONCILIATION**

- frozen status：A_B_DISAGREEMENT
- **DISAGREEMENT_TYPE** = 风险判定分歧 R05
- **NATIVE_OPERATION_CONFLICT** = false
- R05 身份冲突：A=FALSE；B=UNKNOWN。A依据：完整 327 节点及 760 别名目录中，未发现本建议产生的身份冲突；明确共享核心者复用。 B依据：规范身份或候选所有者定义未完备：（具体证据与边界见本项该审查者 reason）

**EVIDENCE SUMMARY**

- Supporting facts：下列有来源的节选支持本项讨论的对象/命题；支持范围及未解决条件已在上方 A/B reason 中逐项说明。
- SC-EV-60435D5F04954369 / SC-PHYS-4FA7140313FB3AF8 / PDF p.27 / 5.4 Material Handling / printed p.21；excerpt SHA256=`c88951455ed96a5adaa7e8bd50efc2b4b46c4eb7a0ee7f787df729b669f69e81`。
  > AMHS must have acceptable return on investment (ROI) and must interface directly with all inline (i.e., used in normal process flow) production and metrology equipment. AMHS must deliver material in a timely fashion to support critical equipment in order to minimize wait time waste.
- Conflicting evidence / unresolved scope：上述 A/B 理由和差异列出已记录的冲突或缺口；未补造反证，也未因省略原文而解除冻结风险。

- **SYSTEM_RECOMMENDED_DECISION** = DEFER
推荐理由（非人工裁决）：双方均建议暂缓；风险标签或置信度差异没有补齐身份/类型/证据缺口。优先保留候选等待人工澄清，不强制选择新的目标、关系类型或对象边界。

HUMAN_USER_DECISION = [PENDING]

OPTIONS:

- [ ] ACCEPT_OWNER <NODE_ID 或已确认候选 ID>（原生 ATTACH）
- [ ] DEFER
- [ ] REJECT

---

<a id="sc-al-0026"></a>
### 038 · SC-AL-0026 · MEMS

- **ITEM_NUMBER** = 38
- **ITEM_ID** = SC-AL-0026
- **OBJECT_TYPE** = aliases
- **DOMAIN** = semiconductor
- **CURRENT_NATIVE_OPERATION** = UNDECIDED（没有已填写的人类原生决定）
- **CURRENT_STATUS** = REVIEW
- **WHY_IN_HUMAN_PACKET** = R01_A_B_DISAGREEMENT；R02；R03；R04；R05；R13；REVIEWER_UNRESOLVED_HUMAN_REQUIRED
- **RISK_RULES** = R01 A/B实质分歧；R02 低或必要UNKNOWN置信度；R03 证据缺口；R04 实质命题歧义；R05 身份冲突；R13 本体/类型映射问题
- **MANDATORY_TRIGGER** = R01_A_B_DISAGREEMENT；R02；R03；R04；R05；R13；REVIEWER_UNRESOLVED_HUMAN_REQUIRED
- **SAMPLE_STATUS** = NOT_SAMPLED
- **SAMPLED_FOR_QUALITY_CONTROL** = false

- **SOURCE_ID / SOURCE_NAME** = SC-PHYS-AA294FCF8FEDE75B / SRC_08CC764E9C0DCB61 / 2025 IRDS — Yield Enhancement and Advanced Manufacturing & Contamination Control
Source provenance：IEEE International Roadmap for Devices and Systems (IRDS)；publication=；edition=2025；as_of=2025；source SHA256=`aa294fcf8fede75be6e2c23c6ec75a6f3504538dceb87eb51edda0134526b34b`。

**CANDIDATE_SUMMARY**

- 别名：MEMS
- 已占用所有者：[]
- 提议所有者：SC-CN-0131
- 提议所有者名称：Microelectromechanical Systems
- Candidate target：SC-CN-0131 = Microelectromechanical Systems；type=Technology；frozen status=REVIEW；仍须目标自身授权。

**AI REVIEW A**

- recommendation：HUMAN_REQUIRED；native_decision：DEFER
- proposed operation / canonical target：DEFER；目标: SC-CN-0131 [Microelectromechanical Systems]；范围/说明: SEMICONDUCTOR_SOURCE_SCOPED_ALIAS_RECOMMENDATION; owner remains candidate until separately authorized
- confidence：LOW
- reason：原文 microelectromechanical (MEMS) 未支持 Systems 完整名称与类型，owner 0131 必须先解决身份范围。
- evidence assessment：INSUFFICIENT；Evidence IDs：SC-EV-C74D00EC86C3E38E
- 必要置信度缺口：entity_resolution_clarity=LOW；evidence_directness=LOW；unit_scope_completeness=UNKNOWN

**AI REVIEW B**

- recommendation：HUMAN_REQUIRED；native_decision：DEFER
- proposed operation / canonical target：DEFER；目标: SC-CN-0131 [Microelectromechanical Systems]；范围/说明: ALIAS_IDENTITY_ONLY; MEMS -> Microelectromechanical Systems
- confidence：LOW
- reason：microelectromechanical (MEMS)未给完整Systems定义，目标的技术/器件类型也未定；不能据缩写自动附着。
- evidence assessment：INSUFFICIENT；Evidence IDs：SC-EV-C74D00EC86C3E38E
- 必要置信度缺口：entity_resolution_clarity=UNKNOWN；evidence_directness=LOW；rubric_applicability_clarity=UNKNOWN；unit_scope_completeness=LOW

**A/B RECONCILIATION**

- frozen status：A_B_DISAGREEMENT
- **DISAGREEMENT_TYPE** = 风险判定分歧 R05；风险判定分歧 R13
- **NATIVE_OPERATION_CONFLICT** = false
- R05 身份冲突：A=FALSE；B=UNKNOWN。A依据：完整 327 节点及 760 别名目录中，未发现本建议产生的身份冲突；明确共享核心者复用。 B依据：对象或关系端点的必要类型尚未统一：（具体证据与边界见本项该审查者 reason）
- R13 本体/类型映射问题：A=FALSE；B=TRUE。A依据：使用原对象可选原生决定及既有类型体系，未引入新 ontology 类型。 B依据：现有类型/关系映射存在未解决的表示问题：（具体证据与边界见本项该审查者 reason）

**EVIDENCE SUMMARY**

- Supporting facts：下列有来源的节选支持本项讨论的对象/命题；支持范围及未解决条件已在上方 A/B reason 中逐项说明。
- SC-EV-C74D00EC86C3E38E / SC-PHYS-AA294FCF8FEDE75B / PDF p.6 / 1 Introduction / More than Moore process groups / printed p.1；excerpt SHA256=`32b10b19734b046a2f54d3a767699a5b4f4a6a65852f7d8373ad9a7b7163f783`。
  > The Yield Enhancement (YE) chapter will display the current advanced and next generation future requirements for high yielding manufacturing of More Moore as well as More than Moore products separated in “critical process groups” including microelectromechanical (MEMS), back-end processes, e. g., packaging.
- Conflicting evidence / unresolved scope：上述 A/B 理由和差异列出已记录的冲突或缺口；未补造反证，也未因省略原文而解除冻结风险。

- **SYSTEM_RECOMMENDED_DECISION** = DEFER
推荐理由（非人工裁决）：双方均建议暂缓；风险标签或置信度差异没有补齐身份/类型/证据缺口。优先保留候选等待人工澄清，不强制选择新的目标、关系类型或对象边界。

HUMAN_USER_DECISION = [PENDING]

OPTIONS:

- [ ] ACCEPT_OWNER <NODE_ID 或已确认候选 ID>（原生 ATTACH）
- [ ] DEFER
- [ ] REJECT

---

<a id="sc-cl-0019"></a>
### 039 · SC-CL-0019 · 2020版IRDS描述的HBM针对3D die stacking进行优化。

- **ITEM_NUMBER** = 39
- **ITEM_ID** = SC-CL-0019
- **OBJECT_TYPE** = claims
- **DOMAIN** = semiconductor
- **CURRENT_NATIVE_OPERATION** = UNDECIDED（没有已填写的人类原生决定）
- **CURRENT_STATUS** = ACCEPTABLE
- **WHY_IN_HUMAN_PACKET** = R01_A_B_DISAGREEMENT；R02；R03；R04；R08；R09；REVIEWER_UNRESOLVED_HUMAN_REQUIRED
- **RISK_RULES** = R01 A/B实质分歧；R02 低或必要UNKNOWN置信度；R03 证据缺口；R04 实质命题歧义；R08 实质关系歧义；R09 因果命题歧义
- **MANDATORY_TRIGGER** = R01_A_B_DISAGREEMENT；R02；R03；R04；R08；R09；REVIEWER_UNRESOLVED_HUMAN_REQUIRED
- **SAMPLE_STATUS** = NOT_SAMPLED
- **SAMPLED_FOR_QUALITY_CONTROL** = false

- **SOURCE_ID / SOURCE_NAME** = SC-PHYS-54CABB8879E180A7 / SRC_0C4EF3703421D29B / 2020 IRDS — Packaging Integration
Source provenance：IEEE International Roadmap for Devices and Systems (IRDS)；publication=；edition=2020；as_of=2020；source SHA256=`54cabb8879e180a7a0363e8964cb2d28735eff03ecee6a45905cd54f06eae5e2`。

**CANDIDATE_SUMMARY**

- 主体：High Bandwidth Memory
- 主体 ID：NODE_20260817_6A9A657D
- 事实时间：2020
- 命题：2020版IRDS描述的HBM针对3D die stacking进行优化。
- 性质：fact
- 时间类别：historical_source_architecture
- 来源时点：2020
- 范围：Historical packaging architecture, not current-generation performance metrics
- Canonical state：NODE_20260817_6A9A657D = High Bandwidth Memory；type=Product；status=active。

**AI REVIEW A**

- recommendation：HUMAN_REQUIRED；native_decision：KEEP_NEEDS_REVIEW
- proposed operation / canonical target：KEEP_NEEDS_REVIEW；目标: NODE_20260817_6A9A657D [High Bandwidth Memory]；范围/说明: Historical packaging architecture, not current-generation performance metrics
- confidence：LOW
- reason：2020 来源确说 HBM 优化为 3D die stacking，但摘录以 Under these conditions 起句而条件未包含；候选未保存这些条件，范围完整性待核。
- evidence assessment：INSUFFICIENT；Evidence IDs：SC-EV-EFC0887512104389
- 必要置信度缺口：evidence_directness=LOW；relation_causal_explicitness=UNKNOWN；unit_scope_completeness=UNKNOWN

**AI REVIEW B**

- recommendation：ACCEPT；native_decision：KEEP
- proposed operation / canonical target：KEEP；目标: NODE_20260817_6A9A657D [High Bandwidth Memory]；范围/说明: Historical packaging architecture, not current-generation performance metrics
- confidence：HIGH
- reason：2020 IRDS原文明确HBM为3D die stacking优化，范围与历史架构一致；不推算当代带宽、代数或性能。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-EFC0887512104389

**A/B RECONCILIATION**

- frozen status：A_B_DISAGREEMENT
- **DISAGREEMENT_TYPE** = KEEP_NEEDS_REVIEW vs KEEP；evidence sufficiency disagreement；ACCEPT/NOTE vs HUMAN_REQUIRED；风险判定分歧 R02；风险判定分歧 R03；风险判定分歧 R04；风险判定分歧 R08；风险判定分歧 R09；必要置信度判定分歧
- **NATIVE_OPERATION_CONFLICT** = true
- 原生操作：A=KEEP_NEEDS_REVIEW；B=KEEP
- 证据充分性：A=INSUFFICIENT；B=SUFFICIENT
- 推荐路由：A=HUMAN_REQUIRED；B=ACCEPT
- R02 低或必要UNKNOWN置信度：A=TRUE；B=FALSE。A依据：按 LOW > UNKNOWN > MEDIUM > HIGH 聚合，本条为 LOW。 B依据：九维按LOW > 必要UNKNOWN > MEDIUM > HIGH聚合为HIGH。
- R03 证据缺口：A=TRUE；B=FALSE。A依据：（具体证据与边界见本项该审查者 reason） B依据：所用证据ID、摘录hash、source hash与定位均绑定；逐项支撑判断见理由。
- R04 实质命题歧义：A=UNKNOWN；B=FALSE。A依据：必要语义边界缺证，无法排除改变 outcome 的解释：（具体证据与边界见本项该审查者 reason） B依据：在明确范围下未见两个会改变本次推荐的证据解释；（具体证据与边界见本项该审查者 reason）
- R08 实质关系歧义：A=UNKNOWN；B=NOT_APPLICABLE。A依据：实质语义有影响，但必要关系/范围判断未定：（具体证据与边界见本项该审查者 reason） B依据：本条审核节点/别名身份或非关系型来源状态命题，不提出关系映射；relation_ambiguity/materiality均不适用。
- R09 因果命题歧义：A=UNKNOWN；B=FALSE。A依据：优化条件在截取句首未给出，不能核实条件性架构效果。 B依据：没有从共现/相邻工序推导经济或技术因果；来源功能/潜在方案按原口径保留。
- 聚合置信度：A=LOW；B=HIGH

**EVIDENCE SUMMARY**

- Supporting facts：下列有来源的节选支持本项讨论的对象/命题；支持范围及未解决条件已在上方 A/B reason 中逐项说明。
- SC-EV-EFC0887512104389 / SC-PHYS-54CABB8879E180A7 / PDF p.16 / 3D Stacks / HBM / printed p.10；excerpt SHA256=`d9cddb60890e78a2e295a82cfaaf5bfcaa51109c055e8b64bf17ccb2d28667f4`。
  > Under these conditions new high bandwidth memories (HBM) have been optimized for 3D die stacking (Figure PI-6).
- Conflicting evidence / unresolved scope：上述 A/B 理由和差异列出已记录的冲突或缺口；未补造反证，也未因省略原文而解除冻结风险。

- **SYSTEM_RECOMMENDED_DECISION** = KEEP_NEEDS_REVIEW
推荐理由（非人工裁决）：优先保留但待审：双方均识别到历史 HBM/3D 堆叠陈述，但 A 指出 Under these conditions 的前置条件未包含；这比直接 KEEP 更完整地保留范围缺口，也无需将有来源的陈述直接删除。

HUMAN_USER_DECISION = [PENDING]

OPTIONS:

- [ ] KEEP
- [ ] DROP
- [ ] KEEP_NEEDS_REVIEW

---

<a id="sc-cn-0007"></a>
### 040 · SC-CN-0007 · Analog Semiconductors

- **ITEM_NUMBER** = 40
- **ITEM_ID** = SC-CN-0007
- **OBJECT_TYPE** = nodes
- **DOMAIN** = 00_industry_structure
- **CURRENT_NATIVE_OPERATION** = CREATE NODE_F557CCEB8BC86CEE
- **CURRENT_STATUS** = CREATE
- **WHY_IN_HUMAN_PACKET** = R01_A_B_DISAGREEMENT；R07；REVIEWER_UNRESOLVED_HUMAN_REQUIRED
- **RISK_RULES** = R01 A/B实质分歧；R07 新增高影响Node
- **MANDATORY_TRIGGER** = R01_A_B_DISAGREEMENT；R07；REVIEWER_UNRESOLVED_HUMAN_REQUIRED
- **SAMPLE_STATUS** = NOT_SAMPLED
- **SAMPLED_FOR_QUALITY_CONTROL** = false

- **SOURCE_ID / SOURCE_NAME** = SC-PHYS-04A42FFC3F71A42F / SRC_1640D08BDF90458F / Making Semiconductors: The Highly Complex and Global Chip Research, Design, and Manufacturing Process
Source provenance：Semiconductor Industry Association (SIA)；publication=2019；edition=；as_of=2019；source SHA256=`04a42ffc3f71a42fa9b996240618874bb7fff21404e93cdb1e7bf53318938c26`。
- **SOURCE_ID / SOURCE_NAME** = SC-PHYS-B33C40EBCB5756F7 / SRC_1DD38DEB69830E97 / Strengthening the Global Semiconductor Supply Chain in an Uncertain Era
Source provenance：Semiconductor Industry Association (SIA) / Boston Consulting Group (BCG)；publication=2021-04；edition=；as_of=2021-04；source SHA256=`b33c40ebcb5756f76e887ba2664f97736252e68ba7bfbedc2d628ce2d7cbc08d`。

**CANDIDATE_SUMMARY**

- Node 类型：Segment
- 名称：Analog Semiconductors
- 已有身份：NODE_F557CCEB8BC86CEE
- 边界说明：Source支持可复用的持久研究对象，未命中现有规范名或已登记别名。
- Planned native target：NODE_F557CCEB8BC86CEE → SC-CN-0007 / Analog Semiconductors / Segment；这是候选映射，不是已存在或获批准的目录对象。

**AI REVIEW A**

- recommendation：HUMAN_REQUIRED；native_decision：CREATE
- proposed operation / canonical target：CREATE；范围/说明: IDENTITY_RECOMMENDATION_ONLY; Analog Semiconductors / Segment; no canonical mutation
- confidence：HIGH
- reason：原文明列电压调节、转换及 PMIC 为模拟产品，较既有 PMIC 广；本批关系 0002 将此类作为 IC 分类分支，构成模拟技术研究的结构锚点。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-086DB7864B530FA0, SC-EV-03AFE72BBC136395

**AI REVIEW B**

- recommendation：ACCEPT；native_decision：CREATE
- proposed operation / canonical target：CREATE；范围/说明: IDENTITY_ONLY; 00_industry_structure; Analog Semiconductors; Segment
- confidence：HIGH
- reason：SIA明示模拟类别及调节实际信号的作用；目录PMIC仅其子产品，不能复用为整个模拟板块。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-086DB7864B530FA0, SC-EV-03AFE72BBC136395

**A/B RECONCILIATION**

- frozen status：A_B_DISAGREEMENT
- **DISAGREEMENT_TYPE** = ACCEPT/NOTE vs HUMAN_REQUIRED；风险判定分歧 R07
- **NATIVE_OPERATION_CONFLICT** = false
- 推荐路由：A=HUMAN_REQUIRED；B=ACCEPT
- R07 新增高影响Node：A=TRUE；B=FALSE。A依据：（具体证据与边界见本项该审查者 reason） B依据：仅局部有界新对象，无本批关键分类锚点、既有父层变更或View/Impact关键依赖；（具体证据与边界见本项该审查者 reason）

**EVIDENCE SUMMARY**

- Supporting facts：下列有来源的节选支持本项讨论的对象/命题；支持范围及未解决条件已在上方 A/B reason 中逐项说明。
- SC-EV-03AFE72BBC136395 / SC-PHYS-B33C40EBCB5756F7 / PDF p.9 / Discrete, Analog, and Other (DAO) / printed p.9；excerpt SHA256=`f033d25f1a4540151a447da6eb18943e418ea2e486697c9730e4891729462289`。
  > Analog products include voltage regulators and data converters that translate analog signals from sources such as voice into digital signals. This category also includes power management integrated circuits found in any type of electronic device, and radio frequency (RF) semiconductors that enable smartphones to receive and process the radio signals coming from the base stations of cellular networks.
- SC-EV-086DB7864B530FA0 / SC-PHYS-04A42FFC3F71A42F / PDF p.1 / Types of Semiconductors / printed p.NOT_KNOWN_OR_UNNUMBERED；excerpt SHA256=`de70cc3f209d1d690acd93eb476001bba1cc790fb80c8683d1bf9cc013d15cfe`。
  > Within ICs are digital semiconductors, which process binary information used by computers, and analog semiconductors, which regulate “real world” conditions such as temperature, speed, sound, and electrical current. Within the digital category are memory products, micro-components (including microprocessors and microcontrollers) and logic products.
- Conflicting evidence / unresolved scope：上述 A/B 理由和差异列出已记录的冲突或缺口；未补造反证，也未因省略原文而解除冻结风险。

- **SYSTEM_RECOMMENDED_DECISION** = CREATE
推荐理由（非人工裁决）：双方均支持同一个 CREATE 提议，分歧在是否构成结构性高影响，而非创建对象、类型或证据支持。系统建议保留共同 CREATE 方向供人工确认，并完整保留较严格的 R07 与 mandatory 路由；没有替人工裁定该风险分歧。

HUMAN_USER_DECISION = [PENDING]

OPTIONS:

- [ ] CREATE
- [ ] REUSE <NODE_ID>
- [ ] DEFER
- [ ] REJECT

---

<a id="sc-cn-0010"></a>
### 041 · SC-CN-0010 · Dynamic Random-Access Memory

- **ITEM_NUMBER** = 41
- **ITEM_ID** = SC-CN-0010
- **OBJECT_TYPE** = nodes
- **DOMAIN** = 00_industry_structure
- **CURRENT_NATIVE_OPERATION** = UNDECIDED（没有已填写的人类原生决定）
- **CURRENT_STATUS** = REVIEW
- **WHY_IN_HUMAN_PACKET** = R01_A_B_DISAGREEMENT；R02；R03；R04；R05；REVIEWER_UNRESOLVED_HUMAN_REQUIRED
- **RISK_RULES** = R01 A/B实质分歧；R02 低或必要UNKNOWN置信度；R03 证据缺口；R04 实质命题歧义；R05 身份冲突
- **MANDATORY_TRIGGER** = R01_A_B_DISAGREEMENT；R02；R03；R04；R05；REVIEWER_UNRESOLVED_HUMAN_REQUIRED
- **SAMPLE_STATUS** = NOT_SAMPLED
- **SAMPLED_FOR_QUALITY_CONTROL** = false

- **SOURCE_ID / SOURCE_NAME** = SC-PHYS-B33C40EBCB5756F7 / SRC_1DD38DEB69830E97 / Strengthening the Global Semiconductor Supply Chain in an Uncertain Era
Source provenance：Semiconductor Industry Association (SIA) / Boston Consulting Group (BCG)；publication=2021-04；edition=；as_of=2021-04；source SHA256=`b33c40ebcb5756f76e887ba2664f97736252e68ba7bfbedc2d628ce2d7cbc08d`。

**CANDIDATE_SUMMARY**

- Node 类型：Product
- 名称：Dynamic Random-Access Memory
- 备选身份：NODE_20260817_B0EE840E
- 边界说明：通用 DRAM 不等于既有 Server DRAM 或 HBM。
- Canonical state：NODE_20260817_B0EE840E = Server DRAM；type=Product；status=active。

**AI REVIEW A**

- recommendation：HUMAN_REQUIRED；native_decision：DEFER
- proposed operation / canonical target：DEFER；范围/说明: IDENTITY_RECOMMENDATION_ONLY; Dynamic Random-Access Memory / Product; no canonical mutation
- confidence：LOW
- reason：证据仅给出 DRAM 缩写及用途，未给出 Dynamic Random-Access Memory 全称等价；可区分 Server DRAM/HBM 的宽窄，仍需全称身份依据。
- evidence assessment：INSUFFICIENT；Evidence IDs：SC-EV-9F7D3244A0780DEA
- 必要置信度缺口：entity_resolution_clarity=LOW；evidence_directness=LOW；unit_scope_completeness=UNKNOWN

**AI REVIEW B**

- recommendation：HUMAN_REQUIRED；native_decision：DEFER
- proposed operation / canonical target：DEFER；范围/说明: IDENTITY_ONLY; 00_industry_structure; Dynamic Random-Access Memory; Product
- confidence：LOW
- reason：摘录明确DRAM功能且其范围大于Server DRAM/HBM，但未给Dynamic Random-Access Memory全称对应；在封闭证据下暂缓规范名与别名绑定。
- evidence assessment：INSUFFICIENT；Evidence IDs：SC-EV-9F7D3244A0780DEA
- 必要置信度缺口：entity_resolution_clarity=UNKNOWN；evidence_directness=LOW；unit_scope_completeness=LOW

**A/B RECONCILIATION**

- frozen status：A_B_DISAGREEMENT
- **DISAGREEMENT_TYPE** = 风险判定分歧 R05
- **NATIVE_OPERATION_CONFLICT** = false
- R05 身份冲突：A=FALSE；B=UNKNOWN。A依据：完整 327 节点及 760 别名目录中，未发现本建议产生的身份冲突；明确共享核心者复用。 B依据：规范身份或候选所有者定义未完备：（具体证据与边界见本项该审查者 reason）

**EVIDENCE SUMMARY**

- Supporting facts：下列有来源的节选支持本项讨论的对象/命题；支持范围及未解决条件已在上方 A/B reason 中逐项说明。
- SC-EV-9F7D3244A0780DEA / SC-PHYS-B33C40EBCB5756F7 / PDF p.9 / Memory / printed p.9；excerpt SHA256=`3e0f10608491e28b4ca65b393efba69601bbd0ab43166ecfceffb1f812be69b2`。
  > DRAM is used to store the data or program code needed by a computer processor to function.
- Conflicting evidence / unresolved scope：上述 A/B 理由和差异列出已记录的冲突或缺口；未补造反证，也未因省略原文而解除冻结风险。

- **SYSTEM_RECOMMENDED_DECISION** = DEFER
推荐理由（非人工裁决）：双方均建议暂缓；风险标签或置信度差异没有补齐身份/类型/证据缺口。优先保留候选等待人工澄清，不强制选择新的目标、关系类型或对象边界。

HUMAN_USER_DECISION = [PENDING]

OPTIONS:

- [ ] CREATE
- [ ] REUSE <NODE_ID>
- [ ] DEFER
- [ ] REJECT

---

<a id="sc-cn-0011"></a>
### 042 · SC-CN-0011 · NAND Flash

- **ITEM_NUMBER** = 42
- **ITEM_ID** = SC-CN-0011
- **OBJECT_TYPE** = nodes
- **DOMAIN** = 00_industry_structure
- **CURRENT_NATIVE_OPERATION** = UNDECIDED（没有已填写的人类原生决定）
- **CURRENT_STATUS** = REVIEW
- **WHY_IN_HUMAN_PACKET** = R01_A_B_DISAGREEMENT；R02；R04；R05；R06；REVIEWER_UNRESOLVED_HUMAN_REQUIRED
- **RISK_RULES** = R01 A/B实质分歧；R02 低或必要UNKNOWN置信度；R04 实质命题歧义；R05 身份冲突；R06 跨域身份冲突
- **MANDATORY_TRIGGER** = R01_A_B_DISAGREEMENT；R02；R04；R05；R06；REVIEWER_UNRESOLVED_HUMAN_REQUIRED
- **SAMPLE_STATUS** = NOT_SAMPLED
- **SAMPLED_FOR_QUALITY_CONTROL** = false

- **SOURCE_ID / SOURCE_NAME** = SC-PHYS-B33C40EBCB5756F7 / SRC_1DD38DEB69830E97 / Strengthening the Global Semiconductor Supply Chain in an Uncertain Era
Source provenance：Semiconductor Industry Association (SIA) / Boston Consulting Group (BCG)；publication=2021-04；edition=；as_of=2021-04；source SHA256=`b33c40ebcb5756f76e887ba2664f97736252e68ba7bfbedc2d628ce2d7cbc08d`。

**CANDIDATE_SUMMARY**

- Node 类型：Product
- 名称：NAND Flash
- 边界说明：PHASE1_1A CROSS_DOMAIN_QUARANTINE；本批只提交半导体证据，不自行解除历史隔离。

**AI REVIEW A**

- recommendation：HUMAN_REQUIRED；native_decision：DEFER
- proposed operation / canonical target：DEFER；范围/说明: IDENTITY_RECOMMENDATION_ONLY; NAND Flash / Product; no canonical mutation
- confidence：LOW
- reason：NAND 的非易失闪存语义清楚，catalog 无可直接复用对象；但输入保留跨域隔离，缺解除隔离的身份处理依据，不能自行消除冲突。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-80E21D50198799F6
- 必要置信度缺口：conflict_accounting=LOW；entity_resolution_clarity=LOW；outcome_completeness=LOW

**AI REVIEW B**

- recommendation：HUMAN_REQUIRED；native_decision：DEFER
- proposed operation / canonical target：DEFER；范围/说明: IDENTITY_ONLY; 00_industry_structure; NAND Flash; Product
- confidence：UNKNOWN
- reason：NAND非易失存储功能有证据，目录未见可安全复用身份；冻结输入明确跨域隔离未解除且缺冲突裁定，不能单凭本条解除。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-80E21D50198799F6
- 必要置信度缺口：conflict_accounting=UNKNOWN；entity_resolution_clarity=UNKNOWN

**A/B RECONCILIATION**

- frozen status：A_B_DISAGREEMENT
- **DISAGREEMENT_TYPE** = 风险判定分歧 R02；风险判定分歧 R04；风险判定分歧 R05；风险判定分歧 R06；必要置信度判定分歧
- **NATIVE_OPERATION_CONFLICT** = false
- R02 低或必要UNKNOWN置信度：A=TRUE；B=UNKNOWN。A依据：按 LOW > UNKNOWN > MEDIUM > HIGH 聚合，本条为 LOW。 B依据：九维按LOW > 必要UNKNOWN > MEDIUM > HIGH聚合为UNKNOWN。
- R04 实质命题歧义：A=UNKNOWN；B=FALSE。A依据：（具体证据与边界见本项该审查者 reason） B依据：在明确范围下未见两个会改变本次推荐的证据解释；（具体证据与边界见本项该审查者 reason）
- R05 身份冲突：A=FALSE；B=UNKNOWN。A依据：完整 327 节点及 760 别名目录中，未发现本建议产生的身份冲突；明确共享核心者复用。 B依据：隔离端点没有可证实的最终canonical身份裁定：（具体证据与边界见本项该审查者 reason）
- R06 跨域身份冲突：A=TRUE；B=UNKNOWN。A依据：（具体证据与边界见本项该审查者 reason） B依据：冻结历史隔离继续有效；来源语义清楚不能替代缺失的跨域身份冲突裁定：（具体证据与边界见本项该审查者 reason）
- 聚合置信度：A=LOW；B=UNKNOWN

**EVIDENCE SUMMARY**

- Supporting facts：下列有来源的节选支持本项讨论的对象/命题；支持范围及未解决条件已在上方 A/B reason 中逐项说明。
- SC-EV-80E21D50198799F6 / SC-PHYS-B33C40EBCB5756F7 / PDF p.9 / Memory / printed p.9；excerpt SHA256=`5d250912604a223b65441507e56872c55e6a67e2cba3ec6abef008dd36fe42e1`。
  > NAND is the most common type of flash memory. Unlike DRAM, it does not need power to retain data, so it is used for permanent storage.
- Conflicting evidence / unresolved scope：上述 A/B 理由和差异列出已记录的冲突或缺口；未补造反证，也未因省略原文而解除冻结风险。

- **SYSTEM_RECOMMENDED_DECISION** = DEFER
推荐理由（非人工裁决）：双方均建议暂缓；风险标签或置信度差异没有补齐身份/类型/证据缺口。优先保留候选等待人工澄清，不强制选择新的目标、关系类型或对象边界。

HUMAN_USER_DECISION = [PENDING]

OPTIONS:

- [ ] CREATE
- [ ] REUSE <NODE_ID>
- [ ] DEFER
- [ ] REJECT

---

<a id="sc-cn-0015"></a>
### 043 · SC-CN-0015 · Semiconductor IP

- **ITEM_NUMBER** = 43
- **ITEM_ID** = SC-CN-0015
- **OBJECT_TYPE** = nodes
- **DOMAIN** = 00_industry_structure
- **CURRENT_NATIVE_OPERATION** = UNDECIDED（没有已填写的人类原生决定）
- **CURRENT_STATUS** = REVIEW
- **WHY_IN_HUMAN_PACKET** = R01_A_B_DISAGREEMENT；R02；R04；R13；REVIEWER_UNRESOLVED_HUMAN_REQUIRED
- **RISK_RULES** = R01 A/B实质分歧；R02 低或必要UNKNOWN置信度；R04 实质命题歧义；R13 本体/类型映射问题
- **MANDATORY_TRIGGER** = R01_A_B_DISAGREEMENT；R02；R04；R13；REVIEWER_UNRESOLVED_HUMAN_REQUIRED
- **SAMPLE_STATUS** = NOT_SAMPLED
- **SAMPLED_FOR_QUALITY_CONTROL** = false

- **SOURCE_ID / SOURCE_NAME** = SC-PHYS-AC86A7FEB4F6ADB5 / SRC_689680B30C113F1B / The Growing Challenge of Semiconductor Design Leadership
Source provenance：Semiconductor Industry Association (SIA) / Boston Consulting Group (BCG)；publication=2022-11；edition=；as_of=2022-11；source SHA256=`ac86a7feb4f6adb52e488086f9281c1f409bd72baecb6bdbed72a0efa3856666`。
- **SOURCE_ID / SOURCE_NAME** = SC-PHYS-B33C40EBCB5756F7 / SRC_1DD38DEB69830E97 / Strengthening the Global Semiconductor Supply Chain in an Uncertain Era
Source provenance：Semiconductor Industry Association (SIA) / Boston Consulting Group (BCG)；publication=2021-04；edition=；as_of=2021-04；source SHA256=`b33c40ebcb5756f76e887ba2664f97736252e68ba7bfbedc2d628ce2d7cbc08d`。

**CANDIDATE_SUMMARY**

- Node 类型：Product
- 名称：Semiconductor IP
- 边界说明：可复用设计 IP 的 Product/Technology/Segment 粒度需人审；IP core、供应商类别与法律权利不能混同。

**AI REVIEW A**

- recommendation：HUMAN_REQUIRED；native_decision：DEFER
- proposed operation / canonical target：DEFER；范围/说明: IDENTITY_RECOMMENDATION_ONLY; Semiconductor IP / Product; no canonical mutation
- confidence：LOW
- reason：证据实际限定可复用 IP core 设计块，而候选 Semiconductor IP 可覆盖法律权利和供应商门类；Product 名称范围需明确后再建。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-4A5084C7428FBCA2, SC-EV-6FF6BB080099D1E2
- 必要置信度缺口：entity_resolution_clarity=LOW；outcome_completeness=LOW

**AI REVIEW B**

- recommendation：ACCEPT_WITH_REVIEW_NOTE；native_decision：CREATE
- proposed operation / canonical target：CREATE；范围/说明: IDENTITY_ONLY; 00_industry_structure; Semiconductor IP; Product
- confidence：MEDIUM
- reason：IP blocks被明确描述为可许可的可复用组件设计，Product可限定为设计交付物；不含法律权利及供应商行业，目录无等价物。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-4A5084C7428FBCA2, SC-EV-6FF6BB080099D1E2

**A/B RECONCILIATION**

- frozen status：A_B_DISAGREEMENT
- **DISAGREEMENT_TYPE** = DEFER vs CREATE；ACCEPT/NOTE vs HUMAN_REQUIRED；风险判定分歧 R02；风险判定分歧 R04；风险判定分歧 R13；必要置信度判定分歧
- **NATIVE_OPERATION_CONFLICT** = true
- 原生操作：A=DEFER；B=CREATE
- 推荐路由：A=HUMAN_REQUIRED；B=ACCEPT_WITH_REVIEW_NOTE
- R02 低或必要UNKNOWN置信度：A=TRUE；B=FALSE。A依据：按 LOW > UNKNOWN > MEDIUM > HIGH 聚合，本条为 LOW。 B依据：九维按LOW > 必要UNKNOWN > MEDIUM > HIGH聚合为MEDIUM。
- R04 实质命题歧义：A=TRUE；B=FALSE。A依据：（具体证据与边界见本项该审查者 reason） B依据：在明确范围下未见两个会改变本次推荐的证据解释；（具体证据与边界见本项该审查者 reason）
- R13 本体/类型映射问题：A=TRUE；B=FALSE。A依据：（具体证据与边界见本项该审查者 reason） B依据：推荐使用现有对象类型及原生允许操作，不新增本体关系或隐式类型强转。
- 聚合置信度：A=LOW；B=MEDIUM

**EVIDENCE SUMMARY**

- Supporting facts：下列有来源的节选支持本项讨论的对象/命题；支持范围及未解决条件已在上方 A/B reason 中逐项说明。
- SC-EV-4A5084C7428FBCA2 / SC-PHYS-B33C40EBCB5756F7 / PDF p.19 / Electronic design automation (EDA) / printed p.19；excerpt SHA256=`ff3544186334c222507c8cbe9684093fa798ca30cad9742c9f24ba470b6e2063`。
  > Core IP suppliers license reusable components designs – commonly called “IP blocks” or “IPs” – with a defined interface and functionality to design firms to incorporate into their chip layouts.
- SC-EV-6FF6BB080099D1E2 / SC-PHYS-AC86A7FEB4F6ADB5 / PDF p.7 / Design Is Complex and Includes Multiple Different Types of Firms and Activities / printed p.5；excerpt SHA256=`9da9a2377834d759f2de42083bcaa3f4fe5058e8a692338d19c2d69126d80626`。
  > Designers will often use existing, reusable architectural building blocks (core IP) to simplify and accelerate creation of the overall design. In all cases, designers use highly advanced EDA software to automate the design process and ensure that chip designs can be manufactured on distinct and often proprietary fabrication processes.
- Conflicting evidence / unresolved scope：上述 A/B 理由和差异列出已记录的冲突或缺口；未补造反证，也未因省略原文而解除冻结风险。

- **SYSTEM_RECOMMENDED_DECISION** = DEFER
推荐理由（非人工裁决）：优先暂缓：B 可接受的是有界 IP 设计交付物，A 指出原候选 Semiconductor IP 名称还可包含法律权利或供应商门类。限定描述尚未变成新的已批准规范身份，不能在展示层替原候选改名或改类型。

HUMAN_USER_DECISION = [PENDING]

OPTIONS:

- [ ] CREATE
- [ ] REUSE <NODE_ID>
- [ ] DEFER
- [ ] REJECT

---

<a id="sc-cn-0016"></a>
### 044 · SC-CN-0016 · Integrated Device Manufacturer

- **ITEM_NUMBER** = 44
- **ITEM_ID** = SC-CN-0016
- **OBJECT_TYPE** = nodes
- **DOMAIN** = 00_industry_structure
- **CURRENT_NATIVE_OPERATION** = UNDECIDED（没有已填写的人类原生决定）
- **CURRENT_STATUS** = REVIEW
- **WHY_IN_HUMAN_PACKET** = R01_A_B_DISAGREEMENT；R02；R04；R05；R13；REVIEWER_UNRESOLVED_HUMAN_REQUIRED
- **RISK_RULES** = R01 A/B实质分歧；R02 低或必要UNKNOWN置信度；R04 实质命题歧义；R05 身份冲突；R13 本体/类型映射问题
- **MANDATORY_TRIGGER** = R01_A_B_DISAGREEMENT；R02；R04；R05；R13；REVIEWER_UNRESOLVED_HUMAN_REQUIRED
- **SAMPLE_STATUS** = NOT_SAMPLED
- **SAMPLED_FOR_QUALITY_CONTROL** = false

- **SOURCE_ID / SOURCE_NAME** = SC-PHYS-B33C40EBCB5756F7 / SRC_1DD38DEB69830E97 / Strengthening the Global Semiconductor Supply Chain in an Uncertain Era
Source provenance：Semiconductor Industry Association (SIA) / Boston Consulting Group (BCG)；publication=2021-04；edition=；as_of=2021-04；source SHA256=`b33c40ebcb5756f76e887ba2664f97736252e68ba7bfbedc2d628ce2d7cbc08d`。

**CANDIDATE_SUMMARY**

- Node 类型：Segment
- 名称：Integrated Device Manufacturer
- 边界说明：经营模式/企业类别并非具体 Company；以 Segment 表达是否合规需审。

**AI REVIEW A**

- recommendation：HUMAN_REQUIRED；native_decision：DEFER
- proposed operation / canonical target：DEFER；范围/说明: IDENTITY_RECOMMENDATION_ONLY; Integrated Device Manufacturer / Segment; no canonical mutation
- confidence：LOW
- reason：原文是跨设计、制造、封测的企业经营模式，非具体实体；当前 Segment 能否承载业务模式无直接规范依据，保留类型裁决。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-12E0E9FE993C4E6F
- 必要置信度缺口：entity_resolution_clarity=LOW；outcome_completeness=LOW

**AI REVIEW B**

- recommendation：HUMAN_REQUIRED；native_decision：DEFER
- proposed operation / canonical target：DEFER；范围/说明: IDENTITY_ONLY; 00_industry_structure; Integrated Device Manufacturer; Segment
- confidence：UNKNOWN
- reason：证据充分定义IDM企业经营模型，现有类型缺BusinessModel；Segment与企业类别不是自动等价，需类型映射裁定。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-12E0E9FE993C4E6F
- 必要置信度缺口：entity_resolution_clarity=UNKNOWN；rubric_applicability_clarity=UNKNOWN

**A/B RECONCILIATION**

- frozen status：A_B_DISAGREEMENT
- **DISAGREEMENT_TYPE** = 风险判定分歧 R02；风险判定分歧 R04；风险判定分歧 R05；必要置信度判定分歧
- **NATIVE_OPERATION_CONFLICT** = false
- R02 低或必要UNKNOWN置信度：A=TRUE；B=UNKNOWN。A依据：按 LOW > UNKNOWN > MEDIUM > HIGH 聚合，本条为 LOW。 B依据：九维按LOW > 必要UNKNOWN > MEDIUM > HIGH聚合为UNKNOWN。
- R04 实质命题歧义：A=TRUE；B=FALSE。A依据：（具体证据与边界见本项该审查者 reason） B依据：在明确范围下未见两个会改变本次推荐的证据解释；（具体证据与边界见本项该审查者 reason）
- R05 身份冲突：A=FALSE；B=UNKNOWN。A依据：完整 327 节点及 760 别名目录中，未发现本建议产生的身份冲突；明确共享核心者复用。 B依据：对象或关系端点的必要类型尚未统一：（具体证据与边界见本项该审查者 reason）
- 聚合置信度：A=LOW；B=UNKNOWN

**EVIDENCE SUMMARY**

- Supporting facts：下列有来源的节选支持本项讨论的对象/命题；支持范围及未解决条件已在上方 A/B reason 中逐项说明。
- SC-EV-12E0E9FE993C4E6F / SC-PHYS-B33C40EBCB5756F7 / PDF p.24 / IDMs / printed p.24；excerpt SHA256=`1121b61d9f79e680e9eeaff59cbc73321ecaa507817ec71eec65bf1e8c727f68`。
  > IDMs are vertically integrated across multiple parts of the value chain, performing design; fabrication; and assembly, packaging and test activities in- house. In practice, some IDMs have hybrid “fab- lite” models where they outsource some of their production and assembly.
- Conflicting evidence / unresolved scope：上述 A/B 理由和差异列出已记录的冲突或缺口；未补造反证，也未因省略原文而解除冻结风险。

- **SYSTEM_RECOMMENDED_DECISION** = DEFER
推荐理由（非人工裁决）：双方均建议暂缓；风险标签或置信度差异没有补齐身份/类型/证据缺口。优先保留候选等待人工澄清，不强制选择新的目标、关系类型或对象边界。

HUMAN_USER_DECISION = [PENDING]

OPTIONS:

- [ ] CREATE
- [ ] REUSE <NODE_ID>
- [ ] DEFER
- [ ] REJECT

---

<a id="sc-cn-0017"></a>
### 045 · SC-CN-0017 · Fabless

- **ITEM_NUMBER** = 45
- **ITEM_ID** = SC-CN-0017
- **OBJECT_TYPE** = nodes
- **DOMAIN** = 00_industry_structure
- **CURRENT_NATIVE_OPERATION** = UNDECIDED（没有已填写的人类原生决定）
- **CURRENT_STATUS** = REVIEW
- **WHY_IN_HUMAN_PACKET** = R01_A_B_DISAGREEMENT；R02；R04；R05；R13；REVIEWER_UNRESOLVED_HUMAN_REQUIRED
- **RISK_RULES** = R01 A/B实质分歧；R02 低或必要UNKNOWN置信度；R04 实质命题歧义；R05 身份冲突；R13 本体/类型映射问题
- **MANDATORY_TRIGGER** = R01_A_B_DISAGREEMENT；R02；R04；R05；R13；REVIEWER_UNRESOLVED_HUMAN_REQUIRED
- **SAMPLE_STATUS** = NOT_SAMPLED
- **SAMPLED_FOR_QUALITY_CONTROL** = false

- **SOURCE_ID / SOURCE_NAME** = SC-PHYS-B33C40EBCB5756F7 / SRC_1DD38DEB69830E97 / Strengthening the Global Semiconductor Supply Chain in an Uncertain Era
Source provenance：Semiconductor Industry Association (SIA) / Boston Consulting Group (BCG)；publication=2021-04；edition=；as_of=2021-04；source SHA256=`b33c40ebcb5756f76e887ba2664f97736252e68ba7bfbedc2d628ce2d7cbc08d`。

**CANDIDATE_SUMMARY**

- Node 类型：Segment
- 名称：Fabless
- 边界说明：无制造设计公司的经营模式分类，Segment 类型需人审。

**AI REVIEW A**

- recommendation：HUMAN_REQUIRED；native_decision：DEFER
- proposed operation / canonical target：DEFER；范围/说明: IDENTITY_RECOMMENDATION_ONLY; Fabless / Segment; no canonical mutation
- confidence：LOW
- reason：Fabless 指专注设计并外包制造封测的企业模式；不能从企业类别直接推出产业 Segment，需统一经营模式表达。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-4003E3FA6E5B24B4
- 必要置信度缺口：entity_resolution_clarity=LOW；outcome_completeness=LOW

**AI REVIEW B**

- recommendation：HUMAN_REQUIRED；native_decision：DEFER
- proposed operation / canonical target：DEFER；范围/说明: IDENTITY_ONLY; 00_industry_structure; Fabless; Segment
- confidence：UNKNOWN
- reason：Fabless指聚焦设计并外包制造封测的企业模型；不可当具体Company，Segment映射仍缺冻结本体依据。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-4003E3FA6E5B24B4
- 必要置信度缺口：entity_resolution_clarity=UNKNOWN；rubric_applicability_clarity=UNKNOWN

**A/B RECONCILIATION**

- frozen status：A_B_DISAGREEMENT
- **DISAGREEMENT_TYPE** = 风险判定分歧 R02；风险判定分歧 R04；风险判定分歧 R05；必要置信度判定分歧
- **NATIVE_OPERATION_CONFLICT** = false
- R02 低或必要UNKNOWN置信度：A=TRUE；B=UNKNOWN。A依据：按 LOW > UNKNOWN > MEDIUM > HIGH 聚合，本条为 LOW。 B依据：九维按LOW > 必要UNKNOWN > MEDIUM > HIGH聚合为UNKNOWN。
- R04 实质命题歧义：A=TRUE；B=FALSE。A依据：（具体证据与边界见本项该审查者 reason） B依据：在明确范围下未见两个会改变本次推荐的证据解释；（具体证据与边界见本项该审查者 reason）
- R05 身份冲突：A=FALSE；B=UNKNOWN。A依据：完整 327 节点及 760 别名目录中，未发现本建议产生的身份冲突；明确共享核心者复用。 B依据：对象或关系端点的必要类型尚未统一：（具体证据与边界见本项该审查者 reason）
- 聚合置信度：A=LOW；B=UNKNOWN

**EVIDENCE SUMMARY**

- Supporting facts：下列有来源的节选支持本项讨论的对象/命题；支持范围及未解决条件已在上方 A/B reason 中逐项说明。
- SC-EV-4003E3FA6E5B24B4 / SC-PHYS-B33C40EBCB5756F7 / PDF p.24 / Fabless / printed p.24；excerpt SHA256=`a3a7f8b09f8936fedb8bab81572a0ca049af160f400a21fbed0044352e043237`。
  > Fabless firms choose to focus on design and outsource fabrication as well as assembly, packaging, and testing.
- Conflicting evidence / unresolved scope：上述 A/B 理由和差异列出已记录的冲突或缺口；未补造反证，也未因省略原文而解除冻结风险。

- **SYSTEM_RECOMMENDED_DECISION** = DEFER
推荐理由（非人工裁决）：双方均建议暂缓；风险标签或置信度差异没有补齐身份/类型/证据缺口。优先保留候选等待人工澄清，不强制选择新的目标、关系类型或对象边界。

HUMAN_USER_DECISION = [PENDING]

OPTIONS:

- [ ] CREATE
- [ ] REUSE <NODE_ID>
- [ ] DEFER
- [ ] REJECT

---

<a id="sc-cn-0018"></a>
### 046 · SC-CN-0018 · Semiconductor Foundry

- **ITEM_NUMBER** = 46
- **ITEM_ID** = SC-CN-0018
- **OBJECT_TYPE** = nodes
- **DOMAIN** = 00_industry_structure
- **CURRENT_NATIVE_OPERATION** = UNDECIDED（没有已填写的人类原生决定）
- **CURRENT_STATUS** = REVIEW
- **WHY_IN_HUMAN_PACKET** = R01_A_B_DISAGREEMENT；R02；R04；R05；R13；REVIEWER_UNRESOLVED_HUMAN_REQUIRED
- **RISK_RULES** = R01 A/B实质分歧；R02 低或必要UNKNOWN置信度；R04 实质命题歧义；R05 身份冲突；R13 本体/类型映射问题
- **MANDATORY_TRIGGER** = R01_A_B_DISAGREEMENT；R02；R04；R05；R13；REVIEWER_UNRESOLVED_HUMAN_REQUIRED
- **SAMPLE_STATUS** = NOT_SAMPLED
- **SAMPLED_FOR_QUALITY_CONTROL** = false

- **SOURCE_ID / SOURCE_NAME** = SC-PHYS-B33C40EBCB5756F7 / SRC_1DD38DEB69830E97 / Strengthening the Global Semiconductor Supply Chain in an Uncertain Era
Source provenance：Semiconductor Industry Association (SIA) / Boston Consulting Group (BCG)；publication=2021-04；edition=；as_of=2021-04；source SHA256=`b33c40ebcb5756f76e887ba2664f97736252e68ba7bfbedc2d628ce2d7cbc08d`。

**CANDIDATE_SUMMARY**

- Node 类型：Segment
- 名称：Semiconductor Foundry
- 边界说明：代工业务模型、实际 fab 设施与具体公司需区分；Segment 候选。

**AI REVIEW A**

- recommendation：HUMAN_REQUIRED；native_decision：DEFER
- proposed operation / canonical target：DEFER；范围/说明: IDENTITY_RECOMMENDATION_ONLY; Semiconductor Foundry / Segment; no canonical mutation
- confidence：LOW
- reason：foundry 原文指第三方制造业务且 IDM 可兼营；与 fab 设施、公司身份可区别，但 Segment 对该业务模式的承载仍待明确。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-E635E342EE356D7D
- 必要置信度缺口：entity_resolution_clarity=LOW；outcome_completeness=LOW

**AI REVIEW B**

- recommendation：HUMAN_REQUIRED；native_decision：DEFER
- proposed operation / canonical target：DEFER；范围/说明: IDENTITY_ONLY; 00_industry_structure; Semiconductor Foundry; Segment
- confidence：UNKNOWN
- reason：foundry语境是为第三方制造的业务/企业类别；与fab设施及Wafer Fabrication工艺均不同，Segment粒度待裁定。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-E635E342EE356D7D
- 必要置信度缺口：entity_resolution_clarity=UNKNOWN；rubric_applicability_clarity=UNKNOWN

**A/B RECONCILIATION**

- frozen status：A_B_DISAGREEMENT
- **DISAGREEMENT_TYPE** = 风险判定分歧 R02；风险判定分歧 R04；风险判定分歧 R05；必要置信度判定分歧
- **NATIVE_OPERATION_CONFLICT** = false
- R02 低或必要UNKNOWN置信度：A=TRUE；B=UNKNOWN。A依据：按 LOW > UNKNOWN > MEDIUM > HIGH 聚合，本条为 LOW。 B依据：九维按LOW > 必要UNKNOWN > MEDIUM > HIGH聚合为UNKNOWN。
- R04 实质命题歧义：A=TRUE；B=FALSE。A依据：（具体证据与边界见本项该审查者 reason） B依据：在明确范围下未见两个会改变本次推荐的证据解释；（具体证据与边界见本项该审查者 reason）
- R05 身份冲突：A=FALSE；B=UNKNOWN。A依据：完整 327 节点及 760 别名目录中，未发现本建议产生的身份冲突；明确共享核心者复用。 B依据：对象或关系端点的必要类型尚未统一：（具体证据与边界见本项该审查者 reason）
- 聚合置信度：A=LOW；B=UNKNOWN

**EVIDENCE SUMMARY**

- Supporting facts：下列有来源的节选支持本项讨论的对象/命题；支持范围及未解决条件已在上方 A/B reason 中逐项说明。
- SC-EV-E635E342EE356D7D / SC-PHYS-B33C40EBCB5756F7 / PDF p.25 / Foundries / printed p.25；excerpt SHA256=`466a26891f7f4559951d016386de0aa52e1f14b51d6354e3a231d04028318558`。
  > Most foundries are focused purely on manufacturing for third parties, although some IDMs with strong manufacturing capabilities may also choose to make chips for others in addition to their own.
- Conflicting evidence / unresolved scope：上述 A/B 理由和差异列出已记录的冲突或缺口；未补造反证，也未因省略原文而解除冻结风险。

- **SYSTEM_RECOMMENDED_DECISION** = DEFER
推荐理由（非人工裁决）：双方均建议暂缓；风险标签或置信度差异没有补齐身份/类型/证据缺口。优先保留候选等待人工澄清，不强制选择新的目标、关系类型或对象边界。

HUMAN_USER_DECISION = [PENDING]

OPTIONS:

- [ ] CREATE
- [ ] REUSE <NODE_ID>
- [ ] DEFER
- [ ] REJECT

---

<a id="sc-cn-0019"></a>
### 047 · SC-CN-0019 · Outsourced Assembly and Test

- **ITEM_NUMBER** = 47
- **ITEM_ID** = SC-CN-0019
- **OBJECT_TYPE** = nodes
- **DOMAIN** = 00_industry_structure
- **CURRENT_NATIVE_OPERATION** = UNDECIDED（没有已填写的人类原生决定）
- **CURRENT_STATUS** = REVIEW
- **WHY_IN_HUMAN_PACKET** = R01_A_B_DISAGREEMENT；R02；R04；R05；R13；REVIEWER_UNRESOLVED_HUMAN_REQUIRED
- **RISK_RULES** = R01 A/B实质分歧；R02 低或必要UNKNOWN置信度；R04 实质命题歧义；R05 身份冲突；R13 本体/类型映射问题
- **MANDATORY_TRIGGER** = R01_A_B_DISAGREEMENT；R02；R04；R05；R13；REVIEWER_UNRESOLVED_HUMAN_REQUIRED
- **SAMPLE_STATUS** = NOT_SAMPLED
- **SAMPLED_FOR_QUALITY_CONTROL** = false

- **SOURCE_ID / SOURCE_NAME** = SC-PHYS-B33C40EBCB5756F7 / SRC_1DD38DEB69830E97 / Strengthening the Global Semiconductor Supply Chain in an Uncertain Era
Source provenance：Semiconductor Industry Association (SIA) / Boston Consulting Group (BCG)；publication=2021-04；edition=；as_of=2021-04；source SHA256=`b33c40ebcb5756f76e887ba2664f97736252e68ba7bfbedc2d628ce2d7cbc08d`。

**CANDIDATE_SUMMARY**

- Node 类型：Segment
- 名称：Outsourced Assembly and Test
- 边界说明：外包封测业务类别，非具体 Company；需批准经营模式类型。

**AI REVIEW A**

- recommendation：HUMAN_REQUIRED；native_decision：DEFER
- proposed operation / canonical target：DEFER；范围/说明: IDENTITY_RECOMMENDATION_ONLY; Outsourced Assembly and Test / Segment; no canonical mutation
- confidence：LOW
- reason：OSAT 描述合同封测服务，不能等同既有封装环节全部；经营模式/服务集合的 Segment 边界尚需裁决。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-B4C418CD78B4A228
- 必要置信度缺口：entity_resolution_clarity=LOW；outcome_completeness=LOW

**AI REVIEW B**

- recommendation：HUMAN_REQUIRED；native_decision：DEFER
- proposed operation / canonical target：DEFER；范围/说明: IDENTITY_ONLY; 00_industry_structure; Outsourced Assembly and Test; Segment
- confidence：UNKNOWN
- reason：OSAT为合同封装测试服务商类别而非单个公司；其Segment表达需保持服务业务和企业类型边界。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-B4C418CD78B4A228
- 必要置信度缺口：entity_resolution_clarity=UNKNOWN；rubric_applicability_clarity=UNKNOWN

**A/B RECONCILIATION**

- frozen status：A_B_DISAGREEMENT
- **DISAGREEMENT_TYPE** = 风险判定分歧 R02；风险判定分歧 R04；风险判定分歧 R05；必要置信度判定分歧
- **NATIVE_OPERATION_CONFLICT** = false
- R02 低或必要UNKNOWN置信度：A=TRUE；B=UNKNOWN。A依据：按 LOW > UNKNOWN > MEDIUM > HIGH 聚合，本条为 LOW。 B依据：九维按LOW > 必要UNKNOWN > MEDIUM > HIGH聚合为UNKNOWN。
- R04 实质命题歧义：A=TRUE；B=FALSE。A依据：（具体证据与边界见本项该审查者 reason） B依据：在明确范围下未见两个会改变本次推荐的证据解释；（具体证据与边界见本项该审查者 reason）
- R05 身份冲突：A=FALSE；B=UNKNOWN。A依据：完整 327 节点及 760 别名目录中，未发现本建议产生的身份冲突；明确共享核心者复用。 B依据：对象或关系端点的必要类型尚未统一：（具体证据与边界见本项该审查者 reason）
- 聚合置信度：A=LOW；B=UNKNOWN

**EVIDENCE SUMMARY**

- Supporting facts：下列有来源的节选支持本项讨论的对象/命题；支持范围及未解决条件已在上方 A/B reason 中逐项说明。
- SC-EV-B4C418CD78B4A228 / SC-PHYS-B33C40EBCB5756F7 / PDF p.25 / OSATs / printed p.25；excerpt SHA256=`6e98f185533d3829751e6afc738844c3a72089e8cb7f4339723840a9c9f7ee3a`。
  > OSATs provide assembly, packaging and test services under contract to both IDMs and fabless companies.
- Conflicting evidence / unresolved scope：上述 A/B 理由和差异列出已记录的冲突或缺口；未补造反证，也未因省略原文而解除冻结风险。

- **SYSTEM_RECOMMENDED_DECISION** = DEFER
推荐理由（非人工裁决）：双方均建议暂缓；风险标签或置信度差异没有补齐身份/类型/证据缺口。优先保留候选等待人工澄清，不强制选择新的目标、关系类型或对象边界。

HUMAN_USER_DECISION = [PENDING]

OPTIONS:

- [ ] CREATE
- [ ] REUSE <NODE_ID>
- [ ] DEFER
- [ ] REJECT

---

<a id="sc-cn-0028"></a>
### 048 · SC-CN-0028 · Chip

- **ITEM_NUMBER** = 48
- **ITEM_ID** = SC-CN-0028
- **OBJECT_TYPE** = nodes
- **DOMAIN** = 01_design_enablement
- **CURRENT_NATIVE_OPERATION** = UNDECIDED（没有已填写的人类原生决定）
- **CURRENT_STATUS** = REVIEW
- **WHY_IN_HUMAN_PACKET** = R01_A_B_DISAGREEMENT；R02；R04；R05；REVIEWER_UNRESOLVED_HUMAN_REQUIRED
- **RISK_RULES** = R01 A/B实质分歧；R02 低或必要UNKNOWN置信度；R04 实质命题歧义；R05 身份冲突
- **MANDATORY_TRIGGER** = R01_A_B_DISAGREEMENT；R02；R04；R05；REVIEWER_UNRESOLVED_HUMAN_REQUIRED
- **SAMPLE_STATUS** = NOT_SAMPLED
- **SAMPLED_FOR_QUALITY_CONTROL** = false

- **SOURCE_ID / SOURCE_NAME** = SC-PHYS-7E064380CA686D9F / SRC_5AF7599EF3DE9C6D / Explaining Common Chip Terms
Source provenance：Intel；publication=2026-03-09；edition=；as_of=2026-03-09；source SHA256=`7e064380ca686d9f00c235f15c007523e89e4a0ffb7e9a22f435218c06799d05`。

**CANDIDATE_SUMMARY**

- Node 类型：Product
- 名称：Chip
- 边界说明：Source 明示 chip 可指 die 或 package；不建立歧义泛节点。

**AI REVIEW A**

- recommendation：HUMAN_REQUIRED；native_decision：DEFER
- proposed operation / canonical target：DEFER；范围/说明: IDENTITY_RECOMMENDATION_ONLY; Chip / Product; no canonical mutation
- confidence：LOW
- reason：Intel 明示 chip 可指 die 或封装件，两个解释改变对象边界；本批不能选择一个义项而维持无限定名称。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-03CECD46D2542360
- 必要置信度缺口：entity_resolution_clarity=LOW；outcome_completeness=LOW

**AI REVIEW B**

- recommendation：HUMAN_REQUIRED；native_decision：REJECT
- proposed operation / canonical target：REJECT；范围/说明: IDENTITY_ONLY; 01_design_enablement; Chip; Product
- confidence：HIGH
- reason：同一摘录明言chip可指裸die或封装版本；拒绝建立无消歧的泛节点，SC-CN-0027只覆盖前者，歧义仍需人工处理。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-03CECD46D2542360

**A/B RECONCILIATION**

- frozen status：A_B_DISAGREEMENT
- **DISAGREEMENT_TYPE** = DEFER vs REJECT；风险判定分歧 R02；风险判定分歧 R05；必要置信度判定分歧
- **NATIVE_OPERATION_CONFLICT** = true
- 原生操作：A=DEFER；B=REJECT
- R02 低或必要UNKNOWN置信度：A=TRUE；B=FALSE。A依据：按 LOW > UNKNOWN > MEDIUM > HIGH 聚合，本条为 LOW。 B依据：九维按LOW > 必要UNKNOWN > MEDIUM > HIGH聚合为HIGH。
- R05 身份冲突：A=FALSE；B=TRUE。A依据：完整 327 节点及 760 别名目录中，未发现本建议产生的身份冲突；明确共享核心者复用。 B依据：不同身份或范围解释尚未收敛：（具体证据与边界见本项该审查者 reason）
- 聚合置信度：A=LOW；B=HIGH

**EVIDENCE SUMMARY**

- Supporting facts：下列有来源的节选支持本项讨论的对象/命题；支持范围及未解决条件已在上方 A/B reason 中逐项说明。
- SC-EV-03CECD46D2542360 / SC-PHYS-7E064380CA686D9F / PDF p.3 / Wafers Become Dies, Packaging Makes Chips / printed p.NOT_KNOWN_OR_UNNUMBERED；excerpt SHA256=`64b20b3f57ab13ec1233287a6131da688c6e9cff7aa92737fc5f855861b94190`。
  > The definition of chip is less rigid — while it can refer to a single die (which is like a little chip of glass), usually it’s associated with the packaged version since that’s the only way the non-chipmaking public encounters it.
- Conflicting evidence / unresolved scope：上述 A/B 理由和差异列出已记录的冲突或缺口；未补造反证，也未因省略原文而解除冻结风险。

- **SYSTEM_RECOMMENDED_DECISION** = REJECT
推荐理由（非人工裁决）：优先建议拒绝当前未消歧的 Chip 节点：双方都承认 Intel 明示裸 die 与封装件两种对象。B 的 REJECT 直接针对当前泛名候选的身份不唯一；不表示否定相关概念，也不创建替代节点。A 的 DEFER 仍原样保留，最终由人工决定。

HUMAN_USER_DECISION = [PENDING]

OPTIONS:

- [ ] CREATE
- [ ] REUSE <NODE_ID>
- [ ] DEFER
- [ ] REJECT

---

<a id="sc-cn-0037"></a>
### 049 · SC-CN-0037 · Quartz Crucible

- **ITEM_NUMBER** = 49
- **ITEM_ID** = SC-CN-0037
- **OBJECT_TYPE** = nodes
- **DOMAIN** = 02_wafer_materials
- **CURRENT_NATIVE_OPERATION** = UNDECIDED（没有已填写的人类原生决定）
- **CURRENT_STATUS** = REVIEW
- **WHY_IN_HUMAN_PACKET** = R01_A_B_DISAGREEMENT；R02；R04；R05；R13；REVIEWER_UNRESOLVED_HUMAN_REQUIRED
- **RISK_RULES** = R01 A/B实质分歧；R02 低或必要UNKNOWN置信度；R04 实质命题歧义；R05 身份冲突；R13 本体/类型映射问题
- **MANDATORY_TRIGGER** = R01_A_B_DISAGREEMENT；R02；R04；R05；R13；REVIEWER_UNRESOLVED_HUMAN_REQUIRED
- **SAMPLE_STATUS** = NOT_SAMPLED
- **SAMPLED_FOR_QUALITY_CONTROL** = false

- **SOURCE_ID / SOURCE_NAME** = SC-PHYS-9E9CEFC24043585C / SRC_8442AD30618C9A2D / Production Processes
Source provenance：SUMCO Corporation；publication=；edition=；as_of=；source SHA256=`9e9cefc24043585c1c5a484340dcf49aa0725b341467942d3d4c34be0da8aee6`。

**CANDIDATE_SUMMARY**

- Node 类型：Equipment
- 名称：Quartz Crucible
- 边界说明：可耗用容器/零部件；Equipment 对比 Product 的粒度需审，不归为硅原料。

**AI REVIEW A**

- recommendation：HUMAN_REQUIRED；native_decision：DEFER
- proposed operation / canonical target：DEFER；范围/说明: IDENTITY_RECOMMENDATION_ONLY; Quartz Crucible / Equipment; no canonical mutation
- confidence：LOW
- reason：原文确认 quartz crucible 是盛放熔料的容器，但 Equipment 与耗材 Product 边界无法由该句裁定；不按原料 Material 处理。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-1811D226786D163F
- 必要置信度缺口：entity_resolution_clarity=LOW；outcome_completeness=LOW

**AI REVIEW B**

- recommendation：HUMAN_REQUIRED；native_decision：DEFER
- proposed operation / canonical target：DEFER；范围/说明: IDENTITY_ONLY; 02_wafer_materials; Quartz Crucible; Equipment
- confidence：UNKNOWN
- reason：石英坩埚作为熔化容器有直接支持，但Equipment与耗用Product/部件的类型边界未给出；不得仅据出现就定设备。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-1811D226786D163F
- 必要置信度缺口：entity_resolution_clarity=UNKNOWN；rubric_applicability_clarity=UNKNOWN

**A/B RECONCILIATION**

- frozen status：A_B_DISAGREEMENT
- **DISAGREEMENT_TYPE** = 风险判定分歧 R02；风险判定分歧 R04；风险判定分歧 R05；必要置信度判定分歧
- **NATIVE_OPERATION_CONFLICT** = false
- R02 低或必要UNKNOWN置信度：A=TRUE；B=UNKNOWN。A依据：按 LOW > UNKNOWN > MEDIUM > HIGH 聚合，本条为 LOW。 B依据：九维按LOW > 必要UNKNOWN > MEDIUM > HIGH聚合为UNKNOWN。
- R04 实质命题歧义：A=TRUE；B=FALSE。A依据：（具体证据与边界见本项该审查者 reason） B依据：在明确范围下未见两个会改变本次推荐的证据解释；（具体证据与边界见本项该审查者 reason）
- R05 身份冲突：A=FALSE；B=UNKNOWN。A依据：完整 327 节点及 760 别名目录中，未发现本建议产生的身份冲突；明确共享核心者复用。 B依据：对象或关系端点的必要类型尚未统一：（具体证据与边界见本项该审查者 reason）
- 聚合置信度：A=LOW；B=UNKNOWN

**EVIDENCE SUMMARY**

- Supporting facts：下列有来源的节选支持本项讨论的对象/命题；支持范围及未解决条件已在上方 A/B reason 中逐项说明。
- SC-EV-1811D226786D163F / SC-PHYS-9E9CEFC24043585C / PDF p.2 / Flow of CZ process / printed p.NOT_KNOWN_OR_UNNUMBERED；excerpt SHA256=`014615fff3d822d511b8420e52cb198218ff0c9777d64741ed7f5b226d6ceb9c`。
  > Polysilicon purified until the metal impurities are no more than a few parts per billion (ppb) is put into a quartz crucible along with boron (B) and phosphorous (P), and melted at a temperature of around 1420℃.
- Conflicting evidence / unresolved scope：上述 A/B 理由和差异列出已记录的冲突或缺口；未补造反证，也未因省略原文而解除冻结风险。

- **SYSTEM_RECOMMENDED_DECISION** = DEFER
推荐理由（非人工裁决）：双方均建议暂缓；风险标签或置信度差异没有补齐身份/类型/证据缺口。优先保留候选等待人工澄清，不强制选择新的目标、关系类型或对象边界。

HUMAN_USER_DECISION = [PENDING]

OPTIONS:

- [ ] CREATE
- [ ] REUSE <NODE_ID>
- [ ] DEFER
- [ ] REJECT

---

<a id="sc-cn-0050"></a>
### 050 · SC-CN-0050 · Annealed Silicon Wafer

- **ITEM_NUMBER** = 50
- **ITEM_ID** = SC-CN-0050
- **OBJECT_TYPE** = nodes
- **DOMAIN** = 02_wafer_materials
- **CURRENT_NATIVE_OPERATION** = UNDECIDED（没有已填写的人类原生决定）
- **CURRENT_STATUS** = REVIEW
- **WHY_IN_HUMAN_PACKET** = R01_A_B_DISAGREEMENT；R02；R04；R13；REVIEWER_UNRESOLVED_HUMAN_REQUIRED
- **RISK_RULES** = R01 A/B实质分歧；R02 低或必要UNKNOWN置信度；R04 实质命题歧义；R13 本体/类型映射问题
- **MANDATORY_TRIGGER** = R01_A_B_DISAGREEMENT；R02；R04；R13；REVIEWER_UNRESOLVED_HUMAN_REQUIRED
- **SAMPLE_STATUS** = NOT_SAMPLED
- **SAMPLED_FOR_QUALITY_CONTROL** = false

- **SOURCE_ID / SOURCE_NAME** = SC-PHYS-9E9CEFC24043585C / SRC_8442AD30618C9A2D / Production Processes
Source provenance：SUMCO Corporation；publication=；edition=；as_of=；source SHA256=`9e9cefc24043585c1c5a484340dcf49aa0725b341467942d3d4c34be0da8aee6`。

**CANDIDATE_SUMMARY**

- Node 类型：Material
- 名称：Annealed Silicon Wafer
- 边界说明：独立产品状态还是 Silicon Wafer 属性，待粒度审查。

**AI REVIEW A**

- recommendation：HUMAN_REQUIRED；native_decision：DEFER
- proposed operation / canonical target：DEFER；范围/说明: IDENTITY_RECOMMENDATION_ONLY; Annealed Silicon Wafer / Material; no canonical mutation
- confidence：LOW
- reason：仅确认退火后晶圆性能改善，不能确定这是独立材料族还是 Silicon Wafer 的加工状态；独立节点粒度影响身份。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-B0A9AF87FF9B65B0
- 必要置信度缺口：entity_resolution_clarity=LOW；outcome_completeness=LOW

**AI REVIEW B**

- recommendation：ACCEPT_WITH_REVIEW_NOTE；native_decision：CREATE
- proposed operation / canonical target：CREATE；范围/说明: IDENTITY_ONLY; 02_wafer_materials; Annealed Silicon Wafer; Material
- confidence：MEDIUM
- reason：Annealed Wafers章节明确退火后的材料状态及改善表层特征，可有界保留加工硅片种类；不宣称新化学材料或通用性能。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-B0A9AF87FF9B65B0

**A/B RECONCILIATION**

- frozen status：A_B_DISAGREEMENT
- **DISAGREEMENT_TYPE** = DEFER vs CREATE；ACCEPT/NOTE vs HUMAN_REQUIRED；风险判定分歧 R02；风险判定分歧 R04；风险判定分歧 R13；必要置信度判定分歧
- **NATIVE_OPERATION_CONFLICT** = true
- 原生操作：A=DEFER；B=CREATE
- 推荐路由：A=HUMAN_REQUIRED；B=ACCEPT_WITH_REVIEW_NOTE
- R02 低或必要UNKNOWN置信度：A=TRUE；B=FALSE。A依据：按 LOW > UNKNOWN > MEDIUM > HIGH 聚合，本条为 LOW。 B依据：九维按LOW > 必要UNKNOWN > MEDIUM > HIGH聚合为MEDIUM。
- R04 实质命题歧义：A=TRUE；B=FALSE。A依据：（具体证据与边界见本项该审查者 reason） B依据：在明确范围下未见两个会改变本次推荐的证据解释；（具体证据与边界见本项该审查者 reason）
- R13 本体/类型映射问题：A=TRUE；B=FALSE。A依据：（具体证据与边界见本项该审查者 reason） B依据：推荐使用现有对象类型及原生允许操作，不新增本体关系或隐式类型强转。
- 聚合置信度：A=LOW；B=MEDIUM

**EVIDENCE SUMMARY**

- Supporting facts：下列有来源的节选支持本项讨论的对象/命题；支持范围及未解决条件已在上方 A/B reason 中逐项说明。
- SC-EV-B0A9AF87FF9B65B0 / SC-PHYS-9E9CEFC24043585C / PDF p.6 / Specialized processing / Annealed Wafers / printed p.NOT_KNOWN_OR_UNNUMBERED；excerpt SHA256=`767ea134e24883643a5e4a6af769da47d7b49995846f1d7cb7d4d057275af248`。
  > A polished wafer undergoes high-temperature annealing in an atmosphere of hydrogen or argon. As this process removes oxygen near the wafer surface, the resulting wafer has improved crystal perfection.
- Conflicting evidence / unresolved scope：上述 A/B 理由和差异列出已记录的冲突或缺口；未补造反证，也未因省略原文而解除冻结风险。

- **SYSTEM_RECOMMENDED_DECISION** = DEFER
推荐理由（非人工裁决）：优先暂缓：B 的 CREATE 依赖把加工状态视作独立硅片类别，而 A 要求先确定材料族与加工状态的粒度。证据支持退火处理，尚不能单独决定 canonical 建模层级。

HUMAN_USER_DECISION = [PENDING]

OPTIONS:

- [ ] CREATE
- [ ] REUSE <NODE_ID>
- [ ] DEFER
- [ ] REJECT

---

<a id="sc-cn-0057"></a>
### 051 · SC-CN-0057 · Lithography Scanner / Stepper

- **ITEM_NUMBER** = 51
- **ITEM_ID** = SC-CN-0057
- **OBJECT_TYPE** = nodes
- **DOMAIN** = 03_fab_process_equipment
- **CURRENT_NATIVE_OPERATION** = UNDECIDED（没有已填写的人类原生决定）
- **CURRENT_STATUS** = REVIEW
- **WHY_IN_HUMAN_PACKET** = R01_A_B_DISAGREEMENT；R02；R04；R05；R13；REVIEWER_UNRESOLVED_HUMAN_REQUIRED
- **RISK_RULES** = R01 A/B实质分歧；R02 低或必要UNKNOWN置信度；R04 实质命题歧义；R05 身份冲突；R13 本体/类型映射问题
- **MANDATORY_TRIGGER** = R01_A_B_DISAGREEMENT；R02；R04；R05；R13；REVIEWER_UNRESOLVED_HUMAN_REQUIRED
- **SAMPLE_STATUS** = NOT_SAMPLED
- **SAMPLED_FOR_QUALITY_CONTROL** = false

- **SOURCE_ID / SOURCE_NAME** = SC-PHYS-C5B6DC633E156218 / SRC_AC29CFEE56F74F5B / Testimony of the Semiconductor Industry Association before the Senate Committee on Environment & Public Works (March 4, 2026)
Source provenance：Semiconductor Industry Association (SIA)；publication=2026-03-04；edition=；as_of=2026-03-04；source SHA256=`c5b6dc633e156218eb950f2dee88f43fbdcc4fc1744a5924f12b977f5cb7df71`。

**CANDIDATE_SUMMARY**

- Node 类型：Equipment
- 名称：Lithography Scanner / Stepper
- 边界说明：Scanner 与 Stepper 是两个子类；优先审查共同父类 Lithography Equipment，不造合并设备身份。

**AI REVIEW A**

- recommendation：HUMAN_REQUIRED；native_decision：DEFER
- proposed operation / canonical target：DEFER；范围/说明: IDENTITY_RECOMMENDATION_ONLY; Lithography Scanner / Stepper / Equipment; no canonical mutation
- confidence：LOW
- reason：stepper 或 scanner 是设备替代类别，斜杠名称可能合并不同设备；证据支持共同用途却未确定统一 canonical 粒度。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-67EC75515BB09180
- 必要置信度缺口：entity_resolution_clarity=LOW；outcome_completeness=LOW

**AI REVIEW B**

- recommendation：HUMAN_REQUIRED；native_decision：DEFER
- proposed operation / canonical target：DEFER；范围/说明: IDENTITY_ONLY; 03_fab_process_equipment; Lithography Scanner / Stepper; Equipment
- confidence：UNKNOWN
- reason：stepper或scanner为两种替代设备，斜杠名称把设备子类并为单身份；共同父设备或拆分会改变端点，暂缓。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-67EC75515BB09180
- 必要置信度缺口：entity_resolution_clarity=UNKNOWN；rubric_applicability_clarity=UNKNOWN

**A/B RECONCILIATION**

- frozen status：A_B_DISAGREEMENT
- **DISAGREEMENT_TYPE** = 风险判定分歧 R02；风险判定分歧 R05；必要置信度判定分歧
- **NATIVE_OPERATION_CONFLICT** = false
- R02 低或必要UNKNOWN置信度：A=TRUE；B=UNKNOWN。A依据：按 LOW > UNKNOWN > MEDIUM > HIGH 聚合，本条为 LOW。 B依据：九维按LOW > 必要UNKNOWN > MEDIUM > HIGH聚合为UNKNOWN。
- R05 身份冲突：A=FALSE；B=TRUE。A依据：完整 327 节点及 760 别名目录中，未发现本建议产生的身份冲突；明确共享核心者复用。 B依据：不同身份或范围解释尚未收敛：（具体证据与边界见本项该审查者 reason）
- 聚合置信度：A=LOW；B=UNKNOWN

**EVIDENCE SUMMARY**

- Supporting facts：下列有来源的节选支持本项讨论的对象/命题；支持范围及未解决条件已在上方 A/B reason 中逐项说明。
- SC-EV-67EC75515BB09180 / SC-PHYS-C5B6DC633E156218 / PDF p.4 / II / Front-End Fabrication / Photolithography / printed p.4；excerpt SHA256=`d49de79df3fb0e595282e9746bcd100459e0a41920f737ed1446f4908192c3a1`。
  > A stepper or scanner (using deep ultraviolet or extreme ultraviolet light) aligns the wafer to a glass photomask and projects intense light through the mask or reticle, exposing the photoresist with the pattern.
- Conflicting evidence / unresolved scope：上述 A/B 理由和差异列出已记录的冲突或缺口；未补造反证，也未因省略原文而解除冻结风险。

- **SYSTEM_RECOMMENDED_DECISION** = DEFER
推荐理由（非人工裁决）：双方均建议暂缓；风险标签或置信度差异没有补齐身份/类型/证据缺口。优先保留候选等待人工澄清，不强制选择新的目标、关系类型或对象边界。

HUMAN_USER_DECISION = [PENDING]

OPTIONS:

- [ ] CREATE
- [ ] REUSE <NODE_ID>
- [ ] DEFER
- [ ] REJECT

---

<a id="sc-cn-0082"></a>
### 052 · SC-CN-0082 · Packaging Encapsulant

- **ITEM_NUMBER** = 52
- **ITEM_ID** = SC-CN-0082
- **OBJECT_TYPE** = nodes
- **DOMAIN** = 03_fab_process_equipment
- **CURRENT_NATIVE_OPERATION** = UNDECIDED（没有已填写的人类原生决定）
- **CURRENT_STATUS** = REVIEW
- **WHY_IN_HUMAN_PACKET** = R01_A_B_DISAGREEMENT；R07；REVIEWER_UNRESOLVED_HUMAN_REQUIRED
- **RISK_RULES** = R01 A/B实质分歧；R07 新增高影响Node
- **MANDATORY_TRIGGER** = R01_A_B_DISAGREEMENT；R07；REVIEWER_UNRESOLVED_HUMAN_REQUIRED
- **SAMPLE_STATUS** = NOT_SAMPLED
- **SAMPLED_FOR_QUALITY_CONTROL** = false

- **SOURCE_ID / SOURCE_NAME** = SC-PHYS-C5B6DC633E156218 / SRC_AC29CFEE56F74F5B / Testimony of the Semiconductor Industry Association before the Senate Committee on Environment & Public Works (March 4, 2026)
Source provenance：Semiconductor Industry Association (SIA)；publication=2026-03-04；edition=；as_of=2026-03-04；source SHA256=`c5b6dc633e156218eb950f2dee88f43fbdcc4fc1744a5924f12b977f5cb7df71`。

**CANDIDATE_SUMMARY**

- Node 类型：Material
- 名称：Packaging Encapsulant
- 备选身份：NODE_20260817_6BF58D0C
- 边界说明：伞形功能材料；含 underfill/coatings/mold compounds，不能等同 Epoxy Molding Compound。
- Canonical state：NODE_20260817_6BF58D0C = Epoxy Molding Compound；type=Material；status=active。

**AI REVIEW A**

- recommendation：ACCEPT；native_decision：CREATE
- proposed operation / canonical target：CREATE；范围/说明: IDENTITY_RECOMMENDATION_ONLY; Packaging Encapsulant / Material; no canonical mutation
- confidence：HIGH
- reason：encapsulants 在原文包含 underfill/coatings/mold compounds，材料伞类比 Epoxy Molding Compound 广，不能复用其子类。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-7C75F6F0987ACA80

**AI REVIEW B**

- recommendation：HUMAN_REQUIRED；native_decision：CREATE
- proposed operation / canonical target：CREATE；范围/说明: IDENTITY_ONLY; 03_fab_process_equipment; Packaging Encapsulant; Material
- confidence：HIGH
- reason：原文把underfill/coatings/mold compounds纳入encapsulants，泛材料族不等同EMC；SC-RL-0049将既有Underfill置于新父层，需结构人审。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-7C75F6F0987ACA80

**A/B RECONCILIATION**

- frozen status：A_B_DISAGREEMENT
- **DISAGREEMENT_TYPE** = ACCEPT/NOTE vs HUMAN_REQUIRED；风险判定分歧 R07
- **NATIVE_OPERATION_CONFLICT** = false
- 推荐路由：A=ACCEPT；B=HUMAN_REQUIRED
- R07 新增高影响Node：A=FALSE；B=TRUE。A依据：本条为普通局部身份建议，未建立跨域共享/关键层级或 View/Impact 锚点；非因新建自动判高影响。 B依据：有具体关键结构/平台依赖：（具体证据与边界见本项该审查者 reason）

**EVIDENCE SUMMARY**

- Supporting facts：下列有来源的节选支持本项讨论的对象/命题；支持范围及未解决条件已在上方 A/B reason 中逐项说明。
- SC-EV-7C75F6F0987ACA80 / SC-PHYS-C5B6DC633E156218 / PDF p.6 / II / Packaging / printed p.6；excerpt SHA256=`7c0174c07077c1aef124bbf97d88cfb8c66091f1c22eefc51f5911112f2f06a0`。
  > To protect against humidity, chemicals, and vibration, connections are enclosed with encapsulants such as underfill, coatings, or mold compounds.
- Conflicting evidence / unresolved scope：上述 A/B 理由和差异列出已记录的冲突或缺口；未补造反证，也未因省略原文而解除冻结风险。

- **SYSTEM_RECOMMENDED_DECISION** = CREATE
推荐理由（非人工裁决）：双方均支持同一个 CREATE 提议，分歧在是否构成结构性高影响，而非创建对象、类型或证据支持。系统建议保留共同 CREATE 方向供人工确认，并完整保留较严格的 R07 与 mandatory 路由；没有替人工裁定该风险分歧。

HUMAN_USER_DECISION = [PENDING]

OPTIONS:

- [ ] CREATE
- [ ] REUSE <NODE_ID>
- [ ] DEFER
- [ ] REJECT

---

<a id="sc-cn-0083"></a>
### 053 · SC-CN-0083 · Semiconductor Cleanroom

- **ITEM_NUMBER** = 53
- **ITEM_ID** = SC-CN-0083
- **OBJECT_TYPE** = nodes
- **DOMAIN** = 03_fab_process_equipment
- **CURRENT_NATIVE_OPERATION** = UNDECIDED（没有已填写的人类原生决定）
- **CURRENT_STATUS** = REVIEW
- **WHY_IN_HUMAN_PACKET** = R01_A_B_DISAGREEMENT；R02；R04；R05；R13；REVIEWER_UNRESOLVED_HUMAN_REQUIRED
- **RISK_RULES** = R01 A/B实质分歧；R02 低或必要UNKNOWN置信度；R04 实质命题歧义；R05 身份冲突；R13 本体/类型映射问题
- **MANDATORY_TRIGGER** = R01_A_B_DISAGREEMENT；R02；R04；R05；R13；REVIEWER_UNRESOLVED_HUMAN_REQUIRED
- **SAMPLE_STATUS** = NOT_SAMPLED
- **SAMPLED_FOR_QUALITY_CONTROL** = false

- **SOURCE_ID / SOURCE_NAME** = SC-PHYS-C5B6DC633E156218 / SRC_AC29CFEE56F74F5B / Testimony of the Semiconductor Industry Association before the Senate Committee on Environment & Public Works (March 4, 2026)
Source provenance：Semiconductor Industry Association (SIA)；publication=2026-03-04；edition=；as_of=2026-03-04；source SHA256=`c5b6dc633e156218eb950f2dee88f43fbdcc4fc1744a5924f12b977f5cb7df71`。

**CANDIDATE_SUMMARY**

- Node 类型：Product
- 名称：Semiconductor Cleanroom
- 边界说明：设施/环境系统在 Product/Equipment/Technology 中如何归类需审。

**AI REVIEW A**

- recommendation：HUMAN_REQUIRED；native_decision：DEFER
- proposed operation / canonical target：DEFER；范围/说明: IDENTITY_RECOMMENDATION_ONLY; Semiconductor Cleanroom / Product; no canonical mutation
- confidence：LOW
- reason：洁净室证据是环境设施与控制系统，Product/Equipment/Technology 的 canonical 类型边界未被确定，需先裁定设施表示。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-3AC8C4181A8977F9
- 必要置信度缺口：entity_resolution_clarity=LOW；outcome_completeness=LOW

**AI REVIEW B**

- recommendation：HUMAN_REQUIRED；native_decision：DEFER
- proposed operation / canonical target：DEFER；范围/说明: IDENTITY_ONLY; 03_fab_process_equipment; Semiconductor Cleanroom; Product
- confidence：UNKNOWN
- reason：证据定义严格温湿度/空气纯度环境及系统，尚不足确定Cleanroom是Product、Equipment还是设施概念；类型映射需裁定。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-3AC8C4181A8977F9
- 必要置信度缺口：entity_resolution_clarity=UNKNOWN；rubric_applicability_clarity=UNKNOWN

**A/B RECONCILIATION**

- frozen status：A_B_DISAGREEMENT
- **DISAGREEMENT_TYPE** = 风险判定分歧 R02；风险判定分歧 R04；风险判定分歧 R05；必要置信度判定分歧
- **NATIVE_OPERATION_CONFLICT** = false
- R02 低或必要UNKNOWN置信度：A=TRUE；B=UNKNOWN。A依据：按 LOW > UNKNOWN > MEDIUM > HIGH 聚合，本条为 LOW。 B依据：九维按LOW > 必要UNKNOWN > MEDIUM > HIGH聚合为UNKNOWN。
- R04 实质命题歧义：A=TRUE；B=FALSE。A依据：（具体证据与边界见本项该审查者 reason） B依据：在明确范围下未见两个会改变本次推荐的证据解释；（具体证据与边界见本项该审查者 reason）
- R05 身份冲突：A=FALSE；B=UNKNOWN。A依据：完整 327 节点及 760 别名目录中，未发现本建议产生的身份冲突；明确共享核心者复用。 B依据：对象或关系端点的必要类型尚未统一：（具体证据与边界见本项该审查者 reason）
- 聚合置信度：A=LOW；B=UNKNOWN

**EVIDENCE SUMMARY**

- Supporting facts：下列有来源的节选支持本项讨论的对象/命题；支持范围及未解决条件已在上方 A/B reason 中逐项说明。
- SC-EV-3AC8C4181A8977F9 / SC-PHYS-C5B6DC633E156218 / PDF p.7 / III.B / Technical clean-environment descriptions only / printed p.7；excerpt SHA256=`8b189360baacb8fb0254999e55435d8384dca456f2b973ade76c8ea768c6602b`。
  > The highly controlled systems in a fab include enclosed processes, automation, and chemical delivery systems. The entire process is conducted in a tightly controlled clean room environment, where there are specific controls on temperature, humidity, and air purity.
- Conflicting evidence / unresolved scope：上述 A/B 理由和差异列出已记录的冲突或缺口；未补造反证，也未因省略原文而解除冻结风险。

- **SYSTEM_RECOMMENDED_DECISION** = DEFER
推荐理由（非人工裁决）：双方均建议暂缓；风险标签或置信度差异没有补齐身份/类型/证据缺口。优先保留候选等待人工澄清，不强制选择新的目标、关系类型或对象边界。

HUMAN_USER_DECISION = [PENDING]

OPTIONS:

- [ ] CREATE
- [ ] REUSE <NODE_ID>
- [ ] DEFER
- [ ] REJECT

---

<a id="sc-cn-0093"></a>
### 054 · SC-CN-0093 · Process Platform Validation

- **ITEM_NUMBER** = 54
- **ITEM_ID** = SC-CN-0093
- **OBJECT_TYPE** = nodes
- **DOMAIN** = 08_assembly_packaging
- **CURRENT_NATIVE_OPERATION** = UNDECIDED（没有已填写的人类原生决定）
- **CURRENT_STATUS** = REVIEW
- **WHY_IN_HUMAN_PACKET** = R01_A_B_DISAGREEMENT；R02；R04；R13；REVIEWER_UNRESOLVED_HUMAN_REQUIRED
- **RISK_RULES** = R01 A/B实质分歧；R02 低或必要UNKNOWN置信度；R04 实质命题歧义；R13 本体/类型映射问题
- **MANDATORY_TRIGGER** = R01_A_B_DISAGREEMENT；R02；R04；R13；REVIEWER_UNRESOLVED_HUMAN_REQUIRED
- **SAMPLE_STATUS** = NOT_SAMPLED
- **SAMPLED_FOR_QUALITY_CONTROL** = false

- **SOURCE_ID / SOURCE_NAME** = SC-PHYS-792E7A66390A5C02 / SRC_1EC7288A377A3B0B / How Silicon Die Become Chip Packages
Source provenance：Intel；publication=2025-02-19；edition=；as_of=2025-02-19；source SHA256=`792e7a66390a5c02a43280077fb1e586a3e46f4abf215608dc831ce5ab665db4`。

**CANDIDATE_SUMMARY**

- Node 类型：Technology
- 名称：Process Platform Validation
- 边界说明：Intel具体测试阶段名；不推广为所有厂商行业标准。

**AI REVIEW A**

- recommendation：HUMAN_REQUIRED；native_decision：DEFER
- proposed operation / canonical target：DEFER；范围/说明: IDENTITY_RECOMMENDATION_ONLY; Process Platform Validation / Technology; no canonical mutation
- confidence：LOW
- reason：PPV 仅被 Intel 特定流程命名且解释为终端使用模拟测试；通用 Process Platform Validation 会扩大厂商范围，需限定身份。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-DB9B42CE1D9D064D
- 必要置信度缺口：entity_resolution_clarity=LOW；outcome_completeness=LOW

**AI REVIEW B**

- recommendation：ACCEPT_WITH_REVIEW_NOTE；native_decision：CREATE
- proposed operation / canonical target：CREATE；范围/说明: IDENTITY_ONLY; 08_assembly_packaging; Process Platform Validation; Technology
- confidence：MEDIUM
- reason：Step 6章节明确Process Platform Validation且PPV模拟终端使用/操作系统；仅Intel该流程的技术步骤，不推广行业标准。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-DB9B42CE1D9D064D

**A/B RECONCILIATION**

- frozen status：A_B_DISAGREEMENT
- **DISAGREEMENT_TYPE** = DEFER vs CREATE；ACCEPT/NOTE vs HUMAN_REQUIRED；风险判定分歧 R02；风险判定分歧 R04；风险判定分歧 R13；必要置信度判定分歧
- **NATIVE_OPERATION_CONFLICT** = true
- 原生操作：A=DEFER；B=CREATE
- 推荐路由：A=HUMAN_REQUIRED；B=ACCEPT_WITH_REVIEW_NOTE
- R02 低或必要UNKNOWN置信度：A=TRUE；B=FALSE。A依据：按 LOW > UNKNOWN > MEDIUM > HIGH 聚合，本条为 LOW。 B依据：九维按LOW > 必要UNKNOWN > MEDIUM > HIGH聚合为MEDIUM。
- R04 实质命题歧义：A=TRUE；B=FALSE。A依据：（具体证据与边界见本项该审查者 reason） B依据：在明确范围下未见两个会改变本次推荐的证据解释；（具体证据与边界见本项该审查者 reason）
- R13 本体/类型映射问题：A=TRUE；B=FALSE。A依据：（具体证据与边界见本项该审查者 reason） B依据：推荐使用现有对象类型及原生允许操作，不新增本体关系或隐式类型强转。
- 聚合置信度：A=LOW；B=MEDIUM

**EVIDENCE SUMMARY**

- Supporting facts：下列有来源的节选支持本项讨论的对象/命题；支持范围及未解决条件已在上方 A/B reason 中逐项说明。
- SC-EV-DB9B42CE1D9D064D / SC-PHYS-792E7A66390A5C02 / PDF p.8 / Step 6: Process Platform Validation / printed p.NOT_KNOWN_OR_UNNUMBERED；excerpt SHA256=`2ff22556e9fb65ea44dc5f94a376ce7545f1b847d483b9700dc311ba523d0869`。
  > PPV mimics end-customer conditions by running simulated tests across usage models and operating systems.
- Conflicting evidence / unresolved scope：上述 A/B 理由和差异列出已记录的冲突或缺口；未补造反证，也未因省略原文而解除冻结风险。

- **SYSTEM_RECOMMENDED_DECISION** = DEFER
推荐理由（非人工裁决）：优先暂缓：B 只在 Intel 流程范围内接受，A 指出原规范名称未体现厂商限定。不能把解释性 scope 注记视作已经批准的新 canonical 边界；先请人工确认限定方式。

HUMAN_USER_DECISION = [PENDING]

OPTIONS:

- [ ] CREATE
- [ ] REUSE <NODE_ID>
- [ ] DEFER
- [ ] REJECT

---

<a id="sc-cn-0095"></a>
### 055 · SC-CN-0095 · Gate-All-Around Transistor

- **ITEM_NUMBER** = 55
- **ITEM_ID** = SC-CN-0095
- **OBJECT_TYPE** = nodes
- **DOMAIN** = 04_device_scaling_memory
- **CURRENT_NATIVE_OPERATION** = CREATE NODE_7171CADEA1A2144D
- **CURRENT_STATUS** = CREATE
- **WHY_IN_HUMAN_PACKET** = R01_A_B_DISAGREEMENT；R07；REVIEWER_UNRESOLVED_HUMAN_REQUIRED
- **RISK_RULES** = R01 A/B实质分歧；R07 新增高影响Node
- **MANDATORY_TRIGGER** = R01_A_B_DISAGREEMENT；R07；REVIEWER_UNRESOLVED_HUMAN_REQUIRED
- **SAMPLE_STATUS** = NOT_SAMPLED
- **SAMPLED_FOR_QUALITY_CONTROL** = false

- **SOURCE_ID / SOURCE_NAME** = SC-PHYS-49A1D3B42E458985 / SRC_96EC545507C25F9F / 2024 IRDS — More Moore
Source provenance：IEEE International Roadmap for Devices and Systems (IRDS)；publication=；edition=2024；as_of=2024；source SHA256=`49a1d3b42e45898555490e602170876e22d1ccf8d7c17711e436d8db36322fa6`。

**CANDIDATE_SUMMARY**

- Node 类型：Technology
- 名称：Gate-All-Around Transistor
- 已有身份：NODE_7171CADEA1A2144D
- 边界说明：环绕栅器件结构族；nanosheet为实现，不自动互设别名。
- Planned native target：NODE_7171CADEA1A2144D → SC-CN-0095 / Gate-All-Around Transistor / Technology；这是候选映射，不是已存在或获批准的目录对象。

**AI REVIEW A**

- recommendation：HUMAN_REQUIRED；native_decision：CREATE
- proposed operation / canonical target：CREATE；范围/说明: IDENTITY_RECOMMENDATION_ONLY; Gate-All-Around Transistor / Technology; no canonical mutation
- confidence：HIGH
- reason：两段支持 gate-all-around 为器件架构族、nanosheet 为实现，不与二者设同义；连接路线图演进关系的关键技术锚点。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-35EF72818E4D715F, SC-EV-19830FDE957518FD

**AI REVIEW B**

- recommendation：ACCEPT；native_decision：CREATE
- proposed operation / canonical target：CREATE；范围/说明: IDENTITY_ONLY; 04_device_scaling_memory; Gate-All-Around Transistor; Technology
- confidence：HIGH
- reason：gate-all-around器件与GAA结构两段对应，Technology粒度足够；nanosheet仅实现示例，非完整同义名。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-35EF72818E4D715F, SC-EV-19830FDE957518FD

**A/B RECONCILIATION**

- frozen status：A_B_DISAGREEMENT
- **DISAGREEMENT_TYPE** = ACCEPT/NOTE vs HUMAN_REQUIRED；风险判定分歧 R07
- **NATIVE_OPERATION_CONFLICT** = false
- 推荐路由：A=HUMAN_REQUIRED；B=ACCEPT
- R07 新增高影响Node：A=TRUE；B=FALSE。A依据：（具体证据与边界见本项该审查者 reason） B依据：仅局部有界新对象，无本批关键分类锚点、既有父层变更或View/Impact关键依赖；（具体证据与边界见本项该审查者 reason）

**EVIDENCE SUMMARY**

- Supporting facts：下列有来源的节选支持本项讨论的对象/命题；支持范围及未解决条件已在上方 A/B reason 中逐项说明。
- SC-EV-19830FDE957518FD / SC-PHYS-49A1D3B42E458985 / PDF p.14 / 4.2 Performance Boosters / printed p.9；excerpt SHA256=`1100f9816944d063c22c62b8752fecc2315c33c30d4dcec9cc01ed9a4812701b`。
  > FinFET has remained as the key device architecture that could sustain scaling until 2025.
- SC-EV-35EF72818E4D715F / SC-PHYS-49A1D3B42E458985 / PDF p.7 / 1.1 Current State of Technology / printed p.2；excerpt SHA256=`9185d017f342bb7db4065c57e4cae150ccd5de86796f92bb25b92765ecbb69dc`。
  > we have seen many critical enablers for the continuous enhancement of transistor on top of geometric scaling, such as strained silicon, high-h metal gate, raised source drain, multi-gate transistor such as finFET, and now evolving to gate-all-around devices.
- Conflicting evidence / unresolved scope：上述 A/B 理由和差异列出已记录的冲突或缺口；未补造反证，也未因省略原文而解除冻结风险。

- **SYSTEM_RECOMMENDED_DECISION** = CREATE
推荐理由（非人工裁决）：双方均支持同一个 CREATE 提议，分歧在是否构成结构性高影响，而非创建对象、类型或证据支持。系统建议保留共同 CREATE 方向供人工确认，并完整保留较严格的 R07 与 mandatory 路由；没有替人工裁定该风险分歧。

HUMAN_USER_DECISION = [PENDING]

OPTIONS:

- [ ] CREATE
- [ ] REUSE <NODE_ID>
- [ ] DEFER
- [ ] REJECT

---

<a id="sc-cn-0096"></a>
### 056 · SC-CN-0096 · Complementary FET

- **ITEM_NUMBER** = 56
- **ITEM_ID** = SC-CN-0096
- **OBJECT_TYPE** = nodes
- **DOMAIN** = 04_device_scaling_memory
- **CURRENT_NATIVE_OPERATION** = UNDECIDED（没有已填写的人类原生决定）
- **CURRENT_STATUS** = REVIEW
- **WHY_IN_HUMAN_PACKET** = R01_A_B_DISAGREEMENT；R02；R03；R04；R05；REVIEWER_UNRESOLVED_HUMAN_REQUIRED
- **RISK_RULES** = R01 A/B实质分歧；R02 低或必要UNKNOWN置信度；R03 证据缺口；R04 实质命题歧义；R05 身份冲突
- **MANDATORY_TRIGGER** = R01_A_B_DISAGREEMENT；R02；R03；R04；R05；REVIEWER_UNRESOLVED_HUMAN_REQUIRED
- **SAMPLE_STATUS** = NOT_SAMPLED
- **SAMPLED_FOR_QUALITY_CONTROL** = false

- **SOURCE_ID / SOURCE_NAME** = SC-PHYS-49A1D3B42E458985 / SRC_96EC545507C25F9F / 2024 IRDS — More Moore
Source provenance：IEEE International Roadmap for Devices and Systems (IRDS)；publication=；edition=2024；as_of=2024；source SHA256=`49a1d3b42e45898555490e602170876e22d1ccf8d7c17711e436d8db36322fa6`。

**CANDIDATE_SUMMARY**

- Node 类型：Technology
- 名称：Complementary FET
- 边界说明：原文此定位仅给CFET缩写及NMOS/PMOS堆叠；全称与独立粒度待审，2031属路线图。

**AI REVIEW A**

- recommendation：HUMAN_REQUIRED；native_decision：DEFER
- proposed operation / canonical target：DEFER；范围/说明: IDENTITY_RECOMMENDATION_ONLY; Complementary FET / Technology; no canonical mutation
- confidence：LOW
- reason：IRDS 仅写 CFET 与 NMOS/PMOS 纵向堆叠，未展开 Complementary FET；结构明确不等于全称身份已证实，2031 仅为预期。
- evidence assessment：INSUFFICIENT；Evidence IDs：SC-EV-5DB96B503421ADF4
- 必要置信度缺口：entity_resolution_clarity=LOW；evidence_directness=LOW；unit_scope_completeness=UNKNOWN

**AI REVIEW B**

- recommendation：HUMAN_REQUIRED；native_decision：DEFER
- proposed operation / canonical target：DEFER；范围/说明: IDENTITY_ONLY; 04_device_scaling_memory; Complementary FET; Technology
- confidence：LOW
- reason：CFET的NMOS/PMOS堆叠和2031预测清楚，但摘录未展开Complementary FET规范名；不能凭缩写完成唯一映射。
- evidence assessment：INSUFFICIENT；Evidence IDs：SC-EV-5DB96B503421ADF4
- 必要置信度缺口：entity_resolution_clarity=UNKNOWN；evidence_directness=LOW；unit_scope_completeness=LOW

**A/B RECONCILIATION**

- frozen status：A_B_DISAGREEMENT
- **DISAGREEMENT_TYPE** = 风险判定分歧 R05
- **NATIVE_OPERATION_CONFLICT** = false
- R05 身份冲突：A=FALSE；B=UNKNOWN。A依据：完整 327 节点及 760 别名目录中，未发现本建议产生的身份冲突；明确共享核心者复用。 B依据：规范身份或候选所有者定义未完备：（具体证据与边界见本项该审查者 reason）

**EVIDENCE SUMMARY**

- Supporting facts：下列有来源的节选支持本项讨论的对象/命题；支持范围及未解决条件已在上方 A/B reason 中逐项说明。
- SC-EV-5DB96B503421ADF4 / SC-PHYS-49A1D3B42E458985 / PDF p.13 / 4.1 Logic Scaling / printed p.8；excerpt SHA256=`453673c2ec42f990646a1741519fe09b68d2d3e7aa96c47e497f6edb2a4303a6`。
  > Early generation of 3D VLSI is expected to start with CFET in 2031 where NMOS and PMOS are placed on top of each other.
- Conflicting evidence / unresolved scope：上述 A/B 理由和差异列出已记录的冲突或缺口；未补造反证，也未因省略原文而解除冻结风险。

- **SYSTEM_RECOMMENDED_DECISION** = DEFER
推荐理由（非人工裁决）：双方均建议暂缓；风险标签或置信度差异没有补齐身份/类型/证据缺口。优先保留候选等待人工澄清，不强制选择新的目标、关系类型或对象边界。

HUMAN_USER_DECISION = [PENDING]

OPTIONS:

- [ ] CREATE
- [ ] REUSE <NODE_ID>
- [ ] DEFER
- [ ] REJECT

---

<a id="sc-cn-0108"></a>
### 057 · SC-CN-0108 · High-NA EUV Lithography

- **ITEM_NUMBER** = 57
- **ITEM_ID** = SC-CN-0108
- **OBJECT_TYPE** = nodes
- **DOMAIN** = 05_lithography_patterning
- **CURRENT_NATIVE_OPERATION** = UNDECIDED（没有已填写的人类原生决定）
- **CURRENT_STATUS** = REVIEW
- **WHY_IN_HUMAN_PACKET** = R01_A_B_DISAGREEMENT；R07；REVIEWER_UNRESOLVED_HUMAN_REQUIRED
- **RISK_RULES** = R01 A/B实质分歧；R07 新增高影响Node
- **MANDATORY_TRIGGER** = R01_A_B_DISAGREEMENT；R07；REVIEWER_UNRESOLVED_HUMAN_REQUIRED
- **SAMPLE_STATUS** = NOT_SAMPLED
- **SAMPLED_FOR_QUALITY_CONTROL** = false

- **SOURCE_ID / SOURCE_NAME** = SC-PHYS-318D85A127B5B6DF / SRC_FFD94DB31A0E9C0A / 2025 IRDS — Lithography and Patterning
Source provenance：IEEE International Roadmap for Devices and Systems (IRDS)；publication=；edition=2025；as_of=2025；source SHA256=`318d85a127b5b6dfa7b3c1330ae20b18d63660a1fa8c8bdfdd7b478844e145ed`。

**CANDIDATE_SUMMARY**

- Node 类型：Technology
- 名称：High-NA EUV Lithography
- 边界说明：高NA光刻分支与EUV父层级需审；性能和采用年份维持路线图限定。

**AI REVIEW A**

- recommendation：HUMAN_REQUIRED；native_decision：CREATE
- proposed operation / canonical target：CREATE；范围/说明: IDENTITY_RECOMMENDATION_ONLY; High-NA EUV Lithography / Technology; no canonical mutation
- confidence：HIGH
- reason：0.55NA EUV 设备交付及 high-NA 分支明确，支持专门技术身份；2027 投产仍是预测，不能覆盖一般 EUV 或提升为既成状态。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-02BE8A33B67A123F, SC-EV-6931BFF731D8EB70

**AI REVIEW B**

- recommendation：ACCEPT_WITH_REVIEW_NOTE；native_decision：CREATE
- proposed operation / canonical target：CREATE；范围/说明: IDENTITY_ONLY; 05_lithography_patterning; High-NA EUV Lithography; Technology
- confidence：MEDIUM
- reason：high NA EUV分支及0.55NA工具证据足以限定技术代际，不能等同全部EUV；2027为预测且本节点不声称投产。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-02BE8A33B67A123F, SC-EV-6931BFF731D8EB70

**A/B RECONCILIATION**

- frozen status：A_B_DISAGREEMENT
- **DISAGREEMENT_TYPE** = ACCEPT/NOTE vs HUMAN_REQUIRED；风险判定分歧 R07
- **NATIVE_OPERATION_CONFLICT** = false
- 推荐路由：A=HUMAN_REQUIRED；B=ACCEPT_WITH_REVIEW_NOTE
- R07 新增高影响Node：A=TRUE；B=FALSE。A依据：（具体证据与边界见本项该审查者 reason） B依据：仅局部有界新对象，无本批关键分类锚点、既有父层变更或View/Impact关键依赖；（具体证据与边界见本项该审查者 reason）

**EVIDENCE SUMMARY**

- Supporting facts：下列有来源的节选支持本项讨论的对象/命题；支持范围及未解决条件已在上方 A/B reason 中逐项说明。
- SC-EV-02BE8A33B67A123F / SC-PHYS-318D85A127B5B6DF / PDF p.6 / Executive Summary / high-NA EUV / printed p.1；excerpt SHA256=`ad8abb888d23d75d728d4fed3320f6b647ba9a5ab255d2697c8073f2a8ac0248`。
  > The availability of both multiple patterning and high NA EUV enables high resolution patterning that already can meet resolution requirements through 2029.
- SC-EV-6931BFF731D8EB70 / SC-PHYS-318D85A127B5B6DF / PDF p.6 / Executive Summary / high-NA EUV / printed p.1；excerpt SHA256=`bb45531be695d54a8ecbebbddd925b87bcee72414544a2109989fd496ef66f88`。
  > EUV exposure tools with a numerical aperture (NA) of 0.55 started being delivered to customers at the end of 2023. They are now in use at multiple sites and multiple customers. First production use of such tools is projected for 2027.
- Conflicting evidence / unresolved scope：上述 A/B 理由和差异列出已记录的冲突或缺口；未补造反证，也未因省略原文而解除冻结风险。

- **SYSTEM_RECOMMENDED_DECISION** = CREATE
推荐理由（非人工裁决）：双方均支持同一个 CREATE 提议，分歧在是否构成结构性高影响，而非创建对象、类型或证据支持。系统建议保留共同 CREATE 方向供人工确认，并完整保留较严格的 R07 与 mandatory 路由；没有替人工裁定该风险分歧。

HUMAN_USER_DECISION = [PENDING]

OPTIONS:

- [ ] CREATE
- [ ] REUSE <NODE_ID>
- [ ] DEFER
- [ ] REJECT

---

<a id="sc-cn-0120"></a>
### 058 · SC-CN-0120 · Yield Management

- **ITEM_NUMBER** = 58
- **ITEM_ID** = SC-CN-0120
- **OBJECT_TYPE** = nodes
- **DOMAIN** = 06_metrology_yield_factory
- **CURRENT_NATIVE_OPERATION** = CREATE NODE_EFBD0210FC23869C
- **CURRENT_STATUS** = CREATE
- **WHY_IN_HUMAN_PACKET** = R01_A_B_DISAGREEMENT；R07；REVIEWER_UNRESOLVED_HUMAN_REQUIRED
- **RISK_RULES** = R01 A/B实质分歧；R07 新增高影响Node
- **MANDATORY_TRIGGER** = R01_A_B_DISAGREEMENT；R07；REVIEWER_UNRESOLVED_HUMAN_REQUIRED
- **SAMPLE_STATUS** = NOT_SAMPLED
- **SAMPLED_FOR_QUALITY_CONTROL** = false

- **SOURCE_ID / SOURCE_NAME** = SC-PHYS-AA294FCF8FEDE75B / SRC_08CC764E9C0DCB61 / 2025 IRDS — Yield Enhancement and Advanced Manufacturing & Contamination Control
Source provenance：IEEE International Roadmap for Devices and Systems (IRDS)；publication=；edition=2025；as_of=2025；source SHA256=`aa294fcf8fede75be6e2c23c6ec75a6f3504538dceb87eb51edda0134526b34b`。

**CANDIDATE_SUMMARY**

- Node 类型：Technology
- 名称：Yield Management
- 已有身份：NODE_EFBD0210FC23869C
- 边界说明：缺陷识别/反馈/相关分析技术体系，yield百分比不是Node。
- Planned native target：NODE_EFBD0210FC23869C → SC-CN-0120 / Yield Management / Technology；这是候选映射，不是已存在或获批准的目录对象。

**AI REVIEW A**

- recommendation：ACCEPT；native_decision：CREATE
- proposed operation / canonical target：CREATE；范围/说明: IDENTITY_RECOMMENDATION_ONLY; Yield Management / Technology; no canonical mutation
- confidence：HIGH
- reason：yield management 有在线检测、反馈和良率失效关联方法链，支持技术体系，非良率百分数节点。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-6C7601C6EFF1962D, SC-EV-ACA3759FAA03DC4E

**AI REVIEW B**

- recommendation：HUMAN_REQUIRED；native_decision：CREATE
- proposed operation / canonical target：CREATE；范围/说明: IDENTITY_ONLY; 06_metrology_yield_factory; Yield Management; Technology
- confidence：HIGH
- reason：良率管理通过inline inspection反馈并关联失效，SC-RL-0050及SC-BV-0006依赖该控制框架；不是yield百分比属性。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-6C7601C6EFF1962D, SC-EV-ACA3759FAA03DC4E

**A/B RECONCILIATION**

- frozen status：A_B_DISAGREEMENT
- **DISAGREEMENT_TYPE** = ACCEPT/NOTE vs HUMAN_REQUIRED；风险判定分歧 R07
- **NATIVE_OPERATION_CONFLICT** = false
- 推荐路由：A=ACCEPT；B=HUMAN_REQUIRED
- R07 新增高影响Node：A=FALSE；B=TRUE。A依据：本条为普通局部身份建议，未建立跨域共享/关键层级或 View/Impact 锚点；非因新建自动判高影响。 B依据：有具体关键结构/平台依赖：（具体证据与边界见本项该审查者 reason）

**EVIDENCE SUMMARY**

- Supporting facts：下列有来源的节选支持本项讨论的对象/命题；支持范围及未解决条件已在上方 A/B reason 中逐项说明。
- SC-EV-6C7601C6EFF1962D / SC-PHYS-AA294FCF8FEDE75B / PDF p.28 / Characterization, Inspection and Analysis / printed p.23；excerpt SHA256=`3b678cebf3c40bfae6c9d3550275d484867c743db9d0b520382011687103deba`。
  > Traditional yield management focuses on adequate inline inspection capabilities to detect and control all relevant defect types to set up short feedback loops as well as enable correlation to yield and test fails.
- SC-EV-ACA3759FAA03DC4E / SC-PHYS-AA294FCF8FEDE75B / PDF p.6 / 1 Introduction / printed p.1；excerpt SHA256=`a9094fe506388f7963abe5e1b6b8647c8fbd843a3a2f8cd39bd63d864672fe70`。
  > During the manufacturing of integrated circuits yield loss is caused, for example, by defects, faults, process variations, and design.
- Conflicting evidence / unresolved scope：上述 A/B 理由和差异列出已记录的冲突或缺口；未补造反证，也未因省略原文而解除冻结风险。

- **SYSTEM_RECOMMENDED_DECISION** = CREATE
推荐理由（非人工裁决）：双方均支持同一个 CREATE 提议，分歧在是否构成结构性高影响，而非创建对象、类型或证据支持。系统建议保留共同 CREATE 方向供人工确认，并完整保留较严格的 R07 与 mandatory 路由；没有替人工裁定该风险分歧。

HUMAN_USER_DECISION = [PENDING]

OPTIONS:

- [ ] CREATE
- [ ] REUSE <NODE_ID>
- [ ] DEFER
- [ ] REJECT

---

<a id="sc-cn-0121"></a>
### 059 · SC-CN-0121 · Substrate Environment Contamination Control

- **ITEM_NUMBER** = 59
- **ITEM_ID** = SC-CN-0121
- **OBJECT_TYPE** = nodes
- **DOMAIN** = 06_metrology_yield_factory
- **CURRENT_NATIVE_OPERATION** = UNDECIDED（没有已填写的人类原生决定）
- **CURRENT_STATUS** = REVIEW
- **WHY_IN_HUMAN_PACKET** = R01_A_B_DISAGREEMENT；R02；R04；R05；REVIEWER_UNRESOLVED_HUMAN_REQUIRED
- **RISK_RULES** = R01 A/B实质分歧；R02 低或必要UNKNOWN置信度；R04 实质命题歧义；R05 身份冲突
- **MANDATORY_TRIGGER** = R01_A_B_DISAGREEMENT；R02；R04；R05；REVIEWER_UNRESOLVED_HUMAN_REQUIRED
- **SAMPLE_STATUS** = NOT_SAMPLED
- **SAMPLED_FOR_QUALITY_CONTROL** = false

- **SOURCE_ID / SOURCE_NAME** = SC-PHYS-AA294FCF8FEDE75B / SRC_08CC764E9C0DCB61 / 2025 IRDS — Yield Enhancement and Advanced Manufacturing & Contamination Control
Source provenance：IEEE International Roadmap for Devices and Systems (IRDS)；publication=；edition=2025；as_of=2025；source SHA256=`aa294fcf8fede75be6e2c23c6ec75a6f3504538dceb87eb51edda0134526b34b`。

**CANDIDATE_SUMMARY**

- Node 类型：Technology
- 名称：Substrate Environment Contamination Control
- 边界说明：同文另一处写Surface Environment；与泛污染控制对象范围需统一后再创建。

**AI REVIEW A**

- recommendation：HUMAN_REQUIRED；native_decision：DEFER
- proposed operation / canonical target：DEFER；范围/说明: IDENTITY_RECOMMENDATION_ONLY; Substrate Environment Contamination Control / Technology; no canonical mutation
- confidence：LOW
- reason：绑定原文写 Substrate Environment，但候选保留同文 Surface Environment 差异提示，主题范围可能不同；冻结摘录不足统一 SECC 身份。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-33944F5B66F30C99
- 必要置信度缺口：entity_resolution_clarity=LOW；outcome_completeness=LOW

**AI REVIEW B**

- recommendation：HUMAN_REQUIRED；native_decision：DEFER
- proposed operation / canonical target：DEFER；范围/说明: IDENTITY_ONLY; 06_metrology_yield_factory; Substrate Environment Contamination Control; Technology
- confidence：HIGH
- reason：Substrate Environment全称虽有直接证据，但冻结材料另有Surface Environment表述；二者范围是否一致影响节点归属，暂缓统一。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-33944F5B66F30C99

**A/B RECONCILIATION**

- frozen status：A_B_DISAGREEMENT
- **DISAGREEMENT_TYPE** = 风险判定分歧 R02；风险判定分歧 R05；必要置信度判定分歧
- **NATIVE_OPERATION_CONFLICT** = false
- R02 低或必要UNKNOWN置信度：A=TRUE；B=FALSE。A依据：按 LOW > UNKNOWN > MEDIUM > HIGH 聚合，本条为 LOW。 B依据：九维按LOW > 必要UNKNOWN > MEDIUM > HIGH聚合为HIGH。
- R05 身份冲突：A=FALSE；B=TRUE。A依据：完整 327 节点及 760 别名目录中，未发现本建议产生的身份冲突；明确共享核心者复用。 B依据：不同身份或范围解释尚未收敛：（具体证据与边界见本项该审查者 reason）
- 聚合置信度：A=LOW；B=HIGH

**EVIDENCE SUMMARY**

- Supporting facts：下列有来源的节选支持本项讨论的对象/命题；支持范围及未解决条件已在上方 A/B reason 中逐项说明。
- SC-EV-33944F5B66F30C99 / SC-PHYS-AA294FCF8FEDE75B / PDF p.7 / 1 Introduction / focus topics / printed p.2；excerpt SHA256=`5cb56877909616c6ceb1d8f4e3dcb89dda3912d1252683b2668e313ad2297b25`。
  > The YE chapter has two focus topics: “Substrate Environment Contamination Control” (SECC) and “Characterization, Inspection and Analysis (CIA)”.
- Conflicting evidence / unresolved scope：上述 A/B 理由和差异列出已记录的冲突或缺口；未补造反证，也未因省略原文而解除冻结风险。

- **SYSTEM_RECOMMENDED_DECISION** = DEFER
推荐理由（非人工裁决）：双方均建议暂缓；风险标签或置信度差异没有补齐身份/类型/证据缺口。优先保留候选等待人工澄清，不强制选择新的目标、关系类型或对象边界。

HUMAN_USER_DECISION = [PENDING]

OPTIONS:

- [ ] CREATE
- [ ] REUSE <NODE_ID>
- [ ] DEFER
- [ ] REJECT

---

<a id="sc-cn-0122"></a>
### 060 · SC-CN-0122 · Airborne Molecular Contamination

- **ITEM_NUMBER** = 60
- **ITEM_ID** = SC-CN-0122
- **OBJECT_TYPE** = nodes
- **DOMAIN** = 06_metrology_yield_factory
- **CURRENT_NATIVE_OPERATION** = UNDECIDED（没有已填写的人类原生决定）
- **CURRENT_STATUS** = REVIEW
- **WHY_IN_HUMAN_PACKET** = R01_A_B_DISAGREEMENT；R02；R04；R05；R13；REVIEWER_UNRESOLVED_HUMAN_REQUIRED
- **RISK_RULES** = R01 A/B实质分歧；R02 低或必要UNKNOWN置信度；R04 实质命题歧义；R05 身份冲突；R13 本体/类型映射问题
- **MANDATORY_TRIGGER** = R01_A_B_DISAGREEMENT；R02；R04；R05；R13；REVIEWER_UNRESOLVED_HUMAN_REQUIRED
- **SAMPLE_STATUS** = NOT_SAMPLED
- **SAMPLED_FOR_QUALITY_CONTROL** = false

- **SOURCE_ID / SOURCE_NAME** = SC-PHYS-AA294FCF8FEDE75B / SRC_08CC764E9C0DCB61 / 2025 IRDS — Yield Enhancement and Advanced Manufacturing & Contamination Control
Source provenance：IEEE International Roadmap for Devices and Systems (IRDS)；publication=；edition=2025；as_of=2025；source SHA256=`aa294fcf8fede75be6e2c23c6ec75a6f3504538dceb87eb51edda0134526b34b`。

**CANDIDATE_SUMMARY**

- Node 类型：ResearchQuestion
- 名称：Airborne Molecular Contamination
- 边界说明：污染物类别、研究问题或环境属性的类型需要治理；不据此创造Pollutant类型。

**AI REVIEW A**

- recommendation：HUMAN_REQUIRED；native_decision：DEFER
- proposed operation / canonical target：DEFER；范围/说明: IDENTITY_RECOMMENDATION_ONLY; Airborne Molecular Contamination / ResearchQuestion; no canonical mutation
- confidence：LOW
- reason：AMC 原文是空气分子污染现象及来源，不是直接提出的 ResearchQuestion；现有类型体系如何承载污染现象需裁决。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-CFE0706D8027F87E
- 必要置信度缺口：entity_resolution_clarity=LOW；outcome_completeness=LOW

**AI REVIEW B**

- recommendation：HUMAN_REQUIRED；native_decision：REJECT
- proposed operation / canonical target：REJECT；范围/说明: IDENTITY_ONLY; 06_metrology_yield_factory; Airborne Molecular Contamination; ResearchQuestion
- confidence：UNKNOWN
- reason：AMC摘录定义污染类别及来源，不是问句或ResearchQuestion；拒绝该类型表达，污染对象如何纳入既有本体仍须人工。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-CFE0706D8027F87E
- 必要置信度缺口：entity_resolution_clarity=UNKNOWN；rubric_applicability_clarity=UNKNOWN

**A/B RECONCILIATION**

- frozen status：A_B_DISAGREEMENT
- **DISAGREEMENT_TYPE** = DEFER vs REJECT；风险判定分歧 R02；风险判定分歧 R04；风险判定分歧 R05；必要置信度判定分歧
- **NATIVE_OPERATION_CONFLICT** = true
- 原生操作：A=DEFER；B=REJECT
- R02 低或必要UNKNOWN置信度：A=TRUE；B=UNKNOWN。A依据：按 LOW > UNKNOWN > MEDIUM > HIGH 聚合，本条为 LOW。 B依据：九维按LOW > 必要UNKNOWN > MEDIUM > HIGH聚合为UNKNOWN。
- R04 实质命题歧义：A=TRUE；B=FALSE。A依据：（具体证据与边界见本项该审查者 reason） B依据：在明确范围下未见两个会改变本次推荐的证据解释；（具体证据与边界见本项该审查者 reason）
- R05 身份冲突：A=FALSE；B=UNKNOWN。A依据：完整 327 节点及 760 别名目录中，未发现本建议产生的身份冲突；明确共享核心者复用。 B依据：对象或关系端点的必要类型尚未统一：（具体证据与边界见本项该审查者 reason）
- 聚合置信度：A=LOW；B=UNKNOWN

**EVIDENCE SUMMARY**

- Supporting facts：下列有来源的节选支持本项讨论的对象/命题；支持范围及未解决条件已在上方 A/B reason 中逐项说明。
- SC-EV-CFE0706D8027F87E / SC-PHYS-AA294FCF8FEDE75B / PDF p.31 / Surface Environment Control / AMC / printed p.26；excerpt SHA256=`59c02bbf94cb4593118027bd89af5a81f8df85e3a43322f5cc313eb6c6196574`。
  > Airborne molecular contamination (AMC)— Fugitive emissions from chemicals used in wafer processing and inadequate exhaust are the main sources of AMC.
- Conflicting evidence / unresolved scope：上述 A/B 理由和差异列出已记录的冲突或缺口；未补造反证，也未因省略原文而解除冻结风险。

- **SYSTEM_RECOMMENDED_DECISION** = REJECT
推荐理由（非人工裁决）：优先建议拒绝当前 ResearchQuestion 类型表达：双方均认为证据定义的是污染类别/现象，并非研究问题，B 的拒绝直接对应这一类型不匹配。保留原证据，是否另建适当类型仍待人工；本文件不选择替代本体。

HUMAN_USER_DECISION = [PENDING]

OPTIONS:

- [ ] CREATE
- [ ] REUSE <NODE_ID>
- [ ] DEFER
- [ ] REJECT

---

<a id="sc-cn-0124"></a>
### 061 · SC-CN-0124 · Automated Material Handling System

- **ITEM_NUMBER** = 61
- **ITEM_ID** = SC-CN-0124
- **OBJECT_TYPE** = nodes
- **DOMAIN** = 06_metrology_yield_factory
- **CURRENT_NATIVE_OPERATION** = UNDECIDED（没有已填写的人类原生决定）
- **CURRENT_STATUS** = REVIEW
- **WHY_IN_HUMAN_PACKET** = R01_A_B_DISAGREEMENT；R02；R03；R04；R05；REVIEWER_UNRESOLVED_HUMAN_REQUIRED
- **RISK_RULES** = R01 A/B实质分歧；R02 低或必要UNKNOWN置信度；R03 证据缺口；R04 实质命题歧义；R05 身份冲突
- **MANDATORY_TRIGGER** = R01_A_B_DISAGREEMENT；R02；R03；R04；R05；REVIEWER_UNRESOLVED_HUMAN_REQUIRED
- **SAMPLE_STATUS** = NOT_SAMPLED
- **SAMPLED_FOR_QUALITY_CONTROL** = false

- **SOURCE_ID / SOURCE_NAME** = SC-PHYS-4FA7140313FB3AF8 / SRC_15959FA40D6E85A4 / 2023 IRDS — Factory Integration
Source provenance：IEEE International Roadmap for Devices and Systems (IRDS)；publication=；edition=2023；as_of=2023；source SHA256=`4fa7140313fb3af883127c329599c4d8e6f4b9abfbe0976f4e8102ebe8c2587d`。

**CANDIDATE_SUMMARY**

- Node 类型：Equipment
- 名称：Automated Material Handling System
- 边界说明：此定位为AMHS需求而非全称定义；需核全称及系统类型后接纳。

**AI REVIEW A**

- recommendation：HUMAN_REQUIRED；native_decision：DEFER
- proposed operation / canonical target：DEFER；范围/说明: IDENTITY_RECOMMENDATION_ONLY; Automated Material Handling System / Equipment; no canonical mutation
- confidence：LOW
- reason：AMHS 的搬运需求明白，但该摘录未展开 Automated Material Handling System 全称且 Equipment 粒度未定，需补身份依据。
- evidence assessment：INSUFFICIENT；Evidence IDs：SC-EV-60435D5F04954369
- 必要置信度缺口：entity_resolution_clarity=LOW；evidence_directness=LOW；unit_scope_completeness=UNKNOWN

**AI REVIEW B**

- recommendation：HUMAN_REQUIRED；native_decision：DEFER
- proposed operation / canonical target：DEFER；范围/说明: IDENTITY_ONLY; 06_metrology_yield_factory; Automated Material Handling System; Equipment
- confidence：LOW
- reason：AMHS功能需求明确，但冻结摘录和Material Handling标题未展开Automated Material Handling System全称；系统身份需补映射。
- evidence assessment：INSUFFICIENT；Evidence IDs：SC-EV-60435D5F04954369
- 必要置信度缺口：entity_resolution_clarity=UNKNOWN；evidence_directness=LOW；unit_scope_completeness=LOW

**A/B RECONCILIATION**

- frozen status：A_B_DISAGREEMENT
- **DISAGREEMENT_TYPE** = 风险判定分歧 R05
- **NATIVE_OPERATION_CONFLICT** = false
- R05 身份冲突：A=FALSE；B=UNKNOWN。A依据：完整 327 节点及 760 别名目录中，未发现本建议产生的身份冲突；明确共享核心者复用。 B依据：规范身份或候选所有者定义未完备：（具体证据与边界见本项该审查者 reason）

**EVIDENCE SUMMARY**

- Supporting facts：下列有来源的节选支持本项讨论的对象/命题；支持范围及未解决条件已在上方 A/B reason 中逐项说明。
- SC-EV-60435D5F04954369 / SC-PHYS-4FA7140313FB3AF8 / PDF p.27 / 5.4 Material Handling / printed p.21；excerpt SHA256=`c88951455ed96a5adaa7e8bd50efc2b4b46c4eb7a0ee7f787df729b669f69e81`。
  > AMHS must have acceptable return on investment (ROI) and must interface directly with all inline (i.e., used in normal process flow) production and metrology equipment. AMHS must deliver material in a timely fashion to support critical equipment in order to minimize wait time waste.
- Conflicting evidence / unresolved scope：上述 A/B 理由和差异列出已记录的冲突或缺口；未补造反证，也未因省略原文而解除冻结风险。

- **SYSTEM_RECOMMENDED_DECISION** = DEFER
推荐理由（非人工裁决）：双方均建议暂缓；风险标签或置信度差异没有补齐身份/类型/证据缺口。优先保留候选等待人工澄清，不强制选择新的目标、关系类型或对象边界。

HUMAN_USER_DECISION = [PENDING]

OPTIONS:

- [ ] CREATE
- [ ] REUSE <NODE_ID>
- [ ] DEFER
- [ ] REJECT

---

<a id="sc-cn-0128"></a>
### 062 · SC-CN-0128 · More Than Moore

- **ITEM_NUMBER** = 62
- **ITEM_ID** = SC-CN-0128
- **OBJECT_TYPE** = nodes
- **DOMAIN** = 07_more_than_moore
- **CURRENT_NATIVE_OPERATION** = UNDECIDED（没有已填写的人类原生决定）
- **CURRENT_STATUS** = REVIEW
- **WHY_IN_HUMAN_PACKET** = R01_A_B_DISAGREEMENT；R02；R04；R05；R13；REVIEWER_UNRESOLVED_HUMAN_REQUIRED
- **RISK_RULES** = R01 A/B实质分歧；R02 低或必要UNKNOWN置信度；R04 实质命题歧义；R05 身份冲突；R13 本体/类型映射问题
- **MANDATORY_TRIGGER** = R01_A_B_DISAGREEMENT；R02；R04；R05；R13；REVIEWER_UNRESOLVED_HUMAN_REQUIRED
- **SAMPLE_STATUS** = NOT_SAMPLED
- **SAMPLED_FOR_QUALITY_CONTROL** = false

- **SOURCE_ID / SOURCE_NAME** = SC-PHYS-59E90A8C09249A8D / SRC_70049F425584945A / 2022 IRDS — More Than Moore
Source provenance：IEEE International Roadmap for Devices and Systems (IRDS)；publication=；edition=2022；as_of=2022；source SHA256=`59e90a8c09249a8dc75f53f661f4f0eff511b9eb65fbc1a1c70ffb363d8166c8`。

**CANDIDATE_SUMMARY**

- Node 类型：Technology
- 名称：More Than Moore
- 边界说明：技术发展范式/功能多样化分类，不把章节名直接升为Industry。

**AI REVIEW A**

- recommendation：HUMAN_REQUIRED；native_decision：DEFER
- proposed operation / canonical target：DEFER；范围/说明: IDENTITY_RECOMMENDATION_ONLY; More Than Moore / Technology; no canonical mutation
- confidence：LOW
- reason：More than Moore 定义为不必遵循缩放规律的功能增加范式，Technology 单体或 Theme 分类有不同语义，需先确定表达层级。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-89281F8024B7CE43
- 必要置信度缺口：entity_resolution_clarity=LOW；outcome_completeness=LOW

**AI REVIEW B**

- recommendation：HUMAN_REQUIRED；native_decision：DEFER
- proposed operation / canonical target：DEFER；范围/说明: IDENTITY_ONLY; 07_more_than_moore; More Than Moore; Technology
- confidence：UNKNOWN
- reason：More than Moore是功能多样化的发展范式，原文不足把整个范式变成单一Technology；Theme或框架属性的映射需裁定。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-89281F8024B7CE43
- 必要置信度缺口：entity_resolution_clarity=UNKNOWN；rubric_applicability_clarity=UNKNOWN

**A/B RECONCILIATION**

- frozen status：A_B_DISAGREEMENT
- **DISAGREEMENT_TYPE** = 风险判定分歧 R02；风险判定分歧 R04；风险判定分歧 R05；必要置信度判定分歧
- **NATIVE_OPERATION_CONFLICT** = false
- R02 低或必要UNKNOWN置信度：A=TRUE；B=UNKNOWN。A依据：按 LOW > UNKNOWN > MEDIUM > HIGH 聚合，本条为 LOW。 B依据：九维按LOW > 必要UNKNOWN > MEDIUM > HIGH聚合为UNKNOWN。
- R04 实质命题歧义：A=TRUE；B=FALSE。A依据：（具体证据与边界见本项该审查者 reason） B依据：在明确范围下未见两个会改变本次推荐的证据解释；（具体证据与边界见本项该审查者 reason）
- R05 身份冲突：A=FALSE；B=UNKNOWN。A依据：完整 327 节点及 760 别名目录中，未发现本建议产生的身份冲突；明确共享核心者复用。 B依据：对象或关系端点的必要类型尚未统一：（具体证据与边界见本项该审查者 reason）
- 聚合置信度：A=LOW；B=UNKNOWN

**EVIDENCE SUMMARY**

- Supporting facts：下列有来源的节选支持本项讨论的对象/命题；支持范围及未解决条件已在上方 A/B reason 中逐项说明。
- SC-EV-89281F8024B7CE43 / SC-PHYS-59E90A8C09249A8D / PDF p.9 / More than Moore: Functional Diversification / printed p.3；excerpt SHA256=`2020643aac602e92845c5a6b4c3b09ae14c4a9b62785d8e9fdf4dec90e92f8b3`。
  > “More than Moore” refers to the incorporation into devices of functionalities that do not necessarily scale according to Moore's Law, but provide additional value in different ways.
- Conflicting evidence / unresolved scope：上述 A/B 理由和差异列出已记录的冲突或缺口；未补造反证，也未因省略原文而解除冻结风险。

- **SYSTEM_RECOMMENDED_DECISION** = DEFER
推荐理由（非人工裁决）：双方均建议暂缓；风险标签或置信度差异没有补齐身份/类型/证据缺口。优先保留候选等待人工澄清，不强制选择新的目标、关系类型或对象边界。

HUMAN_USER_DECISION = [PENDING]

OPTIONS:

- [ ] CREATE
- [ ] REUSE <NODE_ID>
- [ ] DEFER
- [ ] REJECT

---

<a id="sc-cn-0131"></a>
### 063 · SC-CN-0131 · Microelectromechanical Systems

- **ITEM_NUMBER** = 63
- **ITEM_ID** = SC-CN-0131
- **OBJECT_TYPE** = nodes
- **DOMAIN** = 06_metrology_yield_factory
- **CURRENT_NATIVE_OPERATION** = UNDECIDED（没有已填写的人类原生决定）
- **CURRENT_STATUS** = REVIEW
- **WHY_IN_HUMAN_PACKET** = R01_A_B_DISAGREEMENT；R02；R03；R04；R05；R13；REVIEWER_UNRESOLVED_HUMAN_REQUIRED
- **RISK_RULES** = R01 A/B实质分歧；R02 低或必要UNKNOWN置信度；R03 证据缺口；R04 实质命题歧义；R05 身份冲突；R13 本体/类型映射问题
- **MANDATORY_TRIGGER** = R01_A_B_DISAGREEMENT；R02；R03；R04；R05；R13；REVIEWER_UNRESOLVED_HUMAN_REQUIRED
- **SAMPLE_STATUS** = NOT_SAMPLED
- **SAMPLED_FOR_QUALITY_CONTROL** = false

- **SOURCE_ID / SOURCE_NAME** = SC-PHYS-AA294FCF8FEDE75B / SRC_08CC764E9C0DCB61 / 2025 IRDS — Yield Enhancement and Advanced Manufacturing & Contamination Control
Source provenance：IEEE International Roadmap for Devices and Systems (IRDS)；publication=；edition=2025；as_of=2025；source SHA256=`aa294fcf8fede75be6e2c23c6ec75a6f3504538dceb87eb51edda0134526b34b`。

**CANDIDATE_SUMMARY**

- Node 类型：Technology
- 名称：Microelectromechanical Systems
- 边界说明：制造技术与具体Sensor产品需要分层；此定位不足完整定义。

**AI REVIEW A**

- recommendation：HUMAN_REQUIRED；native_decision：DEFER
- proposed operation / canonical target：DEFER；范围/说明: IDENTITY_RECOMMENDATION_ONLY; Microelectromechanical Systems / Technology; no canonical mutation
- confidence：LOW
- reason：摘录仅出现 microelectromechanical (MEMS) 作为 critical process group，未支持 Systems 全称与制造技术/器件边界。
- evidence assessment：INSUFFICIENT；Evidence IDs：SC-EV-C74D00EC86C3E38E
- 必要置信度缺口：entity_resolution_clarity=LOW；evidence_directness=LOW；unit_scope_completeness=UNKNOWN

**AI REVIEW B**

- recommendation：HUMAN_REQUIRED；native_decision：DEFER
- proposed operation / canonical target：DEFER；范围/说明: IDENTITY_ONLY; 06_metrology_yield_factory; Microelectromechanical Systems; Technology
- confidence：LOW
- reason：原文把microelectromechanical列于critical process groups，既不足完整Systems定义又未区分制造技术与具体器件，暂缓。
- evidence assessment：INSUFFICIENT；Evidence IDs：SC-EV-C74D00EC86C3E38E
- 必要置信度缺口：entity_resolution_clarity=UNKNOWN；evidence_directness=LOW；rubric_applicability_clarity=UNKNOWN；unit_scope_completeness=LOW

**A/B RECONCILIATION**

- frozen status：A_B_DISAGREEMENT
- **DISAGREEMENT_TYPE** = 风险判定分歧 R05；风险判定分歧 R13
- **NATIVE_OPERATION_CONFLICT** = false
- R05 身份冲突：A=FALSE；B=UNKNOWN。A依据：完整 327 节点及 760 别名目录中，未发现本建议产生的身份冲突；明确共享核心者复用。 B依据：对象或关系端点的必要类型尚未统一：（具体证据与边界见本项该审查者 reason）
- R13 本体/类型映射问题：A=FALSE；B=TRUE。A依据：使用原对象可选原生决定及既有类型体系，未引入新 ontology 类型。 B依据：现有类型/关系映射存在未解决的表示问题：（具体证据与边界见本项该审查者 reason）

**EVIDENCE SUMMARY**

- Supporting facts：下列有来源的节选支持本项讨论的对象/命题；支持范围及未解决条件已在上方 A/B reason 中逐项说明。
- SC-EV-C74D00EC86C3E38E / SC-PHYS-AA294FCF8FEDE75B / PDF p.6 / 1 Introduction / More than Moore process groups / printed p.1；excerpt SHA256=`32b10b19734b046a2f54d3a767699a5b4f4a6a65852f7d8373ad9a7b7163f783`。
  > The Yield Enhancement (YE) chapter will display the current advanced and next generation future requirements for high yielding manufacturing of More Moore as well as More than Moore products separated in “critical process groups” including microelectromechanical (MEMS), back-end processes, e. g., packaging.
- Conflicting evidence / unresolved scope：上述 A/B 理由和差异列出已记录的冲突或缺口；未补造反证，也未因省略原文而解除冻结风险。

- **SYSTEM_RECOMMENDED_DECISION** = DEFER
推荐理由（非人工裁决）：双方均建议暂缓；风险标签或置信度差异没有补齐身份/类型/证据缺口。优先保留候选等待人工澄清，不强制选择新的目标、关系类型或对象边界。

HUMAN_USER_DECISION = [PENDING]

OPTIONS:

- [ ] CREATE
- [ ] REUSE <NODE_ID>
- [ ] DEFER
- [ ] REJECT

---

<a id="sc-cn-0135"></a>
### 064 · SC-CN-0135 · Photonic Integrated Circuit

- **ITEM_NUMBER** = 64
- **ITEM_ID** = SC-CN-0135
- **OBJECT_TYPE** = nodes
- **DOMAIN** = 07_more_than_moore
- **CURRENT_NATIVE_OPERATION** = UNDECIDED（没有已填写的人类原生决定）
- **CURRENT_STATUS** = REVIEW
- **WHY_IN_HUMAN_PACKET** = R01_A_B_DISAGREEMENT；R02；R03；R04；R05；REVIEWER_UNRESOLVED_HUMAN_REQUIRED
- **RISK_RULES** = R01 A/B实质分歧；R02 低或必要UNKNOWN置信度；R03 证据缺口；R04 实质命题歧义；R05 身份冲突
- **MANDATORY_TRIGGER** = R01_A_B_DISAGREEMENT；R02；R03；R04；R05；REVIEWER_UNRESOLVED_HUMAN_REQUIRED
- **SAMPLE_STATUS** = NOT_SAMPLED
- **SAMPLED_FOR_QUALITY_CONTROL** = false

- **SOURCE_ID / SOURCE_NAME** = SC-PHYS-EECFB29D71F7359F / SRC_C4BD0572E75C8392 / 2024 IRDS — Outside System Connectivity
Source provenance：IEEE International Roadmap for Devices and Systems (IRDS)；publication=；edition=2024；as_of=2024；source SHA256=`eecfb29d71f7359fccc255f854e9efe7262f82f06fad04ee56ecb871cf6defee`。

**CANDIDATE_SUMMARY**

- Node 类型：Product
- 名称：Photonic Integrated Circuit
- 备选身份：NODE_20260817_A418C71D
- 边界说明：通用PIC范围比Silicon Photonics PIC宽，不能直接复用硅光PIC。
- Canonical state：NODE_20260817_A418C71D = Silicon Photonics PIC；type=Product；status=active。

**AI REVIEW A**

- recommendation：HUMAN_REQUIRED；native_decision：DEFER
- proposed operation / canonical target：DEFER；范围/说明: IDENTITY_RECOMMENDATION_ONLY; Photonic Integrated Circuit / Product; no canonical mutation
- confidence：LOW
- reason：绑定摘录仅讨论发射电路激光器与调制器封装，章节提供 PIC 背景却不完整定义通用 Photonic Integrated Circuit；不能自动升为硅光 PIC 的父类。
- evidence assessment：INSUFFICIENT；Evidence IDs：SC-EV-09CB838BE857196B
- 必要置信度缺口：entity_resolution_clarity=LOW；evidence_directness=LOW；unit_scope_completeness=UNKNOWN

**AI REVIEW B**

- recommendation：HUMAN_REQUIRED；native_decision：DEFER
- proposed operation / canonical target：DEFER；范围/说明: IDENTITY_ONLY; 07_more_than_moore; Photonic Integrated Circuit; Product
- confidence：LOW
- reason：章节是Photonic Monolithic Heterogeneous Integrated Circuits，摘录只谈发射电路激光/调制器集成；泛PIC边界未定义，不能并入Silicon Photonics PIC。
- evidence assessment：INSUFFICIENT；Evidence IDs：SC-EV-09CB838BE857196B
- 必要置信度缺口：entity_resolution_clarity=UNKNOWN；evidence_directness=LOW；unit_scope_completeness=LOW

**A/B RECONCILIATION**

- frozen status：A_B_DISAGREEMENT
- **DISAGREEMENT_TYPE** = 风险判定分歧 R05
- **NATIVE_OPERATION_CONFLICT** = false
- R05 身份冲突：A=FALSE；B=UNKNOWN。A依据：完整 327 节点及 760 别名目录中，未发现本建议产生的身份冲突；明确共享核心者复用。 B依据：规范身份或候选所有者定义未完备：（具体证据与边界见本项该审查者 reason）

**EVIDENCE SUMMARY**

- Supporting facts：下列有来源的节选支持本项讨论的对象/命题；支持范围及未解决条件已在上方 A/B reason 中逐项说明。
- SC-EV-09CB838BE857196B / SC-PHYS-EECFB29D71F7359F / PDF p.40 / 6.2.1 Photonic Monolithic Heterogeneous Integrated Circuits / printed p.34；excerpt SHA256=`f9b8cb3d0ab41acc48af118cd3acf1be836df273dda4db3d1f53205b881b772b`。
  > Some of these transmitter circuits have the lasers integrated with the modulators, while some of these have the laser packaged separately from the modulators.
- Conflicting evidence / unresolved scope：上述 A/B 理由和差异列出已记录的冲突或缺口；未补造反证，也未因省略原文而解除冻结风险。

- **SYSTEM_RECOMMENDED_DECISION** = DEFER
推荐理由（非人工裁决）：双方均建议暂缓；风险标签或置信度差异没有补齐身份/类型/证据缺口。优先保留候选等待人工澄清，不强制选择新的目标、关系类型或对象边界。

HUMAN_USER_DECISION = [PENDING]

OPTIONS:

- [ ] CREATE
- [ ] REUSE <NODE_ID>
- [ ] DEFER
- [ ] REJECT

---

<a id="sc-cn-0143"></a>
### 065 · SC-CN-0143 · Diamond Thermal Material

- **ITEM_NUMBER** = 65
- **ITEM_ID** = SC-CN-0143
- **OBJECT_TYPE** = nodes
- **DOMAIN** = 08_assembly_packaging
- **CURRENT_NATIVE_OPERATION** = UNDECIDED（没有已填写的人类原生决定）
- **CURRENT_STATUS** = REVIEW
- **WHY_IN_HUMAN_PACKET** = R01_A_B_DISAGREEMENT；R02；R03；R04；R05；REVIEWER_UNRESOLVED_HUMAN_REQUIRED
- **RISK_RULES** = R01 A/B实质分歧；R02 低或必要UNKNOWN置信度；R03 证据缺口；R04 实质命题歧义；R05 身份冲突
- **MANDATORY_TRIGGER** = R01_A_B_DISAGREEMENT；R02；R03；R04；R05；REVIEWER_UNRESOLVED_HUMAN_REQUIRED
- **SAMPLE_STATUS** = NOT_SAMPLED
- **SAMPLED_FOR_QUALITY_CONTROL** = false

- **SOURCE_ID / SOURCE_NAME** = SC-PHYS-2E34AF6DD70E8C2C / SRC_944238EE8104A292 / 2025 HIR — Materials and Interfaces for Advanced Packaging, Rev 0.9
Source provenance：IEEE Electronics Packaging Society — Heterogeneous Integration Roadmap；publication=2026-03；edition=2025 Rev 0.9；as_of=2026-03；source SHA256=`2e34af6dd70e8c2c5de2aaabec15837693d1322abc0bb5820475188cd028a3f2`。

**CANDIDATE_SUMMARY**

- Node 类型：Material
- 名称：Diamond Thermal Material
- 边界说明：历史DEFER保持；文中为潜在替代方案，未证实部署。

**AI REVIEW A**

- recommendation：HUMAN_REQUIRED；native_decision：DEFER
- proposed operation / canonical target：DEFER；范围/说明: IDENTITY_RECOMMENDATION_ONLY; Diamond Thermal Material / Material; no canonical mutation
- confidence：LOW
- reason：证据是 BSPDN 替换 Si handler 的潜在 diamond 晶圆方案，候选 Diamond Thermal Material 过宽且历史边界待决；不以需求条件推定部署。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-6C7A98013D4B2FCF
- 必要置信度缺口：entity_resolution_clarity=LOW；outcome_completeness=LOW

**AI REVIEW B**

- recommendation：HUMAN_REQUIRED；native_decision：DEFER
- proposed operation / canonical target：DEFER；范围/说明: IDENTITY_ONLY; 08_assembly_packaging; Diamond Thermal Material; Material
- confidence：LOW
- reason：摘录讲BSPDN中用diamond替换Si handler的条件，图中另有diamond heat spreader；泛Diamond Thermal Material可能混入两种对象，且历史待决未解决。
- evidence assessment：INSUFFICIENT；Evidence IDs：SC-EV-6C7A98013D4B2FCF
- 必要置信度缺口：entity_resolution_clarity=UNKNOWN；evidence_directness=LOW；unit_scope_completeness=LOW

**A/B RECONCILIATION**

- frozen status：A_B_DISAGREEMENT
- **DISAGREEMENT_TYPE** = evidence sufficiency disagreement；风险判定分歧 R03；风险判定分歧 R05
- **NATIVE_OPERATION_CONFLICT** = false
- 证据充分性：A=SUFFICIENT；B=INSUFFICIENT
- R03 证据缺口：A=FALSE；B=TRUE。A依据：对应证据已按本条完整命题检查，不以非空摘录代替蕴含核验：（具体证据与边界见本项该审查者 reason） B依据：冻结证据不足以完成必要语义/身份判定：（具体证据与边界见本项该审查者 reason）
- R05 身份冲突：A=FALSE；B=TRUE。A依据：完整 327 节点及 760 别名目录中，未发现本建议产生的身份冲突；明确共享核心者复用。 B依据：不同身份或范围解释尚未收敛：（具体证据与边界见本项该审查者 reason）

**EVIDENCE SUMMARY**

- Supporting facts：下列有来源的节选支持本项讨论的对象/命题；支持范围及未解决条件已在上方 A/B reason 中逐项说明。
- SC-EV-6C7A98013D4B2FCF / SC-PHYS-2E34AF6DD70E8C2C / PDF p.20 / 2.3.2 3DIC Chip Stack Materials / printed p.20；excerpt SHA256=`f0087eeaa8c597c7a7247a67a8be7f1a33bffbdb2f58350ad5c513f4fe01fb41`。
  > For BSPDN, swapping the Si handler with a high k material like SiC or diamond would need 300mm wafers that can be processed through the fab.
- Conflicting evidence / unresolved scope：上述 A/B 理由和差异列出已记录的冲突或缺口；未补造反证，也未因省略原文而解除冻结风险。

- **SYSTEM_RECOMMENDED_DECISION** = DEFER
推荐理由（非人工裁决）：双方均建议暂缓；风险标签或置信度差异没有补齐身份/类型/证据缺口。优先保留候选等待人工澄清，不强制选择新的目标、关系类型或对象边界。

HUMAN_USER_DECISION = [PENDING]

OPTIONS:

- [ ] CREATE
- [ ] REUSE <NODE_ID>
- [ ] DEFER
- [ ] REJECT

---

<a id="sc-cn-0152"></a>
### 066 · SC-CN-0152 · 3DFabric

- **ITEM_NUMBER** = 66
- **ITEM_ID** = SC-CN-0152
- **OBJECT_TYPE** = nodes
- **DOMAIN** = 09_cross_domain_reuse
- **CURRENT_NATIVE_OPERATION** = UNDECIDED（没有已填写的人类原生决定）
- **CURRENT_STATUS** = REVIEW
- **WHY_IN_HUMAN_PACKET** = R01_A_B_DISAGREEMENT；R02；R04；R05；R07；R13；REVIEWER_UNRESOLVED_HUMAN_REQUIRED
- **RISK_RULES** = R01 A/B实质分歧；R02 低或必要UNKNOWN置信度；R04 实质命题歧义；R05 身份冲突；R07 新增高影响Node；R13 本体/类型映射问题
- **MANDATORY_TRIGGER** = R01_A_B_DISAGREEMENT；R02；R04；R05；R07；R13；REVIEWER_UNRESOLVED_HUMAN_REQUIRED
- **SAMPLE_STATUS** = NOT_SAMPLED
- **SAMPLED_FOR_QUALITY_CONTROL** = false

- **SOURCE_ID / SOURCE_NAME** = SC-PHYS-3FB7AE4AD972AA2B / F018b / TSMC 2025 Annual Report
Source provenance：TSMC；publication=；edition=；as_of=2025；source SHA256=`3fb7ae4ad972aa2bc6e45bb36635152ad89d52f4a7165f389bcb94eeb54a6abd`。

**CANDIDATE_SUMMARY**

- Node 类型：Technology
- 名称：3DFabric
- 边界说明：厂商服务体系/品牌伞；仅覆盖TSMC，不与Generic Advanced Packaging合并。

**AI REVIEW A**

- recommendation：HUMAN_REQUIRED；native_decision：DEFER
- proposed operation / canonical target：DEFER；范围/说明: IDENTITY_RECOMMENDATION_ONLY; 3DFabric / Technology; no canonical mutation
- confidence：LOW
- reason：3DFabric 原文为 TSMC 品牌服务组合，Technology 可能把商业服务伞形错作单一技术；应明确厂商范围与类型。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-407CEF45C2BE2751
- 必要置信度缺口：entity_resolution_clarity=LOW；outcome_completeness=LOW

**AI REVIEW B**

- recommendation：HUMAN_REQUIRED；native_decision：DEFER
- proposed operation / canonical target：DEFER；范围/说明: IDENTITY_ONLY; 09_cross_domain_reuse; 3DFabric; Technology
- confidence：UNKNOWN
- reason：3DFabric是TSMC覆盖SoIC/CoWoS等既有关键技术的品牌服务体系，Technology/平台伞形映射未定；会重置家族依赖，需人审。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-407CEF45C2BE2751
- 必要置信度缺口：entity_resolution_clarity=UNKNOWN；rubric_applicability_clarity=UNKNOWN

**A/B RECONCILIATION**

- frozen status：A_B_DISAGREEMENT
- **DISAGREEMENT_TYPE** = 风险判定分歧 R02；风险判定分歧 R04；风险判定分歧 R05；风险判定分歧 R07；必要置信度判定分歧
- **NATIVE_OPERATION_CONFLICT** = false
- R02 低或必要UNKNOWN置信度：A=TRUE；B=UNKNOWN。A依据：按 LOW > UNKNOWN > MEDIUM > HIGH 聚合，本条为 LOW。 B依据：九维按LOW > 必要UNKNOWN > MEDIUM > HIGH聚合为UNKNOWN。
- R04 实质命题歧义：A=TRUE；B=FALSE。A依据：（具体证据与边界见本项该审查者 reason） B依据：在明确范围下未见两个会改变本次推荐的证据解释；（具体证据与边界见本项该审查者 reason）
- R05 身份冲突：A=FALSE；B=UNKNOWN。A依据：完整 327 节点及 760 别名目录中，未发现本建议产生的身份冲突；明确共享核心者复用。 B依据：对象或关系端点的必要类型尚未统一：（具体证据与边界见本项该审查者 reason）
- R07 新增高影响Node：A=FALSE；B=TRUE。A依据：本条为普通局部身份建议，未建立跨域共享/关键层级或 View/Impact 锚点；非因新建自动判高影响。 B依据：有具体关键结构/平台依赖：（具体证据与边界见本项该审查者 reason）
- 聚合置信度：A=LOW；B=UNKNOWN

**EVIDENCE SUMMARY**

- Supporting facts：下列有来源的节选支持本项讨论的对象/命题；支持范围及未解决条件已在上方 A/B reason 中逐项说明。
- SC-EV-407CEF45C2BE2751 / SC-PHYS-3FB7AE4AD972AA2B / PDF p.60 / 5.4.2 Open Innovation Platform / 3DFabric services / printed p.114-117 (two-page spreads; obey section restriction)；excerpt SHA256=`21499de35ffabec8a497f43fd7ef382f84ba4650d994cfe40708f001d70d135c`。
  > using TSMC 3DFabric® advanced packaging services, which include TSMC-SoIC®, CoWoS®, TSMC-SoWTM, and TSMC COUPETM, and achieve system and process co-optimization.
- Conflicting evidence / unresolved scope：上述 A/B 理由和差异列出已记录的冲突或缺口；未补造反证，也未因省略原文而解除冻结风险。

- **SYSTEM_RECOMMENDED_DECISION** = DEFER
推荐理由（非人工裁决）：双方均建议暂缓；风险标签或置信度差异没有补齐身份/类型/证据缺口。优先保留候选等待人工澄清，不强制选择新的目标、关系类型或对象边界。

HUMAN_USER_DECISION = [PENDING]

OPTIONS:

- [ ] CREATE
- [ ] REUSE <NODE_ID>
- [ ] DEFER
- [ ] REJECT

---

<a id="sc-cn-0153"></a>
### 067 · SC-CN-0153 · Open Innovation Platform

- **ITEM_NUMBER** = 67
- **ITEM_ID** = SC-CN-0153
- **OBJECT_TYPE** = nodes
- **DOMAIN** = 09_cross_domain_reuse
- **CURRENT_NATIVE_OPERATION** = UNDECIDED（没有已填写的人类原生决定）
- **CURRENT_STATUS** = REVIEW
- **WHY_IN_HUMAN_PACKET** = R01_A_B_DISAGREEMENT；R02；R04；R05；R07；R13；REVIEWER_UNRESOLVED_HUMAN_REQUIRED
- **RISK_RULES** = R01 A/B实质分歧；R02 低或必要UNKNOWN置信度；R04 实质命题歧义；R05 身份冲突；R07 新增高影响Node；R13 本体/类型映射问题
- **MANDATORY_TRIGGER** = R01_A_B_DISAGREEMENT；R02；R04；R05；R07；R13；REVIEWER_UNRESOLVED_HUMAN_REQUIRED
- **SAMPLE_STATUS** = NOT_SAMPLED
- **SAMPLED_FOR_QUALITY_CONTROL** = false

- **SOURCE_ID / SOURCE_NAME** = SC-PHYS-3FB7AE4AD972AA2B / F018b / TSMC 2025 Annual Report
Source provenance：TSMC；publication=；edition=；as_of=2025；source SHA256=`3fb7ae4ad972aa2bc6e45bb36635152ad89d52f4a7165f389bcb94eeb54a6abd`。

**CANDIDATE_SUMMARY**

- Node 类型：Technology
- 名称：Open Innovation Platform
- 边界说明：TSMC厂商合作生态，不能泛化为全部EDA/IP生态。

**AI REVIEW A**

- recommendation：HUMAN_REQUIRED；native_decision：DEFER
- proposed operation / canonical target：DEFER；范围/说明: IDENTITY_RECOMMENDATION_ONLY; Open Innovation Platform / Technology; no canonical mutation
- confidence：LOW
- reason：OIP 定义为 collaboration alliance/设计基础设施，非简单通用 Technology；需明确 TSMC 生态身份而不能覆盖所有 EDA/IP。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-7B73EC29C7C90875
- 必要置信度缺口：entity_resolution_clarity=LOW；outcome_completeness=LOW

**AI REVIEW B**

- recommendation：HUMAN_REQUIRED；native_decision：DEFER
- proposed operation / canonical target：DEFER；范围/说明: IDENTITY_ONLY; 09_cross_domain_reuse; Open Innovation Platform; Technology
- confidence：UNKNOWN
- reason：OIP被称合作联盟和设计基础设施，不能直接等同单一Technology；作为EDA/IP设计协作基础锚点有结构性影响，需治理类型。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-7B73EC29C7C90875
- 必要置信度缺口：entity_resolution_clarity=UNKNOWN；rubric_applicability_clarity=UNKNOWN

**A/B RECONCILIATION**

- frozen status：A_B_DISAGREEMENT
- **DISAGREEMENT_TYPE** = 风险判定分歧 R02；风险判定分歧 R04；风险判定分歧 R05；风险判定分歧 R07；必要置信度判定分歧
- **NATIVE_OPERATION_CONFLICT** = false
- R02 低或必要UNKNOWN置信度：A=TRUE；B=UNKNOWN。A依据：按 LOW > UNKNOWN > MEDIUM > HIGH 聚合，本条为 LOW。 B依据：九维按LOW > 必要UNKNOWN > MEDIUM > HIGH聚合为UNKNOWN。
- R04 实质命题歧义：A=TRUE；B=FALSE。A依据：（具体证据与边界见本项该审查者 reason） B依据：在明确范围下未见两个会改变本次推荐的证据解释；（具体证据与边界见本项该审查者 reason）
- R05 身份冲突：A=FALSE；B=UNKNOWN。A依据：完整 327 节点及 760 别名目录中，未发现本建议产生的身份冲突；明确共享核心者复用。 B依据：对象或关系端点的必要类型尚未统一：（具体证据与边界见本项该审查者 reason）
- R07 新增高影响Node：A=FALSE；B=TRUE。A依据：本条为普通局部身份建议，未建立跨域共享/关键层级或 View/Impact 锚点；非因新建自动判高影响。 B依据：有具体关键结构/平台依赖：（具体证据与边界见本项该审查者 reason）
- 聚合置信度：A=LOW；B=UNKNOWN

**EVIDENCE SUMMARY**

- Supporting facts：下列有来源的节选支持本项讨论的对象/命题；支持范围及未解决条件已在上方 A/B reason 中逐项说明。
- SC-EV-7B73EC29C7C90875 / SC-PHYS-3FB7AE4AD972AA2B / PDF p.59 / 5.4.2 Open Innovation Platform / printed p.114-117 (two-page spreads; obey section restriction)；excerpt SHA256=`19278db3f8f8d2343e95da66642af8b7bad694e7aa836512d89f849be2cbccd8`。
  > The Open Innovation Platform® collaboration alliance is a comprehensive design technology infrastructure that encompasses all critical IC implementation areas to lower design barriers, improve cycle times and raise first-time silicon success rates.
- Conflicting evidence / unresolved scope：上述 A/B 理由和差异列出已记录的冲突或缺口；未补造反证，也未因省略原文而解除冻结风险。

- **SYSTEM_RECOMMENDED_DECISION** = DEFER
推荐理由（非人工裁决）：双方均建议暂缓；风险标签或置信度差异没有补齐身份/类型/证据缺口。优先保留候选等待人工澄清，不强制选择新的目标、关系类型或对象边界。

HUMAN_USER_DECISION = [PENDING]

OPTIONS:

- [ ] CREATE
- [ ] REUSE <NODE_ID>
- [ ] DEFER
- [ ] REJECT

---

<a id="sc-cn-0159"></a>
### 068 · SC-CN-0159 · Glass Core Substrate

- **ITEM_NUMBER** = 68
- **ITEM_ID** = SC-CN-0159
- **OBJECT_TYPE** = nodes
- **DOMAIN** = 08_assembly_packaging
- **CURRENT_NATIVE_OPERATION** = UNDECIDED（没有已填写的人类原生决定）
- **CURRENT_STATUS** = REVIEW
- **WHY_IN_HUMAN_PACKET** = R01_A_B_DISAGREEMENT；R02；R04；R05；R06；R13；REVIEWER_UNRESOLVED_HUMAN_REQUIRED
- **RISK_RULES** = R01 A/B实质分歧；R02 低或必要UNKNOWN置信度；R04 实质命题歧义；R05 身份冲突；R06 跨域身份冲突；R13 本体/类型映射问题
- **MANDATORY_TRIGGER** = R01_A_B_DISAGREEMENT；R02；R04；R05；R06；R13；REVIEWER_UNRESOLVED_HUMAN_REQUIRED
- **SAMPLE_STATUS** = NOT_SAMPLED
- **SAMPLED_FOR_QUALITY_CONTROL** = false

- **SOURCE_ID / SOURCE_NAME** = SC-PHYS-2E34AF6DD70E8C2C / SRC_944238EE8104A292 / 2025 HIR — Materials and Interfaces for Advanced Packaging, Rev 0.9
Source provenance：IEEE Electronics Packaging Society — Heterogeneous Integration Roadmap；publication=2026-03；edition=2025 Rev 0.9；as_of=2026-03；source SHA256=`2e34af6dd70e8c2c5de2aaabec15837693d1322abc0bb5820475188cd028a3f2`。

**CANDIDATE_SUMMARY**

- Node 类型：Material
- 名称：Glass Core Substrate
- 边界说明：PHASE1_1A CROSS_DOMAIN_QUARANTINE；Figure1仅提出材料位置，不授权新身份或量产结论。

**AI REVIEW A**

- recommendation：HUMAN_REQUIRED；native_decision：DEFER
- proposed operation / canonical target：DEFER；范围/说明: IDENTITY_RECOMMENDATION_ONLY; Glass Core Substrate / Material; no canonical mutation
- confidence：LOW
- reason：已看 Figure 1 中 Glass Core Substrate 的具体位置，但示意图不能解除输入的跨域隔离，且材料/产品粒度仍待身份治理。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-7FF5E762CAC4DB05
- 必要置信度缺口：conflict_accounting=LOW；entity_resolution_clarity=LOW；outcome_completeness=LOW

**AI REVIEW B**

- recommendation：HUMAN_REQUIRED；native_decision：DEFER
- proposed operation / canonical target：DEFER；范围/说明: IDENTITY_ONLY; 08_assembly_packaging; Glass Core Substrate; Material
- confidence：UNKNOWN
- reason：图1确实标Glass Core Substrate，但为前瞻材料位置示意，不能解决Material/Product边界及冻结跨域隔离事项。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-7FF5E762CAC4DB05
- 必要置信度缺口：conflict_accounting=UNKNOWN；entity_resolution_clarity=UNKNOWN；rubric_applicability_clarity=UNKNOWN

**A/B RECONCILIATION**

- frozen status：A_B_DISAGREEMENT
- **DISAGREEMENT_TYPE** = 风险判定分歧 R02；风险判定分歧 R04；风险判定分歧 R05；风险判定分歧 R06；风险判定分歧 R13；必要置信度判定分歧
- **NATIVE_OPERATION_CONFLICT** = false
- R02 低或必要UNKNOWN置信度：A=TRUE；B=UNKNOWN。A依据：按 LOW > UNKNOWN > MEDIUM > HIGH 聚合，本条为 LOW。 B依据：九维按LOW > 必要UNKNOWN > MEDIUM > HIGH聚合为UNKNOWN。
- R04 实质命题歧义：A=UNKNOWN；B=FALSE。A依据：（具体证据与边界见本项该审查者 reason） B依据：在明确范围下未见两个会改变本次推荐的证据解释；（具体证据与边界见本项该审查者 reason）
- R05 身份冲突：A=FALSE；B=UNKNOWN。A依据：完整 327 节点及 760 别名目录中，未发现本建议产生的身份冲突；明确共享核心者复用。 B依据：隔离端点没有可证实的最终canonical身份裁定：（具体证据与边界见本项该审查者 reason）
- R06 跨域身份冲突：A=TRUE；B=UNKNOWN。A依据：（具体证据与边界见本项该审查者 reason） B依据：冻结历史隔离继续有效；来源语义清楚不能替代缺失的跨域身份冲突裁定：（具体证据与边界见本项该审查者 reason）
- R13 本体/类型映射问题：A=FALSE；B=TRUE。A依据：使用原对象可选原生决定及既有类型体系，未引入新 ontology 类型。 B依据：现有类型/关系映射存在未解决的表示问题：（具体证据与边界见本项该审查者 reason）
- 聚合置信度：A=LOW；B=UNKNOWN

**EVIDENCE SUMMARY**

- Supporting facts：下列有来源的节选支持本项讨论的对象/命题；支持范围及未解决条件已在上方 A/B reason 中逐项说明。
- SC-EV-7FF5E762CAC4DB05 / SC-PHYS-2E34AF6DD70E8C2C / PDF p.2 / Overview of key materials and interfaces / printed p.2 / Figure 1；excerpt SHA256=`97c137bbc0f7a3ffb1d3bf72d677a7edf0929eb70f89e5f546c6d94f85b46f7d`。
  > Glass Core Substrate
- Conflicting evidence / unresolved scope：上述 A/B 理由和差异列出已记录的冲突或缺口；未补造反证，也未因省略原文而解除冻结风险。

- **SYSTEM_RECOMMENDED_DECISION** = DEFER
推荐理由（非人工裁决）：双方均建议暂缓；风险标签或置信度差异没有补齐身份/类型/证据缺口。优先保留候选等待人工澄清，不强制选择新的目标、关系类型或对象边界。

HUMAN_USER_DECISION = [PENDING]

OPTIONS:

- [ ] CREATE
- [ ] REUSE <NODE_ID>
- [ ] DEFER
- [ ] REJECT

---

<a id="sc-cn-0163"></a>
### 069 · SC-CN-0163 · RF Integrated Circuit

- **ITEM_NUMBER** = 69
- **ITEM_ID** = SC-CN-0163
- **OBJECT_TYPE** = nodes
- **DOMAIN** = 07_more_than_moore
- **CURRENT_NATIVE_OPERATION** = UNDECIDED（没有已填写的人类原生决定）
- **CURRENT_STATUS** = REVIEW
- **WHY_IN_HUMAN_PACKET** = R01_A_B_DISAGREEMENT；R02；R03；R04；R05；REVIEWER_UNRESOLVED_HUMAN_REQUIRED
- **RISK_RULES** = R01 A/B实质分歧；R02 低或必要UNKNOWN置信度；R03 证据缺口；R04 实质命题歧义；R05 身份冲突
- **MANDATORY_TRIGGER** = R01_A_B_DISAGREEMENT；R02；R03；R04；R05；REVIEWER_UNRESOLVED_HUMAN_REQUIRED
- **SAMPLE_STATUS** = NOT_SAMPLED
- **SAMPLED_FOR_QUALITY_CONTROL** = false

- **SOURCE_ID / SOURCE_NAME** = SC-PHYS-EECFB29D71F7359F / SRC_C4BD0572E75C8392 / 2024 IRDS — Outside System Connectivity
Source provenance：IEEE International Roadmap for Devices and Systems (IRDS)；publication=；edition=2024；as_of=2024；source SHA256=`eecfb29d71f7359fccc255f854e9efe7262f82f06fad04ee56ecb871cf6defee`。

**CANDIDATE_SUMMARY**

- Node 类型：Product
- 名称：RF Integrated Circuit
- 边界说明：RF器件/电路层级与existing RF应用细分存在交叉；本轮保留宽泛电路族待审。

**AI REVIEW A**

- recommendation：HUMAN_REQUIRED；native_decision：DEFER
- proposed operation / canonical target：DEFER；范围/说明: IDENTITY_RECOMMENDATION_ONLY; RF Integrated Circuit / Product; no canonical mutation
- confidence：LOW
- reason：原文谈 RF components 挑战而未限定全部为集成电路，RF Integrated Circuit 的产品范围未被完整支持；需明确排除离散 RF 元件。
- evidence assessment：INSUFFICIENT；Evidence IDs：SC-EV-80314FEB50CF37D6
- 必要置信度缺口：entity_resolution_clarity=LOW；evidence_directness=LOW；unit_scope_completeness=UNKNOWN

**AI REVIEW B**

- recommendation：HUMAN_REQUIRED；native_decision：DEFER
- proposed operation / canonical target：DEFER；范围/说明: IDENTITY_ONLY; 07_more_than_moore; RF Integrated Circuit; Product
- confidence：LOW
- reason：摘录谈RF components/analog technology挑战，没有定义RF Integrated Circuit这一完整产品族；无法从应用场景推出节点粒度。
- evidence assessment：INSUFFICIENT；Evidence IDs：SC-EV-80314FEB50CF37D6
- 必要置信度缺口：entity_resolution_clarity=UNKNOWN；evidence_directness=LOW；unit_scope_completeness=LOW

**A/B RECONCILIATION**

- frozen status：A_B_DISAGREEMENT
- **DISAGREEMENT_TYPE** = 风险判定分歧 R05
- **NATIVE_OPERATION_CONFLICT** = false
- R05 身份冲突：A=FALSE；B=UNKNOWN。A依据：完整 327 节点及 760 别名目录中，未发现本建议产生的身份冲突；明确共享核心者复用。 B依据：规范身份或候选所有者定义未完备：（具体证据与边界见本项该审查者 reason）

**EVIDENCE SUMMARY**

- Supporting facts：下列有来源的节选支持本项讨论的对象/命题；支持范围及未解决条件已在上方 A/B reason 中逐项说明。
- SC-EV-80314FEB50CF37D6 / SC-PHYS-EECFB29D71F7359F / PDF p.31 / 6.1 RF Integrated Circuits and Devices / printed p.25；excerpt SHA256=`baa6ccf7a916ac7060efea71adcf16b86269de8e19f0972d6ff2fedcd39770b5`。
  > The challenges for RF components include 1) achieving high performance, wider bandwidth to increase data rate, and energy efficient RF analog technology with high linearity that is compatible with CMOS based digital processing that has a good compromise for high data rate (wide band) ADC/DAC, and 2) components to meet 5G and 6G performance requirements.
- Conflicting evidence / unresolved scope：上述 A/B 理由和差异列出已记录的冲突或缺口；未补造反证，也未因省略原文而解除冻结风险。

- **SYSTEM_RECOMMENDED_DECISION** = DEFER
推荐理由（非人工裁决）：双方均建议暂缓；风险标签或置信度差异没有补齐身份/类型/证据缺口。优先保留候选等待人工澄清，不强制选择新的目标、关系类型或对象边界。

HUMAN_USER_DECISION = [PENDING]

OPTIONS:

- [ ] CREATE
- [ ] REUSE <NODE_ID>
- [ ] DEFER
- [ ] REJECT

---

<a id="sc-rl-0008"></a>
### 070 · SC-RL-0008 · NAND Flash是Flash memories的一个类别；节点历史隔离尚未解除。

- **ITEM_NUMBER** = 70
- **ITEM_ID** = SC-RL-0008
- **OBJECT_TYPE** = relations
- **DOMAIN** = semiconductor
- **CURRENT_NATIVE_OPERATION** = NEW_RELATION_CANDIDATE
- **CURRENT_STATUS** = REVIEW
- **WHY_IN_HUMAN_PACKET** = R01_A_B_DISAGREEMENT；R02；R04；R05；R06；R08；REVIEWER_UNRESOLVED_HUMAN_REQUIRED
- **RISK_RULES** = R01 A/B实质分歧；R02 低或必要UNKNOWN置信度；R04 实质命题歧义；R05 身份冲突；R06 跨域身份冲突；R08 实质关系歧义
- **MANDATORY_TRIGGER** = R01_A_B_DISAGREEMENT；R02；R04；R05；R06；R08；REVIEWER_UNRESOLVED_HUMAN_REQUIRED
- **SAMPLE_STATUS** = NOT_SAMPLED
- **SAMPLED_FOR_QUALITY_CONTROL** = false

- **SOURCE_ID / SOURCE_NAME** = SC-PHYS-49A1D3B42E458985 / SRC_96EC545507C25F9F / 2024 IRDS — More Moore
Source provenance：IEEE International Roadmap for Devices and Systems (IRDS)；publication=；edition=2024；as_of=2024；source SHA256=`49a1d3b42e45898555490e602170876e22d1ccf8d7c17711e436d8db36322fa6`。

**CANDIDATE_SUMMARY**

- 关系类型：part_of
- 命题：NAND Flash是Flash memories的一个类别；节点历史隔离尚未解除。
- 时间类别：categorical_source_scoped
- 终点：Flash Memory
- 范围：IRDS More Moore 2024 / nonvolatile-memory taxonomy
- 起点：NAND Flash
- Candidate target：SC-CN-0011 = NAND Flash；type=Product；frozen status=REVIEW；仍须目标自身授权。
- Candidate target：SC-CN-0101 = Flash Memory；type=Product；frozen status=CREATE；仍须目标自身授权。

**AI REVIEW A**

- recommendation：HUMAN_REQUIRED；native_decision：DEFER
- proposed operation / canonical target：DEFER；起点: SC-CN-0011 [NAND Flash]；终点: SC-CN-0101 [Flash Memory]；关系: part_of；范围/说明: IRDS More Moore 2024 / nonvolatile-memory taxonomy
- confidence：LOW
- reason：NAND→Flash 分类语义直接，但 NAND 候选 0011 的跨域隔离未解除；保留候选端点并暂缓关系，不能绕过节点冲突。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-288A875770100378
- 必要置信度缺口：conflict_accounting=LOW；entity_resolution_clarity=LOW；outcome_completeness=LOW

**AI REVIEW B**

- recommendation：HUMAN_REQUIRED；native_decision：DEFER
- proposed operation / canonical target：DEFER；起点: SC-CN-0011 [NAND Flash]；终点: SC-CN-0101 [Flash Memory]；关系: part_of；范围/说明: IRDS More Moore 2024 / nonvolatile-memory taxonomy
- confidence：UNKNOWN
- reason：NAND归Flash的分类本身直接支持，但NAND端点跨域隔离未解除；暂缓建边而不改为其他存储身份。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-288A875770100378
- 必要置信度缺口：conflict_accounting=UNKNOWN；entity_resolution_clarity=UNKNOWN

**A/B RECONCILIATION**

- frozen status：A_B_DISAGREEMENT
- **DISAGREEMENT_TYPE** = 风险判定分歧 R02；风险判定分歧 R04；风险判定分歧 R05；风险判定分歧 R06；风险判定分歧 R08；必要置信度判定分歧
- **NATIVE_OPERATION_CONFLICT** = false
- R02 低或必要UNKNOWN置信度：A=TRUE；B=UNKNOWN。A依据：按 LOW > UNKNOWN > MEDIUM > HIGH 聚合，本条为 LOW。 B依据：九维按LOW > 必要UNKNOWN > MEDIUM > HIGH聚合为UNKNOWN。
- R04 实质命题歧义：A=UNKNOWN；B=FALSE。A依据：（具体证据与边界见本项该审查者 reason） B依据：在明确范围下未见两个会改变本次推荐的证据解释；（具体证据与边界见本项该审查者 reason）
- R05 身份冲突：A=FALSE；B=UNKNOWN。A依据：完整 327 节点及 760 别名目录中，未发现本建议产生的身份冲突；明确共享核心者复用。 B依据：隔离端点没有可证实的最终canonical身份裁定：（具体证据与边界见本项该审查者 reason）
- R06 跨域身份冲突：A=TRUE；B=UNKNOWN。A依据：（具体证据与边界见本项该审查者 reason） B依据：冻结历史隔离继续有效；来源语义清楚不能替代缺失的跨域身份冲突裁定：（具体证据与边界见本项该审查者 reason）
- R08 实质关系歧义：A=UNKNOWN；B=FALSE。A依据：实质语义有影响，但必要关系/范围判断未定：（具体证据与边界见本项该审查者 reason） B依据：relation_ambiguity=FALSE; materiality=TRUE。关系类型/端点/范围改变具有知识结果影响；（具体证据与边界见本项该审查者 reason）
- 聚合置信度：A=LOW；B=UNKNOWN
- relation_ambiguity：A=UNKNOWN；B=FALSE

**EVIDENCE SUMMARY**

- Supporting facts：下列有来源的节选支持本项讨论的对象/命题；支持范围及未解决条件已在上方 A/B reason 中逐项说明。
- SC-EV-288A875770100378 / SC-PHYS-49A1D3B42E458985 / PDF p.27 / 5 Nonvolatile Memory / printed p.22；excerpt SHA256=`0d6eee3a3851d1bf15c3869444bf496d00cde00a9ff7f0fedfae6be103233f5a`。
  > Nonvolatile memory may be divided into two large categories—Flash memories (NAND Flash and NOR Flash), and non-charge-based-storage memories.
- Conflicting evidence / unresolved scope：上述 A/B 理由和差异列出已记录的冲突或缺口；未补造反证，也未因省略原文而解除冻结风险。

- **SYSTEM_RECOMMENDED_DECISION** = DEFER
推荐理由（非人工裁决）：双方均建议暂缓；风险标签或置信度差异没有补齐身份/类型/证据缺口。优先保留候选等待人工澄清，不强制选择新的目标、关系类型或对象边界。

HUMAN_USER_DECISION = [PENDING]

OPTIONS:

- [ ] CREATE
- [ ] REUSE <RELATION_ID>
- [ ] DEFER
- [ ] REJECT

---

<a id="sc-rl-0028"></a>
### 071 · SC-RL-0028 · SUMCO所述CZ流程在石英坩埚中熔化多晶硅。

- **ITEM_NUMBER** = 71
- **ITEM_ID** = SC-RL-0028
- **OBJECT_TYPE** = relations
- **DOMAIN** = semiconductor
- **CURRENT_NATIVE_OPERATION** = NEW_RELATION_CANDIDATE
- **CURRENT_STATUS** = REVIEW
- **WHY_IN_HUMAN_PACKET** = R01_A_B_DISAGREEMENT；R02；R04；R05；R13；REVIEWER_UNRESOLVED_HUMAN_REQUIRED
- **RISK_RULES** = R01 A/B实质分歧；R02 低或必要UNKNOWN置信度；R04 实质命题歧义；R05 身份冲突；R13 本体/类型映射问题
- **MANDATORY_TRIGGER** = R01_A_B_DISAGREEMENT；R02；R04；R05；R13；REVIEWER_UNRESOLVED_HUMAN_REQUIRED
- **SAMPLE_STATUS** = NOT_SAMPLED
- **SAMPLED_FOR_QUALITY_CONTROL** = false

- **SOURCE_ID / SOURCE_NAME** = SC-PHYS-9E9CEFC24043585C / SRC_8442AD30618C9A2D / Production Processes
Source provenance：SUMCO Corporation；publication=；edition=；as_of=；source SHA256=`9e9cefc24043585c1c5a484340dcf49aa0725b341467942d3d4c34be0da8aee6`。

**CANDIDATE_SUMMARY**

- 关系类型：uses
- 命题：SUMCO所述CZ流程在石英坩埚中熔化多晶硅。
- 时间类别：categorical_source_scoped
- 终点：Quartz Crucible
- 范围：SUMCO CZ process; undated
- 起点：Czochralski Crystal Growth
- Candidate target：SC-CN-0034 = Czochralski Crystal Growth；type=Technology；frozen status=CREATE；仍须目标自身授权。
- Candidate target：SC-CN-0037 = Quartz Crucible；type=Equipment；frozen status=REVIEW；仍须目标自身授权。

**AI REVIEW A**

- recommendation：HUMAN_REQUIRED；native_decision：DEFER
- proposed operation / canonical target：DEFER；起点: SC-CN-0034 [Czochralski Crystal Growth]；终点: SC-CN-0037 [Quartz Crucible]；关系: uses；范围/说明: SUMCO CZ process; undated
- confidence：LOW
- reason：CZ 小节明确坩埚使用关系，方向不含糊；但目标 Quartz Crucible 0037 的 Equipment/Product 类型未决，暂缓完整关系 outcome。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-1811D226786D163F
- 必要置信度缺口：entity_resolution_clarity=LOW；outcome_completeness=LOW

**AI REVIEW B**

- recommendation：HUMAN_REQUIRED；native_decision：DEFER
- proposed operation / canonical target：DEFER；起点: SC-CN-0034 [Czochralski Crystal Growth]；终点: SC-CN-0037 [Quartz Crucible]；关系: uses；范围/说明: SUMCO CZ process; undated
- confidence：UNKNOWN
- reason：CZ章节石英坩埚内熔化原料支持使用方向，但SC-CN-0037的设备/部件类型未定；端点未解决前暂缓关系。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-1811D226786D163F
- 必要置信度缺口：entity_resolution_clarity=UNKNOWN；rubric_applicability_clarity=UNKNOWN

**A/B RECONCILIATION**

- frozen status：A_B_DISAGREEMENT
- **DISAGREEMENT_TYPE** = 风险判定分歧 R02；风险判定分歧 R04；风险判定分歧 R05；风险判定分歧 R13；必要置信度判定分歧
- **NATIVE_OPERATION_CONFLICT** = false
- R02 低或必要UNKNOWN置信度：A=TRUE；B=UNKNOWN。A依据：按 LOW > UNKNOWN > MEDIUM > HIGH 聚合，本条为 LOW。 B依据：九维按LOW > 必要UNKNOWN > MEDIUM > HIGH聚合为UNKNOWN。
- R04 实质命题歧义：A=TRUE；B=FALSE。A依据：（具体证据与边界见本项该审查者 reason） B依据：在明确范围下未见两个会改变本次推荐的证据解释；（具体证据与边界见本项该审查者 reason）
- R05 身份冲突：A=FALSE；B=UNKNOWN。A依据：完整 327 节点及 760 别名目录中，未发现本建议产生的身份冲突；明确共享核心者复用。 B依据：对象或关系端点的必要类型尚未统一：（具体证据与边界见本项该审查者 reason）
- R13 本体/类型映射问题：A=FALSE；B=TRUE。A依据：使用原对象可选原生决定及既有类型体系，未引入新 ontology 类型。 B依据：现有类型/关系映射存在未解决的表示问题：（具体证据与边界见本项该审查者 reason）
- 聚合置信度：A=LOW；B=UNKNOWN

**EVIDENCE SUMMARY**

- Supporting facts：下列有来源的节选支持本项讨论的对象/命题；支持范围及未解决条件已在上方 A/B reason 中逐项说明。
- SC-EV-1811D226786D163F / SC-PHYS-9E9CEFC24043585C / PDF p.2 / Flow of CZ process / printed p.NOT_KNOWN_OR_UNNUMBERED；excerpt SHA256=`014615fff3d822d511b8420e52cb198218ff0c9777d64741ed7f5b226d6ceb9c`。
  > Polysilicon purified until the metal impurities are no more than a few parts per billion (ppb) is put into a quartz crucible along with boron (B) and phosphorous (P), and melted at a temperature of around 1420℃.
- Conflicting evidence / unresolved scope：上述 A/B 理由和差异列出已记录的冲突或缺口；未补造反证，也未因省略原文而解除冻结风险。

- **SYSTEM_RECOMMENDED_DECISION** = DEFER
推荐理由（非人工裁决）：双方均建议暂缓；风险标签或置信度差异没有补齐身份/类型/证据缺口。优先保留候选等待人工澄清，不强制选择新的目标、关系类型或对象边界。

HUMAN_USER_DECISION = [PENDING]

OPTIONS:

- [ ] CREATE
- [ ] REUSE <RELATION_ID>
- [ ] DEFER
- [ ] REJECT

---

<a id="sc-rl-0037"></a>
### 072 · SC-RL-0037 · SIA所述曝光采用stepper或scanner。

- **ITEM_NUMBER** = 72
- **ITEM_ID** = SC-RL-0037
- **OBJECT_TYPE** = relations
- **DOMAIN** = semiconductor
- **CURRENT_NATIVE_OPERATION** = NEW_RELATION_CANDIDATE
- **CURRENT_STATUS** = REVIEW
- **WHY_IN_HUMAN_PACKET** = R01_A_B_DISAGREEMENT；R02；R04；R05；R08；R13；REVIEWER_UNRESOLVED_HUMAN_REQUIRED
- **RISK_RULES** = R01 A/B实质分歧；R02 低或必要UNKNOWN置信度；R04 实质命题歧义；R05 身份冲突；R08 实质关系歧义；R13 本体/类型映射问题
- **MANDATORY_TRIGGER** = R01_A_B_DISAGREEMENT；R02；R04；R05；R08；R13；REVIEWER_UNRESOLVED_HUMAN_REQUIRED
- **SAMPLE_STATUS** = NOT_SAMPLED
- **SAMPLED_FOR_QUALITY_CONTROL** = false

- **SOURCE_ID / SOURCE_NAME** = SC-PHYS-C5B6DC633E156218 / SRC_AC29CFEE56F74F5B / Testimony of the Semiconductor Industry Association before the Senate Committee on Environment & Public Works (March 4, 2026)
Source provenance：Semiconductor Industry Association (SIA)；publication=2026-03-04；edition=；as_of=2026-03-04；source SHA256=`c5b6dc633e156218eb950f2dee88f43fbdcc4fc1744a5924f12b977f5cb7df71`。

**CANDIDATE_SUMMARY**

- 关系类型：uses
- 命题：SIA所述曝光采用stepper或scanner。
- 时间类别：categorical_source_scoped
- 终点：Lithography Scanner / Stepper
- 范围：SIA 2026 testimony / photolithography equipment
- 起点：Photolithography
- Candidate target：SC-CN-0056 = Photolithography；type=Technology；frozen status=CREATE；仍须目标自身授权。
- Candidate target：SC-CN-0057 = Lithography Scanner / Stepper；type=Equipment；frozen status=REVIEW；仍须目标自身授权。

**AI REVIEW A**

- recommendation：HUMAN_REQUIRED；native_decision：DEFER
- proposed operation / canonical target：DEFER；起点: SC-CN-0056 [Photolithography]；终点: SC-CN-0057 [Lithography Scanner / Stepper]；关系: uses；范围/说明: SIA 2026 testimony / photolithography equipment
- confidence：LOW
- reason：曝光使用 stepper or scanner 有直接证据，但目标 0057 把替代设备合并的身份粒度未定；不能在关系中绕过该歧义。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-67EC75515BB09180
- 必要置信度缺口：entity_resolution_clarity=LOW；outcome_completeness=LOW

**AI REVIEW B**

- recommendation：HUMAN_REQUIRED；native_decision：DEFER
- proposed operation / canonical target：DEFER；起点: SC-CN-0056 [Photolithography]；终点: SC-CN-0057 [Lithography Scanner / Stepper]；关系: uses；范围/说明: SIA 2026 testimony / photolithography equipment
- confidence：UNKNOWN
- reason：原文stepper or scanner是可替代设备，合并端点SC-CN-0057尚未有唯一身份；关系工具选择会改变图端点，需先定粒度。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-67EC75515BB09180
- 必要置信度缺口：entity_resolution_clarity=UNKNOWN；rubric_applicability_clarity=UNKNOWN

**A/B RECONCILIATION**

- frozen status：A_B_DISAGREEMENT
- **DISAGREEMENT_TYPE** = 风险判定分歧 R02；风险判定分歧 R05；风险判定分歧 R08；风险判定分歧 R13；必要置信度判定分歧
- **NATIVE_OPERATION_CONFLICT** = false
- R02 低或必要UNKNOWN置信度：A=TRUE；B=UNKNOWN。A依据：按 LOW > UNKNOWN > MEDIUM > HIGH 聚合，本条为 LOW。 B依据：九维按LOW > 必要UNKNOWN > MEDIUM > HIGH聚合为UNKNOWN。
- R05 身份冲突：A=FALSE；B=TRUE。A依据：完整 327 节点及 760 别名目录中，未发现本建议产生的身份冲突；明确共享核心者复用。 B依据：不同身份或范围解释尚未收敛：（具体证据与边界见本项该审查者 reason）
- R08 实质关系歧义：A=FALSE；B=TRUE。A依据：用途/方向本身明确，但原生 outcome 的端点仍未解决：（具体证据与边界见本项该审查者 reason） B依据：relation_ambiguity=TRUE; materiality=TRUE。关系类型/端点/范围改变具有知识结果影响；（具体证据与边界见本项该审查者 reason）
- R13 本体/类型映射问题：A=FALSE；B=TRUE。A依据：使用原对象可选原生决定及既有类型体系，未引入新 ontology 类型。 B依据：现有类型/关系映射存在未解决的表示问题：（具体证据与边界见本项该审查者 reason）
- 聚合置信度：A=LOW；B=UNKNOWN
- relation_ambiguity：A=FALSE；B=TRUE

**EVIDENCE SUMMARY**

- Supporting facts：下列有来源的节选支持本项讨论的对象/命题；支持范围及未解决条件已在上方 A/B reason 中逐项说明。
- SC-EV-67EC75515BB09180 / SC-PHYS-C5B6DC633E156218 / PDF p.4 / II / Front-End Fabrication / Photolithography / printed p.4；excerpt SHA256=`d49de79df3fb0e595282e9746bcd100459e0a41920f737ed1446f4908192c3a1`。
  > A stepper or scanner (using deep ultraviolet or extreme ultraviolet light) aligns the wafer to a glass photomask and projects intense light through the mask or reticle, exposing the photoresist with the pattern.
- Conflicting evidence / unresolved scope：上述 A/B 理由和差异列出已记录的冲突或缺口；未补造反证，也未因省略原文而解除冻结风险。

- **SYSTEM_RECOMMENDED_DECISION** = DEFER
推荐理由（非人工裁决）：双方均建议暂缓；风险标签或置信度差异没有补齐身份/类型/证据缺口。优先保留候选等待人工澄清，不强制选择新的目标、关系类型或对象边界。

HUMAN_USER_DECISION = [PENDING]

OPTIONS:

- [ ] CREATE
- [ ] REUSE <RELATION_ID>
- [ ] DEFER
- [ ] REJECT

---

<a id="sc-rl-0051"></a>
### 073 · SC-RL-0051 · 单晶拉制将多晶硅原料转化为单晶硅锭。

- **ITEM_NUMBER** = 73
- **ITEM_ID** = SC-RL-0051
- **OBJECT_TYPE** = relations
- **DOMAIN** = semiconductor
- **CURRENT_NATIVE_OPERATION** = NEW_RELATION_CANDIDATE
- **CURRENT_STATUS** = REVIEW
- **WHY_IN_HUMAN_PACKET** = R01_A_B_DISAGREEMENT；R02；R04；R05；R08；R13；REVIEWER_UNRESOLVED_HUMAN_REQUIRED
- **RISK_RULES** = R01 A/B实质分歧；R02 低或必要UNKNOWN置信度；R04 实质命题歧义；R05 身份冲突；R08 实质关系歧义；R13 本体/类型映射问题
- **MANDATORY_TRIGGER** = R01_A_B_DISAGREEMENT；R02；R04；R05；R08；R13；REVIEWER_UNRESOLVED_HUMAN_REQUIRED
- **SAMPLE_STATUS** = NOT_SAMPLED
- **SAMPLED_FOR_QUALITY_CONTROL** = false

- **SOURCE_ID / SOURCE_NAME** = SC-PHYS-9E9CEFC24043585C / SRC_8442AD30618C9A2D / Production Processes
Source provenance：SUMCO Corporation；publication=；edition=；as_of=；source SHA256=`9e9cefc24043585c1c5a484340dcf49aa0725b341467942d3d4c34be0da8aee6`。

**CANDIDATE_SUMMARY**

- 命题：单晶拉制将多晶硅原料转化为单晶硅锭。
- 时间类别：categorical_source_scoped
- 终点：Monocrystalline Silicon Ingot
- 范围：SUMCO process transformation
- 起点：Czochralski Crystal Growth
- Candidate target：SC-CN-0026 = Monocrystalline Silicon Ingot；type=Material；frozen status=CREATE；仍须目标自身授权。
- Candidate target：SC-CN-0034 = Czochralski Crystal Growth；type=Technology；frozen status=CREATE；仍须目标自身授权。

**AI REVIEW A**

- recommendation：HUMAN_REQUIRED；native_decision：DEFER
- proposed operation / canonical target：DEFER；起点: SC-CN-0034 [Czochralski Crystal Growth]；终点: SC-CN-0026 [Monocrystalline Silicon Ingot]；范围/说明: SUMCO process transformation
- confidence：LOW
- reason：证据明确 CZ 制造单晶硅锭，但 relation_type 空白；produces/transforms 与 uses 含义不同，不能填入未经许可新边类型。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-3BE221EFD700F965, SC-EV-C7BD218505458FDB
- 必要置信度缺口：outcome_completeness=LOW；relation_causal_explicitness=UNKNOWN

**AI REVIEW B**

- recommendation：HUMAN_REQUIRED；native_decision：DEFER
- proposed operation / canonical target：DEFER；起点: SC-CN-0034 [Czochralski Crystal Growth]；终点: SC-CN-0026 [Monocrystalline Silicon Ingot]；范围/说明: SUMCO process transformation
- confidence：LOW
- reason：证据描述CZ产出单晶硅锭，但关系类型为空；uses会把产物错作输入，part_of也不表达生产，需既有本体可用的输出关系映射。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-3BE221EFD700F965, SC-EV-C7BD218505458FDB
- 必要置信度缺口：entity_resolution_clarity=UNKNOWN；relation_causal_explicitness=LOW；rubric_applicability_clarity=UNKNOWN

**A/B RECONCILIATION**

- frozen status：A_B_DISAGREEMENT
- **DISAGREEMENT_TYPE** = 风险判定分歧 R04；风险判定分歧 R05；风险判定分歧 R08
- **NATIVE_OPERATION_CONFLICT** = false
- R04 实质命题歧义：A=FALSE；B=TRUE。A依据：限定名称/类型/时间/对象后，无会改变本条 outcome 的第二个成立解释。 B依据：关系类型的可选解释会改变完整关系结果：（具体证据与边界见本项该审查者 reason）
- R05 身份冲突：A=FALSE；B=UNKNOWN。A依据：完整 327 节点及 760 别名目录中，未发现本建议产生的身份冲突；明确共享核心者复用。 B依据：对象或关系端点的必要类型尚未统一：（具体证据与边界见本项该审查者 reason）
- R08 实质关系歧义：A=UNKNOWN；B=TRUE。A依据：实质语义有影响，但必要关系/范围判断未定：（具体证据与边界见本项该审查者 reason） B依据：relation_ambiguity=TRUE; materiality=TRUE。关系类型/端点/范围改变具有知识结果影响；（具体证据与边界见本项该审查者 reason）
- relation_ambiguity：A=UNKNOWN；B=TRUE

**EVIDENCE SUMMARY**

- Supporting facts：下列有来源的节选支持本项讨论的对象/命题；支持范围及未解决条件已在上方 A/B reason 中逐项说明。
- SC-EV-3BE221EFD700F965 / SC-PHYS-9E9CEFC24043585C / PDF p.2 / Monocrystalline pulling process / printed p.NOT_KNOWN_OR_UNNUMBERED；excerpt SHA256=`f2a1f5fd0055ec8e3500d40754ed50d70d52dad829317164794bd41622d18e97`。
  > The monocrystalline ingots that make up the silicon wafer are manufactured using high-quality polysilicon as the raw material.
- SC-EV-C7BD218505458FDB / SC-PHYS-9E9CEFC24043585C / PDF p.2 / Monocrystalline pulling process / Flow of CZ process / printed p.NOT_KNOWN_OR_UNNUMBERED；excerpt SHA256=`912c3479df08fa552a86cfa9d75db0cd77828331ac18b369220ec498e0515be2`。
  > The monocrystalline silicon ingots from which silicon wafers are created are manufactured by a technique called the CZ (Czochralski) crystal growth process.
- Conflicting evidence / unresolved scope：上述 A/B 理由和差异列出已记录的冲突或缺口；未补造反证，也未因省略原文而解除冻结风险。

- **SYSTEM_RECOMMENDED_DECISION** = DEFER
推荐理由（非人工裁决）：双方均建议暂缓；风险标签或置信度差异没有补齐身份/类型/证据缺口。优先保留候选等待人工澄清，不强制选择新的目标、关系类型或对象边界。

HUMAN_USER_DECISION = [PENDING]

OPTIONS:

- [ ] CREATE
- [ ] REUSE <RELATION_ID>
- [ ] DEFER
- [ ] REJECT

---

<a id="sc-rl-0052"></a>
### 074 · SC-RL-0052 · SUMCO将硅锭切片形成晶圆。

- **ITEM_NUMBER** = 74
- **ITEM_ID** = SC-RL-0052
- **OBJECT_TYPE** = relations
- **DOMAIN** = semiconductor
- **CURRENT_NATIVE_OPERATION** = NEW_RELATION_CANDIDATE
- **CURRENT_STATUS** = REVIEW
- **WHY_IN_HUMAN_PACKET** = R01_A_B_DISAGREEMENT；R02；R04；R05；R08；R13；REVIEWER_UNRESOLVED_HUMAN_REQUIRED
- **RISK_RULES** = R01 A/B实质分歧；R02 低或必要UNKNOWN置信度；R04 实质命题歧义；R05 身份冲突；R08 实质关系歧义；R13 本体/类型映射问题
- **MANDATORY_TRIGGER** = R01_A_B_DISAGREEMENT；R02；R04；R05；R08；R13；REVIEWER_UNRESOLVED_HUMAN_REQUIRED
- **SAMPLE_STATUS** = NOT_SAMPLED
- **SAMPLED_FOR_QUALITY_CONTROL** = false

- **SOURCE_ID / SOURCE_NAME** = SC-PHYS-9E9CEFC24043585C / SRC_8442AD30618C9A2D / Production Processes
Source provenance：SUMCO Corporation；publication=；edition=；as_of=；source SHA256=`9e9cefc24043585c1c5a484340dcf49aa0725b341467942d3d4c34be0da8aee6`。

**CANDIDATE_SUMMARY**

- 命题：SUMCO将硅锭切片形成晶圆。
- 时间类别：categorical_source_scoped
- 终点：Silicon Wafer
- 范围：SUMCO wafer forming / slicing
- 起点：Wafer Slicing
- Candidate target：SC-CN-0025 = Silicon Wafer；type=Material；frozen status=CREATE；仍须目标自身授权。
- Candidate target：SC-CN-0038 = Wafer Slicing；type=Technology；frozen status=CREATE；仍须目标自身授权。

**AI REVIEW A**

- recommendation：HUMAN_REQUIRED；native_decision：DEFER
- proposed operation / canonical target：DEFER；起点: SC-CN-0038 [Wafer Slicing]；终点: SC-CN-0025 [Silicon Wafer]；范围/说明: SUMCO wafer forming / slicing
- confidence：LOW
- reason：切晶锭形成硅片是工艺输出关系，现有类型未指定；不能用 uses 倒置输出语义或凭空增加 produces。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-44BA70339AC36BAC
- 必要置信度缺口：outcome_completeness=LOW；relation_causal_explicitness=UNKNOWN

**AI REVIEW B**

- recommendation：HUMAN_REQUIRED；native_decision：DEFER
- proposed operation / canonical target：DEFER；起点: SC-CN-0038 [Wafer Slicing]；终点: SC-CN-0025 [Silicon Wafer]；范围/说明: SUMCO wafer forming / slicing
- confidence：LOW
- reason：切锭形成晶圆是产出/转换命题，空类型不能以uses或upstream_of填补；不同映射改变材料流方向与解释。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-44BA70339AC36BAC
- 必要置信度缺口：entity_resolution_clarity=UNKNOWN；relation_causal_explicitness=LOW；rubric_applicability_clarity=UNKNOWN

**A/B RECONCILIATION**

- frozen status：A_B_DISAGREEMENT
- **DISAGREEMENT_TYPE** = 风险判定分歧 R04；风险判定分歧 R05；风险判定分歧 R08
- **NATIVE_OPERATION_CONFLICT** = false
- R04 实质命题歧义：A=FALSE；B=TRUE。A依据：限定名称/类型/时间/对象后，无会改变本条 outcome 的第二个成立解释。 B依据：关系类型的可选解释会改变完整关系结果：（具体证据与边界见本项该审查者 reason）
- R05 身份冲突：A=FALSE；B=UNKNOWN。A依据：完整 327 节点及 760 别名目录中，未发现本建议产生的身份冲突；明确共享核心者复用。 B依据：对象或关系端点的必要类型尚未统一：（具体证据与边界见本项该审查者 reason）
- R08 实质关系歧义：A=UNKNOWN；B=TRUE。A依据：实质语义有影响，但必要关系/范围判断未定：（具体证据与边界见本项该审查者 reason） B依据：relation_ambiguity=TRUE; materiality=TRUE。关系类型/端点/范围改变具有知识结果影响；（具体证据与边界见本项该审查者 reason）
- relation_ambiguity：A=UNKNOWN；B=TRUE

**EVIDENCE SUMMARY**

- Supporting facts：下列有来源的节选支持本项讨论的对象/命题；支持范围及未解决条件已在上方 A/B reason 中逐项说明。
- SC-EV-44BA70339AC36BAC / SC-PHYS-9E9CEFC24043585C / PDF p.3 / Wafer forming process / Slicing / printed p.NOT_KNOWN_OR_UNNUMBERED；excerpt SHA256=`b0459439e180ff79671cd9239d84ea6970682c6a613f324b5ec9d75a8786654b`。
  > Based on the resistivity desired by the customer, the ingot is then cut into slices of around 1mm thickness, using an inner- diameter saw or wire saw, to form the wafers.
- Conflicting evidence / unresolved scope：上述 A/B 理由和差异列出已记录的冲突或缺口；未补造反证，也未因省略原文而解除冻结风险。

- **SYSTEM_RECOMMENDED_DECISION** = DEFER
推荐理由（非人工裁决）：双方均建议暂缓；风险标签或置信度差异没有补齐身份/类型/证据缺口。优先保留候选等待人工澄清，不强制选择新的目标、关系类型或对象边界。

HUMAN_USER_DECISION = [PENDING]

OPTIONS:

- [ ] CREATE
- [ ] REUSE <RELATION_ID>
- [ ] DEFER
- [ ] REJECT

---

<a id="sc-rl-0053"></a>
### 075 · SC-RL-0053 · 验证工程师通过仿真验证设计功能和时序。

- **ITEM_NUMBER** = 75
- **ITEM_ID** = SC-RL-0053
- **OBJECT_TYPE** = relations
- **DOMAIN** = semiconductor
- **CURRENT_NATIVE_OPERATION** = NEW_RELATION_CANDIDATE
- **CURRENT_STATUS** = REVIEW
- **WHY_IN_HUMAN_PACKET** = R01_A_B_DISAGREEMENT；R02；R04；R05；R08；R13；REVIEWER_UNRESOLVED_HUMAN_REQUIRED
- **RISK_RULES** = R01 A/B实质分歧；R02 低或必要UNKNOWN置信度；R04 实质命题歧义；R05 身份冲突；R08 实质关系歧义；R13 本体/类型映射问题
- **MANDATORY_TRIGGER** = R01_A_B_DISAGREEMENT；R02；R04；R05；R08；R13；REVIEWER_UNRESOLVED_HUMAN_REQUIRED
- **SAMPLE_STATUS** = NOT_SAMPLED
- **SAMPLED_FOR_QUALITY_CONTROL** = false

- **SOURCE_ID / SOURCE_NAME** = SC-PHYS-AC86A7FEB4F6ADB5 / SRC_689680B30C113F1B / The Growing Challenge of Semiconductor Design Leadership
Source provenance：Semiconductor Industry Association (SIA) / Boston Consulting Group (BCG)；publication=2022-11；edition=；as_of=2022-11；source SHA256=`ac86a7feb4f6adb52e488086f9281c1f409bd72baecb6bdbed72a0efa3856666`。

**CANDIDATE_SUMMARY**

- 命题：验证工程师通过仿真验证设计功能和时序。
- 时间类别：categorical_source_scoped
- 终点：Semiconductor Design
- 范围：SIA/BCG Exhibit3 design workflow
- 起点：Semiconductor Design Verification
- Candidate target：SC-CN-0020 = Semiconductor Design；type=Technology；frozen status=CREATE；仍须目标自身授权。
- Candidate target：SC-CN-0157 = Semiconductor Design Verification；type=Technology；frozen status=CREATE；仍须目标自身授权。

**AI REVIEW A**

- recommendation：HUMAN_REQUIRED；native_decision：DEFER
- proposed operation / canonical target：DEFER；起点: SC-CN-0157 [Semiconductor Design Verification]；终点: SC-CN-0020 [Semiconductor Design]；范围/说明: SIA/BCG Exhibit3 design workflow
- confidence：LOW
- reason：Figure 3 支持验证处于设计流程、原文支持 verifies 功能，但候选未选择 part_of 或验证对象语义；缺关系类型使完整 outcome 未决。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-A7155A1FD4102457
- 必要置信度缺口：outcome_completeness=LOW；relation_causal_explicitness=UNKNOWN

**AI REVIEW B**

- recommendation：HUMAN_REQUIRED；native_decision：DEFER
- proposed operation / canonical target：DEFER；起点: SC-CN-0157 [Semiconductor Design Verification]；终点: SC-CN-0020 [Semiconductor Design]；范围/说明: SIA/BCG Exhibit3 design workflow
- confidence：LOW
- reason：Exhibit3支持验证属于设计工作，但空类型尚未说明表示阶段包含还是活动关联；需明确工作流包含是否属于既有part_of合同。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-A7155A1FD4102457
- 必要置信度缺口：entity_resolution_clarity=UNKNOWN；relation_causal_explicitness=LOW；rubric_applicability_clarity=UNKNOWN

**A/B RECONCILIATION**

- frozen status：A_B_DISAGREEMENT
- **DISAGREEMENT_TYPE** = 风险判定分歧 R04；风险判定分歧 R05；风险判定分歧 R08
- **NATIVE_OPERATION_CONFLICT** = false
- R04 实质命题歧义：A=FALSE；B=TRUE。A依据：限定名称/类型/时间/对象后，无会改变本条 outcome 的第二个成立解释。 B依据：关系类型的可选解释会改变完整关系结果：（具体证据与边界见本项该审查者 reason）
- R05 身份冲突：A=FALSE；B=UNKNOWN。A依据：完整 327 节点及 760 别名目录中，未发现本建议产生的身份冲突；明确共享核心者复用。 B依据：对象或关系端点的必要类型尚未统一：（具体证据与边界见本项该审查者 reason）
- R08 实质关系歧义：A=UNKNOWN；B=TRUE。A依据：实质语义有影响，但必要关系/范围判断未定：（具体证据与边界见本项该审查者 reason） B依据：relation_ambiguity=TRUE; materiality=TRUE。关系类型/端点/范围改变具有知识结果影响；（具体证据与边界见本项该审查者 reason）
- relation_ambiguity：A=UNKNOWN；B=TRUE

**EVIDENCE SUMMARY**

- Supporting facts：下列有来源的节选支持本项讨论的对象/命题；支持范围及未解决条件已在上方 A/B reason 中逐项说明。
- SC-EV-A7155A1FD4102457 / SC-PHYS-AC86A7FEB4F6ADB5 / PDF p.8 / Design stages / Verification / printed p.6 / Exhibit 3；excerpt SHA256=`dbfa8018449e4100f86a44c0134a2ba1f92186078f4d812d2873b10f85353d98`。
  > Verification engineers verify design functionality and timing through simulation
- Conflicting evidence / unresolved scope：上述 A/B 理由和差异列出已记录的冲突或缺口；未补造反证，也未因省略原文而解除冻结风险。

- **SYSTEM_RECOMMENDED_DECISION** = DEFER
推荐理由（非人工裁决）：双方均建议暂缓；风险标签或置信度差异没有补齐身份/类型/证据缺口。优先保留候选等待人工澄清，不强制选择新的目标、关系类型或对象边界。

HUMAN_USER_DECISION = [PENDING]

OPTIONS:

- [ ] CREATE
- [ ] REUSE <RELATION_ID>
- [ ] DEFER
- [ ] REJECT

---

<a id="sc-rl-0054"></a>
### 076 · SC-RL-0054 · 光刻与刻蚀存在图形转移工序联系，但不据此声称产业链upstream_of。

- **ITEM_NUMBER** = 76
- **ITEM_ID** = SC-RL-0054
- **OBJECT_TYPE** = relations
- **DOMAIN** = semiconductor
- **CURRENT_NATIVE_OPERATION** = NEW_RELATION_CANDIDATE
- **CURRENT_STATUS** = REVIEW
- **WHY_IN_HUMAN_PACKET** = R01_A_B_DISAGREEMENT；R02；R03；R04；R08；R13；REVIEWER_UNRESOLVED_HUMAN_REQUIRED
- **RISK_RULES** = R01 A/B实质分歧；R02 低或必要UNKNOWN置信度；R03 证据缺口；R04 实质命题歧义；R08 实质关系歧义；R13 本体/类型映射问题
- **MANDATORY_TRIGGER** = R01_A_B_DISAGREEMENT；R02；R03；R04；R08；R13；REVIEWER_UNRESOLVED_HUMAN_REQUIRED
- **SAMPLE_STATUS** = NOT_SAMPLED
- **SAMPLED_FOR_QUALITY_CONTROL** = false

- **SOURCE_ID / SOURCE_NAME** = SC-PHYS-87B4665C30781057 / SRC_ADCEE4236B19B5F2 / Six Crucial Steps in Semiconductor Manufacturing
Source provenance：ASML；publication=2023-10-04；edition=；as_of=2023-10-04；source SHA256=`87b4665c3078105792ca70f18964c938976b72f2dcf0d19379b034d5d6f205f9`。

**CANDIDATE_SUMMARY**

- 命题：光刻与刻蚀存在图形转移工序联系，但不据此声称产业链upstream_of。
- 时间类别：categorical_source_scoped
- 终点：Etching
- 范围：ASML wafer patterning workflow
- 起点：Photolithography
- Candidate target：SC-CN-0056 = Photolithography；type=Technology；frozen status=CREATE；仍须目标自身授权。
- Candidate target：SC-CN-0060 = Etching；type=Technology；frozen status=CREATE；仍须目标自身授权。

**AI REVIEW A**

- recommendation：HUMAN_REQUIRED；native_decision：DEFER
- proposed operation / canonical target：DEFER；起点: SC-CN-0056 [Photolithography]；终点: SC-CN-0060 [Etching]；范围/说明: ASML wafer patterning workflow
- confidence：LOW
- reason：两段各述光刻成像与刻蚀，不能单由共现推出完整时序/因果/上下游；relation_type 亦空缺，保留未建边。
- evidence assessment：INSUFFICIENT；Evidence IDs：SC-EV-F4124019AED7B2C6, SC-EV-FD3B14BF5F4E693A
- 必要置信度缺口：evidence_directness=LOW；outcome_completeness=LOW；relation_causal_explicitness=UNKNOWN；unit_scope_completeness=UNKNOWN

**AI REVIEW B**

- recommendation：HUMAN_REQUIRED；native_decision：DEFER
- proposed operation / canonical target：DEFER；起点: SC-CN-0056 [Photolithography]；终点: SC-CN-0060 [Etching]；范围/说明: ASML wafer patterning workflow
- confidence：LOW
- reason：两摘录分别说光刻曝光与刻蚀类型，未完整证明二者所需精确关系；空类型可能被误填工序顺序或产业因果，均需补语义。
- evidence assessment：INSUFFICIENT；Evidence IDs：SC-EV-F4124019AED7B2C6, SC-EV-FD3B14BF5F4E693A
- 必要置信度缺口：evidence_directness=LOW；relation_causal_explicitness=LOW；unit_scope_completeness=LOW

**A/B RECONCILIATION**

- frozen status：A_B_DISAGREEMENT
- **DISAGREEMENT_TYPE** = 风险判定分歧 R04；风险判定分歧 R08；风险判定分歧 R13
- **NATIVE_OPERATION_CONFLICT** = false
- R04 实质命题歧义：A=UNKNOWN；B=TRUE。A依据：必要语义边界缺证，无法排除改变 outcome 的解释：（具体证据与边界见本项该审查者 reason） B依据：关系类型的可选解释会改变完整关系结果：（具体证据与边界见本项该审查者 reason）
- R08 实质关系歧义：A=UNKNOWN；B=TRUE。A依据：实质语义有影响，但必要关系/范围判断未定：（具体证据与边界见本项该审查者 reason） B依据：relation_ambiguity=TRUE; materiality=TRUE。关系类型/端点/范围改变具有知识结果影响；（具体证据与边界见本项该审查者 reason）
- R13 本体/类型映射问题：A=TRUE；B=FALSE。A依据：（具体证据与边界见本项该审查者 reason） B依据：推荐使用现有对象类型及原生允许操作，不新增本体关系或隐式类型强转。
- relation_ambiguity：A=UNKNOWN；B=TRUE

**EVIDENCE SUMMARY**

- Supporting facts：下列有来源的节选支持本项讨论的对象/命题；支持范围及未解决条件已在上方 A/B reason 中逐项说明。
- SC-EV-F4124019AED7B2C6 / SC-PHYS-87B4665C30781057 / PDF p.5 / Etch / printed p.NOT_KNOWN_OR_UNNUMBERED；excerpt SHA256=`02fec2f77dbbe325687492c55adca4474054844b65aa709378a742455cdbae7a`。
  > As with resist, there are two types of etch: 'wet' and 'dry'. Dry etching uses gases to define the exposed pattern on the wafer. Wet etching uses chemical baths to wash the wafer.
- SC-EV-FD3B14BF5F4E693A / SC-PHYS-87B4665C30781057 / PDF p.3 / Lithography / printed p.NOT_KNOWN_OR_UNNUMBERED；excerpt SHA256=`21298139f48fcf329096f3f7d90d4751ff5497922f91c3a74665ff867615183f`。
  > Light is projected onto the wafer through the 'reticle', which holds the blueprint of the pattern to be printed. The system's optics (lenses in a DUV system and mirrors in an EUV system) shrink and focus the pattern onto the resist layer.
- Conflicting evidence / unresolved scope：上述 A/B 理由和差异列出已记录的冲突或缺口；未补造反证，也未因省略原文而解除冻结风险。

- **SYSTEM_RECOMMENDED_DECISION** = DEFER
推荐理由（非人工裁决）：双方均建议暂缓；风险标签或置信度差异没有补齐身份/类型/证据缺口。优先保留候选等待人工澄清，不强制选择新的目标、关系类型或对象边界。

HUMAN_USER_DECISION = [PENDING]

OPTIONS:

- [ ] CREATE
- [ ] REUSE <RELATION_ID>
- [ ] DEFER
- [ ] REJECT

---

## SECTION C — Residual Random Sample

29 items

<a id="sc-al-0002"></a>
### 077 · SC-AL-0002 · EDA

- **ITEM_NUMBER** = 77
- **ITEM_ID** = SC-AL-0002
- **OBJECT_TYPE** = aliases
- **DOMAIN** = semiconductor
- **CURRENT_NATIVE_OPERATION** = UNDECIDED（没有已填写的人类原生决定）
- **CURRENT_STATUS** = REVIEW
- **WHY_IN_HUMAN_PACKET** = Regime B 已冻结的质量抽样；抽样不构成实质风险
- **RISK_RULES** = 无实质必审风险命中
- **MANDATORY_TRIGGER** = NONE
- **SAMPLE_STATUS** = RANDOM_CORE #6
- **SAMPLED_FOR_QUALITY_CONTROL** = true

- **SOURCE_ID / SOURCE_NAME** = SC-PHYS-AC86A7FEB4F6ADB5 / SRC_689680B30C113F1B / The Growing Challenge of Semiconductor Design Leadership
Source provenance：Semiconductor Industry Association (SIA) / Boston Consulting Group (BCG)；publication=2022-11；edition=；as_of=2022-11；source SHA256=`ac86a7feb4f6adb52e488086f9281c1f409bd72baecb6bdbed72a0efa3856666`。
- **SOURCE_ID / SOURCE_NAME** = SC-PHYS-B33C40EBCB5756F7 / SRC_1DD38DEB69830E97 / Strengthening the Global Semiconductor Supply Chain in an Uncertain Era
Source provenance：Semiconductor Industry Association (SIA) / Boston Consulting Group (BCG)；publication=2021-04；edition=；as_of=2021-04；source SHA256=`b33c40ebcb5756f76e887ba2664f97736252e68ba7bfbedc2d628ce2d7cbc08d`。

**CANDIDATE_SUMMARY**

- 别名：EDA
- 已占用所有者：[]
- 提议所有者：SC-CN-0014
- 提议所有者名称：Electronic Design Automation
- Planned native target：NODE_5C930EA3C5BEEEB1 → SC-CN-0014 / Electronic Design Automation / Technology；这是候选映射，不是已存在或获批准的目录对象。
- Candidate target：SC-CN-0014 = Electronic Design Automation；type=Technology；frozen status=CREATE；仍须目标自身授权。

**AI REVIEW A**

- recommendation：ACCEPT_WITH_REVIEW_NOTE；native_decision：ATTACH
- proposed operation / canonical target：ATTACH；目标: SC-CN-0014 [Electronic Design Automation]；范围/说明: SEMICONDUCTOR_SOURCE_SCOPED_ALIAS_RECOMMENDATION; owner remains candidate until separately authorized
- confidence：MEDIUM
- reason：原文直接写 electronic design automation (EDA)，软件语境排除公司类别；挂到待正式创建的 0014 技术候选。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-01DDAE404737D380, SC-EV-6FF6BB080099D1E2

**AI REVIEW B**

- recommendation：ACCEPT_WITH_REVIEW_NOTE；native_decision：ATTACH
- proposed operation / canonical target：ATTACH；目标: SC-CN-0014 [Electronic Design Automation]；范围/说明: ALIAS_IDENTITY_ONLY; EDA -> Electronic Design Automation
- confidence：HIGH
- reason：原文直接给electronic design automation (EDA)，无既有别名持有人；挂接设计自动化技术候选，所有者尚待正式建档授权。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-01DDAE404737D380, SC-EV-6FF6BB080099D1E2

**A/B RECONCILIATION**

- frozen status：A_B_SUBSTANTIVE_AGREEMENT
- 实质分歧：无；措辞、附注或不改变风险路由的置信度差异不改原冻结一致结论。

**EVIDENCE SUMMARY**

- Supporting facts：下列有来源的节选支持本项讨论的对象/命题；支持范围及未解决条件已在上方 A/B reason 中逐项说明。
- SC-EV-01DDAE404737D380 / SC-PHYS-B33C40EBCB5756F7 / PDF p.19 / Electronic design automation (EDA) / printed p.19；excerpt SHA256=`66ae4b3340bfe72c6a698ece2f0f8a1208d9bab4510fde4f2d2bd8c510247296`。
  > At the design stage, electronic design automation (EDA) companies provide sophisticated software and services to support designing semiconductors, including outsourced design of specialized application specific integrated circuits (ASICs).
- SC-EV-6FF6BB080099D1E2 / SC-PHYS-AC86A7FEB4F6ADB5 / PDF p.7 / Design Is Complex and Includes Multiple Different Types of Firms and Activities / printed p.5；excerpt SHA256=`9da9a2377834d759f2de42083bcaa3f4fe5058e8a692338d19c2d69126d80626`。
  > Designers will often use existing, reusable architectural building blocks (core IP) to simplify and accelerate creation of the overall design. In all cases, designers use highly advanced EDA software to automate the design process and ensure that chip designs can be manufactured on distinct and often proprietary fabrication processes.
- Conflicting evidence：冻结 A/B 未报告本限定范围内的未解决实质证据冲突；不等于完整文献已穷尽。

- **SAMPLING_STRATUM** = domain=semiconductor; object_type=aliases; polarity=NOT_PROVIDED; challenge_level=NOT_PROVIDED
- **SAMPLING_REASON** = RANDOM_CORE #6；原种子/原成员不变，无新增风险
- **A_B_AGREE** = true

- **SYSTEM_RECOMMENDED_DECISION** = ACCEPT_OWNER SC-CN-0014
推荐理由（非人工裁决）：双方推荐同一所有者/共享身份，证据与目录边界一致；建议确认该有界映射。若目标仍为 SC-CN 候选，正式写入须等待目标身份的人类授权，不能提前附着或移动别名。

HUMAN_USER_DECISION = [PENDING]

OPTIONS:

- [ ] ACCEPT_OWNER <NODE_ID 或已确认候选 ID>（原生 ATTACH）
- [ ] DEFER
- [ ] REJECT

---

<a id="sc-al-0007"></a>
### 078 · SC-AL-0007 · SiCl4

- **ITEM_NUMBER** = 78
- **ITEM_ID** = SC-AL-0007
- **OBJECT_TYPE** = aliases
- **DOMAIN** = semiconductor
- **CURRENT_NATIVE_OPERATION** = UNDECIDED（没有已填写的人类原生决定）
- **CURRENT_STATUS** = REVIEW
- **WHY_IN_HUMAN_PACKET** = Regime B 已冻结的质量抽样；抽样不构成实质风险
- **RISK_RULES** = 无实质必审风险命中
- **MANDATORY_TRIGGER** = NONE
- **SAMPLE_STATUS** = RANDOM_CORE #15
- **SAMPLED_FOR_QUALITY_CONTROL** = true

- **SOURCE_ID / SOURCE_NAME** = SC-PHYS-9E9CEFC24043585C / SRC_8442AD30618C9A2D / Production Processes
Source provenance：SUMCO Corporation；publication=；edition=；as_of=；source SHA256=`9e9cefc24043585c1c5a484340dcf49aa0725b341467942d3d4c34be0da8aee6`。

**CANDIDATE_SUMMARY**

- 别名：SiCl4
- 已占用所有者：[]
- 提议所有者：SC-CN-0047
- 提议所有者名称：Silicon Tetrachloride
- Planned native target：NODE_58AC04BDBCA28DDB → SC-CN-0047 / Silicon Tetrachloride / Material；这是候选映射，不是已存在或获批准的目录对象。
- Candidate target：SC-CN-0047 = Silicon Tetrachloride；type=Material；frozen status=CREATE；仍须目标自身授权。

**AI REVIEW A**

- recommendation：ACCEPT_WITH_REVIEW_NOTE；native_decision：ATTACH
- proposed operation / canonical target：ATTACH；目标: SC-CN-0047 [Silicon Tetrachloride]；范围/说明: SEMICONDUCTOR_SOURCE_SCOPED_ALIAS_RECOMMENDATION; owner remains candidate until separately authorized
- confidence：MEDIUM
- reason：silicon tetrachloride (SiCl4) 直接同句展开，准确挂到 0047 材料候选。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-574D5C0F2C499255

**AI REVIEW B**

- recommendation：ACCEPT_WITH_REVIEW_NOTE；native_decision：ATTACH
- proposed operation / canonical target：ATTACH；目标: SC-CN-0047 [Silicon Tetrachloride]；范围/说明: ALIAS_IDENTITY_ONLY; SiCl4 -> Silicon Tetrachloride
- confidence：HIGH
- reason：silicon tetrachloride (SiCl4)直接同位，化学式唯一指向该材料候选；目录无竞争持有人。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-574D5C0F2C499255

**A/B RECONCILIATION**

- frozen status：A_B_SUBSTANTIVE_AGREEMENT
- 实质分歧：无；措辞、附注或不改变风险路由的置信度差异不改原冻结一致结论。

**EVIDENCE SUMMARY**

- Supporting facts：下列有来源的节选支持本项讨论的对象/命题；支持范围及未解决条件已在上方 A/B reason 中逐项说明。
- SC-EV-574D5C0F2C499255 / SC-PHYS-9E9CEFC24043585C / PDF p.5 / Specialized processing / Epitaxial Wafers / printed p.NOT_KNOWN_OR_UNNUMBERED；excerpt SHA256=`05a7510d15a9807f50dcd0d6dee327bf1eb6a76b6d21d1371ceeaa903e645f76`。
  > Polished wafers are heated to around 1200℃ in an epitaxial furnace. Vaporized silicon tetrachloride (SiCl4) and trichlorosilane (SiHCl3) are circulated in the furnace, causing vapor phase (epitaxial) growth of a monocrystalline silicon film on the wafer surface.
- Conflicting evidence：冻结 A/B 未报告本限定范围内的未解决实质证据冲突；不等于完整文献已穷尽。

- **SAMPLING_STRATUM** = domain=semiconductor; object_type=aliases; polarity=NOT_PROVIDED; challenge_level=NOT_PROVIDED
- **SAMPLING_REASON** = RANDOM_CORE #15；原种子/原成员不变，无新增风险
- **A_B_AGREE** = true

- **SYSTEM_RECOMMENDED_DECISION** = ACCEPT_OWNER SC-CN-0047
推荐理由（非人工裁决）：双方推荐同一所有者/共享身份，证据与目录边界一致；建议确认该有界映射。若目标仍为 SC-CN 候选，正式写入须等待目标身份的人类授权，不能提前附着或移动别名。

HUMAN_USER_DECISION = [PENDING]

OPTIONS:

- [ ] ACCEPT_OWNER <NODE_ID 或已确认候选 ID>（原生 ATTACH）
- [ ] DEFER
- [ ] REJECT

---

<a id="sc-al-0020"></a>
### 079 · SC-AL-0020 · DSA

- **ITEM_NUMBER** = 79
- **ITEM_ID** = SC-AL-0020
- **OBJECT_TYPE** = aliases
- **DOMAIN** = semiconductor
- **CURRENT_NATIVE_OPERATION** = UNDECIDED（没有已填写的人类原生决定）
- **CURRENT_STATUS** = REVIEW
- **WHY_IN_HUMAN_PACKET** = Regime B 已冻结的质量抽样；抽样不构成实质风险
- **RISK_RULES** = 无实质必审风险命中
- **MANDATORY_TRIGGER** = NONE
- **SAMPLE_STATUS** = RANDOM_CORE #7
- **SAMPLED_FOR_QUALITY_CONTROL** = true

- **SOURCE_ID / SOURCE_NAME** = SC-PHYS-318D85A127B5B6DF / SRC_FFD94DB31A0E9C0A / 2025 IRDS — Lithography and Patterning
Source provenance：IEEE International Roadmap for Devices and Systems (IRDS)；publication=；edition=2025；as_of=2025；source SHA256=`318d85a127b5b6dfa7b3c1330ae20b18d63660a1fa8c8bdfdd7b478844e145ed`。

**CANDIDATE_SUMMARY**

- 别名：DSA
- 已占用所有者：[]
- 提议所有者：SC-CN-0111
- 提议所有者名称：Directed Self-Assembly
- Planned native target：NODE_5964807E6416D097 → SC-CN-0111 / Directed Self-Assembly / Technology；这是候选映射，不是已存在或获批准的目录对象。
- Candidate target：SC-CN-0111 = Directed Self-Assembly；type=Technology；frozen status=CREATE；仍须目标自身授权。

**AI REVIEW A**

- recommendation：ACCEPT_WITH_REVIEW_NOTE；native_decision：ATTACH
- proposed operation / canonical target：ATTACH；目标: SC-CN-0111 [Directed Self-Assembly]；范围/说明: SEMICONDUCTOR_SOURCE_SCOPED_ALIAS_RECOMMENDATION; owner remains candidate until separately authorized
- confidence：MEDIUM
- reason：DSA (directed self-assembly) 明确展开，owner 0111 的技术身份与潜在效果命题分离。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-B8DFBCC7175C23E6

**AI REVIEW B**

- recommendation：ACCEPT_WITH_REVIEW_NOTE；native_decision：ATTACH
- proposed operation / canonical target：ATTACH；目标: SC-CN-0111 [Directed Self-Assembly]；范围/说明: ALIAS_IDENTITY_ONLY; DSA -> Directed Self-Assembly
- confidence：HIGH
- reason：DSA (directed self-assembly)明确展开；效果潜在性不妨碍技术缩写身份，挂接技术候选。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-B8DFBCC7175C23E6

**A/B RECONCILIATION**

- frozen status：A_B_SUBSTANTIVE_AGREEMENT
- 实质分歧：无；措辞、附注或不改变风险路由的置信度差异不改原冻结一致结论。

**EVIDENCE SUMMARY**

- Supporting facts：下列有来源的节选支持本项讨论的对象/命题；支持范围及未解决条件已在上方 A/B reason 中逐项说明。
- SC-EV-B8DFBCC7175C23E6 / SC-PHYS-318D85A127B5B6DF / PDF p.20 / Patterning alternatives / DSA / printed p.15；excerpt SHA256=`cc3617267c9c48e986aa9bfdb48b535c64efabd62b87d490268d1ae018606a40`。
  > DSA (directed self-assembly) pattern rectification is potentially a way to get rid of stochastic defects and reduce LER while exposing at a relatively low EUV dose.
- Conflicting evidence：冻结 A/B 未报告本限定范围内的未解决实质证据冲突；不等于完整文献已穷尽。

- **SAMPLING_STRATUM** = domain=semiconductor; object_type=aliases; polarity=NOT_PROVIDED; challenge_level=NOT_PROVIDED
- **SAMPLING_REASON** = RANDOM_CORE #7；原种子/原成员不变，无新增风险
- **A_B_AGREE** = true

- **SYSTEM_RECOMMENDED_DECISION** = ACCEPT_OWNER SC-CN-0111
推荐理由（非人工裁决）：双方推荐同一所有者/共享身份，证据与目录边界一致；建议确认该有界映射。若目标仍为 SC-CN 候选，正式写入须等待目标身份的人类授权，不能提前附着或移动别名。

HUMAN_USER_DECISION = [PENDING]

OPTIONS:

- [ ] ACCEPT_OWNER <NODE_ID 或已确认候选 ID>（原生 ATTACH）
- [ ] DEFER
- [ ] REJECT

---

<a id="sc-cl-0003"></a>
### 080 · SC-CL-0003 · 2025版IRDS称，所述0.33NA EUV生产中的多数EUV层使用化学放大型材料。

- **ITEM_NUMBER** = 80
- **ITEM_ID** = SC-CL-0003
- **OBJECT_TYPE** = claims
- **DOMAIN** = semiconductor
- **CURRENT_NATIVE_OPERATION** = UNDECIDED（没有已填写的人类原生决定）
- **CURRENT_STATUS** = ACCEPTABLE
- **WHY_IN_HUMAN_PACKET** = Regime B 已冻结的质量抽样；抽样不构成实质风险
- **RISK_RULES** = 无实质必审风险命中
- **MANDATORY_TRIGGER** = NONE
- **SAMPLE_STATUS** = RANDOM_CORE #18
- **SAMPLED_FOR_QUALITY_CONTROL** = true

- **SOURCE_ID / SOURCE_NAME** = SC-PHYS-318D85A127B5B6DF / SRC_FFD94DB31A0E9C0A / 2025 IRDS — Lithography and Patterning
Source provenance：IEEE International Roadmap for Devices and Systems (IRDS)；publication=；edition=2025；as_of=2025；source SHA256=`318d85a127b5b6dfa7b3c1330ae20b18d63660a1fa8c8bdfdd7b478844e145ed`。

**CANDIDATE_SUMMARY**

- 主体：Chemically Amplified Resist
- 主体 ID：NODE_2C87D1F62B1F2224
- 事实时间：2025
- 命题：2025版IRDS称，所述0.33NA EUV生产中的多数EUV层使用化学放大型材料。
- 性质：fact
- 时间类别：historical_as_reported
- 来源时点：2025
- 范围：IRDS source-as-of; not 2026 present-tense confirmation
- Candidate target：SC-CN-0109 = Chemically Amplified Resist；type=Material；frozen status=CREATE；仍须目标自身授权。

**AI REVIEW A**

- recommendation：ACCEPT；native_decision：KEEP
- proposed operation / canonical target：KEEP；目标: SC-CN-0109 [Chemically Amplified Resist]；范围/说明: IRDS source-as-of; not 2026 present-tense confirmation
- confidence：HIGH
- reason：most EUV levels 对应多数层且限定 0.33NA、2025 来源，未推广到现时普遍采用。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-2CCA00E79D91DD12

**AI REVIEW B**

- recommendation：ACCEPT；native_decision：KEEP
- proposed operation / canonical target：KEEP；目标: SC-CN-0109 [Chemically Amplified Resist]；范围/说明: IRDS source-as-of; not 2026 present-tense confirmation
- confidence：HIGH
- reason：来源明确0.33NA量产多数EUV层使用化学放大型材料，中文保留多数/2025来源口径，不宣称所有层或2026现状。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-2CCA00E79D91DD12

**A/B RECONCILIATION**

- frozen status：A_B_SUBSTANTIVE_AGREEMENT
- 实质分歧：无；措辞、附注或不改变风险路由的置信度差异不改原冻结一致结论。

**EVIDENCE SUMMARY**

- Supporting facts：下列有来源的节选支持本项讨论的对象/命题；支持范围及未解决条件已在上方 A/B reason 中逐项说明。
- SC-EV-2CCA00E79D91DD12 / SC-PHYS-318D85A127B5B6DF / PDF p.17 / EUV Resist Materials / printed p.12；excerpt SHA256=`bc095b935738e34224f2f6e6414ede5e7910cf5ebec73265c08f007fc60c14aa`。
  > Currently, the EUV used in manufacturing is at 0.33NA and chemically amplified materials are in use for most EUV levels in production and metal oxide resists are used for some memory levels.
- Conflicting evidence：冻结 A/B 未报告本限定范围内的未解决实质证据冲突；不等于完整文献已穷尽。

- **SAMPLING_STRATUM** = domain=semiconductor; object_type=claims; polarity=NOT_PROVIDED; challenge_level=NOT_PROVIDED
- **SAMPLING_REASON** = RANDOM_CORE #18；原种子/原成员不变，无新增风险
- **A_B_AGREE** = true

- **SYSTEM_RECOMMENDED_DECISION** = KEEP
推荐理由（非人工裁决）：双方实质一致且没有剩余实质必审风险；建议按来源限定接受共同原生操作。抽样身份本身不新增风险，正式写入仍须满足既有授权流程。

HUMAN_USER_DECISION = [PENDING]

OPTIONS:

- [ ] KEEP
- [ ] DROP
- [ ] KEEP_NEEDS_REVIEW

---

<a id="sc-cl-0014"></a>
### 081 · SC-CL-0014 · UCIe 3.0白皮书描述以数据生成和消费相同速率运行链路来支持连续传输协议。

- **ITEM_NUMBER** = 81
- **ITEM_ID** = SC-CL-0014
- **OBJECT_TYPE** = claims
- **DOMAIN** = semiconductor
- **CURRENT_NATIVE_OPERATION** = UNDECIDED（没有已填写的人类原生决定）
- **CURRENT_STATUS** = ACCEPTABLE
- **WHY_IN_HUMAN_PACKET** = Regime B 已冻结的质量抽样；抽样不构成实质风险
- **RISK_RULES** = 无实质必审风险命中
- **MANDATORY_TRIGGER** = NONE
- **SAMPLE_STATUS** = RANDOM_CORE #20
- **SAMPLED_FOR_QUALITY_CONTROL** = true

- **SOURCE_ID / SOURCE_NAME** = SC-PHYS-86EB13C30D0C5406 / F017 / UCIe 3.0 Specification White Paper
Source provenance：UCIe Consortium；publication=；edition=；as_of=；source SHA256=`86eb13c30d0c5406b647a50107bc5c82ddfa5b4cf7aa36ab959cbe50d8a1ef19`。

**CANDIDATE_SUMMARY**

- 主体：Universal Chiplet Interconnect Express
- 主体 ID：NODE_20260817_2E3D3BE2
- 命题：UCIe 3.0白皮书描述以数据生成和消费相同速率运行链路来支持连续传输协议。
- 性质：fact
- 时间类别：specification_capability
- 范围：White paper describing specification version 3.0; no normative-clause or deployed-product claim
- Canonical state：NODE_20260817_2E3D3BE2 = Universal Chiplet Interconnect Express；type=Standard；status=active。

**AI REVIEW A**

- recommendation：ACCEPT_WITH_REVIEW_NOTE；native_decision：KEEP
- proposed operation / canonical target：KEEP；目标: NODE_20260817_2E3D3BE2 [Universal Chiplet Interconnect Express]；范围/说明: White paper describing specification version 3.0; no normative-clause or deployed-product claim
- confidence：MEDIUM
- reason：原文以链路速率匹配生成/消费速率支持 continuous transmission，版本 3.0 限定完整；缺发布日期不影响版本能力描述。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-56A84BBF8CA0648F

**AI REVIEW B**

- recommendation：ACCEPT_WITH_REVIEW_NOTE；native_decision：KEEP
- proposed operation / canonical target：KEEP；目标: NODE_20260817_2E3D3BE2 [Universal Chiplet Interconnect Express]；范围/说明: White paper describing specification version 3.0; no normative-clause or deployed-product claim
- confidence：MEDIUM
- reason：白皮书直接描述3.0连续传输及同速率运行，标准版本已锚定；无出版日期不影响此版本能力命题，不声称实装。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-56A84BBF8CA0648F

**A/B RECONCILIATION**

- frozen status：A_B_SUBSTANTIVE_AGREEMENT
- 实质分歧：无；措辞、附注或不改变风险路由的置信度差异不改原冻结一致结论。

**EVIDENCE SUMMARY**

- Supporting facts：下列有来源的节选支持本项讨论的对象/命题；支持范围及未解决条件已在上方 A/B reason 中逐项说明。
- SC-EV-56A84BBF8CA0648F / SC-PHYS-86EB13C30D0C5406 / PDF p.3 / Support for Continuous Transmission Protocols / printed p.NOT_KNOWN_OR_UNNUMBERED；excerpt SHA256=`1637022dad6a5c7b777a7e1ed784de7eb66eb2666bb3e227fa66b66def0f06b2`。
  > UCIe 3.0 supports continuous transmission protocols by running the link at the same data rate as data generation and consumption.
- Conflicting evidence：冻结 A/B 未报告本限定范围内的未解决实质证据冲突；不等于完整文献已穷尽。

- **SAMPLING_STRATUM** = domain=semiconductor; object_type=claims; polarity=NOT_PROVIDED; challenge_level=NOT_PROVIDED
- **SAMPLING_REASON** = RANDOM_CORE #20；原种子/原成员不变，无新增风险
- **A_B_AGREE** = true

- **SYSTEM_RECOMMENDED_DECISION** = KEEP
推荐理由（非人工裁决）：双方实质一致且没有剩余实质必审风险；建议按来源限定接受共同原生操作。抽样身份本身不新增风险，正式写入仍须满足既有授权流程。

HUMAN_USER_DECISION = [PENDING]

OPTIONS:

- [ ] KEEP
- [ ] DROP
- [ ] KEEP_NEEDS_REVIEW

---

<a id="sc-cn-0013"></a>
### 082 · SC-CN-0013 · Field Programmable Gate Array

- **ITEM_NUMBER** = 82
- **ITEM_ID** = SC-CN-0013
- **OBJECT_TYPE** = nodes
- **DOMAIN** = 00_industry_structure
- **CURRENT_NATIVE_OPERATION** = CREATE NODE_84012FFB7246DCE0
- **CURRENT_STATUS** = CREATE
- **WHY_IN_HUMAN_PACKET** = Regime B 已冻结的质量抽样；抽样不构成实质风险
- **RISK_RULES** = 无实质必审风险命中
- **MANDATORY_TRIGGER** = NONE
- **SAMPLE_STATUS** = COVERAGE_SUPPLEMENT domain=00_industry_structure
- **SAMPLED_FOR_QUALITY_CONTROL** = true

- **SOURCE_ID / SOURCE_NAME** = SC-PHYS-B33C40EBCB5756F7 / SRC_1DD38DEB69830E97 / Strengthening the Global Semiconductor Supply Chain in an Uncertain Era
Source provenance：Semiconductor Industry Association (SIA) / Boston Consulting Group (BCG)；publication=2021-04；edition=；as_of=2021-04；source SHA256=`b33c40ebcb5756f76e887ba2664f97736252e68ba7bfbedc2d628ce2d7cbc08d`。

**CANDIDATE_SUMMARY**

- Node 类型：Product
- 名称：Field Programmable Gate Array
- 已有身份：NODE_84012FFB7246DCE0
- 边界说明：Source支持可复用的持久研究对象，未命中现有规范名或已登记别名。
- Planned native target：NODE_84012FFB7246DCE0 → SC-CN-0013 / Field Programmable Gate Array / Product；这是候选映射，不是已存在或获批准的目录对象。

**AI REVIEW A**

- recommendation：ACCEPT；native_decision：CREATE
- proposed operation / canonical target：CREATE；范围/说明: IDENTITY_RECOMMENDATION_ONLY; Field Programmable Gate Array / Product; no canonical mutation
- confidence：HIGH
- reason：原文完整拼出 FPGA 并描述可编程逻辑，区别预定功能 ASIC，catalog 没有等价产品节点。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-A2F59CE26FF7C78A

**AI REVIEW B**

- recommendation：ACCEPT；native_decision：CREATE
- proposed operation / canonical target：CREATE；范围/说明: IDENTITY_ONLY; 00_industry_structure; Field Programmable Gate Array; Product
- confidence：HIGH
- reason：原文全称及FPGA缩写对应明确，用户可编程逻辑器件与固定AI ASIC不同；目录无相同身份。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-A2F59CE26FF7C78A

**A/B RECONCILIATION**

- frozen status：A_B_SUBSTANTIVE_AGREEMENT
- 实质分歧：无；措辞、附注或不改变风险路由的置信度差异不改原冻结一致结论。

**EVIDENCE SUMMARY**

- Supporting facts：下列有来源的节选支持本项讨论的对象/命题；支持范围及未解决条件已在上方 A/B reason 中逐项说明。
- SC-EV-A2F59CE26FF7C78A / SC-PHYS-B33C40EBCB5756F7 / PDF p.9 / Logic / printed p.9；excerpt SHA256=`6b7eb4ae7edc3a82a578bb0278e190dc15c6891915bb537aaeeceb7b86c2ba78`。
  > General purpose logic products such as Field Programmable Gate Arrays (FPGAs) do not contain any pre-fixed instructions, allowing a user to program custom logic operations.
- Conflicting evidence：冻结 A/B 未报告本限定范围内的未解决实质证据冲突；不等于完整文献已穷尽。

- **SAMPLING_STRATUM** = domain=00_industry_structure; object_type=nodes; polarity=NOT_PROVIDED; challenge_level=NOT_PROVIDED
- **SAMPLING_REASON** = COVERAGE_SUPPLEMENT domain=00_industry_structure；原种子/原成员不变，无新增风险
- **A_B_AGREE** = true

- **SYSTEM_RECOMMENDED_DECISION** = CREATE
推荐理由（非人工裁决）：双方实质一致且没有剩余实质必审风险；建议按来源限定接受共同原生操作。抽样身份本身不新增风险，正式写入仍须满足既有授权流程。

HUMAN_USER_DECISION = [PENDING]

OPTIONS:

- [ ] CREATE
- [ ] REUSE <NODE_ID>
- [ ] DEFER
- [ ] REJECT

---

<a id="sc-cn-0023"></a>
### 083 · SC-CN-0023 · Design Reference Platform

- **ITEM_NUMBER** = 83
- **ITEM_ID** = SC-CN-0023
- **OBJECT_TYPE** = nodes
- **DOMAIN** = 01_design_enablement
- **CURRENT_NATIVE_OPERATION** = UNDECIDED（没有已填写的人类原生决定）
- **CURRENT_STATUS** = REVIEW
- **WHY_IN_HUMAN_PACKET** = Regime B 已冻结的质量抽样；抽样不构成实质风险
- **RISK_RULES** = 无实质必审风险命中
- **MANDATORY_TRIGGER** = NONE
- **SAMPLE_STATUS** = RANDOM_CORE #24
- **SAMPLED_FOR_QUALITY_CONTROL** = true

- **SOURCE_ID / SOURCE_NAME** = SC-PHYS-AC86A7FEB4F6ADB5 / SRC_689680B30C113F1B / The Growing Challenge of Semiconductor Design Leadership
Source provenance：Semiconductor Industry Association (SIA) / Boston Consulting Group (BCG)；publication=2022-11；edition=；as_of=2022-11；source SHA256=`ac86a7feb4f6adb52e488086f9281c1f409bd72baecb6bdbed72a0efa3856666`。

**CANDIDATE_SUMMARY**

- Node 类型：Product
- 名称：Design Reference Platform
- 边界说明：工具+IP设计使能组合与一般软硬件平台的边界需审。

**AI REVIEW A**

- recommendation：ACCEPT；native_decision：CREATE
- proposed operation / canonical target：CREATE；范围/说明: IDENTITY_RECOMMENDATION_ONLY; Design Reference Platform / Product; no canonical mutation
- confidence：HIGH
- reason：Reference Platforms 原文明确为组合 EDA 与 IP 的设计系统，限定 Design 足以区别通用平台，catalog 无同义对象，可作局部 Product。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-FC514885026E522F

**AI REVIEW B**

- recommendation：ACCEPT_WITH_REVIEW_NOTE；native_decision：CREATE
- proposed operation / canonical target：CREATE；范围/说明: IDENTITY_ONLY; 01_design_enablement; Design Reference Platform; Product
- confidence：MEDIUM
- reason：Reference Platforms被定义为组合EDA/IP以优化PPA的系统，可作有界设计交付平台Product；不泛化为任意硬软件平台。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-FC514885026E522F

**A/B RECONCILIATION**

- frozen status：A_B_SUBSTANTIVE_AGREEMENT
- 实质分歧：无；措辞、附注或不改变风险路由的置信度差异不改原冻结一致结论。

**EVIDENCE SUMMARY**

- Supporting facts：下列有来源的节选支持本项讨论的对象/命题；支持范围及未解决条件已在上方 A/B reason 中逐项说明。
- SC-EV-FC514885026E522F / SC-PHYS-AC86A7FEB4F6ADB5 / PDF p.27 / Electronic Design Automation (EDA) and Core IP / printed p.25；excerpt SHA256=`5164e1108bd03aa147359d8424f4ac243788199e04c21e11920cbe79ab45aa71`。
  > Reference Platforms. These systems carefully combine EDA tools and IP to automate and optimize a design for power, performance and area (cost).
- Conflicting evidence：冻结 A/B 未报告本限定范围内的未解决实质证据冲突；不等于完整文献已穷尽。

- **SAMPLING_STRATUM** = domain=01_design_enablement; object_type=nodes; polarity=NOT_PROVIDED; challenge_level=NOT_PROVIDED
- **SAMPLING_REASON** = RANDOM_CORE #24；原种子/原成员不变，无新增风险
- **A_B_AGREE** = true

- **SYSTEM_RECOMMENDED_DECISION** = CREATE
推荐理由（非人工裁决）：双方实质一致且没有剩余实质必审风险；建议按来源限定接受共同原生操作。抽样身份本身不新增风险，正式写入仍须满足既有授权流程。

HUMAN_USER_DECISION = [PENDING]

OPTIONS:

- [ ] CREATE
- [ ] REUSE <NODE_ID>
- [ ] DEFER
- [ ] REJECT

---

<a id="sc-cn-0034"></a>
### 084 · SC-CN-0034 · Czochralski Crystal Growth

- **ITEM_NUMBER** = 84
- **ITEM_ID** = SC-CN-0034
- **OBJECT_TYPE** = nodes
- **DOMAIN** = 02_wafer_materials
- **CURRENT_NATIVE_OPERATION** = CREATE NODE_E06758E691974EB4
- **CURRENT_STATUS** = CREATE
- **WHY_IN_HUMAN_PACKET** = Regime B 已冻结的质量抽样；抽样不构成实质风险
- **RISK_RULES** = 无实质必审风险命中
- **MANDATORY_TRIGGER** = NONE
- **SAMPLE_STATUS** = RANDOM_CORE #11
- **SAMPLED_FOR_QUALITY_CONTROL** = true

- **SOURCE_ID / SOURCE_NAME** = SC-PHYS-9E9CEFC24043585C / SRC_8442AD30618C9A2D / Production Processes
Source provenance：SUMCO Corporation；publication=；edition=；as_of=；source SHA256=`9e9cefc24043585c1c5a484340dcf49aa0725b341467942d3d4c34be0da8aee6`。

**CANDIDATE_SUMMARY**

- Node 类型：Technology
- 名称：Czochralski Crystal Growth
- 已有身份：NODE_E06758E691974EB4
- 边界说明：晶体生长工艺，不是晶体生长设备。
- Planned native target：NODE_E06758E691974EB4 → SC-CN-0034 / Czochralski Crystal Growth / Technology；这是候选映射，不是已存在或获批准的目录对象。

**AI REVIEW A**

- recommendation：ACCEPT；native_decision：CREATE
- proposed operation / canonical target：CREATE；范围/说明: IDENTITY_RECOMMENDATION_ONLY; Czochralski Crystal Growth / Technology; no canonical mutation
- confidence：HIGH
- reason：原文完整给出 CZ/Czochralski 晶体生长方法，流程技术不同于炉或晶锭材料，catalog 无同义 Technology。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-C7BD218505458FDB, SC-EV-1811D226786D163F

**AI REVIEW B**

- recommendation：ACCEPT；native_decision：CREATE
- proposed operation / canonical target：CREATE；范围/说明: IDENTITY_ONLY; 02_wafer_materials; Czochralski Crystal Growth; Technology
- confidence：HIGH
- reason：CZ全称及单晶生长流程明确；与晶锭材料、坩埚设备不同，可建立局部工艺Technology。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-C7BD218505458FDB, SC-EV-1811D226786D163F

**A/B RECONCILIATION**

- frozen status：A_B_SUBSTANTIVE_AGREEMENT
- 实质分歧：无；措辞、附注或不改变风险路由的置信度差异不改原冻结一致结论。

**EVIDENCE SUMMARY**

- Supporting facts：下列有来源的节选支持本项讨论的对象/命题；支持范围及未解决条件已在上方 A/B reason 中逐项说明。
- SC-EV-1811D226786D163F / SC-PHYS-9E9CEFC24043585C / PDF p.2 / Flow of CZ process / printed p.NOT_KNOWN_OR_UNNUMBERED；excerpt SHA256=`014615fff3d822d511b8420e52cb198218ff0c9777d64741ed7f5b226d6ceb9c`。
  > Polysilicon purified until the metal impurities are no more than a few parts per billion (ppb) is put into a quartz crucible along with boron (B) and phosphorous (P), and melted at a temperature of around 1420℃.
- SC-EV-C7BD218505458FDB / SC-PHYS-9E9CEFC24043585C / PDF p.2 / Monocrystalline pulling process / Flow of CZ process / printed p.NOT_KNOWN_OR_UNNUMBERED；excerpt SHA256=`912c3479df08fa552a86cfa9d75db0cd77828331ac18b369220ec498e0515be2`。
  > The monocrystalline silicon ingots from which silicon wafers are created are manufactured by a technique called the CZ (Czochralski) crystal growth process.
- Conflicting evidence：冻结 A/B 未报告本限定范围内的未解决实质证据冲突；不等于完整文献已穷尽。

- **SAMPLING_STRATUM** = domain=02_wafer_materials; object_type=nodes; polarity=NOT_PROVIDED; challenge_level=NOT_PROVIDED
- **SAMPLING_REASON** = RANDOM_CORE #11；原种子/原成员不变，无新增风险
- **A_B_AGREE** = true

- **SYSTEM_RECOMMENDED_DECISION** = CREATE
推荐理由（非人工裁决）：双方实质一致且没有剩余实质必审风险；建议按来源限定接受共同原生操作。抽样身份本身不新增风险，正式写入仍须满足既有授权流程。

HUMAN_USER_DECISION = [PENDING]

OPTIONS:

- [ ] CREATE
- [ ] REUSE <NODE_ID>
- [ ] DEFER
- [ ] REJECT

---

<a id="sc-cn-0046"></a>
### 085 · SC-CN-0046 · Epitaxial Furnace

- **ITEM_NUMBER** = 85
- **ITEM_ID** = SC-CN-0046
- **OBJECT_TYPE** = nodes
- **DOMAIN** = 02_wafer_materials
- **CURRENT_NATIVE_OPERATION** = CREATE NODE_008076BCD6DD42FC
- **CURRENT_STATUS** = CREATE
- **WHY_IN_HUMAN_PACKET** = Regime B 已冻结的质量抽样；抽样不构成实质风险
- **RISK_RULES** = 无实质必审风险命中
- **MANDATORY_TRIGGER** = NONE
- **SAMPLE_STATUS** = RANDOM_CORE #12
- **SAMPLED_FOR_QUALITY_CONTROL** = true

- **SOURCE_ID / SOURCE_NAME** = SC-PHYS-9E9CEFC24043585C / SRC_8442AD30618C9A2D / Production Processes
Source provenance：SUMCO Corporation；publication=；edition=；as_of=；source SHA256=`9e9cefc24043585c1c5a484340dcf49aa0725b341467942d3d4c34be0da8aee6`。

**CANDIDATE_SUMMARY**

- Node 类型：Equipment
- 名称：Epitaxial Furnace
- 已有身份：NODE_008076BCD6DD42FC
- 边界说明：Source支持可复用的持久研究对象，未命中现有规范名或已登记别名。
- Planned native target：NODE_008076BCD6DD42FC → SC-CN-0046 / Epitaxial Furnace / Equipment；这是候选映射，不是已存在或获批准的目录对象。

**AI REVIEW A**

- recommendation：ACCEPT；native_decision：CREATE
- proposed operation / canonical target：CREATE；范围/说明: IDENTITY_RECOMMENDATION_ONLY; Epitaxial Furnace / Equipment; no canonical mutation
- confidence：HIGH
- reason：原文显式 epitaxial furnace 加热硅片并循环前驱体，是局部 Equipment；与化合物 MOCVD 设备范围不同。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-574D5C0F2C499255

**AI REVIEW B**

- recommendation：ACCEPT；native_decision：CREATE
- proposed operation / canonical target：CREATE；范围/说明: IDENTITY_ONLY; 02_wafer_materials; Epitaxial Furnace; Equipment
- confidence：HIGH
- reason：epitaxial furnace在硅外延工序中被直接指明；不把化合物半导体MOCVD设备当同一通用炉。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-574D5C0F2C499255

**A/B RECONCILIATION**

- frozen status：A_B_SUBSTANTIVE_AGREEMENT
- 实质分歧：无；措辞、附注或不改变风险路由的置信度差异不改原冻结一致结论。

**EVIDENCE SUMMARY**

- Supporting facts：下列有来源的节选支持本项讨论的对象/命题；支持范围及未解决条件已在上方 A/B reason 中逐项说明。
- SC-EV-574D5C0F2C499255 / SC-PHYS-9E9CEFC24043585C / PDF p.5 / Specialized processing / Epitaxial Wafers / printed p.NOT_KNOWN_OR_UNNUMBERED；excerpt SHA256=`05a7510d15a9807f50dcd0d6dee327bf1eb6a76b6d21d1371ceeaa903e645f76`。
  > Polished wafers are heated to around 1200℃ in an epitaxial furnace. Vaporized silicon tetrachloride (SiCl4) and trichlorosilane (SiHCl3) are circulated in the furnace, causing vapor phase (epitaxial) growth of a monocrystalline silicon film on the wafer surface.
- Conflicting evidence：冻结 A/B 未报告本限定范围内的未解决实质证据冲突；不等于完整文献已穷尽。

- **SAMPLING_STRATUM** = domain=02_wafer_materials; object_type=nodes; polarity=NOT_PROVIDED; challenge_level=NOT_PROVIDED
- **SAMPLING_REASON** = RANDOM_CORE #12；原种子/原成员不变，无新增风险
- **A_B_AGREE** = true

- **SYSTEM_RECOMMENDED_DECISION** = CREATE
推荐理由（非人工裁决）：双方实质一致且没有剩余实质必审风险；建议按来源限定接受共同原生操作。抽样身份本身不新增风险，正式写入仍须满足既有授权流程。

HUMAN_USER_DECISION = [PENDING]

OPTIONS:

- [ ] CREATE
- [ ] REUSE <NODE_ID>
- [ ] DEFER
- [ ] REJECT

---

<a id="sc-cn-0073"></a>
### 086 · SC-CN-0073 · CMP Slurry

- **ITEM_NUMBER** = 86
- **ITEM_ID** = SC-CN-0073
- **OBJECT_TYPE** = nodes
- **DOMAIN** = 03_fab_process_equipment
- **CURRENT_NATIVE_OPERATION** = CREATE NODE_E9589394263EE5DE
- **CURRENT_STATUS** = CREATE
- **WHY_IN_HUMAN_PACKET** = Regime B 已冻结的质量抽样；抽样不构成实质风险
- **RISK_RULES** = 无实质必审风险命中
- **MANDATORY_TRIGGER** = NONE
- **SAMPLE_STATUS** = RANDOM_CORE #8
- **SAMPLED_FOR_QUALITY_CONTROL** = true

- **SOURCE_ID / SOURCE_NAME** = SC-PHYS-B33C40EBCB5756F7 / SRC_1DD38DEB69830E97 / Strengthening the Global Semiconductor Supply Chain in an Uncertain Era
Source provenance：Semiconductor Industry Association (SIA) / Boston Consulting Group (BCG)；publication=2021-04；edition=；as_of=2021-04；source SHA256=`b33c40ebcb5756f76e887ba2664f97736252e68ba7bfbedc2d628ce2d7cbc08d`。
- **SOURCE_ID / SOURCE_NAME** = SC-PHYS-C5B6DC633E156218 / SRC_AC29CFEE56F74F5B / Testimony of the Semiconductor Industry Association before the Senate Committee on Environment & Public Works (March 4, 2026)
Source provenance：Semiconductor Industry Association (SIA)；publication=2026-03-04；edition=；as_of=2026-03-04；source SHA256=`c5b6dc633e156218eb950f2dee88f43fbdcc4fc1744a5924f12b977f5cb7df71`。

**CANDIDATE_SUMMARY**

- Node 类型：Material
- 名称：CMP Slurry
- 已有身份：NODE_E9589394263EE5DE
- 边界说明：Source支持可复用的持久研究对象，未命中现有规范名或已登记别名。
- Planned native target：NODE_E9589394263EE5DE → SC-CN-0073 / CMP Slurry / Material；这是候选映射，不是已存在或获批准的目录对象。

**AI REVIEW A**

- recommendation：ACCEPT；native_decision：CREATE
- proposed operation / canonical target：CREATE；范围/说明: IDENTITY_RECOMMENDATION_ONLY; CMP Slurry / Material; no canonical mutation
- confidence：HIGH
- reason：两段定义 CMP 浆料用途和悬浮液组成，不等同单一 silica 粉体，Material 可独立维护。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-58EF14CD46DBE095, SC-EV-AC0F07D293403E3F

**AI REVIEW B**

- recommendation：ACCEPT；native_decision：CREATE
- proposed operation / canonical target：CREATE；范围/说明: IDENTITY_ONLY; 03_fab_process_equipment; CMP Slurry; Material
- confidence：HIGH
- reason：slurry颗粒水悬浮液及CMP用途有两段支持，材料身份明确；不等同单一胶体硅材料。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-58EF14CD46DBE095, SC-EV-AC0F07D293403E3F

**A/B RECONCILIATION**

- frozen status：A_B_SUBSTANTIVE_AGREEMENT
- 实质分歧：无；措辞、附注或不改变风险路由的置信度差异不改原冻结一致结论。

**EVIDENCE SUMMARY**

- Supporting facts：下列有来源的节选支持本项讨论的对象/命题；支持范围及未解决条件已在上方 A/B reason 中逐项说明。
- SC-EV-58EF14CD46DBE095 / SC-PHYS-C5B6DC633E156218 / PDF p.5 / II / Back-End Fabrication / CMP / printed p.5；excerpt SHA256=`b4cd2da9b947220d4834812782d651f5a45ac8f5d89006e34b3c039f9f0e7b6a`。
  > Slurry is a suspension of nanosized silica, polymer, or metal particles dispersed in an aqueous solution containing oxidizers, acids, and corrosion inhibitors.
- SC-EV-AC0F07D293403E3F / SC-PHYS-B33C40EBCB5756F7 / PDF p.22 / Materials / printed p.22；excerpt SHA256=`ea77f5c7e0a3d498990812dddae5bcb8d8499c223d56d919533e339b9714c01f`。
  > Chemical Mechanical Planarization (CMP) slurries: Materials used for polishing the surface of the wafer after the film deposition step to provide a flat surface.
- Conflicting evidence：冻结 A/B 未报告本限定范围内的未解决实质证据冲突；不等于完整文献已穷尽。

- **SAMPLING_STRATUM** = domain=03_fab_process_equipment; object_type=nodes; polarity=NOT_PROVIDED; challenge_level=NOT_PROVIDED
- **SAMPLING_REASON** = RANDOM_CORE #8；原种子/原成员不变，无新增风险
- **A_B_AGREE** = true

- **SYSTEM_RECOMMENDED_DECISION** = CREATE
推荐理由（非人工裁决）：双方实质一致且没有剩余实质必审风险；建议按来源限定接受共同原生操作。抽样身份本身不新增风险，正式写入仍须满足既有授权流程。

HUMAN_USER_DECISION = [PENDING]

OPTIONS:

- [ ] CREATE
- [ ] REUSE <NODE_ID>
- [ ] DEFER
- [ ] REJECT

---

<a id="sc-cn-0074"></a>
### 087 · SC-CN-0074 · CMP Polishing Pad

- **ITEM_NUMBER** = 87
- **ITEM_ID** = SC-CN-0074
- **OBJECT_TYPE** = nodes
- **DOMAIN** = 03_fab_process_equipment
- **CURRENT_NATIVE_OPERATION** = CREATE NODE_A059A0C57C121C11
- **CURRENT_STATUS** = CREATE
- **WHY_IN_HUMAN_PACKET** = Regime B 已冻结的质量抽样；抽样不构成实质风险
- **RISK_RULES** = 无实质必审风险命中
- **MANDATORY_TRIGGER** = NONE
- **SAMPLE_STATUS** = RANDOM_CORE #13
- **SAMPLED_FOR_QUALITY_CONTROL** = true

- **SOURCE_ID / SOURCE_NAME** = SC-PHYS-C5B6DC633E156218 / SRC_AC29CFEE56F74F5B / Testimony of the Semiconductor Industry Association before the Senate Committee on Environment & Public Works (March 4, 2026)
Source provenance：Semiconductor Industry Association (SIA)；publication=2026-03-04；edition=；as_of=2026-03-04；source SHA256=`c5b6dc633e156218eb950f2dee88f43fbdcc4fc1744a5924f12b977f5cb7df71`。

**CANDIDATE_SUMMARY**

- Node 类型：Material
- 名称：CMP Polishing Pad
- 已有身份：NODE_A059A0C57C121C11
- 边界说明：Source支持可复用的持久研究对象，未命中现有规范名或已登记别名。
- Planned native target：NODE_A059A0C57C121C11 → SC-CN-0074 / CMP Polishing Pad / Material；这是候选映射，不是已存在或获批准的目录对象。

**AI REVIEW A**

- recommendation：ACCEPT；native_decision：CREATE
- proposed operation / canonical target：CREATE；范围/说明: IDENTITY_RECOMMENDATION_ONLY; CMP Polishing Pad / Material; no canonical mutation
- confidence：HIGH
- reason：CMP 段显式 polishing pad 与 slurry 配合使用，作为抛光耗材 Material 合理，不是设备身份。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-E1426DD81060C643

**AI REVIEW B**

- recommendation：ACCEPT；native_decision：CREATE
- proposed operation / canonical target：CREATE；范围/说明: IDENTITY_ONLY; 03_fab_process_equipment; CMP Polishing Pad; Material
- confidence：HIGH
- reason：原文明示polishing pad配合slurry磨平晶圆，耗用抛光材料角色明确，区别整体CMP设备。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-E1426DD81060C643

**A/B RECONCILIATION**

- frozen status：A_B_SUBSTANTIVE_AGREEMENT
- 实质分歧：无；措辞、附注或不改变风险路由的置信度差异不改原冻结一致结论。

**EVIDENCE SUMMARY**

- Supporting facts：下列有来源的节选支持本项讨论的对象/命题；支持范围及未解决条件已在上方 A/B reason 中逐项说明。
- SC-EV-E1426DD81060C643 / SC-PHYS-C5B6DC633E156218 / PDF p.5 / II / Back-End Fabrication / CMP / printed p.5；excerpt SHA256=`35b1994c551b3073ed773b253b0c157a5498ed77e2343c093908bd4df7185ea2`。
  > Chemical Mechanical Planarization (CMP): Between many deposition and metallization layers throughout the back-end process, chemical mechanical planarization (CMP) uses chemical and physical forces to create a microscopically flat surface for each successive layer of circuit features. A polishing pad with a liquid chemical called a “slurry” polishes the wafer surface until the desired nanometer topography is achieved on the uppermost exposed layer.
- Conflicting evidence：冻结 A/B 未报告本限定范围内的未解决实质证据冲突；不等于完整文献已穷尽。

- **SAMPLING_STRATUM** = domain=03_fab_process_equipment; object_type=nodes; polarity=NOT_PROVIDED; challenge_level=NOT_PROVIDED
- **SAMPLING_REASON** = RANDOM_CORE #13；原种子/原成员不变，无新增风险
- **A_B_AGREE** = true

- **SYSTEM_RECOMMENDED_DECISION** = CREATE
推荐理由（非人工裁决）：双方实质一致且没有剩余实质必审风险；建议按来源限定接受共同原生操作。抽样身份本身不新增风险，正式写入仍须满足既有授权流程。

HUMAN_USER_DECISION = [PENDING]

OPTIONS:

- [ ] CREATE
- [ ] REUSE <NODE_ID>
- [ ] DEFER
- [ ] REJECT

---

<a id="sc-cn-0085"></a>
### 088 · SC-CN-0085 · Fab Wastewater Treatment

- **ITEM_NUMBER** = 88
- **ITEM_ID** = SC-CN-0085
- **OBJECT_TYPE** = nodes
- **DOMAIN** = 03_fab_process_equipment
- **CURRENT_NATIVE_OPERATION** = CREATE NODE_1A5AABCB1F2C7BBA
- **CURRENT_STATUS** = CREATE
- **WHY_IN_HUMAN_PACKET** = Regime B 已冻结的质量抽样；抽样不构成实质风险
- **RISK_RULES** = 无实质必审风险命中
- **MANDATORY_TRIGGER** = NONE
- **SAMPLE_STATUS** = RANDOM_CORE #14
- **SAMPLED_FOR_QUALITY_CONTROL** = true

- **SOURCE_ID / SOURCE_NAME** = SC-PHYS-C5B6DC633E156218 / SRC_AC29CFEE56F74F5B / Testimony of the Semiconductor Industry Association before the Senate Committee on Environment & Public Works (March 4, 2026)
Source provenance：Semiconductor Industry Association (SIA)；publication=2026-03-04；edition=；as_of=2026-03-04；source SHA256=`c5b6dc633e156218eb950f2dee88f43fbdcc4fc1744a5924f12b977f5cb7df71`。

**CANDIDATE_SUMMARY**

- Node 类型：Technology
- 名称：Fab Wastewater Treatment
- 已有身份：NODE_1A5AABCB1F2C7BBA
- 边界说明：Source支持可复用的持久研究对象，未命中现有规范名或已登记别名。
- Planned native target：NODE_1A5AABCB1F2C7BBA → SC-CN-0085 / Fab Wastewater Treatment / Technology；这是候选映射，不是已存在或获批准的目录对象。

**AI REVIEW A**

- recommendation：ACCEPT；native_decision：CREATE
- proposed operation / canonical target：CREATE；范围/说明: IDENTITY_RECOMMENDATION_ONLY; Fab Wastewater Treatment / Technology; no canonical mutation
- confidence：HIGH
- reason：原文明列废水收集处理为 fab 排放控制技术，范围局部，不自动推断法规合规或处理效率。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-37D8E37F58E96AEA

**AI REVIEW B**

- recommendation：ACCEPT；native_decision：CREATE
- proposed operation / canonical target：CREATE；范围/说明: IDENTITY_ONLY; 03_fab_process_equipment; Fab Wastewater Treatment; Technology
- confidence：HIGH
- reason：原文明确fab废水收集处理这一技术活动，局部工艺身份足够；不附会排放达标或政策结论。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-37D8E37F58E96AEA

**A/B RECONCILIATION**

- frozen status：A_B_SUBSTANTIVE_AGREEMENT
- 实质分歧：无；措辞、附注或不改变风险路由的置信度差异不改原冻结一致结论。

**EVIDENCE SUMMARY**

- Supporting facts：下列有来源的节选支持本项讨论的对象/命题；支持范围及未解决条件已在上方 A/B reason 中逐项说明。
- SC-EV-37D8E37F58E96AEA / SC-PHYS-C5B6DC633E156218 / PDF p.8 / III.B / Technical waste treatment description only / printed p.8；excerpt SHA256=`43d849e0db0f62b53a464fa4387fb84b593f92cd78c51d864d17a530e26421a0`。
  > Semiconductor fabs control environmental releases by implementing strict controls including wastewater collection and treatment, waste management systems, and air emissions abatement.
- Conflicting evidence：冻结 A/B 未报告本限定范围内的未解决实质证据冲突；不等于完整文献已穷尽。

- **SAMPLING_STRATUM** = domain=03_fab_process_equipment; object_type=nodes; polarity=NOT_PROVIDED; challenge_level=NOT_PROVIDED
- **SAMPLING_REASON** = RANDOM_CORE #14；原种子/原成员不变，无新增风险
- **A_B_AGREE** = true

- **SYSTEM_RECOMMENDED_DECISION** = CREATE
推荐理由（非人工裁决）：双方实质一致且没有剩余实质必审风险；建议按来源限定接受共同原生操作。抽样身份本身不新增风险，正式写入仍须满足既有授权流程。

HUMAN_USER_DECISION = [PENDING]

OPTIONS:

- [ ] CREATE
- [ ] REUSE <NODE_ID>
- [ ] DEFER
- [ ] REJECT

---

<a id="sc-cn-0086"></a>
### 089 · SC-CN-0086 · Fab Exhaust Abatement

- **ITEM_NUMBER** = 89
- **ITEM_ID** = SC-CN-0086
- **OBJECT_TYPE** = nodes
- **DOMAIN** = 03_fab_process_equipment
- **CURRENT_NATIVE_OPERATION** = CREATE NODE_1CAC66C92B96C282
- **CURRENT_STATUS** = CREATE
- **WHY_IN_HUMAN_PACKET** = Regime B 已冻结的质量抽样；抽样不构成实质风险
- **RISK_RULES** = 无实质必审风险命中
- **MANDATORY_TRIGGER** = NONE
- **SAMPLE_STATUS** = RANDOM_CORE #25
- **SAMPLED_FOR_QUALITY_CONTROL** = true

- **SOURCE_ID / SOURCE_NAME** = SC-PHYS-C5B6DC633E156218 / SRC_AC29CFEE56F74F5B / Testimony of the Semiconductor Industry Association before the Senate Committee on Environment & Public Works (March 4, 2026)
Source provenance：Semiconductor Industry Association (SIA)；publication=2026-03-04；edition=；as_of=2026-03-04；source SHA256=`c5b6dc633e156218eb950f2dee88f43fbdcc4fc1744a5924f12b977f5cb7df71`。

**CANDIDATE_SUMMARY**

- Node 类型：Technology
- 名称：Fab Exhaust Abatement
- 已有身份：NODE_1CAC66C92B96C282
- 边界说明：Source支持可复用的持久研究对象，未命中现有规范名或已登记别名。
- Planned native target：NODE_1CAC66C92B96C282 → SC-CN-0086 / Fab Exhaust Abatement / Technology；这是候选映射，不是已存在或获批准的目录对象。

**AI REVIEW A**

- recommendation：ACCEPT；native_decision：CREATE
- proposed operation / canonical target：CREATE；范围/说明: IDENTITY_RECOMMENDATION_ONLY; Fab Exhaust Abatement / Technology; no canonical mutation
- confidence：HIGH
- reason：排风去除蒸气热量并经洗涤器/氧化器处理的流程直接支持 fab 废气治理 Technology。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-6D361D680E26A1C9

**AI REVIEW B**

- recommendation：ACCEPT；native_decision：CREATE
- proposed operation / canonical target：CREATE；范围/说明: IDENTITY_ONLY; 03_fab_process_equipment; Fab Exhaust Abatement; Technology
- confidence：HIGH
- reason：排气、洗涤器及热/催化/等离子治理被明确描述，支持有界fab尾气处理Technology。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-6D361D680E26A1C9

**A/B RECONCILIATION**

- frozen status：A_B_SUBSTANTIVE_AGREEMENT
- 实质分歧：无；措辞、附注或不改变风险路由的置信度差异不改原冻结一致结论。

**EVIDENCE SUMMARY**

- Supporting facts：下列有来源的节选支持本项讨论的对象/命题；支持范围及未解决条件已在上方 A/B reason 中逐项说明。
- SC-EV-6D361D680E26A1C9 / SC-PHYS-C5B6DC633E156218 / PDF p.8 / III.B / Technical exhaust/abatement description only / printed p.8；excerpt SHA256=`9770f17dcba2eb09d1b826f5aab4d96641e56bd9078e17f8ef490b11c6324970`。
  > Fab exhaust systems remove chemical vapors and heat from process tools. Acids and bases are routed to centralized scrubbers, while volatile organic compounds are abated via centralized thermal, catalytic, or plasma oxidizers which may be equipped to concentrate contaminants prior to abatement.
- Conflicting evidence：冻结 A/B 未报告本限定范围内的未解决实质证据冲突；不等于完整文献已穷尽。

- **SAMPLING_STRATUM** = domain=03_fab_process_equipment; object_type=nodes; polarity=NOT_PROVIDED; challenge_level=NOT_PROVIDED
- **SAMPLING_REASON** = RANDOM_CORE #25；原种子/原成员不变，无新增风险
- **A_B_AGREE** = true

- **SYSTEM_RECOMMENDED_DECISION** = CREATE
推荐理由（非人工裁决）：双方实质一致且没有剩余实质必审风险；建议按来源限定接受共同原生操作。抽样身份本身不新增风险，正式写入仍须满足既有授权流程。

HUMAN_USER_DECISION = [PENDING]

OPTIONS:

- [ ] CREATE
- [ ] REUSE <NODE_ID>
- [ ] DEFER
- [ ] REJECT

---

<a id="sc-cn-0088"></a>
### 090 · SC-CN-0088 · Package Lid Attach

- **ITEM_NUMBER** = 90
- **ITEM_ID** = SC-CN-0088
- **OBJECT_TYPE** = nodes
- **DOMAIN** = 08_assembly_packaging
- **CURRENT_NATIVE_OPERATION** = CREATE NODE_7B7F9D38AC8C2AFF
- **CURRENT_STATUS** = CREATE
- **WHY_IN_HUMAN_PACKET** = Regime B 已冻结的质量抽样；抽样不构成实质风险
- **RISK_RULES** = 无实质必审风险命中
- **MANDATORY_TRIGGER** = NONE
- **SAMPLE_STATUS** = RANDOM_CORE #22
- **SAMPLED_FOR_QUALITY_CONTROL** = true

- **SOURCE_ID / SOURCE_NAME** = SC-PHYS-792E7A66390A5C02 / SRC_1EC7288A377A3B0B / How Silicon Die Become Chip Packages
Source provenance：Intel；publication=2025-02-19；edition=；as_of=2025-02-19；source SHA256=`792e7a66390a5c02a43280077fb1e586a3e46f4abf215608dc831ce5ab665db4`。

**CANDIDATE_SUMMARY**

- Node 类型：Technology
- 名称：Package Lid Attach
- 已有身份：NODE_7B7F9D38AC8C2AFF
- 边界说明：Source支持可复用的持久研究对象，未命中现有规范名或已登记别名。
- Planned native target：NODE_7B7F9D38AC8C2AFF → SC-CN-0088 / Package Lid Attach / Technology；这是候选映射，不是已存在或获批准的目录对象。

**AI REVIEW A**

- recommendation：ACCEPT；native_decision：CREATE
- proposed operation / canonical target：CREATE；范围/说明: IDENTITY_RECOMMENDATION_ONLY; Package Lid Attach / Technology; no canonical mutation
- confidence：HIGH
- reason：Intel 步骤在 TIM 上放置 lid，Package Lid Attach 是明确局部流程，未与 chip attach 合并。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-B0D5FDA1CCB11F5D

**AI REVIEW B**

- recommendation：ACCEPT；native_decision：CREATE
- proposed operation / canonical target：CREATE；范围/说明: IDENTITY_ONLY; 08_assembly_packaging; Package Lid Attach; Technology
- confidence：HIGH
- reason：先施加TIM再放置散热盖的流程直接支撑lid attach，局部封装工艺可建立。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-B0D5FDA1CCB11F5D

**A/B RECONCILIATION**

- frozen status：A_B_SUBSTANTIVE_AGREEMENT
- 实质分歧：无；措辞、附注或不改变风险路由的置信度差异不改原冻结一致结论。

**EVIDENCE SUMMARY**

- Supporting facts：下列有来源的节选支持本项讨论的对象/命题；支持范围及未解决条件已在上方 A/B reason 中逐项说明。
- SC-EV-B0D5FDA1CCB11F5D / SC-PHYS-792E7A66390A5C02 / PDF p.5 / Step 3: Lid Attach / printed p.NOT_KNOWN_OR_UNNUMBERED；excerpt SHA256=`3b5ed675d8d6973ae9dec0d25aaf265efed1a2ac74bc0fdaa532d58c4a886ff2`。
  > Machines apply thermal interface material onto the die and then place a heat spreader (known as a lid) on top. The lid helps dissipate heat.
- Conflicting evidence：冻结 A/B 未报告本限定范围内的未解决实质证据冲突；不等于完整文献已穷尽。

- **SAMPLING_STRATUM** = domain=08_assembly_packaging; object_type=nodes; polarity=NOT_PROVIDED; challenge_level=NOT_PROVIDED
- **SAMPLING_REASON** = RANDOM_CORE #22；原种子/原成员不变，无新增风险
- **A_B_AGREE** = true

- **SYSTEM_RECOMMENDED_DECISION** = CREATE
推荐理由（非人工裁决）：双方实质一致且没有剩余实质必审风险；建议按来源限定接受共同原生操作。抽样身份本身不新增风险，正式写入仍须满足既有授权流程。

HUMAN_USER_DECISION = [PENDING]

OPTIONS:

- [ ] CREATE
- [ ] REUSE <NODE_ID>
- [ ] DEFER
- [ ] REJECT

---

<a id="sc-cn-0090"></a>
### 091 · SC-CN-0090 · Package Heat Spreader

- **ITEM_NUMBER** = 91
- **ITEM_ID** = SC-CN-0090
- **OBJECT_TYPE** = nodes
- **DOMAIN** = 08_assembly_packaging
- **CURRENT_NATIVE_OPERATION** = CREATE NODE_ABD7EFF80E2BE344
- **CURRENT_STATUS** = CREATE
- **WHY_IN_HUMAN_PACKET** = Regime B 已冻结的质量抽样；抽样不构成实质风险
- **RISK_RULES** = 无实质必审风险命中
- **MANDATORY_TRIGGER** = NONE
- **SAMPLE_STATUS** = RANDOM_CORE #4
- **SAMPLED_FOR_QUALITY_CONTROL** = true

- **SOURCE_ID / SOURCE_NAME** = SC-PHYS-792E7A66390A5C02 / SRC_1EC7288A377A3B0B / How Silicon Die Become Chip Packages
Source provenance：Intel；publication=2025-02-19；edition=；as_of=2025-02-19；source SHA256=`792e7a66390a5c02a43280077fb1e586a3e46f4abf215608dc831ce5ab665db4`。

**CANDIDATE_SUMMARY**

- Node 类型：Product
- 名称：Package Heat Spreader
- 已有身份：NODE_ABD7EFF80E2BE344
- 边界说明：Source支持可复用的持久研究对象，未命中现有规范名或已登记别名。
- Planned native target：NODE_ABD7EFF80E2BE344 → SC-CN-0090 / Package Heat Spreader / Product；这是候选映射，不是已存在或获批准的目录对象。

**AI REVIEW A**

- recommendation：ACCEPT；native_decision：CREATE
- proposed operation / canonical target：CREATE；范围/说明: IDENTITY_RECOMMENDATION_ONLY; Package Heat Spreader / Product; no canonical mutation
- confidence：HIGH
- reason：heat spreader/lid 在原文为帮助散热的封装部件，Product 清楚，区别 TIM 材料。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-B0D5FDA1CCB11F5D

**AI REVIEW B**

- recommendation：ACCEPT；native_decision：CREATE
- proposed operation / canonical target：CREATE；范围/说明: IDENTITY_ONLY; 08_assembly_packaging; Package Heat Spreader; Product
- confidence：HIGH
- reason：heat spreader即lid在该封装实例中承担散热功能，Product身份直接可辨。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-B0D5FDA1CCB11F5D

**A/B RECONCILIATION**

- frozen status：A_B_SUBSTANTIVE_AGREEMENT
- 实质分歧：无；措辞、附注或不改变风险路由的置信度差异不改原冻结一致结论。

**EVIDENCE SUMMARY**

- Supporting facts：下列有来源的节选支持本项讨论的对象/命题；支持范围及未解决条件已在上方 A/B reason 中逐项说明。
- SC-EV-B0D5FDA1CCB11F5D / SC-PHYS-792E7A66390A5C02 / PDF p.5 / Step 3: Lid Attach / printed p.NOT_KNOWN_OR_UNNUMBERED；excerpt SHA256=`3b5ed675d8d6973ae9dec0d25aaf265efed1a2ac74bc0fdaa532d58c4a886ff2`。
  > Machines apply thermal interface material onto the die and then place a heat spreader (known as a lid) on top. The lid helps dissipate heat.
- Conflicting evidence：冻结 A/B 未报告本限定范围内的未解决实质证据冲突；不等于完整文献已穷尽。

- **SAMPLING_STRATUM** = domain=08_assembly_packaging; object_type=nodes; polarity=NOT_PROVIDED; challenge_level=NOT_PROVIDED
- **SAMPLING_REASON** = RANDOM_CORE #4；原种子/原成员不变，无新增风险
- **A_B_AGREE** = true

- **SYSTEM_RECOMMENDED_DECISION** = CREATE
推荐理由（非人工裁决）：双方实质一致且没有剩余实质必审风险；建议按来源限定接受共同原生操作。抽样身份本身不新增风险，正式写入仍须满足既有授权流程。

HUMAN_USER_DECISION = [PENDING]

OPTIONS:

- [ ] CREATE
- [ ] REUSE <NODE_ID>
- [ ] DEFER
- [ ] REJECT

---

<a id="sc-cn-0109"></a>
### 092 · SC-CN-0109 · Chemically Amplified Resist

- **ITEM_NUMBER** = 92
- **ITEM_ID** = SC-CN-0109
- **OBJECT_TYPE** = nodes
- **DOMAIN** = 05_lithography_patterning
- **CURRENT_NATIVE_OPERATION** = CREATE NODE_2C87D1F62B1F2224
- **CURRENT_STATUS** = CREATE
- **WHY_IN_HUMAN_PACKET** = Regime B 已冻结的质量抽样；抽样不构成实质风险
- **RISK_RULES** = 无实质必审风险命中
- **MANDATORY_TRIGGER** = NONE
- **SAMPLE_STATUS** = RANDOM_CORE #27
- **SAMPLED_FOR_QUALITY_CONTROL** = true

- **SOURCE_ID / SOURCE_NAME** = SC-PHYS-318D85A127B5B6DF / SRC_FFD94DB31A0E9C0A / 2025 IRDS — Lithography and Patterning
Source provenance：IEEE International Roadmap for Devices and Systems (IRDS)；publication=；edition=2025；as_of=2025；source SHA256=`318d85a127b5b6dfa7b3c1330ae20b18d63660a1fa8c8bdfdd7b478844e145ed`。

**CANDIDATE_SUMMARY**

- Node 类型：Material
- 名称：Chemically Amplified Resist
- 已有身份：NODE_2C87D1F62B1F2224
- 边界说明：Source支持可复用的持久研究对象，未命中现有规范名或已登记别名。
- Planned native target：NODE_2C87D1F62B1F2224 → SC-CN-0109 / Chemically Amplified Resist / Material；这是候选映射，不是已存在或获批准的目录对象。

**AI REVIEW A**

- recommendation：ACCEPT；native_decision：CREATE
- proposed operation / canonical target：CREATE；范围/说明: IDENTITY_RECOMMENDATION_ONLY; Chemically Amplified Resist / Material; no canonical mutation
- confidence：HIGH
- reason：EUV 小节明确 chemically amplified materials 对应 resist 材料类别，独立于 metal oxide resist，Material 范围可建。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-2CCA00E79D91DD12

**AI REVIEW B**

- recommendation：ACCEPT；native_decision：CREATE
- proposed operation / canonical target：CREATE；范围/说明: IDENTITY_ONLY; 05_lithography_patterning; Chemically Amplified Resist; Material
- confidence：HIGH
- reason：EUV Resist Materials章节明确chemically amplified材料用于部分EUV层；材料族成立，采用状态保持2025来源限定。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-2CCA00E79D91DD12

**A/B RECONCILIATION**

- frozen status：A_B_SUBSTANTIVE_AGREEMENT
- 实质分歧：无；措辞、附注或不改变风险路由的置信度差异不改原冻结一致结论。

**EVIDENCE SUMMARY**

- Supporting facts：下列有来源的节选支持本项讨论的对象/命题；支持范围及未解决条件已在上方 A/B reason 中逐项说明。
- SC-EV-2CCA00E79D91DD12 / SC-PHYS-318D85A127B5B6DF / PDF p.17 / EUV Resist Materials / printed p.12；excerpt SHA256=`bc095b935738e34224f2f6e6414ede5e7910cf5ebec73265c08f007fc60c14aa`。
  > Currently, the EUV used in manufacturing is at 0.33NA and chemically amplified materials are in use for most EUV levels in production and metal oxide resists are used for some memory levels.
- Conflicting evidence：冻结 A/B 未报告本限定范围内的未解决实质证据冲突；不等于完整文献已穷尽。

- **SAMPLING_STRATUM** = domain=05_lithography_patterning; object_type=nodes; polarity=NOT_PROVIDED; challenge_level=NOT_PROVIDED
- **SAMPLING_REASON** = RANDOM_CORE #27；原种子/原成员不变，无新增风险
- **A_B_AGREE** = true

- **SYSTEM_RECOMMENDED_DECISION** = CREATE
推荐理由（非人工裁决）：双方实质一致且没有剩余实质必审风险；建议按来源限定接受共同原生操作。抽样身份本身不新增风险，正式写入仍须满足既有授权流程。

HUMAN_USER_DECISION = [PENDING]

OPTIONS:

- [ ] CREATE
- [ ] REUSE <NODE_ID>
- [ ] DEFER
- [ ] REJECT

---

<a id="sc-cn-0116"></a>
### 093 · SC-CN-0116 · Critical-Dimension Metrology

- **ITEM_NUMBER** = 93
- **ITEM_ID** = SC-CN-0116
- **OBJECT_TYPE** = nodes
- **DOMAIN** = 06_metrology_yield_factory
- **CURRENT_NATIVE_OPERATION** = UNDECIDED（没有已填写的人类原生决定）
- **CURRENT_STATUS** = REVIEW
- **WHY_IN_HUMAN_PACKET** = Regime B 已冻结的质量抽样；抽样不构成实质风险
- **RISK_RULES** = 无实质必审风险命中
- **MANDATORY_TRIGGER** = NONE
- **SAMPLE_STATUS** = RANDOM_CORE #2
- **SAMPLED_FOR_QUALITY_CONTROL** = true

- **SOURCE_ID / SOURCE_NAME** = SC-PHYS-AEDD7CB34D12EF15 / SRC_ECAE5FF71F5DE095 / 2024 IRDS — Metrology
Source provenance：IEEE International Roadmap for Devices and Systems (IRDS)；publication=；edition=2024；as_of=2024；source SHA256=`aedd7cb34d12ef15b799ed9a0f6326840a4551ddc7c6600732c6ae82ab6e93b6`。

**CANDIDATE_SUMMARY**

- Node 类型：Technology
- 名称：Critical-Dimension Metrology
- 边界说明：方法族层次需审；不能仅把一项测量参数CD升为Node。

**AI REVIEW A**

- recommendation：ACCEPT；native_decision：CREATE
- proposed operation / canonical target：CREATE；范围/说明: IDENTITY_RECOMMENDATION_ONLY; Critical-Dimension Metrology / Technology; no canonical mutation
- confidence：HIGH
- reason：原文明列 metrology for critical dimensions，候选限定为测量方法而非 CD 数值；局部 Technology 与计量总类可区分。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-4AAF8C92F8CF20F0

**AI REVIEW B**

- recommendation：ACCEPT；native_decision：CREATE
- proposed operation / canonical target：CREATE；范围/说明: IDENTITY_ONLY; 06_metrology_yield_factory; Critical-Dimension Metrology; Technology
- confidence：HIGH
- reason：原文明说metrology for critical dimensions，研究对象为测量方法族而非CD数值本身，Technology可成立。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-4AAF8C92F8CF20F0

**A/B RECONCILIATION**

- frozen status：A_B_SUBSTANTIVE_AGREEMENT
- 实质分歧：无；措辞、附注或不改变风险路由的置信度差异不改原冻结一致结论。

**EVIDENCE SUMMARY**

- Supporting facts：下列有来源的节选支持本项讨论的对象/命题；支持范围及未解决条件已在上方 A/B reason 中逐项说明。
- SC-EV-4AAF8C92F8CF20F0 / SC-PHYS-AEDD7CB34D12EF15 / PDF p.10 / 2 Scope of Report / printed p.5；excerpt SHA256=`af82e9c1a8a297ea881710d07f9ed44ac480b56343dc94fc86d048319549176d`。
  > The scope includes metrology for critical dimensions (CDs), microscopy for 3D and high aspect ratio (HAR) pattern measurements, overlay measurements, lithography metrology, front-end processes metrology, on-chip interconnect metrology, inter- and intra-die interconnect metrology, materials characterization, metrology for emerging materials and devices, reference materials, and outside systems connectivity needs and challenges.
- Conflicting evidence：冻结 A/B 未报告本限定范围内的未解决实质证据冲突；不等于完整文献已穷尽。

- **SAMPLING_STRATUM** = domain=06_metrology_yield_factory; object_type=nodes; polarity=NOT_PROVIDED; challenge_level=NOT_PROVIDED
- **SAMPLING_REASON** = RANDOM_CORE #2；原种子/原成员不变，无新增风险
- **A_B_AGREE** = true

- **SYSTEM_RECOMMENDED_DECISION** = CREATE
推荐理由（非人工裁决）：双方实质一致且没有剩余实质必审风险；建议按来源限定接受共同原生操作。抽样身份本身不新增风险，正式写入仍须满足既有授权流程。

HUMAN_USER_DECISION = [PENDING]

OPTIONS:

- [ ] CREATE
- [ ] REUSE <NODE_ID>
- [ ] DEFER
- [ ] REJECT

---

<a id="sc-cn-0129"></a>
### 094 · SC-CN-0129 · Image Sensor

- **ITEM_NUMBER** = 94
- **ITEM_ID** = SC-CN-0129
- **OBJECT_TYPE** = nodes
- **DOMAIN** = 07_more_than_moore
- **CURRENT_NATIVE_OPERATION** = CREATE NODE_1402915D5C1803E7
- **CURRENT_STATUS** = CREATE
- **WHY_IN_HUMAN_PACKET** = Regime B 已冻结的质量抽样；抽样不构成实质风险
- **RISK_RULES** = 无实质必审风险命中
- **MANDATORY_TRIGGER** = NONE
- **SAMPLE_STATUS** = RANDOM_CORE #16
- **SAMPLED_FOR_QUALITY_CONTROL** = true

- **SOURCE_ID / SOURCE_NAME** = SC-PHYS-59E90A8C09249A8D / SRC_70049F425584945A / 2022 IRDS — More Than Moore
Source provenance：IEEE International Roadmap for Devices and Systems (IRDS)；publication=；edition=2022；as_of=2022；source SHA256=`59e90a8c09249a8dc75f53f661f4f0eff511b9eb65fbc1a1c70ffb363d8166c8`。

**CANDIDATE_SUMMARY**

- Node 类型：Product
- 名称：Image Sensor
- 已有身份：NODE_1402915D5C1803E7
- 边界说明：Source支持可复用的持久研究对象，未命中现有规范名或已登记别名。
- Planned native target：NODE_1402915D5C1803E7 → SC-CN-0129 / Image Sensor / Product；这是候选映射，不是已存在或获批准的目录对象。

**AI REVIEW A**

- recommendation：ACCEPT；native_decision：CREATE
- proposed operation / canonical target：CREATE；范围/说明: IDENTITY_RECOMMENDATION_ONLY; Image Sensor / Product; no canonical mutation
- confidence：HIGH
- reason：来源明确 image sensors 分 CCD/CMOS 两类，产品族范围清楚，不能并入一般 Photodiode。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-D5E8E48FFAA8D5B3

**AI REVIEW B**

- recommendation：ACCEPT；native_decision：CREATE
- proposed operation / canonical target：CREATE；范围/说明: IDENTITY_ONLY; 07_more_than_moore; Image Sensor; Product
- confidence：HIGH
- reason：image sensors明确分CCD/CMOS两类，Product总族可成立；不把单一光电二极管当该总族。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-D5E8E48FFAA8D5B3

**A/B RECONCILIATION**

- frozen status：A_B_SUBSTANTIVE_AGREEMENT
- 实质分歧：无；措辞、附注或不改变风险路由的置信度差异不改原冻结一致结论。

**EVIDENCE SUMMARY**

- Supporting facts：下列有来源的节选支持本项讨论的对象/命题；支持范围及未解决条件已在上方 A/B reason 中逐项说明。
- SC-EV-D5E8E48FFAA8D5B3 / SC-PHYS-59E90A8C09249A8D / PDF p.11 / 2 Smart Sensors / Image Sensors / printed p.5；excerpt SHA256=`5bdedb9f95bb1dc6356d2327801ef457c38e4c9534513f29c072c6b9f73cba53`。
  > Image sensors are classified into charge-coupled device (CCD) and complementary metal-oxide semiconductor (CMOS),
- Conflicting evidence：冻结 A/B 未报告本限定范围内的未解决实质证据冲突；不等于完整文献已穷尽。

- **SAMPLING_STRATUM** = domain=07_more_than_moore; object_type=nodes; polarity=NOT_PROVIDED; challenge_level=NOT_PROVIDED
- **SAMPLING_REASON** = RANDOM_CORE #16；原种子/原成员不变，无新增风险
- **A_B_AGREE** = true

- **SYSTEM_RECOMMENDED_DECISION** = CREATE
推荐理由（非人工裁决）：双方实质一致且没有剩余实质必审风险；建议按来源限定接受共同原生操作。抽样身份本身不新增风险，正式写入仍须满足既有授权流程。

HUMAN_USER_DECISION = [PENDING]

OPTIONS:

- [ ] CREATE
- [ ] REUSE <NODE_ID>
- [ ] DEFER
- [ ] REJECT

---

<a id="sc-cn-0148"></a>
### 095 · SC-CN-0148 · CoWoS-R

- **ITEM_NUMBER** = 95
- **ITEM_ID** = SC-CN-0148
- **OBJECT_TYPE** = nodes
- **DOMAIN** = 09_cross_domain_reuse
- **CURRENT_NATIVE_OPERATION** = REUSE NODE_B7B4CB43F4C30F10
- **CURRENT_STATUS** = REUSE
- **WHY_IN_HUMAN_PACKET** = Regime B 已冻结的质量抽样；抽样不构成实质风险
- **RISK_RULES** = 无实质必审风险命中
- **MANDATORY_TRIGGER** = NONE
- **SAMPLE_STATUS** = RANDOM_CORE #3
- **SAMPLED_FOR_QUALITY_CONTROL** = true

- **SOURCE_ID / SOURCE_NAME** = SC-PHYS-3FB7AE4AD972AA2B / F018b / TSMC 2025 Annual Report
Source provenance：TSMC；publication=；edition=；as_of=2025；source SHA256=`3fb7ae4ad972aa2bc6e45bb36635152ad89d52f4a7165f389bcb94eeb54a6abd`。

**CANDIDATE_SUMMARY**

- Node 类型：Technology
- 名称：CoWoS-R
- 备选身份：NODE_B7B4CB43F4C30F10
- 已有身份：NODE_B7B4CB43F4C30F10
- 边界说明：复用当前Context Pack的active身份；保留ID、规范名和类型。 ®仅作为同一TSMC标识内的商标排版符人工核对，不注册新别名。
- Canonical state：NODE_B7B4CB43F4C30F10 = CoWoS-R；type=Technology；status=active。

**AI REVIEW A**

- recommendation：ACCEPT；native_decision：REUSE
- proposed operation / canonical target：REUSE；目标: NODE_B7B4CB43F4C30F10 [CoWoS-R]；范围/说明: IDENTITY_RECOMMENDATION_ONLY; CoWoS-R / Technology; no canonical mutation
- confidence：HIGH
- reason：CoWoS-R 明确为 redistribution layer interposer 方案，与现有子技术一致，保持其 ID 和类型。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-BE1EFC0405668731

**AI REVIEW B**

- recommendation：ACCEPT；native_decision：REUSE
- proposed operation / canonical target：REUSE；目标: NODE_B7B4CB43F4C30F10 [CoWoS-R]；范围/说明: IDENTITY_ONLY; 09_cross_domain_reuse; CoWoS-R; Technology
- confidence：HIGH
- reason：CoWoS-R的RDL中介层定义对应目录同名技术，商标符号不引入新对象。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-BE1EFC0405668731

**A/B RECONCILIATION**

- frozen status：A_B_SUBSTANTIVE_AGREEMENT
- 实质分歧：无；措辞、附注或不改变风险路由的置信度差异不改原冻结一致结论。

**EVIDENCE SUMMARY**

- Supporting facts：下列有来源的节选支持本项讨论的对象/命题；支持范围及未解决条件已在上方 A/B reason 中逐项说明。
- SC-EV-BE1EFC0405668731 / SC-PHYS-3FB7AE4AD972AA2B / PDF p.53 / TSMC 3DFabric / CoWoS-R / printed p.102-103 (two-page spreads; obey section restriction)；excerpt SHA256=`44ebdfbacad4f0528034996f5dd8911aa1cd61bddb0c3ca1ccaef233889f89a7`。
  > CoWoS® with redistribution layer interposer (CoWoS®-R) advanced packaging service, featuring multiple redistribution layers (RDL) to enable product design simplicity, supports larger HPC products. This technology entered its third year of volume production in 2025.
- Conflicting evidence：冻结 A/B 未报告本限定范围内的未解决实质证据冲突；不等于完整文献已穷尽。

- **SAMPLING_STRATUM** = domain=09_cross_domain_reuse; object_type=nodes; polarity=NOT_PROVIDED; challenge_level=NOT_PROVIDED
- **SAMPLING_REASON** = RANDOM_CORE #3；原种子/原成员不变，无新增风险
- **A_B_AGREE** = true

- **SYSTEM_RECOMMENDED_DECISION** = REUSE NODE_B7B4CB43F4C30F10
推荐理由（非人工裁决）：双方推荐同一所有者/共享身份，证据与目录边界一致；建议确认该有界映射。若目标仍为 SC-CN 候选，正式写入须等待目标身份的人类授权，不能提前附着或移动别名。

HUMAN_USER_DECISION = [PENDING]

OPTIONS:

- [ ] CREATE
- [ ] REUSE <NODE_ID>
- [ ] DEFER
- [ ] REJECT

---

<a id="sc-cn-0154"></a>
### 096 · SC-CN-0154 · 3D Stacking

- **ITEM_NUMBER** = 96
- **ITEM_ID** = SC-CN-0154
- **OBJECT_TYPE** = nodes
- **DOMAIN** = 04_device_scaling_memory
- **CURRENT_NATIVE_OPERATION** = REUSE NODE_20260817_8006A0B4
- **CURRENT_STATUS** = REUSE
- **WHY_IN_HUMAN_PACKET** = Regime B 已冻结的质量抽样；抽样不构成实质风险
- **RISK_RULES** = 无实质必审风险命中
- **MANDATORY_TRIGGER** = NONE
- **SAMPLE_STATUS** = COVERAGE_SUPPLEMENT domain=04_device_scaling_memory
- **SAMPLED_FOR_QUALITY_CONTROL** = true

- **SOURCE_ID / SOURCE_NAME** = SC-PHYS-49A1D3B42E458985 / SRC_96EC545507C25F9F / 2024 IRDS — More Moore
Source provenance：IEEE International Roadmap for Devices and Systems (IRDS)；publication=；edition=2024；as_of=2024；source SHA256=`49a1d3b42e45898555490e602170876e22d1ccf8d7c17711e436d8db36322fa6`。
- **SOURCE_ID / SOURCE_NAME** = SC-PHYS-54CABB8879E180A7 / SRC_0C4EF3703421D29B / 2020 IRDS — Packaging Integration
Source provenance：IEEE International Roadmap for Devices and Systems (IRDS)；publication=；edition=2020；as_of=2020；source SHA256=`54cabb8879e180a7a0363e8964cb2d28735eff03ecee6a45905cd54f06eae5e2`。

**CANDIDATE_SUMMARY**

- Node 类型：Technology
- 名称：3D Stacking
- 已有身份：NODE_20260817_8006A0B4
- 边界说明：复用当前Context Pack的active身份；保留ID、规范名和类型。
- Canonical state：NODE_20260817_8006A0B4 = 3D Stacking；type=Technology；status=active。

**AI REVIEW A**

- recommendation：ACCEPT；native_decision：REUSE
- proposed operation / canonical target：REUSE；目标: NODE_20260817_8006A0B4 [3D Stacking]；范围/说明: IDENTITY_RECOMMENDATION_ONLY; 3D Stacking / Technology; no canonical mutation
- confidence：HIGH
- reason：IRDS 的细间距堆叠和 HBM 3D die stacking 均对应既有 3D Stacking 技术，复用共享核心。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-502921FAD7A062A0, SC-EV-EFC0887512104389

**AI REVIEW B**

- recommendation：ACCEPT；native_decision：REUSE
- proposed operation / canonical target：REUSE；目标: NODE_20260817_8006A0B4 [3D Stacking]；范围/说明: IDENTITY_ONLY; 04_device_scaling_memory; 3D Stacking; Technology
- confidence：HIGH
- reason：fine-pitch 3D stacking与HBM堆叠语境直接吻合既有3D Stacking，不与特定键合方法合并。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-502921FAD7A062A0, SC-EV-EFC0887512104389

**A/B RECONCILIATION**

- frozen status：A_B_SUBSTANTIVE_AGREEMENT
- 实质分歧：无；措辞、附注或不改变风险路由的置信度差异不改原冻结一致结论。

**EVIDENCE SUMMARY**

- Supporting facts：下列有来源的节选支持本项讨论的对象/命题；支持范围及未解决条件已在上方 A/B reason 中逐项说明。
- SC-EV-502921FAD7A062A0 / SC-PHYS-49A1D3B42E458985 / PDF p.22 / 4.6 3D Integration / printed p.17；excerpt SHA256=`68dffad64b0ad7d8de06d38103d6dec34959c683c9e7c7343fcd6659536f51a8`。
  > this slow-down has been accompanied by fine-pitch 3D stacking assembly such as ubump stacking and hybrid bonding [21].
- SC-EV-EFC0887512104389 / SC-PHYS-54CABB8879E180A7 / PDF p.16 / 3D Stacks / HBM / printed p.10；excerpt SHA256=`d9cddb60890e78a2e295a82cfaaf5bfcaa51109c055e8b64bf17ccb2d28667f4`。
  > Under these conditions new high bandwidth memories (HBM) have been optimized for 3D die stacking (Figure PI-6).
- Conflicting evidence：冻结 A/B 未报告本限定范围内的未解决实质证据冲突；不等于完整文献已穷尽。

- **SAMPLING_STRATUM** = domain=04_device_scaling_memory; object_type=nodes; polarity=NOT_PROVIDED; challenge_level=NOT_PROVIDED
- **SAMPLING_REASON** = COVERAGE_SUPPLEMENT domain=04_device_scaling_memory；原种子/原成员不变，无新增风险
- **A_B_AGREE** = true

- **SYSTEM_RECOMMENDED_DECISION** = REUSE NODE_20260817_8006A0B4
推荐理由（非人工裁决）：双方推荐同一所有者/共享身份，证据与目录边界一致；建议确认该有界映射。若目标仍为 SC-CN 候选，正式写入须等待目标身份的人类授权，不能提前附着或移动别名。

HUMAN_USER_DECISION = [PENDING]

OPTIONS:

- [ ] CREATE
- [ ] REUSE <NODE_ID>
- [ ] DEFER
- [ ] REJECT

---

<a id="sc-cn-0156"></a>
### 097 · SC-CN-0156 · Back End of Line

- **ITEM_NUMBER** = 97
- **ITEM_ID** = SC-CN-0156
- **OBJECT_TYPE** = nodes
- **DOMAIN** = 03_fab_process_equipment
- **CURRENT_NATIVE_OPERATION** = CREATE NODE_4E904C855F447E32
- **CURRENT_STATUS** = CREATE
- **WHY_IN_HUMAN_PACKET** = Regime B 已冻结的质量抽样；抽样不构成实质风险
- **RISK_RULES** = 无实质必审风险命中
- **MANDATORY_TRIGGER** = NONE
- **SAMPLE_STATUS** = RANDOM_CORE #21
- **SAMPLED_FOR_QUALITY_CONTROL** = true

- **SOURCE_ID / SOURCE_NAME** = SC-PHYS-C5B6DC633E156218 / SRC_AC29CFEE56F74F5B / Testimony of the Semiconductor Industry Association before the Senate Committee on Environment & Public Works (March 4, 2026)
Source provenance：Semiconductor Industry Association (SIA)；publication=2026-03-04；edition=；as_of=2026-03-04；source SHA256=`c5b6dc633e156218eb950f2dee88f43fbdcc4fc1744a5924f12b977f5cb7df71`。

**CANDIDATE_SUMMARY**

- Node 类型：Technology
- 名称：Back End of Line
- 已有身份：NODE_4E904C855F447E32
- 边界说明：晶圆互连制造阶段，严格不等同Assembly/Packaging/Test。
- Planned native target：NODE_4E904C855F447E32 → SC-CN-0156 / Back End of Line / Technology；这是候选映射，不是已存在或获批准的目录对象。

**AI REVIEW A**

- recommendation：ACCEPT；native_decision：CREATE
- proposed operation / canonical target：CREATE；范围/说明: IDENTITY_RECOMMENDATION_ONLY; Back End of Line / Technology; no canonical mutation
- confidence：HIGH
- reason：Figure 3 分开 BEOL fab 与后端装配封测，金属互连段补足流程语义；限定晶圆互连技术可建。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-79EA49E93CAF7F64, SC-EV-30ECB7A5649A64DC

**AI REVIEW B**

- recommendation：ACCEPT_WITH_REVIEW_NOTE；native_decision：CREATE
- proposed operation / canonical target：CREATE；范围/说明: IDENTITY_ONLY; 03_fab_process_equipment; Back End of Line; Technology
- confidence：MEDIUM
- reason：SIA图3及金属互连段明确BEOL为晶圆后端互连阶段，区别封装测试；本节点不改装配Segment。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-79EA49E93CAF7F64, SC-EV-30ECB7A5649A64DC

**A/B RECONCILIATION**

- frozen status：A_B_SUBSTANTIVE_AGREEMENT
- 实质分歧：无；措辞、附注或不改变风险路由的置信度差异不改原冻结一致结论。

**EVIDENCE SUMMARY**

- Supporting facts：下列有来源的节选支持本项讨论的对象/命题；支持范围及未解决条件已在上方 A/B reason 中逐项说明。
- SC-EV-30ECB7A5649A64DC / SC-PHYS-C5B6DC633E156218 / PDF p.5 / II / Back-End Fabrication / Metallization / printed p.5；excerpt SHA256=`d6a39a41013572a9d37dcb4c73163c05252d55a2ba42d53bb571d3a1f8ac5214`。
  > Metallization: Prior processing steps prepare the device for metallization, which creates the electrical interconnections between all transistors on the wafer. Following completion of the front end, individual devices are interconnected on the "back end" using a series of alternating metal depositions and dielectric films, each with their respective patterning.
- SC-EV-79EA49E93CAF7F64 / SC-PHYS-C5B6DC633E156218 / PDF p.4 / II / manufacturing process overview / printed p.4 / Figure 3；excerpt SHA256=`89a542845a4ecc9dfc626b49fc7337eccdadca4d317b03cdd058d4aac201e306`。
  > Back End of Line (BEOL) Fab Manufacturing Process Steps
- Conflicting evidence：冻结 A/B 未报告本限定范围内的未解决实质证据冲突；不等于完整文献已穷尽。

- **SAMPLING_STRATUM** = domain=03_fab_process_equipment; object_type=nodes; polarity=NOT_PROVIDED; challenge_level=NOT_PROVIDED
- **SAMPLING_REASON** = RANDOM_CORE #21；原种子/原成员不变，无新增风险
- **A_B_AGREE** = true

- **SYSTEM_RECOMMENDED_DECISION** = CREATE
推荐理由（非人工裁决）：双方实质一致且没有剩余实质必审风险；建议按来源限定接受共同原生操作。抽样身份本身不新增风险，正式写入仍须满足既有授权流程。

HUMAN_USER_DECISION = [PENDING]

OPTIONS:

- [ ] CREATE
- [ ] REUSE <NODE_ID>
- [ ] DEFER
- [ ] REJECT

---

<a id="sc-cn-0161"></a>
### 098 · SC-CN-0161 · Wafer Cleaning

- **ITEM_NUMBER** = 98
- **ITEM_ID** = SC-CN-0161
- **OBJECT_TYPE** = nodes
- **DOMAIN** = 03_fab_process_equipment
- **CURRENT_NATIVE_OPERATION** = CREATE NODE_142DE7A2558ABAA5
- **CURRENT_STATUS** = CREATE
- **WHY_IN_HUMAN_PACKET** = Regime B 已冻结的质量抽样；抽样不构成实质风险
- **RISK_RULES** = 无实质必审风险命中
- **MANDATORY_TRIGGER** = NONE
- **SAMPLE_STATUS** = RANDOM_CORE #23
- **SAMPLED_FOR_QUALITY_CONTROL** = true

- **SOURCE_ID / SOURCE_NAME** = SC-PHYS-AA294FCF8FEDE75B / SRC_08CC764E9C0DCB61 / 2025 IRDS — Yield Enhancement and Advanced Manufacturing & Contamination Control
Source provenance：IEEE International Roadmap for Devices and Systems (IRDS)；publication=；edition=2025；as_of=2025；source SHA256=`aa294fcf8fede75be6e2c23c6ec75a6f3504538dceb87eb51edda0134526b34b`。
- **SOURCE_ID / SOURCE_NAME** = SC-PHYS-C5B6DC633E156218 / SRC_AC29CFEE56F74F5B / Testimony of the Semiconductor Industry Association before the Senate Committee on Environment & Public Works (March 4, 2026)
Source provenance：Semiconductor Industry Association (SIA)；publication=2026-03-04；edition=；as_of=2026-03-04；source SHA256=`c5b6dc633e156218eb950f2dee88f43fbdcc4fc1744a5924f12b977f5cb7df71`。

**CANDIDATE_SUMMARY**

- Node 类型：Technology
- 名称：Wafer Cleaning
- 已有身份：NODE_142DE7A2558ABAA5
- 边界说明：清洁工序不等同湿法刻蚀，不与清洗设备混型。
- Planned native target：NODE_142DE7A2558ABAA5 → SC-CN-0161 / Wafer Cleaning / Technology；这是候选映射，不是已存在或获批准的目录对象。

**AI REVIEW A**

- recommendation：ACCEPT；native_decision：CREATE
- proposed operation / canonical target：CREATE；范围/说明: IDENTITY_RECOMMENDATION_ONLY; Wafer Cleaning / Technology; no canonical mutation
- confidence：HIGH
- reason：预清洗与末道清洗两段支持晶圆清洗技术，区别 wet etching 的材料去除功能，catalog 无同义工艺。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-25D863B317FE099F, SC-EV-D5DC766A624FE286

**AI REVIEW B**

- recommendation：ACCEPT；native_decision：CREATE
- proposed operation / canonical target：CREATE；范围/说明: IDENTITY_ONLY; 03_fab_process_equipment; Wafer Cleaning; Technology
- confidence：HIGH
- reason：预清洗及末道清洗证据直接支持清洁工艺，区别湿法刻蚀和清洗设备，不推断完整recipe。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-25D863B317FE099F, SC-EV-D5DC766A624FE286

**A/B RECONCILIATION**

- frozen status：A_B_SUBSTANTIVE_AGREEMENT
- 实质分歧：无；措辞、附注或不改变风险路由的置信度差异不改原冻结一致结论。

**EVIDENCE SUMMARY**

- Supporting facts：下列有来源的节选支持本项讨论的对象/命题；支持范围及未解决条件已在上方 A/B reason 中逐项说明。
- SC-EV-25D863B317FE099F / SC-PHYS-C5B6DC633E156218 / PDF p.4 / II / Front-End Fabrication / Thermal Oxidation / printed p.4；excerpt SHA256=`7bc1913e286f59649f39cb898d9901b64537356ffb6f975551809c62b0d1bff1`。
  > Wafers are first pre-cleaned using high-purity deionized water and low-particulate chemicals to ensure high-yield production.
- SC-EV-D5DC766A624FE286 / SC-PHYS-AA294FCF8FEDE75B / PDF p.10 / Yield / contamination and reliability / printed p.5；excerpt SHA256=`ff768898a46776020b696413561ea02021ef29b2b95effb5f042d0f6ab7857e1`。
  > Typical sources of contamination are from airborne sources and ultrapure water used in last cleaning steps of the Si channel before oxide and high-k dielectric (e.g. HfO2) deposition.
- Conflicting evidence：冻结 A/B 未报告本限定范围内的未解决实质证据冲突；不等于完整文献已穷尽。

- **SAMPLING_STRATUM** = domain=03_fab_process_equipment; object_type=nodes; polarity=NOT_PROVIDED; challenge_level=NOT_PROVIDED
- **SAMPLING_REASON** = RANDOM_CORE #23；原种子/原成员不变，无新增风险
- **A_B_AGREE** = true

- **SYSTEM_RECOMMENDED_DECISION** = CREATE
推荐理由（非人工裁决）：双方实质一致且没有剩余实质必审风险；建议按来源限定接受共同原生操作。抽样身份本身不新增风险，正式写入仍须满足既有授权流程。

HUMAN_USER_DECISION = [PENDING]

OPTIONS:

- [ ] CREATE
- [ ] REUSE <NODE_ID>
- [ ] DEFER
- [ ] REJECT

---

<a id="sc-rl-0004"></a>
### 099 · SC-RL-0004 · SIA把逻辑产品归入数字半导体类别。

- **ITEM_NUMBER** = 99
- **ITEM_ID** = SC-RL-0004
- **OBJECT_TYPE** = relations
- **DOMAIN** = semiconductor
- **CURRENT_NATIVE_OPERATION** = NEW_RELATION_CANDIDATE
- **CURRENT_STATUS** = REVIEW
- **WHY_IN_HUMAN_PACKET** = Regime B 已冻结的质量抽样；抽样不构成实质风险
- **RISK_RULES** = 无实质必审风险命中
- **MANDATORY_TRIGGER** = NONE
- **SAMPLE_STATUS** = RANDOM_CORE #17
- **SAMPLED_FOR_QUALITY_CONTROL** = true

- **SOURCE_ID / SOURCE_NAME** = SC-PHYS-04A42FFC3F71A42F / SRC_1640D08BDF90458F / Making Semiconductors: The Highly Complex and Global Chip Research, Design, and Manufacturing Process
Source provenance：Semiconductor Industry Association (SIA)；publication=2019；edition=；as_of=2019；source SHA256=`04a42ffc3f71a42fa9b996240618874bb7fff21404e93cdb1e7bf53318938c26`。

**CANDIDATE_SUMMARY**

- 关系类型：part_of
- 命题：SIA把逻辑产品归入数字半导体类别。
- 时间类别：categorical_source_scoped
- 终点：Digital Semiconductors
- 范围：SIA 2019 semiconductor taxonomy
- 起点：Logic Semiconductors
- Candidate target：SC-CN-0006 = Digital Semiconductors；type=Segment；frozen status=CREATE；仍须目标自身授权。
- Candidate target：SC-CN-0008 = Logic Semiconductors；type=Segment；frozen status=CREATE；仍须目标自身授权。

**AI REVIEW A**

- recommendation：ACCEPT_WITH_REVIEW_NOTE；native_decision：CREATE
- proposed operation / canonical target：CREATE；起点: SC-CN-0008 [Logic Semiconductors]；终点: SC-CN-0006 [Digital Semiconductors]；关系: part_of；范围/说明: SIA 2019 semiconductor taxonomy
- confidence：MEDIUM
- reason：SIA 同段列 logic products 于 digital category，逻辑→数字方向正确，未扩展所有计算应用。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-086DB7864B530FA0

**AI REVIEW B**

- recommendation：ACCEPT；native_decision：CREATE
- proposed operation / canonical target：CREATE；起点: SC-CN-0008 [Logic Semiconductors]；终点: SC-CN-0006 [Digital Semiconductors]；关系: part_of；范围/说明: SIA 2019 semiconductor taxonomy
- confidence：HIGH
- reason：同句将logic products列入digital category，子类指向父类清楚；不将微组件也合并为logic。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-086DB7864B530FA0

**A/B RECONCILIATION**

- frozen status：A_B_SUBSTANTIVE_AGREEMENT
- 实质分歧：无；措辞、附注或不改变风险路由的置信度差异不改原冻结一致结论。

**EVIDENCE SUMMARY**

- Supporting facts：下列有来源的节选支持本项讨论的对象/命题；支持范围及未解决条件已在上方 A/B reason 中逐项说明。
- SC-EV-086DB7864B530FA0 / SC-PHYS-04A42FFC3F71A42F / PDF p.1 / Types of Semiconductors / printed p.NOT_KNOWN_OR_UNNUMBERED；excerpt SHA256=`de70cc3f209d1d690acd93eb476001bba1cc790fb80c8683d1bf9cc013d15cfe`。
  > Within ICs are digital semiconductors, which process binary information used by computers, and analog semiconductors, which regulate “real world” conditions such as temperature, speed, sound, and electrical current. Within the digital category are memory products, micro-components (including microprocessors and microcontrollers) and logic products.
- Conflicting evidence：冻结 A/B 未报告本限定范围内的未解决实质证据冲突；不等于完整文献已穷尽。

- **SAMPLING_STRATUM** = domain=semiconductor; object_type=relations; polarity=NOT_PROVIDED; challenge_level=NOT_PROVIDED
- **SAMPLING_REASON** = RANDOM_CORE #17；原种子/原成员不变，无新增风险
- **A_B_AGREE** = true

- **SYSTEM_RECOMMENDED_DECISION** = CREATE
推荐理由（非人工裁决）：双方支持相同方向、类型、端点与来源范围；建议通过该候选关系的抽样复核。保留候选端点与时间限定，不实际建边或推导新的因果。

HUMAN_USER_DECISION = [PENDING]

OPTIONS:

- [ ] CREATE
- [ ] REUSE <RELATION_ID>
- [ ] DEFER
- [ ] REJECT

---

<a id="sc-rl-0009"></a>
### 100 · SC-RL-0009 · IRDS将FeRAM列入非电荷存储型的非易失性存储器。

- **ITEM_NUMBER** = 100
- **ITEM_ID** = SC-RL-0009
- **OBJECT_TYPE** = relations
- **DOMAIN** = semiconductor
- **CURRENT_NATIVE_OPERATION** = NEW_RELATION_CANDIDATE
- **CURRENT_STATUS** = REVIEW
- **WHY_IN_HUMAN_PACKET** = Regime B 已冻结的质量抽样；抽样不构成实质风险
- **RISK_RULES** = 无实质必审风险命中
- **MANDATORY_TRIGGER** = NONE
- **SAMPLE_STATUS** = RANDOM_CORE #1
- **SAMPLED_FOR_QUALITY_CONTROL** = true

- **SOURCE_ID / SOURCE_NAME** = SC-PHYS-49A1D3B42E458985 / SRC_96EC545507C25F9F / 2024 IRDS — More Moore
Source provenance：IEEE International Roadmap for Devices and Systems (IRDS)；publication=；edition=2024；as_of=2024；source SHA256=`49a1d3b42e45898555490e602170876e22d1ccf8d7c17711e436d8db36322fa6`。

**CANDIDATE_SUMMARY**

- 关系类型：part_of
- 命题：IRDS将FeRAM列入非电荷存储型的非易失性存储器。
- 时间类别：categorical_source_scoped
- 终点：Nonvolatile Memory
- 范围：IRDS More Moore 2024 / taxonomy only; development not deployment
- 起点：Ferroelectric Memory
- Candidate target：SC-CN-0100 = Nonvolatile Memory；type=Segment；frozen status=CREATE；仍须目标自身授权。
- Candidate target：SC-CN-0103 = Ferroelectric Memory；type=Product；frozen status=CREATE；仍须目标自身授权。

**AI REVIEW A**

- recommendation：ACCEPT_WITH_REVIEW_NOTE；native_decision：CREATE
- proposed operation / canonical target：CREATE；起点: SC-CN-0103 [Ferroelectric Memory]；终点: SC-CN-0100 [Nonvolatile Memory]；关系: part_of；范围/说明: IRDS More Moore 2024 / taxonomy only; development not deployment
- confidence：MEDIUM
- reason：IRDS 将 ferroelectric/FeRAM 列为非易失存储类型，子类→非易失总类可成立，不主张部署成熟。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-02E262518094E12D

**AI REVIEW B**

- recommendation：ACCEPT；native_decision：CREATE
- proposed operation / canonical target：CREATE；起点: SC-CN-0103 [Ferroelectric Memory]；终点: SC-CN-0100 [Nonvolatile Memory]；关系: part_of；范围/说明: IRDS More Moore 2024 / taxonomy only; development not deployment
- confidence：HIGH
- reason：FeRAM被明确纳入非电荷非易失存储，可直接指向非易失总类；发展阶段不转为部署断言。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-02E262518094E12D

**A/B RECONCILIATION**

- frozen status：A_B_SUBSTANTIVE_AGREEMENT
- 实质分歧：无；措辞、附注或不改变风险路由的置信度差异不改原冻结一致结论。

**EVIDENCE SUMMARY**

- Supporting facts：下列有来源的节选支持本项讨论的对象/命题；支持范围及未解决条件已在上方 A/B reason 中逐项说明。
- SC-EV-02E262518094E12D / SC-PHYS-49A1D3B42E458985 / PDF p.29 / 5.3 Emerging Memories / printed p.24；excerpt SHA256=`192798edc20a9c38bce046badc29ae4d3fa27b103dbb302fcf164428f2da7377`。
  > several non-conventional non-volatile memories that are not based on charge storage, so-called resistive or capacitive memories (ferroelectric or FeRAM, magnetic or MRAM, phase-change or PCRAM, and resistive or ReRAM), are being developed and form the category often called “emerging” memories.
- Conflicting evidence：冻结 A/B 未报告本限定范围内的未解决实质证据冲突；不等于完整文献已穷尽。

- **SAMPLING_STRATUM** = domain=semiconductor; object_type=relations; polarity=NOT_PROVIDED; challenge_level=NOT_PROVIDED
- **SAMPLING_REASON** = RANDOM_CORE #1；原种子/原成员不变，无新增风险
- **A_B_AGREE** = true

- **SYSTEM_RECOMMENDED_DECISION** = CREATE
推荐理由（非人工裁决）：双方支持相同方向、类型、端点与来源范围；建议通过该候选关系的抽样复核。保留候选端点与时间限定，不实际建边或推导新的因果。

HUMAN_USER_DECISION = [PENDING]

OPTIONS:

- [ ] CREATE
- [ ] REUSE <RELATION_ID>
- [ ] DEFER
- [ ] REJECT

---

<a id="sc-rl-0013"></a>
### 101 · SC-RL-0013 · ASML将湿法刻蚀列为刻蚀的一种类型。

- **ITEM_NUMBER** = 101
- **ITEM_ID** = SC-RL-0013
- **OBJECT_TYPE** = relations
- **DOMAIN** = semiconductor
- **CURRENT_NATIVE_OPERATION** = NEW_RELATION_CANDIDATE
- **CURRENT_STATUS** = REVIEW
- **WHY_IN_HUMAN_PACKET** = Regime B 已冻结的质量抽样；抽样不构成实质风险
- **RISK_RULES** = 无实质必审风险命中
- **MANDATORY_TRIGGER** = NONE
- **SAMPLE_STATUS** = RANDOM_CORE #19
- **SAMPLED_FOR_QUALITY_CONTROL** = true

- **SOURCE_ID / SOURCE_NAME** = SC-PHYS-87B4665C30781057 / SRC_ADCEE4236B19B5F2 / Six Crucial Steps in Semiconductor Manufacturing
Source provenance：ASML；publication=2023-10-04；edition=；as_of=2023-10-04；source SHA256=`87b4665c3078105792ca70f18964c938976b72f2dcf0d19379b034d5d6f205f9`。

**CANDIDATE_SUMMARY**

- 关系类型：part_of
- 命题：ASML将湿法刻蚀列为刻蚀的一种类型。
- 时间类别：categorical_source_scoped
- 终点：Etching
- 范围：ASML 2023 generic process taxonomy
- 起点：Wet Etching
- Candidate target：SC-CN-0058 = Wet Etching；type=Technology；frozen status=CREATE；仍须目标自身授权。
- Candidate target：SC-CN-0060 = Etching；type=Technology；frozen status=CREATE；仍须目标自身授权。

**AI REVIEW A**

- recommendation：ACCEPT_WITH_REVIEW_NOTE；native_decision：CREATE
- proposed operation / canonical target：CREATE；起点: SC-CN-0058 [Wet Etching]；终点: SC-CN-0060 [Etching]；关系: part_of；范围/说明: ASML 2023 generic process taxonomy
- confidence：MEDIUM
- reason：ASML 明说两种 etch 之一为 wet，湿刻蚀→刻蚀是分类 part_of，不是工艺时序或因果。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-F4124019AED7B2C6

**AI REVIEW B**

- recommendation：ACCEPT；native_decision：CREATE
- proposed operation / canonical target：CREATE；起点: SC-CN-0058 [Wet Etching]；终点: SC-CN-0060 [Etching]；关系: part_of；范围/说明: ASML 2023 generic process taxonomy
- confidence：HIGH
- reason：ASML直接说刻蚀有wet和dry两种，Wet Etching到Etching分类方向清楚；限定芯片图形刻蚀。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-F4124019AED7B2C6

**A/B RECONCILIATION**

- frozen status：A_B_SUBSTANTIVE_AGREEMENT
- 实质分歧：无；措辞、附注或不改变风险路由的置信度差异不改原冻结一致结论。

**EVIDENCE SUMMARY**

- Supporting facts：下列有来源的节选支持本项讨论的对象/命题；支持范围及未解决条件已在上方 A/B reason 中逐项说明。
- SC-EV-F4124019AED7B2C6 / SC-PHYS-87B4665C30781057 / PDF p.5 / Etch / printed p.NOT_KNOWN_OR_UNNUMBERED；excerpt SHA256=`02fec2f77dbbe325687492c55adca4474054844b65aa709378a742455cdbae7a`。
  > As with resist, there are two types of etch: 'wet' and 'dry'. Dry etching uses gases to define the exposed pattern on the wafer. Wet etching uses chemical baths to wash the wafer.
- Conflicting evidence：冻结 A/B 未报告本限定范围内的未解决实质证据冲突；不等于完整文献已穷尽。

- **SAMPLING_STRATUM** = domain=semiconductor; object_type=relations; polarity=NOT_PROVIDED; challenge_level=NOT_PROVIDED
- **SAMPLING_REASON** = RANDOM_CORE #19；原种子/原成员不变，无新增风险
- **A_B_AGREE** = true

- **SYSTEM_RECOMMENDED_DECISION** = CREATE
推荐理由（非人工裁决）：双方支持相同方向、类型、端点与来源范围；建议通过该候选关系的抽样复核。保留候选端点与时间限定，不实际建边或推导新的因果。

HUMAN_USER_DECISION = [PENDING]

OPTIONS:

- [ ] CREATE
- [ ] REUSE <RELATION_ID>
- [ ] DEFER
- [ ] REJECT

---

<a id="sc-rl-0022"></a>
### 102 · SC-RL-0022 · TSMC所述CoWoS-S服务使用硅中介层。

- **ITEM_NUMBER** = 102
- **ITEM_ID** = SC-RL-0022
- **OBJECT_TYPE** = relations
- **DOMAIN** = semiconductor
- **CURRENT_NATIVE_OPERATION** = NEW_RELATION_CANDIDATE
- **CURRENT_STATUS** = REVIEW
- **WHY_IN_HUMAN_PACKET** = Regime B 已冻结的质量抽样；抽样不构成实质风险
- **RISK_RULES** = 无实质必审风险命中
- **MANDATORY_TRIGGER** = NONE
- **SAMPLE_STATUS** = RANDOM_CORE #9
- **SAMPLED_FOR_QUALITY_CONTROL** = true

- **SOURCE_ID / SOURCE_NAME** = SC-PHYS-3FB7AE4AD972AA2B / F018b / TSMC 2025 Annual Report
Source provenance：TSMC；publication=；edition=；as_of=2025；source SHA256=`3fb7ae4ad972aa2bc6e45bb36635152ad89d52f4a7165f389bcb94eeb54a6abd`。

**CANDIDATE_SUMMARY**

- 关系类型：uses
- 命题：TSMC所述CoWoS-S服务使用硅中介层。
- 时间类别：historical_vendor_architecture
- 终点：Silicon Interposer
- 范围：TSMC 2025 annual report / CoWoS-S architecture
- 起点：CoWoS-S
- Canonical state：NODE_20260817_3A173B33 = Silicon Interposer；type=Product；status=active。
- Canonical state：NODE_3E0E5604C3F64891 = CoWoS-S；type=Technology；status=active。

**AI REVIEW A**

- recommendation：ACCEPT；native_decision：CREATE
- proposed operation / canonical target：CREATE；起点: NODE_3E0E5604C3F64891 [CoWoS-S]；终点: NODE_20260817_3A173B33 [Silicon Interposer]；关系: uses；范围/说明: TSMC 2025 annual report / CoWoS-S architecture
- confidence：HIGH
- reason：CoWoS-S 名称和描述明确 silicon interposer，技术→所用产品 uses 正确，source scope 保留 TSMC 2025。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-A5D5D8057F31DBE3

**AI REVIEW B**

- recommendation：ACCEPT；native_decision：CREATE
- proposed operation / canonical target：CREATE；起点: NODE_3E0E5604C3F64891 [CoWoS-S]；终点: NODE_20260817_3A173B33 [Silicon Interposer]；关系: uses；范围/说明: TSMC 2025 annual report / CoWoS-S architecture
- confidence：HIGH
- reason：CoWoS with silicon interposer直接说明CoWoS-S使用硅中介层，uses方向为技术到产品，非反向归属。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-A5D5D8057F31DBE3

**A/B RECONCILIATION**

- frozen status：A_B_SUBSTANTIVE_AGREEMENT
- 实质分歧：无；措辞、附注或不改变风险路由的置信度差异不改原冻结一致结论。

**EVIDENCE SUMMARY**

- Supporting facts：下列有来源的节选支持本项讨论的对象/命题；支持范围及未解决条件已在上方 A/B reason 中逐项说明。
- SC-EV-A5D5D8057F31DBE3 / SC-PHYS-3FB7AE4AD972AA2B / PDF p.53 / TSMC 3DFabric / CoWoS-S / printed p.102-103 (two-page spreads; obey section restriction)；excerpt SHA256=`1ee0e58c09585bf92677e57e8bbb17bf6f7f18b4c5754477744e11491e64746e`。
  > CoWoS® with silicon interposer (CoWoS®-S) advanced packaging service features high interconnect routing density and embedded deep trench capacitor (eDTC) and has been in volume production for several years.
- Conflicting evidence：冻结 A/B 未报告本限定范围内的未解决实质证据冲突；不等于完整文献已穷尽。

- **SAMPLING_STRATUM** = domain=semiconductor; object_type=relations; polarity=NOT_PROVIDED; challenge_level=NOT_PROVIDED
- **SAMPLING_REASON** = RANDOM_CORE #9；原种子/原成员不变，无新增风险
- **A_B_AGREE** = true

- **SYSTEM_RECOMMENDED_DECISION** = CREATE
推荐理由（非人工裁决）：双方支持相同方向、类型、端点与来源范围；建议通过该候选关系的抽样复核。保留候选端点与时间限定，不实际建边或推导新的因果。

HUMAN_USER_DECISION = [PENDING]

OPTIONS:

- [ ] CREATE
- [ ] REUSE <RELATION_ID>
- [ ] DEFER
- [ ] REJECT

---

<a id="sc-rl-0036"></a>
### 103 · SC-RL-0036 · 光刻曝光利用掩模或reticle上的图形。

- **ITEM_NUMBER** = 103
- **ITEM_ID** = SC-RL-0036
- **OBJECT_TYPE** = relations
- **DOMAIN** = semiconductor
- **CURRENT_NATIVE_OPERATION** = NEW_RELATION_CANDIDATE
- **CURRENT_STATUS** = REVIEW
- **WHY_IN_HUMAN_PACKET** = Regime B 已冻结的质量抽样；抽样不构成实质风险
- **RISK_RULES** = 无实质必审风险命中
- **MANDATORY_TRIGGER** = NONE
- **SAMPLE_STATUS** = RANDOM_CORE #5
- **SAMPLED_FOR_QUALITY_CONTROL** = true

- **SOURCE_ID / SOURCE_NAME** = SC-PHYS-87B4665C30781057 / SRC_ADCEE4236B19B5F2 / Six Crucial Steps in Semiconductor Manufacturing
Source provenance：ASML；publication=2023-10-04；edition=；as_of=2023-10-04；source SHA256=`87b4665c3078105792ca70f18964c938976b72f2dcf0d19379b034d5d6f205f9`。
- **SOURCE_ID / SOURCE_NAME** = SC-PHYS-B33C40EBCB5756F7 / SRC_1DD38DEB69830E97 / Strengthening the Global Semiconductor Supply Chain in an Uncertain Era
Source provenance：Semiconductor Industry Association (SIA) / Boston Consulting Group (BCG)；publication=2021-04；edition=；as_of=2021-04；source SHA256=`b33c40ebcb5756f76e887ba2664f97736252e68ba7bfbedc2d628ce2d7cbc08d`。

**CANDIDATE_SUMMARY**

- 关系类型：uses
- 命题：光刻曝光利用掩模或reticle上的图形。
- 时间类别：categorical_source_scoped
- 终点：Photomask
- 范围：SIA/BCG 2021 and ASML 2023 optical lithography
- 起点：Photolithography
- Candidate target：SC-CN-0053 = Photomask；type=Product；frozen status=CREATE；仍须目标自身授权。
- Candidate target：SC-CN-0056 = Photolithography；type=Technology；frozen status=CREATE；仍须目标自身授权。

**AI REVIEW A**

- recommendation：ACCEPT_WITH_REVIEW_NOTE；native_decision：CREATE
- proposed operation / canonical target：CREATE；起点: SC-CN-0056 [Photolithography]；终点: SC-CN-0053 [Photomask]；关系: uses；范围/说明: SIA/BCG 2021 and ASML 2023 optical lithography
- confidence：MEDIUM
- reason：photomask plate used in lithography 直接支持 uses；无需先解决 reticle 的全域同义争议即可接受光刻→掩模。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-9393F2354C64C727, SC-EV-FD3B14BF5F4E693A

**AI REVIEW B**

- recommendation：ACCEPT；native_decision：CREATE
- proposed operation / canonical target：CREATE；起点: SC-CN-0056 [Photolithography]；终点: SC-CN-0053 [Photomask]；关系: uses；范围/说明: SIA/BCG 2021 and ASML 2023 optical lithography
- confidence：HIGH
- reason：掩模有遮光/透光图形且光经reticle投射，支持光学光刻uses Photomask；不扩大至无掩模曝光。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-9393F2354C64C727, SC-EV-FD3B14BF5F4E693A

**A/B RECONCILIATION**

- frozen status：A_B_SUBSTANTIVE_AGREEMENT
- 实质分歧：无；措辞、附注或不改变风险路由的置信度差异不改原冻结一致结论。

**EVIDENCE SUMMARY**

- Supporting facts：下列有来源的节选支持本项讨论的对象/命题；支持范围及未解决条件已在上方 A/B reason 中逐项说明。
- SC-EV-9393F2354C64C727 / SC-PHYS-B33C40EBCB5756F7 / PDF p.22 / Materials / printed p.22；excerpt SHA256=`def2d7634fa4482f5819e198a1df17516c435020372e9c614ece45c4d72a317b`。
  > Photomask: A plate covered with patterns used in the lithography process. The patterns consist of opaque and clear areas that prevent or allow light through.
- SC-EV-FD3B14BF5F4E693A / SC-PHYS-87B4665C30781057 / PDF p.3 / Lithography / printed p.NOT_KNOWN_OR_UNNUMBERED；excerpt SHA256=`21298139f48fcf329096f3f7d90d4751ff5497922f91c3a74665ff867615183f`。
  > Light is projected onto the wafer through the 'reticle', which holds the blueprint of the pattern to be printed. The system's optics (lenses in a DUV system and mirrors in an EUV system) shrink and focus the pattern onto the resist layer.
- Conflicting evidence：冻结 A/B 未报告本限定范围内的未解决实质证据冲突；不等于完整文献已穷尽。

- **SAMPLING_STRATUM** = domain=semiconductor; object_type=relations; polarity=NOT_PROVIDED; challenge_level=NOT_PROVIDED
- **SAMPLING_REASON** = RANDOM_CORE #5；原种子/原成员不变，无新增风险
- **A_B_AGREE** = true

- **SYSTEM_RECOMMENDED_DECISION** = CREATE
推荐理由（非人工裁决）：双方支持相同方向、类型、端点与来源范围；建议通过该候选关系的抽样复核。保留候选端点与时间限定，不实际建边或推导新的因果。

HUMAN_USER_DECISION = [PENDING]

OPTIONS:

- [ ] CREATE
- [ ] REUSE <RELATION_ID>
- [ ] DEFER
- [ ] REJECT

---

<a id="sc-rl-0043"></a>
### 104 · SC-RL-0043 · IRDS所述Si channel末道清洗使用超纯水。

- **ITEM_NUMBER** = 104
- **ITEM_ID** = SC-RL-0043
- **OBJECT_TYPE** = relations
- **DOMAIN** = semiconductor
- **CURRENT_NATIVE_OPERATION** = NEW_RELATION_CANDIDATE
- **CURRENT_STATUS** = REVIEW
- **WHY_IN_HUMAN_PACKET** = Regime B 已冻结的质量抽样；抽样不构成实质风险
- **RISK_RULES** = 无实质必审风险命中
- **MANDATORY_TRIGGER** = NONE
- **SAMPLE_STATUS** = RANDOM_CORE #26
- **SAMPLED_FOR_QUALITY_CONTROL** = true

- **SOURCE_ID / SOURCE_NAME** = SC-PHYS-AA294FCF8FEDE75B / SRC_08CC764E9C0DCB61 / 2025 IRDS — Yield Enhancement and Advanced Manufacturing & Contamination Control
Source provenance：IEEE International Roadmap for Devices and Systems (IRDS)；publication=；edition=2025；as_of=2025；source SHA256=`aa294fcf8fede75be6e2c23c6ec75a6f3504538dceb87eb51edda0134526b34b`。

**CANDIDATE_SUMMARY**

- 关系类型：uses
- 命题：IRDS所述Si channel末道清洗使用超纯水。
- 时间类别：categorical_source_scoped
- 终点：Ultrapure Water
- 范围：IRDS Yield 2025 / last Si-channel cleaning before dielectric deposition
- 起点：Wafer Cleaning
- Candidate target：SC-CN-0160 = Ultrapure Water；type=Material；frozen status=CREATE；仍须目标自身授权。
- Candidate target：SC-CN-0161 = Wafer Cleaning；type=Technology；frozen status=CREATE；仍须目标自身授权。

**AI REVIEW A**

- recommendation：ACCEPT_WITH_REVIEW_NOTE；native_decision：CREATE
- proposed operation / canonical target：CREATE；起点: SC-CN-0161 [Wafer Cleaning]；终点: SC-CN-0160 [Ultrapure Water]；关系: uses；范围/说明: IRDS Yield 2025 / last Si-channel cleaning before dielectric deposition
- confidence：MEDIUM
- reason：UPW used in last cleaning steps 有直接关系证据；scope 保留 Si channel 介质沉积前末道清洗，不断言水绝无污染。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-D5DC766A624FE286

**AI REVIEW B**

- recommendation：ACCEPT；native_decision：CREATE
- proposed operation / canonical target：CREATE；起点: SC-CN-0161 [Wafer Cleaning]；终点: SC-CN-0160 [Ultrapure Water]；关系: uses；范围/说明: IRDS Yield 2025 / last Si-channel cleaning before dielectric deposition
- confidence：HIGH
- reason：ultrapure water used in last cleaning steps直接支持有界清洗uses超纯水；同时可为污染源不否认使用关系。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-D5DC766A624FE286

**A/B RECONCILIATION**

- frozen status：A_B_SUBSTANTIVE_AGREEMENT
- 实质分歧：无；措辞、附注或不改变风险路由的置信度差异不改原冻结一致结论。

**EVIDENCE SUMMARY**

- Supporting facts：下列有来源的节选支持本项讨论的对象/命题；支持范围及未解决条件已在上方 A/B reason 中逐项说明。
- SC-EV-D5DC766A624FE286 / SC-PHYS-AA294FCF8FEDE75B / PDF p.10 / Yield / contamination and reliability / printed p.5；excerpt SHA256=`ff768898a46776020b696413561ea02021ef29b2b95effb5f042d0f6ab7857e1`。
  > Typical sources of contamination are from airborne sources and ultrapure water used in last cleaning steps of the Si channel before oxide and high-k dielectric (e.g. HfO2) deposition.
- Conflicting evidence：冻结 A/B 未报告本限定范围内的未解决实质证据冲突；不等于完整文献已穷尽。

- **SAMPLING_STRATUM** = domain=semiconductor; object_type=relations; polarity=NOT_PROVIDED; challenge_level=NOT_PROVIDED
- **SAMPLING_REASON** = RANDOM_CORE #26；原种子/原成员不变，无新增风险
- **A_B_AGREE** = true

- **SYSTEM_RECOMMENDED_DECISION** = CREATE
推荐理由（非人工裁决）：双方支持相同方向、类型、端点与来源范围；建议通过该候选关系的抽样复核。保留候选端点与时间限定，不实际建边或推导新的因果。

HUMAN_USER_DECISION = [PENDING]

OPTIONS:

- [ ] CREATE
- [ ] REUSE <RELATION_ID>
- [ ] DEFER
- [ ] REJECT

---

<a id="sc-rl-0046"></a>
### 105 · SC-RL-0046 · Intel所述chip attach把die连接到substrate。

- **ITEM_NUMBER** = 105
- **ITEM_ID** = SC-RL-0046
- **OBJECT_TYPE** = relations
- **DOMAIN** = semiconductor
- **CURRENT_NATIVE_OPERATION** = NEW_RELATION_CANDIDATE
- **CURRENT_STATUS** = REVIEW
- **WHY_IN_HUMAN_PACKET** = Regime B 已冻结的质量抽样；抽样不构成实质风险
- **RISK_RULES** = 无实质必审风险命中
- **MANDATORY_TRIGGER** = NONE
- **SAMPLE_STATUS** = RANDOM_CORE #10
- **SAMPLED_FOR_QUALITY_CONTROL** = true

- **SOURCE_ID / SOURCE_NAME** = SC-PHYS-792E7A66390A5C02 / SRC_1EC7288A377A3B0B / How Silicon Die Become Chip Packages
Source provenance：Intel；publication=2025-02-19；edition=；as_of=2025-02-19；source SHA256=`792e7a66390a5c02a43280077fb1e586a3e46f4abf215608dc831ce5ab665db4`。

**CANDIDATE_SUMMARY**

- 关系类型：uses
- 命题：Intel所述chip attach把die连接到substrate。
- 时间类别：categorical_source_scoped
- 终点：Package Substrate
- 范围：Intel 2025 chip-attach example; not all packages
- 起点：Die Attach
- Candidate target：SC-CN-0031 = Package Substrate；type=Product；frozen status=REVIEW；仍须目标自身授权。
- Candidate target：SC-CN-0087 = Die Attach；type=Technology；frozen status=CREATE；仍须目标自身授权。

**AI REVIEW A**

- recommendation：ACCEPT_WITH_REVIEW_NOTE；native_decision：CREATE
- proposed operation / canonical target：CREATE；起点: SC-CN-0087 [Die Attach]；终点: SC-CN-0031 [Package Substrate]；关系: uses；范围/说明: Intel 2025 chip-attach example; not all packages
- confidence：MEDIUM
- reason：CAM affixes die to substrate 明确工艺使用封装载体，目标用更宽 Package Substrate 0031，不能复用 Advanced Package Substrate 子类。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-05E522303824DD15

**AI REVIEW B**

- recommendation：ACCEPT；native_decision：CREATE
- proposed operation / canonical target：CREATE；起点: SC-CN-0087 [Die Attach]；终点: SC-CN-0031 [Package Substrate]；关系: uses；范围/说明: Intel 2025 chip-attach example; not all packages
- confidence：HIGH
- reason：Intel CAM将die附着substrate明确支持die attach uses通用封装基板；目标不能缩为既有Advanced Package Substrate。
- evidence assessment：SUFFICIENT；Evidence IDs：SC-EV-05E522303824DD15

**A/B RECONCILIATION**

- frozen status：A_B_SUBSTANTIVE_AGREEMENT
- 实质分歧：无；措辞、附注或不改变风险路由的置信度差异不改原冻结一致结论。

**EVIDENCE SUMMARY**

- Supporting facts：下列有来源的节选支持本项讨论的对象/命题；支持范围及未解决条件已在上方 A/B reason 中逐项说明。
- SC-EV-05E522303824DD15 / SC-PHYS-792E7A66390A5C02 / PDF p.3 / Step 1: Chip Attach / printed p.NOT_KNOWN_OR_UNNUMBERED；excerpt SHA256=`9215b333603b91b590dc4e4882c941ea9133146d70e04f033c50df46319fc4e2`。
  > A chip attach module (CAM) affixes die and any other required components (such as capacitors) to the substrate, which is the main body of the package.
- Conflicting evidence：冻结 A/B 未报告本限定范围内的未解决实质证据冲突；不等于完整文献已穷尽。

- **SAMPLING_STRATUM** = domain=semiconductor; object_type=relations; polarity=NOT_PROVIDED; challenge_level=NOT_PROVIDED
- **SAMPLING_REASON** = RANDOM_CORE #10；原种子/原成员不变，无新增风险
- **A_B_AGREE** = true

- **SYSTEM_RECOMMENDED_DECISION** = CREATE
推荐理由（非人工裁决）：双方支持相同方向、类型、端点与来源范围；建议通过该候选关系的抽样复核。保留候选端点与时间限定，不实际建边或推导新的因果。

HUMAN_USER_DECISION = [PENDING]

OPTIONS:

- [ ] CREATE
- [ ] REUSE <RELATION_ID>
- [ ] DEFER
- [ ] REJECT

---

