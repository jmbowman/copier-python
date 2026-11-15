# /// script
# requires-python = ">=3.11"
# ///
"""Fail while the repo's LID major.minor differs from the one its APM lock file pins.

Owned by the copier-python template; run it with `mise run lid-version`. It compares the
`- Version:` bullet in the `## LID` block of the instruction file (AGENTS.md if it exists,
otherwise CLAUDE.md) with the `version` of the lock file's linked-intent-dev entry, by
major.minor, as LID does. A template update that bumps LID's minor or major version fails here
until someone runs `/update-lid` on its branch; a patch bump passes.

It reads the lock file as APM writes it, with the standard library only: a top-level
`dependencies:` list, one `- ` item per package, its scalar fields indented two spaces.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

DEFAULT_LOCK = Path(".config/copier-python/apm.lock.yaml")
INSTRUCTION_FILES = (Path("AGENTS.md"), Path("CLAUDE.md"))
LID_REPO = "jszmajda/lid"
LID_PLUGIN = "plugins/linked-intent-dev"
FIELD = re.compile(r"(?P<key>[A-Za-z_][A-Za-z0-9_]*):(?P<value>.*)")
VERSION_BULLET = re.compile(r"- Version:(?P<value>.*)")
MAJOR_MINOR = re.compile(r"([0-9]+)\.([0-9]+)(?:\.|\Z)")


class GateError(Exception):
    """A problem that fails the gate, described in one line."""


def value(text: str) -> str:
    """Return a field's value: trimmed, with one pair of matching surrounding quotes removed."""
    text = text.strip()
    if len(text) > 1 and text[0] == text[-1] and text[0] in {"'", '"'}:
        return text[1:-1]
    return text


def read_lines(path: Path, what: str) -> list[str]:
    """Return a UTF-8 file's lines, or fail the gate naming the file."""
    try:
        return path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError) as error:
        reason = error.strerror if isinstance(error, OSError) else "not UTF-8 text"
        msg = f"can't read {what} {path}: {reason}"
        raise GateError(msg) from error


def lock_dependencies(lock: Path) -> list[dict[str, list[str]]]:
    """Return each scalar field's values, in order, per item of the lock's `dependencies` list."""
    lines = read_lines(lock, "the lock file")
    items: list[dict[str, list[str]]] = []
    in_dependencies = False
    for line in lines:
        if not in_dependencies:
            in_dependencies = line.rstrip() == "dependencies:"
            continue
        body = line
        if line.startswith("- "):
            items.append({})
            body = "  " + line[2:]  # An item's first field sits on its `- ` line.
        elif line and not line.startswith(" "):
            break  # The next top-level key ends the list.
        # Scalar fields sit at exactly two spaces; nested list items and deeper lines don't.
        scalar = body.startswith("  ") and not body.startswith(("   ", "  - "))
        field = FIELD.fullmatch(body[2:]) if scalar else None
        if items and field and field.group("value").strip():
            items[-1].setdefault(field.group("key"), []).append(value(field.group("value")))
    return items


def locked_lid_version(lock: Path) -> str:
    """Return the version of the lock file's linked-intent-dev entry."""
    entries = [
        item
        for item in lock_dependencies(lock)
        if item.get("repo_url") == [LID_REPO] and item.get("virtual_path") == [LID_PLUGIN]
    ]
    if len(entries) != 1:
        found = "no" if not entries else str(len(entries))
        msg = f"{lock} has {found} {LID_REPO} {LID_PLUGIN} entries; expected one"
        raise GateError(msg)
    versions = entries[0].get("version", [])
    if len(versions) != 1:
        found = "no" if not versions else str(len(versions))
        msg = f"{lock}'s {LID_REPO} {LID_PLUGIN} entry has {found} `version` fields; expected one"
        raise GateError(msg)
    return versions[0]


def major_minor(version: str) -> str | None:
    """Return a version's first two dot-separated parts, as text, or None if it has none.

    `1.4.0`, `1.4` and `1.5.0-rc.1` give `1.4`, `1.4` and `1.5`; `v1.4.0`, `1` and `1.4-rc`
    give None. The parts are compared as text, so `01.4` and `1.4` differ.
    """
    match = MAJOR_MINOR.match(version)
    return f"{match[1]}.{match[2]}" if match else None


def version_problem(instructions: Path, declared: str, lock: Path, locked: str) -> str | None:
    """Return the gate's one-line failure for the two versions, or None if they agree."""
    unreadable = [
        f"{path}'s LID version {version!r}"
        for path, version in ((instructions, declared), (lock, locked))
        if major_minor(version) is None
    ]
    if unreadable:
        verb = "has" if len(unreadable) == 1 else "have"
        return f"{' and '.join(unreadable)} {verb} no major.minor"
    if major_minor(declared) != major_minor(locked):
        return (
            f"{instructions} declares LID {declared}, but the lock file pins {locked}, "
            "a different major.minor; run /update-lid"
        )
    return None


def instruction_file(option: Path | None) -> Path:
    """Return the instruction file to read: the option's, or AGENTS.md, or CLAUDE.md."""
    if option is not None:
        if not option.is_file():
            msg = f"no instruction file: {option} doesn't exist"
            raise GateError(msg)
        return option
    for candidate in INSTRUCTION_FILES:
        if candidate.is_file():
            return candidate
    msg = "no instruction file: neither AGENTS.md nor CLAUDE.md exists"
    raise GateError(msg)


def declared_lid_version(instructions: Path) -> str:
    """Return the `- Version:` value in the file's single `## LID` block."""
    blocks: list[list[str]] = []
    current: list[str] | None = None
    for line in read_lines(instructions, "the instruction file"):
        if line == "## LID":
            current = []
            blocks.append(current)
        elif line.startswith(("# ", "## ")):
            current = None
        elif current is not None:
            current.append(line)
    if len(blocks) != 1:
        found = "no" if not blocks else str(len(blocks))
        msg = f"{instructions} has {found} `## LID` blocks; expected one"
        raise GateError(msg)
    bullets = [match for line in blocks[0] if (match := VERSION_BULLET.fullmatch(line.rstrip()))]
    if len(bullets) != 1:
        found = "no" if not bullets else str(len(bullets))
        msg = f"{instructions}'s `## LID` block has {found} `- Version:` bullets; expected one"
        raise GateError(msg)
    return value(bullets[0].group("value"))


def main() -> None:
    """Compare the two versions, and exit 1 with one line on stderr if the gate fails."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--lock", type=Path, default=DEFAULT_LOCK)
    parser.add_argument("--instructions", type=Path)
    args = parser.parse_args()
    try:
        instructions = instruction_file(args.instructions)
        declared = declared_lid_version(instructions)
        locked = locked_lid_version(args.lock)
    except GateError as error:
        sys.stderr.write(f"{error}\n")
        sys.exit(1)
    problem = version_problem(instructions, declared, args.lock, locked)
    if problem is not None:
        sys.stderr.write(f"{problem}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
