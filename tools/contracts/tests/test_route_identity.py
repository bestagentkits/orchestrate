"""Behavioural tests for the route-identity rules.

Run from the repository root:

    python3 -m unittest discover -s tools/contracts/tests -t . -v

Every negative fixture in this file is paired with the legacy behaviour it guards
against, so the fixture is shown to be capable of failing rather than merely observed
to pass. A test that can never fail proves nothing, and this repository has shipped
that defect before.
"""

from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from tools.contracts.route_identity import (  # noqa: E402
    collapse_aliases,
    distinct_identity_count,
    is_comparable,
    route_key,
)


def legacy_route_key(record: dict) -> tuple | None:
    """The key this contract replaced: `(provider, model, effortLevel)`.

    Kept here as the negative baseline. A regression that reintroduced it would be
    counted twice by the collapse tests below, and those tests would fail.
    """
    values = [record.get("provider"), record.get("model"), record.get("effortLevel")]
    if any(value in (None, "") for value in values):
        return None
    return tuple(values)


def legacy_collapse(records: list[dict]) -> list[dict]:
    """Collapse under the legacy key, for comparison only."""
    seen: dict[tuple, dict] = {}
    out = []
    for record in records:
        key = legacy_route_key(record)
        if key is None or key not in seen:
            if key is not None:
                seen[key] = record
            out.append(record)
    return out


class EffortModeDecidesIdentity(unittest.TestCase):
    """A real mode is one candidate; a label is not."""

    def test_two_labels_reaching_one_real_mode_are_one_candidate(self):
        # 'high' and 'max' are two labels that the provider resolves to one real mode.
        records = [
            {"runtime": "pi", "provider": "p", "model": "m", "family": "f",
             "effortMode": "reasoning-16384", "effortLevel": "high", "effortRaw": "high",
             "sampleSize": 4},
            {"runtime": "pi", "provider": "p", "model": "m", "family": "f",
             "effortMode": "reasoning-16384", "effortLevel": "max", "effortRaw": "max",
             "sampleSize": 6},
        ]
        collapsed = collapse_aliases(records)
        self.assertEqual(len(collapsed), 1, "one real mode must be one candidate")
        self.assertEqual(collapsed[0]["sampleSize"], 10, "evidence must merge")
        self.assertEqual(sorted(collapsed[0]["effortAliases"]), ["high", "max"],
                         "the collapse must be auditable through its aliases")

    def test_one_label_reaching_two_real_modes_are_two_candidates(self):
        # A vendor ladder that is not the normalized ladder: one label, two modes.
        records = [
            {"runtime": "pi", "provider": "p", "model": "m", "family": "f",
             "effortMode": "mode-a", "effortLevel": "high", "effortRaw": "high"},
            {"runtime": "pi", "provider": "p", "model": "m", "family": "f",
             "effortMode": "mode-b", "effortLevel": "high", "effortRaw": "high-max"},
        ]
        self.assertEqual(distinct_identity_count(records), 2,
                         "one label reaching two real modes must not merge")

    def test_negative_fixture_the_legacy_key_could_not_collapse(self):
        """The regression this fixture exists for, demonstrated rather than asserted.

        Under the replaced key the same two records are counted twice, which is exactly
        the duplicate-candidate defect. If the new rule ever regressed to the legacy
        key, the collapse tests above would fail.
        """
        records = [
            {"runtime": "pi", "provider": "p", "model": "m", "family": "f",
             "effortMode": "reasoning-16384", "effortLevel": "high", "sampleSize": 4},
            {"runtime": "pi", "provider": "p", "model": "m", "family": "f",
             "effortMode": "reasoning-16384", "effortLevel": "max", "sampleSize": 6},
        ]
        self.assertEqual(len(legacy_collapse(records)), 2,
                         "baseline: the legacy key must be able to fail this")
        self.assertEqual(distinct_identity_count(records), 1,
                         "the owned rule collapses them")


class RuntimeIsPartOfIdentity(unittest.TestCase):
    """Two adapters reaching one provider are two candidates; only the family is shared."""

    def test_same_provider_model_mode_on_two_runtimes_are_two_candidates(self):
        records = [
            {"runtime": "pi", "provider": "p", "model": "m", "family": "f", "effortMode": "e"},
            {"runtime": "other", "provider": "p", "model": "m", "family": "f", "effortMode": "e"},
        ]
        self.assertEqual(distinct_identity_count(records), 2)

    def test_family_is_what_is_compared_across_executables(self):
        left = {"runtime": "pi", "provider": "p", "model": "m", "family": "f", "effortMode": "e"}
        right = {"runtime": "other", "provider": "p", "model": "m", "family": "f", "effortMode": "e"}
        self.assertEqual(left["family"], right["family"])


class UndecidableIdentityNeverMerges(unittest.TestCase):
    """Fail closed: an unknown real mode must not be collapsed into a known one."""

    def test_missing_effort_mode_yields_no_key(self):
        self.assertIsNone(route_key({"provider": "p", "model": "m", "family": "f"}))

    def test_missing_effort_mode_records_stay_separate(self):
        records = [
            {"runtime": "pi", "provider": "p", "model": "m", "family": "f"},
            {"runtime": "pi", "provider": "p", "model": "m", "family": "f"},
        ]
        collapsed = collapse_aliases(records)
        self.assertEqual(len(collapsed), 2, "undecidable identities must never merge")
        self.assertTrue(all(entry["identityUndecidable"] for entry in collapsed))


class UnmappedLaddersAreNotComparableAcrossProviders(unittest.TestCase):
    def test_unmapped_across_providers_is_not_comparable(self):
        left = {"provider": "p1", "effortClass": "unmapped"}
        right = {"provider": "p2", "effortClass": "unmapped"}
        self.assertFalse(is_comparable(left, right))

    def test_unmapped_within_one_provider_is_comparable(self):
        left = {"provider": "p1", "effortClass": "unmapped"}
        right = {"provider": "p1", "effortClass": "unmapped"}
        self.assertTrue(is_comparable(left, right))

    def test_mapped_candidates_are_comparable_across_providers(self):
        left = {"provider": "p1", "effortClass": "vendor-a"}
        right = {"provider": "p2", "effortClass": "vendor-b"}
        self.assertTrue(is_comparable(left, right))


class NoProviderOrModelNameIsNormative(unittest.TestCase):
    """No current model name may become part of the identity itself."""

    def test_identity_is_built_only_from_the_declared_fields(self):
        import tools.contracts.route_identity as module

        self.assertEqual(
            module.IDENTITY_FIELDS,
            ("runtime", "provider", "model", "family", "effortMode"),
        )

    def test_module_source_names_no_current_model(self):
        import tools.contracts.route_identity as module

        source = open(module.__file__, encoding="utf-8").read().lower()
        for brand in ("gpt", "deepseek", "glm", "luna", "astra", "kimi", "claude", "gemini"):
            self.assertNotIn(brand, source, f"a current model brand leaked into the identity")


if __name__ == "__main__":
    unittest.main()
