# R2 wheel resource and installed smoke qualification

This packaging-only change declares both package-local SQL resources explicitly.
The release wheel must initialize a fresh native database and read the authorized
foundation migration without using a source checkout. Runtime Python, SQL bytes,
schema12 and R2 research semantics remain unchanged. This is Draft qualification,
not permission to activate a release or process a new real Source.

## Package resource authority

| Wheel member | Runtime reader | Frozen Git byte SHA256 |
| --- | --- | --- |
| `pro_a/schema.sql` | `Database.init_schema` | `7df9b6ed87d04fd0e79f7df9ae5367c2caf32d2acfb34f454161c648ee90ff9e` |
| `pro_a/migrations/foundation_0_2_3_relation_native.sql` | `foundation_schema_migration.SQL_PATH` | `17d0706380a4ba57c78081b9aeb37141115564b2f8210671194358d338b8e4f0` |

Setuptools package-data, rather than historical egg-info or a manual build copy,
includes these files. The migration retains its existing `-text` protection and
authorized hash. The build identity contract remains
`pro-a-build-repository-identity-v1`.

Resource closure covers package-local non-Python runtime inputs, not every
historical repository-dependent feature. Reference audit also identifies legacy
View contract documents, navigation packs and qualified overlay receipts outside
the package. Those features are not newly qualified as installed self-contained
by this change. Other package-relative reads inspect already packaged Python
code or generated build identity; configured data and private runtime artifacts
are not release resources.

## Installed smoke isolation

Build the final PR head from a clean detached canonical worktree using invocation
only `core.autocrlf=false` and `core.eol=lf`. Compare all 145 Python files and both
resources against exact committed Git blobs, wheel members and installed bytes.
Record resource member sizes and hashes separately from Python counts.

Create a fresh virtual environment outside the repository, install that exact
wheel and dependencies, and copy public tests into a separate external working
directory. Do not copy `src`, `pyproject.toml` or egg-info. Retain historical
source egg-info unchanged. Clear inherited Python paths and disable automatic
pytest plugin loading. Supply only the copied test-helper directory as needed.

Run `tests/installed_wheel_smoke.py` with the source root, expected final commit,
a private local report destination and pytest arguments. Its audit hook denies
checkout file access, its origin tripwire checks both package and distribution
metadata before and after pytest collection/execution, and its socket guard
forbids external network. A negative checkout-read probe proves the guard is
active. Use a separate `--no-git` invocation for installed provenance without Git.
Paths in the local origin report must not appear in public qualification receipts.

## Required gates

The exact prior 118 logical smoke nodes must all pass in the installed environment,
including the 23 previously failing nodes. The 996-node R2 acceptance scope must
also pass without omissions. Run the new resource tests in the installed
environment and the existing repository identity suite against canonical source.
Compile installed Python and run pip check in the fresh environment.

Fresh native bootstrap checks existing native schema version `0.2.2`, expected
tables, foreign keys and integrity. It is not Workbench schema12 bootstrap.
Foundation resource smoke uses the official frozen-statement/hash preflight;
it does not migrate real Production. SourceOperations construction uses only
disposable fixtures. No provider, retry, Run14 or real processing action is allowed.

## Release boundary

Before and after qualification, require stable and remote main to remain
`97e28e7b5209efde8f09e4e2a087fc826399d84a`, Run13 provider calls to remain four,
and Workbench, Production, Current View and private artifacts to remain unchanged.
Scan the PR and wheel for private content and credentials. Public reports use
environment role labels for origins. Do not delete files or alter runtime identity
implementation to make smoke pass.

Stable rollback is not part of this qualification: the resource omission already
exists in the prior stable wheel. New real Source processing remains blocked
until a separately authorized fixed release. On complete PASS, the next stage is
`R2_PACKAGE_RESOURCE_FIX_RELEASE_AND_CLEAN_RUN14_R1`.
