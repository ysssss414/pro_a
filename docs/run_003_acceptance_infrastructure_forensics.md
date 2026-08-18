# pro_a R1 run_003 Acceptance Infrastructure Forensics

## Scope and evidence boundary

- Baseline: `1027d2a25fb367f27c2d0ad8bc3765b198513aa4`
- Run: `workspace/r1_acceptance/run_003` (read-only evidence; no file was edited)
- Evidence used: `R1_LLM_CALLS.jsonl`, `R1_RUNTIME_RESULTS.jsonl`, `R1_ERROR_CASES.*`, the isolated database, receipts and `R1_RAW_RUNTIME_SNAPSHOT.json`.
- Gold expected answers were not read. Relation acceptance counts and business results were not used to tune extraction or validation.
- run_003 did not persist response bodies. It persisted response/body hashes, lengths, HTTP/finish/token metadata, the post-parse outcome and exact validator errors. Therefore the unique truncated response's literal ending is unrecoverable; this is itself an observability defect. The regression fixture records this evidence limitation explicitly.

Classification codes used below:

1. model malformed output
2. parser/normalizer defect
3. prompt/schema contract mismatch
4. retry/state-machine defect
5. output truncation
6. other infrastructure defect

No business-level Relation rejection is classified as an infrastructure failure.

## Case-by-case diagnosis

All calls below were HTTP 200, used logical attempt 1, had no transport retry, and were configured with `max_tokens=32768`.

| Case | source_id / source | Stage / call | finish / tokens (prompt, completion, max) | Raw JSON syntax | Schema/validation error and retry reason | Terminal runtime state | Root cause |
|---|---|---|---|---|---|---|---|
| INFRA_001 | `SRC_20260818_E3F07A8E` / AI算力框架-海外与国产共振20260810_原文.docx | Impact Review `R1C_00003`; `IMP_20260818_8069C966` | stop / 3,464 / 891 / 32,768 | Yes, object | `Current View major_risks cannot be empty`; row was labelled retry for this validator error, but no retry call occurred | job done; Source analyzed; Impact `retry`; attempts=1; audit rows=0 | 4. The validator rejection is valid business enforcement; the infrastructure failure is the bypassed retry path. |
| INFRA_002 | `SRC_20260818_E3F07A8E` / same | Impact Review `R1C_00005`; `IMP_20260818_C0B7B2FE` | stop / 3,480 / 1,130 / 32,768 | Yes, object | `Current View major_risks[0] must preserve attribution for CLM_20260818_B228B8FE`; same text was the retry reason, without an actual retry | job done; Source analyzed; Impact `retry`; attempts=1; audit rows=0 | 4 |
| INFRA_003 | `SRC_20260818_112DC75A` / ptfe方案进展及硅微粉行业机会.docx | Impact Review `R1C_00010`; `IMP_20260818_1DCA1966` | stop / 3,064 / 854 / 32,768 | Yes, object | `Product Current View key_watch_items missing industry supply/demand`; no actual retry | job done; Source analyzed; Impact `retry`; attempts=1; audit rows=0 | 4 |
| INFRA_004 | `SRC_20260818_112DC75A` / same | Impact Review `R1C_00011`; `IMP_20260818_C2D27E74` | stop / 2,983 / 790 / 32,768 | Yes, object | `Current View investment_implication contains unsupported company/supplier(s): 硅微粉作为封装材料`; no actual retry | job done; Source analyzed; Impact `retry`; attempts=1; audit rows=0 | 4 |
| INFRA_005 | `SRC_20260818_85ADDE96` / Rubin Ultra NVL576规格升级，互联环节迎量价齐升.docx | Source Analysis `R1C_00014` | stop / 22,033 / 8,565 / 32,768 | Yes, object | `Invalid LLM output at node_matches[11].evidence_excerpt: field is required`; no schema/output retry path | job failed; Source remained `stored`; Impact stage not reached | 1 + 2. The model omitted one required field; the all-or-nothing normalizer incorrectly failed the whole Source instead of safely rejecting that match. |
| INFRA_006 | `SRC_20260818_681418DE` / 拥抱AI算力新材料黄金周期20260812_原文.docx | Source Analysis `R1C_00016` | stop / 25,697 / 18,762 / 32,768 | Yes, object | `Invalid LLM output at node_matches[15].evidence_excerpt: field is required`; no schema/output retry path | job failed; Source remained `stored`; Impact stage not reached | 1 + 2 |
| INFRA_007 | `SRC_20260818_C33F2FA3` / 海外算力和超节点的共舞20260814_原文.docx | Impact Review `R1C_00020`; `IMP_20260818_454BE8EE` | stop / 3,085 / 1,297 / 32,768 | Yes, object | `Current View core_logic[0] must preserve attribution for CLM_20260818_0AE0AC9B`; no actual retry | job done; Source analyzed; Impact `retry`; attempts=1; audit rows=0 | 4 |
| INFRA_008 | `SRC_20260818_C33F2FA3` / same | Impact Review `R1C_00021`; `IMP_20260818_BECE4CD2` | stop / 3,229 / 936 / 32,768 | Yes, object | `Current View major_risks[0] must preserve attribution for CLM_20260818_85C008E6`; no actual retry | job done; Source analyzed; Impact `retry`; attempts=1; audit rows=0 | 4 |
| INFRA_009 | `SRC_20260818_C33F2FA3` / same | Impact Review `R1C_00024`; `IMP_20260818_7B091CBE` | stop / 3,294 / 940 / 32,768 | Yes, object | `Current View major_risks[0] must preserve attribution for CLM_20260818_894592A9`; no actual retry | job done; Source analyzed; Impact `retry`; attempts=1; audit rows=0 | 4 |
| INFRA_010 | `SRC_20260818_5BDF601E` / 炬光科技20260812_原文.docx | Source Analysis `R1C_00025` | stop / 28,359 / 29,305 / 32,768 | Yes, object | `Invalid LLM output at node_matches[0].evidence_excerpt: field is required`; no schema/output retry path | job failed; Source remained `stored`; Impact stage not reached | 1 + 2 |
| INFRA_011 | `SRC_20260818_61A92E1E` / 联想集团20260814_原文.docx | Source Analysis `R1C_00026` | length / 26,176 / 32,767 / 32,768 | Unknown. Parsing was correctly bypassed because `finish_reason=length`; response body was not saved. | `LLM output truncated`; no same-payload retry | job failed; Source remained `stored`; Impact stage not reached | 5 + 6. True output explosion: a 17,481-character, one-chunk Source produced 102,211 response characters and saturated the output cap. Missing saved tail/syntax metadata made the exact ending unauditable. |
| INFRA_012 | `SRC_20260818_A3158594` / 锐捷网络20260814_原文.docx | Impact Review `R1C_00029`; `IMP_20260818_55AAFCB5` | stop / 3,040 / 1,117 / 32,768 | Yes, object | `Current View core_logic[1] must retain at least one Claim ID`; no actual retry | job done; Source analyzed; Impact `retry`; attempts=1; audit rows=0 | 4 |
| INFRA_013 | `SRC_20260818_A3158594` / same | Impact Review `R1C_00031`; `IMP_20260818_780DA3C6` | stop / 3,239 / 1,081 / 32,768 | Yes, object | `Current View major_risks[0] must preserve attribution for CLM_20260818_6A8C3C1E`; no actual retry | job done; Source analyzed; Impact `retry`; attempts=1; audit rows=0 | 4 |
| INFRA_014 | `SRC_20260818_9C68BF75` / 鹏鼎控股20260812_原文.docx | Source Analysis `R1C_00032` | stop / 26,215 / 25,333 / 32,768 | Yes, object | `Invalid LLM output at node_matches[2].evidence_excerpt: field is required`; no schema/output retry path | job failed; Source remained `stored`; Impact stage not reached | 1 + 2 |

## Root causes and minimal fixes

### Analyzer output failures

The Source Analysis prompt already required `node_matches[*].evidence_excerpt`; therefore this was not a prompt/schema contract mismatch. Four model objects omitted the field. The infrastructure defect was treating one unsupported match as fatal to the entire otherwise parseable Source.

Fix: a missing, blank or non-string Node-match excerpt now produces deterministic `evidence_validated=false` with `evidence_excerpt_missing`. The match enters `rejected_node_matches`; it can never create a direct match/link. Existing-node evidence requirements remain enforced.

### Impact Review retry failures

`PropagationManager._evaluate_impact_row` directly called the model and validators. On a validation exception its caller wrote `status=retry`, but it never invoked `ImpactRecoveryService`, never constructed the repair prompt and never wrote `impact_attempt_audit`. The persisted `attempts=1` reflected the initial call only. The separate recovery service also left validation exhaustion as `retry`, so an Acceptance run could end with nonterminal rows.

Fix: all initial and batch Impact evaluations now use one recovery implementation. It records the initial candidate/error, sends at most two repair prompts, keeps Node/current view/Evidence/context/previous candidate/errors intact, records every repair round, and ends as `proposed`, `no_change`, `needs_llm`, or explicit terminal `failed`. Exhausted `failed` results are idempotent and cannot invoke the LLM again. Validators were not relaxed.

### Output truncation

The single length case was not a normal large-source boundary: the parsed Source was 17,481 characters and fit in one configured 22,000-character chunk, while the model emitted 102,211 characters and exactly saturated the configured output budget. Globally raising the cap would hide the failure mode and was not done.

Fix: future `length` failures record prompt/completion/total tokens, configured maximum, response length/hash, JSON syntax status and the last 500 characters. Source Analysis discards the partial output and recursively bisects only the offending input chunk (maximum three split levels). Normal calls and the global token cap are unchanged. If a smaller chunk still truncates at the bound, it remains an explicit error rather than accepting partial JSON.

## Frozen-rule check

No change was made to Relation Evidence rules, direction gate, existing-node evidence requirement, candidate acceptance, Current View quality validators, or any other frozen business rule. The changes are limited to safe rejection, retry orchestration/audit/terminal state and truncation recovery/observability.
