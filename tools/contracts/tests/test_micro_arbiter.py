"""Behavioural tests for the direct-to-C3 and bounded-shadow-sampling rules.

Run from the repository root:

    PYTHONPYCACHEPREFIX=/tmp/pyc python3 -m unittest discover -s tools/contracts/tests -t . -v

The cache prefix is required for any run that exercises mutated code; see instrument
defect ID-1 in `plans/260921-0805-issue15-contract-reconciliation/instrument-defects.md`.
"""

from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from tools.contracts.micro_arbiter import (  # noqa: E402
    PATHS,
    SHADOW_SAMPLE_EVERY_N,
    SHADOW_SAMPLE_MAX_PER_RUN,
    STRUCTURAL_C3_REASONS,
    VERDICT_NOT_NEEDED,
    MicroArbiterError,
    decide_verification_path,
    legacy_call_always,
    shadow_sample,
    structural_c3_reasons,
)


def job(**overrides):
    base = {"task": "implement", "importance": "normal", "effect": "scoped-write"}
    base.update(overrides)
    return base


def attempt(**overrides):
    base = {"riskFloorDelta": 0}
    base.update(overrides)
    return base


class StructuralEscalationGoesStraightToC3(unittest.TestCase):
    def _assert_direct(self, job_overrides, expected_reason, attempt_overrides=None):
        decision = decide_verification_path(
            job(**job_overrides), attempt(**(attempt_overrides or {})), calibration_valid=True
        )
        self.assertEqual(decision["path"], "direct-c3")
        self.assertFalse(decision["microArbiterCalled"],
                         "a gatekeeper that cannot change the decision must not be called")
        self.assertIn(expected_reason, decision["reasons"])

    def test_a_verdict_artifact_goes_direct(self):
        self._assert_direct({"task": "review"}, "verdict-artifact")

    def test_a_security_job_goes_direct(self):
        self._assert_direct({"task": "security"}, "security-sensitive")

    def test_an_architecture_decision_goes_direct(self):
        self._assert_direct({"task": "architecture"}, "architecture-or-public-contract")

    def test_a_high_importance_implementation_goes_direct(self):
        self._assert_direct({"importance": "high"}, "high-importance-implementation")

    def test_a_non_zero_risk_floor_delta_goes_direct(self):
        self._assert_direct({}, "non-zero-risk-floor-delta", {"riskFloorDelta": 1})

    def test_an_approval_setting_job_goes_direct(self):
        self._assert_direct({"approval": True}, "approval-dispatch-or-shared-state")

    def test_a_parallel_write_goes_direct(self):
        self._assert_direct({"parallel": True}, "parallel-or-untrusted-write")

    def test_a_destructive_effect_goes_direct(self):
        self._assert_direct({"effect": "destructive"}, "external-destructive-or-credentialed")

    def test_an_unverified_injection_fixture_goes_direct(self):
        decision = decide_verification_path(
            job(), attempt(), calibration_valid=True, injection_fixture_passed=False
        )
        self.assertEqual(decision["path"], "direct-c3")
        self.assertIn("injection-fixture-unverified", decision["reasons"])

    def test_not_needed_is_distinguishable_from_failed(self):
        decision = decide_verification_path(job(task="review"), attempt(), calibration_valid=True)
        self.assertEqual(decision["microArbiterVerdict"], VERDICT_NOT_NEEDED)
        self.assertTrue(decision["reasons"], "a skip must carry its structural reason")

    def test_an_open_job_reports_no_structural_reason(self):
        self.assertEqual(structural_c3_reasons(job(), attempt()), [])


class UncalibratedInstallsSampleOnABound(unittest.TestCase):
    def test_an_uncalibrated_open_job_takes_the_shadow_path(self):
        decision = decide_verification_path(job(), attempt(), calibration_valid=False)
        self.assertEqual(decision["path"], "c3-with-bounded-shadow")
        self.assertFalse(decision["microArbiterCalled"])
        self.assertEqual(decision["reasons"], ["calibration-invalid"])

    def test_a_calibrated_open_job_may_accept_without_c3(self):
        decision = decide_verification_path(job(), attempt(), calibration_valid=True)
        self.assertEqual(decision["path"], "micro-arbiter-may-accept")
        self.assertTrue(decision["microArbiterCalled"])

    def test_sampling_follows_the_declared_cadence(self):
        self.assertTrue(shadow_sample(1, 0))
        self.assertTrue(shadow_sample(1 + SHADOW_SAMPLE_EVERY_N, 1))
        self.assertFalse(shadow_sample(2, 1), "the sample is explicit, not every attempt")

    def test_sampling_is_ceilinged_per_run(self):
        taken = 0
        sampled = []
        for index in range(1, 200):
            if shadow_sample(index, taken):
                sampled.append(index)
                taken += 1
        self.assertEqual(len(sampled), SHADOW_SAMPLE_MAX_PER_RUN,
                         "the shadow sample must stay bounded per run")
        self.assertFalse(shadow_sample(1 + (SHADOW_SAMPLE_MAX_PER_RUN * SHADOW_SAMPLE_EVERY_N),
                                      SHADOW_SAMPLE_MAX_PER_RUN),
                         "sampling stops at the ceiling rather than widening")

    def test_the_bounds_are_pinned(self):
        self.assertEqual(SHADOW_SAMPLE_EVERY_N, 10)
        self.assertEqual(SHADOW_SAMPLE_MAX_PER_RUN, 5)

    def test_a_malformed_attempt_index_is_refused(self):
        with self.assertRaises(MicroArbiterError):
            shadow_sample(0, 0)


class TheNegativeFixtureAlwaysCallingDisagrees(unittest.TestCase):
    def test_the_regression_this_fixture_exists_for(self):
        """A gatekeeper called before every mandatory C3 call is the tax this removes."""
        args = (job(task="review"), attempt())
        legacy = legacy_call_always(*args, calibration_valid=True)
        owned = decide_verification_path(*args, calibration_valid=True)
        self.assertTrue(legacy["microArbiterCalled"], "baseline: always-call must be able to fail this")
        self.assertFalse(owned["microArbiterCalled"], "the owned rule goes straight to C3")
        self.assertNotEqual(legacy["microArbiterCalled"], owned["microArbiterCalled"],
                            "the two rules must disagree, or the fixture cannot fail")

    def test_the_legacy_rule_also_disagrees_on_the_uncalibrated_path(self):
        args = (job(), attempt())
        legacy = legacy_call_always(*args, calibration_valid=False)
        owned = decide_verification_path(*args, calibration_valid=False)
        self.assertTrue(legacy["microArbiterCalled"])
        self.assertFalse(owned["microArbiterCalled"])


class TheVocabulariesAreClosed(unittest.TestCase):
    def test_the_paths_are_enumerated(self):
        self.assertEqual(PATHS, ("direct-c3", "c3-with-bounded-shadow", "micro-arbiter-may-accept"))

    def test_the_structural_reasons_are_enumerated(self):
        self.assertEqual(len(STRUCTURAL_C3_REASONS), 10)
        self.assertEqual(len(set(STRUCTURAL_C3_REASONS)), 10, "the vocabulary must not repeat")

    def test_every_recorded_reason_comes_from_the_closed_set(self):
        cases = [
            (job(task="review"), attempt()),
            (job(task="security"), attempt()),
            (job(parallel=True), attempt()),
            (job(), attempt(riskFloorDelta=2)),
        ]
        for job_case, attempt_case in cases:
            for reason in structural_c3_reasons(job_case, attempt_case):
                self.assertIn(reason, STRUCTURAL_C3_REASONS)


class NoProviderOrModelNameIsNormative(unittest.TestCase):
    def test_module_source_names_no_current_model(self):
        import tools.contracts.micro_arbiter as module

        source_path = module.__file__
        assert source_path is not None
        with open(source_path, encoding="utf-8") as handle:
            source = handle.read().lower()
        for brand in ("gpt", "deepseek", "glm", "luna", "astra", "kimi", "claude", "gemini", "qwen"):
            self.assertNotIn(brand, source, "a current model brand leaked into verification policy")


if __name__ == "__main__":
    unittest.main()
