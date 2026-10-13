# /// script
# requires-python = ">=3.11"
# ///
"""List every named exception to the strict profile in this repo, followed by the total.

Owned by the copier-python template; run it with `mise run exceptions`. It reports and
always exits 0.
"""

from __future__ import annotations

import io
import re
import subprocess
import tokenize
import tomllib
from pathlib import Path
from typing import Any

TEMPLATE_DIR = ".config/copier-python/"
REPO_RUFF_FILE = ".ruff.toml"
RUFF_CONFIG_NAMES = {"ruff.toml", ".ruff.toml"}
# ruff accepts codes separated by commas, spaces or both.
CODES = r"[A-Za-z]+[0-9]+(?:(?:\s*,\s*|\s+)[A-Za-z]+[0-9]+)*"
# `#` must directly precede `noqa`, so a `# ruff: noqa:` comment never matches this too.
LINE_NOQA = re.compile(rf"#\s*noqa\s*:\s*(?P<codes>{CODES})", re.IGNORECASE)
FILE_NOQA = re.compile(rf"#\s*(?:ruff|flake8)\s*:\s*noqa\s*:\s*(?P<codes>{CODES})", re.IGNORECASE)
TY_IGNORE = re.compile(r"#\s*ty\s*:\s*ignore\[(?P<codes>[^\]]*)\]")
TYPE_IGNORE = re.compile(r"#\s*type\s*:\s*ignore\b")


def tracked_files() -> list[str]:
    """Return the repo's tracked files outside the template's own directory."""
    listing = subprocess.run(
        ["git", "ls-files", "-z"],  # noqa: S607
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return [name for name in listing.split("\0") if name and not name.startswith(TEMPLATE_DIR)]


def split_codes(text: str) -> list[str]:
    """Split a list of rule codes separated by commas and/or spaces."""
    return [code for code in re.split(r"[\s,]+", text) if code]


def scan_python(path: str) -> tuple[list[str], list[str]]:
    """Return the exceptions and dead `# type: ignore` locations in one Python file.

    Raises:
        tokenize.TokenError: If the file can't be tokenized.
        SyntaxError: If the tokenizer rejects the file.
        OSError: If the file can't be read, for example tracked but deleted.
    """
    found: list[str] = []
    dead: list[str] = []
    source = Path(path).read_text(encoding="utf-8", errors="replace")
    for token in tokenize.generate_tokens(io.StringIO(source).readline):
        if token.type != tokenize.COMMENT:
            continue
        line = token.start[0]
        comment = token.string
        for match in FILE_NOQA.finditer(comment):
            found += [f"{path}:{line}: {code.upper()}" for code in split_codes(match["codes"])]
        for match in LINE_NOQA.finditer(comment):
            found += [f"{path}:{line}: {code.upper()}" for code in split_codes(match["codes"])]
        for match in TY_IGNORE.finditer(comment):
            found += [f"{path}:{line}: {code}" for code in split_codes(match["codes"])]
        if TYPE_IGNORE.search(comment):
            dead.append(f"{path}:{line}")
    return found, dead


def leaf_settings(table: dict[str, Any], prefix: str = "") -> list[tuple[str, Any]]:
    """Flatten a TOML table into (dotted key, value) pairs for its leaf keys."""
    leaves: list[tuple[str, Any]] = []
    for key, value in table.items():
        dotted = f"{prefix}{key}"
        if isinstance(value, dict):
            leaves += leaf_settings(value, f"{dotted}.")
        else:
            leaves.append((dotted, value))
    return leaves


def scan_repo_ruff_file() -> list[str]:
    """Return the exceptions recorded in the repo's own ruff file."""
    path = Path(REPO_RUFF_FILE)
    if not path.is_file():
        return []
    config = tomllib.loads(path.read_text(encoding="utf-8"))
    found: list[str] = []
    per_file = config.get("lint", {}).get("extend-per-file-ignores", {})
    for pattern, rules in per_file.items():
        found += [
            f"{REPO_RUFF_FILE}: lint.extend-per-file-ignores: {pattern}: {rule}" for rule in rules
        ]
    for key, value in leaf_settings(config):
        if key == "extend" or key.startswith("lint.extend-per-file-ignores."):
            continue
        entries = value if isinstance(value, list) else [value]
        found += [f"{REPO_RUFF_FILE}: {key}: {entry}" for entry in entries]
    return found


def is_nested_ruff_config(path: str) -> bool:
    """Whether a tracked file below the root is a ruff config of its own."""
    name = Path(path).name
    if "/" not in path:
        return False
    if name in RUFF_CONFIG_NAMES:
        return True
    if name != "pyproject.toml":
        return False
    try:
        return "ruff" in tomllib.loads(Path(path).read_text(encoding="utf-8")).get("tool", {})
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError):
        return False


def main() -> None:
    """Print every named exception, the total, and any dead suppressions."""
    found: list[str] = []
    dead: list[str] = []
    notes: list[str] = []
    for path in tracked_files():
        if path.endswith((".py", ".pyi")):
            try:
                file_found, file_dead = scan_python(path)
            except (OSError, tokenize.TokenError, SyntaxError):
                notes.append(f"{path}: unreadable")
                continue
            found += file_found
            dead += file_dead
        elif is_nested_ruff_config(path):
            found.append(f"{path}: nested ruff config")
    found += scan_repo_ruff_file()
    for line in [*notes, *found]:
        print(line)  # noqa: T201
    print(f"Total: {len(found)}")  # noqa: T201
    if dead:
        print("Dead suppressions:")  # noqa: T201
        for line in dead:
            print(line)  # noqa: T201


if __name__ == "__main__":
    main()
