"""Tests of the `skill-links` task's script, run directly in a rendered consumer."""

from __future__ import annotations

import shutil
from typing import TYPE_CHECKING

import pytest

from tests.support import SKILL_LINK_DIRS, consumer_repo, run_task_commands

if TYPE_CHECKING:
    from pathlib import Path


# @spec CHECKS-TASK-015
def test_passes_with_the_template_links(template: Path, tmp_path: Path) -> None:
    """A freshly rendered consumer's skill links all resolve."""
    consumer = consumer_repo(template, tmp_path / "consumer")
    exit_code, output = run_task_commands(consumer, "skill-links")
    assert exit_code == 0, output


# @spec CHECKS-TASK-015
def test_passes_without_skill_directories(template: Path, tmp_path: Path) -> None:
    """A repo with neither skill directory has nothing to check."""
    consumer = consumer_repo(template, tmp_path / "consumer")
    for link_dir in SKILL_LINK_DIRS:
        shutil.rmtree(consumer / link_dir)
    exit_code, output = run_task_commands(consumer, "skill-links")
    assert exit_code == 0, output


# @spec CHECKS-TASK-015
@pytest.mark.parametrize("name", ["removed-skill", "with space", ".hidden", "..double"])
@pytest.mark.parametrize("link_dir", SKILL_LINK_DIRS, ids=str)
def test_fails_on_a_dangling_link(
    template: Path, tmp_path: Path, link_dir: Path, name: str
) -> None:
    """A link to a skill that no longer exists fails the task, which names it."""
    consumer = consumer_repo(template, tmp_path / "consumer")
    (consumer / link_dir / name).symlink_to("../../skills/removed-skill")
    exit_code, output = run_task_commands(consumer, "skill-links")
    assert exit_code != 0
    assert f"{link_dir}/{name}" in output
