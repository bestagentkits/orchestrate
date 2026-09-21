"""Behavioural tests for the failure-class recording and recovery-cost rules.

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

from tools.contracts.reliability import (  # noqa: E402
    KIND_TO_CLASS,
    OBSERVED_KINDS,
    OWNED_CLASSES,
    ReliabilityError,
    classify,
    legacy_recovery_evidence_count,
    may_promote,
    recovery_cost_evidence,
    tally,
)


class ClassesAreRecordedSeparately(unittest.TestCase):
    def test_every_kind_maps_onto_an_owned_class(self):
        for kind in OBSERVED_KINDS:
            self.assertIn(classify(kind)["className"], OWNED_CLASSES)

    def test_the_mapping_is_exactly_the_declared_one(self):
        self.assertEqual(KIND_TO_CLASS, {
            "infrastructure": "transport-or-infrastructure",
            "content": "content-or-verification",
            "permission": "permission-or-authorization",
            "provider-rate-limit": "retryable-provider",
            "evidence-plane-write": "evidence-plane-write",
        })

    def test_counts_are_kept_per_class_and_never_blended(self):
        counts = tally(["infrastructure", "content", "content", "permission"])
        self.assertEqual(counts["transport-or-infrastructure"], 1)
        self.assertEqual(counts["content-or-verification"], 2)
        self.assertEqual(counts["permission-or-authorization"], 1)

    def test_every_class_is_present_even_when_empty(self):
        counts = tally([])
        self.assertEqual(set(counts), set(OWNED_CLASSES))
        self.assertTrue(all(value == 0 for value in counts.values()))

    def test_an_unknown_kind_is_refused(self):
        with self.assertRaises(ReliabilityError):
            tally(["flaky"])


class OnlyInfrastructureFeedsRecoveryCost(unittest.TestCase):
    def test_infrastructure_is_the_only_feeding_class(self):
        for kind in OBSERVED_KINDS:
            self.assertEqual(classify(kind)["feedsRecoveryCost"], kind == "infrastructure")

    def test_the_evidence_helper_reports_only_infrastructure(self):
        evidence = recovery_cost_evidence(["infrastructure", "infrastructure", "content"])
        self.assertEqual(evidence["infrastructureCount"], 2)
        self.assertTrue(evidence["usable"])

    def test_the_excluded_classes_are_named_rather_than_implied(self):
        evidence = recovery_cost_evidence(["content", "permission", "provider-rate-limit",
                                           "evidence-plane-write"])
        excluded = evidence["excludedFromRecoveryCost"]
        self.assertEqual(excluded["content-or-verification"], 1)
        self.assertEqual(excluded["permission-or-authorization"], 1)
        self.assertEqual(excluded["retryable-provider"], 1)
        self.assertEqual(excluded["evidence-plane-write"], 1)
        self.assertEqual(evidence["infrastructureCount"], 0)
        self.assertFalse(evidence["usable"], "content alone must not justify recovery cost")

    def test_content_only_evidence_is_not_usable(self):
        self.assertFalse(recovery_cost_evidence(["content", "content"])["usable"])


class ContentNeverPromotes(unittest.TestCase):
    def test_content_is_not_a_promotion_candidate(self):
        self.assertFalse(may_promote("content"))

    def test_repeated_content_failures_do_not_accumulate_into_a_promotion(self):
        for count in (1, 5, 50):
            with self.subTest(count=count):
                observations = ["content"] * count
                evidence = recovery_cost_evidence(observations)
                self.assertEqual(evidence["infrastructureCount"], 0)
                self.assertFalse(evidence["usable"])
                self.assertFalse(may_promote("content"))

    def test_content_escalates_instead_of_promoting(self):
        self.assertTrue(classify("content")["escalates"])
        self.assertFalse(classify("content")["promotionCandidate"])

    def test_permission_is_a_hard_stop_not_a_promotion(self):
        self.assertTrue(classify("permission")["hardStop"])
        self.assertFalse(may_promote("permission"))

    def test_a_provider_rate_limit_retries_within_the_runtime_first(self):
        self.assertTrue(classify("provider-rate-limit")["retryableWithinRuntime"])
        self.assertFalse(classify("provider-rate-limit")["feedsRecoveryCost"])

    def test_an_evidence_plane_write_neither_promotes_nor_escalates(self):
        decision = classify("evidence-plane-write")
        self.assertFalse(decision["promotionCandidate"])
        self.assertFalse(decision["escalates"])
        self.assertFalse(decision["feedsRecoveryCost"])

    def test_infrastructure_is_the_promotion_candidate(self):
        self.assertTrue(may_promote("infrastructure"))


class TheNegativeFixtureBlendingEverythingDisagrees(unittest.TestCase):
    def test_the_regression_this_fixture_exists_for(self):
        """Counting every failure as recovery evidence misprices a content failure."""
        observations = ["content", "permission", "provider-rate-limit"]
        legacy = legacy_recovery_evidence_count(observations)
        owned = recovery_cost_evidence(observations)["infrastructureCount"]
        self.assertEqual(legacy, 3, "baseline: the legacy rule must be able to count them all")
        self.assertEqual(owned, 0, "the owned rule counts none of them")
        self.assertNotEqual(legacy, owned, "the two rules must disagree, or the fixture cannot fail")

    def test_the_two_rules_agree_only_when_every_failure_is_infrastructure(self):
        observations = ["infrastructure", "infrastructure"]
        self.assertEqual(
            legacy_recovery_evidence_count(observations),
            recovery_cost_evidence(observations)["infrastructureCount"],
        )


class TheVocabularyIsClosed(unittest.TestCase):
    def test_the_observed_kinds_are_enumerated(self):
        self.assertEqual(
            OBSERVED_KINDS,
            ("infrastructure", "content", "permission", "provider-rate-limit", "evidence-plane-write"),
        )

    def test_the_owned_classes_are_referenced_not_redefined(self):
        self.assertEqual(len(OWNED_CLASSES), 5)
        self.assertEqual(set(KIND_TO_CLASS.values()), set(OWNED_CLASSES))


class NoProviderOrModelNameIsNormative(unittest.TestCase):
    def test_module_source_names_no_current_model(self):
        import tools.contracts.reliability as module

        source_path = module.__file__
        assert source_path is not None
        with open(source_path, encoding="utf-8") as handle:
            source = handle.read().lower()
        for brand in ("gpt", "deepseek", "glm", "luna", "astra", "kimi", "claude", "gemini", "qwen"):
            self.assertNotIn(brand, source, "a current model brand leaked into reliability policy")


if __name__ == "__main__":
    unittest.main()
