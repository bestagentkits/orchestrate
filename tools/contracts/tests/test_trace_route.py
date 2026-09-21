"""Behavioural tests for the closed `route` trace payload.

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

from tools.contracts.trace_route import (  # noqa: E402
    COST_DIMENSIONS,
    EVIDENCE_DEGRADATION,
    OWNED_ENUMS,
    PRUNE_REASONS,
    ROUTE_PAYLOAD_FIELDS,
    SEMANTIC_REASONS,
    SEMANTIC_SKIPPED_REASONS,
    TracePayloadError,
    is_valid_route_payload,
    legacy_route_payload_fields,
    reconstruct,
    validate_route_payload,
)

VALID = {
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


def payload(**overrides):
    return {**VALID, **overrides}


class ACompletePayloadValidates(unittest.TestCase):
    def test_the_fixture_is_valid(self):
        self.assertEqual(validate_route_payload(VALID), [])
        self.assertTrue(is_valid_route_payload(VALID))

    def test_a_null_cost_dimension_is_allowed(self):
        """An unexposed dimension is unknown, not zero, and must validate as null."""
        self.assertEqual(validate_route_payload(payload(apiEquivalentCostUsd=None)), [])

    def test_every_field_in_the_declaration_is_exercised_by_the_fixture(self):
        self.assertEqual(set(VALID), set(ROUTE_PAYLOAD_FIELDS))

    def test_an_uppercase_risk_tier_is_a_valid_token(self):
        self.assertEqual(validate_route_payload(payload(riskTier="R2")), [])


class ThePayloadIsClosedInBothDirections(unittest.TestCase):
    def test_each_missing_field_is_reported(self):
        for field in ROUTE_PAYLOAD_FIELDS:
            with self.subTest(field=field):
                incomplete = {k: v for k, v in VALID.items() if k != field}
                self.assertIn(f"missing:{field}", validate_route_payload(incomplete))

    def test_an_added_field_is_reported(self):
        self.assertIn("unknown:classifierProse", validate_route_payload(payload(classifierProse="x")))

    def test_an_empty_payload_reports_every_field_missing(self):
        problems = validate_route_payload({})
        self.assertEqual(len(problems), len(ROUTE_PAYLOAD_FIELDS))


class NoClassifierProseIsStored(unittest.TestCase):
    def test_a_sentence_in_a_token_field_is_rejected(self):
        prose = "the model seems likely to succeed here"
        self.assertIn("not-a-bounded-token:semanticRouterReason",
                      validate_route_payload(payload(semanticRouterReason=prose)))

    def test_classifier_wording_is_rejected_even_when_the_enum_would_also_pass(self):
        for field in ("semanticRouterReason", "evidenceCohort", "selectedModel", "riskTier"):
            with self.subTest(field=field):
                self.assertIn(f"not-a-bounded-token:{field}",
                              validate_route_payload(payload(**{field: "two words"})))

    def test_a_long_token_is_rejected(self):
        self.assertIn("not-a-bounded-token:selectedModel",
                      validate_route_payload(payload(selectedModel="m" * 200)))

    def test_reject_reasons_must_be_tokens_too(self):
        self.assertIn("not-a-bounded-token:hardGateRejectReasons",
                      validate_route_payload(payload(hardGateRejectReasons=["because it failed"])))


class EnumsComeFromTheirOwner(unittest.TestCase):
    def test_each_owned_enum_rejects_a_value_from_outside(self):
        for field, allowed in OWNED_ENUMS.items():
            with self.subTest(field=field):
                self.assertIn(f"outside-owned-enum:{field}",
                              validate_route_payload(payload(**{field: "not-in-the-set"})))
                self.assertEqual(validate_route_payload(payload(**{field: allowed[0]})), [])

    def test_prune_reasons_are_closed(self):
        self.assertIn("outside-owned-enum:pruneReasons",
                      validate_route_payload(payload(pruneReasons=["because-i-felt-like-it"])))
        self.assertEqual(validate_route_payload(payload(pruneReasons=list(PRUNE_REASONS))), [])

    def test_the_owned_vocabularies_are_the_declared_ones(self):
        self.assertEqual(PRUNE_REASONS, ("dominated", "not-eligible", "capability-floor",
                                        "risk-floor", "quality-floor", "budget-floor"))
        self.assertEqual(EVIDENCE_DEGRADATION, ("none", "cohort-to-task-class",
                                                "task-class-to-global", "global-to-none"))
        self.assertEqual(SEMANTIC_REASONS, ("ok", "ambiguous", "margin-below-threshold"))
        self.assertEqual(SEMANTIC_SKIPPED_REASONS, ("deterministic-winner-uncounterable",
                                                    "no-floor-can-change", "budget-exhausted",
                                                    "plane-disabled"))
        self.assertEqual(COST_DIMENSIONS, ("actualMarginalCostUsd", "apiEquivalentCostUsd",
                                           "quotaBurn"))


class TypesAreEnforced(unittest.TestCase):
    def test_a_count_must_be_an_integer(self):
        self.assertIn("not-an-integer:candidateCount", validate_route_payload(payload(candidateCount="7")))

    def test_a_negative_count_is_rejected(self):
        self.assertIn("negative:prunedCount", validate_route_payload(payload(prunedCount=-1)))

    def test_a_cost_must_be_a_number_or_null(self):
        self.assertIn("not-a-number-or-null:expectedVerifiedCostUsd",
                      validate_route_payload(payload(expectedVerifiedCostUsd="2.05")))

    def test_a_boolean_field_must_be_a_boolean(self):
        self.assertIn("not-a-boolean:semanticRouterCalled",
                      validate_route_payload(payload(semanticRouterCalled="false")))

    def test_a_zero_cost_is_still_a_number(self):
        """Zero is a legitimate measurement; the rule forbids zero as a stand-in for unknown."""
        self.assertEqual(validate_route_payload(payload(actualMarginalCostUsd=0)), [])


class TheTraceReconstructsTheDecision(unittest.TestCase):
    def test_reconstruction_returns_every_group(self):
        decision = reconstruct(VALID)
        self.assertEqual(set(decision), {
            "hardGate", "pruned", "evidence", "quality", "costDimensions", "reliability",
            "expectedCost", "selected", "runnerUp", "semanticRouter", "ranking", "counts",
        })

    def test_the_hard_gates_are_recoverable(self):
        decision = reconstruct(VALID)
        self.assertEqual(decision["hardGate"]["survivors"], 4)
        self.assertEqual(decision["hardGate"]["rejects"], 3)
        self.assertEqual(decision["hardGate"]["rejectReasons"],
                         ["capability-floor", "risk-floor", "budget-floor"])

    def test_pruning_is_recoverable(self):
        self.assertEqual(reconstruct(VALID)["pruned"], {"count": 1, "reasons": ["dominated"]})

    def test_evidence_scope_and_sample_are_recoverable(self):
        evidence = reconstruct(VALID)["evidence"]
        self.assertEqual(evidence["cohort"], "cohort-a")
        self.assertEqual(evidence["sampleSize"], 120)
        self.assertEqual(evidence["degradation"], "none")

    def test_a_recorded_degradation_survives_reconstruction(self):
        degraded = payload(evidenceDegradation="cohort-to-task-class")
        self.assertEqual(reconstruct(degraded)["evidence"]["degradation"], "cohort-to-task-class")

    def test_the_quality_bound_and_estimator_are_recoverable(self):
        self.assertEqual(reconstruct(VALID)["quality"],
                         {"bound": 0.83, "estimator": "wilson-lower-bound"})

    def test_all_three_cost_dimensions_are_recoverable_and_stay_null(self):
        dimensions = reconstruct(VALID)["costDimensions"]
        self.assertEqual(dimensions["actualMarginalCostUsd"], 1.25)
        self.assertIsNone(dimensions["apiEquivalentCostUsd"],
                          "an unmeasured dimension must not be reconstructed as zero")
        self.assertEqual(dimensions["quotaBurn"], 0.5)
        self.assertEqual(dimensions["declaredDimension"], "actualMarginalCostUsd")

    def test_reliability_is_recoverable_and_names_the_feeding_class(self):
        reliability = reconstruct(VALID)["reliability"]
        self.assertEqual(reliability["infrastructureFailureProbability"], 0.20)
        self.assertEqual(reliability["recoveryEvidenceClass"], "transport-or-infrastructure")

    def test_the_cost_terms_are_recoverable(self):
        self.assertEqual(reconstruct(VALID)["expectedCost"],
                         {"recoveryCostUsd": 0.25, "c3CostUsd": 0.10, "verifiedCostUsd": 2.05})

    def test_the_selected_effort_mode_is_recoverable(self):
        selected = reconstruct(VALID)["selected"]
        self.assertEqual(selected["effortMode"], "high")
        self.assertEqual(selected["model"], "model-a")

    def test_the_runner_up_and_margin_are_recoverable(self):
        runner = reconstruct(VALID)["runnerUp"]
        self.assertEqual(runner["model"], "model-b")
        self.assertEqual(runner["margin"], 0.14)

    def test_the_semantic_call_or_skip_reason_is_recoverable(self):
        for called, reason, skipped in (
            (False, "ok", "no-floor-can-change"),
            (True, "ambiguous", "deterministic-winner-uncounterable"),
        ):
            with self.subTest(called=called):
                semantic = reconstruct(payload(
                    semanticRouterCalled=called,
                    semanticRouterReason=reason,
                    semanticRouterSkippedReason=skipped,
                ))["semanticRouter"]
                self.assertEqual(semantic["called"], called)
                self.assertEqual(semantic["reason"], reason)
                self.assertEqual(semantic["skippedReason"], skipped)

    def test_reconstruction_refuses_an_incomplete_trace(self):
        incomplete = {k: v for k, v in VALID.items() if k != "pruneReasons"}
        with self.assertRaises(TracePayloadError):
            reconstruct(incomplete)

    def test_reconstruction_does_not_guess_a_missing_value(self):
        """Saying a trace is incomplete is the point; filling the gap would be fabrication."""
        incomplete = {k: v for k, v in VALID.items() if k != "expectedVerifiedCostUsd"}
        try:
            reconstruct(incomplete)
            self.fail("an incomplete trace must not reconstruct")
        except TracePayloadError as error:
            self.assertIn("missing:expectedVerifiedCostUsd", str(error))


class TheNegativeFixtureShowsWhatTheOldPayloadCouldNotExplain(unittest.TestCase):
    def test_the_nine_field_payload_fails_completeness(self):
        legacy = {field: VALID[field] for field in legacy_route_payload_fields() if field in VALID}
        problems = validate_route_payload(legacy)
        self.assertTrue(problems, "baseline: the old payload must be able to fail")

    def test_the_fields_the_old_payload_could_not_explain_are_named(self):
        legacy = {field: VALID[field] for field in legacy_route_payload_fields() if field in VALID}
        problems = set(validate_route_payload(legacy))
        for field in ("pruneReasons", "evidenceSampleSize", "evidenceDegradation",
                      "expectedVerifiedCostUsd", "runnerUpMargin", "semanticRouterReason",
                      "actualMarginalCostUsd"):
            self.assertIn(f"missing:{field}", problems,
                          f"the old payload could not explain {field}")

    def test_the_old_payload_cannot_be_reconstructed(self):
        legacy = {field: VALID[field] for field in legacy_route_payload_fields() if field in VALID}
        with self.assertRaises(TracePayloadError):
            reconstruct(legacy)


class NoProviderOrModelNameIsNormative(unittest.TestCase):
    def test_module_source_names_no_current_model(self):
        import tools.contracts.trace_route as module

        source_path = module.__file__
        assert source_path is not None
        with open(source_path, encoding="utf-8") as handle:
            source = handle.read().lower()
        for brand in ("gpt", "deepseek", "glm", "luna", "astra", "kimi", "claude", "gemini", "qwen"):
            self.assertNotIn(brand, source, "a current model brand leaked into the trace schema")


if __name__ == "__main__":
    unittest.main()
