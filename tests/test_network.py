"""End-to-end tests that install the pinned tools and run real checks in rendered consumers."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import time
import urllib.request
from typing import TYPE_CHECKING, Any

import pytest
import yaml

from tests.support import (
    FRAGMENT,
    SAMPLE,
    commit_all,
    copier_config,
    git,
    isolated_mise_env,
    load_toml,
    release,
    render,
    template_repo,
    update,
)

if TYPE_CHECKING:
    from pathlib import Path

pytestmark = [pytest.mark.network, pytest.mark.slow]

HOOK_BUDGET_SECONDS = 10


def _sample_consumer(template: Path, tmp_path: Path, data: dict[str, Any] | None = None) -> Path:
    """Copy the sample project, commit it, render the template into it, and commit again."""
    consumer = tmp_path / "sample"
    shutil.copytree(SAMPLE, consumer, symlinks=True)
    git(consumer, "init", "-q")
    commit_all(consumer, "sample")
    render(template, consumer, data=data)
    commit_all(consumer, "render")
    return consumer


def _bump_prek(repo: Path) -> None:
    """Release change used by the update tests: append a comment to the template's prek.toml."""
    path = repo / "template" / ".config/copier-python/prek.toml"
    path.write_text(path.read_text() + "# Added in v1.1.0.\n")


def _mise(consumer: Path, *args: str, env: dict[str, str] | None = None) -> tuple[int, str]:
    completed = subprocess.run(  # noqa: S603
        ["mise", *args],  # noqa: S607
        cwd=consumer,
        env={
            **isolated_mise_env(consumer),
            "MISE_TRUSTED_CONFIG_PATHS": str(consumer),
            **(env or {}),
        },
        capture_output=True,
        text=True,
        check=False,
    )
    return completed.returncode, completed.stdout + completed.stderr


def _write(consumer: Path, files: dict[str, str]) -> None:
    for name, content in files.items():
        path = consumer / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
    commit_all(consumer, "add files")


# @spec FILES-RENDER-001
def test_rendered_sample_passes_check(template: Path, tmp_path: Path) -> None:
    """A strict-clean sample project passes `mise run check` right after `mise trust`."""
    consumer = _sample_consumer(template, tmp_path)
    # Not `_mise()`: it pre-trusts the consumer, and this test must prove `mise trust` suffices.
    env = isolated_mise_env(consumer)
    for args in (["trust"], ["run", "check"]):
        completed = subprocess.run(  # noqa: S603
            ["mise", *args],  # noqa: S607
            cwd=consumer,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        assert completed.returncode == 0, completed.stdout + completed.stderr


# @spec FILES-UPD-007
def test_sample_still_passes_after_an_update(tmp_path: Path) -> None:
    """After a Renovate-style update to a later tag, the sample still passes `check`."""
    template = template_repo(tmp_path / "template")
    consumer = _sample_consumer(template, tmp_path)

    release(template, "v1.1.0", _bump_prek)
    update(consumer, "v1.1.0")
    commit_all(consumer, "update")
    code, output = _mise(consumer, "run", "check")
    assert code == 0, output


# @spec FILES-003
def test_minimum_copier_renders_the_same_files(tmp_path: Path) -> None:
    """The oldest supported copier renders and updates the same tree as the locked one."""
    template = template_repo(tmp_path / "template")
    minimum = str(copier_config()["_min_copier_version"])
    old = tmp_path / "old"
    command = ["uvx", "--from", f"copier=={minimum}", "copier", "copy", "--defaults"]
    command += ["--vcs-ref", "v1.0.0", str(template), str(old)]
    subprocess.run(command, check=True, capture_output=True)  # noqa: S603
    new = render(template, tmp_path / "new")
    assert _tree(old) == _tree(new)

    release(template, "v1.1.0", _bump_prek)
    for consumer, use_minimum in ((old, True), (new, False)):
        git(consumer, "init", "-q")
        commit_all(consumer, "render")
        if use_minimum:
            command = ["uvx", "--from", f"copier=={minimum}", "copier", "update", "--defaults"]
            command += ["--skip-answered", "--vcs-ref", "v1.1.0", "--answers-file"]
            command += [".copier-answers.python.yml"]
            subprocess.run(command, cwd=consumer, check=True, capture_output=True)  # noqa: S603
        else:
            update(consumer, "v1.1.0")
    assert _tree(old) == _tree(new)


def _tree(root: Path) -> dict[str, str]:
    """Every file and symlink under `root` (outside `.git`), mapped to its content or target."""
    tree = {}
    for path in sorted(root.rglob("*")):
        relative = str(path.relative_to(root))
        if relative == ".git" or relative.startswith(".git/"):
            continue
        if path.is_symlink():
            tree[relative] = f"-> {path.readlink()}"
        elif path.is_file():
            tree[relative] = path.read_text(errors="replace")
    return tree


# @spec CHECKS-TOOL-003
def test_min_version_not_newer_than_ci_mise(template: Path, tmp_path: Path) -> None:
    """The fragment's minimum mise version is no newer than the CI workflow's pinned mise."""
    ref = str(copier_config()["agentic_development_ref"]["default"])
    url = (
        "https://raw.githubusercontent.com/jmbowman/agentic_development/"
        f"{ref}/.github/workflows/check.yml"
    )
    with urllib.request.urlopen(url, timeout=30) as response:  # noqa: S310
        workflow = yaml.safe_load(response.read())
    job = next(iter(workflow["jobs"].values()))
    ci_mise = next(
        step["with"]["version"]
        for step in job["steps"]
        if str(step.get("uses", "")).startswith("jdx/mise-action@")
    )
    consumer = render(template, tmp_path / "consumer")
    minimum = str(load_toml(consumer / FRAGMENT)["min_version"])

    def key(value: str) -> tuple[int, ...]:
        return tuple(int(part) for part in value.split("."))

    assert key(minimum) <= key(str(ci_mise))


# @spec CHECKS-TASK-003
def test_lint_reports_both_ruff_findings(template: Path, tmp_path: Path) -> None:
    """`lint` runs the formatter check even when the linter has already failed."""
    consumer = _sample_consumer(template, tmp_path)
    _write(consumer, {"src/sample/bad.py": '"""Bad module."""\nimport os\nx  =  1\n'})
    code, output = _mise(consumer, "run", "lint")
    assert code != 0
    assert "F401" in output
    assert re.search(r"would (be )?reformat", output, re.IGNORECASE)
    _write(consumer, {"src/sample/bad.py": '"""Bad module."""\n\nimport os\n'})
    code, output = _mise(consumer, "run", "lint")
    assert code != 0, "a lint failure alone must fail the task"
    assert "F401" in output


# @spec CHECKS-TASK-013
def test_check_runs_the_repo_check_extra(template: Path, tmp_path: Path) -> None:
    """A repo's own `check-extra` runs as part of `check`."""
    consumer = _sample_consumer(template, tmp_path)
    _write(consumer, {".config/mise/config.toml": '[tasks.check-extra]\nrun = "echo REPO-EXTRA"\n'})
    code, output = _mise(consumer, "run", "check")
    assert code == 0, output
    assert "REPO-EXTRA" in output


# @spec CHECKS-TASK-014
def test_hooks_run_the_repo_hooks_extra(template: Path, tmp_path: Path) -> None:
    """A repo's own `hooks-extra` runs with the commit-time hooks."""
    consumer = _sample_consumer(template, tmp_path)
    override = '[tasks.hooks-extra]\nrun = "echo REPO-HOOK; exit 1"\n'
    _write(consumer, {".config/mise/config.toml": override})
    code, output = _mise(consumer, "run", "hooks")
    assert code != 0
    assert "REPO-HOOK" in output


# @spec CHECKS-HOOK-002
def test_commit_refused_without_mise(template: Path, tmp_path: Path) -> None:
    """With the hook installed but neither mise nor its shims on PATH, the commit fails."""
    consumer = _sample_consumer(template, tmp_path)
    code, output = _mise(consumer, "run", "setup")
    assert code == 0, output
    assert shutil.which("mise", path="/usr/bin:/bin") is None, "mise must be off the test PATH"
    head = git(consumer, "rev-parse", "HEAD").stdout
    (consumer / "README.md").write_text("change\n")
    git(consumer, "add", "README.md")
    completed = subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@example.com", "commit", "-qm", "x"],  # noqa: S607
        cwd=consumer,
        env={**os.environ, "PATH": "/usr/bin:/bin"},
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode != 0
    assert "mise" in completed.stdout + completed.stderr
    assert git(consumer, "rev-parse", "HEAD").stdout == head


# @spec CHECKS-HOOK-003
def test_warm_hooks_fit_the_budget(template: Path, tmp_path: Path) -> None:
    """With tools installed and the environment synced, the hooks finish within 10 seconds."""
    consumer = _sample_consumer(template, tmp_path)
    code, output = _mise(consumer, "run", "hooks")
    assert code == 0, output
    started = time.monotonic()
    code, output = _mise(consumer, "run", "hooks")
    assert code == 0, output
    assert time.monotonic() - started < HOOK_BUDGET_SECONDS


def _ruff_locations(output: str, rule: str) -> set[str]:
    return set(re.findall(rf"^(\S+?):\d+:\d+: {rule}\b", output, re.MULTILINE))


# @spec STRICT-RUFF-008
def test_test_relaxations_resolve_from_the_root(template: Path, tmp_path: Path) -> None:
    """S101 is reported in package code but relaxed in every kind of test file."""
    consumer = _sample_consumer(template, tmp_path)
    assertion = '"""Module."""\n\nassert True\n'
    _write(
        consumer,
        {
            "pkg/module.py": assertion,
            "tests/test_x.py": assertion,
            "tests/conftest.py": assertion,
            "pkg/tests/test_y.py": assertion,
            "pkg/tests/helpers.py": assertion,
        },
    )
    _code, output = _mise(consumer, "exec", "--", "ruff", "check", "--output-format", "concise")
    assert _ruff_locations(output, "S101") == {"pkg/module.py"}


# @spec STRICT-RUFF-009
def test_lint_ignores_template_files(template: Path, tmp_path: Path) -> None:
    """Template files under `.config/copier-python/` aren't linted, whatever the answers."""
    consumer = _sample_consumer(template, tmp_path, data={"copyright_notice_regex": "Example Corp"})
    _code, output = _mise(consumer, "run", "lint")
    assert "CPY001" in output, "lint must have run and flagged the sample's own files"
    assert ".config/copier-python" not in output


# @spec STRICT-TY-004
def test_typecheck_ignores_template_files(template: Path, tmp_path: Path) -> None:
    """Template files under `.config/copier-python/` aren't type-checked."""
    consumer = _sample_consumer(template, tmp_path)
    code, output = _mise(consumer, "run", "typecheck")
    assert code == 0, output
    assert ".config/copier-python" not in output


# @spec STRICT-TY-003
def test_pyproject_cannot_relax_ty(template: Path, tmp_path: Path) -> None:
    """A relaxation under `[tool.ty]` in pyproject.toml has no effect."""
    consumer = _sample_consumer(template, tmp_path)
    pyproject = consumer / "pyproject.toml"
    _write(
        consumer,
        {
            "pyproject.toml": pyproject.read_text()
            + '\n[tool.ty.rules]\ninvalid-assignment = "ignore"\n',
            "src/sample/wrong.py": '"""Wrong."""\n\nVALUE: int = "text"\n',
        },
    )
    code, output = _mise(consumer, "exec", "--", "ty", "check")
    assert code != 0
    assert "invalid-assignment" in output


@pytest.mark.parametrize("comment", ["import os  # noqa\n", "# ruff: noqa\nimport os\n"])
# @spec STRICT-BLANKET-001
def test_blanket_noqa_fails_lint(template: Path, tmp_path: Path, comment: str) -> None:
    """A bare line-level or file-level noqa fails `lint`."""
    consumer = _sample_consumer(template, tmp_path)
    _write(consumer, {"src/sample/blanket.py": f'"""Blanket."""\n\n{comment}'})
    code, output = _mise(consumer, "run", "lint")
    assert code != 0
    assert "PGH004" in output


# @spec STRICT-BLANKET-002
def test_blanket_ty_ignore_fails_typecheck(template: Path, tmp_path: Path) -> None:
    """A `ty: ignore` without a rule code fails `typecheck`."""
    consumer = _sample_consumer(template, tmp_path)
    _write(
        consumer, {"src/sample/blanket.py": '"""Blanket."""\n\nVALUE: int = "a"  # ty: ignore\n'}
    )
    code, output = _mise(consumer, "run", "typecheck")
    assert code != 0
    assert "blanket-ignore-comment" in output


# @spec FILES-CONTENT-009
def test_lock_refresh_stub_matches_the_shared_workflow(template: Path, tmp_path: Path) -> None:
    """The stub passes exactly the inputs and secrets the referenced workflow declares."""
    ref = str(copier_config()["agentic_development_ref"]["default"])
    url = (
        "https://raw.githubusercontent.com/jmbowman/agentic_development/"
        f"{ref}/.github/workflows/lock-refresh.yml"
    )
    with urllib.request.urlopen(url, timeout=30) as response:  # noqa: S310
        workflow = yaml.safe_load(response.read())
    call = workflow.get("on", workflow.get(True))["workflow_call"]
    consumer = render(
        template, tmp_path / "consumer", data={"lock_refresh_app_client_id": "Iv23liX"}
    )
    stub = yaml.safe_load((consumer / ".github/workflows/lock-refresh.yml").read_text())
    job = next(iter(stub["jobs"].values()))
    assert set(job["with"]) == set(call.get("inputs", {}))
    assert set(job["secrets"]) == set(call.get("secrets", {}))
