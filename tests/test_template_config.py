"""Tests of the template's own configuration: `copier.yml`, its questions and repo settings."""

from __future__ import annotations

import fnmatch
import json
import re
import tomllib
from importlib.metadata import version

from tests.support import COPIER_YML, REPO_ROOT, TEMPLATE_DIR, copier_config, git

QUESTIONS = ("forge", "line_length", "copyright_notice_regex", "lock_refresh_app_client_id")
REPO_OWNED = {
    ".ruff.toml",
    ".config/mise/config.toml",
    "docs/arrows/index.yaml",
    ".claude/settings.json",
    ".github/workflows/ci.yml",
    ".github/workflows/lock-refresh.yml",
    ".github/renovate.json",
}


def _python_regex(pattern: str) -> str:
    """Translate JavaScript named groups `(?<name>` to Python's `(?P<name>`."""
    return re.sub(r"\(\?<(?=[A-Za-z_])", "(?P<", pattern)


def _js_regex_matches(pattern: str, path: str) -> bool:
    """Apply a Renovate file pattern: `/regex/` or a glob."""
    if pattern.startswith("/") and pattern.endswith("/"):
        return re.search(_python_regex(pattern[1:-1]), path) is not None
    return fnmatch.fnmatch(path, pattern)


def _questions() -> dict[str, dict[str, object]]:
    return {key: value for key, value in copier_config().items() if not key.startswith("_")}


def _asked() -> dict[str, dict[str, object]]:
    return {key: value for key, value in _questions().items() if value.get("when") is not False}


# @spec FILES-001
def test_copier_settings() -> None:
    """The template renders from `template/`, writes a per-layer answers file and keeps symlinks."""
    config = copier_config()
    assert config["_subdirectory"] == "template"
    assert config["_answers_file"] == ".copier-answers.python.yml"
    assert config["_preserve_symlinks"] is True


# @spec FILES-002
def test_no_tasks_migrations_or_extensions() -> None:
    """Nothing in `copier.yml` would require `--trust`."""
    config = copier_config()
    for key in ("_tasks", "_migrations", "_jinja_extensions"):
        assert key not in config


# @spec FILES-005
def test_skip_if_exists_lists_exactly_the_repo_owned_paths() -> None:
    """Exactly the repo-owned paths are rendered once and then left alone."""
    assert set(copier_config()["_skip_if_exists"]) == REPO_OWNED


# @spec FILES-006
def test_mise_fragment_is_copied_verbatim() -> None:
    """The mise fragment isn't a Jinja template, so `{{config_root}}` survives rendering."""
    fragment_dir = TEMPLATE_DIR / ".config" / "copier-python"
    assert (fragment_dir / "mise.toml").is_file()
    assert not (fragment_dir / "mise.toml.jinja").exists()


# @spec FILES-007
def test_agentic_development_ref_is_a_hidden_constant() -> None:
    """`agentic_development_ref` is never asked and holds a release tag."""
    ref = _questions()["agentic_development_ref"]
    assert ref["when"] is False
    assert re.fullmatch(r"v\d+\.\d+\.\d+", str(ref["default"]))


# @spec FILES-008
def test_renovate_custom_manager_tracks_agentic_development_ref() -> None:
    """This repo's Renovate config bumps `agentic_development_ref` from its source repo's tags."""
    config = json.loads((REPO_ROOT / ".github" / "renovate.json").read_text())
    managers = [
        m
        for m in config["customManagers"]
        if m["customType"] == "regex"
        and any(_js_regex_matches(p, "copier.yml") for p in m["managerFilePatterns"])
    ]
    assert len(managers) == 1
    matches = [
        match.groupdict()
        for pattern in managers[0]["matchStrings"]
        for match in re.finditer(_python_regex(pattern), COPIER_YML.read_text())
    ]
    tag = str(_questions()["agentic_development_ref"]["default"])
    assert matches == [
        {
            "currentValue": tag,
            "datasource": "github-tags",
            "depName": "jmbowman/agentic_development",
        }
    ]


# @spec FILES-009
def test_template_files_carry_no_spec_annotations() -> None:
    """Rendered files never cite this repo's spec IDs, which consumers don't have."""
    assert TEMPLATE_DIR.is_dir()
    # Files git ignores (such as APM's download cache) are never committed or rendered.
    listed = git(REPO_ROOT, "ls-files", "--cached", "--others", "--exclude-standard", "template")
    paths = [REPO_ROOT / name for name in listed.stdout.splitlines()]
    offenders = [
        path.relative_to(REPO_ROOT)
        for path in paths
        if path.is_file() and "@spec" in path.read_text(errors="replace")
    ]
    assert paths
    assert offenders == []


# @spec FILES-Q-001
def test_forge_question() -> None:
    """`forge` is a choice whose only value is `github`, the default."""
    forge = _questions()["forge"]
    assert forge["type"] == "str"
    assert forge["choices"] == ["github"]
    assert forge["default"] == "github"


# @spec FILES-Q-002
def test_line_length_question() -> None:
    """`line_length` is an integer defaulting to 100."""
    line_length = _questions()["line_length"]
    assert line_length["type"] == "int"
    assert line_length["default"] == 100


# @spec FILES-Q-003
def test_copyright_notice_regex_question() -> None:
    """`copyright_notice_regex` is a string defaulting to empty."""
    regex = _questions()["copyright_notice_regex"]
    assert regex["type"] == "str"
    assert regex["default"] == ""


# @spec FILES-Q-004
def test_no_other_questions() -> None:
    """Only the documented questions are asked."""
    assert set(_asked()) == set(QUESTIONS)


# @spec FILES-004
def test_tests_run_on_the_locked_copier() -> None:
    """The copier library these tests import is the one pinned in `uv.lock`."""
    lock = tomllib.loads((REPO_ROOT / "uv.lock").read_text())
    locked = next(package["version"] for package in lock["package"] if package["name"] == "copier")
    assert version("copier") == locked


def test_own_ruff_profile_matches_the_template() -> None:
    """This repo's hand-kept ruff ignores match the template's list (a drift guard)."""
    own = tomllib.loads((REPO_ROOT / ".ruff.toml").read_text())["lint"]["ignore"]
    template_lines = (TEMPLATE_DIR / ".config/copier-python/ruff.toml.jinja").read_text()
    quoted = set(re.findall(r'"([A-Z]+[0-9]+)"', template_lines.split("[lint.pydocstyle]")[0]))
    assert set(own) == quoted


# @spec FILES-003
def test_min_copier_version_is_set() -> None:
    """`_min_copier_version` names a release, which the network tests render with."""
    assert re.fullmatch(r"\d+\.\d+\.\d+", str(copier_config()["_min_copier_version"]))


# @spec FILES-Q-005
def test_lock_refresh_app_client_id_question() -> None:
    """The App's client ID is an optional string, asked only for the GitHub forge."""
    question = _questions()["lock_refresh_app_client_id"]
    assert question["type"] == "str"
    assert question["default"] == ""
    assert question["when"] == "{{ forge == 'github' }}"
