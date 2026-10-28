"""Tests of the cloud-session hook, run with a stub `mise` and `curl` in a temporary home."""

from __future__ import annotations

import hashlib
import io
import json
import os
import re
import stat
import subprocess
import tarfile
import tomllib
from typing import TYPE_CHECKING, Any

import pytest
import yaml

from tests.support import FRAGMENT, REPO_ROOT, TEMPLATE_DIR, TEMPLATE_DIR_IN_CONSUMER

if TYPE_CHECKING:
    from pathlib import Path

HOOK = TEMPLATE_DIR_IN_CONSUMER / "session-start.sh"
COMMAND = '"$CLAUDE_PROJECT_DIR"/.config/copier-python/session-start.sh'
SUCCESS = {"hookSpecificOutput": {"hookEventName": "SessionStart", "reloadSkills": True}}

# Logs how it was called (the path, the working directory and the auto-install setting), then
# answers `--version` and `bin-paths`, fails when its arguments equal STUB_FAIL, and sends the
# hook SIGTERM when they equal STUB_KILL.
STUB_MISE = """\
#!/bin/bash
echo "$0|$PWD|${MISE_TASK_RUN_AUTO_INSTALL:-}|$*" >> "$STUB_LOG"
if [ "$*" = "${STUB_KILL:-}" ]; then kill -TERM "$PPID"; sleep 5; fi
case "$1" in
  --version) echo "$STUB_VERSION linux-x64 (2026-01-01)" ;;
  bin-paths) printf '/opt/tool-a/bin\\n/opt/tool-b/bin\\n' ;;
esac
[ "$*" != "${STUB_FAIL:-}" ]
"""
# Copies the requested release file from STUB_RELEASE, as `curl -fsSL -o <file> <url>` would.
STUB_CURL = """\
#!/bin/bash
url="${@: -1}"
echo "$url" >> "$STUB_CURL_LOG"
out=""
while [ $# -gt 0 ]; do
  case "$1" in -o) out="$2"; shift ;; esac
  shift
done
cp "$STUB_RELEASE/$(basename "$url")" "$out" 2>/dev/null || exit 22
"""


def _executable(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def _mise_version() -> str:
    match = re.search(r"^MISE_VERSION=(\S+)$", (TEMPLATE_DIR / HOOK).read_text(), re.MULTILINE)
    assert match
    return str(match.group(1))


def _archive_name(version: str) -> str:
    return f"mise-v{version}-linux-x64.tar.gz"


class Session:
    """A temporary home and environment for running the hook in a rendered consumer."""

    def __init__(self, consumer: Path, tmp_path: Path) -> None:
        """Lay out the stub `curl` and the hook's environment under `tmp_path`."""
        self.consumer = consumer
        self.home = tmp_path / "home"
        self.mise = self.home / ".local/bin/mise"
        self.log = tmp_path / "mise.log"
        self.curl_log = tmp_path / "curl.log"
        self.env_file = tmp_path / "claude.env"
        self.release = tmp_path / "release"
        self.bin = tmp_path / "bin"
        _executable(self.bin / "curl", STUB_CURL)
        self.env = {
            "HOME": str(self.home),
            "PATH": f"{self.bin}:/usr/bin:/bin",
            "CLAUDE_CODE_REMOTE": "true",
            "CLAUDE_PROJECT_DIR": str(consumer),
            "CLAUDE_ENV_FILE": str(self.env_file),
            "STUB_LOG": str(self.log),
            "STUB_CURL_LOG": str(self.curl_log),
            "STUB_RELEASE": str(self.release),
            "STUB_VERSION": _mise_version(),
        }

    def install_current_mise(self) -> None:
        """Put a stub mise at the hook's version where the hook looks for it."""
        _executable(self.mise, STUB_MISE)

    def publish_release(self, *, checksum_ok: bool = True, checksum_line: bool = True) -> None:
        """Lay out the release files the stub curl serves, with a stub mise inside the archive."""
        version = _mise_version()
        self.release.mkdir(parents=True, exist_ok=True)
        buffer = io.BytesIO()
        with tarfile.open(fileobj=buffer, mode="w:gz") as archive:
            data = STUB_MISE.encode()
            info = tarfile.TarInfo("mise/bin/mise")
            info.size = len(data)
            info.mode = 0o755
            archive.addfile(info, io.BytesIO(data))
        name = _archive_name(version)
        (self.release / name).write_bytes(buffer.getvalue())
        digest = hashlib.sha256(buffer.getvalue()).hexdigest() if checksum_ok else "0" * 64
        listed = name if checksum_line else "mise-other.tar.gz"
        (self.release / "SHASUMS256.txt").write_text(f"{digest}  ./{listed}\n")

    def run(self, **overrides: str | None) -> subprocess.CompletedProcess[str]:
        """Run the rendered hook, with `overrides` set in (or, as None, removed from) its env."""
        env = {**self.env, **overrides}
        return subprocess.run(  # noqa: S603
            [str(self.consumer / HOOK)],
            env={key: value for key, value in env.items() if value is not None},
            capture_output=True,
            text=True,
            check=False,
        )

    def mise_calls(self) -> list[list[str]]:
        """Each logged mise call as [path, working directory, auto-install setting, arguments]."""
        if not self.log.exists():
            return []
        return [line.split("|", 3) for line in self.log.read_text().splitlines()]


def _one_object(completed: subprocess.CompletedProcess[str]) -> dict[str, Any]:
    """The hook's stdout, which must be exactly one JSON object, after a zero exit."""
    assert completed.returncode == 0, completed.stderr
    parsed = json.loads(completed.stdout)
    assert isinstance(parsed, dict)
    return parsed


def _notice(completed: subprocess.CompletedProcess[str]) -> str:
    output = _one_object(completed)["hookSpecificOutput"]
    assert isinstance(output, dict)
    assert output["reloadSkills"] is True
    return str(output["additionalContext"])


@pytest.fixture
def session(consumer: Path, tmp_path: Path) -> Session:
    """A fresh home and environment for running the hook in the shared consumer."""
    return Session(consumer, tmp_path)


# @spec SESSION-REG-001
def test_settings_register_the_hook(consumer: Path) -> None:
    """The rendered settings file registers the hook for every session source."""
    settings = json.loads((consumer / ".claude/settings.json").read_text())
    assert settings == {
        "hooks": {"SessionStart": [{"hooks": [{"type": "command", "command": COMMAND}]}]}
    }


# @spec SESSION-REG-002
def test_hook_is_executable(consumer: Path) -> None:
    """Claude Code runs the hook directly, so it must be executable."""
    hook = consumer / HOOK
    assert hook.is_file()
    assert not hook.is_symlink()
    assert os.access(hook, os.X_OK)


# @spec SESSION-HOOK-001
@pytest.mark.parametrize("remote", [None, "false", "1"], ids=["unset", "false", "one"])
def test_does_nothing_outside_cloud_sessions(session: Session, remote: str | None) -> None:
    """Local sessions keep their own mise: no output and no mise commands."""
    session.install_current_mise()
    completed = session.run(CLAUDE_CODE_REMOTE=remote)
    assert completed.returncode == 0
    assert completed.stdout == ""
    assert session.mise_calls() == []


# @spec SESSION-HOOK-002
def test_keeps_a_current_mise(session: Session) -> None:
    """When the right mise is already installed, nothing is downloaded."""
    session.install_current_mise()
    _one_object(session.run())
    assert not session.curl_log.exists()


# @spec SESSION-HOOK-003
@pytest.mark.parametrize("installed", [None, "2020.1.1"], ids=["missing", "other-version"])
def test_downloads_the_pinned_release(session: Session, installed: str | None) -> None:
    """A missing or different mise is replaced from its GitHub release at the hook's version."""
    if installed is not None:
        session.install_current_mise()
        session.env["STUB_VERSION"] = installed
    session.publish_release()
    _one_object(session.run())
    version = _mise_version()
    base = f"https://github.com/jdx/mise/releases/download/v{version}"
    assert session.curl_log.read_text().splitlines() == [
        f"{base}/{_archive_name(version)}",
        f"{base}/SHASUMS256.txt",
    ]


# @spec SESSION-HOOK-010
def test_installs_a_verified_download(session: Session) -> None:
    """A download whose checksum matches becomes the hook's mise."""
    session.publish_release()
    assert _one_object(session.run()) == SUCCESS
    assert session.mise.read_text() == STUB_MISE


# @spec SESSION-HOOK-010
@pytest.mark.parametrize(
    "release",
    [{"checksum_ok": False}, {"checksum_line": False}, None],
    ids=["mismatch", "no-line", "download-fails"],
)
def test_rejects_an_unverified_download(session: Session, release: dict[str, bool] | None) -> None:
    """A mismatch, a missing checksum line or a failed download is "installing mise"."""
    if release is not None:
        session.publish_release(**release)
    notice = _notice(session.run())
    assert "installing mise" in notice
    assert not session.mise.exists()
    assert session.mise_calls() == []


# @spec SESSION-HOOK-004
def test_runs_the_steps_in_order(session: Session) -> None:
    """trust, apm, skills (without auto-install), then the other tools, by absolute path."""
    session.install_current_mise()
    _one_object(session.run())
    calls = [call for call in session.mise_calls() if call[3] not in {"--version", "bin-paths"}]
    words = [call[3].split() for call in calls]
    assert [args[0] for args in words] == ["trust", "install", "run", "install"]
    assert words[1] == ["install", "apm"]
    assert words[2] == ["run", "skills"]
    assert all(arg.startswith("-") for arg in words[3][1:])
    assert calls[2][2] == "false"
    for path, cwd, _auto, _args in calls:
        assert path == str(session.mise)
        assert cwd == str(session.consumer)


# @spec SESSION-HOOK-005
def test_writes_the_path_line(session: Session) -> None:
    """The env file gains a line putting mise and every tool first on PATH."""
    session.install_current_mise()
    _one_object(session.run())
    expected = f'export PATH="{session.home}/.local/bin:/opt/tool-a/bin:/opt/tool-b/bin:$PATH"'
    assert session.env_file.read_text().splitlines() == [expected]


# @spec SESSION-HOOK-011
def test_writes_the_path_line_once(session: Session) -> None:
    """A second run in the same container doesn't repeat the line."""
    session.install_current_mise()
    _one_object(session.run())
    _one_object(session.run())
    assert len(session.env_file.read_text().splitlines()) == 1


# @spec SESSION-HOOK-006
def test_success_prints_the_reload_object(session: Session) -> None:
    """A clean run prints only the object asking Claude Code to reload skills."""
    session.install_current_mise()
    assert _one_object(session.run()) == SUCCESS


# @spec SESSION-HOOK-007
@pytest.mark.parametrize(
    ("failing", "named"),
    [
        ("trust --quiet", "at: mise trust."),
        ("install apm", "at: mise install apm."),
        ("run skills", "at: mise run skills."),
        ("install --quiet", "at: mise install."),
    ],
)
def test_a_failed_step_stops_the_hook(session: Session, failing: str, named: str) -> None:
    """A failing step is named, with mise's path, and no later step runs."""
    session.install_current_mise()
    notice = _notice(session.run(STUB_FAIL=failing))
    assert named in notice
    assert str(session.mise) in notice
    steps = [call[3] for call in session.mise_calls() if call[3] != "--version"]
    assert steps[-1] == failing
    assert "bin-paths" not in steps


# @spec SESSION-HOOK-008
@pytest.mark.parametrize("variable", ["CLAUDE_PROJECT_DIR", "CLAUDE_ENV_FILE"])
def test_a_missing_variable_is_a_failed_step(session: Session, variable: str) -> None:
    """An unset project directory or env file is reported by name."""
    session.install_current_mise()
    assert variable in _notice(session.run(**{variable: None}))


# @spec SESSION-HOOK-008
def test_a_missing_project_directory_is_a_failed_step(session: Session, tmp_path: Path) -> None:
    """A project directory that doesn't exist is reported by name."""
    session.install_current_mise()
    notice = _notice(session.run(CLAUDE_PROJECT_DIR=str(tmp_path / "missing")))
    assert "CLAUDE_PROJECT_DIR" in notice


# @spec SESSION-HOOK-009
def test_a_signal_still_reports(session: Session) -> None:
    """If the hook is terminated mid-step, the exit trap prints the object and exits 0."""
    session.install_current_mise()
    assert "stopped unexpectedly" in _notice(session.run(STUB_KILL="install apm"))


# @spec SESSION-HOOK-009
def test_an_unset_home_still_reports(session: Session) -> None:
    """Without HOME the hook can't place mise, and still prints the object and exits 0."""
    assert "HOME" in _notice(session.run(HOME=None))


# @spec SESSION-HOOK-012
@pytest.mark.parametrize("overrides", [{}, {"STUB_FAIL": "install apm"}], ids=["ok", "failure"])
def test_prints_one_object(session: Session, overrides: dict[str, str]) -> None:
    """Every run prints exactly one JSON object, on one line."""
    session.install_current_mise()
    completed = session.run(**overrides)
    assert len(completed.stdout.strip().splitlines()) == 1
    _one_object(completed)


def _ci_mise_version() -> str:
    workflow = yaml.safe_load((REPO_ROOT / ".github/workflows/ci.yml").read_text())
    versions = [
        str(step["with"]["version"])
        for job in workflow["jobs"].values()
        for step in job["steps"]
        if str(step.get("uses", "")).startswith("jdx/mise-action@")
    ]
    assert len(versions) == 1
    return versions[0]


# @spec SESSION-MISE-001
def test_hook_mise_matches_ci() -> None:
    """The hook installs the mise this repo's CI uses, written without a `v`."""
    assert re.fullmatch(r"\d+\.\d+\.\d+", _mise_version())
    assert _mise_version() == _ci_mise_version()


# @spec SESSION-MISE-002
def test_hook_mise_meets_the_minimum() -> None:
    """The hook's mise satisfies the fragment's `min_version`."""
    minimum = tomllib.loads((TEMPLATE_DIR / FRAGMENT).read_text())["min_version"]

    def key(value: str) -> tuple[int, ...]:
        return tuple(int(part) for part in value.split("."))

    assert key(_mise_version()) >= key(minimum)


def _python_regex(pattern: str) -> str:
    """Translate JavaScript named groups `(?<name>` to Python's `(?P<name>`."""
    return re.sub(r"\(\?<(?=[A-Za-z_])", "(?P<", pattern)


# @spec SESSION-MISE-003
def test_renovate_bumps_the_hook_with_ci() -> None:
    """A regex manager reads the hook's version as the dependency mise-action's input uses."""
    config = json.loads((REPO_ROOT / ".github/renovate.json").read_text())
    path = f"template/{HOOK}"
    hook_text = (TEMPLATE_DIR / HOOK).read_text()
    managers = [
        manager
        for manager in config.get("customManagers", [])
        if any(
            re.search(_python_regex(pattern.strip("/")), path)
            for pattern in manager["managerFilePatterns"]
        )
    ]
    assert len(managers) == 1
    manager = managers[0]
    assert manager["depNameTemplate"] == "jdx/mise"
    assert manager["datasourceTemplate"] == "github-release-attachments"
    values = [
        match.group("currentValue")
        for pattern in manager["matchStrings"]
        for match in re.finditer(_python_regex(pattern), hook_text)
    ]
    assert values == [_mise_version()]
