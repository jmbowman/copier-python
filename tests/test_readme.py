"""Tests of the template's README."""

from __future__ import annotations

import re

from tests.support import REPO_ROOT

ONBOARDING_TOPICS = (
    "shadow",
    "record",
    "--vcs-ref",
    "mise trust",
    "mise run setup",
    "mise run fix",
    "commit",
    "Allow auto-merge",
    "branch rule",
)


def _sections() -> dict[str, str]:
    sections: dict[str, str] = {}
    heading = ""
    for line in (REPO_ROOT / "README.md").read_text().splitlines():
        if line.startswith("## "):
            heading = line.removeprefix("## ").strip().lower()
            sections[heading] = ""
        elif heading:
            sections[heading] += line + "\n"
    return sections


# @spec FILES-DOC-001
def test_readme_documents_preconditions_onboarding_and_fresh_clones() -> None:
    """The README has sections for preconditions, onboarding and setting up a fresh clone."""
    sections = _sections()

    def section(title: str) -> str:
        matches = [body for heading, body in sections.items() if title in heading]
        assert len(matches) == 1, (title, list(sections))
        return matches[0]

    assert section("precondition")
    onboarding = section("onboarding")
    for topic in ONBOARDING_TOPICS:
        assert topic in onboarding, topic
    assert "mise run setup" in section("fresh clone")


LOCK_REFRESH_TOPICS = (
    "mise lock",
    "Contents: read and write",
    "LOCK_REFRESH_APP_PRIVATE_KEY",
    "copier update --data lock_refresh_app_client_id=",
)


# @spec FILES-DOC-002
def test_readme_documents_lock_files_and_the_lock_refresh_app() -> None:
    """Onboarding covers committing lock files and setting up the lock-refresh App."""
    onboarding = next(body for heading, body in _sections().items() if "onboarding" in heading)
    for topic in LOCK_REFRESH_TOPICS:
        assert topic in onboarding, topic


SKILLS_TOPICS = (
    "LID",
    "lock file",
    "mise run setup",
    "mise run check",
    "session hook",
    ".config/copier-python/.claude/skills/",
    "skills/<name>/",
    ".claude/skills/",
    ".agents/skills/",
    "apm.yml",
    "gitignore",
    "reserved",
)
SKILLS_ONBOARDING_TOPICS = (
    ".claude/skills",
    ".agents/skills",
    "same name",
    ".claude/settings.json",
)
HOOK_TOPICS = ("cloud session", ".claude/settings.json", "remov")


def _section(title: str) -> str:
    matches = [body for heading, body in _sections().items() if title in heading]
    assert len(matches) == 1, (title, list(_sections()))
    return matches[0]


# @spec FILES-DOC-003
def test_readme_documents_the_skills() -> None:
    """A skills section covers the template's skills and a repo's own; onboarding checks both."""
    sections = _sections()
    skills = [body for heading, body in sections.items() if "skills" in heading]
    assert len(skills) == 1, list(sections)
    for topic in SKILLS_TOPICS:
        assert topic in skills[0], topic
    onboarding = next(body for heading, body in sections.items() if "onboarding" in heading)
    for topic in SKILLS_ONBOARDING_TOPICS:
        assert topic in onboarding, topic


# @spec FILES-DOC-004
def test_readme_requires_lid() -> None:
    """The README says the template requires LID, and onboarding runs `/update-lid` after setup."""
    readme = (REPO_ROOT / "README.md").read_text()
    assert re.search(r"requires? LID", readme)
    onboarding = _section("onboarding")
    assert "/update-lid" in onboarding
    assert onboarding.index("mise run setup") < onboarding.index("/update-lid")


# @spec FILES-DOC-005
def test_readme_describes_the_session_hook() -> None:
    """The README covers what the hook installs, where it's registered, and how to opt out."""
    hook = _section("session hook")
    for topic in HOOK_TOPICS:
        assert topic in hook, topic
