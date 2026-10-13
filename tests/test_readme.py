"""Tests of the template's README."""

from __future__ import annotations

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
