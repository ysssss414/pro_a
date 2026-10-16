# B1 formal-pipeline qualification: adapter required

An experimental v7 response can compile through the existing source-bound Native compiler, but that does not establish a formally accepted Processing Run or a reviewable Candidate Origin. This qualification adds synthetic boundary tests, without changing runtime behavior.

## Findings

- Source Operations still defaults to the explicit v4 output contract. A versioned v7 compiler already exists; B1 also requires its exact prompt and context policy to be frozen, not merely a version switch.
- The independent Candidate Origin implementation accepts v4 only. Its archive reconstructs Source, Run, Runtime, Attempt and immutable response identities. Experimental ledgers must not be backfilled as accepted formal output.
- Candidate Range Revision changes an exact Evidence range. It cannot change a statement or authorize a one-parent-to-many derivation.
- A legacy Native packet can expose an excerpt while omitting unrecognized parent/Attempt lineage and attribution. Registration alone does not grant P0 Candidate authority. This route is not a B1 admission workaround.
- Metadata authority and observation-preserving deduplication already exist. Model agreement does not establish authority. Different evidence for the same statement needs explicit reconciliation; it must not be discarded as a redundant observation.
- Existing P0, Unified Review, Canonical Admission and Operator controls are reusable. A disposable synthetic control completed mock P0, simulated P1/P2, a real isolated SQLite transaction and idempotent replay. This does not qualify the absent v7 derivation bridge or production OS isolation.

## Minimum follow-up

Extend the existing versioned Candidate Origin/Revision flow, preserving strict v7 compilation and Evidence Binding v2 as the sole Evidence authority. A semantic child proposal must bind its unchanged parent Raw object, original Attempt, child statement, primary binding, context dependencies and proposer identity. A semantic proposal is neither a deterministic split nor a Human approval.

P0 must actually receive the complete parent/child provenance, source attribution and Evidence. A changed child must invalidate affected Advice and downstream approvals. Unresolved metadata, unsupported clauses and ambiguous Nodes stay deferred. Candidate selection cannot turn failed Coverage into complete Coverage.

Reuse the Native intermediate representation and existing P1 Native + Attribution and P2 exact-plan controls. Keep `SOURCE_ASSERTION / UNVERIFIED / CLUE_ONLY`; no Official Current View update follows from source support. Do not create a second evidence or knowledge store, weaken a schema, or disguise v7 as v4.

## Scope and privacy

Only synthetic tests and this engineering note belong in Git. Private material, titles, quotes, Gold rows, request/response payloads, source hashes, local paths and databases remain local. New tests cover protocol rejection, range-revision boundaries, legacy packet authority, cross-batch metadata, explicitly unknown metadata and partially supported compound statements.

No live Provider request, production Run, real Human approval, production mutation, merge or Stable activation is performed. Existing draft work is unchanged. Result: **B1_ADAPTER_REQUIRED**, not production readiness. The next live pilot requires the missing bridge, a real-derived isolated end-to-end receipt, deployment authorization and separately budgeted extraction/semantic/P0 requests.
