# Phase 3F Stage 1 — Review-to-Promotion Handoff Census

Status: **FAIL / STOP — semantic or information gap**

Stage name: `PHASE3F_STAGE1_REVIEW_TO_PROMOTION_HANDOFF_QUALIFICATION`

The stage name and any next-stage name in this document are recommendations,
not recovered historical project requirements. This census implements only the
pre-code contract recovery required by the Stage 1 instruction. It does not
change Phase 3E, Phase 3D, or Production semantics.

## 1. Frozen scope and gates

```text
STARTING_GIT_BASELINE = 37cda6063d841875a18ed41fe5bf12efe6c1889f
STARTING_PRODUCTION_SHA256 = 3c0007f38b136686cb1e0e73e2ad2f389983f61ae2c81679fcf5067835c4eba0
PRODUCTION_SCHEMA_VERSION = 0.2.1
PRODUCTION_INTEGRITY = ok
PRODUCTION_FK_VIOLATIONS = 0
NEW_SOURCE_INGESTED = false
CLOUD_LLM_CALLS = 0
LOCAL_LLM_CALLS = 0
```

The pre-stage worktree contained the expected uncommitted Stage 0 contract and
only the previously understood ignored/untracked workspace artifacts recorded
during Stage 0. The Stage 0 contract was preserved unchanged as standalone
commit `849eb91339d9d57679fd8fb33951f5f13591f49d` before this census.

## 2. Evidence set

### Phase 3E reviewed-artifact surface

| Role | Frozen artifact | SHA256 / identity |
|---|---|---|
| Operational run manifest | `workspace/phase3e2sl6/operational_run/run_manifest.json` | `b087c8899a3fa7992a1e0116241a416258185282f8a3843186a1b86d1262380d`; run `INGEST_2644CBDB2693D5E0` |
| Evidence-bound extraction bundle | `workspace/phase3e2sl6/operational_run/evidence/evidence_bound_extraction_bundle.json` | `daceae2e4d84ecc32967be7b4f2af76e42355d5cbc10eb53852c0eb40a05e8aa` |
| Claim review | `workspace/phase3e2sl6/operational_run/review/claim_review.json` | `35b7670e195fddec131340ab6130ad7a9b0ed49d779497797192932f46ba88f2`; review `CLAIM_REVIEW_F81E3B1798012B1D` |
| Node-operation review | `workspace/phase3e2sl6/operational_run/review/node_operation_review.json` | `ab4dfc63c077010a7da4616cc43ed35fda9c4f9f9890cc4ffd4739c56958c7ea`; review `NODE_REVIEW_DCF77E9B2809B897` |
| Non-executable promotion preview | `workspace/phase3e2sl6/operational_run/promotion/promotion_preview.json` | `7a3ea43961e7a7929472289fc859305708dd435c173ae718ea92a8131e70b0fb` |
| S-L6 semantic-evaluation gold | `workspace/phase3e2sl6/phase3e2sl6_human_semantic_review.json` | `ad7862fd7865029263438b7f27d3c7e49577dff5aee01baad6ec40e8f8e1bad5` |
| Frozen Source | `workspace/phase3e2sl6/operational_run/source/20260831_通信设备行业研究超节点，从“堆卡”走向系统级协同.pdf` | Source `SRC_1D42C19206AE3622`; `2644cbdb2693d5e0ed3b9f13761123e268bfeae76ad1ebb04bb89416cba44c85` |

The operational Claim review is `DRAFT`: all 121 `human_decision` values are
`PENDING`, and `authorization.human_decisions_bound` is false. The operational
Node review is `DRAFT`: all 77 `review_decision` values are `PENDING`,
`authorization.all_review_decisions_pending` is true, and the suggestions are
explicitly advisory. The preview records:

```text
human_claim_decisions_bound = false
human_node_decisions_bound = false
executable = false
production_apply_authorized = false
production_executor_compatible = false
intended_mutations_generated = false
```

The separate S-L6 artifact contains `HUMAN_KEEP` and
`HUMAN_NEEDS_REPAIR`, but it is a semantic-evaluation gold set, not the
operational review surface. `semantic_gold_replay.py` uses these labels only as
an offline oracle and declares
`OFFLINE_FROZEN_GOLD_DIAGNOSTIC_NO_PRODUCTION_AUTHORITY`. It has no operational
Claim-review binding, Node decisions, reviewer authority, or promotion grant.
It therefore cannot be reinterpreted as promotion authorization.

### Phase 3D destination surface

| Role | Frozen artifact | SHA256 / identity |
|---|---|---|
| Deterministic promotion payload | `workspace/phase3d/STAGE3D2_QUALIFICATION_F6A9ECB_V2/phase3d_promotion_payload.json` | `617087227440fca165ebf9212a63b3d80bf056f0a5fe0e74503e8d8184e326f5`; payload `PROMO_2938849C91722C57` |
| Completed human Node review | `workspace/phase3d/STAGE3D3B_HUMAN_REVIEW_637D772/node_operation_review_human.json` | `1b3e8519bc8b33d836a16755082f83de1fcc200f5b377013220bf45eefe90e29`; status `HUMAN_REVIEW_COMPLETE` |
| Authorization-bound candidate | `workspace/phase3d/STAGE3D4A_PRODUCTION_CANDIDATE_22C36BE/phase3d_production_apply_payload.json` | `df6ef6d1de9c6306f23c7b41c3d3a6ce32bc611765d4a413c4c2dd452c9afecb`; payload `PROMO_F2C3A6F4A4AC6F07` |

The Phase 3D artifacts belong to source run `PILOT_20260902_572A6DF2`, not
the Phase 3E run. Their accepted human authorization is exact and cannot be
reused for Phase 3E candidates. The current builders in
`production_promotion.py` and `production_final_qualification.py` are bound to
the earlier Pilot 6 artifact roles/counts. The generic validators and shadow
engine are reusable, but no consumer binds completed Phase 3E Claim and Node
decisions into their payload model.

## 3. Field-level census

The strict Phase 3D authorization-bound candidate is used as the destination
reference because it is the existing artifact that carries explicit human
review provenance. `DIRECT` means the value is present with the same semantics.
`DERIVABLE_DETERMINISTICALLY` means a content-preserving computation is
sufficient. `MISSING` means the required information is absent.
`INCOMPATIBLE` means a present value has a different role or authority.
`NOT_APPLICABLE` means the field is outside the Stage 1 shadow-only boundary.

| Destination field or group | Class | Phase 3E source / rule and finding |
|---|---|---|
| `document_type` | `DERIVABLE_DETERMINISTICALLY` | Fixed Phase 3D contract constant; never copied from the non-executable preview type. |
| `payload_version` | `DERIVABLE_DETERMINISTICALLY` | Fixed Phase 3D version `1`. |
| `payload_hash`, `payload_id` | `DERIVABLE_DETERMINISTICALLY` | Canonical semantic-body SHA256 and `PROMO_` prefix rule already exist. |
| `metadata.source_run_id` | `DIRECT` | Operational manifest run ID. |
| `metadata.repository_commit` | `DERIVABLE_DETERMINISTICALLY` | Bind the handoff release commit; preserve the original extraction commit separately in artifact lineage. |
| `metadata.production_sha256`, `production_schema_version`, `production_schema_sha256`, `production_counts` | `DIRECT` | Exact Phase 3E manifest baseline is present and can be rechecked read-only. |
| `metadata.source_id`, `metadata.source_sha256` | `DIRECT` | Manifest and evidence-bound bundle. |
| `metadata.input_artifact_roles_and_sha256` | `DERIVABLE_DETERMINISTICALLY` | Compute exact hashes for manifest, extraction/evidence, completed reviews, and source receipt. The current frozen drafts can be listed but not represented as completed reviews. |
| `metadata.phase3c_artifact_roles_and_sha256` | `NOT_APPLICABLE` | Pilot 6-specific historical role; Phase 3E role bindings must remain explicitly distinct. |
| `metadata.source_package_sha256`, `source_recovery_receipt_sha256` | `INCOMPATIBLE` | Phase 3E has exact Source bytes and a `source_frozen` receipt, not the historical Phase 3D recovery-package roles. Renaming their roles would be silent coercion. |
| `metadata.stage3d2_qualification`, `stage3d3a_review`, `stage3d3b_human_review` | `MISSING` | These are downstream results and, critically, no completed Phase 3E review exists to bind. |
| `metadata.frozen_timestamp` | `DIRECT` | A frozen input/run timestamp exists; no current-clock value is required for semantic identity. |
| `source_materialization.source_id`, `original_name`, `size`, `source_sha256`, `package_relative_path` | `DIRECT` | Exact frozen Source metadata and bytes exist. |
| `source_materialization.package_sha256`, `archive_logical_destination`, collision status | `DERIVABLE_DETERMINISTICALLY` | Hash/path construction and read-only collision checks are deterministic, but are not reached after the authorization gap. |
| `source_materialization.production_archive_copy_authorized` | `NOT_APPLICABLE` | Must remain false in Stage 1; no Production archive write is authorized. |
| `sources[].source_id`, `source_sha256`, `artifact_hashes`, `archive_copy_intent` | `DIRECT` | Manifest, Source, and frozen receipt provide the same lineage. |
| `sources[].intended_row`: title, original name, SHA, source/analysis modes, source type/rank/origin, author, organization, publication time, ingested time, status, underlying source, metadata | `DIRECT` | Present in the Phase 3E proposed Source/manifest representation. |
| `sources[].intended_row.archived_path` | `DERIVABLE_DETERMINISTICALLY` | Existing Phase 3D archive naming rule can derive it from frozen Source identity; no copy occurs in Stage 1. |
| `sources[].intended_row.ima_media_id`, `ima_kb_id` | `NOT_APPLICABLE` | Empty values only; IMA is out of scope. |
| `evidence[].evidence_id` | `DERIVABLE_DETERMINISTICALLY` | Existing deterministic Phase 3D evidence-ID rule over immutable evidence fields. |
| `evidence[].claim_id`, `source_id`, `source_sha256`, `evidence_pointer`, `evidence_excerpt`, `validation`, `phase3c_evidence` | `DIRECT` | Equivalent evidence and validation fields are frozen for all 121 Claims; the historical field label may be preserved as compatibility metadata without changing its value. |
| `claims[].claim_id`, `source_id`, evidence link | `DIRECT` | Stable IDs and exact bindings exist. |
| `claims[].immutable_projection`, `immutable_projection_sha256` | `DERIVABLE_DETERMINISTICALLY` | Canonical projection/hash over the unchanged Phase 3E Claim. |
| `claims[].table_decision`, `semantic_admission` | `DIRECT` | The evidence-bound bundle and Claim review retain these decisions and reasons. |
| `claims[].reviewer_decision` | `MISSING` | Operational decisions are all `PENDING`. The S-L6 gold label has explicitly non-Production authority and is incompatible with this field's authorization role. |
| `claims[].executable` | `MISSING` | Eligibility cannot be derived without an explicit completed operational human decision. Defaulting to true is forbidden. |
| `claims[].intended_row`: statement, nature, times, Source, Evidence, attribution, scope, assumptions, status, confidence, novelty, structured JSON, creation time | `DIRECT` | Canonical Claim content is fully present, but row inclusion is conditional on missing review authority. |
| `node_operations[].operation_id` | `DERIVABLE_DETERMINISTICALLY` | Existing deterministic ID rule can bind the Phase 3E candidate ID and authorized decision. |
| `node_operations[].candidate_id` | `DIRECT` | Preserve `operation_candidate_id` with an explicit identifier-domain mapping; do not silently replace it. |
| `node_operations[].candidate`, Claim/Evidence refs | `DIRECT` | Name, type, aliases, prospective ID, supporting Claims/Evidence, and lineage exist. |
| `node_operations[].operation` | `MISSING` | `suggested_operation` is advisory only; every actual `review_decision` is `PENDING`. |
| `node_operations[].review_decision`, `review_reason` | `MISSING` | No completed operational reviewer decision, reviewer identity/authority, or binding reason exists. |
| `node_operations[].executable` | `MISSING` | Cannot be true without reviewed CREATE/REUSE plus Phase 3D checks. |
| CREATE `final_node`, `aliases` | `MISSING` | Candidate identity exists, but approved identity/alias intent does not. Candidate suggestions are not authorization. |
| REUSE `resolved_target_id`, `resolution`, `expected_target`, `approved_aliases` | `MISSING` | Advisory exact resolution exists, but approved target/alias intent and completed review binding do not. Fresh exact resolution would still not supply authority. |
| `relation_operations[]` executable decision and final endpoints | `MISSING` | Phase 3E promotion explicitly excludes Relations and has no completed Relation or parent-placement review. |
| Non-structural Relation execution | `INCOMPATIBLE` | Phase 3D blocks it on Production schema `0.2.1`; only validated structural `part_of` can be executable. |
| `excluded_operations[]` | `DERIVABLE_DETERMINISTICALLY` | Draft/PENDING, DEFER/REJECT, unsupported, and excluded Relation objects can be retained audit-only with their existing reasons. This does not make any object executable. |
| `intended_mutations[].mutation_id`, table, operation, key, row, `authorized_by` | `MISSING` | Mutations may be emitted only after exact Claim/Node authorization. The current preview deliberately contains none. |
| `human_authorization.human_review_id`, semantic/file hashes, decision authority, universe, counts | `MISSING` | No completed operational human-review artifact exists for the Phase 3E run. |
| `human_authorization.llm_authorization_used` | `DERIVABLE_DETERMINISTICALLY` | Must be false; zero LLM calls were made. This fact cannot substitute for human authority. |
| `human_authorization.production_apply_authorized`, top-level `production_apply_authorized` | `NOT_APPLICABLE` | Both must remain false; Stage 1 grants no Production apply authority. |
| `audit.artifact_convergence`, operation inventory, link policy, preserved exclusions, hard blocks | `DERIVABLE_DETERMINISTICALLY` | Exact hashes and unchanged records can be carried forward, conditional on a valid completed review input. |
| `qualified_execution_target` | `NOT_APPLICABLE` | Stage 1 is shadow-only and stops before any exact Production execution target/authorization. |

## 4. Rule-level census

| Destination rule | Class | Result |
|---|---|---|
| Accepted Phase 3D document type/version | `DERIVABLE_DETERMINISTICALLY` | Existing constants and validator. |
| Canonical payload identity and replay determinism | `DERIVABLE_DETERMINISTICALLY` | Existing canonical JSON/hash/ID functions; frozen timestamps can be used. |
| Exact input-artifact convergence | `DERIVABLE_DETERMINISTICALLY` | All frozen file hashes can be bound. |
| Exact Production SHA/schema/count baseline | `DIRECT` | Frozen in the manifest and independently read-only verifiable. |
| Exact Source identity and provenance | `DIRECT` | Stable Source ID, SHA, run ID, metadata, and bytes exist. |
| Claim-to-Evidence binding and evidence validity | `DIRECT` | Stable bindings, pointers, excerpts, and validation are present. |
| Explicit completed Claim authorization | `MISSING` | Operational Claim decisions remain `PENDING`; gold labels are oracle-only. |
| Explicit completed Node authorization | `MISSING` | Operational Node decisions remain `PENDING`; suggestions are advisory. |
| Reviewer identity/authority and exact review hash binding | `MISSING` | Not present for the operational Phase 3E review universe. |
| CREATE identity/alias approval | `MISSING` | Candidate proposals exist; approved final identity intent does not. |
| REUSE exact active target and type compatibility | `DERIVABLE_DETERMINISTICALLY` | Phase 3D resolver can recheck it, but approval remains missing. |
| CREATE/REUSE collision, NFKC/casefold, package collision, and target-drift checks | `DERIVABLE_DETERMINISTICALLY` | Generic Phase 3D validator is reusable. |
| UPDATE handling | `DIRECT` | Existing Phase 3D contract blocks executable UPDATE. |
| DEFER/REJECT audit-only behavior | `DIRECT` | Existing validator requires them to be non-executable and mutation-free. |
| Relation endpoint, self-loop, duplicate, cycle, and transitive-redundancy checks | `DERIVABLE_DETERMINISTICALLY` | Existing Phase 3D validator is reusable, but no Phase 3E Relation authorization exists. |
| Mutation operation/table allowlist | `DIRECT` | Existing Phase 3D validator permits INSERT only into its fixed table allowlist. |
| No silent coercion / unknown values fail closed | `DIRECT` | Phase 3D validators reject unsupported operations; the missing Phase 3E consumer cannot authorize any value. |
| Shadow-only Production hard block | `DIRECT` | Existing qualification path blocks configured Production and Stage 1 authorizes no write. |

## 5. Decision-vocabulary census

The same text label can have a different role at a different layer. Only the
repository-real role shown below is accepted.

| Surface and value | Classification | Reason |
|---|---|---|
| Phase 3E Claim `recommended_decision=KEEP/DROP/REVIEW` | `NON_PROMOTABLE` | Explicitly advisory system recommendation, never human authority. |
| Phase 3E Claim `human_decision=PENDING` | `NON_PROMOTABLE` | No completed human decision. |
| Any other Phase 3E operational Claim `human_decision` | `INVALID/UNKNOWN` | No completed operational vocabulary/schema/validator is frozen; fail closed rather than infer a mapping. |
| S-L6 gold `HUMAN_KEEP` / `HUMAN_NEEDS_REPAIR` | `NON_PROMOTABLE` | Offline evaluation oracle with explicitly no Production authority. |
| Phase 3D Claim reviewer decision `KEEP` | `CONDITIONAL` | Promotable only when supplied by the exact accepted review/signoff contract and all evidence/table/semantic gates hold. The Phase 3E drafts do not contain such a decision. |
| Phase 3D Node `CREATE` | `CONDITIONAL` | Requires completed human review, approved final identity/aliases, and collision validation. |
| Phase 3D Node `REUSE` | `CONDITIONAL` | Requires completed human review, one exact active type-compatible target, and drift/collision validation. |
| Phase 3D Node `DEFER` / `REJECT` | `NON_PROMOTABLE` | Audit-only and mutation-free. |
| Phase 3E Node `suggested_operation=CREATE/REUSE/DEFER` | `NON_PROMOTABLE` | Advisory only; it is not `review_decision`. |
| Phase 3E Node `review_decision=PENDING` | `NON_PROMOTABLE` | No human Node authorization. |
| Internal Phase 3D helper `APPROVE_CREATE` / `APPROVE_REUSE` | `CONDITIONAL` | Accepted only at that helper boundary and still subject to exact collision/target validation; not a license to translate Phase 3E suggestions. |
| Unknown/malformed Claim, Node, or Relation decision | `INVALID/UNKNOWN` | Must fail closed. |
| Phase 3E parent-placement suggestion | `NON_PROMOTABLE` | Separate review is required and no completed decision exists. |
| Phase 3E Relation candidate | `NON_PROMOTABLE` | Relations are explicitly excluded from the operational preview. |

## 6. Existing-path determination

```text
EXISTING_DIRECT_HANDOFF_FOUND = false
HANDOFF_GAP_CLASS = SEMANTIC_OR_INFORMATION_GAP
HANDOFF_IMPLEMENTATION_TYPE = NONE_STOPPED_BEFORE_IMPLEMENTATION
```

The gap is not a field-name normalization problem. The semantic content,
Source/Evidence lineage, candidate identifiers, and most baseline fields are
present. What is absent is the information that grants eligibility:

1. a completed, exact-hash-bound operational Claim review with a frozen allowed
   decision vocabulary, reviewer authority, per-Claim decisions, and reasons;
2. a completed, exact-hash-bound operational Node review with final
   CREATE/REUSE/DEFER/REJECT decisions, approved identity/alias intent, exact
   reuse target intent, reviewer authority, and reasons;
3. if any structural parent/Relation is to promote, a separate completed review
   binding its endpoints and decision; otherwise it must remain excluded; and
4. a frozen rule that binds those exact review artifacts to a Phase 3D payload
   without treating recommendations or evaluation gold as authorization.

The earlier Phase 3D human review cannot fill this gap because it binds a
different Source, run, candidate universe, and payload. Deterministically
hashing the current drafts would prove only that the decisions are pending; it
would not create authority. Mapping `HUMAN_KEEP` evaluation labels or advisory
CREATE/REUSE suggestions into executable decisions would invent authorization.

Consequently there is no frozen Phase 3E object that satisfies the required
positive qualification case, even though the artifacts contain many extracted
objects and advisory suggestions. A bridge built now could only be demonstrated
with fabricated positive authority, which Stage 1 expressly forbids. No adapter,
schema translation, synthetic positive fixture, shadow payload, or Production
apply was created.

## 7. Gate result and stop

```text
REVIEW_CONTRACT_RECOVERED = true
PROMOTION_CONTRACT_RECOVERED = true
FIELD_LEVEL_HANDOFF_CENSUS_COMPLETE = true
HUMAN_AUTHORIZATION_REQUIRED = true
UNREVIEWED_PROMOTION_BLOCKED = true
NONPROMOTABLE_DECISIONS_BLOCKED = true
UNKNOWN_DECISIONS_FAIL_CLOSED = true
REQUIRED_PROVENANCE_PRESERVED = NOT_QUALIFIED_NO_HANDOFF_OUTPUT
REQUIRED_EVIDENCE_PRESERVED = NOT_QUALIFIED_NO_HANDOFF_OUTPUT
HANDOFF_DETERMINISTIC = NOT_QUALIFIED_NO_HANDOFF_OUTPUT
PHASE3D_PAYLOAD_VALIDATION = NOT_RUN_NO_AUTHORIZED_PHASE3E_CANDIDATE
PHASE3F_STAGE1_RESULT = FAIL_STOP_SEMANTIC_OR_INFORMATION_GAP
```

Read-only verification performed after the census:

```text
CENSUS_ASSERTIONS = PASS
PHASE3D_FROZEN_REFERENCE_PAYLOAD_VALIDATION = PASS
PHASE3E_PREVIEW_DIRECT_VALIDATION = EXPECTED_REJECT:PAYLOAD_DOCUMENT_TYPE_INVALID
TARGETED_EXISTING_REGRESSION = PASS:10
COMPILEALL = PASS
PRODUCTION_CHANGED = false
PRODUCTION_SHA256_AFTER = 3c0007f38b136686cb1e0e73e2ad2f389983f61ae2c81679fcf5067835c4eba0
PRODUCTION_INTEGRITY_AFTER = ok
PRODUCTION_FK_VIOLATIONS_AFTER = 0
```

The Phase 3D result above validates only the previously accepted Phase 3D
reference payload. It does not validate a Phase 3E handoff payload; none can be
constructed from the frozen inputs without inventing authorization.

Recommended next gate (not a recovered historical stage):
`PHASE3F_STAGE1_REVIEW_COMPLETION_INPUT_GATE`.

Recommended objective: a human operator should complete and freeze, for the
exact `INGEST_2644CBDB2693D5E0` universe, explicit operational Claim and Node
decisions with reviewer authority, reasons, approved CREATE/REUSE identity
intent, and hashes bound to the existing Claim/Node review IDs and Source SHA.
Relations should remain excluded unless separately reviewed. After that input
exists, repeat Stage 1 from this census; do not infer the missing decisions and
do not grant Production authority.

`STOP_REASON = REQUIRED_OPERATIONAL_HUMAN_REVIEW_AUTHORIZATION_NOT_PRESENT`
