# Bounded MCP read projection repair

`READ_PROJECTION_REPAIR = PASS`

`SOURCE_ANALYSIS_COMPACT_WIRE_RELEASE_ACTIVATION_R1 = STOP`

Bounded runs called `SourceOperations._project_run` through `OperationalReads`,
whose missing `bounded` attribute made both `get_processing_run` and `get_source`
return `READ_FAILED`. The new read facades reuse the existing ledger validators
and projection without constructing a runner, provider or write-capable store.
Connections remain SQLite `mode=ro` / `query_only`; no mutation method is exposed.
The 14 MCP tool definitions, including output schemas, are unchanged.

## Qualification

- Implementation: `f83239614bc068faa50c801d1ad7be6e04686257`.
- Reproduced the missing-attribute failure before repair.
- Focused regression: **89 passed** (8 new bounded tests, existing MCP stage 0 and
  stage 3 tests). An earlier test launch could not access the system temporary
  directory; the isolated workspace temporary directory resolved that setup issue.
- Planned, partial, subdivided, complete, failed and unknown-outcome reads match
  native projections. Corrupt event chains and raw artifacts fail closed.
- Exact implementation wheel SHA256:
  `396320a8c83846f33fefdd6e4a262a721b8bcfb8a23ace38d3bb67bac45a53ee`.
- All 137 Python files match source, wheel and isolated installation byte for byte.
  Only `pro_a/mcp/reads.py` differs from the prior release. Installed identity
  matches the implementation commit, runs without Git, ignores an unrelated
  enclosing repository, and rejects all six metadata-corruption cases.
- Real guarded stdio: health, target Source, and all 9 existing runs read
  successfully. All 14 definitions match the previous installation. 89 read-only
  connections; provider, retry, reprocess, review and database-write counters zero.
  Real database hashes unchanged by qualification.

## Frozen execution and live outcome

The operator explicitly authorized the fixed Source-derived transfer to DeepSeek
and selected isolated read qualification followed by execution on the unchanged
`be5e8c2c36ee0baa54378cfebe125e12defeae81` runtime. Cloud runtime, native runtime,
configuration and processing-context resume guards matched the existing Run 8
exactly. No frozen identity was rewritten and no compatibility guard was bypassed.
The corrected read package was not used to execute this frozen run.

One normal `advance_once` dispatched one Segment. The durable response completed
with `finish_reason=stop`, but pure read-only replay of the validator identified
unsupported `node_matches[].role` enums (5 entries; allowed `primary`, `related`).
The whole Segment was rejected as `INVALID_SEGMENT_RESPONSE`; Run 8 terminated
`BLOCKED / BOUNDED_EXTRACTION_FAILED`. No retry or Run 9 was created. No Segment
result, Semantic job or Review Packet was accepted/created. Unknown external
outcome liability is zero. The release activation remains STOP, not PASS.

The read repair can be deployed after that terminal state without changing or
resuming Run 8. A subsequent execution-contract repair requires separate scope
and qualification; this patch does not change prompts, provider parameters,
Wire validation, scheduler, runtime guards or frozen history.

Historical rows across 51 pre-existing tables remain present and unchanged;
all 14 historical queued jobs and old artifacts remain exact. Production,
Current View, review and promotion are unchanged. No raw Source, prompts,
provider response or private filesystem paths are included in this evidence.
