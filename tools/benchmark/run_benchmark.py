#!/usr/bin/env python3
"""Run the orchestrate benchmark and record per-trial measurements.

Each trial runs one task in an isolated workspace that is unpacked from the
fixture payload. The agent is a headless ``pi`` session, and every ``pi``
invocation the agent makes - including any it dispatches itself - is routed
through a PATH shim so that all of them write their session files into one
run-scoped directory. Cost is then the sum of ``usage.cost.total`` over those
session files, which makes the measurement complete for nested dispatch rather
than only for the top-level process.

Success is decided by the task's hidden unittest grader, which is installed
into the workspace only after the agent has finished.

Usage:
    python3 -m tools.benchmark.run_benchmark --out plans/reports/orchestrate-bench --limit 2
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import stat
import subprocess
import sys
import time
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(HERE))

from tools.benchmark import arms as arm_defs
from tools.benchmark import trial_schema
from tools.benchmark.measure import as_float, as_int
from tools.benchmark.task_catalog import GRADER_MODULE, TASKS

FIXTURE_PATH = os.path.join(HERE, "fixtures", "taskflow.json")
SKILL_MD = os.path.join(
    REPO_ROOT, "plugins", "orchestrate", "skills", "orchestrate", "SKILL.md"
)
PROVIDER = "openai-codex"
MODEL = "gpt-6-astra"
GRADER_DIRNAME = "taskflow_bench_tests"
DEFAULT_TRIALS = 2
DEFAULT_CAP_USD = 400.0
DEFAULT_AGENT_TIMEOUT = 1500
GRADER_TIMEOUT = 300

ORCHESTRATE_DIRECTIVE = """\
You are operating under the `orchestrate` skill whose contract is above.

- Complete the user's task in this turn. Do not stop after planning, and do not
  stop after probing runtimes: the change to the working tree must actually be
  made and verified before you finish.
- You may dispatch work to other models or runtimes, and you are expected to
  choose those routes yourself. Dispatch every unit of work as a headless `pi`
  session invocation, because only those are instrumented for this measurement.
  Do not use in-session subagents, and do not dispatch to `omp`.
- Enable the decision plane rather than leaving it as `none`. A Jev (TypeSafe)
  classifier candidate is explicitly configured for this run: obtain its record
  by running `python3 {classifier} probe`, then register that record in this
  run's `runtimes.json` with `role: classifier`. Before any plane call, record
  the egress authorization the preconditions require, naming provider
  `api.typesafe.ai` and the content classes the classifier is sent; the
  credential is in your environment already. Invoke it as
  `python3 {classifier} classify` with the request on stdin, and persist the
  enumerated decision trace to the run's `decisions.jsonl`.
- Work only inside the current working directory.
"""


def read_text(path: str) -> str:
    try:
        with open(path, encoding="utf-8") as handle:
            return handle.read()
    except OSError as exc:
        raise SystemExit(f"cannot read {path}: {exc}") from exc


def write_text(path: str, text: str) -> None:
    try:
        os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)
    except OSError as exc:
        raise SystemExit(f"cannot write {path}: {exc}") from exc


def ensure_dir(path: str) -> None:
    """Create a directory, reporting an unusable path without a traceback."""
    try:
        os.makedirs(path, exist_ok=True)
    except OSError as exc:
        raise SystemExit(f"cannot create directory {path}: {exc}") from exc


def read_credential(path: str, name: str) -> str:
    """Read exactly one variable from a dotenv file, echoing nothing.

    Only the named variable is extracted, so an unrelated secret sitting in the
    same file is never loaded into this process, never passed to a child and
    never written anywhere. The value is returned to the caller and is not
    logged, counted or recorded at any point.
    """
    try:
        with open(path, encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                if key.strip() == name:
                    return value.strip().strip('"').strip("'")
    except OSError as exc:
        raise SystemExit(f"cannot read credential file {path}: {exc}") from exc
    return ""


CREDENTIAL_VARIABLE = "TYPESAFE_API_KEY"


def load_fixture(path: str) -> dict:
    try:
        payload = json.loads(read_text(path))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"fixture is not valid JSON: {exc}") from exc
    for key in ("workspace", "graders", "workspaceDigest"):
        if key not in payload:
            raise SystemExit(f"fixture is missing {key!r}")
    return payload


def materialize(payload: dict, workspace: str) -> None:
    """Unpack the agent-visible workspace. Graders are deliberately absent."""
    ensure_dir(workspace)
    for relative, content in payload["workspace"].items():
        write_text(os.path.join(workspace, relative), content)


def install_graders(payload: dict, workspace: str) -> None:
    """Install the hidden graders, after the agent has stopped."""
    target = os.path.join(workspace, GRADER_DIRNAME)
    ensure_dir(target)
    for relative, content in payload["graders"].items():
        write_text(os.path.join(target, os.path.basename(relative)), content)
    write_text(os.path.join(target, "__init__.py"), "")


def build_shim(shim_dir: str, real_pi: str, invocation_log: str) -> None:
    """Install a `pi` wrapper that forces every session into one directory.

    A caller-supplied ``--session-dir`` is removed rather than respected, which
    is the whole point of the wrapper. The skill under test dispatches its own
    ``pi`` sessions and passes its own relative ``--session-dir``; honouring it
    writes those sessions inside the trial workspace where the cost accounting
    cannot see them, and the candidate's cost is then silently understated.
    """
    ensure_dir(shim_dir)
    script = f'''#!/usr/bin/env python3
"""Benchmark shim: record the invocation, then force one session directory."""

import os
import sys

REAL_PI = {real_pi!r}
LOG = {invocation_log!r}

args = list(sys.argv[1:])
try:
    with open(LOG, "a", encoding="utf-8") as handle:
        handle.write(" ".join(args) + "\\n")
except OSError:
    pass

session_dir = os.environ.get("BM_SESSION_DIR")
if session_dir:
    cleaned = []
    index = 0
    while index < len(args):
        item = args[index]
        if item == "--session-dir":
            index += 2
            continue
        if item.startswith("--session-dir="):
            index += 1
            continue
        cleaned.append(item)
        index += 1
    args = ["--session-dir", session_dir] + cleaned

os.execv(REAL_PI, [REAL_PI] + args)
'''
    shim = os.path.join(shim_dir, "pi")
    write_text(shim, script)
    try:
        os.chmod(shim, os.stat(shim).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    except OSError as exc:
        raise SystemExit(f"cannot mark {shim} executable: {exc}") from exc


def session_file_stats(path: str) -> dict:
    """Return the cost, tokens and models that one session file recorded."""
    cost = 0.0
    tokens: Counter = Counter()
    models: Counter = Counter()
    model_costs: dict[str, float] = {}
    token_fields_seen: set[str] = set()
    current_model = None
    for line in read_text(path).splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if record.get("type") == "model_change":
            current_model = f"{record.get('provider')}/{record.get('modelId')}"
            models[current_model] += 1
        message = record.get("message")
        if not isinstance(message, dict):
            continue
        usage = message.get("usage")
        if not isinstance(usage, dict):
            continue
        message_cost = as_float((usage.get("cost") or {}).get("total"))
        cost += message_cost
        key = current_model or "unknown"
        model_costs[key] = model_costs.get(key, 0.0) + message_cost
        for field in ("input", "output", "cacheRead", "cacheWrite", "reasoning"):
            if field in usage:
                token_fields_seen.add(field)
            tokens[field] += as_int(usage.get(field))
    return {
        "costUsd": cost,
        "tokens": dict(tokens),
        "models": dict(models),
        "modelCosts": dict(model_costs),
        "tokenFieldsSeen": sorted(token_fields_seen),
    }


def session_files(session_dir: str) -> dict[str, dict]:
    """Return per-session-file statistics for every file under a directory.

    Statistics are kept per file rather than as a running total, because every
    trial writes into one shared directory: a caller compares the snapshot taken
    before a trial with the one taken after it to learn that trial's own cost.
    """
    stats: dict[str, dict] = {}
    if not os.path.isdir(session_dir):
        return stats
    for current, _dirs, names in os.walk(session_dir):
        for name in sorted(names):
            if name.endswith(".jsonl"):
                path = os.path.join(current, name)
                stats[path] = session_file_stats(path)
    return stats


def escaped_session_files(workspace: str) -> list[str]:
    """Find session files a dispatch wrote inside the workspace instead.

    The shim forces a single session directory, so this is expected to be empty.
    It exists as a safety net: an escape is counted and reported rather than
    quietly dropped from the candidate's cost.
    """
    found = []
    for current, _dirs, names in os.walk(workspace):
        if "sessions" not in current.split(os.sep):
            continue
        for name in sorted(names):
            if name.endswith(".jsonl"):
                found.append(os.path.join(current, name))
    return found


def combine(stats: dict[str, dict], paths: list) -> dict:
    """Sum the per-file statistics of ``paths`` into one measurement."""
    cost = 0.0
    tokens: Counter = Counter()
    models: Counter = Counter()
    model_costs: dict[str, float] = {}
    token_fields_seen: set[str] = set()
    for path in paths:
        entry = stats[path]
        cost += entry["costUsd"]
        for field, value in entry["tokens"].items():
            tokens[field] += value
        for model, count in entry["models"].items():
            models[model] += count
        for model, value in (entry.get("modelCosts") or {}).items():
            model_costs[model] = model_costs.get(model, 0.0) + value
        token_fields_seen.update(entry.get("tokenFieldsSeen") or [])
    return {
        "costUsd": cost,
        "tokens": dict(tokens),
        "models": dict(models),
        "modelCosts": dict(model_costs),
        "tokenFieldsSeen": sorted(token_fields_seen),
        "sessionFiles": len(paths),
    }


def run_grader(workspace: str, grader_class: str) -> tuple[bool, str]:
    command = [sys.executable, "-m", "unittest", f"{GRADER_MODULE}.{grader_class}", "-v"]
    try:
        finished = subprocess.run(
            command, cwd=workspace, capture_output=True, text=True, timeout=GRADER_TIMEOUT
        )
    except subprocess.TimeoutExpired:
        return False, f"grader timed out after {GRADER_TIMEOUT}s"
    except OSError as exc:
        return False, f"grader could not start: {exc}"
    output = (finished.stdout or "") + (finished.stderr or "")
    return finished.returncode == 0, output


def apply_session_dir(command: list[str], session_dir: str) -> list[str]:
    if "--session-dir" in command:
        return command
    return command[:1] + ["--session-dir", session_dir] + command[1:]


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Run the orchestrate benchmark.")
    parser.add_argument("--out", required=True, help="output directory for results")
    parser.add_argument("--limit", type=int, default=0, help="run only the first N tasks")
    parser.add_argument("--trials", type=int, default=DEFAULT_TRIALS)
    parser.add_argument("--cap-usd", type=float, default=DEFAULT_CAP_USD)
    parser.add_argument("--agent-timeout", type=int, default=DEFAULT_AGENT_TIMEOUT)
    parser.add_argument("--variants", default="astra-only,orchestrate")
    parser.add_argument(
        "--arms",
        default="",
        help="JSON arm list; each arm names its own provider, model, effort, skill "
             "version, directive and plane state",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="skip trials already recorded in the output directory's results.jsonl",
    )
    parser.add_argument(
        "--env-file",
        default="",
        help="dotenv file to read CREDENTIAL_VARIABLE from, for the skill variant only",
    )
    args = parser.parse_args(argv)

    real_pi = shutil.which("pi")
    if not real_pi:
        raise SystemExit("pi is not on PATH")

    payload = load_fixture(FIXTURE_PATH)
    tasks = TASKS[: args.limit] if args.limit else list(TASKS)
    arm_specs: dict = {}
    if args.arms:
        for arm in arm_defs.load_arms(args.arms):
            arm_specs[arm["id"]] = arm
        variants = list(arm_specs)
    else:
        variants = [name.strip() for name in args.variants.split(",") if name.strip()]

    out_dir = os.path.abspath(args.out)
    ensure_dir(out_dir)
    results_path = os.path.join(out_dir, "results.jsonl")
    shim_dir = os.path.join(out_dir, "bin")
    session_dir = os.path.join(out_dir, "sessions")
    invocation_log = os.path.join(out_dir, "invocations.log")
    jev_adapter_log = os.path.join(out_dir, "jev-adapter-invocations.jsonl")
    workspace_root = os.path.join(out_dir, "workspaces")
    ensure_dir(session_dir)
    ensure_dir(workspace_root)
    build_shim(shim_dir, real_pi, invocation_log)

    skill_text = read_text(SKILL_MD) if os.path.exists(SKILL_MD) else ""
    if "orchestrate" in variants and not skill_text:
        raise SystemExit(f"orchestrate variant requested but {SKILL_MD} is missing")
    classifier_path = os.path.join(HERE, "jev_classifier.py")
    # The two-variant mode keeps one shared prompt; arm mode gives every arm its own.
    system_prompt_path = os.path.join(out_dir, "orchestrate-system-prompt.md")
    if not arm_specs:
        write_text(
            system_prompt_path,
            skill_text + "\n\n" + ORCHESTRATE_DIRECTIVE.format(classifier=classifier_path),
        )
    arm_prompts = {
        arm_id: arm_defs.system_prompt_for(spec, out_dir, classifier_path)
        for arm_id, spec in arm_specs.items()
    }

    environment = dict(os.environ)
    environment["PATH"] = shim_dir + os.pathsep + environment.get("PATH", "")
    environment["BM_SESSION_DIR"] = session_dir
    environment["BM_INVOCATION_LOG"] = invocation_log
    environment["JEV_ADAPTER_LOG"] = jev_adapter_log
    environment["BM_ENV_FILE"] = args.env_file

    # The skill reads its provider key from the inherited child environment, and
    # only the skill variant receives it: the plain baseline has no consumer for
    # a provider credential, and putting one in its environment would expose a
    # secret to a process that has no reason to hold it. The base environment is
    # scrubbed first so that a value already present in this shell cannot leak
    # into the baseline either.
    credential = ""
    if args.env_file:
        credential = read_credential(args.env_file, CREDENTIAL_VARIABLE)
    environment.pop(CREDENTIAL_VARIABLE, None)
    variant_environments = {name: dict(environment) for name in variants}
    if credential and "orchestrate" in variant_environments:
        variant_environments["orchestrate"][CREDENTIAL_VARIABLE] = credential
    # An arm receives the provider credential only when it declares the plane on, so an arm
    # that cannot call the plane never holds a secret it has no use for.
    if credential:
        for arm_id, spec in arm_specs.items():
            if spec.get("plane") == "on":
                variant_environments[arm_id][CREDENTIAL_VARIABLE] = credential

    try:
        check_run_identity(out_dir, variants)
    except RunIdentityError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2

    manifest = {
        "fixtureId": payload.get("id"),
        "workspaceDigest": payload.get("workspaceDigest"),
        "graderDigest": payload.get("graderDigest"),
        "provider": PROVIDER,
        "model": MODEL,
        "trials": args.trials,
        "capUsd": args.cap_usd,
        "variants": variants,
        "arms": [arm_specs[name] for name in variants] if arm_specs else [],
        "taskCount": len(tasks),
        "credentialAvailable": bool(credential),
        "credentialVariable": CREDENTIAL_VARIABLE,
        "credentialSource": "env-file" if credential else "absent",
        "startedAt": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }
    write_text(os.path.join(out_dir, "manifest.json"), json.dumps(manifest, indent=2) + "\n")

    # Resume support. A run that is interrupted partway (a wall-clock timeout on
    # the harness, not a failure of any trial) leaves every completed trial on
    # disk. Re-running the whole suite would re-spend on work already done, so
    # `--resume` skips tuples already present and seeds the budget counter from
    # the sessions already under the run directory, which keeps the cap honest.
    runtime_name, runtime_version = runtime_identity(real_pi)
    resume_done: set = set()
    if args.resume and os.path.exists(results_path):
        for line in read_text(results_path).splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                prior = json.loads(line)
            except json.JSONDecodeError:
                continue
            if prior.get("costUsd") is not None:
                resume_done.add((prior.get("taskId"), prior.get("variant"), prior.get("trial")))
        print(f"resume: {len(resume_done)} trial already recorded, skipping them", flush=True)

    existing_pool = session_files(session_dir)
    spent = combine(existing_pool, list(existing_pool))["costUsd"] if existing_pool else 0.0
    if resume_done:
        print(f"resume: budget already spent ${spent:.4f}", flush=True)
    planned = len(variants) * len(tasks) * args.trials
    completed = 0
    # Task-major, then trial, then variant: the two variants of a given task and
    # trial run back to back. That keeps a pair under near-identical provider
    # conditions, so a slow period or a model revision cannot land on one arm
    # only, and it surfaces a broken candidate arm within minutes rather than
    # after the whole baseline has run.
    for task in tasks:
        for trial in range(1, args.trials + 1):
            for variant in variants:
                record = {
                    "variant": variant,
                    "taskId": task["id"],
                    "cohort": task["cohort"],
                    "type": task["type"],
                    "trial": trial,
                }
                if (task["id"], variant, trial) in resume_done:
                    continue
                if spent >= args.cap_usd:
                    record.update({"status": "skipped", "reason": "budget cap reached"})
                    append_result(results_path, record)
                    continue

                name = f"{variant}-{task['id']}-t{trial}"
                workspace = os.path.join(workspace_root, name)
                if os.path.isdir(workspace):
                    try:
                        shutil.rmtree(workspace)
                    except OSError as exc:
                        raise SystemExit(f"cannot clear {workspace}: {exc}") from exc
                materialize(payload, workspace)
                spec = arm_specs.get(variant) or {}
                if spec:
                    arm_defs.materialize_skill(spec, workspace)

                stats_before = session_files(session_dir)
                dispatches_before = count_log_lines(invocation_log)

                started = time.monotonic()
                arm_provider = spec.get("provider", PROVIDER)
                arm_model = spec.get("model", MODEL)
                arm_effort = spec.get("effort")
                command = [
                    real_pi,
                    # `--no-extensions` is not optional here. An installed extension can
                    # silently re-route the declared model to another provider, which makes
                    # the arm measure something other than what it declares. The first
                    # frontier run was stopped for exactly that reason.
                    "--no-extensions",
                    "--no-skills",
                    "--provider",
                    arm_provider,
                    "--model",
                    arm_model,
                    "--print",
                    "--mode",
                    "json",
                ]
                if arm_effort:
                    command += ["--thinking", arm_effort]
                if arm_specs:
                    prompt = arm_prompts.get(variant)
                else:
                    prompt = system_prompt_path if variant == "orchestrate" else None
                if prompt:
                    command += ["--append-system-prompt", prompt]
                command += [task["prompt"]]
                command = apply_session_dir(command, session_dir)

                status = "ok"
                failure = ""
                try:
                    finished = subprocess.run(
                        command,
                        cwd=workspace,
                        env=variant_environments[variant],
                        capture_output=True,
                        text=True,
                        timeout=args.agent_timeout,
                    )
                    exit_code = finished.returncode
                    stdout_tail = (finished.stdout or "")[-4000:]
                    stderr_tail = (finished.stderr or "")[-2000:]
                except subprocess.TimeoutExpired:
                    exit_code = -1
                    status = "timeout"
                    failure = f"agent exceeded {args.agent_timeout}s"
                    stdout_tail = stderr_tail = ""
                duration = time.monotonic() - started

                settlement = settle_session_dir(session_dir)
                stats_after = session_files(session_dir)
                fresh_sessions = [path for path in stats_after if path not in stats_before]
                escaped = escaped_session_files(workspace)
                pool = dict(stats_after)
                for path in escaped:
                    pool[path] = session_file_stats(path)
                trial_stats = combine(pool, fresh_sessions + escaped)
                spent = combine(pool, list(pool))["costUsd"]
                dispatches = max(0, count_log_lines(invocation_log) - dispatches_before)

                # Resolve which models actually did paid work *before* the result record is
                # built, because the record has to carry the contamination verdict.
                requested_key = f"{arm_provider}/{arm_model}"
                may_dispatch = arm_may_dispatch(spec)
                resolution = resolve_models(trial_stats.get("modelCosts") or {},
                                            requested_key, may_dispatch=may_dispatch)
                dominant = resolution.get("dominant") or ""
                resolved_provider, _, resolved_model = dominant.partition("/")
                if resolution["contaminated"]:
                    print(
                        f"  WARNING {name}: {resolution['reason']}",
                        flush=True,
                    )

                rejection = provider_error(fresh_sessions + escaped)
                recovered_error = None
                verdict = classify_provider_error(rejection, trial_stats["costUsd"])
                if verdict == "invalid":
                    # Nothing ran and nothing was paid for: the provider refused the model.
                    status = "invalid"
                    failure = rejection
                    print(
                        f"  WARNING {name}: the provider refused the model; "
                        f"recorded as invalid, not as a task failure: {rejection}",
                        flush=True,
                    )
                elif verdict == "recovered":
                    # The model ran and did paid work, then hit an error it recovered from.
                    # That is a reliability observation, not an availability verdict. Flipping
                    # the status on any error mislabelled five successful ablation trials,
                    # including one that dispatched 14 times and cost $1.80 before finishing.
                    recovered_error = rejection
                    print(
                        f"  note {name}: recovered provider error "
                        f"({str(rejection)[:60]}); trial kept, recorded as a reliability observation",
                        flush=True,
                    )

                install_graders(payload, workspace)
                passed, grader_output = run_grader(workspace, task["grader"])

                record.update(
                    {
                        "arm": spec.get("id") or variant,
                        "armKind": spec.get("kind"),
                        "armNote": spec.get("note"),
                        "requestedProvider": arm_provider,
                        "requestedModel": arm_model,
                        "requestedEffort": arm_effort,
                        "skillSource": spec.get("skill"),
                        "planeState": spec.get("plane"),
                        "armContaminated": resolution["contaminated"],
                        "foreignModels": resolution.get("foreign") or [],
                        "resolvedModels": resolution.get("resolved") or [],
                        "recoveredError": recovered_error,
                        "status": status,
                        "failure": failure,
                        "agentExitCode": exit_code,
                        "success": bool(passed),
                        "durationSeconds": round(duration, 3),
                        "costUsd": round(trial_stats["costUsd"], 6),
                        "cumulativeCostUsd": round(spent, 6),
                        "tokens": trial_stats["tokens"],
                        "models": trial_stats["models"],
                        "sessionFiles": trial_stats["sessionFiles"],
                        "sessionPaths": fresh_sessions,
                        "escapedSessionPaths": escaped,
                        "escapedSessionFiles": len(escaped),
                        "dispatches": dispatches,
                        "settled": settlement["settled"],
                        "settleWaitedSeconds": settlement["waitedSeconds"],
                        "graderOutputTail": grader_output[-1500:],
                        "stdoutTail": stdout_tail[-1500:],
                        "stderrTail": stderr_tail[-800:],
                        "workspace": workspace,
                    }
                )
                gate = read_trace_payload(workspace, "gate")
                route_decision = read_trace_payload(workspace, "route")
                append_trial_record(
                    out_dir,
                    trial_schema.build_trial_record(
                        {
                            "variant": variant,
                            "taskId": task["id"],
                            "cohort": task["cohort"],
                            "type": task["type"],
                            "trial": trial,
                            "status": status,
                            "success": bool(passed),
                            "durationSeconds": round(duration, 3),
                            "requestedProvider": arm_provider,
                            "requestedModel": arm_model,
                            "requestedEffort": arm_effort,
                            "resolvedProvider": resolved_provider or None,
                            "resolvedModel": resolved_model or None,
                            "resolvedEffort": (route_decision or {}).get("selectedEffortMode"),
                            "failureClass": "infrastructure" if status in ("timeout", "invalid") else None,
                            "deterministicVerificationResult": "pass" if passed else "fail",
                        },
                        trial_capabilities(trial_stats, runtime_version, gate),
                        model_costs=trial_stats.get("modelCosts") or {},
                        roles=read_role_assignments(workspace),
                        route_decision=route_decision,
                        evidence_scope=(route_decision or {}).get("evidenceCohort"),
                        runtime_name=runtime_name,
                    ),
                    name,
                )
                append_result(results_path, record)
                completed += 1
                print(
                    f"[{completed}/{planned}] {name:44} success={passed!s:5} "
                    f"cost=${record['costUsd']:.4f} cum=${spent:.2f} dur={duration:.1f}s",
                    flush=True,
                )

    summary = dict(manifest)
    summary.update({"finishedAt": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "spentUsd": round(spent, 6)})
    write_text(os.path.join(out_dir, "summary.json"), json.dumps(summary, indent=2) + "\n")
    print(f"total spent ${spent:.4f} of cap ${args.cap_usd:.2f}")
    return 0


TRIALS_FILE = "trials.jsonl"

#: Where the skill may leave a decision trace, in the order it writes them.
TRACE_CANDIDATES = (
    "trace.jsonl",
    os.path.join(".orchestrate", "trace.jsonl"),
    "decisions.jsonl",
    os.path.join(".orchestrate", "decisions.jsonl"),
)

#: The roles a resolved model can hold in the component cost split.
ROLES = ("coordinator", "worker", "classifier", "arbiter")


def settle_session_dir(
    session_dir: str,
    quiet_checks: int = 3,
    poll_seconds: float = 1.0,
    timeout_seconds: float = 120.0,
) -> dict:
    """Wait until the session directory stops changing, then report the settled state.

    A dispatched ``pi`` session can outlive the trial that started it: the parent process
    exits while the child is still appending to its own session file. Snapshotting
    immediately attributes that cost to no trial, which understates whichever arm dispatched
    more. So the directory is polled until its file count and total cost hold still for
    ``quiet_checks`` consecutive reads, bounded by ``timeout_seconds``.
    """
    deadline = time.monotonic() + timeout_seconds
    stable = 0
    previous = None
    waited = 0.0
    while time.monotonic() < deadline:
        snapshot = session_files(session_dir)
        signature = (len(snapshot), round(combine(snapshot, list(snapshot))["costUsd"], 6))
        if signature == previous:
            stable += 1
            if stable >= quiet_checks:
                return {"settled": True, "waitedSeconds": round(waited, 3), "files": len(snapshot)}
        else:
            stable = 0
            previous = signature
        time.sleep(poll_seconds)
        waited += poll_seconds
    return {"settled": False, "waitedSeconds": round(waited, 3), "files": len(session_files(session_dir))}


def runtime_identity(real_pi: str) -> tuple[str, str | None]:
    """The runtime's own reported version, or ``None`` when it reports none."""
    try:
        finished = subprocess.run(
            [real_pi, "--version"], capture_output=True, text=True, timeout=60
        )
    except (OSError, subprocess.TimeoutExpired):
        return "pi", None
    text = ((finished.stdout or "") + (finished.stderr or "")).strip()
    if not text:
        return "pi", None
    return "pi", text.splitlines()[0].strip() or None


def _collect_roles(node, assignments: dict) -> None:
    """Collect model-to-role assignments from any nesting of the run's runtime record."""
    if isinstance(node, dict):
        role = node.get("role")
        model = node.get("model") or node.get("modelId")
        if isinstance(role, str) and role in ROLES and isinstance(model, str) and model:
            provider = node.get("provider")
            key = f"{provider}/{model}" if isinstance(provider, str) and provider else model
            assignments[key] = role
        for value in node.values():
            _collect_roles(value, assignments)
    elif isinstance(node, list):
        for value in node:
            _collect_roles(value, assignments)


def read_role_assignments(workspace: str) -> dict:
    """Model-to-role assignments the run recorded, empty when it recorded none.

    A shape this reader does not recognise yields no assignments rather than an exception, and
    an unassigned model is a worker downstream, so an unexpected file can understate a role
    but never invent one.
    """
    for name in ("runtimes.json", os.path.join(".orchestrate", "runtimes.json")):
        path = os.path.join(workspace, name)
        if not os.path.exists(path):
            continue
        try:
            data = json.loads(read_text(path))
        except (json.JSONDecodeError, OSError):
            return {}
        assignments: dict = {}
        _collect_roles(data, assignments)
        return assignments
    return {}


def read_trace_payload(workspace: str, kind: str) -> dict | None:
    """The last record of ``kind`` the run left behind, or ``None``.

    Absence is a real answer: a trial where the skill settled nothing to disk has no route
    record, and reporting that as missing is more useful than inventing one.
    """
    found = None
    for name in TRACE_CANDIDATES:
        path = os.path.join(workspace, name)
        if not os.path.exists(path):
            continue
        for line in read_text(path).splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            if entry.get("kind") == kind and isinstance(entry.get("payload"), dict):
                found = entry["payload"]
    return found


def dominant_model(models: dict) -> str | None:
    """The model that produced the most activity in this trial."""
    if not models:
        return None
    return max(models.items(), key=lambda item: item[1])[0]


class RunIdentityError(RuntimeError):
    """Raised when a run would be appended to a directory holding a different arm set."""


def check_run_identity(out_dir: str, variants: list) -> None:
    """Refuse to append a run to a directory that already holds a different arm set.

    A run directory belongs to one experiment. Appending a second arm set to the same
    directory mixes two experiments: `results.jsonl` then holds trials whose arms no longer
    correspond to the manifest, and the audit recomputes over both as if they were one run.
    That mistake was made once during this goal -- the third frontier attempt wrote into the
    second attempt's directory, so eight arms from two different arm files shared one
    results file. The check exists so it cannot be made twice.
    """
    manifest_path = os.path.join(out_dir, "manifest.json")
    if not os.path.exists(manifest_path):
        return
    try:
        with open(manifest_path, "r", encoding="utf-8") as handle:
            previous = json.load(handle)
    except (OSError, json.JSONDecodeError):
        # An unreadable manifest is not evidence of a different arm set, and refusing here
        # would block a legitimate resume of a partially written run.
        return
    previous_variants = list(previous.get("variants") or [])
    if previous_variants and previous_variants != list(variants):
        raise RunIdentityError(
            f"refusing to append to {out_dir}: it holds a different arm set "
            f"({previous_variants}) than this run ({list(variants)}); "
            f"use a new --out directory"
        )


def provider_error(session_paths: list) -> str | None:
    """The provider's rejection message, when a model refused to run at all.

    `pi` exits 0 when the provider rejects a model, so without this check a trial in which
    nothing ran is recorded as a task the model failed -- a quality verdict where the truth
    is an availability verdict. The second frontier run contained exactly that:
    `gpt-5.3-codex-spark` is listed by the catalog and refused by a ChatGPT-account login,
    which produced a $0.0000 "failure" after 3.8 seconds.
    """
    for path in session_paths:
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as handle:
                for line in handle:
                    try:
                        record = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    message = record.get("message")
                    if not isinstance(message, dict):
                        continue
                    if message.get("stopReason") == "error" and message.get("errorMessage"):
                        return str(message["errorMessage"])
        except OSError:
            continue
    return None


def classify_provider_error(rejection: str | None, cost_usd: float) -> str:
    """Whether a provider error makes a trial unavailable or merely unreliable.

    Returns `"none"`, `"invalid"` or `"recovered"`.

    The distinction is the one the harness got wrong. A provider error with no paid work
    behind it means the model never ran -- the ID-5 case, where `gpt-5.3-codex-spark` cost
    $0.0000 and finished in 3.8 seconds. A provider error with paid work behind it means the
    model ran, was billed, hit something transient, and the agent carried on -- which is
    what happened to five ablation trials that succeeded while being recorded as invalid.
    Only the first is an availability verdict.
    """
    if not rejection:
        return "none"
    return "invalid" if cost_usd <= 0 else "recovered"


def arm_may_dispatch(spec: dict) -> bool:
    """Whether an arm is expected to delegate work to other models.

    An arm carrying the dispatch directive may orchestrate, so several paid models are the
    treatment rather than a defect. An arm without the directive, or one explicitly told not
    to dispatch, must stay on its declared model. The observed dispatch counts agree with
    this rule: V0 and VN recorded 0 dispatches and one paid model each, while V1-V5 recorded
    10-18 dispatches and four to five paid models each.
    """
    return spec.get("directive") == "orchestrate" and not spec.get("noDispatchNote")


def resolve_models(model_costs: dict, requested: str, may_dispatch: bool = False) -> dict:
    """Which models actually did paid work, and whether the arm's model was among them.

    Counting `model_change` entries is not enough: an arm can announce its declared model and
    then have an extension re-route the work to a different provider, which leaves the
    declared model with a `model_change` and **no usage at all**. Weighting by cost is what
    makes that visible, and naming the foreign models is what makes it auditable.

    The verdict depends on whether the arm is *expected* to dispatch. A non-dispatching arm
    must have exactly one paid model, so any other model doing paid work is contamination. A
    dispatching arm is an orchestrator: its other paid models are the treatment, and
    contamination there means the declared coordinator did no work at all. Applying the
    non-dispatching rule to an orchestrator reports the treatment as a defect, which is what
    the first ablation attempt did to V1-V5.
    """
    paid = {model: cost for model, cost in (model_costs or {}).items() if cost > 0}
    if not paid:
        return {"resolved": [], "dominant": None, "contaminated": False,
                "foreign": [], "unknown": True, "mayDispatch": may_dispatch,
                "reason": None}
    dominant = max(paid.items(), key=lambda item: item[1])[0]
    foreign = sorted(model for model in paid if model != requested)
    if may_dispatch:
        contaminated = requested not in paid
        reason = (None if not contaminated else
                  f"the declared coordinator {requested} did no paid work")
    else:
        contaminated = bool(foreign)
        reason = (None if not contaminated else
                  f"{', '.join(foreign)} did paid work in a non-dispatching arm")
    return {"resolved": sorted(paid), "dominant": dominant,
            "contaminated": contaminated, "foreign": foreign, "unknown": False,
            "mayDispatch": may_dispatch, "reason": reason}


def _token_capability(stats: dict, field: str) -> dict:
    """A token count is exposed only when the provider actually reported the field."""
    if field in set(stats.get("tokenFieldsSeen") or []):
        return trial_schema.capability(trial_schema.EXPOSED, as_int(stats["tokens"].get(field)))
    return trial_schema.capability(trial_schema.NOT_EXPOSED)


def trial_capabilities(stats: dict, runtime_version: str | None, gate: dict | None) -> dict:
    """The capability entries for one trial, each labelled with how it was obtained."""
    models = sorted(stats.get("models") or {})
    digest = hashlib.sha256("\n".join(models).encode("utf-8")).hexdigest() if models else None
    resolved = dominant_model(stats.get("models") or {})
    model_id = resolved.split("/")[-1] if resolved else None
    gate = gate if isinstance(gate, dict) else {}
    tier = gate.get("tier")
    escalated = gate.get("escalated")
    reason = gate.get("escalationClause")
    c3_observed = isinstance(tier, str)
    return {
        "cacheReadTokens": _token_capability(stats, "cacheRead"),
        "cacheWriteTokens": _token_capability(stats, "cacheWrite"),
        "reasoningTokens": _token_capability(stats, "reasoning"),
        "actualMarginalCostUsd": trial_schema.capability(
            trial_schema.EXPOSED, round(stats["costUsd"], 6)
        ),
        "apiEquivalentCostUsd": trial_schema.capability(trial_schema.NOT_MEASURED),
        "quotaBurn": trial_schema.capability(trial_schema.NOT_MEASURED),
        "rateLimitRemaining": trial_schema.capability(trial_schema.NOT_MEASURED),
        "modelFamily": trial_schema.derive_model_family(model_id),
        "catalogHash": (
            trial_schema.capability(
                trial_schema.DERIVED, digest,
                basis="sha256 over the resolved models observed in this trial")
            if digest else trial_schema.capability(trial_schema.NOT_MEASURED)
        ),
        "runtimeVersion": (
            trial_schema.capability(trial_schema.EXPOSED, runtime_version)
            if runtime_version else trial_schema.capability(trial_schema.NOT_EXPOSED)
        ),
        "retries": trial_schema.capability(trial_schema.NOT_MEASURED),
        "promotions": trial_schema.capability(trial_schema.NOT_MEASURED),
        "c3Required": (
            trial_schema.capability(trial_schema.EXPOSED, tier == "C3")
            if c3_observed else trial_schema.capability(trial_schema.NOT_MEASURED)
        ),
        "c3Reason": (
            trial_schema.capability(trial_schema.EXPOSED, str(reason))
            if c3_observed and bool(escalated) and reason
            else trial_schema.capability(trial_schema.NOT_EXPOSED)
            if c3_observed
            else trial_schema.capability(trial_schema.NOT_MEASURED)
        ),
    }


def append_trial_record(out_dir: str, record: dict, label: str) -> None:
    """Append a full-schema trial record, reporting rather than hiding a schema problem.

    The record is written even when it does not validate, because a trial with a schema defect
    is evidence too, and dropping it would make the run look cleaner than it was.
    """
    problems = trial_schema.validate_trial_record(record)
    path = os.path.join(out_dir, TRIALS_FILE)
    try:
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(record) + "\n")
            handle.flush()
    except OSError as exc:
        raise SystemExit(f"cannot append {TRIALS_FILE}: {exc}") from exc
    if problems:
        print(
            f"trial-schema: {label} recorded with {len(problems)} problem(s): {problems[:6]}",
            flush=True,
        )


def count_log_lines(log_path: str) -> int:
    """Count the `pi` invocations the shim has recorded so far."""
    if not os.path.exists(log_path):
        return 0
    return len(read_text(log_path).splitlines())


def append_result(path: str, record: dict) -> None:
    try:
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(record) + "\n")
            handle.flush()
    except OSError as exc:
        raise SystemExit(f"cannot append results: {exc}") from exc


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
