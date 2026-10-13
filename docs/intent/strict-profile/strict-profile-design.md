---
parent: high-level-design
prefix: STRICT
---

# Strict profile

## Context and Design Philosophy

The template turns on every rule each checker offers and switches off only what can't coexist: rules that conflict with the formatter, and pairs of rules that contradict each other. Style judgments that a reasonable project might make either way are left on, and a repo that disagrees records the exception by name. The base never encodes one repo's taste, and every relaxation is visible.

## ruff base (`.config/copier-python/ruff.toml`)

- `lint.select = ["ALL"]`.
- `lint.ignore` holds only:
  - the selected rules that ruff's formatter documentation lists as conflicting with formatting: `W191`, `E111`, `E114`, `E117`, `D206`, `D300`, `Q000`–`Q004`, `COM812`, `COM819` and `ISC002`;
  - `CPY001`, unless the `copyright_notice_regex` answer is set, in which case it is enabled with `lint.flake8-copyright.notice-rgx`.
- `lint.pydocstyle.convention = "google"`. This also disables the docstring rules that contradict Google style, `D203` among them.
- `lint.per-file-ignores` for test files (`../../**/tests/**`, `../../**/test_*.py`, `../../**/conftest.py`; ruff resolves these patterns from the base file's directory, so the `../../` prefix makes them start at the repo root) holds only `S101` (assert) and `PLR2004` (magic values in comparisons), which every pytest suite triggers by design.
- `line-length` comes from the `line_length` answer (default 100) and applies to both the formatter and `E501`. `E501` stays on: the formatter can't shorten long strings or comments, so those are fixed by hand or excepted.
- Other formatter settings stay at their defaults.

- The base excludes `.config/copier-python/` from ruff, and the ty config excludes it from ty. ruff resolves the base's `extend-exclude = ["."]` from the base file's own directory, while ty resolves `[src] exclude` from the project root, so the ty config names `.config/copier-python`. The template's own files there (such as `exceptions.py`) are checked in the template repo, and they can't satisfy every consumer's answers (a consumer's copyright notice, for example).

Each ignored rule carries a one-line comment naming why.

## ty (`.config/copier-python/ty.toml`)

- `[rules] all = "error"`. This includes `blanket-ignore-comment`, so a `# ty: ignore` without a rule code is an error (the rule exists from ty 0.0.57; the template pins a newer ty).
- `[analysis] respect-type-ignore-comments = false`, so `# type: ignore` has no effect and `# ty: ignore[<rule>]` is the only suppression.

ty finds this file through `TY_CONFIG_FILE`, which the mise fragment sets for every task and mise-activated shell. Its settings take precedence over a `[tool.ty]` table in `pyproject.toml` (verified with ty 0.0.84), so a repo can't loosen ty by accident there.

## Named exceptions

A repo relaxes the profile only in these forms, each scoped as narrowly as the tool allows:

| Form | Where | Scope |
|---|---|---|
| `# noqa: <RULE>[, <RULE>]` | the offending line | one line, listed rules |
| `# ruff: noqa: <RULE>` | top of a file | one file, listed rules |
| `# ty: ignore[<rule>][, <rule>]` | the offending line | one line, listed rules |
| `[lint.extend-per-file-ignores]` | the repo's `.ruff.toml` | one path pattern, listed rules |

Blanket forms aren't allowed:
- ruff's `PGH004` rejects a bare `# noqa` and a bare file-level `# ruff: noqa` (verified);
- `RUF100` flags `noqa` comments that no longer suppress anything;
- ty's `blanket-ignore-comment` rejects a rule-less `ty: ignore`.

A repo's `.ruff.toml` holds `extend` and `[lint.extend-per-file-ignores]` and nothing else. Any other key there, top-level or under `[lint]` (such as `line-length`, `exclude`, `extend-exclude`, `lint.ignore`, `lint.extend-ignore`, `lint.select` or `lint.per-file-ignores`), is also a relaxation, and `exceptions` reports it.

**How `exceptions` counts.**
- It skips `.config/copier-python/`, whose files belong to the template. It scans tracked `*.py` and `*.pyi` files, the repo's `.ruff.toml`, and any other tracked ruff config (`ruff.toml`, `.ruff.toml` or `pyproject.toml` with a `[tool.ruff]` table) below the root, each of which counts as one exception. A Python file that fails to tokenize is listed as `<path>: unreadable` and not counted. In Python files it reads comments only, using Python's tokenizer, so text inside strings and docstrings never counts, and a line with both a `noqa` and a `ty: ignore` comment counts both.
- It counts one exception per rule per site. `# noqa: A, B` counts two, matched the way ruff matches them (case-insensitive, optional whitespace); one `extend-per-file-ignores` pattern with three rules counts three; any other leaf key in `.ruff.toml` (a dotted path at any depth, such as `lint.ignore` or `format.quote-style`) counts one per list entry, or one if its value isn't a list.
- `# type: ignore` comments, which have no effect under this profile, are listed separately as dead suppressions to delete.
- It prints one line per counted exception: `<path>:<line>: <RULE>` for a comment, `.ruff.toml: lint.extend-per-file-ignores: <pattern>: <RULE>` for a per-file entry, and `.ruff.toml: <dotted key>: <entry or value>` for any other setting, then `Total: <n>`, then a `Dead suppressions:` section listing `# type: ignore` comments as `<path>:<line>`.

## Decisions & Alternatives

| Decision | Chosen | Alternatives Considered | Rationale |
|---|---|---|---|
| ruff starting point | `ALL` minus formatter conflicts and contradictions | copier-uv's curated ignore list (about 20 style rules off, such as `EM101`, `TRY003`, `PLR0913` and `C901`) | Tenet 3: style choices stay on unless a repo records an exception. The curated list encodes another project's taste |
| Line length | 100 by default, set per repo through a copier answer, with `E501` on | ruff's default of 88; `E501` off | 88 wraps too eagerly for modern screens. `E501` isn't a formatter conflict, and long strings and comments are exactly what the formatter can't fix |
| Docstring convention | Google, with docstring rules on everywhere, tests included | Docstrings off in tests; no convention | Tenet 3: documenting every function, test scenarios included, is the strict default, and a project that wants less records exceptions. Google style is the common Python convention |
| Test relaxations in the base | `S101` and `PLR2004` only | copier-uv's set (also `ARG005`, `FBT001`) | Asserts and literal comparisons are how pytest works. Anything beyond that is per-repo |
| ty suppressions | `ty: ignore[rule]` only | Also honor `# type: ignore` | One searchable form makes exceptions countable, and stops a rule-less `# type: ignore` from silencing a whole line |
| Per-file ruff exceptions in the repo | `extend-per-file-ignores` | `per-file-ignores` | Setting `per-file-ignores` in the top file replaces the base's test relaxations instead of adding to them (verified) |

## Open Questions & Future Decisions

### Resolved
1. ✅ New rules from ruff or ty upgrades. A release that adds rules under `ALL`, or raises ty's checks, fails CI on its update PR in each consumer. That PR is the work item: fix the code or record a named exception. Adopting rules in deliberate batches would trade away automerge.

### Deferred
1. A stored per-repo exception baseline, with `check` failing when the count rises without a recorded reason. Add it once two repos are onboarded.

## References

- [ruff rules](https://docs.astral.sh/ruff/rules/); [conflicting lint rules](https://docs.astral.sh/ruff/formatter/#conflicting-lint-rules); [`extend-per-file-ignores`](https://docs.astral.sh/ruff/settings/#lint_extend-per-file-ignores); [ty configuration](https://docs.astral.sh/ty/reference/configuration/); [ty rules](https://docs.astral.sh/ty/reference/rules/); [ty suppression comments](https://docs.astral.sh/ty/suppression/).
- Prior art: copier-uv's `project/config/ruff.toml.jinja` (ISC).
