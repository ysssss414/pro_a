# Accepted v7 review bridge, R1

Revision lifecycle addendum: new review entries use
`accepted-v7-review-entry-v2`, with explicit selection, replacement and revocation
under [candidate revision lifecycle v1](b1-revision-lifecycle-v1.md). The v1
descriptor below remains part of immutable Origin/history reconstruction;
legacy v2 packets without lifecycle bindings do not authorize new execution.

This draft addresses the formal entry and review visibility gaps described in
PR #137. It does not deploy a runtime, migrate historical experiments, or grant
production admission. Existing v4 Origins and the v7 extraction-only qualification
stop retain their contracts.

## Versioned boundaries

| Contract | Responsibility | Authority |
| --- | --- | --- |
| `source-candidate-set-v2` | Reconstruct accepted v7 records and exact evidence | Review eligibility only |
| `controlled-claim-children-v1` | Explicit parent/child semantic proposals | No support judgment or Human permission |
| `accepted-v7-review-entry-v1` | Explicit post-extraction Native/Semantic review entry | Stops at Human review |
| Existing Evidence Binding v2 | Exact Primary and Context spans | Location proof, not semantic truth |

`CandidateInputs.publish/read` verifies the stored Source, Run runtime, frozen
domain/configuration, SourcePiece, catalog, segment ownership, request payload,
configuration digest, attempt/outcome ledger, complete accepted result and v7
research attachment. The original raw bytes are compiled again by the existing
v7 compiler; the result and attachment must match accepted artifacts exactly.
An experiment ID, outcome without acceptance, or fabricated caller-supplied
Origin is not a formal input. The pure projection function is not an attestation
API; all formal packet reads reconstruct from the durable archive.

Call `start_v7_review(..., entry_contract=ENTRY_CONTRACT)` explicitly after
publishing inputs. Ordinary `start_candidates` does not silently opt into v7.
The original extraction Run is not resumed into Semantic processing. A separate
review Run freezes the references, exclusions and entry contract. The existing
Semantic, P0, P1, P2 and Independent Operator gates remain required.

## Controlled revisions

A revision specifies its version, exact parent observation/revision, reviewer
and reason, and an explicit child list. Each child specifies its identifier,
statement, fact time, assumption, optional additional v7 Context dependencies,
and `SEMANTIC_REVIEW_REQUIRED`, `DEFER`, or `UNCERTAIN`. There is no KEEP input.
No splitting algorithm or model invocation is provided. Empty child lists defer
unselected parents. Parents and their complete raw values remain in the archive.

Children inherit the parent nature, attribution, Node references and Primary
binding. The limited contract cannot rewrite those fields or substitute Context
for Primary. Inherited Context remains; extra dependencies are explicitly located
by v7 and remain unproved interpretation dependencies. An unsupported but legally
located child remains a proposal requiring semantic review, not an accepted fact.
Statements requiring different Primary evidence need a separately reviewed
future extension; this contract does not manufacture it.

Every child revision changes the frozen Origin and P0 content identity. Old
Advice, Human seals and Admission Plans cannot authorize the new content. Old
immutable packets remain historical evidence; this is not an implicit deletion
or rewrite of a prior Canonical assertion. Exact repeated facts within the batch
share one candidate key and retain all observation/evidence lineage. A new
supporting observation for an already admitted fact fails explicitly with
`CANDIDATE_ADDITIONAL_SUPPORT_REVIEW_REQUIRED`, rather than silently discarding
support or duplicating the Claim. Support-only Canonical updates are outside R1.

## P0 projection and metadata

The formal Native projection includes parent raw Claim, child/revision identity,
original Run/Attempt/Accepted Result identities, runtime/schema/context digests,
exact Primary spans and hashes, Context dependencies, nature, attribution,
conditions, provider metadata and the explicit source-authority decision.
The private archive retains the complete runtime/configuration. The review DTO
contains its digest and relevant version identities, without filesystem paths,
transport secrets or the full request schema. Existing read/disclosure limits
remain unchanged. Unsupported oversized or unsafe content fails closed.

Metadata resolution reuses `source_metadata_authority`; each accepted-result
scope requires an explicit decision. Unknown identities may remain empty. Model
agreement does not create authority. Inconsistent resolved values across input
documents still block the review batch. Original model metadata is retained for
conflict review. Exact Node matches and ambiguities remain existing Native
diagnostics; an anonymous company is not assigned a Canonical identity by this
bridge. A verified v2 Claim-only packet may proceed without inventing Nodes.

## Qualification and production boundary

Tests use deterministic transport, isolated databases, synthetic advice and
explicit test Human principals. They cover accepted-origin reconstruction,
child lineage, disclosure boundaries, stale advice, unknown semantic support,
metadata conflicts, Context ownership, exact duplicates, and existing admission
permissions. Windows MIC is separately exercised with real Low Integrity child
processes against disposable files. Synthetic full-chain tests simulate approval
process roles; they are not real production Human authorization.

Private real-data probes remain local. A clearly labeled TEST FIXTURE may replay
their content through a new synthetic execution after exact locator reencoding.
That execution never becomes historical acceptance of the original experiment.
Private Source, Raw, Evidence, Gold, paths and request identities are excluded
from this public engineering record.

Before a real pilot: review and release the draft through the normal process;
verify the installed wheel/runtime; qualify the chosen material and Provider
budget separately; perform a new bounded formal v7 extraction; explicitly resolve
Source metadata and freeze selected child proposals; request Semantic and P0
review budgets; then obtain P1 and P2 Human decisions and use the independent
Operator. No step is automatically authorized by this draft or its tests.
