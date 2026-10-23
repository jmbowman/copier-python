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
| `_exclude` | `apm.yml`, `apm.lock.yaml`, `apm_modules` and `.gitignore`, each under `/.config/copier-python/` | The files APM keeps beside the template's skills manifest ([Skills](#skills)). With `_subdirectory` set, copier applies none of its default exclusions, so this list is the whole of it. copier matches it against rendered paths |
| `_min_copier_version` | `9.6.0`, the oldest copier version the template is tested with, kept deliberately low. Older releases are untested, not known to fail | Hosted Renovate's copier may lag the newest release, and a minimum above it would fail every update. The rendering and update tests run on this version and on the copier version in this repo's `uv.lock`, which Renovate keeps current, so there is no separate version list to drift |
| `agentic_development_ref` | a constant (a question with `when: false`, so it is never asked or stored in answers) holding the agentic_development tag that this template version's stubs reference | One place for the tag. This repo's own Renovate config bumps it with a custom regex manager (datasource `github-tags`, package `jmbowman/agentic_development`) that matches the constant's `default:` line in `copier.yml`, so each template release references the then-current agentic_development release (verified: copier renders the constant and leaves it out of the answers file) |
| Tasks, migrations, Jinja extensions | none | Updates must run under hosted Renovate without `--trust` |

## Questions

| Question | Type | Default | Used for |
|---|---|---|---|
| `forge` | choice: `github` | `github` | Selects the forge-specific files: the CI stub and the preset reference prefix. Only GitHub exists today, and the question is in place so another forge can be added as a new choice |
| `line_length` | int | `100` | ruff's `line-length`, used by both the formatter and `E501` |
| `copyright_notice_regex` | str | empty | When set, enables ruff's copyright-notice rule (`CPY001`) with this pattern. When empty, the rule is off. Some projects require a notice in every file and some carry none |
| `lock_refresh_app_client_id` | str (asked only when `forge` is `github`) | empty | The client ID of the repo's lock-refresh GitHub App. When set (and `forge` is `github`), the template renders the lock-refresh stub with it. When empty, no stub is rendered, so a repo that doesn't commit `mise.lock` needs no App. The ID isn't sensitive; the App's private key is a repository secret |

These are the only questions. Everything else is discovered rather than asked: ruff, ty and uv read the Python version from `requires-python`, and ruff and ty find source and test files themselves. A question added in a later release must have a default that leaves existing repos passing, because Renovate's update accepts defaults without asking.

## Files and owners

**Layout.** Every template-owned file lives in `.config/copier-python/`, apart from the links that point into it, so the directory itself says where a file comes from. Where a tool only looks elsewhere, a symlink or an environment variable points it there. The repo root gains as few files as the tools allow: two hidden files and one symlink, plus the `.claude/` and `.agents/` directories that hold the skill links.

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
| `.config/copier-python/.claude/skills/<name>/` | template | One directory per skill in agentic_development's skills package, exactly as APM deploys it: the contents of the package's `skills/<name>/`, including its `LICENSE.txt` |
| `.claude/skills/<name>` | template | Symlink to `../../.config/copier-python/.claude/skills/<name>`, one per template skill, for Claude Code, which reads only `.claude/skills/` |
| `.agents/skills/<name>` | template | The same symlink, one per template skill, for agents that read the cross-tool `.agents/skills/` location |
| `.config/mise/config.toml` | repo | Starts with a comment: repo-specific tools and overrides of the `*-extra` tasks go here. It takes precedence over `conf.d` fragments |
| `.ruff.toml` | repo | `extend = ".config/copier-python/ruff.toml"` plus an empty `[lint.extend-per-file-ignores]` table. ruff looks only in the project root and its parents, so the repo's ruff file stays at the root, hidden |
| `.github/workflows/ci.yml` (when `forge` is `github`) | repo | Runs on every push to any branch and calls `jmbowman/agentic_development/.github/workflows/check.yml` with no inputs |
| `.github/workflows/lock-refresh.yml` (when `forge` is `github` and `lock_refresh_app_client_id` is set) | repo | On pull requests that change a copier answers file, calls `jmbowman/agentic_development/.github/workflows/lock-refresh.yml` with the App's client ID and the `LOCK_REFRESH_APP_PRIVATE_KEY` secret, so template updates arrive with a refreshed `mise.lock` ([agentic_development lock-refresh LLD](https://github.com/jmbowman/agentic_development/blob/main/docs/intent/lock-refresh/lock-refresh-design.md)). Its GitHub expressions are wrapped in `{% raw %}`, so copier doesn't read them as Jinja. It needs an agentic_development release that includes the lock-refresh workflow, so the template adds it only once `agentic_development_ref` names such a release |
| `.github/renovate.json` (when `forge` is `github`) | repo | Extends `github>jmbowman/agentic_development//renovate/default`. Renovate reads its config from `.github/` as well as the root |
| `docs/arrows/index.yaml` | repo | `schema_version: 2` and an empty `arrows` map, the minimum `lidc` accepts. A repo that adopts LID's arrow overlay replaces it |

The CI stub triggers on `push` to every branch and on nothing else. Renovate's update PRs come from branches in the same repo, so the push run is the check that the default branch's rule requires before automerge. Pull requests from forks get no CI run from a push trigger. See Deferred.

The stubs reference the agentic_development release in `agentic_development_ref`, the one that was current when this template version was released. The CI stub names it by tag at first; Renovate's digest pinning replaces the tag with its commit SHA in the first update PR, so a consumer's first CI runs use the tag. After the first render, Renovate's github-actions and renovate-config managers bump the references, and the github-actions one pins the workflow by digest with the tag as a comment.

## Skills

agentic_development ships one skills package: its repo root is a Claude Code plugin, with the skills in a top-level `skills/<name>/` and releases tagged `vX.Y.Z`. The template delivers those skills to consumers as template-owned files.

**In this repo.** `template/.config/copier-python/apm.yml` pins the package and deploys only to the `claude` target:

```yaml
name: copier-python-skills
version: 0.0.0
targets:
  - claude
dependencies:
  apm:
    - jmbowman/agentic_development#vX.Y.Z
```

`apm install`, run in `template/.config/copier-python/`, writes the skills to `.claude/skills/<name>/` in that directory, the lock file to `apm.lock.yaml` beside the manifest, its download cache to `apm_modules/`, and `apm_modules/` into a `.gitignore` there. It writes nothing outside the manifest's directory, and it deploys only each `skills/<name>/` directory, none of the package root's other content (verified with APM 0.33.0 against agentic_development v0.3.0). APM always deploys under `.claude/skills/` in the manifest's directory, which is why the skills sit at `.config/copier-python/.claude/skills/` rather than directly in `.config/copier-python/`. The manifest, the lock file, the deployed skills and the `.gitignore` are committed; `apm_modules/` is not. `copier.yml`'s `_exclude` keeps APM's files out of consumers.

`template/.claude/skills/` and `template/.agents/skills/` each hold one symlink per deployed skill, named after it and pointing to `../../.config/copier-python/.claude/skills/<name>`, and nothing else. APM doesn't create these links, so a package release that adds, renames or removes a skill needs them changed by hand. A test fails while the links and the deployed skills differ, so that release's Renovate PR fails CI instead of automerging a skill no agent can reach, or a dangling link.

Renovate's apm manager matches the manifest, bumps the tag, and, because the lock file sits beside the manifest, runs `apm install` with the manifest's directory as its working directory. It commits every file the install adds, changes or deletes, so the skill files, the lock file and the manifest move together in one PR. The shared preset already exempts agentic_development's releases from the release-age delay. The next template tag carries the new skills to consumers.

This repo pins `apm` in its own root `mise.toml`, for regenerating the skills by hand and for its check. The `skills` task runs `apm audit --ci --no-drift` in `template/.config/copier-python/`, which fails when a deployed skill file no longer matches the lock file's hash, so a hand edit to a deployed skill fails the check instead of reaching consumers. `--no-drift` skips the install replay, which would download the package.

Skill files are copied verbatim, because copier renders only files ending in `.jinja`. A skill file whose own name ends in `.jinja` would be rendered and renamed, so the package's skills mustn't contain one. Consumers' `lid` and `conflicts` checks scan every tracked file, the skills included, so the skills also mustn't contain a literal `@spec` annotation or a line starting with a conflict marker. This repo's tests and `conflicts` task check `template/` for both, so a package release that breaks either rule fails its Renovate PR here rather than every consumer's check.

**In a consumer.** Every repo lays out its committed skills the same way:
- `.claude/skills/` and `.agents/skills/` are real directories, one entry per skill. Claude Code reads only the first; other agents read the second.
- The template contributes a link in each to each of its skills.
- A skill developed in the repo lives in its own `skills/<name>/`, with repo-owned links to it from `.claude/skills/<name>` and `.agents/skills/<name>`. A skill meant only for other agents gets only the second link.

A consumer that wants skills of its own from other packages adds a repo-owned root `apm.yml` with `targets: [claude]`, adds `apm` to `.config/mise/config.toml`, and commits what `apm install` deploys. The installed skills are real files in `.claude/skills/<name>/`; a repo that wants other agents to see one adds a link to it from `.agents/skills/<name>`. APM records only its own deployments in the consumer's lock file, so its installs leave the template's links and the repo's own links alone, and `apm audit --ci` covers only the repo's own packages (verified with APM 0.33.0).

The template's skill names are reserved: a consumer's own skills and packages mustn't use the name of one of the template's. APM refuses to deploy a skill over a link, and copier conflicts with a file the repo owns at one of its paths. A skill the package adds later can collide with a consumer's own skill of the same name. That risk is accepted, and kept small by giving the package's skills specific names.

Copier treats the skill files and links like any other template-owned file, with one exception: it never deletes a symlink. An update re-renders them, adding, changing and deleting files and adding links as the release did. When a release removes or renames a skill, its old links are left pointing nowhere, and the consumer's `skill-links` check ([local checks](../local-checks/local-checks-design.md)) fails the update PR until a person deletes them; the repo's edits to them are replayed by a three-way merge; and copier leaves alone entries in `.claude/skills/` and `.agents/skills/` that the template doesn't render (verified with copier 9.19.0). A consumer that deletes one of the template's skills keeps it deleted, but a file a later release adds to that skill arrives on its own; the template offers no per-skill opt-out.

The template's ruff and ty configs exclude `.config/copier-python/`, so consumers don't lint the template's skills; the package's own repo checks them under the strict profile. Skills a consumer deploys with its own `apm.yml` land in `.claude/skills/` and are linted like the rest of the repo.

Claude Code also discovers nested `.claude/skills/` directories while it works on files below them, so in a session working under `.config/copier-python/` each template skill is listed twice, once through its link and once from that directory (observed with Claude Code in this repo's `template/`). Both entries load the same files.

**Skills that need more than their own files.** A later skill may need supporting baseline files: tools, mise tasks, ignore rules or Claude Code settings. Those are ordinary template files, added to the template in the same release that bumps the skills pin, under the same ownership rules as the rest of the baseline.

## Onboarding an existing repo

1. **Check for files the template would shadow or skip, and migrate their content first:**
   - an existing `.ruff.toml`, `.config/mise/config.toml`, `.github/workflows/ci.yml`, `.github/workflows/lock-refresh.yml` or `.github/renovate.json` (kept as-is by `_skip_if_exists`, so it never gets the `extend` line, the stubs or the preset);
   - a root `ruff.toml` or a `[tool.ruff]` table (ruff uses the first config file it finds in a directory, so these compete with `.ruff.toml`);
   - a root `mise.toml` (it outranks `.config/mise/config.toml`; move its content there);
   - a root `renovate.json` or `.renovaterc*` (Renovate uses the first config file it finds);
   - a `[tool.ty]` table (the template's config through `TY_CONFIG_FILE` takes precedence; verified with ty 0.0.84);
   - a `[tool.uv]` table: with `uv.toml` present, uv ignores its settings, though `[tool.uv.sources]` still applies (verified with uv 0.11.24);
   - a `.pre-commit-config.yaml` (no longer used; the hook runs the template's `prek.toml`);
   - a `.claude/skills` or `.agents/skills` that is a link rather than a directory (copier writes the template's links through it; replace it with a real directory holding the same skills, as files or links);
   - a skill in `.claude/skills/` or `.agents/skills/` with the same name as one of the template's (copier stops on the conflict; delete the repo's copy, and remove the package that deploys it from the repo's own `apm.yml`).
2. **Render from a release tag:** `copier copy --vcs-ref vX.Y.Z https://github.com/jmbowman/copier-python.git .`. An untagged render writes a commit hash that Renovate can't compare against tags.
3. **Trust and install:** `mise trust`, then `mise run setup`, which installs the tools and the git hooks.
4. **Fix:** `mise run fix` applies ruff's automatic fixes and formatting. Then fix the remaining findings, or record each as a named exception:
   - ruff: `ruff check --add-noqa`, or an entry in `.ruff.toml`'s per-file table for whole-file cases;
   - ty: `mise exec -- ty check --add-ignore`, so ty runs with the template's config.
5. **Lock (optional, recommended):** run `mise lock` and commit `.config/mise/mise.lock` and any sidecars under `.config/mise/locks/`, so indirect dependencies change only through a PR that CI tests.
6. **Commit:** run `mise run check` until it passes, then commit everything as one onboarding commit.
7. **Forge settings:** enable "Allow auto-merge", and add a branch rule on the default branch that requires the CI check, so Renovate's update PRs merge only after CI passes. If the repo commits `mise.lock`, install the lock-refresh GitHub App on it (repository permission Contents: read and write), add its private key as the secret `LOCK_REFRESH_APP_PRIVATE_KEY`, and answer `lock_refresh_app_client_id` (at render time, or later with `copier update --data lock_refresh_app_client_id=<client ID>`, which renders the stub because it doesn't exist yet).

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

pytest tests in `tests/` render the template with copier's Python API into temporary directories. The skills tests use the skills committed under `template/.config/copier-python/.claude/skills/` and the links beside them, so they run offline. Update tests build their own tags: they copy `template/` and `copier.yml` into a temporary git repository, tag a version, apply a scripted change, and tag again, so they run offline. Conflict-marker fixtures are built at run time, never stored at the start of a line, so this repo's own `conflicts` check doesn't trip on them. "A newer template tag" in the specs means a tag the tests create this way. Template files under `template/` carry no `@spec` annotations, because they are rendered into consumers whose own `lid` gate would reject IDs from another repo; the tests in `tests/` carry the citations. The sample project for rendering tests is a fixture in `tests/fixtures/sample/`, written to pass the strict profile. Tests that need the network (installing tools or packages, running `mise run check` in a rendered project, or reading the shared check and lock-refresh workflows at `agentic_development_ref`) are marked `network`. CI runs them all, and a local run can deselect them.

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
| Skills delivery | The template pins the skills package in `template/.config/copier-python/apm.yml` and renders the deployed skills as template-owned files | Each consumer pins the package in its own `apm.yml`; deployed files gitignored and installed by a SessionStart hook; a plugin marketplace in the repo's Claude Code settings | One update channel per consumer, and the hosted Renovate app has to run `apm install` only in template repos. Committed files are the only form a cloud session loads: it has no `apm` for a hook to run, and it doesn't install plugins from the repo's settings |
| Template skills' form | Real files in `.config/copier-python/.claude/skills/<name>/`, linked from `.claude/skills/<name>` and `.agents/skills/<name>` | Real files in `.claude/skills/<name>/` | The directory marks the skills as the template's, and they sit beside a repo's own skills as links of the same shape. **Cost:** copier can't render one link per entry of a list, so a release that adds or removes a skill needs its links changed by hand, which a test enforces. A consumer's own package can't deploy a skill of the same name over the link, which the reserved names rule out anyway |
| Where `apm install` runs | `template/.config/copier-python/`, the manifest's own directory | A manifest elsewhere in this repo, deploying into the template | Renovate runs `apm install` with no flags in the manifest's directory, so the deployment lands under it. `--root` would redirect the lock file and `.gitignore` as well, and Renovate doesn't pass it |
| Keeping APM's files out of consumers | `_exclude` for the manifest, lock file, `apm_modules/` and `.gitignore` under `/.config/copier-python/` | Leaving the `.gitignore` uncommitted; ignoring `apm_modules/` from this repo's root `.gitignore` | APM writes a `.gitignore` beside the manifest on every install, whatever a parent `.gitignore` says, and Renovate would commit it |
| `.agents/skills` | A real directory with one link per skill, like `.claude/skills/` | One link from `.agents/skills` to `.claude/skills`; a second copy of each skill | A repo can keep skills for other agents only, and each directory belongs to the repo rather than being the template's link. The template's links in both directories are kept in step by the same test. If Claude Code starts reading `.agents/skills/`, the template's `.claude/skills/` links can be dropped in one release |
| `apm` for consumers | Repo-owned: a consumer that adds its own `apm.yml` adds `apm` to `.config/mise/config.toml` | Pinned in the template's mise fragment | Consumers receive the template's skills without running `apm`, so a template pin would install an unused tool in every consumer's setup and CI run |
| Renovate and the rendered skills | No preset exclusion for `.claude/skills/` | Add the skill paths to the shared preset's `ignorePaths` | No Renovate manager reads skill files, and a consumer's own `apm install` leaves the template's skills untouched, so Renovate never changes them |
| Questions | Four (forge, line length, copyright regex, lock-refresh App client ID) | Python version, source paths, toggles per tool | Each question is a knob a future release must keep compatible. Tools already discover the Python version and paths. Line length and the copyright notice are genuine per-repo conventions, and the forge isolates the GitHub-specific files |

## Open Questions & Future Decisions

### Deferred
1. Applying the template to its own repo. Waits until the first release is stable.
2. Template-provided `AGENTS.md` fragments. Revisit when a second consumer exists.
3. Splitting out a `copier-base` layer for the hooks, the mise base, the stubs and the skills pin. Happens when a second language or documentation layer is needed.
4. A `pull_request` trigger for repos that accept contributions from forks, made a copier answer so same-repo PRs aren't checked twice.
5. Script-only repos without `pyproject.toml` or `uv.lock`. Out of scope until one needs the baseline.
6. A skill's supporting baseline files (tools, tasks, ignore rules, Claude Code settings), added with the first skill that needs them.
7. Dropping the template's `.claude/skills/` links, if Claude Code starts reading `.agents/skills/` ([anthropics/claude-code#31005](https://github.com/anthropics/claude-code/issues/31005)).
8. Exempting scripts in third-party skills that a consumer deploys with its own `apm.yml` from the strict profile, when the first such skill needs it.

### Open questions
1. Whether the hosted Renovate app installs `apm` on demand. Renovate's apm manager declares `apm` as a tool to install, and containerbase has an installer for it, but whether the hosted app runs that install is documented, not verified. The first apm PR in this repo settles it. If it can't, the fallback is a workflow that runs `apm install` on Renovate's apm PRs and pushes the result, as the lock-refresh workflow does for `mise lock`.
2. Whether Claude Code in a cloud session loads a skill through a linked `.claude/skills/<name>`. It does locally, as documented, and a cloud session's clone keeps git's symlinks, but this is untested. agentic_development loads its own skill through a linked `.claude/skills/<name>` too, so a cloud session there settles it. If it can't, the template's skills move to real files in `.claude/skills/<name>/`.

## References

- [copier configuration](https://copier.readthedocs.io/en/stable/configuring/); [mise configuration](https://mise.jdx.dev/configuration.html); [prek configuration](https://prek.j178.dev/configuration/); [uv settings](https://docs.astral.sh/uv/reference/settings/).
- Contracts this leaf fulfils: agentic_development's check workflow (`CHECK`) and Renovate preset (`PRESET`) LLDs.
