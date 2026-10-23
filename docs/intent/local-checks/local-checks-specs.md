# Local checks specs

Design: [local-checks-design.md](local-checks-design.md). "The copier-python fragment" is the template-owned `.config/copier-python/mise.toml`, which mise loads through `.config/mise/conf.d/copier-python.toml`. Each task named here is a mise task defined in that fragment.

## Tools and environment

- [x] **CHECKS-TOOL-001**: The copier-python fragment shall pin `uv`, `ruff`, `ty` and `prek` to exact versions (a full version number, not `latest` or a prefix).
- [x] **CHECKS-TOOL-002**: The copier-python fragment shall pin `lidc` to an exact version from the `github:EtaCassiopeia/lid-tooling` backend, with an `asset_pattern` that matches the Linux x86_64 `lidc` binary and no other asset of that release.
- [x] **CHECKS-TOOL-003**: The copier-python fragment shall set mise's `min_version` to a version no newer than the mise version pinned in `.github/workflows/check.yml` of jmbowman/agentic_development at the tag in `agentic_development_ref`, as read by a network-marked test.
- [x] **CHECKS-TOOL-004**: In a rendered consumer, `mise env` shall set `TY_CONFIG_FILE` to the absolute path of that consumer's `.config/copier-python/ty.toml`.

## Tasks

- [x] **CHECKS-TASK-001**: The copier-python fragment's `setup` task shall run `mise install` and then `prek install -c .config/copier-python/prek.toml`.
- [x] **CHECKS-TASK-002**: The copier-python fragment's `sync` task shall run `uv sync --locked --all-extras --all-groups`.
- [x] **CHECKS-TASK-003**: The copier-python fragment's `lint` task shall run both `ruff check` and `ruff format --check`, even when the first fails, and fail if either fails.
- [x] **CHECKS-TASK-004**: The copier-python fragment's `typecheck` task shall depend on `sync` and run `ty check`.
- [x] **CHECKS-TASK-005**: The copier-python fragment's `test` task shall depend on `sync` and run `uv run --locked pytest`.
- [x] **CHECKS-TASK-006**: The copier-python fragment's `lid` task shall run `lidc check --only reverse-orphan,coverage,spec-id-format --fail-on warning`.
- [x] **CHECKS-TASK-007**: The copier-python fragment's `conflicts` task shall search every git-tracked file in the repository, whatever the current directory (`git grep` with pathspec `:/`), for lines beginning `<<<<<<< ` or `>>>>>>> `, succeed when the search finds nothing (exit 1), and fail when it finds a match (exit 0) or errors (exit 2 or more).
- [x] **CHECKS-TASK-008**: The copier-python fragment's `check-extra` and `hooks-extra` tasks shall do nothing and succeed.
- [x] **CHECKS-TASK-009**: The copier-python fragment's `check` task shall depend on `lint`, `typecheck`, `test`, `lid`, `conflicts`, `skill-links` and `check-extra`, and run nothing itself.
- [x] **CHECKS-TASK-010**: The copier-python fragment's `fix` task shall run `ruff check --fix` and then `ruff format`.
- [x] **CHECKS-TASK-011**: The copier-python fragment's `hooks` task shall run `prek run -c .config/copier-python/prek.toml --all-files`.
- [x] **CHECKS-TASK-012**: The copier-python fragment's `exceptions` task shall run `uv run --no-project .config/copier-python/exceptions.py`, which reports named exceptions as specified in `STRICT-EXC-*` and always exits 0.
- [x] **CHECKS-TASK-015**: If any entry directly in the repository root's `.claude/skills/` or `.agents/skills/`, hidden entries included, is a symlink whose target doesn't exist, then the copier-python fragment's `skill-links` task shall fail and print each such entry's path; otherwise, including when neither directory exists, it shall succeed.
- [x] **CHECKS-TASK-013**: When a consumer defines `check-extra` in its `.config/mise/config.toml`, `mise run check` shall run the consumer's definition instead of the copier-python fragment's.
- [x] **CHECKS-TASK-014**: When a consumer defines `hooks-extra` in its `.config/mise/config.toml`, the commit-time hooks shall run the consumer's definition instead of the copier-python fragment's.

## Commit-time hooks

- [x] **CHECKS-HOOK-001**: The copier-python template's `.config/copier-python/prek.toml` shall define only five hooks, one local hook each for the `lint`, `typecheck`, `lid`, `conflicts` and `hooks-extra` tasks, each with `language = "system"`, `entry = "mise run <task>"` and `pass_filenames = false`.
- [x] **CHECKS-HOOK-002**: If neither `mise` nor its shims directory is on `PATH` when the copier-python git hook runs, then `git commit` shall exit non-zero and `HEAD` shall not change.
- [x] **CHECKS-HOOK-003**: In the rendered sample project of FILES-RENDER-001, with tools installed and the environment synced, running all copier-python commit-time hooks a second time shall finish within 10 seconds on the CI runner.
