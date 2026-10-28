"""Tests of what the template renders into a consumer with default answers."""

from __future__ import annotations

import fnmatch
import json
import re
import subprocess
from typing import TYPE_CHECKING, Any

import pytest
import yaml

from tests.support import (
    ANSWERS_FILE,
    FIXTURES,
    FRAGMENT,
    copier_config,
    fragment_tasks,
    isolated_mise_env,
    load_toml,
    render,
    task_commands,
)

if TYPE_CHECKING:
    from pathlib import Path

TEMPLATE_FILES = (
    "mise.toml",
    "ruff.toml",
    "ty.toml",
    "prek.toml",
    "uv.toml",
    "exceptions.py",
    "lid_version.py",
    "session-start.sh",
)
FORMATTER_CONFLICTS = {
    "W191", "E111", "E114", "E117", "D206", "D300",
    "Q000", "Q001", "Q002", "Q003", "Q004", "COM812", "COM819", "ISC002",
}  # fmt: skip
EXACT_VERSION = re.compile(r"\d+\.\d+\.\d+")


def _ref() -> str:
    return str(copier_config()["agentic_development_ref"]["default"])


def _ruff_base(consumer: Path) -> dict[str, Any]:
    return load_toml(consumer / ".config/copier-python/ruff.toml")


@pytest.fixture
def fresh(template: Path, tmp_path: Path) -> Path:
    """A consumer rendered into an empty directory."""
    return render(template, tmp_path / "consumer")


# @spec FILES-LAYOUT-001
def test_template_owned_files_live_in_one_directory(consumer: Path) -> None:
    """The template's regular files are all in `.config/copier-python/`."""
    for name in TEMPLATE_FILES:
        path = consumer / ".config/copier-python" / name
        assert path.is_file(), name
        assert not path.is_symlink(), name


# @spec FILES-LAYOUT-002
def test_conf_d_links_to_the_fragment(consumer: Path) -> None:
    """Mise finds the fragment through a relative symlink in `conf.d`."""
    link = consumer / ".config/mise/conf.d/copier-python.toml"
    assert link.is_symlink()
    assert str(link.readlink()) == "../../copier-python/mise.toml"


# @spec FILES-LAYOUT-003
def test_root_uv_toml_links_to_the_template_copy(consumer: Path) -> None:
    """Uv finds the template's settings through a root symlink."""
    link = consumer / "uv.toml"
    assert link.is_symlink()
    assert str(link.readlink()) == ".config/copier-python/uv.toml"


# @spec FILES-LAYOUT-004
def test_root_gains_only_three_entries(fresh: Path) -> None:
    """Rendering into an empty directory adds only the answers file, `.ruff.toml` and `uv.toml`."""
    root_files = {path.name for path in fresh.iterdir() if path.is_file() or path.is_symlink()}
    assert root_files == {ANSWERS_FILE, ".ruff.toml", "uv.toml"}


# @spec FILES-LAYOUT-005
def test_github_forge_files(consumer: Path) -> None:
    """With the `github` forge, the CI stub and Renovate config are rendered under `.github/`."""
    assert (consumer / ".github/workflows/ci.yml").is_file()
    assert (consumer / ".github/renovate.json").is_file()


# @spec FILES-CONTENT-001
def test_uv_settings(consumer: Path) -> None:
    """The template's uv settings hold only the three-day lock-file delay."""
    assert load_toml(consumer / ".config/copier-python/uv.toml") == {"exclude-newer": "3 days"}


# @spec FILES-CONTENT-002
def test_repo_ruff_file(consumer: Path) -> None:
    """The repo's ruff file extends the base and starts with no exceptions."""
    assert load_toml(consumer / ".ruff.toml") == {
        "extend": ".config/copier-python/ruff.toml",
        "lint": {"extend-per-file-ignores": {}},
    }


# @spec FILES-CONTENT-003
def test_repo_mise_config(consumer: Path) -> None:
    """The repo's mise config is empty apart from a comment naming the override points."""
    path = consumer / ".config/mise/config.toml"
    assert load_toml(path) == {}
    comments = " ".join(line for line in path.read_text().splitlines() if line.startswith("#"))
    assert "check-extra" in comments
    assert "hooks-extra" in comments


# @spec FILES-CONTENT-004
def test_arrow_index_stub(consumer: Path) -> None:
    """The arrow index is the minimal file `lidc` accepts."""
    index = yaml.safe_load((consumer / "docs/arrows/index.yaml").read_text())
    assert index == {"schema_version": 2, "arrows": {}}


# @spec FILES-CONTENT-005
def test_ci_stub(consumer: Path) -> None:
    """The CI stub runs on every push and calls the shared workflow at the template's ref."""
    stub = yaml.safe_load((consumer / ".github/workflows/ci.yml").read_text())
    triggers = stub.get("on", stub.get(True))
    assert triggers == {"push": {"branches": ["**"]}}
    jobs = list(stub["jobs"].values())
    assert len(jobs) == 1
    assert jobs[0]["uses"] == f"jmbowman/agentic_development/.github/workflows/check.yml@{_ref()}"
    assert "with" not in jobs[0]


# @spec FILES-CONTENT-006
def test_renovate_stub(consumer: Path) -> None:
    """The Renovate config only extends the shared preset at the template's ref."""
    config = json.loads((consumer / ".github/renovate.json").read_text())
    assert config == {
        "extends": [f"github>jmbowman/agentic_development//renovate/default#{_ref()}"]
    }


# @spec FILES-CONTENT-007
def test_answers_record_source_and_tag(template: Path, consumer: Path) -> None:
    """The answers file records where the template came from and which tag was rendered."""
    answers = yaml.safe_load((consumer / ANSWERS_FILE).read_text())
    assert answers["_src_path"] == str(template)
    assert answers["_commit"] == "v1.0.0"


# @spec STRICT-RUFF-001, STRICT-RUFF-005, STRICT-RUFF-006
def test_ruff_base_selects_everything(consumer: Path) -> None:
    """The base selects every rule, uses Google docstrings and the answered line length."""
    base = _ruff_base(consumer)
    assert base["lint"]["select"] == ["ALL"]
    assert base["lint"]["pydocstyle"]["convention"] == "google"
    assert base["line-length"] == 100


# @spec STRICT-RUFF-002, STRICT-RUFF-003
def test_ruff_base_ignores_only_formatter_conflicts(consumer: Path) -> None:
    """With no copyright regex, the base ignores the formatter conflicts plus CPY001."""
    assert set(_ruff_base(consumer)["lint"]["ignore"]) == FORMATTER_CONFLICTS | {"CPY001"}
    lines = (consumer / ".config/copier-python/ruff.toml").read_text().splitlines()
    for rule in FORMATTER_CONFLICTS | {"CPY001"}:
        rule_lines = [line for line in lines if f'"{rule}"' in line]
        assert rule_lines, rule
        assert all("#" in line for line in rule_lines), rule


# @spec STRICT-RUFF-004
def test_copyright_regex_enables_cpy001(template: Path, tmp_path: Path) -> None:
    """With a copyright regex, CPY001 stays on and uses that pattern."""
    consumer = render(
        template, tmp_path / "c", data={"copyright_notice_regex": r"\(c\) \d{4} Example"}
    )
    base = _ruff_base(consumer)
    assert "CPY001" not in base["lint"]["ignore"]
    assert base["lint"]["flake8-copyright"]["notice-rgx"] == r"\(c\) \d{4} Example"


# @spec STRICT-RUFF-006
def test_line_length_answer(template: Path, tmp_path: Path) -> None:
    """The base's line length follows the answer."""
    consumer = render(template, tmp_path / "c", data={"line_length": 120})
    assert _ruff_base(consumer)["line-length"] == 120


# @spec STRICT-RUFF-007
def test_test_relaxations(consumer: Path) -> None:
    """Only S101 and PLR2004 are relaxed, only for test files, anchored at the consumer root."""
    relaxations = _ruff_base(consumer)["lint"]["per-file-ignores"]
    assert relaxations == {
        "../../**/tests/**": ["S101", "PLR2004"],
        "../../**/test_*.py": ["S101", "PLR2004"],
        "../../**/conftest.py": ["S101", "PLR2004"],
    }


# @spec STRICT-TY-001, STRICT-TY-002
def test_ty_config(consumer: Path) -> None:
    """Every ty rule is an error, and `# type: ignore` is not honoured."""
    config = load_toml(consumer / ".config/copier-python/ty.toml")
    assert config["rules"] == {"all": "error"}
    assert config["analysis"]["respect-type-ignore-comments"] is False


def _tools(consumer: Path) -> dict[str, Any]:
    return load_toml(consumer / FRAGMENT)["tools"]


# @spec CHECKS-TOOL-001
def test_core_tools_pinned_exactly(consumer: Path) -> None:
    """uv, ruff, ty, prek and apm are pinned to full version numbers."""
    tools = _tools(consumer)
    for name in ("uv", "ruff", "ty", "prek", "apm"):
        assert EXACT_VERSION.fullmatch(str(tools[name])), name


# @spec CHECKS-TOOL-002
def test_lidc_pin_selects_one_linux_binary(consumer: Path) -> None:
    """The lidc pin is exact and its asset pattern matches only the Linux x86_64 binary."""
    lidc = _tools(consumer)["github:EtaCassiopeia/lid-tooling"]
    assert EXACT_VERSION.fullmatch(lidc["version"])
    assets = (FIXTURES / "lid-tooling-release-assets.txt").read_text().split()
    assert fnmatch.filter(assets, lidc["asset_pattern"]) == ["lidc-x86_64-unknown-linux-gnu"]


# @spec CHECKS-TOOL-004
def test_ty_config_path_is_absolute(consumer: Path) -> None:
    """In a consumer, mise sets TY_CONFIG_FILE to that consumer's absolute ty config path."""
    completed = subprocess.run(
        ["mise", "env", "--json"],  # noqa: S607
        cwd=consumer,
        env={**isolated_mise_env(consumer), "MISE_TRUSTED_CONFIG_PATHS": str(consumer)},
        capture_output=True,
        text=True,
        check=True,
    )
    expected = consumer / ".config/copier-python/ty.toml"
    assert json.loads(completed.stdout)["TY_CONFIG_FILE"] == str(expected)
    assert expected.is_file()


@pytest.mark.parametrize(
    ("task", "commands"),
    [
        ("lid-version", ["uv run --no-project .config/copier-python/lid_version.py"]),
        ("sync", ["uv sync --locked --all-extras --all-groups"]),
        ("lint", ["ruff check", "ruff format --check"]),
        ("typecheck", ["ty check"]),
        ("test", ["uv run --locked pytest"]),
        ("lid", ["lidc check --only reverse-orphan,coverage,spec-id-format --fail-on warning"]),
        ("fix", ["ruff check --fix", "ruff format"]),
        ("hooks", ["prek run -c .config/copier-python/prek.toml --all-files"]),
        ("exceptions", ["uv run --no-project .config/copier-python/exceptions.py"]),
    ],
)
# @spec CHECKS-TASK-002, CHECKS-TASK-003, CHECKS-TASK-004, CHECKS-TASK-005, CHECKS-TASK-006
# @spec CHECKS-TASK-010, CHECKS-TASK-011, CHECKS-TASK-012, CHECKS-TASK-019
def test_task_commands(consumer: Path, task: str, commands: list[str]) -> None:
    """Each task runs its commands as whole commands, in order."""
    found = [
        part.strip()
        for entry in task_commands(consumer, task)
        for part in re.split(r"\n|;|&&|\|\|", entry)
        if part.strip()
    ]
    positions = []
    for command in commands:
        assert command in found, (task, found)
        positions.append(found.index(command))
    assert positions == sorted(positions), (task, found)


# @spec CHECKS-TASK-001
def test_setup_installs_apm_and_skills_before_other_tools(consumer: Path) -> None:
    """`setup` runs its steps in the session hook's order, with no dependencies."""
    setup = fragment_tasks(consumer)["setup"]
    assert setup["run"] == [
        "mise install apm",
        "mise run skills",
        "mise install",
        "prek install -c .config/copier-python/prek.toml",
    ]
    assert "depends" not in setup


# @spec CHECKS-TASK-016
def test_skills_task_reinstalls_from_the_lock(consumer: Path) -> None:
    """`skills` clears the installed skills, then installs exactly what the lock records."""
    skills = fragment_tasks(consumer)["skills"]
    assert skills["dir"] == "{{config_root}}/.config/copier-python"
    assert skills["run"] == ["rm -rf .claude", "apm install --frozen"]


# @spec CHECKS-TASK-018
def test_skill_links_installs_skills_first(consumer: Path) -> None:
    """`skill-links` depends on `skills`, so `check` installs the skills in CI."""
    assert fragment_tasks(consumer)["skill-links"]["depends"] == ["skills"]


# @spec CHECKS-TASK-004, CHECKS-TASK-005
def test_environment_tasks_depend_on_sync(consumer: Path) -> None:
    """Type checking and tests run in a synced environment."""
    tasks = fragment_tasks(consumer)
    for name in ("typecheck", "test"):
        assert "sync" in tasks[name]["depends"], name


# @spec CHECKS-TASK-008
def test_extra_tasks_do_nothing(consumer: Path) -> None:
    """The extension points succeed without doing anything by default."""
    for name in ("check-extra", "hooks-extra"):
        assert task_commands(consumer, name) == ["true"], name


# @spec CHECKS-TASK-009
def test_check_aggregates_the_checks(consumer: Path) -> None:
    """`check` depends on every check and runs nothing itself."""
    check = fragment_tasks(consumer)["check"]
    assert set(check["depends"]) == {
        "lint", "typecheck", "test", "lid", "conflicts", "skill-links", "lid-version",
        "check-extra",
    }  # fmt: skip
    assert "run" not in check


# @spec CHECKS-TOOL-003
def test_min_version_is_set(consumer: Path) -> None:
    """The fragment sets mise's minimum version (compared with CI's pin in a network test)."""
    assert EXACT_VERSION.fullmatch(str(load_toml(consumer / FRAGMENT)["min_version"]))


# @spec CHECKS-HOOK-001
def test_hooks(consumer: Path) -> None:
    """Exactly five local hooks, each running one mise task on the whole project."""
    prek = load_toml(consumer / ".config/copier-python/prek.toml")
    hooks = [hook for repo in prek["repos"] for hook in repo["hooks"]]
    assert all(repo["repo"] == "local" for repo in prek["repos"])
    assert sorted(hook["entry"] for hook in hooks) == sorted(
        f"mise run {task}" for task in ("lint", "typecheck", "lid", "conflicts", "hooks-extra")
    )
    for hook in hooks:
        assert hook["language"] == "system"
        assert hook["pass_filenames"] is False


CLIENT_ID = "Iv23liExampleClient"


def _lock_refresh_stub(consumer: Path) -> dict[str, Any]:
    return yaml.safe_load((consumer / ".github/workflows/lock-refresh.yml").read_text())


# @spec FILES-LAYOUT-006
def test_lock_refresh_stub_only_with_a_client_id(
    template: Path, consumer: Path, tmp_path: Path
) -> None:
    """Without an App client ID there's no stub; with one, the stub is rendered."""
    assert not (consumer / ".github/workflows/lock-refresh.yml").exists()
    with_app = render(
        template, tmp_path / "with-app", data={"lock_refresh_app_client_id": CLIENT_ID}
    )
    assert (with_app / ".github/workflows/lock-refresh.yml").is_file()


# @spec FILES-CONTENT-008
def test_lock_refresh_stub(template: Path, tmp_path: Path) -> None:
    """The stub runs on answers-file changes and passes the client ID and the key secret."""
    consumer = render(
        template, tmp_path / "consumer", data={"lock_refresh_app_client_id": CLIENT_ID}
    )
    stub = _lock_refresh_stub(consumer)
    triggers = stub.get("on", stub.get(True))
    assert triggers == {"pull_request": {"paths": [".copier-answers.*.yml"]}}
    assert stub["permissions"] == {"contents": "read"}
    jobs = list(stub["jobs"].values())
    assert len(jobs) == 1
    assert jobs[0]["uses"] == (
        f"jmbowman/agentic_development/.github/workflows/lock-refresh.yml@{_ref()}"
    )
    assert jobs[0]["with"] == {"client-id": CLIENT_ID}
    assert jobs[0]["secrets"] == {"app-private-key": "${{ secrets.LOCK_REFRESH_APP_PRIVATE_KEY }}"}
