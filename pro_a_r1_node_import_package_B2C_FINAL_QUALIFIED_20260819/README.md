# pro_a R1 B.2C — final-qualified Production-bound package revision

Status: `FINAL_ISOLATED_QUALIFICATION_PACKAGE`; Production import is **not authorized or executed** by this package generation/qualification round.

## Canonical Production identity

The target precondition is the project-configured database `workspace/pro_a.db`:

- absolute path: `D:\ej\材料\codex\get_knowledge\pro_a_v0_1\workspace\pro_a.db`
- SHA-256: `d4611908d276200833fbac2adca8918cf3d3f58662080e492d87e593765c046b`
- schema version: `0.2.1`
- schema SHA-256: `31f9b03ab06f62336104424cccb82962b8096aec66b1f23942397c6f4a637718`

The prior package `pro_a_r1_node_import_package_B2C_APPROVED_20260819` is fail-closed for Production: it is bound to the run_006 isolated runtime DB SHA `a5b05b29...6b480`. Do not execute that old package against Production. The old package and attempt_002 are retained unchanged.

## Authorized payload for qualification

- CREATE 24 Nodes from `approved_nodes.csv`.
- Add only `微透镜阵列 → Micro Lens Array` and `光模块PCB → Optical Module PCB`.
- Write zero `part_of` and zero other structural relations.
- Five rows are recorded only as `APPROVED_STRUCTURAL_PATCH_CANDIDATE`.
- Seven rows remain `DEFER_PARENT_REVIEW`.

No structural review status is executable. `apply_b2c_approved.py` applies only rows whose `approval_status` is `APPROVED_FOR_IMPORT`; this revision contains none.

## Target resolution contract

The PowerShell wrapper requires exactly one `-DatabasePath`, resolves it to one absolute file, verifies the package inventory, manifest self-hash, target SHA and target-bound authorization token, then passes that same absolute path once to Python. The tools do not resolve a target from `config.toml`, environment variables or the current working directory.

## Fresh isolated qualification command

Run from repository root only after the fresh-copy receipt exists:

```powershell
$package = (Resolve-Path '.\pro_a_r1_node_import_package_B2C_FINAL_QUALIFIED_20260819').ProviderPath
$isolated = (Resolve-Path '.\workspace\r1_acceptance\b2c_final_qualified_20260819_isolated_fresh\pro_a_b2c_final_qualification.db').ProviderPath
$python = (Get-Command python).Source
$manifestSha = (Get-FileHash -LiteralPath (Join-Path $package 'manifest.json') -Algorithm SHA256).Hash.ToLowerInvariant()
$dbSha = (Get-FileHash -LiteralPath $isolated -Algorithm SHA256).Hash.ToLowerInvariant()
$token = "AUTHORIZE_ISOLATED_DRY_RUN:$manifestSha`:$dbSha"
& (Join-Path $package 'apply_b2c_approved.ps1') -DatabasePath $isolated -TargetIdentity Isolated -AuthorizationToken $token -ReportPath (Join-Path $package 'qualification_report.json') -PythonPath $python
```

Expected exact semantic delta: Nodes `+24`; aliases `+2`; Node Relations/current `part_of`/formal relations/Current Views/Proposals/source/claim/link tables and every other table `+0`.

## Stop gate

Do not point `-DatabasePath` at Production in this round. Do not derive a Production token from the isolated token. Do not start run_007. A later Production import requires a separate human authorization naming this final manifest SHA and the exact still-current Production SHA. `READY_FOR_PRODUCTION_IMPORT_AUTHORIZATION = true` means ready to request that authorization; it is not an import authorization.
