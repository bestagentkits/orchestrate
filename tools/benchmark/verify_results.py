#!/usr/bin/env python3
"""Independently re-check a run's reported cost against its raw session files.

The headline metric is cost per task, and it is computed by the same program
that records the result - so a bug there is invisible from the outside. This
script recomputes every trial's cost straight from the session JSONL and
compares it with the recorded figure, which is what catches an accounting
mistake instead of trusting one.

Attribution uses the recorded `sessionPaths` when present. Older runs that lack
them are reconstructed by walking session files in name order, which is
chronological because their names begin with an ISO-8601 timestamp; that
reconstruction is only valid for a sequentially executed run, so the script says
so when it falls back.

Usage:
    python3 -m tools.benchmark.verify_results <out-directory>
"""

from __future__ import annotations

import json
import os
import sys

from tools.benchmark.measure import as_float, as_int
from tools.benchmark.run_benchmark import combine, session_file_stats, session_files

USAGE = "usage: python3 -m tools.benchmark.verify_results <out-directory>"
TOLERANCE = 1e-6


def load(records_path: str) -> list[dict]:
    records = []
    try:
        with open(records_path, encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    except OSError as exc:
        raise SystemExit(f"cannot read {records_path}: {exc}") from exc
    return records


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        print(USAGE, file=sys.stderr)
        return 2
    out_dir = os.path.abspath(argv[0])
    records = load(os.path.join(out_dir, "results.jsonl"))
    stats = session_files(os.path.join(out_dir, "sessions"))
    if not records:
        raise SystemExit("no results to verify")
    if not stats:
        raise SystemExit("no session files to verify against")

    measured = [r for r in records if r.get("status") != "skipped"]
    explicit = all(r.get("sessionPaths") for r in measured)
    if not explicit:
        print("NOTE: no sessionPaths recorded; reconstructing attribution by name")
        print("      order, which is only valid because the run was sequential\n")

    # A recorded cost includes any session file a dispatch wrote inside the trial
    # workspace after escaping the shim. Those files live outside the run's
    # session directory, so they must be added to the pool or a legitimate
    # escape would be reported as a mismatch.
    pool = dict(stats)
    escaped_paths = [p for r in measured for p in (r.get("escapedSessionPaths") or [])]
    for path in escaped_paths:
        if os.path.exists(path) and path not in pool:
            pool[path] = session_file_stats(path)
    if escaped_paths:
        print(f"NOTE: {len(escaped_paths)} escaped session file(s) included in the check\n")

    ordered = sorted(stats)
    cursor = 0
    mismatches = 0
    checked = 0
    for record in measured:
        if explicit:
            recorded = list(record["sessionPaths"]) + list(record.get("escapedSessionPaths") or [])
            paths = [p for p in recorded if p in pool]
            missing = len(recorded) - len(paths)
            if missing:
                print(f"  WARN {record['taskId']}: {missing} recorded session file(s) missing")
        else:
            count = as_int(record.get("sessionFiles") or 0)
            paths = ordered[cursor : cursor + count]
            cursor += count

        recomputed = combine(pool, paths)["costUsd"]
        claimed = as_float(record.get("costUsd"))
        checked += 1
        if abs(recomputed - claimed) > TOLERANCE:
            mismatches += 1
            print(
                f"  MISMATCH {record['variant']:12} {record['taskId']:22} "
                f"claimed=${claimed:.6f} recomputed=${recomputed:.6f}"
            )

    total = combine(pool, list(pool))["costUsd"]
    attributed = sum(as_float(r.get("costUsd")) for r in measured)
    print(f"\ntrials checked      : {checked}")
    print(f"cost mismatches     : {mismatches}")
    print(f"recorded total      : ${attributed:.6f}")
    print(f"recomputed total    : ${total:.6f}")
    if not explicit and cursor < len(ordered):
        print(f"unattributed sessions: {len(ordered) - cursor} (expected if a trial was killed)")
    if mismatches:
        print("\nRESULT: REJECTED - recorded costs do not match the raw sessions")
        return 1
    print("\nRESULT: verified - recorded costs reproduce from the raw sessions")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
