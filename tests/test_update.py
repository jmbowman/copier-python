"""Tests of `copier update` from one test-created template tag to a later one."""

from __future__ import annotations

import filecmp
import re
from typing import TYPE_CHECKING

from tests.support import (
    SKILL_LINK_DIRS,
    SKILLS_LOCK,
    commit_all,
    consumer_repo,
    fake_skill_install,
    git,
    lock_entries,
    release,
    render,
    run_task_commands,
    skill_link_target,
    template_repo,
    update,
)

if TYPE_CHECKING:
    from pathlib import Path

PREK = ".config/copier-python/prek.toml"
TY = ".config/copier-python/ty.toml"
CONFLICT_START = "<" * 7 + " "
TEMPLATE_OWNED = (
    ".config/copier-python/mise.toml",
    ".config/copier-python/ruff.toml",
    TY,
    PREK,
    ".config/copier-python/uv.toml",
    ".config/copier-python/exceptions.py",
)
REPO_OWNED = (
    ".ruff.toml",
    ".config/mise/config.toml",
    "docs/arrows/index.yaml",
    ".claude/settings.json",
    ".github/workflows/ci.yml",
    ".github/renovate.json",
)


def _source(template: Path, rendered: str) -> Path:
    """Find the file in a template repo that renders to `rendered`."""
    root = template / "template"
    for path in root.rglob("*"):
        if path.is_file() and not path.is_symlink():
            name = re.sub(r"\{%.*?%\}", "", str(path.relative_to(root))).removesuffix(".jinja")
            if name == rendered:
                return path
    msg = f"no template source renders {rendered}"
    raise AssertionError(msg)


def _release_changes(template: Path) -> None:
    """v1.1.0 changes prek.toml and every repo-owned file's starting content."""
    for rendered in (PREK, *REPO_OWNED):
        path = _source(template, rendered)
        extra = "\n" if rendered.endswith(".json") else "# Changed in v1.1.0.\n"
        path.write_text(path.read_text() + extra)


def _setup(tmp_path: Path) -> tuple[Path, Path]:
    template = template_repo(tmp_path / "template")
    consumer = consumer_repo(template, tmp_path / "consumer")
    release(template, "v1.1.0", _release_changes)
    return template, consumer


def _edit(consumer: Path, relative: str, extra: str) -> None:
    path = consumer / relative
    path.write_text(path.read_text() + extra)
    commit_all(consumer, f"edit {relative}")


# @spec FILES-UPD-001
def test_repo_owned_files_are_untouched(tmp_path: Path) -> None:
    """Edited repo-owned files are byte-identical after an update."""
    _template, consumer = _setup(tmp_path)
    _edit(consumer, ".ruff.toml", '"src/legacy.py" = ["T201"]\n')
    before = {name: (consumer / name).read_bytes() for name in REPO_OWNED}
    update(consumer, "v1.1.0")
    assert {name: (consumer / name).read_bytes() for name in REPO_OWNED} == before


# @spec FILES-UPD-002
def test_clean_consumer_matches_the_new_rendering(tmp_path: Path) -> None:
    """A consumer that edited only repo-owned files ends up exactly at the new tag's rendering."""
    template, consumer = _setup(tmp_path)
    _edit(consumer, ".config/mise/config.toml", '[tools]\njq = "1.7.1"\n')
    update(consumer, "v1.1.0")
    fresh = render(template, tmp_path / "fresh", ref="v1.1.0")
    for name in TEMPLATE_OWNED:
        assert filecmp.cmp(consumer / name, fresh / name, shallow=False), name
        assert CONFLICT_START not in (consumer / name).read_text(), name


# @spec FILES-UPD-003
def test_non_overlapping_edit_to_template_file_survives(tmp_path: Path) -> None:
    """An edit to a template-owned file the new tag doesn't touch is kept."""
    _template, consumer = _setup(tmp_path)
    _edit(consumer, TY, "# local note\n")
    update(consumer, "v1.1.0")
    assert (consumer / TY).read_text().endswith("# local note\n")
    assert "# Changed in v1.1.0." in (consumer / PREK).read_text()


# @spec FILES-UPD-004
def test_deleted_template_file_stays_deleted(tmp_path: Path) -> None:
    """A template-owned file the consumer deleted isn't recreated, even when the tag changes it."""
    _template, consumer = _setup(tmp_path)
    (consumer / PREK).unlink()
    commit_all(consumer, "remove prek config")
    update(consumer, "v1.1.0")
    assert not (consumer / PREK).exists()


# @spec FILES-UPD-005
def test_symlinks_survive(tmp_path: Path) -> None:
    """The rendered symlinks are still symlinks with the same targets after an update."""
    _template, consumer = _setup(tmp_path)
    links = {
        ".config/mise/conf.d/copier-python.toml": "../../copier-python/mise.toml",
        "uv.toml": ".config/copier-python/uv.toml",
    }
    update(consumer, "v1.1.0")
    for name, target in links.items():
        path = consumer / name
        assert path.is_symlink(), name
        assert str(path.readlink()) == target, name


# @spec FILES-UPD-006
def test_overlapping_edit_leaves_markers_that_fail_conflicts(tmp_path: Path) -> None:
    """An edit overlapping the new tag's change leaves conflict markers, and `conflicts` fails."""
    _template, consumer = _setup(tmp_path)
    _edit(consumer, PREK, "# local hook note\n")
    update(consumer, "v1.1.0")
    assert CONFLICT_START in (consumer / PREK).read_text()
    git(consumer, "add", "-A")
    exit_code, output = run_task_commands(consumer, "conflicts")
    assert exit_code != 0, output


# @spec FILES-UPD-008
def test_deleted_repo_owned_file_is_recreated(tmp_path: Path) -> None:
    """A repo-owned file the consumer deleted comes back with the newer tag's starting content."""
    template, consumer = _setup(tmp_path)
    (consumer / ".ruff.toml").unlink()
    commit_all(consumer, "remove ruff file")
    update(consumer, "v1.1.0")
    fresh = render(template, tmp_path / "fresh", ref="v1.1.0")
    assert (consumer / ".ruff.toml").read_text() == (fresh / ".ruff.toml").read_text()
    assert "# Changed in v1.1.0." in (consumer / ".ruff.toml").read_text()


# @spec FILES-UPD-009
def test_answering_the_client_id_later_renders_the_stub(tmp_path: Path) -> None:
    """A consumer that opts in after its first render gets the stub on update."""
    _template, consumer = _setup(tmp_path)
    assert not (consumer / ".github/workflows/lock-refresh.yml").exists()
    update(consumer, "v1.0.0", data={"lock_refresh_app_client_id": "Iv23liLater"})
    stub = (consumer / ".github/workflows/lock-refresh.yml").read_text()
    assert "client-id: Iv23liLater" in stub


def _bump_the_locked_package(template: Path) -> None:
    """v1.1.0 changes the skills package's locked commit and version, as a pin bump would."""
    lock = template / "template" / SKILLS_LOCK
    entry = next(
        entry for entry in lock_entries(lock) if entry["repo_url"] == "jmbowman/agentic_development"
    )
    text = lock.read_text()
    text = text.replace(str(entry["resolved_commit"]), "0" * 40)
    text = text.replace(f"version: {entry['version']}\n", "version: 9.9.9\n", 1)
    lock.write_text(text)


def _add_own_skills(consumer: Path) -> dict[str, bytes | str]:
    """Give the consumer a skill as real files and a linked one of its own, and commit them."""
    own_files = consumer / ".claude/skills/own-files/SKILL.md"
    own_files.parent.mkdir(parents=True)
    own_files.write_text("---\nname: own-files\n---\n")
    (consumer / "skills/own-link").mkdir(parents=True)
    (consumer / "skills/own-link/SKILL.md").write_text("---\nname: own-link\n---\n")
    for link_dir in SKILL_LINK_DIRS:
        (consumer / link_dir / "own-link").symlink_to("../../skills/own-link")
    commit_all(consumer, "own skills")
    return _own_entries(consumer)


def _own_entries(consumer: Path) -> dict[str, bytes | str]:
    entries: dict[str, bytes | str] = {
        ".claude/skills/own-files/SKILL.md": (
            consumer / ".claude/skills/own-files/SKILL.md"
        ).read_bytes(),
        "skills/own-link/SKILL.md": (consumer / "skills/own-link/SKILL.md").read_bytes(),
    }
    for link_dir in SKILL_LINK_DIRS:
        entries[f"{link_dir}/own-link"] = str((consumer / link_dir / "own-link").readlink())
    return entries


# @spec FILES-UPD-010
def test_lock_changes_update_beside_the_repos_own_skills(tmp_path: Path) -> None:
    """A release that changes the template's lock file updates cleanly around repo skills."""
    template = template_repo(tmp_path / "template")
    consumer = consumer_repo(template, tmp_path / "consumer")
    own = _add_own_skills(consumer)
    release(template, "v1.1.0", _bump_the_locked_package)

    update(consumer, "v1.1.0")

    fresh = render(template, tmp_path / "fresh", ref="v1.1.0")
    lock = (consumer / SKILLS_LOCK).read_text()
    assert CONFLICT_START not in lock
    assert lock == (fresh / SKILLS_LOCK).read_text()
    assert "0" * 40 in lock
    assert _own_entries(consumer) == own


def _add_links(template: Path) -> None:
    """v1.1.0 adds the two links of a new skill."""
    for link_dir in SKILL_LINK_DIRS:
        (template / "template" / link_dir / "added-skill").symlink_to(
            skill_link_target("added-skill")
        )


def _remove_links(template: Path) -> None:
    """v1.2.0 removes the links v1.1.0 added."""
    for link_dir in SKILL_LINK_DIRS:
        (template / "template" / link_dir / "added-skill").unlink()


# @spec FILES-UPD-011
def test_links_added_by_a_release(tmp_path: Path) -> None:
    """A release that adds a skill's links brings both."""
    template = template_repo(tmp_path / "template")
    consumer = consumer_repo(template, tmp_path / "consumer")
    release(template, "v1.1.0", _add_links)

    update(consumer, "v1.1.0")

    for link_dir in SKILL_LINK_DIRS:
        link = consumer / link_dir / "added-skill"
        assert str(link.readlink()) == skill_link_target("added-skill"), link_dir


# @spec FILES-UPD-012
def test_links_removed_by_a_release_fail_the_check(tmp_path: Path) -> None:
    """Removed links dangle, since copier never deletes symlinks, until a person deletes both."""
    template = template_repo(tmp_path / "template")
    release(template, "v1.1.0", _add_links)
    release(template, "v1.2.0", _remove_links)
    consumer = tmp_path / "consumer"
    consumer.mkdir()
    git(consumer, "init", "-q")
    render(template, consumer, ref="v1.1.0")
    commit_all(consumer, "render v1.1.0")

    update(consumer, "v1.2.0")
    # The lock file never listed `added-skill`, so an install leaves its links dangling.
    fake_skill_install(consumer)
    exit_code, output = run_task_commands(consumer, "skill-links")
    assert exit_code != 0, output
    first, second = (consumer / link_dir / "added-skill" for link_dir in SKILL_LINK_DIRS)
    first.unlink()
    exit_code, output = run_task_commands(consumer, "skill-links")
    assert exit_code != 0, output
    assert str(second.relative_to(consumer)) in output
    second.unlink()
    exit_code, output = run_task_commands(consumer, "skill-links")
    assert exit_code == 0, output
