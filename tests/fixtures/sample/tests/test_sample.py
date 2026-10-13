"""Tests for `sample.add`."""

from sample import add


def test_add() -> None:
    """Adding two integers returns their sum."""
    assert add(2, 3) == 5
