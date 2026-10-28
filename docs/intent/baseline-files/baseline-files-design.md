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

The template adds tooling around an existing Python project. It doesn't create one. It also requires the repo to follow LID: its `lid` and LID version checks fail without LID's docs and the `## LID` block in the instruction file. Onboarding sets that up with `/update-lid` when a repo has none.

## Template configuration (`copier.yml`)

| Setting | Value | Why |
|---|---|---|
| `_subdirectory` | `template` | Keeps the template's own tests, docs and tooling out of what consumers receive |
| `_answers_file` | `.copier-answers.python.yml` | A per-layer answers file, so a later `copier-base` layer can coexist, each with its own Renovate PR |
| `_templates_suffix` | `.jinja` (copier's default) | Files without the suffix are copied verbatim. That lets Renovate update tool pins in the template's mise fragment directly |
| `_preserve_symlinks` | `true` | The links from tool-required paths into `.config/copier-python/` are rendered as symlinks, not copies (verified across copy and update) |
| `_skip_if_exists` | every repo-owned path (table below) | Rendered once, never overwritten, recreated only if deleted |
| `_exclude` | `/.config/copier-python/.claude` and `/.config/copier-python/apm_modules` | The installed skills and APM's download cache, when an `apm install` has put them in a working copy of the template ([Skills](#skills)). The template's nested `.gitignore` keeps both out of commits, and copier renders from a commit; the exclusion keeps them out of consumers even if a forced `git add` commits them. With `_subdirectory` set, copier applies none of its default exclusions, so this list is the whole of it. copier matches it against rendered paths |
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
| `.config/copier-python/apm.yml` | template | The pin of agentic_development's skills package ([Skills](#skills)) |
| `.config/copier-python/apm.lock.yaml` | template | APM's lock file for that pin and the LID plugin the package brings: each package's commit, version and deployed files, and each file's hash |
| `.config/copier-python/.gitignore` | template | Ignores `/.claude/` and `apm_modules/` in that directory: the installed skills and APM's download cache |
| `.config/copier-python/lid_version.py` | template | The LID version gate's script: a standard-library Python script, run with `uv run --no-project` ([local checks](../local-checks/local-checks-design.md)) |
| `.config/copier-python/session-start.sh` | template | The session hook ([cloud sessions](../cloud-sessions/cloud-sessions-design.md)). Executable |
| `.claude/skills/<name>` | template | Symlink to `../../.config/copier-python/.claude/skills/<name>`, one per template skill, for Claude Code, which reads only `.claude/skills/` |
| `.agents/skills/<name>` | template | The same symlink, one per template skill, for agents that read the cross-tool `.agents/skills/` location |
| `.claude/settings.json` | repo | Registers the session hook. Repos keep their own permissions and hooks here, and add their own entries beside the template's. A repo opts out of the hook by removing its entry; deleting the file would make the next update recreate it |
| `.config/mise/config.toml` | repo | Starts with a comment: repo-specific tools and overrides of the `*-extra` tasks go here. It takes precedence over `conf.d` fragments |
| `.ruff.toml` | repo | `extend = ".config/copier-python/ruff.toml"` plus an empty `[lint.extend-per-file-ignores]` table. ruff looks only in the project root and its parents, so the repo's ruff file stays at the root, hidden |
| `.github/workflows/ci.yml` (when `forge` is `github`) | repo | Runs on every push to any branch and calls `jmbowman/agentic_development/.github/workflows/check.yml` with no inputs |
| `.github/workflows/lock-refresh.yml` (when `forge` is `github` and `lock_refresh_app_client_id` is set) | repo | On pull requests that change a copier answers file, calls `jmbowman/agentic_development/.github/workflows/lock-refresh.yml` with the App's client ID and the `LOCK_REFRESH_APP_PRIVATE_KEY` secret, so template updates arrive with a refreshed `mise.lock` ([agentic_development lock-refresh LLD](https://github.com/jmbowman/agentic_development/blob/main/docs/intent/lock-refresh/lock-refresh-design.md)). Its GitHub expressions are wrapped in `{% raw %}`, so copier doesn't read them as Jinja. It needs an agentic_development release that includes the lock-refresh workflow, so the template adds it only once `agentic_development_ref` names such a release |
| `.github/renovate.json` (when `forge` is `github`) | repo | Extends `github>jmbowman/agentic_development//renovate/default`. Renovate reads its config from `.github/` as well as the root |
| `docs/arrows/index.yaml` | repo | `schema_version: 2` and an empty `arrows` map, the minimum `lidc` accepts. A repo that adopts LID's arrow overlay replaces it |

The CI stub triggers on `push` to every branch and on nothing else. Renovate's update PRs come from branches in the same repo, so the push run is the check that the default branch's rule requires before automerge. Pull requests from forks get no CI run from a push trigger. See Deferred.

The stubs reference the agentic_development release in `agentic_development_ref`, the one that was current when this template version was released. The CI stub names it by tag at first; Renovate's digest pinning replaces the tag with its commit SHA in the first update PR, so a consumer's first CI runs use the tag. After the first render, Renovate's github-actions and renovate-config managers bump the references, and the github-actions one pins the workflow by digest with the tag as a comment.

## Skills

The template pins one package, and consumers install it and what it brings from the template's lock file:
- **agentic_development's skills package.** Its repo root is a Claude Code plugin, with the skills in a top-level `skills/<name>/` and releases tagged `vX.Y.Z`.
- **LID's `linked-intent-dev` plugin** (`jszmajda/lid/plugins/linked-intent-dev`), which deploys the `linked-intent-dev`, `update-lid` and `lid-coach` skills. The skills package's own root `apm.yml` pins it under `dependencies`, and APM installs a package's `dependencies` (not its `devDependencies`) along with it, so it arrives at the version agentic_development uses itself, and the lock file records it with `depth: 2` and `resolved_by: jmbowman/agentic_development` (observed in this repo's lock file from agentic_development v0.3.1). Which LID plugins come is therefore agentic_development's choice; it pins only `linked-intent-dev`.

"The template's skills" are the skill directories that the lock file's entries list in their `deployed_files` (the entries of the form `.claude/skills/<name>`).

**The manifest and lock file.** `.config/copier-python/apm.yml` deploys only to the `claude` target:

```yaml
name: copier-python-skills
version: 0.0.0
targets:
  - claude
dependencies:
  apm:
    - jmbowman/agentic_development#vX.Y.Z
```

`apm.lock.yaml` beside it records each package's commit, version and deployed files, and each file's hash. Both are template-owned and rendered verbatim. So is `.config/copier-python/.gitignore`, which ignores `/.claude/` (the installed skills) and `apm_modules/` (APM's download cache). APM writes `apm_modules/` into a `.gitignore` beside its manifest on every install, whatever a parent `.gitignore` says, so the template's own copy carries that line already and an install leaves it unchanged (verified with APM 0.35.0).

**Installing.** `apm install --frozen`, run in `.config/copier-python/`, deploys exactly what the lock file records into `.config/copier-python/.claude/skills/<name>/`, and fails when the manifest and the lock file disagree. It deploys only each package's skill directories, none of a package root's other content (verified with APM 0.33.0). APM always deploys under `.claude/skills/` beside its manifest, which is why the skills sit there rather than directly in `.config/copier-python/`. A frozen install fetches by git from `github.com` and needs no GitHub API access (tested with APM 0.33.0 from an empty cache, behind a proxy refusing `api.github.com`). Once the packages are in APM's user-level cache, it needs no network at all, even with `apm_modules/` removed (verified with APM 0.35.0 behind an unreachable proxy).

The `skills` task ([local checks](../local-checks/local-checks-design.md)) runs the install after removing `.config/copier-python/.claude/`. APM removes only what its current lock file records, and a template update replaces the lock file, so without the removal a skill a release dropped would stay installed, and its links would still resolve locally while CI's fail. The task runs:
- in `setup`, so a fresh clone and a re-run after an update get the current skills;
- in cloud sessions, through the session hook ([cloud sessions](../cloud-sessions/cloud-sessions-design.md));
- before `skill-links`, so `check` installs the skills in CI and locally alike, and neither the CI stub nor the shared check workflow needs a step of its own.

**Links.** For each of the template's skills, the template renders `.claude/skills/<name>` and `.agents/skills/<name>` as symlinks to `../../.config/copier-python/.claude/skills/<name>`. In a fresh clone they point nowhere until the first install. APM doesn't create these links, and copier can't render one link per entry of a list, so they are files in `template/`: a package release that adds, renames or removes a skill needs them changed by hand, on the Renovate PR that bumps the pin. A test fails that PR while the links and the lock file's skills differ: each directory must hold exactly one link per skill, named after it, with exactly that target. Only a package's `.claude/skills/<name>` entries count as skills; a package that deploys other kinds of file (commands, agents) isn't supported. copier's update never deletes a symlink, so a skill a release removes leaves its links in consumers, pointing nowhere, and the consumer's `skill-links` check fails the update PR until a person deletes them.

**In this repo.** Renovate's apm manager matches `template/.config/copier-python/apm.yml`, bumps a tag, and, because the lock file sits beside the manifest, runs `apm install` there and commits the manifest and lock file; the installed skills are ignored. The hosted Renovate app installs `apm` for this on demand (verified on this repo's PR #43, whose single Renovate commit refreshed the lock file). Its weekly lock-file maintenance, which `config:best-practices` enables, deletes the lock file and runs `apm install` again; with the tag pins unchanged, the new lock file normally matches the old one. The shared preset exempts agentic_development's releases from the release-age delay. A LID bump comes inside a skills package release, which the preset's hold on LID bumps doesn't cover, so the template's PR merges as usual; consumers' LID version gate then holds the template update that carries it.

This repo installs LID for its own sessions from a root `apm.yml`, which pins `jszmajda/lid/plugins/linked-intent-dev#vX.Y.Z` with `targets: [claude]`, and its `apm.lock.yaml`. Its root `.gitignore` ignores `/.claude/skills/` and `apm_modules/`. Its root `mise.toml` pins `apm` and defines:
- `skills`, which runs `apm install --frozen` at the root, after removing `.claude/skills/`;
- `template-skills`, which runs the same install in `template/.config/copier-python/`, so `check` fails when the template's manifest and lock file disagree;
- `lid-version`, which runs the template's LID version gate script against the root lock file and `AGENTS.md`.

`setup` runs `skills`. `test` depends on `template-skills`, so the install, which removes and refills `template/.config/copier-python/.claude/`, finishes before any test copies the template; `check` depends on `test` and `lid-version`.

**The packages' content.** Installed skills are neither committed nor rendered, so copier never reads them, and consumers' checks don't scan them: `conflicts` searches only tracked files, and `lidc` 0.3.0 skips hidden directories (`crates/lid-core/src/parse/source.rs:47` in lid-tooling). The template's ruff and ty configs exclude `.config/copier-python/`, so consumers don't lint the template's skills; each package's own repo checks them. Skills a consumer deploys with its own `apm.yml` land in `.claude/skills/` and are linted like the rest of the repo.

**In a consumer.** Every repo lays out its skills the same way:
- `.claude/skills/` and `.agents/skills/` are real directories, one entry per skill. Claude Code reads only the first; other agents read the second.
- The template contributes a link in each to each of its skills.
- A skill developed in the repo lives in its own `skills/<name>/`, with repo-owned links to it from `.claude/skills/<name>` and `.agents/skills/<name>`. A skill meant only for other agents gets only the second link.

A consumer that wants skills of its own from other packages adds a repo-owned root `apm.yml` with `targets: [claude]`, installs with the `apm` the template already pins, and gitignores what the install deploys into `.claude/skills/<name>/`. A repo that wants other agents to see one of those skills adds a link to it from `.agents/skills/<name>`. APM records only its own deployments in each lock file, so the consumer's installs and the template's leave each other's skills and the repo's links alone, and `apm audit --ci` at the root covers only the repo's own packages and passes beside the template's skills (verified with APM 0.33.0).

The template's skill names are reserved, LID's included: a consumer's own skills and packages mustn't use one. APM refuses to deploy a skill over a link, and copier conflicts with a file the repo owns at one of its paths. A skill a package adds later can collide with a consumer's own skill of the same name. That risk is accepted, and kept small by giving the package's skills specific names.

The repo's edits to the template's links are replayed by a three-way merge, and copier leaves alone entries in `.claude/skills/` and `.agents/skills/` that the template doesn't render (verified with copier 9.19.0). A consumer that deletes one of the template's links keeps it deleted; the template offers no per-skill opt-out.

Claude Code loads a skill through a linked `.claude/skills/<name>` locally and in cloud sessions (verified in a cloud session with Claude Code 2.1.307). It also discovers nested `.claude/skills/` directories while it works on files below them, so in a session working under `.config/copier-python/` each template skill is listed twice, once through its link and once from that directory. Both entries load the same files.

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
   - a skill in `.claude/skills/` or `.agents/skills/` with the same name as one of the template's, LID's included (copier stops on the conflict; delete the repo's copy, and remove the package that deploys it from the repo's own `apm.yml`);
   - an existing `.claude/settings.json` (kept as-is by `_skip_if_exists`; add the template's SessionStart hook entry to it by hand).
2. **Render from a release tag:** `copier copy --vcs-ref vX.Y.Z https://github.com/jmbowman/copier-python.git .`. An untagged render writes a commit hash that Renovate can't compare against tags.
3. **Trust and install:** `mise trust`, then `mise run setup`, which installs the tools, the template's skills and the git hooks.
4. **LID:** if the repo's instruction file (`AGENTS.md` or `CLAUDE.md`) has no `## LID` block whose `- Version:` matches the LID version in the template's lock file (`.config/copier-python/apm.lock.yaml`), run `/update-lid`, which step 3 installed with the template's LID skills. In a repo without LID it bootstraps the minimum the checks need: the LID directives and `## LID` block in the instruction file (creating `AGENTS.md`, with `CLAUDE.md` linked to it, if there's none), `docs/intent/`, and a starting `docs/high-level-design.md`; the template already rendered `docs/arrows/index.yaml`. In a repo on an older LID version it walks the docs forward. The LID version gate fails until the versions match.
5. **Fix:** `mise run fix` applies ruff's automatic fixes and formatting. Then fix the remaining findings, or record each as a named exception:
   - ruff: `ruff check --add-noqa`, or an entry in `.ruff.toml`'s per-file table for whole-file cases;
   - ty: `mise exec -- ty check --add-ignore`, so ty runs with the template's config.
6. **Lock (optional, recommended):** run `mise lock` and commit `.config/mise/mise.lock` and any sidecars under `.config/mise/locks/`, so indirect dependencies change only through a PR that CI tests.
7. **Commit:** run `mise run check` until it passes, then commit everything as one onboarding commit.
8. **Forge settings:** enable "Allow auto-merge", and add a branch rule on the default branch that requires the CI check, so Renovate's update PRs merge only after CI passes. If the repo commits `mise.lock`, install the lock-refresh GitHub App on it (repository permission Contents: read and write), add its private key as the secret `LOCK_REFRESH_APP_PRIVATE_KEY`, and answer `lock_refresh_app_client_id` (at render time, or later with `copier update --data lock_refresh_app_client_id=<client ID>`, which renders the stub because it doesn't exist yet).

A fresh clone of an onboarded repo needs only `mise trust` and `mise run setup`.

## Updates

Renovate runs `copier update --skip-answered --defaults` for each new tag:
- template-owned files are re-rendered, so a repo that has edited only repo-owned files ends up exactly at the new tag's rendering, without conflicts;
- repo-owned files are untouched, except that copier recreates one the repo deleted;
- a repo's edits to template-owned files are replayed by a three-way merge;
- a template-owned file the repo deleted stays deleted.

An overlapping edit leaves inline conflict markers. Renovate reports that as an artifact error, which blocks automerge, and the `conflicts` check fails as well.

After an update lands locally, the next `mise run` installs any newly pinned tool automatically. Trust given earlier at the repo root covers new fragments too (verified with mise 2026.7.2). An update that changes the template's lock file needs `mise run setup` (or `mise run skills`) to install the new skills locally; `mise run check` does it too.

An update whose lock file carries a new LID version fails the LID version gate until someone runs `/update-lid` on the update's branch and pushes the walk ([local checks](../local-checks/local-checks-design.md)). This is the one kind of template update that waits for a person by design.

## Testing the template

pytest tests in `tests/` render the template with copier's Python API into temporary directories. The skills tests read the template's skills from its lock file and check the links against them offline; tests that install the skills, in this repo or in a rendered consumer, are marked `network`. Update tests build their own tags: they copy `template/` and `copier.yml` into a temporary git repository, tag a version, apply a scripted change, and tag again, so they run offline. Conflict-marker fixtures are built at run time, never stored at the start of a line, so this repo's own `conflicts` check doesn't trip on them. "A newer template tag" in the specs means a tag the tests create this way. Template files under `template/` carry no `@spec` annotations, because they are rendered into consumers whose own `lid` gate would reject IDs from another repo; the tests in `tests/` carry the citations. The sample project for rendering tests is a fixture in `tests/fixtures/sample/`, written to pass the strict profile. Tests that need the network (installing tools or packages, running `mise run check` in a rendered project, or reading the shared check and lock-refresh workflows at `agentic_development_ref`) are marked `network`. CI runs them all, and a local run can deselect them.

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
| Skills delivery | The template's manifest and lock file, rendered into consumers; skills installed from the lock file and gitignored | The installed skill files committed in each consumer; each consumer pins the packages in its own `apm.yml`; a plugin marketplace in the repo's Claude Code settings | Consumers carry pins, not copies of other repos' files, and get one update channel. The hosted Renovate app runs `apm install` only in template repos. Committed copies would put every skill file in every consumer and in every update diff |
| Template skills' location | Installed in `.config/copier-python/.claude/skills/<name>/`, linked from `.claude/skills/<name>` and `.agents/skills/<name>` | Installed directly in `.claude/skills/<name>/` | The directory marks the skills as the template's, and they sit beside a repo's own skills as links of the same shape. **Cost:** copier can't render one link per entry of a list, so a release that adds or removes a skill needs its links changed by hand, which a test enforces |
| Where the manifest lives | `.config/copier-python/apm.yml` | A root `apm.yml` | APM allows one manifest per directory, and a root one would collide with a consumer's own. APM always deploys under `.claude/skills/` beside its manifest, and Renovate runs `apm install` with no flags there |
| Ignoring APM's output | A template-owned `.config/copier-python/.gitignore` | A line in the consumer's root `.gitignore`; `_exclude` only | The template never renders the root `.gitignore`, which the repo owns. APM writes `apm_modules/` into a `.gitignore` beside its manifest anyway, so a template-owned one there keeps installs from changing a tracked file |
| Removing stale skills | The `skills` task removes `.config/copier-python/.claude/` before installing | Relying on APM; a check for installed skills the lock file doesn't list | APM removes only what its current lock file records, and a template update replaces the lock file. Reinstalling from APM's cache costs about a second and leaves exactly what the lock file records |
| `.agents/skills` | A real directory with one link per skill, like `.claude/skills/` | One link from `.agents/skills` to `.claude/skills`; a second copy of each skill | A repo can keep skills for other agents only, and each directory belongs to the repo rather than being the template's link. The template's links in both directories are kept in step by the same test. If Claude Code starts reading `.agents/skills/`, the template's `.claude/skills/` links can be dropped in one release |
| `apm` for consumers | Pinned in the template's mise fragment | Repo-owned, added only by repos with their own `apm.yml` | Every consumer installs the template's skills, so every consumer needs `apm` |
| How the template gets LID | Through the skills package's own `dependencies` | A direct pin in the template's manifest, with agentic_development moving its LID pin to `devDependencies` | One pin to bump, and one LID version across the system. **Cost:** the template can't choose its LID version or plugins, and the shared preset's hold on LID bumps doesn't see a bump that arrives inside a skills package release; consumers' LID version gate still holds the update that carries it |
| `.claude/settings.json` | Repo-owned, rendered once with the hook entry | Template-owned | Repos keep their own permissions and hooks there, and Claude Code can't include a second settings file. **Cost:** a later change to the hook's registration reaches existing consumers only by hand; changes to the script reach them with each update |
| Renovate and the installed skills | No preset exclusion | Add the skill paths to the shared preset's `ignorePaths` | Installed skills are untracked, and no Renovate manager reads the links |
| Questions | Four (forge, line length, copyright regex, lock-refresh App client ID) | Python version, source paths, toggles per tool | Each question is a knob a future release must keep compatible. Tools already discover the Python version and paths. Line length and the copyright notice are genuine per-repo conventions, and the forge isolates the GitHub-specific files |

## Open Questions & Future Decisions

### Deferred
1. Applying the template to its own repo. Waits until the first release is stable.
2. Template-provided `AGENTS.md` fragments. Revisit when a second consumer exists.
3. Splitting out a `copier-base` layer for the hooks, the mise base, the stubs, the skills pin, the session hook and the LID version gate. Happens when a second language or documentation layer is needed.
4. A `pull_request` trigger for repos that accept contributions from forks, made a copier answer so same-repo PRs aren't checked twice.
5. Script-only repos without `pyproject.toml` or `uv.lock`. Out of scope until one needs the baseline.
6. A skill's supporting baseline files (tools, tasks, ignore rules, Claude Code settings), added with the first skill that needs them.
7. Dropping the template's `.claude/skills/` links, if Claude Code starts reading `.agents/skills/` ([anthropics/claude-code#31005](https://github.com/anthropics/claude-code/issues/31005)).
8. Exempting scripts in third-party skills that a consumer deploys with its own `apm.yml` from the strict profile, when the first such skill needs it.

## References

- [copier configuration](https://copier.readthedocs.io/en/stable/configuring/); [mise configuration](https://mise.jdx.dev/configuration.html); [prek configuration](https://prek.j178.dev/configuration/); [uv settings](https://docs.astral.sh/uv/reference/settings/).
- Contracts this leaf fulfils: agentic_development's check workflow (`CHECK`) and Renovate preset (`PRESET`) LLDs.
