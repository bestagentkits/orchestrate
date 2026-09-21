"""The full per-trial field set for the benchmark, with explicit capability metadata.

Issue #15 Phase 2 lists what a trial must capture: runtime version and catalog hash, requested
versus resolved provider/model/effort, model family, token and cache usage, the three cost
dimensions, the coordinator/worker/classifier/arbiter cost split, retries and failure class,
the deterministic verification result, the C3 requirement and reason, and the route decision
trace with its evidence scope.

The hard rule is the last clause of the objective: **where a provider exposes nothing, the
field is `null` with explicit capability metadata, never fabricated.** A zero is a
measurement; a null with a stated reason is an absence. This module keeps those two apart by
making every provider-dependent field carry a state from a closed vocabulary, so a reader can
tell "the provider did not report cache reads" from "cache reads were zero" without guessing.

Four states, and each is checkable:

- ``exposed`` - the provider or runtime reported it, so the value must be present;
- ``derived`` - computed locally from recorded data, so the derivation basis is recorded;
- ``not-exposed-by-provider`` - the provider does not report it, so the value is ``null``;
- ``not-measured`` - it could be exposed but this trial did not measure it, so the value is
  ``null``.
"""

from __future__ import annotations

from tools.contracts.reliability import OBSERVED_KINDS

EXPOSED = "exposed"
DERIVED = "derived"
NOT_EXPOSED = "not-exposed-by-provider"
NOT_MEASURED = "not-measured"

CAPABILITY_STATES = (EXPOSED, DERIVED, NOT_EXPOSED, NOT_MEASURED)

#: Fields whose availability depends on the provider or runtime exposing something.
CAPABILITY_GATED = (
    "cacheReadTokens",
    "cacheWriteTokens",
    "reasoningTokens",
    "actualMarginalCostUsd",
    "apiEquivalentCostUsd",
    "quotaBurn",
    "rateLimitRemaining",
    "modelFamily",
    "catalogHash",
    "runtimeVersion",
    # The harness counts dispatch invocations, which is a superset of retries and
    # promotions. Until it can tell them apart they are recorded as unmeasured rather than
    # as zero, because zero would assert a count that was never taken.
    "retries",
    "promotions",
    # Whether C3 was required is the skill's decision, and a trial where the skill never
    # settled leaves no evidence of it. Recording `null` keeps "not observed" apart from
    # "observed as not required".
    "c3Required",
    "c3Reason",
)

_REQUIRED_BASE = (
    # identity and outcome
    "variant",
    "taskId",
    "cohort",
    "type",
    "trial",
    "status",
    "success",
    "durationSeconds",
    # requested versus resolved: these may differ, and the difference is the point
    "requestedProvider",
    "requestedModel",
    "requestedEffort",
    "resolvedProvider",
    "resolvedModel",
    "resolvedEffort",
    # runtime identity
    "runtimeName",
    # component cost split
    "coordinatorCostUsd",
    "workerCostUsd",
    "classifierCostUsd",
    "arbiterCostUsd",
    "totalCostUsd",
    # reliability and verification
    "failureClass",
    "deterministicVerificationResult",
    # decision evidence
    "routeDecisionTrace",
    "evidenceScope",
    "capability",
)

#: Recorded for every trial, present or explicitly null. The provider-dependent fields are
#: appended rather than restated, so the two declarations cannot drift apart.
REQUIRED_FIELDS = _REQUIRED_BASE + tuple(f for f in CAPABILITY_GATED if f not in _REQUIRED_BASE)

_COMPONENTS = ("coordinatorCostUsd", "workerCostUsd", "classifierCostUsd", "arbiterCostUsd")

#: Roles a resolved model can hold. Anything unassigned is a worker.
ROLES = ("coordinator", "worker", "classifier", "arbiter")

_SPLIT_TOLERANCE = 0.01


class TrialSchemaError(ValueError):
    """Raised for an input that cannot be assembled into a trial record."""


def capability(state: str, value=None, basis: str | None = None) -> dict:
    """One provider-dependent field's value and the state that qualifies it."""
    if state not in CAPABILITY_STATES:
        raise TrialSchemaError(f"unknown capability state {state!r}")
    if state == EXPOSED and value is None:
        raise TrialSchemaError("an exposed field must carry a value")
    if state in (NOT_EXPOSED, NOT_MEASURED) and value is not None:
        raise TrialSchemaError(f"a {state} field must be null, not {value!r}")
    if state == DERIVED and value is None:
        raise TrialSchemaError("a derived field must carry a value")
    entry = {"state": state, "value": value if state != DERIVED else value}
    if state == DERIVED:
        if not basis:
            raise TrialSchemaError("a derived field must record its basis")
        entry["basis"] = basis
    return entry


def split_capabilities(entries: dict) -> tuple[dict, dict]:
    """Separate capability entries into the record's fields and its capability map."""
    values: dict = {}
    metadata: dict = {}
    for field in CAPABILITY_GATED:
        entry = entries.get(field)
        if entry is None:
            raise TrialSchemaError(f"missing capability entry for {field}")
        if entry["state"] not in CAPABILITY_STATES:
            raise TrialSchemaError(f"unknown capability state for {field}")
        values[field] = entry["value"]
        meta = {"state": entry["state"]}
        if entry["state"] == DERIVED:
            meta["basis"] = entry["basis"]
        metadata[field] = meta
    return values, metadata


def derive_model_family(model_id: str | None) -> dict:
    """The family a provider-local model id belongs to, as a stated derivation.

    The provider does not report a family, so this is recorded as derived rather than
    exposed, and the basis names the rule the caller can re-run. A heuristic presented as a
    provider fact would be exactly the fabrication the objective forbids.
    """
    if not model_id:
        return capability(NOT_EXPOSED)
    head = ""
    for character in model_id:
        if character.isdigit():
            break
        head += character
    family = head.strip(".-_/").split("-")[0]
    if not family or not family.isalpha():
        return capability(NOT_EXPOSED)
    return capability(DERIVED, family, basis=f"leading-alphabetic-token:{model_id}")


def component_split(model_counts: dict, roles: dict | None = None, model_costs: dict | None = None) -> dict:
    """Split attributable cost across the four roles.

    ``model_costs`` maps ``provider/model`` to its cost. A role is taken from the caller's
    role assignments when present, and a model with no assignment is a worker. An
    unassignable model is still counted: dropping it would understate the trial.
    """
    roles = roles or {}
    model_costs = model_costs or {}
    split = {component: 0.0 for component in _COMPONENTS}
    for model, cost in model_costs.items():
        role = roles.get(model, "worker")
        if role not in ROLES:
            role = "worker"
        split[f"{role}CostUsd"] = split.get(f"{role}CostUsd", 0.0) + cost
    return split


def build_trial_record(
    core: dict,
    capabilities: dict,
    model_costs: dict,
    roles: dict | None = None,
    route_decision: dict | None = None,
    evidence_scope: str | None = None,
    runtime_name: str = "pi",
) -> dict:
    """Assemble a complete trial record.

    Nothing is invented. A field the caller cannot supply arrives as ``null`` through a
    capability entry with a state saying why, which is the difference between a record that
    reports an absence and one that reports a fabricated zero.
    """
    values, metadata = split_capabilities(capabilities)
    split = component_split({}, roles, model_costs)
    total = sum(split.values())

    record = {
        "variant": core.get("variant"),
        "taskId": core.get("taskId"),
        "cohort": core.get("cohort"),
        "type": core.get("type"),
        "trial": core.get("trial"),
        "status": core.get("status", "ok"),
        "success": bool(core.get("success")),
        "durationSeconds": core.get("durationSeconds"),
        "requestedProvider": core.get("requestedProvider"),
        "requestedModel": core.get("requestedModel"),
        "requestedEffort": core.get("requestedEffort"),
        "resolvedProvider": core.get("resolvedProvider"),
        "resolvedModel": core.get("resolvedModel"),
        "resolvedEffort": core.get("resolvedEffort"),
        "runtimeName": runtime_name,
        "coordinatorCostUsd": round(split["coordinatorCostUsd"], 6),
        "workerCostUsd": round(split["workerCostUsd"], 6),
        "classifierCostUsd": round(split["classifierCostUsd"], 6),
        "arbiterCostUsd": round(split["arbiterCostUsd"], 6),
        "totalCostUsd": round(total, 6),
        "failureClass": core.get("failureClass"),
        "deterministicVerificationResult": core.get("deterministicVerificationResult"),
        "routeDecisionTrace": route_decision,
        "evidenceScope": evidence_scope,
        "capability": metadata,
    }
    record.update(values)
    return record


def validate_trial_record(record: dict) -> list[str]:
    """Every problem with a trial record, as stable machine-readable codes."""
    if not isinstance(record, dict):
        raise TrialSchemaError("a trial record must be an object")

    problems: list[str] = []

    for field in REQUIRED_FIELDS:
        if field not in record:
            problems.append(f"missing:{field}")

    for field in record:
        if field not in REQUIRED_FIELDS:
            problems.append(f"unknown:{field}")

    metadata = record.get("capability")
    if not isinstance(metadata, dict):
        return problems + ["malformed:capability"]

    for field in CAPABILITY_GATED:
        entry = metadata.get(field)
        if not isinstance(entry, dict):
            problems.append(f"missing-capability-state:{field}")
            continue
        state = entry.get("state")
        if state not in CAPABILITY_STATES:
            problems.append(f"unknown-capability-state:{field}")
            continue
        value = record.get(field)
        if state == EXPOSED and value is None:
            problems.append(f"exposed-but-null:{field}")
        if state in (NOT_EXPOSED, NOT_MEASURED) and value is not None:
            problems.append(f"fabricated-value:{field}")
        if state == DERIVED and not entry.get("basis"):
            problems.append(f"derived-without-basis:{field}")

    failure_class = record.get("failureClass")
    if failure_class is not None and failure_class not in OBSERVED_KINDS:
        problems.append(f"unknown-failure-class:{failure_class}")
    if record.get("status") in ("ok",) and failure_class is not None:
        problems.append("failure-class-on-a-successful-trial")

    if bool(record.get("c3Required")) and not record.get("c3Reason"):
        problems.append("c3-required-without-a-reason")
    if not record.get("c3Required") and record.get("c3Reason"):
        problems.append("c3-reason-without-a-requirement")

    component_sum = 0
    known_components = 0
    for component in _COMPONENTS:
        value = record.get(component)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            component_sum += value
            known_components += 1
        else:
            problems.append(f"not-a-number:{component}")

    total = record.get("totalCostUsd")
    if not isinstance(total, (int, float)) or isinstance(total, bool):
        problems.append("not-a-number:totalCostUsd")
    elif known_components == len(_COMPONENTS):
        if abs(component_sum - total) > _SPLIT_TOLERANCE:
            problems.append("components-do-not-sum-to-total")

    if record.get("routeDecisionTrace") is not None:
        from tools.contracts import trace_route

        for problem in trace_route.validate_route_payload(record["routeDecisionTrace"]):
            problems.append(f"route-trace:{problem}")

    return problems


def is_valid_trial_record(record: dict) -> bool:
    return not validate_trial_record(record)


def legacy_trial_fields() -> tuple:
    """The fields a trial carried before this contract.

    Kept as the negative baseline so the completeness fixture can fail: this set cannot name
    a resolved model, split a cost by component, classify a failure, or explain a route.
    """
    return (
        "variant",
        "taskId",
        "cohort",
        "type",
        "trial",
        "status",
        "failure",
        "agentExitCode",
        "success",
        "durationSeconds",
        "costUsd",
        "cumulativeCostUsd",
        "tokens",
        "models",
        "sessionFiles",
        "dispatches",
    )
