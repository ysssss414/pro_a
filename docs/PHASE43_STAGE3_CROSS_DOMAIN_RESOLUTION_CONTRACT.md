# Phase 4.3 Stage 3 — AI Hardware × Semiconductor Cross-Domain Resolution

## Authority and baseline

This document records the HUMAN_USER Stage 3 execution instruction of 2026-09-22. The canonical development and local-data workspace is `<CANONICAL_PRO_A_WORKSPACE>`, which must be a normal root clone (`git-dir` and `git-common-dir` both `.git`). The separate `pro_a_codex` clone is retained as a clean/recovery clone and is not a Stage 3 implementation target. Historical linked worktrees may remain.

The frozen Git entry baseline is `origin/main = main = 690fc4f26e02607fb54a48053cf8faf6775621c3`. Stage 3 uses branch `codex/phase43-stage3-cross-domain-resolution` from that exact commit. Stage 2's qualified structured Foundation package, human qualification decisions, and public receipts remain frozen inputs. The Stage 2 qualification covered 105 of 274 candidate objects; 169 were not given HUMAN_USER attribution. Its native qualification did not complete operational review or authorize Production handoff. Stage 2's canonical input and runtime assets may remain private, ignored, or untracked.

The qualified Stage 2 package is `semiconductor_foundation_backfill_web_pro_v1`, bound by package SHA-256 `131421d3bbe3b968a1c72ee6e3767cfad6141a0cdaea1850ba30cccbd3932918`. The AI Hardware canonical baseline is the existing `workspace/pro_a.db` catalog, not a new industry namespace. Input paths must be established from Stage 2 receipts, runtime configuration, the structured Foundation importer, and existing local references, rather than guessed. Private/local structured inputs and the Production database must never be added to Git.

## Objective and identity decisions

Resolve AI Hardware and Semiconductor candidates against one shared canonical Source / Node / Claim / Relation identity model. Use Git-tracked code and contracts with read-only local Production/canonical data and read-only qualified Stage 2 private structured inputs. Isolate generated Stage 3 candidate qualification and reconciliation artifacts in a Stage 3 artifact store.

Use the existing entity-resolution vocabulary: `REUSE`, `CREATE`, `REVIEW`, `DEFER`, `REJECT`. An identity match may reuse an existing canonical Node across domains. New domain membership does not create a second Node or a new Claim. Exact canonical/registered-alias matching and existing shared identity rules govern proposals. Similar names, translation, trademarks, granularity changes, different Node types, ambiguous abbreviations, and brand/subsidiary/listed-entity distinctions require review rather than silent merging. An alias cannot be attached to an owner solely from a domain dictionary. Candidate `CREATE` and `REUSE` are proposals and remain subject to human governance.

## Relation reconciliation and evidence

Reconcile proposed relations against existing canonical edges by endpoint identity, direction, relation type, scope, temporal meaning, and evidence. Preserve categorical, temporal, current canonical, and research-hypothesis distinctions. Do not turn co-occurrence, industry labels, chronology, proposed capability, or an unsupported functional/categorical mapping into a factual edge. When the ontology cannot express a proposition faithfully, retain a Claim/Gap or review candidate; do not silently extend the ontology or force a different relation type. Parent/causal ambiguity, cycles, possible duplicates, and endpoint ambiguity remain review issues.

Preserve each candidate's original structured content, Source/hash/locator/excerpt binding, native relation evidence, review history, and provenance. Do not reingest raw PDFs, call providers, or ingest new Sources. Existing evidence cannot be rewritten to make a candidate eligible. The Stage 2 frozen receipts and HUMAN_USER decisions remain unchanged.

## Human-review and operating boundaries

Automated qualification does not confer HUMAN_USER approval, canonical activation, or Production authority. Preserve the 105 Stage 2 qualification decisions exactly and leave the other 169 without HUMAN_USER attribution. Keep `DEFER` and `REJECT` as completed qualification decisions with their audit records; do not interpret them as absence of an object. Ambiguous identity, alias ownership, relation, evidence, and low-confidence cases route to bounded human review. Stage 2 Workbench WIP is 274 / `HARD_STOP`; Stage 3 must not bypass the existing new-intake guard or represent candidate reconciliation as completed operational review.

Results must be deterministic and idempotent for the same frozen package, canonical snapshot, code, and decisions. A replay must not add duplicate candidates or mutate prior artifacts. Drift in bound inputs or context fails closed.

## Production and Git boundary

Production path: `workspace/pro_a.db`. Required SHA-256 before and after: `6e5a303ccee9c192c350c2550cc232649e56ffee939b7a09cd6b170cc1c8fba1`. Production is read-only; `WRITE_COUNT = 0` and `APPLY_EXECUTED = false`. Stage 3 may not call the Production apply path or mutate canonical tables. Qualification outputs belong only in isolated Stage 3 storage.

Codex performs Git fetch, branch, add, commit, push, and Draft PR operations itself when they are in the authorized Stage 3 workflow, requesting environment approval for `.git` writes when needed. It must not use hard reset, force checkout, `git clean -fd`, discard local files, or delete the recovery clone. Preserve expected ignored/private data and historical qualification artifacts. Public Git changes must exclude private Source content and local runtime data. No merge, Production apply, or release action follows from a Draft PR.

## 29. ACCEPTANCE GATES

### Gate A — Baseline

```text
Stage 2 frozen baseline exact
Stage 2 qualification unchanged
Production unchanged
```

### Gate B — Input Integrity

```text
AI Hardware source identified
Semiconductor source identified
comparison population frozen
input hashes bound
```

### Gate C — Identity Candidate Retrieval

```text
deterministic
no silent merge
candidate reasons inspectable
```

### Gate D — Canonical Resolution

Every candidate has exactly one outcome:

```text
REUSE_CANONICAL
CREATE_NEW_CANONICAL
KEEP_DOMAIN_SPECIFIC
DEFER
REJECT
```

### Gate E — Cross-Domain Evidence

```text
source provenance retained
claim provenance retained
temporal semantics retained
cross-source leakage = 0
```

### Gate F — Relation Reconciliation

Every comparable relation has exactly one outcome and compatible endpoints.

### Gate G — Collision Safety

```text
no silent alias reassignment
no silent type overwrite
no quarantine bypass
```

### Gate H — Determinism

Two-workspace structural match.

### Gate I — Idempotency

Replay adds no duplicates.

### Gate J — Review Governance

All mandatory-risk cases enter frozen Stage 3 review population.

### Gate K — Regression

Existing Stage 0 / Stage 1 / Stage 2 / Gold behavior remains intact.

### Gate L — Production

```text
zero writes
zero apply
zero Official View activation
```

All Gates A–L must PASS for automated Stage 3 qualification to PASS.

## 30. TESTING

Add focused tests for at least:

```text
exact canonical reuse
alias-driven candidate resolution
generic vs vendor-specific non-merge
parent vs child non-merge
type mismatch DEFER
historical quarantine preservation
multi-domain assignment
Claim provenance preservation
cross-source leakage prevention
relation duplicate reuse
compatible different relations coexist
relation endpoint ambiguity
ontology pressure DEFER
deterministic two-workspace replay
idempotent replay
Production immutability
```

Run existing regression suites appropriate to changed runtime scope.

At minimum preserve:

```text
Stage 0 regression
Stage 1 Frozen Gold 120/120
Stage 2 regression
full backend pytest where feasible
frontend tests/build if touched or required by existing gate
compileall
```

Do not weaken existing assertions merely to make Stage 3 pass.

## 31. AI DOUBLE REVIEW — DO NOT PERFORM YET UNLESS ALREADY PART OF THE FROZEN PLAN

This first Stage 3 task ends after:

```text
automated cross-domain resolution
frozen review population
automated qualification
portable review handoff
```

Do not automatically perform HUMAN_USER decisions.

If the existing Phase 4.3 plan explicitly defines AI Review A/B as part of the same Stage 3 implementation task, you may prepare the machinery, but stop before pretending a HUMAN_USER decision exists.

Preferred state:

```text
AUTOMATED_STAGE3 = PASS
FINAL_HUMAN_QUALIFICATION = PENDING
```

if human-required cases exist.

## 32. GIT

Codex must perform its own Git workflow.

Require:

```text
git add
git commit
git push
```

Canonical development/data workspace for the resumed task is:

```text
<CANONICAL_PRO_A_WORKSPACE>
```

Git operations that require `.git` metadata/network access may request environment approval and must then be executed by Codex itself.

No HUMAN_USER PowerShell handoff.

Open a Draft PR:

```text
head =
codex/phase43-stage3-cross-domain-resolution

base =
main
```

Suggested PR title:

```text
Phase 4.3 Stage 3 — Cross-Domain Canonical Resolution
```

Do not merge.

## 33. STOP CONDITIONS

Immediately STOP on:

```text
baseline drift
ambiguous authoritative AI Hardware input
Stage 2 artifact mutation
Production mutation
canonical registry fork
cross-source evidence leakage
non-deterministic resolution
Git write failure after required environment approval
unexpected new provider/source ingestion
unresolved test regression
```

Do not work around these by weakening gates.

Ordinary sandbox denial of `.git` writes is not itself a Stage 3 blocker if environment approval is available.

## 34. FINAL OUTPUT

Return:

```text
PHASE43_STAGE3_CROSS_DOMAIN_RESOLUTION = PASS / BLOCKED / FAIL

BASELINE
EXPECTED =
LOCAL =
REMOTE =
MATCH =

INPUTS
AI_HARDWARE_INPUT =
AI_HARDWARE_INPUT_SHA =
SEMICONDUCTOR_INPUT =
SEMICONDUCTOR_INPUT_SHA =

POPULATION
AI_HARDWARE_NODES =
SEMICONDUCTOR_NODES =
COMPARISON_CANDIDATES =
POPULATION_SHA256 =

IDENTITY_RESOLUTION
REUSE_CANONICAL =
CREATE_NEW_CANONICAL =
KEEP_DOMAIN_SPECIFIC =
DEFER =
REJECT =
CROSS_DOMAIN_COLLISIONS =
UNRESOLVED_IDENTITY_CONFLICTS =
ONTOLOGY_PRESSURE_CASES =

RELATION_RESOLUTION
RELATIONS_COMPARED =
REUSE_RELATION =
CREATE_RELATION =
KEEP_DOMAIN_SPECIFIC_RELATION =
DEFER_RELATION =
REJECT_RELATION =

EVIDENCE
CROSS_SOURCE_LEAKAGE =
PROVENANCE_PRESERVED =
TEMPORAL_SEMANTICS_PRESERVED =

DETERMINISM
WORKSPACE_A_SHA =
WORKSPACE_B_SHA =
STRUCTURAL_MATCH =
IDEMPOTENT_REPLAY =

REVIEW
HUMAN_REQUIRED =
MANDATORY_EXCEPTIONS =
RESIDUAL_ELIGIBLE =
FINAL_HUMAN_QUALIFICATION = PENDING / NOT_REQUIRED

REGRESSION
STAGE0 =
STAGE1_GOLD =
STAGE2 =
BACKEND =
FRONTEND =
FRONTEND_BUILD =
COMPILEALL =

PRODUCTION
SHA_BEFORE =
SHA_AFTER =
WRITE_COUNT =
APPLY_EXECUTED =
OFFICIAL_VIEW_ACTIVATIONS =

GIT
WORKSPACE =
BRANCH =
COMMIT_SHA =
PUSHED =
DRAFT_PR_NUMBER =
DRAFT_PR_OPEN =
MERGED = false

STAGE4_STARTED = false

NEXT_ACTION =
If automated Stage 3 PASS and HUMAN_REQUIRED > 0, perform Stage 3 AI double review and bounded HUMAN_USER qualification; otherwise proceed to Stage 3 pre-merge audit.
```

Do not start Stage 4.

## CONTRACT AUTHORITY CLARIFICATION

此前不存在更早的本地 Stage 3 Cross-Domain Resolution contract 文件。

本轮 HUMAN_USER 提供的完整 Stage 3 task specification—including此前已收到的前半段以及本消息补充的 Sections 29–34—共同构成：

```text
PHASE43_STAGE3_AUTHORITATIVE_EXECUTION_CONTRACT
```

请在实际 resolution 前完整冻结为：

```text
docs/PHASE43_STAGE3_CROSS_DOMAIN_RESOLUTION_CONTRACT.md
```

冻结后继续执行 Stage 3，不要再次因历史上不存在该文档而 BLOCK。
