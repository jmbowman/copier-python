"""Tests of the `skill-links` task's script, run directly in a rendered consumer."""

from __future__ import annotations

import os
import shutil
import subprocess
from typing import TYPE_CHECKING

import pytest

from tests.support import (
    MISE_SHELL,
    SKILL_LINK_DIRS,
    consumer_repo,
    fake_skill_install,
    task_commands,
)

if TYPE_CHECKING:
    from pathlib import Path


def _run(consumer: Path) -> subprocess.CompletedProcess[str]:
    """Run the task's script (without its `skills` dependency) in the consumer's root."""
    (script,) = task_commands(consumer, "skill-links")
    return subprocess.run(  # noqa: S603
        [*MISE_SHELL, script],
        cwd=consumer,
        env=dict(os.environ),
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.fixture
def installed(template: Path, tmp_path: Path) -> Path:
    """A rendered consumer whose template skills are installed, so its links resolve."""
    consumer = consumer_repo(template, tmp_path / "consumer")
    fake_skill_install(consumer)
    return consumer


# @spec CHECKS-TASK-015
def test_passes_with_the_template_links(installed: Path) -> None:
    """Once the skills are installed, every template link resolves."""
    completed = _run(installed)
    assert completed.returncode == 0, completed.stderr


# @spec CHECKS-TASK-015
def test_passes_without_skill_directories(installed: Path) -> None:
    """A repo with neither skill directory has nothing to check."""
    for link_dir in SKILL_LINK_DIRS:
        shutil.rmtree(installed / link_dir)
    completed = _run(installed)
    assert completed.returncode == 0, completed.stderr


# @spec CHECKS-TASK-015
def test_passes_on_a_link_to_a_file(installed: Path) -> None:
    """A link that resolves to a file isn't dangling."""
    (installed / "notes.md").write_text("notes\n")
    (installed / ".claude/skills/notes").symlink_to("../../notes.md")
    completed = _run(installed)
    assert completed.returncode == 0, completed.stderr


# @spec CHECKS-TASK-015
@pytest.mark.parametrize("name", ["removed-skill", "with space", ".hidden", "..double"])
@pytest.mark.parametrize("link_dir", SKILL_LINK_DIRS, ids=str)
def test_fails_on_a_dangling_link(installed: Path, link_dir: Path, name: str) -> None:
    """A link to a skill that no longer exists fails the task, which names it on stderr."""
    (installed / link_dir / name).symlink_to("../../skills/removed-skill")
    completed = _run(installed)
    assert completed.returncode != 0
    assert f"{link_dir}/{name}" in completed.stderr


# @spec CHECKS-TASK-015
def test_fails_on_a_link_loop(installed: Path) -> None:
    """A link that points at itself never resolves."""
    (installed / ".agents/skills/loop").symlink_to("loop")
    completed = _run(installed)
    assert completed.returncode != 0
    assert ".agents/skills/loop" in completed.stderr


# @spec CHECKS-TASK-015
def test_follows_a_linked_skill_directory(installed: Path) -> None:
    """When `.claude/skills` is itself a link, its entries are checked through it."""
    real = installed / "elsewhere"
    shutil.move(installed / ".claude/skills", real)
    (installed / ".claude/skills").symlink_to("../elsewhere")
    (real / "gone").symlink_to("../../skills/gone")
    completed = _run(installed)
    assert completed.returncode != 0
    assert ".claude/skills/gone" in completed.stderr
