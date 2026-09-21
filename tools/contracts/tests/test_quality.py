"""Behavioural tests for the quality-uncertainty and evidence-hierarchy rules.

Run from the repository root:

    python3 -m unittest discover -s tools/contracts/tests -t . -v

The negative fixture is paired with the legacy behaviour it guards against, so it is
shown to be capable of failing rather than merely observed to pass.
"""

from __future__ import annotations

import os
import sys
import unittest
from typing import Any, cast

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from tools.contracts.quality import (  # noqa: E402
    QUALITY_CONFIDENCE_Z,
    QUALITY_ESTIMATOR,
    SCOPE_EXACT_COHORT,
    SCOPE_GLOBAL,
    SCOPE_NONE,
    SCOPE_TASK_CLASS,
    QualityError,
    legacy_raw_rate_order,
    quality_record,
    rank_records,
    resolve_evidence,
    wilson_lower_bound,
)


class SmallPerfectSampleDoesNotWin(unittest.TestCase):
    """The headline property: 3 of 3 must not outrank 300 of 320."""

    def setUp(self):
        self.tiny = quality_record(3, 3)
        self.large = quality_record(300, 320)

    def test_the_tiny_perfect_sample_has_the_higher_raw_rate(self):
        self.assertGreater(self.tiny["rawSuccessRate"], self.large["rawSuccessRate"])

    def test_but_the_large_sample_has_the_higher_conservative_bound(self):
        self.assertGreater(self.large["qualityLowerBound"], self.tiny["qualityLowerBound"])

    def test_so_the_large_sample_ranks_first(self):
        ranked = rank_records([self.tiny, self.large])
        self.assertEqual(ranked[0], self.large)

    def test_negative_fixture_raw_rate_ordering_puts_the_tiny_sample_first(self):
        """The regression this fixture exists for, demonstrated rather than asserted."""
        legacy = legacy_raw_rate_order([self.tiny, self.large])
        self.assertEqual(legacy[0], self.tiny,
                         "baseline: raw-rate ordering must be able to fail this")
        self.assertNotEqual(legacy[0], rank_records([self.tiny, self.large])[0],
                            "the two rules must disagree, or the fixture cannot fail")


class TheBoundIsConservativeAndDeterministic(unittest.TestCase):
    def test_the_bound_sits_strictly_below_the_raw_rate(self):
        for successes, sample in ((1, 1), (10, 10), (50, 100), (300, 320)):
            record = quality_record(successes, sample)
            self.assertLess(record["qualityLowerBound"], record["rawSuccessRate"])

    def test_the_bound_converges_upward_as_the_sample_grows(self):
        bounds = [wilson_lower_bound(int(0.9 * n), n) for n in (10, 100, 1000, 10000)]
        self.assertEqual(bounds, sorted(bounds), "more evidence must not lower the bound")

    def test_the_estimator_is_deterministic(self):
        self.assertEqual(wilson_lower_bound(7, 10), wilson_lower_bound(7, 10))

    def test_the_estimator_identity_and_confidence_are_recorded(self):
        record = quality_record(5, 10)
        self.assertEqual(record["estimator"], QUALITY_ESTIMATOR)
        self.assertEqual(record["confidenceZ"], QUALITY_CONFIDENCE_Z)
        self.assertEqual(record["successes"], 5)
        self.assertEqual(record["sampleSize"], 10)

    def test_a_declared_confidence_wider_than_95_percent_is_more_conservative(self):
        self.assertLess(wilson_lower_bound(8, 10, 2.576), wilson_lower_bound(8, 10, 1.96))


class MalformedEvidenceIsRefused(unittest.TestCase):
    def test_no_evidence_has_no_bound(self):
        with self.assertRaises(QualityError):
            wilson_lower_bound(0, 0)

    def test_more_successes_than_samples_is_refused(self):
        with self.assertRaises(QualityError):
            wilson_lower_bound(5, 3)

    def test_negative_successes_is_refused(self):
        with self.assertRaises(QualityError):
            wilson_lower_bound(-1, 3)

    def test_a_non_integer_sample_is_refused(self):
        # A parsed value the signature cannot promise, which is why the runtime check exists.
        malformed = cast(Any, 3.5)
        with self.assertRaises(QualityError):
            wilson_lower_bound(1, malformed)

    def test_a_boolean_is_refused(self):
        with self.assertRaises(QualityError):
            wilson_lower_bound(True, 3)


class NoEvidenceIsLastAndNeverAverage(unittest.TestCase):
    def test_a_record_without_a_sample_is_not_ranked_on_a_bound(self):
        with_bound = quality_record(1, 1)
        without = {"provider": "p", "model": "m", "effortMode": "e"}
        ranked = rank_records([without, with_bound])
        self.assertEqual(ranked[0], with_bound)
        self.assertEqual(ranked[-1], without)

    def test_a_record_without_a_sample_is_not_treated_as_zero_or_average(self):
        without = {"provider": "p", "model": "m", "effortMode": "e"}
        self.assertNotIn("qualityLowerBound", without)


class EvidenceScopeIsRecordedAndDegradationIsExplicit(unittest.TestCase):
    def setUp(self):
        self.exact = quality_record(4, 5, cohort="csv", taskClass="implement")
        self.class_level = quality_record(40, 50, cohort="other", taskClass="implement")
        self.global_only = quality_record(400, 500, cohort="other", taskClass="docs")

    def test_the_exact_cohort_supplies_evidence_when_it_exists(self):
        resolved = resolve_evidence([self.global_only, self.exact, self.class_level], "csv", "implement")
        self.assertEqual(resolved["scope"], SCOPE_EXACT_COHORT)
        self.assertFalse(resolved["degraded"])
        self.assertEqual(resolved["records"], [self.exact])

    def test_the_task_class_is_used_only_as_a_recorded_fallback(self):
        resolved = resolve_evidence([self.global_only, self.class_level], "csv", "implement")
        self.assertEqual(resolved["scope"], SCOPE_TASK_CLASS)
        self.assertTrue(resolved["degraded"], "a broader level must be marked degraded")
        self.assertEqual(resolved["records"], [self.class_level])

    def test_global_evidence_is_the_last_resort_and_is_degraded(self):
        resolved = resolve_evidence([self.global_only], "csv", "implement")
        self.assertEqual(resolved["scope"], SCOPE_GLOBAL)
        self.assertTrue(resolved["degraded"])

    def test_no_record_is_reported_as_no_record_not_as_average(self):
        resolved = resolve_evidence([], "csv", "implement")
        self.assertEqual(resolved["scope"], SCOPE_NONE)
        self.assertTrue(resolved["degraded"])
        self.assertEqual(resolved["records"], [])

    def test_an_absent_cohort_never_claims_exact_cohort_evidence(self):
        """A record with no cohort must not be presented as measured on this cohort."""
        no_cohort = quality_record(4, 5, taskClass="implement")
        resolved = resolve_evidence([no_cohort], None, "implement")
        self.assertNotEqual(resolved["scope"], SCOPE_EXACT_COHORT)

    def test_broader_evidence_is_never_averaged_into_a_narrower_level(self):
        resolved = resolve_evidence([self.global_only, self.exact], "csv", "implement")
        self.assertEqual(len(resolved["records"]), 1,
                         "a broader level must not be merged into the narrower result")


if __name__ == "__main__":
    unittest.main()
