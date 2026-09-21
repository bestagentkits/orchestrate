"""Behavioural tests for the calibration validity and durability rules.

Run from the repository root:

    PYTHONPYCACHEPREFIX=/tmp/pyc python3 -m unittest discover -s tools/contracts/tests -t . -v

The cache prefix is required for any run that exercises mutated code; see instrument
defect ID-1 in `plans/260921-0805-issue15-contract-reconciliation/instrument-defects.md`.

A note on the blocker rule. The goal's contract says that if a self-invalidation-proof
durable calibration design turns out to be impossible, the contradiction is to be reported
rather than papered over by a weaker contract. It is not impossible, and the reason is
tested below: the floors are supplied by the caller from the owner-pinned constants and
never read from the record, and durability itself is refused when the classifier version is
not observable. The residual limitation is real and is stated rather than hidden - an
unversioned classifier cannot use a durable record at all - but it is a conservative
degradation to the bounded shadow sample, not a relaxation of verification.
"""

from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from tools.contracts.calibration import (  # noqa: E402
    IDENTITY_COMPONENTS,
    INVALID_REASONS,
    CalibrationError,
    durable_record_is_reusable,
    legacy_validity_trusting_the_record,
    validity,
)

NOW = "2026-09-21T00:00:00Z"
MINIMUM_SAMPLES = 30
AGREEMENT_FLOOR = 0.95
INITIAL_THRESHOLD = 0.90
FULL_SIGNALS = (
    "artifact_matches_expected_output",
    "claims_supported_by_evidence",
    "materially_unresolved",
)

IDENTITY = {
    "classifierProvider": "provider-a",
    "classifierModelId": "classifier-a",
    "classifierVersion": "1.13.0",
    "decisionSchemaHash": "schema-a",
    "promptContractHash": "prompt-a",
    "signalSetHash": "signals-a",
    "thresholdPolicy": "threshold-a",
}

RECORD = {
    **IDENTITY,
    "sampleCount": 40,
    "minimum": MINIMUM_SAMPLES,
    "agreement": 0.97,
    "threshold": 0.92,
    "signals": list(FULL_SIGNALS),
    "expiresAt": "2026-10-01T00:00:00Z",
}


def check(record=None, identity=None, now=NOW):
    return validity(
        RECORD if record is None else record,
        IDENTITY if identity is None else identity,
        now,
        minimum_samples=MINIMUM_SAMPLES,
        agreement_floor=AGREEMENT_FLOOR,
        initial_threshold=INITIAL_THRESHOLD,
        full_signal_set=FULL_SIGNALS,
    )


class AValidRecordIsReusable(unittest.TestCase):
    def test_a_matching_fresh_record_is_reusable(self):
        result = check()
        self.assertTrue(result["reusable"])
        self.assertEqual(result["reasons"], [])

    def test_the_wrapper_agrees(self):
        self.assertTrue(durable_record_is_reusable(
            RECORD, IDENTITY, now=NOW, minimum_samples=MINIMUM_SAMPLES,
            agreement_floor=AGREEMENT_FLOOR, initial_threshold=INITIAL_THRESHOLD,
            full_signal_set=FULL_SIGNALS,
        ))


class EveryIdentityChangeInvalidates(unittest.TestCase):
    def test_each_component_change_invalidates_the_record(self):
        for component in IDENTITY_COMPONENTS:
            with self.subTest(component=component):
                changed = {**RECORD, component: "changed"}
                result = check(record=changed)
                self.assertFalse(result["reusable"], f"{component} change must invalidate")
                self.assertIn("identity-mismatch", result["reasons"])

    def test_a_model_change_invalidates(self):
        changed = {**RECORD, "classifierModelId": "classifier-b"}
        self.assertIn("identity-mismatch", check(record=changed)["reasons"])

    def test_a_schema_change_invalidates(self):
        changed = {**RECORD, "decisionSchemaHash": "schema-b"}
        self.assertIn("identity-mismatch", check(record=changed)["reasons"])

    def test_a_prompt_contract_change_invalidates(self):
        changed = {**RECORD, "promptContractHash": "prompt-b"}
        self.assertIn("identity-mismatch", check(record=changed)["reasons"])

    def test_a_signal_set_change_invalidates(self):
        changed = {**RECORD, "signalSetHash": "signals-b"}
        self.assertIn("identity-mismatch", check(record=changed)["reasons"])

    def test_a_threshold_policy_change_invalidates(self):
        changed = {**RECORD, "thresholdPolicy": "threshold-b"}
        self.assertIn("identity-mismatch", check(record=changed)["reasons"])


class ExpiryAndFloors(unittest.TestCase):
    def test_an_expired_record_is_rejected(self):
        result = check(now="2026-11-01T00:00:00Z")
        self.assertFalse(result["reusable"])
        self.assertIn("expired", result["reasons"])

    def test_too_few_samples_is_rejected(self):
        result = check(record={**RECORD, "sampleCount": 10})
        self.assertIn("below-minimum-samples", result["reasons"])

    def test_agreement_below_the_floor_is_rejected(self):
        result = check(record={**RECORD, "agreement": 0.80})
        self.assertIn("agreement-below-floor", result["reasons"])

    def test_a_threshold_below_the_initial_value_is_rejected(self):
        result = check(record={**RECORD, "threshold": 0.50})
        self.assertIn("threshold-below-initial", result["reasons"])

    def test_an_incomplete_signal_set_is_rejected(self):
        result = check(record={**RECORD, "signals": ["artifact_matches_expected_output"]})
        self.assertIn("signal-set-incomplete", result["reasons"])

    def test_every_recorded_reason_comes_from_the_closed_set(self):
        result = check(record={**RECORD, "sampleCount": 1, "agreement": 0.1, "threshold": 0.1})
        for reason in result["reasons"]:
            self.assertIn(reason, INVALID_REASONS)


class ARecordCannotValidateItself(unittest.TestCase):
    def test_a_record_asserting_its_own_lower_minimum_is_rejected(self):
        """The floors come from the owner, so a self-satisfied record is invalid."""
        asserting = {**RECORD, "minimum": 1, "sampleCount": 1}
        result = check(record=asserting)
        self.assertFalse(result["reusable"])
        self.assertIn("self-asserted-floor", result["reasons"])

    def test_the_owners_lower_value_cannot_be_lowered_by_the_record(self):
        for claimed in (0, 1, 29):
            with self.subTest(claimed=claimed):
                result = check(record={**RECORD, "minimum": claimed})
                self.assertIn("self-asserted-floor", result["reasons"])

    def test_the_wrapper_never_reads_floors_from_the_record(self):
        lowered = {**RECORD, "minimum": 1, "threshold": 0.01, "agreement": 0.01}
        self.assertFalse(durable_record_is_reusable(
            lowered, IDENTITY, now=NOW, minimum_samples=MINIMUM_SAMPLES,
            agreement_floor=AGREEMENT_FLOOR, initial_threshold=INITIAL_THRESHOLD,
            full_signal_set=FULL_SIGNALS,
        ))

    def test_the_negative_fixture_trusts_the_record(self):
        """The regression this fixture exists for, demonstrated rather than asserted."""
        asserting = {**RECORD, "minimum": 1, "sampleCount": 1, "agreement": 0.01,
                     "threshold": 0.01, "signals": ["only_one_signal"]}
        legacy_accepts = legacy_validity_trusting_the_record(asserting, NOW)
        owned_accepts = check(record=asserting)["reusable"]
        self.assertTrue(legacy_accepts, "baseline: trusting the record must be able to fail this")
        self.assertFalse(owned_accepts, "the owned rule refuses a self-validating record")
        self.assertNotEqual(legacy_accepts, owned_accepts,
                            "the two rules must disagree, or the fixture cannot fail")


class AnUnobservableVersionRefusesDurability(unittest.TestCase):
    def test_a_runtime_without_a_version_cannot_reuse_a_durable_record(self):
        """A silent classifier change would be undetectable, so reuse is refused."""
        unversioned = {k: v for k, v in IDENTITY.items() if k != "classifierVersion"}
        record_without_version = {k: v for k, v in RECORD.items() if k != "classifierVersion"}
        result = check(record=record_without_version, identity=unversioned)
        self.assertFalse(result["reusable"])
        self.assertIn("version-unobservable", result["reasons"])

    def test_an_observable_version_allows_reuse(self):
        self.assertTrue(check()["reusable"])

    def test_an_empty_record_is_refused_rather_than_treated_as_valid(self):
        with self.assertRaises(CalibrationError):
            check(record={})


class TheVocabularyIsClosed(unittest.TestCase):
    def test_the_identity_components_are_enumerated(self):
        self.assertEqual(
            IDENTITY_COMPONENTS,
            ("classifierProvider", "classifierModelId", "classifierVersion",
             "decisionSchemaHash", "promptContractHash", "signalSetHash", "thresholdPolicy"),
        )

    def test_the_reasons_are_enumerated_without_repetition(self):
        self.assertEqual(len(INVALID_REASONS), 8)
        self.assertEqual(len(set(INVALID_REASONS)), 8)

    def test_the_reported_order_is_deterministic(self):
        record = {**RECORD, "sampleCount": 1, "agreement": 0.1, "minimum": 1, "threshold": 0.1}
        self.assertEqual(check(record=record)["reasons"], check(record=record)["reasons"])


class NoProviderOrModelNameIsNormative(unittest.TestCase):
    def test_module_source_names_no_current_model(self):
        import tools.contracts.calibration as module

        source_path = module.__file__
        assert source_path is not None
        with open(source_path, encoding="utf-8") as handle:
            source = handle.read().lower()
        for brand in ("gpt", "deepseek", "glm", "luna", "astra", "kimi", "claude", "gemini", "qwen"):
            self.assertNotIn(brand, source, "a current model brand leaked into calibration policy")


if __name__ == "__main__":
    unittest.main()
