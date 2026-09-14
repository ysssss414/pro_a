# Phase 4.2 Stage 2: attribution and guarded operational handoff

Stage 2 separates native human review, Claim–Node attribution, generic shadow
qualification and external operator execution. The web application has read-only
canonical access. Stage 2 acceptance authorizes disposable database execution only;
real Production activation requires a separate explicit authorization.

The frozen machine contract is `PHASE4_STAGE42_STAGE2_PROMOTION_CONTRACT.json`,
SHA-256 `6d2dc5bf1d2d5c8e2945da86cd5bd25f0f4b3bb306e2946ad67738fdc9e16a7c`.
Adapter version is `phase42-operational-v1`; operator entry version is
`phase42-operator-v1`. Historical Foundation, Phase 2 and Production validators are
unchanged. Generic operational handoff remains SHADOW_ONLY_QUALIFICATION and still
fails the historical final validator with FINAL_PAYLOAD_DOCUMENT_TYPE_MISMATCH.

## Workbench preparation and human attribution

Stop Workbench writers, retain the existing Stage 1 configuration and run:

```text
python -m pro_a.workbench --config workspace/demo/workbench.toml prepare-attribution
```

This explicit schema 2→3 migration first flushes a `.stage1-backup`, preserves the
registry and all sealed native review BLOBs, then adds append-only attribution,
package and receipt tables. Startup never migrates knowledge or Workbench schema.
Stage 0/1 read and decision contracts continue to work with their earlier schemas.

Only after native review is sealed does the Review route expose attribution. Each
KEEP Claim must receive LINK, MULTI_LINK, NO_LINK or DEFER explicitly. Nodes come
only from the sealed review's CREATE/REUSE outcomes; a proposed display name is
never a key. CREATE uses the native prospective Node ID, while REUSE uses the
exact reviewed target. No Node support, co-occurrence or native suggestion creates
a link. Every selected Node has an independently explicit subject/context/related
role, reusing the existing canonical vocabulary and role validator. The sidecar
retains the exact existing Claim scope; the canonical link schema has no scope
column. DROP and KEEP_NEEDS_REVIEW are not canonical KEEP Claims and cannot link.

Attribution saves bind reviewer, actor/session, reason, timestamp, stable Claim and
Node identities, expected revision, packet/Source/sealed-object identities, schema
and runtime identity. Append-only events are replayed on read; conflicting revisions
require explicit retry, and identical operation IDs cannot append twice. Nothing is
prefilled. Sealing requires all accepted Claims and an explicit confirmation. The
sidecar is immutable; this version does not reopen a sealed attribution. DEFER is
a valid sealed human outcome but blocks qualification. Resolve it in a separately
authorized future attribution revision workflow; it is never converted to NO_LINK.

## Shadow qualification and exact changes

Qualification validates sealed native completion and the separate sidecar, verifies
the frozen Source bytes and exact baseline, then reuses `build_handoff_core` with
FULL_OPERATIONAL_POLICY. The existing core still performs its disposable shadow
apply, exact semantic diff, replay, rollback and restore checks. The Stage 1 native
validation receipt supplies a newly named Stage 2 bridge binding; no historical
authorization artifact is relabelled as Foundation.

The separate operational envelope adds only explicit sidecar links. Its insert
allowlist is sources, claims, nodes, node_aliases, node_relations (part_of only), and
claim_node_links. UPDATE, DELETE, schema changes, source_node_links, functional
relations, views, questions and other tables are excluded. Source summary metadata
from generic shadow output is removed; Stage 2 creates no canonical model summary.

The exact diff contains complete rows (including schema defaults), keys, table names,
inserts, unchanged rows and full pre/post semantic identities. Collisions reject;
an existing exact row is a no-op. Repeated qualification returns the same immutable
package. After a successful execution, projecting its same mutation set yields only
no-ops; its consumed grant cannot execute again. There is no automatic baseline rebase.

The Web projection shows exact keys and safe values, with explicit hashes for private
Source metadata columns. An external operator inspects the full registered envelope
before authorizing it. The browser never receives raw native envelopes or a writer
credential. Qualification does not change canonical knowledge.

## External operator entry

An operator-owned TOML binds the existing Workbench configuration and a separate
ledger directory, outside Workbench state and execution storage:

```toml
[operator]
workbench_config = "workbench.toml"
ledger = "operator/ledger.sqlite3"
```

The canonical target comes only from the pinned Workbench configuration. Execution
accepts a registered envelope ID, never arbitrary database paths or mutation JSON.
Use a disposable target for Stage 2 qualification. Keep the target and ledger on a
local filesystem supporting SQLite's atomic rollback-journal transactions. The operator
account needs canonical/ledger/materialization write access; the web account gets
canonical read access and only Workbench state write access. Do not grant the web
account access to the operator config or ledger. HTTP request context also blocks the
new operator connection before it can open writable SQLite, including accidental
direct calls. The HTTP application does not import or spawn the privileged module.

After inspecting the qualified envelope, the operator runs these separately:

```text
python -m pro_a.operational_operator --config workspace/demo/operator.toml init
python -m pro_a.operational_operator --config workspace/demo/operator.toml inspect --envelope OPERATIONAL_ID
python -m pro_a.operational_operator --config workspace/demo/operator.toml register --envelope OPERATIONAL_ID --confirm OPERATIONAL_ID
python -m pro_a.operational_operator --config workspace/demo/operator.toml execute --envelope OPERATIONAL_ID --confirm OPERATIONAL_ID
python -m pro_a.operational_operator --config workspace/demo/operator.toml reconcile --envelope OPERATIONAL_ID
```

Both confirm values must be the actual complete envelope ID. Registration pins the
target file identity, baseline, validated package and predicted diff. A changed
baseline, runtime, source, target alias, symlink/junction, hardlink or unregistered
identity blocks the entry. The Source is copied to a content-addressed immutable
`operational_sources/<source-sha256>` sibling of the target DB, flushed and verified
before commit; native execution files are never changed. A failed precommit attempt
may leave that verified, unreferenced Source object for later identical reuse.

Execution uses BEGIN IMMEDIATE over attached file-backed target and operator ledger,
DELETE journal mode and synchronous FULL. Only allowlisted canonical INSERTs pass
the SQLite authorizer; trigger-driven writes are rejected. All table contents must
match the exact predicted post-state and foreign keys must validate. Consumed grant
state and the immutable execution receipt commit atomically with canonical changes.
No table or schema metadata is added to the canonical target.

## Receipts, uncertainty and reconciliation

Precommit exceptions roll back canonical changes and retain a separate ROLLED_BACK
attempt receipt in the operator ledger; the grant remains READY. A successful receipt
contains adapter/entry versions, envelope/review/sidecar identities, baseline, diff,
actual counts, keys, timestamp and post-state identity. Consumed grants and their
receipts cannot be rewritten or deleted. A second concurrent/replayed execution
cannot consume the grant twice.

If commit was attempted and its result is uncertain, or commit succeeded but file
receipt export failed, return RECOVERY_REQUIRED. Never reset consumption. After a
postcommit process crash, the ledger proves consumption and prevents duplicate
inserts; operator reconciliation verifies the canonical post-state and Source bytes
before exporting the same immutable receipt. Missing/inconsistent ledger or receipt,
post-state drift, mismatched exported bytes, and leftover/unknown SQLite journals
block with RECOVERY_REQUIRED. This stage does not silently repair a stranded journal
or conflicting receipt file. Preserve all target, ledger and journal files for explicit
operator recovery. Physical power interruption was not simulated in acceptance.

The operator's reconcile command registers the verified receipt in Workbench. HTTP
can then verify only that registered ID, rechecking package/bindings/counts/keys, the
entire canonical post-state and materialized Source hash. The UI shows VERIFIED and
existing Explorer reads discover the Source through Claim–Node links. No hidden
lookup table, Source→Node shortcut, Current View change or browser Apply is used.

Tests are in `test_workbench_stage2.py`, `test_workbench_stage2_guards.py` and
`AttributionReview.test.tsx`, with synthetic-only subprocess crash and fixture helpers.
Acceptance receipts, exact envelopes, browser evidence and disposable databases
remain in ignored workspace storage. Stage 3 and real Production Apply are excluded.
