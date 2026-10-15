# copier-python

A [copier](https://copier.readthedocs.io) template that adds a strict Python baseline to a repo:
ruff with every rule on, ty with every rule as an error, prek commit hooks, mise tasks, a CI stub
calling the shared [agentic_development](https://github.com/jmbowman/agentic_development) check
workflow, and a Renovate config that keeps all of it current. Template-owned files live in
`.config/copier-python/`; the design is in `docs/`.

## Preconditions

The repo already has:

- a `pyproject.toml` with `requires-python`;
- a committed `uv.lock`;
- pytest in a dependency group or optional extra;
- at least one test.

## Onboarding an existing repo

1. Check for files the template would shadow or skip, and move their content first: an existing
   `.ruff.toml`, `.config/mise/config.toml`, `.github/workflows/ci.yml`,
   `.github/workflows/lock-refresh.yml` or `.github/renovate.json`;
   a root `ruff.toml` or `[tool.ruff]` table; a root `mise.toml`; a root `renovate.json` or
   `.renovaterc*`; `[tool.ty]` and `[tool.uv]` tables; a `.pre-commit-config.yaml`.
2. Render from a release tag, never an untagged commit:
   `copier copy --vcs-ref vX.Y.Z https://github.com/jmbowman/copier-python.git .`
3. Run `mise trust`, then `mise run setup` to install the tools and the git hook.
4. Run `mise run fix` for ruff's automatic fixes and formatting. Fix what remains, or record each
   finding as a named exception: `ruff check --add-noqa`, an entry in `.ruff.toml`'s
   `[lint.extend-per-file-ignores]` table, or `mise exec -- ty check --add-ignore`.
   `mise run exceptions` lists them all.
5. Optionally, but recommended: run `mise lock` and commit `.config/mise/mise.lock` and any
   sidecar files under `.config/mise/locks/`, so tools' indirect dependencies change only through
   a PR that CI tests.
6. Run `mise run check` until it passes, then commit everything as one onboarding commit.
7. In the repo's GitHub settings, enable "Allow auto-merge" and add a branch rule on the default
   branch that requires the CI check, so Renovate's update PRs merge only after CI passes.
8. If the repo commits `mise.lock`, template updates need their lock files refreshed:
   - install a GitHub App on the repo with the repository permission Contents: read and write
     (and nothing else);
   - add its private key as the repository secret `LOCK_REFRESH_APP_PRIVATE_KEY`;
   - give its client ID as the `lock_refresh_app_client_id` answer, at render time or later with
     `copier update --data lock_refresh_app_client_id=<client ID>`, which adds the
     `.github/workflows/lock-refresh.yml` stub.

## Setting up a fresh clone

Run `mise trust`, then `mise run setup`.

## Updates

Renovate opens a PR for each template release and runs `copier update`. Template-owned files are
re-rendered; repo-owned files (`.ruff.toml`, `.config/mise/config.toml`, the `.github/` stubs,
`docs/arrows/index.yaml`) stay as the repo left them. Add checks by overriding `check-extra` or
`hooks-extra` in `.config/mise/config.toml`; don't edit files under `.config/copier-python/`.

## License

[Apache License 2.0](LICENSE).
