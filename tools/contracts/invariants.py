"""Negative fixtures for the fifteen regressions issue #15 requires to be testable.

Each fixture pairs the **contract behaviour** with the **broken behaviour** it replaced and
states the invariant as a predicate. A fixture only counts as evidence when it holds on the
contract and fails on the broken behaviour, which is what the test module asserts; a fixture
that can never fail proves nothing.

The invariants are behavioural: they call the owned implementation and the retired rule on
the same scenario and compare the verdict. Only the first fixture is a scan, because a
hardcoded normative default is a property of text rather than of a code path.

The normative owners are the reference documents under
`plugins/orchestrate/skills/orchestrate/references/`; the constants and rules live there and
are not restated here.
"""

from __future__ import annotations

import pathlib
import re

from tools.contracts import (
    calibration,
    cost_dimensions,
    micro_arbiter,
    pareto,
    quality,
    reliability,
    route_identity,
    routing,
    trace_route,
    voi_gate,
)

SKILL_DIR = pathlib.Path(__file__).resolve().parents[2] / "plugins" / "orchestrate" / "skills" / "orchestrate"

#: A brand token followed by a version-ish digit. This is the shape of a pasted model name,
#: and it is deliberately narrower than the bare brand word: the repository may discuss a
#: harness generically, but no normative default may name a current model.
MODEL_NAME_SHAPE = re.compile(
    r"\b(?:gpt|glm|deepseek|kimi|qwen|gemini|claude|mistral|llama|luna|astra|opus|sonnet|haiku)"
    r"[-\s]?v?\d",
    re.IGNORECASE,
)


def scan_normative_model_defaults(text: str) -> list[str]:
    """Every model-name-shaped token in a normative payload."""
    return [match.group(0) for match in MODEL_NAME_SHAPE.finditer(text)]


def normative_text() -> str:
    """The whole normative payload, read from disk rather than transcribed."""
    parts = []
    for path in sorted(SKILL_DIR.rglob("*.md")):
        parts.append(path.read_text(encoding="utf-8"))
    return "\n".join(parts)


# --- scenarios ---------------------------------------------------------------------------

SIGNALS = (
    "artifact_matches_expected_output",
    "claims_supported_by_evidence",
    "materially_unresolved",
)

ROUTE_PAYLOAD = {
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

EFFORT_ALIAS_RECORDS = [
    {"runtime": "pi", "provider": "provider-a", "model": "model-a", "family": "family-a",
     "effortMode": "high", "effortLevel": "high", "sampleSize": 10},
    {"runtime": "pi", "provider": "provider-a", "model": "model-a", "family": "family-a",
     "effortMode": "high", "effortLevel": "detailed", "sampleSize": 5},
]

CLOSE_CANDIDATES = [{"expectedVerifiedCostUsd": 1.0}, {"expectedVerifiedCostUsd": 5.0}]

HARD_GATE_SCENARIO = [
    {"name": "expensive-c2", "capabilityTier": "C2", "qualityLowerBound": 0.90,
     "expectedVerifiedCostUsd": 5.0},
    {"name": "cheap-c1", "capabilityTier": "C1", "qualityLowerBound": 0.90,
     "expectedVerifiedCostUsd": 1.0},
]

DOMINATED_AND_PROTECTED = [
    {"name": "dominator", "qualityLowerBound": 0.90, "reliability": 0.90,
     "expectedVerifiedCostUsd": 1.0, "durationSeconds": 100.0, "expectedRecoveryCostUsd": 0.10,
     "accountingMode": "api-equivalent", "cohort": "cohort-x"},
    {"name": "independent-reviewer", "qualityLowerBound": 0.80, "reliability": 0.80,
     "expectedVerifiedCostUsd": 2.0, "durationSeconds": 200.0, "expectedRecoveryCostUsd": 0.20,
     "accountingMode": "api-equivalent", "cohort": "cohort-x", "independentFamily": True},
]

CALIBRATION_IDENTITY = {
    "classifierProvider": "provider-a",
    "classifierModelId": "classifier-b",
    "classifierVersion": "2.0.0",
    "decisionSchemaHash": "schema-a",
    "promptContractHash": "prompt-a",
    "signalSetHash": "signals-a",
    "thresholdPolicy": "threshold-a",
}

STALE_CALIBRATION_RECORD = {
    **CALIBRATION_IDENTITY,
    "classifierModelId": "classifier-a",
    "sampleCount": 50,
    "minimum": 30,
    "agreement": 0.99,
    "threshold": 0.95,
    "signals": list(SIGNALS),
    "expiresAt": "2026-10-01T00:00:00Z",
}

NOW = "2026-09-21T00:00:00Z"


def _calibration_is_reusable(record) -> bool:
    return bool(calibration.validity(
        record, CALIBRATION_IDENTITY, NOW,
        minimum_samples=30, agreement_floor=0.95, initial_threshold=0.90,
        full_signal_set=SIGNALS,
    )["reusable"])


def _budget_verdict(budget) -> str:
    try:
        cost_dimensions.assert_budget_declares_dimension(budget)
    except cost_dimensions.CostError:
        return "refused"
    return "accepted"


def _selected_name(candidates: list[dict], required_tier: str, floor: float) -> str:
    """The selected route's name, or ``none`` when nothing clears.

    ``select_route`` returns ``None`` to mean blocked rather than resolving by weakening a
    floor, so the fixture keeps that as a distinct outcome instead of subsisting.
    """
    selected = routing.select_route(candidates, required_tier, floor)
    return selected["name"] if selected else "none"


def _naive_cash_with_quota(record) -> float:
    return (record.get("actualMarginalCostUsd") or 0.0) + (record.get("quotaBurn") or 0.0)


def _naive_cost_ranking(candidates) -> str:
    """The regression: rank by cost across every candidate, gate or no gate."""
    return min(candidates, key=lambda c: c["expectedVerifiedCostUsd"])["name"]


def _legacy_every_failure_promotes(kind: str) -> bool:
    """The regression: every failure class treated as a promotion candidate."""
    return True


def _legacy_bare_quality_score(records) -> dict:
    """The regression: return a score without the scope and degradation that qualify it."""
    best = max(records, key=lambda r: r["qualityLowerBound"])
    return {"qualityLowerBound": best["qualityLowerBound"]}


def _legacy_nine_field_payload() -> dict:
    return {field: ROUTE_PAYLOAD[field] for field in trace_route.legacy_route_payload_fields()}


# --- the fifteen fixtures -----------------------------------------------------------------

REGRESSIONS = (
    {
        "id": "R01",
        "name": "A provider or model name introduced as a normative default",
        "owner": "the whole normative payload",
        "contract": lambda: scan_normative_model_defaults(normative_text()),
        "broken": lambda: scan_normative_model_defaults(
            "the deterministic default is gpt-6-astra unless overridden"),
        "holds": lambda result: result == [],
    },
    {
        "id": "R02",
        "name": "A missing cost interpreted as zero",
        "owner": "metrics-and-self-improvement.md",
        "contract": lambda: cost_dimensions.total_cash(
            {"actualMarginalCostUsd": 1.0, "apiEquivalentCostUsd": None, "quotaBurn": 0.5}),
        "broken": lambda: _naive_cash_with_quota(
            {"actualMarginalCostUsd": 1.0, "apiEquivalentCostUsd": None, "quotaBurn": 0.5}),
        "holds": lambda result: result is None,
    },
    {
        "id": "R03",
        "name": "Two normalized effort labels reaching one real mode become two candidates",
        "owner": "benchmark-evidence.md",
        "contract": lambda: route_identity.distinct_identity_count(EFFORT_ALIAS_RECORDS),
        "broken": lambda: len(EFFORT_ALIAS_RECORDS),
        "holds": lambda result: result == 1,
    },
    {
        "id": "R04",
        "name": "A low-sample perfect rate outranks a statistically stronger candidate",
        "owner": "benchmark-evidence.md",
        "contract": lambda: quality.rank_records(
            [quality.quality_record(3, 3), quality.quality_record(300, 320)])[0]["sampleSize"],
        "broken": lambda: quality.legacy_raw_rate_order(
            [quality.quality_record(3, 3), quality.quality_record(300, 320)])[0]["sampleSize"],
        "holds": lambda result: result == 320,
    },
    {
        "id": "R05",
        "name": "Semantic routing called despite a decisive deterministic winner",
        "owner": "routing-policy.md",
        "contract": lambda: voi_gate.decide_semantic_routing(
            CLOSE_CANDIDATES, "C3", "R3", True)["semanticRouterCalled"],
        "broken": lambda: voi_gate.legacy_always_call(CLOSE_CANDIDATES)["semanticRouterCalled"],
        "holds": lambda result: not result,
    },
    {
        "id": "R06",
        "name": "Micro-arbiter called on a structurally C3-mandatory path",
        "owner": "verification.md",
        "contract": lambda: micro_arbiter.decide_verification_path(
            {"task": "security"}, {}, calibration_valid=False)["path"],
        "broken": lambda: micro_arbiter.legacy_call_always({"task": "security"}, {})["path"],
        "holds": lambda result: result == "direct-c3",
    },
    {
        "id": "R07",
        "name": "Stale or incompatible calibration reused",
        "owner": "verification.md",
        "contract": lambda: _calibration_is_reusable(STALE_CALIBRATION_RECORD),
        "broken": lambda: calibration.legacy_validity_trusting_the_record(STALE_CALIBRATION_RECORD, NOW),
        "holds": lambda result: not result,
    },
    {
        "id": "R08",
        "name": "Cost-aware ranking restores a hard-filtered candidate",
        "owner": "routing-policy.md",
        "contract": lambda: _selected_name(
            [c for c in HARD_GATE_SCENARIO if routing.clears_capability(c, "C2")], "C2", 0.5),
        "broken": lambda: _naive_cost_ranking(HARD_GATE_SCENARIO),
        "holds": lambda result: result == "expensive-c2",
    },
    {
        "id": "R09",
        "name": "Pareto pruning removes a required independent-review route",
        "owner": "routing-policy.md",
        "contract": lambda: [c["name"] for c in pareto.prune(
            DOMINATED_AND_PROTECTED, {"requiresIndependence": True})[0]],
        "broken": lambda: [c["name"] for c in pareto.legacy_prune_without_protections(
            DOMINATED_AND_PROTECTED)],
        "holds": lambda result: "independent-reviewer" in result,
    },
    {
        "id": "R10",
        "name": "Quota burn compared with API cash as though both were dollars",
        "owner": "metrics-and-self-improvement.md",
        "contract": lambda: cost_dimensions.total_cash(
            {"actualMarginalCostUsd": 1.0, "apiEquivalentCostUsd": 2.0, "quotaBurn": 10.0}),
        "broken": lambda: _naive_cash_with_quota(
            {"actualMarginalCostUsd": 1.0, "apiEquivalentCostUsd": 2.0, "quotaBurn": 10.0})
            + 2.0,
        "holds": lambda result: result == 3.0,
    },
    {
        "id": "R11",
        "name": "A budget or objective that does not state its cost dimension",
        "owner": "metrics-and-self-improvement.md",
        "contract": lambda: _budget_verdict({"limit": 20}),
        "broken": lambda: "accepted" if {"limit": 20}.get("limit") is not None else "refused",
        "holds": lambda result: result == "refused",
    },
    {
        "id": "R12",
        "name": "A content failure feeding recovery cost or a promotion loop",
        "owner": "metrics-and-self-improvement.md",
        "contract": lambda: (
            reliability.recovery_cost_evidence(["content"] * 3)["usable"],
            reliability.may_promote("content"),
        ),
        "broken": lambda: (
            reliability.legacy_recovery_evidence_count(["content"] * 3) > 0,
            True,
        ),
        "holds": lambda result: result == (False, False),
    },
    {
        "id": "R13",
        "name": "A permission or sandbox hard stop turned into a promotion",
        "owner": "fallback-policy.md",
        "contract": lambda: reliability.may_promote("permission"),
        "broken": lambda: _legacy_every_failure_promotes("permission"),
        "holds": lambda result: not result,
    },
    {
        "id": "R14",
        "name": "The route trace missing a field or carrying classifier prose",
        "owner": "trace-and-logging.md",
        "contract": lambda: trace_route.validate_route_payload(ROUTE_PAYLOAD),
        "broken": lambda: trace_route.validate_route_payload(_legacy_nine_field_payload()),
        "holds": lambda result: result == [],
    },
    {
        "id": "R15",
        "name": "Quality evidence used without recording its scope or degradation",
        "owner": "benchmark-evidence.md",
        "contract": lambda: quality.resolve_evidence(
            [{"cohort": None, "taskClass": None, "successes": 90, "sampleSize": 100,
              "rawSuccessRate": 0.90, "qualityLowerBound": 0.82}], "cohort-x", "class-y"),
        "broken": lambda: _legacy_bare_quality_score(
            [{"qualityLowerBound": 0.82}]),
        "holds": lambda result: result.get("scope") is not None
                              and bool(result.get("degraded")),
    },
)

REGRESSION_COUNT = 15


def run_all() -> list[dict]:
    """Evaluate every fixture against its contract and its broken behaviour."""
    results = []
    for regression in REGRESSIONS:
        contract_result = regression["contract"]()
        broken_result = regression["broken"]()
        results.append({
            "id": regression["id"],
            "name": regression["name"],
            "owner": regression["owner"],
            "contract_holds": bool(regression["holds"](contract_result)),
            "broken_fails": not bool(regression["holds"](broken_result)),
        })
    return results
