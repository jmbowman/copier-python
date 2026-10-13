---
parent: high-level-design
prefix: FILES
---

# Baseline files

## Context and Design Philosophy

This leaf defines what the template renders, who owns each file, which questions it asks, and how a repo is onboarded and updated. Its guiding rule is the template tenet: clean updates over a rich first render. Template-owned files contain nothing a repo will predictably want to change, and every predictable change has a repo-owned place to live.

## Preconditions

A consumer repo has:
- a `pyproject.toml` with `requires-python`;
- a committed `uv.lock`;
- pytest in a dependency group or optional extra;
- at least one test.

The template adds tooling around an existing Python project. It doesn't create one.

## Template configuration (`copier.yml`)

| Setting | Value | Why |
|---|---|---|
| `_subdirectory` | `template` | Keeps the template's own tests, docs and tooling out of what consumers receive |
| `_answers_file` | `.copier-answers.python.yml` | A per-layer answers file, so a later `copier-base` layer can coexist, each with its own Renovate PR |
| `_templates_suffix` | `.jinja` (copier's default) | Files without the suffix are copied verbatim. That lets Renovate update tool pins in the template's mise fragment directly |
| `_preserve_symlinks` | `true` | The links from tool-required paths into `.config/copier-python/` are rendered as symlinks, not copies (verified across copy and update) |
| `_skip_if_exists` | every repo-owned path (table below) | Rendered once, never overwritten, recreated only if deleted |
| `_min_copier_version` | `9.6.0`, the oldest copier version the template is tested with, kept deliberately low. Older releases are untested, not known to fail | Hosted Renovate's copier may lag the newest release, and a minimum above it would fail every update. The rendering and update tests run on this version and on the copier version in this repo's `uv.lock`, which Renovate keeps current, so there is no separate version list to drift |
| `agentic_development_ref` | a constant (a question with `when: false`, so it is never asked or stored in answers) holding the agentic_development tag that this template version's stubs reference | One place for the tag. This repo's own Renovate config bumps it with a custom regex manager (datasource `github-tags`, package `jmbowman/agentic_development`) that matches the constant's `default:` line in `copier.yml`, so each template release references the then-current agentic_development release (verified: copier renders the constant and leaves it out of the answers file) |
| Tasks, migrations, Jinja extensions | none | Updates must run under hosted Renovate without `--trust` |

## Questions

| Question | Type | Default | Used for |
|---|---|---|---|
| `forge` | choice: `github` | `github` | Selects the forge-specific files: the CI stub and the preset reference prefix. Only GitHub exists today, and the question is in place so another forge can be added as a new choice |
| `line_length` | int | `100` | ruff's `line-length`, used by both the formatter and `E501` |
| `copyright_notice_regex` | str | empty | When set, enables ruff's copyright-notice rule (`CPY001`) with this pattern. When empty, the rule is off. Some projects require a notice in every file and some carry none |

These are the only questions. Everything else is discovered rather than asked: ruff, ty and uv read the Python version from `requires-python`, and ruff and ty find source and test files themselves. A question added in a later release must have a default that leaves existing repos passing, because Renovate's update accepts defaults without asking.

## Files and owners

**Layout.** Every template-owned file lives in `.config/copier-python/`, so the directory itself says where a file comes from. Where a tool only looks elsewhere, a symlink or an environment variable points it there. The repo root gains as few files as the tools allow: two hidden files and one symlink.

| Path in the consumer | Owner | Content |
|---|---|---|
| `.copier-answers.python.yml` | copier | Template source (`https://github.com/jmbowman/copier-python.git`), version tag and answers. Must sit at the root: Renovate runs copier from the answers file's directory |
| `.config/copier-python/mise.toml` | template | Pinned tools, mise's `min_version`, `TY_CONFIG_FILE`, and the check tasks ([local checks](../local-checks/local-checks-design.md)). Not a `.jinja` file |
| `.config/mise/conf.d/copier-python.toml` | template | Symlink to `../../copier-python/mise.toml`, so mise loads the fragment. `conf.d/` holds only templates' links: Renovate ignores it, and CI trusts a `check` task defined there, so repo config never goes in it |
| `.config/copier-python/ruff.toml` | template | The strict ruff base ([strict profile](../strict-profile/strict-profile-design.md)) |
| `.config/copier-python/ty.toml` | template | The strict ty config. ty finds it through `TY_CONFIG_FILE`, which the mise fragment sets to `{{config_root}}/.config/copier-python/ty.toml`, an absolute path to the repo root even through the symlink (verified with mise 2026.7.2) |
| `.config/copier-python/prek.toml` | template | Commit-time hooks, each calling a mise task. `prek install -c` records this path in the git hook |
| `.config/copier-python/exceptions.py` | template | The `exceptions` task's scanner: a standard-library Python script, run with `uv run --no-project` |
| `.config/copier-python/uv.toml` | template | `exclude-newer = "3 days"`, the lock-file half of the shared preset's supply-chain delay |
| `uv.toml` | template | Symlink to `.config/copier-python/uv.toml`. uv reads project settings only from the project root, and Renovate's lock-file maintenance runs uv there without mise's environment |
| `.config/mise/config.toml` | repo | Starts with a comment: repo-specific tools and overrides of the `*-extra` tasks go here. It takes precedence over `conf.d` fragments |
| `.ruff.toml` | repo | `extend = ".config/copier-python/ruff.toml"` plus an empty `[lint.extend-per-file-ignores]` table. ruff looks only in the project root and its parents, so the repo's ruff file stays at the root, hidden |
| `.github/workflows/ci.yml` (when `forge` is `github`) | repo | Runs on every push to any branch and calls `jmbowman/agentic_development/.github/workflows/check.yml` with no inputs |
| `.github/renovate.json` (when `forge` is `github`) | repo | Extends `github>jmbowman/agentic_development//renovate/default`. Renovate reads its config from `.github/` as well as the root |
| `docs/arrows/index.yaml` | repo | `schema_version: 2` and an empty `arrows` map, the minimum `lidc` accepts. A repo that adopts LID's arrow overlay replaces it |

The CI stub triggers on `push` to every branch and on nothing else. Renovate's update PRs come from branches in the same repo, so the push run is the check that the default branch's rule requires before automerge. Pull requests from forks get no CI run from a push trigger. See Deferred.

The two stubs reference the agentic_development release in `agentic_development_ref`, the one that was current when this template version was released. The CI stub names it by tag at first; Renovate's digest pinning replaces the tag with its commit SHA in the first update PR, so a consumer's first CI runs use the tag. After the first render, Renovate's github-actions and renovate-config managers bump the references, and the github-actions one pins the workflow by digest with the tag as a comment.

## Onboarding an existing repo

1. **Check for files the template would shadow or skip, and migrate their content first:**
   - an existing `.ruff.toml`, `.config/mise/config.toml`, `.github/workflows/ci.yml` or `.github/renovate.json` (kept as-is by `_skip_if_exists`, so it never gets the `extend` line, the stub or the preset);
   - a root `ruff.toml` or a `[tool.ruff]` table (ruff uses the first config file it finds in a directory, so these compete with `.ruff.toml`);
   - a root `mise.toml` (it outranks `.config/mise/config.toml`; move its content there);
   - a root `renovate.json` or `.renovaterc*` (Renovate uses the first config file it finds);
   - a `[tool.ty]` table (the template's config through `TY_CONFIG_FILE` takes precedence; verified with ty 0.0.84);
   - a `[tool.uv]` table: with `uv.toml` present, uv ignores its settings, though `[tool.uv.sources]` still applies (verified with uv 0.11.24);
   - a `.pre-commit-config.yaml` (no longer used; the hook runs the template's `prek.toml`).
2. **Render from a release tag:** `copier copy --vcs-ref vX.Y.Z https://github.com/jmbowman/copier-python.git .`. An untagged render writes a commit hash that Renovate can't compare against tags.
3. **Trust and install:** `mise trust`, then `mise run setup`, which installs the tools and the git hooks.
4. **Fix:** `mise run fix` applies ruff's automatic fixes and formatting. Then fix the remaining findings, or record each as a named exception:
   - ruff: `ruff check --add-noqa`, or an entry in `.ruff.toml`'s per-file table for whole-file cases;
   - ty: `mise exec -- ty check --add-ignore`, so ty runs with the template's config.
5. **Commit:** run `mise run check` until it passes, then commit everything as one onboarding commit.
6. **Forge settings:** enable "Allow auto-merge", and add a branch rule on the default branch that requires the CI check, so Renovate's update PRs merge only after CI passes.

A fresh clone of an onboarded repo needs only `mise trust` and `mise run setup`.

## Updates

Renovate runs `copier update --skip-answered --defaults` for each new tag:
- template-owned files are re-rendered, so a repo that has edited only repo-owned files ends up exactly at the new tag's rendering, without conflicts;
- repo-owned files are untouched, except that copier recreates one the repo deleted;
- a repo's edits to template-owned files are replayed by a three-way merge;
- a template-owned file the repo deleted stays deleted.

An overlapping edit leaves inline conflict markers. Renovate reports that as an artifact error, which blocks automerge, and the `conflicts` check fails as well.

After an update lands locally, the next `mise run` installs any newly pinned tool automatically. Trust given earlier at the repo root covers new fragments too (verified with mise 2026.7.2).

## Testing the template

pytest tests in `tests/` render the template with copier's Python API into temporary directories. Update tests build their own tags: they copy `template/` and `copier.yml` into a temporary git repository, tag a version, apply a scripted change, and tag again, so they run offline. Conflict-marker fixtures are built at run time, never stored at the start of a line, so this repo's own `conflicts` check doesn't trip on them. "A newer template tag" in the specs means a tag the tests create this way. Template files under `template/` carry no `@spec` annotations, because they are rendered into consumers whose own `lid` gate would reject IDs from another repo; the tests in `tests/` carry the citations. The sample project for rendering tests is a fixture in `tests/fixtures/sample/`, written to pass the strict profile. Tests that need the network (installing tools or packages, running `mise run check` in a rendered project, or reading the shared check workflow at `agentic_development_ref`) are marked `network`. CI runs them all, and a local run can deselect them.

## Decisions & Alternatives

| Decision | Chosen | Alternatives Considered | Rationale |
|---|---|---|---|
| File layout | Template-owned files in `.config/copier-python/`, linked from tool-required paths; repo-owned files in `.config/` where tools allow | Template files at the tool-default paths in the root | One directory shows what the template owns, and the root stays nearly empty. Tested: copier preserves the symlinks across copy and update, mise follows the symlinked fragment, prek records its config path at install, and `TY_CONFIG_FILE` points ty at its config |
| Pointing tools at `.config/copier-python/` | Environment variable for ty, install flag for prek, symlinks for mise and uv | Symlinks everywhere; command-line flags in each task | Each tool's own mechanism, with a root symlink only where a tool or Renovate reads the file without mise's environment. **Cost:** ty sees `TY_CONFIG_FILE` only in a mise-activated shell or a mise task. An editor's ty language server started elsewhere runs ty's defaults, less strict than CI, until the editor is started from a mise-activated shell or given the variable in its settings. A root `ty.toml` symlink would remove that cost at the price of one more root file |
| mise config ownership | Template-owned fragment plus repo-owned `.config/mise/config.toml` | Template-owned `mise.toml` | mise merges both, and the repo's file wins for any task or tool it redefines. That gives repos an override point without touching template files. Verified: one `mise trust` at the repo root covers current and later fragments |
| Hook config ownership | Template-owned `prek.toml`; repo extras through an overridable mise task | Repo-owned `prek.toml` | prek reads one config per project with no includes, so a repo-owned file would never receive new template hooks |
| ruff base location | `.config/copier-python/ruff.toml`, with its path patterns prefixed `../../` | A root `ruff-base.toml` | ruff anchors `per-file-ignores` patterns to the declaring file's directory. Prefixing climbs back to the repo root (verified with ruff) |
| Lock-file supply-chain delay | Template-owned `uv.toml` (linked at the root) with `exclude-newer = "3 days"` | `[tool.uv]` in `pyproject.toml`; no delay for lock files | The template doesn't edit `pyproject.toml`. uv records the setting as a span (`exclude-newer-span = "P3D"`), so `uv sync --locked` stays valid as time passes (verified with uv 0.11.24) |
| `docs/arrows/index.yaml` | Repo-owned minimal stub | Not rendered; template-owned | `lidc` refuses to run without it. The repo owns it because a real arrow overlay replaces its content |
| `pyproject.toml` | Never rendered or edited | Render tool sections into it | Project metadata belongs to the repo. A partially template-owned file would conflict on every update |
| Questions | Three (forge, line length, copyright regex) | Python version, source paths, toggles per tool | Each question is a knob a future release must keep compatible. Tools already discover the Python version and paths. Line length and the copyright notice are genuine per-repo conventions, and the forge isolates the GitHub-specific files |

## Open Questions & Future Decisions

### Deferred
1. Applying the template to its own repo. Waits until the first release is stable.
2. Template-provided `AGENTS.md` fragments. Revisit when a second consumer exists.
3. A repo-owned `apm.yml` that depends on agentic_development's skills package, rendered once, after that package exists.
4. Splitting out a `copier-base` layer for the hooks, the mise base and the stubs. Happens when a second language or documentation layer is needed.
5. A `pull_request` trigger for repos that accept contributions from forks, made a copier answer so same-repo PRs aren't checked twice.
6. Script-only repos without `pyproject.toml` or `uv.lock`. Out of scope until one needs the baseline.

## References

- [copier configuration](https://copier.readthedocs.io/en/stable/configuring/); [mise configuration](https://mise.jdx.dev/configuration.html); [prek configuration](https://prek.j178.dev/configuration/); [uv settings](https://docs.astral.sh/uv/reference/settings/).
- Contracts this leaf fulfils: agentic_development's check workflow (`CHECK`) and Renovate preset (`PRESET`) LLDs.
