# Phase 2.4C Current View IA Refinement

The previous View UI was a NO-GO for投研阅读 because it rendered the full Markdown export, exposed raw Claim IDs, and displayed overlapping `core_logic` / `key_facts` plus empty type sections. The canonical View records themselves were already valid and remain unchanged.

The Explorer now uses `content_json` for a compact structured card:

- Company: 当前判断 → 关键进展 → 投资逻辑 → 关键验证点 → 证据边界 → 证据。
- Product: 当前判断 → 关键变化 → 专业维度（仅非空且非重复）→ 投资含义 → 关键验证点 → 证据边界 → 证据。
- Evidence is summarized as the primary Claim count with the existing View Source action; Claim IDs remain in Claims.
- Governance metadata is secondary, and initial `recent_change` is hidden.
- Malformed/empty structured content falls back to `content_md` without a blank screen.

No backend, schema, endpoint, Production row, Proposal, or canonical `content_json`/`content_md` changed. The two fixture Views remain 2 official Views with the same Production SHA.

Focused presentation tests cover Company/Product templates, deduplication, empty-section hiding, evidence summary, source action, and initial recent-change suppression. Release regression on 2026-08-27 passed: frontend 8 files / 18 tests, frontend production build, and full pytest 365 tests. The Vite bundle-size warning and one Starlette deprecation warning are non-blocking.

Automated browser control was not exposed in the release environment. The existing API and frontend dev servers started normally, but visual acceptance remains manual:

- MLCC: open View; confirm Product template, no duplicated price fact, no empty type sections, visible evidence boundary and `3 primary Claims`, no raw Claim IDs, working View Source, and no console/runtime errors.
- 昀冢科技: open View; confirm Company template, conclusion, exactly 6 key progress items without duplicated core logic, visible evidence boundary and `6 primary Claims`, hidden initial recent change, no raw Claim IDs, working View Source, and no console/runtime errors.

```text
PHASE2_4C_COMPLETE = false

Frontend tests = PASS
Frontend build = PASS
Full pytest = PASS
Browser smoke = MANUAL_BROWSER_SMOKE_REQUIRED

Production invariant = PASS
Canonical View content invariant = PASS

Backend changed = NO
Production DB changed = NO
Canonical View content changed = NO

Evidence-quality metadata extension = deferred
DEFER_EVIDENCE_QUALITY_METADATA = true

GENERALIZATION_READY = NO
```

No new Views were generated. After the checklist passes, only the completion flags and Browser smoke result should change; no business-code change is required.
