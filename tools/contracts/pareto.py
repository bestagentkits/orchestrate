"""Reference implementation of the deterministic Pareto-pruning rules.

The normative rules live in
`plugins/orchestrate/skills/orchestrate/references/routing-policy.md` under
"Pareto pruning".

The property that matters most here is not that pruning works, but that it **cannot**
remove a candidate something else depends on. An over-eager prune deletes the C3
independent route or the fallback and looks like a cost optimisation while it is actually
a safety regression, which is why every protection below is fail-closed.
"""

from __future__ import annotations

#: Pinned by routing-policy.md, which owns it.
PARETO_TOLERANCE = 0.05

HIGHER_IS_BETTER = ("qualityLowerBound", "reliability")
LOWER_IS_BETTER = ("expectedVerifiedCostUsd", "durationSeconds", "expectedRecoveryCostUsd")
PARETO_DIMENSIONS = HIGHER_IS_BETTER + LOWER_IS_BETTER

#: Reasons a candidate must survive pruning even when dominated.
PROTECTIONS = (
    "explicit-pin",
    "c3-independence",
    "stronger-controls",
    "fallback-resilience",
    "non-comparable-evidence",
    "different-accounting",
)


class ParetoError(ValueError):
    """Raised for a pruning input that violates the owned contract."""


def _compare(left, right, tolerance: float) -> int:
    """Compare two values, treating a difference inside the tolerance as equal."""
    scale = max(abs(left), abs(right), 1e-12)
    if abs(left - right) <= tolerance * scale:
        return 0
    return 1 if left > right else -1


def _better(left: dict, right: dict, dimension: str, tolerance: float) -> bool:
    """Whether ``left`` is materially better than ``right`` on one dimension."""
    verdict = _compare(left[dimension], right[dimension], tolerance)
    return verdict == 1 if dimension in HIGHER_IS_BETTER else verdict == -1


def _no_worse(left: dict, right: dict, dimension: str, tolerance: float) -> bool:
    """Whether ``left`` is no worse than ``right`` on one dimension."""
    verdict = _compare(left[dimension], right[dimension], tolerance)
    return verdict >= 0 if dimension in HIGHER_IS_BETTER else verdict <= 0


def _complete(candidate: dict) -> bool:
    """Whether every ranking dimension is known, so dominance can be established."""
    for dimension in PARETO_DIMENSIONS:
        value = candidate.get(dimension)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return False
    return True


def comparable_for_pruning(left: dict, right: dict) -> bool:
    """Whether two candidates may be compared at all.

    Different accounting modes are not comparable, and neither are different evidence
    scopes: a cost in one dimension is not a cost in another, and a bound measured on one
    cohort is not a bound for another.
    """
    return left.get("accountingMode") == right.get("accountingMode") and left.get("cohort") == right.get("cohort")


def protection_reasons(candidate: dict, dominator: dict | None, requirements: dict) -> list[str]:
    """Every reason this candidate must survive pruning, empty when it has none."""
    reasons: list[str] = []
    if candidate.get("pinned"):
        reasons.append("explicit-pin")
    if requirements.get("requiresIndependence") and candidate.get("independentFamily"):
        reasons.append("c3-independence")
    if dominator is not None and candidate.get("controlStrength", 0) > dominator.get("controlStrength", 0):
        reasons.append("stronger-controls")
    if requirements.get("requiresFallback") and candidate.get("fallbackCandidate"):
        reasons.append("fallback-resilience")
    if dominator is not None:
        if candidate.get("cohort") != dominator.get("cohort") or candidate.get("taskClass") != dominator.get("taskClass"):
            reasons.append("non-comparable-evidence")
        if candidate.get("accountingMode") != dominator.get("accountingMode"):
            reasons.append("different-accounting")
    return reasons


def dominates(left: dict, right: dict, tolerance: float = PARETO_TOLERANCE) -> bool:
    """Whether ``left`` dominates ``right``.

    An incomplete candidate is never dominated, and never dominates: dominance cannot be
    established on a value that is not known.
    """
    if not _complete(left) or not _complete(right):
        return False
    if not comparable_for_pruning(left, right):
        return False
    if not all(_no_worse(left, right, dimension, tolerance) for dimension in PARETO_DIMENSIONS):
        return False
    return any(_better(left, right, dimension, tolerance) for dimension in PARETO_DIMENSIONS)


def prune(candidates: list[dict], requirements: dict | None = None) -> tuple[list[dict], list[dict]]:
    """Return the surviving candidates and a structured trace of every decision."""
    requirements = requirements or {}
    trace: list[dict] = []
    pruned_names: set = set()

    for candidate in candidates:
        for other in candidates:
            if candidate is other or other.get("name") in pruned_names:
                continue
            if not dominates(other, candidate):
                continue
            reasons = protection_reasons(candidate, other, requirements)
            if reasons:
                trace.append({
                    "decision": "kept",
                    "candidate": candidate.get("name"),
                    "protectedBy": reasons,
                    "wouldHaveBeenDominatedBy": other.get("name"),
                })
                continue
            better_on = [d for d in PARETO_DIMENSIONS if _better(other, candidate, d, PARETO_TOLERANCE)]
            trace.append({
                "decision": "pruned",
                "candidate": candidate.get("name"),
                "dominatedBy": other.get("name"),
                "betterOn": better_on,
            })
            pruned_names.add(candidate.get("name"))
            break

    survivors = [c for c in candidates if c.get("name") not in pruned_names]
    return survivors, trace


def legacy_prune_without_protections(candidates: list[dict]) -> list[dict]:
    """The behaviour this contract replaced: prune on dominance alone.

    Kept as the negative baseline so the fixture guarding against it can fail. It removes
    pinned, independent-review and fallback candidates whenever they look dominated.
    """
    survivors = []
    for candidate in candidates:
        if not any(dominates(other, candidate) for other in candidates if other is not candidate):
            survivors.append(candidate)
    return survivors
