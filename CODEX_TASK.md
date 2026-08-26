# Codex continuation brief — Phase 2.4A Subject-Aware Current View Pilot

## Phase 2.4A closure

`PHASE2_4A_COMPLETE = true`. Exactly two artifact-only `current_view_change` Proposal payloads
were generated for MLCC and 昀冢科技. Direct factual support is limited to `role=subject`;
MLCC's 8 company Claims remain `CONTEXT_ONLY`, and `related` is prohibited as direct support.
The MLCC draft uses 3 primary Claims. The 昀冢科技 draft has 8 subject Claims available, uses
6 current Claims as primary Evidence, and retains 2 `needs_review` Claims only as unresolved
review items.

Both proposals pass the subject-aware gate and existing frozen Current View content validator,
but `MLCC_VIEW_PILOT_READY`, `YUNZHONG_VIEW_PILOT_READY`, and
`SUBJECT_AWARE_VIEW_MODEL_VALID` remain `PARTIAL` because all Evidence comes from one B-rank
secondary Source and no draft has human confirmation. No Proposal or Current View row was
created. Production remains byte-identical at SHA-256
`83a109d22ef08d5a230f28a341ef67cc0ca6ff5014be7e89d7e2ab4de8caf895`.

## Phase 2.3F closure

`PHASE2_3F_COMPLETE = true`. The explicitly authorized atomic Production write created active Company Node `NODE_20260826_BC260F3E` (`昀冢科技`, `primary_type=Company`) with zero aliases; inserted 8 Company `role=subject` Claim links; changed 3 MLCC links from `related` to `subject`; and changed 8 MLCC links from `related` to `context`.

The minimal role contract is frozen as `subject / context / related`. Link existence no longer implies primary subject. Node Claims now expose `link_role`, and Explorer renders Subject / Context / Related from stored roles. Production is 294 Nodes / 737 Aliases / 19 Claim links: MLCC has 3 subject + 8 context Claims, and 昀冢科技 has 8 subject Claims. The NO_LINK Claim remains unlinked; Claims, Sources, Source links, Relations, Current Views, RQs and Gaps are unchanged. Pre-SHA `bad76ded1584ad22b86ccd8c19b1d6205b048c30103e71bb3e3e800f1f802d54`; post-SHA `83a109d22ef08d5a230f28a341ef67cc0ca6ff5014be7e89d7e2ab4de8caf895`.

## Phase 2.3E closure

`PHASE2_3E_COMPLETE = true`. The read-only review found no exact canonical or alias match for `昀冢科技`, so a non-applied Company Node proposal uses the frozen `primary_type=Entity` and no inferred aliases. The 11 Phase 2.3D links divide into 3 `MLCC_PRIMARY` Claims and 8 `COMPANY_PRIMARY_MLCC_CONTEXT` Claims; the existing MLCC links remain untouched.

Production currently stores only `claim_node_links.role=related`, which cannot distinguish MLCC as primary subject from MLCC as context. `ROLE_MODEL_SUFFICIENT = NO` and `MLCC_CURRENT_VIEW_READY = PARTIAL`: only the explicit 3-Claim entity-granularity allowlist is eligible, and no Current View was generated. Review artifacts are under `artifacts/phase2_3e/`; the formal report is `docs/PHASE2_3E_ENTITY_GRANULARITY_REVIEW.md`. Production remained byte-identical at SHA-256 `bad76ded1584ad22b86ccd8c19b1d6205b048c30103e71bb3e3e800f1f802d54`.

## Phase 2.3D closure

`PHASE2_3D_CLAIM_NODE_ACTIVATION_COMPLETE = true`. Human adjudication authorized exactly 11 Claims to link to active canonical Node `NODE_20260817_DABE52FE` (`MLCC`) with role `related`; `CLM_20260814_84099D0C` remains explicitly unlinked. The allowlisted links were inserted in one transaction after exact Claim/Source/Node/drift gates and a byte-identical Production backup.

Production now has 11 Claim → MLCC links, one unlinked Claim and one Node at `LEVEL_2_EVIDENCE_CONNECTED`. Claim contents/statuses, Source links, Current Views, Research Questions, Knowledge Gaps and Relations were unchanged. Formal receipt, coverage and activation report are under `artifacts/phase2_3d/` and `docs/PHASE2_3D_CLAIM_NODE_ACTIVATION.md`.

## Phase 2.3C closure

Phase 2.3C is a read-only human review package for the current unlinked Claims. `src/pro_a/adjudication.py` reads Production through the existing `ReadOnlyQuery` boundary, constructs only the deterministic union of direct Source links and exact canonical/alias signals, and emits `docs/PHASE2_3C_CLAIM_NODE_ADJUDICATION.md` plus `artifacts/phase2_3c/claim_node_adjudication.csv`. Every item remains `PENDING`; no Claim → Node link, proposal, view, gap, relation or decision is written.

The package is ready for reviewer adjudication, not Claim → Node activation.

## Phase 2.3B closure

Phase 2.3B is complete as a read-only audit. `src/pro_a/coverage.py` uses the existing SQLite `mode=ro` / `query_only` boundary and emits deterministic Node, Source, Claim and unlinked-Claim CSVs under `artifacts/phase2_3b/`. The formal findings are in `docs/PHASE2_3B_KNOWLEDGE_COVERAGE_AUDIT.md`.

Production audit baseline and post-check are identical at SHA-256 `8a4247b9da2c3d6f288f8a8af8519f33673bc45b5a4327a57c50436d39dd50b4`: 293 active Nodes, 737 aliases, 181 stored Relations, 174 current `part_of`, 2 Sources, 12 Claims, 0 Claim → Node links, 0 Current Views, 0 Research Questions and 0 Knowledge Gaps. All 12 Claims are unlinked and classified as ambiguous review candidates; exact canonical/alias mentions are review signals only.

No schema, frontend, API, LLM, write workflow or Production row changed. The next authorized decision is a human Claim-to-Node adjudication package, not automatic linking.

## Current state

Phase 1 已完成并冻结，Phase 1.1 已完成。最新正式 Production baseline：

- `workspace/pro_a.db`
- SHA-256 `83a109d22ef08d5a230f28a341ef67cc0ca6ff5014be7e89d7e2ab4de8caf895`
- 294 Nodes / 737 Aliases / 181 Node Relations
- 174 current `part_of`
- 19 Claim links: MLCC 3 subject + 8 context; 昀冢科技 8 subject; 1 unlinked Claim
- 0 Current Views / 0 Current View Proposals
- Phase 1.1 functional Relation import count = 0

Phase 2 — Knowledge Exploration & Interaction Layer 已启动。目标顺序：

```text
Search → Browse → Trace → Research → Ask
```

Phase 2.0 kickoff documentation、Phase 2.1A read-only query/API foundation、Phase 2.2 Explorer MVP 和 Phase 2.3A Knowledge Detail & Research Surface 已完成。

## Implemented read boundary

- `src/pro_a/query.py` 是独立 read model；SQLite connection 使用 URI `mode=ro` 和 `PRAGMA query_only=ON`。
- HTTP path 不使用会 commit / migrate 的 `Database.connect()` 或 `Database.init_schema()`。
- `src/pro_a/api.py` 提供 health、stats、node list/search/detail、1-hop neighbors、claims、sources、current-view、research-question、knowledge-gaps 和 Source Detail endpoints。
- Node list/search limit cap 为 100；Neighborhood 仅 current Relations、1 hop。
- Claim response 附 Source metadata；Node Sources 合并 direct 和 Claim provenance 并按 Source 去重。
- API 默认 `127.0.0.1`，可用 `python -m pro_a.api --config config.toml` 启动。
- Tests 只使用 pytest isolated temporary SQLite fixture，不指向 Production。
- Current View 复用 `CURRENT_VIEW_ORDER`；Node 存在但无 View/RQ 时返回 `null`，无 Gap 时返回 `[]`；Source Detail 不返回 `archived_path`。

## Implemented explorer boundary

- `frontend/` 是独立 React + TypeScript + Vite 应用；Cytoscape 仅渲染所选 Node 的 current 1-hop。
- UI 数据入口只有 read API；Node selection 分组并行加载 core 与 knowledge modules，单一 knowledge endpoint 失败不清空 Overview。
- Search 覆盖 canonical name / alias，使用 250 ms debounce、AbortController 和明确的 loading / empty / error state。
- 三栏桌面 UI 覆盖 Search、directed graph、Overview / View / Research / Claims / Sources；Source provenance 区分 direct 与 claim path。
- View 展示 governed Current View content 与 revision metadata；Research 展示 RQ、answer、variables、supporting/opposing Claims、falsifier 与所有 Gaps。
- Source card、Claim Source 与 View trigger 可进入右栏 Source Detail；可从 Source linked Node 返回 Node exploration。
- `?node=` 保存并恢复选择；API unavailable 状态提供 Retry，不进入白屏。
- Vitest + React Testing Library 覆盖 API client、Search、graph direction、View/Research、Source Detail navigation、partial failure、offline 与 StrictMode URL restore。

## Default continuation behavior

除非用户明确给出后续任务：

- 不自动扩展到 Phase 2.3B、Ask/chatbot、RAG、embedding、vector DB 或 recursive traversal；
- 不写 Production，不创建 write API，不调用 Proposal acceptance；
- 不修改 schema、frozen validators、Existing Node Match、Evidence、Relation semantics 或 human approval contract；
- 不借 Phase 2 修复 Relation backlog 或启用 IMA。

恢复工作时先读：

1. `docs/PHASE1_1B_FUNCTIONAL_RELATION_CLOSURE.md`
2. `docs/REQUIREMENTS_FROZEN.md`
3. `README.md`
4. `docs/ROADMAP.md`
5. `src/pro_a/query.py`
6. `src/pro_a/api.py`
7. `frontend/src/App.tsx`
8. `frontend/src/api/client.ts`
9. `frontend/src/components/ViewTab.tsx`
10. `frontend/src/components/ResearchTab.tsx`
11. `frontend/src/components/SourceDetailPanel.tsx`

## Next recommended step

由人工 reviewer 对 `artifacts/phase2_4a/current_view_pilot_review.json` 中的两个 Current
View proposal 分别执行 `APPROVE / REVISE / REJECT`。未经明确批准，不写入 Production
Proposal，也不创建 official Current View。
