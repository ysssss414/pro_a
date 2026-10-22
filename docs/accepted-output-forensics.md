# Accepted output forensics

`pro_a.workbench.extraction_forensics.inspect_accepted_run` reconstructs accepted single-attempt output batches from a metadata-blocked Run without constructing a Provider or modifying processing state. It validates the existing event/record ledger, raw/result and prompt identities, source bytes, recorded runtime and frozen context. Unexpected attempt histories or incomplete evidence fail closed.

Pass a private `WorkbenchConfig`, the existing Run ID, and the recorded processing runtime/context SHA values. The returned object is private source material; do not publish it or commit it to this repository. This is an opt-in Python diagnostic, not a new Web/MCP route.

The result is always `SALVAGE_ONLY`, with `resume_authorized=false` and `canonical_permission=false`. Every claim remains `UNCERTAIN` / `NOT_AUTHORIZED`. Exact text groups preserve all Observation IDs and evidence; neither matching text nor byte-valid evidence proves semantic support. Pointer conflicts are diagnostic flags only. Metadata variants become an unresolved candidate using the existing explicit authority contract; no first-result selection or majority vote is performed.

This module does not alter the legacy lossless recovery topology, qualify a new execution runtime, reopen batches, dispatch remaining calls, create a Review Packet, submit Advice, or bypass Human/Operator approval. Formal continuation requires separate qualification. A read-only projection is not successful Pipeline recovery.

Use a controlled snapshot. Relocating a Workbench copy requires changing only the disposable copy's path bindings while preserving the original backup and all frozen run/event/result identities. On DELETE journals the diagnostic holds a read transaction; concurrent WAL changes fail via data-version checking. Interrupted or repeated reads persist no partial state.

Validation: synthetic tests cover wrong evidence remaining unapproved, duplicate preservation, missing evidence, identity drift, raw corruption, concurrent/idempotent reads and interrupted reads. Existing metadata authority, observation governance, recovery, Review Engine, Unified Review and Canonical Admission tests remain applicable. No private Run fixtures are committed.
