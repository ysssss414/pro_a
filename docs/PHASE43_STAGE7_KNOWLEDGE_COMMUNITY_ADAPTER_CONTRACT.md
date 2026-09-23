# Phase 4.3 Stage 7 — Knowledge Community adapter

`EXPORT_CONTRACT_VERSION = zsxq-pro-a-community-export-v1`
`EXPORT_CONTRACT_SHA256 = 6a3e2dc77287d426b8afda46df9fed24b6188e27df16946a8e88b59d91d66d48`

The shared JSON contract is [pro_a_community_export_contract_v1.json](pro_a_community_export_contract_v1.json). ZSXQ remains read-only and exports a deterministic ZIP for explicit transfer. The authenticated pro_a API offers `POST /api/workbench/v1/source-operations/community-preview`, `POST /api/workbench/v1/source-operations/community-import`, and `GET /api/workbench/v1/source-operations/community-domains`. POSTs require the ZIP body, CSRF token, and `X-Company-Node-ID`; import also requires an operator-selected `X-Primary-Domain`. The Company ID must resolve exactly to an active canonical Production Company. The processing domain must be an already registered pack. No Company or domain is inferred from ZSXQ text or model output.

The importer allows only the two exact ZIP members, rejects malformed/oversized archives and hash/count/order mismatches, and renders one deterministic PDF per bundle. The PDF contains only topic ID, date, author, group, keyword sources, and sanitized source evidence. Chinese glyphs are embedded from an OS-managed font; if none of the supported fonts is present, import fails closed. The private sidecar carries routing metadata and page ranges. Nothing maps ZSXQ credibility to Source Rank, Claim confidence, or Direct Impact.

The adapter reuses `SourceOperations.upload()` and `.start()`, with `community_material`, `knowledge_community`, null material date/title, and existing `LOW_TRUST_CLUE_ONLY` trust policy. An immutable `KNOWLEDGE_COMMUNITY_BUNDLE_BOUND` event precedes Company intent and queue events. The bundle SHA is bound into cloud-input checkpoints and checked on resume. Same bundle and Company dedupe; another Company for the same Source conflicts. Stage 1 capacity, existing Review and Attribution, and separate qualification/activation controls remain authoritative. Import creates no canonical claim, link, Current View, Direct Impact, or Production Apply.

Limits: ZIP 20 MiB; uncompressed 40 MiB; compression ratio 100:1 per member; 100 topics; 12,000 evidence characters per topic; 500,000 total. Workbench schema remains 11.
