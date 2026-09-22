"""Pre-flight probe: which catalog models can this account actually run?

A model can be listed in the live catalog and still be unusable with the credentials on
this machine. `pi` exits 0 when the provider rejects a model, so a trial in which nothing
ran is indistinguishable from a trial the model failed -- and would be reported as a
quality result. The first frontier run contained exactly that: `gpt-5.3-codex-spark` is
listed by the catalog and rejected by a ChatGPT-account login, which produced a $0.0000
"failure" after 3.8 seconds.

This probe separates "the model cannot run here" from "the model ran and failed", before
any arm is planned, at the cost of one trivial call per candidate.

The probe never prints a credential: it reads only the model's own JSON stream, and the
only error text it keeps is the provider's rejection message.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time

PROBE_PROMPT = "Reply with the single word OK"
PROBE_TIMEOUT_SECONDS = 120


def pi_binary() -> str:
    """The real `pi` on PATH, never the benchmark shim."""
    found = shutil.which("pi")
    if not found:
        raise RuntimeError("pi is not on PATH; the probe cannot run")
    return found


def as_int(value) -> int:
    """Coerce a provider-reported count, tolerating anything a provider may send.

    Usage fields arrive from outside the process, so a string, a float or a missing key is
    possible; a probe that crashed on one odd field would report a usable model as broken.
    """
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def parse_probe_stream(text: str) -> dict:
    """Read the provider's verdict out of a `--mode json` stream.

    A usable model ends its turn with usage; an unusable one ends it with `stopReason`
    `error` and an `errorMessage`. Both are reported, because "no error" and "no work"
    are different facts and only the pair distinguishes them.
    """
    error_message = None
    output_tokens = 0
    input_tokens = 0
    saw_message = False
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        message = record.get("message")
        if not isinstance(message, dict):
            continue
        if message.get("role") != "assistant":
            continue
        saw_message = True
        usage = message.get("usage") or {}
        output_tokens += as_int(usage.get("output"))
        input_tokens += as_int(usage.get("input"))
        if message.get("stopReason") == "error" and message.get("errorMessage"):
            error_message = str(message["errorMessage"])
    return {
        "sawAssistantMessage": saw_message,
        "errorMessage": error_message,
        "inputTokens": input_tokens,
        "outputTokens": output_tokens,
    }


def probe_model(provider: str, model: str, timeout_seconds: int = PROBE_TIMEOUT_SECONDS) -> dict:
    """Run one trivial call and report whether the model can run here at all."""
    command = [
        pi_binary(),
        # The probe must measure the model the arm will actually use, so the same isolation
        # the harness applies is applied here: an extension can re-route the model silently.
        "--no-extensions",
        "--no-skills",
        "--provider",
        provider,
        "--model",
        model,
        "--print",
        "--mode",
        "json",
        PROBE_PROMPT,
    ]
    started = time.monotonic()
    try:
        finished = subprocess.run(
            command, capture_output=True, text=True, timeout=timeout_seconds, check=False
        )
        parsed = parse_probe_stream(finished.stdout or "")
        exit_code = finished.returncode
        stderr_tail = (finished.stderr or "")[-300:]
    except subprocess.TimeoutExpired:
        parsed = {"sawAssistantMessage": False, "errorMessage": None,
                  "inputTokens": 0, "outputTokens": 0}
        exit_code = -1
        stderr_tail = f"probe exceeded {timeout_seconds}s"
    except OSError as error:
        parsed = {"sawAssistantMessage": False, "errorMessage": str(error),
                  "inputTokens": 0, "outputTokens": 0}
        exit_code = -1
        stderr_tail = str(error)

    usable = bool(parsed["sawAssistantMessage"] and not parsed["errorMessage"])
    return {
        "provider": provider,
        "model": model,
        "route": f"{provider}/{model}",
        "usable": usable,
        "errorMessage": parsed["errorMessage"],
        "sawAssistantMessage": parsed["sawAssistantMessage"],
        "inputTokens": parsed["inputTokens"],
        "outputTokens": parsed["outputTokens"],
        "exitCode": exit_code,
        "stderrTail": stderr_tail,
        "durationSeconds": round(time.monotonic() - started, 3),
    }


def probe_all(routes: list[str], timeout_seconds: int = PROBE_TIMEOUT_SECONDS) -> list[dict]:
    """Probe `provider/model` routes in order, keeping every verdict."""
    results = []
    for route in routes:
        provider, _, model = route.partition("/")
        if not provider or not model:
            raise ValueError(f"route must be provider/model, got {route!r}")
        results.append(probe_model(provider, model, timeout_seconds))
    return results


def summarize(results: list[dict]) -> dict:
    usable = [r["route"] for r in results if r["usable"]]
    unusable = {r["route"]: r["errorMessage"] for r in results if not r["usable"]}
    return {
        "probed": len(results),
        "usable": usable,
        "unusable": unusable,
        "results": results,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Probe which catalog models can run here")
    parser.add_argument("--routes", required=True,
                        help="comma-separated provider/model routes to probe")
    parser.add_argument("--out", help="write the JSON report here")
    parser.add_argument("--timeout", type=int, default=PROBE_TIMEOUT_SECONDS)
    args = parser.parse_args(argv)

    routes = [route.strip() for route in args.routes.split(",") if route.strip()]
    if not routes:
        print("no routes given", file=sys.stderr)
        return 2

    try:
        report = summarize(probe_all(routes, args.timeout))
    except (RuntimeError, ValueError) as error:
        print(f"probe failed: {error}", file=sys.stderr)
        return 2

    for result in report["results"]:
        verdict = "usable" if result["usable"] else "UNUSABLE"
        detail = "" if result["usable"] else f"  <- {result['errorMessage']}"
        print(f"  {verdict:9} {result['route']:44} {result['durationSeconds']}s{detail}")

    print(f"\nusable: {len(report['usable'])}/{report['probed']}")
    if args.out:
        try:
            with open(args.out, "w", encoding="utf-8") as handle:
                json.dump(report, handle, indent=2, sort_keys=True)
                handle.write("\n")
        except OSError as error:
            print(f"could not write {args.out}: {error}", file=sys.stderr)
            return 1
        print(f"report: {args.out}")
    return 0 if report["usable"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
