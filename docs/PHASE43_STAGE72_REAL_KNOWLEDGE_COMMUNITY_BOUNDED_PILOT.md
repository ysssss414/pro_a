# Phase 4.3 Stage 7.2 — Real Knowledge Community bounded pilot

## Qualification result

`BLOCKED / PROVIDER_FAILURE`. This is not `PASS_PENDING_HUMAN_REVIEW`: the only real Workbench Run failed during the first source-analysis cloud job, before Claim extraction, Evidence binding, or review packet registration. The Run remains `FAILED`; it was not retried.

The preferred Company, 景旺电子, is not present as a canonical Company in the real Production knowledge database. The permitted single fallback was the sole active canonical Company, 昀冢科技. One substantive but secondhand Community post, published 2026-08-14, was selected. Its raw read-only detail was frozen once; it had no direct files or images. This tests one primary item and zero attachments. The topic and group IDs are hashed in committed evidence; the private snapshot retains the platform identifiers and source content for operator inspection.

The exact-name search returned 31 hits from three successful groups; eleven of fourteen group searches failed with `ZsxqCommandError`. The selected item was the newest retrieved successful hit, not a proven global latest item. At retrieval it was approximately 41 days old. This selection limitation and the secondhand nature of the material prevent any source-authority upgrade. No independent corroboration was performed.

## Execution trace

1. Git preflight: `origin/main = 9179e28e73c8658b4893729a90f40166f556a0bd`; isolated branch `codex/phase43-stage72-real-community-bounded-pilot`. Production SHA `6e5a303ccee9c192c350c2550cc232649e56ffee939b7a09cd6b170cc1c8fba1`; Workbench SHA `f8cf49f5a4d0ed54ffb4f57bea051f0481a44d35adcd4d8f84eadeecb07b46e9`. Workbench schema 11, WIP `OPEN`, zero private Sources/Runs, zero Domain Packs/assignments.
2. ZSXQ read-only acquisition: one detail snapshot SHA `5d6495ca74876920c736c2edc730b9385272f6a03b0ded1b7b54b4c89e37ac2c`. One `deepseek-flash` routing request succeeded (request ID `7346a0c8-461a-4343-babc-12597d20a9bc`; 2,018 input and 846 output tokens). This routing result was used only to form the existing export contract, not to qualify authority or a Claim.
3. The unmodified single-topic export passed the bundle parser and canonical Company preview. A real Unicode issue in the PDF normalization path initially raised `COMMUNITY_PDF_TEXT_LOSS`: the configured Chinese font lacked two symbols in the post. The narrow repair encodes unsupported glyphs as visible Unicode escapes in the derived PDF, preserving the unchanged raw API snapshot and bundle. Deterministic rendering passed; the source PDF is two pages with SHA `01337f50a22eb139496fbd0cdac82a5d44b012e9735d023f7a2b0f934f24621e`.
4. Real Workbench import created Source `SRC_C70218574FB158D7` and Run `SOURCE_RUN_BBADD851DA1E4526BAB9B6EBD1DBDCF0`. Reimport returned both same IDs and `duplicate=true`. The Run context bound `SHARED_CORE_PENDING / PENDING`, no primary Domain, and Shared Core SHA `7393c58ffd981a60bcfec38615b10621def6d972d914f47971548cb6437fd87d`. Context SHA: `eb731f13986c3ff64984481fc2e09e45e53981d7cb1dd7b4c96c3bbf181a1350`.
5. `QUEUED → EXTRACTION_PROCESSING` completed locally. One real `SOURCE_ANALYSIS_PIECE` DeepSeek call then returned a durable `KNOWN_FAILURE / PROVIDER_ERROR`; job validation remained `NOT_RUN`, request ID and token usage were not recorded. The Run entered `FAILED / EXTRACTION_JOBS`. No semantic job, Claim, Evidence binding, or review packet was created. The failure is at the provider adapter boundary; the persisted record does **not** distinguish an HTTP rejection, malformed completion, or another `LLMError`. The Workbench key differs from the separately successful ZSXQ routing key, but the absent HTTP status means authentication cannot be identified as the cause.

## Quality gates and boundaries

| Gate | Result | Evidence or limit |
| --- | --- | --- |
| Source provenance | PASS | One frozen private raw detail; stable platform item/group IDs in private provenance, publish and retrieval times, bundle/source checksums. |
| Source canonicalization | PASS | Second import returned the same Source and Run IDs. Two upload events reflect first upload and exact duplicate. |
| Raw immutability | PASS | Raw API detail SHA remained `5d6495ca74876920c736c2edc730b9385272f6a03b0ded1b7b54b4c89e37ac2c`; PDF is a separate derived layer. |
| Shared Core Pending context | PASS | Frozen context SHA and Shared Core SHA match; assignment and Pack counts remain zero. |
| Provider execution | BLOCKED | One Workbench cloud attempt failed as `PROVIDER_ERROR`; no usable model output or usage receipt. |
| Claim extraction | NOT_REACHED | 0 candidate Claims and 0 extracted entities. |
| Evidence binding | NOT_REACHED | 0 bindings. |
| Review packet | NOT_CREATED | No native review packet or projection. |
| Workbench scope | PASS for observed rows | One Source, one Run, one failed cloud job and its bounded events/artifacts; no other active Run or review projection. |
| Production and ZSXQ writes | PASS | Production SHA unchanged; ZSXQ write calls = 0. |
| Visual browser check | UNAVAILABLE | Browser control runtime failed at initialization. Authenticated read-only local HTTP projection verified Source/Run state and zero packets. |

The pilot used **2 real provider calls**: one successful ZSXQ routing call and one failed Workbench extraction call. The aggregate input/output token totals and cost are `UNAVAILABLE` because the failed call has no usage record. The known routing subset is 2,018 input and 846 output tokens. One routing request ID is known; the failed Workbench request ID is `UNAVAILABLE`. The hard cap was 10, and no hidden provider retry was used.

Final Production SHA: `6e5a303ccee9c192c350c2550cc232649e56ffee939b7a09cd6b170cc1c8fba1`; Production write count = 0 by unchanged database hash. Final Workbench SHA: `1ff852dbe76c5fc4054c3e6f4e308b98a66f918dc3081e287b793c682a61ca44`. Observed delta: 1 private Source, 2 upload events, 1 processing Run, 7 Run events, 1 cloud input/registered packet (not a review packet), 1 source job, 1 cloud job, 1 dispatch/attempt/outcome, 1 frozen Run context; 0 cloud result artifacts, review projections, Domain assignments, or Domain Packs. The browser login used an ephemeral token held outside Git, then removed; local verification services were stopped.

## Code repair and remaining work

The importer glyph repair is isolated in commit `5d1cd8468a9c073bd0bd931ce8498da32dab6b6e`. The Stage 7 community suite passed `4/4`; Shared Core Pending suite passed `14/14`; the targeted glyph regression passed again after the final readability edit. The Run's runtime identity names the pre-repair Git HEAD because the real import preceded this commit; the canonical Source PDF SHA and stored context bind the actual derived input. This provenance limit is documented rather than hidden.

Before any separate recovery attempt, add a **privacy-safe** failure category to the real adapter's durable diagnostic (for example, HTTP status class versus JSON parse versus output truncation), while retaining no response body or credential. Inspect the Workbench credential configuration through the authorized operator path. A new Run, if later approved, must have a fresh explicit reprocess reason and stay within a separately authorized provider budget. This pilot does not authorize that retry.

The normal human Source/Claim/Evidence/Domain review is not yet practical: there are no Claims or review packet. See [the blocked pilot packet](PHASE43_STAGE72_REAL_COMMUNITY_PILOT_PACKET.md) for identifiers and deferred review questions. No PR or merge is created here; this branch carries only the narrow repair and sanitized evidence.
