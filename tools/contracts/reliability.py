"""Reference implementation of the failure-class recording and recovery-cost rules.

The normative rules live in
`plugins/orchestrate/skills/orchestrate/references/metrics-and-self-improvement.md` under
"Failure classes and recovery cost". The classes themselves are owned by
`references/failure-modes.md`; this module does not define a second taxonomy, it maps the
observed kinds onto the owned classes and decides which may feed a recovery estimate.

Two properties are demonstrated:

- failures are counted **per class**, never as one blended rate, because blending lets a
  content failure be mispriced as an infrastructure one;
- **only** infrastructure evidence feeds `expectedRecoveryCost`, and a content failure can
  never become a promotion or a retry loop.
"""

from __future__ import annotations

#: Owned by failure-modes.md. Not redefined here, only referenced.
OWNED_CLASSES = (
    "transport-or-infrastructure",
    "content-or-verification",
    "permission-or-authorization",
    "retryable-provider",
    "evidence-plane-write",
)

#: The observable kinds a run records, and the owned class each maps onto.
OBSERVED_KINDS = (
    "infrastructure",
    "content",
    "permission",
    "provider-rate-limit",
    "evidence-plane-write",
)

KIND_TO_CLASS = {
    "infrastructure": "transport-or-infrastructure",
    "content": "content-or-verification",
    "permission": "permission-or-authorization",
    "provider-rate-limit": "retryable-provider",
    "evidence-plane-write": "evidence-plane-write",
}


class ReliabilityError(ValueError):
    """Raised for an observation that violates the owned contract."""


def classify(kind: str) -> dict:
    """Map one observed kind onto its owned class and its consequences."""
    if kind not in KIND_TO_CLASS:
        raise ReliabilityError(f"unknown failure kind {kind!r}")
    infrastructure = kind == "infrastructure"
    content = kind == "content"
    permission = kind == "permission"
    return {
        "kind": kind,
        "className": KIND_TO_CLASS[kind],
        "feedsRecoveryCost": infrastructure,
        "promotionCandidate": infrastructure,
        "retryableWithinRuntime": kind == "provider-rate-limit",
        "escalates": content,
        "hardStop": permission,
    }


def tally(observations: list[str]) -> dict:
    """Count observations per owned class.

    Every class is present in the result, including the empty ones, so a reader cannot
    mistake an absent key for a zero or for a class that was never considered.
    """
    counts = {name: 0 for name in OWNED_CLASSES}
    for kind in observations:
        counts[KIND_TO_CLASS[_validated(kind)]] += 1
    return counts


def recovery_cost_evidence(observations: list[str]) -> dict:
    """The evidence that may feed ``expectedRecoveryCost``, and only that evidence.

    Returns the infrastructure count plus the classes that were deliberately **excluded**,
    so the exclusion is visible rather than implied by silence.
    """
    counts = tally(observations)
    excluded = {name: count for name, count in counts.items() if name != "transport-or-infrastructure"}
    return {
        "infrastructureCount": counts["transport-or-infrastructure"],
        "excludedFromRecoveryCost": excluded,
        "usable": counts["transport-or-infrastructure"] > 0,
    }


def may_promote(kind: str) -> bool:
    """Whether this kind may ever be the reason a route is promoted.

    Content failures are excluded explicitly and permanently: retrying a content failure on
    another runtime selects for the answer rather than for the work. Permission stops are
    excluded because promoting past one launders a control decision.
    """
    return classify(kind)["promotionCandidate"]


def _validated(kind: str) -> str:
    if kind not in KIND_TO_CLASS:
        raise ReliabilityError(f"unknown failure kind {kind!r}")
    return kind


def legacy_recovery_evidence_count(observations: list[str]) -> int:
    """The behaviour this contract replaced: every failure treated as recovery evidence.

    Kept as the negative baseline so the fixture guarding against it can fail. Counting
    every kind is how a content failure gets mispriced as an infrastructure one, which then
    argues for promoting away from a runtime that was never at fault.
    """
    for kind in observations:
        _validated(kind)
    return len(observations)
