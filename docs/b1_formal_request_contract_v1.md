# B1 formal request contract v1 (unpublished)

This opt-in contract is separate from generic v7 and from the historical v7
Operator qualification entry. Existing v4/v7 defaults and their 24,000-token
output contracts do not change. No Web/MCP intake or automatic review is added.

## Frozen scope and request

`b1-evidence-first-request-v1` uses the byte-frozen B1 System Prompt, unchanged
v7 ProviderRecord/Schema and Evidence Binding v2. A new output binding/series
identifies one SourcePiece, at most 16 explicitly assigned units and one attempt.
Its output ceiling is 12,000, local input continuation threshold 13,000, server
input ceiling 14,000 and total reservation 26,000 tokens. Unknown outcomes retain
the reservation; no automatic retry or subdivision is authorized.

The local Operator explicitly selects B1. The phase4 configuration references
hash-pinned local context and counter manifests. Context pins Source/Piece SHA,
ordered Assigned refs, a reviewed dependency closure for every Assigned ref and
a source metadata reference with the same Source SHA. The reference is not a Human metadata resolution.
Missing/ambiguous authority still blocks downstream promotion under existing
Source Metadata governance. Context cannot be Primary Evidence.

The complete rendered request and local token proof are persisted in the existing
Attempt payload before dispatch. The counter processes that exact request,
including System/User, full tools/schema and the official V4.1 chat template and
special tokens. It is a local estimate, never server usage. The transport verifies
the same request/proof; no post-count request mutation is permitted. Runtime,
Processing Context, Source input, Attempt and Candidate Origin retain their
existing frozen identity chain. No experimental Raw becomes an Accepted Result.

The counter registry pins the previously qualified executable, source, Cargo
manifest/lock and tokenizer hashes and recipe commit. A different claimed V4.1
counter is not accepted merely because a new manifest hashes itself correctly.
Counter changes require separate qualification. The estimator grants no budget
or dispatch authority; the existing durable ledger reserves the sole attempt.
Actual server Finish/Usage/Model remain in Raw. A local model/budget failure is
recorded separately and cannot produce an Accepted Result.

## Difference boundary

The System Prompt, Evidence-first rules, schema/binding, tool definition,
temperature 0.1, thinking disabled, stream false, model/endpoint and output 12k
are preserved from B1. The reviewed closure is applied without rewriting text.
Formal execution IDs, processing metadata, source metadata reference and current
Node Catalog are explicit governance/request inputs. They change request identity
and require separate verification; technical tests cannot establish model-quality
equivalence. `evaluation_only` is false for an explicitly selected formal Run.
The model receives a contract SHA reference, not a repeated contract body. The
complete contract stays in the frozen execution payload and runtime chain.

## Stop boundary

B1 uses the actual Source Operations/ledger and accepts only verified v7 output.
It stops after bounded extraction. Candidate Origin and the released, separately
versioned review entry remain explicit subsequent actions, requiring Source
Metadata decisions and applicable P0/P1/P2/Human/Operator authority. Neither this
contract nor its successful extraction grants review or Canonical permission.

The existing internal runtime field `output_operator_qualification` carries the
distinct `b1-source-operations-extraction-entry-v1` identity. The old v7 entry and
its extraction stop are unchanged. No ordinary worker automatically selects B1.
Read-only projections report `B1_FROZEN_ASSIGNED_ONLY`; completion of that scope
does not establish full Source coverage. Legacy read responses omit these new
scope fields.

## Explicit local configuration and entry

The private phase4 TOML adds `[b1]` with exactly `context_file`, `context_sha256`,
`counter_identity_file`, `counter_identity_sha256`. The context JSON has version
`b1-reviewed-context-v1`, Source/Piece SHA, ordered `assigned_evidence_refs`,
complete `closure`, and `source_metadata_reference`. Files and private paths are
local; no credential belongs in these records.

After publication and separate live authorization, the existing service is
passed to `pro_a.workbench.b1_extraction.start` with
`request_contract='b1-evidence-first-request-v1'`, registered `source_id`, reason
and idempotency key. `advance(..., provider=None)` can freeze the actual Native
input before an authorized extraction attempt. `providers` reconstructs the
frozen configuration; `advance` uses the existing durable ledger. This document
is not a command to create a Run, dispatch, review, approve or Apply.

This Draft is not installed as Stable. Synthetic tests are not live B1 evidence,
and Pilot readiness requires publication, exact scope/request/count, external
processing permission, model/account/budget checks and a Human Review Policy.
