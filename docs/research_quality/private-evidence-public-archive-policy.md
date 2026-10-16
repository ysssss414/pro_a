# Private evidence / public engineering archive policy

**Applicability:** project research processing, source extraction, model-quality pilots, governed review/admission qualification and supporting engineering work. The GitHub repository is **public**. Public version control is for sanitized engineering knowledge and source code, **not** the private research corpus.

## Two records for one experiment

Every substantive task should produce:

1. **Private evidence packet (local):** complete frozen source, request/response, Raw, Evidence bindings, adjudication matrix, Gold reference when used, actual Provider usage, ledgers, exact source/Run IDs, restricted original authorizations and immutable receipts. Use local directory permissions and an inventory with full SHA-256 checksums. Follow rights and retention constraints.
2. **Public engineering summary (GitHub):** redacted experiment objective, version/contract family, fixed scoring denominators, aggregate results, failure categories, independent-qualification limits, remaining blockers and next decision. Public release must not require reconstructing protected raw observations.

An archive checksum of a **private ZIP** may be published only after an explicit privacy review and when that digest's correlation risk is acceptable. Never substitute it for Source authenticity, and never publish the original Source file hash or identifying file metadata by default. This public summary must remain independently understandable without opening private material.

## Disallowed content in a public commit

Do not commit, paste into PR comments, or attach:

- Source PDFs or source excerpts, even inside a “sanitized” ZIP with forgotten embedded images, text pages or metadata.
- Full prompts/complete model requests, system/user messages containing protected source text, schemas filled with actual private entities, Raw model responses, full Evidence spans, page crops, Gold quotations or claim-by-claim audits.
- Source/Run/Artifact IDs, exact private Source hashes, local absolute paths, filenames revealing nonpublic research access, database dumps, snapshot copies, private account balances, credentials, keys or secrets.
- Directly identifiable proprietary meetings, participants, confidential company guidance, private model-account information, unpublished trade decisions or any user/person-specific research context.
- Any unreviewed auto-generated document that embeds source text in a stack trace, test fixture, screenshot, prompt preview, JSON body, CSV row or Markdown table.

A file being “only a test artifact,” “only a report,” or “only a SHA inventory” does not make it safe for a public Git repository.

## Acceptable public artifacts after checking

- Sanitized project status, research-quality metrics and failed-guard classifications.
- Versioned general extraction/review contracts that do not embed private samples.
- Synthetic fixtures with fabricated company/source content.
- Regression tests that do not serialize real provider input/output.
- Code changes in a Draft PR with separated scope and explicit backward-compatibility requirements.
- Aggregated real-experiment performance, with sample size, adjudication limits, original denominators and candid failure analysis.
- A carefully reviewed fingerprint of an internal private **evidence packet** if useful for local traceability; publishing one is optional.

All findings derived from a proprietary Source should be framed as **research-process diagnostics**, not as endorsement of the underlying real-world statements. No public raw Claim, named material or named supplier is needed to explain Evidence mismatches.

## Archival and review procedure

1. Finish the task locally and preserve the immutable, restricted evidence package and its hashes.
2. Draft a fresh redacted Markdown summary. Do **not** copy complete private receipts, original tables, model outputs or raw JSON to GitHub.
3. Run privacy checks against the proposed complete Git diff. Inspect both added and modified content, filenames and commit messages.
4. Search for credentials, local paths, Source/Run IDs, material titles, source-level hashes, excerpts, Gold answers, full prompts, model outputs and embedded images. No regex scanner replaces manual review.
5. Check technical accuracy: source vs. analyst vs. model statements, input scope, sample denominators, Provider calls, actual vs. estimated cost, unresolved failures and differences between offline and live quality.
6. Create/update a **documentation-only Draft PR** for experiment archives. Do not mix research archiving with code fixes or change runtime as part of a documentation task.
7. If code must change, create an appropriately scoped separate code PR with synthetic tests, backward-compatibility proof, privacy scanning and explicit release decision.
8. After GitHub upload, read back the changed filenames and file contents and confirm Draft/unmerged status. Preserve the private-to-public packet checksum mapping locally.
9. Consolidate closely related experiments into a single retrospective periodically; avoid one PR per minor Provider experiment.

## Non-negotiable operational boundaries

- Creating a branch or Draft PR is **not** authorization to merge, switch Stable, run a model, make a formal Review decision or write Canonical/Production.
- Human review and independent Operator exact-approval requirements remain in force.
- A passing byte-level Evidence locator is not sufficient for semantic truth or source-statement support.
- Failed/partial runs must not be represented as complete, and a safe salvage reader is not a general Run-recovery qualification.
- Unexecuted future Provider requests do not become authorized merely because their frozen envelopes or budgets are published.
- If rights-holder restrictions or sensitive data exposure are unclear, keep the relevant artifact local and publish only the high-level engineering lesson.

## Archive outcome labels

- **PUBLIC_ARCHIVE_DRAFT:** redacted evidence-backed summary on a Draft PR; no release.
- **PRIVATE_ONLY:** private source-related content not fit for public GitHub.
- **CODE_CHANGE_DRAFT:** code/test PR subject to separate compatibility and release gates.
- **RELEASED:** only after approved merge/activation evidence confirms it; never infer from a PASS test receipt.

The public narrative and the private evidence chain must retain separate identities. A later legitimate reviewer should be able to audit aggregate decisions with public context and, if authorized, verify exact private artifacts via the local evidence manifest.
