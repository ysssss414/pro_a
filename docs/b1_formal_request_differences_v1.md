# Experimental B1 versus formal B1

This is a request contract comparison, not a new model-quality result. B1 is the
only candidate. The historical experimental requests and results stay immutable.

| Component | Generic formal v7 | Experimental B1 | New opt-in formal B1 | Treatment |
|---|---|---|---|---|
| System Prompt | Generic v7 semantic/encoding prompt | Frozen Evidence-first B1 | Exact frozen B1 bytes, SHA256 `61caec45852846bd428e05e635b456774ee8243d4326ae32987be3695193ffa8` | Preserve; resource bytes/version guarded |
| Research/output rules | Generic full-piece extraction | Evidence before Claim; zero Claim allowed; preserve conditions, forecasts, anonymous identities and conflicts | Same B1 rules | Preserve; semantic support still needs review |
| Schema/tool | Strict v7 ProviderRecord | Strict v7 ProviderRecord, `emit_source_analysis` | Same full schema, tool name, description, strict flag and forced tool choice | Preserve; no extra-field relaxation |
| Evidence | Intent v7, Binding v2 | Intent v7, Binding v2 | Same compiler/resolver; Assigned ownership plus visible dependency checks | Preserve existing truth source; explicit B1 scope check |
| Context | Full SourcePiece including original research prompt | Reviewed closure, explicit Assigned/Context regions | Hash-pinned closure, original exact Unit text and region order | Preserve source-specific closure; reject missing/foreign dependencies |
| User request | Generic v7 native wrapper | Source/Piece, Assigned, reference metadata, Node Catalog, source regions | Same B1 fields plus explicit formal execution/contract identities; `evaluation_only=false` | Governance packaging changes request; needs technical and future live validation |
| Node Catalog | Native scoped catalog | Frozen source-specific catalog | Actual Native scoped catalog; never silently replace it with the experimental catalog | Source-specific change requiring a new request/count and quality assessment |
| Source metadata | Provider proposal | Reference plus unresolved-variant review policy | Same reference policy; no automatic Human decision or Source overwrite | Existing explicit Source Metadata authority remains mandatory |
| Model/endpoint | DeepSeek strict tool endpoint | `deepseek-flash`, beta chat completions | Same requested alias/endpoint, explicit runtime/provider identity | Alias does not freeze provider weights; actual service revision needs fresh verification |
| Sampling | Non-thinking, temperature 0.1, stream false | Same | Same | Preserve actual wire parameters |
| Output cap | 24,000 | 12,000 | 12,000; independent B1 binding/series/budget identity | Preserve B1; generic v7 stays 24,000 |
| Input/cost | Existing generic budget contract | Qualified complete local V4.1 count, 13k continue/14k server cap | Same local counter/tool/tokenizer identities, complete request count, 26k total reservation | Recount every actual frozen request; no character estimate or old 84k/110k reuse |
| Persistence | Formal Run/Attempt/Accepted | Experimental ledger only | Actual Source Operations and existing bounded ledger; complete request and preflight persisted before dispatch | Required governance packaging; no invented historical acceptance |
| Native/Review attachment | Native v7 with non-authoritative research attachment | Offline compiler/quality evaluation | Same native compiler and attachment; real accepted Origin can use released review bridge | Location is not semantic truth; no admission permission |
| Runtime/Processing Context | Existing frozen runtime and context | Experimental identities | Explicit B1 policy, context/counter manifests, source input, request and Attempt digests | Required governance packaging; drift fails closed |
| Completion | Existing Operator v7 stops after extraction | Experiment stops after one response | New explicit B1 entry also stops after extraction; review bridge is a separate action | Original v7 stop and v4 default are unchanged |
| Coverage | Frozen generic series | Selected experimental scope | Assigned scope can complete; full Source coverage remains NOT_ESTABLISHED | No incomplete Source is reported COMPLETE |

Local synthetic transport/counter fixtures validate identity and safety only.
They do not establish new model recall, entailment, attribution or cost-quality
improvement. Actual server usage remains authoritative. Publication, permission,
scope, model/account, current tariff, metadata, review policy and separate
Semantic/P0 budgets remain prerequisites for a real Pilot.
