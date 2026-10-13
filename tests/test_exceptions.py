"""Tests of the `exceptions` scanner rendered into consumers."""

from __future__ import annotations

import subprocess
import sys
from typing import TYPE_CHECKING

from tests.support import commit_all, consumer_repo, task_commands

if TYPE_CHECKING:
    from pathlib import Path

SCANNER = ".config/copier-python/exceptions.py"


def _scan(template: Path, tmp_path: Path, files: dict[str, str]) -> tuple[int, list[str]]:
    consumer = consumer_repo(template, tmp_path / "consumer")
    for name, content in files.items():
        path = consumer / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
    commit_all(consumer, "files")
    completed = subprocess.run(  # noqa: S603
        [sys.executable, SCANNER], cwd=consumer, capture_output=True, text=True, check=False
    )
    return completed.returncode, completed.stdout.splitlines()


def _total(lines: list[str]) -> int:
    totals = [line for line in lines if line.startswith("Total: ")]
    assert len(totals) == 1, lines
    return int(totals[0].removeprefix("Total: "))


# @spec STRICT-EXC-002, STRICT-EXC-005, CHECKS-TASK-012
def test_counts_each_rule_in_each_comment(template: Path, tmp_path: Path) -> None:
    """Each rule code in noqa, ruff-noqa and ty-ignore comments counts once, with its location."""
    code, lines = _scan(
        template,
        tmp_path,
        {
            "pkg/a.py": (
                "# ruff: noqa: D100\n"
                "import os  # noqa: F401, E401\n"
                "x: int = 'a'  # ty: ignore[invalid-assignment, unused-ignore-comment]\n"
                "y = 1  #NOQA:E501\n"
            )
        },
    )
    assert code == 0
    assert "pkg/a.py:1: D100" in lines
    assert "pkg/a.py:2: F401" in lines
    assert "pkg/a.py:2: E401" in lines
    assert "pkg/a.py:3: invalid-assignment" in lines
    assert "pkg/a.py:3: unused-ignore-comment" in lines
    assert "pkg/a.py:4: E501" in lines
    assert _total(lines) == 6


# @spec STRICT-EXC-001, STRICT-EXC-007
def test_skips_the_template_directory(template: Path, tmp_path: Path) -> None:
    """The template's own files in `.config/copier-python/` are never scanned or counted."""
    _code, lines = _scan(template, tmp_path, {})
    assert not any(line.startswith(".config/copier-python") for line in lines), lines
    assert _total(lines) == 0


# @spec STRICT-EXC-002
def test_counts_every_noqa_form_ruff_accepts(template: Path, tmp_path: Path) -> None:
    """Space-separated codes and flake8-style file-level exemptions count like the others."""
    _code, lines = _scan(
        template,
        tmp_path,
        {"pkg/e.py": "# flake8: noqa: F401\nimport os  # noqa: E501 W291\n"},
    )
    assert "pkg/e.py:1: F401" in lines
    assert "pkg/e.py:2: E501" in lines
    assert "pkg/e.py:2: W291" in lines
    assert _total(lines) == 3


# @spec STRICT-EXC-001
def test_reads_comments_only(template: Path, tmp_path: Path) -> None:
    """Text that merely looks like a suppression inside strings and docstrings is ignored."""
    _code, lines = _scan(
        template,
        tmp_path,
        {"pkg/b.py": '"""Mentions # noqa: E501 in a docstring."""\nTEXT = "# ty: ignore[x]"\n'},
    )
    assert _total(lines) == 0


# @spec STRICT-EXC-001
def test_scans_stub_files_and_skips_untracked(template: Path, tmp_path: Path) -> None:
    """Tracked `.pyi` files are scanned; untracked Python files are not."""
    consumer = consumer_repo(template, tmp_path / "consumer")
    (consumer / "pkg").mkdir()
    (consumer / "pkg" / "c.pyi").write_text("def f() -> int: ...  # noqa: ANN201\n")
    commit_all(consumer, "stub")
    (consumer / "pkg" / "untracked.py").write_text("import os  # noqa: F401\n")
    completed = subprocess.run(  # noqa: S603
        [sys.executable, SCANNER], cwd=consumer, capture_output=True, text=True, check=False
    )
    lines = completed.stdout.splitlines()
    assert "pkg/c.pyi:1: ANN201" in lines
    assert _total(lines) == 1


# @spec STRICT-EXC-003, STRICT-EXC-004, STRICT-EXC-005
def test_counts_ruff_file_settings(template: Path, tmp_path: Path) -> None:
    """Per-file entries count per rule; other keys count per list entry or once for a scalar."""
    _code, lines = _scan(
        template,
        tmp_path,
        {
            ".ruff.toml": (
                'extend = ".config/copier-python/ruff.toml"\n'
                "line-length = 120\n"
                "[lint]\n"
                'extend-ignore = ["ERA001", "TD003"]\n'
                "[lint.extend-per-file-ignores]\n"
                '"scripts/*.py" = ["T201", "INP001"]\n'
            )
        },
    )
    assert ".ruff.toml: lint.extend-per-file-ignores: scripts/*.py: T201" in lines
    assert ".ruff.toml: lint.extend-per-file-ignores: scripts/*.py: INP001" in lines
    assert ".ruff.toml: line-length: 120" in lines
    assert ".ruff.toml: lint.extend-ignore: ERA001" in lines
    assert ".ruff.toml: lint.extend-ignore: TD003" in lines
    assert _total(lines) == 5


# @spec STRICT-EXC-006
def test_lists_dead_type_ignores_after_the_total(template: Path, tmp_path: Path) -> None:
    """`# type: ignore` comments are listed as dead suppressions and not counted."""
    _code, lines = _scan(template, tmp_path, {"pkg/d.py": "x: int = 'a'  # type: ignore\n"})
    assert _total(lines) == 0
    heading = lines.index("Dead suppressions:")
    assert heading > lines.index("Total: 0")
    assert "pkg/d.py:1" in lines[heading + 1 :]


# @spec STRICT-EXC-007
def test_counts_nested_ruff_configs(template: Path, tmp_path: Path) -> None:
    """Each tracked ruff config below the root counts once."""
    _code, lines = _scan(
        template,
        tmp_path,
        {
            "sub/ruff.toml": "line-length = 200\n",
            "other/pyproject.toml": '[project]\nname = "o"\n[tool.ruff]\nline-length = 200\n',
            "plain/pyproject.toml": '[project]\nname = "p"\n',
        },
    )
    assert "sub/ruff.toml: nested ruff config" in lines
    assert "other/pyproject.toml: nested ruff config" in lines
    assert not any(line.startswith("plain/pyproject.toml") for line in lines)
    assert _total(lines) == 2


# @spec STRICT-EXC-008
def test_reports_untokenizable_files(template: Path, tmp_path: Path) -> None:
    """A tracked Python file that can't be tokenized is listed and not counted."""
    code, lines = _scan(template, tmp_path, {"pkg/broken.py": 'x = """unterminated\n'})
    assert code == 0
    assert "pkg/broken.py: unreadable" in lines
    assert _total(lines) == 0


# @spec STRICT-EXC-008, CHECKS-TASK-012
def test_reports_tracked_files_missing_from_the_working_tree(
    template: Path, tmp_path: Path
) -> None:
    """A tracked file deleted before committing is listed as unreadable, and the scan exits 0."""
    consumer = consumer_repo(template, tmp_path / "consumer")
    (consumer / "gone.py").write_text("x = 1\n")
    commit_all(consumer, "add")
    (consumer / "gone.py").unlink()
    completed = subprocess.run(  # noqa: S603
        [sys.executable, SCANNER], cwd=consumer, capture_output=True, text=True, check=False
    )
    assert completed.returncode == 0, completed.stderr
    assert "gone.py: unreadable" in completed.stdout.splitlines()


# @spec CHECKS-TASK-012
def test_task_runs_the_scanner_with_uv(consumer: Path) -> None:
    """The `exceptions` task runs the scanner without the project's environment."""
    assert task_commands(consumer, "exceptions") == [f"uv run --no-project {SCANNER}"]
