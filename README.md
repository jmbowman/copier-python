# copier-python

A [copier](https://copier.readthedocs.io) template that adds a strict Python baseline to a repo:
ruff with every rule on, ty with every rule as an error, prek commit hooks, mise tasks, a CI stub
calling the shared [agentic_development](https://github.com/jmbowman/agentic_development) check
workflow, a Renovate config that keeps all of it current, agent skills (agentic_development's and
LID's), and a session hook that sets up Claude Code cloud sessions. Template-owned files live in
`.config/copier-python/`; the design is in `docs/`.

## Preconditions

The repo already has:

- a `pyproject.toml` with `requires-python`;
- a committed `uv.lock`;
- pytest in a dependency group or optional extra;
- at least one test.

The template also requires LID ([linked-intent development](https://github.com/jszmajda/lid)):
its checks fail without LID's docs and the `## LID` block in the repo's instruction file.
Onboarding sets that up for a repo that doesn't use LID yet.

## Onboarding an existing repo

1. Check for files the template would shadow or skip, and move their content first: an existing
   `.ruff.toml`, `.config/mise/config.toml`, `.github/workflows/ci.yml`,
   `.github/workflows/lock-refresh.yml` or `.github/renovate.json`;
   a root `ruff.toml` or `[tool.ruff]` table; a root `mise.toml`; a root `renovate.json` or
   `.renovaterc*`; `[tool.ty]` and `[tool.uv]` tables; a `.pre-commit-config.yaml`.
   For skills: a `.claude/skills` or `.agents/skills` that is a link rather than a directory
   (replace it with a real directory holding the same skills), and a skill with the same name as
   one of the template's (remove the repo's copy, and the package that deploys it). An existing
   `.claude/settings.json` is kept as it is: add the template's session hook entry to it by hand
   (see [Session hook](#session-hook)).
2. Render from a release tag, never an untagged commit:
   `copier copy --vcs-ref vX.Y.Z https://github.com/jmbowman/copier-python.git .`
3. Run `mise trust`, then `mise run setup` to install the tools, the template's skills and the
   git hook.
4. Run `/update-lid` in Claude Code, from the LID skills `mise run setup` installed, unless the
   instruction file (`AGENTS.md` or `CLAUDE.md`) already has a `## LID` block at the LID version
   in `.config/copier-python/apm.lock.yaml`. In a repo without LID it adds the minimum the checks
   need: the LID block,
   `docs/intent/` and a starting `docs/high-level-design.md`.
5. Run `mise run fix` for ruff's automatic fixes and formatting. Fix what remains, or record each
   finding as a named exception: `ruff check --add-noqa`, an entry in `.ruff.toml`'s
   `[lint.extend-per-file-ignores]` table, or `mise exec -- ty check --add-ignore`.
   `mise run exceptions` lists them all.
6. Optionally, but recommended: run `mise lock` and commit `.config/mise/mise.lock` and any
   sidecar files under `.config/mise/locks/`, so tools' indirect dependencies change only through
   a PR that CI tests.
7. Run `mise run check` until it passes, then commit everything as one onboarding commit.
8. In the repo's GitHub settings, enable "Allow auto-merge" and add a branch rule on the default
   branch that requires the CI check, so Renovate's update PRs merge only after CI passes.
9. If the repo commits `mise.lock`, template updates need their lock files refreshed:
   - install a GitHub App on the repo with the repository permission Contents: read and write
     (and nothing else);
   - add its private key as the repository secret `LOCK_REFRESH_APP_PRIVATE_KEY`;
   - give its client ID as the `lock_refresh_app_client_id` answer, at render time or later with
     `copier update --data lock_refresh_app_client_id=<client ID>`, which adds the
     `.github/workflows/lock-refresh.yml` stub.

## Skills

The template delivers the skills in agentic_development's skills package (such as
`prior-art-search`) and the LID skills it brings (`linked-intent-dev`, `update-lid` and
`lid-coach`). It renders an [APM](https://github.com/microsoft/apm) manifest and lock file into
`.config/copier-python/`, and `mise run setup`, the [session hook](#session-hook) in cloud sessions,
and `mise run check` install exactly what the lock file records into
`.config/copier-python/.claude/skills/`, which is gitignored. The template's committed links lead
there from `.claude/skills/`, where Claude Code reads skills, and from `.agents/skills/`, where
other agents do. Skill updates arrive with template updates: run `mise run setup` after one to
install them locally. Installing needs network access to GitHub the first time.

A repo can add skills of its own beside the template's:

- a skill developed in the repo lives in `skills/<name>/`, with links to it from
  `.claude/skills/<name>` and `.agents/skills/<name>`;
- skills from other packages: add a root `apm.yml` with `targets: [claude]` and run `apm install`
  (the template already pins `apm`). It installs them into `.claude/skills/<name>/`, which the repo
  gitignores, and commits `apm.yml` and `apm.lock.yaml`. Link an installed skill from
  `.agents/skills/<name>` (to `../../.claude/skills/<name>`) for other agents to see it.

The template's skill names are reserved: a repo's own skills mustn't reuse one.

copier never deletes a symlink, so a template release that removes or renames a skill leaves
its old links pointing nowhere. The `skill-links` check then fails the update PR; delete the
links it names and push.

## Session hook

Claude Code cloud sessions (such as claude.ai/code) start from a fresh clone with no tools. The
template's SessionStart hook, `.config/copier-python/session-start.sh`, installs mise, the pinned
tools and the template's skills there, and does nothing in local sessions. If a step fails, the
session still starts, and the agent is told what's missing. The cloud environment's network
policy has to allow GitHub (releases and git), PyPI, and the hosts of any tools the repo pins
itself.

`.claude/settings.json` registers the hook. The repo owns that file: the template writes it once,
and the repo adds its own permissions and hooks beside the entry. To opt out of the hook, remove
its entry; deleting the file would make the next template update recreate it.

## Setting up a fresh clone

Run `mise trust`, then `mise run setup`.

## Updates

Renovate opens a PR for each template release and runs `copier update`. Template-owned files are
re-rendered; repo-owned files (`.ruff.toml`, `.config/mise/config.toml`, the `.github/` stubs,
`docs/arrows/index.yaml`, `.claude/settings.json`) stay as the repo left them. An update that
moves to a new LID version fails the `lid-version` check until someone runs `/update-lid` on its
branch and pushes the result; it then merges as usual. Add checks by overriding `check-extra` or
`hooks-extra` in `.config/mise/config.toml`; don't edit files under `.config/copier-python/` or
the template's skill links.

## License

[Apache License 2.0](LICENSE).
