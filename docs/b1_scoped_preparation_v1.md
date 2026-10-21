# B1 continuous-range planning and request preparation

This opt-in extension preserves the released B1 system prompt, v7 record schema,
Evidence Binding v2, one-call/12,000-output budget and extraction stop boundary.
It grants neither inference authorization nor review/admission authority.
Generic v4/v7 and unselected full-document planning keep their own contracts.

## Original-source range

`continuous-source-range-v1` / `continuous-range-native-planner-v1` supports one
continuous original page range. `source_scope.select` uses the real parser's
semantic-eligible original text. It freezes original SHA, parser component and
package identities, parsed/semantic text and segment hashes, page bounds, global
Unicode half-open coordinates, exact range SHA and mapping `global_start + local`.
Ambiguous/missing page markers, parser/source drift and out-of-range coordinates
fail closed. The original PDF is never rewritten or replaced by a clipped PDF.

The existing Analyzer generates the piece, scoped Node Catalog and exact Evidence
Catalog. The range must fit the existing hard cap and produce exactly one piece.
Its identity includes the range contract hash. Local Evidence offsets remain
Binding v2 coordinates; the range contract reconstructs original coordinates.
Assigned/Context refs must belong to this actual catalog. No merged offline units,
fuzzy evidence, empty-catalog substitution or larger global cap is introduced.
Selected-range completion never establishes full Source coverage.

## Counter registry

The original `deepseek-v41-complete-request-counter-v1` registration remains
immutable. v2 pins official recipe `935817c66f5d6e64838f419692545f06787e485f`,
the executable, source, Cargo manifest/lock, official source archive and tokenizer.
Only Core/Request/Encoding dependencies are built; no OpenCV or system install.
The local API alias `deepseek-flash` maps explicitly to `DeepSeek-V4.1-Flash` for
conversion; the Provider wire retains the API alias. This is an encoding-family
qualification, not proof of server weights or server-exact usage.

Scope selection explicitly requires v2. B1's frozen runtime, input and provider
configuration bind that selection; legacy B1 selects the old registration. The
new request domain is exactly two plain-text System/User messages, one strict
forced function tool with complete schema, thinking disabled, stream false,
temperature 0.1 and 12,000 output tokens. Extra request parameters, multimedia,
assistant/tool turns and other sampling settings are outside this qualification.

Old/new official converters were compared on full converted projections/debug
records, rendered text/structure and complete token ID sequences, including
Chinese, whitespace, JSON escapes, schema key order and literal special-token
spellings. The registered v1 executable matched the old conversion probe. Both
the normal request template and special-token handling differ in the new recipe;
tokenizer-file equality does not establish request-encoding equivalence. Detailed
private comparisons remain local. v2 proof binds ordered wire bytes, converted
request, rendered text/structure and all token IDs, as well as canonical object
identity. The 13,000 local input ceiling retains margin below 14,000 server input;
actual server usage and costs remain authoritative after any future response.

## Prepare-only entry and future consumption

An Operator explicitly selects B1 and the hash-pinned scope/context/counter files.
The real Source Operations parser freezes Native input, one Series and one Segment.
`workbench.b1_extraction.prepare` then records `b1-request-preparation-v1` using the
existing immutable artifact store and `B1_REQUEST_PREPARED` ledger event. No new
database table, Attempt, Accepted Result, budget reservation, Dispatch or worker
job is created. Repeated preparation is hash-idempotent, including after restart;
preparation after an Attempt is forbidden.

The artifact separates canonical request-object identity, ordered Provider wire
JSON/SHA, count proof, internal input/config/runtime identities and preparation
event identity. A future Attempt ID is absent: it does not belong to the API wire
and is allocated only by the existing reservation path. Unknown external outcomes
still retain their liability and never retry automatically.

Scoped dispatch requires this prepared artifact. It reconstructs the current
frozen Source/Scope/Context/Catalog/runtime/configuration/counter, freshly counts
the same request and compares the complete frozen payload and wire bytes before
existing reservation/Dispatch. Requests' JSON encoder is checked against the
frozen bytes. Any drift or missing preparation stops the whole request; it cannot
silently render a replacement and reuse the old proof. Preparation itself is not
an authorization to call any model.

Missing authors/dates/anonymous identities stay unknown in reference metadata.
Source metadata authority, Human review policy, Semantic/P0 budgets and P1/P2
remain separate downstream requirements. No fabricated HUMAN_USER resolution or
historical experimental Accepted Result is created by this extension.

## Qualification and deployment

Synthetic tests cover deterministic/cross-default-piece scope, global coordinate
reconstruction, cap/drift/ambiguity/foreign-context refusals, request domain,
prepare replay/restart/zero-reservation, exact future wire consumption and the
existing extraction stop. Applicable v4/v7, ownership, Evidence, lifecycle,
Operator, Windows MIC/HTTP and installed byte/identity gates must also pass.
These scoped checks do not claim whole-repository CI or live model quality.
Private source, requests, Gold, databases, account data and audit bundles must
never be committed. Release validation precedes any real preparation Run.
