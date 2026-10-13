"""Tests of the `conflicts` task's script, run directly in a rendered consumer."""

from __future__ import annotations

from typing import TYPE_CHECKING

from tests.support import commit_all, consumer_repo, run_task_commands

if TYPE_CHECKING:
    from pathlib import Path

START = "<" * 7
END = ">" * 7


def _consumer_with(tmp_path: Path, template: Path, content: str | None) -> Path:
    consumer = consumer_repo(template, tmp_path / "consumer")
    if content is not None:
        (consumer / "docs" / "notes.md").write_text(content)
        commit_all(consumer, "notes")
    return consumer


# @spec CHECKS-TASK-007
def test_passes_without_markers(template: Path, tmp_path: Path) -> None:
    """With no conflict markers, the task succeeds."""
    consumer = _consumer_with(tmp_path, template, "Heading\n=======\n")
    exit_code, output = run_task_commands(consumer, "conflicts")
    assert exit_code == 0, output


# @spec CHECKS-TASK-007
def test_fails_on_a_start_marker(template: Path, tmp_path: Path) -> None:
    """A line starting with a conflict-start marker fails the task."""
    consumer = _consumer_with(tmp_path, template, f"{START} before updating\nold\n")
    exit_code, _output = run_task_commands(consumer, "conflicts")
    assert exit_code != 0


# @spec CHECKS-TASK-007
def test_fails_on_an_end_marker_from_a_subdirectory(template: Path, tmp_path: Path) -> None:
    """The whole repo is searched, even when run from a subdirectory."""
    consumer = _consumer_with(tmp_path, template, f"new\n{END} after updating\n")
    exit_code, _output = run_task_commands(consumer, "conflicts", cwd=consumer / "docs")
    assert exit_code != 0


# @spec CHECKS-TASK-007
def test_fails_outside_a_git_repository(template: Path, tmp_path: Path) -> None:
    """If git can't search (exit 2 or more), the task fails rather than passing."""
    consumer = _consumer_with(tmp_path, template, None)
    outside = tmp_path / "not-a-repo"
    outside.mkdir()
    env = {"GIT_CEILING_DIRECTORIES": str(tmp_path)}
    exit_code, _output = run_task_commands(consumer, "conflicts", cwd=outside, env=env)
    assert exit_code != 0
