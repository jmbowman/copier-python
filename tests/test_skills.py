"""Tests of the skills the template delivers: its pins, its links, and this repo's own setup."""

from __future__ import annotations

import re
import tomllib
from typing import TYPE_CHECKING, Any

import pytest
import yaml

from tests.support import (
    LID_PLUGIN,
    LID_REPO,
    REPO_ROOT,
    SKILL_LINK_DIRS,
    SKILLS,
    SKILLS_LOCK,
    TEMPLATE_DIR,
    TEMPLATE_DIR_IN_CONSUMER,
    commit_all,
    copier_config,
    git,
    lock_entries,
    release,
    render,
    skill_link_target,
    template_repo,
    template_skills,
)

if TYPE_CHECKING:
    from pathlib import Path

MANIFEST_DIR = TEMPLATE_DIR / TEMPLATE_DIR_IN_CONSUMER
RENDERED_APM_FILES = ("apm.yml", "apm.lock.yaml", ".gitignore")
TAG = r"v\d+\.\d+\.\d+"


def _manifest_dependencies(manifest: Path) -> list[str]:
    parsed = yaml.safe_load(manifest.read_text())
    assert parsed["targets"] == ["claude"]
    dependencies = parsed["dependencies"]["apm"]
    assert isinstance(dependencies, list)
    return [str(dependency) for dependency in dependencies]


def _own_mise() -> dict[str, Any]:
    return tomllib.loads((REPO_ROOT / "mise.toml").read_text())


def _own_tasks() -> dict[str, dict[str, Any]]:
    return _own_mise()["tasks"]


def test_template_has_skills() -> None:
    """The skills tests below would pass vacuously without at least one skill."""
    assert template_skills()


# @spec FILES-SKILL-001
def test_manifest_pins_the_skills_package_by_tag() -> None:
    """The template's APM manifest deploys only to Claude and pins one package at a release tag."""
    dependencies = _manifest_dependencies(MANIFEST_DIR / "apm.yml")
    assert len(dependencies) == 1
    assert re.fullmatch(rf"jmbowman/agentic_development#{TAG}", dependencies[0])


# @spec FILES-SKILL-013
def test_lock_records_the_pinned_skills_package() -> None:
    """The lock file holds the skills package once, at the manifest's tag."""
    tag = _manifest_dependencies(MANIFEST_DIR / "apm.yml")[0].split("#")[1]
    entries = [
        entry
        for entry in lock_entries(TEMPLATE_DIR / SKILLS_LOCK)
        if entry["repo_url"] == "jmbowman/agentic_development"
    ]
    assert len(entries) == 1
    assert entries[0]["resolved_ref"] == tag


# @spec FILES-SKILL-020
def test_lock_records_lid() -> None:
    """The lock file holds LID's linked-intent-dev plugin once, brought by the skills package."""
    entries = [
        entry
        for entry in lock_entries(TEMPLATE_DIR / SKILLS_LOCK)
        if entry["repo_url"] == LID_REPO and entry.get("virtual_path") == LID_PLUGIN
    ]
    assert len(entries) == 1


# @spec FILES-SKILL-003
@pytest.mark.parametrize("link_dir", SKILL_LINK_DIRS, ids=str)
def test_template_links_each_skill(link_dir: Path) -> None:
    """Each locked skill has one correctly aimed link in the link directory, and nothing else."""
    entries = {path.name: path for path in (TEMPLATE_DIR / link_dir).iterdir()}
    assert sorted(entries) == template_skills()
    for name, path in entries.items():
        assert path.is_symlink(), name
        assert str(path.readlink()) == skill_link_target(name), name


# @spec FILES-SKILL-004
def test_installed_files_are_excluded_from_rendering() -> None:
    """`_exclude` names exactly the installed skills and APM's download cache."""
    expected = {f"/{TEMPLATE_DIR_IN_CONSUMER}/.claude", f"/{TEMPLATE_DIR_IN_CONSUMER}/apm_modules"}
    assert set(copier_config()["_exclude"]) == expected


# @spec FILES-SKILL-006
@pytest.mark.parametrize("name", RENDERED_APM_FILES)
def test_apm_files_render_verbatim(consumer: Path, name: str) -> None:
    """The manifest, lock file and ignore file reach the consumer unchanged."""
    rendered = consumer / TEMPLATE_DIR_IN_CONSUMER / name
    assert rendered.is_file()
    assert rendered.read_bytes() == (MANIFEST_DIR / name).read_bytes()


# @spec FILES-SKILL-014
def test_ignore_file_lists_installed_skills_and_cache(consumer: Path) -> None:
    """The template's ignore file covers the installed skills and APM's cache."""
    lines = (consumer / TEMPLATE_DIR_IN_CONSUMER / ".gitignore").read_text().splitlines()
    assert "/.claude/" in lines
    assert "apm_modules/" in lines


# @spec FILES-SKILL-021
@pytest.mark.parametrize(
    "path",
    [f"{SKILLS}/any-skill/SKILL.md", f"{TEMPLATE_DIR_IN_CONSUMER}/apm_modules/pkg/file"],
)
def test_git_ignores_installed_skills_and_cache(consumer: Path, path: str) -> None:
    """In a rendered repo, git ignores what an install writes."""
    assert git(consumer, "check-ignore", "-q", path).returncode == 0


# @spec FILES-SKILL-007
@pytest.mark.parametrize("link_dir", SKILL_LINK_DIRS, ids=str)
def test_skill_links_render(consumer: Path, link_dir: Path) -> None:
    """The consumer gets a link to each locked skill in both skill directories."""
    for name in template_skills():
        link = consumer / link_dir / name
        assert link.is_symlink(), name
        assert str(link.readlink()) == skill_link_target(name), name


def _commit_an_install(template: Path) -> None:
    """Force-commit files where an install would put them, as `git add -f` would."""
    base = template / "template" / TEMPLATE_DIR_IN_CONSUMER
    for path in (base / ".claude/skills/stray/SKILL.md", base / "apm_modules/pkg/apm.yml"):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("stray\n")
    git(template, "add", "-f", ".")


# @spec FILES-SKILL-008
def test_committed_install_files_do_not_render(tmp_path: Path) -> None:
    """Installed skills and APM's cache stay out of consumers even if committed by force."""
    template = template_repo(tmp_path / "template")
    release(template, "v1.1.0", _commit_an_install)
    consumer = render(template, tmp_path / "consumer", ref="v1.1.0")
    assert not (consumer / TEMPLATE_DIR_IN_CONSUMER / ".claude").exists()
    assert not (consumer / TEMPLATE_DIR_IN_CONSUMER / "apm_modules").exists()


# @spec FILES-SKILL-009
def test_rendering_keeps_the_repos_own_skills(template: Path, tmp_path: Path) -> None:
    """A repo's own skill entries stay as they were, beside the template's new links."""
    consumer = tmp_path / "consumer"
    own_skill = consumer / ".claude/skills/own-files/SKILL.md"
    own_skill.parent.mkdir(parents=True)
    own_skill.write_text("---\nname: own-files\n---\n")
    (consumer / "skills/own-link").mkdir(parents=True)
    (consumer / "skills/own-link/SKILL.md").write_text("---\nname: own-link\n---\n")
    (consumer / ".agents/skills").mkdir(parents=True)
    (consumer / ".agents/skills/own-link").symlink_to("../../skills/own-link")
    git(consumer, "init", "-q")
    commit_all(consumer, "own skills")

    render(template, consumer)

    assert own_skill.read_text() == "---\nname: own-files\n---\n"
    assert str((consumer / ".agents/skills/own-link").readlink()) == "../../skills/own-link"
    for link_dir in SKILL_LINK_DIRS:
        for name in template_skills():
            assert (consumer / link_dir / name).is_symlink(), (link_dir, name)


# @spec FILES-SKILL-010
def test_own_mise_pins_apm() -> None:
    """This repo pins an exact apm version."""
    assert re.fullmatch(r"\d+\.\d+\.\d+", str(_own_mise()["tools"]["apm"]))


# @spec FILES-SKILL-022
def test_own_skills_task_reinstalls_lid() -> None:
    """This repo's `skills` task clears its installed skills, then installs from its lock file."""
    task = _own_tasks()["skills"]
    assert task["run"] == ["rm -rf .claude/skills", "apm install --frozen"]
    assert "dir" not in task


# @spec FILES-SKILL-016
def test_template_skills_task_installs_in_the_template() -> None:
    """`template-skills` clears and reinstalls the template's skills from its lock file."""
    task = _own_tasks()["template-skills"]
    assert task["dir"] == f"{{{{config_root}}}}/template/{TEMPLATE_DIR_IN_CONSUMER}"
    assert task["run"] == ["rm -rf .claude", "apm install --frozen"]


# @spec FILES-SKILL-023
def test_own_tests_wait_for_the_template_install() -> None:
    """The template's install finishes before any test copies the template."""
    assert "template-skills" in _own_tasks()["test"]["depends"]


# @spec FILES-SKILL-017
def test_own_lid_version_task() -> None:
    """This repo runs the template's LID version gate against its root files."""
    assert _own_tasks()["lid-version"]["run"] == (
        "uv run --no-project template/.config/copier-python/lid_version.py"
        " --lock apm.lock.yaml --instructions AGENTS.md"
    )


# @spec FILES-SKILL-024
def test_own_check_runs_the_lid_version_gate() -> None:
    """This repo's `check` includes its LID version gate."""
    assert "lid-version" in _own_tasks()["check"]["depends"]


# @spec FILES-SKILL-018
def test_own_setup_installs_skills() -> None:
    """This repo's `setup` installs its LID skills."""
    assert "mise run skills" in _own_tasks()["setup"]["run"]


# @spec FILES-SKILL-019
def test_own_manifest_pins_lid() -> None:
    """This repo's own APM manifest pins LID's linked-intent-dev plugin at a release tag."""
    dependencies = _manifest_dependencies(REPO_ROOT / "apm.yml")
    assert len(dependencies) == 1
    assert re.fullmatch(rf"{LID_REPO}/{LID_PLUGIN}#{TAG}", dependencies[0])


# @spec FILES-SKILL-025
@pytest.mark.parametrize("path", [".claude/skills/any-skill/SKILL.md", "apm_modules/pkg/file"])
def test_own_installs_are_ignored(path: str) -> None:
    """This repo's root ignore rules cover its installed skills and APM's cache."""
    assert git(REPO_ROOT, "check-ignore", "-q", path).returncode == 0


# @spec FILES-SKILL-012
def test_own_ty_skips_the_template_skills() -> None:
    """This repo's ty doesn't check scripts in the template's skills."""
    config = tomllib.loads((REPO_ROOT / ".config/ty.toml").read_text())
    assert f"template/{TEMPLATE_DIR_IN_CONSUMER}/.claude" in config["src"]["exclude"]
