"""Reference implementation of the expected-verified-cost objective.

The normative rules live in
`plugins/orchestrate/skills/orchestrate/references/routing-policy.md` under
"Expected verified cost".

The property that matters most is the treatment of the unknown. A cost term that was not
measured must make the objective unknown, because a zero is a *measurement* of zero and an
unmeasured route that scores zero wins every comparison on price while being, in fact,
unmeasured. The mirror property matters too: an unavailable probability must use a
conservative default rather than zero, or the expected cost of an unreliable route
collapses to the cost of a reliable one.
"""

from __future__ import annotations

#: Pinned by routing-policy.md, which owns them.
CONSERVATIVE_INFRASTRUCTURE_FAILURE_PROBABILITY = 0.20
CONSERVATIVE_CONTENT_FAILURE_PROBABILITY = 0.20
CONSERVATIVE_C3_REQUIRED_PROBABILITY = 1.00

#: Cost terms. Each is denominated in a cost dimension owned elsewhere.
COST_TERMS = (
    "routingOverhead",
    "workerCost",
    "verificationCost",
    "expectedRecoveryCost",
    "expectedEscalationCost",
    "expectedArbiterCost",
)

#: Probability terms, with the conservative default applied when unmeasured.
PROBABILITY_DEFAULTS = {
    "infrastructureFailureProbability": CONSERVATIVE_INFRASTRUCTURE_FAILURE_PROBABILITY,
    "contentFailureProbability": CONSERVATIVE_CONTENT_FAILURE_PROBABILITY,
    "c3RequiredProbability": CONSERVATIVE_C3_REQUIRED_PROBABILITY,
}


class ExpectedCostError(ValueError):
    """Raised for an objective input that violates the owned contract."""


def _cost_term(route: dict, name: str):
    """A cost term, or ``None`` when it was not measured.

    ``None`` propagates: it is not coerced to zero anywhere in this module.
    """
    value = route.get(name)
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ExpectedCostError(f"{name} must be a number or null, got {type(value).__name__}")
    if value < 0:
        raise ExpectedCostError(f"{name} must not be negative")
    return value


def probability_term(route: dict, name: str) -> tuple[int | float, bool]:
    """A probability and whether it came from a conservative default.

    Returns the value and a flag, so a caller can record that a substitution happened
    rather than presenting a default as a measurement.
    """
    default = PROBABILITY_DEFAULTS[name]
    value = route.get(name)
    if value is None:
        return default, True
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ExpectedCostError(f"{name} must be a probability or null")
    if not 0.0 <= value <= 1.0:
        raise ExpectedCostError(f"{name} must lie within [0, 1]")
    return value, False


def expected_verified_cost(route: dict) -> float | None:
    """The objective, or ``None`` when any cost term is unmeasured.

    Never returns a number built from a missing cost. A test asserts that an incomplete
    route scores ``None`` rather than a cheaper-than-everything figure.
    """
    terms = []
    for name in COST_TERMS:
        value = _cost_term(route, name)
        if value is None:
            return None
        terms.append(value)

    infrastructure, _ = probability_term(route, "infrastructureFailureProbability")
    content, _ = probability_term(route, "contentFailureProbability")
    c3, _ = probability_term(route, "c3RequiredProbability")

    routing, worker, verification, recovery, escalation, arbiter = terms
    return (
        routing
        + worker
        + verification
        + infrastructure * recovery
        + content * escalation
        + c3 * arbiter
    )


def conservative_substitutions(route: dict) -> list[str]:
    """Which probability terms fell back to a conservative default, for the trace."""
    return [name for name in PROBABILITY_DEFAULTS if route.get(name) is None]


def compare_expected_cost(left: dict, right: dict) -> int | None:
    """Compare two routes on the objective.

    ``None`` when either objective is unknown: an unknown can neither win nor lose a cost
    comparison, so it never becomes the cheapest by default.
    """
    a = expected_verified_cost(left)
    b = expected_verified_cost(right)
    if a is None or b is None:
        return None
    return (a > b) - (a < b)


def legacy_expected_cost_treating_unknown_as_zero(route: dict) -> int | float:
    """The behaviour this contract replaced: a missing cost counted as free.

    Kept as the negative baseline so the fixture guarding against it can fail.
    """
    total = 0
    for name in COST_TERMS:
        value = route.get(name)
        total += value if isinstance(value, (int, float)) and not isinstance(value, bool) else 0
    infrastructure = route.get("infrastructureFailureProbability") or 0
    content = route.get("contentFailureProbability") or 0
    c3 = route.get("c3RequiredProbability") or 0
    total += infrastructure * (route.get("expectedRecoveryCost") or 0)
    total += content * (route.get("expectedEscalationCost") or 0)
    total += c3 * (route.get("expectedArbiterCost") or 0)
    return total
