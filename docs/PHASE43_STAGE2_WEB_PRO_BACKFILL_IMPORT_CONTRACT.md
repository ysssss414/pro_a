# Qualified Web-Pro Foundation backfill import contract

The admitted input is `semiconductor_foundation_backfill_web_pro_v1`, with 21
logical Source slots representing 20 physical Sources. These counts are read from
the qualified manifest. Its 330-check upstream receipt is admission evidence;
the local structured-only validator also passed 100 checks. Neither receipt
authorizes canonical Production changes.

`phase43_stage2_web_pro_backfill_import_contract.json` publishes the exact file
inventory, SHA-256 bindings, manifest/qualification receipt digests, domain pack,
schema, adapter version, entry commit and complete Python runtime source digest.
It is a sanitized projection of the sealed private contract, whose digest it
records. The private contract additionally binds the absolute disposable target.
It was frozen before import. Runtime, package, domain or baseline drift rejects
execution; a new runtime requires a newly frozen contract and separate target.

The canonical schema remains 0.2.3 and the Workbench schema remains 10. The
semiconductor pack is declarative; Source/Node identity uses the shared catalog,
exact canonical/alias resolution and shared deterministic identifier helpers.
The importer creates candidate artifacts and Workbench projection rows only.

```text
MODE = QUALIFIED_STRUCTURED_FOUNDATION_BACKFILL
RAW_PDF_VALIDATION_REQUIRED = false
RAW_PDF_EXTRACTION_REQUIRED = false
PROVIDER_CALLS_REQUIRED = false
WORKER_LLM_PIPELINE_REQUIRED = false
PRODUCTION_WRITE_ALLOWED = false
ORDINARY_SOURCE_RUNS_PER_ROLLING_24H = 3
```

All original package bytes are archived privately and hash-bound. Every primary
candidate field is explicitly classified and retained in native candidate
content; supplemental tables and view Markdown remain immutable candidate
context. Unmapped fields require review and never become implicit canonical
columns or ontology additions. ACCEPTABLE is an automated recommendation,
not a human decision or Production status.

Shared Source byte identity is reused. Node creation requires no shared catalog
match plus bound evidence, and always requires human review. Alias ownership,
unknown confidence, ontology pressure, relation/parent ambiguity and view
activation remain human exceptions. Claims cannot be acceptable without matching
Source/hash/evidence/excerpt bindings. Temporal semantics are preserved; no
Official Current View is activated.

The native Foundation packet is registered through the existing artifact
registry and Stage 1 bounded projection. Default page size is 25, maximum 100.
All rows count toward aggregate pending WIP. One finite package can cross the
existing pre-intake hard threshold; subsequent new intake stops above 200.
Replaying the same package does not add WIP. Private packages cannot enter DEMO.

The Workbench's operational Source-review save/seal API cannot approve this
native Foundation packet. Human review uses its existing native decision fields
and immutable identity checks. This import mode is explicitly rejected by the
Production handoff path. Future Production-entry work requires separate scope.

Reproduction uses the existing local Python environment and public test config:

```powershell
# Freeze first; <target> must be a new disposable qualification root.
python scripts/qualify_structured_foundation.py --package <qualified-package> --production <read-only-production-file> --expected-production-sha 6e5a303ccee9c192c350c2550cc232649e56ffee939b7a09cd6b170cc1c8fba1 --pack domains/semiconductor --output <target>
# Repeat the same arguments with --execute to import into target/a and target/b.
# Each receives a byte copy of the baseline, a private state DB and artifacts.
```

Gate definitions were frozen separately in
`PHASE43_STAGE2_WEB_PRO_ACCEPTANCE_CONTRACT.md`. Private packages, qualification
databases, native review packets and obsolete raw-PDF preflight files are
excluded from the Git handoff.
