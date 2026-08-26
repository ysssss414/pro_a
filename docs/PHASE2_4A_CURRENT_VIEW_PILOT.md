# Phase 2.4A — Subject-Aware Current View Pilot

PHASE2_4A_COMPLETE = true
MLCC_VIEW_PILOT_READY = PARTIAL
YUNZHONG_VIEW_PILOT_READY = PARTIAL
SUBJECT_AWARE_VIEW_MODEL_VALID = PARTIAL
PRODUCTION_WRITE_AUTHORIZED_FOR_CURRENT_VIEW = false
HUMAN_REVIEW_REQUIRED = true

## Outcome

Exactly two artifact-only `current_view_change` Proposal payloads were generated for human
review: `NODE_20260817_DABE52FE` / MLCC and `NODE_20260826_BC260F3E` / 昀冢科技. They reuse the frozen
Proposal fields and Current View `content_json` shape, but no row was inserted into
`proposals` or `current_views`. No LLM was called.

The deterministic gate passes subject/context separation, source traceability, frozen content
validation, uncertainty handling and scope-overreach checks. The model verdict remains
`PARTIAL`, because both pilots rely on one B-rank secondary Source and neither draft has been
human-confirmed.

## CURRENT_VIEW_EVIDENCE_POLICY

- `subject`: required for every direct factual assertion and every primary supporting Claim.
- `context`: review-package background only; label CONTEXT_ONLY and never use as direct support.
- `related`: prohibited as direct Current View support until human subject/context adjudication.
- `needs_review`: exclude from primary evidence and list explicitly as unresolved.
- `expert_judgment`: retain as attributed judgment; never present as data or confirmed fact.
- `company_guidance`: retain company attribution, future time anchor, and guidance status.

## MLCC pilot

- Subject Claims available / primary: 3 / 3.
- Context Claims: 8, all `CONTEXT_ONLY`.
- Verdict: `PARTIAL` — Only three subject Claims from one secondary Source; two are expert judgment.
- Summary: 截至2026年8月，MLCC已存数据支持7月和8月单月价格环比上涨30%以上；周期长度及AI挤出效应仅保留为分析师判断。[CLM_20260814_980FA010] [CLM_20260814_BAED6789] [CLM_20260814_D2C7FCD1]

### Primary Evidence

| Claim | Role/use | Nature | Status | Confidence | Time | Source |
|---|---|---|---|---:|---|---|
| CLM_20260814_980FA010 | PRIMARY | data | current | 0.9 | 2026-07/2026-08 | SRC_20260814_F6E1EFAD — 财通电子&新科技 昀冢科技业绩说明会更新：MLCC业绩答卷&未来指引双超预期 |
| CLM_20260814_BAED6789 | PRIMARY | expert_judgment | current | 0.7 | 2026-08-13 | SRC_20260814_F6E1EFAD — 财通电子&新科技 昀冢科技业绩说明会更新：MLCC业绩答卷&未来指引双超预期 |
| CLM_20260814_D2C7FCD1 | PRIMARY | expert_judgment | current | 0.7 | 2026-08-13 | SRC_20260814_F6E1EFAD — 财通电子&新科技 昀冢科技业绩说明会更新：MLCC业绩答卷&未来指引双超预期 |

### Context-only Evidence

| Claim | Role/use | Nature | Status | Confidence | Time | Source |
|---|---|---|---|---:|---|---|
| CLM_20260814_E1A48290 | CONTEXT_ONLY | data | current | 0.9 | 2026-06 | SRC_20260814_F6E1EFAD — 财通电子&新科技 昀冢科技业绩说明会更新：MLCC业绩答卷&未来指引双超预期 |
| CLM_20260814_9A069D06 | CONTEXT_ONLY | company_guidance | current | 0.8 | 2028年底 | SRC_20260814_F6E1EFAD — 财通电子&新科技 昀冢科技业绩说明会更新：MLCC业绩答卷&未来指引双超预期 |
| CLM_20260814_8E4B9E25 | CONTEXT_ONLY | company_guidance | current | 0.8 | 2027年底 | SRC_20260814_F6E1EFAD — 财通电子&新科技 昀冢科技业绩说明会更新：MLCC业绩答卷&未来指引双超预期 |
| CLM_20260814_541F5C31 | CONTEXT_ONLY | company_guidance | current | 0.8 | 2026Q4 | SRC_20260814_F6E1EFAD — 财通电子&新科技 昀冢科技业绩说明会更新：MLCC业绩答卷&未来指引双超预期 |
| CLM_20260814_939CAEDD | CONTEXT_ONLY | company_guidance | current | 0.8 | 2026H2 | SRC_20260814_F6E1EFAD — 财通电子&新科技 昀冢科技业绩说明会更新：MLCC业绩答卷&未来指引双超预期 |
| CLM_20260814_BA7AC415 | CONTEXT_ONLY | fact | current | 0.8 | 2026-08-13 | SRC_20260814_F6E1EFAD — 财通电子&新科技 昀冢科技业绩说明会更新：MLCC业绩答卷&未来指引双超预期 |
| CLM_20260814_0B6E52F8 | CONTEXT_ONLY | company_guidance | needs_review | 0.0 | 2026H2 | SRC_20260814_F6E1EFAD — 财通电子&新科技 昀冢科技业绩说明会更新：MLCC业绩答卷&未来指引双超预期 |
| CLM_20260814_E53B8E9C | CONTEXT_ONLY | company_guidance | needs_review | 0.0 | 2026H2 | SRC_20260814_F6E1EFAD — 财通电子&新科技 昀冢科技业绩说明会更新：MLCC业绩答卷&未来指引双超预期 |

### Rejected context leakage

The validator rejects the following company-only facts from MLCC Summary, Key Facts and other
primary content: `80亿颗/月`, `120亿颗/月`, `220亿颗/月`, `400亿颗/月`, `7.5亿元`, `车规认证`, `车规级`, `70%以上`. None appears in the MLCC primary proposal. These Claims remain
visible only in the `CONTEXT_ONLY` review section.

## 昀冢科技 pilot

- Subject Claims available / primary: 8 / 6.
- Context Claims: 0.
- Two `needs_review` Claims are isolated as unresolved and excluded from primary Evidence.
- Verdict: `PARTIAL` — Eight subject Claims exist, but two are needs_review and all come from one secondary Source.
- Summary: 昀冢科技现有证据支持其MLCC一期产线出货、扩产计划、车规级高容产品认证和单月营收变化的公司级候选判断；未来产能均保留为公司指引。[CLM_20260814_541F5C31] [CLM_20260814_8E4B9E25] [CLM_20260814_939CAEDD] [CLM_20260814_9A069D06] [CLM_20260814_BA7AC415] [CLM_20260814_E1A48290]

### Subject Evidence

| Claim | Role/use | Nature | Status | Confidence | Time | Source |
|---|---|---|---|---:|---|---|
| CLM_20260814_E1A48290 | PRIMARY | data | current | 0.9 | 2026-06 | SRC_20260814_F6E1EFAD — 财通电子&新科技 昀冢科技业绩说明会更新：MLCC业绩答卷&未来指引双超预期 |
| CLM_20260814_9A069D06 | PRIMARY | company_guidance | current | 0.8 | 2028年底 | SRC_20260814_F6E1EFAD — 财通电子&新科技 昀冢科技业绩说明会更新：MLCC业绩答卷&未来指引双超预期 |
| CLM_20260814_8E4B9E25 | PRIMARY | company_guidance | current | 0.8 | 2027年底 | SRC_20260814_F6E1EFAD — 财通电子&新科技 昀冢科技业绩说明会更新：MLCC业绩答卷&未来指引双超预期 |
| CLM_20260814_541F5C31 | PRIMARY | company_guidance | current | 0.8 | 2026Q4 | SRC_20260814_F6E1EFAD — 财通电子&新科技 昀冢科技业绩说明会更新：MLCC业绩答卷&未来指引双超预期 |
| CLM_20260814_939CAEDD | PRIMARY | company_guidance | current | 0.8 | 2026H2 | SRC_20260814_F6E1EFAD — 财通电子&新科技 昀冢科技业绩说明会更新：MLCC业绩答卷&未来指引双超预期 |
| CLM_20260814_BA7AC415 | PRIMARY | fact | current | 0.8 | 2026-08-13 | SRC_20260814_F6E1EFAD — 财通电子&新科技 昀冢科技业绩说明会更新：MLCC业绩答卷&未来指引双超预期 |
| CLM_20260814_0B6E52F8 | UNRESOLVED_ONLY | company_guidance | needs_review | 0.0 | 2026H2 | SRC_20260814_F6E1EFAD — 财通电子&新科技 昀冢科技业绩说明会更新：MLCC业绩答卷&未来指引双超预期 |
| CLM_20260814_E53B8E9C | UNRESOLVED_ONLY | company_guidance | needs_review | 0.0 | 2026H2 | SRC_20260814_F6E1EFAD — 财通电子&新科技 昀冢科技业绩说明会更新：MLCC业绩答卷&未来指引双超预期 |

### Uncertainty handling

`CLM_20260814_0B6E52F8` and `CLM_20260814_E53B8E9C` retain `needs_review` and confidence
`0.0`. The first is not used to assert a 70% product mix; the second is not turned into an
industry-wide cycle fact. Company guidance is phrased as “据公司材料/预计/计划”, while
`fact` and `data` remain separately typed. Time anchors stay in the Claim evidence and draft
statements.

## Traceability and validation

Every primary assertion carries at least one Claim ID. Each ID resolves to an existing Claim,
a `role=subject` link to the target Node, an existing Source ID and Source title. `context` and
`related` links are rejected as direct support. The existing frozen Current View content
validator also passes both drafts.

- Production SHA: `83A109D22EF08D5A230F28A341EF67CC0CA6FF5014BE7E89D7E2AB4DE8CAF895` before and after.
- Current Views: 0 → 0.
- Current View Proposals in DB: 0 → 0.
- Integrity: `ok`.
- Foreign-key violations: 0.

## Next recommendation

Human reviewers should `APPROVE`, `REVISE`, or `REJECT` each artifact proposal independently.
Only an explicit later approval may create a pending Production Proposal or an official Current
View through the frozen acceptance path. Do not broaden this pilot to other Nodes yet.
