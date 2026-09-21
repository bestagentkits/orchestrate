"""Reference implementation of the task quality floor and verification-strength rules.

The normative rules live in
`plugins/orchestrate/skills/orchestrate/references/routing-policy.md` under
"Task quality floor" and "Verification strength".

The property this module exists to demonstrate is the one that is easiest to get
backwards: selection picks the **cheapest route that clears the floor**, not the strongest
route available. A second property guards a safety invariant: verification strength may
re-rank eligible routes, and may never widen eligibility downward.

A third property is fail-closed rather than fail-open: a candidate whose capability tier
cannot be established does not clear a floor, because the contract forbids assigning a
load-bearing job to a candidate that cannot be classified confidently.
"""

from __future__ import annotations

#: Pinned by routing-policy.md, which owns them.
QUALITY_FLOOR_STRONG_VERIFICATION = 0.50
QUALITY_FLOOR_WEAK_VERIFICATION = 0.85
QUALITY_FLOOR_JUDGMENT = 0.90

STRONG_VERIFICATION = "strong"
WEAK_VERIFICATION = "weak"

CAPABILITY_TIERS = ("C1", "C2", "C3")

JUDGMENT_TASK_CLASSES = ("architecture", "review", "audit", "security", "arbiter")


class RoutingError(ValueError):
    """Raised for a routing input that violates the owned contract."""


def tier_rank(tier: str) -> int:
    """Numeric position of a capability tier, for comparison only."""
    if tier not in CAPABILITY_TIERS:
        raise RoutingError(f"unknown capability tier {tier!r}")
    return CAPABILITY_TIERS.index(tier) + 1


def quality_floor(
    verification_strength: str,
    importance: str = "normal",
    task_class: str = "implement",
) -> float:
    """Derive the required quality floor from job properties, never from a provider."""
    if verification_strength not in (STRONG_VERIFICATION, WEAK_VERIFICATION):
        raise RoutingError(f"unknown verification strength {verification_strength!r}")
    floor = (
        QUALITY_FLOOR_STRONG_VERIFICATION
        if verification_strength == STRONG_VERIFICATION
        else QUALITY_FLOOR_WEAK_VERIFICATION
    )
    if task_class in JUDGMENT_TASK_CLASSES:
        floor = max(floor, QUALITY_FLOOR_JUDGMENT)
    if importance == "high":
        floor = max(floor, QUALITY_FLOOR_JUDGMENT)
    return floor


def clears_capability(candidate: dict, required_tier: str) -> bool:
    """Whether a candidate meets the required capability tier.

    This is the capability floor and it is not negotiable by verification strength, cost
    or quality evidence. A candidate whose tier cannot be established **fails closed**: the
    contract says a candidate that cannot be classified confidently must not be assigned a
    load-bearing job, so an absent tier never clears a floor.
    """
    tier = candidate.get("capabilityTier")
    if not isinstance(tier, str) or tier not in CAPABILITY_TIERS:
        return False
    return tier_rank(tier) >= tier_rank(required_tier)


def clears_quality(candidate: dict, floor: float) -> bool:
    """Whether a candidate's conservative quality bound clears the floor.

    A candidate with no bound cannot clear a floor by default: no evidence is not the same
    as good evidence, and treating it as clearing would let an unmeasured route win.
    """
    bound = candidate.get("qualityLowerBound")
    return bound is not None and bound >= floor


def select_route(candidates: list[dict], required_tier: str, floor: float) -> dict | None:
    """The cheapest route clearing both the capability tier and the quality floor.

    Cost is compared only where it is known, because an unknown cost is not a cheap one.
    Returns ``None`` when nothing clears, which the caller reports as `blocked` rather than
    resolving by weakening a floor.
    """
    affordable = []
    for candidate in candidates:
        if not clears_capability(candidate, required_tier):
            continue
        if not clears_quality(candidate, floor):
            continue
        if candidate.get("expectedVerifiedCostUsd") is None:
            continue
        affordable.append(candidate)
    if not affordable:
        return None
    return min(affordable, key=lambda c: c["expectedVerifiedCostUsd"])


def legacy_strongest_route(candidates: list[dict], required_tier: str) -> dict | None:
    """The behaviour this contract replaced: pick the strongest, ignore cost.

    Kept as the negative baseline so the fixture guarding against it can fail.
    """
    eligible = [c for c in candidates if clears_capability(c, required_tier) and c.get("qualityLowerBound") is not None]
    if not eligible:
        return None
    return max(eligible, key=lambda c: c["qualityLowerBound"])
