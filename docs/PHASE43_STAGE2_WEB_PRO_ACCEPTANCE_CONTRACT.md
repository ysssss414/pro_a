# Stage 2 qualified structured Foundation acceptance contract

This contract supersedes the abandoned raw-PDF preflight interpretation. The five
untracked raw-PDF preflight artifacts remain historical only and are excluded from
this qualification chain and Git handoff. The authoritative input is the qualified
Web-Pro structured package. Raw-PDF parsing, OCR, decryption and extraction are out
of scope. Source counts come from the package manifest, never a hardcoded PDF count.

| Gate | Frozen requirement |
|---|---|
| A | Exact Stage 2 entry/predecessor identity; Stage 0/1 and Gold evidence unchanged. |
| B | Unambiguous package; required files, all provided hashes, declared counts, unique IDs and internally consistent upstream qualification receipt. No raw-PDF gate. |
| C | Lossless original fields plus deterministic DIRECT_MAPPING/NORMALIZED_MAPPING/REVIEW_REQUIRED/UNSUPPORTED accounting; unsupported ontology goes to review/defer. |
| D | Shared Source/Node identities; same-byte existing Sources and exact compatible cross-domain Nodes reuse canonical identities; collisions never overwrite. |
| E | Every acceptable Claim retains a recoverable structured evidence pointer and Source/hash binding; cross-Source mismatches cannot become acceptable. |
| F | Every relation classified ACCEPTABLE/REVIEW/REJECT; type, endpoint, direction and evidence checks; ambiguous hierarchy/causality requires review. |
| G | Shared Stage 1 registry and bounded projection; 25 default/100 max page size; unchanged global WIP soft >100/hard >200. No fabricated human decisions. Native Foundation packet remains the review authority. |
| H | Two disposable workspace imports have identical structural identities/classifications; reimport reuses the same registered packet with no candidate accumulation. |
| I | Fresh relevant Stage 0/1 tests, Frozen Gold 120, full backend pytest, frontend tests/build and compileall. |
| J | Production before/after byte SHA remains 6e5a303ccee9c192c350c2550cc232649e56ffee939b7a09cd6b170cc1c8fba1; zero writes/apply. |

Mode: QUALIFIED_STRUCTURED_FOUNDATION_BACKFILL. No provider, extraction, Source run
or cloud job is created. Ordinary 3-run/24h quota is unchanged. One exclusive
offline importer admits one finite package, bounded at 128 files, 8 MiB/file and
10,000 structured rows/table. Review WIP is checked before new packet registration;
a package that produces hard-stop WIP blocks subsequent intake without erasing any
review item. Idempotent replay remains readable and does not add WIP. No per-Source
workspaces are used to bypass aggregate review limits.

The Workbench exposes the same paginated candidate projection and on-demand detail.
Its operational Source-review save/seal API is deliberately not an alias/relation
approval mechanism: structured Foundation decisions use the existing native
Foundation packet, separately authorized by HUMAN_USER. This Stage 2 importer is
candidate-only, and shared Production handoff rejects this mode explicitly.

All private structured files and original fields remain hash-bound in the isolated
qualification artifact store, including supplemental evidence, temporal metadata,
maps, coverage, conflict/review references and view Markdown. They are not copied
to Git. Public receipts contain hashes/counts and code/contracts/tests only.

Automated qualification is separate from human qualification. Mandatory exceptions
and a deterministic residual sample are delivered with the native review packet;
HUMAN_REQUIRED >0 does not by itself block automated import qualification. No Stage 3.
