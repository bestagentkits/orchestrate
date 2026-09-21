"""Behavioural tests for the task quality floor and verification-strength rules.

Run from the repository root:

    python3 -m unittest discover -s tools/contracts/tests -t . -v

Two safety-shaped properties are guarded here, and both have a negative fixture paired
with the legacy behaviour they replaced:

- selection picks the cheapest route that clears the floor, not the strongest;
- verification strength re-ranks eligible routes and never widens eligibility downward.
"""

from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from tools.contracts.routing import (  # noqa: E402
    CAPABILITY_TIERS,
    QUALITY_FLOOR_JUDGMENT,
    QUALITY_FLOOR_STRONG_VERIFICATION,
    QUALITY_FLOOR_WEAK_VERIFICATION,
    STRONG_VERIFICATION,
    WEAK_VERIFICATION,
    RoutingError,
    clears_capability,
    clears_quality,
    legacy_strongest_route,
    quality_floor,
    select_route,
    tier_rank,
)


def route(name, tier, bound, cost):
    return {
        "name": name,
        "capabilityTier": tier,
        "qualityLowerBound": bound,
        "expectedVerifiedCostUsd": cost,
    }


class CheapestClearingTheFloorWins(unittest.TestCase):
    def setUp(self):
        self.cheap = route("cheap", "C2", 0.60, 1.0)
        self.mid = route("mid", "C2", 0.70, 3.0)
        self.strong = route("strong", "C3", 0.95, 10.0)
        self.candidates = [self.strong, self.mid, self.cheap]

    def test_the_cheapest_clearing_route_is_selected(self):
        chosen = select_route(self.candidates, "C2", QUALITY_FLOOR_STRONG_VERIFICATION)
        self.assertEqual(chosen, self.cheap)

    def test_the_strongest_route_is_not_selected_despite_the_better_bound(self):
        chosen = select_route(self.candidates, "C2", QUALITY_FLOOR_STRONG_VERIFICATION)
        assert chosen is not None
        self.assertNotEqual(chosen, self.strong)
        self.assertGreater(self.strong["qualityLowerBound"], chosen["qualityLowerBound"])

    def test_negative_fixture_strongest_first_disagrees(self):
        """The regression this fixture exists for, demonstrated rather than asserted."""
        legacy = legacy_strongest_route(self.candidates, "C2")
        owned = select_route(self.candidates, "C2", QUALITY_FLOOR_STRONG_VERIFICATION)
        self.assertEqual(legacy, self.strong, "baseline: strongest-first must be able to fail this")
        self.assertNotEqual(legacy, owned, "the two rules must disagree, or the fixture cannot fail")


class AFloorsAreNotNegotiable(unittest.TestCase):
    def test_a_route_below_the_capability_tier_is_never_selected(self):
        cheap_but_weak = route("weak", "C1", 0.99, 0.1)
        chosen = select_route([cheap_but_weak], "C2", QUALITY_FLOOR_STRONG_VERIFICATION)
        self.assertIsNone(chosen, "a C1 route must not be selected when C2 is required")

    def test_strong_verification_cannot_widen_eligibility_downward(self):
        """Lowering the floor for strong verification must not admit a lower tier."""
        strong_floor = quality_floor(STRONG_VERIFICATION)
        weak_floor = quality_floor(WEAK_VERIFICATION)
        self.assertLess(strong_floor, weak_floor, "strong verification lowers the floor")
        weak = route("weak", "C1", 0.99, 0.1)
        for floor in (strong_floor, weak_floor):
            self.assertIsNone(select_route([weak], "C2", floor))

    def test_a_quality_floor_never_replaces_the_capability_floor(self):
        strong_but_low_tier = route("s", "C1", 0.99, 0.1)
        weak_but_right_tier = route("w", "C3", 0.60, 5.0)
        chosen = select_route([strong_but_low_tier, weak_but_right_tier], "C2", 0.10)
        self.assertEqual(chosen, weak_but_right_tier)


class MissingEvidenceFailsClosed(unittest.TestCase):
    def test_a_route_with_no_quality_bound_does_not_clear_a_floor(self):
        no_bound = {"name": "x", "capabilityTier": "C2", "expectedVerifiedCostUsd": 1.0}
        self.assertFalse(clears_quality(no_bound, 0.10))

    def test_a_route_with_no_tier_does_not_clear_the_capability_floor(self):
        no_tier = {"name": "x", "qualityLowerBound": 0.99, "expectedVerifiedCostUsd": 1.0}
        self.assertFalse(clears_capability(no_tier, "C1"))

    def test_a_route_with_an_unclassifiable_tier_does_not_clear(self):
        bad_tier = {"name": "x", "capabilityTier": "C9", "qualityLowerBound": 0.99}
        self.assertFalse(clears_capability(bad_tier, "C1"))

    def test_a_route_with_unknown_cost_is_not_the_cheapest(self):
        unknown_cost = {"name": "u", "capabilityTier": "C2", "qualityLowerBound": 0.99,
                        "expectedVerifiedCostUsd": None}
        known = route("k", "C2", 0.99, 2.0)
        self.assertEqual(select_route([unknown_cost, known], "C2", 0.10), known)

    def test_nothing_clearing_yields_none_rather_than_a_weakened_floor(self):
        self.assertIsNone(select_route([route("w", "C1", 0.1, 0.01)], "C3", 0.90))


class FloorDerivation(unittest.TestCase):
    def test_strong_verification_requires_less_than_weak(self):
        self.assertLess(quality_floor(STRONG_VERIFICATION), quality_floor(WEAK_VERIFICATION))

    def test_judgment_work_requires_the_top_band(self):
        for task_class in ("architecture", "review", "audit", "security", "arbiter"):
            self.assertEqual(quality_floor(STRONG_VERIFICATION, task_class=task_class), QUALITY_FLOOR_JUDGMENT)

    def test_high_importance_requires_the_top_band(self):
        self.assertEqual(
            quality_floor(STRONG_VERIFICATION, importance="high"), QUALITY_FLOOR_JUDGMENT
        )

    def test_an_unknown_verification_strength_is_refused(self):
        with self.assertRaises(RoutingError):
            quality_floor("medium")

    def test_the_tier_vocabulary_is_exactly_three_tiers(self):
        self.assertEqual(CAPABILITY_TIERS, ("C1", "C2", "C3"))
        self.assertEqual([tier_rank(t) for t in CAPABILITY_TIERS], [1, 2, 3])

    def test_an_unknown_tier_is_refused_by_the_rank_helper(self):
        with self.assertRaises(RoutingError):
            tier_rank("C4")

    def test_the_pinned_constants_match_the_contract(self):
        self.assertEqual(QUALITY_FLOOR_STRONG_VERIFICATION, 0.50)
        self.assertEqual(QUALITY_FLOOR_WEAK_VERIFICATION, 0.85)
        self.assertEqual(QUALITY_FLOOR_JUDGMENT, 0.90)


class NoProviderOrModelNameIsNormative(unittest.TestCase):
    def test_module_source_names_no_current_model(self):
        import tools.contracts.routing as module

        source = open(module.__file__, encoding="utf-8").read().lower()
        for brand in ("gpt", "deepseek", "glm", "luna", "astra", "kimi", "claude", "gemini", "qwen"):
            self.assertNotIn(brand, source, f"a current model brand leaked into routing policy")


if __name__ == "__main__":
    unittest.main()
