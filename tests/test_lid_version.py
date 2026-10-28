"""Tests of the LID version gate, `.config/copier-python/lid_version.py`."""

from __future__ import annotations

import ast
import subprocess
import sys
from typing import TYPE_CHECKING

import pytest

from tests.support import (
    REPO_ROOT,
    SKILLS_LOCK,
    TEMPLATE_DIR,
    TEMPLATE_DIR_IN_CONSUMER,
    locked_lid_version,
)

if TYPE_CHECKING:
    from pathlib import Path

GATE = TEMPLATE_DIR / TEMPLATE_DIR_IN_CONSUMER / "lid_version.py"

LID_ENTRY = """\
- repo_url: jszmajda/lid
  name: linked-intent-dev
  resolved_ref: v1.4.0
  version: {version}
  virtual_path: plugins/linked-intent-dev
  deployed_files:
  - .claude/skills/linked-intent-dev
  - .claude/skills/linked-intent-dev/SKILL.md
"""
OTHER_ENTRY = """\
- repo_url: jmbowman/agentic_development
  name: agentic-development
  version: 0.0.0
  deployed_files:
  - .claude/skills/prior-art-search
"""


def _lock(*entries: str) -> str:
    return "lockfile_version: '1'\napm_version: 0.35.0\ndependencies:\n" + "".join(entries)


def _instructions(version: str = "1.4.0", heading: str = "## LID") -> str:
    return f"# Repo\n\n{heading}\n- Mode: Full\n- Version: {version}\n\n## LID Tooling\n- x\n"


def _repo(
    tmp_path: Path,
    lock: str | None = None,
    agents: str | None = None,
    claude: str | None = None,
) -> Path:
    """A directory laid out like a consumer's root, holding the given files."""
    lock_path = tmp_path / SKILLS_LOCK
    lock_path.parent.mkdir(parents=True)
    if lock is not None:
        lock_path.write_text(lock)
    if agents is not None:
        (tmp_path / "AGENTS.md").write_text(agents)
    if claude is not None:
        (tmp_path / "CLAUDE.md").write_text(claude)
    return tmp_path


def _gate(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603
        [sys.executable, "-I", str(GATE), *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )


def _fails_with_one_line(completed: subprocess.CompletedProcess[str]) -> str:
    assert completed.returncode == 1, completed
    lines = completed.stderr.strip().splitlines()
    assert len(lines) == 1, completed.stderr
    return lines[0]


# @spec CHECKS-GATE-001
@pytest.mark.parametrize("bullet", ["1.4.0", " 1.4.0  ", "'1.4.0'", '"1.4.0"'])
@pytest.mark.parametrize("locked", ["1.4.0", "'1.4.0'"])
def test_matching_versions_pass(tmp_path: Path, bullet: str, locked: str) -> None:
    """Equal values pass, whitespace and quotes aside."""
    repo = _repo(tmp_path, _lock(LID_ENTRY.format(version=locked)), _instructions(bullet))
    completed = _gate(repo)
    assert completed.returncode == 0, completed.stderr


# @spec CHECKS-GATE-002
def test_a_version_mismatch_fails_naming_both(tmp_path: Path) -> None:
    """A mismatch names both versions and how to fix it."""
    repo = _repo(tmp_path, _lock(LID_ENTRY.format(version="1.5.0")), _instructions("1.4.0"))
    line = _fails_with_one_line(_gate(repo))
    assert "1.4.0" in line
    assert "1.5.0" in line
    assert "/update-lid" in line


# @spec CHECKS-GATE-003
def test_agents_md_is_read_without_falling_back(tmp_path: Path) -> None:
    """With AGENTS.md present, its block counts and CLAUDE.md is ignored."""
    lock = _lock(LID_ENTRY.format(version="1.4.0"))
    repo = _repo(tmp_path, lock, agents=_instructions("1.3.0"), claude=_instructions("1.4.0"))
    assert "1.3.0" in _fails_with_one_line(_gate(repo))


# @spec CHECKS-GATE-003
def test_claude_md_is_read_without_agents_md(tmp_path: Path) -> None:
    """Without AGENTS.md, CLAUDE.md is the instruction file."""
    repo = _repo(tmp_path, _lock(LID_ENTRY.format(version="1.4.0")), claude=_instructions())
    assert _gate(repo).returncode == 0


# @spec CHECKS-GATE-004
def test_a_longer_lid_heading_is_another_section(tmp_path: Path) -> None:
    """`## LID Tooling` is neither the block nor part of it."""
    instructions = "# Repo\n\n## LID Tooling\n- Version: 9.9.9\n\n## LID\n- Version: 1.4.0\n"
    repo = _repo(tmp_path, _lock(LID_ENTRY.format(version="1.4.0")), instructions)
    completed = _gate(repo)
    assert completed.returncode == 0, completed.stderr


# @spec CHECKS-GATE-004
def test_the_heading_must_be_exact(tmp_path: Path) -> None:
    """A `## LID` heading with trailing text or spaces doesn't start the block."""
    instructions = "## LID \n- Version: 1.4.0\n"
    repo = _repo(tmp_path, _lock(LID_ENTRY.format(version="1.4.0")), instructions)
    assert "no `## LID` blocks" in _fails_with_one_line(_gate(repo))


# @spec CHECKS-GATE-004
def test_the_block_ends_at_the_next_heading(tmp_path: Path) -> None:
    """A `- Version:` bullet after the next `## ` heading isn't in the block."""
    instructions = "## LID\n- Mode: Full\n\n## Other\n- Version: 1.4.0\n"
    repo = _repo(tmp_path, _lock(LID_ENTRY.format(version="1.4.0")), instructions)
    _fails_with_one_line(_gate(repo))


# @spec CHECKS-GATE-005
@pytest.mark.parametrize(
    "lock",
    [_lock(OTHER_ENTRY), _lock(LID_ENTRY.format(version="1.4.0") * 2)],
    ids=["none", "two"],
)
def test_lid_entry_count_must_be_one(tmp_path: Path, lock: str) -> None:
    """No LID entry, or two, fails."""
    assert "entries" in _fails_with_one_line(_gate(_repo(tmp_path, lock, _instructions())))


# @spec CHECKS-GATE-006
def test_no_instruction_file_fails(tmp_path: Path) -> None:
    """A repo with neither AGENTS.md nor CLAUDE.md fails."""
    line = _fails_with_one_line(_gate(_repo(tmp_path, _lock(LID_ENTRY.format(version="1.4.0")))))
    assert "no instruction file" in line


# @spec CHECKS-GATE-007
@pytest.mark.parametrize(
    "instructions",
    ["# Repo\n- Version: 1.4.0\n", _instructions() + "\n" + _instructions()],
    ids=["none", "two"],
)
def test_lid_block_count_must_be_one(tmp_path: Path, instructions: str) -> None:
    """No `## LID` block, or two, fails."""
    repo = _repo(tmp_path, _lock(LID_ENTRY.format(version="1.4.0")), instructions)
    assert "`## LID` blocks" in _fails_with_one_line(_gate(repo))


# @spec CHECKS-GATE-008
@pytest.mark.parametrize(
    "instructions",
    ["## LID\n- Mode: Full\n", "## LID\n- Version: 1.4.0\n- Version: 1.4.0\n"],
    ids=["none", "two"],
)
def test_version_bullet_count_must_be_one(tmp_path: Path, instructions: str) -> None:
    """No `- Version:` bullet in the block, or two, fails."""
    repo = _repo(tmp_path, _lock(LID_ENTRY.format(version="1.4.0")), instructions)
    assert "`- Version:` bullets" in _fails_with_one_line(_gate(repo))


# @spec CHECKS-GATE-009
def test_lid_entry_found_in_any_field_order(tmp_path: Path) -> None:
    """Field order and nested lists don't hide the LID entry."""
    reordered = """\
- deployed_files:
  - .claude/skills/linked-intent-dev
  - repo_url: not-a-field
  virtual_path: plugins/linked-intent-dev
  version: 1.4.0
  repo_url: jszmajda/lid
"""
    repo = _repo(tmp_path, _lock(OTHER_ENTRY, reordered), _instructions())
    completed = _gate(repo)
    assert completed.returncode == 0, completed.stderr


# @spec CHECKS-GATE-012
def test_a_missing_lock_file_fails(tmp_path: Path) -> None:
    """Without a lock file, the gate names the file it couldn't read."""
    line = _fails_with_one_line(_gate(_repo(tmp_path, None, _instructions())))
    assert "apm.lock.yaml" in line


# @spec CHECKS-GATE-012
def test_a_lock_file_that_isnt_text_fails(tmp_path: Path) -> None:
    """A lock file that isn't UTF-8 fails with one line, not a traceback."""
    repo = _repo(tmp_path, None, _instructions())
    (repo / SKILLS_LOCK).write_bytes(b"\xff\xfe\x00not text")
    assert "apm.lock.yaml" in _fails_with_one_line(_gate(repo))


# @spec CHECKS-GATE-012
def test_an_unreadable_instruction_file_fails(tmp_path: Path) -> None:
    """An instruction file the gate can't read fails with one line naming it."""
    repo = _repo(tmp_path, _lock(LID_ENTRY.format(version="1.4.0")), _instructions())
    (repo / "AGENTS.md").chmod(0)
    try:
        assert "AGENTS.md" in _fails_with_one_line(_gate(repo))
    finally:
        (repo / "AGENTS.md").chmod(0o644)


# @spec CHECKS-GATE-010
def test_options_override_the_paths(tmp_path: Path) -> None:
    """`--lock` and `--instructions` read other files, relative to the working directory."""
    repo = _repo(tmp_path, _lock(OTHER_ENTRY), _instructions("1.0.0"))
    (repo / "other").mkdir()
    (repo / "other/apm.lock.yaml").write_text(_lock(LID_ENTRY.format(version="2.0.0")))
    (repo / "other/RULES.md").write_text(_instructions("2.0.0"))
    completed = _gate(repo, "--lock", "other/apm.lock.yaml", "--instructions", "other/RULES.md")
    assert completed.returncode == 0, completed.stderr


# @spec CHECKS-GATE-013
def test_a_missing_instructions_option_file_fails(tmp_path: Path) -> None:
    """A missing `--instructions` file fails before any other file is read."""
    # No lock file either: the gate must report the instruction file, not the lock.
    repo = _repo(tmp_path, None, claude=_instructions())
    line = _fails_with_one_line(_gate(repo, "--instructions", "AGENTS.md"))
    assert "no instruction file" in line


# @spec CHECKS-GATE-009
@pytest.mark.parametrize(
    "lock", [TEMPLATE_DIR / SKILLS_LOCK, REPO_ROOT / "apm.lock.yaml"], ids=["template", "root"]
)
def test_real_lock_files_parse(tmp_path: Path, lock: Path) -> None:
    """The line reader agrees with a YAML parser on the lock files APM actually writes."""
    repo = _repo(tmp_path, lock.read_text(), _instructions(locked_lid_version(lock)))
    completed = _gate(repo)
    assert completed.returncode == 0, completed.stderr


# @spec CHECKS-GATE-011
def test_only_standard_library_imports() -> None:
    """The gate runs with `uv run --no-project`, so it imports only the standard library."""
    tree = ast.parse(GATE.read_text())
    modules = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    } | {
        node.module.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None and node.level == 0
    }
    assert modules
    assert modules <= sys.stdlib_module_names | {"__future__"}
