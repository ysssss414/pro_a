# Explicit candidate selection v1 (draft)

Existing `source-candidate-set-v1` can reconstruct v4 Provider responses with exact observation and Evidence lineage. Its default projection includes every eligible object and requires matching source metadata across inputs. A small independently reviewed subset needs a separate, explicit selection identity; changing a Provider version label is not a valid adaptation.

This draft adds the optional `source-candidate-selection-v1` manifest to the existing candidate-input path. It binds 5–10 original Claim observation IDs and revision hashes, input document identities, accepted Result hashes, the original frozen Context hash, and an existing source-metadata resolution. Selection is limited to already eligible Claims with complete Evidence and existing Canonical Node dependencies. Candidate Node creation and unresolved dependencies are not supported. Node match observations are restricted to the selected Claims' own input documents and required node IDs.

The Workbench boundary reconstructs every original document and verifies persisted accepted Results and frozen Context before use. The manifest remains inside the hashed native candidate input through extraction projection, Review Packet validation, and subsequent reads. Neither selection nor metadata resolution grants Reality Support, Coverage completion, Human review approval, or Canonical execution permission. Unsupported/uncertain semantic judgments still pass through the unchanged P0/P1/P2 validators. Source metadata values additionally satisfy the actual v4 schema; model consensus is not metadata authority.

The original blocked Run and paid extraction records remain untouched. B-lite starts a derived candidate Run and reuses the paid extraction; its separate semantic decomposition stage still requires a qualified model backend. Zero extraction calls does not mean zero semantic/model calls or zero Workbench state creation in a future live pilot.

## Deliberate limits before production

- This is a draft Python service path, with no new Web/MCP endpoint or automated Human identity.
- Obtain and authenticate a real metadata decision through the existing controlled operator process. Test-only resolutions are not reusable authority.
- Assess release qualification and the operator-facing selection/partial-coverage presentation before enabling a live pilot. The original Coverage remains incomplete; a completed selected Packet must not be described as full Source success.
- Recheck the current Canonical baseline, exact node identities, duplicates, input records and current Runtime. Produce fresh review Context; never reuse isolated Artifact IDs, mock Advice, approvals, envelopes or receipts.
- Only after genuine model review and actual P1/P2 confirmation may the separately isolated production Operator execute. The existing Windows integrity boundary is unchanged.
- This draft does not support v7 inputs, candidate replacement workflows, arbitrary protocol conversion, bulk recovery or whole-Run resume.

## Validation

`tests/test_selective_candidate_admission.py` uses synthetic public-safe fixtures to exercise origin preservation, subset size, identity drift, unapproved/invalid metadata, unresolved dependencies, duplicate exclusion, rejection of v7 relabelling and exclusion of unrelated node observations. Existing candidate-origin and governance tests remain applicable. A separate private disposable integration harness can replay real accepted inputs with explicitly synthetic semantic, model and Human decisions; it is not evidence of real model quality or authenticated production approval.
