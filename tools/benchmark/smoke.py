#!/usr/bin/env python3
"""End-to-end smoke test of the instrumented harness at zero provider cost.

The point of this script is to exercise the real code paths — fixture materialization, the
`pi` shim, session accounting, the settle window, the full-schema trial record, the route and
gate trace readers, and the independent accounting audit — without calling a provider and
without paying for the model matrix. A stub `pi` stands in for the agent, so the harness cannot
tell the difference in shape and nothing is mocked out.

What the smoke asserts:

- the run produced both arms and both results and full-schema trial records;
- every trial record validates against the closed schema;
- the route decision trace was captured from the workspace and passed the trace owner's own
  validation, and the C3 requirement was derived from the gate record rather than assumed;
- the accounting audit passes, with nothing unattributed;
- the trials settled.

Usage:
    python3 -m tools.benchmark.smoke [<out-directory>]
"""

from __future__ import annotations

import json
import os
import shutil
import stat
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(HERE))

from tools.benchmark import run_benchmark, trial_schema, verify_results  # noqa: E402

DEFAULT_OUT = os.path.join(REPO_ROOT, "plans", "reports", "issue15-smoke")

#: The cost one stubbed invocation declares. It is a fixed constant, not a measurement of
#: anything, and it exists so the accounting path has a non-zero number to reconcile.
SMOKE_COST = 0.0125

SMOKE_TOKENS = {"input": 100, "output": 20, "cacheRead": 5, "cacheWrite": 1, "reasoning": 3}

ROUTE_PAYLOAD = {
    "candidateCount": 3, "eligibleCount": 2, "rankedCount": 2,
    "hardGateSurvivors": 2, "hardGateRejects": 1,
    "hardGateRejectReasons": ["capability-floor"],
    "prunedCount": 0, "pruneReasons": [],
    "evidenceCohort": "smoke-cohort", "evidenceSampleSize": 12, "evidenceDegradation": "none",
    "qualityBound": 0.70, "qualityEstimator": "wilson-lower-bound",
    "actualMarginalCostUsd": SMOKE_COST, "apiEquivalentCostUsd": None, "quotaBurn": None,
    "costDimensionUsed": "actualMarginalCostUsd",
    "infrastructureFailureProbability": 0.20,
    "recoveryCostEvidenceClass": "transport-or-infrastructure",
    "expectedRecoveryCostUsd": 0.0025, "expectedC3CostUsd": 0.0,
    "expectedVerifiedCostUsd": SMOKE_COST,
    "selectedRuntime": "pi", "selectedProvider": "provider-smoke",
    "selectedModel": "model-smoke", "selectedFamily": "model",
    "selectedEffortMode": "medium", "effortLevel": "medium",
    "runnerUpRuntime": "pi", "runnerUpProvider": "provider-smoke",
    "runnerUpModel": "model-smoke-alt", "runnerUpEffortMode": "low",
    "runnerUpMargin": 0.25,
    "semanticRouterCalled": False, "semanticRouterReason": "ok",
    "semanticRouterSkippedReason": "no-floor-can-change",
    "benchmarkRef": "smoke-cohort/0000-00-00", "benchmarkDegraded": "none",
    "capabilityFloorDelta": 0.0, "riskFloorDelta": 0.0, "riskTier": "R1",
}

GATE_PAYLOAD = {"tier": "C1", "controlsChecked": 4, "approvalsRequired": 0,
                "escalated": False, "escalationClause": None}


def stub_source() -> str:
    """The stub `pi`. It answers probes, records a session, and leaves the workspace alone.

    It deliberately does **not** fix the fixture, so the grader fails. The smoke is testing the
    instrumentation, not the agent: a failing grade is a legitimate outcome that must still be
    recorded, audited and reconciled.
    """
    return f'''#!/usr/bin/env python3
"""Stub `pi` for the zero-cost smoke test. It is not a model and calls nothing."""

import json
import os
import sys
import time

ARGS = list(sys.argv[1:])
COST = {SMOKE_COST!r}
TOKENS = {SMOKE_TOKENS!r}
ROUTE = {ROUTE_PAYLOAD!r}
GATE = {GATE_PAYLOAD!r}

if "--version" in ARGS or "-V" in ARGS:
    print("0.0.0-smoke")
    raise SystemExit(0)

if "--list-models" in ARGS:
    print("provider-smoke/model-smoke")
    print("provider-smoke/model-smoke-alt")
    raise SystemExit(0)

# A real session invocation: record usage, then leave the code untouched.
session_dir = os.environ.get("BM_SESSION_DIR")
if session_dir and ("--print" in ARGS or "-p" in ARGS or "--mode" in ARGS):
    os.makedirs(session_dir, exist_ok=True)
    stamp = time.strftime("%Y%m%dT%H%M%S", time.gmtime())
    name = f"{{stamp}}-{{os.getpid()}}-{{time.time_ns() % 1000000}}.jsonl"
    with open(os.path.join(session_dir, name), "w", encoding="utf-8") as handle:
        handle.write(json.dumps({{"type": "model_change", "provider": "provider-smoke",
                                 "modelId": "model-smoke"}}) + "\\n")
        handle.write(json.dumps({{"message": {{"usage": {{"cost": {{"total": COST}}, **TOKENS}}}}}}) + "\\n")

# Leave a decision trace, so the trial record's route and gate fields come from a real read.
trace_dir = os.path.join(os.getcwd(), ".orchestrate")
os.makedirs(trace_dir, exist_ok=True)
with open(os.path.join(trace_dir, "trace.jsonl"), "w", encoding="utf-8") as handle:
    handle.write(json.dumps({{"kind": "route", "payload": ROUTE}}) + "\\n")
    handle.write(json.dumps({{"kind": "gate", "payload": GATE}}) + "\\n")

raise SystemExit(0)
'''


def install_stub(bin_dir: str) -> str:
    """Write the stub `pi` and return the directory to put first on PATH."""
    path = os.path.join(bin_dir, "pi")
    try:
        os.makedirs(bin_dir, exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(stub_source())
        # Owner-only execute: the stub runs as this user, so no group or world bit is needed.
        os.chmod(path, os.stat(path).st_mode | stat.S_IXUSR)
    except OSError as exc:
        raise SystemExit(f"cannot install the stub pi: {exc}") from exc
    return bin_dir


def main(argv: list[str]) -> int:
    out_dir = os.path.abspath(argv[0] if argv else DEFAULT_OUT)
    try:
        if os.path.isdir(out_dir):
            shutil.rmtree(out_dir)
        os.makedirs(out_dir, exist_ok=True)
    except OSError as exc:
        raise SystemExit(f"cannot prepare {out_dir}: {exc}") from exc

    bin_dir = install_stub(os.path.join(out_dir, "stub-bin"))
    previous_path = os.environ.get("PATH", "")
    os.environ["PATH"] = bin_dir + os.pathsep + previous_path
    try:
        exit_code = run_benchmark.main([
            "--out", out_dir,
            "--limit", "1",
            "--trials", "1",
            "--cap-usd", "1",
            "--agent-timeout", "60",
            "--variants", "astra-only,orchestrate",
        ])
    finally:
        os.environ["PATH"] = previous_path

    print()
    if exit_code != 0:
        print(f"FAIL: the harness exited {exit_code}")
        return 1

    failures: list[str] = []

    results = verify_results.load(os.path.join(out_dir, "results.jsonl"))
    trials = verify_results.load(os.path.join(out_dir, "trials.jsonl"))
    print(f"results records : {len(results)}")
    print(f"trial records   : {len(trials)}")
    if len(results) != 2:
        failures.append(f"expected 2 result records, got {len(results)}")
    if len(trials) != 2:
        failures.append(f"expected 2 trial records, got {len(trials)}")

    for record in trials:
        problems = trial_schema.validate_trial_record(record)
        if problems:
            failures.append(f"trial schema {record.get('taskId')}/{record.get('variant')}: {problems}")

    traced = [t for t in trials if t.get("routeDecisionTrace") is not None]
    print(f"route traces    : {len(traced)} of {len(trials)}")
    if not traced:
        failures.append("no trial captured a route decision trace from the workspace")

    for record in traced:
        print(f"  {record['variant']:12} c3Required={record.get('c3Required')} "
              f"c3Reason={record.get('c3Reason')} "
              f"evidenceScope={record.get('evidenceScope')} "
              f"modelFamily={record.get('modelFamily')}")

    settled = [t for t in trials if t.get("capability")]
    for record in results:
        if not record.get("settled"):
            failures.append(f"{record.get('variant')} trial did not settle")

    audit = verify_results.audit_run(out_dir)
    print()
    print(f"audit verdict   : {audit['verdict']}")
    print(f"cost mismatches : {audit['mismatches']}")
    print(f"token mismatches: {audit['tokenMismatches']}")
    print(f"unattributed    : ${audit['unattributedCost']:.6f} across {audit['unattributedFiles']} file(s)")
    print(f"total cost      : ${audit['recomputedTotal']:.6f} (stub-declared, no provider called)")
    if audit["verdict"] != "verified":
        failures.append(f"audit rejected the smoke run: {audit['problems'][:6]}")
    if audit["recomputedTotal"] <= 0:
        failures.append("the accounting path recorded no cost at all")

    print()
    if failures:
        print(f"FAIL: {len(failures)} problem(s)")
        for failure in failures:
            print(f"  {failure}")
        return 1
    print("PASS: the instrumented harness ran end to end and the accounting audit verified it")
    print(f"      artifact: {out_dir}")
    print("      paid provider calls: 0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
