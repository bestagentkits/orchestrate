#!/usr/bin/env python3
"""Pack the taskflow fixture into a single hashable payload.

The fixture is intentionally-broken sample code whose defects are the subject
of the benchmark tasks. Keeping it as one JSON payload rather than as loose
source files does two things: static analysis tools do not report the planted
defects as if they were real repository problems, and the exact bytes handed to
an agent become pinnable by digest, so a reported result can name the fixture it
was measured against.

Usage:
    python3 tools/benchmark/build_fixture.py <source-dir> <output.json>

``<source-dir>`` must contain ``taskflow/`` (the agent-visible workspace) and
``tests/`` (the graders, extracted only at scoring time).
"""

from __future__ import annotations

import hashlib
import json
import os
import sys

FIXTURE_ID = "taskflow"
FIXTURE_VERSION = "1.0.0"
WORKSPACE_DIR = "taskflow"
GRADER_DIR = "tests"
USAGE = "usage: python3 tools/benchmark/build_fixture.py <source-dir> <output.json>"


def read_text(path: str) -> str:
    """Read a UTF-8 file, reporting an unreadable path without a traceback."""
    try:
        with open(path, encoding="utf-8") as handle:
            return handle.read()
    except OSError as exc:
        raise SystemExit(f"cannot read {path}: {exc}") from exc


def write_text(path: str, text: str) -> None:
    """Write a UTF-8 file, creating its parent directory if needed."""
    try:
        parent = os.path.dirname(os.path.abspath(path)) or "."
        os.makedirs(parent, exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)
    except OSError as exc:
        raise SystemExit(f"cannot write {path}: {exc}") from exc


def collect(source: str, relative: str) -> dict[str, str]:
    """Return every file under ``source/relative`` keyed by its relative path."""
    base = os.path.join(source, relative)
    if not os.path.isdir(base):
        return {}
    files: dict[str, str] = {}
    for current, _dirs, names in os.walk(base):
        for name in sorted(names):
            if name.endswith(".pyc"):
                continue
            absolute = os.path.join(current, name)
            files[os.path.relpath(absolute, source)] = read_text(absolute)
    return dict(sorted(files.items()))


def digest(files: dict[str, str]) -> str:
    """Hash a file map so the same fixture always yields the same digest."""
    hasher = hashlib.sha256()
    for path, content in sorted(files.items()):
        hasher.update(path.encode("utf-8"))
        hasher.update(b"\0")
        hasher.update(content.encode("utf-8"))
        hasher.update(b"\0")
    return hasher.hexdigest()


def build(source: str) -> dict:
    """Return the fixture payload for ``source``."""
    workspace = collect(source, WORKSPACE_DIR)
    graders = collect(source, GRADER_DIR)
    if not workspace:
        raise SystemExit(f"no workspace files found under {source}/{WORKSPACE_DIR}")
    if not graders:
        raise SystemExit(f"no grader files found under {source}/{GRADER_DIR}")
    return {
        "id": FIXTURE_ID,
        "version": FIXTURE_VERSION,
        "workspaceDigest": digest(workspace),
        "graderDigest": digest(graders),
        "workspace": workspace,
        "graders": graders,
    }


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(USAGE, file=sys.stderr)
        return 2
    source, destination = argv
    if not destination.endswith(".json"):
        print(f"destination must end in .json: {destination}", file=sys.stderr)
        return 2

    payload = build(source)
    write_text(destination, json.dumps(payload, indent=2) + "\n")

    print(f"workspace files : {len(payload['workspace'])}")
    print(f"grader files    : {len(payload['graders'])}")
    print(f"workspaceDigest : {payload['workspaceDigest']}")
    print(f"graderDigest    : {payload['graderDigest']}")
    print(f"written         : {destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
