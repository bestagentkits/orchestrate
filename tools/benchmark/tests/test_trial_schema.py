"""Behavioural tests for the full per-trial field set and its capability metadata.

Run from the repository root:

    PYTHONPYCACHEPREFIX=/tmp/pyc python3 -m unittest discover -s tools -t . -v

The cache prefix is required for any run that exercises mutated code; see instrument
defect ID-1 in `plans/260921-0805-issue15-contract-reconciliation/instrument-defects.md`.
"""

from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from tools.benchmark import trial_schema as ts  # noqa: E402

ROUTE_TRACE = {
    "candidateCount": 7,
    "eligibleCount": 4,
    "rankedCount": 3,
    "hardGateSurvivors": 4,
    "hardGateRejects": 3,
    "hardGateRejectReasons": ["capability-floor", "risk-floor", "budget-floor"],
    "prunedCount": 1,
    "pruneReasons": ["dominated"],
    "evidenceCohort": "cohort-a",
    "evidenceSampleSize": 120,
    "evidenceDegradation": "none",
    "qualityBound": 0.83,
    "qualityEstimator": "wilson-lower-bound",
    "actualMarginalCostUsd": 1.25,
    "apiEquivalentCostUsd": None,
    "quotaBurn": 0.5,
    "costDimensionUsed": "actualMarginalCostUsd",
    "infrastructureFailureProbability": 0.20,
    "recoveryCostEvidenceClass": "transport-or-infrastructure",
    "expectedRecoveryCostUsd": 0.25,
    "expectedC3CostUsd": 0.10,
    "expectedVerifiedCostUsd": 2.05,
    "selectedRuntime": "pi",
    "selectedProvider": "provider-a",
    "selectedModel": "model-a",
    "selectedFamily": "family-a",
    "selectedEffortMode": "high",
    "effortLevel": "high",
    "runnerUpRuntime": "pi",
    "runnerUpProvider": "provider-a",
    "runnerUpModel": "model-b",
    "runnerUpEffortMode": "medium",
    "runnerUpMargin": 0.14,
    "semanticRouterCalled": False,
    "semanticRouterReason": "ok",
    "semanticRouterSkippedReason": "no-floor-can-change",
    "benchmarkRef": "cohort-a/2026-09-21",
    "benchmarkDegraded": "none",
    "capabilityFloorDelta": 0.0,
    "riskFloorDelta": 0.0,
    "riskTier": "R1",
}

CORE = {
    "variant": "orchestrate",
    "taskId": "task-01",
    "cohort": "cohort-a",
    "type": "fix",
    "trial": 1,
    "status": "ok",
    "success": True,
    "durationSeconds": 123.4,
    "requestedProvider": "provider-a",
    "requestedModel": "model-a",
    "requestedEffort": "high",
    "resolvedProvider": "provider-a",
    "resolvedModel": "model-a",
    "resolvedEffort": "high",
    "failureClass": None,
    "deterministicVerificationResult": "pass",
}

MODEL_COSTS = {"provider-a/model-a": 1.0, "provider-b/model-b": 0.25}
ROLES = {"provider-a/model-a": "coordinator", "provider-b/model-b": "classifier"}


def capabilities(**overrides):
    entries = {
        "cacheReadTokens": ts.capability(ts.EXPOSED, 1200),
        "cacheWriteTokens": ts.capability(ts.EXPOSED, 300),
        "reasoningTokens": ts.capability(ts.NOT_EXPOSED),
        "actualMarginalCostUsd": ts.capability(ts.EXPOSED, 1.25),
        "apiEquivalentCostUsd": ts.capability(ts.EXPOSED, 1.30),
        "quotaBurn": ts.capability(ts.NOT_EXPOSED),
        "rateLimitRemaining": ts.capability(ts.NOT_MEASURED),
        "modelFamily": ts.capability(ts.DERIVED, "model", basis="leading-alphabetic-token:model-a"),
        "catalogHash": ts.capability(ts.DERIVED, "abc123", basis="sha256 over observed resolved models"),
        "runtimeVersion": ts.capability(ts.EXPOSED, "1.2.3"),
        "retries": ts.capability(ts.NOT_MEASURED),
        "promotions": ts.capability(ts.NOT_MEASURED),
        "c3Required": ts.capability(ts.EXPOSED, False),
        "c3Reason": ts.capability(ts.NOT_EXPOSED),
    }
    entries.update(overrides)
    return entries


def full_record(**overrides):
    record = ts.build_trial_record(
        CORE, capabilities(), MODEL_COSTS, ROLES,
        route_decision=ROUTE_TRACE, evidence_scope="exact-cohort",
    )
    record.update(overrides)
    return record


class ACompleteTrialValidates(unittest.TestCase):
    def test_the_fixture_validates(self):
        self.assertEqual(ts.validate_trial_record(full_record()), [])
        self.assertTrue(ts.is_valid_trial_record(full_record()))

    def test_the_fixture_exercises_every_declared_field(self):
        self.assertEqual(set(full_record()), set(ts.REQUIRED_FIELDS))

    def test_requested_and_resolved_are_both_recorded_and_may_differ(self):
        record = ts.build_trial_record(
            {**CORE, "resolvedModel": "model-b", "resolvedProvider": "provider-b"},
            capabilities(), MODEL_COSTS, ROLES,
        )
        self.assertEqual(record["requestedModel"], "model-a")
        self.assertEqual(record["resolvedModel"], "model-b")
        self.assertEqual(ts.validate_trial_record(record), [])

    def test_the_component_split_sums_to_the_total(self):
        record = full_record()
        parts = [record[c] for c in ("coordinatorCostUsd", "workerCostUsd",
                                    "classifierCostUsd", "arbiterCostUsd")]
        self.assertAlmostEqual(sum(parts), record["totalCostUsd"], places=6)

    def test_the_roles_are_honoured_and_unassigned_models_become_workers(self):
        split = ts.component_split({}, ROLES, MODEL_COSTS)
        self.assertEqual(split["coordinatorCostUsd"], 1.0)
        self.assertEqual(split["classifierCostUsd"], 0.25)
        self.assertEqual(split["workerCostUsd"], 0.0)
        unassigned = ts.component_split({}, {}, {"provider-a/model-a": 1.0})
        self.assertEqual(unassigned["workerCostUsd"], 1.0)


class ThePayloadIsClosed(unittest.TestCase):
    def test_each_missing_field_is_reported(self):
        for field in ts.REQUIRED_FIELDS:
            with self.subTest(field=field):
                record = full_record()
                del record[field]
                self.assertIn(f"missing:{field}", ts.validate_trial_record(record))

    def test_an_added_field_is_reported(self):
        self.assertIn("unknown:costUsd", ts.validate_trial_record(full_record(costUsd=1.0)))


class NothingIsFabricated(unittest.TestCase):
    def test_a_gated_field_without_a_capability_state_is_reported(self):
        record = full_record()
        del record["capability"]["quotaBurn"]
        self.assertIn("missing-capability-state:quotaBurn", ts.validate_trial_record(record))

    def test_a_value_present_while_the_provider_does_not_expose_it_is_reported(self):
        """A zero where the provider reports nothing is the fabrication the rule forbids."""
        record = full_record(quotaBurn=0.0)
        self.assertIn("fabricated-value:quotaBurn", ts.validate_trial_record(record))

    def test_an_exposed_field_may_not_be_null(self):
        record = full_record(cacheReadTokens=None)
        self.assertIn("exposed-but-null:cacheReadTokens", ts.validate_trial_record(record))

    def test_a_derived_field_must_record_its_basis(self):
        record = full_record()
        record["capability"]["modelFamily"] = {"state": ts.DERIVED}
        self.assertIn("derived-without-basis:modelFamily", ts.validate_trial_record(record))

    def test_the_builder_refuses_to_construct_a_fabricated_entry(self):
        with self.assertRaises(ts.TrialSchemaError):
            ts.capability(ts.NOT_EXPOSED, 0.0)
        with self.assertRaises(ts.TrialSchemaError):
            ts.capability(ts.EXPOSED, None)
        with self.assertRaises(ts.TrialSchemaError):
            ts.capability(ts.DERIVED, "x")

    def test_an_unknown_capability_state_is_refused(self):
        with self.assertRaises(ts.TrialSchemaError):
            ts.capability("maybe", 1.0)

    def test_an_unmeasured_count_is_null_rather_than_zero(self):
        record = full_record()
        self.assertIsNone(record["retries"])
        self.assertIsNone(record["promotions"])
        self.assertEqual(record["capability"]["retries"]["state"], ts.NOT_MEASURED)


class TheModelFamilyDerivationIsStated(unittest.TestCase):
    def test_a_model_id_yields_a_derived_family_with_its_basis(self):
        entry = ts.derive_model_family("model-a")
        self.assertEqual(entry["state"], ts.DERIVED)
        self.assertEqual(entry["value"], "model")
        self.assertIn("model-a", entry["basis"])

    def test_a_missing_model_id_is_not_exposed_rather_than_guessed(self):
        self.assertEqual(ts.derive_model_family(None)["state"], ts.NOT_EXPOSED)
        self.assertEqual(ts.derive_model_family("")["state"], ts.NOT_EXPOSED)


class ReliabilityAndVerification(unittest.TestCase):
    def test_a_failure_class_outside_the_owned_taxonomy_is_reported(self):
        record = full_record(failureClass="flaky")
        self.assertIn("unknown-failure-class:flaky", ts.validate_trial_record(record))

    def test_an_owned_failure_class_is_accepted(self):
        record = full_record(status="timeout", failureClass="infrastructure")
        self.assertEqual(ts.validate_trial_record(record), [])

    def test_a_c3_requirement_must_carry_its_reason(self):
        record = ts.build_trial_record(
            CORE,
            capabilities(c3Required=ts.capability(ts.EXPOSED, True),
                         c3Reason=ts.capability(ts.NOT_EXPOSED)),
            MODEL_COSTS, ROLES,
        )
        self.assertIn("c3-required-without-a-reason", ts.validate_trial_record(record))

    def test_a_c3_requirement_with_a_reason_is_accepted(self):
        record = ts.build_trial_record(
            CORE,
            capabilities(c3Required=ts.capability(ts.EXPOSED, True),
                         c3Reason=ts.capability(ts.EXPOSED, "security-sensitive")),
            MODEL_COSTS, ROLES,
        )
        self.assertEqual(ts.validate_trial_record(record), [])

    def test_a_reason_without_a_requirement_is_reported(self):
        record = ts.build_trial_record(
            CORE,
            capabilities(c3Required=ts.capability(ts.EXPOSED, False),
                         c3Reason=ts.capability(ts.EXPOSED, "security-sensitive")),
            MODEL_COSTS, ROLES,
        )
        self.assertIn("c3-reason-without-a-requirement", ts.validate_trial_record(record))

    def test_an_unobserved_c3_decision_stays_null_rather_than_false(self):
        record = ts.build_trial_record(
            CORE,
            capabilities(c3Required=ts.capability(ts.NOT_MEASURED),
                         c3Reason=ts.capability(ts.NOT_MEASURED)),
            MODEL_COSTS, ROLES,
        )
        self.assertIsNone(record["c3Required"])
        self.assertIsNone(record["c3Reason"])
        self.assertEqual(ts.validate_trial_record(record), [])


class TheAccountingIsCheckedHereToo(unittest.TestCase):
    def test_components_that_do_not_sum_to_the_total_are_reported(self):
        record = full_record(totalCostUsd=99.0)
        self.assertIn("components-do-not-sum-to-total", ts.validate_trial_record(record))

    def test_a_negative_component_is_reported(self):
        record = full_record(coordinatorCostUsd=-1.0)
        self.assertIn("components-do-not-sum-to-total", ts.validate_trial_record(record))

    def test_a_non_numeric_total_is_reported(self):
        self.assertIn("not-a-number:totalCostUsd", ts.validate_trial_record(full_record(totalCostUsd="1.25")))


class TheRouteTraceIsValidatedByItsOwner(unittest.TestCase):
    def test_an_invalid_route_trace_is_reported_through_the_trace_owner(self):
        problems = ts.validate_trial_record(full_record(routeDecisionTrace={"candidateCount": 1}))
        self.assertTrue(any(p.startswith("route-trace:missing:") for p in problems))

    def test_a_valid_route_trace_is_accepted(self):
        self.assertEqual(ts.validate_trial_record(full_record()), [])

    def test_an_absent_route_trace_is_allowed_and_stays_null(self):
        record = ts.build_trial_record(CORE, capabilities(), MODEL_COSTS, ROLES)
        self.assertIsNone(record["routeDecisionTrace"])
        self.assertEqual(ts.validate_trial_record(record), [])


class TheNegativeFixtureShowsWhatTheOldRecordCouldNotSay(unittest.TestCase):
    def test_the_previous_field_set_fails_completeness(self):
        legacy = {field: full_record().get(field) for field in ts.legacy_trial_fields()}
        problems = ts.validate_trial_record(legacy)
        self.assertTrue(problems, "baseline: the previous record must be able to fail")

    def test_the_fields_the_old_record_could_not_name_are_reported(self):
        legacy = {field: full_record().get(field) for field in ts.legacy_trial_fields()}
        problems = set(ts.validate_trial_record(legacy))
        for field in ("resolvedModel", "resolvedEffort", "coordinatorCostUsd", "workerCostUsd",
                      "classifierCostUsd", "arbiterCostUsd", "failureClass", "c3Required",
                      "routeDecisionTrace", "evidenceScope", "capability"):
            self.assertIn(f"missing:{field}", problems,
                          f"the previous record could not name {field}")


class NoProviderOrModelNameIsNormative(unittest.TestCase):
    def test_module_source_names_no_current_model(self):
        import tools.benchmark.trial_schema as module

        source_path = module.__file__
        assert source_path is not None
        with open(source_path, encoding="utf-8") as handle:
            source = handle.read().lower()
        for brand in ("gpt", "deepseek", "glm", "luna", "astra", "kimi", "claude", "gemini", "qwen"):
            self.assertNotIn(brand, source, "a current model brand leaked into the trial schema")


if __name__ == "__main__":
    unittest.main()
