# Phase 2.4B Current View Activation

Two Human-approved official Current Views were activated: MLCC and 昀冢科技. The subject-aware model is validated, while knowledge sufficiency remains `PARTIAL` for both targets.

- MLCC direct evidence: `CLM_20260814_980FA010`, `CLM_20260814_BAED6789`, `CLM_20260814_D2C7FCD1` (3 subject Claims); its 8 context Claims remain excluded from direct evidence.
- 昀冢科技 direct evidence: `CLM_20260814_541F5C31`, `CLM_20260814_8E4B9E25`, `CLM_20260814_939CAEDD`, `CLM_20260814_9A069D06`, `CLM_20260814_BA7AC415`, `CLM_20260814_E1A48290` (6 Claims); `CLM_20260814_0B6E52F8` and `CLM_20260814_E53B8E9C` remain unresolved-only.
- Production SHA: `83A109D22EF08D5A230F28A341EF67CC0CA6FF5014BE7E89D7E2AB4DE8CAF895` → `581978E1C587B065A6EEF9C980013AF3DE1A9E8A8781857385404C9F61105250`.
- Backup SHA equals the pre-write SHA; integrity check is `ok` and foreign-key violations are 0.
- Proposals changed from 9 to 11: exactly 2 created and exactly 2 accepted. Current Views changed from 0 to 2.
- An idempotent rerun detected the exact accepted state and performed 0 writes.

Validation artifacts: [activation receipt](../artifacts/phase2_4b/current_view_activation_receipt.json) and [post-activation summary](../artifacts/phase2_4b/post_current_view_summary.json).
