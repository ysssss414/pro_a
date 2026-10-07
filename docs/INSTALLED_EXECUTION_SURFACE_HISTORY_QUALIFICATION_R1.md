# Installed execution surface history qualification

Cross-release qualification uses two distinct authorities: historical Python
bytes from the immutable Git commit recorded by the Run, and target bytes from
the executing package. An installed package must not infer a history repository
from its site-packages ancestors or the operator's current working directory.

The Python-only qualification operators accept `historical_repository_root`.
The root must be an explicit, local, non-linked Git worktree root containing the
full historical commit. Git environment overrides and replacement objects are
disabled. History is read as commit-bound blobs with Git object hash checks;
dirty working files and a changed HEAD do not select historical bytes. Nothing
from the history checkout is imported as target runtime code.

```python
assess_truncation_recovery_compatibility(
    config, run_id, truncated_attempt_id,
    persist=False,
    historical_repository_root=verified_history_repository,
)
```

The same history argument is available on the Stage 7.2C and bounded-retry
assessment functions. It is not available on HTTP requests, frontend controls,
MCP public tools, or execution/recovery actions. This is an evidence source,
not a runtime override, qualification token, or compatibility waiver.

Explicit assessments read fresh evidence rather than reuse cached success.
Unavailable Git, an unavailable commit/repository, mismatched root, corrupt
blob, missing protected selector, or a changed semantic surface fails closed.
Explicit history failure blocks qualification even when runtime identities
otherwise match. Source-checkout callers retain the existing default of their
own verified repository. Installed identity and ordinary extraction still do
not need Git; cross-release history assessment needs its explicit Git evidence
source and executable. No archive format or network fallback is added.

AST selectors, normalization rules, dependency closure, compatibility contract,
research semantics, provider contract, Evidence Binding, Wire, ledger/recovery
policy, and schema12 are unchanged. A history source supplies bytes only; it
cannot make a changed research or provider surface equivalent.

This is a Draft-only qualification change. Qualification must cover the actual
installed candidate wheel with checkout imports denied, fixed historical bytes,
negative evidence/semantic cases, and a read-only assessment of a private Run14
copy. Run14's historical truncation remains failed; no partial response is
reparsed, no qualification event is appended to the real Workbench, and no real
recovery, provider call, retry, subdivision, aggregate, or Semantic action occurs.
Passing this candidate does not change the already-published stable runtime or
convert its earlier compatibility STOP into PASS. Merge, activation, a fresh
released-runtime assessment, durable qualification and live recovery require a
separate authorized stage.
