# Internal test intake: ten total Runs per 24 hours

Ordinary intake remains limited to three Runs per 24 hours. The explicit internal
`SourceOperations.start_qualification_intake` permits registered new Sources and
existing Sources within a fixed ceiling of ten total Runs in the same rolling
24-hour window. The count includes ordinary and qualification Runs, including
failed Runs. It does not reset or hide historical counts.

The v7 operator uses this path only when its caller supplies a sanitized
`qualification_reason`. Omitting that argument preserves ordinary intake. The
existing history-only qualification reprocessing entry remains unchanged.
No HTTP, frontend or MCP override is exposed.

The shared creation transaction checks the other intake guards, freezes the
selected execution identity, and records the existing run-window audit event
with an additional `qualification_limit: 10`. Audit failure rolls back creation.
Idempotent replay preserves the Run and event; concurrent creation cannot consume
the tenth slot twice. Both the entry and the fixed limit are included in execution
identity checks. This change grants no Provider calls, retry, subdivision,
Semantic execution, Production writes or Canonical admission.

Qualification uses disposable synthetic fixtures with networking forbidden.
The deployed Stable remains unchanged until separate release authorization.
