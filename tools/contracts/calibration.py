"""Reference implementation of the calibration validity and durability rules.

The normative rules live in
`plugins/orchestrate/skills/orchestrate/references/verification.md` under "Calibration"
and its "Durability and invalidation" subsection.

Two properties are load-bearing here:

- a durable record is reusable only when **every** identity component matches, so a model,
  schema, prompt, signal-set or threshold change invalidates it;
- the record **cannot validate itself**. The floors come from the owner-pinned constants
  passed in by the caller, so a file that asserts its own lower minimum is invalid by
  construction rather than merely suspicious.

The third property is the conservative branch required by the contract: when the runtime
cannot supply a classifier version, a silent classifier change would be undetectable, so
durable reuse is refused and the install stays on the bounded shadow sample. That is a
deliberate choice to degrade rather than to trust an unobservable.
"""

from __future__ import annotations

#: The identity components. A mismatch in any one of them invalidates reuse.
IDENTITY_COMPONENTS = (
    "classifierProvider",
    "classifierModelId",
    "classifierVersion",
    "decisionSchemaHash",
    "promptContractHash",
    "signalSetHash",
    "thresholdPolicy",
)

#: Closed vocabulary of invalidation reasons.
INVALID_REASONS = (
    "identity-mismatch",
    "version-unobservable",
    "expired",
    "below-minimum-samples",
    "agreement-below-floor",
    "threshold-below-initial",
    "signal-set-incomplete",
    "self-asserted-floor",
)


class CalibrationError(ValueError):
    """Raised for a calibration record that cannot be evaluated."""


def _component_mismatches(record: dict, identity: dict) -> list[str]:
    mismatches = []
    for component in IDENTITY_COMPONENTS:
        if record.get(component) != identity.get(component):
            mismatches.append(component)
    return mismatches


def validity(
    record: dict,
    identity: dict,
    now: str,
    minimum_samples: int,
    agreement_floor: float,
    initial_threshold: float,
    full_signal_set: tuple | list | set,
) -> dict:
    """Whether a calibration record may be reused, and every reason it may not.

    ``minimum_samples``, ``agreement_floor``, ``initial_threshold`` and
    ``full_signal_set`` are supplied by the caller from the owner-pinned constants. They are
    deliberately **not** read from the record, which is what stops a record from validating
    itself.
    """
    if not isinstance(record, dict) or not record:
        raise CalibrationError("a calibration record is required")

    reasons: list[str] = []

    if not identity.get("classifierVersion"):
        reasons.append("version-unobservable")

    if _component_mismatches(record, identity):
        reasons.append("identity-mismatch")

    expires_at = record.get("expiresAt")
    if not expires_at or str(expires_at) <= str(now):
        reasons.append("expired")

    if (record.get("sampleCount") or 0) < minimum_samples:
        reasons.append("below-minimum-samples")

    # The record's declared minimum must equal the owner's value. A record carrying a
    # lower one is asserting its own floor, which is self-validation.
    if record.get("minimum") != minimum_samples:
        reasons.append("self-asserted-floor")

    agreement = record.get("agreement")
    if agreement is None or agreement < agreement_floor:
        reasons.append("agreement-below-floor")

    threshold = record.get("threshold")
    if threshold is None or threshold < initial_threshold:
        reasons.append("threshold-below-initial")

    declared = record.get("signals")
    if declared is None or set(declared) != set(full_signal_set):
        reasons.append("signal-set-incomplete")

    ordered = [reason for reason in INVALID_REASONS if reason in reasons]
    return {"reusable": not ordered, "reasons": ordered}


def durable_record_is_reusable(record: dict, identity: dict, **kwargs) -> bool:
    """Convenience wrapper returning only the verdict."""
    return bool(validity(record, identity, **kwargs)["reusable"])


def legacy_validity_trusting_the_record(record: dict, now: str) -> bool:
    """The behaviour this contract replaced: the record supplies its own floors.

    Kept as the negative baseline so the fixture guarding against it can fail. It checks
    only that the record looks internally satisfied, which is exactly the self-validation
    the owned rule forbids.
    """
    if not record:
        return False
    if str(record.get("expiresAt") or "") <= str(now):
        return False
    return (record.get("sampleCount") or 0) >= (record.get("minimum") or 0)
