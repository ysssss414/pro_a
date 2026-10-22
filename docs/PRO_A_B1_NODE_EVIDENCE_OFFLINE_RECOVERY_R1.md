# B1 Node evidence contract and offline recovery

This change adds an opt-in pure recovery module. It does not change the v7 tool
schema, frozen prompts, Node property compiler, Source Operations, durable
acceptance, Revision lifecycle, or any write/authorization entry.

## Contract decision

`node_candidate_intent.PROPERTY_FIELDS` represents semantic scalar properties.
`evidence_ref` is an active type-specific property on Event. On other types, a
single explicit value is retained in `preserved_fields`; it is not silently
discarded. `compile_properties` rejects a repeated field across the property
arrays, even when its values happen to be identical.

The sent v7 schema permits arrays of property objects but does not encode
uniqueness by `field`. The sent system explicitly prohibits repeated properties.
The v6 compiler first collects candidate support from explicit
`Claim.related_candidate_names` edges and `evidence_properties`, then compiles
scalar properties. A schema-valid response can therefore still fail this
semantic-format check. Duplicate support references are not proof of identical
content and must not be resolved with first-wins or last-wins.

Multiple Claim evidence bindings already legally support one candidate through
`related_candidate_names`. `candidate-support-set-ownership-v1` verifies all
support and derives containment in the assigned Segment. Support relationships
are inputs to that ownership calculation; they are not interchangeable with an
arbitrarily chosen ownership anchor or with Event's semantic evidence property.

## Explicit recovery rule

`offline-node-evidence-link-recovery-v1` requires a separate
`node-evidence-support-classification-v1` proposal. A reviewer must explicitly
classify the selected non-type properties as support already expressed by
linked Claims. The program does not infer this classification.

For a selected non-Event/type-specific candidate with multiple `evidence_ref`
occurrences, every occurrence must resolve to the same evidence unit, mode,
exact span and excerpt hash as at least one existing explicitly linked Claim.
The proposal is pinned to original bytes and the Source/Piece/Series/Segment
identities. The projection moves all selected occurrences out of scalar slots,
retains every original property and binding in its mapping, and records every
matching Claim support path. No Claim or reference is invented or deleted.
Identical duplicate occurrences remain distinct mapping entries. Different
evidence values are independently validated and preserved.

The existing v7 compiler, v6 support-set ownership calculation and Wire v3
expander validate the complete projected record. An unrepresented support,
Event/type-specific conflict, other scalar duplicate, dangling Claim reference,
or existing compiler failure still rejects the whole projection. There is no
automatic fallback to a partial accepted batch.

The artifact embeds the exact original bytes and a reversible occurrence map,
the proposal version, original/projected hashes, compile result and review
attachment. `verify` reconstructs the full artifact, so modifying a mapping,
reference, source identity or permission flag invalidates it. Single-evidence
behavior remains unchanged when there is no conversion proposal.

## Permission and downstream limits

`formal_accepted=False`, `semantic_authorization=NOT_ESTABLISHED` and
`canonical_permission=False` are fixed. The new artifact version is not an
accepted `CandidateInputs` origin. There is no ledger write or Provider path.
A local compile result hash is not an Accepted record, approval or Grant.

Analyzer validation must still run separately: explicit names/aliases for
existing-node matches/links, candidate quality and full references can expose
further issues. Source support is distinct from reality confirmation.
Source rank must not be upgraded merely to make a new Node eligible. If a Node
is held, dependent Claims retain `related_candidate_names` and remain held for
that dependency; independently auditable source statements need not all wait
for external fact verification.

Semantic splits, changes to links and Node descriptions are separately authored
review proposals, never automatic string splitting. The existing
`controlled-claim-children-v1` cannot express every link/Node edit, and its formal
ingress requires a real accepted v7 archive and Human lifecycle selection.
This module does not bypass those requirements. Replacing a revision must still
invalidate old content-bound Advice, Seal and execution authority.

## Qualification

Synthetic tests cover unchanged single evidence, distinct and identical repeated
support occurrences, unresolved support, exact-range mismatch, type/scalar
conflicts, intact references, immutable reconstruction and lack of formal
permissions. Related existing regression tests cover v7, research isolation,
accepted origins, Revision replacement/revocation and stale authority. Test
counts, installation evidence and the private real-response replay are reported
separately; overlapping suites are not additive coverage.

No private source material or model response belongs in repository fixtures.
