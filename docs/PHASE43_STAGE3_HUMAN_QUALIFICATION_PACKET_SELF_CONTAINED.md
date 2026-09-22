# Phase 4.3 Stage 3 — HUMAN_USER Qualification Packet

This is an advisory, self-contained review of the frozen 100-item Stage 3 population. Every item requires explicit HUMAN_USER authorization. AI consensus grants no authority. No canonical or Production mutation has been made.

- Baseline: `690fc4f26e02607fb54a48053cf8faf6775621c3`; population SHA-256: `207f4f57f78f0fe0034a3bb17edd38cc911a21cd322ea753ac02edc41a70babb`.
- Stage 2 immutable packet SHA-256: `06006a1c98247f1803dac9cdcd0f10ade5d84beddc56a12e3768e5a9e5bfc66c`.
- Section A: 96 mandatory items with A/B substantive agreement.
- Section B: 4 substantive disagreements.
- Residual sample: 0. HUMAN_USER decisions applied: 0.
- Native REUSE options require a specific validated canonical target ID. CREATE remains a proposal and does not activate a canonical object.

## Structural case summary

The following IDs locate all frozen items matching the requested structural topics. Each item below retains its bound evidence and both AI reviews.

| Topic | Frozen items | Review boundary |
|---|---|---|
| High Bandwidth Memory / DRAM | `SC-CN-0010`, `SC-CN-0138`, `SC-RL-0025`, `SC-RL-0026` | Keep generic DRAM separate from Server DRAM and HBM; retain source-scoped HBM relations. |
| Advanced Packaging | `SC-CN-0032` | Generic packaging class may reuse its exact Segment; vendor services remain separate. |
| CoWoS family | `SC-CN-0146`, `SC-CN-0149`, `SC-CN-0148`, `SC-CN-0147`, `SC-RL-0019`, `SC-RL-0020`, `SC-RL-0021`, `SC-RL-0022`, `SC-RL-0023`, `SC-RL-0024`, `SC-RL-0025` | Review S/R variant names and existing edge temporal semantics without duplicating relations. |
| SoIC | `SC-CN-0150` | Preserve the specific identity and distinguish it from broader 3DFabric service scope. |
| 3DFabric | `SC-CN-0152` | Vendor service umbrella remains a distinct, deferred identity question. |
| Interposer variants | `SC-CN-0114`, `SC-CN-0113`, `SC-CN-0112`, `SC-RL-0017`, `SC-RL-0018`, `SC-RL-0022`, `SC-RL-0023`, `SC-RL-0024` | Generic, silicon, and RDL interposers retain separate granularity. |
| UCIe | `SC-CN-0144`, `SC-CN-0145` | Reuse the standard identity; treat UCIe 3.0 as version-scoped evidence, not a parallel node. |
| Chiplet / Chiplet Architecture | `SC-CN-0033`, `SC-CN-0151` | Physical companion die and architecture technology have different object boundaries. |
| Silicon Photonics / PIC | `SC-CN-0135`, `SC-CN-0136` | Generic PIC breadth cannot be silently merged with silicon photonics. |
| EDA / PDK / Process Node | none in frozen population | No frozen comparison item for these terms if locator is empty. |
| Photoresist | `SC-CN-0052`, `SC-RL-0015`, `SC-RL-0016`, `SC-RL-0035` | Separate generic lithography resist, packaging resist, and resin component scope. |
| CMP | `SC-CN-0042`, `SC-RL-0031`, `SC-RL-0038`, `SC-RL-0039` | Keep starting-wafer mirror polishing and fabrication CMP granularity review visible. |
| Semiconductor Metrology | `SC-CN-0115` | Technology/function differs from a specific metrology Equipment identity. |
| Underfill / Packaging Encapsulant | `SC-CN-0082`, `SC-CN-0081`, `SC-RL-0049` | Underfill is narrower than the umbrella protection-material class. |
| Glass Core Substrate | `SC-CN-0159` | Historical quarantine remains binding. |
| Diamond thermal material | `SC-CN-0143` | Potential replacement use does not establish deployed material identity. |

Cross-domain collision: `SC-CN-0142` (target/status review). Unresolved automated identity conflicts: 25. Ontology-pressure relations: `SC-RL-0051`–`SC-RL-0054`. Temporal mismatch relations: `SC-RL-0019`, `SC-RL-0020`.

## Section A — Consensus, mandatory HUMAN_USER authorization

### Item 001 — SC-CN-0032 — Advanced Packaging

- ITEM_NUMBER: 1; ITEM_ID: `SC-CN-0032`; OBJECT_TYPE: identity.
- DOMAIN / context: `01_design_enablement` Semiconductor structured Foundation candidate against shared AI Hardware canonical catalog; cross-domain status: `GOVERNED_REUSE`.
- AUTOMATED_STAGE3_OUTCOME: `REUSE_CANONICAL`; CURRENT_CANONICAL_TARGET: `NODE_20260817_4452D283`.
- Possible existing canonical IDs (unresolved unless explicitly reused): `NODE_20260817_4452D283`.
- CANDIDATE_SUMMARY: Advanced Packaging; candidate type `Segment`; comparison scope `复用当前Context Pack的active身份；保留ID、规范名和类型。`; frozen candidate rationale: 复用当前Context Pack的active身份；保留ID、规范名和类型。
- WHY_HUMAN_REQUIRED: frozen Stage 3 mandatory review population; automated reasons: EXACT_SHARED_CATALOG_IDENTITY.
- RISK_FLAGS: A=EXACT_SHARED_CATALOG_IDENTITY; B=none.

**AI REVIEW A**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `REUSE_CANONICAL`; target: `NODE_20260817_4452D283`; confidence: HIGH; materiality: HIGH.
- reason: Advanced Packaging is the same Segment as the active exact-name catalog entry; the source does not narrow it to a vendor service.
- evidence assessment: Intel defines the general multi-die packaging class, which supports the name and scope but does not itself authorize the existing node.
- temporal scope assessed: {'source_as_of': ['2026-03-09'], 'publication_date': ['2026-03-09'], 'identity_claim': 'candidate_only'}
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'same', 'object_type': 'compatible', 'scope': 'compatible', 'granularity': 'same', 'quarantine': 'clear', 'ontology': 'compatible', 'evidence_sufficiency': 'sufficient', 'temporal': 'compatible'}

**AI REVIEW B**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `REUSE_CANONICAL`; target: `NODE_20260817_4452D283`; confidence: HIGH; materiality: LOW.
- reason: Exact active catalog identity: Advanced Packaging to Advanced Packaging; source uses the same Segment object.
- evidence assessment: SC-EV-B4BF4AEAB06DB96F from SC-P0-005_Intel_Common_Chip_Terms.pdf [source SC-PHYS-7E064380CA686D9F; SHA 7e064380ca686d9f00c235f15c007523e89e4a0ffb7e9a22f435218c06799d05; PDF p.6, What is a Package?]: Advanced packaging refers to a set of specialized technologies introduced over the past decade to combine multiple dies in a single package. Boundary: Exact active catalog identity: Advanced Packaging to Advanced Packaging; source uses the same Segment object. All source excerpts remain UNAUTHORIZED_CANDIDATE evidence.
- temporal scope assessed: 2026-03-09
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'same', 'object_type': 'compatible', 'scope': 'compatible', 'granularity': 'same', 'quarantine': 'clear', 'ontology': 'compatible', 'evidence_sufficiency': 'sufficient', 'temporal': 'compatible'}

**A/B RECONCILIATION**

- A_B_SUBSTANTIVE_AGREEMENT; disagreement type: none; native-operation conflict: false; target conflict: false.
- Interpretation differences: none.
- Reconciliation assessment: Same native operation, target, and material interpretation.
- Non-material rubric-label differences retained for audit: none.

**EVIDENCE SUMMARY**

- Source `SC-PHYS-7E064380CA686D9F` (SHA-256 `7e064380ca686d9f00c235f15c007523e89e4a0ffb7e9a22f435218c06799d05`), file `SC-P0-005_Intel_Common_Chip_Terms.pdf`, p. 6, section What is a Package?; evidence `SC-EV-B4BF4AEAB06DB96F`; as-of 2026-03-09; excerpt: “Advanced packaging refers to a set of specialized technologies introduced over the past decade to combine multiple dies in a single package.”
- Temporal scope: source as-of dates above; no relation temporal claim.

- SYSTEM_RECOMMENDED_DECISION: `REUSE_CANONICAL`.
- SYSTEM_RECOMMENDATION_REASON: A/B substantive consensus; frozen automated outcome: REUSE_CANONICAL.
- HUMAN_USER_DECISION = PENDING
- VALID NATIVE OPTIONS: REUSE_CANONICAL, CREATE_NEW_CANONICAL, KEEP_DOMAIN_SPECIFIC, DEFER, REJECT; REUSE requires an explicit validated target ID and all options remain subject to frozen controls.

### Item 003 — SC-CN-0151 — Chiplet Architecture

- ITEM_NUMBER: 3; ITEM_ID: `SC-CN-0151`; OBJECT_TYPE: identity.
- DOMAIN / context: `09_cross_domain_reuse` Semiconductor structured Foundation candidate against shared AI Hardware canonical catalog; cross-domain status: `GOVERNED_REUSE`.
- AUTOMATED_STAGE3_OUTCOME: `REUSE_CANONICAL`; CURRENT_CANONICAL_TARGET: `NODE_20260817_CB56C000`.
- Possible existing canonical IDs (unresolved unless explicitly reused): `NODE_20260817_CB56C000`.
- CANDIDATE_SUMMARY: Chiplet Architecture; candidate type `Technology`; comparison scope `复用当前Context Pack的active身份；保留ID、规范名和类型。`; frozen candidate rationale: 复用当前Context Pack的active身份；保留ID、规范名和类型。
- WHY_HUMAN_REQUIRED: frozen Stage 3 mandatory review population; automated reasons: EXACT_SHARED_CATALOG_IDENTITY.
- RISK_FLAGS: A=EXACT_SHARED_CATALOG_IDENTITY; B=none.

**AI REVIEW A**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `REUSE_CANONICAL`; target: `NODE_20260817_CB56C000`; confidence: HIGH; materiality: MEDIUM.
- reason: Chiplet Architecture matches the active Technology exactly; the TSMC usage does not turn it into a physical chiplet.
- evidence assessment: The TSMC SoIC passage names chiplet architecture in an HPC integration context, consistent with the existing technology identity.
- temporal scope assessed: {'source_as_of': ['2025'], 'publication_date': [None], 'identity_claim': 'candidate_only'}
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'same', 'object_type': 'compatible', 'scope': 'compatible', 'granularity': 'same', 'quarantine': 'clear', 'ontology': 'compatible', 'evidence_sufficiency': 'sufficient', 'temporal': 'compatible'}

**AI REVIEW B**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `REUSE_CANONICAL`; target: `NODE_20260817_CB56C000`; confidence: HIGH; materiality: LOW.
- reason: Exact active catalog identity: Chiplet Architecture to Chiplet Architecture; source uses the same Technology object.
- evidence assessment: SC-EV-2BD04E0EEBBAD758 from SC-P0-020B_TSMC_2025_Annual_Report.pdf [source F018b; SHA 3fb7ae4ad972aa2bc6e45bb36635152ad89d52f4a7165f389bcb94eeb54a6abd; PDF p.53, TSMC 3DFabric / SoIC]: TSMC-SoIC® Chip-on-Wafer (CoW) 3D vertical integration solution offers high-density interconnect for chiplet architecture for HPC products. 3nm system on integrated chip (SoIC) stacking technology successfully entered volume production in 2025. Boundary: Exact active catalog identity: Chiplet Architecture to Chiplet Architecture; source uses the same Technology object. All source excerpts remain UNAUTHORIZED_CANDIDATE evidence.
- temporal scope assessed: 2025
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'same', 'object_type': 'compatible', 'scope': 'compatible', 'granularity': 'same', 'quarantine': 'clear', 'ontology': 'compatible', 'evidence_sufficiency': 'sufficient', 'temporal': 'compatible'}

**A/B RECONCILIATION**

- A_B_SUBSTANTIVE_AGREEMENT; disagreement type: none; native-operation conflict: false; target conflict: false.
- Interpretation differences: none.
- Reconciliation assessment: Same native operation, target, and material interpretation.
- Non-material rubric-label differences retained for audit: none.

**EVIDENCE SUMMARY**

- Source `F018b` (SHA-256 `3fb7ae4ad972aa2bc6e45bb36635152ad89d52f4a7165f389bcb94eeb54a6abd`), file `SC-P0-020B_TSMC_2025_Annual_Report.pdf`, p. 53, section TSMC 3DFabric / SoIC; evidence `SC-EV-2BD04E0EEBBAD758`; as-of 2025; excerpt: “TSMC-SoIC® Chip-on-Wafer (CoW) 3D vertical integration solution offers high-density interconnect for chiplet architecture for HPC products. 3nm system on integrated chip (SoIC) stacking technology successfully entered volume production in 2025.”
- Temporal scope: source as-of dates above; no relation temporal claim.

- SYSTEM_RECOMMENDED_DECISION: `REUSE_CANONICAL`.
- SYSTEM_RECOMMENDATION_REASON: A/B substantive consensus; frozen automated outcome: REUSE_CANONICAL.
- HUMAN_USER_DECISION = PENDING
- VALID NATIVE OPTIONS: REUSE_CANONICAL, CREATE_NEW_CANONICAL, KEEP_DOMAIN_SPECIFIC, DEFER, REJECT; REUSE requires an explicit validated target ID and all options remain subject to frozen controls.

### Item 004 — SC-CN-0130 — CMOS Image Sensor

- ITEM_NUMBER: 4; ITEM_ID: `SC-CN-0130`; OBJECT_TYPE: identity.
- DOMAIN / context: `07_more_than_moore` Semiconductor structured Foundation candidate against shared AI Hardware canonical catalog; cross-domain status: `DISTINCT_BROADER_OR_DIFFERENT_OBJECT`.
- AUTOMATED_STAGE3_OUTCOME: `CREATE_NEW_CANONICAL`; CURRENT_CANONICAL_TARGET: `NODE_FF8DC56E8080F36A`.
- Possible existing canonical IDs (unresolved unless explicitly reused): `none`.
- CANDIDATE_SUMMARY: CMOS Image Sensor; candidate type `Product`; comparison scope `Source支持可复用的持久研究对象，未命中现有规范名或已登记别名。`; frozen candidate rationale: Source支持可复用的持久研究对象，未命中现有规范名或已登记别名。
- WHY_HUMAN_REQUIRED: frozen Stage 3 mandatory review population; automated reasons: NEW_CANONICAL_NODE, NO_SHARED_CATALOG_MATCH.
- RISK_FLAGS: A=NEW_CANONICAL_NODE, NO_SHARED_CATALOG_MATCH; B=none.

**AI REVIEW A**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `CREATE_NEW_CANONICAL`; target: `NODE_FF8DC56E8080F36A`; confidence: HIGH; materiality: MEDIUM.
- reason: CMOS Image Sensor is a specific image-sensor Product with no deterministic catalog match; CCD is a sibling, not an alias.
- evidence assessment: The source distinguishes CMOS and CCD image sensors, directly supporting a durable CMOS sensor category.
- temporal scope assessed: {'source_as_of': ['2022'], 'publication_date': [None], 'identity_claim': 'candidate_only'}
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'distinct', 'object_type': 'compatible', 'scope': 'compatible', 'granularity': 'unknown', 'quarantine': 'clear', 'ontology': 'compatible', 'evidence_sufficiency': 'sufficient', 'temporal': 'compatible'}

**AI REVIEW B**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `CREATE_NEW_CANONICAL`; target: `NODE_FF8DC56E8080F36A`; confidence: HIGH; materiality: LOW.
- reason: CMOS Image Sensor is a product subtype explicitly contrasted with CCD; no frozen active same-name target is retrieved.
- evidence assessment: SC-EV-D5E8E48FFAA8D5B3 from SC-P0-014_2022_IRDS_More_Than_Moore.pdf [source SC-PHYS-59E90A8C09249A8D; SHA 59e90a8c09249a8dc75f53f661f4f0eff511b9eb65fbc1a1c70ffb363d8166c8; PDF p.11, 2 Smart Sensors / Image Sensors]: Image sensors are classified into charge-coupled device (CCD) and complementary metal-oxide semiconductor (CMOS), Boundary: CMOS Image Sensor is a product subtype explicitly contrasted with CCD; no frozen active same-name target is retrieved. All source excerpts remain UNAUTHORIZED_CANDIDATE evidence.
- temporal scope assessed: 2022
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'distinct', 'object_type': 'compatible', 'scope': 'compatible', 'granularity': 'different', 'quarantine': 'clear', 'ontology': 'compatible', 'evidence_sufficiency': 'sufficient', 'temporal': 'compatible'}

**A/B RECONCILIATION**

- A_B_SUBSTANTIVE_AGREEMENT; disagreement type: none; native-operation conflict: false; target conflict: false.
- Interpretation differences: none.
- Reconciliation assessment: Both reviewers propose the same distinct candidate. Scope and granularity labels compare it with different reference objects, without changing the identity boundary.
- Non-material rubric-label differences retained for audit: granularity.

**EVIDENCE SUMMARY**

- Source `SC-PHYS-59E90A8C09249A8D` (SHA-256 `59e90a8c09249a8dc75f53f661f4f0eff511b9eb65fbc1a1c70ffb363d8166c8`), file `SC-P0-014_2022_IRDS_More_Than_Moore.pdf`, p. 11, section 2 Smart Sensors / Image Sensors; evidence `SC-EV-D5E8E48FFAA8D5B3`; as-of 2022; excerpt: “Image sensors are classified into charge-coupled device (CCD) and complementary metal-oxide semiconductor (CMOS),”
- Temporal scope: source as-of dates above; no relation temporal claim.

- SYSTEM_RECOMMENDED_DECISION: `CREATE_NEW_CANONICAL`.
- SYSTEM_RECOMMENDATION_REASON: A/B substantive consensus; frozen automated outcome: CREATE_NEW_CANONICAL.
- HUMAN_USER_DECISION = PENDING
- VALID NATIVE OPTIONS: REUSE_CANONICAL, CREATE_NEW_CANONICAL, KEEP_DOMAIN_SPECIFIC, DEFER, REJECT; REUSE requires an explicit validated target ID and all options remain subject to frozen controls.

### Item 005 — SC-CN-0043 — Colloidal Silica

- ITEM_NUMBER: 5; ITEM_ID: `SC-CN-0043`; OBJECT_TYPE: identity.
- DOMAIN / context: `02_wafer_materials` Semiconductor structured Foundation candidate against shared AI Hardware canonical catalog; cross-domain status: `DISTINCT_BROADER_OR_DIFFERENT_OBJECT`.
- AUTOMATED_STAGE3_OUTCOME: `DEFER`; CURRENT_CANONICAL_TARGET: `none`.
- Possible existing canonical IDs (unresolved unless explicitly reused): `none`.
- CANDIDATE_SUMMARY: Colloidal Silica; candidate type `Material`; comparison scope `胶体二氧化硅抛光介质，不自动并入既有 Silica Powder/球硅。`; frozen candidate rationale: 胶体二氧化硅抛光介质，不自动并入既有 Silica Powder/球硅。
- WHY_HUMAN_REQUIRED: frozen Stage 3 mandatory review population; automated reasons: AMBIGUOUS_IDENTITY.
- RISK_FLAGS: A=AMBIGUOUS_IDENTITY, PROPOSED_OUTCOME_DIFFERS; B=none.

**AI REVIEW A**

- recommendation: CHALLENGE_AUTOMATION; native decision: `CREATE_NEW_CANONICAL`; target: `none`; confidence: MEDIUM; materiality: MEDIUM.
- reason: Colloidal Silica is a polishing dispersion and should remain distinct from the existing Silica Powder material.
- evidence assessment: SUMCO names colloidal silica as the mechano-chemical polishing medium; its physical form and use support the narrower material identity.
- temporal scope assessed: {'source_as_of': [None], 'publication_date': [None], 'identity_claim': 'candidate_only'}
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'distinct', 'object_type': 'compatible', 'scope': 'mismatch', 'granularity': 'different', 'quarantine': 'clear', 'ontology': 'compatible', 'evidence_sufficiency': 'sufficient', 'temporal': 'compatible'}

**AI REVIEW B**

- recommendation: CHALLENGE_AUTOMATION; native decision: `CREATE_NEW_CANONICAL`; target: `none`; confidence: HIGH; materiality: MEDIUM.
- reason: Colloidal silica is a dispersed polishing medium in starting-wafer mirror finishing, not silica powder or spherical silica; a distinct Material node is justified.
- evidence assessment: SC-EV-FD093A8B2A6553C4 from SC-P0-006_SUMCO_Silicon_Wafer_Production_Processes.pdf [source SC-PHYS-9E9CEFC24043585C; SHA 9e9cefc24043585c1c5a484340dcf49aa0725b341467942d3d4c34be0da8aee6; PDF p.4, Wafer forming process / Polishing]: The wafer surfaces are made perfectly flat and given a mirror finish by means of mechano-chemical polishing using colloidal silica. Boundary: Colloidal silica is a dispersed polishing medium in starting-wafer mirror finishing, not silica powder or spherical silica; a distinct Material node is justified. All source excerpts remain UNAUTHORIZED_CANDIDATE evidence.
- temporal scope assessed: not_established
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'distinct', 'object_type': 'compatible', 'scope': 'compatible', 'granularity': 'different', 'quarantine': 'clear', 'ontology': 'compatible', 'evidence_sufficiency': 'sufficient', 'temporal': 'compatible'}

**A/B RECONCILIATION**

- A_B_SUBSTANTIVE_AGREEMENT; disagreement type: none; native-operation conflict: false; target conflict: false.
- Interpretation differences: none.
- Reconciliation assessment: Both reviewers propose the same distinct candidate. Scope and granularity labels compare it with different reference objects, without changing the identity boundary.
- Non-material rubric-label differences retained for audit: scope.

**EVIDENCE SUMMARY**

- Source `SC-PHYS-9E9CEFC24043585C` (SHA-256 `9e9cefc24043585c1c5a484340dcf49aa0725b341467942d3d4c34be0da8aee6`), file `SC-P0-006_SUMCO_Silicon_Wafer_Production_Processes.pdf`, p. 4, section Wafer forming process / Polishing; evidence `SC-EV-FD093A8B2A6553C4`; as-of unknown; excerpt: “The wafer surfaces are made perfectly flat and given a mirror finish by means of mechano-chemical polishing using colloidal silica.”
- Temporal scope: source as-of dates above; no relation temporal claim.

- SYSTEM_RECOMMENDED_DECISION: `CREATE_NEW_CANONICAL`.
- SYSTEM_RECOMMENDATION_REASON: A/B substantive consensus; frozen automated outcome: DEFER.
- HUMAN_USER_DECISION = PENDING
- VALID NATIVE OPTIONS: REUSE_CANONICAL, CREATE_NEW_CANONICAL, KEEP_DOMAIN_SPECIFIC, DEFER, REJECT; REUSE requires an explicit validated target ID and all options remain subject to frozen controls.

### Item 006 — SC-CN-0146 — CoWoS

- ITEM_NUMBER: 6; ITEM_ID: `SC-CN-0146`; OBJECT_TYPE: identity.
- DOMAIN / context: `05_lithography_patterning` Semiconductor structured Foundation candidate against shared AI Hardware canonical catalog; cross-domain status: `GOVERNED_REUSE`.
- AUTOMATED_STAGE3_OUTCOME: `REUSE_CANONICAL`; CURRENT_CANONICAL_TARGET: `NODE_20260814_9B66BB15`.
- Possible existing canonical IDs (unresolved unless explicitly reused): `NODE_20260814_9B66BB15`.
- CANDIDATE_SUMMARY: CoWoS; candidate type `Technology`; comparison scope `复用当前Context Pack的active身份；保留ID、规范名和类型。`; frozen candidate rationale: 复用当前Context Pack的active身份；保留ID、规范名和类型。
- WHY_HUMAN_REQUIRED: frozen Stage 3 mandatory review population; automated reasons: EXACT_SHARED_CATALOG_IDENTITY.
- RISK_FLAGS: A=EXACT_SHARED_CATALOG_IDENTITY; B=none.

**AI REVIEW A**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `REUSE_CANONICAL`; target: `NODE_20260814_9B66BB15`; confidence: HIGH; materiality: HIGH.
- reason: CoWoS matches the active TSMC Technology exactly; vendor ownership stays in scope.
- evidence assessment: Interposer and annual-report evidence identifies TSMC CoWoS as the same packaging service, without implying generic industry ownership.
- temporal scope assessed: {'source_as_of': ['2025'], 'publication_date': [None], 'identity_claim': 'candidate_only'}
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'same', 'object_type': 'compatible', 'scope': 'compatible', 'granularity': 'same', 'quarantine': 'clear', 'ontology': 'compatible', 'evidence_sufficiency': 'sufficient', 'temporal': 'compatible'}

**AI REVIEW B**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `REUSE_CANONICAL`; target: `NODE_20260814_9B66BB15`; confidence: HIGH; materiality: LOW.
- reason: Exact active catalog identity: CoWoS to CoWoS; source uses the same Technology object.
- evidence assessment: SC-EV-A5D0D8DB04C96333 from SC-P0-010_2025_IRDS_Lithography_and_Patterning.pdf [source SC-PHYS-318D85A127B5B6DF; SHA 318d85a127b5b6dfa7b3c1330ae20b18d63660a1fa8c8bdfdd7b478844e145ed; PDF p.21, Packaging Lithography]: Interposers are used by TSMC (CoWoS) and others to integrate high-performance chips for AI and other applications. | SC-EV-BA8E4B43B6360938 from SC-P0-020B_TSMC_2025_Annual_Report.pdf [source F018b; SHA 3fb7ae4ad972aa2bc6e45bb36635152ad89d52f4a7165f389bcb94eeb54a6abd; PDF p.53, TSMC 3DFabric / CoWoS]: CoWoS® advanced packaging service integrates multiple system-on-chip (SoC) chips and the high-bandwidth memory (HBM) stacks to enhance HPC products with superior compute power and memory bandwidth. Boundary: Exact active catalog identity: CoWoS to CoWoS; source uses the same Technology object. All source excerpts remain UNAUTHORIZED_CANDIDATE evidence.
- temporal scope assessed: 2025
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'same', 'object_type': 'compatible', 'scope': 'compatible', 'granularity': 'same', 'quarantine': 'clear', 'ontology': 'compatible', 'evidence_sufficiency': 'sufficient', 'temporal': 'compatible'}

**A/B RECONCILIATION**

- A_B_SUBSTANTIVE_AGREEMENT; disagreement type: none; native-operation conflict: false; target conflict: false.
- Interpretation differences: none.
- Reconciliation assessment: Same native operation, target, and material interpretation.
- Non-material rubric-label differences retained for audit: none.

**EVIDENCE SUMMARY**

- Source `SC-PHYS-318D85A127B5B6DF` (SHA-256 `318d85a127b5b6dfa7b3c1330ae20b18d63660a1fa8c8bdfdd7b478844e145ed`), file `SC-P0-010_2025_IRDS_Lithography_and_Patterning.pdf`, p. 21, section Packaging Lithography; evidence `SC-EV-A5D0D8DB04C96333`; as-of 2025; excerpt: “Interposers are used by TSMC (CoWoS) and others to integrate high-performance chips for AI and other applications.”
- Source `F018b` (SHA-256 `3fb7ae4ad972aa2bc6e45bb36635152ad89d52f4a7165f389bcb94eeb54a6abd`), file `SC-P0-020B_TSMC_2025_Annual_Report.pdf`, p. 53, section TSMC 3DFabric / CoWoS; evidence `SC-EV-BA8E4B43B6360938`; as-of 2025; excerpt: “CoWoS® advanced packaging service integrates multiple system-on-chip (SoC) chips and the high-bandwidth memory (HBM) stacks to enhance HPC products with superior compute power and memory bandwidth.”
- Temporal scope: source as-of dates above; no relation temporal claim.

- SYSTEM_RECOMMENDED_DECISION: `REUSE_CANONICAL`.
- SYSTEM_RECOMMENDATION_REASON: A/B substantive consensus; frozen automated outcome: REUSE_CANONICAL.
- HUMAN_USER_DECISION = PENDING
- VALID NATIVE OPTIONS: REUSE_CANONICAL, CREATE_NEW_CANONICAL, KEEP_DOMAIN_SPECIFIC, DEFER, REJECT; REUSE requires an explicit validated target ID and all options remain subject to frozen controls.

### Item 007 — SC-CN-0149 — CoWoS-L

- ITEM_NUMBER: 7; ITEM_ID: `SC-CN-0149`; OBJECT_TYPE: identity.
- DOMAIN / context: `09_cross_domain_reuse` Semiconductor structured Foundation candidate against shared AI Hardware canonical catalog; cross-domain status: `GOVERNED_REUSE`.
- AUTOMATED_STAGE3_OUTCOME: `REUSE_CANONICAL`; CURRENT_CANONICAL_TARGET: `NODE_1A7F2D5816F5B7EE`.
- Possible existing canonical IDs (unresolved unless explicitly reused): `NODE_1A7F2D5816F5B7EE`.
- CANDIDATE_SUMMARY: CoWoS-L; candidate type `Technology`; comparison scope `复用当前Context Pack的active身份；保留ID、规范名和类型。`; frozen candidate rationale: 复用当前Context Pack的active身份；保留ID、规范名和类型。
- WHY_HUMAN_REQUIRED: frozen Stage 3 mandatory review population; automated reasons: EXACT_SHARED_CATALOG_IDENTITY.
- RISK_FLAGS: A=EXACT_SHARED_CATALOG_IDENTITY; B=none.

**AI REVIEW A**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `REUSE_CANONICAL`; target: `NODE_1A7F2D5816F5B7EE`; confidence: HIGH; materiality: MEDIUM.
- reason: CoWoS-L matches the current active variant rather than CoWoS-S or CoWoS-R; the older review does not supersede current identity.
- evidence assessment: TSMC describes the L branch with RDL interposer and LSI, features that distinguish this service variant.
- temporal scope assessed: {'source_as_of': ['2024', '2025'], 'publication_date': [None], 'identity_claim': 'candidate_only'}
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'same', 'object_type': 'compatible', 'scope': 'compatible', 'granularity': 'same', 'quarantine': 'clear', 'ontology': 'compatible', 'evidence_sufficiency': 'sufficient', 'temporal': 'compatible'}

**AI REVIEW B**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `REUSE_CANONICAL`; target: `NODE_1A7F2D5816F5B7EE`; confidence: HIGH; materiality: LOW.
- reason: Exact active catalog identity: CoWoS-L to CoWoS-L; source uses the same Technology object.
- evidence assessment: SC-EV-75CA7F58A25524DB from SC-P0-020A_TSMC_2024_Business_Overview.pdf [source F018; SHA 911b414a2af8f41b91b3a3e3afbccd300582d380748959541b7c60ff68e5bb92; PDF p.9, Technology Leadership / advanced packaging]: CoWoS-L improves product design flexibility by integrating a variety of embedded chips, while LSI with higher routing density and embedded deep trench capacitor facilitates the expansion of HPC products to larger sizes. | SC-EV-444CA37AE04D85CF from SC-P0-020B_TSMC_2025_Annual_Report.pdf [source F018b; SHA 3fb7ae4ad972aa2bc6e45bb36635152ad89d52f4a7165f389bcb94eeb54a6abd; PDF p.53, TSMC 3DFabric / CoWoS-L]: CoWoS®-L advanced packaging service enables larger HPC products by combining Chip on Wafer on Substrate with RDL-based interposer, higher density embedded local silicon interconnect (LSI), eDTC, and the integration of diverse embedded chips. | SC-EV-E2297FB1F53EF6D7 from SC-P0-020A_TSMC_2024_Business_Overview.pdf [source F018; SHA 911b414a2af8f41b91b3a3e3afbccd300582d380748959541b7c60ff68e5bb92; PDF p.9, Technology Leadership / advanced packaging]: CoWoS®-L technology, combining Chip on Wafer on Substrate with RDL-based interposer and embedded local silicon interconnect (LSI), started volume production in 2024. Boundary: Exact active catalog identity: CoWoS-L to CoWoS-L; source uses the same Technology object. All source excerpts remain UNAUTHORIZED_CANDIDATE evidence.
- temporal scope assessed: 2024
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'same', 'object_type': 'compatible', 'scope': 'compatible', 'granularity': 'same', 'quarantine': 'clear', 'ontology': 'compatible', 'evidence_sufficiency': 'sufficient', 'temporal': 'compatible'}

**A/B RECONCILIATION**

- A_B_SUBSTANTIVE_AGREEMENT; disagreement type: none; native-operation conflict: false; target conflict: false.
- Interpretation differences: none.
- Reconciliation assessment: Same native operation, target, and material interpretation.
- Non-material rubric-label differences retained for audit: none.

**EVIDENCE SUMMARY**

- Source `F018` (SHA-256 `911b414a2af8f41b91b3a3e3afbccd300582d380748959541b7c60ff68e5bb92`), file `SC-P0-020A_TSMC_2024_Business_Overview.pdf`, p. 9, section Technology Leadership / advanced packaging; evidence `SC-EV-75CA7F58A25524DB`; as-of 2024; excerpt: “CoWoS-L improves product design flexibility by integrating a variety of embedded chips, while LSI with higher routing density and embedded deep trench capacitor facilitates the expansion of HPC products to larger sizes.”
- Source `F018b` (SHA-256 `3fb7ae4ad972aa2bc6e45bb36635152ad89d52f4a7165f389bcb94eeb54a6abd`), file `SC-P0-020B_TSMC_2025_Annual_Report.pdf`, p. 53, section TSMC 3DFabric / CoWoS-L; evidence `SC-EV-444CA37AE04D85CF`; as-of 2025; excerpt: “CoWoS®-L advanced packaging service enables larger HPC products by combining Chip on Wafer on Substrate with RDL-based interposer, higher density embedded local silicon interconnect (LSI), eDTC, and the integration of diverse embedded chips.”
- Source `F018` (SHA-256 `911b414a2af8f41b91b3a3e3afbccd300582d380748959541b7c60ff68e5bb92`), file `SC-P0-020A_TSMC_2024_Business_Overview.pdf`, p. 9, section Technology Leadership / advanced packaging; evidence `SC-EV-E2297FB1F53EF6D7`; as-of 2024; excerpt: “CoWoS®-L technology, combining Chip on Wafer on Substrate with RDL-based interposer and embedded local silicon interconnect (LSI), started volume production in 2024.”
- Temporal scope: source as-of dates above; no relation temporal claim.

- SYSTEM_RECOMMENDED_DECISION: `REUSE_CANONICAL`.
- SYSTEM_RECOMMENDATION_REASON: A/B substantive consensus; frozen automated outcome: REUSE_CANONICAL.
- HUMAN_USER_DECISION = PENDING
- VALID NATIVE OPTIONS: REUSE_CANONICAL, CREATE_NEW_CANONICAL, KEEP_DOMAIN_SPECIFIC, DEFER, REJECT; REUSE requires an explicit validated target ID and all options remain subject to frozen controls.

### Item 008 — SC-CN-0148 — CoWoS®-R

- ITEM_NUMBER: 8; ITEM_ID: `SC-CN-0148`; OBJECT_TYPE: identity.
- DOMAIN / context: `09_cross_domain_reuse` Semiconductor structured Foundation candidate against shared AI Hardware canonical catalog; cross-domain status: `GOVERNED_REUSE`.
- AUTOMATED_STAGE3_OUTCOME: `DEFER`; CURRENT_CANONICAL_TARGET: `none`.
- Possible existing canonical IDs (unresolved unless explicitly reused): `none`.
- CANDIDATE_SUMMARY: CoWoS®-R; candidate type `Technology`; comparison scope `复用当前Context Pack的active身份；保留ID、规范名和类型。 ®仅作为同一TSMC标识内的商标排版符人工核对，不注册新别名。`; frozen candidate rationale: 复用当前Context Pack的active身份；保留ID、规范名和类型。 ®仅作为同一TSMC标识内的商标排版符人工核对，不注册新别名。
- WHY_HUMAN_REQUIRED: frozen Stage 3 mandatory review population; automated reasons: ALIAS_OR_DECORATION_REQUIRES_REVIEW, AMBIGUOUS_IDENTITY.
- RISK_FLAGS: A=ALIAS_OR_DECORATION_REQUIRES_REVIEW, AMBIGUOUS_IDENTITY, PROPOSED_OUTCOME_DIFFERS; B=FROZEN_STAGE2_DECISION, ALIAS_OR_TRANSLATION.

**AI REVIEW A**

- recommendation: CHALLENGE_AUTOMATION; native decision: `REUSE_CANONICAL`; target: `NODE_B7B4CB43F4C30F10`; confidence: MEDIUM; materiality: HIGH.
- reason: The exact CoWoS-R name appears inside TSMC's trademarked expression and points to the current active Technology; reuse can be approved without registering the decorated spelling as an alias.
- evidence assessment: The annual-report text explicitly writes CoWoS-R beside the redistribution-layer interposer description, supporting variant identity and architecture.
- temporal scope assessed: {'source_as_of': ['2025'], 'publication_date': [None], 'identity_claim': 'candidate_only'}
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'same', 'object_type': 'compatible', 'scope': 'compatible', 'granularity': 'same', 'quarantine': 'clear', 'ontology': 'compatible', 'evidence_sufficiency': 'sufficient', 'temporal': 'compatible'}

**AI REVIEW B**

- recommendation: CHALLENGE_AUTOMATION; native decision: `REUSE_CANONICAL`; target: `NODE_B7B4CB43F4C30F10`; confidence: MEDIUM; materiality: HIGH.
- reason: TSMC CoWoS®-R names the R variant of existing CoWoS-R; the registered mark decorates the brand. Reuse the listed node without silently registering an alias.
- evidence assessment: SC-EV-BE1EFC0405668731 from SC-P0-020B_TSMC_2025_Annual_Report.pdf [source F018b; SHA 3fb7ae4ad972aa2bc6e45bb36635152ad89d52f4a7165f389bcb94eeb54a6abd; PDF p.53, TSMC 3DFabric / CoWoS-R]: CoWoS® with redistribution layer interposer (CoWoS®-R) advanced packaging service, featuring multiple redistribution layers (RDL) to enable product design simplicity, supports larger HPC products. This technology entered its third year of volume production in 2025. Boundary: TSMC CoWoS®-R names the R variant of existing CoWoS-R; the registered mark decorates the brand. Reuse the listed node without silently registering an alias. All source excerpts remain UNAUTHORIZED_CANDIDATE evidence.
- temporal scope assessed: 2025
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'same', 'object_type': 'compatible', 'scope': 'compatible', 'granularity': 'same', 'quarantine': 'clear', 'ontology': 'compatible', 'evidence_sufficiency': 'sufficient', 'temporal': 'compatible'}

**A/B RECONCILIATION**

- A_B_SUBSTANTIVE_AGREEMENT; disagreement type: none; native-operation conflict: false; target conflict: false.
- Interpretation differences: none.
- Reconciliation assessment: Same native operation, target, and material interpretation.
- Non-material rubric-label differences retained for audit: none.

**EVIDENCE SUMMARY**

- Source `F018b` (SHA-256 `3fb7ae4ad972aa2bc6e45bb36635152ad89d52f4a7165f389bcb94eeb54a6abd`), file `SC-P0-020B_TSMC_2025_Annual_Report.pdf`, p. 53, section TSMC 3DFabric / CoWoS-R; evidence `SC-EV-BE1EFC0405668731`; as-of 2025; excerpt: “CoWoS® with redistribution layer interposer (CoWoS®-R) advanced packaging service, featuring multiple redistribution layers (RDL) to enable product design simplicity, supports larger HPC products. This technology entered its third year of volume production in 2025.”
- Temporal scope: source as-of dates above; no relation temporal claim.

- SYSTEM_RECOMMENDED_DECISION: `REUSE_CANONICAL`.
- SYSTEM_RECOMMENDATION_REASON: A/B substantive consensus; frozen automated outcome: DEFER.
- HUMAN_USER_DECISION = PENDING
- VALID NATIVE OPTIONS: REUSE_CANONICAL, CREATE_NEW_CANONICAL, KEEP_DOMAIN_SPECIFIC, DEFER, REJECT; REUSE requires an explicit validated target ID and all options remain subject to frozen controls.

### Item 009 — SC-CN-0147 — CoWoS®-S

- ITEM_NUMBER: 9; ITEM_ID: `SC-CN-0147`; OBJECT_TYPE: identity.
- DOMAIN / context: `09_cross_domain_reuse` Semiconductor structured Foundation candidate against shared AI Hardware canonical catalog; cross-domain status: `GOVERNED_REUSE`.
- AUTOMATED_STAGE3_OUTCOME: `DEFER`; CURRENT_CANONICAL_TARGET: `none`.
- Possible existing canonical IDs (unresolved unless explicitly reused): `none`.
- CANDIDATE_SUMMARY: CoWoS®-S; candidate type `Technology`; comparison scope `复用当前Context Pack的active身份；保留ID、规范名和类型。 ®仅作为同一TSMC标识内的商标排版符人工核对，不注册新别名。`; frozen candidate rationale: 复用当前Context Pack的active身份；保留ID、规范名和类型。 ®仅作为同一TSMC标识内的商标排版符人工核对，不注册新别名。
- WHY_HUMAN_REQUIRED: frozen Stage 3 mandatory review population; automated reasons: ALIAS_OR_DECORATION_REQUIRES_REVIEW, AMBIGUOUS_IDENTITY.
- RISK_FLAGS: A=ALIAS_OR_DECORATION_REQUIRES_REVIEW, AMBIGUOUS_IDENTITY, PROPOSED_OUTCOME_DIFFERS; B=ALIAS_OR_TRANSLATION.

**AI REVIEW A**

- recommendation: CHALLENGE_AUTOMATION; native decision: `REUSE_CANONICAL`; target: `NODE_3E0E5604C3F64891`; confidence: MEDIUM; materiality: HIGH.
- reason: The exact CoWoS-S name appears in TSMC's parenthetical label for its silicon-interposer branch; trademark decoration need not create another node.
- evidence assessment: The source names CoWoS-S and describes its silicon interposer; it supports this active variant, not the broader CoWoS family alone.
- temporal scope assessed: {'source_as_of': ['2025'], 'publication_date': [None], 'identity_claim': 'candidate_only'}
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'same', 'object_type': 'compatible', 'scope': 'compatible', 'granularity': 'same', 'quarantine': 'clear', 'ontology': 'compatible', 'evidence_sufficiency': 'sufficient', 'temporal': 'compatible'}

**AI REVIEW B**

- recommendation: CHALLENGE_AUTOMATION; native decision: `REUSE_CANONICAL`; target: `NODE_3E0E5604C3F64891`; confidence: MEDIUM; materiality: HIGH.
- reason: TSMC CoWoS®-S names the S silicon-interposer variant of existing CoWoS-S; the trademark glyph does not change vendor, suffix, type, or granularity.
- evidence assessment: SC-EV-A5D5D8057F31DBE3 from SC-P0-020B_TSMC_2025_Annual_Report.pdf [source F018b; SHA 3fb7ae4ad972aa2bc6e45bb36635152ad89d52f4a7165f389bcb94eeb54a6abd; PDF p.53, TSMC 3DFabric / CoWoS-S]: CoWoS® with silicon interposer (CoWoS®-S) advanced packaging service features high interconnect routing density and embedded deep trench capacitor (eDTC) and has been in volume production for several years. Boundary: TSMC CoWoS®-S names the S silicon-interposer variant of existing CoWoS-S; the trademark glyph does not change vendor, suffix, type, or granularity. All source excerpts remain UNAUTHORIZED_CANDIDATE evidence.
- temporal scope assessed: 2025
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'same', 'object_type': 'compatible', 'scope': 'compatible', 'granularity': 'same', 'quarantine': 'clear', 'ontology': 'compatible', 'evidence_sufficiency': 'sufficient', 'temporal': 'compatible'}

**A/B RECONCILIATION**

- A_B_SUBSTANTIVE_AGREEMENT; disagreement type: none; native-operation conflict: false; target conflict: false.
- Interpretation differences: none.
- Reconciliation assessment: Same native operation, target, and material interpretation.
- Non-material rubric-label differences retained for audit: none.

**EVIDENCE SUMMARY**

- Source `F018b` (SHA-256 `3fb7ae4ad972aa2bc6e45bb36635152ad89d52f4a7165f389bcb94eeb54a6abd`), file `SC-P0-020B_TSMC_2025_Annual_Report.pdf`, p. 53, section TSMC 3DFabric / CoWoS-S; evidence `SC-EV-A5D5D8057F31DBE3`; as-of 2025; excerpt: “CoWoS® with silicon interposer (CoWoS®-S) advanced packaging service features high interconnect routing density and embedded deep trench capacitor (eDTC) and has been in volume production for several years.”
- Temporal scope: source as-of dates above; no relation temporal claim.

- SYSTEM_RECOMMENDED_DECISION: `REUSE_CANONICAL`.
- SYSTEM_RECOMMENDATION_REASON: A/B substantive consensus; frozen automated outcome: DEFER.
- HUMAN_USER_DECISION = PENDING
- VALID NATIVE OPTIONS: REUSE_CANONICAL, CREATE_NEW_CANONICAL, KEEP_DOMAIN_SPECIFIC, DEFER, REJECT; REUSE requires an explicit validated target ID and all options remain subject to frozen controls.

### Item 010 — SC-CN-0143 — Diamond Thermal Material

- ITEM_NUMBER: 10; ITEM_ID: `SC-CN-0143`; OBJECT_TYPE: identity.
- DOMAIN / context: `08_assembly_packaging` Semiconductor structured Foundation candidate against shared AI Hardware canonical catalog; cross-domain status: `REVIEW_REQUIRED`.
- AUTOMATED_STAGE3_OUTCOME: `DEFER`; CURRENT_CANONICAL_TARGET: `none`.
- Possible existing canonical IDs (unresolved unless explicitly reused): `none`.
- CANDIDATE_SUMMARY: Diamond Thermal Material; candidate type `Material`; comparison scope `历史DEFER保持；文中为潜在替代方案，未证实部署。`; frozen candidate rationale: 历史DEFER保持；文中为潜在替代方案，未证实部署。
- WHY_HUMAN_REQUIRED: frozen Stage 3 mandatory review population; automated reasons: AMBIGUOUS_IDENTITY, FROZEN_STAGE2_HUMAN_DECISION.
- RISK_FLAGS: A=AMBIGUOUS_IDENTITY, FROZEN_STAGE2_HUMAN_DECISION; B=FROZEN_STAGE2_DECISION, UNRESOLVED_IDENTITY, EVIDENCE_LIMIT.

**AI REVIEW A**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `DEFER`; target: `none`; confidence: HIGH; materiality: HIGH.
- reason: Diamond Thermal Material remains a Phase 1 deferred proposal; a possible Si-handler replacement does not establish deployed material identity or lift that decision.
- evidence assessment: HIR frames diamond as a material that would need processable 300 mm wafers, so the passage is conditional rather than evidence of use.
- temporal scope assessed: {'source_as_of': ['2026-03'], 'publication_date': ['2026-03'], 'identity_claim': 'candidate_only'}
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'ambiguous', 'object_type': 'unknown', 'scope': 'unknown', 'granularity': 'unknown', 'quarantine': 'clear', 'ontology': 'compatible', 'evidence_sufficiency': 'limited', 'temporal': 'unresolved'}

**AI REVIEW B**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `DEFER`; target: `none`; confidence: MEDIUM; materiality: MEDIUM.
- reason: Diamond is only a possible high-conductivity Si-handler replacement requiring processable 300 mm wafers. It does not establish deployment; preserve Stage 2 DEFER.
- evidence assessment: SC-EV-6C7A98013D4B2FCF from SC-P0-018_2025_HIR_Materials_and_Interfaces_Advanced_Packaging.pdf [source SC-PHYS-2E34AF6DD70E8C2C; SHA 2e34af6dd70e8c2c5de2aaabec15837693d1322abc0bb5820475188cd028a3f2; PDF p.20, 2.3.2 3DIC Chip Stack Materials]: For BSPDN, swapping the Si handler with a high k material like SiC or diamond would need 300mm wafers that can be processed through the fab. Boundary: Diamond is only a possible high-conductivity Si-handler replacement requiring processable 300 mm wafers. It does not establish deployment; preserve Stage 2 DEFER. All source excerpts remain UNAUTHORIZED_CANDIDATE evidence.
- temporal scope assessed: 2026-03
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'ambiguous', 'object_type': 'unknown', 'scope': 'unknown', 'granularity': 'unknown', 'quarantine': 'preserved', 'ontology': 'unresolved', 'evidence_sufficiency': 'limited', 'temporal': 'unresolved'}

**A/B RECONCILIATION**

- A_B_SUBSTANTIVE_AGREEMENT; disagreement type: none; native-operation conflict: false; target conflict: false.
- Interpretation differences: none.
- Reconciliation assessment: Both reviewers preserve the same governed hold. Rubric labels distinguish source support for a concept from sufficiency for canonical admission.
- Non-material rubric-label differences retained for audit: ontology, quarantine.

**EVIDENCE SUMMARY**

- Source `SC-PHYS-2E34AF6DD70E8C2C` (SHA-256 `2e34af6dd70e8c2c5de2aaabec15837693d1322abc0bb5820475188cd028a3f2`), file `SC-P0-018_2025_HIR_Materials_and_Interfaces_Advanced_Packaging.pdf`, p. 20, section 2.3.2 3DIC Chip Stack Materials; evidence `SC-EV-6C7A98013D4B2FCF`; as-of 2026-03; excerpt: “For BSPDN, swapping the Si handler with a high k material like SiC or diamond would need 300mm wafers that can be processed through the fab.”
- Temporal scope: source as-of dates above; no relation temporal claim.

- SYSTEM_RECOMMENDED_DECISION: `DEFER`.
- SYSTEM_RECOMMENDATION_REASON: Frozen structural, Stage 2 decision, evidence, or temporal exception remains unresolved.
- HUMAN_USER_DECISION = PENDING
- VALID NATIVE OPTIONS: REUSE_CANONICAL, CREATE_NEW_CANONICAL, KEEP_DOMAIN_SPECIFIC, DEFER, REJECT; REUSE requires an explicit validated target ID and all options remain subject to frozen controls.

### Item 011 — SC-CN-0010 — Dynamic Random-Access Memory

- ITEM_NUMBER: 11; ITEM_ID: `SC-CN-0010`; OBJECT_TYPE: identity.
- DOMAIN / context: `00_industry_structure` Semiconductor structured Foundation candidate against shared AI Hardware canonical catalog; cross-domain status: `DISTINCT_BROADER_OR_DIFFERENT_OBJECT`.
- AUTOMATED_STAGE3_OUTCOME: `DEFER`; CURRENT_CANONICAL_TARGET: `none`.
- Possible existing canonical IDs (unresolved unless explicitly reused): `none`.
- CANDIDATE_SUMMARY: Dynamic Random-Access Memory; candidate type `Product`; comparison scope `通用 DRAM 不等于既有 Server DRAM 或 HBM。`; frozen candidate rationale: 通用 DRAM 不等于既有 Server DRAM 或 HBM。
- WHY_HUMAN_REQUIRED: frozen Stage 3 mandatory review population; automated reasons: AMBIGUOUS_IDENTITY, FROZEN_STAGE2_HUMAN_DECISION.
- RISK_FLAGS: A=AMBIGUOUS_IDENTITY, FROZEN_STAGE2_HUMAN_DECISION; B=FROZEN_STAGE2_DECISION, UNRESOLVED_IDENTITY.

**AI REVIEW A**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `DEFER`; target: `none`; confidence: HIGH; materiality: HIGH.
- reason: General DRAM is broader than Server DRAM and HBM; the frozen Stage 2 DEFER remains binding pending a separate granularity decision.
- evidence assessment: SIA/BCG explains ordinary DRAM's processor-memory function, but supplies no basis to merge it into a server or HBM subtype.
- temporal scope assessed: {'source_as_of': ['2021-04'], 'publication_date': ['2021-04'], 'identity_claim': 'candidate_only'}
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'ambiguous', 'object_type': 'compatible', 'scope': 'mismatch', 'granularity': 'different', 'quarantine': 'clear', 'ontology': 'compatible', 'evidence_sufficiency': 'sufficient', 'temporal': 'compatible'}

**AI REVIEW B**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `DEFER`; target: `none`; confidence: MEDIUM; materiality: MEDIUM.
- reason: Generic DRAM covers more than Server DRAM and HBM; the source definition does not select a canonical level. Preserve Stage 2 DEFER.
- evidence assessment: SC-EV-9F7D3244A0780DEA from SC-P0-002_SIA_BCG_Global_Semiconductor_Supply_Chain_2021.pdf [source SC-PHYS-B33C40EBCB5756F7; SHA b33c40ebcb5756f76e887ba2664f97736252e68ba7bfbedc2d628ce2d7cbc08d; PDF p.9, Memory]: DRAM is used to store the data or program code needed by a computer processor to function. Boundary: Generic DRAM covers more than Server DRAM and HBM; the source definition does not select a canonical level. Preserve Stage 2 DEFER. All source excerpts remain UNAUTHORIZED_CANDIDATE evidence.
- temporal scope assessed: 2021-04
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'ambiguous', 'object_type': 'unknown', 'scope': 'mismatch', 'granularity': 'different', 'quarantine': 'preserved', 'ontology': 'unresolved', 'evidence_sufficiency': 'limited', 'temporal': 'compatible'}

**A/B RECONCILIATION**

- A_B_SUBSTANTIVE_AGREEMENT; disagreement type: none; native-operation conflict: false; target conflict: false.
- Interpretation differences: none.
- Reconciliation assessment: Both reviewers preserve the same governed hold. Rubric labels distinguish source support for a concept from sufficiency for canonical admission.
- Non-material rubric-label differences retained for audit: evidence_sufficiency, object_type, ontology, quarantine.

**EVIDENCE SUMMARY**

- Source `SC-PHYS-B33C40EBCB5756F7` (SHA-256 `b33c40ebcb5756f76e887ba2664f97736252e68ba7bfbedc2d628ce2d7cbc08d`), file `SC-P0-002_SIA_BCG_Global_Semiconductor_Supply_Chain_2021.pdf`, p. 9, section Memory; evidence `SC-EV-9F7D3244A0780DEA`; as-of 2021-04; excerpt: “DRAM is used to store the data or program code needed by a computer processor to function.”
- Temporal scope: source as-of dates above; no relation temporal claim.

- SYSTEM_RECOMMENDED_DECISION: `DEFER`.
- SYSTEM_RECOMMENDATION_REASON: Frozen structural, Stage 2 decision, evidence, or temporal exception remains unresolved.
- HUMAN_USER_DECISION = PENDING
- VALID NATIVE OPTIONS: REUSE_CANONICAL, CREATE_NEW_CANONICAL, KEEP_DOMAIN_SPECIFIC, DEFER, REJECT; REUSE requires an explicit validated target ID and all options remain subject to frozen controls.

### Item 012 — SC-CN-0077 — Semiconductor Electrical Test Equipment

- ITEM_NUMBER: 12; ITEM_ID: `SC-CN-0077`; OBJECT_TYPE: identity.
- DOMAIN / context: `03_fab_process_equipment` Semiconductor structured Foundation candidate against shared AI Hardware canonical catalog; cross-domain status: `DISTINCT_BROADER_OR_DIFFERENT_OBJECT`.
- AUTOMATED_STAGE3_OUTCOME: `CREATE_NEW_CANONICAL`; CURRENT_CANONICAL_TARGET: `NODE_DBDB929B816162A6`.
- Possible existing canonical IDs (unresolved unless explicitly reused): `none`.
- CANDIDATE_SUMMARY: Semiconductor Electrical Test Equipment; candidate type `Equipment`; comparison scope `通用电学测试设备；不是光器件 Burn-In 设备。`; frozen candidate rationale: 通用电学测试设备；不是光器件 Burn-In 设备。
- WHY_HUMAN_REQUIRED: frozen Stage 3 mandatory review population; automated reasons: NEW_CANONICAL_NODE, NO_SHARED_CATALOG_MATCH.
- RISK_FLAGS: A=NEW_CANONICAL_NODE, NO_SHARED_CATALOG_MATCH; B=none.

**AI REVIEW A**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `CREATE_NEW_CANONICAL`; target: `NODE_DBDB929B816162A6`; confidence: MEDIUM; materiality: MEDIUM.
- reason: Semiconductor Electrical Test Equipment is a wafer-test equipment category, separate from optical burn-in equipment.
- evidence assessment: SIA describes an automated computer-driven wafer chip test system; the generic equipment label is supported, though the exact name is normalized.
- temporal scope assessed: {'source_as_of': ['2026-03-04'], 'publication_date': ['2026-03-04'], 'identity_claim': 'candidate_only'}
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'distinct', 'object_type': 'compatible', 'scope': 'compatible', 'granularity': 'unknown', 'quarantine': 'clear', 'ontology': 'compatible', 'evidence_sufficiency': 'sufficient', 'temporal': 'compatible'}

**AI REVIEW B**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `CREATE_NEW_CANONICAL`; target: `NODE_DBDB929B816162A6`; confidence: HIGH; materiality: LOW.
- reason: An automatic computer-driven wafer test system is Equipment distinct from optical burn-in equipment; no exact shared identity is retrieved.
- evidence assessment: SC-EV-B2A0CD10691438AE from SC-P0-008_Senate-EPW-testimony-3.4.2026.pdf [source SC-PHYS-C5B6DC633E156218; SHA c5b6dc633e156218eb950f2dee88f43fbdcc4fc1744a5924f12b977f5cb7df71; PDF p.5, II / Electrical Test]: Electrical Test: An automatic, computer-driven test system checks the functionality of each chip on the wafer. Chips that do not pass are marked for automatic rejection. Boundary: An automatic computer-driven wafer test system is Equipment distinct from optical burn-in equipment; no exact shared identity is retrieved. All source excerpts remain UNAUTHORIZED_CANDIDATE evidence.
- temporal scope assessed: 2026-03-04
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'distinct', 'object_type': 'compatible', 'scope': 'compatible', 'granularity': 'different', 'quarantine': 'clear', 'ontology': 'compatible', 'evidence_sufficiency': 'sufficient', 'temporal': 'compatible'}

**A/B RECONCILIATION**

- A_B_SUBSTANTIVE_AGREEMENT; disagreement type: none; native-operation conflict: false; target conflict: false.
- Interpretation differences: none.
- Reconciliation assessment: Both reviewers propose the same distinct candidate. Scope and granularity labels compare it with different reference objects, without changing the identity boundary.
- Non-material rubric-label differences retained for audit: granularity.

**EVIDENCE SUMMARY**

- Source `SC-PHYS-C5B6DC633E156218` (SHA-256 `c5b6dc633e156218eb950f2dee88f43fbdcc4fc1744a5924f12b977f5cb7df71`), file `SC-P0-008_Senate-EPW-testimony-3.4.2026.pdf`, p. 5, section II / Electrical Test; evidence `SC-EV-B2A0CD10691438AE`; as-of 2026-03-04; excerpt: “Electrical Test: An automatic, computer-driven test system checks the functionality of each chip on the wafer. Chips that do not pass are marked for automatic rejection.”
- Temporal scope: source as-of dates above; no relation temporal claim.

- SYSTEM_RECOMMENDED_DECISION: `CREATE_NEW_CANONICAL`.
- SYSTEM_RECOMMENDATION_REASON: A/B substantive consensus; frozen automated outcome: CREATE_NEW_CANONICAL.
- HUMAN_USER_DECISION = PENDING
- VALID NATIVE OPTIONS: REUSE_CANONICAL, CREATE_NEW_CANONICAL, KEEP_DOMAIN_SPECIFIC, DEFER, REJECT; REUSE requires an explicit validated target ID and all options remain subject to frozen controls.

### Item 013 — SC-CN-0082 — Packaging Encapsulant

- ITEM_NUMBER: 13; ITEM_ID: `SC-CN-0082`; OBJECT_TYPE: identity.
- DOMAIN / context: `03_fab_process_equipment` Semiconductor structured Foundation candidate against shared AI Hardware canonical catalog; cross-domain status: `REVIEW_REQUIRED`.
- AUTOMATED_STAGE3_OUTCOME: `DEFER`; CURRENT_CANONICAL_TARGET: `none`.
- Possible existing canonical IDs (unresolved unless explicitly reused): `none`.
- CANDIDATE_SUMMARY: Packaging Encapsulant; candidate type `Material`; comparison scope `伞形功能材料；含 underfill/coatings/mold compounds，不能等同 Epoxy Molding Compound。`; frozen candidate rationale: 伞形功能材料；含 underfill/coatings/mold compounds，不能等同 Epoxy Molding Compound。
- WHY_HUMAN_REQUIRED: frozen Stage 3 mandatory review population; automated reasons: AMBIGUOUS_IDENTITY.
- RISK_FLAGS: A=AMBIGUOUS_IDENTITY, PROPOSED_OUTCOME_DIFFERS; B=FROZEN_STAGE2_DECISION, SCOPE_OR_TYPE_BOUNDARY.

**AI REVIEW A**

- recommendation: CHALLENGE_AUTOMATION; native decision: `CREATE_NEW_CANONICAL`; target: `none`; confidence: MEDIUM; materiality: HIGH.
- reason: Packaging Encapsulant is a parent material class covering underfill, coatings, and molding compounds; it cannot reuse Epoxy Molding Compound.
- evidence assessment: The source lists several encapsulant forms used to protect package connections, directly supporting the wider class and its child distinction.
- temporal scope assessed: {'source_as_of': ['2026-03-04'], 'publication_date': ['2026-03-04'], 'identity_claim': 'candidate_only'}
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'distinct', 'object_type': 'compatible', 'scope': 'mismatch', 'granularity': 'different', 'quarantine': 'clear', 'ontology': 'compatible', 'evidence_sufficiency': 'sufficient', 'temporal': 'compatible'}

**AI REVIEW B**

- recommendation: CHALLENGE_AUTOMATION; native decision: `CREATE_NEW_CANONICAL`; target: `none`; confidence: LOW; materiality: MEDIUM.
- reason: Packaging encapsulant is an umbrella protection-material class containing underfill, coatings, and mold compounds. Stage 2 CREATE supports a distinct class, not an epoxy molding compound merge.
- evidence assessment: SC-EV-7C75F6F0987ACA80 from SC-P0-008_Senate-EPW-testimony-3.4.2026.pdf [source SC-PHYS-C5B6DC633E156218; SHA c5b6dc633e156218eb950f2dee88f43fbdcc4fc1744a5924f12b977f5cb7df71; PDF p.6, II / Packaging]: To protect against humidity, chemicals, and vibration, connections are enclosed with encapsulants such as underfill, coatings, or mold compounds. Boundary: Packaging encapsulant is an umbrella protection-material class containing underfill, coatings, and mold compounds. Stage 2 CREATE supports a distinct class, not an epoxy molding compound merge. All source excerpts remain UNAUTHORIZED_CANDIDATE evidence.
- temporal scope assessed: 2026-03-04
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'distinct', 'object_type': 'compatible', 'scope': 'compatible', 'granularity': 'different', 'quarantine': 'clear', 'ontology': 'pressure', 'evidence_sufficiency': 'sufficient', 'temporal': 'compatible'}

**A/B RECONCILIATION**

- A_B_SUBSTANTIVE_AGREEMENT; disagreement type: none; native-operation conflict: false; target conflict: false.
- Interpretation differences: none.
- Reconciliation assessment: Both reviewers propose the same distinct candidate. Scope and granularity labels compare it with different reference objects, without changing the identity boundary.
- Non-material rubric-label differences retained for audit: ontology, scope.

**EVIDENCE SUMMARY**

- Source `SC-PHYS-C5B6DC633E156218` (SHA-256 `c5b6dc633e156218eb950f2dee88f43fbdcc4fc1744a5924f12b977f5cb7df71`), file `SC-P0-008_Senate-EPW-testimony-3.4.2026.pdf`, p. 6, section II / Packaging; evidence `SC-EV-7C75F6F0987ACA80`; as-of 2026-03-04; excerpt: “To protect against humidity, chemicals, and vibration, connections are enclosed with encapsulants such as underfill, coatings, or mold compounds.”
- Temporal scope: source as-of dates above; no relation temporal claim.

- SYSTEM_RECOMMENDED_DECISION: `CREATE_NEW_CANONICAL`.
- SYSTEM_RECOMMENDATION_REASON: A/B substantive consensus; frozen automated outcome: DEFER.
- HUMAN_USER_DECISION = PENDING
- VALID NATIVE OPTIONS: REUSE_CANONICAL, CREATE_NEW_CANONICAL, KEEP_DOMAIN_SPECIFIC, DEFER, REJECT; REUSE requires an explicit validated target ID and all options remain subject to frozen controls.

### Item 014 — SC-CN-0159 — Glass Core Substrate

- ITEM_NUMBER: 14; ITEM_ID: `SC-CN-0159`; OBJECT_TYPE: identity.
- DOMAIN / context: `08_assembly_packaging` Semiconductor structured Foundation candidate against shared AI Hardware canonical catalog; cross-domain status: `QUARANTINED`.
- AUTOMATED_STAGE3_OUTCOME: `DEFER`; CURRENT_CANONICAL_TARGET: `none`.
- Possible existing canonical IDs (unresolved unless explicitly reused): `none`.
- CANDIDATE_SUMMARY: Glass Core Substrate; candidate type `Material`; comparison scope `PHASE1_1A CROSS_DOMAIN_QUARANTINE；Figure1仅提出材料位置，不授权新身份或量产结论。`; frozen candidate rationale: PHASE1_1A CROSS_DOMAIN_QUARANTINE；Figure1仅提出材料位置，不授权新身份或量产结论。
- WHY_HUMAN_REQUIRED: frozen Stage 3 mandatory review population; automated reasons: AMBIGUOUS_IDENTITY, FROZEN_STAGE2_HUMAN_DECISION, HISTORICAL_QUARANTINE.
- RISK_FLAGS: A=AMBIGUOUS_IDENTITY, FROZEN_STAGE2_HUMAN_DECISION, HISTORICAL_QUARANTINE; B=FROZEN_STAGE2_DECISION, UNRESOLVED_IDENTITY, HISTORICAL_QUARANTINE, EVIDENCE_LIMIT.

**AI REVIEW A**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `DEFER`; target: `none`; confidence: HIGH; materiality: HIGH.
- reason: Glass Core Substrate is historically quarantined and the frozen Stage 2 DEFER must remain until an explicit release decision.
- evidence assessment: The HIR figure only locates a proposed glass-core material; it cannot establish adoption or override quarantine.
- temporal scope assessed: {'source_as_of': ['2026-03'], 'publication_date': ['2026-03'], 'identity_claim': 'candidate_only'}
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'ambiguous', 'object_type': 'unknown', 'scope': 'unknown', 'granularity': 'unknown', 'quarantine': 'preserved', 'ontology': 'compatible', 'evidence_sufficiency': 'limited', 'temporal': 'unresolved'}

**AI REVIEW B**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `DEFER`; target: `none`; confidence: MEDIUM; materiality: HIGH.
- reason: Glass Core Substrate appears as a figure label only; historical cross-domain quarantine and absent deployment evidence bar activation.
- evidence assessment: SC-EV-7FF5E762CAC4DB05 from SC-P0-018_2025_HIR_Materials_and_Interfaces_Advanced_Packaging.pdf [source SC-PHYS-2E34AF6DD70E8C2C; SHA 2e34af6dd70e8c2c5de2aaabec15837693d1322abc0bb5820475188cd028a3f2; PDF p.2, Overview of key materials and interfaces]: Glass Core Substrate Boundary: Glass Core Substrate appears as a figure label only; historical cross-domain quarantine and absent deployment evidence bar activation. All source excerpts remain UNAUTHORIZED_CANDIDATE evidence.
- temporal scope assessed: 2026-03
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'ambiguous', 'object_type': 'unknown', 'scope': 'unknown', 'granularity': 'unknown', 'quarantine': 'preserved', 'ontology': 'unresolved', 'evidence_sufficiency': 'limited', 'temporal': 'unresolved'}

**A/B RECONCILIATION**

- A_B_SUBSTANTIVE_AGREEMENT; disagreement type: none; native-operation conflict: false; target conflict: false.
- Interpretation differences: none.
- Reconciliation assessment: Both reviewers preserve the same governed hold. Rubric labels distinguish source support for a concept from sufficiency for canonical admission.
- Non-material rubric-label differences retained for audit: ontology.

**EVIDENCE SUMMARY**

- Source `SC-PHYS-2E34AF6DD70E8C2C` (SHA-256 `2e34af6dd70e8c2c5de2aaabec15837693d1322abc0bb5820475188cd028a3f2`), file `SC-P0-018_2025_HIR_Materials_and_Interfaces_Advanced_Packaging.pdf`, p. 2, section Overview of key materials and interfaces; evidence `SC-EV-7FF5E762CAC4DB05`; as-of 2026-03; excerpt: “Glass Core Substrate”
- Temporal scope: source as-of dates above; no relation temporal claim.

- SYSTEM_RECOMMENDED_DECISION: `DEFER`.
- SYSTEM_RECOMMENDATION_REASON: Frozen structural, Stage 2 decision, evidence, or temporal exception remains unresolved.
- HUMAN_USER_DECISION = PENDING
- VALID NATIVE OPTIONS: REUSE_CANONICAL, CREATE_NEW_CANONICAL, KEEP_DOMAIN_SPECIFIC, DEFER, REJECT; REUSE requires an explicit validated target ID and all options remain subject to frozen controls.

### Item 015 — SC-CN-0138 — HBM

- ITEM_NUMBER: 15; ITEM_ID: `SC-CN-0138`; OBJECT_TYPE: identity.
- DOMAIN / context: `08_assembly_packaging` Semiconductor structured Foundation candidate against shared AI Hardware canonical catalog; cross-domain status: `GOVERNED_REUSE`.
- AUTOMATED_STAGE3_OUTCOME: `REUSE_CANONICAL`; CURRENT_CANONICAL_TARGET: `NODE_20260817_6A9A657D`.
- Possible existing canonical IDs (unresolved unless explicitly reused): `NODE_20260817_6A9A657D`.
- CANDIDATE_SUMMARY: HBM; candidate type `Product`; comparison scope `复用当前Context Pack的active身份；保留ID、规范名和类型。`; frozen candidate rationale: 复用当前Context Pack的active身份；保留ID、规范名和类型。
- WHY_HUMAN_REQUIRED: frozen Stage 3 mandatory review population; automated reasons: EXACT_SHARED_CATALOG_IDENTITY.
- RISK_FLAGS: A=EXACT_SHARED_CATALOG_IDENTITY; B=ALIAS_OR_TRANSLATION.

**AI REVIEW A**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `REUSE_CANONICAL`; target: `NODE_20260817_6A9A657D`; confidence: HIGH; materiality: HIGH.
- reason: High Bandwidth Memory aligns with the registered HBM alias and active Product node; it is not generic DRAM.
- evidence assessment: IRDS describes HBM optimized for stacked dies, confirming the specialized product scope represented by the alias.
- temporal scope assessed: {'source_as_of': ['2020', '2025'], 'publication_date': [None], 'identity_claim': 'candidate_only'}
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'same', 'object_type': 'compatible', 'scope': 'compatible', 'granularity': 'same', 'quarantine': 'clear', 'ontology': 'compatible', 'evidence_sufficiency': 'sufficient', 'temporal': 'compatible'}

**AI REVIEW B**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `REUSE_CANONICAL`; target: `NODE_20260817_6A9A657D`; confidence: MEDIUM; materiality: LOW.
- reason: Exact active catalog identity: HBM to High Bandwidth Memory; source uses the same Product object.
- evidence assessment: SC-EV-EFC0887512104389 from SC-P0-017_2020_IRDS_Packaging_Integration.pdf [source SC-PHYS-54CABB8879E180A7; SHA 54cabb8879e180a7a0363e8964cb2d28735eff03ecee6a45905cd54f06eae5e2; PDF p.16, 3D Stacks / HBM]: Under these conditions new high bandwidth memories (HBM) have been optimized for 3D die stacking (Figure PI-6). | SC-EV-BA8E4B43B6360938 from SC-P0-020B_TSMC_2025_Annual_Report.pdf [source F018b; SHA 3fb7ae4ad972aa2bc6e45bb36635152ad89d52f4a7165f389bcb94eeb54a6abd; PDF p.53, TSMC 3DFabric / CoWoS]: CoWoS® advanced packaging service integrates multiple system-on-chip (SoC) chips and the high-bandwidth memory (HBM) stacks to enhance HPC products with superior compute power and memory bandwidth. Boundary: Exact active catalog identity: HBM to High Bandwidth Memory; source uses the same Product object. All source excerpts remain UNAUTHORIZED_CANDIDATE evidence.
- temporal scope assessed: 2020
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'same', 'object_type': 'compatible', 'scope': 'compatible', 'granularity': 'same', 'quarantine': 'clear', 'ontology': 'compatible', 'evidence_sufficiency': 'sufficient', 'temporal': 'compatible'}

**A/B RECONCILIATION**

- A_B_SUBSTANTIVE_AGREEMENT; disagreement type: none; native-operation conflict: false; target conflict: false.
- Interpretation differences: none.
- Reconciliation assessment: Same native operation, target, and material interpretation.
- Non-material rubric-label differences retained for audit: none.

**EVIDENCE SUMMARY**

- Source `SC-PHYS-54CABB8879E180A7` (SHA-256 `54cabb8879e180a7a0363e8964cb2d28735eff03ecee6a45905cd54f06eae5e2`), file `SC-P0-017_2020_IRDS_Packaging_Integration.pdf`, p. 16, section 3D Stacks / HBM; evidence `SC-EV-EFC0887512104389`; as-of 2020; excerpt: “Under these conditions new high bandwidth memories (HBM) have been optimized for 3D die stacking (Figure PI-6).”
- Source `F018b` (SHA-256 `3fb7ae4ad972aa2bc6e45bb36635152ad89d52f4a7165f389bcb94eeb54a6abd`), file `SC-P0-020B_TSMC_2025_Annual_Report.pdf`, p. 53, section TSMC 3DFabric / CoWoS; evidence `SC-EV-BA8E4B43B6360938`; as-of 2025; excerpt: “CoWoS® advanced packaging service integrates multiple system-on-chip (SoC) chips and the high-bandwidth memory (HBM) stacks to enhance HPC products with superior compute power and memory bandwidth.”
- Temporal scope: source as-of dates above; no relation temporal claim.

- SYSTEM_RECOMMENDED_DECISION: `REUSE_CANONICAL`.
- SYSTEM_RECOMMENDATION_REASON: A/B substantive consensus; frozen automated outcome: REUSE_CANONICAL.
- HUMAN_USER_DECISION = PENDING
- VALID NATIVE OPTIONS: REUSE_CANONICAL, CREATE_NEW_CANONICAL, KEEP_DOMAIN_SPECIFIC, DEFER, REJECT; REUSE requires an explicit validated target ID and all options remain subject to frozen controls.

### Item 016 — SC-CN-0140 — Hybrid Bonding

- ITEM_NUMBER: 16; ITEM_ID: `SC-CN-0140`; OBJECT_TYPE: identity.
- DOMAIN / context: `08_assembly_packaging` Semiconductor structured Foundation candidate against shared AI Hardware canonical catalog; cross-domain status: `GOVERNED_REUSE`.
- AUTOMATED_STAGE3_OUTCOME: `REUSE_CANONICAL`; CURRENT_CANONICAL_TARGET: `NODE_20260817_6ABA49BC`.
- Possible existing canonical IDs (unresolved unless explicitly reused): `NODE_20260817_6ABA49BC`.
- CANDIDATE_SUMMARY: Hybrid Bonding; candidate type `Technology`; comparison scope `复用当前Context Pack的active身份；保留ID、规范名和类型。`; frozen candidate rationale: 复用当前Context Pack的active身份；保留ID、规范名和类型。
- WHY_HUMAN_REQUIRED: frozen Stage 3 mandatory review population; automated reasons: EXACT_SHARED_CATALOG_IDENTITY.
- RISK_FLAGS: A=EXACT_SHARED_CATALOG_IDENTITY; B=none.

**AI REVIEW A**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `REUSE_CANONICAL`; target: `NODE_20260817_6ABA49BC`; confidence: HIGH; materiality: MEDIUM.
- reason: Hybrid Bonding is an exact active Technology match with no type or granularity shift.
- evidence assessment: HIR defines combined metal and dielectric bonding interfaces, directly fitting the existing technology object.
- temporal scope assessed: {'source_as_of': ['2026-03'], 'publication_date': ['2026-03'], 'identity_claim': 'candidate_only'}
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'same', 'object_type': 'compatible', 'scope': 'compatible', 'granularity': 'same', 'quarantine': 'clear', 'ontology': 'compatible', 'evidence_sufficiency': 'sufficient', 'temporal': 'compatible'}

**AI REVIEW B**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `REUSE_CANONICAL`; target: `NODE_20260817_6ABA49BC`; confidence: HIGH; materiality: LOW.
- reason: Exact active catalog identity: Hybrid Bonding to Hybrid Bonding; source uses the same Technology object.
- evidence assessment: SC-EV-98C39E1AB621ADE6 from SC-P0-018_2025_HIR_Materials_and_Interfaces_Advanced_Packaging.pdf [source SC-PHYS-2E34AF6DD70E8C2C; SHA 2e34af6dd70e8c2c5de2aaabec15837693d1322abc0bb5820475188cd028a3f2; PDF p.12, 2.2.3.3 Hybrid Bonding Materials and Processes]: Hybrid bonding combines metal–metal (typically Cu–Cu) and dielectric–dielectric (e.g., SiO₂, SiCN, polymer) interfaces, enabling simultaneous electrical and mechanical connections at sub-micron pitches. Boundary: Exact active catalog identity: Hybrid Bonding to Hybrid Bonding; source uses the same Technology object. All source excerpts remain UNAUTHORIZED_CANDIDATE evidence.
- temporal scope assessed: 2026-03
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'same', 'object_type': 'compatible', 'scope': 'compatible', 'granularity': 'same', 'quarantine': 'clear', 'ontology': 'compatible', 'evidence_sufficiency': 'sufficient', 'temporal': 'compatible'}

**A/B RECONCILIATION**

- A_B_SUBSTANTIVE_AGREEMENT; disagreement type: none; native-operation conflict: false; target conflict: false.
- Interpretation differences: none.
- Reconciliation assessment: Same native operation, target, and material interpretation.
- Non-material rubric-label differences retained for audit: none.

**EVIDENCE SUMMARY**

- Source `SC-PHYS-2E34AF6DD70E8C2C` (SHA-256 `2e34af6dd70e8c2c5de2aaabec15837693d1322abc0bb5820475188cd028a3f2`), file `SC-P0-018_2025_HIR_Materials_and_Interfaces_Advanced_Packaging.pdf`, p. 12, section 2.2.3.3 Hybrid Bonding Materials and Processes; evidence `SC-EV-98C39E1AB621ADE6`; as-of 2026-03; excerpt: “Hybrid bonding combines metal–metal (typically Cu–Cu) and dielectric–dielectric (e.g., SiO₂, SiCN, polymer) interfaces, enabling simultaneous electrical and mechanical connections at sub-micron pitches.”
- Temporal scope: source as-of dates above; no relation temporal claim.

- SYSTEM_RECOMMENDED_DECISION: `REUSE_CANONICAL`.
- SYSTEM_RECOMMENDATION_REASON: A/B substantive consensus; frozen automated outcome: REUSE_CANONICAL.
- HUMAN_USER_DECISION = PENDING
- VALID NATIVE OPTIONS: REUSE_CANONICAL, CREATE_NEW_CANONICAL, KEEP_DOMAIN_SPECIFIC, DEFER, REJECT; REUSE requires an explicit validated target ID and all options remain subject to frozen controls.

### Item 017 — SC-CN-0115 — Semiconductor Metrology

- ITEM_NUMBER: 17; ITEM_ID: `SC-CN-0115`; OBJECT_TYPE: identity.
- DOMAIN / context: `06_metrology_yield_factory` Semiconductor structured Foundation candidate against shared AI Hardware canonical catalog; cross-domain status: `DISTINCT_BROADER_OR_DIFFERENT_OBJECT`.
- AUTOMATED_STAGE3_OUTCOME: `DEFER`; CURRENT_CANONICAL_TARGET: `none`.
- Possible existing canonical IDs (unresolved unless explicitly reused): `none`.
- CANDIDATE_SUMMARY: Semiconductor Metrology; candidate type `Technology`; comparison scope `测量方法/功能域；不与半导体计量Equipment混型。`; frozen candidate rationale: 测量方法/功能域；不与半导体计量Equipment混型。
- WHY_HUMAN_REQUIRED: frozen Stage 3 mandatory review population; automated reasons: AMBIGUOUS_IDENTITY.
- RISK_FLAGS: A=AMBIGUOUS_IDENTITY, PROPOSED_OUTCOME_DIFFERS; B=FROZEN_STAGE2_DECISION, SCOPE_OR_TYPE_BOUNDARY.

**AI REVIEW A**

- recommendation: CHALLENGE_AUTOMATION; native decision: `CREATE_NEW_CANONICAL`; target: `none`; confidence: MEDIUM; materiality: MEDIUM.
- reason: Semiconductor Metrology is a measurement technology/function domain, distinct from Advanced Packaging 3D Metrology Equipment.
- evidence assessment: IRDS enumerates CD, 3D, overlay and front-end measurements; it supports a broad method domain but not a specific equipment identity.
- temporal scope assessed: {'source_as_of': ['2024', '2021-04'], 'publication_date': [None, '2021-04'], 'identity_claim': 'candidate_only'}
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'distinct', 'object_type': 'mismatch', 'scope': 'mismatch', 'granularity': 'different', 'quarantine': 'clear', 'ontology': 'compatible', 'evidence_sufficiency': 'sufficient', 'temporal': 'compatible'}

**AI REVIEW B**

- recommendation: CHALLENGE_AUTOMATION; native decision: `CREATE_NEW_CANONICAL`; target: `none`; confidence: MEDIUM; materiality: MEDIUM.
- reason: The roadmap lists dimension, overlay, materials, and interconnect measurement methods. This Technology differs from metrology Equipment; retain Stage 2 CREATE.
- evidence assessment: SC-EV-4AAF8C92F8CF20F0 from SC-P0-011_2024_IRDS_Metrology.pdf [source SC-PHYS-AEDD7CB34D12EF15; SHA aedd7cb34d12ef15b799ed9a0f6326840a4551ddc7c6600732c6ae82ab6e93b6; PDF p.10, 2 Scope of Report]: The scope includes metrology for critical dimensions (CDs), microscopy for 3D and high aspect ratio (HAR) pattern measurements, overlay measurements, lithography metrology, front-end processes metrology, on-chip interconnect metrology, inter- and intra-die interconnect metrology, materials characterization, metrology for emerging materials and devices, re... | SC-EV-8641CA42AE8B686A from SC-P0-002_SIA_BCG_Global_Semiconductor_Supply_Chain_2021.pdf [source SC-PHYS-B33C40EBCB5756F7; SHA b33c40ebcb5756f76e887ba2664f97736252e68ba7bfbedc2d628ce2d7cbc08d; PDF p.20, Wafer processing and testing equipment]: Strict metrology and inspection processes using specialized equipment are therefore established at critical points of the semiconductor manufacturing process to ensure that a certain yield can be confirmed and maintained. Boundary: The roadmap lists dimension, overlay, materials, and interconnect measurement methods. This Technology differs from metrology Equipment; retain Stage 2 CREATE. All source excerpts remain UNAUTHORIZED_CANDIDATE evidence.
- temporal scope assessed: 2024
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'distinct', 'object_type': 'mismatch', 'scope': 'compatible', 'granularity': 'different', 'quarantine': 'clear', 'ontology': 'compatible', 'evidence_sufficiency': 'sufficient', 'temporal': 'compatible'}

**A/B RECONCILIATION**

- A_B_SUBSTANTIVE_AGREEMENT; disagreement type: none; native-operation conflict: false; target conflict: false.
- Interpretation differences: none.
- Reconciliation assessment: Both reviewers propose the same distinct candidate. Scope and granularity labels compare it with different reference objects, without changing the identity boundary.
- Non-material rubric-label differences retained for audit: scope.

**EVIDENCE SUMMARY**

- Source `SC-PHYS-AEDD7CB34D12EF15` (SHA-256 `aedd7cb34d12ef15b799ed9a0f6326840a4551ddc7c6600732c6ae82ab6e93b6`), file `SC-P0-011_2024_IRDS_Metrology.pdf`, p. 10, section 2 Scope of Report; evidence `SC-EV-4AAF8C92F8CF20F0`; as-of 2024; excerpt: “The scope includes metrology for critical dimensions (CDs), microscopy for 3D and high aspect ratio (HAR) pattern measurements, overlay measurements, lithography metrology, front-end processes metrology, on-chip interconnect metrology, inter- and intra-die interconnect metrology, materials characterization, metrology for emerging materials and devices, reference materials, and outside systems conn…”
- Source `SC-PHYS-B33C40EBCB5756F7` (SHA-256 `b33c40ebcb5756f76e887ba2664f97736252e68ba7bfbedc2d628ce2d7cbc08d`), file `SC-P0-002_SIA_BCG_Global_Semiconductor_Supply_Chain_2021.pdf`, p. 20, section Wafer processing and testing equipment; evidence `SC-EV-8641CA42AE8B686A`; as-of 2021-04; excerpt: “Strict metrology and inspection processes using specialized equipment are therefore established at critical points of the semiconductor manufacturing process to ensure that a certain yield can be confirmed and maintained.”
- Temporal scope: source as-of dates above; no relation temporal claim.

- SYSTEM_RECOMMENDED_DECISION: `CREATE_NEW_CANONICAL`.
- SYSTEM_RECOMMENDATION_REASON: A/B substantive consensus; frozen automated outcome: DEFER.
- HUMAN_USER_DECISION = PENDING
- VALID NATIVE OPTIONS: REUSE_CANONICAL, CREATE_NEW_CANONICAL, KEEP_DOMAIN_SPECIFIC, DEFER, REJECT; REUSE requires an explicit validated target ID and all options remain subject to frozen controls.

### Item 018 — SC-CN-0011 — NAND Flash

- ITEM_NUMBER: 18; ITEM_ID: `SC-CN-0011`; OBJECT_TYPE: identity.
- DOMAIN / context: `00_industry_structure` Semiconductor structured Foundation candidate against shared AI Hardware canonical catalog; cross-domain status: `QUARANTINED`.
- AUTOMATED_STAGE3_OUTCOME: `DEFER`; CURRENT_CANONICAL_TARGET: `none`.
- Possible existing canonical IDs (unresolved unless explicitly reused): `none`.
- CANDIDATE_SUMMARY: NAND Flash; candidate type `Product`; comparison scope `PHASE1_1A CROSS_DOMAIN_QUARANTINE；本批只提交半导体证据，不自行解除历史隔离。`; frozen candidate rationale: PHASE1_1A CROSS_DOMAIN_QUARANTINE；本批只提交半导体证据，不自行解除历史隔离。
- WHY_HUMAN_REQUIRED: frozen Stage 3 mandatory review population; automated reasons: AMBIGUOUS_IDENTITY, FROZEN_STAGE2_HUMAN_DECISION, HISTORICAL_QUARANTINE.
- RISK_FLAGS: A=AMBIGUOUS_IDENTITY, FROZEN_STAGE2_HUMAN_DECISION, HISTORICAL_QUARANTINE; B=FROZEN_STAGE2_DECISION, UNRESOLVED_IDENTITY, HISTORICAL_QUARANTINE.

**AI REVIEW A**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `DEFER`; target: `none`; confidence: HIGH; materiality: HIGH.
- reason: NAND Flash has a Phase 1 cross-domain quarantine and Stage 2 DEFER; taxonomy evidence does not release either control.
- evidence assessment: SIA/BCG distinguishes NAND's persistent storage from DRAM, but identity admission remains governed by the prior quarantine.
- temporal scope assessed: {'source_as_of': ['2021-04'], 'publication_date': ['2021-04'], 'identity_claim': 'candidate_only'}
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'ambiguous', 'object_type': 'unknown', 'scope': 'unknown', 'granularity': 'unknown', 'quarantine': 'preserved', 'ontology': 'compatible', 'evidence_sufficiency': 'sufficient', 'temporal': 'compatible'}

**AI REVIEW B**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `DEFER`; target: `none`; confidence: MEDIUM; materiality: HIGH.
- reason: NAND Flash is a named nonvolatile product, but historical cross-domain quarantine remains binding despite this explanatory excerpt.
- evidence assessment: SC-EV-80E21D50198799F6 from SC-P0-002_SIA_BCG_Global_Semiconductor_Supply_Chain_2021.pdf [source SC-PHYS-B33C40EBCB5756F7; SHA b33c40ebcb5756f76e887ba2664f97736252e68ba7bfbedc2d628ce2d7cbc08d; PDF p.9, Memory]: NAND is the most common type of flash memory. Unlike DRAM, it does not need power to retain data, so it is used for permanent storage. Boundary: NAND Flash is a named nonvolatile product, but historical cross-domain quarantine remains binding despite this explanatory excerpt. All source excerpts remain UNAUTHORIZED_CANDIDATE evidence.
- temporal scope assessed: 2021-04
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'ambiguous', 'object_type': 'unknown', 'scope': 'unknown', 'granularity': 'unknown', 'quarantine': 'preserved', 'ontology': 'unresolved', 'evidence_sufficiency': 'limited', 'temporal': 'compatible'}

**A/B RECONCILIATION**

- A_B_SUBSTANTIVE_AGREEMENT; disagreement type: none; native-operation conflict: false; target conflict: false.
- Interpretation differences: none.
- Reconciliation assessment: Both reviewers preserve the same governed hold. Rubric labels distinguish source support for a concept from sufficiency for canonical admission.
- Non-material rubric-label differences retained for audit: evidence_sufficiency, ontology.

**EVIDENCE SUMMARY**

- Source `SC-PHYS-B33C40EBCB5756F7` (SHA-256 `b33c40ebcb5756f76e887ba2664f97736252e68ba7bfbedc2d628ce2d7cbc08d`), file `SC-P0-002_SIA_BCG_Global_Semiconductor_Supply_Chain_2021.pdf`, p. 9, section Memory; evidence `SC-EV-80E21D50198799F6`; as-of 2021-04; excerpt: “NAND is the most common type of flash memory. Unlike DRAM, it does not need power to retain data, so it is used for permanent storage.”
- Temporal scope: source as-of dates above; no relation temporal claim.

- SYSTEM_RECOMMENDED_DECISION: `DEFER`.
- SYSTEM_RECOMMENDATION_REASON: Frozen structural, Stage 2 decision, evidence, or temporal exception remains unresolved.
- HUMAN_USER_DECISION = PENDING
- VALID NATIVE OPTIONS: REUSE_CANONICAL, CREATE_NEW_CANONICAL, KEEP_DOMAIN_SPECIFIC, DEFER, REJECT; REUSE requires an explicit validated target ID and all options remain subject to frozen controls.

### Item 019 — SC-CN-0102 — NOR Flash

- ITEM_NUMBER: 19; ITEM_ID: `SC-CN-0102`; OBJECT_TYPE: identity.
- DOMAIN / context: `04_device_scaling_memory` Semiconductor structured Foundation candidate against shared AI Hardware canonical catalog; cross-domain status: `GOVERNED_REUSE`.
- AUTOMATED_STAGE3_OUTCOME: `REUSE_CANONICAL`; CURRENT_CANONICAL_TARGET: `NODE_15BC05D614287450`.
- Possible existing canonical IDs (unresolved unless explicitly reused): `NODE_15BC05D614287450`.
- CANDIDATE_SUMMARY: NOR Flash; candidate type `Product`; comparison scope `复用当前Context Pack的active身份；保留ID、规范名和类型。`; frozen candidate rationale: 复用当前Context Pack的active身份；保留ID、规范名和类型。
- WHY_HUMAN_REQUIRED: frozen Stage 3 mandatory review population; automated reasons: EXACT_SHARED_CATALOG_IDENTITY.
- RISK_FLAGS: A=EXACT_SHARED_CATALOG_IDENTITY; B=none.

**AI REVIEW A**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `REUSE_CANONICAL`; target: `NODE_15BC05D614287450`; confidence: HIGH; materiality: MEDIUM.
- reason: NOR Flash matches the active Product identity and is distinct from NAND Flash.
- evidence assessment: IRDS lists NOR as one Flash Memory category, corroborating the name without changing its node boundary.
- temporal scope assessed: {'source_as_of': ['2024'], 'publication_date': [None], 'identity_claim': 'candidate_only'}
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'same', 'object_type': 'compatible', 'scope': 'compatible', 'granularity': 'same', 'quarantine': 'clear', 'ontology': 'compatible', 'evidence_sufficiency': 'sufficient', 'temporal': 'compatible'}

**AI REVIEW B**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `REUSE_CANONICAL`; target: `NODE_15BC05D614287450`; confidence: HIGH; materiality: LOW.
- reason: Exact active catalog identity: NOR Flash to NOR Flash; source uses the same Product object.
- evidence assessment: SC-EV-288A875770100378 from SC-P0-009_2024_IRDS_More_Moore.pdf [source SC-PHYS-49A1D3B42E458985; SHA 49a1d3b42e45898555490e602170876e22d1ccf8d7c17711e436d8db36322fa6; PDF p.27, 5 Nonvolatile Memory]: Nonvolatile memory may be divided into two large categories—Flash memories (NAND Flash and NOR Flash), and non-charge-based-storage memories. Boundary: Exact active catalog identity: NOR Flash to NOR Flash; source uses the same Product object. All source excerpts remain UNAUTHORIZED_CANDIDATE evidence.
- temporal scope assessed: 2024
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'same', 'object_type': 'compatible', 'scope': 'compatible', 'granularity': 'same', 'quarantine': 'clear', 'ontology': 'compatible', 'evidence_sufficiency': 'sufficient', 'temporal': 'compatible'}

**A/B RECONCILIATION**

- A_B_SUBSTANTIVE_AGREEMENT; disagreement type: none; native-operation conflict: false; target conflict: false.
- Interpretation differences: none.
- Reconciliation assessment: Same native operation, target, and material interpretation.
- Non-material rubric-label differences retained for audit: none.

**EVIDENCE SUMMARY**

- Source `SC-PHYS-49A1D3B42E458985` (SHA-256 `49a1d3b42e45898555490e602170876e22d1ccf8d7c17711e436d8db36322fa6`), file `SC-P0-009_2024_IRDS_More_Moore.pdf`, p. 27, section 5 Nonvolatile Memory; evidence `SC-EV-288A875770100378`; as-of 2024; excerpt: “Nonvolatile memory may be divided into two large categories—Flash memories (NAND Flash and NOR Flash), and non-charge-based-storage memories.”
- Temporal scope: source as-of dates above; no relation temporal claim.

- SYSTEM_RECOMMENDED_DECISION: `REUSE_CANONICAL`.
- SYSTEM_RECOMMENDATION_REASON: A/B substantive consensus; frozen automated outcome: REUSE_CANONICAL.
- HUMAN_USER_DECISION = PENDING
- VALID NATIVE OPTIONS: REUSE_CANONICAL, CREATE_NEW_CANONICAL, KEEP_DOMAIN_SPECIFIC, DEFER, REJECT; REUSE requires an explicit validated target ID and all options remain subject to frozen controls.

### Item 020 — SC-CN-0052 — Photoresist

- ITEM_NUMBER: 20; ITEM_ID: `SC-CN-0052`; OBJECT_TYPE: identity.
- DOMAIN / context: `00_industry_structure` Semiconductor structured Foundation candidate against shared AI Hardware canonical catalog; cross-domain status: `DISTINCT_BROADER_OR_DIFFERENT_OBJECT`.
- AUTOMATED_STAGE3_OUTCOME: `DEFER`; CURRENT_CANONICAL_TARGET: `none`.
- Possible existing canonical IDs (unresolved unless explicitly reused): `none`.
- CANDIDATE_SUMMARY: Photoresist; candidate type `Material`; comparison scope `通用光刻胶；不同于 Advanced Packaging Photoresist，也不同于 Photoresist Resin 组分。`; frozen candidate rationale: 通用光刻胶；不同于 Advanced Packaging Photoresist，也不同于 Photoresist Resin 组分。
- WHY_HUMAN_REQUIRED: frozen Stage 3 mandatory review population; automated reasons: AMBIGUOUS_IDENTITY.
- RISK_FLAGS: A=AMBIGUOUS_IDENTITY, PROPOSED_OUTCOME_DIFFERS; B=FROZEN_STAGE2_DECISION, SCOPE_OR_TYPE_BOUNDARY.

**AI REVIEW A**

- recommendation: CHALLENGE_AUTOMATION; native decision: `CREATE_NEW_CANONICAL`; target: `none`; confidence: MEDIUM; materiality: HIGH.
- reason: Generic Photoresist is broader than Advanced Packaging Photoresist and different from Photoresist Resin, its component; Stage 2 already favored creation.
- evidence assessment: SIA/BCG and ASML describe resist used in general lithography and positive/negative forms, enough to ground the parent material class.
- temporal scope assessed: {'source_as_of': ['2021-04', '2023-10-04'], 'publication_date': ['2021-04', '2023-10-04'], 'identity_claim': 'candidate_only'}
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'distinct', 'object_type': 'compatible', 'scope': 'mismatch', 'granularity': 'different', 'quarantine': 'clear', 'ontology': 'compatible', 'evidence_sufficiency': 'sufficient', 'temporal': 'compatible'}

**AI REVIEW B**

- recommendation: CHALLENGE_AUTOMATION; native decision: `CREATE_NEW_CANONICAL`; target: `none`; confidence: MEDIUM; materiality: MEDIUM.
- reason: The excerpt defines generic wafer-lithography photoresist. That Material class is broader than packaging resist and differs from photoresist resin; retain Stage 2 CREATE.
- evidence assessment: SC-EV-B569E06E885DA787 from SC-P0-002_SIA_BCG_Global_Semiconductor_Supply_Chain_2021.pdf [source SC-PHYS-B33C40EBCB5756F7; SHA b33c40ebcb5756f76e887ba2664f97736252e68ba7bfbedc2d628ce2d7cbc08d; PDF p.22, Materials]: Photoresist: A special material that undergoes a chemical reaction upon exposure to light. Silicon wafers are covered with a photoresist layer, which is imprinted with the patterns contained in the photomask during the lithography process. | SC-EV-5A701F864F4A7C10 from SC-P0-007_ASML_Six_Semiconductor_Manufacturing_Steps.pdf [source SC-PHYS-87B4665C30781057; SHA 87b4665c3078105792ca70f18964c938976b72f2dcf0d19379b034d5d6f205f9; PDF p.3, Photoresist coating]: The wafer is then covered with a light-sensitive coating called 'photoresist', or 'resist' for short. There are two types of resist: positive and negative. Boundary: The excerpt defines generic wafer-lithography photoresist. That Material class is broader than packaging resist and differs from photoresist resin; retain Stage 2 CREATE. All source excerpts remain UNAUTHORIZED_CANDIDATE evidence.
- temporal scope assessed: 2021-04
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'distinct', 'object_type': 'compatible', 'scope': 'compatible', 'granularity': 'different', 'quarantine': 'clear', 'ontology': 'compatible', 'evidence_sufficiency': 'sufficient', 'temporal': 'compatible'}

**A/B RECONCILIATION**

- A_B_SUBSTANTIVE_AGREEMENT; disagreement type: none; native-operation conflict: false; target conflict: false.
- Interpretation differences: none.
- Reconciliation assessment: Both reviewers propose the same distinct candidate. Scope and granularity labels compare it with different reference objects, without changing the identity boundary.
- Non-material rubric-label differences retained for audit: scope.

**EVIDENCE SUMMARY**

- Source `SC-PHYS-B33C40EBCB5756F7` (SHA-256 `b33c40ebcb5756f76e887ba2664f97736252e68ba7bfbedc2d628ce2d7cbc08d`), file `SC-P0-002_SIA_BCG_Global_Semiconductor_Supply_Chain_2021.pdf`, p. 22, section Materials; evidence `SC-EV-B569E06E885DA787`; as-of 2021-04; excerpt: “Photoresist: A special material that undergoes a chemical reaction upon exposure to light. Silicon wafers are covered with a photoresist layer, which is imprinted with the patterns contained in the photomask during the lithography process.”
- Source `SC-PHYS-87B4665C30781057` (SHA-256 `87b4665c3078105792ca70f18964c938976b72f2dcf0d19379b034d5d6f205f9`), file `SC-P0-007_ASML_Six_Semiconductor_Manufacturing_Steps.pdf`, p. 3, section Photoresist coating; evidence `SC-EV-5A701F864F4A7C10`; as-of 2023-10-04; excerpt: “The wafer is then covered with a light-sensitive coating called 'photoresist', or 'resist' for short. There are two types of resist: positive and negative.”
- Temporal scope: source as-of dates above; no relation temporal claim.

- SYSTEM_RECOMMENDED_DECISION: `CREATE_NEW_CANONICAL`.
- SYSTEM_RECOMMENDATION_REASON: A/B substantive consensus; frozen automated outcome: DEFER.
- HUMAN_USER_DECISION = PENDING
- VALID NATIVE OPTIONS: REUSE_CANONICAL, CREATE_NEW_CANONICAL, KEEP_DOMAIN_SPECIFIC, DEFER, REJECT; REUSE requires an explicit validated target ID and all options remain subject to frozen controls.

### Item 021 — SC-CN-0135 — Photonic Integrated Circuit

- ITEM_NUMBER: 21; ITEM_ID: `SC-CN-0135`; OBJECT_TYPE: identity.
- DOMAIN / context: `07_more_than_moore` Semiconductor structured Foundation candidate against shared AI Hardware canonical catalog; cross-domain status: `REVIEW_REQUIRED`.
- AUTOMATED_STAGE3_OUTCOME: `DEFER`; CURRENT_CANONICAL_TARGET: `none`.
- Possible existing canonical IDs (unresolved unless explicitly reused): `none`.
- CANDIDATE_SUMMARY: Photonic Integrated Circuit; candidate type `Product`; comparison scope `通用PIC范围比Silicon Photonics PIC宽，不能直接复用硅光PIC。`; frozen candidate rationale: 通用PIC范围比Silicon Photonics PIC宽，不能直接复用硅光PIC。
- WHY_HUMAN_REQUIRED: frozen Stage 3 mandatory review population; automated reasons: AMBIGUOUS_IDENTITY, FROZEN_STAGE2_HUMAN_DECISION.
- RISK_FLAGS: A=AMBIGUOUS_IDENTITY, FROZEN_STAGE2_HUMAN_DECISION; B=FROZEN_STAGE2_DECISION, UNRESOLVED_IDENTITY, EVIDENCE_LIMIT.

**AI REVIEW A**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `DEFER`; target: `none`; confidence: HIGH; materiality: HIGH.
- reason: Photonic Integrated Circuit spans more materials than Silicon Photonics PIC, and the frozen Stage 2 DEFER should hold.
- evidence assessment: The source discusses integrated lasers and modulators in transmitter circuits, but does not settle a generic PIC-to-silicon PIC mapping.
- temporal scope assessed: {'source_as_of': ['2024'], 'publication_date': [None], 'identity_claim': 'candidate_only'}
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'ambiguous', 'object_type': 'compatible', 'scope': 'mismatch', 'granularity': 'different', 'quarantine': 'clear', 'ontology': 'compatible', 'evidence_sufficiency': 'limited', 'temporal': 'compatible'}

**AI REVIEW B**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `DEFER`; target: `none`; confidence: LOW; materiality: MEDIUM.
- reason: The excerpt concerns laser integration or separate packaging in transmitter circuits; it does not define generic Photonic Integrated Circuit or equate it with Silicon Photonics PIC.
- evidence assessment: SC-EV-09CB838BE857196B from SC-P0-015_2024_IRDS_Outside_System_Connectivity.pdf [source SC-PHYS-EECFB29D71F7359F; SHA eecfb29d71f7359fccc255f854e9efe7262f82f06fad04ee56ecb871cf6defee; PDF p.40, 6.2.1 Photonic Monolithic Heterogeneous Integrated Circuits]: Some of these transmitter circuits have the lasers integrated with the modulators, while some of these have the laser packaged separately from the modulators. Boundary: The excerpt concerns laser integration or separate packaging in transmitter circuits; it does not define generic Photonic Integrated Circuit or equate it with Silicon Photonics PIC. All source excerpts remain UNAUTHORIZED_CANDIDATE evidence.
- temporal scope assessed: 2024
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'ambiguous', 'object_type': 'unknown', 'scope': 'mismatch', 'granularity': 'different', 'quarantine': 'preserved', 'ontology': 'unresolved', 'evidence_sufficiency': 'insufficient', 'temporal': 'compatible'}

**A/B RECONCILIATION**

- A_B_SUBSTANTIVE_AGREEMENT; disagreement type: none; native-operation conflict: false; target conflict: false.
- Interpretation differences: none.
- Reconciliation assessment: Both reviewers preserve the same governed hold. Rubric labels distinguish source support for a concept from sufficiency for canonical admission.
- Non-material rubric-label differences retained for audit: evidence_sufficiency, object_type, ontology, quarantine.

**EVIDENCE SUMMARY**

- Source `SC-PHYS-EECFB29D71F7359F` (SHA-256 `eecfb29d71f7359fccc255f854e9efe7262f82f06fad04ee56ecb871cf6defee`), file `SC-P0-015_2024_IRDS_Outside_System_Connectivity.pdf`, p. 40, section 6.2.1 Photonic Monolithic Heterogeneous Integrated Circuits; evidence `SC-EV-09CB838BE857196B`; as-of 2024; excerpt: “Some of these transmitter circuits have the lasers integrated with the modulators, while some of these have the laser packaged separately from the modulators.”
- Temporal scope: source as-of dates above; no relation temporal claim.

- SYSTEM_RECOMMENDED_DECISION: `DEFER`.
- SYSTEM_RECOMMENDATION_REASON: Frozen structural, Stage 2 decision, evidence, or temporal exception remains unresolved.
- HUMAN_USER_DECISION = PENDING
- VALID NATIVE OPTIONS: REUSE_CANONICAL, CREATE_NEW_CANONICAL, KEEP_DOMAIN_SPECIFIC, DEFER, REJECT; REUSE requires an explicit validated target ID and all options remain subject to frozen controls.

### Item 022 — SC-CN-0132 — Power Electronics

- ITEM_NUMBER: 22; ITEM_ID: `SC-CN-0132`; OBJECT_TYPE: identity.
- DOMAIN / context: `07_more_than_moore` Semiconductor structured Foundation candidate against shared AI Hardware canonical catalog; cross-domain status: `DISTINCT_BROADER_OR_DIFFERENT_OBJECT`.
- AUTOMATED_STAGE3_OUTCOME: `DEFER`; CURRENT_CANONICAL_TARGET: `none`.
- Possible existing canonical IDs (unresolved unless explicitly reused): `none`.
- CANDIDATE_SUMMARY: Power Electronics; candidate type `Technology`; comparison scope `电能变换/控制技术，不等同Power Semiconductor产业段。`; frozen candidate rationale: 电能变换/控制技术，不等同Power Semiconductor产业段。
- WHY_HUMAN_REQUIRED: frozen Stage 3 mandatory review population; automated reasons: AMBIGUOUS_IDENTITY.
- RISK_FLAGS: A=AMBIGUOUS_IDENTITY, PROPOSED_OUTCOME_DIFFERS; B=SCOPE_OR_TYPE_BOUNDARY.

**AI REVIEW A**

- recommendation: CHALLENGE_AUTOMATION; native decision: `CREATE_NEW_CANONICAL`; target: `none`; confidence: MEDIUM; materiality: MEDIUM.
- reason: Power Electronics is a conversion/control Technology, not the Power Semiconductor segment; this warrants a distinct object.
- evidence assessment: IRDS directly defines power electronics as energy conversion, control and conditioning technology.
- temporal scope assessed: {'source_as_of': ['2022'], 'publication_date': [None], 'identity_claim': 'candidate_only'}
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'distinct', 'object_type': 'mismatch', 'scope': 'mismatch', 'granularity': 'different', 'quarantine': 'clear', 'ontology': 'compatible', 'evidence_sufficiency': 'sufficient', 'temporal': 'compatible'}

**AI REVIEW B**

- recommendation: CHALLENGE_AUTOMATION; native decision: `CREATE_NEW_CANONICAL`; target: `none`; confidence: MEDIUM; materiality: MEDIUM.
- reason: Power Electronics is defined as energy conversion and control Technology, distinct from the Power Semiconductor industry segment; a separate node is supported.
- evidence assessment: SC-EV-A72108B7E930E34C from SC-P0-014_2022_IRDS_More_Than_Moore.pdf [source SC-PHYS-59E90A8C09249A8D; SHA 59e90a8c09249a8dc75f53f661f4f0eff511b9eb65fbc1a1c70ffb363d8166c8; PDF p.19, 3 Smart Energy / Introduction]: Power electronics is the technology associated with the efficient conversion, control and conditioning of electric energy from the source to the load. Boundary: Power Electronics is defined as energy conversion and control Technology, distinct from the Power Semiconductor industry segment; a separate node is supported. All source excerpts remain UNAUTHORIZED_CANDIDATE evidence.
- temporal scope assessed: 2022
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'distinct', 'object_type': 'mismatch', 'scope': 'mismatch', 'granularity': 'different', 'quarantine': 'clear', 'ontology': 'compatible', 'evidence_sufficiency': 'sufficient', 'temporal': 'compatible'}

**A/B RECONCILIATION**

- A_B_SUBSTANTIVE_AGREEMENT; disagreement type: none; native-operation conflict: false; target conflict: false.
- Interpretation differences: none.
- Reconciliation assessment: Same native operation, target, and material interpretation.
- Non-material rubric-label differences retained for audit: none.

**EVIDENCE SUMMARY**

- Source `SC-PHYS-59E90A8C09249A8D` (SHA-256 `59e90a8c09249a8dc75f53f661f4f0eff511b9eb65fbc1a1c70ffb363d8166c8`), file `SC-P0-014_2022_IRDS_More_Than_Moore.pdf`, p. 19, section 3 Smart Energy / Introduction; evidence `SC-EV-A72108B7E930E34C`; as-of 2022; excerpt: “Power electronics is the technology associated with the efficient conversion, control and conditioning of electric energy from the source to the load.”
- Temporal scope: source as-of dates above; no relation temporal claim.

- SYSTEM_RECOMMENDED_DECISION: `CREATE_NEW_CANONICAL`.
- SYSTEM_RECOMMENDATION_REASON: A/B substantive consensus; frozen automated outcome: DEFER.
- HUMAN_USER_DECISION = PENDING
- VALID NATIVE OPTIONS: REUSE_CANONICAL, CREATE_NEW_CANONICAL, KEEP_DOMAIN_SPECIFIC, DEFER, REJECT; REUSE requires an explicit validated target ID and all options remain subject to frozen controls.

### Item 023 — SC-CN-0141 — RDL

- ITEM_NUMBER: 23; ITEM_ID: `SC-CN-0141`; OBJECT_TYPE: identity.
- DOMAIN / context: `08_assembly_packaging` Semiconductor structured Foundation candidate against shared AI Hardware canonical catalog; cross-domain status: `GOVERNED_REUSE`.
- AUTOMATED_STAGE3_OUTCOME: `REUSE_CANONICAL`; CURRENT_CANONICAL_TARGET: `NODE_20260817_F039433D`.
- Possible existing canonical IDs (unresolved unless explicitly reused): `NODE_20260817_F039433D`.
- CANDIDATE_SUMMARY: RDL; candidate type `Technology`; comparison scope `复用当前Context Pack的active身份；保留ID、规范名和类型。`; frozen candidate rationale: 复用当前Context Pack的active身份；保留ID、规范名和类型。
- WHY_HUMAN_REQUIRED: frozen Stage 3 mandatory review population; automated reasons: EXACT_SHARED_CATALOG_IDENTITY.
- RISK_FLAGS: A=EXACT_SHARED_CATALOG_IDENTITY; B=ALIAS_OR_TRANSLATION.

**AI REVIEW A**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `REUSE_CANONICAL`; target: `NODE_20260817_F039433D`; confidence: HIGH; materiality: MEDIUM.
- reason: Redistribution Layer has an active registered RDL alias with matching Technology type.
- evidence assessment: HIR describes RDL's role in fan-out and chiplet interconnects, consistent with the existing identity.
- temporal scope assessed: {'source_as_of': ['2026-03', '2025'], 'publication_date': ['2026-03', None], 'identity_claim': 'candidate_only'}
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'same', 'object_type': 'compatible', 'scope': 'compatible', 'granularity': 'same', 'quarantine': 'clear', 'ontology': 'compatible', 'evidence_sufficiency': 'sufficient', 'temporal': 'compatible'}

**AI REVIEW B**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `REUSE_CANONICAL`; target: `NODE_20260817_F039433D`; confidence: MEDIUM; materiality: LOW.
- reason: Exact active catalog identity: RDL to Redistribution Layer; source uses the same Technology object.
- evidence assessment: SC-EV-331918819CB99398 from SC-P0-018_2025_HIR_Materials_and_Interfaces_Advanced_Packaging.pdf [source SC-PHYS-2E34AF6DD70E8C2C; SHA 2e34af6dd70e8c2c5de2aaabec15837693d1322abc0bb5820475188cd028a3f2; PDF p.14, 2.2.3.7 Redistribution Layer and Damascene Processing]: RDL technologies are critical for fan-out wafer-level packaging (FOWLP), chiplet integration, and fine-pitch interconnects. | SC-EV-BE1EFC0405668731 from SC-P0-020B_TSMC_2025_Annual_Report.pdf [source F018b; SHA 3fb7ae4ad972aa2bc6e45bb36635152ad89d52f4a7165f389bcb94eeb54a6abd; PDF p.53, TSMC 3DFabric / CoWoS-R]: CoWoS® with redistribution layer interposer (CoWoS®-R) advanced packaging service, featuring multiple redistribution layers (RDL) to enable product design simplicity, supports larger HPC products. This technology entered its third year of volume production in 2025. Boundary: Exact active catalog identity: RDL to Redistribution Layer; source uses the same Technology object. All source excerpts remain UNAUTHORIZED_CANDIDATE evidence.
- temporal scope assessed: 2026-03
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'same', 'object_type': 'compatible', 'scope': 'compatible', 'granularity': 'same', 'quarantine': 'clear', 'ontology': 'compatible', 'evidence_sufficiency': 'sufficient', 'temporal': 'compatible'}

**A/B RECONCILIATION**

- A_B_SUBSTANTIVE_AGREEMENT; disagreement type: none; native-operation conflict: false; target conflict: false.
- Interpretation differences: none.
- Reconciliation assessment: Same native operation, target, and material interpretation.
- Non-material rubric-label differences retained for audit: none.

**EVIDENCE SUMMARY**

- Source `SC-PHYS-2E34AF6DD70E8C2C` (SHA-256 `2e34af6dd70e8c2c5de2aaabec15837693d1322abc0bb5820475188cd028a3f2`), file `SC-P0-018_2025_HIR_Materials_and_Interfaces_Advanced_Packaging.pdf`, p. 14, section 2.2.3.7 Redistribution Layer and Damascene Processing; evidence `SC-EV-331918819CB99398`; as-of 2026-03; excerpt: “RDL technologies are critical for fan-out wafer-level packaging (FOWLP), chiplet integration, and fine-pitch interconnects.”
- Source `F018b` (SHA-256 `3fb7ae4ad972aa2bc6e45bb36635152ad89d52f4a7165f389bcb94eeb54a6abd`), file `SC-P0-020B_TSMC_2025_Annual_Report.pdf`, p. 53, section TSMC 3DFabric / CoWoS-R; evidence `SC-EV-BE1EFC0405668731`; as-of 2025; excerpt: “CoWoS® with redistribution layer interposer (CoWoS®-R) advanced packaging service, featuring multiple redistribution layers (RDL) to enable product design simplicity, supports larger HPC products. This technology entered its third year of volume production in 2025.”
- Temporal scope: source as-of dates above; no relation temporal claim.

- SYSTEM_RECOMMENDED_DECISION: `REUSE_CANONICAL`.
- SYSTEM_RECOMMENDATION_REASON: A/B substantive consensus; frozen automated outcome: REUSE_CANONICAL.
- HUMAN_USER_DECISION = PENDING
- VALID NATIVE OPTIONS: REUSE_CANONICAL, CREATE_NEW_CANONICAL, KEEP_DOMAIN_SPECIFIC, DEFER, REJECT; REUSE requires an explicit validated target ID and all options remain subject to frozen controls.

### Item 024 — SC-CN-0142 — RDL Dielectric Material

- ITEM_NUMBER: 24; ITEM_ID: `SC-CN-0142`; OBJECT_TYPE: identity.
- DOMAIN / context: `08_assembly_packaging` Semiconductor structured Foundation candidate against shared AI Hardware canonical catalog; cross-domain status: `REVIEW_REQUIRED`.
- AUTOMATED_STAGE3_OUTCOME: `DEFER`; CURRENT_CANONICAL_TARGET: `none`.
- Possible existing canonical IDs (unresolved unless explicitly reused): `NODE_20260817_0873A4EF`.
- CANDIDATE_SUMMARY: RDL Dielectric Material; candidate type `Material`; comparison scope `原文RDL dielectrics对应候选规范名尚缺exact registered expression；附到现有同义候选，不建第二份。`; frozen candidate rationale: 原文RDL dielectrics对应候选规范名尚缺exact registered expression；附到现有同义候选，不建第二份。
- WHY_HUMAN_REQUIRED: frozen Stage 3 mandatory review population; automated reasons: IDENTITY_TARGET_OR_STATUS_REVIEW.
- RISK_FLAGS: A=IDENTITY_TARGET_OR_STATUS_REVIEW; B=UNRESOLVED_IDENTITY.

**AI REVIEW A**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `DEFER`; target: `none`; confidence: MEDIUM; materiality: MEDIUM.
- reason: The catalog retrieves RDL Dielectric Material exactly, but its governing status and the source's plural expression still require identity-target review.
- evidence assessment: HIR identifies RDL dielectrics as packaging interconnect materials, yet that passage alone cannot validate ownership of the candidate catalog node.
- temporal scope assessed: {'source_as_of': ['2026-03'], 'publication_date': ['2026-03'], 'identity_claim': 'candidate_only'}
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'ambiguous', 'object_type': 'compatible', 'scope': 'unknown', 'granularity': 'unknown', 'quarantine': 'unresolved', 'ontology': 'compatible', 'evidence_sufficiency': 'limited', 'temporal': 'compatible'}

**AI REVIEW B**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `DEFER`; target: `none`; confidence: MEDIUM; materiality: MEDIUM.
- reason: RDL dielectrics are a material family, but a possibly synonymous existing candidate lacks registered exact expression. Resolve the target before a second node.
- evidence assessment: SC-EV-3032F6F70575E525 from SC-P0-018_2025_HIR_Materials_and_Interfaces_Advanced_Packaging.pdf [source SC-PHYS-2E34AF6DD70E8C2C; SHA 2e34af6dd70e8c2c5de2aaabec15837693d1322abc0bb5820475188cd028a3f2; PDF p.4, 2.1.1 Technology / Systems Focus]: Redistribution layer (RDL) dielectrics have become a central technology bottleneck for advanced semiconductor packaging as system performance increasingly depends on package-level interconnects rather than on-device wiring alone. Boundary: RDL dielectrics are a material family, but a possibly synonymous existing candidate lacks registered exact expression. Resolve the target before a second node. All source excerpts remain UNAUTHORIZED_CANDIDATE evidence.
- temporal scope assessed: 2026-03
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'ambiguous', 'object_type': 'unknown', 'scope': 'unknown', 'granularity': 'unknown', 'quarantine': 'clear', 'ontology': 'unresolved', 'evidence_sufficiency': 'limited', 'temporal': 'compatible'}

**A/B RECONCILIATION**

- A_B_SUBSTANTIVE_AGREEMENT; disagreement type: none; native-operation conflict: false; target conflict: false.
- Interpretation differences: none.
- Reconciliation assessment: Both reviewers preserve the same governed hold. Rubric labels distinguish source support for a concept from sufficiency for canonical admission.
- Non-material rubric-label differences retained for audit: object_type, ontology, quarantine.

**EVIDENCE SUMMARY**

- Source `SC-PHYS-2E34AF6DD70E8C2C` (SHA-256 `2e34af6dd70e8c2c5de2aaabec15837693d1322abc0bb5820475188cd028a3f2`), file `SC-P0-018_2025_HIR_Materials_and_Interfaces_Advanced_Packaging.pdf`, p. 4, section 2.1.1 Technology / Systems Focus; evidence `SC-EV-3032F6F70575E525`; as-of 2026-03; excerpt: “Redistribution layer (RDL) dielectrics have become a central technology bottleneck for advanced semiconductor packaging as system performance increasingly depends on package-level interconnects rather than on-device wiring alone.”
- Temporal scope: source as-of dates above; no relation temporal claim.

- SYSTEM_RECOMMENDED_DECISION: `DEFER`.
- SYSTEM_RECOMMENDATION_REASON: Frozen structural, Stage 2 decision, evidence, or temporal exception remains unresolved.
- HUMAN_USER_DECISION = PENDING
- VALID NATIVE OPTIONS: REUSE_CANONICAL, CREATE_NEW_CANONICAL, KEEP_DOMAIN_SPECIFIC, DEFER, REJECT; REUSE requires an explicit validated target ID and all options remain subject to frozen controls.

### Item 025 — SC-CN-0114 — RDL Interposer

- ITEM_NUMBER: 25; ITEM_ID: `SC-CN-0114`; OBJECT_TYPE: identity.
- DOMAIN / context: `05_lithography_patterning` Semiconductor structured Foundation candidate against shared AI Hardware canonical catalog; cross-domain status: `GOVERNED_REUSE`.
- AUTOMATED_STAGE3_OUTCOME: `REUSE_CANONICAL`; CURRENT_CANONICAL_TARGET: `NODE_20260817_4AA22685`.
- Possible existing canonical IDs (unresolved unless explicitly reused): `NODE_20260817_4AA22685`.
- CANDIDATE_SUMMARY: RDL Interposer; candidate type `Product`; comparison scope `复用当前Context Pack的active身份；保留ID、规范名和类型。`; frozen candidate rationale: 复用当前Context Pack的active身份；保留ID、规范名和类型。
- WHY_HUMAN_REQUIRED: frozen Stage 3 mandatory review population; automated reasons: EXACT_SHARED_CATALOG_IDENTITY.
- RISK_FLAGS: A=EXACT_SHARED_CATALOG_IDENTITY; B=none.

**AI REVIEW A**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `REUSE_CANONICAL`; target: `NODE_20260817_4AA22685`; confidence: HIGH; materiality: MEDIUM.
- reason: RDL Interposer is an exact active Product match; a glass carrier in one source does not redefine all interposers.
- evidence assessment: IRDS and TSMC both identify an RDL-based interposer, supporting the existing product category.
- temporal scope assessed: {'source_as_of': ['2025'], 'publication_date': [None], 'identity_claim': 'candidate_only'}
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'same', 'object_type': 'compatible', 'scope': 'compatible', 'granularity': 'same', 'quarantine': 'clear', 'ontology': 'compatible', 'evidence_sufficiency': 'sufficient', 'temporal': 'compatible'}

**AI REVIEW B**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `REUSE_CANONICAL`; target: `NODE_20260817_4AA22685`; confidence: HIGH; materiality: LOW.
- reason: Exact active catalog identity: RDL Interposer to RDL Interposer; source uses the same Product object.
- evidence assessment: SC-EV-205CE90A3724B5BA from SC-P0-010_2025_IRDS_Lithography_and_Patterning.pdf [source SC-PHYS-318D85A127B5B6DF; SHA 318d85a127b5b6dfa7b3c1330ae20b18d63660a1fa8c8bdfdd7b478844e145ed; PDF p.21, Packaging Lithography]: The second one is a RDL interposer using glass carriers. | SC-EV-BE1EFC0405668731 from SC-P0-020B_TSMC_2025_Annual_Report.pdf [source F018b; SHA 3fb7ae4ad972aa2bc6e45bb36635152ad89d52f4a7165f389bcb94eeb54a6abd; PDF p.53, TSMC 3DFabric / CoWoS-R]: CoWoS® with redistribution layer interposer (CoWoS®-R) advanced packaging service, featuring multiple redistribution layers (RDL) to enable product design simplicity, supports larger HPC products. This technology entered its third year of volume production in 2025. Boundary: Exact active catalog identity: RDL Interposer to RDL Interposer; source uses the same Product object. All source excerpts remain UNAUTHORIZED_CANDIDATE evidence.
- temporal scope assessed: 2025
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'same', 'object_type': 'compatible', 'scope': 'compatible', 'granularity': 'same', 'quarantine': 'clear', 'ontology': 'compatible', 'evidence_sufficiency': 'sufficient', 'temporal': 'compatible'}

**A/B RECONCILIATION**

- A_B_SUBSTANTIVE_AGREEMENT; disagreement type: none; native-operation conflict: false; target conflict: false.
- Interpretation differences: none.
- Reconciliation assessment: Same native operation, target, and material interpretation.
- Non-material rubric-label differences retained for audit: none.

**EVIDENCE SUMMARY**

- Source `SC-PHYS-318D85A127B5B6DF` (SHA-256 `318d85a127b5b6dfa7b3c1330ae20b18d63660a1fa8c8bdfdd7b478844e145ed`), file `SC-P0-010_2025_IRDS_Lithography_and_Patterning.pdf`, p. 21, section Packaging Lithography; evidence `SC-EV-205CE90A3724B5BA`; as-of 2025; excerpt: “The second one is a RDL interposer using glass carriers.”
- Source `F018b` (SHA-256 `3fb7ae4ad972aa2bc6e45bb36635152ad89d52f4a7165f389bcb94eeb54a6abd`), file `SC-P0-020B_TSMC_2025_Annual_Report.pdf`, p. 53, section TSMC 3DFabric / CoWoS-R; evidence `SC-EV-BE1EFC0405668731`; as-of 2025; excerpt: “CoWoS® with redistribution layer interposer (CoWoS®-R) advanced packaging service, featuring multiple redistribution layers (RDL) to enable product design simplicity, supports larger HPC products. This technology entered its third year of volume production in 2025.”
- Temporal scope: source as-of dates above; no relation temporal claim.

- SYSTEM_RECOMMENDED_DECISION: `REUSE_CANONICAL`.
- SYSTEM_RECOMMENDATION_REASON: A/B substantive consensus; frozen automated outcome: REUSE_CANONICAL.
- HUMAN_USER_DECISION = PENDING
- VALID NATIVE OPTIONS: REUSE_CANONICAL, CREATE_NEW_CANONICAL, KEEP_DOMAIN_SPECIFIC, DEFER, REJECT; REUSE requires an explicit validated target ID and all options remain subject to frozen controls.

### Item 026 — SC-CN-0163 — RF Integrated Circuit

- ITEM_NUMBER: 26; ITEM_ID: `SC-CN-0163`; OBJECT_TYPE: identity.
- DOMAIN / context: `07_more_than_moore` Semiconductor structured Foundation candidate against shared AI Hardware canonical catalog; cross-domain status: `REVIEW_REQUIRED`.
- AUTOMATED_STAGE3_OUTCOME: `DEFER`; CURRENT_CANONICAL_TARGET: `none`.
- Possible existing canonical IDs (unresolved unless explicitly reused): `none`.
- CANDIDATE_SUMMARY: RF Integrated Circuit; candidate type `Product`; comparison scope `RF器件/电路层级与existing RF应用细分存在交叉；本轮保留宽泛电路族待审。`; frozen candidate rationale: RF器件/电路层级与existing RF应用细分存在交叉；本轮保留宽泛电路族待审。
- WHY_HUMAN_REQUIRED: frozen Stage 3 mandatory review population; automated reasons: AMBIGUOUS_IDENTITY, FROZEN_STAGE2_HUMAN_DECISION.
- RISK_FLAGS: A=AMBIGUOUS_IDENTITY, FROZEN_STAGE2_HUMAN_DECISION; B=FROZEN_STAGE2_DECISION, UNRESOLVED_IDENTITY, EVIDENCE_LIMIT.

**AI REVIEW A**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `DEFER`; target: `none`; confidence: HIGH; materiality: MEDIUM.
- reason: RF Integrated Circuit remains a broad circuit Product with unresolved overlap against RF application segments; honor Stage 2 DEFER.
- evidence assessment: IRDS discusses RF component performance and CMOS compatibility, but the excerpt does not pin a single catalog granularity.
- temporal scope assessed: {'source_as_of': ['2024'], 'publication_date': [None], 'identity_claim': 'candidate_only'}
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'ambiguous', 'object_type': 'unknown', 'scope': 'unknown', 'granularity': 'unknown', 'quarantine': 'clear', 'ontology': 'compatible', 'evidence_sufficiency': 'limited', 'temporal': 'compatible'}

**AI REVIEW B**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `DEFER`; target: `none`; confidence: LOW; materiality: MEDIUM.
- reason: The span discusses RF analog components and ADC/DAC performance, not the boundary of an RF Integrated Circuit Product class.
- evidence assessment: SC-EV-80314FEB50CF37D6 from SC-P0-015_2024_IRDS_Outside_System_Connectivity.pdf [source SC-PHYS-EECFB29D71F7359F; SHA eecfb29d71f7359fccc255f854e9efe7262f82f06fad04ee56ecb871cf6defee; PDF p.31, 6.1 RF Integrated Circuits and Devices]: The challenges for RF components include 1) achieving high performance, wider bandwidth to increase data rate, and energy efficient RF analog technology with high linearity that is compatible with CMOS based digital processing that has a good compromise for high data rate (wide band) ADC/DAC, and 2) components to meet 5G and 6G performance requirements. Boundary: The span discusses RF analog components and ADC/DAC performance, not the boundary of an RF Integrated Circuit Product class. All source excerpts remain UNAUTHORIZED_CANDIDATE evidence.
- temporal scope assessed: 2024
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'ambiguous', 'object_type': 'unknown', 'scope': 'unknown', 'granularity': 'unknown', 'quarantine': 'preserved', 'ontology': 'unresolved', 'evidence_sufficiency': 'insufficient', 'temporal': 'compatible'}

**A/B RECONCILIATION**

- A_B_SUBSTANTIVE_AGREEMENT; disagreement type: none; native-operation conflict: false; target conflict: false.
- Interpretation differences: none.
- Reconciliation assessment: Both reviewers preserve the same governed hold. Rubric labels distinguish source support for a concept from sufficiency for canonical admission.
- Non-material rubric-label differences retained for audit: evidence_sufficiency, ontology, quarantine.

**EVIDENCE SUMMARY**

- Source `SC-PHYS-EECFB29D71F7359F` (SHA-256 `eecfb29d71f7359fccc255f854e9efe7262f82f06fad04ee56ecb871cf6defee`), file `SC-P0-015_2024_IRDS_Outside_System_Connectivity.pdf`, p. 31, section 6.1 RF Integrated Circuits and Devices; evidence `SC-EV-80314FEB50CF37D6`; as-of 2024; excerpt: “The challenges for RF components include 1) achieving high performance, wider bandwidth to increase data rate, and energy efficient RF analog technology with high linearity that is compatible with CMOS based digital processing that has a good compromise for high data rate (wide band) ADC/DAC, and 2) components to meet 5G and 6G performance requirements.”
- Temporal scope: source as-of dates above; no relation temporal claim.

- SYSTEM_RECOMMENDED_DECISION: `DEFER`.
- SYSTEM_RECOMMENDATION_REASON: Frozen structural, Stage 2 decision, evidence, or temporal exception remains unresolved.
- HUMAN_USER_DECISION = PENDING
- VALID NATIVE OPTIONS: REUSE_CANONICAL, CREATE_NEW_CANONICAL, KEEP_DOMAIN_SPECIFIC, DEFER, REJECT; REUSE requires an explicit validated target ID and all options remain subject to frozen controls.

### Item 027 — SC-CN-0001 — Semiconductor

- ITEM_NUMBER: 27; ITEM_ID: `SC-CN-0001`; OBJECT_TYPE: identity.
- DOMAIN / context: `00_industry_structure` Semiconductor structured Foundation candidate against shared AI Hardware canonical catalog; cross-domain status: `REVIEW_REQUIRED`.
- AUTOMATED_STAGE3_OUTCOME: `DEFER`; CURRENT_CANONICAL_TARGET: `none`.
- Possible existing canonical IDs (unresolved unless explicitly reused): `none`.
- CANDIDATE_SUMMARY: Semiconductor; candidate type `Industry`; comparison scope `现有中文 Industry 半导体无已注册英文映射；不得创建平行根节点；需明确批准英文别名。`; frozen candidate rationale: 现有中文 Industry 半导体无已注册英文映射；不得创建平行根节点；需明确批准英文别名。
- WHY_HUMAN_REQUIRED: frozen Stage 3 mandatory review population; automated reasons: AMBIGUOUS_IDENTITY.
- RISK_FLAGS: A=AMBIGUOUS_IDENTITY; B=UNRESOLVED_IDENTITY.

**AI REVIEW A**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `DEFER`; target: `none`; confidence: HIGH; materiality: HIGH.
- reason: English Semiconductor may correspond to the Chinese Industry root 半导体, but no approved bilingual alias establishes reuse; avoid a parallel root.
- evidence assessment: SIA's IC/discrete description establishes the industry subject, not an authorized translation mapping to the existing node.
- temporal scope assessed: {'source_as_of': ['2019'], 'publication_date': ['2019'], 'identity_claim': 'candidate_only'}
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'ambiguous', 'object_type': 'compatible', 'scope': 'unknown', 'granularity': 'unknown', 'quarantine': 'clear', 'ontology': 'compatible', 'evidence_sufficiency': 'sufficient', 'temporal': 'compatible'}

**AI REVIEW B**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `DEFER`; target: `none`; confidence: MEDIUM; materiality: HIGH.
- reason: English Semiconductor may match the active Chinese 半导体 Industry root, but no governed translation is frozen; a parallel root would fragment identity.
- evidence assessment: SC-EV-AC855AD6CD7AF8B7 from SC-P0-001_SIA_Making_Semiconductors_2019.pdf [source SC-PHYS-04A42FFC3F71A42F; SHA 04a42ffc3f71a42fa9b996240618874bb7fff21404e93cdb1e7bf53318938c26; PDF p.1, Types of Semiconductors]: Integrated circuits (ICs) are sophisticated semiconductors that often contain billions of transistors and perform high-level functions, while discretes often contain fewer transistors and perform simpler functions. Boundary: English Semiconductor may match the active Chinese 半导体 Industry root, but no governed translation is frozen; a parallel root would fragment identity. All source excerpts remain UNAUTHORIZED_CANDIDATE evidence.
- temporal scope assessed: 2019
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'ambiguous', 'object_type': 'unknown', 'scope': 'unknown', 'granularity': 'unknown', 'quarantine': 'clear', 'ontology': 'unresolved', 'evidence_sufficiency': 'limited', 'temporal': 'compatible'}

**A/B RECONCILIATION**

- A_B_SUBSTANTIVE_AGREEMENT; disagreement type: none; native-operation conflict: false; target conflict: false.
- Interpretation differences: none.
- Reconciliation assessment: Both reviewers preserve the same governed hold. Rubric labels distinguish source support for a concept from sufficiency for canonical admission.
- Non-material rubric-label differences retained for audit: evidence_sufficiency, object_type, ontology.

**EVIDENCE SUMMARY**

- Source `SC-PHYS-04A42FFC3F71A42F` (SHA-256 `04a42ffc3f71a42fa9b996240618874bb7fff21404e93cdb1e7bf53318938c26`), file `SC-P0-001_SIA_Making_Semiconductors_2019.pdf`, p. 1, section Types of Semiconductors; evidence `SC-EV-AC855AD6CD7AF8B7`; as-of 2019; excerpt: “Integrated circuits (ICs) are sophisticated semiconductors that often contain billions of transistors and perform high-level functions, while discretes often contain fewer transistors and perform simpler functions.”
- Temporal scope: source as-of dates above; no relation temporal claim.

- SYSTEM_RECOMMENDED_DECISION: `DEFER`.
- SYSTEM_RECOMMENDATION_REASON: A/B substantive consensus; frozen automated outcome: DEFER.
- HUMAN_USER_DECISION = PENDING
- VALID NATIVE OPTIONS: REUSE_CANONICAL, CREATE_NEW_CANONICAL, KEEP_DOMAIN_SPECIFIC, DEFER, REJECT; REUSE requires an explicit validated target ID and all options remain subject to frozen controls.

### Item 028 — SC-CN-0003 — Semiconductor Manufacturing Equipment

- ITEM_NUMBER: 28; ITEM_ID: `SC-CN-0003`; OBJECT_TYPE: identity.
- DOMAIN / context: `00_industry_structure` Semiconductor structured Foundation candidate against shared AI Hardware canonical catalog; cross-domain status: `REVIEW_REQUIRED`.
- AUTOMATED_STAGE3_OUTCOME: `DEFER`; CURRENT_CANONICAL_TARGET: `none`.
- Possible existing canonical IDs (unresolved unless explicitly reused): `none`.
- CANDIDATE_SUMMARY: Semiconductor Manufacturing Equipment; candidate type `Segment`; comparison scope `现有半导体设备节点未登记对应英文；待确认域范围及别名。`; frozen candidate rationale: 现有半导体设备节点未登记对应英文；待确认域范围及别名。
- WHY_HUMAN_REQUIRED: frozen Stage 3 mandatory review population; automated reasons: AMBIGUOUS_IDENTITY.
- RISK_FLAGS: A=AMBIGUOUS_IDENTITY; B=UNRESOLVED_IDENTITY.

**AI REVIEW A**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `DEFER`; target: `none`; confidence: HIGH; materiality: HIGH.
- reason: Semiconductor Manufacturing Equipment may map to 半导体设备, but exact bilingual scope and alias ownership are unresolved.
- evidence assessment: SIA/BCG mentions many specialist wafer-processing and testing equipment types, too broad to prove the existing Chinese segment's boundary.
- temporal scope assessed: {'source_as_of': ['2021-04'], 'publication_date': ['2021-04'], 'identity_claim': 'candidate_only'}
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'ambiguous', 'object_type': 'compatible', 'scope': 'unknown', 'granularity': 'unknown', 'quarantine': 'clear', 'ontology': 'compatible', 'evidence_sufficiency': 'sufficient', 'temporal': 'compatible'}

**AI REVIEW B**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `DEFER`; target: `none`; confidence: MEDIUM; materiality: MEDIUM.
- reason: Manufacturing equipment may match the existing Chinese semiconductor-equipment segment; an equipment list does not authorize a bilingual alias.
- evidence assessment: SC-EV-F3222CB2AB4DD994 from SC-P0-002_SIA_BCG_Global_Semiconductor_Supply_Chain_2021.pdf [source SC-PHYS-B33C40EBCB5756F7; SHA b33c40ebcb5756f76e887ba2664f97736252e68ba7bfbedc2d628ce2d7cbc08d; PDF p.19, Wafer processing and testing equipment]: Semiconductor manufacturing uses more than 50 different types of sophisticated wafer processing and testing equipment provided by specialist vendors for each step in the fabrication process. Boundary: Manufacturing equipment may match the existing Chinese semiconductor-equipment segment; an equipment list does not authorize a bilingual alias. All source excerpts remain UNAUTHORIZED_CANDIDATE evidence.
- temporal scope assessed: 2021-04
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'ambiguous', 'object_type': 'unknown', 'scope': 'unknown', 'granularity': 'unknown', 'quarantine': 'clear', 'ontology': 'unresolved', 'evidence_sufficiency': 'limited', 'temporal': 'compatible'}

**A/B RECONCILIATION**

- A_B_SUBSTANTIVE_AGREEMENT; disagreement type: none; native-operation conflict: false; target conflict: false.
- Interpretation differences: none.
- Reconciliation assessment: Both reviewers preserve the same governed hold. Rubric labels distinguish source support for a concept from sufficiency for canonical admission.
- Non-material rubric-label differences retained for audit: evidence_sufficiency, object_type, ontology.

**EVIDENCE SUMMARY**

- Source `SC-PHYS-B33C40EBCB5756F7` (SHA-256 `b33c40ebcb5756f76e887ba2664f97736252e68ba7bfbedc2d628ce2d7cbc08d`), file `SC-P0-002_SIA_BCG_Global_Semiconductor_Supply_Chain_2021.pdf`, p. 19, section Wafer processing and testing equipment; evidence `SC-EV-F3222CB2AB4DD994`; as-of 2021-04; excerpt: “Semiconductor manufacturing uses more than 50 different types of sophisticated wafer processing and testing equipment provided by specialist vendors for each step in the fabrication process.”
- Temporal scope: source as-of dates above; no relation temporal claim.

- SYSTEM_RECOMMENDED_DECISION: `DEFER`.
- SYSTEM_RECOMMENDATION_REASON: A/B substantive consensus; frozen automated outcome: DEFER.
- HUMAN_USER_DECISION = PENDING
- VALID NATIVE OPTIONS: REUSE_CANONICAL, CREATE_NEW_CANONICAL, KEEP_DOMAIN_SPECIFIC, DEFER, REJECT; REUSE requires an explicit validated target ID and all options remain subject to frozen controls.

### Item 029 — SC-CN-0002 — Semiconductor Materials

- ITEM_NUMBER: 29; ITEM_ID: `SC-CN-0002`; OBJECT_TYPE: identity.
- DOMAIN / context: `00_industry_structure` Semiconductor structured Foundation candidate against shared AI Hardware canonical catalog; cross-domain status: `REVIEW_REQUIRED`.
- AUTOMATED_STAGE3_OUTCOME: `DEFER`; CURRENT_CANONICAL_TARGET: `none`.
- Possible existing canonical IDs (unresolved unless explicitly reused): `none`.
- CANDIDATE_SUMMARY: Semiconductor Materials; candidate type `Segment`; comparison scope `现有半导体材料节点为中文身份；英文等价映射未经登记。`; frozen candidate rationale: 现有半导体材料节点为中文身份；英文等价映射未经登记。
- WHY_HUMAN_REQUIRED: frozen Stage 3 mandatory review population; automated reasons: AMBIGUOUS_IDENTITY.
- RISK_FLAGS: A=AMBIGUOUS_IDENTITY; B=UNRESOLVED_IDENTITY.

**AI REVIEW A**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `DEFER`; target: `none`; confidence: HIGH; materiality: HIGH.
- reason: Semiconductor Materials may map to 半导体材料, yet the current record lacks a registered English alias and a confirmed shared segment scope.
- evidence assessment: The wafer-material passage gives examples, not a definitive equivalence to the Chinese catalog segment.
- temporal scope assessed: {'source_as_of': ['2021-04'], 'publication_date': ['2021-04'], 'identity_claim': 'candidate_only'}
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'ambiguous', 'object_type': 'compatible', 'scope': 'unknown', 'granularity': 'unknown', 'quarantine': 'clear', 'ontology': 'compatible', 'evidence_sufficiency': 'sufficient', 'temporal': 'compatible'}

**AI REVIEW B**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `DEFER`; target: `none`; confidence: MEDIUM; materiality: MEDIUM.
- reason: Semiconductor Materials may match the existing Chinese materials segment; wafer and polysilicon examples do not prove an English alias.
- evidence assessment: SC-EV-A47357C4422D938D from SC-P0-002_SIA_BCG_Global_Semiconductor_Supply_Chain_2021.pdf [source SC-PHYS-B33C40EBCB5756F7; SHA b33c40ebcb5756f76e887ba2664f97736252e68ba7bfbedc2d628ce2d7cbc08d; PDF p.22, Materials]: Silicon wafers: Polysilicon is melted, formed into single crystal ingots which are then sliced into wafers, cleaned, polished, and oxidized in preparation for circuit imprinting within fabrication facilities. | SC-EV-3CEFE864BD6A09B8 from SC-P0-002_SIA_BCG_Global_Semiconductor_Supply_Chain_2021.pdf [source SC-PHYS-B33C40EBCB5756F7; SHA b33c40ebcb5756f76e887ba2664f97736252e68ba7bfbedc2d628ce2d7cbc08d; PDF p.22, Materials]: Back-end materials include leadframes, organic substrates, ceramic packages, encapsulation resins, bonding wires and die-attach materials. Boundary: Semiconductor Materials may match the existing Chinese materials segment; wafer and polysilicon examples do not prove an English alias. All source excerpts remain UNAUTHORIZED_CANDIDATE evidence.
- temporal scope assessed: 2021-04
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'ambiguous', 'object_type': 'unknown', 'scope': 'unknown', 'granularity': 'unknown', 'quarantine': 'clear', 'ontology': 'unresolved', 'evidence_sufficiency': 'limited', 'temporal': 'compatible'}

**A/B RECONCILIATION**

- A_B_SUBSTANTIVE_AGREEMENT; disagreement type: none; native-operation conflict: false; target conflict: false.
- Interpretation differences: none.
- Reconciliation assessment: Both reviewers preserve the same governed hold. Rubric labels distinguish source support for a concept from sufficiency for canonical admission.
- Non-material rubric-label differences retained for audit: evidence_sufficiency, object_type, ontology.

**EVIDENCE SUMMARY**

- Source `SC-PHYS-B33C40EBCB5756F7` (SHA-256 `b33c40ebcb5756f76e887ba2664f97736252e68ba7bfbedc2d628ce2d7cbc08d`), file `SC-P0-002_SIA_BCG_Global_Semiconductor_Supply_Chain_2021.pdf`, p. 22, section Materials; evidence `SC-EV-A47357C4422D938D`; as-of 2021-04; excerpt: “Silicon wafers: Polysilicon is melted, formed into single crystal ingots which are then sliced into wafers, cleaned, polished, and oxidized in preparation for circuit imprinting within fabrication facilities.”
- Source `SC-PHYS-B33C40EBCB5756F7` (SHA-256 `b33c40ebcb5756f76e887ba2664f97736252e68ba7bfbedc2d628ce2d7cbc08d`), file `SC-P0-002_SIA_BCG_Global_Semiconductor_Supply_Chain_2021.pdf`, p. 22, section Materials; evidence `SC-EV-3CEFE864BD6A09B8`; as-of 2021-04; excerpt: “Back-end materials include leadframes, organic substrates, ceramic packages, encapsulation resins, bonding wires and die-attach materials.”
- Temporal scope: source as-of dates above; no relation temporal claim.

- SYSTEM_RECOMMENDED_DECISION: `DEFER`.
- SYSTEM_RECOMMENDATION_REASON: A/B substantive consensus; frozen automated outcome: DEFER.
- HUMAN_USER_DECISION = PENDING
- VALID NATIVE OPTIONS: REUSE_CANONICAL, CREATE_NEW_CANONICAL, KEEP_DOMAIN_SPECIFIC, DEFER, REJECT; REUSE requires an explicit validated target ID and all options remain subject to frozen controls.

### Item 030 — SC-CN-0113 — Silicon Interposer

- ITEM_NUMBER: 30; ITEM_ID: `SC-CN-0113`; OBJECT_TYPE: identity.
- DOMAIN / context: `05_lithography_patterning` Semiconductor structured Foundation candidate against shared AI Hardware canonical catalog; cross-domain status: `GOVERNED_REUSE`.
- AUTOMATED_STAGE3_OUTCOME: `REUSE_CANONICAL`; CURRENT_CANONICAL_TARGET: `NODE_20260817_3A173B33`.
- Possible existing canonical IDs (unresolved unless explicitly reused): `NODE_20260817_3A173B33`.
- CANDIDATE_SUMMARY: Silicon Interposer; candidate type `Product`; comparison scope `复用当前Context Pack的active身份；保留ID、规范名和类型。`; frozen candidate rationale: 复用当前Context Pack的active身份；保留ID、规范名和类型。
- WHY_HUMAN_REQUIRED: frozen Stage 3 mandatory review population; automated reasons: EXACT_SHARED_CATALOG_IDENTITY.
- RISK_FLAGS: A=EXACT_SHARED_CATALOG_IDENTITY; B=none.

**AI REVIEW A**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `REUSE_CANONICAL`; target: `NODE_20260817_3A173B33`; confidence: HIGH; materiality: MEDIUM.
- reason: Silicon Interposer is an exact active Product; it remains a child of generic Interposer.
- evidence assessment: IRDS describes silicon substrate and fine RDL construction, directly supporting the specialized product identity.
- temporal scope assessed: {'source_as_of': ['2025'], 'publication_date': [None], 'identity_claim': 'candidate_only'}
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'same', 'object_type': 'compatible', 'scope': 'compatible', 'granularity': 'same', 'quarantine': 'clear', 'ontology': 'compatible', 'evidence_sufficiency': 'sufficient', 'temporal': 'compatible'}

**AI REVIEW B**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `REUSE_CANONICAL`; target: `NODE_20260817_3A173B33`; confidence: HIGH; materiality: LOW.
- reason: Exact active catalog identity: Silicon Interposer to Silicon Interposer; source uses the same Product object.
- evidence assessment: SC-EV-34A6DFF0912F7884 from SC-P0-010_2025_IRDS_Lithography_and_Patterning.pdf [source SC-PHYS-318D85A127B5B6DF; SHA 318d85a127b5b6dfa7b3c1330ae20b18d63660a1fa8c8bdfdd7b478844e145ed; PDF p.21, Packaging Lithography]: This roadmap focuses on two types of interposer products. 1) Silicon interposers and silicon bridge interposers—This type uses fine re-distribution layers (RDLs) on silicon substrate formed by BEOL processes for fine pitch interconnections. 2) Organic interposers and RDL interposers—This type has RDLs only in organic layers for die-to-die interconnections. | SC-EV-A5D5D8057F31DBE3 from SC-P0-020B_TSMC_2025_Annual_Report.pdf [source F018b; SHA 3fb7ae4ad972aa2bc6e45bb36635152ad89d52f4a7165f389bcb94eeb54a6abd; PDF p.53, TSMC 3DFabric / CoWoS-S]: CoWoS® with silicon interposer (CoWoS®-S) advanced packaging service features high interconnect routing density and embedded deep trench capacitor (eDTC) and has been in volume production for several years. Boundary: Exact active catalog identity: Silicon Interposer to Silicon Interposer; source uses the same Product object. All source excerpts remain UNAUTHORIZED_CANDIDATE evidence.
- temporal scope assessed: 2025
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'same', 'object_type': 'compatible', 'scope': 'compatible', 'granularity': 'same', 'quarantine': 'clear', 'ontology': 'compatible', 'evidence_sufficiency': 'sufficient', 'temporal': 'compatible'}

**A/B RECONCILIATION**

- A_B_SUBSTANTIVE_AGREEMENT; disagreement type: none; native-operation conflict: false; target conflict: false.
- Interpretation differences: none.
- Reconciliation assessment: Same native operation, target, and material interpretation.
- Non-material rubric-label differences retained for audit: none.

**EVIDENCE SUMMARY**

- Source `SC-PHYS-318D85A127B5B6DF` (SHA-256 `318d85a127b5b6dfa7b3c1330ae20b18d63660a1fa8c8bdfdd7b478844e145ed`), file `SC-P0-010_2025_IRDS_Lithography_and_Patterning.pdf`, p. 21, section Packaging Lithography; evidence `SC-EV-34A6DFF0912F7884`; as-of 2025; excerpt: “This roadmap focuses on two types of interposer products. 1) Silicon interposers and silicon bridge interposers—This type uses fine re-distribution layers (RDLs) on silicon substrate formed by BEOL processes for fine pitch interconnections. 2) Organic interposers and RDL interposers—This type has RDLs only in organic layers for die-to-die interconnections.”
- Source `F018b` (SHA-256 `3fb7ae4ad972aa2bc6e45bb36635152ad89d52f4a7165f389bcb94eeb54a6abd`), file `SC-P0-020B_TSMC_2025_Annual_Report.pdf`, p. 53, section TSMC 3DFabric / CoWoS-S; evidence `SC-EV-A5D5D8057F31DBE3`; as-of 2025; excerpt: “CoWoS® with silicon interposer (CoWoS®-S) advanced packaging service features high interconnect routing density and embedded deep trench capacitor (eDTC) and has been in volume production for several years.”
- Temporal scope: source as-of dates above; no relation temporal claim.

- SYSTEM_RECOMMENDED_DECISION: `REUSE_CANONICAL`.
- SYSTEM_RECOMMENDATION_REASON: A/B substantive consensus; frozen automated outcome: REUSE_CANONICAL.
- HUMAN_USER_DECISION = PENDING
- VALID NATIVE OPTIONS: REUSE_CANONICAL, CREATE_NEW_CANONICAL, KEEP_DOMAIN_SPECIFIC, DEFER, REJECT; REUSE requires an explicit validated target ID and all options remain subject to frozen controls.

### Item 031 — SC-CN-0136 — Silicon Photonics

- ITEM_NUMBER: 31; ITEM_ID: `SC-CN-0136`; OBJECT_TYPE: identity.
- DOMAIN / context: `07_more_than_moore` Semiconductor structured Foundation candidate against shared AI Hardware canonical catalog; cross-domain status: `GOVERNED_REUSE`.
- AUTOMATED_STAGE3_OUTCOME: `REUSE_CANONICAL`; CURRENT_CANONICAL_TARGET: `NODE_20260814_A1DA7680`.
- Possible existing canonical IDs (unresolved unless explicitly reused): `NODE_20260814_A1DA7680`.
- CANDIDATE_SUMMARY: Silicon Photonics; candidate type `Technology`; comparison scope `复用当前Context Pack的active身份；保留ID、规范名和类型。`; frozen candidate rationale: 复用当前Context Pack的active身份；保留ID、规范名和类型。
- WHY_HUMAN_REQUIRED: frozen Stage 3 mandatory review population; automated reasons: EXACT_SHARED_CATALOG_IDENTITY.
- RISK_FLAGS: A=EXACT_SHARED_CATALOG_IDENTITY; B=ALIAS_OR_TRANSLATION.

**AI REVIEW A**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `REUSE_CANONICAL`; target: `NODE_20260814_A1DA7680`; confidence: MEDIUM; materiality: HIGH.
- reason: 硅光 is a registered alias of the active silicon-photonics Technology, not a generic PIC Product.
- evidence assessment: The source discusses silicon photonics and laser integration, consistent with the technology boundary though it does not authorize a PIC merge.
- temporal scope assessed: {'source_as_of': ['2024'], 'publication_date': [None], 'identity_claim': 'candidate_only'}
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'same', 'object_type': 'compatible', 'scope': 'compatible', 'granularity': 'same', 'quarantine': 'clear', 'ontology': 'compatible', 'evidence_sufficiency': 'sufficient', 'temporal': 'compatible'}

**AI REVIEW B**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `REUSE_CANONICAL`; target: `NODE_20260814_A1DA7680`; confidence: MEDIUM; materiality: LOW.
- reason: Exact active catalog identity: Silicon Photonics to 硅光; source uses the same Technology object.
- evidence assessment: SC-EV-0BB79B11D73733F8 from SC-P0-015_2024_IRDS_Outside_System_Connectivity.pdf [source SC-PHYS-EECFB29D71F7359F; SHA eecfb29d71f7359fccc255f854e9efe7262f82f06fad04ee56ecb871cf6defee; PDF p.41, 6.2 Photonic Integrated Circuits and Devices]: There is significant discussion over whether the laser should be packaged separately or integrated on the silicon photonics due to the high temperatures generated by the switching IC, which would cause thermal drift of wavelength and reduce the life of the laser. Boundary: Exact active catalog identity: Silicon Photonics to 硅光; source uses the same Technology object. All source excerpts remain UNAUTHORIZED_CANDIDATE evidence.
- temporal scope assessed: 2024
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'same', 'object_type': 'compatible', 'scope': 'compatible', 'granularity': 'same', 'quarantine': 'clear', 'ontology': 'compatible', 'evidence_sufficiency': 'sufficient', 'temporal': 'compatible'}

**A/B RECONCILIATION**

- A_B_SUBSTANTIVE_AGREEMENT; disagreement type: none; native-operation conflict: false; target conflict: false.
- Interpretation differences: none.
- Reconciliation assessment: Same native operation, target, and material interpretation.
- Non-material rubric-label differences retained for audit: none.

**EVIDENCE SUMMARY**

- Source `SC-PHYS-EECFB29D71F7359F` (SHA-256 `eecfb29d71f7359fccc255f854e9efe7262f82f06fad04ee56ecb871cf6defee`), file `SC-P0-015_2024_IRDS_Outside_System_Connectivity.pdf`, p. 41, section 6.2 Photonic Integrated Circuits and Devices; evidence `SC-EV-0BB79B11D73733F8`; as-of 2024; excerpt: “There is significant discussion over whether the laser should be packaged separately or integrated on the silicon photonics due to the high temperatures generated by the switching IC, which would cause thermal drift of wavelength and reduce the life of the laser.”
- Temporal scope: source as-of dates above; no relation temporal claim.

- SYSTEM_RECOMMENDED_DECISION: `REUSE_CANONICAL`.
- SYSTEM_RECOMMENDATION_REASON: A/B substantive consensus; frozen automated outcome: REUSE_CANONICAL.
- HUMAN_USER_DECISION = PENDING
- VALID NATIVE OPTIONS: REUSE_CANONICAL, CREATE_NEW_CANONICAL, KEEP_DOMAIN_SPECIFIC, DEFER, REJECT; REUSE requires an explicit validated target ID and all options remain subject to frozen controls.

### Item 032 — SC-CN-0150 — SoIC

- ITEM_NUMBER: 32; ITEM_ID: `SC-CN-0150`; OBJECT_TYPE: identity.
- DOMAIN / context: `09_cross_domain_reuse` Semiconductor structured Foundation candidate against shared AI Hardware canonical catalog; cross-domain status: `GOVERNED_REUSE`.
- AUTOMATED_STAGE3_OUTCOME: `REUSE_CANONICAL`; CURRENT_CANONICAL_TARGET: `NODE_44D6561B5D639E9A`.
- Possible existing canonical IDs (unresolved unless explicitly reused): `NODE_44D6561B5D639E9A`.
- CANDIDATE_SUMMARY: SoIC; candidate type `Technology`; comparison scope `复用当前Context Pack的active身份；保留ID、规范名和类型。`; frozen candidate rationale: 复用当前Context Pack的active身份；保留ID、规范名和类型。
- WHY_HUMAN_REQUIRED: frozen Stage 3 mandatory review population; automated reasons: EXACT_SHARED_CATALOG_IDENTITY.
- RISK_FLAGS: A=EXACT_SHARED_CATALOG_IDENTITY; B=ALIAS_OR_TRANSLATION.

**AI REVIEW A**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `REUSE_CANONICAL`; target: `NODE_44D6561B5D639E9A`; confidence: HIGH; materiality: MEDIUM.
- reason: System on Integrated Chips uses the registered SoIC identity for TSMC's stacking Technology.
- evidence assessment: The TSMC passage explicitly pairs SoIC with vertical integration and chiplet architecture.
- temporal scope assessed: {'source_as_of': ['2025'], 'publication_date': [None], 'identity_claim': 'candidate_only'}
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'same', 'object_type': 'compatible', 'scope': 'compatible', 'granularity': 'same', 'quarantine': 'clear', 'ontology': 'compatible', 'evidence_sufficiency': 'sufficient', 'temporal': 'compatible'}

**AI REVIEW B**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `REUSE_CANONICAL`; target: `NODE_44D6561B5D639E9A`; confidence: MEDIUM; materiality: LOW.
- reason: Exact active catalog identity: SoIC to System on Integrated Chips; source uses the same Technology object.
- evidence assessment: SC-EV-2BD04E0EEBBAD758 from SC-P0-020B_TSMC_2025_Annual_Report.pdf [source F018b; SHA 3fb7ae4ad972aa2bc6e45bb36635152ad89d52f4a7165f389bcb94eeb54a6abd; PDF p.53, TSMC 3DFabric / SoIC]: TSMC-SoIC® Chip-on-Wafer (CoW) 3D vertical integration solution offers high-density interconnect for chiplet architecture for HPC products. 3nm system on integrated chip (SoIC) stacking technology successfully entered volume production in 2025. Boundary: Exact active catalog identity: SoIC to System on Integrated Chips; source uses the same Technology object. All source excerpts remain UNAUTHORIZED_CANDIDATE evidence.
- temporal scope assessed: 2025
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'same', 'object_type': 'compatible', 'scope': 'compatible', 'granularity': 'same', 'quarantine': 'clear', 'ontology': 'compatible', 'evidence_sufficiency': 'sufficient', 'temporal': 'compatible'}

**A/B RECONCILIATION**

- A_B_SUBSTANTIVE_AGREEMENT; disagreement type: none; native-operation conflict: false; target conflict: false.
- Interpretation differences: none.
- Reconciliation assessment: Same native operation, target, and material interpretation.
- Non-material rubric-label differences retained for audit: none.

**EVIDENCE SUMMARY**

- Source `F018b` (SHA-256 `3fb7ae4ad972aa2bc6e45bb36635152ad89d52f4a7165f389bcb94eeb54a6abd`), file `SC-P0-020B_TSMC_2025_Annual_Report.pdf`, p. 53, section TSMC 3DFabric / SoIC; evidence `SC-EV-2BD04E0EEBBAD758`; as-of 2025; excerpt: “TSMC-SoIC® Chip-on-Wafer (CoW) 3D vertical integration solution offers high-density interconnect for chiplet architecture for HPC products. 3nm system on integrated chip (SoIC) stacking technology successfully entered volume production in 2025.”
- Temporal scope: source as-of dates above; no relation temporal claim.

- SYSTEM_RECOMMENDED_DECISION: `REUSE_CANONICAL`.
- SYSTEM_RECOMMENDATION_REASON: A/B substantive consensus; frozen automated outcome: REUSE_CANONICAL.
- HUMAN_USER_DECISION = PENDING
- VALID NATIVE OPTIONS: REUSE_CANONICAL, CREATE_NEW_CANONICAL, KEEP_DOMAIN_SPECIFIC, DEFER, REJECT; REUSE requires an explicit validated target ID and all options remain subject to frozen controls.

### Item 035 — SC-CN-0154 — 3D Stacking

- ITEM_NUMBER: 35; ITEM_ID: `SC-CN-0154`; OBJECT_TYPE: identity.
- DOMAIN / context: `04_device_scaling_memory` Semiconductor structured Foundation candidate against shared AI Hardware canonical catalog; cross-domain status: `GOVERNED_REUSE`.
- AUTOMATED_STAGE3_OUTCOME: `REUSE_CANONICAL`; CURRENT_CANONICAL_TARGET: `NODE_20260817_8006A0B4`.
- Possible existing canonical IDs (unresolved unless explicitly reused): `NODE_20260817_8006A0B4`.
- CANDIDATE_SUMMARY: 3D Stacking; candidate type `Technology`; comparison scope `复用当前Context Pack的active身份；保留ID、规范名和类型。`; frozen candidate rationale: 复用当前Context Pack的active身份；保留ID、规范名和类型。
- WHY_HUMAN_REQUIRED: frozen Stage 3 mandatory review population; automated reasons: EXACT_SHARED_CATALOG_IDENTITY.
- RISK_FLAGS: A=EXACT_SHARED_CATALOG_IDENTITY; B=FROZEN_STAGE2_DECISION.

**AI REVIEW A**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `REUSE_CANONICAL`; target: `NODE_20260817_8006A0B4`; confidence: HIGH; materiality: MEDIUM.
- reason: 3D Stacking matches the active Technology exactly; hybrid bonding is one means, not a replacement identity.
- evidence assessment: IRDS discusses fine-pitch 3D assembly and examples, supporting the existing broad stacking concept.
- temporal scope assessed: {'source_as_of': ['2024', '2020'], 'publication_date': [None], 'identity_claim': 'candidate_only'}
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'same', 'object_type': 'compatible', 'scope': 'compatible', 'granularity': 'same', 'quarantine': 'clear', 'ontology': 'compatible', 'evidence_sufficiency': 'sufficient', 'temporal': 'compatible'}

**AI REVIEW B**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `REUSE_CANONICAL`; target: `NODE_20260817_8006A0B4`; confidence: MEDIUM; materiality: LOW.
- reason: Exact active catalog identity: 3D Stacking to 3D Stacking; source uses the same Technology object.
- evidence assessment: SC-EV-502921FAD7A062A0 from SC-P0-009_2024_IRDS_More_Moore.pdf [source SC-PHYS-49A1D3B42E458985; SHA 49a1d3b42e45898555490e602170876e22d1ccf8d7c17711e436d8db36322fa6; PDF p.22, 4.6 3D Integration]: this slow-down has been accompanied by fine-pitch 3D stacking assembly such as ubump stacking and hybrid bonding [21]. | SC-EV-EFC0887512104389 from SC-P0-017_2020_IRDS_Packaging_Integration.pdf [source SC-PHYS-54CABB8879E180A7; SHA 54cabb8879e180a7a0363e8964cb2d28735eff03ecee6a45905cd54f06eae5e2; PDF p.16, 3D Stacks / HBM]: Under these conditions new high bandwidth memories (HBM) have been optimized for 3D die stacking (Figure PI-6). Boundary: Exact active catalog identity: 3D Stacking to 3D Stacking; source uses the same Technology object. All source excerpts remain UNAUTHORIZED_CANDIDATE evidence.
- temporal scope assessed: 2024
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'same', 'object_type': 'compatible', 'scope': 'compatible', 'granularity': 'same', 'quarantine': 'clear', 'ontology': 'compatible', 'evidence_sufficiency': 'sufficient', 'temporal': 'compatible'}

**A/B RECONCILIATION**

- A_B_SUBSTANTIVE_AGREEMENT; disagreement type: none; native-operation conflict: false; target conflict: false.
- Interpretation differences: none.
- Reconciliation assessment: Same native operation, target, and material interpretation.
- Non-material rubric-label differences retained for audit: none.

**EVIDENCE SUMMARY**

- Source `SC-PHYS-49A1D3B42E458985` (SHA-256 `49a1d3b42e45898555490e602170876e22d1ccf8d7c17711e436d8db36322fa6`), file `SC-P0-009_2024_IRDS_More_Moore.pdf`, p. 22, section 4.6 3D Integration; evidence `SC-EV-502921FAD7A062A0`; as-of 2024; excerpt: “this slow-down has been accompanied by fine-pitch 3D stacking assembly such as ubump stacking and hybrid bonding [21].”
- Source `SC-PHYS-54CABB8879E180A7` (SHA-256 `54cabb8879e180a7a0363e8964cb2d28735eff03ecee6a45905cd54f06eae5e2`), file `SC-P0-017_2020_IRDS_Packaging_Integration.pdf`, p. 16, section 3D Stacks / HBM; evidence `SC-EV-EFC0887512104389`; as-of 2020; excerpt: “Under these conditions new high bandwidth memories (HBM) have been optimized for 3D die stacking (Figure PI-6).”
- Temporal scope: source as-of dates above; no relation temporal claim.

- SYSTEM_RECOMMENDED_DECISION: `REUSE_CANONICAL`.
- SYSTEM_RECOMMENDATION_REASON: A/B substantive consensus; frozen automated outcome: REUSE_CANONICAL.
- HUMAN_USER_DECISION = PENDING
- VALID NATIVE OPTIONS: REUSE_CANONICAL, CREATE_NEW_CANONICAL, KEEP_DOMAIN_SPECIFIC, DEFER, REJECT; REUSE requires an explicit validated target ID and all options remain subject to frozen controls.

### Item 036 — SC-CN-0152 — 3DFabric

- ITEM_NUMBER: 36; ITEM_ID: `SC-CN-0152`; OBJECT_TYPE: identity.
- DOMAIN / context: `09_cross_domain_reuse` Semiconductor structured Foundation candidate against shared AI Hardware canonical catalog; cross-domain status: `REVIEW_REQUIRED`.
- AUTOMATED_STAGE3_OUTCOME: `DEFER`; CURRENT_CANONICAL_TARGET: `none`.
- Possible existing canonical IDs (unresolved unless explicitly reused): `none`.
- CANDIDATE_SUMMARY: 3DFabric; candidate type `Technology`; comparison scope `厂商服务体系/品牌伞；仅覆盖TSMC，不与Generic Advanced Packaging合并。`; frozen candidate rationale: 厂商服务体系/品牌伞；仅覆盖TSMC，不与Generic Advanced Packaging合并。
- WHY_HUMAN_REQUIRED: frozen Stage 3 mandatory review population; automated reasons: AMBIGUOUS_IDENTITY, FROZEN_STAGE2_HUMAN_DECISION.
- RISK_FLAGS: A=AMBIGUOUS_IDENTITY, FROZEN_STAGE2_HUMAN_DECISION; B=FROZEN_STAGE2_DECISION, UNRESOLVED_IDENTITY, SCOPE_OR_TYPE_BOUNDARY.

**AI REVIEW A**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `DEFER`; target: `none`; confidence: HIGH; materiality: HIGH.
- reason: 3DFabric is TSMC's service umbrella, not generic Advanced Packaging; the Stage 2 DEFER remains appropriate.
- evidence assessment: TSMC lists SoIC, CoWoS and other branded services under 3DFabric, proving a brand family but not an approved canonical boundary.
- temporal scope assessed: {'source_as_of': ['2025'], 'publication_date': [None], 'identity_claim': 'candidate_only'}
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'ambiguous', 'object_type': 'unknown', 'scope': 'unknown', 'granularity': 'unknown', 'quarantine': 'clear', 'ontology': 'compatible', 'evidence_sufficiency': 'sufficient', 'temporal': 'compatible'}

**AI REVIEW B**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `DEFER`; target: `none`; confidence: LOW; materiality: HIGH.
- reason: 3DFabric is a TSMC service portfolio containing SoIC and CoWoS; a vendor umbrella is not generic Advanced Packaging Technology.
- evidence assessment: SC-EV-407CEF45C2BE2751 from SC-P0-020B_TSMC_2025_Annual_Report.pdf [source F018b; SHA 3fb7ae4ad972aa2bc6e45bb36635152ad89d52f4a7165f389bcb94eeb54a6abd; PDF p.60, 5.4.2 Open Innovation Platform / 3DFabric services]: using TSMC 3DFabric® advanced packaging services, which include TSMC-SoIC®, CoWoS®, TSMC-SoWTM, and TSMC COUPETM, and achieve system and process co-optimization. Boundary: 3DFabric is a TSMC service portfolio containing SoIC and CoWoS; a vendor umbrella is not generic Advanced Packaging Technology. All source excerpts remain UNAUTHORIZED_CANDIDATE evidence.
- temporal scope assessed: 2025
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'ambiguous', 'object_type': 'mismatch', 'scope': 'mismatch', 'granularity': 'different', 'quarantine': 'preserved', 'ontology': 'pressure', 'evidence_sufficiency': 'limited', 'temporal': 'unresolved'}

**A/B RECONCILIATION**

- A_B_SUBSTANTIVE_AGREEMENT; disagreement type: none; native-operation conflict: false; target conflict: false.
- Interpretation differences: none.
- Reconciliation assessment: Both reviewers preserve the same governed hold. Rubric labels distinguish source support for a concept from sufficiency for canonical admission.
- Non-material rubric-label differences retained for audit: evidence_sufficiency, granularity, object_type, ontology, quarantine, scope, temporal.

**EVIDENCE SUMMARY**

- Source `F018b` (SHA-256 `3fb7ae4ad972aa2bc6e45bb36635152ad89d52f4a7165f389bcb94eeb54a6abd`), file `SC-P0-020B_TSMC_2025_Annual_Report.pdf`, p. 60, section 5.4.2 Open Innovation Platform / 3DFabric services; evidence `SC-EV-407CEF45C2BE2751`; as-of 2025; excerpt: “using TSMC 3DFabric® advanced packaging services, which include TSMC-SoIC®, CoWoS®, TSMC-SoWTM, and TSMC COUPETM, and achieve system and process co-optimization.”
- Temporal scope: source as-of dates above; no relation temporal claim.

- SYSTEM_RECOMMENDED_DECISION: `DEFER`.
- SYSTEM_RECOMMENDATION_REASON: Frozen structural, Stage 2 decision, evidence, or temporal exception remains unresolved.
- HUMAN_USER_DECISION = PENDING
- VALID NATIVE OPTIONS: REUSE_CANONICAL, CREATE_NEW_CANONICAL, KEEP_DOMAIN_SPECIFIC, DEFER, REJECT; REUSE requires an explicit validated target ID and all options remain subject to frozen controls.

### Item 037 — SC-CN-0089 — Thermal Interface Material

- ITEM_NUMBER: 37; ITEM_ID: `SC-CN-0089`; OBJECT_TYPE: identity.
- DOMAIN / context: `08_assembly_packaging` Semiconductor structured Foundation candidate against shared AI Hardware canonical catalog; cross-domain status: `DISTINCT_BROADER_OR_DIFFERENT_OBJECT`.
- AUTOMATED_STAGE3_OUTCOME: `CREATE_NEW_CANONICAL`; CURRENT_CANONICAL_TARGET: `NODE_54340D9806971D42`.
- Possible existing canonical IDs (unresolved unless explicitly reused): `none`.
- CANDIDATE_SUMMARY: Thermal Interface Material; candidate type `Material`; comparison scope `Source支持可复用的持久研究对象，未命中现有规范名或已登记别名。`; frozen candidate rationale: Source支持可复用的持久研究对象，未命中现有规范名或已登记别名。
- WHY_HUMAN_REQUIRED: frozen Stage 3 mandatory review population; automated reasons: NEW_CANONICAL_NODE, NO_SHARED_CATALOG_MATCH.
- RISK_FLAGS: A=NEW_CANONICAL_NODE, NO_SHARED_CATALOG_MATCH; B=none.

**AI REVIEW A**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `CREATE_NEW_CANONICAL`; target: `NODE_54340D9806971D42`; confidence: HIGH; materiality: MEDIUM.
- reason: Thermal Interface Material is a distinct package material class without a catalog match.
- evidence assessment: Intel describes applying it to a die before adding a heat-spreader lid, directly identifying the material's role.
- temporal scope assessed: {'source_as_of': ['2025-02-19'], 'publication_date': ['2025-02-19'], 'identity_claim': 'candidate_only'}
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'distinct', 'object_type': 'compatible', 'scope': 'compatible', 'granularity': 'unknown', 'quarantine': 'clear', 'ontology': 'compatible', 'evidence_sufficiency': 'sufficient', 'temporal': 'compatible'}

**AI REVIEW B**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `CREATE_NEW_CANONICAL`; target: `NODE_54340D9806971D42`; confidence: HIGH; materiality: LOW.
- reason: Thermal interface material is applied between die and lid in the Intel example; the Material class has no frozen exact target.
- evidence assessment: SC-EV-B0D5FDA1CCB11F5D from SC-P0-016_Intel_Assembly_and_Test.pdf [source SC-PHYS-792E7A66390A5C02; SHA 792e7a66390a5c02a43280077fb1e586a3e46f4abf215608dc831ce5ab665db4; PDF p.5, Step 3: Lid Attach]: Machines apply thermal interface material onto the die and then place a heat spreader (known as a lid) on top. The lid helps dissipate heat. Boundary: Thermal interface material is applied between die and lid in the Intel example; the Material class has no frozen exact target. All source excerpts remain UNAUTHORIZED_CANDIDATE evidence.
- temporal scope assessed: 2025-02-19
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'distinct', 'object_type': 'compatible', 'scope': 'compatible', 'granularity': 'different', 'quarantine': 'clear', 'ontology': 'compatible', 'evidence_sufficiency': 'sufficient', 'temporal': 'compatible'}

**A/B RECONCILIATION**

- A_B_SUBSTANTIVE_AGREEMENT; disagreement type: none; native-operation conflict: false; target conflict: false.
- Interpretation differences: none.
- Reconciliation assessment: Both reviewers propose the same distinct candidate. Scope and granularity labels compare it with different reference objects, without changing the identity boundary.
- Non-material rubric-label differences retained for audit: granularity.

**EVIDENCE SUMMARY**

- Source `SC-PHYS-792E7A66390A5C02` (SHA-256 `792e7a66390a5c02a43280077fb1e586a3e46f4abf215608dc831ce5ab665db4`), file `SC-P0-016_Intel_Assembly_and_Test.pdf`, p. 5, section Step 3: Lid Attach; evidence `SC-EV-B0D5FDA1CCB11F5D`; as-of 2025-02-19; excerpt: “Machines apply thermal interface material onto the die and then place a heat spreader (known as a lid) on top. The lid helps dissipate heat.”
- Temporal scope: source as-of dates above; no relation temporal claim.

- SYSTEM_RECOMMENDED_DECISION: `CREATE_NEW_CANONICAL`.
- SYSTEM_RECOMMENDATION_REASON: A/B substantive consensus; frozen automated outcome: CREATE_NEW_CANONICAL.
- HUMAN_USER_DECISION = PENDING
- VALID NATIVE OPTIONS: REUSE_CANONICAL, CREATE_NEW_CANONICAL, KEEP_DOMAIN_SPECIFIC, DEFER, REJECT; REUSE requires an explicit validated target ID and all options remain subject to frozen controls.

### Item 038 — SC-CN-0139 — TSV

- ITEM_NUMBER: 38; ITEM_ID: `SC-CN-0139`; OBJECT_TYPE: identity.
- DOMAIN / context: `08_assembly_packaging` Semiconductor structured Foundation candidate against shared AI Hardware canonical catalog; cross-domain status: `GOVERNED_REUSE`.
- AUTOMATED_STAGE3_OUTCOME: `REUSE_CANONICAL`; CURRENT_CANONICAL_TARGET: `NODE_20260817_6EA7B10F`.
- Possible existing canonical IDs (unresolved unless explicitly reused): `NODE_20260817_6EA7B10F`.
- CANDIDATE_SUMMARY: TSV; candidate type `Technology`; comparison scope `证据原文使用TSVs；对应缩写基词已登记，保留复数观察。`; frozen candidate rationale: 复用当前Context Pack的active身份；保留ID、规范名和类型。
- WHY_HUMAN_REQUIRED: frozen Stage 3 mandatory review population; automated reasons: EXACT_SHARED_CATALOG_IDENTITY.
- RISK_FLAGS: A=EXACT_SHARED_CATALOG_IDENTITY; B=ALIAS_OR_TRANSLATION.

**AI REVIEW A**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `REUSE_CANONICAL`; target: `NODE_20260817_6EA7B10F`; confidence: HIGH; materiality: MEDIUM.
- reason: Through-Silicon Via maps to the registered TSV alias and active Technology node.
- evidence assessment: IRDS connects TSV arrays to HBM die-to-die data transfer, fitting the interconnect technology.
- temporal scope assessed: {'source_as_of': ['2020', '2026-03'], 'publication_date': [None, '2026-03'], 'identity_claim': 'candidate_only'}
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'same', 'object_type': 'compatible', 'scope': 'compatible', 'granularity': 'same', 'quarantine': 'clear', 'ontology': 'compatible', 'evidence_sufficiency': 'sufficient', 'temporal': 'compatible'}

**AI REVIEW B**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `REUSE_CANONICAL`; target: `NODE_20260817_6EA7B10F`; confidence: MEDIUM; materiality: LOW.
- reason: Exact active catalog identity: TSV to Through-Silicon Via; source uses the same Technology object.
- evidence assessment: SC-EV-B87D40867DB6A731 from SC-P0-017_2020_IRDS_Packaging_Integration.pdf [source SC-PHYS-54CABB8879E180A7; SHA 54cabb8879e180a7a0363e8964cb2d28735eff03ecee6a45905cd54f06eae5e2; PDF p.16, 3D Stacks / HBM]: Because of the large array of TSVs available in HBM stacks to transfer data between individual die (e.g., a controller at the base topped by 4-8 DRAM die) | SC-EV-5C8A70D896D693D9 from SC-P0-018_2025_HIR_Materials_and_Interfaces_Advanced_Packaging.pdf [source SC-PHYS-2E34AF6DD70E8C2C; SHA 2e34af6dd70e8c2c5de2aaabec15837693d1322abc0bb5820475188cd028a3f2; PDF p.17, 2.3.1.1 Package Cooling / embedded cooling co-design]: Besides custom cooling microchannel design for high-power densities, the 2-phase embedded cooling system requires co-design of through silicon vias (TSV) since the bumps from the laminate will need TSVs to thread past the embedded cooling microchannel structure to connect the bumps to the chip BEOL. Boundary: Exact active catalog identity: TSV to Through-Silicon Via; source uses the same Technology object. All source excerpts remain UNAUTHORIZED_CANDIDATE evidence.
- temporal scope assessed: 2020
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'same', 'object_type': 'compatible', 'scope': 'compatible', 'granularity': 'same', 'quarantine': 'clear', 'ontology': 'compatible', 'evidence_sufficiency': 'sufficient', 'temporal': 'compatible'}

**A/B RECONCILIATION**

- A_B_SUBSTANTIVE_AGREEMENT; disagreement type: none; native-operation conflict: false; target conflict: false.
- Interpretation differences: none.
- Reconciliation assessment: Same native operation, target, and material interpretation.
- Non-material rubric-label differences retained for audit: none.

**EVIDENCE SUMMARY**

- Source `SC-PHYS-54CABB8879E180A7` (SHA-256 `54cabb8879e180a7a0363e8964cb2d28735eff03ecee6a45905cd54f06eae5e2`), file `SC-P0-017_2020_IRDS_Packaging_Integration.pdf`, p. 16, section 3D Stacks / HBM; evidence `SC-EV-B87D40867DB6A731`; as-of 2020; excerpt: “Because of the large array of TSVs available in HBM stacks to transfer data between individual die (e.g., a controller at the base topped by 4-8 DRAM die)”
- Source `SC-PHYS-2E34AF6DD70E8C2C` (SHA-256 `2e34af6dd70e8c2c5de2aaabec15837693d1322abc0bb5820475188cd028a3f2`), file `SC-P0-018_2025_HIR_Materials_and_Interfaces_Advanced_Packaging.pdf`, p. 17, section 2.3.1.1 Package Cooling / embedded cooling co-design; evidence `SC-EV-5C8A70D896D693D9`; as-of 2026-03; excerpt: “Besides custom cooling microchannel design for high-power densities, the 2-phase embedded cooling system requires co-design of through silicon vias (TSV) since the bumps from the laminate will need TSVs to thread past the embedded cooling microchannel structure to connect the bumps to the chip BEOL.”
- Temporal scope: source as-of dates above; no relation temporal claim.

- SYSTEM_RECOMMENDED_DECISION: `REUSE_CANONICAL`.
- SYSTEM_RECOMMENDATION_REASON: A/B substantive consensus; frozen automated outcome: REUSE_CANONICAL.
- HUMAN_USER_DECISION = PENDING
- VALID NATIVE OPTIONS: REUSE_CANONICAL, CREATE_NEW_CANONICAL, KEEP_DOMAIN_SPECIFIC, DEFER, REJECT; REUSE requires an explicit validated target ID and all options remain subject to frozen controls.

### Item 039 — SC-CN-0144 — UCIe

- ITEM_NUMBER: 39; ITEM_ID: `SC-CN-0144`; OBJECT_TYPE: identity.
- DOMAIN / context: `09_cross_domain_reuse` Semiconductor structured Foundation candidate against shared AI Hardware canonical catalog; cross-domain status: `GOVERNED_REUSE`.
- AUTOMATED_STAGE3_OUTCOME: `REUSE_CANONICAL`; CURRENT_CANONICAL_TARGET: `NODE_20260817_2E3D3BE2`.
- Possible existing canonical IDs (unresolved unless explicitly reused): `NODE_20260817_2E3D3BE2`.
- CANDIDATE_SUMMARY: UCIe; candidate type `Standard`; comparison scope `复用当前Context Pack的active身份；保留ID、规范名和类型。`; frozen candidate rationale: 复用当前Context Pack的active身份；保留ID、规范名和类型。
- WHY_HUMAN_REQUIRED: frozen Stage 3 mandatory review population; automated reasons: EXACT_SHARED_CATALOG_IDENTITY.
- RISK_FLAGS: A=EXACT_SHARED_CATALOG_IDENTITY; B=ALIAS_OR_TRANSLATION.

**AI REVIEW A**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `REUSE_CANONICAL`; target: `NODE_20260817_2E3D3BE2`; confidence: HIGH; materiality: HIGH.
- reason: Universal Chiplet Interconnect Express matches the registered UCIe Standard, independent of any particular version.
- evidence assessment: The standards source calls UCIe a framework for communication among diverse chiplets, supporting the base standard identity.
- temporal scope assessed: {'source_as_of': [None], 'publication_date': [None], 'identity_claim': 'candidate_only'}
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'same', 'object_type': 'compatible', 'scope': 'compatible', 'granularity': 'same', 'quarantine': 'clear', 'ontology': 'compatible', 'evidence_sufficiency': 'sufficient', 'temporal': 'compatible'}

**AI REVIEW B**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `REUSE_CANONICAL`; target: `NODE_20260817_2E3D3BE2`; confidence: MEDIUM; materiality: LOW.
- reason: Exact active catalog identity: UCIe to Universal Chiplet Interconnect Express; source uses the same Standard object.
- evidence assessment: SC-EV-6142D3B803848285 from SC-P0-019_UCIe_3_0_Specification_White_Paper.pdf [source F017; SHA 86eb13c30d0c5406b647a50107bc5c82ddfa5b4cf7aa36ab959cbe50d8a1ef19; PDF p.1, Introduction]: UCIe has emerged as the leading standard for chiplet interconnects, providing a uniﬁed framework for communication between diverse chiplets from multiple sources. | SC-EV-56A84BBF8CA0648F from SC-P0-019_UCIe_3_0_Specification_White_Paper.pdf [source F017; SHA 86eb13c30d0c5406b647a50107bc5c82ddfa5b4cf7aa36ab959cbe50d8a1ef19; PDF p.3, Support for Continuous Transmission Protocols]: UCIe 3.0 supports continuous transmission protocols by running the link at the same data rate as data generation and consumption. Boundary: Exact active catalog identity: UCIe to Universal Chiplet Interconnect Express; source uses the same Standard object. All source excerpts remain UNAUTHORIZED_CANDIDATE evidence.
- temporal scope assessed: not_established
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'same', 'object_type': 'compatible', 'scope': 'compatible', 'granularity': 'same', 'quarantine': 'clear', 'ontology': 'compatible', 'evidence_sufficiency': 'sufficient', 'temporal': 'compatible'}

**A/B RECONCILIATION**

- A_B_SUBSTANTIVE_AGREEMENT; disagreement type: none; native-operation conflict: false; target conflict: false.
- Interpretation differences: none.
- Reconciliation assessment: Same native operation, target, and material interpretation.
- Non-material rubric-label differences retained for audit: none.

**EVIDENCE SUMMARY**

- Source `F017` (SHA-256 `86eb13c30d0c5406b647a50107bc5c82ddfa5b4cf7aa36ab959cbe50d8a1ef19`), file `SC-P0-019_UCIe_3_0_Specification_White_Paper.pdf`, p. 1, section Introduction; evidence `SC-EV-6142D3B803848285`; as-of unknown; excerpt: “UCIe has emerged as the leading standard for chiplet interconnects, providing a uniﬁed framework for communication between diverse chiplets from multiple sources.”
- Source `F017` (SHA-256 `86eb13c30d0c5406b647a50107bc5c82ddfa5b4cf7aa36ab959cbe50d8a1ef19`), file `SC-P0-019_UCIe_3_0_Specification_White_Paper.pdf`, p. 3, section Support for Continuous Transmission Protocols; evidence `SC-EV-56A84BBF8CA0648F`; as-of unknown; excerpt: “UCIe 3.0 supports continuous transmission protocols by running the link at the same data rate as data generation and consumption.”
- Temporal scope: source as-of dates above; no relation temporal claim.

- SYSTEM_RECOMMENDED_DECISION: `REUSE_CANONICAL`.
- SYSTEM_RECOMMENDATION_REASON: A/B substantive consensus; frozen automated outcome: REUSE_CANONICAL.
- HUMAN_USER_DECISION = PENDING
- VALID NATIVE OPTIONS: REUSE_CANONICAL, CREATE_NEW_CANONICAL, KEEP_DOMAIN_SPECIFIC, DEFER, REJECT; REUSE requires an explicit validated target ID and all options remain subject to frozen controls.

### Item 040 — SC-CN-0145 — UCIe 3.0

- ITEM_NUMBER: 40; ITEM_ID: `SC-CN-0145`; OBJECT_TYPE: identity.
- DOMAIN / context: `09_cross_domain_reuse` Semiconductor structured Foundation candidate against shared AI Hardware canonical catalog; cross-domain status: `DISTINCT_BROADER_OR_DIFFERENT_OBJECT`.
- AUTOMATED_STAGE3_OUTCOME: `REJECT`; CURRENT_CANONICAL_TARGET: `none`.
- Possible existing canonical IDs (unresolved unless explicitly reused): `none`.
- CANDIDATE_SUMMARY: UCIe 3.0; candidate type `Standard`; comparison scope `规范版本作为UCIe的scope/Claim，不创建平行版本节点。`; frozen candidate rationale: 规范版本作为UCIe的scope/Claim，不创建平行版本节点。
- WHY_HUMAN_REQUIRED: frozen Stage 3 mandatory review population; automated reasons: FROZEN_STAGE2_REJECTION.
- RISK_FLAGS: A=FROZEN_STAGE2_REJECTION; B=SCOPE_OR_TYPE_BOUNDARY.

**AI REVIEW A**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `REJECT`; target: `none`; confidence: HIGH; materiality: MEDIUM.
- reason: UCIe 3.0 is a version of the UCIe Standard and should be retained as versioned Claim/scope, not a parallel node.
- evidence assessment: The excerpt attributes continuous-transmission support specifically to version 3.0; it supports a version-scoped fact, not new identity.
- temporal scope assessed: {'source_as_of': [None], 'publication_date': [None], 'identity_claim': 'candidate_only'}
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'distinct', 'object_type': 'compatible', 'scope': 'mismatch', 'granularity': 'different', 'quarantine': 'clear', 'ontology': 'compatible', 'evidence_sufficiency': 'sufficient', 'temporal': 'compatible'}

**AI REVIEW B**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `REJECT`; target: `none`; confidence: LOW; materiality: HIGH.
- reason: UCIe 3.0 is a versioned assertion about UCIe, not a second generic standard identity. Preserve Stage 2 REJECT.
- evidence assessment: SC-EV-56A84BBF8CA0648F from SC-P0-019_UCIe_3_0_Specification_White_Paper.pdf [source F017; SHA 86eb13c30d0c5406b647a50107bc5c82ddfa5b4cf7aa36ab959cbe50d8a1ef19; PDF p.3, Support for Continuous Transmission Protocols]: UCIe 3.0 supports continuous transmission protocols by running the link at the same data rate as data generation and consumption. Boundary: UCIe 3.0 is a versioned assertion about UCIe, not a second generic standard identity. Preserve Stage 2 REJECT. All source excerpts remain UNAUTHORIZED_CANDIDATE evidence.
- temporal scope assessed: not_established
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'distinct', 'object_type': 'compatible', 'scope': 'compatible', 'granularity': 'different', 'quarantine': 'clear', 'ontology': 'pressure', 'evidence_sufficiency': 'sufficient', 'temporal': 'compatible'}

**A/B RECONCILIATION**

- A_B_SUBSTANTIVE_AGREEMENT; disagreement type: none; native-operation conflict: false; target conflict: false.
- Interpretation differences: none.
- Reconciliation assessment: Both reviewers reject a versioned parallel node and retain version context as a claim or scope.
- Non-material rubric-label differences retained for audit: ontology, scope.

**EVIDENCE SUMMARY**

- Source `F017` (SHA-256 `86eb13c30d0c5406b647a50107bc5c82ddfa5b4cf7aa36ab959cbe50d8a1ef19`), file `SC-P0-019_UCIe_3_0_Specification_White_Paper.pdf`, p. 3, section Support for Continuous Transmission Protocols; evidence `SC-EV-56A84BBF8CA0648F`; as-of unknown; excerpt: “UCIe 3.0 supports continuous transmission protocols by running the link at the same data rate as data generation and consumption.”
- Temporal scope: source as-of dates above; no relation temporal claim.

- SYSTEM_RECOMMENDED_DECISION: `REJECT`.
- SYSTEM_RECOMMENDATION_REASON: A/B substantive consensus; frozen automated outcome: REJECT.
- HUMAN_USER_DECISION = PENDING
- VALID NATIVE OPTIONS: REUSE_CANONICAL, CREATE_NEW_CANONICAL, KEEP_DOMAIN_SPECIFIC, DEFER, REJECT; REUSE requires an explicit validated target ID and all options remain subject to frozen controls.

### Item 042 — SC-CN-0081 — Underfill

- ITEM_NUMBER: 42; ITEM_ID: `SC-CN-0081`; OBJECT_TYPE: identity.
- DOMAIN / context: `03_fab_process_equipment` Semiconductor structured Foundation candidate against shared AI Hardware canonical catalog; cross-domain status: `SEMICONDUCTOR_NATIVE`.
- AUTOMATED_STAGE3_OUTCOME: `REUSE_CANONICAL`; CURRENT_CANONICAL_TARGET: `NODE_20260817_397D3280`.
- Possible existing canonical IDs (unresolved unless explicitly reused): `NODE_20260817_397D3280`.
- CANDIDATE_SUMMARY: Underfill; candidate type `Material`; comparison scope `复用当前Context Pack的active身份；保留ID、规范名和类型。`; frozen candidate rationale: Cross-domain coverage annotation after freeze; exact same PASS A identity recommendation and evidence.
- WHY_HUMAN_REQUIRED: frozen Stage 3 mandatory review population; automated reasons: EXACT_SHARED_CATALOG_IDENTITY.
- RISK_FLAGS: A=EXACT_SHARED_CATALOG_IDENTITY; B=none.

**AI REVIEW A**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `REUSE_CANONICAL`; target: `NODE_20260817_397D3280`; confidence: HIGH; materiality: MEDIUM.
- reason: Underfill Material matches the active registered alias and remains a child of the broader encapsulant class.
- evidence assessment: The source lists underfill among connection-protecting encapsulants, supporting that material identity.
- temporal scope assessed: {'source_as_of': ['2026-03-04'], 'publication_date': ['2026-03-04'], 'identity_claim': 'candidate_only'}
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'same', 'object_type': 'compatible', 'scope': 'compatible', 'granularity': 'same', 'quarantine': 'clear', 'ontology': 'compatible', 'evidence_sufficiency': 'sufficient', 'temporal': 'compatible'}

**AI REVIEW B**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `REUSE_CANONICAL`; target: `NODE_20260817_397D3280`; confidence: HIGH; materiality: LOW.
- reason: Exact active catalog identity: Underfill to Underfill Material; source uses the same Material object.
- evidence assessment: SC-EV-7C75F6F0987ACA80 from SC-P0-008_Senate-EPW-testimony-3.4.2026.pdf [source SC-PHYS-C5B6DC633E156218; SHA c5b6dc633e156218eb950f2dee88f43fbdcc4fc1744a5924f12b977f5cb7df71; PDF p.6, II / Packaging]: To protect against humidity, chemicals, and vibration, connections are enclosed with encapsulants such as underfill, coatings, or mold compounds. Boundary: Exact active catalog identity: Underfill to Underfill Material; source uses the same Material object. All source excerpts remain UNAUTHORIZED_CANDIDATE evidence.
- temporal scope assessed: 2026-03-04
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'same', 'object_type': 'compatible', 'scope': 'compatible', 'granularity': 'same', 'quarantine': 'clear', 'ontology': 'compatible', 'evidence_sufficiency': 'sufficient', 'temporal': 'compatible'}

**A/B RECONCILIATION**

- A_B_SUBSTANTIVE_AGREEMENT; disagreement type: none; native-operation conflict: false; target conflict: false.
- Interpretation differences: none.
- Reconciliation assessment: Same native operation, target, and material interpretation.
- Non-material rubric-label differences retained for audit: none.

**EVIDENCE SUMMARY**

- Source `SC-PHYS-C5B6DC633E156218` (SHA-256 `c5b6dc633e156218eb950f2dee88f43fbdcc4fc1744a5924f12b977f5cb7df71`), file `SC-P0-008_Senate-EPW-testimony-3.4.2026.pdf`, p. 6, section II / Packaging; evidence `SC-EV-7C75F6F0987ACA80`; as-of 2026-03-04; excerpt: “To protect against humidity, chemicals, and vibration, connections are enclosed with encapsulants such as underfill, coatings, or mold compounds.”
- Temporal scope: source as-of dates above; no relation temporal claim.

- SYSTEM_RECOMMENDED_DECISION: `REUSE_CANONICAL`.
- SYSTEM_RECOMMENDATION_REASON: A/B substantive consensus; frozen automated outcome: REUSE_CANONICAL.
- HUMAN_USER_DECISION = PENDING
- VALID NATIVE OPTIONS: REUSE_CANONICAL, CREATE_NEW_CANONICAL, KEEP_DOMAIN_SPECIFIC, DEFER, REJECT; REUSE requires an explicit validated target ID and all options remain subject to frozen controls.

### Item 043 — SC-CN-0112 — Interposer

- ITEM_NUMBER: 43; ITEM_ID: `SC-CN-0112`; OBJECT_TYPE: identity.
- DOMAIN / context: `05_lithography_patterning` Semiconductor structured Foundation candidate against shared AI Hardware canonical catalog; cross-domain status: `SEMICONDUCTOR_NATIVE`.
- AUTOMATED_STAGE3_OUTCOME: `CREATE_NEW_CANONICAL`; CURRENT_CANONICAL_TARGET: `NODE_C37B83D6D0B8A843`.
- Possible existing canonical IDs (unresolved unless explicitly reused): `none`.
- CANDIDATE_SUMMARY: Interposer; candidate type `Product`; comparison scope `中间互连/节距转换基板，非Package Substrate的同义词。`; frozen candidate rationale: Cross-domain coverage annotation after freeze; exact same PASS A identity recommendation and evidence.
- WHY_HUMAN_REQUIRED: frozen Stage 3 mandatory review population; automated reasons: NEW_CANONICAL_NODE, NO_SHARED_CATALOG_MATCH.
- RISK_FLAGS: A=NEW_CANONICAL_NODE, NO_SHARED_CATALOG_MATCH; B=FROZEN_STAGE2_DECISION.

**AI REVIEW A**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `CREATE_NEW_CANONICAL`; target: `NODE_C37B83D6D0B8A843`; confidence: HIGH; materiality: HIGH.
- reason: Interposer is a generic intermediate substrate; Silicon and RDL Interposers are narrower products, and Package Substrate is a different position.
- evidence assessment: IRDS defines an interposer by die-to-die interconnection and pitch transformation toward the package substrate.
- temporal scope assessed: {'source_as_of': ['2025'], 'publication_date': [None], 'identity_claim': 'candidate_only'}
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'distinct', 'object_type': 'compatible', 'scope': 'mismatch', 'granularity': 'different', 'quarantine': 'clear', 'ontology': 'compatible', 'evidence_sufficiency': 'sufficient', 'temporal': 'compatible'}

**AI REVIEW B**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `CREATE_NEW_CANONICAL`; target: `NODE_C37B83D6D0B8A843`; confidence: MEDIUM; materiality: LOW.
- reason: Interposer is an intermediate die-to-die or pitch-conversion substrate, distinct from a package foundation substrate.
- evidence assessment: SC-EV-55BA223EDE3A8F9F from SC-P0-010_2025_IRDS_Lithography_and_Patterning.pdf [source SC-PHYS-318D85A127B5B6DF; SHA 318d85a127b5b6dfa7b3c1330ae20b18d63660a1fa8c8bdfdd7b478844e145ed; PDF p.21, Packaging Lithography]: Interposers are defined as intermediate substrates to realize interconnections between multiple dies and or to transform pitches between dice and a package substrate. Boundary: Interposer is an intermediate die-to-die or pitch-conversion substrate, distinct from a package foundation substrate. All source excerpts remain UNAUTHORIZED_CANDIDATE evidence.
- temporal scope assessed: 2025
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'distinct', 'object_type': 'compatible', 'scope': 'compatible', 'granularity': 'different', 'quarantine': 'clear', 'ontology': 'compatible', 'evidence_sufficiency': 'sufficient', 'temporal': 'compatible'}

**A/B RECONCILIATION**

- A_B_SUBSTANTIVE_AGREEMENT; disagreement type: none; native-operation conflict: false; target conflict: false.
- Interpretation differences: none.
- Reconciliation assessment: Both reviewers propose the same distinct candidate. Scope and granularity labels compare it with different reference objects, without changing the identity boundary.
- Non-material rubric-label differences retained for audit: scope.

**EVIDENCE SUMMARY**

- Source `SC-PHYS-318D85A127B5B6DF` (SHA-256 `318d85a127b5b6dfa7b3c1330ae20b18d63660a1fa8c8bdfdd7b478844e145ed`), file `SC-P0-010_2025_IRDS_Lithography_and_Patterning.pdf`, p. 21, section Packaging Lithography; evidence `SC-EV-55BA223EDE3A8F9F`; as-of 2025; excerpt: “Interposers are defined as intermediate substrates to realize interconnections between multiple dies and or to transform pitches between dice and a package substrate.”
- Temporal scope: source as-of dates above; no relation temporal claim.

- SYSTEM_RECOMMENDED_DECISION: `CREATE_NEW_CANONICAL`.
- SYSTEM_RECOMMENDATION_REASON: A/B substantive consensus; frozen automated outcome: CREATE_NEW_CANONICAL.
- HUMAN_USER_DECISION = PENDING
- VALID NATIVE OPTIONS: REUSE_CANONICAL, CREATE_NEW_CANONICAL, KEEP_DOMAIN_SPECIFIC, DEFER, REJECT; REUSE requires an explicit validated target ID and all options remain subject to frozen controls.

### Item 044 — OBS_656B35D110452867 — 2.5D integration

- ITEM_NUMBER: 44; ITEM_ID: `OBS_656B35D110452867`; OBJECT_TYPE: identity.
- DOMAIN / context: `semiconductor` Semiconductor structured Foundation candidate against shared AI Hardware canonical catalog; cross-domain status: `NO_NODE_OR_EDGE_EMITTED`.
- AUTOMATED_STAGE3_OUTCOME: `DEFER`; CURRENT_CANONICAL_TARGET: `none`.
- Possible existing canonical IDs (unresolved unless explicitly reused): `none`.
- CANDIDATE_SUMMARY: 2.5D integration; candidate type `unknown`; comparison scope `HIGH_PRIORITY_COVERAGE_CHECK_ONLY`; frozen candidate rationale: PI-12 was visually screened, but generic 2.5D wording to this governed identity was not admitted in PASS A.
- WHY_HUMAN_REQUIRED: frozen Stage 3 mandatory review population; automated reasons: NOT_ADMITTED_IN_STAGE2.
- RISK_FLAGS: A=NOT_ADMITTED_IN_STAGE2; B=UNRESOLVED_IDENTITY, NOT_ADMITTED_IN_STAGE2.

**AI REVIEW A**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `DEFER`; target: `none`; confidence: HIGH; materiality: LOW.
- reason: 2.5D integration was only visually screened; no admitted candidate connects it to 2.5D Interposer Packaging.
- evidence assessment: The observation has no frozen source span or evidence ID, so it cannot support identity reuse or creation.
- temporal scope assessed: {'source_as_of': [], 'publication_date': [], 'identity_claim': 'candidate_only'}
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'ambiguous', 'object_type': 'unknown', 'scope': 'unknown', 'granularity': 'unknown', 'quarantine': 'clear', 'ontology': 'compatible', 'evidence_sufficiency': 'insufficient', 'temporal': 'unresolved'}

**AI REVIEW B**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `DEFER`; target: `none`; confidence: LOW; materiality: MEDIUM.
- reason: 2.5D integration was screened as wording only; no admitted candidate or evidence binding proves equivalence to 2.5D Interposer Packaging.
- evidence assessment: No admitted candidate, source ID, or evidence excerpt for OBS_656B35D110452867; comparison wording alone cannot establish identity.
- temporal scope assessed: not_established
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'ambiguous', 'object_type': 'unknown', 'scope': 'unknown', 'granularity': 'unknown', 'quarantine': 'clear', 'ontology': 'unresolved', 'evidence_sufficiency': 'insufficient', 'temporal': 'compatible'}

**A/B RECONCILIATION**

- A_B_SUBSTANTIVE_AGREEMENT; disagreement type: none; native-operation conflict: false; target conflict: false.
- Interpretation differences: none.
- Reconciliation assessment: Both reviewers defer an observation with no admitted candidate or evidence. Ontology and temporal labels are not actionable without admission.
- Non-material rubric-label differences retained for audit: ontology, temporal.

**EVIDENCE SUMMARY**

- No admitted source excerpt is bound to this observation.
- Temporal scope: source as-of dates above; no relation temporal claim.

- SYSTEM_RECOMMENDED_DECISION: `DEFER`.
- SYSTEM_RECOMMENDATION_REASON: Frozen structural, Stage 2 decision, evidence, or temporal exception remains unresolved.
- HUMAN_USER_DECISION = PENDING
- VALID NATIVE OPTIONS: DEFER, REJECT for this unadmitted observation; CREATE/REUSE requires a separately admitted candidate.

### Item 045 — OBS_B13CBB8C551799BB — Co-Packaged Optics

- ITEM_NUMBER: 45; ITEM_ID: `OBS_B13CBB8C551799BB`; OBJECT_TYPE: identity.
- DOMAIN / context: `semiconductor` Semiconductor structured Foundation candidate against shared AI Hardware canonical catalog; cross-domain status: `NO_NODE_OR_EDGE_EMITTED`.
- AUTOMATED_STAGE3_OUTCOME: `DEFER`; CURRENT_CANONICAL_TARGET: `none`.
- Possible existing canonical IDs (unresolved unless explicitly reused): `NODE_20260814_7CC5B5D5`.
- CANDIDATE_SUMMARY: Co-Packaged Optics; candidate type `unknown`; comparison scope `HIGH_PRIORITY_COVERAGE_CHECK_ONLY`; frozen candidate rationale: Mentioned in HIR overview; no independently scoped identity candidate frozen; no resurrection of previously deferred CPO/laser edge.
- WHY_HUMAN_REQUIRED: frozen Stage 3 mandatory review population; automated reasons: NOT_ADMITTED_IN_STAGE2.
- RISK_FLAGS: A=NOT_ADMITTED_IN_STAGE2; B=UNRESOLVED_IDENTITY, NOT_ADMITTED_IN_STAGE2.

**AI REVIEW A**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `DEFER`; target: `none`; confidence: HIGH; materiality: MEDIUM.
- reason: Co-Packaged Optics retrieves a CPO alias, but no independently scoped Stage 2 candidate was admitted and an old CPO/laser edge remains deferred.
- evidence assessment: The observation has no bound evidence excerpt; exact alias retrieval is not source authorization or a relation decision.
- temporal scope assessed: {'source_as_of': [], 'publication_date': [], 'identity_claim': 'candidate_only'}
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'ambiguous', 'object_type': 'unknown', 'scope': 'unknown', 'granularity': 'unknown', 'quarantine': 'clear', 'ontology': 'compatible', 'evidence_sufficiency': 'insufficient', 'temporal': 'unresolved'}

**AI REVIEW B**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `DEFER`; target: `none`; confidence: LOW; materiality: MEDIUM.
- reason: Co-Packaged Optics retrieves a CPO alias, but this observation has no admitted candidate or evidence and cannot reopen a deferred CPO/laser edge.
- evidence assessment: No admitted candidate, source ID, or evidence excerpt for OBS_B13CBB8C551799BB; comparison wording alone cannot establish identity.
- temporal scope assessed: not_established
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'ambiguous', 'object_type': 'unknown', 'scope': 'unknown', 'granularity': 'unknown', 'quarantine': 'clear', 'ontology': 'unresolved', 'evidence_sufficiency': 'insufficient', 'temporal': 'compatible'}

**A/B RECONCILIATION**

- A_B_SUBSTANTIVE_AGREEMENT; disagreement type: none; native-operation conflict: false; target conflict: false.
- Interpretation differences: none.
- Reconciliation assessment: Both reviewers defer an observation with no admitted candidate or evidence. Ontology and temporal labels are not actionable without admission.
- Non-material rubric-label differences retained for audit: ontology, temporal.

**EVIDENCE SUMMARY**

- No admitted source excerpt is bound to this observation.
- Temporal scope: source as-of dates above; no relation temporal claim.

- SYSTEM_RECOMMENDED_DECISION: `DEFER`.
- SYSTEM_RECOMMENDATION_REASON: Frozen structural, Stage 2 decision, evidence, or temporal exception remains unresolved.
- HUMAN_USER_DECISION = PENDING
- VALID NATIVE OPTIONS: DEFER, REJECT for this unadmitted observation; CREATE/REUSE requires a separately admitted candidate.

### Item 046 — OBS_BEEF46D038465707 — Through-Glass Via

- ITEM_NUMBER: 46; ITEM_ID: `OBS_BEEF46D038465707`; OBJECT_TYPE: identity.
- DOMAIN / context: `semiconductor` Semiconductor structured Foundation candidate against shared AI Hardware canonical catalog; cross-domain status: `NO_NODE_OR_EDGE_EMITTED`.
- AUTOMATED_STAGE3_OUTCOME: `DEFER`; CURRENT_CANONICAL_TARGET: `none`.
- Possible existing canonical IDs (unresolved unless explicitly reused): `none`.
- CANDIDATE_SUMMARY: Through-Glass Via; candidate type `unknown`; comparison scope `HIGH_PRIORITY_COVERAGE_CHECK_ONLY`; frozen candidate rationale: No authoritative in-scope evidence span established; keep historical quarantine and no candidate Node.
- WHY_HUMAN_REQUIRED: frozen Stage 3 mandatory review population; automated reasons: NOT_ADMITTED_IN_STAGE2.
- RISK_FLAGS: A=NOT_ADMITTED_IN_STAGE2, HISTORICAL_QUARANTINE; B=UNRESOLVED_IDENTITY, NOT_ADMITTED_IN_STAGE2, HISTORICAL_QUARANTINE.

**AI REVIEW A**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `DEFER`; target: `none`; confidence: HIGH; materiality: HIGH.
- reason: Through-Glass Via remains cross-domain quarantined and has no admitted candidate or endpoint.
- evidence assessment: No authoritative in-scope evidence span is attached to this observation; preserve quarantine.
- temporal scope assessed: {'source_as_of': [], 'publication_date': [], 'identity_claim': 'candidate_only'}
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'ambiguous', 'object_type': 'unknown', 'scope': 'unknown', 'granularity': 'unknown', 'quarantine': 'preserved', 'ontology': 'compatible', 'evidence_sufficiency': 'insufficient', 'temporal': 'unresolved'}

**AI REVIEW B**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `DEFER`; target: `none`; confidence: LOW; materiality: HIGH.
- reason: Through-Glass Via lacks an in-scope authoritative span and remains quarantined; no candidate node can be created from this observation.
- evidence assessment: No admitted candidate, source ID, or evidence excerpt for OBS_BEEF46D038465707; comparison wording alone cannot establish identity.
- temporal scope assessed: not_established
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'ambiguous', 'object_type': 'unknown', 'scope': 'unknown', 'granularity': 'unknown', 'quarantine': 'preserved', 'ontology': 'unresolved', 'evidence_sufficiency': 'insufficient', 'temporal': 'compatible'}

**A/B RECONCILIATION**

- A_B_SUBSTANTIVE_AGREEMENT; disagreement type: none; native-operation conflict: false; target conflict: false.
- Interpretation differences: none.
- Reconciliation assessment: Both reviewers defer an observation with no admitted candidate or evidence. Ontology and temporal labels are not actionable without admission.
- Non-material rubric-label differences retained for audit: ontology, temporal.

**EVIDENCE SUMMARY**

- No admitted source excerpt is bound to this observation.
- Temporal scope: source as-of dates above; no relation temporal claim.

- SYSTEM_RECOMMENDED_DECISION: `DEFER`.
- SYSTEM_RECOMMENDATION_REASON: Frozen structural, Stage 2 decision, evidence, or temporal exception remains unresolved.
- HUMAN_USER_DECISION = PENDING
- VALID NATIVE OPTIONS: DEFER, REJECT for this unadmitted observation; CREATE/REUSE requires a separately admitted candidate.

### Item 047 — SC-RL-0001 — Digital Semiconductors → Integrated Circuits

- ITEM_NUMBER: 47; ITEM_ID: `SC-RL-0001`; OBJECT_TYPE: relation.
- DOMAIN / context: `semiconductor` Semiconductor structured Foundation candidate against shared AI Hardware canonical catalog; cross-domain status: `candidate`.
- AUTOMATED_STAGE3_OUTCOME: `CREATE_RELATION`; CURRENT_CANONICAL_TARGET: `none`.
- Possible existing canonical IDs (unresolved unless explicitly reused): `none`.
- CANDIDATE_SUMMARY: Digital Semiconductors → Integrated Circuits; candidate type `part_of`; comparison scope `SIA 2019 semiconductor taxonomy`; frozen candidate rationale: Source原文直接支持有界命题；仅供local review，不表示授权。
- WHY_HUMAN_REQUIRED: frozen Stage 3 mandatory review population; automated reasons: DISTINCT_RELATION_PROPOSAL, LOW_OR_UNKNOWN_CONFIDENCE, PARENT_OR_CAUSAL_REVIEW.
- RISK_FLAGS: A=DISTINCT_RELATION_PROPOSAL, LOW_OR_UNKNOWN_CONFIDENCE, PARENT_OR_CAUSAL_REVIEW; B=none.

**AI REVIEW A**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `CREATE_RELATION`; target: `{'from_node_id': 'NODE_9D05271E8992A20F', 'to_node_id': 'NODE_1D7323F4CB07233F', 'from_ref': 'SC-CN-0006', 'to_ref': 'SC-CN-0004', 'relation_type': 'part_of', 'existing_relation_ids': []}`; confidence: MEDIUM; materiality: MEDIUM.
- reason: SIA's taxonomy places Digital Semiconductors within Integrated Circuits; retain direction and source scope.
- evidence assessment: The SIA excerpt explicitly says digital semiconductors are within ICs, although it does not assert a universal ontology.
- temporal scope assessed: {'source_scope': 'SIA 2019 semiconductor taxonomy', 'temporal_status': 'categorical_source_scoped', 'runtime_status': 'categorical', 'valid_from': '', 'valid_to': '', 'source_as_of': ['2019']}
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'same', 'object_type': 'compatible', 'scope': 'compatible', 'granularity': 'different', 'quarantine': 'clear', 'ontology': 'compatible', 'evidence_sufficiency': 'sufficient', 'temporal': 'compatible'}

**AI REVIEW B**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `CREATE_RELATION`; target: `none`; confidence: HIGH; materiality: LOW.
- reason: Digital Semiconductors → Integrated Circuits (part_of): SIA nests digital devices within ICs. Keep Digital Semiconductors as child only in its 2019 taxonomy.
- evidence assessment: SC-EV-086DB7864B530FA0 from SC-P0-001_SIA_Making_Semiconductors_2019.pdf [source SC-PHYS-04A42FFC3F71A42F; SHA 04a42ffc3f71a42fa9b996240618874bb7fff21404e93cdb1e7bf53318938c26; PDF p.1, Types of Semiconductors]: Within ICs are digital semiconductors, which process binary information used by computers, and analog semiconductors, which regulate “real world” conditions such as temperature, speed, sound, and electrical current. Within the digital category are memory products, micro-components (including microprocessors and microcontrollers) and logic products. Boundary: Digital Semiconductors → Integrated Circuits (part_of): SIA nests digital devices within ICs. Keep Digital Semiconductors as child only in its 2019 taxonomy. All source excerpts remain UNAUTHORIZED_CANDIDATE evidence.
- temporal scope assessed: categorical_source_scoped
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'same', 'object_type': 'compatible', 'scope': 'compatible', 'granularity': 'same', 'quarantine': 'clear', 'ontology': 'compatible', 'evidence_sufficiency': 'sufficient', 'temporal': 'compatible'}

**A/B RECONCILIATION**

- A_B_SUBSTANTIVE_AGREEMENT; disagreement type: none; native-operation conflict: false; target conflict: false.
- Interpretation differences: none.
- Reconciliation assessment: Both reviewers support the same frozen endpoints, relation type, source scope, and evidence. Granularity labels refer to parent-child levels versus the proposed edge; bounded evidence comments do not change the edge.
- Non-material rubric-label differences retained for audit: granularity.

**EVIDENCE SUMMARY**

- Source `SC-PHYS-04A42FFC3F71A42F` (SHA-256 `04a42ffc3f71a42fa9b996240618874bb7fff21404e93cdb1e7bf53318938c26`), file `SC-P0-001_SIA_Making_Semiconductors_2019.pdf`, p. 1, section Types of Semiconductors; evidence `SC-EV-086DB7864B530FA0`; as-of 2019; excerpt: “Within ICs are digital semiconductors, which process binary information used by computers, and analog semiconductors, which regulate “real world” conditions such as temperature, speed, sound, and electrical current. Within the digital category are memory products, micro-components (including microprocessors and microcontrollers) and logic products.”
- Temporal scope: categorical_source_scoped.

- SYSTEM_RECOMMENDED_DECISION: `CREATE_RELATION`.
- SYSTEM_RECOMMENDATION_REASON: A/B substantive consensus; frozen automated outcome: CREATE_RELATION.
- HUMAN_USER_DECISION = PENDING
- VALID NATIVE OPTIONS: REUSE_RELATION, CREATE_RELATION, KEEP_DOMAIN_SPECIFIC_RELATION, DEFER_RELATION, REJECT_RELATION; REUSE requires an explicit validated target ID and all options remain subject to frozen controls.

### Item 048 — SC-RL-0002 — Analog Semiconductors → Integrated Circuits

- ITEM_NUMBER: 48; ITEM_ID: `SC-RL-0002`; OBJECT_TYPE: relation.
- DOMAIN / context: `semiconductor` Semiconductor structured Foundation candidate against shared AI Hardware canonical catalog; cross-domain status: `candidate`.
- AUTOMATED_STAGE3_OUTCOME: `CREATE_RELATION`; CURRENT_CANONICAL_TARGET: `none`.
- Possible existing canonical IDs (unresolved unless explicitly reused): `none`.
- CANDIDATE_SUMMARY: Analog Semiconductors → Integrated Circuits; candidate type `part_of`; comparison scope `SIA 2019 semiconductor taxonomy`; frozen candidate rationale: Source原文直接支持有界命题；仅供local review，不表示授权。
- WHY_HUMAN_REQUIRED: frozen Stage 3 mandatory review population; automated reasons: DISTINCT_RELATION_PROPOSAL, LOW_OR_UNKNOWN_CONFIDENCE, PARENT_OR_CAUSAL_REVIEW.
- RISK_FLAGS: A=DISTINCT_RELATION_PROPOSAL, LOW_OR_UNKNOWN_CONFIDENCE, PARENT_OR_CAUSAL_REVIEW; B=none.

**AI REVIEW A**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `CREATE_RELATION`; target: `{'from_node_id': 'NODE_F557CCEB8BC86CEE', 'to_node_id': 'NODE_1D7323F4CB07233F', 'from_ref': 'SC-CN-0007', 'to_ref': 'SC-CN-0004', 'relation_type': 'part_of', 'existing_relation_ids': []}`; confidence: MEDIUM; materiality: MEDIUM.
- reason: Analog Semiconductors is the sibling IC category, not a child of Digital Semiconductors.
- evidence assessment: The same SIA taxonomy separately locates analog semiconductors within ICs.
- temporal scope assessed: {'source_scope': 'SIA 2019 semiconductor taxonomy', 'temporal_status': 'categorical_source_scoped', 'runtime_status': 'categorical', 'valid_from': '', 'valid_to': '', 'source_as_of': ['2019']}
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'same', 'object_type': 'compatible', 'scope': 'compatible', 'granularity': 'different', 'quarantine': 'clear', 'ontology': 'compatible', 'evidence_sufficiency': 'sufficient', 'temporal': 'compatible'}

**AI REVIEW B**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `CREATE_RELATION`; target: `none`; confidence: HIGH; materiality: LOW.
- reason: Analog Semiconductors → Integrated Circuits (part_of): SIA nests analog devices within ICs; analog is sibling to digital, not its child.
- evidence assessment: SC-EV-086DB7864B530FA0 from SC-P0-001_SIA_Making_Semiconductors_2019.pdf [source SC-PHYS-04A42FFC3F71A42F; SHA 04a42ffc3f71a42fa9b996240618874bb7fff21404e93cdb1e7bf53318938c26; PDF p.1, Types of Semiconductors]: Within ICs are digital semiconductors, which process binary information used by computers, and analog semiconductors, which regulate “real world” conditions such as temperature, speed, sound, and electrical current. Within the digital category are memory products, micro-components (including microprocessors and microcontrollers) and logic products. Boundary: Analog Semiconductors → Integrated Circuits (part_of): SIA nests analog devices within ICs; analog is sibling to digital, not its child. All source excerpts remain UNAUTHORIZED_CANDIDATE evidence.
- temporal scope assessed: categorical_source_scoped
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'same', 'object_type': 'compatible', 'scope': 'compatible', 'granularity': 'same', 'quarantine': 'clear', 'ontology': 'compatible', 'evidence_sufficiency': 'sufficient', 'temporal': 'compatible'}

**A/B RECONCILIATION**

- A_B_SUBSTANTIVE_AGREEMENT; disagreement type: none; native-operation conflict: false; target conflict: false.
- Interpretation differences: none.
- Reconciliation assessment: Both reviewers support the same frozen endpoints, relation type, source scope, and evidence. Granularity labels refer to parent-child levels versus the proposed edge; bounded evidence comments do not change the edge.
- Non-material rubric-label differences retained for audit: granularity.

**EVIDENCE SUMMARY**

- Source `SC-PHYS-04A42FFC3F71A42F` (SHA-256 `04a42ffc3f71a42fa9b996240618874bb7fff21404e93cdb1e7bf53318938c26`), file `SC-P0-001_SIA_Making_Semiconductors_2019.pdf`, p. 1, section Types of Semiconductors; evidence `SC-EV-086DB7864B530FA0`; as-of 2019; excerpt: “Within ICs are digital semiconductors, which process binary information used by computers, and analog semiconductors, which regulate “real world” conditions such as temperature, speed, sound, and electrical current. Within the digital category are memory products, micro-components (including microprocessors and microcontrollers) and logic products.”
- Temporal scope: categorical_source_scoped.

- SYSTEM_RECOMMENDED_DECISION: `CREATE_RELATION`.
- SYSTEM_RECOMMENDATION_REASON: A/B substantive consensus; frozen automated outcome: CREATE_RELATION.
- HUMAN_USER_DECISION = PENDING
- VALID NATIVE OPTIONS: REUSE_RELATION, CREATE_RELATION, KEEP_DOMAIN_SPECIFIC_RELATION, DEFER_RELATION, REJECT_RELATION; REUSE requires an explicit validated target ID and all options remain subject to frozen controls.

### Item 049 — SC-RL-0003 — Semiconductor Memory → Digital Semiconductors

- ITEM_NUMBER: 49; ITEM_ID: `SC-RL-0003`; OBJECT_TYPE: relation.
- DOMAIN / context: `semiconductor` Semiconductor structured Foundation candidate against shared AI Hardware canonical catalog; cross-domain status: `candidate`.
- AUTOMATED_STAGE3_OUTCOME: `CREATE_RELATION`; CURRENT_CANONICAL_TARGET: `none`.
- Possible existing canonical IDs (unresolved unless explicitly reused): `none`.
- CANDIDATE_SUMMARY: Semiconductor Memory → Digital Semiconductors; candidate type `part_of`; comparison scope `SIA 2019 semiconductor taxonomy`; frozen candidate rationale: Source原文直接支持有界命题；仅供local review，不表示授权。
- WHY_HUMAN_REQUIRED: frozen Stage 3 mandatory review population; automated reasons: DISTINCT_RELATION_PROPOSAL, LOW_OR_UNKNOWN_CONFIDENCE, PARENT_OR_CAUSAL_REVIEW.
- RISK_FLAGS: A=DISTINCT_RELATION_PROPOSAL, LOW_OR_UNKNOWN_CONFIDENCE, PARENT_OR_CAUSAL_REVIEW; B=none.

**AI REVIEW A**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `CREATE_RELATION`; target: `{'from_node_id': 'NODE_CD6598B7D56BCC1A', 'to_node_id': 'NODE_9D05271E8992A20F', 'from_ref': 'SC-CN-0009', 'to_ref': 'SC-CN-0006', 'relation_type': 'part_of', 'existing_relation_ids': []}`; confidence: MEDIUM; materiality: MEDIUM.
- reason: Semiconductor Memory is a digital category under SIA's product taxonomy; this is a categorical edge.
- evidence assessment: SIA names memory products within the digital category, directly supporting the child-to-parent direction.
- temporal scope assessed: {'source_scope': 'SIA 2019 semiconductor taxonomy', 'temporal_status': 'categorical_source_scoped', 'runtime_status': 'categorical', 'valid_from': '', 'valid_to': '', 'source_as_of': ['2019']}
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'same', 'object_type': 'compatible', 'scope': 'compatible', 'granularity': 'different', 'quarantine': 'clear', 'ontology': 'compatible', 'evidence_sufficiency': 'sufficient', 'temporal': 'compatible'}

**AI REVIEW B**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `CREATE_RELATION`; target: `none`; confidence: HIGH; materiality: LOW.
- reason: Semiconductor Memory → Digital Semiconductors (part_of): SIA places memory products in the digital category; classification does not assert deployment.
- evidence assessment: SC-EV-086DB7864B530FA0 from SC-P0-001_SIA_Making_Semiconductors_2019.pdf [source SC-PHYS-04A42FFC3F71A42F; SHA 04a42ffc3f71a42fa9b996240618874bb7fff21404e93cdb1e7bf53318938c26; PDF p.1, Types of Semiconductors]: Within ICs are digital semiconductors, which process binary information used by computers, and analog semiconductors, which regulate “real world” conditions such as temperature, speed, sound, and electrical current. Within the digital category are memory products, micro-components (including microprocessors and microcontrollers) and logic products. Boundary: Semiconductor Memory → Digital Semiconductors (part_of): SIA places memory products in the digital category; classification does not assert deployment. All source excerpts remain UNAUTHORIZED_CANDIDATE evidence.
- temporal scope assessed: categorical_source_scoped
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'same', 'object_type': 'compatible', 'scope': 'compatible', 'granularity': 'same', 'quarantine': 'clear', 'ontology': 'compatible', 'evidence_sufficiency': 'sufficient', 'temporal': 'compatible'}

**A/B RECONCILIATION**

- A_B_SUBSTANTIVE_AGREEMENT; disagreement type: none; native-operation conflict: false; target conflict: false.
- Interpretation differences: none.
- Reconciliation assessment: Both reviewers support the same frozen endpoints, relation type, source scope, and evidence. Granularity labels refer to parent-child levels versus the proposed edge; bounded evidence comments do not change the edge.
- Non-material rubric-label differences retained for audit: granularity.

**EVIDENCE SUMMARY**

- Source `SC-PHYS-04A42FFC3F71A42F` (SHA-256 `04a42ffc3f71a42fa9b996240618874bb7fff21404e93cdb1e7bf53318938c26`), file `SC-P0-001_SIA_Making_Semiconductors_2019.pdf`, p. 1, section Types of Semiconductors; evidence `SC-EV-086DB7864B530FA0`; as-of 2019; excerpt: “Within ICs are digital semiconductors, which process binary information used by computers, and analog semiconductors, which regulate “real world” conditions such as temperature, speed, sound, and electrical current. Within the digital category are memory products, micro-components (including microprocessors and microcontrollers) and logic products.”
- Temporal scope: categorical_source_scoped.

- SYSTEM_RECOMMENDED_DECISION: `CREATE_RELATION`.
- SYSTEM_RECOMMENDATION_REASON: A/B substantive consensus; frozen automated outcome: CREATE_RELATION.
- HUMAN_USER_DECISION = PENDING
- VALID NATIVE OPTIONS: REUSE_RELATION, CREATE_RELATION, KEEP_DOMAIN_SPECIFIC_RELATION, DEFER_RELATION, REJECT_RELATION; REUSE requires an explicit validated target ID and all options remain subject to frozen controls.

### Item 050 — SC-RL-0004 — Logic Semiconductors → Digital Semiconductors

- ITEM_NUMBER: 50; ITEM_ID: `SC-RL-0004`; OBJECT_TYPE: relation.
- DOMAIN / context: `semiconductor` Semiconductor structured Foundation candidate against shared AI Hardware canonical catalog; cross-domain status: `candidate`.
- AUTOMATED_STAGE3_OUTCOME: `CREATE_RELATION`; CURRENT_CANONICAL_TARGET: `none`.
- Possible existing canonical IDs (unresolved unless explicitly reused): `none`.
- CANDIDATE_SUMMARY: Logic Semiconductors → Digital Semiconductors; candidate type `part_of`; comparison scope `SIA 2019 semiconductor taxonomy`; frozen candidate rationale: Source原文直接支持有界命题；仅供local review，不表示授权。
- WHY_HUMAN_REQUIRED: frozen Stage 3 mandatory review population; automated reasons: DISTINCT_RELATION_PROPOSAL, LOW_OR_UNKNOWN_CONFIDENCE, PARENT_OR_CAUSAL_REVIEW.
- RISK_FLAGS: A=DISTINCT_RELATION_PROPOSAL, LOW_OR_UNKNOWN_CONFIDENCE, PARENT_OR_CAUSAL_REVIEW; B=FROZEN_STAGE2_DECISION.

**AI REVIEW A**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `CREATE_RELATION`; target: `{'from_node_id': 'NODE_C21D053FE4EC0E97', 'to_node_id': 'NODE_9D05271E8992A20F', 'from_ref': 'SC-CN-0008', 'to_ref': 'SC-CN-0006', 'relation_type': 'part_of', 'existing_relation_ids': []}`; confidence: MEDIUM; materiality: MEDIUM.
- reason: Logic Semiconductors belongs under Digital Semiconductors in this SIA taxonomy, consistent with the frozen Stage 2 CREATE.
- evidence assessment: The source explicitly lists logic products beside memory and micro-components under digital semiconductors.
- temporal scope assessed: {'source_scope': 'SIA 2019 semiconductor taxonomy', 'temporal_status': 'categorical_source_scoped', 'runtime_status': 'categorical', 'valid_from': '', 'valid_to': '', 'source_as_of': ['2019']}
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'same', 'object_type': 'compatible', 'scope': 'compatible', 'granularity': 'different', 'quarantine': 'clear', 'ontology': 'compatible', 'evidence_sufficiency': 'sufficient', 'temporal': 'compatible'}

**AI REVIEW B**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `CREATE_RELATION`; target: `none`; confidence: MEDIUM; materiality: LOW.
- reason: Logic Semiconductors → Digital Semiconductors (part_of): SIA places logic products in the digital category. Preserve scoped Stage 2 CREATE.
- evidence assessment: SC-EV-086DB7864B530FA0 from SC-P0-001_SIA_Making_Semiconductors_2019.pdf [source SC-PHYS-04A42FFC3F71A42F; SHA 04a42ffc3f71a42fa9b996240618874bb7fff21404e93cdb1e7bf53318938c26; PDF p.1, Types of Semiconductors]: Within ICs are digital semiconductors, which process binary information used by computers, and analog semiconductors, which regulate “real world” conditions such as temperature, speed, sound, and electrical current. Within the digital category are memory products, micro-components (including microprocessors and microcontrollers) and logic products. Boundary: Logic Semiconductors → Digital Semiconductors (part_of): SIA places logic products in the digital category. Preserve scoped Stage 2 CREATE. All source excerpts remain UNAUTHORIZED_CANDIDATE evidence.
- temporal scope assessed: categorical_source_scoped
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'same', 'object_type': 'compatible', 'scope': 'compatible', 'granularity': 'same', 'quarantine': 'clear', 'ontology': 'compatible', 'evidence_sufficiency': 'sufficient', 'temporal': 'compatible'}

**A/B RECONCILIATION**

- A_B_SUBSTANTIVE_AGREEMENT; disagreement type: none; native-operation conflict: false; target conflict: false.
- Interpretation differences: none.
- Reconciliation assessment: Both reviewers support the same frozen endpoints, relation type, source scope, and evidence. Granularity labels refer to parent-child levels versus the proposed edge; bounded evidence comments do not change the edge.
- Non-material rubric-label differences retained for audit: granularity.

**EVIDENCE SUMMARY**

- Source `SC-PHYS-04A42FFC3F71A42F` (SHA-256 `04a42ffc3f71a42fa9b996240618874bb7fff21404e93cdb1e7bf53318938c26`), file `SC-P0-001_SIA_Making_Semiconductors_2019.pdf`, p. 1, section Types of Semiconductors; evidence `SC-EV-086DB7864B530FA0`; as-of 2019; excerpt: “Within ICs are digital semiconductors, which process binary information used by computers, and analog semiconductors, which regulate “real world” conditions such as temperature, speed, sound, and electrical current. Within the digital category are memory products, micro-components (including microprocessors and microcontrollers) and logic products.”
- Temporal scope: categorical_source_scoped.

- SYSTEM_RECOMMENDED_DECISION: `CREATE_RELATION`.
- SYSTEM_RECOMMENDATION_REASON: A/B substantive consensus; frozen automated outcome: CREATE_RELATION.
- HUMAN_USER_DECISION = PENDING
- VALID NATIVE OPTIONS: REUSE_RELATION, CREATE_RELATION, KEEP_DOMAIN_SPECIFIC_RELATION, DEFER_RELATION, REJECT_RELATION; REUSE requires an explicit validated target ID and all options remain subject to frozen controls.

### Item 051 — SC-RL-0005 — Integrated Circuits → Semiconductor

- ITEM_NUMBER: 51; ITEM_ID: `SC-RL-0005`; OBJECT_TYPE: relation.
- DOMAIN / context: `semiconductor` Semiconductor structured Foundation candidate against shared AI Hardware canonical catalog; cross-domain status: `candidate`.
- AUTOMATED_STAGE3_OUTCOME: `DEFER_RELATION`; CURRENT_CANONICAL_TARGET: `none`.
- Possible existing canonical IDs (unresolved unless explicitly reused): `none`.
- CANDIDATE_SUMMARY: Integrated Circuits → Semiconductor; candidate type `part_of`; comparison scope `SIA 2019 taxonomy; root English identity held`; frozen candidate rationale: 一个或两个端点尚未通过身份候选准入；证据保留，不提前授权端点。
- WHY_HUMAN_REQUIRED: frozen Stage 3 mandatory review population; automated reasons: ENDPOINT_AMBIGUITY, EVIDENCE_WARNING, LOW_OR_UNKNOWN_CONFIDENCE, PARENT_OR_CAUSAL_REVIEW, RELATION_AMBIGUITY.
- RISK_FLAGS: A=ENDPOINT_AMBIGUITY, EVIDENCE_WARNING, LOW_OR_UNKNOWN_CONFIDENCE, PARENT_OR_CAUSAL_REVIEW, RELATION_AMBIGUITY; B=UNRESOLVED_RELATION, ENDPOINT_OR_RECONCILIATION.

**AI REVIEW A**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `DEFER_RELATION`; target: `{'from_node_id': 'NODE_1D7323F4CB07233F', 'to_node_id': None, 'from_ref': 'SC-CN-0004', 'to_ref': 'SC-CN-0001', 'relation_type': 'part_of', 'existing_relation_ids': []}`; confidence: HIGH; materiality: HIGH.
- reason: Integrated Circuits to Semiconductor is a plausible taxonomy edge, but the English root identity is held and the target node is unresolved.
- evidence assessment: SIA calls ICs sophisticated semiconductors; this supports a category statement but cannot settle the bilingual root endpoint.
- temporal scope assessed: {'source_scope': 'SIA 2019 taxonomy; root English identity held', 'temporal_status': 'categorical_source_scoped', 'runtime_status': 'categorical', 'valid_from': '', 'valid_to': '', 'source_as_of': ['2019']}
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'ambiguous', 'object_type': 'unknown', 'scope': 'unknown', 'granularity': 'different', 'quarantine': 'clear', 'ontology': 'compatible', 'evidence_sufficiency': 'sufficient', 'temporal': 'compatible'}

**AI REVIEW B**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `DEFER_RELATION`; target: `none`; confidence: MEDIUM; materiality: HIGH.
- reason: Integrated Circuits → Semiconductor (part_of): ICs are semiconductors, but English Semiconductor may duplicate an unregistered Chinese Industry root; settle that endpoint.
- evidence assessment: SC-EV-AC855AD6CD7AF8B7 from SC-P0-001_SIA_Making_Semiconductors_2019.pdf [source SC-PHYS-04A42FFC3F71A42F; SHA 04a42ffc3f71a42fa9b996240618874bb7fff21404e93cdb1e7bf53318938c26; PDF p.1, Types of Semiconductors]: Integrated circuits (ICs) are sophisticated semiconductors that often contain billions of transistors and perform high-level functions, while discretes often contain fewer transistors and perform simpler functions. Boundary: Integrated Circuits → Semiconductor (part_of): ICs are semiconductors, but English Semiconductor may duplicate an unregistered Chinese Industry root; settle that endpoint. All source excerpts remain UNAUTHORIZED_CANDIDATE evidence.
- temporal scope assessed: categorical_source_scoped
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'ambiguous', 'object_type': 'unknown', 'scope': 'unknown', 'granularity': 'unknown', 'quarantine': 'clear', 'ontology': 'unresolved', 'evidence_sufficiency': 'limited', 'temporal': 'compatible'}

**A/B RECONCILIATION**

- A_B_SUBSTANTIVE_AGREEMENT; disagreement type: none; native-operation conflict: false; target conflict: false.
- Interpretation differences: none.
- Reconciliation assessment: Both reviewers hold the same endpoint, temporal, or ontology exception. Rubric labels compare concept support with authority for the relation.
- Non-material rubric-label differences retained for audit: evidence_sufficiency, granularity, ontology.

**EVIDENCE SUMMARY**

- Source `SC-PHYS-04A42FFC3F71A42F` (SHA-256 `04a42ffc3f71a42fa9b996240618874bb7fff21404e93cdb1e7bf53318938c26`), file `SC-P0-001_SIA_Making_Semiconductors_2019.pdf`, p. 1, section Types of Semiconductors; evidence `SC-EV-AC855AD6CD7AF8B7`; as-of 2019; excerpt: “Integrated circuits (ICs) are sophisticated semiconductors that often contain billions of transistors and perform high-level functions, while discretes often contain fewer transistors and perform simpler functions.”
- Temporal scope: categorical_source_scoped.

- SYSTEM_RECOMMENDED_DECISION: `DEFER_RELATION`.
- SYSTEM_RECOMMENDATION_REASON: Frozen structural, Stage 2 decision, evidence, or temporal exception remains unresolved.
- HUMAN_USER_DECISION = PENDING
- VALID NATIVE OPTIONS: REUSE_RELATION, CREATE_RELATION, KEEP_DOMAIN_SPECIFIC_RELATION, DEFER_RELATION, REJECT_RELATION; REUSE requires an explicit validated target ID and all options remain subject to frozen controls.

### Item 052 — SC-RL-0006 — Flash Memory → Nonvolatile Memory

- ITEM_NUMBER: 52; ITEM_ID: `SC-RL-0006`; OBJECT_TYPE: relation.
- DOMAIN / context: `semiconductor` Semiconductor structured Foundation candidate against shared AI Hardware canonical catalog; cross-domain status: `candidate`.
- AUTOMATED_STAGE3_OUTCOME: `CREATE_RELATION`; CURRENT_CANONICAL_TARGET: `none`.
- Possible existing canonical IDs (unresolved unless explicitly reused): `none`.
- CANDIDATE_SUMMARY: Flash Memory → Nonvolatile Memory; candidate type `part_of`; comparison scope `IRDS More Moore 2024 / nonvolatile-memory taxonomy`; frozen candidate rationale: Source原文直接支持有界命题；仅供local review，不表示授权。
- WHY_HUMAN_REQUIRED: frozen Stage 3 mandatory review population; automated reasons: DISTINCT_RELATION_PROPOSAL, LOW_OR_UNKNOWN_CONFIDENCE, PARENT_OR_CAUSAL_REVIEW.
- RISK_FLAGS: A=DISTINCT_RELATION_PROPOSAL, LOW_OR_UNKNOWN_CONFIDENCE, PARENT_OR_CAUSAL_REVIEW; B=none.

**AI REVIEW A**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `CREATE_RELATION`; target: `{'from_node_id': 'NODE_72FEF7A4F79F7EE7', 'to_node_id': 'NODE_00C120377853665C', 'from_ref': 'SC-CN-0101', 'to_ref': 'SC-CN-0100', 'relation_type': 'part_of', 'existing_relation_ids': []}`; confidence: HIGH; materiality: MEDIUM.
- reason: Flash Memory is nested under Nonvolatile Memory in the cited IRDS taxonomy.
- evidence assessment: IRDS states flash is one of the two large nonvolatile-memory categories.
- temporal scope assessed: {'source_scope': 'IRDS More Moore 2024 / nonvolatile-memory taxonomy', 'temporal_status': 'categorical_source_scoped', 'runtime_status': 'categorical', 'valid_from': '', 'valid_to': '', 'source_as_of': ['2024']}
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'same', 'object_type': 'compatible', 'scope': 'compatible', 'granularity': 'different', 'quarantine': 'clear', 'ontology': 'compatible', 'evidence_sufficiency': 'sufficient', 'temporal': 'compatible'}

**AI REVIEW B**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `CREATE_RELATION`; target: `none`; confidence: HIGH; materiality: LOW.
- reason: Flash Memory → Nonvolatile Memory (part_of): IRDS divides nonvolatile memory into Flash and other classes; Flash is a categorical child.
- evidence assessment: SC-EV-288A875770100378 from SC-P0-009_2024_IRDS_More_Moore.pdf [source SC-PHYS-49A1D3B42E458985; SHA 49a1d3b42e45898555490e602170876e22d1ccf8d7c17711e436d8db36322fa6; PDF p.27, 5 Nonvolatile Memory]: Nonvolatile memory may be divided into two large categories—Flash memories (NAND Flash and NOR Flash), and non-charge-based-storage memories. Boundary: Flash Memory → Nonvolatile Memory (part_of): IRDS divides nonvolatile memory into Flash and other classes; Flash is a categorical child. All source excerpts remain UNAUTHORIZED_CANDIDATE evidence.
- temporal scope assessed: categorical_source_scoped
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'same', 'object_type': 'compatible', 'scope': 'compatible', 'granularity': 'same', 'quarantine': 'clear', 'ontology': 'compatible', 'evidence_sufficiency': 'sufficient', 'temporal': 'compatible'}

**A/B RECONCILIATION**

- A_B_SUBSTANTIVE_AGREEMENT; disagreement type: none; native-operation conflict: false; target conflict: false.
- Interpretation differences: none.
- Reconciliation assessment: Both reviewers support the same frozen endpoints, relation type, source scope, and evidence. Granularity labels refer to parent-child levels versus the proposed edge; bounded evidence comments do not change the edge.
- Non-material rubric-label differences retained for audit: granularity.

**EVIDENCE SUMMARY**

- Source `SC-PHYS-49A1D3B42E458985` (SHA-256 `49a1d3b42e45898555490e602170876e22d1ccf8d7c17711e436d8db36322fa6`), file `SC-P0-009_2024_IRDS_More_Moore.pdf`, p. 27, section 5 Nonvolatile Memory; evidence `SC-EV-288A875770100378`; as-of 2024; excerpt: “Nonvolatile memory may be divided into two large categories—Flash memories (NAND Flash and NOR Flash), and non-charge-based-storage memories.”
- Temporal scope: categorical_source_scoped.

- SYSTEM_RECOMMENDED_DECISION: `CREATE_RELATION`.
- SYSTEM_RECOMMENDATION_REASON: A/B substantive consensus; frozen automated outcome: CREATE_RELATION.
- HUMAN_USER_DECISION = PENDING
- VALID NATIVE OPTIONS: REUSE_RELATION, CREATE_RELATION, KEEP_DOMAIN_SPECIFIC_RELATION, DEFER_RELATION, REJECT_RELATION; REUSE requires an explicit validated target ID and all options remain subject to frozen controls.

### Item 053 — SC-RL-0007 — NOR Flash → Flash Memory

- ITEM_NUMBER: 53; ITEM_ID: `SC-RL-0007`; OBJECT_TYPE: relation.
- DOMAIN / context: `semiconductor` Semiconductor structured Foundation candidate against shared AI Hardware canonical catalog; cross-domain status: `candidate`.
- AUTOMATED_STAGE3_OUTCOME: `CREATE_RELATION`; CURRENT_CANONICAL_TARGET: `none`.
- Possible existing canonical IDs (unresolved unless explicitly reused): `none`.
- CANDIDATE_SUMMARY: NOR Flash → Flash Memory; candidate type `part_of`; comparison scope `IRDS More Moore 2024 / nonvolatile-memory taxonomy`; frozen candidate rationale: Source原文直接支持有界命题；仅供local review，不表示授权。
- WHY_HUMAN_REQUIRED: frozen Stage 3 mandatory review population; automated reasons: DISTINCT_RELATION_PROPOSAL, LOW_OR_UNKNOWN_CONFIDENCE, PARENT_OR_CAUSAL_REVIEW.
- RISK_FLAGS: A=DISTINCT_RELATION_PROPOSAL, LOW_OR_UNKNOWN_CONFIDENCE, PARENT_OR_CAUSAL_REVIEW; B=none.

**AI REVIEW A**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `CREATE_RELATION`; target: `{'from_node_id': 'NODE_15BC05D614287450', 'to_node_id': 'NODE_72FEF7A4F79F7EE7', 'from_ref': 'NODE_15BC05D614287450', 'to_ref': 'SC-CN-0101', 'relation_type': 'part_of', 'existing_relation_ids': []}`; confidence: HIGH; materiality: MEDIUM.
- reason: NOR Flash is a named Flash Memory subtype; it is not interchangeable with NAND.
- evidence assessment: The IRDS excerpt explicitly puts NOR Flash inside its flash-memory parenthesis.
- temporal scope assessed: {'source_scope': 'IRDS More Moore 2024 / nonvolatile-memory taxonomy', 'temporal_status': 'categorical_source_scoped', 'runtime_status': 'categorical', 'valid_from': '', 'valid_to': '', 'source_as_of': ['2024']}
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'same', 'object_type': 'compatible', 'scope': 'compatible', 'granularity': 'different', 'quarantine': 'clear', 'ontology': 'compatible', 'evidence_sufficiency': 'sufficient', 'temporal': 'compatible'}

**AI REVIEW B**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `CREATE_RELATION`; target: `none`; confidence: HIGH; materiality: LOW.
- reason: NOR Flash → Flash Memory (part_of): IRDS lists NOR Flash within Flash memories; do not conflate active NOR with NAND.
- evidence assessment: SC-EV-288A875770100378 from SC-P0-009_2024_IRDS_More_Moore.pdf [source SC-PHYS-49A1D3B42E458985; SHA 49a1d3b42e45898555490e602170876e22d1ccf8d7c17711e436d8db36322fa6; PDF p.27, 5 Nonvolatile Memory]: Nonvolatile memory may be divided into two large categories—Flash memories (NAND Flash and NOR Flash), and non-charge-based-storage memories. Boundary: NOR Flash → Flash Memory (part_of): IRDS lists NOR Flash within Flash memories; do not conflate active NOR with NAND. All source excerpts remain UNAUTHORIZED_CANDIDATE evidence.
- temporal scope assessed: categorical_source_scoped
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'same', 'object_type': 'compatible', 'scope': 'compatible', 'granularity': 'same', 'quarantine': 'clear', 'ontology': 'compatible', 'evidence_sufficiency': 'sufficient', 'temporal': 'compatible'}

**A/B RECONCILIATION**

- A_B_SUBSTANTIVE_AGREEMENT; disagreement type: none; native-operation conflict: false; target conflict: false.
- Interpretation differences: none.
- Reconciliation assessment: Both reviewers support the same frozen endpoints, relation type, source scope, and evidence. Granularity labels refer to parent-child levels versus the proposed edge; bounded evidence comments do not change the edge.
- Non-material rubric-label differences retained for audit: granularity.

**EVIDENCE SUMMARY**

- Source `SC-PHYS-49A1D3B42E458985` (SHA-256 `49a1d3b42e45898555490e602170876e22d1ccf8d7c17711e436d8db36322fa6`), file `SC-P0-009_2024_IRDS_More_Moore.pdf`, p. 27, section 5 Nonvolatile Memory; evidence `SC-EV-288A875770100378`; as-of 2024; excerpt: “Nonvolatile memory may be divided into two large categories—Flash memories (NAND Flash and NOR Flash), and non-charge-based-storage memories.”
- Temporal scope: categorical_source_scoped.

- SYSTEM_RECOMMENDED_DECISION: `CREATE_RELATION`.
- SYSTEM_RECOMMENDATION_REASON: A/B substantive consensus; frozen automated outcome: CREATE_RELATION.
- HUMAN_USER_DECISION = PENDING
- VALID NATIVE OPTIONS: REUSE_RELATION, CREATE_RELATION, KEEP_DOMAIN_SPECIFIC_RELATION, DEFER_RELATION, REJECT_RELATION; REUSE requires an explicit validated target ID and all options remain subject to frozen controls.

### Item 054 — SC-RL-0008 — NAND Flash → Flash Memory

- ITEM_NUMBER: 54; ITEM_ID: `SC-RL-0008`; OBJECT_TYPE: relation.
- DOMAIN / context: `semiconductor` Semiconductor structured Foundation candidate against shared AI Hardware canonical catalog; cross-domain status: `candidate`.
- AUTOMATED_STAGE3_OUTCOME: `DEFER_RELATION`; CURRENT_CANONICAL_TARGET: `none`.
- Possible existing canonical IDs (unresolved unless explicitly reused): `none`.
- CANDIDATE_SUMMARY: NAND Flash → Flash Memory; candidate type `part_of`; comparison scope `IRDS More Moore 2024 / nonvolatile-memory taxonomy`; frozen candidate rationale: 一个或两个端点尚未通过身份候选准入；证据保留，不提前授权端点。
- WHY_HUMAN_REQUIRED: frozen Stage 3 mandatory review population; automated reasons: EVIDENCE_WARNING, FROZEN_STAGE2_HUMAN_DECISION, LOW_OR_UNKNOWN_CONFIDENCE, PARENT_OR_CAUSAL_REVIEW, RELATION_AMBIGUITY.
- RISK_FLAGS: A=EVIDENCE_WARNING, FROZEN_STAGE2_HUMAN_DECISION, LOW_OR_UNKNOWN_CONFIDENCE, PARENT_OR_CAUSAL_REVIEW, RELATION_AMBIGUITY, HISTORICAL_QUARANTINE; B=FROZEN_STAGE2_DECISION, UNRESOLVED_RELATION, ENDPOINT_OR_RECONCILIATION, HISTORICAL_QUARANTINE.

**AI REVIEW A**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `DEFER_RELATION`; target: `{'from_node_id': None, 'to_node_id': 'NODE_72FEF7A4F79F7EE7', 'from_ref': 'SC-CN-0011', 'to_ref': 'SC-CN-0101', 'relation_type': 'part_of', 'existing_relation_ids': []}`; confidence: HIGH; materiality: HIGH.
- reason: NAND-to-Flash taxonomy evidence is direct, but the NAND endpoint is quarantined and Stage 2 deferred.
- evidence assessment: IRDS names NAND as flash memory; the excerpt does not release its historical identity quarantine.
- temporal scope assessed: {'source_scope': 'IRDS More Moore 2024 / nonvolatile-memory taxonomy', 'temporal_status': 'categorical_source_scoped', 'runtime_status': 'categorical', 'valid_from': '', 'valid_to': '', 'source_as_of': ['2024']}
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'ambiguous', 'object_type': 'unknown', 'scope': 'unknown', 'granularity': 'different', 'quarantine': 'preserved', 'ontology': 'compatible', 'evidence_sufficiency': 'sufficient', 'temporal': 'compatible'}

**AI REVIEW B**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `DEFER_RELATION`; target: `none`; confidence: MEDIUM; materiality: HIGH.
- reason: NAND Flash → Flash Memory (part_of): IRDS lists NAND, but the NAND endpoint carries historical quarantine. Preserve Stage 2 DEFER.
- evidence assessment: SC-EV-288A875770100378 from SC-P0-009_2024_IRDS_More_Moore.pdf [source SC-PHYS-49A1D3B42E458985; SHA 49a1d3b42e45898555490e602170876e22d1ccf8d7c17711e436d8db36322fa6; PDF p.27, 5 Nonvolatile Memory]: Nonvolatile memory may be divided into two large categories—Flash memories (NAND Flash and NOR Flash), and non-charge-based-storage memories. Boundary: NAND Flash → Flash Memory (part_of): IRDS lists NAND, but the NAND endpoint carries historical quarantine. Preserve Stage 2 DEFER. All source excerpts remain UNAUTHORIZED_CANDIDATE evidence.
- temporal scope assessed: categorical_source_scoped
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'ambiguous', 'object_type': 'unknown', 'scope': 'unknown', 'granularity': 'unknown', 'quarantine': 'preserved', 'ontology': 'unresolved', 'evidence_sufficiency': 'limited', 'temporal': 'compatible'}

**A/B RECONCILIATION**

- A_B_SUBSTANTIVE_AGREEMENT; disagreement type: none; native-operation conflict: false; target conflict: false.
- Interpretation differences: none.
- Reconciliation assessment: Both reviewers hold the same endpoint, temporal, or ontology exception. Rubric labels compare concept support with authority for the relation.
- Non-material rubric-label differences retained for audit: evidence_sufficiency, granularity, ontology.

**EVIDENCE SUMMARY**

- Source `SC-PHYS-49A1D3B42E458985` (SHA-256 `49a1d3b42e45898555490e602170876e22d1ccf8d7c17711e436d8db36322fa6`), file `SC-P0-009_2024_IRDS_More_Moore.pdf`, p. 27, section 5 Nonvolatile Memory; evidence `SC-EV-288A875770100378`; as-of 2024; excerpt: “Nonvolatile memory may be divided into two large categories—Flash memories (NAND Flash and NOR Flash), and non-charge-based-storage memories.”
- Temporal scope: categorical_source_scoped.

- SYSTEM_RECOMMENDED_DECISION: `DEFER_RELATION`.
- SYSTEM_RECOMMENDATION_REASON: Frozen structural, Stage 2 decision, evidence, or temporal exception remains unresolved.
- HUMAN_USER_DECISION = PENDING
- VALID NATIVE OPTIONS: REUSE_RELATION, CREATE_RELATION, KEEP_DOMAIN_SPECIFIC_RELATION, DEFER_RELATION, REJECT_RELATION; REUSE requires an explicit validated target ID and all options remain subject to frozen controls.

### Item 055 — SC-RL-0009 — Ferroelectric Memory → Nonvolatile Memory

- ITEM_NUMBER: 55; ITEM_ID: `SC-RL-0009`; OBJECT_TYPE: relation.
- DOMAIN / context: `semiconductor` Semiconductor structured Foundation candidate against shared AI Hardware canonical catalog; cross-domain status: `candidate`.
- AUTOMATED_STAGE3_OUTCOME: `CREATE_RELATION`; CURRENT_CANONICAL_TARGET: `none`.
- Possible existing canonical IDs (unresolved unless explicitly reused): `none`.
- CANDIDATE_SUMMARY: Ferroelectric Memory → Nonvolatile Memory; candidate type `part_of`; comparison scope `IRDS More Moore 2024 / taxonomy only; development not deployment`; frozen candidate rationale: Source原文直接支持有界命题；仅供local review，不表示授权。
- WHY_HUMAN_REQUIRED: frozen Stage 3 mandatory review population; automated reasons: DISTINCT_RELATION_PROPOSAL, LOW_OR_UNKNOWN_CONFIDENCE, PARENT_OR_CAUSAL_REVIEW.
- RISK_FLAGS: A=DISTINCT_RELATION_PROPOSAL, LOW_OR_UNKNOWN_CONFIDENCE, PARENT_OR_CAUSAL_REVIEW; B=FROZEN_STAGE2_DECISION, SCOPE_LIMIT.

**AI REVIEW A**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `CREATE_RELATION`; target: `{'from_node_id': 'NODE_B1CAA8EE5AD4C87E', 'to_node_id': 'NODE_00C120377853665C', 'from_ref': 'SC-CN-0103', 'to_ref': 'SC-CN-0100', 'relation_type': 'part_of', 'existing_relation_ids': []}`; confidence: MEDIUM; materiality: MEDIUM.
- reason: Ferroelectric Memory is an IRDS nonvolatile category, with development status kept separate from deployment.
- evidence assessment: The source lists FeRAM among non-charge-storage nonvolatile memories being developed.
- temporal scope assessed: {'source_scope': 'IRDS More Moore 2024 / taxonomy only; development not deployment', 'temporal_status': 'categorical_source_scoped', 'runtime_status': 'categorical', 'valid_from': '', 'valid_to': '', 'source_as_of': ['2024']}
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'same', 'object_type': 'compatible', 'scope': 'compatible', 'granularity': 'different', 'quarantine': 'clear', 'ontology': 'compatible', 'evidence_sufficiency': 'sufficient', 'temporal': 'compatible'}

**AI REVIEW B**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `CREATE_RELATION`; target: `none`; confidence: MEDIUM; materiality: LOW.
- reason: Ferroelectric Memory → Nonvolatile Memory (part_of): IRDS lists FeRAM among emerging non-charge NVMs; being developed does not imply deployment.
- evidence assessment: SC-EV-02E262518094E12D from SC-P0-009_2024_IRDS_More_Moore.pdf [source SC-PHYS-49A1D3B42E458985; SHA 49a1d3b42e45898555490e602170876e22d1ccf8d7c17711e436d8db36322fa6; PDF p.29, 5.3 Emerging Memories]: several non-conventional non-volatile memories that are not based on charge storage, so-called resistive or capacitive memories (ferroelectric or FeRAM, magnetic or MRAM, phase-change or PCRAM, and resistive or ReRAM), are being developed and form the category often called “emerging” memories. Boundary: Ferroelectric Memory → Nonvolatile Memory (part_of): IRDS lists FeRAM among emerging non-charge NVMs; being developed does not imply deployment. All source excerpts remain UNAUTHORIZED_CANDIDATE evidence.
- temporal scope assessed: categorical_source_scoped
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'same', 'object_type': 'compatible', 'scope': 'compatible', 'granularity': 'same', 'quarantine': 'clear', 'ontology': 'compatible', 'evidence_sufficiency': 'sufficient', 'temporal': 'compatible'}

**A/B RECONCILIATION**

- A_B_SUBSTANTIVE_AGREEMENT; disagreement type: none; native-operation conflict: false; target conflict: false.
- Interpretation differences: none.
- Reconciliation assessment: Both reviewers support the same frozen endpoints, relation type, source scope, and evidence. Granularity labels refer to parent-child levels versus the proposed edge; bounded evidence comments do not change the edge.
- Non-material rubric-label differences retained for audit: granularity.

**EVIDENCE SUMMARY**

- Source `SC-PHYS-49A1D3B42E458985` (SHA-256 `49a1d3b42e45898555490e602170876e22d1ccf8d7c17711e436d8db36322fa6`), file `SC-P0-009_2024_IRDS_More_Moore.pdf`, p. 29, section 5.3 Emerging Memories; evidence `SC-EV-02E262518094E12D`; as-of 2024; excerpt: “several non-conventional non-volatile memories that are not based on charge storage, so-called resistive or capacitive memories (ferroelectric or FeRAM, magnetic or MRAM, phase-change or PCRAM, and resistive or ReRAM), are being developed and form the category often called “emerging” memories.”
- Temporal scope: categorical_source_scoped.

- SYSTEM_RECOMMENDED_DECISION: `CREATE_RELATION`.
- SYSTEM_RECOMMENDATION_REASON: A/B substantive consensus; frozen automated outcome: CREATE_RELATION.
- HUMAN_USER_DECISION = PENDING
- VALID NATIVE OPTIONS: REUSE_RELATION, CREATE_RELATION, KEEP_DOMAIN_SPECIFIC_RELATION, DEFER_RELATION, REJECT_RELATION; REUSE requires an explicit validated target ID and all options remain subject to frozen controls.

### Item 056 — SC-RL-0010 — Magnetic Memory → Nonvolatile Memory

- ITEM_NUMBER: 56; ITEM_ID: `SC-RL-0010`; OBJECT_TYPE: relation.
- DOMAIN / context: `semiconductor` Semiconductor structured Foundation candidate against shared AI Hardware canonical catalog; cross-domain status: `candidate`.
- AUTOMATED_STAGE3_OUTCOME: `CREATE_RELATION`; CURRENT_CANONICAL_TARGET: `none`.
- Possible existing canonical IDs (unresolved unless explicitly reused): `none`.
- CANDIDATE_SUMMARY: Magnetic Memory → Nonvolatile Memory; candidate type `part_of`; comparison scope `IRDS More Moore 2024 / taxonomy only; development not deployment`; frozen candidate rationale: Source原文直接支持有界命题；仅供local review，不表示授权。
- WHY_HUMAN_REQUIRED: frozen Stage 3 mandatory review population; automated reasons: DISTINCT_RELATION_PROPOSAL, LOW_OR_UNKNOWN_CONFIDENCE, PARENT_OR_CAUSAL_REVIEW.
- RISK_FLAGS: A=DISTINCT_RELATION_PROPOSAL, LOW_OR_UNKNOWN_CONFIDENCE, PARENT_OR_CAUSAL_REVIEW; B=SCOPE_LIMIT.

**AI REVIEW A**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `CREATE_RELATION`; target: `{'from_node_id': 'NODE_5D3279045196FA32', 'to_node_id': 'NODE_00C120377853665C', 'from_ref': 'SC-CN-0104', 'to_ref': 'SC-CN-0100', 'relation_type': 'part_of', 'existing_relation_ids': []}`; confidence: MEDIUM; materiality: MEDIUM.
- reason: Magnetic Memory is a nonvolatile-memory subtype in this roadmap, without a commercial-use assertion.
- evidence assessment: IRDS lists MRAM as a magnetic non-charge-storage memory under development.
- temporal scope assessed: {'source_scope': 'IRDS More Moore 2024 / taxonomy only; development not deployment', 'temporal_status': 'categorical_source_scoped', 'runtime_status': 'categorical', 'valid_from': '', 'valid_to': '', 'source_as_of': ['2024']}
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'same', 'object_type': 'compatible', 'scope': 'compatible', 'granularity': 'different', 'quarantine': 'clear', 'ontology': 'compatible', 'evidence_sufficiency': 'sufficient', 'temporal': 'compatible'}

**AI REVIEW B**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `CREATE_RELATION`; target: `none`; confidence: MEDIUM; materiality: LOW.
- reason: Magnetic Memory → Nonvolatile Memory (part_of): IRDS lists MRAM among emerging non-charge NVMs; classification does not imply commercial use.
- evidence assessment: SC-EV-02E262518094E12D from SC-P0-009_2024_IRDS_More_Moore.pdf [source SC-PHYS-49A1D3B42E458985; SHA 49a1d3b42e45898555490e602170876e22d1ccf8d7c17711e436d8db36322fa6; PDF p.29, 5.3 Emerging Memories]: several non-conventional non-volatile memories that are not based on charge storage, so-called resistive or capacitive memories (ferroelectric or FeRAM, magnetic or MRAM, phase-change or PCRAM, and resistive or ReRAM), are being developed and form the category often called “emerging” memories. Boundary: Magnetic Memory → Nonvolatile Memory (part_of): IRDS lists MRAM among emerging non-charge NVMs; classification does not imply commercial use. All source excerpts remain UNAUTHORIZED_CANDIDATE evidence.
- temporal scope assessed: categorical_source_scoped
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'same', 'object_type': 'compatible', 'scope': 'compatible', 'granularity': 'same', 'quarantine': 'clear', 'ontology': 'compatible', 'evidence_sufficiency': 'sufficient', 'temporal': 'compatible'}

**A/B RECONCILIATION**

- A_B_SUBSTANTIVE_AGREEMENT; disagreement type: none; native-operation conflict: false; target conflict: false.
- Interpretation differences: none.
- Reconciliation assessment: Both reviewers support the same frozen endpoints, relation type, source scope, and evidence. Granularity labels refer to parent-child levels versus the proposed edge; bounded evidence comments do not change the edge.
- Non-material rubric-label differences retained for audit: granularity.

**EVIDENCE SUMMARY**

- Source `SC-PHYS-49A1D3B42E458985` (SHA-256 `49a1d3b42e45898555490e602170876e22d1ccf8d7c17711e436d8db36322fa6`), file `SC-P0-009_2024_IRDS_More_Moore.pdf`, p. 29, section 5.3 Emerging Memories; evidence `SC-EV-02E262518094E12D`; as-of 2024; excerpt: “several non-conventional non-volatile memories that are not based on charge storage, so-called resistive or capacitive memories (ferroelectric or FeRAM, magnetic or MRAM, phase-change or PCRAM, and resistive or ReRAM), are being developed and form the category often called “emerging” memories.”
- Temporal scope: categorical_source_scoped.

- SYSTEM_RECOMMENDED_DECISION: `CREATE_RELATION`.
- SYSTEM_RECOMMENDATION_REASON: A/B substantive consensus; frozen automated outcome: CREATE_RELATION.
- HUMAN_USER_DECISION = PENDING
- VALID NATIVE OPTIONS: REUSE_RELATION, CREATE_RELATION, KEEP_DOMAIN_SPECIFIC_RELATION, DEFER_RELATION, REJECT_RELATION; REUSE requires an explicit validated target ID and all options remain subject to frozen controls.

### Item 057 — SC-RL-0011 — Phase-Change Memory → Nonvolatile Memory

- ITEM_NUMBER: 57; ITEM_ID: `SC-RL-0011`; OBJECT_TYPE: relation.
- DOMAIN / context: `semiconductor` Semiconductor structured Foundation candidate against shared AI Hardware canonical catalog; cross-domain status: `candidate`.
- AUTOMATED_STAGE3_OUTCOME: `CREATE_RELATION`; CURRENT_CANONICAL_TARGET: `none`.
- Possible existing canonical IDs (unresolved unless explicitly reused): `none`.
- CANDIDATE_SUMMARY: Phase-Change Memory → Nonvolatile Memory; candidate type `part_of`; comparison scope `IRDS More Moore 2024 / taxonomy only; development not deployment`; frozen candidate rationale: Source原文直接支持有界命题；仅供local review，不表示授权。
- WHY_HUMAN_REQUIRED: frozen Stage 3 mandatory review population; automated reasons: DISTINCT_RELATION_PROPOSAL, LOW_OR_UNKNOWN_CONFIDENCE, PARENT_OR_CAUSAL_REVIEW.
- RISK_FLAGS: A=DISTINCT_RELATION_PROPOSAL, LOW_OR_UNKNOWN_CONFIDENCE, PARENT_OR_CAUSAL_REVIEW; B=SCOPE_LIMIT.

**AI REVIEW A**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `CREATE_RELATION`; target: `{'from_node_id': 'NODE_4EB43CB194100A71', 'to_node_id': 'NODE_00C120377853665C', 'from_ref': 'SC-CN-0105', 'to_ref': 'SC-CN-0100', 'relation_type': 'part_of', 'existing_relation_ids': []}`; confidence: MEDIUM; materiality: MEDIUM.
- reason: Phase-Change Memory is a taxonomy child of Nonvolatile Memory, not evidence of production adoption.
- evidence assessment: IRDS includes PCRAM in the non-charge-storage memory list being developed.
- temporal scope assessed: {'source_scope': 'IRDS More Moore 2024 / taxonomy only; development not deployment', 'temporal_status': 'categorical_source_scoped', 'runtime_status': 'categorical', 'valid_from': '', 'valid_to': '', 'source_as_of': ['2024']}
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'same', 'object_type': 'compatible', 'scope': 'compatible', 'granularity': 'different', 'quarantine': 'clear', 'ontology': 'compatible', 'evidence_sufficiency': 'sufficient', 'temporal': 'compatible'}

**AI REVIEW B**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `CREATE_RELATION`; target: `none`; confidence: MEDIUM; materiality: LOW.
- reason: Phase-Change Memory → Nonvolatile Memory (part_of): IRDS lists PCRAM among emerging non-charge NVMs; preserve roadmap taxonomy scope.
- evidence assessment: SC-EV-02E262518094E12D from SC-P0-009_2024_IRDS_More_Moore.pdf [source SC-PHYS-49A1D3B42E458985; SHA 49a1d3b42e45898555490e602170876e22d1ccf8d7c17711e436d8db36322fa6; PDF p.29, 5.3 Emerging Memories]: several non-conventional non-volatile memories that are not based on charge storage, so-called resistive or capacitive memories (ferroelectric or FeRAM, magnetic or MRAM, phase-change or PCRAM, and resistive or ReRAM), are being developed and form the category often called “emerging” memories. Boundary: Phase-Change Memory → Nonvolatile Memory (part_of): IRDS lists PCRAM among emerging non-charge NVMs; preserve roadmap taxonomy scope. All source excerpts remain UNAUTHORIZED_CANDIDATE evidence.
- temporal scope assessed: categorical_source_scoped
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'same', 'object_type': 'compatible', 'scope': 'compatible', 'granularity': 'same', 'quarantine': 'clear', 'ontology': 'compatible', 'evidence_sufficiency': 'sufficient', 'temporal': 'compatible'}

**A/B RECONCILIATION**

- A_B_SUBSTANTIVE_AGREEMENT; disagreement type: none; native-operation conflict: false; target conflict: false.
- Interpretation differences: none.
- Reconciliation assessment: Both reviewers support the same frozen endpoints, relation type, source scope, and evidence. Granularity labels refer to parent-child levels versus the proposed edge; bounded evidence comments do not change the edge.
- Non-material rubric-label differences retained for audit: granularity.

**EVIDENCE SUMMARY**

- Source `SC-PHYS-49A1D3B42E458985` (SHA-256 `49a1d3b42e45898555490e602170876e22d1ccf8d7c17711e436d8db36322fa6`), file `SC-P0-009_2024_IRDS_More_Moore.pdf`, p. 29, section 5.3 Emerging Memories; evidence `SC-EV-02E262518094E12D`; as-of 2024; excerpt: “several non-conventional non-volatile memories that are not based on charge storage, so-called resistive or capacitive memories (ferroelectric or FeRAM, magnetic or MRAM, phase-change or PCRAM, and resistive or ReRAM), are being developed and form the category often called “emerging” memories.”
- Temporal scope: categorical_source_scoped.

- SYSTEM_RECOMMENDED_DECISION: `CREATE_RELATION`.
- SYSTEM_RECOMMENDATION_REASON: A/B substantive consensus; frozen automated outcome: CREATE_RELATION.
- HUMAN_USER_DECISION = PENDING
- VALID NATIVE OPTIONS: REUSE_RELATION, CREATE_RELATION, KEEP_DOMAIN_SPECIFIC_RELATION, DEFER_RELATION, REJECT_RELATION; REUSE requires an explicit validated target ID and all options remain subject to frozen controls.

### Item 058 — SC-RL-0012 — Resistive Memory → Nonvolatile Memory

- ITEM_NUMBER: 58; ITEM_ID: `SC-RL-0012`; OBJECT_TYPE: relation.
- DOMAIN / context: `semiconductor` Semiconductor structured Foundation candidate against shared AI Hardware canonical catalog; cross-domain status: `candidate`.
- AUTOMATED_STAGE3_OUTCOME: `CREATE_RELATION`; CURRENT_CANONICAL_TARGET: `none`.
- Possible existing canonical IDs (unresolved unless explicitly reused): `none`.
- CANDIDATE_SUMMARY: Resistive Memory → Nonvolatile Memory; candidate type `part_of`; comparison scope `IRDS More Moore 2024 / taxonomy only; development not deployment`; frozen candidate rationale: Source原文直接支持有界命题；仅供local review，不表示授权。
- WHY_HUMAN_REQUIRED: frozen Stage 3 mandatory review population; automated reasons: DISTINCT_RELATION_PROPOSAL, LOW_OR_UNKNOWN_CONFIDENCE, PARENT_OR_CAUSAL_REVIEW.
- RISK_FLAGS: A=DISTINCT_RELATION_PROPOSAL, LOW_OR_UNKNOWN_CONFIDENCE, PARENT_OR_CAUSAL_REVIEW; B=SCOPE_LIMIT.

**AI REVIEW A**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `CREATE_RELATION`; target: `{'from_node_id': 'NODE_A192C1E5558E8615', 'to_node_id': 'NODE_00C120377853665C', 'from_ref': 'SC-CN-0106', 'to_ref': 'SC-CN-0100', 'relation_type': 'part_of', 'existing_relation_ids': []}`; confidence: MEDIUM; materiality: MEDIUM.
- reason: Resistive Memory can be placed under the IRDS nonvolatile category with the development qualifier retained.
- evidence assessment: IRDS explicitly names ReRAM in its resistive/non-charge-storage memory list.
- temporal scope assessed: {'source_scope': 'IRDS More Moore 2024 / taxonomy only; development not deployment', 'temporal_status': 'categorical_source_scoped', 'runtime_status': 'categorical', 'valid_from': '', 'valid_to': '', 'source_as_of': ['2024']}
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'same', 'object_type': 'compatible', 'scope': 'compatible', 'granularity': 'different', 'quarantine': 'clear', 'ontology': 'compatible', 'evidence_sufficiency': 'sufficient', 'temporal': 'compatible'}

**AI REVIEW B**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `CREATE_RELATION`; target: `none`; confidence: MEDIUM; materiality: LOW.
- reason: Resistive Memory → Nonvolatile Memory (part_of): IRDS lists ReRAM among emerging non-charge NVMs; keep the 2024 roadmap boundary.
- evidence assessment: SC-EV-02E262518094E12D from SC-P0-009_2024_IRDS_More_Moore.pdf [source SC-PHYS-49A1D3B42E458985; SHA 49a1d3b42e45898555490e602170876e22d1ccf8d7c17711e436d8db36322fa6; PDF p.29, 5.3 Emerging Memories]: several non-conventional non-volatile memories that are not based on charge storage, so-called resistive or capacitive memories (ferroelectric or FeRAM, magnetic or MRAM, phase-change or PCRAM, and resistive or ReRAM), are being developed and form the category often called “emerging” memories. Boundary: Resistive Memory → Nonvolatile Memory (part_of): IRDS lists ReRAM among emerging non-charge NVMs; keep the 2024 roadmap boundary. All source excerpts remain UNAUTHORIZED_CANDIDATE evidence.
- temporal scope assessed: categorical_source_scoped
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'same', 'object_type': 'compatible', 'scope': 'compatible', 'granularity': 'same', 'quarantine': 'clear', 'ontology': 'compatible', 'evidence_sufficiency': 'sufficient', 'temporal': 'compatible'}

**A/B RECONCILIATION**

- A_B_SUBSTANTIVE_AGREEMENT; disagreement type: none; native-operation conflict: false; target conflict: false.
- Interpretation differences: none.
- Reconciliation assessment: Both reviewers support the same frozen endpoints, relation type, source scope, and evidence. Granularity labels refer to parent-child levels versus the proposed edge; bounded evidence comments do not change the edge.
- Non-material rubric-label differences retained for audit: granularity.

**EVIDENCE SUMMARY**

- Source `SC-PHYS-49A1D3B42E458985` (SHA-256 `49a1d3b42e45898555490e602170876e22d1ccf8d7c17711e436d8db36322fa6`), file `SC-P0-009_2024_IRDS_More_Moore.pdf`, p. 29, section 5.3 Emerging Memories; evidence `SC-EV-02E262518094E12D`; as-of 2024; excerpt: “several non-conventional non-volatile memories that are not based on charge storage, so-called resistive or capacitive memories (ferroelectric or FeRAM, magnetic or MRAM, phase-change or PCRAM, and resistive or ReRAM), are being developed and form the category often called “emerging” memories.”
- Temporal scope: categorical_source_scoped.

- SYSTEM_RECOMMENDED_DECISION: `CREATE_RELATION`.
- SYSTEM_RECOMMENDATION_REASON: A/B substantive consensus; frozen automated outcome: CREATE_RELATION.
- HUMAN_USER_DECISION = PENDING
- VALID NATIVE OPTIONS: REUSE_RELATION, CREATE_RELATION, KEEP_DOMAIN_SPECIFIC_RELATION, DEFER_RELATION, REJECT_RELATION; REUSE requires an explicit validated target ID and all options remain subject to frozen controls.

### Item 059 — SC-RL-0013 — Wet Etching → Etching

- ITEM_NUMBER: 59; ITEM_ID: `SC-RL-0013`; OBJECT_TYPE: relation.
- DOMAIN / context: `semiconductor` Semiconductor structured Foundation candidate against shared AI Hardware canonical catalog; cross-domain status: `candidate`.
- AUTOMATED_STAGE3_OUTCOME: `CREATE_RELATION`; CURRENT_CANONICAL_TARGET: `none`.
- Possible existing canonical IDs (unresolved unless explicitly reused): `none`.
- CANDIDATE_SUMMARY: Wet Etching → Etching; candidate type `part_of`; comparison scope `ASML 2023 generic process taxonomy`; frozen candidate rationale: Source原文直接支持有界命题；仅供local review，不表示授权。
- WHY_HUMAN_REQUIRED: frozen Stage 3 mandatory review population; automated reasons: DISTINCT_RELATION_PROPOSAL, LOW_OR_UNKNOWN_CONFIDENCE, PARENT_OR_CAUSAL_REVIEW.
- RISK_FLAGS: A=DISTINCT_RELATION_PROPOSAL, LOW_OR_UNKNOWN_CONFIDENCE, PARENT_OR_CAUSAL_REVIEW; B=FROZEN_STAGE2_DECISION.

**AI REVIEW A**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `CREATE_RELATION`; target: `{'from_node_id': 'NODE_A33DE27B0BCC969C', 'to_node_id': 'NODE_7FDCA2B3859210F3', 'from_ref': 'SC-CN-0058', 'to_ref': 'SC-CN-0060', 'relation_type': 'part_of', 'existing_relation_ids': []}`; confidence: HIGH; materiality: MEDIUM.
- reason: Wet Etching is a type of Etching in ASML's process taxonomy; Stage 2 CREATE is consistent.
- evidence assessment: ASML states there are wet and dry etch types and identifies wet chemical baths.
- temporal scope assessed: {'source_scope': 'ASML 2023 generic process taxonomy', 'temporal_status': 'categorical_source_scoped', 'runtime_status': 'categorical', 'valid_from': '', 'valid_to': '', 'source_as_of': ['2023-10-04']}
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'same', 'object_type': 'compatible', 'scope': 'compatible', 'granularity': 'different', 'quarantine': 'clear', 'ontology': 'compatible', 'evidence_sufficiency': 'sufficient', 'temporal': 'compatible'}

**AI REVIEW B**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `CREATE_RELATION`; target: `none`; confidence: MEDIUM; materiality: LOW.
- reason: Wet Etching → Etching (part_of): ASML names wet etch as an etch type and describes chemical baths; child-to-parent direction is correct.
- evidence assessment: SC-EV-F4124019AED7B2C6 from SC-P0-007_ASML_Six_Semiconductor_Manufacturing_Steps.pdf [source SC-PHYS-87B4665C30781057; SHA 87b4665c3078105792ca70f18964c938976b72f2dcf0d19379b034d5d6f205f9; PDF p.5, Etch]: As with resist, there are two types of etch: 'wet' and 'dry'. Dry etching uses gases to define the exposed pattern on the wafer. Wet etching uses chemical baths to wash the wafer. Boundary: Wet Etching → Etching (part_of): ASML names wet etch as an etch type and describes chemical baths; child-to-parent direction is correct. All source excerpts remain UNAUTHORIZED_CANDIDATE evidence.
- temporal scope assessed: categorical_source_scoped
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'same', 'object_type': 'compatible', 'scope': 'compatible', 'granularity': 'same', 'quarantine': 'clear', 'ontology': 'compatible', 'evidence_sufficiency': 'sufficient', 'temporal': 'compatible'}

**A/B RECONCILIATION**

- A_B_SUBSTANTIVE_AGREEMENT; disagreement type: none; native-operation conflict: false; target conflict: false.
- Interpretation differences: none.
- Reconciliation assessment: Both reviewers support the same frozen endpoints, relation type, source scope, and evidence. Granularity labels refer to parent-child levels versus the proposed edge; bounded evidence comments do not change the edge.
- Non-material rubric-label differences retained for audit: granularity.

**EVIDENCE SUMMARY**

- Source `SC-PHYS-87B4665C30781057` (SHA-256 `87b4665c3078105792ca70f18964c938976b72f2dcf0d19379b034d5d6f205f9`), file `SC-P0-007_ASML_Six_Semiconductor_Manufacturing_Steps.pdf`, p. 5, section Etch; evidence `SC-EV-F4124019AED7B2C6`; as-of 2023-10-04; excerpt: “As with resist, there are two types of etch: 'wet' and 'dry'. Dry etching uses gases to define the exposed pattern on the wafer. Wet etching uses chemical baths to wash the wafer.”
- Temporal scope: categorical_source_scoped.

- SYSTEM_RECOMMENDED_DECISION: `CREATE_RELATION`.
- SYSTEM_RECOMMENDATION_REASON: A/B substantive consensus; frozen automated outcome: CREATE_RELATION.
- HUMAN_USER_DECISION = PENDING
- VALID NATIVE OPTIONS: REUSE_RELATION, CREATE_RELATION, KEEP_DOMAIN_SPECIFIC_RELATION, DEFER_RELATION, REJECT_RELATION; REUSE requires an explicit validated target ID and all options remain subject to frozen controls.

### Item 060 — SC-RL-0014 — Dry Etching → Etching

- ITEM_NUMBER: 60; ITEM_ID: `SC-RL-0014`; OBJECT_TYPE: relation.
- DOMAIN / context: `semiconductor` Semiconductor structured Foundation candidate against shared AI Hardware canonical catalog; cross-domain status: `candidate`.
- AUTOMATED_STAGE3_OUTCOME: `CREATE_RELATION`; CURRENT_CANONICAL_TARGET: `none`.
- Possible existing canonical IDs (unresolved unless explicitly reused): `none`.
- CANDIDATE_SUMMARY: Dry Etching → Etching; candidate type `part_of`; comparison scope `ASML 2023 generic process taxonomy`; frozen candidate rationale: Source原文直接支持有界命题；仅供local review，不表示授权。
- WHY_HUMAN_REQUIRED: frozen Stage 3 mandatory review population; automated reasons: DISTINCT_RELATION_PROPOSAL, LOW_OR_UNKNOWN_CONFIDENCE, PARENT_OR_CAUSAL_REVIEW.
- RISK_FLAGS: A=DISTINCT_RELATION_PROPOSAL, LOW_OR_UNKNOWN_CONFIDENCE, PARENT_OR_CAUSAL_REVIEW; B=none.

**AI REVIEW A**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `CREATE_RELATION`; target: `{'from_node_id': 'NODE_967575C2572D76D4', 'to_node_id': 'NODE_7FDCA2B3859210F3', 'from_ref': 'SC-CN-0059', 'to_ref': 'SC-CN-0060', 'relation_type': 'part_of', 'existing_relation_ids': []}`; confidence: HIGH; materiality: MEDIUM.
- reason: Dry Etching is the second ASML Etching subtype and should not be conflated with wet etching.
- evidence assessment: ASML describes gas-based dry etching as one of two etch types.
- temporal scope assessed: {'source_scope': 'ASML 2023 generic process taxonomy', 'temporal_status': 'categorical_source_scoped', 'runtime_status': 'categorical', 'valid_from': '', 'valid_to': '', 'source_as_of': ['2023-10-04']}
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'same', 'object_type': 'compatible', 'scope': 'compatible', 'granularity': 'different', 'quarantine': 'clear', 'ontology': 'compatible', 'evidence_sufficiency': 'sufficient', 'temporal': 'compatible'}

**AI REVIEW B**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `CREATE_RELATION`; target: `none`; confidence: HIGH; materiality: LOW.
- reason: Dry Etching → Etching (part_of): ASML names dry etch as an etch type and describes gases; child-to-parent direction is correct.
- evidence assessment: SC-EV-F4124019AED7B2C6 from SC-P0-007_ASML_Six_Semiconductor_Manufacturing_Steps.pdf [source SC-PHYS-87B4665C30781057; SHA 87b4665c3078105792ca70f18964c938976b72f2dcf0d19379b034d5d6f205f9; PDF p.5, Etch]: As with resist, there are two types of etch: 'wet' and 'dry'. Dry etching uses gases to define the exposed pattern on the wafer. Wet etching uses chemical baths to wash the wafer. Boundary: Dry Etching → Etching (part_of): ASML names dry etch as an etch type and describes gases; child-to-parent direction is correct. All source excerpts remain UNAUTHORIZED_CANDIDATE evidence.
- temporal scope assessed: categorical_source_scoped
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'same', 'object_type': 'compatible', 'scope': 'compatible', 'granularity': 'same', 'quarantine': 'clear', 'ontology': 'compatible', 'evidence_sufficiency': 'sufficient', 'temporal': 'compatible'}

**A/B RECONCILIATION**

- A_B_SUBSTANTIVE_AGREEMENT; disagreement type: none; native-operation conflict: false; target conflict: false.
- Interpretation differences: none.
- Reconciliation assessment: Both reviewers support the same frozen endpoints, relation type, source scope, and evidence. Granularity labels refer to parent-child levels versus the proposed edge; bounded evidence comments do not change the edge.
- Non-material rubric-label differences retained for audit: granularity.

**EVIDENCE SUMMARY**

- Source `SC-PHYS-87B4665C30781057` (SHA-256 `87b4665c3078105792ca70f18964c938976b72f2dcf0d19379b034d5d6f205f9`), file `SC-P0-007_ASML_Six_Semiconductor_Manufacturing_Steps.pdf`, p. 5, section Etch; evidence `SC-EV-F4124019AED7B2C6`; as-of 2023-10-04; excerpt: “As with resist, there are two types of etch: 'wet' and 'dry'. Dry etching uses gases to define the exposed pattern on the wafer. Wet etching uses chemical baths to wash the wafer.”
- Temporal scope: categorical_source_scoped.

- SYSTEM_RECOMMENDED_DECISION: `CREATE_RELATION`.
- SYSTEM_RECOMMENDATION_REASON: A/B substantive consensus; frozen automated outcome: CREATE_RELATION.
- HUMAN_USER_DECISION = PENDING
- VALID NATIVE OPTIONS: REUSE_RELATION, CREATE_RELATION, KEEP_DOMAIN_SPECIFIC_RELATION, DEFER_RELATION, REJECT_RELATION; REUSE requires an explicit validated target ID and all options remain subject to frozen controls.

### Item 061 — SC-RL-0015 — Positive Photoresist → Photoresist

- ITEM_NUMBER: 61; ITEM_ID: `SC-RL-0015`; OBJECT_TYPE: relation.
- DOMAIN / context: `semiconductor` Semiconductor structured Foundation candidate against shared AI Hardware canonical catalog; cross-domain status: `candidate`.
- AUTOMATED_STAGE3_OUTCOME: `DEFER_RELATION`; CURRENT_CANONICAL_TARGET: `none`.
- Possible existing canonical IDs (unresolved unless explicitly reused): `none`.
- CANDIDATE_SUMMARY: Positive Photoresist → Photoresist; candidate type `part_of`; comparison scope `ASML 2023 resist taxonomy`; frozen candidate rationale: 一个或两个端点尚未通过身份候选准入；证据保留，不提前授权端点。
- WHY_HUMAN_REQUIRED: frozen Stage 3 mandatory review population; automated reasons: ENDPOINT_AMBIGUITY, EVIDENCE_WARNING, LOW_OR_UNKNOWN_CONFIDENCE, PARENT_OR_CAUSAL_REVIEW, RELATION_AMBIGUITY.
- RISK_FLAGS: A=ENDPOINT_AMBIGUITY, EVIDENCE_WARNING, LOW_OR_UNKNOWN_CONFIDENCE, PARENT_OR_CAUSAL_REVIEW, RELATION_AMBIGUITY; B=UNRESOLVED_RELATION, ENDPOINT_OR_RECONCILIATION.

**AI REVIEW A**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `DEFER_RELATION`; target: `{'from_node_id': None, 'to_node_id': None, 'from_ref': 'SC-CN-0054', 'to_ref': 'SC-CN-0052', 'relation_type': 'part_of', 'existing_relation_ids': []}`; confidence: HIGH; materiality: MEDIUM.
- reason: Positive Photoresist to Photoresist is a sound taxonomy proposal, but the generic Photoresist target has no approved identity yet.
- evidence assessment: ASML explicitly says resist has positive and negative types; evidence is sufficient for taxonomy after endpoint review.
- temporal scope assessed: {'source_scope': 'ASML 2023 resist taxonomy', 'temporal_status': 'categorical_source_scoped', 'runtime_status': 'categorical', 'valid_from': '', 'valid_to': '', 'source_as_of': ['2023-10-04']}
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'ambiguous', 'object_type': 'unknown', 'scope': 'unknown', 'granularity': 'different', 'quarantine': 'clear', 'ontology': 'compatible', 'evidence_sufficiency': 'sufficient', 'temporal': 'compatible'}

**AI REVIEW B**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `DEFER_RELATION`; target: `none`; confidence: MEDIUM; materiality: HIGH.
- reason: Positive Photoresist → Photoresist (part_of): ASML splits resist into positive and negative, but generic Photoresist identity remains under Stage 3 review.
- evidence assessment: SC-EV-5A701F864F4A7C10 from SC-P0-007_ASML_Six_Semiconductor_Manufacturing_Steps.pdf [source SC-PHYS-87B4665C30781057; SHA 87b4665c3078105792ca70f18964c938976b72f2dcf0d19379b034d5d6f205f9; PDF p.3, Photoresist coating]: The wafer is then covered with a light-sensitive coating called 'photoresist', or 'resist' for short. There are two types of resist: positive and negative. Boundary: Positive Photoresist → Photoresist (part_of): ASML splits resist into positive and negative, but generic Photoresist identity remains under Stage 3 review. All source excerpts remain UNAUTHORIZED_CANDIDATE evidence.
- temporal scope assessed: categorical_source_scoped
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'ambiguous', 'object_type': 'unknown', 'scope': 'unknown', 'granularity': 'unknown', 'quarantine': 'clear', 'ontology': 'unresolved', 'evidence_sufficiency': 'limited', 'temporal': 'compatible'}

**A/B RECONCILIATION**

- A_B_SUBSTANTIVE_AGREEMENT; disagreement type: none; native-operation conflict: false; target conflict: false.
- Interpretation differences: none.
- Reconciliation assessment: Both reviewers hold the same endpoint, temporal, or ontology exception. Rubric labels compare concept support with authority for the relation.
- Non-material rubric-label differences retained for audit: evidence_sufficiency, granularity, ontology.

**EVIDENCE SUMMARY**

- Source `SC-PHYS-87B4665C30781057` (SHA-256 `87b4665c3078105792ca70f18964c938976b72f2dcf0d19379b034d5d6f205f9`), file `SC-P0-007_ASML_Six_Semiconductor_Manufacturing_Steps.pdf`, p. 3, section Photoresist coating; evidence `SC-EV-5A701F864F4A7C10`; as-of 2023-10-04; excerpt: “The wafer is then covered with a light-sensitive coating called 'photoresist', or 'resist' for short. There are two types of resist: positive and negative.”
- Temporal scope: categorical_source_scoped.

- SYSTEM_RECOMMENDED_DECISION: `DEFER_RELATION`.
- SYSTEM_RECOMMENDATION_REASON: Frozen structural, Stage 2 decision, evidence, or temporal exception remains unresolved.
- HUMAN_USER_DECISION = PENDING
- VALID NATIVE OPTIONS: REUSE_RELATION, CREATE_RELATION, KEEP_DOMAIN_SPECIFIC_RELATION, DEFER_RELATION, REJECT_RELATION; REUSE requires an explicit validated target ID and all options remain subject to frozen controls.

### Item 062 — SC-RL-0016 — Negative Photoresist → Photoresist

- ITEM_NUMBER: 62; ITEM_ID: `SC-RL-0016`; OBJECT_TYPE: relation.
- DOMAIN / context: `semiconductor` Semiconductor structured Foundation candidate against shared AI Hardware canonical catalog; cross-domain status: `candidate`.
- AUTOMATED_STAGE3_OUTCOME: `DEFER_RELATION`; CURRENT_CANONICAL_TARGET: `none`.
- Possible existing canonical IDs (unresolved unless explicitly reused): `none`.
- CANDIDATE_SUMMARY: Negative Photoresist → Photoresist; candidate type `part_of`; comparison scope `ASML 2023 resist taxonomy`; frozen candidate rationale: 一个或两个端点尚未通过身份候选准入；证据保留，不提前授权端点。
- WHY_HUMAN_REQUIRED: frozen Stage 3 mandatory review population; automated reasons: ENDPOINT_AMBIGUITY, EVIDENCE_WARNING, LOW_OR_UNKNOWN_CONFIDENCE, PARENT_OR_CAUSAL_REVIEW, RELATION_AMBIGUITY.
- RISK_FLAGS: A=ENDPOINT_AMBIGUITY, EVIDENCE_WARNING, LOW_OR_UNKNOWN_CONFIDENCE, PARENT_OR_CAUSAL_REVIEW, RELATION_AMBIGUITY; B=UNRESOLVED_RELATION, ENDPOINT_OR_RECONCILIATION.

**AI REVIEW A**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `DEFER_RELATION`; target: `{'from_node_id': None, 'to_node_id': None, 'from_ref': 'SC-CN-0055', 'to_ref': 'SC-CN-0052', 'relation_type': 'part_of', 'existing_relation_ids': []}`; confidence: HIGH; materiality: MEDIUM.
- reason: Negative Photoresist has the same unresolved parent endpoint; keep a separate child edge pending identity approval.
- evidence assessment: ASML names negative resist as a distinct type, but does not authorize the held Photoresist node.
- temporal scope assessed: {'source_scope': 'ASML 2023 resist taxonomy', 'temporal_status': 'categorical_source_scoped', 'runtime_status': 'categorical', 'valid_from': '', 'valid_to': '', 'source_as_of': ['2023-10-04']}
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'ambiguous', 'object_type': 'unknown', 'scope': 'unknown', 'granularity': 'different', 'quarantine': 'clear', 'ontology': 'compatible', 'evidence_sufficiency': 'sufficient', 'temporal': 'compatible'}

**AI REVIEW B**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `DEFER_RELATION`; target: `none`; confidence: MEDIUM; materiality: HIGH.
- reason: Negative Photoresist → Photoresist (part_of): Negative resist is sibling to positive resist; settle generic Photoresist before attaching either child.
- evidence assessment: SC-EV-5A701F864F4A7C10 from SC-P0-007_ASML_Six_Semiconductor_Manufacturing_Steps.pdf [source SC-PHYS-87B4665C30781057; SHA 87b4665c3078105792ca70f18964c938976b72f2dcf0d19379b034d5d6f205f9; PDF p.3, Photoresist coating]: The wafer is then covered with a light-sensitive coating called 'photoresist', or 'resist' for short. There are two types of resist: positive and negative. Boundary: Negative Photoresist → Photoresist (part_of): Negative resist is sibling to positive resist; settle generic Photoresist before attaching either child. All source excerpts remain UNAUTHORIZED_CANDIDATE evidence.
- temporal scope assessed: categorical_source_scoped
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'ambiguous', 'object_type': 'unknown', 'scope': 'unknown', 'granularity': 'unknown', 'quarantine': 'clear', 'ontology': 'unresolved', 'evidence_sufficiency': 'limited', 'temporal': 'compatible'}

**A/B RECONCILIATION**

- A_B_SUBSTANTIVE_AGREEMENT; disagreement type: none; native-operation conflict: false; target conflict: false.
- Interpretation differences: none.
- Reconciliation assessment: Both reviewers hold the same endpoint, temporal, or ontology exception. Rubric labels compare concept support with authority for the relation.
- Non-material rubric-label differences retained for audit: evidence_sufficiency, granularity, ontology.

**EVIDENCE SUMMARY**

- Source `SC-PHYS-87B4665C30781057` (SHA-256 `87b4665c3078105792ca70f18964c938976b72f2dcf0d19379b034d5d6f205f9`), file `SC-P0-007_ASML_Six_Semiconductor_Manufacturing_Steps.pdf`, p. 3, section Photoresist coating; evidence `SC-EV-5A701F864F4A7C10`; as-of 2023-10-04; excerpt: “The wafer is then covered with a light-sensitive coating called 'photoresist', or 'resist' for short. There are two types of resist: positive and negative.”
- Temporal scope: categorical_source_scoped.

- SYSTEM_RECOMMENDED_DECISION: `DEFER_RELATION`.
- SYSTEM_RECOMMENDATION_REASON: Frozen structural, Stage 2 decision, evidence, or temporal exception remains unresolved.
- HUMAN_USER_DECISION = PENDING
- VALID NATIVE OPTIONS: REUSE_RELATION, CREATE_RELATION, KEEP_DOMAIN_SPECIFIC_RELATION, DEFER_RELATION, REJECT_RELATION; REUSE requires an explicit validated target ID and all options remain subject to frozen controls.

### Item 063 — SC-RL-0017 — Silicon Interposer → Interposer

- ITEM_NUMBER: 63; ITEM_ID: `SC-RL-0017`; OBJECT_TYPE: relation.
- DOMAIN / context: `semiconductor` Semiconductor structured Foundation candidate against shared AI Hardware canonical catalog; cross-domain status: `candidate`.
- AUTOMATED_STAGE3_OUTCOME: `CREATE_RELATION`; CURRENT_CANONICAL_TARGET: `none`.
- Possible existing canonical IDs (unresolved unless explicitly reused): `none`.
- CANDIDATE_SUMMARY: Silicon Interposer → Interposer; candidate type `part_of`; comparison scope `IRDS 2025 packaging-lithography interposer taxonomy`; frozen candidate rationale: Source原文直接支持有界命题；仅供local review，不表示授权。
- WHY_HUMAN_REQUIRED: frozen Stage 3 mandatory review population; automated reasons: DISTINCT_RELATION_PROPOSAL, LOW_OR_UNKNOWN_CONFIDENCE, PARENT_OR_CAUSAL_REVIEW.
- RISK_FLAGS: A=DISTINCT_RELATION_PROPOSAL, LOW_OR_UNKNOWN_CONFIDENCE, PARENT_OR_CAUSAL_REVIEW; B=none.

**AI REVIEW A**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `CREATE_RELATION`; target: `{'from_node_id': 'NODE_20260817_3A173B33', 'to_node_id': 'NODE_C37B83D6D0B8A843', 'from_ref': 'NODE_20260817_3A173B33', 'to_ref': 'SC-CN-0112', 'relation_type': 'part_of', 'existing_relation_ids': []}`; confidence: MEDIUM; materiality: MEDIUM.
- reason: Silicon Interposer is a subtype of generic Interposer in the scoped IRDS taxonomy.
- evidence assessment: IRDS lists silicon interposers among the two interposer product types it discusses.
- temporal scope assessed: {'source_scope': 'IRDS 2025 packaging-lithography interposer taxonomy', 'temporal_status': 'categorical_source_scoped', 'runtime_status': 'categorical', 'valid_from': '', 'valid_to': '', 'source_as_of': ['2025']}
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'same', 'object_type': 'compatible', 'scope': 'compatible', 'granularity': 'different', 'quarantine': 'clear', 'ontology': 'compatible', 'evidence_sufficiency': 'sufficient', 'temporal': 'compatible'}

**AI REVIEW B**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `CREATE_RELATION`; target: `none`; confidence: HIGH; materiality: LOW.
- reason: Silicon Interposer → Interposer (part_of): IRDS names silicon interposers as an interposer product type; generic Interposer is a separate parent proposal.
- evidence assessment: SC-EV-34A6DFF0912F7884 from SC-P0-010_2025_IRDS_Lithography_and_Patterning.pdf [source SC-PHYS-318D85A127B5B6DF; SHA 318d85a127b5b6dfa7b3c1330ae20b18d63660a1fa8c8bdfdd7b478844e145ed; PDF p.21, Packaging Lithography]: This roadmap focuses on two types of interposer products. 1) Silicon interposers and silicon bridge interposers—This type uses fine re-distribution layers (RDLs) on silicon substrate formed by BEOL processes for fine pitch interconnections. 2) Organic interposers and RDL interposers—This type has RDLs only in organic layers for die-to-die interconnections. Boundary: Silicon Interposer → Interposer (part_of): IRDS names silicon interposers as an interposer product type; generic Interposer is a separate parent proposal. All source excerpts remain UNAUTHORIZED_CANDIDATE evidence.
- temporal scope assessed: categorical_source_scoped
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'same', 'object_type': 'compatible', 'scope': 'compatible', 'granularity': 'same', 'quarantine': 'clear', 'ontology': 'compatible', 'evidence_sufficiency': 'sufficient', 'temporal': 'compatible'}

**A/B RECONCILIATION**

- A_B_SUBSTANTIVE_AGREEMENT; disagreement type: none; native-operation conflict: false; target conflict: false.
- Interpretation differences: none.
- Reconciliation assessment: Both reviewers support the same frozen endpoints, relation type, source scope, and evidence. Granularity labels refer to parent-child levels versus the proposed edge; bounded evidence comments do not change the edge.
- Non-material rubric-label differences retained for audit: granularity.

**EVIDENCE SUMMARY**

- Source `SC-PHYS-318D85A127B5B6DF` (SHA-256 `318d85a127b5b6dfa7b3c1330ae20b18d63660a1fa8c8bdfdd7b478844e145ed`), file `SC-P0-010_2025_IRDS_Lithography_and_Patterning.pdf`, p. 21, section Packaging Lithography; evidence `SC-EV-34A6DFF0912F7884`; as-of 2025; excerpt: “This roadmap focuses on two types of interposer products. 1) Silicon interposers and silicon bridge interposers—This type uses fine re-distribution layers (RDLs) on silicon substrate formed by BEOL processes for fine pitch interconnections. 2) Organic interposers and RDL interposers—This type has RDLs only in organic layers for die-to-die interconnections.”
- Temporal scope: categorical_source_scoped.

- SYSTEM_RECOMMENDED_DECISION: `CREATE_RELATION`.
- SYSTEM_RECOMMENDATION_REASON: A/B substantive consensus; frozen automated outcome: CREATE_RELATION.
- HUMAN_USER_DECISION = PENDING
- VALID NATIVE OPTIONS: REUSE_RELATION, CREATE_RELATION, KEEP_DOMAIN_SPECIFIC_RELATION, DEFER_RELATION, REJECT_RELATION; REUSE requires an explicit validated target ID and all options remain subject to frozen controls.

### Item 064 — SC-RL-0018 — RDL Interposer → Interposer

- ITEM_NUMBER: 64; ITEM_ID: `SC-RL-0018`; OBJECT_TYPE: relation.
- DOMAIN / context: `semiconductor` Semiconductor structured Foundation candidate against shared AI Hardware canonical catalog; cross-domain status: `candidate`.
- AUTOMATED_STAGE3_OUTCOME: `CREATE_RELATION`; CURRENT_CANONICAL_TARGET: `none`.
- Possible existing canonical IDs (unresolved unless explicitly reused): `none`.
- CANDIDATE_SUMMARY: RDL Interposer → Interposer; candidate type `part_of`; comparison scope `IRDS 2025 packaging-lithography interposer taxonomy`; frozen candidate rationale: Source原文直接支持有界命题；仅供local review，不表示授权。
- WHY_HUMAN_REQUIRED: frozen Stage 3 mandatory review population; automated reasons: DISTINCT_RELATION_PROPOSAL, LOW_OR_UNKNOWN_CONFIDENCE, PARENT_OR_CAUSAL_REVIEW.
- RISK_FLAGS: A=DISTINCT_RELATION_PROPOSAL, LOW_OR_UNKNOWN_CONFIDENCE, PARENT_OR_CAUSAL_REVIEW; B=none.

**AI REVIEW A**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `CREATE_RELATION`; target: `{'from_node_id': 'NODE_20260817_4AA22685', 'to_node_id': 'NODE_C37B83D6D0B8A843', 'from_ref': 'NODE_20260817_4AA22685', 'to_ref': 'SC-CN-0112', 'relation_type': 'part_of', 'existing_relation_ids': []}`; confidence: MEDIUM; materiality: MEDIUM.
- reason: RDL Interposer is the other scoped interposer product type; do not infer that every interposer uses RDL.
- evidence assessment: The IRDS roadmap distinguishes an RDL interposer category from silicon interposers.
- temporal scope assessed: {'source_scope': 'IRDS 2025 packaging-lithography interposer taxonomy', 'temporal_status': 'categorical_source_scoped', 'runtime_status': 'categorical', 'valid_from': '', 'valid_to': '', 'source_as_of': ['2025']}
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'same', 'object_type': 'compatible', 'scope': 'compatible', 'granularity': 'different', 'quarantine': 'clear', 'ontology': 'compatible', 'evidence_sufficiency': 'sufficient', 'temporal': 'compatible'}

**AI REVIEW B**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `CREATE_RELATION`; target: `none`; confidence: HIGH; materiality: LOW.
- reason: RDL Interposer → Interposer (part_of): IRDS names RDL interposers as a type using organic-layer RDLs, distinct from Silicon Interposer.
- evidence assessment: SC-EV-34A6DFF0912F7884 from SC-P0-010_2025_IRDS_Lithography_and_Patterning.pdf [source SC-PHYS-318D85A127B5B6DF; SHA 318d85a127b5b6dfa7b3c1330ae20b18d63660a1fa8c8bdfdd7b478844e145ed; PDF p.21, Packaging Lithography]: This roadmap focuses on two types of interposer products. 1) Silicon interposers and silicon bridge interposers—This type uses fine re-distribution layers (RDLs) on silicon substrate formed by BEOL processes for fine pitch interconnections. 2) Organic interposers and RDL interposers—This type has RDLs only in organic layers for die-to-die interconnections. Boundary: RDL Interposer → Interposer (part_of): IRDS names RDL interposers as a type using organic-layer RDLs, distinct from Silicon Interposer. All source excerpts remain UNAUTHORIZED_CANDIDATE evidence.
- temporal scope assessed: categorical_source_scoped
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'same', 'object_type': 'compatible', 'scope': 'compatible', 'granularity': 'same', 'quarantine': 'clear', 'ontology': 'compatible', 'evidence_sufficiency': 'sufficient', 'temporal': 'compatible'}

**A/B RECONCILIATION**

- A_B_SUBSTANTIVE_AGREEMENT; disagreement type: none; native-operation conflict: false; target conflict: false.
- Interpretation differences: none.
- Reconciliation assessment: Both reviewers support the same frozen endpoints, relation type, source scope, and evidence. Granularity labels refer to parent-child levels versus the proposed edge; bounded evidence comments do not change the edge.
- Non-material rubric-label differences retained for audit: granularity.

**EVIDENCE SUMMARY**

- Source `SC-PHYS-318D85A127B5B6DF` (SHA-256 `318d85a127b5b6dfa7b3c1330ae20b18d63660a1fa8c8bdfdd7b478844e145ed`), file `SC-P0-010_2025_IRDS_Lithography_and_Patterning.pdf`, p. 21, section Packaging Lithography; evidence `SC-EV-34A6DFF0912F7884`; as-of 2025; excerpt: “This roadmap focuses on two types of interposer products. 1) Silicon interposers and silicon bridge interposers—This type uses fine re-distribution layers (RDLs) on silicon substrate formed by BEOL processes for fine pitch interconnections. 2) Organic interposers and RDL interposers—This type has RDLs only in organic layers for die-to-die interconnections.”
- Temporal scope: categorical_source_scoped.

- SYSTEM_RECOMMENDED_DECISION: `CREATE_RELATION`.
- SYSTEM_RECOMMENDATION_REASON: A/B substantive consensus; frozen automated outcome: CREATE_RELATION.
- HUMAN_USER_DECISION = PENDING
- VALID NATIVE OPTIONS: REUSE_RELATION, CREATE_RELATION, KEEP_DOMAIN_SPECIFIC_RELATION, DEFER_RELATION, REJECT_RELATION; REUSE requires an explicit validated target ID and all options remain subject to frozen controls.

### Item 065 — SC-RL-0019 — CoWoS-S → CoWoS

- ITEM_NUMBER: 65; ITEM_ID: `SC-RL-0019`; OBJECT_TYPE: relation.
- DOMAIN / context: `semiconductor` Semiconductor structured Foundation candidate against shared AI Hardware canonical catalog; cross-domain status: `candidate`.
- AUTOMATED_STAGE3_OUTCOME: `DEFER_RELATION`; CURRENT_CANONICAL_TARGET: `REL_C7A9B2A6B39D730E`.
- Possible existing canonical IDs (unresolved unless explicitly reused): `REL_C7A9B2A6B39D730E`.
- CANDIDATE_SUMMARY: CoWoS-S → CoWoS; candidate type `part_of`; comparison scope `TSMC packaging family taxonomy`; frozen candidate rationale: Source原文直接支持有界命题；仅供local review，不表示授权。 当前已存在同scope关系；仅提交新的证据候选，不能重复创建边或复用旧授权。
- WHY_HUMAN_REQUIRED: frozen Stage 3 mandatory review population; automated reasons: LOW_OR_UNKNOWN_CONFIDENCE, PARENT_OR_CAUSAL_REVIEW, TEMPORAL_MISMATCH.
- RISK_FLAGS: A=LOW_OR_UNKNOWN_CONFIDENCE, PARENT_OR_CAUSAL_REVIEW, TEMPORAL_MISMATCH; B=UNRESOLVED_RELATION, ENDPOINT_OR_RECONCILIATION, TEMPORAL_MISMATCH.

**AI REVIEW A**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `DEFER_RELATION`; target: `{'from_node_id': 'NODE_3E0E5604C3F64891', 'to_node_id': 'NODE_20260814_9B66BB15', 'from_ref': 'NODE_3E0E5604C3F64891', 'to_ref': 'NODE_20260814_9B66BB15', 'relation_type': 'part_of', 'existing_relation_ids': ['REL_C7A9B2A6B39D730E']}`; confidence: HIGH; materiality: HIGH.
- reason: An existing CoWoS-S-to-CoWoS edge is identified, but its current temporal status differs from the candidate's source-scoped categorical status; attach evidence only after temporal review.
- evidence assessment: TSMC describes CoWoS-S as a silicon-interposer service; the text supports family membership but cannot rewrite existing edge validity.
- temporal scope assessed: {'source_scope': 'TSMC packaging family taxonomy', 'temporal_status': 'categorical_source_scoped', 'runtime_status': 'categorical', 'valid_from': '', 'valid_to': '', 'source_as_of': ['2025']}
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'same', 'object_type': 'compatible', 'scope': 'unknown', 'granularity': 'different', 'quarantine': 'clear', 'ontology': 'compatible', 'evidence_sufficiency': 'sufficient', 'temporal': 'mismatch'}

**AI REVIEW B**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `DEFER_RELATION`; target: `none`; confidence: MEDIUM; materiality: HIGH.
- reason: CoWoS-S → CoWoS (part_of): A CoWoS-S to CoWoS edge exists, but its temporal status mismatches this source-scoped category; do not duplicate it.
- evidence assessment: SC-EV-A5D5D8057F31DBE3 from SC-P0-020B_TSMC_2025_Annual_Report.pdf [source F018b; SHA 3fb7ae4ad972aa2bc6e45bb36635152ad89d52f4a7165f389bcb94eeb54a6abd; PDF p.53, TSMC 3DFabric / CoWoS-S]: CoWoS® with silicon interposer (CoWoS®-S) advanced packaging service features high interconnect routing density and embedded deep trench capacitor (eDTC) and has been in volume production for several years. Boundary: CoWoS-S → CoWoS (part_of): A CoWoS-S to CoWoS edge exists, but its temporal status mismatches this source-scoped category; do not duplicate it. All source excerpts remain UNAUTHORIZED_CANDIDATE evidence.
- temporal scope assessed: categorical_source_scoped
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'ambiguous', 'object_type': 'compatible', 'scope': 'compatible', 'granularity': 'same', 'quarantine': 'clear', 'ontology': 'unresolved', 'evidence_sufficiency': 'limited', 'temporal': 'mismatch'}

**A/B RECONCILIATION**

- A_B_SUBSTANTIVE_AGREEMENT; disagreement type: none; native-operation conflict: false; target conflict: false.
- Interpretation differences: none.
- Reconciliation assessment: Both reviewers hold the same endpoint, temporal, or ontology exception. Rubric labels compare concept support with authority for the relation.
- Non-material rubric-label differences retained for audit: evidence_sufficiency, granularity, identity_boundary, ontology, scope.

**EVIDENCE SUMMARY**

- Source `F018b` (SHA-256 `3fb7ae4ad972aa2bc6e45bb36635152ad89d52f4a7165f389bcb94eeb54a6abd`), file `SC-P0-020B_TSMC_2025_Annual_Report.pdf`, p. 53, section TSMC 3DFabric / CoWoS-S; evidence `SC-EV-A5D5D8057F31DBE3`; as-of 2025; excerpt: “CoWoS® with silicon interposer (CoWoS®-S) advanced packaging service features high interconnect routing density and embedded deep trench capacitor (eDTC) and has been in volume production for several years.”
- Temporal scope: categorical_source_scoped.

- SYSTEM_RECOMMENDED_DECISION: `DEFER_RELATION`.
- SYSTEM_RECOMMENDATION_REASON: Frozen structural, Stage 2 decision, evidence, or temporal exception remains unresolved.
- HUMAN_USER_DECISION = PENDING
- VALID NATIVE OPTIONS: REUSE_RELATION, CREATE_RELATION, KEEP_DOMAIN_SPECIFIC_RELATION, DEFER_RELATION, REJECT_RELATION; REUSE requires an explicit validated target ID and all options remain subject to frozen controls.

### Item 066 — SC-RL-0020 — CoWoS-R → CoWoS

- ITEM_NUMBER: 66; ITEM_ID: `SC-RL-0020`; OBJECT_TYPE: relation.
- DOMAIN / context: `semiconductor` Semiconductor structured Foundation candidate against shared AI Hardware canonical catalog; cross-domain status: `candidate`.
- AUTOMATED_STAGE3_OUTCOME: `DEFER_RELATION`; CURRENT_CANONICAL_TARGET: `REL_64DC09E2645913E2`.
- Possible existing canonical IDs (unresolved unless explicitly reused): `REL_64DC09E2645913E2`.
- CANDIDATE_SUMMARY: CoWoS-R → CoWoS; candidate type `part_of`; comparison scope `TSMC packaging family taxonomy`; frozen candidate rationale: Source原文直接支持有界命题；仅供local review，不表示授权。 当前已存在同scope关系；仅提交新的证据候选，不能重复创建边或复用旧授权。
- WHY_HUMAN_REQUIRED: frozen Stage 3 mandatory review population; automated reasons: LOW_OR_UNKNOWN_CONFIDENCE, PARENT_OR_CAUSAL_REVIEW, TEMPORAL_MISMATCH.
- RISK_FLAGS: A=LOW_OR_UNKNOWN_CONFIDENCE, PARENT_OR_CAUSAL_REVIEW, TEMPORAL_MISMATCH; B=UNRESOLVED_RELATION, ENDPOINT_OR_RECONCILIATION, TEMPORAL_MISMATCH.

**AI REVIEW A**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `DEFER_RELATION`; target: `{'from_node_id': 'NODE_B7B4CB43F4C30F10', 'to_node_id': 'NODE_20260814_9B66BB15', 'from_ref': 'NODE_B7B4CB43F4C30F10', 'to_ref': 'NODE_20260814_9B66BB15', 'relation_type': 'part_of', 'existing_relation_ids': ['REL_64DC09E2645913E2']}`; confidence: HIGH; materiality: HIGH.
- reason: The existing CoWoS-R-to-CoWoS edge must not be duplicated or silently converted from current to categorical status.
- evidence assessment: TSMC names the R branch and its RDL interposer; this supports a bounded family assertion, not automatic reuse of the current edge.
- temporal scope assessed: {'source_scope': 'TSMC packaging family taxonomy', 'temporal_status': 'categorical_source_scoped', 'runtime_status': 'categorical', 'valid_from': '', 'valid_to': '', 'source_as_of': ['2025']}
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'same', 'object_type': 'compatible', 'scope': 'unknown', 'granularity': 'different', 'quarantine': 'clear', 'ontology': 'compatible', 'evidence_sufficiency': 'sufficient', 'temporal': 'mismatch'}

**AI REVIEW B**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `DEFER_RELATION`; target: `none`; confidence: MEDIUM; materiality: HIGH.
- reason: CoWoS-R → CoWoS (part_of): A CoWoS-R to CoWoS edge exists, but its temporal status mismatches this source-scoped category; hold reconciliation.
- evidence assessment: SC-EV-BE1EFC0405668731 from SC-P0-020B_TSMC_2025_Annual_Report.pdf [source F018b; SHA 3fb7ae4ad972aa2bc6e45bb36635152ad89d52f4a7165f389bcb94eeb54a6abd; PDF p.53, TSMC 3DFabric / CoWoS-R]: CoWoS® with redistribution layer interposer (CoWoS®-R) advanced packaging service, featuring multiple redistribution layers (RDL) to enable product design simplicity, supports larger HPC products. This technology entered its third year of volume production in 2025. Boundary: CoWoS-R → CoWoS (part_of): A CoWoS-R to CoWoS edge exists, but its temporal status mismatches this source-scoped category; hold reconciliation. All source excerpts remain UNAUTHORIZED_CANDIDATE evidence.
- temporal scope assessed: categorical_source_scoped
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'ambiguous', 'object_type': 'compatible', 'scope': 'compatible', 'granularity': 'same', 'quarantine': 'clear', 'ontology': 'unresolved', 'evidence_sufficiency': 'limited', 'temporal': 'mismatch'}

**A/B RECONCILIATION**

- A_B_SUBSTANTIVE_AGREEMENT; disagreement type: none; native-operation conflict: false; target conflict: false.
- Interpretation differences: none.
- Reconciliation assessment: Both reviewers hold the same endpoint, temporal, or ontology exception. Rubric labels compare concept support with authority for the relation.
- Non-material rubric-label differences retained for audit: evidence_sufficiency, granularity, identity_boundary, ontology, scope.

**EVIDENCE SUMMARY**

- Source `F018b` (SHA-256 `3fb7ae4ad972aa2bc6e45bb36635152ad89d52f4a7165f389bcb94eeb54a6abd`), file `SC-P0-020B_TSMC_2025_Annual_Report.pdf`, p. 53, section TSMC 3DFabric / CoWoS-R; evidence `SC-EV-BE1EFC0405668731`; as-of 2025; excerpt: “CoWoS® with redistribution layer interposer (CoWoS®-R) advanced packaging service, featuring multiple redistribution layers (RDL) to enable product design simplicity, supports larger HPC products. This technology entered its third year of volume production in 2025.”
- Temporal scope: categorical_source_scoped.

- SYSTEM_RECOMMENDED_DECISION: `DEFER_RELATION`.
- SYSTEM_RECOMMENDATION_REASON: Frozen structural, Stage 2 decision, evidence, or temporal exception remains unresolved.
- HUMAN_USER_DECISION = PENDING
- VALID NATIVE OPTIONS: REUSE_RELATION, CREATE_RELATION, KEEP_DOMAIN_SPECIFIC_RELATION, DEFER_RELATION, REJECT_RELATION; REUSE requires an explicit validated target ID and all options remain subject to frozen controls.

### Item 067 — SC-RL-0021 — CoWoS-L → CoWoS

- ITEM_NUMBER: 67; ITEM_ID: `SC-RL-0021`; OBJECT_TYPE: relation.
- DOMAIN / context: `semiconductor` Semiconductor structured Foundation candidate against shared AI Hardware canonical catalog; cross-domain status: `candidate`.
- AUTOMATED_STAGE3_OUTCOME: `CREATE_RELATION`; CURRENT_CANONICAL_TARGET: `none`.
- Possible existing canonical IDs (unresolved unless explicitly reused): `none`.
- CANDIDATE_SUMMARY: CoWoS-L → CoWoS; candidate type `part_of`; comparison scope `TSMC packaging family taxonomy`; frozen candidate rationale: Source原文直接支持有界命题；仅供local review，不表示授权。
- WHY_HUMAN_REQUIRED: frozen Stage 3 mandatory review population; automated reasons: DISTINCT_RELATION_PROPOSAL, LOW_OR_UNKNOWN_CONFIDENCE, PARENT_OR_CAUSAL_REVIEW.
- RISK_FLAGS: A=DISTINCT_RELATION_PROPOSAL, LOW_OR_UNKNOWN_CONFIDENCE, PARENT_OR_CAUSAL_REVIEW; B=none.

**AI REVIEW A**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `CREATE_RELATION`; target: `{'from_node_id': 'NODE_1A7F2D5816F5B7EE', 'to_node_id': 'NODE_20260814_9B66BB15', 'from_ref': 'NODE_1A7F2D5816F5B7EE', 'to_ref': 'NODE_20260814_9B66BB15', 'relation_type': 'part_of', 'existing_relation_ids': []}`; confidence: MEDIUM; materiality: MEDIUM.
- reason: CoWoS-L is a distinct TSMC CoWoS service branch with no existing comparable edge.
- evidence assessment: The annual report presents CoWoS-L as a service combining CoWoS with an RDL-based interposer and LSI.
- temporal scope assessed: {'source_scope': 'TSMC packaging family taxonomy', 'temporal_status': 'categorical_source_scoped', 'runtime_status': 'categorical', 'valid_from': '', 'valid_to': '', 'source_as_of': ['2025', '2024']}
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'same', 'object_type': 'compatible', 'scope': 'compatible', 'granularity': 'different', 'quarantine': 'clear', 'ontology': 'compatible', 'evidence_sufficiency': 'sufficient', 'temporal': 'compatible'}

**AI REVIEW B**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `CREATE_RELATION`; target: `none`; confidence: HIGH; materiality: LOW.
- reason: CoWoS-L → CoWoS (part_of): TSMC identifies CoWoS-L as a branded CoWoS branch, distinct from S and R; scope the family edge to TSMC.
- evidence assessment: SC-EV-444CA37AE04D85CF from SC-P0-020B_TSMC_2025_Annual_Report.pdf [source F018b; SHA 3fb7ae4ad972aa2bc6e45bb36635152ad89d52f4a7165f389bcb94eeb54a6abd; PDF p.53, TSMC 3DFabric / CoWoS-L]: CoWoS®-L advanced packaging service enables larger HPC products by combining Chip on Wafer on Substrate with RDL-based interposer, higher density embedded local silicon interconnect (LSI), eDTC, and the integration of diverse embedded chips. | SC-EV-E2297FB1F53EF6D7 from SC-P0-020A_TSMC_2024_Business_Overview.pdf [source F018; SHA 911b414a2af8f41b91b3a3e3afbccd300582d380748959541b7c60ff68e5bb92; PDF p.9, Technology Leadership / advanced packaging]: CoWoS®-L technology, combining Chip on Wafer on Substrate with RDL-based interposer and embedded local silicon interconnect (LSI), started volume production in 2024. Boundary: CoWoS-L → CoWoS (part_of): TSMC identifies CoWoS-L as a branded CoWoS branch, distinct from S and R; scope the family edge to TSMC. All source excerpts remain UNAUTHORIZED_CANDIDATE evidence.
- temporal scope assessed: categorical_source_scoped
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'same', 'object_type': 'compatible', 'scope': 'compatible', 'granularity': 'same', 'quarantine': 'clear', 'ontology': 'compatible', 'evidence_sufficiency': 'sufficient', 'temporal': 'compatible'}

**A/B RECONCILIATION**

- A_B_SUBSTANTIVE_AGREEMENT; disagreement type: none; native-operation conflict: false; target conflict: false.
- Interpretation differences: none.
- Reconciliation assessment: Both reviewers support the same frozen endpoints, relation type, source scope, and evidence. Granularity labels refer to parent-child levels versus the proposed edge; bounded evidence comments do not change the edge.
- Non-material rubric-label differences retained for audit: granularity.

**EVIDENCE SUMMARY**

- Source `F018b` (SHA-256 `3fb7ae4ad972aa2bc6e45bb36635152ad89d52f4a7165f389bcb94eeb54a6abd`), file `SC-P0-020B_TSMC_2025_Annual_Report.pdf`, p. 53, section TSMC 3DFabric / CoWoS-L; evidence `SC-EV-444CA37AE04D85CF`; as-of 2025; excerpt: “CoWoS®-L advanced packaging service enables larger HPC products by combining Chip on Wafer on Substrate with RDL-based interposer, higher density embedded local silicon interconnect (LSI), eDTC, and the integration of diverse embedded chips.”
- Source `F018` (SHA-256 `911b414a2af8f41b91b3a3e3afbccd300582d380748959541b7c60ff68e5bb92`), file `SC-P0-020A_TSMC_2024_Business_Overview.pdf`, p. 9, section Technology Leadership / advanced packaging; evidence `SC-EV-E2297FB1F53EF6D7`; as-of 2024; excerpt: “CoWoS®-L technology, combining Chip on Wafer on Substrate with RDL-based interposer and embedded local silicon interconnect (LSI), started volume production in 2024.”
- Temporal scope: categorical_source_scoped.

- SYSTEM_RECOMMENDED_DECISION: `CREATE_RELATION`.
- SYSTEM_RECOMMENDATION_REASON: A/B substantive consensus; frozen automated outcome: CREATE_RELATION.
- HUMAN_USER_DECISION = PENDING
- VALID NATIVE OPTIONS: REUSE_RELATION, CREATE_RELATION, KEEP_DOMAIN_SPECIFIC_RELATION, DEFER_RELATION, REJECT_RELATION; REUSE requires an explicit validated target ID and all options remain subject to frozen controls.

### Item 068 — SC-RL-0022 — CoWoS-S → Silicon Interposer

- ITEM_NUMBER: 68; ITEM_ID: `SC-RL-0022`; OBJECT_TYPE: relation.
- DOMAIN / context: `semiconductor` Semiconductor structured Foundation candidate against shared AI Hardware canonical catalog; cross-domain status: `candidate`.
- AUTOMATED_STAGE3_OUTCOME: `CREATE_RELATION`; CURRENT_CANONICAL_TARGET: `none`.
- Possible existing canonical IDs (unresolved unless explicitly reused): `none`.
- CANDIDATE_SUMMARY: CoWoS-S → Silicon Interposer; candidate type `uses`; comparison scope `TSMC 2025 annual report / CoWoS-S architecture`; frozen candidate rationale: Source原文直接支持有界命题；仅供local review，不表示授权。
- WHY_HUMAN_REQUIRED: frozen Stage 3 mandatory review population; automated reasons: DISTINCT_RELATION_PROPOSAL, LOW_OR_UNKNOWN_CONFIDENCE.
- RISK_FLAGS: A=DISTINCT_RELATION_PROPOSAL, LOW_OR_UNKNOWN_CONFIDENCE; B=FROZEN_STAGE2_DECISION.

**AI REVIEW A**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `CREATE_RELATION`; target: `{'from_node_id': 'NODE_3E0E5604C3F64891', 'to_node_id': 'NODE_20260817_3A173B33', 'from_ref': 'NODE_3E0E5604C3F64891', 'to_ref': 'NODE_20260817_3A173B33', 'relation_type': 'uses', 'existing_relation_ids': []}`; confidence: HIGH; materiality: MEDIUM.
- reason: CoWoS-S uses a Silicon Interposer in TSMC's described architecture; preserve the historical vendor scope.
- evidence assessment: The TSMC wording directly expands S as silicon interposer and describes its routing density.
- temporal scope assessed: {'source_scope': 'TSMC 2025 annual report / CoWoS-S architecture', 'temporal_status': 'historical_vendor_architecture', 'runtime_status': 'categorical', 'valid_from': '', 'valid_to': '', 'source_as_of': ['2025']}
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'same', 'object_type': 'compatible', 'scope': 'compatible', 'granularity': 'unknown', 'quarantine': 'clear', 'ontology': 'compatible', 'evidence_sufficiency': 'sufficient', 'temporal': 'compatible'}

**AI REVIEW B**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `CREATE_RELATION`; target: `none`; confidence: MEDIUM; materiality: LOW.
- reason: CoWoS-S → Silicon Interposer (uses): TSMC expands CoWoS-S as a silicon-interposer architecture; this describes the vendor variant, not every CoWoS.
- evidence assessment: SC-EV-A5D5D8057F31DBE3 from SC-P0-020B_TSMC_2025_Annual_Report.pdf [source F018b; SHA 3fb7ae4ad972aa2bc6e45bb36635152ad89d52f4a7165f389bcb94eeb54a6abd; PDF p.53, TSMC 3DFabric / CoWoS-S]: CoWoS® with silicon interposer (CoWoS®-S) advanced packaging service features high interconnect routing density and embedded deep trench capacitor (eDTC) and has been in volume production for several years. Boundary: CoWoS-S → Silicon Interposer (uses): TSMC expands CoWoS-S as a silicon-interposer architecture; this describes the vendor variant, not every CoWoS. All source excerpts remain UNAUTHORIZED_CANDIDATE evidence.
- temporal scope assessed: historical_vendor_architecture
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'same', 'object_type': 'compatible', 'scope': 'compatible', 'granularity': 'same', 'quarantine': 'clear', 'ontology': 'compatible', 'evidence_sufficiency': 'sufficient', 'temporal': 'compatible'}

**A/B RECONCILIATION**

- A_B_SUBSTANTIVE_AGREEMENT; disagreement type: none; native-operation conflict: false; target conflict: false.
- Interpretation differences: none.
- Reconciliation assessment: Both reviewers support the same frozen endpoints, relation type, source scope, and evidence. Granularity labels refer to parent-child levels versus the proposed edge; bounded evidence comments do not change the edge.
- Non-material rubric-label differences retained for audit: granularity.

**EVIDENCE SUMMARY**

- Source `F018b` (SHA-256 `3fb7ae4ad972aa2bc6e45bb36635152ad89d52f4a7165f389bcb94eeb54a6abd`), file `SC-P0-020B_TSMC_2025_Annual_Report.pdf`, p. 53, section TSMC 3DFabric / CoWoS-S; evidence `SC-EV-A5D5D8057F31DBE3`; as-of 2025; excerpt: “CoWoS® with silicon interposer (CoWoS®-S) advanced packaging service features high interconnect routing density and embedded deep trench capacitor (eDTC) and has been in volume production for several years.”
- Temporal scope: historical_vendor_architecture.

- SYSTEM_RECOMMENDED_DECISION: `CREATE_RELATION`.
- SYSTEM_RECOMMENDATION_REASON: A/B substantive consensus; frozen automated outcome: CREATE_RELATION.
- HUMAN_USER_DECISION = PENDING
- VALID NATIVE OPTIONS: REUSE_RELATION, CREATE_RELATION, KEEP_DOMAIN_SPECIFIC_RELATION, DEFER_RELATION, REJECT_RELATION; REUSE requires an explicit validated target ID and all options remain subject to frozen controls.

### Item 069 — SC-RL-0023 — CoWoS-R → RDL Interposer

- ITEM_NUMBER: 69; ITEM_ID: `SC-RL-0023`; OBJECT_TYPE: relation.
- DOMAIN / context: `semiconductor` Semiconductor structured Foundation candidate against shared AI Hardware canonical catalog; cross-domain status: `candidate`.
- AUTOMATED_STAGE3_OUTCOME: `CREATE_RELATION`; CURRENT_CANONICAL_TARGET: `none`.
- Possible existing canonical IDs (unresolved unless explicitly reused): `none`.
- CANDIDATE_SUMMARY: CoWoS-R → RDL Interposer; candidate type `uses`; comparison scope `TSMC 2025 annual report / CoWoS-R architecture`; frozen candidate rationale: Source原文直接支持有界命题；仅供local review，不表示授权。
- WHY_HUMAN_REQUIRED: frozen Stage 3 mandatory review population; automated reasons: DISTINCT_RELATION_PROPOSAL, LOW_OR_UNKNOWN_CONFIDENCE.
- RISK_FLAGS: A=DISTINCT_RELATION_PROPOSAL, LOW_OR_UNKNOWN_CONFIDENCE; B=none.

**AI REVIEW A**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `CREATE_RELATION`; target: `{'from_node_id': 'NODE_B7B4CB43F4C30F10', 'to_node_id': 'NODE_20260817_4AA22685', 'from_ref': 'NODE_B7B4CB43F4C30F10', 'to_ref': 'NODE_20260817_4AA22685', 'relation_type': 'uses', 'existing_relation_ids': []}`; confidence: HIGH; materiality: MEDIUM.
- reason: CoWoS-R uses an RDL Interposer in TSMC's described architecture, not every CoWoS variant.
- evidence assessment: TSMC writes redistribution-layer interposer in the CoWoS-R service name and description.
- temporal scope assessed: {'source_scope': 'TSMC 2025 annual report / CoWoS-R architecture', 'temporal_status': 'historical_vendor_architecture', 'runtime_status': 'categorical', 'valid_from': '', 'valid_to': '', 'source_as_of': ['2025']}
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'same', 'object_type': 'compatible', 'scope': 'compatible', 'granularity': 'unknown', 'quarantine': 'clear', 'ontology': 'compatible', 'evidence_sufficiency': 'sufficient', 'temporal': 'compatible'}

**AI REVIEW B**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `CREATE_RELATION`; target: `none`; confidence: HIGH; materiality: LOW.
- reason: CoWoS-R → RDL Interposer (uses): TSMC expands CoWoS-R as a redistribution-layer interposer architecture; limit uses to that variant.
- evidence assessment: SC-EV-BE1EFC0405668731 from SC-P0-020B_TSMC_2025_Annual_Report.pdf [source F018b; SHA 3fb7ae4ad972aa2bc6e45bb36635152ad89d52f4a7165f389bcb94eeb54a6abd; PDF p.53, TSMC 3DFabric / CoWoS-R]: CoWoS® with redistribution layer interposer (CoWoS®-R) advanced packaging service, featuring multiple redistribution layers (RDL) to enable product design simplicity, supports larger HPC products. This technology entered its third year of volume production in 2025. Boundary: CoWoS-R → RDL Interposer (uses): TSMC expands CoWoS-R as a redistribution-layer interposer architecture; limit uses to that variant. All source excerpts remain UNAUTHORIZED_CANDIDATE evidence.
- temporal scope assessed: historical_vendor_architecture
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'same', 'object_type': 'compatible', 'scope': 'compatible', 'granularity': 'same', 'quarantine': 'clear', 'ontology': 'compatible', 'evidence_sufficiency': 'sufficient', 'temporal': 'compatible'}

**A/B RECONCILIATION**

- A_B_SUBSTANTIVE_AGREEMENT; disagreement type: none; native-operation conflict: false; target conflict: false.
- Interpretation differences: none.
- Reconciliation assessment: Both reviewers support the same frozen endpoints, relation type, source scope, and evidence. Granularity labels refer to parent-child levels versus the proposed edge; bounded evidence comments do not change the edge.
- Non-material rubric-label differences retained for audit: granularity.

**EVIDENCE SUMMARY**

- Source `F018b` (SHA-256 `3fb7ae4ad972aa2bc6e45bb36635152ad89d52f4a7165f389bcb94eeb54a6abd`), file `SC-P0-020B_TSMC_2025_Annual_Report.pdf`, p. 53, section TSMC 3DFabric / CoWoS-R; evidence `SC-EV-BE1EFC0405668731`; as-of 2025; excerpt: “CoWoS® with redistribution layer interposer (CoWoS®-R) advanced packaging service, featuring multiple redistribution layers (RDL) to enable product design simplicity, supports larger HPC products. This technology entered its third year of volume production in 2025.”
- Temporal scope: historical_vendor_architecture.

- SYSTEM_RECOMMENDED_DECISION: `CREATE_RELATION`.
- SYSTEM_RECOMMENDATION_REASON: A/B substantive consensus; frozen automated outcome: CREATE_RELATION.
- HUMAN_USER_DECISION = PENDING
- VALID NATIVE OPTIONS: REUSE_RELATION, CREATE_RELATION, KEEP_DOMAIN_SPECIFIC_RELATION, DEFER_RELATION, REJECT_RELATION; REUSE requires an explicit validated target ID and all options remain subject to frozen controls.

### Item 070 — SC-RL-0024 — CoWoS-L → RDL Interposer

- ITEM_NUMBER: 70; ITEM_ID: `SC-RL-0024`; OBJECT_TYPE: relation.
- DOMAIN / context: `semiconductor` Semiconductor structured Foundation candidate against shared AI Hardware canonical catalog; cross-domain status: `candidate`.
- AUTOMATED_STAGE3_OUTCOME: `CREATE_RELATION`; CURRENT_CANONICAL_TARGET: `none`.
- Possible existing canonical IDs (unresolved unless explicitly reused): `none`.
- CANDIDATE_SUMMARY: CoWoS-L → RDL Interposer; candidate type `uses`; comparison scope `TSMC 2025 annual report / CoWoS-L architecture`; frozen candidate rationale: Source原文直接支持有界命题；仅供local review，不表示授权。
- WHY_HUMAN_REQUIRED: frozen Stage 3 mandatory review population; automated reasons: DISTINCT_RELATION_PROPOSAL, LOW_OR_UNKNOWN_CONFIDENCE.
- RISK_FLAGS: A=DISTINCT_RELATION_PROPOSAL, LOW_OR_UNKNOWN_CONFIDENCE; B=none.

**AI REVIEW A**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `CREATE_RELATION`; target: `{'from_node_id': 'NODE_1A7F2D5816F5B7EE', 'to_node_id': 'NODE_20260817_4AA22685', 'from_ref': 'NODE_1A7F2D5816F5B7EE', 'to_ref': 'NODE_20260817_4AA22685', 'relation_type': 'uses', 'existing_relation_ids': []}`; confidence: HIGH; materiality: MEDIUM.
- reason: CoWoS-L uses an RDL-based interposer while also including LSI; the edge is variant-specific.
- evidence assessment: TSMC explicitly says its L service combines CoWoS with an RDL-based interposer.
- temporal scope assessed: {'source_scope': 'TSMC 2025 annual report / CoWoS-L architecture', 'temporal_status': 'historical_vendor_architecture', 'runtime_status': 'categorical', 'valid_from': '', 'valid_to': '', 'source_as_of': ['2025']}
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'same', 'object_type': 'compatible', 'scope': 'compatible', 'granularity': 'unknown', 'quarantine': 'clear', 'ontology': 'compatible', 'evidence_sufficiency': 'sufficient', 'temporal': 'compatible'}

**AI REVIEW B**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `CREATE_RELATION`; target: `none`; confidence: HIGH; materiality: LOW.
- reason: CoWoS-L → RDL Interposer (uses): TSMC says CoWoS-L combines an RDL-based interposer with local silicon interconnect; the RDL uses edge is variant-specific.
- evidence assessment: SC-EV-444CA37AE04D85CF from SC-P0-020B_TSMC_2025_Annual_Report.pdf [source F018b; SHA 3fb7ae4ad972aa2bc6e45bb36635152ad89d52f4a7165f389bcb94eeb54a6abd; PDF p.53, TSMC 3DFabric / CoWoS-L]: CoWoS®-L advanced packaging service enables larger HPC products by combining Chip on Wafer on Substrate with RDL-based interposer, higher density embedded local silicon interconnect (LSI), eDTC, and the integration of diverse embedded chips. Boundary: CoWoS-L → RDL Interposer (uses): TSMC says CoWoS-L combines an RDL-based interposer with local silicon interconnect; the RDL uses edge is variant-specific. All source excerpts remain UNAUTHORIZED_CANDIDATE evidence.
- temporal scope assessed: historical_vendor_architecture
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'same', 'object_type': 'compatible', 'scope': 'compatible', 'granularity': 'same', 'quarantine': 'clear', 'ontology': 'compatible', 'evidence_sufficiency': 'sufficient', 'temporal': 'compatible'}

**A/B RECONCILIATION**

- A_B_SUBSTANTIVE_AGREEMENT; disagreement type: none; native-operation conflict: false; target conflict: false.
- Interpretation differences: none.
- Reconciliation assessment: Both reviewers support the same frozen endpoints, relation type, source scope, and evidence. Granularity labels refer to parent-child levels versus the proposed edge; bounded evidence comments do not change the edge.
- Non-material rubric-label differences retained for audit: granularity.

**EVIDENCE SUMMARY**

- Source `F018b` (SHA-256 `3fb7ae4ad972aa2bc6e45bb36635152ad89d52f4a7165f389bcb94eeb54a6abd`), file `SC-P0-020B_TSMC_2025_Annual_Report.pdf`, p. 53, section TSMC 3DFabric / CoWoS-L; evidence `SC-EV-444CA37AE04D85CF`; as-of 2025; excerpt: “CoWoS®-L advanced packaging service enables larger HPC products by combining Chip on Wafer on Substrate with RDL-based interposer, higher density embedded local silicon interconnect (LSI), eDTC, and the integration of diverse embedded chips.”
- Temporal scope: historical_vendor_architecture.

- SYSTEM_RECOMMENDED_DECISION: `CREATE_RELATION`.
- SYSTEM_RECOMMENDATION_REASON: A/B substantive consensus; frozen automated outcome: CREATE_RELATION.
- HUMAN_USER_DECISION = PENDING
- VALID NATIVE OPTIONS: REUSE_RELATION, CREATE_RELATION, KEEP_DOMAIN_SPECIFIC_RELATION, DEFER_RELATION, REJECT_RELATION; REUSE requires an explicit validated target ID and all options remain subject to frozen controls.

### Item 071 — SC-RL-0025 — CoWoS → High Bandwidth Memory

- ITEM_NUMBER: 71; ITEM_ID: `SC-RL-0025`; OBJECT_TYPE: relation.
- DOMAIN / context: `semiconductor` Semiconductor structured Foundation candidate against shared AI Hardware canonical catalog; cross-domain status: `candidate`.
- AUTOMATED_STAGE3_OUTCOME: `CREATE_RELATION`; CURRENT_CANONICAL_TARGET: `none`.
- Possible existing canonical IDs (unresolved unless explicitly reused): `none`.
- CANDIDATE_SUMMARY: CoWoS → High Bandwidth Memory; candidate type `uses`; comparison scope `TSMC 2025 described HPC CoWoS service; not every generic package`; frozen candidate rationale: Source原文直接支持有界命题；仅供local review，不表示授权。
- WHY_HUMAN_REQUIRED: frozen Stage 3 mandatory review population; automated reasons: DISTINCT_RELATION_PROPOSAL, LOW_OR_UNKNOWN_CONFIDENCE.
- RISK_FLAGS: A=DISTINCT_RELATION_PROPOSAL, LOW_OR_UNKNOWN_CONFIDENCE; B=SCOPE_LIMIT.

**AI REVIEW A**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `CREATE_RELATION`; target: `{'from_node_id': 'NODE_20260814_9B66BB15', 'to_node_id': 'NODE_20260817_6A9A657D', 'from_ref': 'NODE_20260814_9B66BB15', 'to_ref': 'NODE_20260817_6A9A657D', 'relation_type': 'uses', 'existing_relation_ids': []}`; confidence: MEDIUM; materiality: HIGH.
- reason: CoWoS uses HBM only in the cited HPC service configuration; avoid a universal packaging claim.
- evidence assessment: TSMC says its CoWoS HPC service integrates SoC chips and HBM stacks, giving direct but scoped support.
- temporal scope assessed: {'source_scope': 'TSMC 2025 described HPC CoWoS service; not every generic package', 'temporal_status': 'historical_vendor_architecture', 'runtime_status': 'categorical', 'valid_from': '', 'valid_to': '', 'source_as_of': ['2025']}
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'same', 'object_type': 'compatible', 'scope': 'compatible', 'granularity': 'unknown', 'quarantine': 'clear', 'ontology': 'compatible', 'evidence_sufficiency': 'sufficient', 'temporal': 'compatible'}

**AI REVIEW B**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `CREATE_RELATION`; target: `none`; confidence: MEDIUM; materiality: LOW.
- reason: CoWoS → High Bandwidth Memory (uses): TSMC says its HPC CoWoS service integrates HBM stacks; this is not a property of every generic package.
- evidence assessment: SC-EV-BA8E4B43B6360938 from SC-P0-020B_TSMC_2025_Annual_Report.pdf [source F018b; SHA 3fb7ae4ad972aa2bc6e45bb36635152ad89d52f4a7165f389bcb94eeb54a6abd; PDF p.53, TSMC 3DFabric / CoWoS]: CoWoS® advanced packaging service integrates multiple system-on-chip (SoC) chips and the high-bandwidth memory (HBM) stacks to enhance HPC products with superior compute power and memory bandwidth. Boundary: CoWoS → High Bandwidth Memory (uses): TSMC says its HPC CoWoS service integrates HBM stacks; this is not a property of every generic package. All source excerpts remain UNAUTHORIZED_CANDIDATE evidence.
- temporal scope assessed: historical_vendor_architecture
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'same', 'object_type': 'compatible', 'scope': 'compatible', 'granularity': 'same', 'quarantine': 'clear', 'ontology': 'compatible', 'evidence_sufficiency': 'sufficient', 'temporal': 'compatible'}

**A/B RECONCILIATION**

- A_B_SUBSTANTIVE_AGREEMENT; disagreement type: none; native-operation conflict: false; target conflict: false.
- Interpretation differences: none.
- Reconciliation assessment: Both reviewers support the same frozen endpoints, relation type, source scope, and evidence. Granularity labels refer to parent-child levels versus the proposed edge; bounded evidence comments do not change the edge.
- Non-material rubric-label differences retained for audit: granularity.

**EVIDENCE SUMMARY**

- Source `F018b` (SHA-256 `3fb7ae4ad972aa2bc6e45bb36635152ad89d52f4a7165f389bcb94eeb54a6abd`), file `SC-P0-020B_TSMC_2025_Annual_Report.pdf`, p. 53, section TSMC 3DFabric / CoWoS; evidence `SC-EV-BA8E4B43B6360938`; as-of 2025; excerpt: “CoWoS® advanced packaging service integrates multiple system-on-chip (SoC) chips and the high-bandwidth memory (HBM) stacks to enhance HPC products with superior compute power and memory bandwidth.”
- Temporal scope: historical_vendor_architecture.

- SYSTEM_RECOMMENDED_DECISION: `CREATE_RELATION`.
- SYSTEM_RECOMMENDATION_REASON: A/B substantive consensus; frozen automated outcome: CREATE_RELATION.
- HUMAN_USER_DECISION = PENDING
- VALID NATIVE OPTIONS: REUSE_RELATION, CREATE_RELATION, KEEP_DOMAIN_SPECIFIC_RELATION, DEFER_RELATION, REJECT_RELATION; REUSE requires an explicit validated target ID and all options remain subject to frozen controls.

### Item 072 — SC-RL-0026 — High Bandwidth Memory → Through-Silicon Via

- ITEM_NUMBER: 72; ITEM_ID: `SC-RL-0026`; OBJECT_TYPE: relation.
- DOMAIN / context: `semiconductor` Semiconductor structured Foundation candidate against shared AI Hardware canonical catalog; cross-domain status: `candidate`.
- AUTOMATED_STAGE3_OUTCOME: `CREATE_RELATION`; CURRENT_CANONICAL_TARGET: `none`.
- Possible existing canonical IDs (unresolved unless explicitly reused): `none`.
- CANDIDATE_SUMMARY: High Bandwidth Memory → Through-Silicon Via; candidate type `uses`; comparison scope `IRDS Packaging 2020 described HBM stack architecture; not future HBM variants`; frozen candidate rationale: Source原文直接支持有界命题；仅供local review，不表示授权。
- WHY_HUMAN_REQUIRED: frozen Stage 3 mandatory review population; automated reasons: DISTINCT_RELATION_PROPOSAL, LOW_OR_UNKNOWN_CONFIDENCE.
- RISK_FLAGS: A=DISTINCT_RELATION_PROPOSAL, LOW_OR_UNKNOWN_CONFIDENCE; B=SCOPE_LIMIT.

**AI REVIEW A**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `CREATE_RELATION`; target: `{'from_node_id': 'NODE_20260817_6A9A657D', 'to_node_id': 'NODE_20260817_6EA7B10F', 'from_ref': 'NODE_20260817_6A9A657D', 'to_ref': 'NODE_20260817_6EA7B10F', 'relation_type': 'uses', 'existing_relation_ids': []}`; confidence: MEDIUM; materiality: MEDIUM.
- reason: The cited HBM stack architecture uses TSV arrays for die-to-die transfer; future variants are outside scope.
- evidence assessment: IRDS describes TSVs available between a controller and stacked DRAM dies in HBM.
- temporal scope assessed: {'source_scope': 'IRDS Packaging 2020 described HBM stack architecture; not future HBM variants', 'temporal_status': 'historical_source_architecture', 'runtime_status': 'categorical', 'valid_from': '', 'valid_to': '', 'source_as_of': ['2020']}
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'same', 'object_type': 'compatible', 'scope': 'compatible', 'granularity': 'unknown', 'quarantine': 'clear', 'ontology': 'compatible', 'evidence_sufficiency': 'sufficient', 'temporal': 'compatible'}

**AI REVIEW B**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `CREATE_RELATION`; target: `none`; confidence: MEDIUM; materiality: LOW.
- reason: High Bandwidth Memory → Through-Silicon Via (uses): IRDS describes TSV arrays moving data between die in HBM stacks; scope uses to the described stack architecture.
- evidence assessment: SC-EV-B87D40867DB6A731 from SC-P0-017_2020_IRDS_Packaging_Integration.pdf [source SC-PHYS-54CABB8879E180A7; SHA 54cabb8879e180a7a0363e8964cb2d28735eff03ecee6a45905cd54f06eae5e2; PDF p.16, 3D Stacks / HBM]: Because of the large array of TSVs available in HBM stacks to transfer data between individual die (e.g., a controller at the base topped by 4-8 DRAM die) Boundary: High Bandwidth Memory → Through-Silicon Via (uses): IRDS describes TSV arrays moving data between die in HBM stacks; scope uses to the described stack architecture. All source excerpts remain UNAUTHORIZED_CANDIDATE evidence.
- temporal scope assessed: historical_source_architecture
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'same', 'object_type': 'compatible', 'scope': 'compatible', 'granularity': 'same', 'quarantine': 'clear', 'ontology': 'compatible', 'evidence_sufficiency': 'sufficient', 'temporal': 'compatible'}

**A/B RECONCILIATION**

- A_B_SUBSTANTIVE_AGREEMENT; disagreement type: none; native-operation conflict: false; target conflict: false.
- Interpretation differences: none.
- Reconciliation assessment: Both reviewers support the same frozen endpoints, relation type, source scope, and evidence. Granularity labels refer to parent-child levels versus the proposed edge; bounded evidence comments do not change the edge.
- Non-material rubric-label differences retained for audit: granularity.

**EVIDENCE SUMMARY**

- Source `SC-PHYS-54CABB8879E180A7` (SHA-256 `54cabb8879e180a7a0363e8964cb2d28735eff03ecee6a45905cd54f06eae5e2`), file `SC-P0-017_2020_IRDS_Packaging_Integration.pdf`, p. 16, section 3D Stacks / HBM; evidence `SC-EV-B87D40867DB6A731`; as-of 2020; excerpt: “Because of the large array of TSVs available in HBM stacks to transfer data between individual die (e.g., a controller at the base topped by 4-8 DRAM die)”
- Temporal scope: historical_source_architecture.

- SYSTEM_RECOMMENDED_DECISION: `CREATE_RELATION`.
- SYSTEM_RECOMMENDATION_REASON: A/B substantive consensus; frozen automated outcome: CREATE_RELATION.
- HUMAN_USER_DECISION = PENDING
- VALID NATIVE OPTIONS: REUSE_RELATION, CREATE_RELATION, KEEP_DOMAIN_SPECIFIC_RELATION, DEFER_RELATION, REJECT_RELATION; REUSE requires an explicit validated target ID and all options remain subject to frozen controls.

### Item 073 — SC-RL-0027 — Czochralski Crystal Growth → Polysilicon

- ITEM_NUMBER: 73; ITEM_ID: `SC-RL-0027`; OBJECT_TYPE: relation.
- DOMAIN / context: `semiconductor` Semiconductor structured Foundation candidate against shared AI Hardware canonical catalog; cross-domain status: `candidate`.
- AUTOMATED_STAGE3_OUTCOME: `CREATE_RELATION`; CURRENT_CANONICAL_TARGET: `none`.
- Possible existing canonical IDs (unresolved unless explicitly reused): `none`.
- CANDIDATE_SUMMARY: Czochralski Crystal Growth → Polysilicon; candidate type `uses`; comparison scope `SUMCO monocrystalline pulling / CZ process; undated`; frozen candidate rationale: Source原文直接支持有界命题；仅供local review，不表示授权。
- WHY_HUMAN_REQUIRED: frozen Stage 3 mandatory review population; automated reasons: DISTINCT_RELATION_PROPOSAL, LOW_OR_UNKNOWN_CONFIDENCE.
- RISK_FLAGS: A=DISTINCT_RELATION_PROPOSAL, LOW_OR_UNKNOWN_CONFIDENCE; B=none.

**AI REVIEW A**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `CREATE_RELATION`; target: `{'from_node_id': 'NODE_E06758E691974EB4', 'to_node_id': 'NODE_0767AE187754B8E1', 'from_ref': 'SC-CN-0034', 'to_ref': 'SC-CN-0024', 'relation_type': 'uses', 'existing_relation_ids': []}`; confidence: MEDIUM; materiality: MEDIUM.
- reason: Czochralski Crystal Growth uses Polysilicon feedstock in SUMCO's silicon-ingot process.
- evidence assessment: SUMCO states high-quality polysilicon is the raw material for monocrystalline ingots.
- temporal scope assessed: {'source_scope': 'SUMCO monocrystalline pulling / CZ process; undated', 'temporal_status': 'categorical_source_scoped', 'runtime_status': 'categorical', 'valid_from': '', 'valid_to': '', 'source_as_of': [None]}
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'same', 'object_type': 'compatible', 'scope': 'compatible', 'granularity': 'unknown', 'quarantine': 'clear', 'ontology': 'compatible', 'evidence_sufficiency': 'sufficient', 'temporal': 'compatible'}

**AI REVIEW B**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `CREATE_RELATION`; target: `none`; confidence: HIGH; materiality: LOW.
- reason: Czochralski Crystal Growth → Polysilicon (uses): SUMCO identifies polysilicon as raw material for monocrystalline ingots; avoid generalizing every CZ recipe.
- evidence assessment: SC-EV-3BE221EFD700F965 from SC-P0-006_SUMCO_Silicon_Wafer_Production_Processes.pdf [source SC-PHYS-9E9CEFC24043585C; SHA 9e9cefc24043585c1c5a484340dcf49aa0725b341467942d3d4c34be0da8aee6; PDF p.2, Monocrystalline pulling process]: The monocrystalline ingots that make up the silicon wafer are manufactured using high-quality polysilicon as the raw material. | SC-EV-C7BD218505458FDB from SC-P0-006_SUMCO_Silicon_Wafer_Production_Processes.pdf [source SC-PHYS-9E9CEFC24043585C; SHA 9e9cefc24043585c1c5a484340dcf49aa0725b341467942d3d4c34be0da8aee6; PDF p.2, Monocrystalline pulling process / Flow of CZ process]: The monocrystalline silicon ingots from which silicon wafers are created are manufactured by a technique called the CZ (Czochralski) crystal growth process. Boundary: Czochralski Crystal Growth → Polysilicon (uses): SUMCO identifies polysilicon as raw material for monocrystalline ingots; avoid generalizing every CZ recipe. All source excerpts remain UNAUTHORIZED_CANDIDATE evidence.
- temporal scope assessed: categorical_source_scoped
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'same', 'object_type': 'compatible', 'scope': 'compatible', 'granularity': 'same', 'quarantine': 'clear', 'ontology': 'compatible', 'evidence_sufficiency': 'sufficient', 'temporal': 'compatible'}

**A/B RECONCILIATION**

- A_B_SUBSTANTIVE_AGREEMENT; disagreement type: none; native-operation conflict: false; target conflict: false.
- Interpretation differences: none.
- Reconciliation assessment: Both reviewers support the same frozen endpoints, relation type, source scope, and evidence. Granularity labels refer to parent-child levels versus the proposed edge; bounded evidence comments do not change the edge.
- Non-material rubric-label differences retained for audit: granularity.

**EVIDENCE SUMMARY**

- Source `SC-PHYS-9E9CEFC24043585C` (SHA-256 `9e9cefc24043585c1c5a484340dcf49aa0725b341467942d3d4c34be0da8aee6`), file `SC-P0-006_SUMCO_Silicon_Wafer_Production_Processes.pdf`, p. 2, section Monocrystalline pulling process; evidence `SC-EV-3BE221EFD700F965`; as-of unknown; excerpt: “The monocrystalline ingots that make up the silicon wafer are manufactured using high-quality polysilicon as the raw material.”
- Source `SC-PHYS-9E9CEFC24043585C` (SHA-256 `9e9cefc24043585c1c5a484340dcf49aa0725b341467942d3d4c34be0da8aee6`), file `SC-P0-006_SUMCO_Silicon_Wafer_Production_Processes.pdf`, p. 2, section Monocrystalline pulling process / Flow of CZ process; evidence `SC-EV-C7BD218505458FDB`; as-of unknown; excerpt: “The monocrystalline silicon ingots from which silicon wafers are created are manufactured by a technique called the CZ (Czochralski) crystal growth process.”
- Temporal scope: categorical_source_scoped.

- SYSTEM_RECOMMENDED_DECISION: `CREATE_RELATION`.
- SYSTEM_RECOMMENDATION_REASON: A/B substantive consensus; frozen automated outcome: CREATE_RELATION.
- HUMAN_USER_DECISION = PENDING
- VALID NATIVE OPTIONS: REUSE_RELATION, CREATE_RELATION, KEEP_DOMAIN_SPECIFIC_RELATION, DEFER_RELATION, REJECT_RELATION; REUSE requires an explicit validated target ID and all options remain subject to frozen controls.

### Item 074 — SC-RL-0028 — Czochralski Crystal Growth → Quartz Crucible

- ITEM_NUMBER: 74; ITEM_ID: `SC-RL-0028`; OBJECT_TYPE: relation.
- DOMAIN / context: `semiconductor` Semiconductor structured Foundation candidate against shared AI Hardware canonical catalog; cross-domain status: `candidate`.
- AUTOMATED_STAGE3_OUTCOME: `DEFER_RELATION`; CURRENT_CANONICAL_TARGET: `none`.
- Possible existing canonical IDs (unresolved unless explicitly reused): `none`.
- CANDIDATE_SUMMARY: Czochralski Crystal Growth → Quartz Crucible; candidate type `uses`; comparison scope `SUMCO CZ process; undated`; frozen candidate rationale: 一个或两个端点尚未通过身份候选准入；证据保留，不提前授权端点。
- WHY_HUMAN_REQUIRED: frozen Stage 3 mandatory review population; automated reasons: EVIDENCE_WARNING, FROZEN_STAGE2_HUMAN_DECISION, LOW_OR_UNKNOWN_CONFIDENCE, RELATION_AMBIGUITY.
- RISK_FLAGS: A=EVIDENCE_WARNING, FROZEN_STAGE2_HUMAN_DECISION, LOW_OR_UNKNOWN_CONFIDENCE, RELATION_AMBIGUITY; B=FROZEN_STAGE2_DECISION, UNRESOLVED_RELATION, ENDPOINT_OR_RECONCILIATION.

**AI REVIEW A**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `DEFER_RELATION`; target: `{'from_node_id': 'NODE_E06758E691974EB4', 'to_node_id': None, 'from_ref': 'SC-CN-0034', 'to_ref': 'SC-CN-0037', 'relation_type': 'uses', 'existing_relation_ids': []}`; confidence: HIGH; materiality: MEDIUM.
- reason: The quartz-crucible use is directly described, but the Quartz Crucible endpoint remains unadmitted under Stage 2 DEFER.
- evidence assessment: SUMCO says purified polysilicon and dopants are placed in a quartz crucible and melted; the equipment/material boundary still needs approval.
- temporal scope assessed: {'source_scope': 'SUMCO CZ process; undated', 'temporal_status': 'categorical_source_scoped', 'runtime_status': 'categorical', 'valid_from': '', 'valid_to': '', 'source_as_of': [None]}
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'ambiguous', 'object_type': 'unknown', 'scope': 'unknown', 'granularity': 'unknown', 'quarantine': 'clear', 'ontology': 'compatible', 'evidence_sufficiency': 'sufficient', 'temporal': 'compatible'}

**AI REVIEW B**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `DEFER_RELATION`; target: `none`; confidence: MEDIUM; materiality: HIGH.
- reason: Czochralski Crystal Growth → Quartz Crucible (uses): SUMCO mentions a quartz crucible, but Stage 2 deferred this process relation; preserve boundary review.
- evidence assessment: SC-EV-1811D226786D163F from SC-P0-006_SUMCO_Silicon_Wafer_Production_Processes.pdf [source SC-PHYS-9E9CEFC24043585C; SHA 9e9cefc24043585c1c5a484340dcf49aa0725b341467942d3d4c34be0da8aee6; PDF p.2, Flow of CZ process]: Polysilicon purified until the metal impurities are no more than a few parts per billion (ppb) is put into a quartz crucible along with boron (B) and phosphorous (P), and melted at a temperature of around 1420℃. Boundary: Czochralski Crystal Growth → Quartz Crucible (uses): SUMCO mentions a quartz crucible, but Stage 2 deferred this process relation; preserve boundary review. All source excerpts remain UNAUTHORIZED_CANDIDATE evidence.
- temporal scope assessed: categorical_source_scoped
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'ambiguous', 'object_type': 'unknown', 'scope': 'unknown', 'granularity': 'unknown', 'quarantine': 'preserved', 'ontology': 'unresolved', 'evidence_sufficiency': 'limited', 'temporal': 'compatible'}

**A/B RECONCILIATION**

- A_B_SUBSTANTIVE_AGREEMENT; disagreement type: none; native-operation conflict: false; target conflict: false.
- Interpretation differences: none.
- Reconciliation assessment: Both reviewers hold the same endpoint, temporal, or ontology exception. Rubric labels compare concept support with authority for the relation.
- Non-material rubric-label differences retained for audit: evidence_sufficiency, ontology, quarantine.

**EVIDENCE SUMMARY**

- Source `SC-PHYS-9E9CEFC24043585C` (SHA-256 `9e9cefc24043585c1c5a484340dcf49aa0725b341467942d3d4c34be0da8aee6`), file `SC-P0-006_SUMCO_Silicon_Wafer_Production_Processes.pdf`, p. 2, section Flow of CZ process; evidence `SC-EV-1811D226786D163F`; as-of unknown; excerpt: “Polysilicon purified until the metal impurities are no more than a few parts per billion (ppb) is put into a quartz crucible along with boron (B) and phosphorous (P), and melted at a temperature of around 1420℃.”
- Temporal scope: categorical_source_scoped.

- SYSTEM_RECOMMENDED_DECISION: `DEFER_RELATION`.
- SYSTEM_RECOMMENDATION_REASON: Frozen structural, Stage 2 decision, evidence, or temporal exception remains unresolved.
- HUMAN_USER_DECISION = PENDING
- VALID NATIVE OPTIONS: REUSE_RELATION, CREATE_RELATION, KEEP_DOMAIN_SPECIFIC_RELATION, DEFER_RELATION, REJECT_RELATION; REUSE requires an explicit validated target ID and all options remain subject to frozen controls.

### Item 075 — SC-RL-0029 — Wafer Lapping → Lapping Machine

- ITEM_NUMBER: 75; ITEM_ID: `SC-RL-0029`; OBJECT_TYPE: relation.
- DOMAIN / context: `semiconductor` Semiconductor structured Foundation candidate against shared AI Hardware canonical catalog; cross-domain status: `candidate`.
- AUTOMATED_STAGE3_OUTCOME: `CREATE_RELATION`; CURRENT_CANONICAL_TARGET: `none`.
- Possible existing canonical IDs (unresolved unless explicitly reused): `none`.
- CANDIDATE_SUMMARY: Wafer Lapping → Lapping Machine; candidate type `uses`; comparison scope `SUMCO wafer forming / lapping; undated`; frozen candidate rationale: Source原文直接支持有界命题；仅供local review，不表示授权。
- WHY_HUMAN_REQUIRED: frozen Stage 3 mandatory review population; automated reasons: DISTINCT_RELATION_PROPOSAL, LOW_OR_UNKNOWN_CONFIDENCE.
- RISK_FLAGS: A=DISTINCT_RELATION_PROPOSAL, LOW_OR_UNKNOWN_CONFIDENCE; B=none.

**AI REVIEW A**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `CREATE_RELATION`; target: `{'from_node_id': 'NODE_409C34CE34598421', 'to_node_id': 'NODE_564E043C0B9D7684', 'from_ref': 'SC-CN-0039', 'to_ref': 'SC-CN-0040', 'relation_type': 'uses', 'existing_relation_ids': []}`; confidence: HIGH; materiality: MEDIUM.
- reason: Wafer Lapping uses a Lapping Machine in SUMCO's forming flow; machine and process have distinct types.
- evidence assessment: SUMCO explicitly locates alumina-abrasive wafer polishing inside a lapping machine.
- temporal scope assessed: {'source_scope': 'SUMCO wafer forming / lapping; undated', 'temporal_status': 'categorical_source_scoped', 'runtime_status': 'categorical', 'valid_from': '', 'valid_to': '', 'source_as_of': [None]}
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'same', 'object_type': 'compatible', 'scope': 'compatible', 'granularity': 'unknown', 'quarantine': 'clear', 'ontology': 'compatible', 'evidence_sufficiency': 'sufficient', 'temporal': 'compatible'}

**AI REVIEW B**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `CREATE_RELATION`; target: `none`; confidence: HIGH; materiality: LOW.
- reason: Wafer Lapping → Lapping Machine (uses): SUMCO states sliced wafers are worked in a lapping machine; process-to-equipment direction is direct.
- evidence assessment: SC-EV-59686E8EF98436C8 from SC-P0-006_SUMCO_Silicon_Wafer_Production_Processes.pdf [source SC-PHYS-9E9CEFC24043585C; SHA 9e9cefc24043585c1c5a484340dcf49aa0725b341467942d3d4c34be0da8aee6; PDF p.4, Wafer forming process / Lapping]: The sliced wafers are polished by alumina abrasive in a lapping machine to the desired thickness, while improving the surface parallelism. Boundary: Wafer Lapping → Lapping Machine (uses): SUMCO states sliced wafers are worked in a lapping machine; process-to-equipment direction is direct. All source excerpts remain UNAUTHORIZED_CANDIDATE evidence.
- temporal scope assessed: categorical_source_scoped
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'same', 'object_type': 'compatible', 'scope': 'compatible', 'granularity': 'same', 'quarantine': 'clear', 'ontology': 'compatible', 'evidence_sufficiency': 'sufficient', 'temporal': 'compatible'}

**A/B RECONCILIATION**

- A_B_SUBSTANTIVE_AGREEMENT; disagreement type: none; native-operation conflict: false; target conflict: false.
- Interpretation differences: none.
- Reconciliation assessment: Both reviewers support the same frozen endpoints, relation type, source scope, and evidence. Granularity labels refer to parent-child levels versus the proposed edge; bounded evidence comments do not change the edge.
- Non-material rubric-label differences retained for audit: granularity.

**EVIDENCE SUMMARY**

- Source `SC-PHYS-9E9CEFC24043585C` (SHA-256 `9e9cefc24043585c1c5a484340dcf49aa0725b341467942d3d4c34be0da8aee6`), file `SC-P0-006_SUMCO_Silicon_Wafer_Production_Processes.pdf`, p. 4, section Wafer forming process / Lapping; evidence `SC-EV-59686E8EF98436C8`; as-of unknown; excerpt: “The sliced wafers are polished by alumina abrasive in a lapping machine to the desired thickness, while improving the surface parallelism.”
- Temporal scope: categorical_source_scoped.

- SYSTEM_RECOMMENDED_DECISION: `CREATE_RELATION`.
- SYSTEM_RECOMMENDATION_REASON: A/B substantive consensus; frozen automated outcome: CREATE_RELATION.
- HUMAN_USER_DECISION = PENDING
- VALID NATIVE OPTIONS: REUSE_RELATION, CREATE_RELATION, KEEP_DOMAIN_SPECIFIC_RELATION, DEFER_RELATION, REJECT_RELATION; REUSE requires an explicit validated target ID and all options remain subject to frozen controls.

### Item 076 — SC-RL-0030 — Wafer Lapping → Alumina Abrasive

- ITEM_NUMBER: 76; ITEM_ID: `SC-RL-0030`; OBJECT_TYPE: relation.
- DOMAIN / context: `semiconductor` Semiconductor structured Foundation candidate against shared AI Hardware canonical catalog; cross-domain status: `candidate`.
- AUTOMATED_STAGE3_OUTCOME: `CREATE_RELATION`; CURRENT_CANONICAL_TARGET: `none`.
- Possible existing canonical IDs (unresolved unless explicitly reused): `none`.
- CANDIDATE_SUMMARY: Wafer Lapping → Alumina Abrasive; candidate type `uses`; comparison scope `SUMCO wafer forming / lapping; undated`; frozen candidate rationale: Source原文直接支持有界命题；仅供local review，不表示授权。
- WHY_HUMAN_REQUIRED: frozen Stage 3 mandatory review population; automated reasons: DISTINCT_RELATION_PROPOSAL, LOW_OR_UNKNOWN_CONFIDENCE.
- RISK_FLAGS: A=DISTINCT_RELATION_PROPOSAL, LOW_OR_UNKNOWN_CONFIDENCE; B=none.

**AI REVIEW A**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `CREATE_RELATION`; target: `{'from_node_id': 'NODE_409C34CE34598421', 'to_node_id': 'NODE_897F37EE3A740091', 'from_ref': 'SC-CN-0039', 'to_ref': 'SC-CN-0041', 'relation_type': 'uses', 'existing_relation_ids': []}`; confidence: HIGH; materiality: MEDIUM.
- reason: Wafer Lapping uses Alumina Abrasive in the cited flow; this is an input, not an output relation.
- evidence assessment: The same SUMCO sentence directly names alumina abrasive as the polishing medium.
- temporal scope assessed: {'source_scope': 'SUMCO wafer forming / lapping; undated', 'temporal_status': 'categorical_source_scoped', 'runtime_status': 'categorical', 'valid_from': '', 'valid_to': '', 'source_as_of': [None]}
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'same', 'object_type': 'compatible', 'scope': 'compatible', 'granularity': 'unknown', 'quarantine': 'clear', 'ontology': 'compatible', 'evidence_sufficiency': 'sufficient', 'temporal': 'compatible'}

**AI REVIEW B**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `CREATE_RELATION`; target: `none`; confidence: HIGH; materiality: LOW.
- reason: Wafer Lapping → Alumina Abrasive (uses): SUMCO states alumina abrasive is used while lapping; process-to-material direction is direct.
- evidence assessment: SC-EV-59686E8EF98436C8 from SC-P0-006_SUMCO_Silicon_Wafer_Production_Processes.pdf [source SC-PHYS-9E9CEFC24043585C; SHA 9e9cefc24043585c1c5a484340dcf49aa0725b341467942d3d4c34be0da8aee6; PDF p.4, Wafer forming process / Lapping]: The sliced wafers are polished by alumina abrasive in a lapping machine to the desired thickness, while improving the surface parallelism. Boundary: Wafer Lapping → Alumina Abrasive (uses): SUMCO states alumina abrasive is used while lapping; process-to-material direction is direct. All source excerpts remain UNAUTHORIZED_CANDIDATE evidence.
- temporal scope assessed: categorical_source_scoped
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'same', 'object_type': 'compatible', 'scope': 'compatible', 'granularity': 'same', 'quarantine': 'clear', 'ontology': 'compatible', 'evidence_sufficiency': 'sufficient', 'temporal': 'compatible'}

**A/B RECONCILIATION**

- A_B_SUBSTANTIVE_AGREEMENT; disagreement type: none; native-operation conflict: false; target conflict: false.
- Interpretation differences: none.
- Reconciliation assessment: Both reviewers support the same frozen endpoints, relation type, source scope, and evidence. Granularity labels refer to parent-child levels versus the proposed edge; bounded evidence comments do not change the edge.
- Non-material rubric-label differences retained for audit: granularity.

**EVIDENCE SUMMARY**

- Source `SC-PHYS-9E9CEFC24043585C` (SHA-256 `9e9cefc24043585c1c5a484340dcf49aa0725b341467942d3d4c34be0da8aee6`), file `SC-P0-006_SUMCO_Silicon_Wafer_Production_Processes.pdf`, p. 4, section Wafer forming process / Lapping; evidence `SC-EV-59686E8EF98436C8`; as-of unknown; excerpt: “The sliced wafers are polished by alumina abrasive in a lapping machine to the desired thickness, while improving the surface parallelism.”
- Temporal scope: categorical_source_scoped.

- SYSTEM_RECOMMENDED_DECISION: `CREATE_RELATION`.
- SYSTEM_RECOMMENDATION_REASON: A/B substantive consensus; frozen automated outcome: CREATE_RELATION.
- HUMAN_USER_DECISION = PENDING
- VALID NATIVE OPTIONS: REUSE_RELATION, CREATE_RELATION, KEEP_DOMAIN_SPECIFIC_RELATION, DEFER_RELATION, REJECT_RELATION; REUSE requires an explicit validated target ID and all options remain subject to frozen controls.

### Item 077 — SC-RL-0031 — Silicon Wafer Polishing → Colloidal Silica

- ITEM_NUMBER: 77; ITEM_ID: `SC-RL-0031`; OBJECT_TYPE: relation.
- DOMAIN / context: `semiconductor` Semiconductor structured Foundation candidate against shared AI Hardware canonical catalog; cross-domain status: `candidate`.
- AUTOMATED_STAGE3_OUTCOME: `DEFER_RELATION`; CURRENT_CANONICAL_TARGET: `none`.
- Possible existing canonical IDs (unresolved unless explicitly reused): `none`.
- CANDIDATE_SUMMARY: Silicon Wafer Polishing → Colloidal Silica; candidate type `uses`; comparison scope `SUMCO starting silicon wafer polishing; not all CMP`; frozen candidate rationale: 一个或两个端点尚未通过身份候选准入；证据保留，不提前授权端点。
- WHY_HUMAN_REQUIRED: frozen Stage 3 mandatory review population; automated reasons: ENDPOINT_AMBIGUITY, EVIDENCE_WARNING, LOW_OR_UNKNOWN_CONFIDENCE, RELATION_AMBIGUITY.
- RISK_FLAGS: A=ENDPOINT_AMBIGUITY, EVIDENCE_WARNING, LOW_OR_UNKNOWN_CONFIDENCE, RELATION_AMBIGUITY; B=UNRESOLVED_RELATION, ENDPOINT_OR_RECONCILIATION.

**AI REVIEW A**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `DEFER_RELATION`; target: `{'from_node_id': None, 'to_node_id': None, 'from_ref': 'SC-CN-0042', 'to_ref': 'SC-CN-0043', 'relation_type': 'uses', 'existing_relation_ids': []}`; confidence: HIGH; materiality: MEDIUM.
- reason: Silicon Wafer Polishing uses Colloidal Silica in this source, but both candidate endpoints require identity admission.
- evidence assessment: SUMCO directly names colloidal silica for mirror finishing; its scope is starting wafers rather than all CMP.
- temporal scope assessed: {'source_scope': 'SUMCO starting silicon wafer polishing; not all CMP', 'temporal_status': 'categorical_source_scoped', 'runtime_status': 'categorical', 'valid_from': '', 'valid_to': '', 'source_as_of': [None]}
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'ambiguous', 'object_type': 'unknown', 'scope': 'unknown', 'granularity': 'unknown', 'quarantine': 'clear', 'ontology': 'compatible', 'evidence_sufficiency': 'sufficient', 'temporal': 'compatible'}

**AI REVIEW B**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `DEFER_RELATION`; target: `none`; confidence: MEDIUM; materiality: HIGH.
- reason: Silicon Wafer Polishing → Colloidal Silica (uses): SUMCO links colloidal silica to starting-wafer mirror polishing; endpoint identities need review first.
- evidence assessment: SC-EV-FD093A8B2A6553C4 from SC-P0-006_SUMCO_Silicon_Wafer_Production_Processes.pdf [source SC-PHYS-9E9CEFC24043585C; SHA 9e9cefc24043585c1c5a484340dcf49aa0725b341467942d3d4c34be0da8aee6; PDF p.4, Wafer forming process / Polishing]: The wafer surfaces are made perfectly flat and given a mirror finish by means of mechano-chemical polishing using colloidal silica. Boundary: Silicon Wafer Polishing → Colloidal Silica (uses): SUMCO links colloidal silica to starting-wafer mirror polishing; endpoint identities need review first. All source excerpts remain UNAUTHORIZED_CANDIDATE evidence.
- temporal scope assessed: categorical_source_scoped
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'ambiguous', 'object_type': 'unknown', 'scope': 'unknown', 'granularity': 'unknown', 'quarantine': 'clear', 'ontology': 'unresolved', 'evidence_sufficiency': 'limited', 'temporal': 'compatible'}

**A/B RECONCILIATION**

- A_B_SUBSTANTIVE_AGREEMENT; disagreement type: none; native-operation conflict: false; target conflict: false.
- Interpretation differences: none.
- Reconciliation assessment: Both reviewers hold the same endpoint, temporal, or ontology exception. Rubric labels compare concept support with authority for the relation.
- Non-material rubric-label differences retained for audit: evidence_sufficiency, ontology.

**EVIDENCE SUMMARY**

- Source `SC-PHYS-9E9CEFC24043585C` (SHA-256 `9e9cefc24043585c1c5a484340dcf49aa0725b341467942d3d4c34be0da8aee6`), file `SC-P0-006_SUMCO_Silicon_Wafer_Production_Processes.pdf`, p. 4, section Wafer forming process / Polishing; evidence `SC-EV-FD093A8B2A6553C4`; as-of unknown; excerpt: “The wafer surfaces are made perfectly flat and given a mirror finish by means of mechano-chemical polishing using colloidal silica.”
- Temporal scope: categorical_source_scoped.

- SYSTEM_RECOMMENDED_DECISION: `DEFER_RELATION`.
- SYSTEM_RECOMMENDATION_REASON: Frozen structural, Stage 2 decision, evidence, or temporal exception remains unresolved.
- HUMAN_USER_DECISION = PENDING
- VALID NATIVE OPTIONS: REUSE_RELATION, CREATE_RELATION, KEEP_DOMAIN_SPECIFIC_RELATION, DEFER_RELATION, REJECT_RELATION; REUSE requires an explicit validated target ID and all options remain subject to frozen controls.

### Item 078 — SC-RL-0032 — Silicon Epitaxial Growth → Epitaxial Furnace

- ITEM_NUMBER: 78; ITEM_ID: `SC-RL-0032`; OBJECT_TYPE: relation.
- DOMAIN / context: `semiconductor` Semiconductor structured Foundation candidate against shared AI Hardware canonical catalog; cross-domain status: `candidate`.
- AUTOMATED_STAGE3_OUTCOME: `CREATE_RELATION`; CURRENT_CANONICAL_TARGET: `none`.
- Possible existing canonical IDs (unresolved unless explicitly reused): `none`.
- CANDIDATE_SUMMARY: Silicon Epitaxial Growth → Epitaxial Furnace; candidate type `uses`; comparison scope `SUMCO silicon epitaxial-wafer process; undated`; frozen candidate rationale: Source原文直接支持有界命题；仅供local review，不表示授权。
- WHY_HUMAN_REQUIRED: frozen Stage 3 mandatory review population; automated reasons: DISTINCT_RELATION_PROPOSAL, LOW_OR_UNKNOWN_CONFIDENCE.
- RISK_FLAGS: A=DISTINCT_RELATION_PROPOSAL, LOW_OR_UNKNOWN_CONFIDENCE; B=none.

**AI REVIEW A**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `CREATE_RELATION`; target: `{'from_node_id': 'NODE_1C0486F0BBD2696F', 'to_node_id': 'NODE_008076BCD6DD42FC', 'from_ref': 'SC-CN-0044', 'to_ref': 'SC-CN-0046', 'relation_type': 'uses', 'existing_relation_ids': []}`; confidence: HIGH; materiality: MEDIUM.
- reason: Silicon Epitaxial Growth uses an Epitaxial Furnace in SUMCO's described process.
- evidence assessment: SUMCO says polished wafers are heated in an epitaxial furnace before vapor-phase silicon growth.
- temporal scope assessed: {'source_scope': 'SUMCO silicon epitaxial-wafer process; undated', 'temporal_status': 'categorical_source_scoped', 'runtime_status': 'categorical', 'valid_from': '', 'valid_to': '', 'source_as_of': [None]}
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'same', 'object_type': 'compatible', 'scope': 'compatible', 'granularity': 'unknown', 'quarantine': 'clear', 'ontology': 'compatible', 'evidence_sufficiency': 'sufficient', 'temporal': 'compatible'}

**AI REVIEW B**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `CREATE_RELATION`; target: `none`; confidence: HIGH; materiality: LOW.
- reason: Silicon Epitaxial Growth → Epitaxial Furnace (uses): SUMCO places polished wafers in an epitaxial furnace for vapor-phase growth; equipment direction is direct.
- evidence assessment: SC-EV-574D5C0F2C499255 from SC-P0-006_SUMCO_Silicon_Wafer_Production_Processes.pdf [source SC-PHYS-9E9CEFC24043585C; SHA 9e9cefc24043585c1c5a484340dcf49aa0725b341467942d3d4c34be0da8aee6; PDF p.5, Specialized processing / Epitaxial Wafers]: Polished wafers are heated to around 1200℃ in an epitaxial furnace. Vaporized silicon tetrachloride (SiCl4) and trichlorosilane (SiHCl3) are circulated in the furnace, causing vapor phase (epitaxial) growth of a monocrystalline silicon film on the wafer surface. Boundary: Silicon Epitaxial Growth → Epitaxial Furnace (uses): SUMCO places polished wafers in an epitaxial furnace for vapor-phase growth; equipment direction is direct. All source excerpts remain UNAUTHORIZED_CANDIDATE evidence.
- temporal scope assessed: categorical_source_scoped
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'same', 'object_type': 'compatible', 'scope': 'compatible', 'granularity': 'same', 'quarantine': 'clear', 'ontology': 'compatible', 'evidence_sufficiency': 'sufficient', 'temporal': 'compatible'}

**A/B RECONCILIATION**

- A_B_SUBSTANTIVE_AGREEMENT; disagreement type: none; native-operation conflict: false; target conflict: false.
- Interpretation differences: none.
- Reconciliation assessment: Both reviewers support the same frozen endpoints, relation type, source scope, and evidence. Granularity labels refer to parent-child levels versus the proposed edge; bounded evidence comments do not change the edge.
- Non-material rubric-label differences retained for audit: granularity.

**EVIDENCE SUMMARY**

- Source `SC-PHYS-9E9CEFC24043585C` (SHA-256 `9e9cefc24043585c1c5a484340dcf49aa0725b341467942d3d4c34be0da8aee6`), file `SC-P0-006_SUMCO_Silicon_Wafer_Production_Processes.pdf`, p. 5, section Specialized processing / Epitaxial Wafers; evidence `SC-EV-574D5C0F2C499255`; as-of unknown; excerpt: “Polished wafers are heated to around 1200℃ in an epitaxial furnace. Vaporized silicon tetrachloride (SiCl4) and trichlorosilane (SiHCl3) are circulated in the furnace, causing vapor phase (epitaxial) growth of a monocrystalline silicon film on the wafer surface.”
- Temporal scope: categorical_source_scoped.

- SYSTEM_RECOMMENDED_DECISION: `CREATE_RELATION`.
- SYSTEM_RECOMMENDATION_REASON: A/B substantive consensus; frozen automated outcome: CREATE_RELATION.
- HUMAN_USER_DECISION = PENDING
- VALID NATIVE OPTIONS: REUSE_RELATION, CREATE_RELATION, KEEP_DOMAIN_SPECIFIC_RELATION, DEFER_RELATION, REJECT_RELATION; REUSE requires an explicit validated target ID and all options remain subject to frozen controls.

### Item 079 — SC-RL-0033 — Silicon Epitaxial Growth → Silicon Tetrachloride

- ITEM_NUMBER: 79; ITEM_ID: `SC-RL-0033`; OBJECT_TYPE: relation.
- DOMAIN / context: `semiconductor` Semiconductor structured Foundation candidate against shared AI Hardware canonical catalog; cross-domain status: `candidate`.
- AUTOMATED_STAGE3_OUTCOME: `CREATE_RELATION`; CURRENT_CANONICAL_TARGET: `none`.
- Possible existing canonical IDs (unresolved unless explicitly reused): `none`.
- CANDIDATE_SUMMARY: Silicon Epitaxial Growth → Silicon Tetrachloride; candidate type `uses`; comparison scope `SUMCO described silicon epitaxy chemistry; not all precursor recipes`; frozen candidate rationale: Source原文直接支持有界命题；仅供local review，不表示授权。
- WHY_HUMAN_REQUIRED: frozen Stage 3 mandatory review population; automated reasons: DISTINCT_RELATION_PROPOSAL, LOW_OR_UNKNOWN_CONFIDENCE.
- RISK_FLAGS: A=DISTINCT_RELATION_PROPOSAL, LOW_OR_UNKNOWN_CONFIDENCE; B=none.

**AI REVIEW A**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `CREATE_RELATION`; target: `{'from_node_id': 'NODE_1C0486F0BBD2696F', 'to_node_id': 'NODE_58AC04BDBCA28DDB', 'from_ref': 'SC-CN-0044', 'to_ref': 'SC-CN-0047', 'relation_type': 'uses', 'existing_relation_ids': []}`; confidence: MEDIUM; materiality: MEDIUM.
- reason: Silicon Epitaxial Growth uses SiCl4 in the SUMCO recipe, without claiming all recipes use it.
- evidence assessment: SUMCO names vaporized silicon tetrachloride circulating in the furnace.
- temporal scope assessed: {'source_scope': 'SUMCO described silicon epitaxy chemistry; not all precursor recipes', 'temporal_status': 'categorical_source_scoped', 'runtime_status': 'categorical', 'valid_from': '', 'valid_to': '', 'source_as_of': [None]}
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'same', 'object_type': 'compatible', 'scope': 'compatible', 'granularity': 'unknown', 'quarantine': 'clear', 'ontology': 'compatible', 'evidence_sufficiency': 'sufficient', 'temporal': 'compatible'}

**AI REVIEW B**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `CREATE_RELATION`; target: `none`; confidence: HIGH; materiality: LOW.
- reason: Silicon Epitaxial Growth → Silicon Tetrachloride (uses): SUMCO names vaporized SiCl4 in silicon epitaxy; limit the precursor edge to that recipe.
- evidence assessment: SC-EV-574D5C0F2C499255 from SC-P0-006_SUMCO_Silicon_Wafer_Production_Processes.pdf [source SC-PHYS-9E9CEFC24043585C; SHA 9e9cefc24043585c1c5a484340dcf49aa0725b341467942d3d4c34be0da8aee6; PDF p.5, Specialized processing / Epitaxial Wafers]: Polished wafers are heated to around 1200℃ in an epitaxial furnace. Vaporized silicon tetrachloride (SiCl4) and trichlorosilane (SiHCl3) are circulated in the furnace, causing vapor phase (epitaxial) growth of a monocrystalline silicon film on the wafer surface. Boundary: Silicon Epitaxial Growth → Silicon Tetrachloride (uses): SUMCO names vaporized SiCl4 in silicon epitaxy; limit the precursor edge to that recipe. All source excerpts remain UNAUTHORIZED_CANDIDATE evidence.
- temporal scope assessed: categorical_source_scoped
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'same', 'object_type': 'compatible', 'scope': 'compatible', 'granularity': 'same', 'quarantine': 'clear', 'ontology': 'compatible', 'evidence_sufficiency': 'sufficient', 'temporal': 'compatible'}

**A/B RECONCILIATION**

- A_B_SUBSTANTIVE_AGREEMENT; disagreement type: none; native-operation conflict: false; target conflict: false.
- Interpretation differences: none.
- Reconciliation assessment: Both reviewers support the same frozen endpoints, relation type, source scope, and evidence. Granularity labels refer to parent-child levels versus the proposed edge; bounded evidence comments do not change the edge.
- Non-material rubric-label differences retained for audit: granularity.

**EVIDENCE SUMMARY**

- Source `SC-PHYS-9E9CEFC24043585C` (SHA-256 `9e9cefc24043585c1c5a484340dcf49aa0725b341467942d3d4c34be0da8aee6`), file `SC-P0-006_SUMCO_Silicon_Wafer_Production_Processes.pdf`, p. 5, section Specialized processing / Epitaxial Wafers; evidence `SC-EV-574D5C0F2C499255`; as-of unknown; excerpt: “Polished wafers are heated to around 1200℃ in an epitaxial furnace. Vaporized silicon tetrachloride (SiCl4) and trichlorosilane (SiHCl3) are circulated in the furnace, causing vapor phase (epitaxial) growth of a monocrystalline silicon film on the wafer surface.”
- Temporal scope: categorical_source_scoped.

- SYSTEM_RECOMMENDED_DECISION: `CREATE_RELATION`.
- SYSTEM_RECOMMENDATION_REASON: A/B substantive consensus; frozen automated outcome: CREATE_RELATION.
- HUMAN_USER_DECISION = PENDING
- VALID NATIVE OPTIONS: REUSE_RELATION, CREATE_RELATION, KEEP_DOMAIN_SPECIFIC_RELATION, DEFER_RELATION, REJECT_RELATION; REUSE requires an explicit validated target ID and all options remain subject to frozen controls.

### Item 080 — SC-RL-0034 — Silicon Epitaxial Growth → Trichlorosilane

- ITEM_NUMBER: 80; ITEM_ID: `SC-RL-0034`; OBJECT_TYPE: relation.
- DOMAIN / context: `semiconductor` Semiconductor structured Foundation candidate against shared AI Hardware canonical catalog; cross-domain status: `candidate`.
- AUTOMATED_STAGE3_OUTCOME: `CREATE_RELATION`; CURRENT_CANONICAL_TARGET: `none`.
- Possible existing canonical IDs (unresolved unless explicitly reused): `none`.
- CANDIDATE_SUMMARY: Silicon Epitaxial Growth → Trichlorosilane; candidate type `uses`; comparison scope `SUMCO described silicon epitaxy chemistry; not all precursor recipes`; frozen candidate rationale: Source原文直接支持有界命题；仅供local review，不表示授权。
- WHY_HUMAN_REQUIRED: frozen Stage 3 mandatory review population; automated reasons: DISTINCT_RELATION_PROPOSAL, LOW_OR_UNKNOWN_CONFIDENCE.
- RISK_FLAGS: A=DISTINCT_RELATION_PROPOSAL, LOW_OR_UNKNOWN_CONFIDENCE; B=none.

**AI REVIEW A**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `CREATE_RELATION`; target: `{'from_node_id': 'NODE_1C0486F0BBD2696F', 'to_node_id': 'NODE_1DAECC13834A407E', 'from_ref': 'SC-CN-0044', 'to_ref': 'SC-CN-0048', 'relation_type': 'uses', 'existing_relation_ids': []}`; confidence: MEDIUM; materiality: MEDIUM.
- reason: Silicon Epitaxial Growth also uses trichlorosilane in the same bounded recipe.
- evidence assessment: SUMCO lists SiHCl3 alongside SiCl4 as a vaporized precursor.
- temporal scope assessed: {'source_scope': 'SUMCO described silicon epitaxy chemistry; not all precursor recipes', 'temporal_status': 'categorical_source_scoped', 'runtime_status': 'categorical', 'valid_from': '', 'valid_to': '', 'source_as_of': [None]}
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'same', 'object_type': 'compatible', 'scope': 'compatible', 'granularity': 'unknown', 'quarantine': 'clear', 'ontology': 'compatible', 'evidence_sufficiency': 'sufficient', 'temporal': 'compatible'}

**AI REVIEW B**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `CREATE_RELATION`; target: `none`; confidence: HIGH; materiality: LOW.
- reason: Silicon Epitaxial Growth → Trichlorosilane (uses): SUMCO names trichlorosilane with SiCl4 in epitaxy; do not generalize to all epitaxial processes.
- evidence assessment: SC-EV-574D5C0F2C499255 from SC-P0-006_SUMCO_Silicon_Wafer_Production_Processes.pdf [source SC-PHYS-9E9CEFC24043585C; SHA 9e9cefc24043585c1c5a484340dcf49aa0725b341467942d3d4c34be0da8aee6; PDF p.5, Specialized processing / Epitaxial Wafers]: Polished wafers are heated to around 1200℃ in an epitaxial furnace. Vaporized silicon tetrachloride (SiCl4) and trichlorosilane (SiHCl3) are circulated in the furnace, causing vapor phase (epitaxial) growth of a monocrystalline silicon film on the wafer surface. Boundary: Silicon Epitaxial Growth → Trichlorosilane (uses): SUMCO names trichlorosilane with SiCl4 in epitaxy; do not generalize to all epitaxial processes. All source excerpts remain UNAUTHORIZED_CANDIDATE evidence.
- temporal scope assessed: categorical_source_scoped
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'same', 'object_type': 'compatible', 'scope': 'compatible', 'granularity': 'same', 'quarantine': 'clear', 'ontology': 'compatible', 'evidence_sufficiency': 'sufficient', 'temporal': 'compatible'}

**A/B RECONCILIATION**

- A_B_SUBSTANTIVE_AGREEMENT; disagreement type: none; native-operation conflict: false; target conflict: false.
- Interpretation differences: none.
- Reconciliation assessment: Both reviewers support the same frozen endpoints, relation type, source scope, and evidence. Granularity labels refer to parent-child levels versus the proposed edge; bounded evidence comments do not change the edge.
- Non-material rubric-label differences retained for audit: granularity.

**EVIDENCE SUMMARY**

- Source `SC-PHYS-9E9CEFC24043585C` (SHA-256 `9e9cefc24043585c1c5a484340dcf49aa0725b341467942d3d4c34be0da8aee6`), file `SC-P0-006_SUMCO_Silicon_Wafer_Production_Processes.pdf`, p. 5, section Specialized processing / Epitaxial Wafers; evidence `SC-EV-574D5C0F2C499255`; as-of unknown; excerpt: “Polished wafers are heated to around 1200℃ in an epitaxial furnace. Vaporized silicon tetrachloride (SiCl4) and trichlorosilane (SiHCl3) are circulated in the furnace, causing vapor phase (epitaxial) growth of a monocrystalline silicon film on the wafer surface.”
- Temporal scope: categorical_source_scoped.

- SYSTEM_RECOMMENDED_DECISION: `CREATE_RELATION`.
- SYSTEM_RECOMMENDATION_REASON: A/B substantive consensus; frozen automated outcome: CREATE_RELATION.
- HUMAN_USER_DECISION = PENDING
- VALID NATIVE OPTIONS: REUSE_RELATION, CREATE_RELATION, KEEP_DOMAIN_SPECIFIC_RELATION, DEFER_RELATION, REJECT_RELATION; REUSE requires an explicit validated target ID and all options remain subject to frozen controls.

### Item 081 — SC-RL-0035 — Photolithography → Photoresist

- ITEM_NUMBER: 81; ITEM_ID: `SC-RL-0035`; OBJECT_TYPE: relation.
- DOMAIN / context: `semiconductor` Semiconductor structured Foundation candidate against shared AI Hardware canonical catalog; cross-domain status: `candidate`.
- AUTOMATED_STAGE3_OUTCOME: `DEFER_RELATION`; CURRENT_CANONICAL_TARGET: `none`.
- Possible existing canonical IDs (unresolved unless explicitly reused): `none`.
- CANDIDATE_SUMMARY: Photolithography → Photoresist; candidate type `uses`; comparison scope `SIA/BCG 2021 materials / lithography`; frozen candidate rationale: Source原文直接支持有界命题；仅供local review，不表示授权。
- WHY_HUMAN_REQUIRED: frozen Stage 3 mandatory review population; automated reasons: ENDPOINT_AMBIGUITY, LOW_OR_UNKNOWN_CONFIDENCE, RELATION_AMBIGUITY.
- RISK_FLAGS: A=ENDPOINT_AMBIGUITY, LOW_OR_UNKNOWN_CONFIDENCE, RELATION_AMBIGUITY; B=UNRESOLVED_RELATION, ENDPOINT_OR_RECONCILIATION.

**AI REVIEW A**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `DEFER_RELATION`; target: `{'from_node_id': 'NODE_D71397E38AE45F20', 'to_node_id': None, 'from_ref': 'SC-CN-0056', 'to_ref': 'SC-CN-0052', 'relation_type': 'uses', 'existing_relation_ids': []}`; confidence: HIGH; materiality: MEDIUM.
- reason: Photolithography uses Photoresist, but the general resist node remains held; the process link can follow identity approval.
- evidence assessment: SIA/BCG says resist is exposed and imprinted with a photomask during lithography.
- temporal scope assessed: {'source_scope': 'SIA/BCG 2021 materials / lithography', 'temporal_status': 'categorical_source_scoped', 'runtime_status': 'categorical', 'valid_from': '', 'valid_to': '', 'source_as_of': ['2021-04']}
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'ambiguous', 'object_type': 'unknown', 'scope': 'unknown', 'granularity': 'unknown', 'quarantine': 'clear', 'ontology': 'compatible', 'evidence_sufficiency': 'sufficient', 'temporal': 'compatible'}

**AI REVIEW B**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `DEFER_RELATION`; target: `none`; confidence: MEDIUM; materiality: HIGH.
- reason: Photolithography → Photoresist (uses): The source puts photoresist on wafers during lithography, but generic Photoresist identity remains unresolved.
- evidence assessment: SC-EV-B569E06E885DA787 from SC-P0-002_SIA_BCG_Global_Semiconductor_Supply_Chain_2021.pdf [source SC-PHYS-B33C40EBCB5756F7; SHA b33c40ebcb5756f76e887ba2664f97736252e68ba7bfbedc2d628ce2d7cbc08d; PDF p.22, Materials]: Photoresist: A special material that undergoes a chemical reaction upon exposure to light. Silicon wafers are covered with a photoresist layer, which is imprinted with the patterns contained in the photomask during the lithography process. Boundary: Photolithography → Photoresist (uses): The source puts photoresist on wafers during lithography, but generic Photoresist identity remains unresolved. All source excerpts remain UNAUTHORIZED_CANDIDATE evidence.
- temporal scope assessed: categorical_source_scoped
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'ambiguous', 'object_type': 'unknown', 'scope': 'unknown', 'granularity': 'unknown', 'quarantine': 'clear', 'ontology': 'unresolved', 'evidence_sufficiency': 'limited', 'temporal': 'compatible'}

**A/B RECONCILIATION**

- A_B_SUBSTANTIVE_AGREEMENT; disagreement type: none; native-operation conflict: false; target conflict: false.
- Interpretation differences: none.
- Reconciliation assessment: Both reviewers hold the same endpoint, temporal, or ontology exception. Rubric labels compare concept support with authority for the relation.
- Non-material rubric-label differences retained for audit: evidence_sufficiency, ontology.

**EVIDENCE SUMMARY**

- Source `SC-PHYS-B33C40EBCB5756F7` (SHA-256 `b33c40ebcb5756f76e887ba2664f97736252e68ba7bfbedc2d628ce2d7cbc08d`), file `SC-P0-002_SIA_BCG_Global_Semiconductor_Supply_Chain_2021.pdf`, p. 22, section Materials; evidence `SC-EV-B569E06E885DA787`; as-of 2021-04; excerpt: “Photoresist: A special material that undergoes a chemical reaction upon exposure to light. Silicon wafers are covered with a photoresist layer, which is imprinted with the patterns contained in the photomask during the lithography process.”
- Temporal scope: categorical_source_scoped.

- SYSTEM_RECOMMENDED_DECISION: `DEFER_RELATION`.
- SYSTEM_RECOMMENDATION_REASON: Frozen structural, Stage 2 decision, evidence, or temporal exception remains unresolved.
- HUMAN_USER_DECISION = PENDING
- VALID NATIVE OPTIONS: REUSE_RELATION, CREATE_RELATION, KEEP_DOMAIN_SPECIFIC_RELATION, DEFER_RELATION, REJECT_RELATION; REUSE requires an explicit validated target ID and all options remain subject to frozen controls.

### Item 082 — SC-RL-0036 — Photolithography → Photomask

- ITEM_NUMBER: 82; ITEM_ID: `SC-RL-0036`; OBJECT_TYPE: relation.
- DOMAIN / context: `semiconductor` Semiconductor structured Foundation candidate against shared AI Hardware canonical catalog; cross-domain status: `candidate`.
- AUTOMATED_STAGE3_OUTCOME: `CREATE_RELATION`; CURRENT_CANONICAL_TARGET: `none`.
- Possible existing canonical IDs (unresolved unless explicitly reused): `none`.
- CANDIDATE_SUMMARY: Photolithography → Photomask; candidate type `uses`; comparison scope `SIA/BCG 2021 and ASML 2023 optical lithography`; frozen candidate rationale: Source原文直接支持有界命题；仅供local review，不表示授权。
- WHY_HUMAN_REQUIRED: frozen Stage 3 mandatory review population; automated reasons: DISTINCT_RELATION_PROPOSAL, LOW_OR_UNKNOWN_CONFIDENCE.
- RISK_FLAGS: A=DISTINCT_RELATION_PROPOSAL, LOW_OR_UNKNOWN_CONFIDENCE; B=FROZEN_STAGE2_DECISION.

**AI REVIEW A**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `CREATE_RELATION`; target: `{'from_node_id': 'NODE_D71397E38AE45F20', 'to_node_id': 'NODE_72297BCF151CC0EF', 'from_ref': 'SC-CN-0056', 'to_ref': 'SC-CN-0053', 'relation_type': 'uses', 'existing_relation_ids': []}`; confidence: MEDIUM; materiality: MEDIUM.
- reason: Photolithography uses a Photomask to carry the exposure pattern; Stage 2 CREATE supports the proposal.
- evidence assessment: SIA/BCG defines a photomask as a patterned plate used in lithography, although it does not set equipment scope.
- temporal scope assessed: {'source_scope': 'SIA/BCG 2021 and ASML 2023 optical lithography', 'temporal_status': 'categorical_source_scoped', 'runtime_status': 'categorical', 'valid_from': '', 'valid_to': '', 'source_as_of': ['2021-04', '2023-10-04']}
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'same', 'object_type': 'compatible', 'scope': 'compatible', 'granularity': 'unknown', 'quarantine': 'clear', 'ontology': 'compatible', 'evidence_sufficiency': 'sufficient', 'temporal': 'compatible'}

**AI REVIEW B**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `CREATE_RELATION`; target: `none`; confidence: MEDIUM; materiality: LOW.
- reason: Photolithography → Photomask (uses): The photomask definition says it carries patterns used in lithography; this directly supports uses.
- evidence assessment: SC-EV-9393F2354C64C727 from SC-P0-002_SIA_BCG_Global_Semiconductor_Supply_Chain_2021.pdf [source SC-PHYS-B33C40EBCB5756F7; SHA b33c40ebcb5756f76e887ba2664f97736252e68ba7bfbedc2d628ce2d7cbc08d; PDF p.22, Materials]: Photomask: A plate covered with patterns used in the lithography process. The patterns consist of opaque and clear areas that prevent or allow light through. | SC-EV-FD3B14BF5F4E693A from SC-P0-007_ASML_Six_Semiconductor_Manufacturing_Steps.pdf [source SC-PHYS-87B4665C30781057; SHA 87b4665c3078105792ca70f18964c938976b72f2dcf0d19379b034d5d6f205f9; PDF p.3, Lithography]: Light is projected onto the wafer through the 'reticle', which holds the blueprint of the pattern to be printed. The system's optics (lenses in a DUV system and mirrors in an EUV system) shrink and focus the pattern onto the resist layer. Boundary: Photolithography → Photomask (uses): The photomask definition says it carries patterns used in lithography; this directly supports uses. All source excerpts remain UNAUTHORIZED_CANDIDATE evidence.
- temporal scope assessed: categorical_source_scoped
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'same', 'object_type': 'compatible', 'scope': 'compatible', 'granularity': 'same', 'quarantine': 'clear', 'ontology': 'compatible', 'evidence_sufficiency': 'sufficient', 'temporal': 'compatible'}

**A/B RECONCILIATION**

- A_B_SUBSTANTIVE_AGREEMENT; disagreement type: none; native-operation conflict: false; target conflict: false.
- Interpretation differences: none.
- Reconciliation assessment: Both reviewers support the same frozen endpoints, relation type, source scope, and evidence. Granularity labels refer to parent-child levels versus the proposed edge; bounded evidence comments do not change the edge.
- Non-material rubric-label differences retained for audit: granularity.

**EVIDENCE SUMMARY**

- Source `SC-PHYS-B33C40EBCB5756F7` (SHA-256 `b33c40ebcb5756f76e887ba2664f97736252e68ba7bfbedc2d628ce2d7cbc08d`), file `SC-P0-002_SIA_BCG_Global_Semiconductor_Supply_Chain_2021.pdf`, p. 22, section Materials; evidence `SC-EV-9393F2354C64C727`; as-of 2021-04; excerpt: “Photomask: A plate covered with patterns used in the lithography process. The patterns consist of opaque and clear areas that prevent or allow light through.”
- Source `SC-PHYS-87B4665C30781057` (SHA-256 `87b4665c3078105792ca70f18964c938976b72f2dcf0d19379b034d5d6f205f9`), file `SC-P0-007_ASML_Six_Semiconductor_Manufacturing_Steps.pdf`, p. 3, section Lithography; evidence `SC-EV-FD3B14BF5F4E693A`; as-of 2023-10-04; excerpt: “Light is projected onto the wafer through the 'reticle', which holds the blueprint of the pattern to be printed. The system's optics (lenses in a DUV system and mirrors in an EUV system) shrink and focus the pattern onto the resist layer.”
- Temporal scope: categorical_source_scoped.

- SYSTEM_RECOMMENDED_DECISION: `CREATE_RELATION`.
- SYSTEM_RECOMMENDATION_REASON: A/B substantive consensus; frozen automated outcome: CREATE_RELATION.
- HUMAN_USER_DECISION = PENDING
- VALID NATIVE OPTIONS: REUSE_RELATION, CREATE_RELATION, KEEP_DOMAIN_SPECIFIC_RELATION, DEFER_RELATION, REJECT_RELATION; REUSE requires an explicit validated target ID and all options remain subject to frozen controls.

### Item 083 — SC-RL-0037 — Photolithography → Lithography Scanner / Stepper

- ITEM_NUMBER: 83; ITEM_ID: `SC-RL-0037`; OBJECT_TYPE: relation.
- DOMAIN / context: `semiconductor` Semiconductor structured Foundation candidate against shared AI Hardware canonical catalog; cross-domain status: `candidate`.
- AUTOMATED_STAGE3_OUTCOME: `DEFER_RELATION`; CURRENT_CANONICAL_TARGET: `none`.
- Possible existing canonical IDs (unresolved unless explicitly reused): `none`.
- CANDIDATE_SUMMARY: Photolithography → Lithography Scanner / Stepper; candidate type `uses`; comparison scope `SIA 2026 testimony / photolithography equipment`; frozen candidate rationale: 一个或两个端点尚未通过身份候选准入；证据保留，不提前授权端点。
- WHY_HUMAN_REQUIRED: frozen Stage 3 mandatory review population; automated reasons: EVIDENCE_WARNING, FROZEN_STAGE2_HUMAN_DECISION, LOW_OR_UNKNOWN_CONFIDENCE, RELATION_AMBIGUITY.
- RISK_FLAGS: A=EVIDENCE_WARNING, FROZEN_STAGE2_HUMAN_DECISION, LOW_OR_UNKNOWN_CONFIDENCE, RELATION_AMBIGUITY; B=FROZEN_STAGE2_DECISION, UNRESOLVED_RELATION, ENDPOINT_OR_RECONCILIATION.

**AI REVIEW A**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `DEFER_RELATION`; target: `{'from_node_id': 'NODE_D71397E38AE45F20', 'to_node_id': None, 'from_ref': 'SC-CN-0056', 'to_ref': 'SC-CN-0057', 'relation_type': 'uses', 'existing_relation_ids': []}`; confidence: HIGH; materiality: MEDIUM.
- reason: A stepper or scanner is used for exposure, but the combined Lithography Scanner / Stepper endpoint is held by Stage 2.
- evidence assessment: SIA describes either device aligning wafers to a photomask and projecting DUV or EUV light.
- temporal scope assessed: {'source_scope': 'SIA 2026 testimony / photolithography equipment', 'temporal_status': 'categorical_source_scoped', 'runtime_status': 'categorical', 'valid_from': '', 'valid_to': '', 'source_as_of': ['2026-03-04']}
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'ambiguous', 'object_type': 'unknown', 'scope': 'unknown', 'granularity': 'unknown', 'quarantine': 'clear', 'ontology': 'compatible', 'evidence_sufficiency': 'sufficient', 'temporal': 'compatible'}

**AI REVIEW B**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `DEFER_RELATION`; target: `none`; confidence: MEDIUM; materiality: HIGH.
- reason: Photolithography → Lithography Scanner / Stepper (uses): SIA describes stepper/scanner exposure, but Stage 2 deferred the relation; keep equipment endpoint under review.
- evidence assessment: SC-EV-67EC75515BB09180 from SC-P0-008_Senate-EPW-testimony-3.4.2026.pdf [source SC-PHYS-C5B6DC633E156218; SHA c5b6dc633e156218eb950f2dee88f43fbdcc4fc1744a5924f12b977f5cb7df71; PDF p.4, II / Front-End Fabrication / Photolithography]: A stepper or scanner (using deep ultraviolet or extreme ultraviolet light) aligns the wafer to a glass photomask and projects intense light through the mask or reticle, exposing the photoresist with the pattern. Boundary: Photolithography → Lithography Scanner / Stepper (uses): SIA describes stepper/scanner exposure, but Stage 2 deferred the relation; keep equipment endpoint under review. All source excerpts remain UNAUTHORIZED_CANDIDATE evidence.
- temporal scope assessed: categorical_source_scoped
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'ambiguous', 'object_type': 'unknown', 'scope': 'unknown', 'granularity': 'unknown', 'quarantine': 'preserved', 'ontology': 'unresolved', 'evidence_sufficiency': 'limited', 'temporal': 'compatible'}

**A/B RECONCILIATION**

- A_B_SUBSTANTIVE_AGREEMENT; disagreement type: none; native-operation conflict: false; target conflict: false.
- Interpretation differences: none.
- Reconciliation assessment: Both reviewers hold the same endpoint, temporal, or ontology exception. Rubric labels compare concept support with authority for the relation.
- Non-material rubric-label differences retained for audit: evidence_sufficiency, ontology, quarantine.

**EVIDENCE SUMMARY**

- Source `SC-PHYS-C5B6DC633E156218` (SHA-256 `c5b6dc633e156218eb950f2dee88f43fbdcc4fc1744a5924f12b977f5cb7df71`), file `SC-P0-008_Senate-EPW-testimony-3.4.2026.pdf`, p. 4, section II / Front-End Fabrication / Photolithography; evidence `SC-EV-67EC75515BB09180`; as-of 2026-03-04; excerpt: “A stepper or scanner (using deep ultraviolet or extreme ultraviolet light) aligns the wafer to a glass photomask and projects intense light through the mask or reticle, exposing the photoresist with the pattern.”
- Temporal scope: categorical_source_scoped.

- SYSTEM_RECOMMENDED_DECISION: `DEFER_RELATION`.
- SYSTEM_RECOMMENDATION_REASON: Frozen structural, Stage 2 decision, evidence, or temporal exception remains unresolved.
- HUMAN_USER_DECISION = PENDING
- VALID NATIVE OPTIONS: REUSE_RELATION, CREATE_RELATION, KEEP_DOMAIN_SPECIFIC_RELATION, DEFER_RELATION, REJECT_RELATION; REUSE requires an explicit validated target ID and all options remain subject to frozen controls.

### Item 084 — SC-RL-0038 — Chemical Mechanical Planarization → CMP Slurry

- ITEM_NUMBER: 84; ITEM_ID: `SC-RL-0038`; OBJECT_TYPE: relation.
- DOMAIN / context: `semiconductor` Semiconductor structured Foundation candidate against shared AI Hardware canonical catalog; cross-domain status: `candidate`.
- AUTOMATED_STAGE3_OUTCOME: `CREATE_RELATION`; CURRENT_CANONICAL_TARGET: `none`.
- Possible existing canonical IDs (unresolved unless explicitly reused): `none`.
- CANDIDATE_SUMMARY: Chemical Mechanical Planarization → CMP Slurry; candidate type `uses`; comparison scope `SIA 2026 testimony / wafer back-end CMP`; frozen candidate rationale: Source原文直接支持有界命题；仅供local review，不表示授权。
- WHY_HUMAN_REQUIRED: frozen Stage 3 mandatory review population; automated reasons: DISTINCT_RELATION_PROPOSAL, LOW_OR_UNKNOWN_CONFIDENCE.
- RISK_FLAGS: A=DISTINCT_RELATION_PROPOSAL, LOW_OR_UNKNOWN_CONFIDENCE; B=none.

**AI REVIEW A**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `CREATE_RELATION`; target: `{'from_node_id': 'NODE_D350AEDB638F3572', 'to_node_id': 'NODE_E9589394263EE5DE', 'from_ref': 'SC-CN-0072', 'to_ref': 'SC-CN-0073', 'relation_type': 'uses', 'existing_relation_ids': []}`; confidence: MEDIUM; materiality: MEDIUM.
- reason: CMP uses Slurry in SIA's back-end planarization account; the edge is a process-input statement.
- evidence assessment: SIA explains chemical and physical flattening and identifies slurry in the same bounded CMP description.
- temporal scope assessed: {'source_scope': 'SIA 2026 testimony / wafer back-end CMP', 'temporal_status': 'categorical_source_scoped', 'runtime_status': 'categorical', 'valid_from': '', 'valid_to': '', 'source_as_of': ['2026-03-04']}
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'same', 'object_type': 'compatible', 'scope': 'compatible', 'granularity': 'unknown', 'quarantine': 'clear', 'ontology': 'compatible', 'evidence_sufficiency': 'sufficient', 'temporal': 'compatible'}

**AI REVIEW B**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `CREATE_RELATION`; target: `none`; confidence: HIGH; materiality: LOW.
- reason: Chemical Mechanical Planarization → CMP Slurry (uses): SIA specifies slurry and pad for wafer back-end CMP; slurry is a distinct material input in that scope.
- evidence assessment: SC-EV-E1426DD81060C643 from SC-P0-008_Senate-EPW-testimony-3.4.2026.pdf [source SC-PHYS-C5B6DC633E156218; SHA c5b6dc633e156218eb950f2dee88f43fbdcc4fc1744a5924f12b977f5cb7df71; PDF p.5, II / Back-End Fabrication / CMP]: Chemical Mechanical Planarization (CMP): Between many deposition and metallization layers throughout the back-end process, chemical mechanical planarization (CMP) uses chemical and physical forces to create a microscopically flat surface for each successive layer of circuit features. A polishing pad with a liquid chemical called a “slurry” polishes the wa... Boundary: Chemical Mechanical Planarization → CMP Slurry (uses): SIA specifies slurry and pad for wafer back-end CMP; slurry is a distinct material input in that scope. All source excerpts remain UNAUTHORIZED_CANDIDATE evidence.
- temporal scope assessed: categorical_source_scoped
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'same', 'object_type': 'compatible', 'scope': 'compatible', 'granularity': 'same', 'quarantine': 'clear', 'ontology': 'compatible', 'evidence_sufficiency': 'sufficient', 'temporal': 'compatible'}

**A/B RECONCILIATION**

- A_B_SUBSTANTIVE_AGREEMENT; disagreement type: none; native-operation conflict: false; target conflict: false.
- Interpretation differences: none.
- Reconciliation assessment: Both reviewers support the same frozen endpoints, relation type, source scope, and evidence. Granularity labels refer to parent-child levels versus the proposed edge; bounded evidence comments do not change the edge.
- Non-material rubric-label differences retained for audit: granularity.

**EVIDENCE SUMMARY**

- Source `SC-PHYS-C5B6DC633E156218` (SHA-256 `c5b6dc633e156218eb950f2dee88f43fbdcc4fc1744a5924f12b977f5cb7df71`), file `SC-P0-008_Senate-EPW-testimony-3.4.2026.pdf`, p. 5, section II / Back-End Fabrication / CMP; evidence `SC-EV-E1426DD81060C643`; as-of 2026-03-04; excerpt: “Chemical Mechanical Planarization (CMP): Between many deposition and metallization layers throughout the back-end process, chemical mechanical planarization (CMP) uses chemical and physical forces to create a microscopically flat surface for each successive layer of circuit features. A polishing pad with a liquid chemical called a “slurry” polishes the wafer surface until the desired nanometer top…”
- Temporal scope: categorical_source_scoped.

- SYSTEM_RECOMMENDED_DECISION: `CREATE_RELATION`.
- SYSTEM_RECOMMENDATION_REASON: A/B substantive consensus; frozen automated outcome: CREATE_RELATION.
- HUMAN_USER_DECISION = PENDING
- VALID NATIVE OPTIONS: REUSE_RELATION, CREATE_RELATION, KEEP_DOMAIN_SPECIFIC_RELATION, DEFER_RELATION, REJECT_RELATION; REUSE requires an explicit validated target ID and all options remain subject to frozen controls.

### Item 085 — SC-RL-0039 — Chemical Mechanical Planarization → CMP Polishing Pad

- ITEM_NUMBER: 85; ITEM_ID: `SC-RL-0039`; OBJECT_TYPE: relation.
- DOMAIN / context: `semiconductor` Semiconductor structured Foundation candidate against shared AI Hardware canonical catalog; cross-domain status: `candidate`.
- AUTOMATED_STAGE3_OUTCOME: `CREATE_RELATION`; CURRENT_CANONICAL_TARGET: `none`.
- Possible existing canonical IDs (unresolved unless explicitly reused): `none`.
- CANDIDATE_SUMMARY: Chemical Mechanical Planarization → CMP Polishing Pad; candidate type `uses`; comparison scope `SIA 2026 testimony / wafer back-end CMP`; frozen candidate rationale: Source原文直接支持有界命题；仅供local review，不表示授权。
- WHY_HUMAN_REQUIRED: frozen Stage 3 mandatory review population; automated reasons: DISTINCT_RELATION_PROPOSAL, LOW_OR_UNKNOWN_CONFIDENCE.
- RISK_FLAGS: A=DISTINCT_RELATION_PROPOSAL, LOW_OR_UNKNOWN_CONFIDENCE; B=none.

**AI REVIEW A**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `CREATE_RELATION`; target: `{'from_node_id': 'NODE_D350AEDB638F3572', 'to_node_id': 'NODE_A059A0C57C121C11', 'from_ref': 'SC-CN-0072', 'to_ref': 'SC-CN-0074', 'relation_type': 'uses', 'existing_relation_ids': []}`; confidence: MEDIUM; materiality: MEDIUM.
- reason: CMP uses a Polishing Pad in the cited wafer back-end process, distinct from slurry material.
- evidence assessment: The SIA CMP passage names the pad as part of the flattening operation.
- temporal scope assessed: {'source_scope': 'SIA 2026 testimony / wafer back-end CMP', 'temporal_status': 'categorical_source_scoped', 'runtime_status': 'categorical', 'valid_from': '', 'valid_to': '', 'source_as_of': ['2026-03-04']}
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'same', 'object_type': 'compatible', 'scope': 'compatible', 'granularity': 'unknown', 'quarantine': 'clear', 'ontology': 'compatible', 'evidence_sufficiency': 'sufficient', 'temporal': 'compatible'}

**AI REVIEW B**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `CREATE_RELATION`; target: `none`; confidence: HIGH; materiality: LOW.
- reason: Chemical Mechanical Planarization → CMP Polishing Pad (uses): SIA specifies a polishing pad with slurry for wafer back-end CMP; pad is a separate input.
- evidence assessment: SC-EV-E1426DD81060C643 from SC-P0-008_Senate-EPW-testimony-3.4.2026.pdf [source SC-PHYS-C5B6DC633E156218; SHA c5b6dc633e156218eb950f2dee88f43fbdcc4fc1744a5924f12b977f5cb7df71; PDF p.5, II / Back-End Fabrication / CMP]: Chemical Mechanical Planarization (CMP): Between many deposition and metallization layers throughout the back-end process, chemical mechanical planarization (CMP) uses chemical and physical forces to create a microscopically flat surface for each successive layer of circuit features. A polishing pad with a liquid chemical called a “slurry” polishes the wa... Boundary: Chemical Mechanical Planarization → CMP Polishing Pad (uses): SIA specifies a polishing pad with slurry for wafer back-end CMP; pad is a separate input. All source excerpts remain UNAUTHORIZED_CANDIDATE evidence.
- temporal scope assessed: categorical_source_scoped
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'same', 'object_type': 'compatible', 'scope': 'compatible', 'granularity': 'same', 'quarantine': 'clear', 'ontology': 'compatible', 'evidence_sufficiency': 'sufficient', 'temporal': 'compatible'}

**A/B RECONCILIATION**

- A_B_SUBSTANTIVE_AGREEMENT; disagreement type: none; native-operation conflict: false; target conflict: false.
- Interpretation differences: none.
- Reconciliation assessment: Both reviewers support the same frozen endpoints, relation type, source scope, and evidence. Granularity labels refer to parent-child levels versus the proposed edge; bounded evidence comments do not change the edge.
- Non-material rubric-label differences retained for audit: granularity.

**EVIDENCE SUMMARY**

- Source `SC-PHYS-C5B6DC633E156218` (SHA-256 `c5b6dc633e156218eb950f2dee88f43fbdcc4fc1744a5924f12b977f5cb7df71`), file `SC-P0-008_Senate-EPW-testimony-3.4.2026.pdf`, p. 5, section II / Back-End Fabrication / CMP; evidence `SC-EV-E1426DD81060C643`; as-of 2026-03-04; excerpt: “Chemical Mechanical Planarization (CMP): Between many deposition and metallization layers throughout the back-end process, chemical mechanical planarization (CMP) uses chemical and physical forces to create a microscopically flat surface for each successive layer of circuit features. A polishing pad with a liquid chemical called a “slurry” polishes the wafer surface until the desired nanometer top…”
- Temporal scope: categorical_source_scoped.

- SYSTEM_RECOMMENDED_DECISION: `CREATE_RELATION`.
- SYSTEM_RECOMMENDATION_REASON: A/B substantive consensus; frozen automated outcome: CREATE_RELATION.
- HUMAN_USER_DECISION = PENDING
- VALID NATIVE OPTIONS: REUSE_RELATION, CREATE_RELATION, KEEP_DOMAIN_SPECIFIC_RELATION, DEFER_RELATION, REJECT_RELATION; REUSE requires an explicit validated target ID and all options remain subject to frozen controls.

### Item 086 — SC-RL-0040 — Chemical Vapor Deposition → Semiconductor Process Gases

- ITEM_NUMBER: 86; ITEM_ID: `SC-RL-0040`; OBJECT_TYPE: relation.
- DOMAIN / context: `semiconductor` Semiconductor structured Foundation candidate against shared AI Hardware canonical catalog; cross-domain status: `candidate`.
- AUTOMATED_STAGE3_OUTCOME: `CREATE_RELATION`; CURRENT_CANONICAL_TARGET: `none`.
- Possible existing canonical IDs (unresolved unless explicitly reused): `none`.
- CANDIDATE_SUMMARY: Chemical Vapor Deposition → Semiconductor Process Gases; candidate type `uses`; comparison scope `SIA/BCG 2021 and SIA 2026; generic process-input class`; frozen candidate rationale: Source原文直接支持有界命题；仅供local review，不表示授权。
- WHY_HUMAN_REQUIRED: frozen Stage 3 mandatory review population; automated reasons: DISTINCT_RELATION_PROPOSAL, LOW_OR_UNKNOWN_CONFIDENCE.
- RISK_FLAGS: A=DISTINCT_RELATION_PROPOSAL, LOW_OR_UNKNOWN_CONFIDENCE; B=SCOPE_LIMIT.

**AI REVIEW A**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `CREATE_RELATION`; target: `{'from_node_id': 'NODE_B978F373FF68B837', 'to_node_id': 'NODE_827BB1ECF3990FC9', 'from_ref': 'SC-CN-0067', 'to_ref': 'SC-CN-0062', 'relation_type': 'uses', 'existing_relation_ids': []}`; confidence: MEDIUM; materiality: MEDIUM.
- reason: CVD uses Semiconductor Process Gases as a generic input class; no individual precursor is implied.
- evidence assessment: SIA/BCG explicitly lists gases used in CVD, alongside different uses as dopants and etchants.
- temporal scope assessed: {'source_scope': 'SIA/BCG 2021 and SIA 2026; generic process-input class', 'temporal_status': 'categorical_source_scoped', 'runtime_status': 'categorical', 'valid_from': '', 'valid_to': '', 'source_as_of': ['2021-04', '2026-03-04']}
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'same', 'object_type': 'compatible', 'scope': 'compatible', 'granularity': 'unknown', 'quarantine': 'clear', 'ontology': 'compatible', 'evidence_sufficiency': 'sufficient', 'temporal': 'compatible'}

**AI REVIEW B**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `CREATE_RELATION`; target: `none`; confidence: MEDIUM; materiality: LOW.
- reason: Chemical Vapor Deposition → Semiconductor Process Gases (uses): SIA says some process gases are used in CVD; support a class edge without naming a specific gas.
- evidence assessment: SC-EV-D3003F5E735D6873 from SC-P0-002_SIA_BCG_Global_Semiconductor_Supply_Chain_2021.pdf [source SC-PHYS-B33C40EBCB5756F7; SHA b33c40ebcb5756f76e887ba2664f97736252e68ba7bfbedc2d628ce2d7cbc08d; PDF p.22, Materials]: Gases: Used to protect wafers from atmospheric exposure. Other gases are used in the semiconductor manufacturing process as dopants, dry etchants, and in chemical vapor deposition (CVD). | SC-EV-9DD6210673D502A2 from SC-P0-008_Senate-EPW-testimony-3.4.2026.pdf [source SC-PHYS-C5B6DC633E156218; SHA c5b6dc633e156218eb950f2dee88f43fbdcc4fc1744a5924f12b977f5cb7df71; PDF p.5, II / Back-End Fabrication / Metallization]: Metals may be sputtered from solid targets, deposited via chemical vapor deposition using gaseous or liquid precursors, or—in the case of copper—electroplated from a copper solution. Boundary: Chemical Vapor Deposition → Semiconductor Process Gases (uses): SIA says some process gases are used in CVD; support a class edge without naming a specific gas. All source excerpts remain UNAUTHORIZED_CANDIDATE evidence.
- temporal scope assessed: categorical_source_scoped
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'same', 'object_type': 'compatible', 'scope': 'compatible', 'granularity': 'same', 'quarantine': 'clear', 'ontology': 'compatible', 'evidence_sufficiency': 'sufficient', 'temporal': 'compatible'}

**A/B RECONCILIATION**

- A_B_SUBSTANTIVE_AGREEMENT; disagreement type: none; native-operation conflict: false; target conflict: false.
- Interpretation differences: none.
- Reconciliation assessment: Both reviewers support the same frozen endpoints, relation type, source scope, and evidence. Granularity labels refer to parent-child levels versus the proposed edge; bounded evidence comments do not change the edge.
- Non-material rubric-label differences retained for audit: granularity.

**EVIDENCE SUMMARY**

- Source `SC-PHYS-B33C40EBCB5756F7` (SHA-256 `b33c40ebcb5756f76e887ba2664f97736252e68ba7bfbedc2d628ce2d7cbc08d`), file `SC-P0-002_SIA_BCG_Global_Semiconductor_Supply_Chain_2021.pdf`, p. 22, section Materials; evidence `SC-EV-D3003F5E735D6873`; as-of 2021-04; excerpt: “Gases: Used to protect wafers from atmospheric exposure. Other gases are used in the semiconductor manufacturing process as dopants, dry etchants, and in chemical vapor deposition (CVD).”
- Source `SC-PHYS-C5B6DC633E156218` (SHA-256 `c5b6dc633e156218eb950f2dee88f43fbdcc4fc1744a5924f12b977f5cb7df71`), file `SC-P0-008_Senate-EPW-testimony-3.4.2026.pdf`, p. 5, section II / Back-End Fabrication / Metallization; evidence `SC-EV-9DD6210673D502A2`; as-of 2026-03-04; excerpt: “Metals may be sputtered from solid targets, deposited via chemical vapor deposition using gaseous or liquid precursors, or—in the case of copper—electroplated from a copper solution.”
- Temporal scope: categorical_source_scoped.

- SYSTEM_RECOMMENDED_DECISION: `CREATE_RELATION`.
- SYSTEM_RECOMMENDATION_REASON: A/B substantive consensus; frozen automated outcome: CREATE_RELATION.
- HUMAN_USER_DECISION = PENDING
- VALID NATIVE OPTIONS: REUSE_RELATION, CREATE_RELATION, KEEP_DOMAIN_SPECIFIC_RELATION, DEFER_RELATION, REJECT_RELATION; REUSE requires an explicit validated target ID and all options remain subject to frozen controls.

### Item 087 — SC-RL-0041 — Sputtering → Sputtering Target

- ITEM_NUMBER: 87; ITEM_ID: `SC-RL-0041`; OBJECT_TYPE: relation.
- DOMAIN / context: `semiconductor` Semiconductor structured Foundation candidate against shared AI Hardware canonical catalog; cross-domain status: `candidate`.
- AUTOMATED_STAGE3_OUTCOME: `CREATE_RELATION`; CURRENT_CANONICAL_TARGET: `none`.
- Possible existing canonical IDs (unresolved unless explicitly reused): `none`.
- CANDIDATE_SUMMARY: Sputtering → Sputtering Target; candidate type `uses`; comparison scope `SIA 2026 testimony / metallization`; frozen candidate rationale: Source原文直接支持有界命题；仅供local review，不表示授权。
- WHY_HUMAN_REQUIRED: frozen Stage 3 mandatory review population; automated reasons: DISTINCT_RELATION_PROPOSAL, LOW_OR_UNKNOWN_CONFIDENCE.
- RISK_FLAGS: A=DISTINCT_RELATION_PROPOSAL, LOW_OR_UNKNOWN_CONFIDENCE; B=none.

**AI REVIEW A**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `CREATE_RELATION`; target: `{'from_node_id': 'NODE_ACA917DEC746327B', 'to_node_id': 'NODE_25601851C52EAD4B', 'from_ref': 'SC-CN-0068', 'to_ref': 'SC-CN-0069', 'relation_type': 'uses', 'existing_relation_ids': []}`; confidence: HIGH; materiality: MEDIUM.
- reason: Sputtering uses a solid Sputtering Target in the metallization method described.
- evidence assessment: SIA contrasts metal sputtering from solid targets with CVD and copper electroplating.
- temporal scope assessed: {'source_scope': 'SIA 2026 testimony / metallization', 'temporal_status': 'categorical_source_scoped', 'runtime_status': 'categorical', 'valid_from': '', 'valid_to': '', 'source_as_of': ['2026-03-04']}
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'same', 'object_type': 'compatible', 'scope': 'compatible', 'granularity': 'unknown', 'quarantine': 'clear', 'ontology': 'compatible', 'evidence_sufficiency': 'sufficient', 'temporal': 'compatible'}

**AI REVIEW B**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `CREATE_RELATION`; target: `none`; confidence: HIGH; materiality: LOW.
- reason: Sputtering → Sputtering Target (uses): SIA says metals may be sputtered from solid targets; support a process-to-target-class uses edge.
- evidence assessment: SC-EV-9DD6210673D502A2 from SC-P0-008_Senate-EPW-testimony-3.4.2026.pdf [source SC-PHYS-C5B6DC633E156218; SHA c5b6dc633e156218eb950f2dee88f43fbdcc4fc1744a5924f12b977f5cb7df71; PDF p.5, II / Back-End Fabrication / Metallization]: Metals may be sputtered from solid targets, deposited via chemical vapor deposition using gaseous or liquid precursors, or—in the case of copper—electroplated from a copper solution. Boundary: Sputtering → Sputtering Target (uses): SIA says metals may be sputtered from solid targets; support a process-to-target-class uses edge. All source excerpts remain UNAUTHORIZED_CANDIDATE evidence.
- temporal scope assessed: categorical_source_scoped
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'same', 'object_type': 'compatible', 'scope': 'compatible', 'granularity': 'same', 'quarantine': 'clear', 'ontology': 'compatible', 'evidence_sufficiency': 'sufficient', 'temporal': 'compatible'}

**A/B RECONCILIATION**

- A_B_SUBSTANTIVE_AGREEMENT; disagreement type: none; native-operation conflict: false; target conflict: false.
- Interpretation differences: none.
- Reconciliation assessment: Both reviewers support the same frozen endpoints, relation type, source scope, and evidence. Granularity labels refer to parent-child levels versus the proposed edge; bounded evidence comments do not change the edge.
- Non-material rubric-label differences retained for audit: granularity.

**EVIDENCE SUMMARY**

- Source `SC-PHYS-C5B6DC633E156218` (SHA-256 `c5b6dc633e156218eb950f2dee88f43fbdcc4fc1744a5924f12b977f5cb7df71`), file `SC-P0-008_Senate-EPW-testimony-3.4.2026.pdf`, p. 5, section II / Back-End Fabrication / Metallization; evidence `SC-EV-9DD6210673D502A2`; as-of 2026-03-04; excerpt: “Metals may be sputtered from solid targets, deposited via chemical vapor deposition using gaseous or liquid precursors, or—in the case of copper—electroplated from a copper solution.”
- Temporal scope: categorical_source_scoped.

- SYSTEM_RECOMMENDED_DECISION: `CREATE_RELATION`.
- SYSTEM_RECOMMENDATION_REASON: A/B substantive consensus; frozen automated outcome: CREATE_RELATION.
- HUMAN_USER_DECISION = PENDING
- VALID NATIVE OPTIONS: REUSE_RELATION, CREATE_RELATION, KEEP_DOMAIN_SPECIFIC_RELATION, DEFER_RELATION, REJECT_RELATION; REUSE requires an explicit validated target ID and all options remain subject to frozen controls.

### Item 088 — SC-RL-0042 — Thermal Oxidation → Oxidation Furnace

- ITEM_NUMBER: 88; ITEM_ID: `SC-RL-0042`; OBJECT_TYPE: relation.
- DOMAIN / context: `semiconductor` Semiconductor structured Foundation candidate against shared AI Hardware canonical catalog; cross-domain status: `candidate`.
- AUTOMATED_STAGE3_OUTCOME: `CREATE_RELATION`; CURRENT_CANONICAL_TARGET: `none`.
- Possible existing canonical IDs (unresolved unless explicitly reused): `none`.
- CANDIDATE_SUMMARY: Thermal Oxidation → Oxidation Furnace; candidate type `uses`; comparison scope `SIA 2026 testimony / thermal oxidation`; frozen candidate rationale: Source原文直接支持有界命题；仅供local review，不表示授权。
- WHY_HUMAN_REQUIRED: frozen Stage 3 mandatory review population; automated reasons: DISTINCT_RELATION_PROPOSAL, LOW_OR_UNKNOWN_CONFIDENCE.
- RISK_FLAGS: A=DISTINCT_RELATION_PROPOSAL, LOW_OR_UNKNOWN_CONFIDENCE; B=none.

**AI REVIEW A**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `CREATE_RELATION`; target: `{'from_node_id': 'NODE_BF8A35B76A72573D', 'to_node_id': 'NODE_3EFAF401A1A5E24F', 'from_ref': 'SC-CN-0064', 'to_ref': 'SC-CN-0065', 'relation_type': 'uses', 'existing_relation_ids': []}`; confidence: HIGH; materiality: MEDIUM.
- reason: Thermal Oxidation uses an Oxidation Furnace in the described dry/wet oxidation process.
- evidence assessment: SIA states wafers are heated near 1000°C in an oxidation furnace before oxygen or vapor exposure.
- temporal scope assessed: {'source_scope': 'SIA 2026 testimony / thermal oxidation', 'temporal_status': 'categorical_source_scoped', 'runtime_status': 'categorical', 'valid_from': '', 'valid_to': '', 'source_as_of': ['2026-03-04']}
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'same', 'object_type': 'compatible', 'scope': 'compatible', 'granularity': 'unknown', 'quarantine': 'clear', 'ontology': 'compatible', 'evidence_sufficiency': 'sufficient', 'temporal': 'compatible'}

**AI REVIEW B**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `CREATE_RELATION`; target: `none`; confidence: HIGH; materiality: LOW.
- reason: Thermal Oxidation → Oxidation Furnace (uses): SIA places wafers in an oxidation furnace near 1000 C; Thermal Oxidation uses that Equipment.
- evidence assessment: SC-EV-2E46BB1C1CE805D8 from SC-P0-008_Senate-EPW-testimony-3.4.2026.pdf [source SC-PHYS-C5B6DC633E156218; SHA c5b6dc633e156218eb950f2dee88f43fbdcc4fc1744a5924f12b977f5cb7df71; PDF p.4, II / Front-End Fabrication / Thermal Oxidation]: The silicon wafers are then heated to approximately 1000°C in an oxidation furnace and exposed to ultra-pure oxygen (dry oxidation) or water vapor (wet oxidation). Under carefully controlled conditions, a silicon dioxide insulator film of uniform thickness forms on the wafer surface. Boundary: Thermal Oxidation → Oxidation Furnace (uses): SIA places wafers in an oxidation furnace near 1000 C; Thermal Oxidation uses that Equipment. All source excerpts remain UNAUTHORIZED_CANDIDATE evidence.
- temporal scope assessed: categorical_source_scoped
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'same', 'object_type': 'compatible', 'scope': 'compatible', 'granularity': 'same', 'quarantine': 'clear', 'ontology': 'compatible', 'evidence_sufficiency': 'sufficient', 'temporal': 'compatible'}

**A/B RECONCILIATION**

- A_B_SUBSTANTIVE_AGREEMENT; disagreement type: none; native-operation conflict: false; target conflict: false.
- Interpretation differences: none.
- Reconciliation assessment: Both reviewers support the same frozen endpoints, relation type, source scope, and evidence. Granularity labels refer to parent-child levels versus the proposed edge; bounded evidence comments do not change the edge.
- Non-material rubric-label differences retained for audit: granularity.

**EVIDENCE SUMMARY**

- Source `SC-PHYS-C5B6DC633E156218` (SHA-256 `c5b6dc633e156218eb950f2dee88f43fbdcc4fc1744a5924f12b977f5cb7df71`), file `SC-P0-008_Senate-EPW-testimony-3.4.2026.pdf`, p. 4, section II / Front-End Fabrication / Thermal Oxidation; evidence `SC-EV-2E46BB1C1CE805D8`; as-of 2026-03-04; excerpt: “The silicon wafers are then heated to approximately 1000°C in an oxidation furnace and exposed to ultra-pure oxygen (dry oxidation) or water vapor (wet oxidation). Under carefully controlled conditions, a silicon dioxide insulator film of uniform thickness forms on the wafer surface.”
- Temporal scope: categorical_source_scoped.

- SYSTEM_RECOMMENDED_DECISION: `CREATE_RELATION`.
- SYSTEM_RECOMMENDATION_REASON: A/B substantive consensus; frozen automated outcome: CREATE_RELATION.
- HUMAN_USER_DECISION = PENDING
- VALID NATIVE OPTIONS: REUSE_RELATION, CREATE_RELATION, KEEP_DOMAIN_SPECIFIC_RELATION, DEFER_RELATION, REJECT_RELATION; REUSE requires an explicit validated target ID and all options remain subject to frozen controls.

### Item 089 — SC-RL-0043 — Wafer Cleaning → Ultrapure Water

- ITEM_NUMBER: 89; ITEM_ID: `SC-RL-0043`; OBJECT_TYPE: relation.
- DOMAIN / context: `semiconductor` Semiconductor structured Foundation candidate against shared AI Hardware canonical catalog; cross-domain status: `candidate`.
- AUTOMATED_STAGE3_OUTCOME: `CREATE_RELATION`; CURRENT_CANONICAL_TARGET: `none`.
- Possible existing canonical IDs (unresolved unless explicitly reused): `none`.
- CANDIDATE_SUMMARY: Wafer Cleaning → Ultrapure Water; candidate type `uses`; comparison scope `IRDS Yield 2025 / last Si-channel cleaning before dielectric deposition`; frozen candidate rationale: Source原文直接支持有界命题；仅供local review，不表示授权。
- WHY_HUMAN_REQUIRED: frozen Stage 3 mandatory review population; automated reasons: DISTINCT_RELATION_PROPOSAL, LOW_OR_UNKNOWN_CONFIDENCE.
- RISK_FLAGS: A=DISTINCT_RELATION_PROPOSAL, LOW_OR_UNKNOWN_CONFIDENCE; B=FROZEN_STAGE2_DECISION, SCOPE_LIMIT.

**AI REVIEW A**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `CREATE_RELATION`; target: `{'from_node_id': 'NODE_142DE7A2558ABAA5', 'to_node_id': 'NODE_E82590B91C83BFBD', 'from_ref': 'SC-CN-0161', 'to_ref': 'SC-CN-0160', 'relation_type': 'uses', 'existing_relation_ids': []}`; confidence: MEDIUM; materiality: MEDIUM.
- reason: Wafer Cleaning uses Ultrapure Water for the specified last Si-channel cleaning step, without generalizing to every clean.
- evidence assessment: IRDS mentions ultrapure water used in last cleaning before oxide and high-k deposition, despite discussing it as a contamination source.
- temporal scope assessed: {'source_scope': 'IRDS Yield 2025 / last Si-channel cleaning before dielectric deposition', 'temporal_status': 'categorical_source_scoped', 'runtime_status': 'categorical', 'valid_from': '', 'valid_to': '', 'source_as_of': ['2025']}
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'same', 'object_type': 'compatible', 'scope': 'compatible', 'granularity': 'unknown', 'quarantine': 'clear', 'ontology': 'compatible', 'evidence_sufficiency': 'sufficient', 'temporal': 'compatible'}

**AI REVIEW B**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `CREATE_RELATION`; target: `none`; confidence: MEDIUM; materiality: LOW.
- reason: Wafer Cleaning → Ultrapure Water (uses): IRDS calls ultrapure water a contamination source in last Si-channel cleaning; uses is indirect and narrow.
- evidence assessment: SC-EV-D5DC766A624FE286 from SC-P0-012_2025_IRDS_Yield_Enhancement_AMC.pdf [source SC-PHYS-AA294FCF8FEDE75B; SHA aa294fcf8fede75be6e2c23c6ec75a6f3504538dceb87eb51edda0134526b34b; PDF p.10, Yield / contamination and reliability]: Typical sources of contamination are from airborne sources and ultrapure water used in last cleaning steps of the Si channel before oxide and high-k dielectric (e.g. HfO2) deposition. Boundary: Wafer Cleaning → Ultrapure Water (uses): IRDS calls ultrapure water a contamination source in last Si-channel cleaning; uses is indirect and narrow. All source excerpts remain UNAUTHORIZED_CANDIDATE evidence.
- temporal scope assessed: categorical_source_scoped
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'same', 'object_type': 'compatible', 'scope': 'compatible', 'granularity': 'same', 'quarantine': 'clear', 'ontology': 'compatible', 'evidence_sufficiency': 'limited', 'temporal': 'compatible'}

**A/B RECONCILIATION**

- A_B_SUBSTANTIVE_AGREEMENT; disagreement type: none; native-operation conflict: false; target conflict: false.
- Interpretation differences: none.
- Reconciliation assessment: Both reviewers support the same frozen endpoints, relation type, source scope, and evidence. Granularity labels refer to parent-child levels versus the proposed edge; bounded evidence comments do not change the edge.
- Non-material rubric-label differences retained for audit: evidence_sufficiency, granularity.

**EVIDENCE SUMMARY**

- Source `SC-PHYS-AA294FCF8FEDE75B` (SHA-256 `aa294fcf8fede75be6e2c23c6ec75a6f3504538dceb87eb51edda0134526b34b`), file `SC-P0-012_2025_IRDS_Yield_Enhancement_AMC.pdf`, p. 10, section Yield / contamination and reliability; evidence `SC-EV-D5DC766A624FE286`; as-of 2025; excerpt: “Typical sources of contamination are from airborne sources and ultrapure water used in last cleaning steps of the Si channel before oxide and high-k dielectric (e.g. HfO2) deposition.”
- Temporal scope: categorical_source_scoped.

- SYSTEM_RECOMMENDED_DECISION: `CREATE_RELATION`.
- SYSTEM_RECOMMENDATION_REASON: A/B substantive consensus; frozen automated outcome: CREATE_RELATION.
- HUMAN_USER_DECISION = PENDING
- VALID NATIVE OPTIONS: REUSE_RELATION, CREATE_RELATION, KEEP_DOMAIN_SPECIFIC_RELATION, DEFER_RELATION, REJECT_RELATION; REUSE requires an explicit validated target ID and all options remain subject to frozen controls.

### Item 090 — SC-RL-0044 — Wire Bonding → Wire Bonding Machine

- ITEM_NUMBER: 90; ITEM_ID: `SC-RL-0044`; OBJECT_TYPE: relation.
- DOMAIN / context: `semiconductor` Semiconductor structured Foundation candidate against shared AI Hardware canonical catalog; cross-domain status: `candidate`.
- AUTOMATED_STAGE3_OUTCOME: `CREATE_RELATION`; CURRENT_CANONICAL_TARGET: `none`.
- Possible existing canonical IDs (unresolved unless explicitly reused): `none`.
- CANDIDATE_SUMMARY: Wire Bonding → Wire Bonding Machine; candidate type `uses`; comparison scope `SIA 2026 testimony / packaging`; frozen candidate rationale: Source原文直接支持有界命题；仅供local review，不表示授权。
- WHY_HUMAN_REQUIRED: frozen Stage 3 mandatory review population; automated reasons: DISTINCT_RELATION_PROPOSAL, LOW_OR_UNKNOWN_CONFIDENCE.
- RISK_FLAGS: A=DISTINCT_RELATION_PROPOSAL, LOW_OR_UNKNOWN_CONFIDENCE; B=none.

**AI REVIEW A**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `CREATE_RELATION`; target: `{'from_node_id': 'NODE_3251B0CC45A7664F', 'to_node_id': 'NODE_AF55F670500B2B21', 'from_ref': 'SC-CN-0079', 'to_ref': 'SC-CN-0080', 'relation_type': 'uses', 'existing_relation_ids': []}`; confidence: HIGH; materiality: MEDIUM.
- reason: Wire Bonding uses a Wire Bonding Machine; the alternative solder-sphere path is outside this edge.
- evidence assessment: SIA explicitly says a wire bonding machine attaches wires for package connections.
- temporal scope assessed: {'source_scope': 'SIA 2026 testimony / packaging', 'temporal_status': 'categorical_source_scoped', 'runtime_status': 'categorical', 'valid_from': '', 'valid_to': '', 'source_as_of': ['2026-03-04']}
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'same', 'object_type': 'compatible', 'scope': 'compatible', 'granularity': 'unknown', 'quarantine': 'clear', 'ontology': 'compatible', 'evidence_sufficiency': 'sufficient', 'temporal': 'compatible'}

**AI REVIEW B**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `CREATE_RELATION`; target: `none`; confidence: HIGH; materiality: LOW.
- reason: Wire Bonding → Wire Bonding Machine (uses): SIA states a wire bonding machine attaches package wires; process-to-equipment use is direct.
- evidence assessment: SC-EV-10E6259F18C93BE1 from SC-P0-008_Senate-EPW-testimony-3.4.2026.pdf [source SC-PHYS-C5B6DC633E156218; SHA c5b6dc633e156218eb950f2dee88f43fbdcc4fc1744a5924f12b977f5cb7df71; PDF p.6, II / Packaging]: A wire bonding machine attaches wires—a fraction of the width of a human hair—or solder spheres are added to facilitate electrical connection. Boundary: Wire Bonding → Wire Bonding Machine (uses): SIA states a wire bonding machine attaches package wires; process-to-equipment use is direct. All source excerpts remain UNAUTHORIZED_CANDIDATE evidence.
- temporal scope assessed: categorical_source_scoped
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'same', 'object_type': 'compatible', 'scope': 'compatible', 'granularity': 'same', 'quarantine': 'clear', 'ontology': 'compatible', 'evidence_sufficiency': 'sufficient', 'temporal': 'compatible'}

**A/B RECONCILIATION**

- A_B_SUBSTANTIVE_AGREEMENT; disagreement type: none; native-operation conflict: false; target conflict: false.
- Interpretation differences: none.
- Reconciliation assessment: Both reviewers support the same frozen endpoints, relation type, source scope, and evidence. Granularity labels refer to parent-child levels versus the proposed edge; bounded evidence comments do not change the edge.
- Non-material rubric-label differences retained for audit: granularity.

**EVIDENCE SUMMARY**

- Source `SC-PHYS-C5B6DC633E156218` (SHA-256 `c5b6dc633e156218eb950f2dee88f43fbdcc4fc1744a5924f12b977f5cb7df71`), file `SC-P0-008_Senate-EPW-testimony-3.4.2026.pdf`, p. 6, section II / Packaging; evidence `SC-EV-10E6259F18C93BE1`; as-of 2026-03-04; excerpt: “A wire bonding machine attaches wires—a fraction of the width of a human hair—or solder spheres are added to facilitate electrical connection.”
- Temporal scope: categorical_source_scoped.

- SYSTEM_RECOMMENDED_DECISION: `CREATE_RELATION`.
- SYSTEM_RECOMMENDATION_REASON: A/B substantive consensus; frozen automated outcome: CREATE_RELATION.
- HUMAN_USER_DECISION = PENDING
- VALID NATIVE OPTIONS: REUSE_RELATION, CREATE_RELATION, KEEP_DOMAIN_SPECIFIC_RELATION, DEFER_RELATION, REJECT_RELATION; REUSE requires an explicit validated target ID and all options remain subject to frozen controls.

### Item 091 — SC-RL-0045 — Wafer Electrical Test → Semiconductor Electrical Test Equipment

- ITEM_NUMBER: 91; ITEM_ID: `SC-RL-0045`; OBJECT_TYPE: relation.
- DOMAIN / context: `semiconductor` Semiconductor structured Foundation candidate against shared AI Hardware canonical catalog; cross-domain status: `candidate`.
- AUTOMATED_STAGE3_OUTCOME: `CREATE_RELATION`; CURRENT_CANONICAL_TARGET: `none`.
- Possible existing canonical IDs (unresolved unless explicitly reused): `none`.
- CANDIDATE_SUMMARY: Wafer Electrical Test → Semiconductor Electrical Test Equipment; candidate type `uses`; comparison scope `SIA 2026 testimony / wafer electrical test`; frozen candidate rationale: Source原文直接支持有界命题；仅供local review，不表示授权。
- WHY_HUMAN_REQUIRED: frozen Stage 3 mandatory review population; automated reasons: DISTINCT_RELATION_PROPOSAL, LOW_OR_UNKNOWN_CONFIDENCE.
- RISK_FLAGS: A=DISTINCT_RELATION_PROPOSAL, LOW_OR_UNKNOWN_CONFIDENCE; B=none.

**AI REVIEW A**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `CREATE_RELATION`; target: `{'from_node_id': 'NODE_D84A8FF56B6E5184', 'to_node_id': 'NODE_DBDB929B816162A6', 'from_ref': 'SC-CN-0076', 'to_ref': 'SC-CN-0077', 'relation_type': 'uses', 'existing_relation_ids': []}`; confidence: MEDIUM; materiality: MEDIUM.
- reason: Wafer Electrical Test uses automated semiconductor test equipment, conditional on admitting the new generic equipment identity.
- evidence assessment: SIA describes a computer-driven system checking functionality of each wafer chip before rejection marking.
- temporal scope assessed: {'source_scope': 'SIA 2026 testimony / wafer electrical test', 'temporal_status': 'categorical_source_scoped', 'runtime_status': 'categorical', 'valid_from': '', 'valid_to': '', 'source_as_of': ['2026-03-04']}
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'same', 'object_type': 'compatible', 'scope': 'compatible', 'granularity': 'unknown', 'quarantine': 'clear', 'ontology': 'compatible', 'evidence_sufficiency': 'sufficient', 'temporal': 'compatible'}

**AI REVIEW B**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `CREATE_RELATION`; target: `none`; confidence: HIGH; materiality: LOW.
- reason: Wafer Electrical Test → Semiconductor Electrical Test Equipment (uses): SIA describes an automatic test system checking chips on wafers; this equipment differs from burn-in.
- evidence assessment: SC-EV-B2A0CD10691438AE from SC-P0-008_Senate-EPW-testimony-3.4.2026.pdf [source SC-PHYS-C5B6DC633E156218; SHA c5b6dc633e156218eb950f2dee88f43fbdcc4fc1744a5924f12b977f5cb7df71; PDF p.5, II / Electrical Test]: Electrical Test: An automatic, computer-driven test system checks the functionality of each chip on the wafer. Chips that do not pass are marked for automatic rejection. Boundary: Wafer Electrical Test → Semiconductor Electrical Test Equipment (uses): SIA describes an automatic test system checking chips on wafers; this equipment differs from burn-in. All source excerpts remain UNAUTHORIZED_CANDIDATE evidence.
- temporal scope assessed: categorical_source_scoped
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'same', 'object_type': 'compatible', 'scope': 'compatible', 'granularity': 'same', 'quarantine': 'clear', 'ontology': 'compatible', 'evidence_sufficiency': 'sufficient', 'temporal': 'compatible'}

**A/B RECONCILIATION**

- A_B_SUBSTANTIVE_AGREEMENT; disagreement type: none; native-operation conflict: false; target conflict: false.
- Interpretation differences: none.
- Reconciliation assessment: Both reviewers support the same frozen endpoints, relation type, source scope, and evidence. Granularity labels refer to parent-child levels versus the proposed edge; bounded evidence comments do not change the edge.
- Non-material rubric-label differences retained for audit: granularity.

**EVIDENCE SUMMARY**

- Source `SC-PHYS-C5B6DC633E156218` (SHA-256 `c5b6dc633e156218eb950f2dee88f43fbdcc4fc1744a5924f12b977f5cb7df71`), file `SC-P0-008_Senate-EPW-testimony-3.4.2026.pdf`, p. 5, section II / Electrical Test; evidence `SC-EV-B2A0CD10691438AE`; as-of 2026-03-04; excerpt: “Electrical Test: An automatic, computer-driven test system checks the functionality of each chip on the wafer. Chips that do not pass are marked for automatic rejection.”
- Temporal scope: categorical_source_scoped.

- SYSTEM_RECOMMENDED_DECISION: `CREATE_RELATION`.
- SYSTEM_RECOMMENDATION_REASON: A/B substantive consensus; frozen automated outcome: CREATE_RELATION.
- HUMAN_USER_DECISION = PENDING
- VALID NATIVE OPTIONS: REUSE_RELATION, CREATE_RELATION, KEEP_DOMAIN_SPECIFIC_RELATION, DEFER_RELATION, REJECT_RELATION; REUSE requires an explicit validated target ID and all options remain subject to frozen controls.

### Item 092 — SC-RL-0046 — Die Attach → Package Substrate

- ITEM_NUMBER: 92; ITEM_ID: `SC-RL-0046`; OBJECT_TYPE: relation.
- DOMAIN / context: `semiconductor` Semiconductor structured Foundation candidate against shared AI Hardware canonical catalog; cross-domain status: `candidate`.
- AUTOMATED_STAGE3_OUTCOME: `DEFER_RELATION`; CURRENT_CANONICAL_TARGET: `none`.
- Possible existing canonical IDs (unresolved unless explicitly reused): `none`.
- CANDIDATE_SUMMARY: Die Attach → Package Substrate; candidate type `uses`; comparison scope `Intel 2025 chip-attach example; not all packages`; frozen candidate rationale: 一个或两个端点尚未通过身份候选准入；证据保留，不提前授权端点。
- WHY_HUMAN_REQUIRED: frozen Stage 3 mandatory review population; automated reasons: ENDPOINT_AMBIGUITY, EVIDENCE_WARNING, LOW_OR_UNKNOWN_CONFIDENCE, RELATION_AMBIGUITY.
- RISK_FLAGS: A=ENDPOINT_AMBIGUITY, EVIDENCE_WARNING, LOW_OR_UNKNOWN_CONFIDENCE, RELATION_AMBIGUITY; B=FROZEN_STAGE2_DECISION, UNRESOLVED_RELATION, ENDPOINT_OR_RECONCILIATION.

**AI REVIEW A**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `DEFER_RELATION`; target: `{'from_node_id': 'NODE_1C2962E7272B0409', 'to_node_id': None, 'from_ref': 'SC-CN-0087', 'to_ref': 'SC-CN-0031', 'relation_type': 'uses', 'existing_relation_ids': []}`; confidence: HIGH; materiality: MEDIUM.
- reason: Die Attach connects die to Package Substrate in the Intel example, but the general substrate endpoint remains held.
- evidence assessment: Intel says its chip-attach module affixes dies and components to the substrate; it does not define all package designs.
- temporal scope assessed: {'source_scope': 'Intel 2025 chip-attach example; not all packages', 'temporal_status': 'categorical_source_scoped', 'runtime_status': 'categorical', 'valid_from': '', 'valid_to': '', 'source_as_of': ['2025-02-19']}
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'ambiguous', 'object_type': 'unknown', 'scope': 'unknown', 'granularity': 'unknown', 'quarantine': 'clear', 'ontology': 'compatible', 'evidence_sufficiency': 'sufficient', 'temporal': 'compatible'}

**AI REVIEW B**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `DEFER_RELATION`; target: `none`; confidence: MEDIUM; materiality: HIGH.
- reason: Die Attach → Package Substrate (uses): Intel says chip attach affixes die to substrate, but broad Package Substrate identity remains unresolved; do not activate this Stage 3 edge.
- evidence assessment: SC-EV-05E522303824DD15 from SC-P0-016_Intel_Assembly_and_Test.pdf [source SC-PHYS-792E7A66390A5C02; SHA 792e7a66390a5c02a43280077fb1e586a3e46f4abf215608dc831ce5ab665db4; PDF p.3, Step 1: Chip Attach]: A chip attach module (CAM) affixes die and any other required components (such as capacitors) to the substrate, which is the main body of the package. Boundary: Die Attach → Package Substrate (uses): Intel says chip attach affixes die to substrate, but broad Package Substrate identity remains unresolved; do not activate this Stage 3 edge. All source excerpts remain UNAUTHORIZED_CANDIDATE evidence.
- temporal scope assessed: categorical_source_scoped
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'ambiguous', 'object_type': 'unknown', 'scope': 'unknown', 'granularity': 'unknown', 'quarantine': 'clear', 'ontology': 'unresolved', 'evidence_sufficiency': 'limited', 'temporal': 'compatible'}

**A/B RECONCILIATION**

- A_B_SUBSTANTIVE_AGREEMENT; disagreement type: none; native-operation conflict: false; target conflict: false.
- Interpretation differences: none.
- Reconciliation assessment: Both reviewers hold the same endpoint, temporal, or ontology exception. Rubric labels compare concept support with authority for the relation.
- Non-material rubric-label differences retained for audit: evidence_sufficiency, ontology.

**EVIDENCE SUMMARY**

- Source `SC-PHYS-792E7A66390A5C02` (SHA-256 `792e7a66390a5c02a43280077fb1e586a3e46f4abf215608dc831ce5ab665db4`), file `SC-P0-016_Intel_Assembly_and_Test.pdf`, p. 3, section Step 1: Chip Attach; evidence `SC-EV-05E522303824DD15`; as-of 2025-02-19; excerpt: “A chip attach module (CAM) affixes die and any other required components (such as capacitors) to the substrate, which is the main body of the package.”
- Temporal scope: categorical_source_scoped.

- SYSTEM_RECOMMENDED_DECISION: `DEFER_RELATION`.
- SYSTEM_RECOMMENDATION_REASON: Frozen structural, Stage 2 decision, evidence, or temporal exception remains unresolved.
- HUMAN_USER_DECISION = PENDING
- VALID NATIVE OPTIONS: REUSE_RELATION, CREATE_RELATION, KEEP_DOMAIN_SPECIFIC_RELATION, DEFER_RELATION, REJECT_RELATION; REUSE requires an explicit validated target ID and all options remain subject to frozen controls.

### Item 093 — SC-RL-0047 — Package Lid Attach → Thermal Interface Material

- ITEM_NUMBER: 93; ITEM_ID: `SC-RL-0047`; OBJECT_TYPE: relation.
- DOMAIN / context: `semiconductor` Semiconductor structured Foundation candidate against shared AI Hardware canonical catalog; cross-domain status: `candidate`.
- AUTOMATED_STAGE3_OUTCOME: `CREATE_RELATION`; CURRENT_CANONICAL_TARGET: `none`.
- Possible existing canonical IDs (unresolved unless explicitly reused): `none`.
- CANDIDATE_SUMMARY: Package Lid Attach → Thermal Interface Material; candidate type `uses`; comparison scope `Intel 2025 package lid-attach example`; frozen candidate rationale: Source原文直接支持有界命题；仅供local review，不表示授权。
- WHY_HUMAN_REQUIRED: frozen Stage 3 mandatory review population; automated reasons: DISTINCT_RELATION_PROPOSAL, LOW_OR_UNKNOWN_CONFIDENCE.
- RISK_FLAGS: A=DISTINCT_RELATION_PROPOSAL, LOW_OR_UNKNOWN_CONFIDENCE; B=none.

**AI REVIEW A**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `CREATE_RELATION`; target: `{'from_node_id': 'NODE_7B7F9D38AC8C2AFF', 'to_node_id': 'NODE_54340D9806971D42', 'from_ref': 'SC-CN-0088', 'to_ref': 'SC-CN-0089', 'relation_type': 'uses', 'existing_relation_ids': []}`; confidence: HIGH; materiality: MEDIUM.
- reason: Package Lid Attach uses Thermal Interface Material on the die in Intel's described sequence.
- evidence assessment: Intel explicitly places TIM application before heat-spreader placement.
- temporal scope assessed: {'source_scope': 'Intel 2025 package lid-attach example', 'temporal_status': 'categorical_source_scoped', 'runtime_status': 'categorical', 'valid_from': '', 'valid_to': '', 'source_as_of': ['2025-02-19']}
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'same', 'object_type': 'compatible', 'scope': 'compatible', 'granularity': 'unknown', 'quarantine': 'clear', 'ontology': 'compatible', 'evidence_sufficiency': 'sufficient', 'temporal': 'compatible'}

**AI REVIEW B**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `CREATE_RELATION`; target: `none`; confidence: HIGH; materiality: LOW.
- reason: Package Lid Attach → Thermal Interface Material (uses): Intel says machines apply thermal interface material before placing a lid; scope uses to this example.
- evidence assessment: SC-EV-B0D5FDA1CCB11F5D from SC-P0-016_Intel_Assembly_and_Test.pdf [source SC-PHYS-792E7A66390A5C02; SHA 792e7a66390a5c02a43280077fb1e586a3e46f4abf215608dc831ce5ab665db4; PDF p.5, Step 3: Lid Attach]: Machines apply thermal interface material onto the die and then place a heat spreader (known as a lid) on top. The lid helps dissipate heat. Boundary: Package Lid Attach → Thermal Interface Material (uses): Intel says machines apply thermal interface material before placing a lid; scope uses to this example. All source excerpts remain UNAUTHORIZED_CANDIDATE evidence.
- temporal scope assessed: categorical_source_scoped
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'same', 'object_type': 'compatible', 'scope': 'compatible', 'granularity': 'same', 'quarantine': 'clear', 'ontology': 'compatible', 'evidence_sufficiency': 'sufficient', 'temporal': 'compatible'}

**A/B RECONCILIATION**

- A_B_SUBSTANTIVE_AGREEMENT; disagreement type: none; native-operation conflict: false; target conflict: false.
- Interpretation differences: none.
- Reconciliation assessment: Both reviewers support the same frozen endpoints, relation type, source scope, and evidence. Granularity labels refer to parent-child levels versus the proposed edge; bounded evidence comments do not change the edge.
- Non-material rubric-label differences retained for audit: granularity.

**EVIDENCE SUMMARY**

- Source `SC-PHYS-792E7A66390A5C02` (SHA-256 `792e7a66390a5c02a43280077fb1e586a3e46f4abf215608dc831ce5ab665db4`), file `SC-P0-016_Intel_Assembly_and_Test.pdf`, p. 5, section Step 3: Lid Attach; evidence `SC-EV-B0D5FDA1CCB11F5D`; as-of 2025-02-19; excerpt: “Machines apply thermal interface material onto the die and then place a heat spreader (known as a lid) on top. The lid helps dissipate heat.”
- Temporal scope: categorical_source_scoped.

- SYSTEM_RECOMMENDED_DECISION: `CREATE_RELATION`.
- SYSTEM_RECOMMENDATION_REASON: A/B substantive consensus; frozen automated outcome: CREATE_RELATION.
- HUMAN_USER_DECISION = PENDING
- VALID NATIVE OPTIONS: REUSE_RELATION, CREATE_RELATION, KEEP_DOMAIN_SPECIFIC_RELATION, DEFER_RELATION, REJECT_RELATION; REUSE requires an explicit validated target ID and all options remain subject to frozen controls.

### Item 094 — SC-RL-0048 — Package Lid Attach → Package Heat Spreader

- ITEM_NUMBER: 94; ITEM_ID: `SC-RL-0048`; OBJECT_TYPE: relation.
- DOMAIN / context: `semiconductor` Semiconductor structured Foundation candidate against shared AI Hardware canonical catalog; cross-domain status: `candidate`.
- AUTOMATED_STAGE3_OUTCOME: `CREATE_RELATION`; CURRENT_CANONICAL_TARGET: `none`.
- Possible existing canonical IDs (unresolved unless explicitly reused): `none`.
- CANDIDATE_SUMMARY: Package Lid Attach → Package Heat Spreader; candidate type `uses`; comparison scope `Intel 2025 package lid-attach example`; frozen candidate rationale: Source原文直接支持有界命题；仅供local review，不表示授权。
- WHY_HUMAN_REQUIRED: frozen Stage 3 mandatory review population; automated reasons: DISTINCT_RELATION_PROPOSAL, LOW_OR_UNKNOWN_CONFIDENCE.
- RISK_FLAGS: A=DISTINCT_RELATION_PROPOSAL, LOW_OR_UNKNOWN_CONFIDENCE; B=none.

**AI REVIEW A**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `CREATE_RELATION`; target: `{'from_node_id': 'NODE_7B7F9D38AC8C2AFF', 'to_node_id': 'NODE_ABD7EFF80E2BE344', 'from_ref': 'SC-CN-0088', 'to_ref': 'SC-CN-0090', 'relation_type': 'uses', 'existing_relation_ids': []}`; confidence: HIGH; materiality: MEDIUM.
- reason: Package Lid Attach uses a Package Heat Spreader as the lid in Intel's example.
- evidence assessment: Intel says the heat spreader is placed on top and serves as a lid to dissipate heat.
- temporal scope assessed: {'source_scope': 'Intel 2025 package lid-attach example', 'temporal_status': 'categorical_source_scoped', 'runtime_status': 'categorical', 'valid_from': '', 'valid_to': '', 'source_as_of': ['2025-02-19']}
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'same', 'object_type': 'compatible', 'scope': 'compatible', 'granularity': 'unknown', 'quarantine': 'clear', 'ontology': 'compatible', 'evidence_sufficiency': 'sufficient', 'temporal': 'compatible'}

**AI REVIEW B**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `CREATE_RELATION`; target: `none`; confidence: HIGH; materiality: LOW.
- reason: Package Lid Attach → Package Heat Spreader (uses): Intel identifies the placed lid as a heat spreader; this is a distinct component input.
- evidence assessment: SC-EV-B0D5FDA1CCB11F5D from SC-P0-016_Intel_Assembly_and_Test.pdf [source SC-PHYS-792E7A66390A5C02; SHA 792e7a66390a5c02a43280077fb1e586a3e46f4abf215608dc831ce5ab665db4; PDF p.5, Step 3: Lid Attach]: Machines apply thermal interface material onto the die and then place a heat spreader (known as a lid) on top. The lid helps dissipate heat. Boundary: Package Lid Attach → Package Heat Spreader (uses): Intel identifies the placed lid as a heat spreader; this is a distinct component input. All source excerpts remain UNAUTHORIZED_CANDIDATE evidence.
- temporal scope assessed: categorical_source_scoped
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'same', 'object_type': 'compatible', 'scope': 'compatible', 'granularity': 'same', 'quarantine': 'clear', 'ontology': 'compatible', 'evidence_sufficiency': 'sufficient', 'temporal': 'compatible'}

**A/B RECONCILIATION**

- A_B_SUBSTANTIVE_AGREEMENT; disagreement type: none; native-operation conflict: false; target conflict: false.
- Interpretation differences: none.
- Reconciliation assessment: Both reviewers support the same frozen endpoints, relation type, source scope, and evidence. Granularity labels refer to parent-child levels versus the proposed edge; bounded evidence comments do not change the edge.
- Non-material rubric-label differences retained for audit: granularity.

**EVIDENCE SUMMARY**

- Source `SC-PHYS-792E7A66390A5C02` (SHA-256 `792e7a66390a5c02a43280077fb1e586a3e46f4abf215608dc831ce5ab665db4`), file `SC-P0-016_Intel_Assembly_and_Test.pdf`, p. 5, section Step 3: Lid Attach; evidence `SC-EV-B0D5FDA1CCB11F5D`; as-of 2025-02-19; excerpt: “Machines apply thermal interface material onto the die and then place a heat spreader (known as a lid) on top. The lid helps dissipate heat.”
- Temporal scope: categorical_source_scoped.

- SYSTEM_RECOMMENDED_DECISION: `CREATE_RELATION`.
- SYSTEM_RECOMMENDATION_REASON: A/B substantive consensus; frozen automated outcome: CREATE_RELATION.
- HUMAN_USER_DECISION = PENDING
- VALID NATIVE OPTIONS: REUSE_RELATION, CREATE_RELATION, KEEP_DOMAIN_SPECIFIC_RELATION, DEFER_RELATION, REJECT_RELATION; REUSE requires an explicit validated target ID and all options remain subject to frozen controls.

### Item 095 — SC-RL-0049 — Underfill Material → Packaging Encapsulant

- ITEM_NUMBER: 95; ITEM_ID: `SC-RL-0049`; OBJECT_TYPE: relation.
- DOMAIN / context: `semiconductor` Semiconductor structured Foundation candidate against shared AI Hardware canonical catalog; cross-domain status: `candidate`.
- AUTOMATED_STAGE3_OUTCOME: `DEFER_RELATION`; CURRENT_CANONICAL_TARGET: `none`.
- Possible existing canonical IDs (unresolved unless explicitly reused): `none`.
- CANDIDATE_SUMMARY: Underfill Material → Packaging Encapsulant; candidate type `part_of`; comparison scope `HIR 2025 Rev0.9 / March 2026 encapsulant taxonomy`; frozen candidate rationale: 一个或两个端点尚未通过身份候选准入；证据保留，不提前授权端点。
- WHY_HUMAN_REQUIRED: frozen Stage 3 mandatory review population; automated reasons: ENDPOINT_AMBIGUITY, EVIDENCE_WARNING, LOW_OR_UNKNOWN_CONFIDENCE, PARENT_OR_CAUSAL_REVIEW, RELATION_AMBIGUITY.
- RISK_FLAGS: A=ENDPOINT_AMBIGUITY, EVIDENCE_WARNING, LOW_OR_UNKNOWN_CONFIDENCE, PARENT_OR_CAUSAL_REVIEW, RELATION_AMBIGUITY; B=UNRESOLVED_RELATION, ENDPOINT_OR_RECONCILIATION.

**AI REVIEW A**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `DEFER_RELATION`; target: `{'from_node_id': 'NODE_20260817_397D3280', 'to_node_id': None, 'from_ref': 'NODE_20260817_397D3280', 'to_ref': 'SC-CN-0082', 'relation_type': 'part_of', 'existing_relation_ids': []}`; confidence: HIGH; materiality: MEDIUM.
- reason: Underfill is a kind of Packaging Encapsulant, but the parent material identity remains unresolved.
- evidence assessment: HIR explicitly lists underfill and molding compounds among encapsulants; source support does not admit the parent node.
- temporal scope assessed: {'source_scope': 'HIR 2025 Rev0.9 / March 2026 encapsulant taxonomy', 'temporal_status': 'categorical_source_scoped', 'runtime_status': 'categorical', 'valid_from': '', 'valid_to': '', 'source_as_of': ['2026-03']}
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'ambiguous', 'object_type': 'unknown', 'scope': 'unknown', 'granularity': 'different', 'quarantine': 'clear', 'ontology': 'compatible', 'evidence_sufficiency': 'sufficient', 'temporal': 'compatible'}

**AI REVIEW B**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `DEFER_RELATION`; target: `none`; confidence: MEDIUM; materiality: HIGH.
- reason: Underfill Material → Packaging Encapsulant (part_of): HIR lists underfill among encapsulants, but the parent Packaging Encapsulant identity awaits governance.
- evidence assessment: SC-EV-25E1F286A1FC489C from SC-P0-018_2025_HIR_Materials_and_Interfaces_Advanced_Packaging.pdf [source SC-PHYS-2E34AF6DD70E8C2C; SHA 2e34af6dd70e8c2c5de2aaabec15837693d1322abc0bb5820475188cd028a3f2; PDF p.25, 2.4.1 Materials for Reliability]: Encapsulant materials, including underfill and mold compounds, are vital for ensuring package reliability. They provide electrical isolation for the chip and interconnects, protect against mechanical damage and environmental contamination, and help distribute thermomechanical stresses during reliability testing and use conditions. Boundary: Underfill Material → Packaging Encapsulant (part_of): HIR lists underfill among encapsulants, but the parent Packaging Encapsulant identity awaits governance. All source excerpts remain UNAUTHORIZED_CANDIDATE evidence.
- temporal scope assessed: categorical_source_scoped
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'ambiguous', 'object_type': 'unknown', 'scope': 'unknown', 'granularity': 'unknown', 'quarantine': 'clear', 'ontology': 'unresolved', 'evidence_sufficiency': 'limited', 'temporal': 'compatible'}

**A/B RECONCILIATION**

- A_B_SUBSTANTIVE_AGREEMENT; disagreement type: none; native-operation conflict: false; target conflict: false.
- Interpretation differences: none.
- Reconciliation assessment: Both reviewers hold the same endpoint, temporal, or ontology exception. Rubric labels compare concept support with authority for the relation.
- Non-material rubric-label differences retained for audit: evidence_sufficiency, granularity, ontology.

**EVIDENCE SUMMARY**

- Source `SC-PHYS-2E34AF6DD70E8C2C` (SHA-256 `2e34af6dd70e8c2c5de2aaabec15837693d1322abc0bb5820475188cd028a3f2`), file `SC-P0-018_2025_HIR_Materials_and_Interfaces_Advanced_Packaging.pdf`, p. 25, section 2.4.1 Materials for Reliability; evidence `SC-EV-25E1F286A1FC489C`; as-of 2026-03; excerpt: “Encapsulant materials, including underfill and mold compounds, are vital for ensuring package reliability. They provide electrical isolation for the chip and interconnects, protect against mechanical damage and environmental contamination, and help distribute thermomechanical stresses during reliability testing and use conditions.”
- Temporal scope: categorical_source_scoped.

- SYSTEM_RECOMMENDED_DECISION: `DEFER_RELATION`.
- SYSTEM_RECOMMENDATION_REASON: Frozen structural, Stage 2 decision, evidence, or temporal exception remains unresolved.
- HUMAN_USER_DECISION = PENDING
- VALID NATIVE OPTIONS: REUSE_RELATION, CREATE_RELATION, KEEP_DOMAIN_SPECIFIC_RELATION, DEFER_RELATION, REJECT_RELATION; REUSE requires an explicit validated target ID and all options remain subject to frozen controls.

### Item 096 — SC-RL-0050 — Yield Management → Semiconductor Defect Inspection

- ITEM_NUMBER: 96; ITEM_ID: `SC-RL-0050`; OBJECT_TYPE: relation.
- DOMAIN / context: `semiconductor` Semiconductor structured Foundation candidate against shared AI Hardware canonical catalog; cross-domain status: `candidate`.
- AUTOMATED_STAGE3_OUTCOME: `CREATE_RELATION`; CURRENT_CANONICAL_TARGET: `none`.
- Possible existing canonical IDs (unresolved unless explicitly reused): `none`.
- CANDIDATE_SUMMARY: Yield Management → Semiconductor Defect Inspection; candidate type `uses`; comparison scope `IRDS Yield 2025 / traditional inline yield-management method`; frozen candidate rationale: Source原文直接支持有界命题；仅供local review，不表示授权。
- WHY_HUMAN_REQUIRED: frozen Stage 3 mandatory review population; automated reasons: DISTINCT_RELATION_PROPOSAL, LOW_OR_UNKNOWN_CONFIDENCE.
- RISK_FLAGS: A=DISTINCT_RELATION_PROPOSAL, LOW_OR_UNKNOWN_CONFIDENCE; B=SCOPE_LIMIT.

**AI REVIEW A**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `CREATE_RELATION`; target: `{'from_node_id': 'NODE_EFBD0210FC23869C', 'to_node_id': 'NODE_E007F116FD57BEFC', 'from_ref': 'SC-CN-0120', 'to_ref': 'SC-CN-0119', 'relation_type': 'uses', 'existing_relation_ids': []}`; confidence: MEDIUM; materiality: MEDIUM.
- reason: Yield Management uses inline Semiconductor Defect Inspection as a traditional feedback method, not the only method.
- evidence assessment: IRDS says traditional yield management depends on inline inspection to detect defects and correlate them with yield and test failures.
- temporal scope assessed: {'source_scope': 'IRDS Yield 2025 / traditional inline yield-management method', 'temporal_status': 'categorical_source_scoped', 'runtime_status': 'categorical', 'valid_from': '', 'valid_to': '', 'source_as_of': ['2025']}
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'same', 'object_type': 'compatible', 'scope': 'compatible', 'granularity': 'unknown', 'quarantine': 'clear', 'ontology': 'compatible', 'evidence_sufficiency': 'sufficient', 'temporal': 'compatible'}

**AI REVIEW B**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `CREATE_RELATION`; target: `none`; confidence: MEDIUM; materiality: LOW.
- reason: Yield Management → Semiconductor Defect Inspection (uses): IRDS says yield management uses inline inspection feedback and correlation to test fails; it does not prove inspection quality.
- evidence assessment: SC-EV-6C7601C6EFF1962D from SC-P0-012_2025_IRDS_Yield_Enhancement_AMC.pdf [source SC-PHYS-AA294FCF8FEDE75B; SHA aa294fcf8fede75be6e2c23c6ec75a6f3504538dceb87eb51edda0134526b34b; PDF p.28, Characterization, Inspection and Analysis]: Traditional yield management focuses on adequate inline inspection capabilities to detect and control all relevant defect types to set up short feedback loops as well as enable correlation to yield and test fails. Boundary: Yield Management → Semiconductor Defect Inspection (uses): IRDS says yield management uses inline inspection feedback and correlation to test fails; it does not prove inspection quality. All source excerpts remain UNAUTHORIZED_CANDIDATE evidence.
- temporal scope assessed: categorical_source_scoped
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'same', 'object_type': 'compatible', 'scope': 'compatible', 'granularity': 'same', 'quarantine': 'clear', 'ontology': 'compatible', 'evidence_sufficiency': 'limited', 'temporal': 'compatible'}

**A/B RECONCILIATION**

- A_B_SUBSTANTIVE_AGREEMENT; disagreement type: none; native-operation conflict: false; target conflict: false.
- Interpretation differences: none.
- Reconciliation assessment: Both reviewers support the same frozen endpoints, relation type, source scope, and evidence. Granularity labels refer to parent-child levels versus the proposed edge; bounded evidence comments do not change the edge.
- Non-material rubric-label differences retained for audit: evidence_sufficiency, granularity.

**EVIDENCE SUMMARY**

- Source `SC-PHYS-AA294FCF8FEDE75B` (SHA-256 `aa294fcf8fede75be6e2c23c6ec75a6f3504538dceb87eb51edda0134526b34b`), file `SC-P0-012_2025_IRDS_Yield_Enhancement_AMC.pdf`, p. 28, section Characterization, Inspection and Analysis; evidence `SC-EV-6C7601C6EFF1962D`; as-of 2025; excerpt: “Traditional yield management focuses on adequate inline inspection capabilities to detect and control all relevant defect types to set up short feedback loops as well as enable correlation to yield and test fails.”
- Temporal scope: categorical_source_scoped.

- SYSTEM_RECOMMENDED_DECISION: `CREATE_RELATION`.
- SYSTEM_RECOMMENDATION_REASON: A/B substantive consensus; frozen automated outcome: CREATE_RELATION.
- HUMAN_USER_DECISION = PENDING
- VALID NATIVE OPTIONS: REUSE_RELATION, CREATE_RELATION, KEEP_DOMAIN_SPECIFIC_RELATION, DEFER_RELATION, REJECT_RELATION; REUSE requires an explicit validated target ID and all options remain subject to frozen controls.

### Item 097 — SC-RL-0051 — Czochralski Crystal Growth → Monocrystalline Silicon Ingot

- ITEM_NUMBER: 97; ITEM_ID: `SC-RL-0051`; OBJECT_TYPE: relation.
- DOMAIN / context: `semiconductor` Semiconductor structured Foundation candidate against shared AI Hardware canonical catalog; cross-domain status: `candidate`.
- AUTOMATED_STAGE3_OUTCOME: `DEFER_RELATION`; CURRENT_CANONICAL_TARGET: `none`.
- Possible existing canonical IDs (unresolved unless explicitly reused): `none`.
- CANDIDATE_SUMMARY: Czochralski Crystal Growth → Monocrystalline Silicon Ingot; candidate type ``; comparison scope `SUMCO process transformation`; frozen candidate rationale: PROCESS_OUTPUT: runtime produces is producer/product semantics; process transformation not explicitly authorized as that edge
- WHY_HUMAN_REQUIRED: frozen Stage 3 mandatory review population; automated reasons: EVIDENCE_WARNING, FROZEN_STAGE2_HUMAN_DECISION, LOW_OR_UNKNOWN_CONFIDENCE, ONTOLOGY_PRESSURE, RELATION_AMBIGUITY.
- RISK_FLAGS: A=EVIDENCE_WARNING, FROZEN_STAGE2_HUMAN_DECISION, LOW_OR_UNKNOWN_CONFIDENCE, ONTOLOGY_PRESSURE, RELATION_AMBIGUITY; B=FROZEN_STAGE2_DECISION, UNRESOLVED_RELATION, ONTOLOGY_PRESSURE.

**AI REVIEW A**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `DEFER_RELATION`; target: `{'from_node_id': 'NODE_E06758E691974EB4', 'to_node_id': 'NODE_811C2B2A6DA22D14', 'from_ref': 'SC-CN-0034', 'to_ref': 'SC-CN-0026', 'relation_type': None, 'existing_relation_ids': []}`; confidence: HIGH; materiality: HIGH.
- reason: CZ growth transforms polysilicon into monocrystalline ingot; the empty relation type reflects a real process-output vocabulary gap.
- evidence assessment: SUMCO supports input and ingot production, but neither produces nor other current edge types safely encode process transformation.
- temporal scope assessed: {'source_scope': 'SUMCO process transformation', 'temporal_status': 'categorical_source_scoped', 'runtime_status': 'categorical', 'valid_from': '', 'valid_to': '', 'source_as_of': [None]}
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'same', 'object_type': 'compatible', 'scope': 'compatible', 'granularity': 'unknown', 'quarantine': 'clear', 'ontology': 'pressure', 'evidence_sufficiency': 'sufficient', 'temporal': 'unresolved'}

**AI REVIEW B**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `DEFER_RELATION`; target: `none`; confidence: LOW; materiality: HIGH.
- reason: Czochralski Crystal Growth → Monocrystalline Silicon Ingot: Polysilicon input becomes monocrystalline ingot output; transformation is needed, not uses or part_of.
- evidence assessment: SC-EV-3BE221EFD700F965 from SC-P0-006_SUMCO_Silicon_Wafer_Production_Processes.pdf [source SC-PHYS-9E9CEFC24043585C; SHA 9e9cefc24043585c1c5a484340dcf49aa0725b341467942d3d4c34be0da8aee6; PDF p.2, Monocrystalline pulling process]: The monocrystalline ingots that make up the silicon wafer are manufactured using high-quality polysilicon as the raw material. | SC-EV-C7BD218505458FDB from SC-P0-006_SUMCO_Silicon_Wafer_Production_Processes.pdf [source SC-PHYS-9E9CEFC24043585C; SHA 9e9cefc24043585c1c5a484340dcf49aa0725b341467942d3d4c34be0da8aee6; PDF p.2, Monocrystalline pulling process / Flow of CZ process]: The monocrystalline silicon ingots from which silicon wafers are created are manufactured by a technique called the CZ (Czochralski) crystal growth process. Boundary: Czochralski Crystal Growth → Monocrystalline Silicon Ingot: Polysilicon input becomes monocrystalline ingot output; transformation is needed, not uses or part_of. All source excerpts remain UNAUTHORIZED_CANDIDATE evidence.
- temporal scope assessed: categorical_source_scoped
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'same', 'object_type': 'compatible', 'scope': 'compatible', 'granularity': 'same', 'quarantine': 'preserved', 'ontology': 'pressure', 'evidence_sufficiency': 'limited', 'temporal': 'unresolved'}

**A/B RECONCILIATION**

- A_B_SUBSTANTIVE_AGREEMENT; disagreement type: none; native-operation conflict: false; target conflict: false.
- Interpretation differences: none.
- Reconciliation assessment: Both reviewers hold the same endpoint, temporal, or ontology exception. Rubric labels compare concept support with authority for the relation.
- Non-material rubric-label differences retained for audit: evidence_sufficiency, granularity, quarantine.

**EVIDENCE SUMMARY**

- Source `SC-PHYS-9E9CEFC24043585C` (SHA-256 `9e9cefc24043585c1c5a484340dcf49aa0725b341467942d3d4c34be0da8aee6`), file `SC-P0-006_SUMCO_Silicon_Wafer_Production_Processes.pdf`, p. 2, section Monocrystalline pulling process; evidence `SC-EV-3BE221EFD700F965`; as-of unknown; excerpt: “The monocrystalline ingots that make up the silicon wafer are manufactured using high-quality polysilicon as the raw material.”
- Source `SC-PHYS-9E9CEFC24043585C` (SHA-256 `9e9cefc24043585c1c5a484340dcf49aa0725b341467942d3d4c34be0da8aee6`), file `SC-P0-006_SUMCO_Silicon_Wafer_Production_Processes.pdf`, p. 2, section Monocrystalline pulling process / Flow of CZ process; evidence `SC-EV-C7BD218505458FDB`; as-of unknown; excerpt: “The monocrystalline silicon ingots from which silicon wafers are created are manufactured by a technique called the CZ (Czochralski) crystal growth process.”
- Temporal scope: categorical_source_scoped.

- SYSTEM_RECOMMENDED_DECISION: `DEFER_RELATION`.
- SYSTEM_RECOMMENDATION_REASON: Frozen structural, Stage 2 decision, evidence, or temporal exception remains unresolved.
- HUMAN_USER_DECISION = PENDING
- VALID NATIVE OPTIONS: REUSE_RELATION, CREATE_RELATION, KEEP_DOMAIN_SPECIFIC_RELATION, DEFER_RELATION, REJECT_RELATION; REUSE requires an explicit validated target ID and all options remain subject to frozen controls.

### Item 098 — SC-RL-0052 — Wafer Slicing → Silicon Wafer

- ITEM_NUMBER: 98; ITEM_ID: `SC-RL-0052`; OBJECT_TYPE: relation.
- DOMAIN / context: `semiconductor` Semiconductor structured Foundation candidate against shared AI Hardware canonical catalog; cross-domain status: `candidate`.
- AUTOMATED_STAGE3_OUTCOME: `DEFER_RELATION`; CURRENT_CANONICAL_TARGET: `none`.
- Possible existing canonical IDs (unresolved unless explicitly reused): `none`.
- CANDIDATE_SUMMARY: Wafer Slicing → Silicon Wafer; candidate type ``; comparison scope `SUMCO wafer forming / slicing`; frozen candidate rationale: PROCESS_OUTPUT: preserve transformation in map, do not force stage_of / processed_by / input_to
- WHY_HUMAN_REQUIRED: frozen Stage 3 mandatory review population; automated reasons: EVIDENCE_WARNING, FROZEN_STAGE2_HUMAN_DECISION, LOW_OR_UNKNOWN_CONFIDENCE, ONTOLOGY_PRESSURE, RELATION_AMBIGUITY.
- RISK_FLAGS: A=EVIDENCE_WARNING, FROZEN_STAGE2_HUMAN_DECISION, LOW_OR_UNKNOWN_CONFIDENCE, ONTOLOGY_PRESSURE, RELATION_AMBIGUITY; B=FROZEN_STAGE2_DECISION, UNRESOLVED_RELATION, ONTOLOGY_PRESSURE.

**AI REVIEW A**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `DEFER_RELATION`; target: `{'from_node_id': 'NODE_F8EB3DB6DCE1EB4C', 'to_node_id': 'NODE_B96F04EBB6D1FD0A', 'from_ref': 'SC-CN-0038', 'to_ref': 'SC-CN-0025', 'relation_type': None, 'existing_relation_ids': []}`; confidence: HIGH; materiality: HIGH.
- reason: Wafer Slicing forms wafers from ingots; sequence or input-to language would misstate the process-output proposition.
- evidence assessment: SUMCO explicitly says cutting the ingot into slices forms wafers; the claim should stay outside the current edge vocabulary.
- temporal scope assessed: {'source_scope': 'SUMCO wafer forming / slicing', 'temporal_status': 'categorical_source_scoped', 'runtime_status': 'categorical', 'valid_from': '', 'valid_to': '', 'source_as_of': [None]}
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'same', 'object_type': 'compatible', 'scope': 'compatible', 'granularity': 'unknown', 'quarantine': 'clear', 'ontology': 'pressure', 'evidence_sufficiency': 'sufficient', 'temporal': 'unresolved'}

**AI REVIEW B**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `DEFER_RELATION`; target: `none`; confidence: LOW; materiality: HIGH.
- reason: Wafer Slicing → Silicon Wafer: Ingot slicing forms wafers; no available relation type faithfully represents produces or transforms.
- evidence assessment: SC-EV-44BA70339AC36BAC from SC-P0-006_SUMCO_Silicon_Wafer_Production_Processes.pdf [source SC-PHYS-9E9CEFC24043585C; SHA 9e9cefc24043585c1c5a484340dcf49aa0725b341467942d3d4c34be0da8aee6; PDF p.3, Wafer forming process / Slicing]: Based on the resistivity desired by the customer, the ingot is then cut into slices of around 1mm thickness, using an inner- diameter saw or wire saw, to form the wafers. Boundary: Wafer Slicing → Silicon Wafer: Ingot slicing forms wafers; no available relation type faithfully represents produces or transforms. All source excerpts remain UNAUTHORIZED_CANDIDATE evidence.
- temporal scope assessed: categorical_source_scoped
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'same', 'object_type': 'compatible', 'scope': 'compatible', 'granularity': 'same', 'quarantine': 'preserved', 'ontology': 'pressure', 'evidence_sufficiency': 'limited', 'temporal': 'unresolved'}

**A/B RECONCILIATION**

- A_B_SUBSTANTIVE_AGREEMENT; disagreement type: none; native-operation conflict: false; target conflict: false.
- Interpretation differences: none.
- Reconciliation assessment: Both reviewers hold the same endpoint, temporal, or ontology exception. Rubric labels compare concept support with authority for the relation.
- Non-material rubric-label differences retained for audit: evidence_sufficiency, granularity, quarantine.

**EVIDENCE SUMMARY**

- Source `SC-PHYS-9E9CEFC24043585C` (SHA-256 `9e9cefc24043585c1c5a484340dcf49aa0725b341467942d3d4c34be0da8aee6`), file `SC-P0-006_SUMCO_Silicon_Wafer_Production_Processes.pdf`, p. 3, section Wafer forming process / Slicing; evidence `SC-EV-44BA70339AC36BAC`; as-of unknown; excerpt: “Based on the resistivity desired by the customer, the ingot is then cut into slices of around 1mm thickness, using an inner- diameter saw or wire saw, to form the wafers.”
- Temporal scope: categorical_source_scoped.

- SYSTEM_RECOMMENDED_DECISION: `DEFER_RELATION`.
- SYSTEM_RECOMMENDATION_REASON: Frozen structural, Stage 2 decision, evidence, or temporal exception remains unresolved.
- HUMAN_USER_DECISION = PENDING
- VALID NATIVE OPTIONS: REUSE_RELATION, CREATE_RELATION, KEEP_DOMAIN_SPECIFIC_RELATION, DEFER_RELATION, REJECT_RELATION; REUSE requires an explicit validated target ID and all options remain subject to frozen controls.

### Item 099 — SC-RL-0053 — Semiconductor Design Verification → Semiconductor Design

- ITEM_NUMBER: 99; ITEM_ID: `SC-RL-0053`; OBJECT_TYPE: relation.
- DOMAIN / context: `semiconductor` Semiconductor structured Foundation candidate against shared AI Hardware canonical catalog; cross-domain status: `candidate`.
- AUTOMATED_STAGE3_OUTCOME: `DEFER_RELATION`; CURRENT_CANONICAL_TARGET: `none`.
- Possible existing canonical IDs (unresolved unless explicitly reused): `none`.
- CANDIDATE_SUMMARY: Semiconductor Design Verification → Semiconductor Design; candidate type ``; comparison scope `SIA/BCG Exhibit3 design workflow`; frozen candidate rationale: ENGINEERING_VERIFICATION: runtime validates is not assumed equivalent to engineering verification
- WHY_HUMAN_REQUIRED: frozen Stage 3 mandatory review population; automated reasons: EVIDENCE_WARNING, FROZEN_STAGE2_HUMAN_DECISION, LOW_OR_UNKNOWN_CONFIDENCE, ONTOLOGY_PRESSURE, RELATION_AMBIGUITY.
- RISK_FLAGS: A=EVIDENCE_WARNING, FROZEN_STAGE2_HUMAN_DECISION, LOW_OR_UNKNOWN_CONFIDENCE, ONTOLOGY_PRESSURE, RELATION_AMBIGUITY; B=FROZEN_STAGE2_DECISION, UNRESOLVED_RELATION, ONTOLOGY_PRESSURE.

**AI REVIEW A**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `DEFER_RELATION`; target: `{'from_node_id': 'NODE_0B5CDFEE66D76FB0', 'to_node_id': 'NODE_63D3FFF5A5A14739', 'from_ref': 'SC-CN-0157', 'to_ref': 'SC-CN-0020', 'relation_type': None, 'existing_relation_ids': []}`; confidence: HIGH; materiality: HIGH.
- reason: Engineering verification of semiconductor design is not identical to the runtime validates relation; preserve the claim pending ontology review.
- evidence assessment: SIA/BCG says verification engineers check functionality and timing through simulation, but the actor/process mapping is not settled.
- temporal scope assessed: {'source_scope': 'SIA/BCG Exhibit3 design workflow', 'temporal_status': 'categorical_source_scoped', 'runtime_status': 'categorical', 'valid_from': '', 'valid_to': '', 'source_as_of': ['2022-11']}
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'same', 'object_type': 'compatible', 'scope': 'compatible', 'granularity': 'unknown', 'quarantine': 'clear', 'ontology': 'pressure', 'evidence_sufficiency': 'limited', 'temporal': 'unresolved'}

**AI REVIEW B**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `DEFER_RELATION`; target: `none`; confidence: LOW; materiality: HIGH.
- reason: Semiconductor Design Verification → Semiconductor Design: Simulation verifies functionality and timing; the excerpt does not justify parent or causal relation types.
- evidence assessment: SC-EV-A7155A1FD4102457 from SC-P0-004_2022_The-Growing-Challenge-of-Semiconductor-Design-Leadership_FINAL.pdf [source SC-PHYS-AC86A7FEB4F6ADB5; SHA ac86a7feb4f6adb52e488086f9281c1f409bd72baecb6bdbed72a0efa3856666; PDF p.8, Design stages / Verification]: Verification engineers verify design functionality and timing through simulation Boundary: Semiconductor Design Verification → Semiconductor Design: Simulation verifies functionality and timing; the excerpt does not justify parent or causal relation types. All source excerpts remain UNAUTHORIZED_CANDIDATE evidence.
- temporal scope assessed: categorical_source_scoped
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'same', 'object_type': 'compatible', 'scope': 'compatible', 'granularity': 'same', 'quarantine': 'preserved', 'ontology': 'pressure', 'evidence_sufficiency': 'limited', 'temporal': 'unresolved'}

**A/B RECONCILIATION**

- A_B_SUBSTANTIVE_AGREEMENT; disagreement type: none; native-operation conflict: false; target conflict: false.
- Interpretation differences: none.
- Reconciliation assessment: Both reviewers hold the same endpoint, temporal, or ontology exception. Rubric labels compare concept support with authority for the relation.
- Non-material rubric-label differences retained for audit: granularity, quarantine.

**EVIDENCE SUMMARY**

- Source `SC-PHYS-AC86A7FEB4F6ADB5` (SHA-256 `ac86a7feb4f6adb52e488086f9281c1f409bd72baecb6bdbed72a0efa3856666`), file `SC-P0-004_2022_The-Growing-Challenge-of-Semiconductor-Design-Leadership_FINAL.pdf`, p. 8, section Design stages / Verification; evidence `SC-EV-A7155A1FD4102457`; as-of 2022-11; excerpt: “Verification engineers verify design functionality and timing through simulation”
- Temporal scope: categorical_source_scoped.

- SYSTEM_RECOMMENDED_DECISION: `DEFER_RELATION`.
- SYSTEM_RECOMMENDATION_REASON: Frozen structural, Stage 2 decision, evidence, or temporal exception remains unresolved.
- HUMAN_USER_DECISION = PENDING
- VALID NATIVE OPTIONS: REUSE_RELATION, CREATE_RELATION, KEEP_DOMAIN_SPECIFIC_RELATION, DEFER_RELATION, REJECT_RELATION; REUSE requires an explicit validated target ID and all options remain subject to frozen controls.

### Item 100 — SC-RL-0054 — Photolithography → Etching

- ITEM_NUMBER: 100; ITEM_ID: `SC-RL-0054`; OBJECT_TYPE: relation.
- DOMAIN / context: `semiconductor` Semiconductor structured Foundation candidate against shared AI Hardware canonical catalog; cross-domain status: `candidate`.
- AUTOMATED_STAGE3_OUTCOME: `DEFER_RELATION`; CURRENT_CANONICAL_TARGET: `none`.
- Possible existing canonical IDs (unresolved unless explicitly reused): `none`.
- CANDIDATE_SUMMARY: Photolithography → Etching; candidate type ``; comparison scope `ASML wafer patterning workflow`; frozen candidate rationale: PROCESS_SEQUENCE: process order or preparation is not industrial-chain upstream_of
- WHY_HUMAN_REQUIRED: frozen Stage 3 mandatory review population; automated reasons: EVIDENCE_WARNING, FROZEN_STAGE2_HUMAN_DECISION, LOW_OR_UNKNOWN_CONFIDENCE, ONTOLOGY_PRESSURE, RELATION_AMBIGUITY.
- RISK_FLAGS: A=EVIDENCE_WARNING, FROZEN_STAGE2_HUMAN_DECISION, LOW_OR_UNKNOWN_CONFIDENCE, ONTOLOGY_PRESSURE, RELATION_AMBIGUITY; B=FROZEN_STAGE2_DECISION, UNRESOLVED_RELATION, ONTOLOGY_PRESSURE.

**AI REVIEW A**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `DEFER_RELATION`; target: `{'from_node_id': 'NODE_D71397E38AE45F20', 'to_node_id': 'NODE_7FDCA2B3859210F3', 'from_ref': 'SC-CN-0056', 'to_ref': 'SC-CN-0060', 'relation_type': None, 'existing_relation_ids': []}`; confidence: HIGH; materiality: HIGH.
- reason: Photolithography and Etching are linked by pattern-transfer workflow, not by the industry's upstream_of relation.
- evidence assessment: The two ASML spans separately describe reticle exposure and wet/dry etching; neither proves an industrial-chain causal edge.
- temporal scope assessed: {'source_scope': 'ASML wafer patterning workflow', 'temporal_status': 'categorical_source_scoped', 'runtime_status': 'categorical', 'valid_from': '', 'valid_to': '', 'source_as_of': ['2023-10-04']}
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'same', 'object_type': 'compatible', 'scope': 'compatible', 'granularity': 'unknown', 'quarantine': 'clear', 'ontology': 'pressure', 'evidence_sufficiency': 'limited', 'temporal': 'unresolved'}

**AI REVIEW B**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `DEFER_RELATION`; target: `none`; confidence: LOW; materiality: HIGH.
- reason: Photolithography → Etching: ASML discusses dry and wet etching in patterning; chronology does not establish upstream_of.
- evidence assessment: SC-EV-F4124019AED7B2C6 from SC-P0-007_ASML_Six_Semiconductor_Manufacturing_Steps.pdf [source SC-PHYS-87B4665C30781057; SHA 87b4665c3078105792ca70f18964c938976b72f2dcf0d19379b034d5d6f205f9; PDF p.5, Etch]: As with resist, there are two types of etch: 'wet' and 'dry'. Dry etching uses gases to define the exposed pattern on the wafer. Wet etching uses chemical baths to wash the wafer. | SC-EV-FD3B14BF5F4E693A from SC-P0-007_ASML_Six_Semiconductor_Manufacturing_Steps.pdf [source SC-PHYS-87B4665C30781057; SHA 87b4665c3078105792ca70f18964c938976b72f2dcf0d19379b034d5d6f205f9; PDF p.3, Lithography]: Light is projected onto the wafer through the 'reticle', which holds the blueprint of the pattern to be printed. The system's optics (lenses in a DUV system and mirrors in an EUV system) shrink and focus the pattern onto the resist layer. Boundary: Photolithography → Etching: ASML discusses dry and wet etching in patterning; chronology does not establish upstream_of. All source excerpts remain UNAUTHORIZED_CANDIDATE evidence.
- temporal scope assessed: categorical_source_scoped
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'same', 'object_type': 'compatible', 'scope': 'compatible', 'granularity': 'same', 'quarantine': 'preserved', 'ontology': 'pressure', 'evidence_sufficiency': 'limited', 'temporal': 'unresolved'}

**A/B RECONCILIATION**

- A_B_SUBSTANTIVE_AGREEMENT; disagreement type: none; native-operation conflict: false; target conflict: false.
- Interpretation differences: none.
- Reconciliation assessment: Both reviewers hold the same endpoint, temporal, or ontology exception. Rubric labels compare concept support with authority for the relation.
- Non-material rubric-label differences retained for audit: granularity, quarantine.

**EVIDENCE SUMMARY**

- Source `SC-PHYS-87B4665C30781057` (SHA-256 `87b4665c3078105792ca70f18964c938976b72f2dcf0d19379b034d5d6f205f9`), file `SC-P0-007_ASML_Six_Semiconductor_Manufacturing_Steps.pdf`, p. 5, section Etch; evidence `SC-EV-F4124019AED7B2C6`; as-of 2023-10-04; excerpt: “As with resist, there are two types of etch: 'wet' and 'dry'. Dry etching uses gases to define the exposed pattern on the wafer. Wet etching uses chemical baths to wash the wafer.”
- Source `SC-PHYS-87B4665C30781057` (SHA-256 `87b4665c3078105792ca70f18964c938976b72f2dcf0d19379b034d5d6f205f9`), file `SC-P0-007_ASML_Six_Semiconductor_Manufacturing_Steps.pdf`, p. 3, section Lithography; evidence `SC-EV-FD3B14BF5F4E693A`; as-of 2023-10-04; excerpt: “Light is projected onto the wafer through the 'reticle', which holds the blueprint of the pattern to be printed. The system's optics (lenses in a DUV system and mirrors in an EUV system) shrink and focus the pattern onto the resist layer.”
- Temporal scope: categorical_source_scoped.

- SYSTEM_RECOMMENDED_DECISION: `DEFER_RELATION`.
- SYSTEM_RECOMMENDATION_REASON: Frozen structural, Stage 2 decision, evidence, or temporal exception remains unresolved.
- HUMAN_USER_DECISION = PENDING
- VALID NATIVE OPTIONS: REUSE_RELATION, CREATE_RELATION, KEEP_DOMAIN_SPECIFIC_RELATION, DEFER_RELATION, REJECT_RELATION; REUSE requires an explicit validated target ID and all options remain subject to frozen controls.

## Section B — Substantive A/B disagreement

### Item 002 — SC-CN-0033 — Chiplet

- ITEM_NUMBER: 2; ITEM_ID: `SC-CN-0033`; OBJECT_TYPE: identity.
- DOMAIN / context: `01_design_enablement` Semiconductor structured Foundation candidate against shared AI Hardware canonical catalog; cross-domain status: `REVIEW_REQUIRED`.
- AUTOMATED_STAGE3_OUTCOME: `DEFER`; CURRENT_CANONICAL_TARGET: `none`.
- Possible existing canonical IDs (unresolved unless explicitly reused): `none`.
- CANDIDATE_SUMMARY: Chiplet; candidate type `Product`; comparison scope `Source为物理小裸片，既有 Chiplet Architecture 是 Technology；不得自动改型或合并。`; frozen candidate rationale: Source为物理小裸片，既有 Chiplet Architecture 是 Technology；不得自动改型或合并。
- WHY_HUMAN_REQUIRED: frozen Stage 3 mandatory review population; automated reasons: AMBIGUOUS_IDENTITY.
- RISK_FLAGS: A=AMBIGUOUS_IDENTITY, PROPOSED_OUTCOME_DIFFERS; B=UNRESOLVED_IDENTITY, SCOPE_OR_TYPE_BOUNDARY.

**AI REVIEW A**

- recommendation: CHALLENGE_AUTOMATION; native decision: `CREATE_NEW_CANONICAL`; target: `none`; confidence: MEDIUM; materiality: HIGH.
- reason: Chiplet denotes a physical small die, whereas Chiplet Architecture is a Technology; the type and object boundary support a separate Product proposal.
- evidence assessment: Intel explicitly calls small companion dies chiplets; this supports the product concept, although no approved canonical identity exists yet.
- temporal scope assessed: {'source_as_of': ['2026-03-09'], 'publication_date': ['2026-03-09'], 'identity_claim': 'candidate_only'}
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'distinct', 'object_type': 'mismatch', 'scope': 'mismatch', 'granularity': 'different', 'quarantine': 'clear', 'ontology': 'compatible', 'evidence_sufficiency': 'sufficient', 'temporal': 'compatible'}

**AI REVIEW B**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `DEFER`; target: `none`; confidence: MEDIUM; materiality: MEDIUM.
- reason: Chiplet denotes a physical companion die; Chiplet Architecture is the technology of arranging chiplets. The product and technology identities differ.
- evidence assessment: SC-EV-BE5865482E8780B8 from SC-P0-005_Intel_Common_Chip_Terms.pdf [source SC-PHYS-7E064380CA686D9F; SHA 7e064380ca686d9f00c235f15c007523e89e4a0ffb7e9a22f435218c06799d05; PDF p.7, What is a Package?]: Small companion dies connected with advanced packaging are often referred to as chiplets. Boundary: Chiplet denotes a physical companion die; Chiplet Architecture is the technology of arranging chiplets. The product and technology identities differ. All source excerpts remain UNAUTHORIZED_CANDIDATE evidence.
- temporal scope assessed: 2026-03-09
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'ambiguous', 'object_type': 'mismatch', 'scope': 'mismatch', 'granularity': 'different', 'quarantine': 'clear', 'ontology': 'unresolved', 'evidence_sufficiency': 'limited', 'temporal': 'compatible'}

**A/B RECONCILIATION**

- A_B_SUBSTANTIVE_DISAGREEMENT; disagreement type: NATIVE_OPERATION_CONFLICT, EVIDENCE_CONFLICT, TYPE_OR_SCOPE_CONFLICT; native-operation conflict: true; target conflict: false.
- Interpretation differences: evidence_sufficiency, identity_boundary, ontology.
- Reconciliation assessment: A proposes a distinct Chiplet Product; B holds the product boundary for explicit admission.
- Non-material rubric-label differences retained for audit: none.

**EVIDENCE SUMMARY**

- Source `SC-PHYS-7E064380CA686D9F` (SHA-256 `7e064380ca686d9f00c235f15c007523e89e4a0ffb7e9a22f435218c06799d05`), file `SC-P0-005_Intel_Common_Chip_Terms.pdf`, p. 7, section What is a Package?; evidence `SC-EV-BE5865482E8780B8`; as-of 2026-03-09; excerpt: “Small companion dies connected with advanced packaging are often referred to as chiplets.”
- Temporal scope: source as-of dates above; no relation temporal claim.

- SYSTEM_RECOMMENDED_DECISION: `DEFER`.
- SYSTEM_RECOMMENDATION_REASON: Material A/B interpretation or native-operation conflict requires HUMAN_USER adjudication.
- HUMAN_USER_DECISION = PENDING
- VALID NATIVE OPTIONS: REUSE_CANONICAL, CREATE_NEW_CANONICAL, KEEP_DOMAIN_SPECIFIC, DEFER, REJECT; REUSE requires an explicit validated target ID and all options remain subject to frozen controls.

### Item 033 — SC-CN-0051 — Silicon-On-Insulator Wafers

- ITEM_NUMBER: 33; ITEM_ID: `SC-CN-0051`; OBJECT_TYPE: identity.
- DOMAIN / context: `02_wafer_materials` Semiconductor structured Foundation candidate against shared AI Hardware canonical catalog; cross-domain status: `REVIEW_REQUIRED`.
- AUTOMATED_STAGE3_OUTCOME: `DEFER`; CURRENT_CANONICAL_TARGET: `none`.
- Possible existing canonical IDs (unresolved unless explicitly reused): `none`.
- CANDIDATE_SUMMARY: Silicon-On-Insulator Wafers; candidate type `Material`; comparison scope `材料同一性很强，但 source复数短语/SOI未作为现有英文别名登记；提交明确映射审核。`; frozen candidate rationale: 材料同一性很强，但 source复数短语/SOI未作为现有英文别名登记；提交明确映射审核。
- WHY_HUMAN_REQUIRED: frozen Stage 3 mandatory review population; automated reasons: AMBIGUOUS_IDENTITY.
- RISK_FLAGS: A=AMBIGUOUS_IDENTITY, PROPOSED_OUTCOME_DIFFERS; B=UNRESOLVED_IDENTITY, EVIDENCE_LIMIT.

**AI REVIEW A**

- recommendation: CHALLENGE_AUTOMATION; native decision: `REUSE_CANONICAL`; target: `NODE_20260817_7A9AE357`; confidence: MEDIUM; materiality: MEDIUM.
- reason: Silicon-On-Insulator Wafers is the plural of the existing Silicon-on-Insulator Wafer material; approve the same node with explicit expression review.
- evidence assessment: SUMCO describes active and handle wafers bonded across an oxide layer, matching SOI wafer construction rather than another material.
- temporal scope assessed: {'source_as_of': [None], 'publication_date': [None], 'identity_claim': 'candidate_only'}
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'same', 'object_type': 'compatible', 'scope': 'compatible', 'granularity': 'same', 'quarantine': 'clear', 'ontology': 'compatible', 'evidence_sufficiency': 'sufficient', 'temporal': 'compatible'}

**AI REVIEW B**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `DEFER`; target: `none`; confidence: LOW; materiality: MEDIUM.
- reason: The cited span describes handle and active wafer bonding but does not itself name Silicon-On-Insulator; hold candidate-to-SOI mapping.
- evidence assessment: SC-EV-CFBF2B108331D342 from SC-P0-006_SUMCO_Silicon_Wafer_Production_Processes.pdf [source SC-PHYS-9E9CEFC24043585C; SHA 9e9cefc24043585c1c5a484340dcf49aa0725b341467942d3d4c34be0da8aee6; PDF p.7, Specialized processing / Silicon-On-Insulator Wafers]: An oxide layer is formed for one or both of the handle wafer and the active wafer on which semiconductor devices will be built. The two wafers are then bonded together by annealing. Next the active wafer is ground and polished to the desired thickness. Boundary: The cited span describes handle and active wafer bonding but does not itself name Silicon-On-Insulator; hold candidate-to-SOI mapping. All source excerpts remain UNAUTHORIZED_CANDIDATE evidence.
- temporal scope assessed: not_established
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'ambiguous', 'object_type': 'unknown', 'scope': 'unknown', 'granularity': 'unknown', 'quarantine': 'clear', 'ontology': 'unresolved', 'evidence_sufficiency': 'insufficient', 'temporal': 'compatible'}

**A/B RECONCILIATION**

- A_B_SUBSTANTIVE_DISAGREEMENT; disagreement type: NATIVE_OPERATION_CONFLICT, TARGET_CONFLICT, EVIDENCE_CONFLICT, TYPE_OR_SCOPE_CONFLICT; native-operation conflict: true; target conflict: true.
- Interpretation differences: evidence_sufficiency, granularity, identity_boundary, object_type, ontology, scope.
- Reconciliation assessment: A proposes reuse of the existing SOI Wafer ID; B finds the bound excerpt insufficient to authorize the plural-name mapping.
- Non-material rubric-label differences retained for audit: none.

**EVIDENCE SUMMARY**

- Source `SC-PHYS-9E9CEFC24043585C` (SHA-256 `9e9cefc24043585c1c5a484340dcf49aa0725b341467942d3d4c34be0da8aee6`), file `SC-P0-006_SUMCO_Silicon_Wafer_Production_Processes.pdf`, p. 7, section Specialized processing / Silicon-On-Insulator Wafers; evidence `SC-EV-CFBF2B108331D342`; as-of unknown; excerpt: “An oxide layer is formed for one or both of the handle wafer and the active wafer on which semiconductor devices will be built. The two wafers are then bonded together by annealing. Next the active wafer is ground and polished to the desired thickness.”
- Temporal scope: source as-of dates above; no relation temporal claim.

- SYSTEM_RECOMMENDED_DECISION: `DEFER`.
- SYSTEM_RECOMMENDATION_REASON: Material A/B interpretation or native-operation conflict requires HUMAN_USER adjudication.
- HUMAN_USER_DECISION = PENDING
- VALID NATIVE OPTIONS: REUSE_CANONICAL, CREATE_NEW_CANONICAL, KEEP_DOMAIN_SPECIFIC, DEFER, REJECT; REUSE requires an explicit validated target ID and all options remain subject to frozen controls.

### Item 034 — SC-CN-0031 — Package Substrate

- ITEM_NUMBER: 34; ITEM_ID: `SC-CN-0031`; OBJECT_TYPE: identity.
- DOMAIN / context: `01_design_enablement` Semiconductor structured Foundation candidate against shared AI Hardware canonical catalog; cross-domain status: `REVIEW_REQUIRED`.
- AUTOMATED_STAGE3_OUTCOME: `DEFER`; CURRENT_CANONICAL_TARGET: `none`.
- Possible existing canonical IDs (unresolved unless explicitly reused): `none`.
- CANDIDATE_SUMMARY: Package Substrate; candidate type `Product`; comparison scope `通用封装载板范围比既有 Advanced Package Substrate 广；不得合并为高端载板。`; frozen candidate rationale: 通用封装载板范围比既有 Advanced Package Substrate 广；不得合并为高端载板。
- WHY_HUMAN_REQUIRED: frozen Stage 3 mandatory review population; automated reasons: AMBIGUOUS_IDENTITY.
- RISK_FLAGS: A=AMBIGUOUS_IDENTITY, PROPOSED_OUTCOME_DIFFERS; B=UNRESOLVED_IDENTITY, SCOPE_OR_TYPE_BOUNDARY.

**AI REVIEW A**

- recommendation: CHALLENGE_AUTOMATION; native decision: `CREATE_NEW_CANONICAL`; target: `none`; confidence: MEDIUM; materiality: HIGH.
- reason: Package Substrate is the general die-bearing package foundation; Advanced Package Substrate is a narrower product, so a separate parent is justified.
- evidence assessment: Intel defines substrate broadly and names organic, ceramic and glass materials, not only advanced packaging substrates.
- temporal scope assessed: {'source_as_of': ['2026-03-09'], 'publication_date': ['2026-03-09'], 'identity_claim': 'candidate_only'}
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'distinct', 'object_type': 'compatible', 'scope': 'mismatch', 'granularity': 'different', 'quarantine': 'clear', 'ontology': 'compatible', 'evidence_sufficiency': 'sufficient', 'temporal': 'compatible'}

**AI REVIEW B**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `DEFER`; target: `none`; confidence: MEDIUM; materiality: HIGH.
- reason: Generic package substrate spans organic, ceramic, and glass foundations, broader than Advanced Package Substrate; do not merge these levels.
- evidence assessment: SC-EV-B0FAEABBEA6C0690 from SC-P0-005_Intel_Common_Chip_Terms.pdf [source SC-PHYS-7E064380CA686D9F; SHA 7e064380ca686d9f00c235f15c007523e89e4a0ffb7e9a22f435218c06799d05; PDF p.6, What is a Package?]: The material that dies are attached to and that provides the foundation of the package is called the substrate. It is composed of materials like organic laminates, ceramics or glass. Boundary: Generic package substrate spans organic, ceramic, and glass foundations, broader than Advanced Package Substrate; do not merge these levels. All source excerpts remain UNAUTHORIZED_CANDIDATE evidence.
- temporal scope assessed: 2026-03-09
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'ambiguous', 'object_type': 'unknown', 'scope': 'mismatch', 'granularity': 'different', 'quarantine': 'clear', 'ontology': 'unresolved', 'evidence_sufficiency': 'limited', 'temporal': 'compatible'}

**A/B RECONCILIATION**

- A_B_SUBSTANTIVE_DISAGREEMENT; disagreement type: NATIVE_OPERATION_CONFLICT, EVIDENCE_CONFLICT, TYPE_OR_SCOPE_CONFLICT; native-operation conflict: true; target conflict: false.
- Interpretation differences: evidence_sufficiency, identity_boundary, object_type, ontology.
- Reconciliation assessment: A proposes a new generic Package Substrate parent; B defers the broader-than-advanced boundary.
- Non-material rubric-label differences retained for audit: none.

**EVIDENCE SUMMARY**

- Source `SC-PHYS-7E064380CA686D9F` (SHA-256 `7e064380ca686d9f00c235f15c007523e89e4a0ffb7e9a22f435218c06799d05`), file `SC-P0-005_Intel_Common_Chip_Terms.pdf`, p. 6, section What is a Package?; evidence `SC-EV-B0FAEABBEA6C0690`; as-of 2026-03-09; excerpt: “The material that dies are attached to and that provides the foundation of the package is called the substrate. It is composed of materials like organic laminates, ceramics or glass.”
- Temporal scope: source as-of dates above; no relation temporal claim.

- SYSTEM_RECOMMENDED_DECISION: `DEFER`.
- SYSTEM_RECOMMENDATION_REASON: Material A/B interpretation or native-operation conflict requires HUMAN_USER adjudication.
- HUMAN_USER_DECISION = PENDING
- VALID NATIVE OPTIONS: REUSE_CANONICAL, CREATE_NEW_CANONICAL, KEEP_DOMAIN_SPECIFIC, DEFER, REJECT; REUSE requires an explicit validated target ID and all options remain subject to frozen controls.

### Item 041 — SC-CN-0042 — Silicon Wafer Polishing

- ITEM_NUMBER: 41; ITEM_ID: `SC-CN-0042`; OBJECT_TYPE: identity.
- DOMAIN / context: `02_wafer_materials` Semiconductor structured Foundation candidate against shared AI Hardware canonical catalog; cross-domain status: `REVIEW_REQUIRED`.
- AUTOMATED_STAGE3_OUTCOME: `DEFER`; CURRENT_CANONICAL_TARGET: `none`.
- Possible existing canonical IDs (unresolved unless explicitly reused): `none`.
- CANDIDATE_SUMMARY: Silicon Wafer Polishing; candidate type `Technology`; comparison scope `起始硅片镜面抛光与晶圆制造 CMP 工艺的层级关系需审。`; frozen candidate rationale: 起始硅片镜面抛光与晶圆制造 CMP 工艺的层级关系需审。
- WHY_HUMAN_REQUIRED: frozen Stage 3 mandatory review population; automated reasons: AMBIGUOUS_IDENTITY.
- RISK_FLAGS: A=AMBIGUOUS_IDENTITY, PROPOSED_OUTCOME_DIFFERS; B=UNRESOLVED_IDENTITY.

**AI REVIEW A**

- recommendation: CHALLENGE_AUTOMATION; native decision: `CREATE_NEW_CANONICAL`; target: `none`; confidence: MEDIUM; materiality: MEDIUM.
- reason: Silicon Wafer Polishing is a starting-wafer process, distinct in type and stage from Advanced Packaging CMP Equipment.
- evidence assessment: SUMCO explicitly describes mirror-finishing wafer surfaces by mechano-chemical polishing with colloidal silica.
- temporal scope assessed: {'source_as_of': [None], 'publication_date': [None], 'identity_claim': 'candidate_only'}
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'distinct', 'object_type': 'mismatch', 'scope': 'mismatch', 'granularity': 'different', 'quarantine': 'clear', 'ontology': 'compatible', 'evidence_sufficiency': 'sufficient', 'temporal': 'compatible'}

**AI REVIEW B**

- recommendation: AGREE_WITH_AUTOMATION; native decision: `DEFER`; target: `none`; confidence: MEDIUM; materiality: MEDIUM.
- reason: SUMCO describes starting-wafer mirror polishing; its overlap with fabrication CMP is not a same-scope identity match.
- evidence assessment: SC-EV-FD093A8B2A6553C4 from SC-P0-006_SUMCO_Silicon_Wafer_Production_Processes.pdf [source SC-PHYS-9E9CEFC24043585C; SHA 9e9cefc24043585c1c5a484340dcf49aa0725b341467942d3d4c34be0da8aee6; PDF p.4, Wafer forming process / Polishing]: The wafer surfaces are made perfectly flat and given a mirror finish by means of mechano-chemical polishing using colloidal silica. Boundary: SUMCO describes starting-wafer mirror polishing; its overlap with fabrication CMP is not a same-scope identity match. All source excerpts remain UNAUTHORIZED_CANDIDATE evidence.
- temporal scope assessed: not_established
- type/scope/granularity/evidence/temporal assessment: {'identity_boundary': 'ambiguous', 'object_type': 'unknown', 'scope': 'mismatch', 'granularity': 'different', 'quarantine': 'clear', 'ontology': 'unresolved', 'evidence_sufficiency': 'limited', 'temporal': 'compatible'}

**A/B RECONCILIATION**

- A_B_SUBSTANTIVE_DISAGREEMENT; disagreement type: NATIVE_OPERATION_CONFLICT, EVIDENCE_CONFLICT, TYPE_OR_SCOPE_CONFLICT; native-operation conflict: true; target conflict: false.
- Interpretation differences: evidence_sufficiency, identity_boundary, object_type, ontology.
- Reconciliation assessment: A proposes a distinct starting-wafer polishing Process; B defers its boundary against fabrication CMP.
- Non-material rubric-label differences retained for audit: none.

**EVIDENCE SUMMARY**

- Source `SC-PHYS-9E9CEFC24043585C` (SHA-256 `9e9cefc24043585c1c5a484340dcf49aa0725b341467942d3d4c34be0da8aee6`), file `SC-P0-006_SUMCO_Silicon_Wafer_Production_Processes.pdf`, p. 4, section Wafer forming process / Polishing; evidence `SC-EV-FD093A8B2A6553C4`; as-of unknown; excerpt: “The wafer surfaces are made perfectly flat and given a mirror finish by means of mechano-chemical polishing using colloidal silica.”
- Temporal scope: source as-of dates above; no relation temporal claim.

- SYSTEM_RECOMMENDED_DECISION: `DEFER`.
- SYSTEM_RECOMMENDATION_REASON: Material A/B interpretation or native-operation conflict requires HUMAN_USER adjudication.
- HUMAN_USER_DECISION = PENDING
- VALID NATIVE OPTIONS: REUSE_CANONICAL, CREATE_NEW_CANONICAL, KEEP_DOMAIN_SPECIFIC, DEFER, REJECT; REUSE requires an explicit validated target ID and all options remain subject to frozen controls.
