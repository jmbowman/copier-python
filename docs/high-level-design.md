# High-Level Design: copier-python

This is the Python baseline template of [agentic_development](https://github.com/jmbowman/agentic_development) (`../agentic_development` locally). That repo's HLD defines the system, its glossary, the file-ownership model and the tenets, which all apply here.

## Problem

Every Python repo developed with this system needs the same strict tooling: ruff, ty, prek hooks, mise tasks, CI and Renovate. Today some have none, and keeping hand-copied config consistent fails as soon as the baseline changes. The baseline has to be applied to a repo once and then kept current automatically, and each repo's own adjustments have to survive every update.

## Approach

A copier template, released by git tag, that a repo applies with `copier copy` and that Renovate's copier manager keeps current with `copier update`.

- **Applies to new and existing repos.** The template adds tooling files. It never creates or rewrites package source, tests or `pyproject.toml` project metadata.
- **Template-owned base, repo-owned top.** Where a tool supports inheritance, the template owns the base config and the repo owns a thin top file that extends it. Named exceptions live in repo-owned files or as inline suppressions in code.
- **Per-repo knobs are copier questions,** kept to the few that tools can't discover themselves. Answers are stored in `.copier-answers.python.yml`. Changing an answer is a re-render, not a hand edit. A new question added in a template release takes its default during Renovate's update, so every new question needs a safe default.
- **Shared pieces are referenced, not copied.** The repo-owned CI stub calls the shared check workflow in agentic_development without passing inputs (the workflow reads the template-maintained tool pins and tasks), and the repo-owned `.github/renovate.json` extends that repo's preset, each pinned to a tag.
- **Except skills, which arrive as committed copies.** The template pins agentic_development's skills package in its own APM manifest and renders the deployed skill files into each consumer's `.config/copier-python/` as template-owned files, linked from the locations agents read skills from. An agent session, including a cloud session working only from the clone, can't follow a reference to a skill in another repo, so the files themselves have to be in the repo. A consumer gets skill updates as template updates, with no APM tooling of its own, and can still manage its own skills beside the template's.
- **The LID coherence gate is always on.** `lidc check` runs in commit-time hooks and in CI, as it does across the system.
- **Onboarding an existing repo.** The repo's existing violations are fixed, or recorded as named exceptions, before or as part of the first `copier copy`, so the first CI run passes. The LLD defines how the exceptions are generated.

## Target Users

- **Python repos, new or existing,** from small stdlib CLIs upward, whose developers want the system's strict baseline.
- **Agents working in those repos.** They rely on the checks being present and strict, and they record any exception as a named exception rather than weakening the base.

## Goals

- `copier copy` plus a push gives a repo green CI on its first run, given code that passes the strict baseline or has its exceptions recorded.
- `copier update` to a new release completes without conflicts when the repo has edited only repo-owned files.
- `mise run check` runs every check locally. Commit-time hooks run the fast subset.
- ty runs at one pinned version with every rule at error level. ruff runs from `select = ["ALL"]` minus a commented list of exclusions.
- Every named exception in a consumer repo can be found with one documented search.

## Non-Goals

- **Package scaffolding:** no `src/` layout, CLI skeleton, docs site, release or publishing workflow.
- **Other languages and documentation tooling.** Those are separate template layers, each with its own answers file.
- **The instruction file (`AGENTS.md` / `CLAUDE.md`).** LID's `/update-lid` owns it, and a template-owned copy would conflict with every LID upgrade. The template doesn't render it at all. *Alternatives:* render a thin starting file once as repo-owned; or, later, provide template-owned fragments that `AGENTS.md` includes.
- **Tool choices per repo.** A repo can't swap ruff or ty for another tool through this template.

## Tenets

The system tenets apply. One more, local to templates:

1. **Clean updates over a rich first render.** Prefer the file shape that keeps later updates conflict-free, even when it makes the first render less convenient.

## System Design

Files rendered into a consumer repo, by owner. Template-owned files live in `.config/copier-python/`, linked from wherever a tool requires them. The [baseline files](intent/baseline-files/baseline-files-design.md) LLD holds the full table and the onboarding procedure.

| File | Owner | Purpose |
|---|---|---|
| `.copier-answers.python.yml` | copier | Answers and the template version, at the root where Renovate runs copier |
| `.config/copier-python/ruff.toml` | template | The strict baseline: `select = ["ALL"]` minus formatter conflicts, plus test relaxations |
| `.config/copier-python/ty.toml` | template | Every rule at error level, found through `TY_CONFIG_FILE`. Exceptions are inline `ty: ignore[rule]` comments in code |
| `.config/copier-python/uv.toml` | template | A 3-day `exclude-newer` delay for lock-file updates, linked from a root `uv.toml` |
| `.config/copier-python/mise.toml` | template | Pinned uv, ruff, ty, prek and `lidc`, plus the check tasks, linked from `.config/mise/conf.d/` |
| `.config/copier-python/prek.toml` | template | Commit-time hooks, each running a mise task |
| `.config/copier-python/.claude/skills/<name>/` | template | Each skill in agentic_development's skills package, as deployed by APM in the template repo |
| `.claude/skills/<name>`, `.agents/skills/<name>` | template | A link to each of the template's skills, for Claude Code and for agents that read the cross-tool location |
| `.ruff.toml` | repo | Extends the base. Per-file named exceptions live here |
| `.config/mise/config.toml` | repo | Repo-specific tools and the `check-extra` and `hooks-extra` overrides |
| `.github/workflows/ci.yml` | repo | A short stub that calls the shared check workflow at a tag (rendered for the `github` forge) |
| `.github/workflows/lock-refresh.yml` | repo | A short stub that calls the shared lock-refresh workflow at a tag, so template updates arrive with a refreshed `mise.lock` (rendered for the `github` forge when the repo gives its lock-refresh App's client ID) |
| `.github/renovate.json` | repo | Extends the shared preset at a tag (rendered for the `github` forge) |
| `docs/arrows/index.yaml` | repo | The minimal file `lidc` requires |

```mermaid
sequenceDiagram
  participant T as template
  participant R as Renovate
  participant C as repo
  T->>R: new tag
  R->>C: copier update
  R->>C: PR, automerge on
  C->>C: CI passes, PR merges
```

1. Renovate sees a new copier-python tag through its git-tags datasource.
2. It runs `copier update --vcs-ref <tag>` without `--trust`. Template-owned files are re-rendered, the repo's edits to them are replayed, and repo-owned files are left alone.
3. It pushes an update branch and opens a PR with automerge enabled.
4. CI runs on the push, and GitHub merges the PR once the required check passes.

Skill updates take one more step, in this repo: Renovate's apm manager bumps the skills package pin in the template's APM manifest, runs `apm install` beside it, and commits the redeployed skill files with the lock file. The next template tag carries them to consumers through the flow above. A package release that adds or removes a skill also needs its links added or removed by hand, and this repo's tests fail the PR until they match.

**Testing the template.** The template's tests render it with copier's Python API into temporary repos. Each test checks one ownership rule:
- a fresh copy passes `mise run check` on a small sample package;
- an update from one tagged version to the next keeps edits to repo-owned files and applies new template-owned content without conflicts;
- a template-owned file edited by hand produces the expected merge, not silent loss.

## Key Design Decisions

- **Built here, borrowing from published templates.** The surveyed Python copier templates (copier-astral, copier-uv, substrate, ss-python and others) all copy their CI workflows instead of referencing them. The two read in source leave ty unpinned or non-strict and need `--trust` for Jinja extensions. Borrowed: copier-uv's strict ruff base with a curated ignore list, and copier-astral's pytest rendering tests, extended with update tests, which neither has.
- **ruff `extend` for the base; inline suppressions for ty.** ruff's `extend` takes only a local path, so the base is copied into the repo and the thin top file inherits from it. ty has no `extends` mechanism, and per-path `[[overrides]]` would mean editing the template-owned file, so per-line suppressions carry ty's exceptions. *Alternative:* render ty overrides from a copier answer. That would put exceptions in the answers file, far from the code they excuse.
- **Skills through the template's own APM manifest.** The skills package is pinned in `template/.config/copier-python/apm.yml`, so Renovate runs `apm install` in that directory and the skills deploy into the template's `.config/copier-python/.claude/skills/`, where the directory itself says they come from the template. copier excludes APM's own files (the manifest, its lock file, `apm_modules/` and the `.gitignore` APM writes beside the manifest), so consumers receive only the skills. In every repo, `.claude/skills/` and `.agents/skills/` are real directories of skills, each skill either a link or, for one a repo deploys with APM, real files. The template contributes a link in each to each of its skills, and a skill developed in the repo lives in its own `skills/<name>/`, linked from both. *Alternatives:*
  - each consumer pins the package in its own `apm.yml` (a second update channel per repo, and `apm install` under Renovate in every consumer);
  - deployed files gitignored and installed by a SessionStart hook (cloud sessions have no `apm`, so every session pays for an install);
  - a plugin marketplace in the repo's Claude Code settings (cloud sessions don't install those plugins);
  - the template's skills as real files in `.claude/skills/` (no links to keep in step with the package, but nothing marks those skills as the template's, and they read differently from a repo's own linked skills);
  - `.agents/skills` as one link to `.claude/skills` (no second set of links, but a repo can't then keep a skill for other agents only, and the directory isn't its own).
- **One template for now, not layered.** Base concerns (hooks, mise, Renovate stubs) stay in this template until a second language or documentation layer needs them. Then a `copier-base` layer is split out, and consumers move to two answers files. The skills pin is language-neutral, so it moves to that layer too.
- **The template repo doesn't consume itself yet.** Its own tooling is configured by hand at first. Applying the template to its own repo, as GitLab's infra template does, waits until the first release is stable.

**The tooling repos' own checks.** This repo isn't a template consumer yet. It has its own hand-written CI workflow, which runs `mise run check` from a root `mise.toml`, with the same strict profile and blocking `lidc` gate that consumers get. Its Renovate config extends agentic_development's shared preset. The shared check workflow isn't used here, because it requires `check` to come from `.config/mise/conf.d/`, which is reserved for template links and ignored by the preset. Its `.ruff.toml` excludes `template/` (whose `.ruff.toml` only works in consumers) and `tests/fixtures/`, and the `lint` task checks `template/.config/copier-python/exceptions.py` explicitly with `--config .ruff.toml`, which relies on ruff's `force-exclude` staying off. It pins `apm`, and its check fails when the skills committed under `template/` no longer match their lock file. Its ty config excludes those skills (`template/.config/copier-python/.claude`), whose scripts are checked in the skills package's own repo and may import packages this repo doesn't install. This changes once the template applies itself to its own repo.

## Success Metrics

- Renovate update PRs for this template merge automatically, without conflicts, in every consumer that has edited only repo-owned files.
- Each consumer's count of named exceptions goes down over time.
- The template's tests catch a broken render or a conflicting update before a tag is pushed.

## References

- System HLD: [agentic_development](https://github.com/jmbowman/agentic_development) `docs/high-level-design.md`.
- [copier configuration](https://copier.readthedocs.io/en/stable/configuring/); [ruff `extend`](https://docs.astral.sh/ruff/settings/#extend); [ty configuration](https://docs.astral.sh/ty/reference/configuration/); [ty suppression comments](https://docs.astral.sh/ty/suppression/); [prek configuration](https://prek.j178.dev/configuration/).
- Prior art: [copier-uv](https://github.com/pawamoy/copier-uv) (ISC), [copier-astral](https://github.com/ritwiktiwari/copier-astral) (MIT).
