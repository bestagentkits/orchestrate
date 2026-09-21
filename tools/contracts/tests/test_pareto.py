"""Behavioural tests for the deterministic Pareto-pruning rules.

Run from the repository root:

    PYTHONPYCACHEPREFIX=/tmp/pyc python3 -m unittest discover -s tools/contracts/tests -t . -v

The cache prefix is not decoration. Instrument defect ID-1 in
`plans/260921-0805-issue15-contract-reconciliation/instrument-defects.md` records a case
where stale bytecode made a correct source look broken, so every run that exercises
mutated code names a scratch cache directory.
"""

from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from tools.contracts.pareto import (  # noqa: E402
    PARETO_DIMENSIONS,
    PARETO_TOLERANCE,
    PROTECTIONS,
    comparable_for_pruning,
    dominates,
    legacy_prune_without_protections,
    prune,
    protection_reasons,
)


def cand(
    name,
    quality: float | None = 0.8,
    cost: float | None = 2.0,
    duration: float | None = 100.0,
    reliability: float | None = 0.9,
    recovery: float | None = 0.5,
    **extra,
):
    """A candidate. A dimension may be ``None``, because unmeasured is a real state."""
    base = {
        "name": name,
        "qualityLowerBound": quality,
        "expectedVerifiedCostUsd": cost,
        "durationSeconds": duration,
        "reliability": reliability,
        "expectedRecoveryCostUsd": recovery,
        "accountingMode": "api-equivalent",
        "cohort": "implement",
    }
    base.update(extra)
    return base


WINNER = cand("winner", quality=0.90, cost=1.0, duration=50.0, reliability=0.95, recovery=0.2)
LOSER = cand("loser", quality=0.70, cost=3.0, duration=200.0, reliability=0.80, recovery=0.8)


def names(candidates):
    return sorted(c["name"] for c in candidates)


class DominatedCandidatesArePruned(unittest.TestCase):
    def test_a_dominated_candidate_is_removed(self):
        survivors, _ = prune([WINNER, LOSER])
        self.assertEqual(names(survivors), ["winner"])

    def test_an_identical_candidate_is_not_pruned(self):
        """No material improvement means no dominance, so noise never prunes."""
        survivors, _ = prune([cand("a"), cand("b")])
        self.assertEqual(names(survivors), ["a", "b"])

    def test_a_difference_inside_the_tolerance_is_not_material(self):
        a = cand("a", cost=1.0)
        b = cand("b", cost=1.0 * (1 + PARETO_TOLERANCE / 2))
        self.assertFalse(dominates(a, b))
        self.assertFalse(dominates(b, a))

    def test_a_difference_beyond_the_tolerance_is_material(self):
        a = cand("a", cost=1.0)
        b = cand("b", cost=1.0 * (1 + PARETO_TOLERANCE * 4))
        self.assertTrue(dominates(a, b))

    def test_an_unknown_dimension_prevents_pruning(self):
        """An unknown is not a value, so dominance cannot be established on it."""
        incomplete = cand("incomplete", quality=None)
        survivors, trace = prune([WINNER, incomplete])
        self.assertIn("incomplete", names(survivors))
        self.assertEqual(trace, [])


class ProtectedCandidatesAlwaysSurvive(unittest.TestCase):
    def _assert_survives_with(self, protected, reason):
        survivors, trace = prune([WINNER, protected], {"requiresIndependence": True, "requiresFallback": True})
        self.assertIn(protected["name"], names(survivors), f"{reason} must protect the candidate")
        kept = [e for e in trace if e["decision"] == "kept" and e["candidate"] == protected["name"]]
        self.assertTrue(kept, "a protection must be recorded in the trace")
        self.assertIn(reason, kept[0]["protectedBy"])

    def test_an_explicit_pin_is_protected(self):
        self._assert_survives_with({**LOSER, "pinned": True}, "explicit-pin")

    def test_c3_independence_is_protected(self):
        self._assert_survives_with({**LOSER, "independentFamily": True}, "c3-independence")

    def test_stronger_controls_are_protected(self):
        self._assert_survives_with({**LOSER, "controlStrength": 5}, "stronger-controls")

    def test_fallback_resilience_is_protected(self):
        self._assert_survives_with({**LOSER, "fallbackCandidate": True}, "fallback-resilience")

    def test_independence_is_not_protected_when_it_is_not_required(self):
        unprotected = {**LOSER, "independentFamily": True}
        survivors, _ = prune([WINNER, unprotected], {"requiresIndependence": False})
        self.assertNotIn("loser", names(survivors),
                         "independence protects only when independence is required")

    def test_the_negative_fixture_prunes_what_the_protections_keep(self):
        """The regression this fixture exists for, demonstrated rather than asserted."""
        pinned = {**LOSER, "pinned": True}
        legacy = legacy_prune_without_protections([WINNER, pinned])
        owned, _ = prune([WINNER, pinned])
        self.assertNotIn("loser", names(legacy), "baseline: pruning without protections must drop a pin")
        self.assertIn("loser", names(owned), "the owned rule keeps the pin")
        self.assertNotEqual(names(legacy), names(owned), "the two rules must disagree, or the fixture cannot fail")


class IncomparableEvidenceBlocksPruning(unittest.TestCase):
    def test_a_different_cohort_is_not_comparable(self):
        other = {**LOSER, "cohort": "docs"}
        self.assertFalse(comparable_for_pruning(WINNER, other))
        survivors, _ = prune([WINNER, other])
        self.assertIn(other["name"], names(survivors))

    def test_a_different_accounting_mode_is_not_comparable(self):
        other = {**LOSER, "accountingMode": "quota"}
        self.assertFalse(comparable_for_pruning(WINNER, other))
        survivors, _ = prune([WINNER, other])
        self.assertIn(other["name"], names(survivors))

    def test_a_pinned_candidate_is_never_removed_even_when_dominated(self):
        pinned_winner = {**WINNER, "pinned": True}
        survivors, _ = prune([pinned_winner, LOSER])
        self.assertIn("winner", names(survivors))


class EveryDecisionIsExplainable(unittest.TestCase):
    def test_a_prune_entry_names_the_dominator_and_the_winning_dimensions(self):
        _, trace = prune([WINNER, LOSER])
        entry = [e for e in trace if e["decision"] == "pruned"][0]
        self.assertEqual(entry["candidate"], "loser")
        self.assertEqual(entry["dominatedBy"], "winner")
        self.assertTrue(entry["betterOn"], "a prune must say what it won on")
        self.assertTrue(set(entry["betterOn"]).issubset(set(PARETO_DIMENSIONS)))

    def test_no_trace_entry_is_emitted_when_nothing_is_pruned(self):
        _, trace = prune([cand("a"), cand("b")])
        self.assertEqual(trace, [])

    def test_the_trace_is_structured_not_prose(self):
        _, trace = prune([WINNER, {**LOSER, "pinned": True}])
        for entry in trace:
            self.assertIn(entry["decision"], ("pruned", "kept"))
            self.assertIsInstance(entry.get("protectedBy", entry.get("betterOn")), list)


class TheVocabularyIsClosed(unittest.TestCase):
    def test_the_dimensions_are_exactly_the_ranked_ones(self):
        self.assertEqual(
            PARETO_DIMENSIONS,
            ("qualityLowerBound", "reliability", "expectedVerifiedCostUsd", "durationSeconds", "expectedRecoveryCostUsd"),
        )

    def test_the_protection_vocabulary_is_closed(self):
        self.assertEqual(
            PROTECTIONS,
            ("explicit-pin", "c3-independence", "stronger-controls", "fallback-resilience",
             "non-comparable-evidence", "different-accounting"),
        )

    def test_the_tolerance_is_pinned(self):
        self.assertEqual(PARETO_TOLERANCE, 0.05)


class NoProviderOrModelNameIsNormative(unittest.TestCase):
    def test_module_source_names_no_current_model(self):
        import tools.contracts.pareto as module

        source = open(module.__file__, encoding="utf-8").read().lower()
        for brand in ("gpt", "deepseek", "glm", "luna", "astra", "kimi", "claude", "gemini", "qwen"):
            self.assertNotIn(brand, source, "a current model brand leaked into routing policy")


if __name__ == "__main__":
    unittest.main()
