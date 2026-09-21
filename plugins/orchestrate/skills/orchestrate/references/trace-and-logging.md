# Trace and Logging

This document owns the **span identifiers**, the **correlation rule**, **retention**
and **export**, and it joins what the other owners already define.

It owns none of these, and states so in the negative: it does **not** own the event
envelope or the event kinds ([event-protocol.md](event-protocol.md)), the directory
layout ([output-layout.md](output-layout.md)), the decision-trace fields
([decision-plane.md](decision-plane.md)), or the telemetry fields
([metrics-and-self-improvement.md](metrics-and-self-improvement.md)).

## What is already correlated, and what is not

The corpus is **already correlated**. `runId` and `jobId` appear in the event envelope
and in the run and attempt records.

What was missing:

- a **span** identifier, to separate operations inside one attempt;
- a **pairing rule**, so a promoted attempt is distinguishable from a retry of the same
  attempt;
- any identifier at all on the decision trace, which previously carried none.

## The correlation identity

| Field | Owner | Already exists | Meaning |
|---|---|---|---|
| `runId` | [job-spec.md](job-spec.md) and the envelope | yes | The run. |
| `jobId` | [job-spec.md](job-spec.md) and the envelope | yes | The job within the run. |
| `attempt` | the attempt record and the envelope | yes | The attempt ordinal. **This ordinal *is* the attempt identity.** |
| `spanId` | this document | new | The operation inside one attempt. |
| `parentSpanId` | this document | new | The span this one belongs to. |

The rule is that no second spelling may be introduced. The attempt identity is the
ordinal the record already carries; this document adds spans around it and nothing
else. A new name for the same concept would split the join it exists to make possible.

The pairing rule: a promotion is a **new `attempt` value**, so `promotionOf` names the
ordinal it succeeded. A retry of the same candidate reuses neither the span nor the
attempt ordinal of the attempt it replaced.

## The trace record

```json
{
  "seq": 0,
  "ts": "<iso-8601>",
  "runId": "<run-id>",
  "jobId": "<job-id>",
  "attempt": 1,
  "spanId": "<span-id>",
  "parentSpanId": "<span-id-or-null>",
  "kind": "<kind>",
  "payload": {}
}
```

| `kind` | Meaning |
|---|---|
| `run.start` | The run began. |
| `run.end` | The run ended, with its terminal status. |
| `probe` | A live availability or capability probe. |
| `fetch` | A benchmark fetch attempt. This kind exists because
  [benchmark-evidence.md](benchmark-evidence.md) introduced a fetch that must be auditable
  on the same footing as a decision-plane call. |
| `route` | A routing decision. |
| `decide` | A decision-plane call. |
| `gate` | A safety-gate evaluation. |
| `dispatch` | A runtime dispatch. |
| `promote` | A promotion to the next chain candidate. |
| `observe` | Observation of a dispatched job. |
| `check` | A deterministic check. |
| `verdict` | An arbiter verdict. |
| `fail_safe` | A terminal fail-safe. |
| `report` | The report was written. |

The payload is **schema-closed per `kind`**. That is a checkable property, not a
promise, so four kinds are enumerated here:

| `kind` | Closed payload fields |
|---|---|
| `route` | the full route payload, enumerated below. It is the hardest schema here because it is the record a reader audits to see why a route won. |
| `promote` | `promotionOf`, `promotionTrigger`, `fromRuntime`, `toRuntime`, `budgetUsed`, `budgetMax` |
| `gate` | `tier`, `controlsChecked`, `approvalsRequired`, `escalated`, `escalationClause` |
| `fail_safe` | `reason`, `triggers`, `candidatesTried`, `benchmarkDegraded`, `terminal` |

Every field is an enum, a number or a reference. **No free-text model, runtime or error
prose is stored**, because free text is where a secret or a hostile string would enter.

### The route payload

A `route` record must explain the whole decision on its own, so its field set is larger than
the others and is enumerated here. Every string field is a **bounded token** or a reference,
never a sentence, and the fields whose vocabulary has an owner draw from that owner's closed
set rather than from a set invented here.

| Group | Fields | Kind |
|---|---|---|
| Counts | `candidateCount`, `eligibleCount`, `rankedCount`, `hardGateSurvivors`, `hardGateRejects`, `hardGateRejectReasons`, `prunedCount`, `evidenceSampleSize` | integer, or bounded tokens for the reason list |
| Pruning | `pruneReasons` | bounded tokens from [routing-policy.md](routing-policy.md) |
| Evidence | `evidenceCohort`, `evidenceDegradation` | bounded tokens; degradation from [benchmark-evidence.md](benchmark-evidence.md) |
| Quality | `qualityBound`, `qualityEstimator` | number or `null`; the estimator is named by [benchmark-evidence.md](benchmark-evidence.md) |
| Cost dimensions | `actualMarginalCostUsd`, `apiEquivalentCostUsd`, `quotaBurn`, `costDimensionUsed` | number or `null`; the dimension vocabulary is owned by [metrics-and-self-improvement.md](metrics-and-self-improvement.md) |
| Reliability | `infrastructureFailureProbability`, `recoveryCostEvidenceClass` | number or `null`; the feeding class is owned by [metrics-and-self-improvement.md](metrics-and-self-improvement.md) |
| Expected cost | `expectedRecoveryCostUsd`, `expectedC3CostUsd`, `expectedVerifiedCostUsd` | number or `null`, per [routing-policy.md](routing-policy.md) |
| Selected route | `selectedRuntime`, `selectedProvider`, `selectedModel`, `selectedFamily`, `selectedEffortMode`, `effortLevel` | bounded tokens; the identity is the one [benchmark-evidence.md](benchmark-evidence.md) defines |
| Runner-up | `runnerUpRuntime`, `runnerUpProvider`, `runnerUpModel`, `runnerUpEffortMode`, `runnerUpMargin` | bounded tokens, and a number or `null` for the margin |
| Semantic router | `semanticRouterCalled`, `semanticRouterReason`, `semanticRouterSkippedReason` | boolean and bounded tokens from [routing-policy.md](routing-policy.md) |
| Ranking | `benchmarkRef`, `benchmarkDegraded`, `capabilityFloorDelta`, `riskFloorDelta`, `riskTier` | a reference, bounded tokens and numbers or `null` |

Three rules make this auditable rather than merely present:

- **An unmeasured term is `null`, never `0`.** A cost dimension the provider does not expose
  is recorded as `null` beside the capability metadata saying it was unavailable; writing `0`
  would claim a measurement that was never taken. See
  [metrics-and-self-improvement.md](metrics-and-self-improvement.md).
- **A reason is an enum, not prose.** `pruneReasons`, `semanticRouterReason`,
  `semanticRouterSkippedReason` and `hardGateRejectReasons` carry values from their owning
  document's closed set. A classifier's own wording is never stored: the classifier returns
  typed answers rather than text, and those answers are translated into these enums before
  they reach the trace.
- **The payload is closed in both directions.** A missing field and an added field are both
  violations, so completeness is asserted rather than hoped for.

## Joining the existing artifacts

| Artifact | Owner | Join key |
|---|---|---|
| `events.jsonl` | [event-protocol.md](event-protocol.md) | `runId, jobId, attempt` |
| `state.json` run and attempt records | [job-spec.md](job-spec.md) | `runId, jobId, attempt` |
| `decisions.jsonl` | [decision-plane.md](decision-plane.md) | `runId, jobId, attempt` |
| `metrics.jsonl` | [metrics-and-self-improvement.md](metrics-and-self-improvement.md) | `runId, jobId, attempt` |
| the benchmark cache | [benchmark-evidence.md](benchmark-evidence.md) | **exempt** |

The benchmark cache is cross-run by design and carries `refreshedByRunId` as provenance
instead. That exemption is scoped to that one artifact and to no other.

Per-artifact field schemas stay with their owners and are not restated here.

## What must be answerable from the trace

- Which candidates passed the hard filter, which were rejected, and why.
- Which benchmark record ranked the chosen candidate, and whether ranking was degraded.
- Which runtime, model and effort were selected, and by which rule.
- Which gate conditions held, and which forced escalation.
- Whether the attempt was a retry or a promotion, and what triggered it.
- What the verdict was, and from which route.
- What the terminal status was.

The route payload carries the routing half of that answerability, so these are answerable from
it directly:

- Which candidates survived the hard gates, which were rejected and under which gate, and
  which were pruned and under which reason or protection.
- Which evidence cohort and sample size ranked the choice, what quality bound came from it,
  and what degradation was recorded when broader evidence had to be used.
- Which cost dimensions were measured, which were `null`, and which dimension the budget
  declared.
- What the expected recovery, escalation and C3 costs were, and what the resulting expected
  verified cost was.
- Which effort mode was actually selected, what the runner-up was, and by what margin it lost.
- Whether the semantic router was called, and when it was not, which skip reason applied.

A run whose trace cannot answer these is **incomplete**, and the report must say so
rather than implying a complete audit trail.

## Retention and bounds

```text
TRACE_MAX_RECORDS=50000
TRACE_MAX_BYTES=67108864
TRACE_ROTATE_AT_BYTES=8388608
TRACE_RETAIN_RUNS=1
```

The trace is run-scoped. It is bounded by `TRACE_MAX_RECORDS` records and
`TRACE_MAX_BYTES` bytes, rotated inside the run directory at `TRACE_ROTATE_AT_BYTES`,
and never extended across runs. A bound that is named but unpinned cannot be asserted,
so the values are fixed here rather than deferred.

The benchmark cache is the one cross-run artifact and is **not** part of the trace.

## Redaction and export

Redaction happens **on write**, not on export. The payload schema is what makes that
possible, which is why the per-kind field sets are enumerated above.

The trace is excluded from diagnostic exports unless reviewed, matching the rule the
decision trace already carries. An export bundles a **reviewed bounded slice** rather
than the raw file.

The trace records `credentialSource` and `credentialTrust` only — never a value, nor any
part of one, per [decision-plane.md](decision-plane.md).

## When tracing fails

A trace write failure is an **evidence-plane write failure**, the third class defined in
[failure-modes.md](failure-modes.md). It **neither promotes nor escalates**. The run
continues, the affected evidence is marked incomplete through the report's completeness
field, and a run whose trace is partial states that in the report and is never described
as complete.

**A trace write failure must not consume a promotion**, because the runtime is healthy.

## Related

- [event-protocol.md](event-protocol.md) — the envelope and the event kinds.
- [output-layout.md](output-layout.md) — where the trace file sits in the run directory.
- [decision-plane.md](decision-plane.md) — the decision trace this document gives
  identifiers to.
- [metrics-and-self-improvement.md](metrics-and-self-improvement.md) — telemetry, joined
  by the same identity.
- [job-spec.md](job-spec.md) — the run and attempt records.
- [fallback-policy.md](fallback-policy.md) — the promotions that pairing distinguishes.
- [benchmark-evidence.md](benchmark-evidence.md) — the cross-run cache and its
  exemption.
