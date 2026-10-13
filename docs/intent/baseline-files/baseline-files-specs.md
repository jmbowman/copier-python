# Baseline files specs

Design: [baseline-files-design.md](baseline-files-design.md). "A consumer" is a repo the copier-python template is rendered into. "Template-owned" files are re-rendered on update; "repo-owned" files are rendered once and listed in `_skip_if_exists`. "A newer template tag" is a later tag that the test suite creates on a modified copy of the template. "The sample project" is the strict-clean fixture in `tests/fixtures/sample/`.

## Template configuration

- [x] **FILES-001**: The copier-python template's `copier.yml` shall set `_subdirectory` to `template`, `_answers_file` to `.copier-answers.python.yml` and `_preserve_symlinks` to `true`.
- [x] **FILES-002**: The copier-python template shall define no copier tasks, migrations or Jinja extensions, so that `copier copy` and `copier update` succeed without `--trust`.
- [x] **FILES-003**: The copier-python template's rendering and update tests shall run on the copier version given by `_min_copier_version`.
- [x] **FILES-004**: The copier-python template's rendering and update tests shall run on the copier version recorded in this repo's `uv.lock`.
- [x] **FILES-005**: The copier-python template's `_skip_if_exists` shall list `.ruff.toml`, `.config/mise/config.toml` and `docs/arrows/index.yaml`, and, where `forge` is `github`, `.github/workflows/ci.yml` and `.github/renovate.json`, and no other path.
- [x] **FILES-006**: The copier-python template shall store `template/.config/copier-python/mise.toml` without the `.jinja` suffix, so that copier copies it verbatim.
- [x] **FILES-007**: The copier-python template shall define `agentic_development_ref` as a constant (a question with `when: false`) holding an agentic_development release tag.
- [x] **FILES-009**: No file under the copier-python repo's `template/` directory shall contain an `@spec` annotation.
- [x] **FILES-008**: The copier-python repo's own Renovate config shall define a custom regex manager, with datasource `github-tags` and package `jmbowman/agentic_development`, whose pattern matches the `default:` line of `agentic_development_ref` in `copier.yml` and captures its tag.

## Questions

- [x] **FILES-Q-001**: The copier-python template shall ask `forge`, a choice with the single value `github`, defaulting to `github`.
- [x] **FILES-Q-002**: The copier-python template shall ask `line_length`, an integer defaulting to `100`.
- [x] **FILES-Q-003**: The copier-python template shall ask `copyright_notice_regex`, a string defaulting to empty.
- [x] **FILES-Q-004**: The copier-python template shall ask no question other than `forge`, `line_length` and `copyright_notice_regex`.

## Rendered layout

- [x] **FILES-LAYOUT-001**: When the copier-python template is rendered, it shall write `mise.toml`, `ruff.toml`, `ty.toml`, `prek.toml`, `uv.toml` and `exceptions.py` as regular files in the consumer's `.config/copier-python/`.
- [x] **FILES-LAYOUT-002**: When the copier-python template is rendered, it shall create `.config/mise/conf.d/copier-python.toml` as a symlink to `../../copier-python/mise.toml`.
- [x] **FILES-LAYOUT-003**: When the copier-python template is rendered, it shall create `uv.toml` in the consumer's root as a symlink to `.config/copier-python/uv.toml`.
- [x] **FILES-LAYOUT-004**: When the copier-python template is rendered into an empty directory, the only regular files or symlinks it writes directly in that directory shall be `.copier-answers.python.yml`, `.ruff.toml` and the `uv.toml` symlink.
- [x] **FILES-LAYOUT-005**: Where `forge` is `github`, the copier-python template shall render `.github/workflows/ci.yml` and `.github/renovate.json`.

## Rendered content

- [x] **FILES-CONTENT-001**: The `.config/copier-python/uv.toml` rendered by the copier-python template shall set `exclude-newer = "3 days"` and nothing else.
- [x] **FILES-CONTENT-002**: The `.ruff.toml` rendered by the copier-python template shall parse as TOML equal to `extend = ".config/copier-python/ruff.toml"` plus an empty `[lint.extend-per-file-ignores]` table.
- [x] **FILES-CONTENT-003**: The `.config/mise/config.toml` rendered by the copier-python template shall parse as empty TOML and contain a comment naming the `check-extra` and `hooks-extra` tasks as the ones to override there.
- [x] **FILES-CONTENT-004**: The `docs/arrows/index.yaml` rendered by the copier-python template shall parse as YAML equal to `schema_version: 2` with an empty `arrows` map.
- [x] **FILES-CONTENT-005**: Where `forge` is `github`, the `.github/workflows/ci.yml` rendered by the copier-python template shall trigger only on `push` with `branches: ["**"]`, and its single job shall call `jmbowman/agentic_development/.github/workflows/check.yml@<agentic_development_ref>` with no `with` inputs.
- [x] **FILES-CONTENT-006**: Where `forge` is `github`, the `.github/renovate.json` rendered by the copier-python template shall parse as JSON equal to an object whose only key, `extends`, lists `github>jmbowman/agentic_development//renovate/default#<agentic_development_ref>`.
- [x] **FILES-CONTENT-007**: When a consumer is rendered with `copier copy --vcs-ref <tag> <source>`, the `.copier-answers.python.yml` written by the copier-python template shall record `<source>` as `_src_path` and `<tag>` as `_commit`.

## Rendering a sample project

- [x] **FILES-RENDER-001**: When the copier-python template is rendered with default answers into a copy of the sample project (a git repository with its files committed, a `pyproject.toml` with `requires-python`, a committed `uv.lock`, pytest in a dependency group, and at least one test, all clean under the strict profile), then `mise trust` followed by `mise run check` in that copy shall exit 0.

## Updating

- [x] **FILES-UPD-001**: When a consumer is updated to a newer template tag, `copier update` shall leave every existing repo-owned file byte-identical.
- [x] **FILES-UPD-008**: When a consumer that deleted a repo-owned file is updated to a newer template tag, `copier update` shall recreate that file with the newer tag's starting content.
- [x] **FILES-UPD-002**: When a consumer whose only edits are to repo-owned files is updated to a newer template tag, `copier update` shall finish without conflict markers, and every template-owned file shall match the newer tag's rendering.
- [x] **FILES-UPD-003**: When a consumer that edited a template-owned file is updated to a newer template tag that doesn't change the edited lines, `copier update` shall keep the edit.
- [x] **FILES-UPD-004**: When a consumer that deleted a template-owned file is updated to a newer template tag, `copier update` shall not recreate the file.
- [x] **FILES-UPD-005**: When a consumer is updated to a newer template tag, `copier update` shall keep every symlink the copier-python template renders as a symlink with the same target.
- [x] **FILES-UPD-006**: If a consumer's edit to a template-owned file overlaps a change in the newer template tag, then `copier update` shall leave inline conflict markers in that file, and the consumer's `mise run conflicts` shall fail.
- [x] **FILES-UPD-007**: When a copy of the sample project, rendered from one test-created template tag, is updated to a later synthetic tag with `copier update --skip-answered --defaults` (the command Renovate runs), its `mise run check` shall still exit 0.

## Documentation

- [x] **FILES-DOC-001**: The copier-python template's README shall have a section for each of: preconditions; onboarding (checking for shadowed files, rendering from a tag, trust and setup, fixing or recording findings, committing, and enabling "Allow auto-merge" with a branch rule requiring the CI check); and setting up a fresh clone.
