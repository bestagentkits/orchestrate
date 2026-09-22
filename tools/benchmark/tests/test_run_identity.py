"""A run directory belongs to exactly one arm set.

The guard exists because the mistake was made: the third frontier attempt wrote into the
second attempt's directory, so `results.jsonl` held eight arms drawn from two different arm
files while `manifest.json` described only one of them. These tests pin the refusal, and
equally pin the cases that must **not** refuse, because a guard that blocks a legitimate
resume is its own defect.
"""

from __future__ import annotations

import json
import os
import tempfile
import unittest

from tools.benchmark import run_benchmark


def write_manifest(directory: str, payload) -> None:
    with open(os.path.join(directory, "manifest.json"), "w", encoding="utf-8") as handle:
        if isinstance(payload, str):
            handle.write(payload)
        else:
            json.dump(payload, handle)


class CheckRunIdentity(unittest.TestCase):
    def test_an_empty_directory_is_accepted(self):
        with tempfile.TemporaryDirectory() as directory:
            run_benchmark.check_run_identity(directory, ["a", "b"])

    def test_the_same_arm_set_is_accepted(self):
        with tempfile.TemporaryDirectory() as directory:
            write_manifest(directory, {"variants": ["a", "b"]})
            run_benchmark.check_run_identity(directory, ["a", "b"])

    def test_a_different_arm_set_is_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            write_manifest(directory, {"variants": ["a", "b"]})
            with self.assertRaises(run_benchmark.RunIdentityError) as caught:
                run_benchmark.check_run_identity(directory, ["a", "c"])
            self.assertIn("different arm set", str(caught.exception))
            self.assertIn("a new --out directory", str(caught.exception))

    def test_an_added_arm_is_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            write_manifest(directory, {"variants": ["a", "b"]})
            with self.assertRaises(run_benchmark.RunIdentityError):
                run_benchmark.check_run_identity(directory, ["a", "b", "c"])

    def test_an_unreadable_manifest_does_not_refuse(self):
        with tempfile.TemporaryDirectory() as directory:
            write_manifest(directory, "{ this is not json")
            run_benchmark.check_run_identity(directory, ["a", "b"])

    def test_a_manifest_without_variants_does_not_refuse(self):
        with tempfile.TemporaryDirectory() as directory:
            write_manifest(directory, {"fixtureId": "taskflow"})
            run_benchmark.check_run_identity(directory, ["a", "b"])

    def test_the_refusal_names_both_arm_sets(self):
        with tempfile.TemporaryDirectory() as directory:
            write_manifest(directory, {"variants": ["W-spark", "W-terra"]})
            with self.assertRaises(run_benchmark.RunIdentityError) as caught:
                run_benchmark.check_run_identity(directory, ["W-terra", "W-glm"])
            message = str(caught.exception)
            self.assertIn("W-spark", message)
            self.assertIn("W-glm", message)


class ResolveModels(unittest.TestCase):
    """Resolution is by paid cost, because a declared model can do no work at all."""

    def test_the_declared_model_resolves_when_it_did_the_work(self):
        result = run_benchmark.resolve_models({"openai-codex/gpt-6-astra": 0.17},
                                              "openai-codex/gpt-6-astra")
        self.assertFalse(result["contaminated"])
        self.assertEqual(result["dominant"], "openai-codex/gpt-6-astra")
        self.assertEqual(result["foreign"], [])

    def test_a_substituted_model_is_contamination(self):
        result = run_benchmark.resolve_models(
            {"openai-codex/gpt-6-astra": 0.0, "opencode-go/deepseek-v4.1-flash": 0.013},
            "openai-codex/gpt-6-astra",
        )
        self.assertTrue(result["contaminated"])
        self.assertEqual(result["dominant"], "opencode-go/deepseek-v4.1-flash")
        self.assertEqual(result["foreign"], ["opencode-go/deepseek-v4.1-flash"])

    def test_a_zero_cost_declared_model_alone_is_unknown_not_resolved(self):
        result = run_benchmark.resolve_models({"openai-codex/gpt-5.3-codex-spark": 0.0},
                                              "openai-codex/gpt-5.3-codex-spark")
        self.assertTrue(result["unknown"])
        self.assertIsNone(result["dominant"])
        self.assertFalse(result["contaminated"])

    def test_no_models_at_all_is_unknown(self):
        result = run_benchmark.resolve_models({}, "openai-codex/gpt-6-astra")
        self.assertTrue(result["unknown"])
        self.assertEqual(result["resolved"], [])

    def test_a_dispatching_arm_with_its_coordinator_present_is_not_contaminated(self):
        """An orchestrator's other paid models are the treatment, not a defect.

        Applying the non-dispatching rule here is what flagged V1-V5 in the first ablation
        attempt while they were doing exactly what they were asked to do.
        """
        result = run_benchmark.resolve_models(
            {"openai-codex/gpt-6-astra": 0.4,
             "opencode-go/deepseek-v4.1-flash": 1.1,
             "deepseek/deepseek-v4-pro": 0.3},
            "openai-codex/gpt-6-astra",
            may_dispatch=True,
        )
        self.assertFalse(result["contaminated"])
        self.assertIsNone(result["reason"])
        self.assertEqual(len(result["resolved"]), 3)
        self.assertEqual(result["dominant"], "opencode-go/deepseek-v4.1-flash")

    def test_a_dispatching_arm_whose_coordinator_never_ran_is_contaminated(self):
        result = run_benchmark.resolve_models(
            {"opencode-go/deepseek-v4.1-flash": 1.1},
            "openai-codex/gpt-6-astra",
            may_dispatch=True,
        )
        self.assertTrue(result["contaminated"])
        self.assertIn("did no paid work", result["reason"])

    def test_the_reason_names_the_foreign_models_when_dispatch_is_forbidden(self):
        result = run_benchmark.resolve_models(
            {"openai-codex/gpt-6-astra": 0.1, "opencode-go/glm-5.3": 0.2},
            "openai-codex/gpt-6-astra",
            may_dispatch=False,
        )
        self.assertTrue(result["contaminated"])
        self.assertIn("opencode-go/glm-5.3", result["reason"])


class ArmMayDispatch(unittest.TestCase):
    """The rule that distinguishes an orchestrator from a direct worker."""

    def test_the_directive_without_a_note_may_dispatch(self):
        self.assertTrue(run_benchmark.arm_may_dispatch(
            {"directive": "orchestrate", "plane": "on"}))

    def test_the_directive_with_the_no_dispatch_note_may_not(self):
        self.assertFalse(run_benchmark.arm_may_dispatch(
            {"directive": "orchestrate", "noDispatchNote": "do not dispatch"}))

    def test_no_directive_may_not_dispatch(self):
        self.assertFalse(run_benchmark.arm_may_dispatch(
            {"directive": "none", "plane": "off"}))

    def test_an_empty_spec_may_not_dispatch(self):
        self.assertFalse(run_benchmark.arm_may_dispatch({}))

    def test_the_plane_alone_does_not_grant_dispatch(self):
        """V2 is plane-off and still orchestrated; VN is plane-off and did not."""
        self.assertFalse(run_benchmark.arm_may_dispatch({"plane": "on"}))


class ProviderError(unittest.TestCase):
    """A refused model must not be readable as a failed task."""

    def _session(self, directory: str, records: list) -> str:
        path = os.path.join(directory, "session.jsonl")
        with open(path, "w", encoding="utf-8") as handle:
            for record in records:
                handle.write(json.dumps(record) + "\n")
        return path

    def test_a_provider_rejection_is_returned(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self._session(directory, [
                {"type": "model_change", "provider": "openai-codex",
                 "modelId": "gpt-5.3-codex-spark"},
                {"message": {"role": "assistant", "stopReason": "error",
                             "errorMessage": "Codex error: not supported"}},
            ])
            self.assertEqual(run_benchmark.provider_error([path]),
                             "Codex error: not supported")

    def test_a_normal_turn_reports_nothing(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self._session(directory, [
                {"message": {"role": "assistant", "stopReason": "stop",
                             "usage": {"output": 12}}},
            ])
            self.assertIsNone(run_benchmark.provider_error([path]))

    def test_a_missing_file_reports_nothing(self):
        self.assertIsNone(run_benchmark.provider_error(["/nonexistent/session.jsonl"]))

    def test_unparseable_lines_are_skipped(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "session.jsonl")
            with open(path, "w", encoding="utf-8") as handle:
                handle.write("not json\n")
                handle.write(json.dumps({"message": {"role": "assistant",
                                                     "stopReason": "error",
                                                     "errorMessage": "refused"}}) + "\n")
            self.assertEqual(run_benchmark.provider_error([path]), "refused")


class ClassifyProviderError(unittest.TestCase):
    """Only an error with no paid work behind it is an availability verdict.

    Both cases are real: `gpt-5.3-codex-spark` was refused at $0.0000 in 3.8 s, and five
    ablation trials hit a WebSocket or overload error mid-run, kept working, and succeeded.
    """

    def test_no_error_is_neither(self):
        self.assertEqual(run_benchmark.classify_provider_error(None, 0.0), "none")
        self.assertEqual(run_benchmark.classify_provider_error("", 1.0), "none")

    def test_an_error_with_no_paid_work_is_invalid(self):
        self.assertEqual(
            run_benchmark.classify_provider_error("Codex error: not supported", 0.0),
            "invalid",
        )

    def test_an_error_with_paid_work_behind_it_is_recovered(self):
        self.assertEqual(
            run_benchmark.classify_provider_error("WebSocket error", 1.7910),
            "recovered",
        )

    def test_a_cent_of_paid_work_is_enough_to_keep_the_trial(self):
        self.assertEqual(
            run_benchmark.classify_provider_error("servers are overloaded", 0.01),
            "recovered",
        )


if __name__ == "__main__":
    unittest.main()
