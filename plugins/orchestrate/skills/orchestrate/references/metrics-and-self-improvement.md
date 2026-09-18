# Metrics and Self-Improvement

Use the executable run's `metrics.jsonl` plus arbiter evidence. Compare accepted
quality and first-pass verification, retries, intervention count and reason,
wall time, and usage/cost only when reported. Preserve runtime, provider, model
family, task class, inputs and budget so comparisons mean the same thing.
Unknown cost is null, not free; more output is not better work.

Turn a diagnosed failure into a bounded regression case, rerun with equivalent
inputs and checks, and compare the result. A meaningful sample of comparable
jobs is needed before suggesting routing changes. Record suggestions; change
routing policy only through a reviewed edit. Replaying event records does not
reproduce nondeterministic model execution.

## Arbiter-gate telemetry

Record **per attempt**, in the `attemptRecords[]` array owned by
[job-spec.md](job-spec.md), so the micro-arbiter can be calibrated and audited.
Job-level values are aggregates and are never the calibration source:

| Field | Meaning |
| --- | --- |
| `riskTier` | the attempt's recorded tier, `max(tierDerivation, riskFloorDelta)` |
| `capabilityFloorDelta` | any capability-floor raise applied to the attempt |
| `riskFloorDelta` | any risk-floor raise applied; a non-zero value forces C3 |
| `microArbiterVerdict` | the signals returned, or `none` with a reason |
| `acceptedWithoutC3` | whether the escalation matrix accepted with no C3 call |
| `c3Verdict` | the C3 outcome when a C3 call occurred |
| `c3EscalationReason` | which escalation clause fired |
| `laterOutcome` | whether an accepted attempt later failed, and how |

Because the record is per attempt, an attempt accepted on the micro-arbiter path
and later contradicted by a C3 verdict on a retry remains pair able. A job-level
`acceptedWithoutC3Count` cannot express that and must not be used for
calibration.

This telemetry is the **only** legitimate source of micro-arbiter calibration,
and it is only usable as ground truth for samples that received a C3 audit. See
the calibration rules in [verification.md](verification.md).

Two derived figures matter:

- **Agreement rate** — how often the micro-arbiter verdict matched the C3
  verdict, computed per classifier candidate, never pooled.
- **Accepted-without-C3 count** — how many attempts bypassed the C3 call, which
  the run report must report. A rising count with flat agreement is the signal
  that a threshold is drifting.

An accepted attempt that later failed is a calibration event, not an
inconvenience: it lowers agreement and is the evidence a threshold change must
cite.
