"""Behavioural tests for the cost-dimension rules.

Run from the repository root:

    python3 -m unittest discover -s tools/contracts/tests -t . -v

The negative fixture is paired with the legacy behaviour it guards against, so it is
shown to be capable of failing rather than merely observed to pass. A test that can
never fail proves nothing.
"""

from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from tools.contracts.cost_dimensions import (  # noqa: E402
    ACTUAL_MARGINAL,
    API_EQUIVALENT,
    COST_DIMENSIONS,
    QUOTA_BURN,
    CostError,
    assert_budget_declares_dimension,
    compare,
    cost_record,
    total_cash,
)


def legacy_total_cash(record: dict) -> float:
    """The behaviour this contract replaced: a missing cost coerced to free.

    Kept as the negative baseline. Any regression that treated an unknown as zero would
    agree with this function, and the fixture below would fail.
    """
    return float(record.get(ACTUAL_MARGINAL) or 0) + float(record.get(API_EQUIVALENT) or 0)


class DimensionsAreIndependent(unittest.TestCase):
    def test_all_three_are_recorded_separately(self):
        record = cost_record(**{ACTUAL_MARGINAL: 1.5, API_EQUIVALENT: 2.0, QUOTA_BURN: 7})
        self.assertEqual(record[ACTUAL_MARGINAL], 1.5)
        self.assertEqual(record[API_EQUIVALENT], 2.0)
        self.assertEqual(record[QUOTA_BURN], 7)

    def test_quota_is_never_summed_into_cash(self):
        record = cost_record(**{ACTUAL_MARGINAL: 1.0, API_EQUIVALENT: 1.0, QUOTA_BURN: 1000})
        self.assertEqual(total_cash(record), 2.0, "quota burn must not inflate a cash total")

    def test_an_unknown_dimension_is_refused(self):
        with self.assertRaises(CostError):
            cost_record(promptTokens=10)


class UnknownIsNullNeverZero(unittest.TestCase):
    def test_an_unmeasured_dimension_is_none_not_zero(self):
        record = cost_record(**{API_EQUIVALENT: 3.0})
        self.assertIsNone(record[ACTUAL_MARGINAL])

    def test_a_measured_zero_is_distinguishable_from_unknown(self):
        measured_zero = cost_record(**{ACTUAL_MARGINAL: 0, API_EQUIVALENT: 0})
        unmeasured = cost_record()
        self.assertEqual(measured_zero[ACTUAL_MARGINAL], 0)
        self.assertIsNone(unmeasured[ACTUAL_MARGINAL])
        self.assertNotEqual(measured_zero[ACTUAL_MARGINAL], unmeasured[ACTUAL_MARGINAL])

    def test_unknown_makes_the_cash_total_unknown(self):
        self.assertIsNone(total_cash(cost_record(**{ACTUAL_MARGINAL: 5.0})))
        self.assertIsNone(total_cash(cost_record()))

    def test_negative_fixture_the_legacy_total_called_unknown_free(self):
        """The regression this fixture exists for, demonstrated rather than asserted."""
        unmeasured = cost_record()
        self.assertEqual(legacy_total_cash(unmeasured), 0.0,
                         "baseline: the legacy rule must be able to call unknown free")
        self.assertIsNone(total_cash(unmeasured),
                          "the owned rule keeps it unknown")
        self.assertNotEqual(legacy_total_cash(unmeasured), total_cash(unmeasured),
                            "the two rules must disagree, or the fixture cannot fail")


class BudgetsMustDeclareTheirDimension(unittest.TestCase):
    def test_a_budget_without_a_dimension_is_refused(self):
        with self.assertRaises(CostError):
            assert_budget_declares_dimension({"limit": 20})

    def test_a_budget_with_an_unknown_dimension_is_refused(self):
        with self.assertRaises(CostError):
            assert_budget_declares_dimension({"costDimension": "usd", "limit": 20})

    def test_a_budget_without_a_limit_is_refused(self):
        with self.assertRaises(CostError):
            assert_budget_declares_dimension({"costDimension": ACTUAL_MARGINAL})

    def test_a_declared_budget_returns_its_dimension(self):
        self.assertEqual(
            assert_budget_declares_dimension({"costDimension": QUOTA_BURN, "limit": 100}),
            QUOTA_BURN,
        )


class UnknownNeverWinsAComparison(unittest.TestCase):
    def test_comparison_with_an_unknown_yields_no_verdict(self):
        known = cost_record(**{ACTUAL_MARGINAL: 1.0})
        unknown = cost_record()
        self.assertIsNone(compare(known, unknown, ACTUAL_MARGINAL))
        self.assertIsNone(compare(unknown, known, ACTUAL_MARGINAL))

    def test_two_known_values_compare_normally(self):
        cheap = cost_record(**{ACTUAL_MARGINAL: 1.0})
        dear = cost_record(**{ACTUAL_MARGINAL: 2.0})
        self.assertEqual(compare(cheap, dear, ACTUAL_MARGINAL), -1)


class MalformedCostValuesAreRefused(unittest.TestCase):
    def test_a_string_is_refused(self):
        with self.assertRaises(CostError):
            cost_record(**{ACTUAL_MARGINAL: "1.0"})

    def test_a_negative_value_is_refused(self):
        with self.assertRaises(CostError):
            cost_record(**{ACTUAL_MARGINAL: -1.0})

    def test_a_boolean_is_refused(self):
        with self.assertRaises(CostError):
            cost_record(**{ACTUAL_MARGINAL: True})

    def test_the_vocabulary_is_exactly_the_three_dimensions(self):
        self.assertEqual(
            COST_DIMENSIONS,
            ("actualMarginalCostUsd", "apiEquivalentCostUsd", "quotaBurn"),
        )


if __name__ == "__main__":
    unittest.main()
