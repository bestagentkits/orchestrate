"""Reference implementation of the decision-plane value-of-information gate.

The normative rules live in
`plugins/orchestrate/skills/orchestrate/references/routing-policy.md` under
"Deterministic ambiguity gate", and the call contract in
`references/decision-plane.md` under "Value of information".

The property this module exists to demonstrate is that a probabilistic call is made only
when it can change a permitted decision. The expensive failure mode is a plane that is
consulted on every job regardless, which is a recurring tax that buys nothing whenever the
deterministic answer was already decisive.

The second property is that a skip is a **recorded outcome**, not a missing one: a reviewer
must be able to tell "we did not need it" from "we forgot to ask".
"""

from __future__ import annotations

#: Pinned by routing-policy.md, which owns it.
SEMANTIC_MARGIN_THRESHOLD = 0.15

#: Closed vocabularies. The trace stores enums, never prose.
CALL_REASONS = (
    "close-candidates",
    "ambiguous-classification",
    "floor-could-rise",
    "unclear-requirements",
)
SKIP_REASONS = (
    "deterministic-winner-decisive",
    "no-floor-could-change",
)

TIER_MAX = "C3"
RISK_MAX = "R3"


class VoIError(ValueError):
    """Raised for a gate input that violates the owned contract."""


def candidate_margin(candidates: list[dict]) -> float | None:
    """The relative objective gap between the best and the runner-up.

    ``None`` when the margin cannot be computed, which the gate treats as "not decisive"
    rather than as a wide margin. A single candidate has no runner-up and is treated as
    decisive, because nothing can overtake it deterministically.
    """
    costs = []
    for candidate in candidates:
        value = candidate.get("expectedVerifiedCostUsd")
        if value is None:
            return None
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise VoIError("expectedVerifiedCostUsd must be a number or null")
        costs.append(value)
    if not costs:
        return None
    if len(costs) == 1:
        return 1.0
    ordered = sorted(costs)
    best, runner_up = ordered[0], ordered[1]
    if best <= 0:
        return 0.0
    return (runner_up - best) / best


def floor_could_still_rise(required_tier: str, risk_tier: str, independence_required: bool) -> bool:
    """Whether any semantic signal could legally raise rigor on this job.

    A signal may only raise a floor. So a job already at C3, already at R3, and already
    requiring independent review has nothing left for a probabilistic call to raise, which
    is precisely when the call cannot change a permitted decision.
    """
    return (
        required_tier != TIER_MAX
        or risk_tier != RISK_MAX
        or not independence_required
    )


def decide_semantic_routing(
    candidates: list[dict],
    required_tier: str,
    risk_tier: str,
    independence_required: bool,
    classification_ambiguous: bool = False,
    requirements_clear: bool = True,
) -> dict:
    """Whether to call the semantic router, and the recorded reason either way."""
    margin = candidate_margin(candidates)

    if classification_ambiguous:
        return _call("ambiguous-classification", margin)
    if not requirements_clear:
        return _call("unclear-requirements", margin)
    if floor_could_still_rise(required_tier, risk_tier, independence_required):
        return _call("floor-could-rise", margin)
    if margin is None:
        return _call("close-candidates", margin)
    if margin < SEMANTIC_MARGIN_THRESHOLD:
        return _call("close-candidates", margin)
    return {
        "semanticRouterCalled": False,
        "semanticRouterSkippedReason": "deterministic-winner-decisive",
        "semanticRouterSecondarySkippedReason": "no-floor-could-change",
        "candidateMargin": margin,
    }


def _call(reason: str, margin: float | None) -> dict:
    if reason not in CALL_REASONS:
        raise VoIError(f"unknown call reason {reason!r}")
    return {
        "semanticRouterCalled": True,
        "semanticRouterReason": reason,
        "candidateMargin": margin,
    }


def probe_is_reusable(probe: dict | None, run_id: str, candidate_set_hash: str) -> bool:
    """Whether a classifier probe may be reused instead of re-run.

    Reuse is scoped to the live evidence it was taken from. A different run, a changed
    candidate set, or a probe that is no longer verified invalidates it, and only then is
    re-probing warranted.
    """
    if not probe:
        return False
    return (
        probe.get("runId") == run_id
        and probe.get("candidateSetHash") == candidate_set_hash
        and probe.get("state") == "verified"
    )


def legacy_always_call(candidates: list[dict], **_: object) -> dict:
    """The behaviour this contract replaced: consult the plane on every job.

    Kept as the negative baseline so the fixture guarding against it can fail.
    """
    return {
        "semanticRouterCalled": True,
        "semanticRouterReason": "close-candidates",
        "candidateMargin": candidate_margin(candidates),
    }
