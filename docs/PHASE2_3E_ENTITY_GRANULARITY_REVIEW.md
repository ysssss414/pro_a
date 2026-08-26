# Phase 2.3E — Entity Granularity & Claim Attribution Review

YUNZHONG_TECH_NODE_EXISTS = NO
COMPANY_NODE_NEEDED = YES
ROLE_MODEL_SUFFICIENT = NO
MLCC_CURRENT_VIEW_READY = PARTIAL

## Executive conclusion

The deterministic lookup found no exact `canonical_name` or `node_aliases.alias` match for
`昀冢科技`. The 11 Phase 2.3D Claims divide into 3
`MLCC_PRIMARY` and 8
`COMPANY_PRIMARY_MLCC_CONTEXT`; no Claim was forced into `COMPANY_PRIMARY` or `AMBIGUOUS`.
The existing MLCC links should remain, but their semantic meaning is primary subject for
three Claims and context for eight Claims.

The Company Node proposal uses frozen `primary_type=Entity`; `Company` is recorded as the
entity kind/proposed business category because `Company` is not an allowed frozen Node Type.
No alias is proposed: the only explicit company string is identical to the proposed canonical
name.

## Deterministic Company Node lookup

- Exact canonical matches: 0
- Exact alias matches: 0
- Duplicate exact match: `false`
- Deterministic `昀冢` substring diagnostics: canonical
  0, aliases
  0
- Fuzzy matching, entity resolution, web research and inferred aliases were not used.

## Claim attribution review

`current_view_eligible` below is the entity-granularity gate only. Any later Current View
proposal must still pass the frozen Evidence, attribution and governance validators.

| Claim | Class | Primary subject | MLCC semantic role | Current View eligible | Reason |
|---|---|---|---|---|---|
| CLM_20260814_0B6E52F8 | COMPANY_PRIMARY_MLCC_CONTEXT | 昀冢科技 | CONTEXT | false | 昀冢科技是显式主体；新扩产中的产品结构是公司经营事实，MLCC 只表示产品/业务上下文。 |
| CLM_20260814_541F5C31 | COMPANY_PRIMARY_MLCC_CONTEXT | 昀冢科技 | CONTEXT | false | 昀冢科技一期产线的出货量、爬坡和满产时间是公司产能事实，MLCC 是该产线的产品上下文。 |
| CLM_20260814_8E4B9E25 | COMPANY_PRIMARY_MLCC_CONTEXT | 昀冢科技 | CONTEXT | false | 二期投资和量产计划直接陈述昀冢科技的资本开支与产能，不能升格为 MLCC 行业总产能。 |
| CLM_20260814_939CAEDD | COMPANY_PRIMARY_MLCC_CONTEXT | 昀冢科技 | CONTEXT | false | statement 与 evidence 都将量产提前及扩产计划归于公司；高容/超高容 MLCC 是上下文。 |
| CLM_20260814_980FA010 | MLCC_PRIMARY | MLCC | PRIMARY_SUBJECT | true | statement 与 evidence 直接陈述 MLCC 价格环比变化，未将公司营收、产能或投资写成产品整体事实。 |
| CLM_20260814_9A069D06 | COMPANY_PRIMARY_MLCC_CONTEXT | 昀冢科技 | CONTEXT | false | 三期投资、量产爬坡和公司月产能直接以昀冢科技为主体；MLCC 是产品上下文。 |
| CLM_20260814_BA7AC415 | COMPANY_PRIMARY_MLCC_CONTEXT | 昀冢科技 | CONTEXT | false | 认证和实验室进度属于昀冢科技的车规级高容产品，不能解释为整个 MLCC 产品类别已完成认证。 |
| CLM_20260814_BAED6789 | MLCC_PRIMARY | MLCC | PRIMARY_SUBJECT | true | Claim 直接比较本轮与上一轮 MLCC 行业周期持续期。 |
| CLM_20260814_D2C7FCD1 | MLCC_PRIMARY | MLCC | PRIMARY_SUBJECT | true | Claim 比较国内外 MLCC 原厂并陈述 AI 挤出效应，事实层级是行业/产品趋势。 |
| CLM_20260814_E1A48290 | COMPANY_PRIMARY_MLCC_CONTEXT | 昀冢科技 | CONTEXT | false | 营收必须归属于报告主体；Source 标题限定昀冢科技，且 evidence 没有行业汇总口径，因此 MLCC 只是业务上下文。 |
| CLM_20260814_E53B8E9C | COMPANY_PRIMARY_MLCC_CONTEXT | 昀冢科技 | CONTEXT | false | 昀冢科技/公司是原预判的显式主体；MLCC 上行周期是该公司判断的上下文，不应丢失公司 attribution。 |

Eligible Claim IDs: `CLM_20260814_980FA010`, `CLM_20260814_BAED6789`, `CLM_20260814_D2C7FCD1`

Ineligible Claim IDs: `CLM_20260814_0B6E52F8`, `CLM_20260814_541F5C31`, `CLM_20260814_8E4B9E25`, `CLM_20260814_939CAEDD`, `CLM_20260814_9A069D06`, `CLM_20260814_BA7AC415`, `CLM_20260814_E1A48290`, `CLM_20260814_E53B8E9C`

## `claim_node_links.role` audit

- Production distinct values: `related (11)`.
- Schema: `claim_node_links.role` is unconstrained text with default `related`; there is no
  subject/context enum or CHECK constraint.
- Read API: Node Claims select membership without returning role. Source Detail exposes the
  stored role as an opaque string; provenance also carries it without interpreting semantics.
- Frontend: role is typed and rendered as a plain string; no subject/context filtering exists.
- Coverage: Claim coverage and knowledge levels count link existence and ignore role semantics.
- Validators/write paths: Phase 1 ingestion/proposal paths and Phase 2.3D write `related` for
  Claim links. Existing `primary`/`related` validation in Analyzer applies to Source-to-Node
  matches, not a governed Claim subject/context model.

`ROLE_MODEL_SUFFICIENT = NO`: the current value cannot distinguish three MLCC-primary links
from eight MLCC-context links. A minimal future contract is `subject`, `context`, `related`,
but it must be frozen and implemented consistently before any role mutation.

## Current View gate

`MLCC_CURRENT_VIEW_READY = PARTIAL`. The explicit three-Claim allowlist can safely pass the
entity-granularity gate, but selecting all 11 Claims by `node_id=MLCC` is unsafe because the
persisted role does not encode subject versus context. This phase does not generate a Current
View.

## Proposed next write package (not authorized here)

1. Human-review and create one canonical `昀冢科技` Node using
   frozen `primary_type=Entity`; do not add unobserved aliases.
2. Freeze minimal Claim-link role semantics and update schema/read/coverage/write validation
   together.
3. Add Company subject links for the eight company-primary Claims; retain all MLCC links and
   review those eight MLCC roles as context. Keep the three MLCC-primary Claims as MLCC subject.
4. Re-run integrity, foreign-key, coverage and Current View eligibility checks before any
   governed Current View proposal.

`PRODUCTION_WRITE_AUTHORIZED = false`.

## Read-only invariance

- Production pre-SHA: `BAD76DED1584AD22B86CCD8C19B1D6205B048C30103E71BB3E3E800F1F802D54`
- Production post-SHA at artifact generation: `BAD76DED1584AD22B86CCD8C19B1D6205B048C30103E71BB3E3E800F1F802D54`
- Company Node proposal generated: `true`
- Production rows changed: `false`

## Scope exclusions

No Node/Alias/Claim/link/role/View/RQ/Gap/Relation/schema/API/frontend mutation was performed.
No LLM, embedding, RAG or web call was used.
