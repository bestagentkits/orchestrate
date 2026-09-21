"""Behavioural tests for the frozen experiment manifest and its pre-registration.

Run from the repository root:

    PYTHONPYCACHEPREFIX=/tmp/pyc python3 -m unittest discover -s tools -t . -v

The manifest's whole purpose is to be fixed before a result exists, so the tests check that it
cannot be silently incomplete: a missing frozen field, a missing pre-registered parameter, a
fixture whose digests do not match, or a manifest that claims a paid run all fail validation.
"""

from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from tools.benchmark import freeze_manifest as fm  # noqa: E402

RUNTIME = {
    "runtimeName": fm.capability(fm.EXPOSED, "pi"),
    "runtimeVersion": fm.capability(fm.EXPOSED, "0.0.0-test"),
}
REPOSITORY = {
    "orchestrateCommit": fm.capability(fm.EXPOSED, "0" * 40),
    "orchestrateBranch": fm.capability(fm.EXPOSED, "benchmark"),
    "worktreeClean": fm.capability(fm.EXPOSED, True),
    "worktreeDirtyFiles": 0,
}
CATALOG = {"state": fm.NOT_MEASURED, "value": None, "basis": "test stub"}
FIXTURE = {
    "id": "taskflow", "version": "1.0.0",
    "workspaceDigest": fm.capability(fm.EXPOSED, "a" * 64),
    "graderDigest": fm.capability(fm.EXPOSED, "b" * 64),
    "recomputed": {"workspace": "a" * 64, "graders": "b" * 64},
    "digestsMatch": True,
}


def manifest(**overrides):
    built = fm.build_manifest(runtime=RUNTIME, repository=REPOSITORY,
                              catalog=CATALOG, fixture=FIXTURE)
    built.update(overrides)
    return built


class AManifestValidates(unittest.TestCase):
    def test_the_stub_manifest_validates(self):
        self.assertEqual(fm.validate_manifest(manifest()), [])

    def test_every_frozen_field_is_present(self):
        for field in fm.FROZEN_FIELDS:
            with self.subTest(field=field):
                self.assertIn(field, manifest())

    def test_every_preregistered_parameter_is_present(self):
        registered = manifest()["preregistration"]
        for field in fm.PREREGISTERED_FIELDS:
            with self.subTest(field=field):
                self.assertIn(field, registered)
                self.assertTrue(registered[field], f"{field} must not be empty")

    def test_the_real_build_is_also_complete(self):
        """The production path, with its live resolvers, must satisfy the same contract."""
        built = fm.build_manifest(
            runtime=RUNTIME, repository=REPOSITORY, catalog=CATALOG,
        )
        self.assertEqual(fm.validate_manifest(built), [])
        self.assertTrue(built["fixture"]["digestsMatch"], "the shipped fixture must verify")


class IncompletenessIsRejected(unittest.TestCase):
    def test_a_missing_frozen_field_is_reported(self):
        for field in fm.FROZEN_FIELDS:
            with self.subTest(field=field):
                built = manifest()
                del built[field]
                self.assertIn(f"missing:{field}", fm.validate_manifest(built))

    def test_a_missing_preregistration_parameter_is_reported(self):
        for field in fm.PREREGISTERED_FIELDS:
            with self.subTest(field=field):
                built = manifest()
                del built["preregistration"][field]
                self.assertIn(f"missing-preregistration:{field}", fm.validate_manifest(built))

    def test_a_fixture_digest_mismatch_is_reported(self):
        built = manifest(fixture={**FIXTURE, "digestsMatch": False})
        self.assertIn("fixture-digests-do-not-match", fm.validate_manifest(built))

    def test_a_claimed_paid_run_is_reported(self):
        """The objective forbids the paid experiment, so the manifest asserts it did not run."""
        built = manifest(paidRunExecuted=True)
        self.assertIn("paid-run-claimed", fm.validate_manifest(built))

    def test_an_unstated_capability_is_reported(self):
        built = manifest(runtimeVersion={"value": "x"})
        self.assertIn("unstated-capability:runtimeVersion", fm.validate_manifest(built))

    def test_recorded_credential_values_are_reported(self):
        built = manifest()
        built["authReadiness"] = {**built["authReadiness"], "valuesRecorded": True}
        self.assertIn("credential-values-recorded", fm.validate_manifest(built))

    def test_a_missing_required_arm_is_reported(self):
        built = manifest()
        built["arms"] = [arm for arm in built["arms"] if arm["id"] != "V2"]
        self.assertIn("missing-arm:V2", fm.validate_manifest(built))


class NothingIsFabricated(unittest.TestCase):
    def test_an_exposed_field_must_carry_a_value(self):
        with self.assertRaises(fm.ManifestError):
            fm.capability(fm.EXPOSED, None)

    def test_an_unmeasured_field_must_be_null(self):
        with self.assertRaises(fm.ManifestError):
            fm.capability(fm.NOT_MEASURED, 0)

    def test_a_derived_field_must_record_its_basis(self):
        with self.assertRaises(fm.ManifestError):
            fm.capability(fm.DERIVED, "x")

    def test_pricing_is_not_measured_rather_than_copied(self):
        """A copied price would make the frozen comparison a transcription."""
        pricing = manifest()["pricingSnapshot"]
        self.assertEqual(pricing["state"], fm.NOT_MEASURED)
        self.assertIsNone(pricing["value"])
        self.assertIn("run time", pricing["basis"])

    def test_auth_readiness_records_no_value(self):
        auth = manifest()["authReadiness"]
        self.assertFalse(auth["valuesRecorded"])
        self.assertTrue(all(isinstance(v, bool) for v in auth["environmentVariables"].values()))
        self.assertIn("note", auth)


class ThePreRegistrationIsUsable(unittest.TestCase):
    def test_the_primary_metric_declares_its_cost_dimension(self):
        metric = manifest()["preregistration"]["primaryMetric"]
        self.assertEqual(metric["dimension"], "actualMarginalCostUsd")
        self.assertIn("successful", metric["definition"])

    def test_the_margin_and_the_saving_threshold_are_numeric_and_ordered(self):
        registered = manifest()["preregistration"]
        margin = registered["nonInferiorityMargin"]["value"]
        saving = registered["minimumWorthwhileSaving"]["value"]
        self.assertIsInstance(margin, float)
        self.assertIsInstance(saving, float)
        self.assertGreater(saving, 0.0)
        self.assertLess(margin, 1.0)

    def test_the_stopping_rule_spends_alpha_across_the_looks(self):
        rule = manifest()["preregistration"]["stoppingRule"]
        self.assertLess(rule["interimAlpha"], rule["finalAlpha"])
        self.assertIn("stopForBenefit", rule)
        self.assertIn("stopForFutility", rule)

    def test_the_critical_cohorts_are_named(self):
        cohorts = manifest()["preregistration"]["criticalCohorts"]
        self.assertIn("security-sensitive", cohorts)
        self.assertIn("c3-mandatory", cohorts)

    def test_the_trial_count_is_consistent_with_the_arms(self):
        registered = manifest()["preregistration"]["trialCount"]
        self.assertEqual(registered["planned"],
                         registered["tasks"] * registered["trialsPerTaskPerArm"] * registered["arms"])

    def test_the_paired_procedure_is_task_major(self):
        self.assertIn("task-major", manifest()["preregistration"]["pairedProcedure"]["design"])

    def test_the_improvement_conditions_include_the_audit_and_the_cohorts(self):
        conditions = " ".join(manifest()["preregistration"]["improvementConditions"])
        self.assertIn("non-inferiority", conditions)
        self.assertIn("critical cohort", conditions)
        self.assertIn("accounting audit", conditions)


class TheArmsAndTheProtocolAreDefined(unittest.TestCase):
    def test_the_required_arms_are_defined(self):
        ids = [arm["id"] for arm in fm.ARMS]
        for required in ("V0", "V1", "V2", "V3", "V4", "V5", "ORACLE"):
            self.assertIn(required, ids)

    def test_v1_is_named_for_what_it_measures(self):
        """The measured arm is skill-plus-directive; the manifest must not overstate it."""
        v1 = next(arm for arm in fm.ARMS if arm["id"] == "V1")
        self.assertIn("directive", v1["name"])
        self.assertIn("not separable", v1["note"])

    def test_the_oracle_is_marked_as_not_a_policy(self):
        oracle = next(arm for arm in fm.ARMS if arm["id"] == "ORACLE")
        self.assertIn("never as a policy", oracle["note"])

    def test_the_worker_frontier_comes_before_the_router_ablation(self):
        protocol = manifest()["workerFrontierProtocol"]
        self.assertIn("workers first", protocol["order"])
        self.assertTrue(protocol["coordinatorHeldFixed"])

    def test_external_evidence_never_enters_the_candidate_set(self):
        protocol = manifest()["workerFrontierProtocol"]
        self.assertIn("never enter the candidate set", protocol["externalEvidence"])


class TheTimeBandCanInvalidate(unittest.TestCase):
    def test_the_band_states_what_invalidates_it(self):
        band = manifest()["timeBand"]
        self.assertIn("maxAgeDays", band)
        self.assertIn("validUntil", band)
        for trigger in ("runtime version", "catalog digest", "fixture", "commit"):
            self.assertIn(trigger, band["invalidation"])


class NoProviderOrModelNameIsNormative(unittest.TestCase):
    def test_module_source_names_no_current_model(self):
        module = fm
        source_path = module.__file__
        assert source_path is not None
        with open(source_path, encoding="utf-8") as handle:
            source = handle.read().lower()
        for brand in ("gpt", "deepseek", "glm", "luna", "astra", "kimi", "claude", "gemini", "qwen"):
            self.assertNotIn(brand, source, "a current model brand leaked into the manifest tool")


if __name__ == "__main__":
    unittest.main()
