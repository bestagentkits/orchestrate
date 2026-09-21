"""Behavioural tests for the expected-verified-cost objective.

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

from tools.contracts.expected_cost import (  # noqa: E402
    CONSERVATIVE_C3_REQUIRED_PROBABILITY,
    CONSERVATIVE_CONTENT_FAILURE_PROBABILITY,
    CONSERVATIVE_INFRASTRUCTURE_FAILURE_PROBABILITY,
    COST_TERMS,
    PROBABILITY_DEFAULTS,
    ExpectedCostError,
    compare_expected_cost,
    conservative_substitutions,
    expected_verified_cost,
    legacy_expected_cost_treating_unknown_as_zero,
    probability_term,
)


def full_route(**overrides):
    route = {
        "routingOverhead": 1.0,
        "workerCost": 2.0,
        "verificationCost": 3.0,
        "expectedRecoveryCost": 4.0,
        "expectedEscalationCost": 5.0,
        "expectedArbiterCost": 6.0,
        "infrastructureFailureProbability": 0.5,
        "contentFailureProbability": 0.1,
        "c3RequiredProbability": 0.2,
    }
    route.update(overrides)
    return route


def cost(route):
    """The objective where a number is expected, failing the test if it is unknown."""
    value = expected_verified_cost(route)
    assert value is not None, "expected a measurable objective, got unknown"
    return value


class EveryTermContributes(unittest.TestCase):
    def test_the_objective_is_the_sum_of_all_six_terms(self):
        # 1 + 2 + 3 + 0.5*4 + 0.1*5 + 0.2*6 = 9.7
        self.assertAlmostEqual(cost(full_route()), 9.7, places=9)

    def test_recovery_cost_enters_only_through_the_infrastructure_probability(self):
        self.assertAlmostEqual(
            cost(full_route(expectedRecoveryCost=8.0)) - cost(full_route()),
            0.5 * 4.0,
            places=9,
        )

    def test_arbiter_cost_enters_only_through_the_c3_probability(self):
        self.assertAlmostEqual(
            cost(full_route(expectedArbiterCost=16.0)) - cost(full_route()),
            0.2 * 10.0,
            places=9,
        )

    def test_escalation_cost_enters_only_through_the_content_probability(self):
        self.assertAlmostEqual(
            cost(full_route(expectedEscalationCost=25.0)) - cost(full_route()),
            0.1 * 20.0,
            places=9,
        )

    def test_an_unavailable_probability_uses_a_conservative_default_not_zero(self):
        unknown_probabilities = full_route(
            infrastructureFailureProbability=None,
            contentFailureProbability=None,
            c3RequiredProbability=None,
        )
        zero_probabilities = full_route(
            infrastructureFailureProbability=0,
            contentFailureProbability=0,
            c3RequiredProbability=0,
        )
        self.assertGreater(cost(unknown_probabilities), 0.0)
        self.assertGreater(
            cost(unknown_probabilities),
            cost(zero_probabilities),
            "an unknown probability must cost more than an assumed-impossible one",
        )

    def test_c3_is_assumed_required_until_evidence_says_otherwise(self):
        self.assertEqual(CONSERVATIVE_C3_REQUIRED_PROBABILITY, 1.0)
        self.assertGreaterEqual(cost(full_route(c3RequiredProbability=None)), 6.0)


class UnknownIsNeverZero(unittest.TestCase):
    def test_a_missing_cost_term_makes_the_objective_unknown(self):
        for term in COST_TERMS:
            self.assertIsNone(
                expected_verified_cost(full_route(**{term: None})),
                f"{term} missing must not score a number",
            )

    def test_a_measured_zero_is_still_a_number(self):
        self.assertIsNotNone(expected_verified_cost(full_route(routingOverhead=0)))

    def test_an_unknown_objective_never_wins_or_loses_a_comparison(self):
        partial = full_route(workerCost=None)
        self.assertIsNone(compare_expected_cost(partial, full_route()))
        self.assertIsNone(compare_expected_cost(full_route(), partial))

    def test_the_negative_fixture_treats_unknown_as_free(self):
        """The regression this fixture exists for, demonstrated rather than asserted."""
        partial = full_route(workerCost=None, verificationCost=None)
        legacy = legacy_expected_cost_treating_unknown_as_zero(partial)
        self.assertIsInstance(legacy, (int, float),
                              "baseline: the legacy rule must be able to call unknown free")
        self.assertIsNone(expected_verified_cost(partial), "the owned rule keeps it unknown")
        self.assertNotEqual(legacy, expected_verified_cost(partial),
                            "the two rules must disagree, or the fixture cannot fail")

    def test_a_route_that_looks_cheapest_only_because_it_is_unmeasured_loses(self):
        measured = full_route(workerCost=2.0, verificationCost=3.0)
        unmeasured = full_route(workerCost=None, verificationCost=None)
        self.assertLess(
            legacy_expected_cost_treating_unknown_as_zero(unmeasured),
            legacy_expected_cost_treating_unknown_as_zero(measured),
            "baseline: the unmeasured route must look cheaper",
        )
        self.assertIsNone(compare_expected_cost(unmeasured, measured),
                          "the owned rule refuses to rank it at all")


class SubstitutionsAreRecorded(unittest.TestCase):
    def test_a_substituted_probability_is_reported(self):
        route = full_route(infrastructureFailureProbability=None)
        self.assertEqual(conservative_substitutions(route), ["infrastructureFailureProbability"])

    def test_a_measured_probability_is_not_reported(self):
        self.assertEqual(conservative_substitutions(full_route()), [])

    def test_the_flag_distinguishes_a_default_from_a_measurement(self):
        _, substituted = probability_term({}, "c3RequiredProbability")
        self.assertTrue(substituted)
        _, measured = probability_term({"c3RequiredProbability": 0.0}, "c3RequiredProbability")
        self.assertFalse(measured)


class MalformedInputIsRefused(unittest.TestCase):
    def test_a_negative_cost_is_refused(self):
        with self.assertRaises(ExpectedCostError):
            expected_verified_cost(full_route(workerCost=-1.0))

    def test_a_non_numeric_cost_is_refused(self):
        with self.assertRaises(ExpectedCostError):
            expected_verified_cost(full_route(workerCost="2.0"))

    def test_a_probability_above_one_is_refused(self):
        with self.assertRaises(ExpectedCostError):
            expected_verified_cost(full_route(c3RequiredProbability=1.5))

    def test_a_negative_probability_is_refused(self):
        with self.assertRaises(ExpectedCostError):
            expected_verified_cost(full_route(contentFailureProbability=-0.1))

    def test_a_boolean_is_refused(self):
        with self.assertRaises(ExpectedCostError):
            expected_verified_cost(full_route(workerCost=True))


class TheVocabularyAndConstantsAreClosed(unittest.TestCase):
    def test_the_cost_terms_are_exactly_the_six(self):
        self.assertEqual(
            COST_TERMS,
            ("routingOverhead", "workerCost", "verificationCost",
             "expectedRecoveryCost", "expectedEscalationCost", "expectedArbiterCost"),
        )

    def test_the_probability_defaults_are_pinned(self):
        self.assertEqual(PROBABILITY_DEFAULTS, {
            "infrastructureFailureProbability": CONSERVATIVE_INFRASTRUCTURE_FAILURE_PROBABILITY,
            "contentFailureProbability": CONSERVATIVE_CONTENT_FAILURE_PROBABILITY,
            "c3RequiredProbability": CONSERVATIVE_C3_REQUIRED_PROBABILITY,
        })
        self.assertEqual(CONSERVATIVE_INFRASTRUCTURE_FAILURE_PROBABILITY, 0.20)
        self.assertEqual(CONSERVATIVE_CONTENT_FAILURE_PROBABILITY, 0.20)
        self.assertEqual(CONSERVATIVE_C3_REQUIRED_PROBABILITY, 1.00)


class NoProviderOrModelNameIsNormative(unittest.TestCase):
    def test_module_source_names_no_current_model(self):
        import tools.contracts.expected_cost as module

        source = open(module.__file__, encoding="utf-8").read().lower()
        for brand in ("gpt", "deepseek", "glm", "luna", "astra", "kimi", "claude", "gemini", "qwen"):
            self.assertNotIn(brand, source, "a current model brand leaked into the objective")


if __name__ == "__main__":
    unittest.main()
