"""Tests of the skills the template delivers: how this repo holds them and how they render."""

from __future__ import annotations

import os
import re
import tomllib
from typing import TYPE_CHECKING

import pytest
import yaml

from tests.support import (
    REPO_ROOT,
    SKILL_LINK_DIRS,
    SKILLS,
    TEMPLATE_DIR,
    TEMPLATE_DIR_IN_CONSUMER,
    commit_all,
    copier_config,
    git,
    render,
    skill_link_target,
    template_skills,
)

if TYPE_CHECKING:
    from pathlib import Path

MANIFEST_DIR = TEMPLATE_DIR / TEMPLATE_DIR_IN_CONSUMER
APM_FILES = {"apm.yml", "apm.lock.yaml", "apm_modules", ".gitignore"}


def _files_under(root: Path) -> set[str]:
    """Every regular file below `root`, as a path relative to `root`."""
    return {
        str(path.relative_to(root))
        for path in root.rglob("*")
        if path.is_file() and not path.is_symlink()
    }


def _deployed_files() -> set[str]:
    """The files the template's APM lock file records as deployed, relative to the manifest."""
    lock = yaml.safe_load((MANIFEST_DIR / "apm.lock.yaml").read_text())
    # `deployed_files` also lists directories; only files have hashes.
    return {
        path for dependency in lock["dependencies"] for path in dependency["deployed_file_hashes"]
    }


@pytest.fixture
def fresh(template: Path, tmp_path: Path) -> Path:
    """A consumer rendered into an empty directory."""
    return render(template, tmp_path / "consumer")


def test_template_has_skills() -> None:
    """The skills tests below would pass vacuously without at least one skill."""
    assert template_skills()


# @spec FILES-SKILL-001
def test_manifest_pins_the_skills_package_by_tag() -> None:
    """The template's APM manifest deploys only to Claude and pins one package at a release tag."""
    manifest = yaml.safe_load((MANIFEST_DIR / "apm.yml").read_text())
    assert manifest["targets"] == ["claude"]
    dependencies = manifest["dependencies"]["apm"]
    assert len(dependencies) == 1
    assert re.fullmatch(r"jmbowman/agentic_development#v\d+\.\d+\.\d+", dependencies[0])


# @spec FILES-SKILL-002
def test_committed_skills_are_what_apm_deployed() -> None:
    """The skill files on disk are exactly the files the lock file lists as deployed."""
    in_manifest_dir = SKILLS.relative_to(TEMPLATE_DIR_IN_CONSUMER)
    on_disk = {str(in_manifest_dir / name) for name in _files_under(TEMPLATE_DIR / SKILLS)}
    assert on_disk == _deployed_files()


# @spec FILES-SKILL-003
@pytest.mark.parametrize("link_dir", SKILL_LINK_DIRS, ids=str)
def test_template_links_each_skill(link_dir: Path) -> None:
    """Each skill has one correctly aimed link in the link directory, which holds nothing else."""
    entries = {path.name: path for path in (TEMPLATE_DIR / link_dir).iterdir()}
    assert sorted(entries) == template_skills()
    for name, path in entries.items():
        assert path.is_symlink(), name
        assert str(path.readlink()) == skill_link_target(name), name


# @spec FILES-SKILL-004
def test_apm_files_are_excluded_from_rendering() -> None:
    """The `_exclude` list is exactly the files APM keeps beside the manifest."""
    expected = {f"/{TEMPLATE_DIR_IN_CONSUMER}/{name}" for name in APM_FILES}
    assert set(copier_config()["_exclude"]) == expected


# @spec FILES-SKILL-005
def test_no_skill_file_is_a_jinja_template() -> None:
    """No skill file ends in `.jinja`, so copier copies them all verbatim."""
    assert [name for name in _files_under(TEMPLATE_DIR / SKILLS) if name.endswith(".jinja")] == []


# @spec FILES-SKILL-006
def test_skill_files_render_verbatim(consumer: Path) -> None:
    """Every skill file reaches the consumer as an identical regular file at the same path."""
    names = _files_under(TEMPLATE_DIR / SKILLS)
    assert names
    for name in names:
        rendered = consumer / SKILLS / name
        assert rendered.is_file(), name
        assert not rendered.is_symlink(), name
        assert rendered.read_bytes() == (TEMPLATE_DIR / SKILLS / name).read_bytes(), name


# @spec FILES-SKILL-007
@pytest.mark.parametrize("link_dir", SKILL_LINK_DIRS, ids=str)
def test_skill_links_render(consumer: Path, link_dir: Path) -> None:
    """The consumer gets a working link to each skill in both skill directories."""
    for name in template_skills():
        link = consumer / link_dir / name
        assert link.is_symlink(), name
        assert str(link.readlink()) == skill_link_target(name), name
        assert (link / "SKILL.md").is_file(), name


# @spec FILES-SKILL-008
def test_no_apm_files_render(fresh: Path) -> None:
    """Nothing APM-internal reaches a consumer."""
    rendered = {name for _root, dirs, files in os.walk(fresh) for name in dirs + files}
    assert rendered & APM_FILES == set()


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
def test_check_audits_the_committed_skills() -> None:
    """This repo pins apm, and `check` audits the template's skills against their lock file."""
    config = tomllib.loads((REPO_ROOT / "mise.toml").read_text())
    assert re.fullmatch(r"\d+\.\d+\.\d+", str(config["tools"]["apm"]))
    tasks = config["tasks"]
    assert "skills" in tasks["check"]["depends"]
    assert tasks["skills"]["run"] == "apm audit --ci --no-drift"
    assert tasks["skills"]["dir"] == f"{{{{config_root}}}}/template/{TEMPLATE_DIR_IN_CONSUMER}"


# @spec FILES-SKILL-012
def test_own_ty_skips_the_template_skills() -> None:
    """This repo's ty doesn't check scripts in the template's skills."""
    config = tomllib.loads((REPO_ROOT / ".config/ty.toml").read_text())
    assert f"template/{TEMPLATE_DIR_IN_CONSUMER}/.claude" in config["src"]["exclude"]
