"""Behavioural tests for the decision-plane value-of-information gate.

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

from tools.contracts.voi_gate import (  # noqa: E402
    CALL_REASONS,
    SEMANTIC_MARGIN_THRESHOLD,
    SKIP_REASONS,
    VoIError,
    candidate_margin,
    decide_semantic_routing,
    floor_could_still_rise,
    legacy_always_call,
    probe_is_reusable,
)


def routes(*costs):
    return [{"name": f"r{i}", "expectedVerifiedCostUsd": c} for i, c in enumerate(costs)]


#: A job with nothing left for a probabilistic signal to raise.
SATURATED = {"required_tier": "C3", "risk_tier": "R3", "independence_required": True}


class DecisiveWinnerSkipsTheCall(unittest.TestCase):
    def test_a_decisive_winner_with_no_raisable_floor_is_skipped(self):
        decision = decide_semantic_routing(routes(10.0, 20.0), **SATURATED)
        self.assertFalse(decision["semanticRouterCalled"])
        self.assertEqual(decision["semanticRouterSkippedReason"], "deterministic-winner-decisive")
        self.assertEqual(decision["semanticRouterSecondarySkippedReason"], "no-floor-could-change")

    def test_a_single_candidate_needs_no_second_opinion(self):
        decision = decide_semantic_routing(routes(10.0), **SATURATED)
        self.assertFalse(decision["semanticRouterCalled"])

    def test_a_skip_is_recorded_not_absent(self):
        decision = decide_semantic_routing(routes(10.0, 20.0), **SATURATED)
        self.assertIn("semanticRouterCalled", decision)
        self.assertIn("semanticRouterSkippedReason", decision)
        self.assertNotIn("semanticRouterReason", decision,
                         "a skip must not also claim a call reason")

    def test_the_margin_is_recorded_on_a_skip(self):
        decision = decide_semantic_routing(routes(10.0, 20.0), **SATURATED)
        self.assertAlmostEqual(decision["candidateMargin"], 1.0, places=9)


class TheCallHappensWhenItCanMatter(unittest.TestCase):
    def test_close_candidates_are_worth_a_call(self):
        decision = decide_semantic_routing(routes(10.0, 10.5), **SATURATED)
        self.assertTrue(decision["semanticRouterCalled"])
        self.assertEqual(decision["semanticRouterReason"], "close-candidates")

    def test_a_decisive_winner_still_calls_when_a_floor_could_rise(self):
        decision = decide_semantic_routing(
            routes(10.0, 20.0), required_tier="C2", risk_tier="R1", independence_required=False
        )
        self.assertTrue(decision["semanticRouterCalled"])
        self.assertEqual(decision["semanticRouterReason"], "floor-could-rise")

    def test_an_ambiguous_classification_is_worth_a_call(self):
        decision = decide_semantic_routing(routes(10.0, 20.0), classification_ambiguous=True, **SATURATED)
        self.assertTrue(decision["semanticRouterCalled"])
        self.assertEqual(decision["semanticRouterReason"], "ambiguous-classification")

    def test_unclear_requirements_are_worth_a_call(self):
        decision = decide_semantic_routing(routes(10.0, 20.0), requirements_clear=False, **SATURATED)
        self.assertTrue(decision["semanticRouterCalled"])
        self.assertEqual(decision["semanticRouterReason"], "unclear-requirements")

    def test_an_unknown_margin_is_not_treated_as_decisive(self):
        decision = decide_semantic_routing(routes(10.0, None), **SATURATED)
        self.assertTrue(decision["semanticRouterCalled"])
        self.assertEqual(decision["semanticRouterReason"], "close-candidates")


class FloorRaisability(unittest.TestCase):
    def test_a_saturated_job_has_nothing_left_to_raise(self):
        self.assertFalse(floor_could_still_rise("C3", "R3", True))

    def test_a_tier_below_the_maximum_could_rise(self):
        self.assertTrue(floor_could_still_rise("C2", "R3", True))

    def test_a_risk_tier_below_the_maximum_could_rise(self):
        self.assertTrue(floor_could_still_rise("C3", "R1", True))

    def test_missing_independence_could_be_imposed(self):
        self.assertTrue(floor_could_still_rise("C3", "R3", False))


class MarginArithmetic(unittest.TestCase):
    def test_the_margin_is_relative_to_the_best(self):
        margin = candidate_margin(routes(10.0, 12.0))
        assert margin is not None
        self.assertAlmostEqual(margin, 0.2, places=9)

    def test_a_single_candidate_is_decisive(self):
        self.assertEqual(candidate_margin(routes(10.0)), 1.0)

    def test_no_candidates_is_no_margin(self):
        self.assertIsNone(candidate_margin([]))

    def test_an_unknown_cost_is_no_margin(self):
        self.assertIsNone(candidate_margin(routes(10.0, None)))

    def test_the_threshold_is_pinned(self):
        self.assertEqual(SEMANTIC_MARGIN_THRESHOLD, 0.15)


class ProbeIsReusedWithinItsScope(unittest.TestCase):
    def setUp(self):
        self.probe = {"runId": "run-1", "candidateSetHash": "abc", "state": "verified"}

    def test_a_matching_probe_is_reused(self):
        self.assertTrue(probe_is_reusable(self.probe, "run-1", "abc"))

    def test_a_new_run_invalidates_the_probe(self):
        self.assertFalse(probe_is_reusable(self.probe, "run-2", "abc"))

    def test_a_changed_candidate_set_invalidates_the_probe(self):
        self.assertFalse(probe_is_reusable(self.probe, "run-1", "def"))

    def test_an_unverified_probe_is_not_reused(self):
        self.assertFalse(probe_is_reusable({**self.probe, "state": "stale"}, "run-1", "abc"))

    def test_a_missing_probe_is_not_reused(self):
        self.assertFalse(probe_is_reusable(None, "run-1", "abc"))


class TheNegativeFixtureAlwaysCallingDisagrees(unittest.TestCase):
    def test_the_regression_this_fixture_exists_for(self):
        """A plane consulted on every job is the cost this gate removes."""
        args = routes(10.0, 20.0)
        legacy = legacy_always_call(args, **SATURATED)
        owned = decide_semantic_routing(args, **SATURATED)
        self.assertTrue(legacy["semanticRouterCalled"], "baseline: always-call must be able to fail this")
        self.assertFalse(owned["semanticRouterCalled"], "the owned rule skips a decisive case")
        self.assertNotEqual(legacy["semanticRouterCalled"], owned["semanticRouterCalled"],
                            "the two rules must disagree, or the fixture cannot fail")


class TheVocabulariesAreClosed(unittest.TestCase):
    def test_call_reasons_are_enumerated(self):
        self.assertEqual(
            CALL_REASONS,
            ("close-candidates", "ambiguous-classification", "floor-could-rise", "unclear-requirements"),
        )

    def test_skip_reasons_are_enumerated(self):
        self.assertEqual(
            SKIP_REASONS,
            ("deterministic-winner-decisive", "no-floor-could-change"),
        )

    def test_every_recorded_reason_comes_from_a_closed_set(self):
        for decision in (
            decide_semantic_routing(routes(10.0, 10.5), **SATURATED),
            decide_semantic_routing(routes(10.0, 20.0), **SATURATED),
            decide_semantic_routing(routes(10.0, 20.0), required_tier="C1", risk_tier="R0",
                                    independence_required=False),
        ):
            if decision["semanticRouterCalled"]:
                self.assertIn(decision["semanticRouterReason"], CALL_REASONS)
            else:
                self.assertIn(decision["semanticRouterSkippedReason"], SKIP_REASONS)

    def test_a_malformed_cost_is_refused(self):
        with self.assertRaises(VoIError):
            candidate_margin([{"name": "a", "expectedVerifiedCostUsd": "10"}])


class NoProviderOrModelNameIsNormative(unittest.TestCase):
    def test_module_source_names_no_current_model(self):
        import tools.contracts.voi_gate as module

        source = open(module.__file__, encoding="utf-8").read().lower()
        for brand in ("gpt", "deepseek", "glm", "luna", "astra", "kimi", "claude", "gemini", "qwen"):
            self.assertNotIn(brand, source, "a current model brand leaked into routing policy")


if __name__ == "__main__":
    unittest.main()
