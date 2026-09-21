# Metrics and Self-Improvement

Use the executable run's `metrics.jsonl` plus arbiter evidence. Compare accepted
quality and first-pass verification, retries, intervention count and reason,
wall time, and usage/cost only when reported. Preserve runtime, provider, model
family, task class, inputs and budget so comparisons mean the same thing.
Unknown cost is null, not free; more output is not better work.

## Cost dimensions

One `costUsd` field cannot describe every provider, so cost is recorded in three
dimensions and they are never interchangeable:

| Dimension | What it is | When it is `null` |
| --- | --- | --- |
| `actualMarginalCostUsd` | Money actually attributable to this request, when measurable | A subscription-only route with no incremental charge |
| `apiEquivalentCostUsd` | Normalized public/API-price-equivalent usage, for efficiency comparison | No price basis is available |
| `quotaBurn` | Subscription or rate-limit allowance consumed, in the unit the provider meters | The provider exposes no allowance |

The binding rules:

- **Unknown is `null`, never `0`.** A zero is a measurement of zero cost; a null is the
  absence of a measurement. Treating the absence as zero makes an unmeasured route look
  free, so a cost objective would buy the wrong answer while reporting a saving.
- **A budget or objective states the dimension it uses.** `budget: 20` cannot say whether
  it caps cash, price-equivalent usage or an allowance, and the three are not comparable.
  A budget that does not declare its dimension is **refused**, not defaulted to the most
  convenient one.
- **Quota is never added to dollars.** `quotaBurn` records allowance consumed in the unit
  the provider meters, and the unit is recorded alongside the value. Adding it to a USD
  dimension is the conflation this section exists to prevent.
- **An unknown never wins a comparison.** Comparing two routes on a dimension where either
  side is unknown yields no verdict rather than a favourable one.
- **`apiEquivalentCostUsd` is not what a user was charged.** It compares efficiency. Any
  statement about spend uses `actualMarginalCostUsd`.
- The dimension a benchmark record carries is named by its `accountingMode` field, owned
  by [benchmark-evidence.md](benchmark-evidence.md). This document owns the dimension
  vocabulary those records name.

Turn a diagnosed failure into a bounded regression case, rerun with equivalent
inputs and checks, and compare the result. A meaningful sample of comparable
jobs is needed before suggesting routing changes. Record suggestions; change
routing policy only through a reviewed edit. Replaying event records does not
reproduce nondeterministic model execution.

## Failure classes and recovery cost

Observed failures are recorded **separately by class**, and the class decides whether the
observation may feed a cost estimate. The classes themselves are owned by
[failure-modes.md](failure-modes.md); this section owns only the recording split and which
evidence may feed `expectedRecoveryCost`.

| Observed class | Recorded as | Feeds `expectedRecoveryCost` |
| --- | --- | --- |
| Transport or infrastructure | an infrastructure failure | **Yes**, and only this one |
| Content or verification | a content failure | No |
| Permission, sandbox or authorization | a hard stop | No |
| Provider rate-limit or quota | a retryable provider failure | No |
| Evidence-plane write | an incomplete-evidence event | No |

The binding rules:

- A count is kept **per class**, never as one blended failure rate. Blending them is how a
  content failure gets mispriced as an infrastructure one.
- Only **infrastructure** evidence feeds `expectedRecoveryCost`, because only that class
  describes a runtime failing independently of the work.
- **Expected recovery cost is a ranking input only.** It may order otherwise-eligible routes,
  and it may never add, restore or remove a route, and it never changes a promotion
  trigger — those are owned by [fallback-policy.md](fallback-policy.md).
- A **content** failure never becomes a promotion or a retry loop, and repeated content
  failures must not accumulate into a promotion argument. It escalates, per
  [verification.md](verification.md).
- A **permission** stop is never a promotion trigger: promoting past it would launder a
  control decision into a runtime the user did not approve.
- An **evidence-plane write** failure neither promotes nor escalates; it is recorded and the
  affected evidence is marked incomplete.

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
| `model` | the model resolved for **this attempt**, so a promoted attempt does not overwrite its predecessor's value |
| `effortLevel` | the normalized reasoning-effort level the attempt ran at |
| `effortRaw` | the vendor's own effort parameter, verbatim |
| `benchmarkRef` | the benchmark record key that ranked this attempt, or null when ranking was degraded |

Because the record is per attempt, an attempt accepted on the micro-arbiter path
and later contradicted by a C3 verdict on a retry remains pair able. A job-level
`acceptedWithoutC3Count` cannot express that and must not be used for
calibration.

This telemetry is the **only** legitimate source of micro-arbiter calibration,
and it is only usable as ground truth for samples that received a C3 audit. See
the calibration rules in [verification.md](verification.md).

Each record carries `runId`, `jobId` and `attempt`, so a metric is joinable to the
attempt that produced it. The correlation rule itself is owned by
[trace-and-logging.md](trace-and-logging.md).

This run's recorded outcomes for a comparable task class are the **highest-authority**
benchmark evidence, above any fetched leaderboard. The authority order is owned by
[benchmark-evidence.md](benchmark-evidence.md); this document owns the fields.

Two derived figures matter:

- **Agreement rate** — how often the micro-arbiter verdict matched the C3
  verdict, computed per classifier candidate, never pooled.
- **Accepted-without-C3 count** — how many attempts bypassed the C3 call, which
  the run report must report. A rising count with flat agreement is the signal
  that a threshold is drifting.

An accepted attempt that later failed is a calibration event, not an
inconvenience: it lowers agreement and is the evidence a threshold change must
cite.
