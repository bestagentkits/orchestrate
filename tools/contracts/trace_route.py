"""Reference implementation of the closed `route` trace payload.

The normative schema lives in
`plugins/orchestrate/skills/orchestrate/references/trace-and-logging.md`. That document
owns the payload field set; this module makes the two properties it claims checkable:

- the payload is **schema-closed** - a missing field and an unknown field both fail;
- **no classifier prose** is stored - every string is a bounded token, and the fields whose
  vocabularies have an owner must draw from that owner's closed set.

A trace that validates here reconstructs the whole route decision: hard-gate survivors and
rejects, prunes, evidence scope and sample, quality bound, the three cost dimensions,
reliability, expected recovery and C3 cost, selected effort, expected verified cost, the
runner-up, the margin, and why the semantic router was called or skipped.
"""

from __future__ import annotations

import re

#: Owned by routing-policy.md (Pareto pruning protections).
PRUNE_REASONS = (
    "dominated",
    "not-eligible",
    "capability-floor",
    "risk-floor",
    "quality-floor",
    "budget-floor",
)

#: Owned by benchmark-evidence.md (evidence hierarchy degradation).
EVIDENCE_DEGRADATION = (
    "none",
    "cohort-to-task-class",
    "task-class-to-global",
    "global-to-none",
)

#: Owned by routing-policy.md (deterministic ambiguity gate).
SEMANTIC_REASONS = ("ok", "ambiguous", "margin-below-threshold")

SEMANTIC_SKIPPED_REASONS = (
    "deterministic-winner-uncounterable",
    "no-floor-can-change",
    "budget-exhausted",
    "plane-disabled",
)

#: Owned by metrics-and-self-improvement.md (cost dimensions).
COST_DIMENSIONS = ("actualMarginalCostUsd", "apiEquivalentCostUsd", "quotaBurn")

#: Owned by metrics-and-self-improvement.md (failure classes feeding recovery cost).
RECOVERY_COST_EVIDENCE_CLASSES = ("transport-or-infrastructure",)

COUNTS = (
    "candidateCount",
    "eligibleCount",
    "rankedCount",
    "hardGateSurvivors",
    "hardGateRejects",
    "prunedCount",
    "evidenceSampleSize",
)

NUMBERS_OR_NULL = (
    "qualityBound",
    "actualMarginalCostUsd",
    "apiEquivalentCostUsd",
    "quotaBurn",
    "infrastructureFailureProbability",
    "expectedRecoveryCostUsd",
    "expectedC3CostUsd",
    "expectedVerifiedCostUsd",
    "runnerUpMargin",
    "capabilityFloorDelta",
    "riskFloorDelta",
)

#: Bounded tokens: a provider-local model id is fine, a sentence is not.
TOKENS = (
    "selectedRuntime",
    "selectedProvider",
    "selectedModel",
    "selectedFamily",
    "selectedEffortMode",
    "effortLevel",
    "runnerUpRuntime",
    "runnerUpProvider",
    "runnerUpModel",
    "runnerUpEffortMode",
    "evidenceCohort",
    "evidenceDegradation",
    "qualityEstimator",
    "costDimensionUsed",
    "recoveryCostEvidenceClass",
    "semanticRouterReason",
    "semanticRouterSkippedReason",
    "riskTier",
    "benchmarkDegraded",
)

BOOLEANS = ("semanticRouterCalled",)

REFERENCES = ("benchmarkRef",)

#: Enum members that must come from a specific owner's closed set.
OWNED_ENUMS = {
    "evidenceDegradation": EVIDENCE_DEGRADATION,
    "semanticRouterReason": SEMANTIC_REASONS,
    "semanticRouterSkippedReason": SEMANTIC_SKIPPED_REASONS,
    "costDimensionUsed": COST_DIMENSIONS,
    "recoveryCostEvidenceClass": RECOVERY_COST_EVIDENCE_CLASSES,
}

ENUM_LIST_FIELDS = ("pruneReasons",)

#: The complete field set. A field outside this tuple is a schema violation.
ROUTE_PAYLOAD_FIELDS = (
    COUNTS + NUMBERS_OR_NULL + TOKENS + BOOLEANS + REFERENCES
    + ENUM_LIST_FIELDS + ("hardGateRejectReasons",)
)

#: Bounded tokens: a provider-local model id is fine, a sentence is not. Owned-enum fields are
#: checked here as well as against their owner's set, so prose is reported as prose and not
#: only as a value outside a vocabulary.
_TOKENS = TOKENS

_TOKEN_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,63}$")
_REF_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$")


class TracePayloadError(ValueError):
    """Raised when a payload cannot be validated at all."""


def validate_route_payload(payload: dict) -> list[str]:
    """Every problem with a `route` payload, using stable machine-readable codes."""
    if not isinstance(payload, dict):
        raise TracePayloadError("a route payload must be an object")

    problems: list[str] = []

    for field in ROUTE_PAYLOAD_FIELDS:
        if field not in payload:
            problems.append(f"missing:{field}")

    for field in payload:
        if field not in ROUTE_PAYLOAD_FIELDS:
            problems.append(f"unknown:{field}")

    for field in COUNTS:
        if field in payload and not isinstance(payload[field], int):
            problems.append(f"not-an-integer:{field}")
        elif field in payload and isinstance(payload[field], int) and payload[field] < 0:
            problems.append(f"negative:{field}")

    for field in NUMBERS_OR_NULL:
        if field not in payload:
            continue
        value = payload[field]
        if value is None:
            continue
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            problems.append(f"not-a-number-or-null:{field}")

    for field in BOOLEANS:
        if field in payload and not isinstance(payload[field], bool):
            problems.append(f"not-a-boolean:{field}")

    for field in _TOKENS:
        if field not in payload:
            continue
        value = payload[field]
        if not isinstance(value, str) or not _TOKEN_PATTERN.match(value):
            problems.append(f"not-a-bounded-token:{field}")

    for field in REFERENCES:
        if field not in payload:
            continue
        value = payload[field]
        if not isinstance(value, str) or not _REF_PATTERN.match(value):
            problems.append(f"not-a-reference:{field}")

    for field, allowed in OWNED_ENUMS.items():
        if field not in payload:
            continue
        if payload[field] not in allowed:
            problems.append(f"outside-owned-enum:{field}")

    for field in ENUM_LIST_FIELDS:
        if field not in payload:
            continue
        value = payload[field]
        if not isinstance(value, list):
            problems.append(f"not-a-list:{field}")
            continue
        for item in value:
            if item not in PRUNE_REASONS:
                problems.append(f"outside-owned-enum:{field}")

    if "hardGateRejectReasons" in payload:
        reasons = payload["hardGateRejectReasons"]
        if not isinstance(reasons, list):
            problems.append("not-a-list:hardGateRejectReasons")
        else:
            for item in reasons:
                if not isinstance(item, str) or not _TOKEN_PATTERN.match(item):
                    problems.append("not-a-bounded-token:hardGateRejectReasons")

    return problems


def is_valid_route_payload(payload: dict) -> bool:
    return not validate_route_payload(payload)


def reconstruct(payload: dict) -> dict:
    """Rebuild the route decision a valid trace states.

    Raises rather than guessing: an incomplete trace cannot be reconstructed, and saying so
    is the point. `None` cost dimensions stay `None` - an unmeasurable term is unknown, never
    zero.
    """
    problems = validate_route_payload(payload)
    if problems:
        raise TracePayloadError("; ".join(problems))

    return {
        "hardGate": {
            "survivors": payload["hardGateSurvivors"],
            "rejects": payload["hardGateRejects"],
            "rejectReasons": list(payload["hardGateRejectReasons"]),
        },
        "pruned": {
            "count": payload["prunedCount"],
            "reasons": list(payload["pruneReasons"]),
        },
        "evidence": {
            "cohort": payload["evidenceCohort"],
            "sampleSize": payload["evidenceSampleSize"],
            "degradation": payload["evidenceDegradation"],
        },
        "quality": {
            "bound": payload["qualityBound"],
            "estimator": payload["qualityEstimator"],
        },
        "costDimensions": {
            "actualMarginalCostUsd": payload["actualMarginalCostUsd"],
            "apiEquivalentCostUsd": payload["apiEquivalentCostUsd"],
            "quotaBurn": payload["quotaBurn"],
            "declaredDimension": payload["costDimensionUsed"],
        },
        "reliability": {
            "infrastructureFailureProbability": payload["infrastructureFailureProbability"],
            "recoveryEvidenceClass": payload["recoveryCostEvidenceClass"],
        },
        "expectedCost": {
            "recoveryCostUsd": payload["expectedRecoveryCostUsd"],
            "c3CostUsd": payload["expectedC3CostUsd"],
            "verifiedCostUsd": payload["expectedVerifiedCostUsd"],
        },
        "selected": {
            "runtime": payload["selectedRuntime"],
            "provider": payload["selectedProvider"],
            "model": payload["selectedModel"],
            "family": payload["selectedFamily"],
            "effortMode": payload["selectedEffortMode"],
            "effortLevel": payload["effortLevel"],
        },
        "runnerUp": {
            "runtime": payload["runnerUpRuntime"],
            "provider": payload["runnerUpProvider"],
            "model": payload["runnerUpModel"],
            "effortMode": payload["runnerUpEffortMode"],
            "margin": payload["runnerUpMargin"],
        },
        "semanticRouter": {
            "called": payload["semanticRouterCalled"],
            "reason": payload["semanticRouterReason"],
            "skippedReason": payload["semanticRouterSkippedReason"],
        },
        "ranking": {
            "benchmarkRef": payload["benchmarkRef"],
            "benchmarkDegraded": payload["benchmarkDegraded"],
            "capabilityFloorDelta": payload["capabilityFloorDelta"],
            "riskFloorDelta": payload["riskFloorDelta"],
            "riskTier": payload["riskTier"],
        },
        "counts": {
            "candidates": payload["candidateCount"],
            "eligible": payload["eligibleCount"],
            "ranked": payload["rankedCount"],
        },
    }


def legacy_route_payload_fields() -> tuple:
    """The nine fields the `route` payload carried before this contract.

    Kept as the negative baseline so the completeness fixture can fail: a trace with these
    fields cannot explain pruning, evidence scope, the cost dimensions, reliability, the
    runner-up, the margin or the semantic call, and that is exactly what the goal's trace
    contract forbids.
    """
    return (
        "candidateCount",
        "eligibleCount",
        "rankedCount",
        "benchmarkRef",
        "benchmarkDegraded",
        "capabilityFloorDelta",
        "riskFloorDelta",
        "riskTier",
        "effortLevel",
    )
