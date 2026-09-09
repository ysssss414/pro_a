# Foundation completed-artifact payload envelope

The payload envelope is separate from the unchanged V4 review execution and V3
storage/evidence contracts. It does not change decisions or mutation compilation.
An outer checksum is integrity, not Human Review authorization.

Frozen envelope ID:
`FOUNDATION_PROMOTION_PAYLOAD_ENVELOPE_CONTRACT_V2_COMPLETED_ARTIFACT_BOUND`

Frozen envelope SHA256:
`1e35d84cafd48ed3f95032c083ec24da6e746226a4ad2e81af22a3318194ce2a`

## Trusted caller inputs

`foundation_payload_envelope.PayloadVerificationBasis` is a frozen dataclass.
The caller must obtain its expected completed ID, semantic SHA, byte SHA, review
contract SHA, Production SHA/schema, historical review implementation commit and
payload implementation commit from an external trusted authorization. **Never
construct the basis from the payload being verified.** There is deliberately no
payload-to-basis factory or implicit default authority.

Supply actual completed JSON bytes or a read-only artifact path as
`completed_artifact`. The helper reads bytes once, hashes those exact bytes,
parses them, removes only
`human_completion.completed_packet_semantic_sha256`, and hashes compact sorted
UTF-8 JSON (`ensure_ascii=False`, no trailing newline). It checks the internal
declaration against that recomputation, then checks the external basis. State
must be COMPLETED with EXPLICIT_HUMAN_APPROVAL.

The payload's mandatory `review_basis` binds completed packet ID, semantic SHA,
file SHA, review contract SHA, and historical review implementation commit.
Actual artifact, trusted expectation, and payload binding must all agree. The
embedded review must equal the actual parsed artifact, not merely carry matching
declared identifiers. Semantically equivalent but byte-different files fail.
Embedded-review and envelope equality use canonical JSON identities, not Python
dictionary coercion (`false` must not compare equal to `0`, nor `true` to `1`).

## Entry points and order

`build_foundation_handoff(..., verification_basis=..., completed_artifact=...)`
uses the shared artifact helper and emits `review_basis` plus the frozen
`payload_envelope_contract`. Metadata's `foundation_review` file binding now
means byte SHA, not a canonical hash of parsed JSON.

`validate_payload`, `validate_foundation_payload`,
`validate_executable_operations` and the shared shadow entry point require these
external arguments for **every Foundation payload**, including legacy Foundation
payloads. Missing authority fails closed; there is no legacy Foundation escape
hatch. Other adapters retain their existing behavior.

External artifact/basis/envelope checks precede outer payload self-hash and
mutation-plan validation. The shadow entry point checks before opening SQLite,
and reuses the same basis for its pre-mutation validation. This change does not
grant authority to run it. Callers that have not supplied the new inputs cannot
execute Foundation payloads; existing Production authorization remains separate.

For serialized payload verification use
`validate_payload_artifact(payload_bytes_or_path,
expected_payload_file_sha256=external_frozen_file_sha,
verification_basis=trusted_basis, completed_artifact=actual_completed_artifact)`.
It checks the completed binding first, then the exact payload bytes and semantic
self-hash, then the mutation plan. Recomputing attacker-controlled outer hashes
does not make an invalid inner binding valid. The future Production authorization
must additionally pin the final qualified payload identity; this helper does not
create that authorization.

## Historical review versus new payload implementation

The completed packet's `repository_commit` is not rewritten. The new payload
stores `metadata.review_basis_implementation_commit` separately from
`metadata.payload_builder_verifier_implementation_commit` (the latter also remains
the established `metadata.repository_commit`). Both are checked against the
external basis. Changing only this envelope does not reopen Human Review.

`MUTATION_CORE` is the canonical dictionary of `intended_mutations`, `mapping`,
`node_operations`, `relation_operations`, and `claims`. It includes deterministic
runtime resolutions and audit dispositions but excludes the envelope and
metadata. An envelope-only correction must leave this entire core identical.

## Qualification boundary

Prior failed payloads are superseded diagnostics, never upgraded in place. New
diagnostic builds prove determinism and unchanged mutation core but are not
qualified payloads. No schema, Human Review, or official Current View changes are
part of this contract. Fresh explicit authorization is needed for later real
payload preparation/shadow validation under the new implementation and envelope
contract, followed by separate exact-payload Production authority.
