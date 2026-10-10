# Partial non-canonical observation review MVP

Stage: `PARTIAL_NON_CANONICAL_OBSERVATION_REVIEW_MVP`.
Protected Stable: `941fe1109621da7ffc0703035930186f1c7516c1`.

Blocked Sources now have an independent research reader. It displays existing
accepted segment objects without waiting for Source completion. Failed v7 Raw
can also be inspected object by object, as quarantined research material. These
views and research markers confer no acceptance, coverage or canonical authority.

## Accepted research access

`workbench.research_review.project_run` reads frozen SourcePiece inputs, verifies
the Source event chain and bounded ledger, and loads the existing immutable Wire
and v7 review attachments. It preserves object order, original values, result
hashes and segment/family/index locators. It does not create permanent Claim IDs,
register a Review Packet or build the authoritative observation ledger.

The view includes frozen Source/Run/Series/Segment/Attempt/configuration/runtime
identities, observed provider outcome, exact evidence and source locations,
context review metadata and incompleteness. Candidate evidence retains all v6
support paths; Relations retain their explicit supporting Claim references.
`SEGMENT_ACCEPTED / SOURCE_INCOMPLETE / RESEARCH_REVIEW_PENDING` are distinct.

Read-only qualification of the protected real v7 Run found exactly two accepted
segments, 22 Claims and three Node Matches, with evidence displayed for all 25.
The Run remains BLOCKED. Its 24 uncalled leaves remain uncalled; their fail-close
FAILED state is not misrepresented as 24 failed provider responses.

## Strict prefix forensics and independent checks

`research_quarantine.parse_prefix` traverses root-object and array grammar using
the strict JSON decoder. Each complete value is decoded again from its exact
original slice. Evidence object spans are UTF-8 byte offsets, with SHA256 of the
original object bytes. Escapes, strings containing brackets, nested values and
Unicode do not alter boundaries. Duplicate keys, non-JSON constants, non-finite
numbers and unpaired surrogates are rejected. Duplicate root fields invalidate
membership proofs; no objects from that ambiguous root are retained.

Traversal stops at the first error. Unclosed objects and all following objects
remain unavailable. There is no regular-expression object splitting, bracket or
quote completion, suffix search, JSON repair, object removal or resubmission.
An object whose own boundary is complete may be examined even if its enclosing
array/root never closes. That never makes the whole response valid.

`inspect_response` supports only an explicitly frozen v7 attempt. It retains
original values, family/index and byte identity, including invalid objects.
Object Schema/lexical properties, existing v7 intent -> Evidence Binding v2,
Assigned ownership, scoped Node IDs and context locations are checked separately.
For complete JSON, Candidate name/support and Relation Claim references are
diagnosed, along with response Schema/Assigned acknowledgements. Dependencies
on invalid support are retained and reported, rather than silently discarded.

For malformed JSON, cross-object reference status is `REFERENCE_UNRESOLVED`,
total counts are UNKNOWN and suffix status is `UNKNOWN_SUFFIX`, even when a
prefix object's location is verified. Schema-valid correct locations remain
`SEMANTIC_REVIEW_REQUIRED / NOT_ESTABLISHED`: false numbers, attribution and
context declarations are not machine-certified research truth.

The protected third real response yields exactly nine complete prefix Claims.
All nine pass standalone Schema, independent location and Assigned ownership.
Their cross-object relations and suffix remain UNKNOWN; none is Accepted.
Raw bytes and original failure classification are preserved through the durable
attempt/envelope hash binding. Actual forensic outputs remain private.

## Independent private artifacts and research markers

`ResearchAttachments.publish` derives a diagnostic document from a verified
durable failed attempt; it cannot quarantine an already accepted attempt.
`NON_CANONICAL_QUARANTINE_V1` stores frozen scope, Raw SHA/artifact reference,
original object bytes' spans/hashes/values, status/error details, failure code
and response incompleteness. Objects bind their identities to this original
scope and Raw. No filtered ProviderRecord or SegmentWireResult is generated.

Artifacts use the existing checked private Artifact paths and `write_once`.
The existing Workbench writer transaction serializes publication. There are
**no new SQL tables, ledger rows, accepted results, registration records or
events**. The independent single-file diagnostic commits at immutable atomic
publication, not at a bounded ledger event. A crash before publication leaves
no committed document; after publication a deterministic replay recovers the
same content-addressed reference. Reading checks file hash, path identity,
authority and exact replay against the still hash-bound original attempt.

This intentionally avoids a two-file/SQL commit protocol and schema13. It is a
private research attachment, not a lossless accepted Segment representation.
The existing filesystem publisher's durability assumptions are unchanged;
tests cover process interruption/restart, not a claim of new power-loss guarantees.

Markers are independent append-only files, serialized by the same writer lock.
Each records reviewer, UTC time, original object identity, decision, reason,
sequence, previous file hash and its own sealed record hash. Reads validate the
chain, identity and authority. The only decisions are `INTERESTING`,
`NEEDS_FOLLOWUP` and `NOT_USEFUL`. They do not map to KEEP/CREATE/REUSE/Promotion.
The original candidates and Raw remain immutable. A marker interrupted after
publication is recovered as committed; the tool does not automatically retry it.

## Runnable internal reader

The package supplies a local static HTML view with original statements, exact
evidence, location/status, expandable provenance/context/fault details and
research markers. All model/Source text is escaped. There are no promotion
controls or added MCP/public API write tools.

Use the installed package with a private Workbench configuration and explicit
Run/Attempt IDs. The reader rebuilds frozen components without executing or
resuming the Run:

```sh
python -m pro_a.workbench.research_review --config workbench.toml --run RUN_ID --output research.html
python -m pro_a.workbench.research_review --config workbench.toml --run RUN_ID --inspect-attempt ATTEMPT_ID --output forensic.html
```

For isolated operator qualification, `--publish-attempt ATTEMPT_ID` prints a
private immutable artifact reference. Save that reference as `attachment.json`;
read it with `--attachment attachment.json`. To append a research marker:

```sh
python -m pro_a.workbench.research_review --config workbench.toml --run RUN_ID --attachment attachment.json --object-id OBJECT_ID --reviewer REVIEWER --decision NEEDS_FOLLOWUP --reason REASON
```

Export to a new file outside the Artifact store; an existing file is never
overwritten. Re-export with `--attachment` to display appended markers.
During this stage publication/annotation are exercised **only in synthetic
isolated environments**. The protected real Run receives no artifact or marker.

## Qualification and limits

The MVP's 21 focused checks cover lexical boundaries, invalid evidence,
missing/incomplete Candidate/Relation references, false-but-located semantics,
root-order independence, HTML escaping and the shipped reader entrypoint.
One complete offline formal Fake Provider Run accepts its first segment,
fails its next response and exposes both accepted content and a quarantined
prefix. It exercises persistence, interruptions, child-process restart, all
three markers and tamper rejection. Original ledger/event/acceptance tables
and the synthetic knowledge database remain unchanged by review operations.
The strict compiler rejects quarantine documents, incomplete coverage blocks
the authoritative observation ledger, and no Semantic Job is registered.

180 focused/related checks pass, including the MVP and v7, node intent,
Evidence Binding and Wire regressions. An initial wider round recorded one
failure in `test_foundation_dormant_and_schema12_surfaces_fail_closed`: the
old cloud execution-surface comparison reports unavailable historical surface
instead of the test's expected changed surface. The same failure is reproduced
from the protected Stable with identical execution sources and test bytes.
That assertion is excluded from the final selected round, not reported as PASS.
No existing execution/acceptance module or test is changed to conceal it.

Installed qualification reuses the existing isolated candidate and smoke
harness. It checks exact Git/Wheel/installed Python+SQL bytes, no-Git build
identity, dependency consistency, source-checkout denial, the new MVP, frozen
v7 bounded resume, default v4 restart, historical v1–v6 identities and package
resources. All **41 installed checks pass**. The qualified code commit is
`bc8dfc6f995dfd10ca00a693bd9fb2ed7e29f9a2`; its wheel SHA256 is
`67ed63f0a9c0295f709d8cc8736e55520fd68f0036edc85f2250c54f85b31865`.
All 166 packaged Python/SQL files match exact Git and installed bytes. This
receipt's follow-up commit changes documentation only. The installed reader
also reproduces the real 25 accepted objects and nine quarantined prefix Claims
with code-checkout access denied, no actual ledger writes and no provider calls.
The old private bootstrap's MCP import encounters the already-known Windows
pywintypes limitation in the isolated environment; direct frozen Workbench
reader configuration avoids that unrelated import without changing MCP.

Real qualification uses read-only SQLite connections plus a write-denying
authorizer and an audit guard that permits outputs only in the private report
directory. Full before/after inventories include Run13–16, the current v7 Run,
Raw/Accepted/Events, Source/native artifacts, Production, Current View and
formal installed Stable. No execution or acceptance rule is relaxed.

`REAL_PROVIDER_CALLS=0; NEW_REAL_RUNS=0; SEMANTIC_JOBS=0; PRODUCTION_WRITES=0;
CURRENT_VIEW_WRITES=0`. Default v4, frozen protocols v1–v7, Evidence Binding v2
and Schema12 remain unchanged. Real Candidate/Relation behavior is NOT_OBSERVED
because the qualified real responses contain neither; it is covered synthetically.

Public material contains only sanitized code, synthetic tests and this report.
Private Source/Raw/requests/responses, credentials, identities and user filesystem
paths stay local. No Stable release, merge, historical repair or new protocol.

`STAGE_RESULT=PASS`. Installed, private historical integrity and privacy gates
pass within the non-authoritative research boundary described above.
`NEXT_STAGE=PARTIAL_REVIEW_RELEASE_AND_REAL_SOURCE_ACCUMULATION`.
