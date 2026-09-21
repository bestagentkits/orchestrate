"""Reference implementation of the quality-uncertainty and evidence-hierarchy rules.

The normative rules live in
`plugins/orchestrate/skills/orchestrate/references/benchmark-evidence.md` under
"Quality uncertainty" and "Evidence hierarchy".

Two properties matter and both are tested:

- a conservative lower bound, so a tiny perfect sample cannot outrank a large
  statistically stronger one;
- evidence resolved by scope, with the scope recorded and a broader fallback marked as a
  degradation rather than presented as a measurement of the job's own cohort.
"""

from __future__ import annotations

import math

#: Pinned by benchmark-evidence.md, which owns it. The 95% one-sided lower bound.
QUALITY_CONFIDENCE_Z = 1.96

#: Recorded alongside every bound so a bound can be reproduced instead of trusted.
QUALITY_ESTIMATOR = "wilson-lower-bound"

#: Evidence scopes, most comparable first.
SCOPE_EXACT_COHORT = "exact-cohort"
SCOPE_TASK_CLASS = "task-class"
SCOPE_GLOBAL = "global"
SCOPE_NONE = "none"

SCOPE_ORDER = (SCOPE_EXACT_COHORT, SCOPE_TASK_CLASS, SCOPE_GLOBAL, SCOPE_NONE)


class QualityError(ValueError):
    """Raised for evidence that violates the owned contract."""


def wilson_lower_bound(successes: int, sample_size: int, z: float = QUALITY_CONFIDENCE_Z) -> float:
    """The Wilson score interval lower bound for a binomial proportion.

    Chosen over a Beta credible bound only because it needs no special functions and is
    therefore reproducible from the standard library alone, which is what "deterministic
    for the same evidence" has to mean in practice.
    """
    if isinstance(successes, bool) or isinstance(sample_size, bool):
        raise QualityError("successes and sample_size must be integers")
    if not isinstance(successes, int) or not isinstance(sample_size, int):
        raise QualityError("successes and sample_size must be integers")
    if sample_size <= 0:
        raise QualityError("sample_size must be positive; there is no bound for no evidence")
    if successes < 0 or successes > sample_size:
        raise QualityError("successes must lie within the sample")
    proportion = successes / sample_size
    z_squared = z * z
    centre = proportion + z_squared / (2 * sample_size)
    margin = z * math.sqrt((proportion * (1 - proportion) + z_squared / (4 * sample_size)) / sample_size)
    return (centre - margin) / (1 + z_squared / sample_size)


def quality_record(successes: int, sample_size: int, **extra) -> dict:
    """A quality record carrying the raw rate, the bound and the estimator identity."""
    bound = wilson_lower_bound(successes, sample_size)
    record = {
        "successes": successes,
        "sampleSize": sample_size,
        "rawSuccessRate": successes / sample_size,
        "qualityLowerBound": bound,
        "estimator": QUALITY_ESTIMATOR,
        "confidenceZ": QUALITY_CONFIDENCE_Z,
    }
    record.update(extra)
    return record


def rank_records(records: list[dict]) -> list[dict]:
    """Rank by conservative bound, descending, with no-evidence records last.

    A record without a sample size is never ranked on a bound. It does not become
    average, and it does not become zero either: it is placed after every record that
    has evidence, preserving the input order among such records.
    """
    with_evidence = [r for r in records if r.get("sampleSize")]
    without_evidence = [r for r in records if not r.get("sampleSize")]
    return sorted(with_evidence, key=lambda r: r["qualityLowerBound"], reverse=True) + without_evidence


def resolve_evidence(records: list[dict], cohort: str | None, task_class: str | None) -> dict:
    """Resolve the scope that supplies ranking evidence, recording any degradation.

    Narrower evidence is never averaged into broader evidence, and a narrower record is
    never invented when it does not exist. An absent cohort or task class is a real
    input, not a misuse: it must fall through to a broader level rather than match a
    record that also carries no cohort.
    """
    for scope, predicate in (
        (SCOPE_EXACT_COHORT, lambda r: bool(cohort) and r.get("cohort") == cohort),
        (SCOPE_TASK_CLASS, lambda r: bool(task_class) and r.get("taskClass") == task_class),
        (SCOPE_GLOBAL, lambda r: True),
    ):
        matches = [r for r in records if predicate(r)]
        if matches:
            return {
                "scope": scope,
                "degraded": scope != SCOPE_EXACT_COHORT,
                "records": rank_records(matches),
            }
    return {"scope": SCOPE_NONE, "degraded": True, "records": []}


def legacy_raw_rate_order(records: list[dict]) -> list[dict]:
    """The behaviour this contract replaced: order by raw rate, ignoring sample size.

    Kept as the negative baseline so the fixture guarding against it can fail.
    """
    return sorted(records, key=lambda r: r.get("rawSuccessRate", 0.0), reverse=True)
