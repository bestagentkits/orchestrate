#!/usr/bin/env python3
"""Aggregate a benchmark run into the metrics the study reports.

Reads <out>/results.jsonl and writes <out>/analysis.json, then prints a short
text summary. Costs and durations are only compared between variants for tasks
that both variants actually ran, so a partially completed run cannot report a
comparison it did not measure.

Usage:
    python3 -m tools.benchmark.analyze <out-directory>
"""

from __future__ import annotations

import json
import math
import os
import statistics
import sys
from collections import Counter, defaultdict

# Resolved at runtime: this module runs as `python3 -m tools.benchmark.analyze`, so the
# repository root is on sys.path and the sibling package is importable. A checker invoked
# without the repository root reports it as unresolvable, which is a configuration artifact
# rather than a defect; `python3 -c "from tools.benchmark.analyze import *"` resolves it.
from tools.benchmark.measure import as_float, as_int  # pyright: ignore[reportMissingImports]

USAGE = "usage: python3 -m tools.benchmark.analyze <out-directory>"


def read_results(path: str) -> list[dict]:
    records = []
    try:
        with open(path, encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    except OSError as exc:
        raise SystemExit(f"cannot read {path}: {exc}") from exc
    return records


def percentile(values: list[float], fraction: float) -> float:
    """Interpolate the requested percentile of ``values``."""
    if not values:
        return 0.0
    ordered = sorted(values)
    position = (len(ordered) - 1) * fraction
    lower = math.floor(position)
    upper = min(lower + 1, len(ordered) - 1)
    return ordered[lower] + (position - lower) * (ordered[upper] - ordered[lower])


def summarize(records: list[dict]) -> dict:
    """Aggregate one variant's trials."""
    measured = [r for r in records if r.get("status") != "skipped"]
    successes = [r for r in measured if r.get("success")]
    costs = [as_float(r.get("costUsd")) for r in measured]
    durations = [as_float(r.get("durationSeconds")) for r in measured]
    models: Counter = Counter()
    tokens: Counter = Counter()
    for record in measured:
        for model, count in (record.get("models") or {}).items():
            models[model] += as_int(count)
        for field, value in (record.get("tokens") or {}).items():
            tokens[field] += as_int(value)
    return {
        "attempts": len(measured),
        "successes": len(successes),
        "successRate": (len(successes) / len(measured)) if measured else 0.0,
        "totalCostUsd": round(sum(costs), 6),
        "costPerTaskUsd": round(sum(costs) / len(costs), 6) if costs else 0.0,
        "costPerSuccessfulTaskUsd": round(sum(costs) / len(successes), 6) if successes else None,
        "medianDurationSeconds": round(statistics.median(durations), 3) if durations else 0.0,
        "p95DurationSeconds": round(percentile(durations, 0.95), 3) if durations else 0.0,
        "totalDurationSeconds": round(sum(durations), 3),
        "tokens": dict(tokens),
        "models": dict(models),
        "dispatches": sum(as_int(r.get("dispatches")) for r in measured),
        "failures": sorted({str(r.get("failure")) for r in measured if r.get("failure")}),
    }


def paired(records: list[dict], keep: tuple[str, str]) -> dict:
    """Compare two variants per task and trial, on the trials both completed."""
    by_variant: dict[str, dict] = defaultdict(dict)
    for record in records:
        if record.get("status") == "skipped" or record["variant"] not in keep:
            continue
        by_variant[record["variant"]][(record["taskId"], record["trial"])] = record

    shared = sorted(set(by_variant[keep[0]]) & set(by_variant[keep[1]]))
    cost_deltas: list[float] = []
    time_deltas: list[float] = []
    outcomes: Counter = Counter()
    per_task = []
    for key in shared:
        first = by_variant[keep[0]][key]
        second = by_variant[keep[1]][key]
        cost_deltas.append(as_float(second.get("costUsd")) - as_float(first.get("costUsd")))
        time_deltas.append(
            as_float(second.get("durationSeconds")) - as_float(first.get("durationSeconds"))
        )
        if second.get("success") and not first.get("success"):
            outcomes["candidateOnly"] += 1
        elif first.get("success") and not second.get("success"):
            outcomes["baselineOnly"] += 1
        elif first.get("success") and second.get("success"):
            outcomes["bothSucceeded"] += 1
        else:
            outcomes["neitherSucceeded"] += 1
        per_task.append(
            {
                "taskId": key[0],
                "trial": key[1],
                "cohort": first.get("cohort"),
                "baselineCostUsd": first.get("costUsd"),
                "candidateCostUsd": second.get("costUsd"),
                "baselineSeconds": first.get("durationSeconds"),
                "candidateSeconds": second.get("durationSeconds"),
                "baselineSuccess": first.get("success"),
                "candidateSuccess": second.get("success"),
            }
        )
    return {
        "baseline": keep[0],
        "candidate": keep[1],
        "pairedCount": len(shared),
        "meanCostDeltaUsd": round(statistics.mean(cost_deltas), 6) if shared else None,
        "meanDurationDeltaSeconds": round(statistics.mean(time_deltas), 3) if shared else None,
        "candidateCheaperOn": sum(1 for delta in cost_deltas if delta < 0),
        "candidateFasterOn": sum(1 for delta in time_deltas if delta < 0),
        "outcomes": dict(outcomes),
        "perTask": per_task,
    }


def by_cohort(records: list[dict]) -> dict:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for record in records:
        if record.get("status") != "skipped":
            grouped[record.get("cohort", "unknown")].append(record)
    return {
        cohort: {
            "attempts": len(items),
            "successRate": round(sum(1 for r in items if r.get("success")) / len(items), 4),
            "costPerTaskUsd": round(
                sum(as_float(r.get("costUsd")) for r in items) / len(items), 6
            ),
        }
        for cohort, items in sorted(grouped.items())
    }


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        print(USAGE, file=sys.stderr)
        return 2
    out_dir = os.path.abspath(argv[0])
    records = read_results(os.path.join(out_dir, "results.jsonl"))
    if not records:
        raise SystemExit("no results recorded")

    variants = sorted({record["variant"] for record in records})
    report = {
        "variants": {
            name: summarize([r for r in records if r["variant"] == name]) for name in variants
        },
        "byCohort": {
            name: by_cohort([r for r in records if r["variant"] == name]) for name in variants
        },
    }
    if len(variants) >= 2:
        report["paired"] = paired(records, (variants[0], variants[1]))

    destination = os.path.join(out_dir, "analysis.json")
    try:
        with open(destination, "w", encoding="utf-8") as handle:
            json.dump(report, handle, indent=2)
            handle.write("\n")
    except OSError as exc:
        raise SystemExit(f"cannot write {destination}: {exc}") from exc

    for name, summary in report["variants"].items():
        print(
            f"{name:14} attempts={summary['attempts']:3} success={summary['successRate']:.0%} "
            f"cost=${summary['totalCostUsd']:.4f} $/task=${summary['costPerTaskUsd']:.4f} "
            f"median={summary['medianDurationSeconds']:.1f}s"
        )
    if "paired" in report:
        comparison = report["paired"]
        print(
            f"paired={comparison['pairedCount']} "
            f"mean cost delta=${comparison['meanCostDeltaUsd']} "
            f"mean duration delta={comparison['meanDurationDeltaSeconds']}s "
            f"cheaper_on={comparison['candidateCheaperOn']} "
            f"faster_on={comparison['candidateFasterOn']} "
            f"outcomes={comparison['outcomes']}"
        )
    print(f"written: {destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
