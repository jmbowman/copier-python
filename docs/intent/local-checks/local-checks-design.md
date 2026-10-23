---
parent: high-level-design
prefix: CHECKS
---

# Local checks

## Context and Design Philosophy

Every check is a mise task defined in the template's mise fragment. CI runs `mise run --continue-on-error check`, and commit-time hooks run the fast tasks, so local runs and CI use the same commands at the same tool versions. Commit-time hooks must finish within 10 seconds on a typical slice. Anything slower runs only in CI.

## Pinned tools

The fragment `.config/copier-python/mise.toml`, loaded through its link in `.config/mise/conf.d/`, sets mise's `min_version` (no newer than the mise version the shared check workflow pins) and `TY_CONFIG_FILE`, and pins exact versions of:
- `uv` (environments, and Python itself from `requires-python`);
- `ruff`;
- `ty`;
- `prek`;
- `lidc`, from the `github:EtaCassiopeia/lid-tooling` backend with an `asset_pattern` that selects the `lidc` binary.

Renovate keeps the pins current in the template repo. `mise run` installs a missing pinned tool automatically before running a task (verified with mise 2026.7.2).

## Tasks

| Task | Runs | At commit? |
|---|---|---|
| `setup` | `mise install`, then `prek install -c .config/copier-python/prek.toml` | — |
| `sync` | `uv sync --locked --all-extras --all-groups` | via dependents |
| `lint` | `ruff check` and `ruff format --check`, both run even if the first fails | yes |
| `typecheck` | `ty check`, after `sync` | yes |
| `test` | `uv run --locked pytest`, after `sync` | no (CI and on demand) |
| `lid` | `lidc check --only reverse-orphan,coverage,spec-id-format --fail-on warning` | yes |
| `conflicts` | `git grep` over every tracked file in the repo (pathspec `:/`, so it doesn't depend on the current directory) for lines starting `<<<<<<< ` or `>>>>>>> ` | yes |
| `skill-links` | Fails, naming each, on any entry directly in the repo's `.claude/skills/` or `.agents/skills/` that is a symlink whose target doesn't exist. Passes when neither directory exists | no (CI and on demand) |
| `check-extra` | nothing (template default) | — |
| `hooks-extra` | nothing (template default) | yes |
| `check` | depends on `lint`, `typecheck`, `test`, `lid`, `conflicts`, `skill-links` and `check-extra` | — |
| `fix` | `ruff check --fix` then `ruff format` | — |
| `hooks` | `prek run -c .config/copier-python/prek.toml --all-files`: every commit-time hook, on demand. prek finds no config by itself, because only the installed git hook records the path | — |
| `exceptions` | `uv run --no-project .config/copier-python/exceptions.py`: lists every named exception and the total ([strict profile](../strict-profile/strict-profile-design.md#named-exceptions)) | — |

**Shell.** mise runs each entry of a task's `run` list separately with `sh -o errexit`, so task commands are POSIX `sh`, and a task that must run several commands whatever their results uses one entry.

**Exit codes.**
- `conflicts` passes when `git grep` finds nothing (exit 1), and fails on a match (exit 0) or on an error (exit 2 or more, including running outside a git repository).
- `exceptions` always exits 0. It reports and doesn't gate.

**Dangling skill links.** copier's update never deletes a symlink, so when a template release removes or renames one of its skills ([baseline files](../baseline-files/baseline-files-design.md#skills)), the skill's files go but its links in `.claude/skills/` and `.agents/skills/` stay, pointing nowhere. `skill-links` fails the Renovate PR that does this, so it doesn't automerge, and a person deletes the links. It catches a repo's own broken skill links the same way.

**Extension.** A repo adds its own checks by redefining `check-extra` or `hooks-extra` in its `.config/mise/config.toml`, which takes precedence over the fragment. Redefining any other template task is a contract violation. For `check`, the shared CI workflow enforces this by verifying where the task is defined.

**Markers.** The `test` task runs every collected test and never filters pytest markers. Which markers a repo uses, and what a local run deselects, is the repo's own policy.

**Raising `min_version`.** The fragment raises mise's `min_version` only when a template feature needs it, and keeps it at or below the mise version pinned by the previous agentic_development release, so a consumer whose workflow-tag update hasn't merged yet still passes CI.

**Sync at commit.** `typecheck` depends on `sync` so that ty sees the current environment. When `uv.lock` is unchanged, `uv sync` is a no-op from uv's cache and needs no network. A commit that changes dependencies pays the install time once.

## Hooks (`.config/copier-python/prek.toml`)

One local hook per commit-time task, and no others: `lint`, `typecheck`, `lid`, `conflicts` and `hooks-extra`.
- Each uses `language = "system"`, `entry = "mise run <task>"` and `pass_filenames = false`.
- Each task checks the whole project, so hook and CI results are identical.
- Running prek by hand goes through `mise run hooks` or `mise run setup`. A bare `prek install` would install a hook with no config path.
- If mise isn't on `PATH`, every hook fails and the commit is refused. Hooks fail closed rather than letting unchecked commits through.

## Decisions & Alternatives

| Decision | Chosen | Alternatives Considered | Rationale |
|---|---|---|---|
| Where checks are defined | mise tasks | Commands in the prek config and in the workflow | One definition serves hooks, CI and manual runs, which is what lets the CI stub pass no inputs |
| Hooks: whole project or staged files | Whole project | Staged files only | Same result as CI. Measured on a project of about 1,800 lines: ty 0.7 s and ruff 0.1 s |
| Tests at commit | No | Run pytest in the hook | Test suites grow past the 10-second budget. CI runs them on every push |
| Repo extension points | Overridable no-op tasks `check-extra` and `hooks-extra` | Repo-owned hook file; editing template files | Repos add checks without touching template-owned files, and every template hook keeps updating |
| Conflict-marker check | A mise task using `git grep` | A third-party hook | No extra dependency. Only the `<<<<<<<` and `>>>>>>>` forms are checked, because `=======` alone is a valid Markdown heading underline |
| Tool installation | mise pins | uv dev dependencies for ruff and ty | Tool versions belong to the template, not to each repo's lock file. Renovate bumps them in one place |
| Dangling skill links | A `skill-links` task in `check`, not run at commit | Accept them as a known limitation; run the task at commit too | A dangling link is a skill no agent can load, and only a template update or a repo's own change creates one. CI on the update PR is where it's caught. Leaving it out of the hooks keeps the hook list to the checks a commit can break in the usual way |
| Hooks without mise | Fail closed | Skip when mise is missing | A skipped hook is an unchecked commit, and CI would catch it only after the push |

## Open Questions & Future Decisions

### Deferred
1. Excluding paths from `conflicts` (for example test fixtures that hold markers on purpose). Add a repo-owned exclusion list when a repo needs one.
2. Staged-file hooks, if a repo grows enough that whole-project runs exceed 10 seconds.
3. macOS support. The `lidc` `asset_pattern` selects the Linux x86_64 binary, which covers the supported platforms today (Linux workstations and CI). Add a per-platform pattern when a macOS user needs it.

## References

- [mise tasks](https://mise.jdx.dev/tasks/); [prek configuration](https://prek.j178.dev/configuration/); [lid-tooling releases](https://github.com/EtaCassiopeia/lid-tooling/releases); [git grep exit status](https://git-scm.com/docs/git-grep).
