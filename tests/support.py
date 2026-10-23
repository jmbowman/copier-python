"""Helpers for rendering the template into temporary consumers and inspecting them."""

from __future__ import annotations

import os
import shutil
import subprocess
import tomllib
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml
from copier import run_copy, run_update

if TYPE_CHECKING:
    from collections.abc import Callable

REPO_ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_DIR = REPO_ROOT / "template"
COPIER_YML = REPO_ROOT / "copier.yml"
FIXTURES = REPO_ROOT / "tests" / "fixtures"
SAMPLE = FIXTURES / "sample"
ANSWERS_FILE = ".copier-answers.python.yml"
TEMPLATE_DIR_IN_CONSUMER = Path(".config/copier-python")
FRAGMENT = TEMPLATE_DIR_IN_CONSUMER / "mise.toml"
# Where the template's skills live, relative to `template/` and to a consumer's root.
SKILLS = TEMPLATE_DIR_IN_CONSUMER / ".claude" / "skills"
SKILL_LINK_DIRS = (Path(".claude/skills"), Path(".agents/skills"))

# How mise runs each entry of a task's `run`: POSIX sh with errexit (mise.jdx.dev/tasks/toml-tasks).
MISE_SHELL = ["sh", "-o", "errexit", "-c"]


def copier_config() -> dict[str, Any]:
    """Return this repo's parsed `copier.yml`."""
    return yaml.safe_load(COPIER_YML.read_text())


def template_skills() -> list[str]:
    """Return the names of the skills committed in this repo's template."""
    return sorted(path.name for path in (TEMPLATE_DIR / SKILLS).iterdir() if path.is_dir())


def skill_link_target(name: str) -> str:
    """Return the target of the links to skill `name` in `.claude/skills/` and `.agents/skills/`.

    Args:
        name: The skill's name.

    Returns:
        The relative link target.
    """
    return f"../../{SKILLS}/{name}"


def git(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """Run git in `cwd` with a fixed identity, failing on error.

    Args:
        cwd: The repository directory.
        *args: git arguments.

    Returns:
        The completed process.
    """
    identity = ["-c", "user.name=test", "-c", "user.email=test@example.com"]
    return subprocess.run(  # noqa: S603
        ["git", *identity, *args],  # noqa: S607
        cwd=cwd,
        capture_output=True,
        text=True,
        check=True,
    )


def commit_all(repo: Path, message: str) -> None:
    """Stage everything in `repo` and commit it.

    Args:
        repo: The repository directory.
        message: The commit message.
    """
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "--allow-empty", "-m", message)


def template_repo(dest: Path, tag: str = "v1.0.0") -> Path:
    """Copy this template into a fresh git repo at `dest` and tag it.

    Args:
        dest: Where to create the repo.
        tag: The first release tag.

    Returns:
        The repo path.
    """
    dest.mkdir(parents=True)
    shutil.copy2(COPIER_YML, dest / "copier.yml")
    # Leave out local caches: APM's download cache and Python bytecode are never committed.
    caches = shutil.ignore_patterns("apm_modules", "__pycache__")
    shutil.copytree(TEMPLATE_DIR, dest / "template", symlinks=True, ignore=caches)
    git(dest, "init", "-q")
    commit_all(dest, "template")
    git(dest, "tag", tag)
    return dest


def release(template: Path, tag: str, change: Callable[[Path], None]) -> None:
    """Apply `change` to a template repo, commit it, and tag the result.

    Args:
        template: A repo made by `template_repo`.
        tag: The new release tag.
        change: Called with the repo path to modify files.
    """
    change(template)
    commit_all(template, tag)
    git(template, "tag", tag)


def render(
    template: Path, consumer: Path, ref: str = "v1.0.0", data: dict[str, Any] | None = None
) -> Path:
    """Render `template` at `ref` into `consumer` with default answers.

    Args:
        template: A template repo.
        consumer: The destination directory.
        ref: The template tag to render.
        data: Answers overriding the defaults.

    Returns:
        The consumer path.
    """
    run_copy(str(template), consumer, data=data or {}, defaults=True, vcs_ref=ref, quiet=True)
    return consumer


def update(consumer: Path, ref: str, data: dict[str, Any] | None = None) -> None:
    """Update a committed consumer to `ref` the way Renovate does.

    Args:
        consumer: A consumer repo with everything committed.
        ref: The template tag to update to.
        data: Answers to set, as `copier update --data` does.
    """
    run_update(
        consumer,
        data=data or {},
        answers_file=ANSWERS_FILE,
        defaults=True,
        skip_answered=True,
        overwrite=True,
        vcs_ref=ref,
        quiet=True,
    )


def consumer_repo(template: Path, dest: Path, data: dict[str, Any] | None = None) -> Path:
    """Render `template` into `dest`, make it a git repo, and commit.

    Args:
        template: A template repo.
        dest: The destination directory.
        data: Answers overriding the defaults.

    Returns:
        The consumer path.
    """
    dest.mkdir(parents=True)
    git(dest, "init", "-q")
    render(template, dest, data=data)
    commit_all(dest, "render")
    return dest


def load_toml(path: Path) -> dict[str, Any]:
    """Parse a TOML file.

    Args:
        path: The file to read.

    Returns:
        The parsed document.
    """
    return tomllib.loads(path.read_text())


def fragment_tasks(consumer: Path) -> dict[str, dict[str, Any]]:
    """Return the tasks defined in a consumer's copier-python mise fragment.

    Args:
        consumer: A rendered consumer.

    Returns:
        The `[tasks]` table.
    """
    return load_toml(consumer / FRAGMENT)["tasks"]


def task_commands(consumer: Path, name: str) -> list[str]:
    """Return a fragment task's `run` entries, each of which mise runs separately.

    Args:
        consumer: A rendered consumer.
        name: The task name.

    Returns:
        The task's `run` entries (one entry when `run` is a string).
    """
    run = fragment_tasks(consumer)[name].get("run", [])
    if isinstance(run, list):
        return [str(command) for command in run]
    return [str(run)]


def run_task_commands(
    consumer: Path, name: str, cwd: Path | None = None, env: dict[str, str] | None = None
) -> tuple[int, str]:
    """Run a fragment task's commands the way mise does, stopping at the first failure.

    Args:
        consumer: A rendered consumer.
        name: The task name.
        cwd: The working directory (the consumer by default).
        env: Extra environment variables.

    Returns:
        The exit code of the last command run, and the combined output.
    """
    output = ""
    for command in task_commands(consumer, name):
        code, text = run_script(cwd or consumer, command, env)
        output += text
        if code != 0:
            return code, output
    return 0, output


def isolated_mise_env(root: Path) -> dict[str, str]:
    """Environment for running mise in `root` without the user's global config or state.

    Args:
        root: The directory whose config mise should trust and read.

    Returns:
        A copy of the environment with `MISE_*` variables replaced.
    """
    empty = root.parent / f"{root.name}-empty-mise.toml"
    empty.write_text("")
    return {
        **{key: value for key, value in os.environ.items() if not key.startswith("MISE_")},
        "MISE_GLOBAL_CONFIG_FILE": str(empty),
        "MISE_SYSTEM_CONFIG_FILE": str(empty),
        "MISE_STATE_DIR": str(root.parent / f"{root.name}-mise-state"),
    }


def run_script(cwd: Path, script: str, env: dict[str, str] | None = None) -> tuple[int, str]:
    """Run one shell command as mise would, and return its exit code and combined output.

    Args:
        cwd: The working directory.
        script: The script text.
        env: Extra environment variables.

    Returns:
        The exit code and output.
    """
    completed = subprocess.run(  # noqa: S603
        [*MISE_SHELL, script],
        cwd=cwd,
        env={**os.environ, **(env or {})},
        capture_output=True,
        text=True,
        check=False,
    )
    return completed.returncode, completed.stdout + completed.stderr
