#!/usr/bin/env python3
"""Freeze the experiment environment and pre-register the analysis, without running it.

Issue #15 Phase 3 requires the environment to be frozen before any measurement, and the
statistics to be pre-registered before any result is seen. Both are properties of a document
written *in advance*, so this tool resolves what it can from live evidence and refuses to
invent the rest.

The central rule of this repository applies with full force here: **no catalog value, model
name, price or version may be copied into the skill.** This tool exists so the frozen values
live in a run artifact rather than in the contract, and so they are resolved at freeze time
instead of transcribed. A field that cannot be resolved is recorded as `null` with a
capability state saying why, never guessed.

Credential values are never read, printed or stored: only presence, the source location and
the source's trust class.

Usage:
    python3 -m tools.benchmark.freeze_manifest <output.json>
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(HERE))

FIXTURE_PATH = os.path.join(HERE, "fixtures", "taskflow.json")
USAGE = "usage: python3 -m tools.benchmark.freeze_manifest <output.json>"

#: Capability vocabulary, shared with the trial schema's intent: a value is exposed, derived,
#: not exposed by the source, or not measured yet.
EXPOSED = "exposed"
DERIVED = "derived"
NOT_EXPOSED = "not-exposed-by-source"
NOT_MEASURED = "not-measured"

CAPABILITY_STATES = (EXPOSED, DERIVED, NOT_EXPOSED, NOT_MEASURED)

#: Every field that must be frozen. A manifest missing one of these is not a manifest.
FROZEN_FIELDS = (
    "runtimeName",
    "runtimeVersion",
    "orchestrateCommit",
    "orchestrateBranch",
    "worktreeClean",
    "environment",
    "catalogSnapshot",
    "authReadiness",
    "fixture",
    "pricingSnapshot",
    "timeBand",
    "arms",
    "preregistration",
    "workerFrontierProtocol",
)

#: Every pre-registered parameter. A manifest missing one cannot be used to judge a result.
PREREGISTERED_FIELDS = (
    "primaryMetric",
    "secondaryMetrics",
    "nonInferiorityMargin",
    "minimumWorthwhileSaving",
    "trialCount",
    "stoppingRule",
    "stratification",
    "pairedProcedure",
    "statisticalTests",
    "criticalCohorts",
    "improvementConditions",
)

#: The arms. V1 is named for what it actually measures, because the measured configuration is
#: skill-plus-directive; see settlement-confound.md.
ARMS = (
    {"id": "V0", "name": "strong single-model baseline", "decisionPlane": False,
     "note": "the coordinator model alone, no routing policy"},
    {"id": "V1", "name": "current routing policy (skill plus harness directive)",
     "decisionPlane": True,
     "note": "the measured arm is skill-plus-directive, not the skill alone; the directive's "
             "dispatch mandate is not separable from the skill without a further arm"},
    {"id": "V2", "name": "generalized deterministic cost-aware router", "decisionPlane": False,
     "note": "the new policy with the decision plane off, so its deterministic half is "
             "measured alone"},
    {"id": "V3", "name": "V2 plus decision plane on value-positive choices", "decisionPlane": True,
     "note": "the plane is called only where it can change a permitted decision"},
    {"id": "V4", "name": "V3 plus a calibrated micro-arbiter", "decisionPlane": True,
     "note": "calibration valid, so an eligible C3 call can be avoided"},
    {"id": "V5", "name": "V4 plus durable calibration reuse", "decisionPlane": True,
     "note": "only if the durability contract is implemented; otherwise recorded as not run"},
    {"id": "ORACLE", "name": "offline retrospective oracle", "decisionPlane": False,
     "note": "the retrospectively cheapest eligible successful route per task, used only to "
             "estimate routing headroom and never as a policy"},
)

#: The critical cohorts that may not regress at all. This is a gate, not a statistical test.
CRITICAL_COHORTS = (
    "security-sensitive",
    "c3-mandatory",
    "independence-required",
)


class ManifestError(ValueError):
    """Raised for a manifest that cannot be built or validated."""


def capability(state: str, value=None, basis: str | None = None) -> dict:
    """One frozen field's value and the state that qualifies it."""
    if state not in CAPABILITY_STATES:
        raise ManifestError(f"unknown capability state {state!r}")
    if state == EXPOSED and value is None:
        raise ManifestError("an exposed field must carry a value")
    if state in (NOT_EXPOSED, NOT_MEASURED) and value is not None:
        raise ManifestError(f"a {state} field must be null")
    entry: dict = {"state": state, "value": value}
    if state == DERIVED:
        if not basis:
            raise ManifestError("a derived field must record its basis")
        entry["basis"] = basis
    return entry


def _run(command: list[str], timeout: int = 60) -> tuple[int, str]:
    try:
        finished = subprocess.run(command, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired):
        return -1, ""
    return finished.returncode, ((finished.stdout or "") + (finished.stderr or "")).strip()


def resolve_runtime() -> dict:
    """The runtime's own reported version, or a stated absence."""
    code, text = _run(["pi", "--version"])
    if code != 0 or not text:
        return {"runtimeName": capability(EXPOSED, "pi"),
                "runtimeVersion": capability(NOT_EXPOSED)}
    return {"runtimeName": capability(EXPOSED, "pi"),
            "runtimeVersion": capability(EXPOSED, text.splitlines()[0].strip())}


def resolve_repository() -> dict:
    """The exact commit under test, and whether the worktree was clean when frozen."""
    _, commit = _run(["git", "rev-parse", "HEAD"])
    _, branch = _run(["git", "rev-parse", "--abbrev-ref", "HEAD"])
    _, status = _run(["git", "status", "--porcelain"])
    dirty = len([line for line in status.splitlines() if line.strip()])
    return {
        "orchestrateCommit": capability(EXPOSED, commit) if commit else capability(NOT_MEASURED),
        "orchestrateBranch": capability(EXPOSED, branch) if branch else capability(NOT_MEASURED),
        "worktreeClean": capability(EXPOSED, dirty == 0),
        "worktreeDirtyFiles": dirty,
    }


def resolve_environment() -> dict:
    return {
        "pythonVersion": capability(EXPOSED, platform.python_version()),
        "platform": capability(EXPOSED, f"{platform.system()} {platform.release()} {platform.machine()}"),
        "frozenAt": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }


def resolve_catalog() -> dict:
    """A live catalog snapshot, or an explicit statement that none was taken.

    The catalog is live runtime evidence, so it is read from the runtime rather than
    transcribed. When the runtime cannot list it without network access or credentials, the
    manifest says so instead of carrying a stale list forward.
    """
    code, text = _run(["pi", "--no-extensions", "--list-models"], timeout=120)
    if code != 0 or not text:
        return {"state": NOT_MEASURED, "value": None,
                "basis": "the runtime did not list its catalog in this environment"}
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    models = [line.strip() for line in text.splitlines() if line.strip()]
    return {"state": EXPOSED, "value": {"digest": digest, "count": len(models)},
            "basis": "sha256 over the runtime's own model listing"}


def resolve_auth() -> dict:
    """Auth readiness as presence, source and trust class. Never a value."""
    variables = ("TYPESAFE_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY")
    presence = {name: bool(os.environ.get(name)) for name in variables}
    env_file = "/home/orca/www/orchestrate/.env"
    return {
        "environmentVariables": presence,
        "envFilePresent": os.path.exists(env_file),
        "envFileTrustClass": "operator-provided-local-file" if os.path.exists(env_file) else None,
        "valuesRecorded": False,
        "note": "presence, source location and trust class only; no value is read or stored",
    }


def resolve_fixture() -> dict:
    """Recompute the fixture digests and confirm the payload's own digests match."""
    if not os.path.exists(FIXTURE_PATH):
        raise ManifestError(f"fixture payload missing: {FIXTURE_PATH}")
    try:
        with open(FIXTURE_PATH, encoding="utf-8") as handle:
            payload = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        raise ManifestError(f"cannot read the fixture payload: {exc}") from exc
    recomputed = {
        "workspace": _digest(payload.get("workspace") or {}),
        "graders": _digest(payload.get("graders") or {}),
    }
    return {
        "id": payload.get("id"),
        "version": payload.get("version"),
        "workspaceDigest": capability(EXPOSED, payload.get("workspaceDigest")),
        "graderDigest": capability(EXPOSED, payload.get("graderDigest")),
        "recomputed": recomputed,
        "digestsMatch": (recomputed["workspace"] == payload.get("workspaceDigest")
                         and recomputed["graders"] == payload.get("graderDigest")),
    }


def _digest(files: dict) -> str:
    hasher = hashlib.sha256()
    for path, content in sorted(files.items()):
        hasher.update(path.encode("utf-8"))
        hasher.update(b"\0")
        hasher.update(str(content).encode("utf-8"))
        hasher.update(b"\0")
    return hasher.hexdigest()


def resolve_pricing() -> dict:
    """Pricing is not resolvable offline, and a copied price is worse than an absent one."""
    return {
        "state": NOT_MEASURED,
        "value": None,
        "basis": "prices must be captured at run time from the provider's own usage report; "
                 "copying a price into the skill or the manifest would make the frozen "
                 "comparison a transcription rather than a measurement",
    }


def resolve_time_band(days: int = 14) -> dict:
    """The window in which the frozen environment is still the environment that was frozen."""
    now = time.time()
    return {
        "frozenAt": time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime(now)),
        "validUntil": time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime(now + days * 86400)),
        "maxAgeDays": days,
        "invalidation": "a runtime version change, a catalog digest change, a fixture or grader "
                        "digest change, or a commit change invalidates the band and requires a "
                        "re-freeze before any result is compared",
    }


def preregistration() -> dict:
    """The analysis, fixed before any result exists."""
    return {
        "primaryMetric": {
            "name": "verified cost per successful task",
            "definition": "total end-to-end attributable cost divided by accepted successful "
                          "tasks, including coordinator, worker, classifier, retry, fallback, "
                          "micro-arbiter and C3 arbiter calls",
            "dimension": "actualMarginalCostUsd",
            "note": "quota burn is never added to dollars; the metric declares its dimension",
        },
        "secondaryMetrics": [
            "success rate",
            "settlement rate (trials reaching a verified, reported outcome)",
            "duration per successful task",
            "dispatch cost share",
            "non-settlement rate",
        ],
        "nonInferiorityMargin": {
            "value": 0.05,
            "unit": "absolute success-rate difference",
            "note": "the candidate may not be worse than the baseline by more than five "
                    "percentage points",
        },
        "minimumWorthwhileSaving": {
            "value": 0.15,
            "unit": "relative reduction in verified cost per successful task",
            "note": "a smaller saving is not claimed as an improvement even if it is positive",
        },
        "trialCount": {
            "tasks": 20,
            "trialsPerTaskPerArm": 3,
            "arms": len(ARMS),
            "planned": 20 * 3 * len(ARMS),
            "note": "the oracle arm is computed offline and costs nothing",
        },
        "stoppingRule": {
            "interimAt": "50% of planned trials per arm",
            "interimAlpha": 0.005,
            "finalAlpha": 0.045,
            "stopForBenefit": "interim lower confidence bound for the saving exceeds the "
                              "minimum worthwhile saving AND non-inferiority holds",
            "stopForFutility": "the success-rate difference confidence interval lies entirely "
                               "below the non-inferiority margin",
            "note": "alpha is spent across two looks so the final threshold is not the "
                    "unadjusted 0.05",
        },
        "stratification": {
            "by": ["task cohort", "task type"],
            "note": "every stratum reports its own paired estimate; a pooled estimate alone is "
                    "not reported as the result",
        },
        "pairedProcedure": {
            "design": "task-major, paired by (task, trial)",
            "note": "both arms of a pair run back to back so a slow period or a model revision "
                    "cannot land on one arm only",
        },
        "statisticalTests": {
            "cost": "paired bootstrap over task-level pairs, 10000 resamples, percentile interval",
            "success": "paired difference in proportions with a Newcombe interval",
            "nonInferiority": "the lower confidence bound of the success-rate difference must "
                              "sit above minus the non-inferiority margin",
            "multiplicity": "two looks with alpha spending as declared in the stopping rule",
        },
        "criticalCohorts": list(CRITICAL_COHORTS),
        "improvementConditions": [
            "the confidence interval for quality degradation stays inside the pre-registered "
            "non-inferiority margin",
            "the confidence interval for verified-cost savings is positive and clears the "
            "minimum worthwhile saving",
            "no critical cohort regresses",
            "no safety, control or independence invariant is weakened",
            "the accounting audit passes on the run",
        ],
    }


def worker_frontier_protocol() -> dict:
    """The step that must precede the router ablation."""
    return {
        "order": "workers first, router second",
        "step1": "run the frozen catalog's models and effort modes directly as workers on the "
                 "frozen fixture, with no orchestration, to identify the local Pareto frontier "
                 "over verified cost and quality",
        "step2": "freeze that frontier and use it as the candidate set for the router ablation",
        "reason": "measuring the router against an unfrozen candidate set would confound the "
                  "policy's effect with the candidate set's composition",
        "coordinatorHeldFixed": True,
        "note": "the coordinator is held fixed during the router ablation; coordinator "
                "optimization is a separate later experiment",
        "externalEvidence": "external leaderboards may seed hypotheses but are never proof of "
                            "this skill's performance and never enter the candidate set directly",
    }


def build_manifest(runtime: dict | None = None, repository: dict | None = None,
                   catalog: dict | None = None, fixture: dict | None = None) -> dict:
    """Assemble the frozen manifest. Nothing is invented; unresolved fields say so.

    The resolvers are injectable so a test can build a manifest without shelling out to the
    runtime or to git, and so a re-freeze can supply an already-captured snapshot.
    """
    manifest = {
        **(runtime if runtime is not None else resolve_runtime()),
        **(repository if repository is not None else resolve_repository()),
        "environment": resolve_environment(),
        "catalogSnapshot": catalog if catalog is not None else resolve_catalog(),
        "authReadiness": resolve_auth(),
        "fixture": fixture if fixture is not None else resolve_fixture(),
        "pricingSnapshot": resolve_pricing(),
        "timeBand": resolve_time_band(),
        "arms": [dict(arm) for arm in ARMS],
        "preregistration": preregistration(),
        "workerFrontierProtocol": worker_frontier_protocol(),
        "paidRunExecuted": False,
    }
    return manifest


def validate_manifest(manifest: dict) -> list[str]:
    """Every problem with a manifest, as stable machine-readable codes."""
    if not isinstance(manifest, dict):
        raise ManifestError("a manifest must be an object")
    problems: list[str] = []
    for field in FROZEN_FIELDS:
        if field not in manifest:
            problems.append(f"missing:{field}")
    for field in PREREGISTERED_FIELDS:
        if not (manifest.get("preregistration") or {}).get(field):
            problems.append(f"missing-preregistration:{field}")
    if manifest.get("paidRunExecuted"):
        problems.append("paid-run-claimed")

    fixture = manifest.get("fixture") or {}
    if not fixture.get("digestsMatch"):
        problems.append("fixture-digests-do-not-match")

    for field in ("runtimeVersion", "orchestrateCommit", "catalogSnapshot"):
        entry = manifest.get(field)
        if field == "catalogSnapshot":
            if not isinstance(entry, dict) or entry.get("state") not in CAPABILITY_STATES:
                problems.append(f"unstated-capability:{field}")
            continue
        if not isinstance(entry, dict) or entry.get("state") not in CAPABILITY_STATES:
            problems.append(f"unstated-capability:{field}")

    auth = manifest.get("authReadiness") or {}
    if auth.get("valuesRecorded"):
        problems.append("credential-values-recorded")

    arms = manifest.get("arms") or []
    ids = [arm.get("id") for arm in arms]
    for required in ("V0", "V1", "V2", "V3", "V4", "ORACLE"):
        if required not in ids:
            problems.append(f"missing-arm:{required}")

    margin = (manifest.get("preregistration") or {}).get("nonInferiorityMargin") or {}
    if not isinstance(margin.get("value"), (int, float)):
        problems.append("non-inferiority-margin-not-numeric")
    saving = (manifest.get("preregistration") or {}).get("minimumWorthwhileSaving") or {}
    if not isinstance(saving.get("value"), (int, float)):
        problems.append("saving-threshold-not-numeric")

    return problems


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        print(USAGE, file=sys.stderr)
        return 2
    destination = argv[0]
    manifest = build_manifest()
    problems = validate_manifest(manifest)
    try:
        with open(destination, "w", encoding="utf-8") as handle:
            handle.write(json.dumps(manifest, indent=2) + "\n")
    except OSError as exc:
        raise SystemExit(f"cannot write {destination}: {exc}") from exc

    print(f"written        : {destination}")
    print(f"runtime        : {manifest['runtimeName']['value']} "
          f"{manifest['runtimeVersion'].get('value')}")
    print(f"commit         : {(manifest['orchestrateCommit'].get('value') or '')[:12]}")
    print(f"catalog        : {manifest['catalogSnapshot']['state']}")
    print(f"fixture digests: {'match' if manifest['fixture']['digestsMatch'] else 'MISMATCH'}")
    print(f"paid run       : {manifest['paidRunExecuted']}")
    if problems:
        print(f"\n{len(problems)} problem(s): {problems}")
        return 1
    print("\nRESULT: frozen and pre-registered; no paid run executed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
