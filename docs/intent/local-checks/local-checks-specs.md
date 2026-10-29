# Local checks specs

Design: [local-checks-design.md](local-checks-design.md). "The copier-python fragment" is the template-owned `.config/copier-python/mise.toml`, which mise loads through `.config/mise/conf.d/copier-python.toml`. Each task named here is a mise task defined in that fragment.

## Tools and environment

- [x] **CHECKS-TOOL-001**: The copier-python fragment shall pin `uv`, `ruff`, `ty`, `prek` and `apm` to exact versions (a full version number, not `latest` or a prefix).
- [x] **CHECKS-TOOL-002**: The copier-python fragment shall pin `lidc` to an exact version from the `github:EtaCassiopeia/lid-tooling` backend, with an `asset_pattern` that matches the Linux x86_64 `lidc` binary and no other asset of that release.
- [x] **CHECKS-TOOL-003**: The copier-python fragment shall set mise's `min_version` to a version no newer than the mise version pinned in `.github/workflows/check.yml` of jmbowman/agentic_development at the tag in `agentic_development_ref`, as read by a network-marked test.
- [x] **CHECKS-TOOL-004**: In a rendered consumer, `mise env` shall set `TY_CONFIG_FILE` to the absolute path of that consumer's `.config/copier-python/ty.toml`.

## Tasks

- [x] **CHECKS-TASK-001**: The copier-python fragment's `setup` task shall have, as its `run` list in this order, `mise install apm`, `mise run skills`, `mise install` and `prek install -c .config/copier-python/prek.toml`, and no `depends`.
- [x] **CHECKS-TASK-016**: The copier-python fragment's `skills` task shall remove `.config/copier-python/.claude/` and then run `apm install --frozen` in `.config/copier-python/`.
- [x] **CHECKS-TASK-017**: When the template's lock file no longer lists a skill that an earlier `skills` run installed, the copier-python fragment's `skills` task shall leave `.config/copier-python/.claude/skills/` holding exactly one directory for each name `<name>` for which some entry of the lock file lists `.claude/skills/<name>` in its `deployed_files`, and nothing else, as checked by a network-marked test.
- [x] **CHECKS-TASK-018**: The copier-python fragment's `skill-links` task shall depend on `skills`.
- [x] **CHECKS-TASK-019**: The copier-python fragment's `lid-version` task shall run `uv run --no-project .config/copier-python/lid_version.py`.
- [x] **CHECKS-TASK-002**: The copier-python fragment's `sync` task shall run `uv sync --locked --all-extras --all-groups`.
- [x] **CHECKS-TASK-003**: The copier-python fragment's `lint` task shall run both `ruff check` and `ruff format --check`, even when the first fails, and fail if either fails.
- [x] **CHECKS-TASK-004**: The copier-python fragment's `typecheck` task shall depend on `sync` and run `ty check`.
- [x] **CHECKS-TASK-005**: The copier-python fragment's `test` task shall depend on `sync` and run `uv run --locked pytest`.
- [x] **CHECKS-TASK-006**: The copier-python fragment's `lid` task shall run `lidc check --only reverse-orphan,coverage,spec-id-format --fail-on warning`.
- [x] **CHECKS-TASK-007**: The copier-python fragment's `conflicts` task shall search every git-tracked file in the repository, whatever the current directory (`git grep` with pathspec `:/`), for lines beginning `<<<<<<< ` or `>>>>>>> `, succeed when the search finds nothing (exit 1), and fail when it finds a match (exit 0) or errors (exit 2 or more).
- [x] **CHECKS-TASK-008**: The copier-python fragment's `check-extra` and `hooks-extra` tasks shall do nothing and succeed.
- [x] **CHECKS-TASK-009**: The copier-python fragment's `check` task shall depend on `lint`, `typecheck`, `test`, `lid`, `conflicts`, `skill-links`, `lid-version` and `check-extra`, and run nothing itself.
- [x] **CHECKS-TASK-010**: The copier-python fragment's `fix` task shall run `ruff check --fix` and then `ruff format`.
- [x] **CHECKS-TASK-011**: The copier-python fragment's `hooks` task shall run `prek run -c .config/copier-python/prek.toml --all-files`.
- [x] **CHECKS-TASK-012**: The copier-python fragment's `exceptions` task shall run `uv run --no-project .config/copier-python/exceptions.py`, which reports named exceptions as specified in `STRICT-EXC-*` and always exits 0.
- [x] **CHECKS-TASK-015**: If any entry directly in `.claude/skills/` or `.agents/skills/` under the directory mise runs the task in (the project root), hidden entries included and through a link if the directory itself is one, is a symlink that doesn't resolve (a link loop included), then the copier-python fragment's `skill-links` task shall fail and print each such entry's path, relative to the project root, to stderr; otherwise, including when neither directory exists and when a link resolves to a file, it shall succeed.
- [x] **CHECKS-TASK-013**: When a consumer defines `check-extra` in its `.config/mise/config.toml`, `mise run check` shall run the consumer's definition instead of the copier-python fragment's.
- [x] **CHECKS-TASK-014**: When a consumer defines `hooks-extra` in its `.config/mise/config.toml`, the commit-time hooks shall run the consumer's definition instead of the copier-python fragment's.

## LID version gate

"The gate" is the template-owned `.config/copier-python/lid_version.py`, run from the repository root. "The instruction file" is `AGENTS.md` if it exists there, otherwise `CLAUDE.md`. "The `## LID` block" runs from a line that is exactly `## LID` to the next line starting with `# ` or `## `. "The LID entry" is the item of the lock file's top-level `dependencies` list whose `repo_url` is exactly `jszmajda/lid` and whose `virtual_path` is exactly `plugins/linked-intent-dev`. Lines inside fenced code blocks are read like any other line. "A value" is the text after the key's colon, with surrounding whitespace trimmed and one pair of matching surrounding quotes (`'` or `"`) removed.

- [x] **CHECKS-GATE-001**: When the `- Version:` value in the instruction file's `## LID` block equals the LID entry's `version` value, the gate shall exit 0.
- [x] **CHECKS-GATE-002**: If the `- Version:` value in the instruction file's `## LID` block differs from the LID entry's `version` value, then the gate shall exit 1 and print to stderr one line naming both versions and `/update-lid`.
- [x] **CHECKS-GATE-003**: When `AGENTS.md` exists at the repository root, the gate shall read the `## LID` block from `AGENTS.md` only, even when `CLAUDE.md` also exists.
- [x] **CHECKS-GATE-004**: The gate shall treat a heading that only begins with `## LID`, such as `## LID Tooling`, as outside the `## LID` block.
- [x] **CHECKS-GATE-005**: If the lock file holds no LID entry or more than one, then the gate shall exit 1 and print to stderr one line naming the problem.
- [x] **CHECKS-GATE-006**: If there's no instruction file, then the gate shall exit 1 and print to stderr one line naming the problem.
- [x] **CHECKS-GATE-007**: If the instruction file has no `## LID` block or more than one, then the gate shall exit 1 and print to stderr one line naming the problem.
- [x] **CHECKS-GATE-008**: If the instruction file's `## LID` block has no `- Version:` bullet or more than one, then the gate shall exit 1 and print to stderr one line naming the problem.
- [x] **CHECKS-GATE-009**: The gate shall find the LID entry whatever the order of its fields, skipping nested lists such as `deployed_files`.
- [x] **CHECKS-GATE-012**: If the lock file doesn't exist or can't be read, then the gate shall exit 1 and print to stderr one line naming the file.
- [x] **CHECKS-GATE-010**: The gate shall read the lock file from `.config/copier-python/apm.lock.yaml` and the instruction file as defined above, unless the `--lock` or `--instructions` option names another path; every path is relative to the working directory.
- [x] **CHECKS-GATE-013**: If the `--instructions` option names a file that doesn't exist, then the gate shall fail as when there's no instruction file, without reading any other file.
- [x] **CHECKS-GATE-011**: The gate shall import only modules from Python's standard library.

## Commit-time hooks

- [x] **CHECKS-HOOK-001**: The copier-python template's `.config/copier-python/prek.toml` shall define only five hooks, one local hook each for the `lint`, `typecheck`, `lid`, `conflicts` and `hooks-extra` tasks, each with `language = "system"`, `entry = "mise run <task>"` and `pass_filenames = false`.
- [x] **CHECKS-HOOK-002**: If neither `mise` nor its shims directory is on `PATH` when the copier-python git hook runs, then `git commit` shall exit non-zero and `HEAD` shall not change.
- [x] **CHECKS-HOOK-003**: In the rendered sample project of FILES-RENDER-001, with tools installed and the environment synced, running all copier-python commit-time hooks a second time shall finish within 10 seconds on the CI runner.
