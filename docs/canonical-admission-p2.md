# Canonical Admission P2

P1 seals Native and Attribution with one human decision. P2 qualifies that exact
result and freezes an Admission Plan. A second authenticated human decision
authorizes only the displayed Plan SHA, including its exact Envelope, Diff,
baseline, evidence and runtime. It does not verify the source assertion as fact
or authorize a Current View change.

The Workbench prepares and records authorization. It does not import, spawn or
call the Operator. The independent `python -m pro_a.operator_handoff --config
operator.toml --watch` process consumes registered approvals. It uses the existing
Operator register, attached SQLite transaction, receipt export and reconcile.
The historical Operator CLI remains available, but its register and execute
entries require P2 approval for every material approved through P1.

## Deployment boundary

The initial P2 deployment supports Windows mandatory integrity isolation.
Run Web and MCP under `python -m pro_a.process_boundary` using a Low primary
token. Use `--stdio` for the MCP pipe transport. The launcher disables privileges
and passes only the three explicit standard handles in stdio mode. The worker
runs separately at Medium integrity or above with its own Operator configuration.

Only mutable Workbench state, artifacts, processing workspace and dedicated
temporary directories may be provisioned Low. Keep Canonical and its parent,
Operator ledger/configuration, installed code, Python executable and launchers
Medium or above. Do not lower the whole workspace or runtime directory.
Provision ACLs and mandatory labels explicitly with an inventory and backup;
the process launcher never changes permissions. Before accepting P2 approval,
the server checks its actual token and proves that write, delete and DACL access
to Canonical, its parent and executing code is denied by Windows. A normal
unrestricted Web process cannot record P2 approval.

Start the worker from the trusted operator launcher or terminal, never from a
Web request or model tool. It has no listening socket and accepts no raw SQL,
mutations or browser-supplied execution payload. Its configured database and
ledger remain fixed. No new MCP tool is introduced.

## Daily operation

1. Review all evidence and decisions in P1, then approve Native + Attribution once.
2. Inspect the automatically qualified Canonical Admission Plan. Review each
   INSERT/UNCHANGED row, precise IDs, evidence, links/roles, excluded candidates,
   unresolved attribution and baseline. Private fields are individually named
   and hashed; their full values remain bound to the Envelope and Operator checks.
3. Confirm the exact plan once. The UI shows `AUTHORIZED_PENDING_OPERATOR` if
   the independent worker has not picked it up. No third business approval is needed.
4. Refresh to see the durable execution receipt and actual counts/post-state.
   `RECONCILED` means the registered receipt has been checked against Canonical.
   Existing MCP Source/Claim/Node/Evidence queries can consume the result.

Do not treat timeout or a lost HTTP response as a failed transaction. Reopen the
same material and read its durable state. Repeated approval reads the original
authorization. The worker serializes handoff across processes; a consumed Grant
is only reconciled, never reset or executed again. A READY Grant can resume the
unchanged transaction after a verified rollback. Existing journal uncertainty
remains a fail-closed Operator recovery condition.

Baseline, file identity or runtime drift blocks execution. A new Diff requires
a new qualified review/plan and another second human decision; P2 never mutates
the old sealed package to make it pass. Resolve an earlier unfinished execution
before processing another approval. Never restore an old Canonical database to
roll back a code release after successful knowledge ingestion.

Schema12 event records hold Plan, Approval and technical status. Grant and Receipt
remain authoritative in the existing Operator ledger and transaction contract.
No automatic schema migration, Provider call or production Apply is performed
by installing the feature.
