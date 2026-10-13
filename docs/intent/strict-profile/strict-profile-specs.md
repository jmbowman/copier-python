# Strict profile specs

Design: [strict-profile-design.md](strict-profile-design.md). "The ruff base" is the template-owned `.config/copier-python/ruff.toml`. "The ty config" is the template-owned `.config/copier-python/ty.toml`. "The repo's ruff file" is the repo-owned `.ruff.toml`.

## ruff base

- [x] **STRICT-RUFF-001**: The copier-python ruff base (`.config/copier-python/ruff.toml`) shall set `lint.select = ["ALL"]`.
- [x] **STRICT-RUFF-002**: The copier-python ruff base's `lint.ignore` shall contain `W191`, `E111`, `E114`, `E117`, `D206`, `D300`, `Q000`, `Q001`, `Q002`, `Q003`, `Q004`, `COM812`, `COM819` and `ISC002`, each on a line with a comment, and no other rule except as STRICT-RUFF-003 requires.
- [x] **STRICT-RUFF-003**: Where `copyright_notice_regex` is empty, the copier-python ruff base's `lint.ignore` shall also contain `CPY001`.
- [x] **STRICT-RUFF-004**: Where `copyright_notice_regex` is set, the copier-python ruff base shall leave `CPY001` enabled and set `lint.flake8-copyright.notice-rgx` to the answer.
- [x] **STRICT-RUFF-005**: The copier-python ruff base shall set `lint.pydocstyle.convention = "google"`.
- [x] **STRICT-RUFF-006**: The copier-python ruff base shall set `line-length` to the `line_length` answer.
- [x] **STRICT-RUFF-007**: The copier-python ruff base's `lint.per-file-ignores` shall relax only `S101` and `PLR2004`, and only for the consumer-root globs `**/tests/**`, `**/test_*.py` and `**/conftest.py`.
- [x] **STRICT-RUFF-008**: In a rendered consumer, ruff (at the copier-python fragment's pinned version) shall report `S101` for an `assert` in `pkg/module.py`, and not for one in `tests/test_x.py`, `tests/conftest.py`, `pkg/tests/test_y.py` or `pkg/tests/helpers.py`.
- [x] **STRICT-RUFF-009**: In a rendered consumer, `mise run lint` shall not report findings for files under `.config/copier-python/`.

## ty config

- [x] **STRICT-TY-001**: The copier-python ty config (`.config/copier-python/ty.toml`) shall set `[rules] all = "error"`.
- [x] **STRICT-TY-002**: The copier-python ty config shall set `[analysis] respect-type-ignore-comments = false`.
- [x] **STRICT-TY-004**: In a rendered consumer, `mise run typecheck` shall not report findings for files under `.config/copier-python/`.
- [x] **STRICT-TY-003**: In a rendered consumer whose `pyproject.toml` sets `invalid-assignment = "ignore"` under `[tool.ty.rules]`, `mise exec -- ty check` shall still report an `invalid-assignment` error.

## Blanket suppressions

- [x] **STRICT-BLANKET-001**: In a rendered consumer, a bare `# noqa` comment, or a bare file-level `# ruff: noqa` comment, shall make `mise run lint` fail.
- [x] **STRICT-BLANKET-002**: In a rendered consumer, a `# ty: ignore` comment without a rule code shall make `mise run typecheck` fail.

## Named exceptions (`exceptions` task)

- [x] **STRICT-EXC-001**: The copier-python `exceptions` task shall scan only git-tracked files outside `.config/copier-python/` ending in `.py` or `.pyi`, the repo's ruff file (`.ruff.toml`) and any other tracked ruff config file, and in Python files shall read only comments, as found by Python's tokenizer.
- [x] **STRICT-EXC-007**: The copier-python `exceptions` task shall count each tracked `ruff.toml`, `.ruff.toml`, or `pyproject.toml` with a `[tool.ruff]` table, below the repository root and outside `.config/copier-python/`, as one exception, printed as `<path>: nested ruff config`.
- [x] **STRICT-EXC-008**: If a tracked Python file can't be read (for example, deleted but still tracked) or fails to tokenize, then the copier-python `exceptions` task shall print `<path>: unreadable` and not count it.
- [x] **STRICT-EXC-002**: The copier-python `exceptions` task shall count one exception for each rule code listed in each comment that ruff treats as a coded `noqa` or file-level `ruff: noqa` (case-insensitive, with optional whitespace), and in each `ty: ignore[...]` comment.
- [x] **STRICT-EXC-003**: The copier-python `exceptions` task shall count one exception for each rule code listed under each pattern in the `[lint.extend-per-file-ignores]` table of the repo's ruff file.
- [x] **STRICT-EXC-004**: The copier-python `exceptions` task shall count, for each leaf key of the repo's ruff file (a dotted path at any depth) other than `extend` and those under `lint.extend-per-file-ignores`, one exception per list entry, or one if the value isn't a list.
- [x] **STRICT-EXC-005**: The copier-python `exceptions` task shall print one line per counted exception, as `<path>:<line>: <RULE>` for a comment, `.ruff.toml: lint.extend-per-file-ignores: <pattern>: <RULE>` for a per-file entry, or `.ruff.toml: <dotted key>: <entry or value>` for any other setting, followed by a line `Total: <n>`.
- [x] **STRICT-EXC-006**: The copier-python `exceptions` task shall list each `# type: ignore` comment as `<path>:<line>` under a `Dead suppressions:` heading, after the total, without counting it.
