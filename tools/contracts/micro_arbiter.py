"""Reference implementation of the direct-to-C3 and bounded-shadow-sampling rules.

The normative rules live in
`plugins/orchestrate/skills/orchestrate/references/verification.md` under "Direct to C3"
and in `references/decision-plane.md` under the micro-arbiter task.

Two properties are demonstrated here:

- a structurally C3-mandatory path goes straight to C3, because a gatekeeper whose verdict
  cannot feed an unreachable accept predicate is a call that buys nothing;
- an uncalibrated installation samples for calibration on a **bounded explicit** schedule
  instead of observing on every attempt, which is the recurring tax this rule removes.

The third, quieter property is that "not needed" stays distinguishable from "failed": a
skipped micro-arbiter is recorded as an explicit `none` with a reason, rather than as an
absence a reader has to interpret.
"""

from __future__ import annotations

#: Pinned by verification.md, which owns them.
SHADOW_SAMPLE_EVERY_N = 10
SHADOW_SAMPLE_MAX_PER_RUN = 5

#: Closed vocabulary. The escalation list in verification.md is the source of these.
STRUCTURAL_C3_REASONS = (
    "security-sensitive",
    "verdict-artifact",
    "architecture-or-public-contract",
    "high-importance-implementation",
    "external-destructive-or-credentialed",
    "parallel-or-untrusted-write",
    "non-zero-risk-floor-delta",
    "contradictory-evidence",
    "injection-fixture-unverified",
    "approval-dispatch-or-shared-state",
)

#: The three verification paths an attempt can take.
PATHS = ("direct-c3", "c3-with-bounded-shadow", "micro-arbiter-may-accept")

VERDICT_NOT_NEEDED = "none"

JUDGMENT_TASKS = ("review", "audit", "security", "arbiter")


class MicroArbiterError(ValueError):
    """Raised for a verification input that violates the owned contract."""


def structural_c3_reasons(job: dict, attempt: dict, injection_fixture_passed: bool = True) -> list[str]:
    """Every structural reason C3 is already mandatory, empty when the path is open.

    These are conditions under which the accept predicate is unreachable regardless of what
    a micro-arbiter would return, so the gatekeeper cannot change a permitted decision.
    """
    reasons: list[str] = []
    task = job.get("task")
    if task in ("audit", "security") or job.get("securitySensitive"):
        reasons.append("security-sensitive")
    if task in JUDGMENT_TASKS or job.get("artifactIsVerdict"):
        if "verdict-artifact" not in reasons:
            reasons.append("verdict-artifact")
    if task == "architecture" or job.get("publicContractDecision"):
        reasons.append("architecture-or-public-contract")
    if task == "implement" and job.get("importance") == "high":
        reasons.append("high-importance-implementation")
    if job.get("effect") in ("high-impact-write", "destructive", "external") or job.get("credentialed"):
        reasons.append("external-destructive-or-credentialed")
    if job.get("parallel") or job.get("untrustedPrompt"):
        reasons.append("parallel-or-untrusted-write")
    if attempt.get("riskFloorDelta"):
        reasons.append("non-zero-risk-floor-delta")
    if attempt.get("contradictoryEvidence"):
        reasons.append("contradictory-evidence")
    if not injection_fixture_passed:
        reasons.append("injection-fixture-unverified")
    if job.get("approval") or job.get("emitsDispatch") or job.get("mutatesSharedState"):
        reasons.append("approval-dispatch-or-shared-state")
    return reasons


def decide_verification_path(
    job: dict,
    attempt: dict,
    calibration_valid: bool,
    injection_fixture_passed: bool = True,
) -> dict:
    """Which verification path this attempt takes, and why.

    The micro-arbiter is invoked only on the one path where its verdict can reach the accept
    predicate. Everywhere else the verdict is recorded as `none` **with** the reason, so an
    unneeded call is never mistaken for a missing one.
    """
    reasons = structural_c3_reasons(job, attempt, injection_fixture_passed)
    if reasons:
        return {
            "path": "direct-c3",
            "reasons": reasons,
            "microArbiterCalled": False,
            "microArbiterVerdict": VERDICT_NOT_NEEDED,
        }
    if not calibration_valid:
        return {
            "path": "c3-with-bounded-shadow",
            "reasons": ["calibration-invalid"],
            "microArbiterCalled": False,
            "microArbiterVerdict": VERDICT_NOT_NEEDED,
        }
    return {
        "path": "micro-arbiter-may-accept",
        "reasons": [],
        "microArbiterCalled": True,
        "microArbiterVerdict": None,
    }


def shadow_sample(attempt_index: int, samples_taken: int) -> bool:
    """Whether this attempt is sampled for calibration while the install is uncalibrated.

    Bounded twice: the cadence keeps the sample explicit and spread out, and the ceiling
    stops a long run from sampling without limit. When the ceiling is reached, sampling
    stops rather than widening.
    """
    if attempt_index < 1:
        raise MicroArbiterError("attempt_index starts at 1")
    if samples_taken < 0:
        raise MicroArbiterError("samples_taken must not be negative")
    if samples_taken >= SHADOW_SAMPLE_MAX_PER_RUN:
        return False
    return (attempt_index - 1) % SHADOW_SAMPLE_EVERY_N == 0


def legacy_call_always(job: dict, attempt: dict, **_: object) -> dict:
    """The behaviour this contract replaced: the gatekeeper runs before every C3 call.

    Kept as the negative baseline so the fixture guarding against it can fail.
    """
    return {
        "path": "micro-arbiter-may-accept",
        "reasons": [],
        "microArbiterCalled": True,
        "microArbiterVerdict": None,
    }
