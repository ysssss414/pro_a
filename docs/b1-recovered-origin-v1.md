# Failed-Raw Recovery Origin and full-field review revisions

This opt-in operator entry reconstructs a failed v7 response from the existing
durable archive. It neither creates an Accepted result nor resumes extraction.
The old accepted-v7 entry retains its strict accepted-result requirement.

| Contract | Meaning | Authority |
|---|---|---|
| `offline-node-evidence-link-recovery-v1` | Lossless representation recovery | None |
| `recovered-full-field-revisions-v1` | Explicit complete Claim and Node description proposals | Semantic authorship only |
| `source-recovery-candidate-set-v1` | Independently auditable failed-Raw Origin | Review preparation only |
| `recovered-v7-review-entry-v1` | Explicit existing Native/Semantic entry | Requires metadata decision and lifecycle selections |

## Trusted reconstruction

`CandidateInputs.publish_recovered/read` and `verify_documents` reconstruct the
Source bytes, Run runtime, SourcePiece, catalog, series/segment/event chain,
Attempt, configuration, outcome and Raw envelope from persistent records. The
Run must remain BLOCKED, the outcome must be confirmed successful tool output,
and its segment must have no Accepted result. Original Raw must still fail with
the supported duplicate evidence property error. Other failures are not repaired
by this entry. Original request, outcome, usage, liabilities and failure state
are never edited.

Scoped B1 uses the existing `b1_preparation.frozen_payload` reader, including the
original preparation event, ordered wire and qualified counter. It does not
silently replace a prepared request with a freshly rendered request. Ordinary
accepted-v7 reconstruction is unchanged. No Provider invocation, reservation or
Dispatch occurs in this entry.

The recovery proposal is re-executed against these trusted inputs. All original
support occurrences and linked Claim evidence are retained. Uploading an Origin
with a self-consistent content hash or reviewer name cannot attest its Source:
every read reconstructs it and compares the complete document. Registration is
an immutable artifact plus existing append-only lifecycle publication events;
it does not select a version or grant approval. Expected identity can be checked
inside the registration transaction.

## Full-field semantic proposals

Each child carries a complete strict v7 Claim record, exact original parent
index/hash, previous draft/hash, child ID, reason, and a review note for every
field. The complete compound parent remains separate immutable lineage.
Statement, structured data, scope, time, nature, record status, assumptions,
attribution, associations and Context must be reviewed together by a model or
human. The program validates shape, identity, Assigned Primary binding, Context
binding, references and governance restrictions; it is not a semantic oracle.
The previous draft and model reviewer string are provenance, not trusted review
identity or a Human choice.

Association edits are explicit full-field revisions, not disguised limited-v1
Claim splits. Node description/research-reason revisions have their own exact
parent/hash and reason; this version forbids Node identity/type/support edits.
Every original match receives an explicit KEEP/DEFER decision. Existing Node
Match, thematic `related` links and source Context interpretation are distinct.
A missing literal name diagnoses an entity match problem; it does not prove
that a thematic relation is false. Deferred thematic suggestions remain visible
in the preparation evidence rather than becoming automatic subject links.

## Closed independent set and existing authorities

This first version intentionally makes all new candidate Nodes and all Claims
with candidate-Node prerequisites DEFER. Original parents and unsupported
families are also DEFER. Full semantic revisions remain visible, but only
candidate-independent children can enter the existing projection. Their real
references cannot be omitted by a selection filter. Existing canonical IDs must
belong to the frozen catalog. No Source rank is automatically raised.

Metadata authority reuses `source_metadata_authority` with an explicit recovery
scope containing recovery identities rather than fictional Accepted hashes.
`start_recovered_review` requires its own entry descriptor, a resolution for this
scope, and the existing `RevisionLifecycle` selection of each eligible child and
its original parent. Publication, reviewer strings and content hashes supply
none of these decisions. Review Policy remains packet-specific and unselected.

The existing lifecycle, immutable packet, Advice, Seal, Admission and Operator
mechanisms are reused. REPLACE/REVOKE invalidate frozen selections; original
packets remain historical. The same state-database `BEGIN IMMEDIATE` reservation
is held through Canonical/Grant commit. There is no parallel approval system.

## Operator entry and task boundary

`python -m pro_a.workbench.recovered_origin` defaults to read-only inspection.
It requires configuration, Run, Attempt, recovery/revisions files and the exact
expected Origin identity. Registration additionally requires `--register` and
`--confirm-run` matching the Run. It never starts a worker, chooses Human
metadata/lifecycle/policy, invokes a model, or writes Canonical.

Private per-material objects, hashes and exact future commands are distributed
only in the local delivery ZIP. They are excluded from this public code change.
Qualification uses temporary databases, synthetic transport and explicit test
Human principals. Passing these fixtures does not authorize real registration,
Semantic/P0/P1/P2, Advice, Grant, Apply, or Source rank approval.

The required end-to-end run exposed a pre-existing catalog hot spot: the ASCII
suffix search could retry inside the same long run. A negative lookbehind limits
attempts to run starts; the earliest successful match, abbreviation handling,
catalog coordinates and identities are unchanged. Tests compare complete
catalogs against the previous expression, including multiline/CRLF and long
ASCII cases. No catalog cache or reduced validation boundary is introduced.

Private support maps use JSON coordinates named `original_path`/`claim_path`.
The review projection explicitly exposes these as `original_coordinate` and
`claim_coordinate`, keeping all values and evidence. This preserves the existing
disclosure prohibition on path fields without weakening it.

The broader Wire regression exposed a pre-existing diagnostic-test assumption,
also reproduced on unchanged Stable: the historical commit predates
`SourceOperations._start`, so its cloud surface cannot be compared. The test now
pins that exact missing historical selector and the existing fail-closed refusal,
rather than claiming a semantic comparison ran. Retry compatibility production
code is unchanged; no qualification or retry authority is granted.
