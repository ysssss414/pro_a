# Provider JSON syntax failure forensics R1

## Decision

`PROVIDER_JSON_SYNTAX_FAILURE_FORENSICS_R1 = PASS`

Run #13 Batch 2 failed because the provider's logical tool-call
`function.arguments` string was already malformed at the earliest captured
provider boundary.  The local adapter, UTF-8 conversion, append-only persistence,
reload and authoritative replay preserved that string byte-for-byte.  Local
validation correctly failed closed before ProviderRecord shape validation,
Evidence Binding, Semantic processing or a Segment result.

No retry, subdivision, provider replay, Run #14, Semantic job, Production write,
Current View write, Review action, release pointer change, activation or provider
call occurred in this stage.

## Frozen state and exact failed object

The pre-stage snapshot was taken before diagnostic code changes.  Its exact
Workbench, Production, Current View, private artifact and stable-runtime hashes
all match the post-stage snapshot.

| Identity | Value |
|---|---|
| Baseline / stable | `35e54a7d342317487b2e99e540fb4011bdec43b1` |
| Workbench schema | `12` |
| Run | `SOURCE_RUN_C20262EA7D194A5A865A83BB44D34855` (ordinal 13) |
| Run state | `BLOCKED`, `ORCHESTRATION`, `BOUNDED_EXTRACTION_FAILED` |
| Series | `SERIES_F57C73A6998FC55437B2A24BCF3D7122` |
| Piece | `PIECE_598EBD4F7EB24E8C` (piece ordinal 1) |
| Batch | `SEGMENT_21A99A39D2B2484AFBD954947CEB88F8`, stable path `[1]`, range `[16,32)` |
| Attempt | `ATTEMPT_F95CC2B665DDC7829FC81C0183E0AF8C`, attempt 1 |
| Provider request-body digest | `6818352b8d63f53db9b61d8ec701804639ef62d79c05eaffd173981ef90e6cef` |
| Ledger request identity | `933145e3a46b5ecae8549f75c8acf7801394d844b410d57f19b6343d218299be` |
| Configuration identity | `3a8ec2a67fd2cae8f71eb273ea3d1dba6fc2c662326474a857475662e22111fc` |
| Runtime identity | `e32654f7d5e8a8327ebb9e80b4133da4baa7c99231ecfb1ffe58d5d70d6b00f5` |
| Provider response identity | request ID `362addc3-ab15-4bee-9be9-16d93d30789a`; model `deepseek-flash` |
| Durable artifact identity | append-only outcome row plus artifact-relative hash `6e2373167b6eee00dd0691b6838bff65d7667e360a8264679372132fe2536fc5` |

The private artifact path and Source material are deliberately not published.

## Raw immutability

The durable local raw envelope is 20,763 bytes with SHA-256
`b94e45c96c2dba10ec3d24b8f175f09f043ea0b6c4daf42a789f87c0e2087002`.
Its base64-decoded argument payload is strict UTF-8, 15,093 bytes / 11,665
characters, with SHA-256
`563d2d0f4dc67089a3ae4813711c4de0bbea4fd36e983c1eb49f3697150a1c38`.
The embedded raw hash matches.  Before and after the forensic work, all four
values were identical: `RAW_ARTIFACT_MUTATED = false`.

Content-minimizing boundary records:

- first 64 argument bytes SHA-256:
  `353c2dc9c90d74df9a0c2f2b5f8bf7b48dc5a232fa4d57c80b702d0d41f5cd27`
- first 64 sanitized shape:
  `'{"xxxxxxxxxxxxxxx": {"xxxxx": "xxx xxxxxxx xxxxxxxxxxxxxxxxxxxxx'`
- last 64 argument bytes SHA-256:
  `b475418e41f6c31cec5977b926aacfb79de0db739dc3b2ad6c25c06655a6fcb8`
- last 64 sanitized shape:
  `'[]}, {"xxxxxxxxxxxx": "xxxxxxxxxxxxxxxxxxx", "xxxxxxxxxx": []}]}'`

## Layered diagnosis

### Layer A — provider outer envelope

The HTTP 200 provider body was successfully decoded as a top-level JSON object by
the live provider-boundary observer.  It contained exactly one assistant function
tool call, named `emit_source_analysis`, with `function.arguments` of type string.
`finish_reason=tool_calls`.  A malformed outer envelope or tool shape would have
failed before creating the observed outcome and `call-002` receipt.

The complete HTTP response bytes were not retained as a second durable artifact.
The earliest logical structured-output capture was the string returned directly
by `response.json()['choices'][0]['message']['tool_calls'][0]['function']['arguments']`.
This is sufficient for the failure-boundary conclusion below because the live
observer captured it before the adapter consumed the response and asserted its
UTF-8 bytes equal the persisted and validator bytes.  The full HTTP-body byte
identity itself is not claimed.

### Layer B — `function.arguments`

The strict CPython JSON parser reports:

```text
message     = Expecting ',' delimiter
line        = 1
column      = 7380
char offset = 7379
UTF-8 byte offset = 9941
error codepoint = U+007B "{"
nearest public schema field = structured_json
```

The 200-character-before / 200-character-after shape below retains only JSON
punctuation and whitespace; all content is redacted.  The error marker is the
`{` after the prematurely closed one-space string:

```text
… "xxxxxxxxxxxxxxx": " "{"xxxxxxx":"xxxxxxxxx","xxxxxxx":"xxxxxxxxxxxx","xxxxxxxxxxx":"xxxxxxxxxxxxxx"}" …
                         ^
```

`JSON_ERROR_CLASS = QUOTE_CORRUPTION_UNESCAPED_EMBEDDED_JSON`.
The provider emitted an unescaped nested JSON object where `structured_json` was
required to remain one JSON string.  This is not a record-shape, linkage,
Evidence Binding or semantic error.

### Layer C — parsed ProviderRecord schema

Not entered.  Focused tests place sentinels at record-shape validation, Evidence
Binding and Segment-result creation; none is reached after the syntax failure.
The live ledger contains no result for Batch 2, no completed Series result, no
Semantic job and no Review packet.

## Truncation determination

`OUTPUT_TRUNCATION = false`.

- configured maximum: 12,000 output tokens
- provider usage: 4,663 output tokens
- termination: `tool_calls`, not `length`
- HTTP/local external outcome: successful receipt, not capacity failure
- argument payload ends with a closing object brace and no trailing whitespace
- more than 4,000 characters remain after the syntax-error location
- no provider capacity, local budget or truncation signal was recorded

JSON invalidity alone was not treated as evidence of truncation.

## Transformation and persistence integrity

The live execution surface was frozen before dispatch.  Its `runtime.py`,
`live.py`, and `creation_override.py` hashes still equal the frozen receipt.  The
Batch 2 observer performed these checks in order:

1. parsed the provider outer envelope;
2. required the correct single function tool call and string arguments;
3. captured `arguments.encode('utf-8')` before the adapter consumed the response;
4. after raw durability, reloaded the append-only private envelope;
5. required captured bytes = adapter content bytes = persisted bytes;
6. required the raw-body hash match before invoking authoritative validation.

The existence of the completed call receipt proves those assertions passed.
Fresh replay also revalidates the local envelope identity and embedded raw hash.
Therefore:

```text
EARLIEST_CAPTURE_EQUALS_PERSISTED_RAW = true
PERSISTED_EQUALS_REPLAY_INPUT = true
ROOT_CAUSE_CLASS = PROVIDER_MALFORMED_STRUCTURED_OUTPUT
```

No evidence supports a local serialization, persistence or reload defect.

## Fresh-process deterministic replay

Three independent Python processes used the frozen stable package, disabled all
socket connections, forced Workbench connections read-only, and invoked the
authoritative parser from the durable artifact.  All three produced the same
failure class and exact line/column/character offset.  Their stdout hash was
`0b7aba152c8a3b3740230dc5e67d4328cac90730f5d781952a850b3774d60526`;
their audit-receipt hash was
`a45c023c79d837f555313963944c720b1df82acc06a2a1f06975818ce9f41e8b`.
Every replay retained the original Workbench and raw-artifact hashes and made zero
provider calls.

## Batch 1 / Batch 2 bounded comparison

Both requests used the same provider/model/configuration, system prompt, strict
tool schema, 12,000-token ceiling, complete SourcePiece, 77-unit context, 61
foreign context units, 3,595 Source characters and 15,112-character / 28,524-byte
message payload.  The system-prompt SHA-256 is
`4083dcb879420ca01d868b2138580f52cfeeef263ac9d8f1bbfcd687dabce11b`;
the tool-schema SHA-256 is
`ffe6fbbba3b4db8e857a6c538c59f5dfb9689da8aabb1b02ced0c2539ca304d7`.

| Owned Evidence text metric | Batch 1 | Batch 2 |
|---|---:|---:|
| owned refs | 16 | 16 |
| characters | 875 | 517 |
| UTF-8 bytes | 2,301 | 1,477 |
| `"` / `\` | 0 / 0 | 0 / 0 |
| `{` / `}` | 0 / 0 | 0 / 0 |
| `[` / `]` | 0 / 0 | 0 / 0 |
| newlines | 17 | 10 |
| code fences / JSON-like objects | 0 / 0 | 0 / 0 |
| disallowed control characters | 0 | 0 |

Both contain ordinary non-ASCII Source text; neither contains replacement,
isolated-surrogate, bidi-control or zero-width anomaly evidence.  Batch 2 is
smaller on the differing owned-Evidence dimension.  These observations are
correlation checks only and do not establish causation.

## Strict-tool behavior

The frozen request sent `strict=true`, the required tool schema and explicit
`tool_choice=emit_source_analysis`.  The provider reported a tool call with the
correct function name and string arguments.  This live observation demonstrates
that strict tool mode does not guarantee syntactically valid argument JSON.  The
local parser remained authoritative and rejected the malformed value without
coercion or repair.

## Retry and subdivision assessment

This one live malformed-JSON observation is a candidate for a separately
qualified, explicit same-Run retry, not evidence of capacity pressure.

- `RETRY_CANDIDATE = true`; retry execution in this stage is forbidden and was
  not performed.
- Preserve the same Batch, frozen request/context/source and original immutable
  attempt; allocate one new attempt identity and account one new provider call.
- Qualify a distinct reason such as `PROVIDER_MALFORMED_TOOL_ARGUMENTS_JSON`.
- Recommended bound: one retry, i.e. at most two total attempts for this Batch.
- Try the same Batch before considering any subdivision.
- A second non-truncated malformed response should fail closed and stop.  It does
  not by itself justify automatic subdivision; subdivision needs direct
  truncation/capacity or separately qualified input-shape evidence.
- Raw/envelope identity mismatch, local persistence defect, runtime/config/context
  drift, security/privacy failure, invalid tool identity/type, unknown external
  outcome, and ownership/linkage/Evidence Binding/semantic validation failure
  must never be admitted through repair or tolerant parsing.

`SUBDIVISION_JUSTIFIED_BY_CURRENT_EVIDENCE = false`.

## Tests and baseline exception

Focused qualification: `13 passed`.

The final related matrix covered lexical tool adapters, bounded persistence and
recovery, output decomposition, claim disposition linkage, Series binding,
ProviderRecord parsing and whole-piece execution: `886 passed, 1 failed`.
The single failure is a pre-existing baseline assertion in
`test_active_runtime_closure_and_historical_surfaces`: it requests the obsolete
`whole_piece_compact` runtime key, while schema 12 now freezes
`whole_piece_output_decomposition`.  This stage changes neither that test nor the
runtime identity code and does not repair the unrelated baseline mismatch.

## Immutable post-state

```text
Workbench DB SHA-256 = e10667e589011ccc8d912d75d2e2c58f9cae2bc3ec2273b305a222625a8b2aa3
Production DB SHA-256 = 6e5a303ccee9c192c350c2550cc232649e56ffee939b7a09cd6b170cc1c8fba1
Current View tree SHA-256 = 32632183ed24ef668786abf7775ef82f9136c9427342f8a55954cd010400d924
Private artifact tree SHA-256 = 59619b0b88dc809f1043103050cc6c40c9682929d8751fff2f5956f91b126e01
Run #13 provider attempts/outcomes = 2 / 2
Run #13 accepted Segment results = 1 (Batch 1 only)
Run #13 Semantic jobs / Series results / Review packet = 0 / 0 / none
Source run count = 13; Run #14 absent
```

## Required final fields

```text
PROVIDER_JSON_SYNTAX_FAILURE_FORENSICS_R1 = PASS
BASELINE_SHA = 35e54a7d342317487b2e99e540fb4011bdec43b1
STABLE_SHA = 35e54a7d342317487b2e99e540fb4011bdec43b1
SCHEMA = 12
RUN13_STATE_BEFORE = BLOCKED
RUN13_STATE_AFTER = BLOCKED
RUN13_PROVIDER_CALLS_BEFORE = 2
RUN13_PROVIDER_CALLS_AFTER = 2
FAILED_BATCH_ID = SEGMENT_21A99A39D2B2484AFBD954947CEB88F8
ATTEMPT_ID = ATTEMPT_F95CC2B665DDC7829FC81C0183E0AF8C
RAW_ARTIFACT_SHA256_BEFORE = b94e45c96c2dba10ec3d24b8f175f09f043ea0b6c4daf42a789f87c0e2087002
RAW_ARTIFACT_SHA256_AFTER = b94e45c96c2dba10ec3d24b8f175f09f043ea0b6c4daf42a789f87c0e2087002
RAW_ARTIFACT_MUTATED = false
OUTER_PROVIDER_ENVELOPE_JSON_VALID = true
TOOL_ARGUMENTS_JSON_VALID = false
JSON_ERROR_CLASS = QUOTE_CORRUPTION_UNESCAPED_EMBEDDED_JSON
JSON_ERROR_LINE = 1
JSON_ERROR_COLUMN = 7380
JSON_ERROR_CHAR_OFFSET = 7379
JSON_ERROR_BYTE_OFFSET = 9941
OUTPUT_TOKENS = 4663
FINISH_REASON = tool_calls
OUTPUT_TRUNCATION = false
EARLIEST_CAPTURE_EQUALS_PERSISTED_RAW = true
PERSISTED_EQUALS_REPLAY_INPUT = true
FRESH_PROCESS_REPLAY_COUNT = 3
FRESH_PROCESS_REPLAY_DETERMINISTIC = true
ROOT_CAUSE_CLASS = PROVIDER_MALFORMED_STRUCTURED_OUTPUT
LOCAL_FAIL_CLOSED_BEHAVIOR = PASS
SEMANTIC_WRITES = 0
PRODUCTION_WRITES = 0
CURRENT_VIEW_WRITES = 0
REVIEW_ACTIONS = 0
RUN14_CREATED = false
REAL_PROVIDER_CALLS = 0
SUBDIVISION_JUSTIFIED_BY_CURRENT_EVIDENCE = false
RETRY_CANDIDATE = true
RETRY_EXECUTED = false
FOCUSED_TESTS = 13 passed
RELATED_REGRESSION = 886 passed; 1 pre-existing baseline exception
NEXT_STAGE = MALFORMED_PROVIDER_JSON_SAME_RUN_RETRY_QUALIFICATION_R1
```

The machine-readable companion receipt contains the Draft PR field and privacy
scan result.  This stage stops here; it does not continue Run #13.
