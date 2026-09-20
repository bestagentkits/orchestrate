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
    for line in read_text(path).splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if record.get("type") == "model_change":
            models[f"{record.get('provider')}/{record.get('modelId')}"] += 1
        message = record.get("message")
        if not isinstance(message, dict):
            continue
        usage = message.get("usage")
        if not isinstance(usage, dict):
            continue
        cost += as_float((usage.get("cost") or {}).get("total"))
        for field in ("input", "output", "cacheRead", "cacheWrite", "reasoning"):
            tokens[field] += as_int(usage.get(field))
    return {"costUsd": cost, "tokens": dict(tokens), "models": dict(models)}


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
    for path in paths:
        entry = stats[path]
        cost += entry["costUsd"]
        for field, value in entry["tokens"].items():
            tokens[field] += value
        for model, count in entry["models"].items():
            models[model] += count
    return {
        "costUsd": cost,
        "tokens": dict(tokens),
        "models": dict(models),
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
    system_prompt_path = os.path.join(out_dir, "orchestrate-system-prompt.md")
    classifier_path = os.path.join(HERE, "jev_classifier.py")
    write_text(
        system_prompt_path,
        skill_text + "\n\n" + ORCHESTRATE_DIRECTIVE.format(classifier=classifier_path),
    )

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

    manifest = {
        "fixtureId": payload.get("id"),
        "workspaceDigest": payload.get("workspaceDigest"),
        "graderDigest": payload.get("graderDigest"),
        "provider": PROVIDER,
        "model": MODEL,
        "trials": args.trials,
        "capUsd": args.cap_usd,
        "variants": variants,
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

                stats_before = session_files(session_dir)
                dispatches_before = count_log_lines(invocation_log)

                started = time.monotonic()
                command = [
                    real_pi,
                    "--no-skills",
                    "--provider",
                    PROVIDER,
                    "--model",
                    MODEL,
                    "--print",
                    "--mode",
                    "json",
                ]
                if variant == "orchestrate":
                    command += ["--append-system-prompt", system_prompt_path]
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

                stats_after = session_files(session_dir)
                fresh_sessions = [path for path in stats_after if path not in stats_before]
                escaped = escaped_session_files(workspace)
                pool = dict(stats_after)
                for path in escaped:
                    pool[path] = session_file_stats(path)
                trial_stats = combine(pool, fresh_sessions + escaped)
                spent = combine(pool, list(pool))["costUsd"]
                dispatches = max(0, count_log_lines(invocation_log) - dispatches_before)

                install_graders(payload, workspace)
                passed, grader_output = run_grader(workspace, task["grader"])

                record.update(
                    {
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
                        "graderOutputTail": grader_output[-1500:],
                        "stdoutTail": stdout_tail[-1500:],
                        "stderrTail": stderr_tail[-800:],
                        "workspace": workspace,
                    }
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
