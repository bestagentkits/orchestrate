"""Arm definitions for the router ablation and the worker-frontier run.

An *arm* is one complete experimental configuration: which provider, model and effort run
the job, which version of the skill they are given, whether the harness directive is
attached, and whether the decision plane is enabled.

Two things this module deliberately does not do:

- it does not carry a model name as a default. Arm specs are authored from the **live
  catalog** at run time and written into the run's own artifact, so the frozen comparison
  names the environment it was measured against without any model becoming a policy
  constant;
- it does not deliver only `SKILL.md`. The skill is a directory of documents whose rules
  live in `references/`, and a trial workspace contains only the fixture, so an arm given
  the summary alone would be measured against a summary rather than against the contract.
  A skill arm therefore materialises the whole skill directory into the workspace and also
  appends `SKILL.md` to the system prompt, which is what the earlier run did.

Usage:
    python3 -m tools.benchmark.arms plan --out <file> --frontier <provider/model,effort>...
    python3 -m tools.benchmark.arms validate <file>
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(HERE))
SKILL_DIR = os.path.join(REPO_ROOT, "plugins", "orchestrate", "skills", "orchestrate")

USAGE = "usage: python3 -m tools.benchmark.arms plan|validate ..."

#: Where a skill arm's documents are placed inside the trial workspace.
SKILL_WORKSPACE_SUBDIR = ".orchestrate-skill"

#: Skill sources. `previous` resolves the contract from a pinned ref, which is how the
#: pre-change policy is measured against the new one without editing either.
SKILL_SOURCES = ("none", "current", "previous")
DIRECTIVES = ("none", "orchestrate")
PLANE_STATES = ("off", "on")

#: The ref the pre-change contract is read from. It is the commit the cost-aware contract
#: was built on top of, so `previous` means exactly "the policy as it stood before".
PREVIOUS_SKILL_REF = "a1ea8e9"

DISPATCH_DIRECTIVE = """\
You are operating under the `orchestrate` skill whose contract is above.

- Complete the user's task in this turn. Do not stop after planning, and do not
  stop after probing runtimes: the change to the working tree must actually be
  made and verified before you finish.
- You may dispatch work to other models or runtimes, and you are expected to
  choose those routes yourself. Dispatch every unit of work as a headless `pi`
  session invocation, because only those are instrumented for this measurement.
  Do not use in-session subagents, and do not dispatch to `omp`.
- Work only inside the current working directory.
"""

PLANE_DIRECTIVE = """\
- Enable the decision plane rather than leaving it as `none`. A Jev (TypeSafe)
  classifier candidate is explicitly configured for this run: obtain its record
  by running `python3 {classifier} probe`, then register that record in this
  run's `runtimes.json` with `role: classifier`. Before any plane call, record
  the egress authorization the preconditions require, naming provider
  `api.typesafe.ai` and the content classes the classifier is sent; the
  credential is in your environment already. Invoke it as
  `python3 {classifier} classify` with the request on stdin, and persist the
  enumerated decision trace to the run's `decisions.jsonl`.
"""

#: A directive for the arm that keeps the skill but removes the dispatch mandate. It exists
#: to separate "the skill's contract" from "the workflow the directive imposes", which the
#: settlement analysis showed cannot be separated without it.
NO_DISPATCH_NOTE = """\
- You are not required to dispatch work to other runtimes for this measurement, and you may
  complete the task with this session alone. Follow the skill's contract otherwise.
"""


class ArmError(ValueError):
    """Raised for an arm specification that cannot be used."""


def _run(command: list[str], timeout: int = 120) -> tuple[int, str]:
    try:
        finished = subprocess.run(command, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired):
        return -1, ""
    return finished.returncode, (finished.stdout or "").strip()


def live_catalog() -> list[tuple[str, str]]:
    """The runtime's own model listing as ``(provider, model)`` pairs.

    Resolved from the runtime rather than transcribed, so no catalog value becomes a
    constant of this module.
    """
    code, text = _run(["pi", "--no-extensions", "--list-models"])
    if code != 0 or not text:
        return []
    pairs = []
    for line in text.splitlines()[1:]:
        parts = line.split()
        if len(parts) >= 2:
            pairs.append((parts[0], parts[1]))
    return pairs


def read_git_text(ref: str, path: str) -> str:
    """One file's contents at a ref, or an empty string when it does not exist there."""
    code, text = _run(["git", "-C", REPO_ROOT, "show", f"{ref}:{path}"], timeout=60)
    return text if code == 0 else ""


def list_git_files(ref: str, directory: str) -> list[str]:
    """Every file under a directory at a ref."""
    code, text = _run(
        ["git", "-C", REPO_ROOT, "ls-tree", "-r", "--name-only", ref, "--", directory],
        timeout=60,
    )
    if code != 0:
        return []
    return [line.strip() for line in text.splitlines() if line.strip()]


def skill_files(source: str) -> dict:
    """The skill's files for an arm, keyed by their path relative to the skill directory."""
    relative = os.path.relpath(SKILL_DIR, REPO_ROOT)
    if source == "none":
        return {}
    if source == "current":
        files = {}
        try:
            for current, _dirs, names in os.walk(SKILL_DIR):
                for name in sorted(names):
                    absolute = os.path.join(current, name)
                    with open(absolute, encoding="utf-8") as handle:
                        files[os.path.relpath(absolute, SKILL_DIR)] = handle.read()
        except OSError as exc:
            raise ArmError(f"cannot read the skill directory: {exc}") from exc
        return files
    if source == "previous":
        files = {}
        for path in list_git_files(PREVIOUS_SKILL_REF, relative):
            content = read_git_text(PREVIOUS_SKILL_REF, path)
            files[os.path.relpath(path, relative)] = content
        return files
    raise ArmError(f"unknown skill source {source!r}")


def build_directive(arm: dict, classifier_path: str) -> str:
    """The harness directive for an arm, assembled from its declared parts."""
    directive = arm.get("directive", "none")
    plane = arm.get("plane", "off")
    if directive == "none" and arm.get("noDispatchNote"):
        return NO_DISPATCH_NOTE
    if directive == "none":
        return ""
    text = DISPATCH_DIRECTIVE
    if arm.get("noDispatchNote"):
        text = text.replace(
            "- You may dispatch work to other models or runtimes, and you are expected to\n"
            "  choose those routes yourself. Dispatch every unit of work as a headless `pi`\n"
            "  session invocation, because only those are instrumented for this measurement.\n"
            "  Do not use in-session subagents, and do not dispatch to `omp`.\n",
            NO_DISPATCH_NOTE,
        )
    if plane == "on":
        text = text.replace(
            "- Work only inside the current working directory.\n",
            PLANE_DIRECTIVE.format(classifier=classifier_path)
            + "- Work only inside the current working directory.\n",
        )
    return text


def system_prompt_for(arm: dict, out_dir: str, classifier_path: str) -> str | None:
    """Write an arm's system prompt and return its path, or ``None`` when it has none."""
    files = skill_files(arm.get("skill", "none"))
    directive = build_directive(arm, classifier_path)
    if not files and not directive:
        return None
    skill_md = files.get("SKILL.md", "")
    text = skill_md + ("\n\n" + directive if directive else "")
    if not text.strip():
        return None
    path = os.path.join(out_dir, f"arm-{arm['id']}-system-prompt.md")
    try:
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)
    except OSError as exc:
        raise ArmError(f"cannot write the arm system prompt: {exc}") from exc
    return path


def materialize_skill(arm: dict, workspace: str) -> int:
    """Place an arm's skill documents inside the trial workspace. Returns the file count."""
    files = skill_files(arm.get("skill", "none"))
    if not files:
        return 0
    target = os.path.join(workspace, SKILL_WORKSPACE_SUBDIR)
    written = 0
    for relative, content in sorted(files.items()):
        path = os.path.join(target, relative)
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(content)
        except OSError as exc:
            raise ArmError(f"cannot materialize the skill into the workspace: {exc}") from exc
        written += 1
    return written


def validate_arms(arms) -> list[str]:
    """Every problem with an arm list, as stable machine-readable codes."""
    if not isinstance(arms, list) or not arms:
        return ["not-a-list"]
    problems: list[str] = []
    seen: set = set()
    for arm in arms:
        if not isinstance(arm, dict):
            problems.append("arm-not-an-object")
            continue
        arm_id = arm.get("id")
        if not arm_id:
            problems.append("missing-id")
        elif arm_id in seen:
            problems.append(f"duplicate-id:{arm_id}")
        else:
            seen.add(arm_id)
        for field in ("provider", "model"):
            if not arm.get(field):
                problems.append(f"missing:{field}:{arm_id}")
        if arm.get("skill", "none") not in SKILL_SOURCES:
            problems.append(f"unknown-skill:{arm_id}")
        if arm.get("directive", "none") not in DIRECTIVES:
            problems.append(f"unknown-directive:{arm_id}")
        if arm.get("plane", "off") not in PLANE_STATES:
            problems.append(f"unknown-plane:{arm_id}")
        if arm.get("plane") == "on" and arm.get("skill", "none") == "none":
            problems.append(f"plane-without-a-skill:{arm_id}")
    return problems


def load_arms(path: str) -> list[dict]:
    try:
        with open(path, encoding="utf-8") as handle:
            arms = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        raise ArmError(f"cannot read {path}: {exc}") from exc
    problems = validate_arms(arms)
    if problems:
        raise ArmError(f"invalid arm list: {problems}")
    return arms


def plan_frontier_arms(models: list[tuple[str, str]], effort: str) -> list[dict]:
    """One arm per ``(provider, model)`` at a fixed effort, with no skill and no directive.

    This is the worker-frontier run: the models are measured directly on the frozen fixture,
    which is what the manifest requires before any router is measured, so that the policy's
    effect is not confounded with the composition of the candidate set.
    """
    arms = []
    for provider, model in models:
        arms.append({
            "id": f"W-{provider}-{model}",
            "provider": provider,
            "model": model,
            "effort": effort,
            "skill": "none",
            "directive": "none",
            "plane": "off",
            "kind": "worker-frontier",
        })
    return arms


def plan_ablation_arms(provider: str, model: str, effort: str) -> list[dict]:
    """The manifest's ablation arms plus the arm that removes the dispatch mandate.

    V4 and V5 assume a calibrated micro-arbiter. In a run that has not accumulated
    calibration samples they degrade to V3, and the arm note says so rather than implying a
    configuration that was not actually exercised.
    """
    calibration_note = ("In a run without accumulated calibration samples this arm degrades "
                        "to V3; the degradation is recorded rather than assumed away.")
    return [
        {"id": "V0", "provider": provider, "model": model, "effort": effort,
         "skill": "none", "directive": "none", "plane": "off",
         "kind": "ablation", "note": "strong single-model baseline"},
        {"id": "V1", "provider": provider, "model": model, "effort": effort,
         "skill": "previous", "directive": "orchestrate", "plane": "on",
         "kind": "ablation",
         "note": "the pre-change policy, measured as skill-plus-directive"},
        {"id": "V2", "provider": provider, "model": model, "effort": effort,
         "skill": "current", "directive": "orchestrate", "plane": "off",
         "kind": "ablation", "note": "the new deterministic cost-aware router, plane off"},
        {"id": "V3", "provider": provider, "model": model, "effort": effort,
         "skill": "current", "directive": "orchestrate", "plane": "on",
         "kind": "ablation", "note": "V2 with the plane called only where it can matter"},
        {"id": "V4", "provider": provider, "model": model, "effort": effort,
         "skill": "current", "directive": "orchestrate", "plane": "on",
         "kind": "ablation", "note": "V3 with a calibrated micro-arbiter. " + calibration_note},
        {"id": "V5", "provider": provider, "model": model, "effort": effort,
         "skill": "current", "directive": "orchestrate", "plane": "on",
         "kind": "ablation", "note": "V4 with durable calibration reuse. " + calibration_note},
        {"id": "VN", "provider": provider, "model": model, "effort": effort,
         "skill": "current", "directive": "orchestrate", "plane": "off",
         "noDispatchNote": True, "kind": "ablation",
         "note": "the new contract WITHOUT the dispatch mandate; the arm that separates the "
                 "skill's contract from the workflow the directive imposes"},
    ]


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Plan or validate benchmark arms.")
    sub = parser.add_subparsers(dest="command", required=True)

    plan = sub.add_parser("plan", help="write an arm list")
    plan.add_argument("--out", required=True)
    plan.add_argument("--mode", choices=("frontier", "ablation"), required=True)
    plan.add_argument("--provider", default="", help="provider for the ablation arms")
    plan.add_argument("--model", default="", help="model for the ablation arms")
    plan.add_argument("--effort", default="high")
    plan.add_argument("--frontier", default="", help="comma-separated provider/model pairs")

    check = sub.add_parser("validate", help="validate an arm list")
    check.add_argument("path")

    args = parser.parse_args(argv)

    if args.command == "validate":
        try:
            with open(args.path, encoding="utf-8") as handle:
                arms = json.load(handle)
        except (OSError, json.JSONDecodeError) as exc:
            print(f"INVALID: cannot read {args.path}: {exc}", file=sys.stderr)
            return 1
        problems = validate_arms(arms)
        if problems:
            print(f"INVALID: {problems}")
            return 1
        print("arms valid")
        return 0

    if args.mode == "frontier":
        if args.frontier:
            pairs = []
            for item in args.frontier.split(","):
                item = item.strip()
                if item:
                    provider, _, model = item.partition("/")
                    pairs.append((provider, model))
        else:
            pairs = live_catalog()
        arms = plan_frontier_arms(pairs, args.effort)
    else:
        arms = plan_ablation_arms(args.provider, args.model, args.effort)

    problems = validate_arms(arms)
    if problems:
        print(f"INVALID: {problems}", file=sys.stderr)
        return 1
    try:
        with open(args.out, "w", encoding="utf-8") as handle:
            handle.write(json.dumps(arms, indent=2) + "\n")
    except OSError as exc:
        print(f"cannot write {args.out}: {exc}", file=sys.stderr)
        return 1
    print(f"wrote {len(arms)} arm(s) to {args.out}")
    for arm in arms:
        print(f"  {arm['id']:34} {arm['provider']}/{arm['model']}@{arm.get('effort')} "
              f"skill={arm.get('skill')} directive={arm.get('directive')} plane={arm.get('plane')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
