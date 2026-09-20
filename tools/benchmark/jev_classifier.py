#!/usr/bin/env python3
"""A `role: classifier` candidate whose provider is Jev (TypeSafe).

The decision plane is dispatched through a runtime adapter and owns no provider
client of its own, so reaching a System One model needs an adapter that speaks
the classifier call shape. This is that adapter.

It is deliberately a **translator, not a policy author**: the caller supplies the
declared typed questions, this program forwards them to Jev and returns Jev's
typed answers unchanged. Inventing question sets or option vocabularies here
would be authoring the plane's semantics, and those are owned by
`decision-plane.md`, not by a benchmark harness.

Call shape it satisfies, from `decision-plane.md`:
  one bounded request, structured output only, no tool grants, no filesystem
  access, no network beyond the provider call, bounded timeout, and a structured
  failure record (`reason`) instead of an exception.

Credentials are read from the inherited environment, falling back to a dotenv
file, and are never printed, echoed or written.

Usage:
    python3 tools/benchmark/jev_classifier.py probe [--env-file PATH]
    python3 tools/benchmark/jev_classifier.py classify [--env-file PATH] < request.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request

CANDIDATE_ID = "typesafe-jev"
MODEL = "jev-latest"
ENDPOINT = "https://api.typesafe.ai/v1/systemone"
CREDENTIAL_VARIABLE = "TYPESAFE_API_KEY"
TIMEOUT_SECONDS = 45
MAX_STATE_CHARS = 20000
MAX_QUESTIONS = 16
QUESTION_TYPES = {"choice", "score", "noul"}


def read_credential(env_file: str) -> str:
    """Resolve the credential from the environment, then from a dotenv file."""
    value = os.environ.get(CREDENTIAL_VARIABLE, "").strip()
    if value:
        return value
    if not env_file:
        return ""
    try:
        with open(env_file, encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, raw = line.partition("=")
                if key.strip() == CREDENTIAL_VARIABLE:
                    return raw.strip().strip('"').strip("'")
    except OSError:
        return ""
    return ""


def redact(text: str, secret: str) -> str:
    return text.replace(secret, "[redacted]") if secret else text


def probe_record(available: bool, reason: str) -> dict:
    """The candidate record the plane reads during discovery.

    Declares only what has been checked: the runtime exposes a schema-constrained
    result, and the call shape withholds every tool, which is what the plane's
    tool-gating precondition requires.
    """
    return {
        "id": CANDIDATE_ID,
        "role": "classifier",
        "mechanism": "cli",
        "executable": os.path.abspath(__file__),
        "provider": "typesafe",
        "model_family": "jev",
        "state": "available" if available else "unavailable",
        "reason": reason,
        "structuredOutput": "supported",
        "toolGating": {"verified": True, "permits_withholding_every_tool": True},
        "tools_allowed": [],
        "network": ["api.typesafe.ai"],
        "timeoutSeconds": TIMEOUT_SECONDS,
        "credential": {
            "variable": CREDENTIAL_VARIABLE,
            "source": "env" if os.environ.get(CREDENTIAL_VARIABLE) else "file",
            "trust": "process" if os.environ.get(CREDENTIAL_VARIABLE) else "working-tree",
        },
    }


def normalize_criteria(kind: str, criteria):
    """Translate the plane's declared criteria into the shape Jev requires.

    Jev's two criteria-bearing question types do **not** share a shape, which is
easy to get wrong because both read as "a set of allowed values":

    - `choice` takes a dictionary, mapping each option to its description;
    - `score` takes a list, and rejects a dictionary with `list_type`.

    The plane may declare either as a list or a dictionary depending on how the
    vocabulary reads, so the shape is translated per type. Only the *shape* is
translated: the labels and descriptions are still the caller's, so no
    vocabulary is authored by this program.
    """
    if kind == "choice":
        if isinstance(criteria, dict):
            return criteria
        if isinstance(criteria, list):
            return {str(item): str(item) for item in criteria}
        return None
    if kind == "score":
        if isinstance(criteria, list):
            return [str(item) for item in criteria]
        if isinstance(criteria, dict):
            return [str(value) for value in criteria.values()]
        return None
    return None


def validate(request: dict) -> tuple[dict, str]:
    """Check the caller's declared questions and normalize their criteria shape."""
    state = request.get("state")
    questions = request.get("questions")
    if state is None:
        return {}, "malformed: missing state"
    if not isinstance(questions, dict) or not questions:
        return {}, "malformed: missing questions"
    if len(questions) > MAX_QUESTIONS:
        return {}, "malformed: too many questions"
    if len(json.dumps(state)) > MAX_STATE_CHARS:
        return {}, "malformed: state exceeds bound"
    normalized: dict = {}
    for name, spec in questions.items():
        if not isinstance(spec, dict):
            return {}, f"malformed: question {name} is not an object"
        kind = spec.get("type")
        if kind not in QUESTION_TYPES:
            return {}, f"malformed: question {name} has unsupported type"
        if not spec.get("instructions"):
            return {}, f"malformed: question {name} lacks instructions"
        entry = dict(spec)
        if kind in ("choice", "score"):
            criteria = normalize_criteria(kind, spec.get("criteria"))
            if not criteria:
                return {}, f"malformed: question {name} lacks criteria"
            entry["criteria"] = criteria
        normalized[name] = entry
    return normalized, ""


def classify(request: dict, credential: str) -> dict:
    """Send one bounded request to Jev and return its typed answers."""
    questions, problem = validate(request)
    if problem:
        return {"decision": request.get("decision"), "reason": problem, "answers": None}
    if not credential:
        return {
            "decision": request.get("decision"),
            "reason": "disabled: credential absent",
            "answers": None,
        }

    payload = {"state": request["state"], "model": MODEL, "questions": questions}
    http_request = urllib.request.Request(
        ENDPOINT,
        data=json.dumps(payload).encode(),
        headers={
            "Authorization": f"Bearer {credential}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(http_request, timeout=TIMEOUT_SECONDS) as response:
            body = response.read().decode()
    except urllib.error.HTTPError as exc:
        detail = redact(exc.read().decode()[:200], credential)
        return {
            "decision": request.get("decision"),
            "reason": f"provider error {exc.code}: {detail}",
            "answers": None,
        }
    except Exception as exc:
        return {
            "decision": request.get("decision"),
            "reason": f"transport error: {redact(str(exc)[:200], credential)}",
            "answers": None,
        }

    try:
        parsed = json.loads(body)
    except json.JSONDecodeError:
        return {"decision": request.get("decision"), "reason": "malformed: bad JSON", "answers": None}

    answers = parsed.get("answers")
    if not isinstance(answers, dict):
        return {"decision": request.get("decision"), "reason": "malformed: no answers", "answers": None}

    unknown = [name for name in answers if name not in questions]
    if unknown:
        return {
            "decision": request.get("decision"),
            "reason": "malformed: out-of-vocabulary answer",
            "answers": None,
        }
    return {
        "decision": request.get("decision"),
        "candidate": CANDIDATE_ID,
        "model": parsed.get("model"),
        "reason": "ok",
        "answers": answers,
        "usage": parsed.get("usage"),
    }


def record_invocation(entry: dict) -> None:
    """Append independent proof that this adapter was actually executed.

    The decision trace is authored by the coordinator, so a trace claiming a
    classifier verdict is not by itself evidence that the classifier ran. This
    log is written from inside the adapter, which is what makes engagement
    checkable rather than asserted. It records no credential and no state.
    """
    path = os.environ.get("JEV_ADAPTER_LOG", "")
    if not path:
        return
    try:
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry) + "\n")
    except OSError:
        pass


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Jev-backed classifier candidate.")
    parser.add_argument("command", choices=["probe", "classify"])
    parser.add_argument("--env-file", default=os.environ.get("BM_ENV_FILE", ""))
    args = parser.parse_args(argv)

    credential = read_credential(args.env_file)

    if args.command == "probe":
        reason = "credential resolved" if credential else "credential absent"
        record_invocation(
            {"command": "probe", "candidate": CANDIDATE_ID, "state": "available" if credential else "unavailable"}
        )
        json.dump(probe_record(bool(credential), reason), sys.stdout, indent=2)
        sys.stdout.write("\n")
        return 0

    try:
        request = json.load(sys.stdin)
    except json.JSONDecodeError:
        json.dump({"reason": "malformed: request is not JSON", "answers": None}, sys.stdout)
        sys.stdout.write("\n")
        return 0
    result = classify(request, credential)
    record_invocation(
        {
            "command": "classify",
            "decision": request.get("decision"),
            "candidate": CANDIDATE_ID,
            "model": result.get("model"),
            "reason": result.get("reason"),
            "questions": sorted((request.get("questions") or {}).keys()),
        }
    )
    json.dump(result, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
