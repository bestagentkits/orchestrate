#!/usr/bin/env python3
"""Independently re-check a run's accounting against its raw session files.

The headline metric is cost per task, and it is computed by the same program that records
the result - so a bug there is invisible from the outside. This script recomputes every
trial's attributable cost, tokens and nested-dispatch cost straight from the session JSONL,
compares them with the recorded figures, and checks the component split in `trials.jsonl`
against the recomputed total.

It also reports cost that **no trial claims**. That is the audit's second job: a dispatch
that outlives its parent trial keeps writing to its session file after the trial was
snapshotted, so the leftover is attributed to nothing. Treating that leftover as acceptable
would understate whichever arm happened to dispatch more.

Attribution uses the recorded `sessionPaths` when present. Older runs that lack them are
reconstructed by walking session files in name order, which is chronological because their
names begin with an ISO-8601 timestamp; that reconstruction is only valid for a sequentially
executed run, so the script says so when it falls back.

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

#: The component fields a full-schema trial record carries.
COMPONENTS = ("coordinatorCostUsd", "workerCostUsd", "classifierCostUsd", "arbiterCostUsd")

#: Leftover cost below this is rounding, not a missing trial.
UNATTRIBUTED_TOLERANCE = 0.01


def load(records_path: str) -> list[dict]:
    """Read a JSONL file, skipping blank and malformed lines."""
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


def _load_trials(out_dir: str) -> dict:
    """Full-schema trial records keyed by (taskId, variant, trial), when the file exists."""
    path = os.path.join(out_dir, "trials.jsonl")
    if not os.path.exists(path):
        return {}
    keyed = {}
    for record in load(path):
        keyed[(record.get("taskId"), record.get("variant"), record.get("trial"))] = record
    return keyed


def _trial_paths(record: dict, pool: dict) -> tuple[list[str], int]:
    recorded = list(record.get("sessionPaths") or []) + list(record.get("escapedSessionPaths") or [])
    paths = [p for p in recorded if p in pool]
    return paths, len(recorded) - len(paths)


def audit_run(out_dir: str, tolerance: float = TOLERANCE) -> dict:
    """Recompute a run's accounting and return the verdict with its evidence.

    Nothing here trusts a recorded figure: every number is rebuilt from the session files,
    and each recorded figure is compared against the rebuilt one.
    """
    out_dir = os.path.abspath(out_dir)
    records = load(os.path.join(out_dir, "results.jsonl"))
    stats = session_files(os.path.join(out_dir, "sessions"))
    if not records:
        raise SystemExit("no results to verify")
    if not stats:
        raise SystemExit("no session files to verify against")

    measured = [r for r in records if r.get("status") != "skipped"]
    skipped = [r for r in records if r.get("status") == "skipped"]
    explicit = all(r.get("sessionPaths") for r in measured)
    trials = _load_trials(out_dir)

    # A recorded cost includes any session file a dispatch wrote inside the trial workspace
    # after escaping the shim. Those files live outside the run's session directory, so they
    # must join the pool or a legitimate escape would be reported as a mismatch.
    pool = dict(stats)
    escaped_paths = [p for r in measured for p in (r.get("escapedSessionPaths") or [])]
    for path in escaped_paths:
        if os.path.exists(path) and path not in pool:
            pool[path] = session_file_stats(path)

    problems: list[str] = []
    warnings: list[str] = []
    ordered = sorted(stats)
    cursor = 0
    mismatches = 0
    checked = 0
    token_mismatches = 0
    component_mismatches = 0
    claimed_paths: set = set()

    for record in measured:
        if explicit:
            paths, missing = _trial_paths(record, pool)
            if missing:
                warnings.append(f"{record.get('taskId')}: {missing} recorded session file(s) missing")
        else:
            count = as_int(record.get("sessionFiles") or 0)
            paths = ordered[cursor : cursor + count]
            cursor += count
        claimed_paths.update(paths)

        rebuilt = combine(pool, paths)
        claimed_cost = as_float(record.get("costUsd"))
        checked += 1
        if abs(rebuilt["costUsd"] - claimed_cost) > tolerance:
            mismatches += 1
            problems.append(
                f"cost:{record.get('taskId')}: claimed={claimed_cost:.6f} "
                f"recomputed={rebuilt['costUsd']:.6f}"
            )

        # Tokens, recomputed from the same raw records.
        recorded_tokens = record.get("tokens") or {}
        for field, rebuilt_value in rebuilt["tokens"].items():
            recorded_value = as_int(recorded_tokens.get(field))
            if as_int(rebuilt_value) != recorded_value:
                token_mismatches += 1
                problems.append(
                    f"tokens:{record.get('taskId')}:{field}: recorded={recorded_value} "
                    f"recomputed={as_int(rebuilt_value)}"
                )

        # Nested dispatch: every `pi` invocation writes its own session file, so a settled
        # trial has one file for the top-level run plus one per dispatch. Fewer files than
        # that means a dispatch outlived the snapshot and its cost went unattributed.
        dispatches = as_int(record.get("dispatches"))
        if explicit and len(paths) < dispatches + 1:
            warnings.append(
                f"{record.get('taskId')}: {len(paths)} session file(s) for "
                f"{dispatches} dispatch(es); a dispatch may have outlived the snapshot"
            )

        # Component totals, when the full-schema record exists.
        trial = trials.get((record.get("taskId"), record.get("variant"), record.get("trial")))
        if trial is not None:
            parts = [trial.get(name) for name in COMPONENTS]
            numeric_parts = [
                part for part in parts
                if isinstance(part, (int, float)) and not isinstance(part, bool)
            ]
            trial_total = trial.get("totalCostUsd")
            if (len(numeric_parts) == len(parts)
                    and isinstance(trial_total, (int, float))
                    and not isinstance(trial_total, bool)):
                component_total = 0
                for part in numeric_parts:
                    component_total += part
                if abs(component_total - trial_total) > tolerance:
                    component_mismatches += 1
                    problems.append(
                        f"components:{record.get('taskId')}: split={component_total:.6f} "
                        f"total={trial_total:.6f}"
                    )
                if abs(component_total - rebuilt["costUsd"]) > tolerance:
                    component_mismatches += 1
                    problems.append(
                        f"components-vs-sessions:{record.get('taskId')}: "
                        f"components={component_total:.6f} sessions={rebuilt['costUsd']:.6f}"
                    )

    unattributed = [p for p in ordered if p not in claimed_paths]
    unattributed_cost = combine(stats, unattributed)["costUsd"] if unattributed else 0.0

    total = combine(pool, list(pool))["costUsd"]
    attributed = sum(as_float(r.get("costUsd")) for r in measured)

    # Unattributed cost means a session file belongs to no trial. Below the tolerance it is
    # rounding; above it, some trial's cost is understated and the run is not auditable.
    if unattributed_cost > UNATTRIBUTED_TOLERANCE:
        problems.append(
            f"unattributed-cost={unattributed_cost:.6f} across {len(unattributed)} file(s)"
        )

    if not explicit and cursor < len(ordered):
        warnings.append(f"{len(ordered) - cursor} unattributed session(s) (expected if a trial was killed)")

    return {
        "outDir": out_dir,
        "checked": checked,
        "skipped": len(skipped),
        "mismatches": mismatches,
        "tokenMismatches": token_mismatches,
        "componentMismatches": component_mismatches,
        "recordedTotal": attributed,
        "recomputedTotal": total,
        "unattributedCost": unattributed_cost,
        "unattributedFiles": len(unattributed),
        "problems": problems,
        "warnings": warnings,
        "verdict": "rejected" if problems else "verified",
    }


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        print(USAGE, file=sys.stderr)
        return 2
    result = audit_run(argv[0])

    for warning in result["warnings"]:
        print(f"  WARN {warning}")
    if result["warnings"]:
        print()

    print(f"trials checked      : {result['checked']} (skipped {result['skipped']})")
    print(f"cost mismatches     : {result['mismatches']}")
    print(f"token mismatches    : {result['tokenMismatches']}")
    print(f"component mismatches: {result['componentMismatches']}")
    print(f"recorded total      : ${result['recordedTotal']:.6f}")
    print(f"recomputed total    : ${result['recomputedTotal']:.6f}")
    print(f"unattributed cost   : ${result['unattributedCost']:.6f} "
          f"across {result['unattributedFiles']} file(s)")

    if result["problems"]:
        print(f"\n{len(result['problems'])} problem(s):")
        for problem in result["problems"][:20]:
            print(f"  {problem}")
        print("\nRESULT: REJECTED - the recorded accounting does not reproduce")
        return 1
    print("\nRESULT: verified - the recorded accounting reproduces from the raw records")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
