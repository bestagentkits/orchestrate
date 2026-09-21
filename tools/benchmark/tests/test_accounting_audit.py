"""Behavioural tests for the independent accounting audit and the settle window.

Run from the repository root:

    PYTHONPYCACHEPREFIX=/tmp/pyc python3 -m unittest discover -s tools -t . -v

Each test builds a synthetic run directory from raw session files, so the audit is exercised
against records whose correct answer is known by construction. The load-bearing pair is
`test_a_consistent_run_verifies` and the deliberately inconsistent runs beside it: an audit
that only ever passes is not an audit.
"""

from __future__ import annotations

import json
import os
import pathlib
import sys
import tempfile
import threading
import time
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from tools.benchmark import run_benchmark, verify_results  # noqa: E402


def write_session(path: str, cost: float, tokens: dict | None = None,
                  provider: str = "provider-a", model: str = "model-a") -> None:
    """One session file, in the shape the runtime writes."""
    pathlib.Path(path).parent.mkdir(parents=True, exist_ok=True)
    lines = [
        json.dumps({"type": "model_change", "provider": provider, "modelId": model}),
        json.dumps({"message": {"usage": {"cost": {"total": cost}, **(tokens or {})}}}),
    ]
    pathlib.Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_jsonl(path: str, rows: list[dict]) -> None:
    pathlib.Path(path).parent.mkdir(parents=True, exist_ok=True)
    pathlib.Path(path).write_text(
        "\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8"
    )


def build_run(root: str, results: list[dict], sessions: dict, trials: list[dict] | None = None) -> str:
    """A run directory whose session files are the ground truth."""
    out = pathlib.Path(root)
    (out / "sessions").mkdir(parents=True, exist_ok=True)
    for name, spec in sessions.items():
        write_session(str(out / "sessions" / name), spec["cost"], spec.get("tokens"),
                      spec.get("provider", "provider-a"), spec.get("model", "model-a"))
    write_jsonl(str(out / "results.jsonl"), results)
    if trials is not None:
        write_jsonl(str(out / "trials.jsonl"), trials)
    return str(out)


def consistent_results(session_path: str, cost: float = 1.0, tokens: dict | None = None) -> list[dict]:
    return [{
        "variant": "orchestrate",
        "taskId": "task-01",
        "trial": 1,
        "status": "ok",
        "success": True,
        "costUsd": cost,
        "tokens": tokens or {"input": 10},
        "sessionPaths": [session_path],
        "escapedSessionPaths": [],
        "dispatches": 0,
        "sessionFiles": 1,
    }]


class AConsistentRunVerifies(unittest.TestCase):
    def test_a_consistent_run_verifies(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = build_run(
                tmp,
                consistent_results("/PLACEHOLDER", 1.0),
                {"s1.jsonl": {"cost": 1.0, "tokens": {"input": 10}}},
            )
            # Patch the recorded path to the real one now that the directory exists.
            results = consistent_results(os.path.join(out, "sessions", "s1.jsonl"), 1.0)
            write_jsonl(os.path.join(out, "results.jsonl"), results)

            result = verify_results.audit_run(out)
            self.assertEqual(result["verdict"], "verified", result["problems"])
            self.assertEqual(result["problems"], [])
            self.assertEqual(result["mismatches"], 0)
            self.assertAlmostEqual(result["unattributedCost"], 0.0, places=9)
            self.assertAlmostEqual(result["recordedTotal"], 1.0, places=9)
            self.assertAlmostEqual(result["recomputedTotal"], 1.0, places=9)


class AInconsistentRunIsRejected(unittest.TestCase):
    def test_a_cost_mismatch_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = build_run(tmp, [], {"s1.jsonl": {"cost": 2.0, "tokens": {"input": 10}}})
            write_jsonl(os.path.join(out, "results.jsonl"),
                        consistent_results(os.path.join(out, "sessions", "s1.jsonl"), 1.0))
            result = verify_results.audit_run(out)
            self.assertEqual(result["verdict"], "rejected")
            self.assertTrue(any(p.startswith("cost:") for p in result["problems"]), result["problems"])

    def test_a_token_mismatch_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = build_run(tmp, [], {"s1.jsonl": {"cost": 1.0, "tokens": {"input": 99}}})
            write_jsonl(os.path.join(out, "results.jsonl"),
                        consistent_results(os.path.join(out, "sessions", "s1.jsonl"), 1.0))
            result = verify_results.audit_run(out)
            self.assertEqual(result["verdict"], "rejected")
            self.assertTrue(any(p.startswith("tokens:") for p in result["problems"]), result["problems"])

    def test_cost_that_belongs_to_no_trial_is_rejected(self):
        """The measured escape: a session file no trial claims understates that trial."""
        with tempfile.TemporaryDirectory() as tmp:
            out = build_run(
                tmp, [],
                {"s1.jsonl": {"cost": 1.0, "tokens": {"input": 10}},
                 "s2.jsonl": {"cost": 0.85, "tokens": {"input": 5}}},
            )
            write_jsonl(os.path.join(out, "results.jsonl"),
                        consistent_results(os.path.join(out, "sessions", "s1.jsonl"), 1.0))
            result = verify_results.audit_run(out)
            self.assertEqual(result["verdict"], "rejected")
            self.assertAlmostEqual(result["unattributedCost"], 0.85, places=6)
            self.assertEqual(result["unattributedFiles"], 1)
            self.assertTrue(any(p.startswith("unattributed-cost=") for p in result["problems"]))

    def test_rounding_leftover_alone_is_not_a_rejection(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = build_run(tmp, [], {"s1.jsonl": {"cost": 1.0, "tokens": {"input": 10}}})
            write_jsonl(os.path.join(out, "results.jsonl"),
                        consistent_results(os.path.join(out, "sessions", "s1.jsonl"), 1.0))
            self.assertEqual(verify_results.audit_run(out)["verdict"], "verified")

    def test_a_component_split_that_does_not_sum_to_its_total_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            session = os.path.join(tmp, "sessions", "s1.jsonl")
            out = build_run(tmp, [], {"s1.jsonl": {"cost": 1.0, "tokens": {"input": 10}}})
            write_jsonl(os.path.join(out, "results.jsonl"), consistent_results(session, 1.0))
            write_jsonl(os.path.join(out, "trials.jsonl"), [{
                "taskId": "task-01", "variant": "orchestrate", "trial": 1,
                "coordinatorCostUsd": 1.0, "workerCostUsd": 1.0,
                "classifierCostUsd": 0.0, "arbiterCostUsd": 0.0,
                "totalCostUsd": 1.0,
            }])
            result = verify_results.audit_run(out)
            self.assertEqual(result["verdict"], "rejected")
            self.assertTrue(any(p.startswith("components:") for p in result["problems"]), result["problems"])

    def test_components_that_disagree_with_the_sessions_are_rejected(self):
        """The split can be internally consistent and still not match the raw records."""
        with tempfile.TemporaryDirectory() as tmp:
            session = os.path.join(tmp, "sessions", "s1.jsonl")
            out = build_run(tmp, [], {"s1.jsonl": {"cost": 1.0, "tokens": {"input": 10}}})
            write_jsonl(os.path.join(out, "results.jsonl"), consistent_results(session, 1.0))
            write_jsonl(os.path.join(out, "trials.jsonl"), [{
                "taskId": "task-01", "variant": "orchestrate", "trial": 1,
                "coordinatorCostUsd": 1.5, "workerCostUsd": 0.5,
                "classifierCostUsd": 0.0, "arbiterCostUsd": 0.0,
                "totalCostUsd": 2.0,
            }])
            result = verify_results.audit_run(out)
            self.assertEqual(result["verdict"], "rejected")
            # The split sums to its own total, so only the session comparison catches it.
            self.assertTrue(
                any(p.startswith("components-vs-sessions:") for p in result["problems"]),
                result["problems"],
            )


class NestedDispatchIsAudited(unittest.TestCase):
    def test_fewer_session_files_than_dispatches_is_warned_about(self):
        with tempfile.TemporaryDirectory() as tmp:
            session = os.path.join(tmp, "sessions", "s1.jsonl")
            out = build_run(tmp, [], {"s1.jsonl": {"cost": 1.0, "tokens": {"input": 10}}})
            results = consistent_results(session, 1.0)
            results[0]["dispatches"] = 2
            write_jsonl(os.path.join(out, "results.jsonl"), results)
            result = verify_results.audit_run(out)
            self.assertTrue(any("dispatch" in w for w in result["warnings"]), result["warnings"])

    def test_a_settled_trial_with_its_dispatch_files_is_not_warned_about(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = build_run(
                tmp, [],
                {"s1.jsonl": {"cost": 1.0, "tokens": {"input": 10}},
                 "s2.jsonl": {"cost": 0.5, "tokens": {"input": 4}}},
            )
            results = consistent_results(os.path.join(out, "sessions", "s1.jsonl"), 1.5,
                                         tokens={"input": 14})
            results[0]["dispatches"] = 1
            results[0]["sessionPaths"] = [os.path.join(out, "sessions", "s1.jsonl"),
                                          os.path.join(out, "sessions", "s2.jsonl")]
            write_jsonl(os.path.join(out, "results.jsonl"), results)
            result = verify_results.audit_run(out)
            self.assertEqual(result["verdict"], "verified", result["problems"])
            self.assertFalse(any("dispatch" in w for w in result["warnings"]), result["warnings"])

    def test_skipped_trials_are_excluded_from_the_audit(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = build_run(tmp, [], {"s1.jsonl": {"cost": 1.0, "tokens": {"input": 10}}})
            results = consistent_results(os.path.join(out, "sessions", "s1.jsonl"), 1.0)
            results.append({"variant": "orchestrate", "taskId": "task-02", "trial": 1,
                            "status": "skipped", "reason": "budget cap reached"})
            write_jsonl(os.path.join(out, "results.jsonl"), results)
            result = verify_results.audit_run(out)
            self.assertEqual(result["checked"], 1)
            self.assertEqual(result["skipped"], 1)
            self.assertEqual(result["verdict"], "verified", result["problems"])


class TheSettleWindowClosesTheLateWriteRace(unittest.TestCase):
    def test_an_immediate_snapshot_is_time_dependent(self):
        """The baseline the settle window exists for: a later write is simply not seen."""
        with tempfile.TemporaryDirectory() as tmp:
            sessions = os.path.join(tmp, "sessions")
            os.makedirs(sessions)
            write_session(os.path.join(sessions, "s1.jsonl"), 1.0)
            self.assertEqual(len(run_benchmark.session_files(sessions)), 1)
            write_session(os.path.join(sessions, "s2.jsonl"), 2.0)
            self.assertEqual(len(run_benchmark.session_files(sessions)), 2)

    def test_settle_waits_for_a_writer_that_finishes_late(self):
        """The window must exceed the linger, which is what the default 3x1.0s provides."""
        with tempfile.TemporaryDirectory() as tmp:
            sessions = os.path.join(tmp, "sessions")
            os.makedirs(sessions)
            write_session(os.path.join(sessions, "s1.jsonl"), 1.0)

            def late_writer():
                time.sleep(0.05)
                write_session(os.path.join(sessions, "s2.jsonl"), 2.0)

            thread = threading.Thread(target=late_writer)
            thread.start()
            try:
                result = run_benchmark.settle_session_dir(
                    sessions, quiet_checks=5, poll_seconds=0.05, timeout_seconds=5.0
                )
            finally:
                thread.join()
            self.assertTrue(result["settled"])
            self.assertEqual(result["files"], 2, "the late write must be inside the snapshot")

    def test_a_writer_that_outlasts_the_quiet_window_is_missed(self):
        """The residual limitation, stated rather than hidden.

        The window bounds the race; it does not abolish it. A dispatch that lingers longer
        than the quiet window is still outside the snapshot, which is exactly why the audit's
        unattributed-cost check exists as the backstop rather than relying on the window alone.
        """
        with tempfile.TemporaryDirectory() as tmp:
            sessions = os.path.join(tmp, "sessions")
            os.makedirs(sessions)
            write_session(os.path.join(sessions, "s1.jsonl"), 1.0)
            result = run_benchmark.settle_session_dir(
                sessions, quiet_checks=2, poll_seconds=0.01, timeout_seconds=5.0
            )
            write_session(os.path.join(sessions, "s2.jsonl"), 2.0)
            self.assertTrue(result["settled"])
            self.assertEqual(result["files"], 1, "a write after the window is outside it by design")
            self.assertEqual(len(run_benchmark.session_files(sessions)), 2)

    def test_a_trial_that_never_settles_says_so(self):
        """A directory that keeps changing must report settled=False rather than a snapshot."""
        with tempfile.TemporaryDirectory() as tmp:
            sessions = os.path.join(tmp, "sessions")
            os.makedirs(sessions)
            write_session(os.path.join(sessions, "s1.jsonl"), 1.0)
            stop = threading.Event()

            def restless():
                index = 0
                while not stop.is_set():
                    index += 1
                    write_session(os.path.join(sessions, f"w{index}.jsonl"), 0.1)
                    time.sleep(0.005)

            thread = threading.Thread(target=restless)
            thread.start()
            try:
                result = run_benchmark.settle_session_dir(
                    sessions, quiet_checks=3, poll_seconds=0.01, timeout_seconds=0.3
                )
            finally:
                stop.set()
                thread.join()
            self.assertFalse(result["settled"], "a restless directory must not be reported as settled")

    def test_a_quiet_directory_settles(self):
        with tempfile.TemporaryDirectory() as tmp:
            sessions = os.path.join(tmp, "sessions")
            os.makedirs(sessions)
            write_session(os.path.join(sessions, "s1.jsonl"), 1.0)
            result = run_benchmark.settle_session_dir(
                sessions, quiet_checks=2, poll_seconds=0.01, timeout_seconds=5.0
            )
            self.assertTrue(result["settled"])
            self.assertEqual(result["files"], 1)

    def test_a_settled_trial_records_its_settlement(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = build_run(tmp, [], {"s1.jsonl": {"cost": 1.0, "tokens": {"input": 10}}})
            results = consistent_results(os.path.join(out, "sessions", "s1.jsonl"), 1.0)
            results[0]["settled"] = True
            results[0]["settleWaitedSeconds"] = 3.0
            write_jsonl(os.path.join(out, "results.jsonl"), results)
            self.assertEqual(verify_results.audit_run(out)["verdict"], "verified")


class TheAuditNeedsSomethingToAudit(unittest.TestCase):
    def test_an_empty_run_directory_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(SystemExit):
                verify_results.audit_run(tmp)


if __name__ == "__main__":
    unittest.main()
