"""Pytest fixtures shared by the template's tests."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from tests.support import consumer_repo, template_repo

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture(scope="module")
def template(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A throwaway git copy of this template, tagged `v1.0.0`."""
    return template_repo(tmp_path_factory.mktemp("template") / "repo")


@pytest.fixture(scope="module")
def consumer(template: Path, tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A consumer rendered from `template` at `v1.0.0` with default answers and committed."""
    return consumer_repo(template, tmp_path_factory.mktemp("consumer") / "repo")
