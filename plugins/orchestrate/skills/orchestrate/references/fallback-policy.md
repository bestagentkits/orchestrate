# Fallback and Fail-Safe

This document owns what happens when a **runtime** fails.

It does not own what happens when a **work product** fails
([verification.md](verification.md)), who is eligible
([routing-policy.md](routing-policy.md)), or the tier and the controls
([safety-policy.md](safety-policy.md)).

## Terminology

**Promotion** means moving one job's attempt to the next candidate in the promotion
chain, creating a **new attempt with its own record** rather than editing the
previous one.

This is this document's reading of the request's "next promotion". A user-curated
promotion list is not needed, because the declared `fallback_runtime` field already
provides a user-ordered list.

## Promotion triggers

The rule is: only an infrastructure failure promotes.

| Trigger | Evidence | Notes |
|---|---|---|
| Quota or rate-limit exhaustion | The provider's own quota or rate-limit response, **after** the retry budget for the current candidate is exhausted | Not before the retry budget; exhaustion is the precondition. |
| Provider outage | A transport error, or a repeated server error | |
| Process crash or spawn failure | A non-zero exit with no work product, or a failure to spawn at all | |
| Runtime binary missing since the probe | The binary the probe recorded is no longer resolvable | The probe evidence is stale, not the job. |
| Dispatch timeout attributable to the transport | A timeout with no evidence the work began | A timeout attributable to the work is not this. |

**An authorization or permission failure never promotes.** A classified `PERMISSION`,
`SANDBOX` or `AUTH` result is a hard stop owned by
[failure-modes.md](failure-modes.md), and promoting past it would launder a control
decision into a different runtime — the same decision, made by a runtime the user did
not approve for it.

## What never promotes

- A **failed check never promotes.** Promoting on a failed check is retrying until
  the check passes, with extra steps.
- A failed or ambiguous arbiter verdict never promotes.
- Contradictory evidence never promotes.
- A missing artifact never promotes.
- An uncertainty signal never promotes.
- A permission, sandbox or authorization stop never promotes.
- A slow-but-working runtime never promotes on duration alone.

Every one of these escalates per [verification.md](verification.md).

## Composition with retry

Two bounded mechanisms already existed and they collide unless precedence is stated.
For a given candidate, the same-runtime bounded retry policy in
[job-spec.md](job-spec.md) runs **first** and is bounded by `retry.max_attempts`.
Only when that budget is exhausted does a promotion occur.

The combined ceiling, as the single bound an implementer applies:

```text
dispatches for one job  <=  (1 + maxPromotions) x max(1, max_attempts)
```

This product is the one bound. It is not two independent bounds applied in sequence,
and it must not be read as permitting `maxPromotions` promotions **each** with a full
retry budget beyond the product.

Retry semantics stay with [job-spec.md](job-spec.md). This document owns when a
promotion is allowed, and nothing here redefines a retry class.

## Building the chain

The chain is built positionally, because the tree already defines an order:

1. the job's declared `fallback_runtime` entries, **in declared order**;
2. then the remaining hard-filter survivors, in benchmark-ranked order per
   [benchmark-evidence.md](benchmark-evidence.md).

An explicit user order always wins over a benchmark score, so the benchmark ranking
only fills the tail.

A candidate enters the chain only if it:

- (a) passed the hard filter under the **same** floors;
- (b) is not weaker on any control concern (below);
- (c) is re-probed live for availability at promotion time; and
- (d) has not already failed this job in this run.

The four exclusions, stated negatively: a rejected candidate never enters; a
weak-on-any-concern candidate never enters; a candidate whose availability is only
cached never enters; and a candidate already tried for this job is skipped, to
prevent cycling.

## The control comparison

"Same or stronger controls" was an undefined predicate. It is defined here by
anchoring to the six concerns in [safety-policy.md](safety-policy.md): **approval,
tool gating, write boundary, isolation, timeout and bypass**.

A successor is weaker if it is weaker on any concern, and a candidate weaker on any
concern is **excluded from the chain regardless of how much stronger it is on the
others**. The comparison is per-concern, with no dominance relation and no
trade-off.

Two cases the definition settles:

- A candidate with stronger isolation but weaker capture is weaker on **capture**, and
  is excluded. Strength elsewhere does not pay for it.
- A candidate whose isolation is **prompt-only** is excluded from any chain for a job
  at R2 or above, because [safety-policy.md](safety-policy.md) keeps destructive and
  credentialed external actions off prompt-only isolation.

## The budget

Promotions are bounded by `fallback.maxPromotions`, defaulting to
`MAX_PROMOTIONS_DEFAULT` and never exceeding `MAX_PROMOTIONS_MAX`. A declared value
above the maximum is **rejected**, not clamped.

Each promotion is a new attempt with its own record. Exhausting the budget **is** the
fail-safe condition — it is not an error to retry around.

## Re-gating a successor

Both this document and [job-spec.md](job-spec.md) are normative, and `job-spec.md`
says fallback selection "reruns the full capability and risk gate". That sentence and
a claim that the gate is not re-decided must be reconciled explicitly.

What **does** re-run on promotion:

- availability, re-probed live; and
- the control re-verification from the chain rule (b) — the successor must not be
  weaker on any concern.

What does **not** change:

- the job's tier, its approvals, and its egress authority, which were decided by the
  safety gate for this job and are not re-decided by a promotion.

This is the precise reading of "reruns the full capability and risk gate": the gate's
**eligibility and control checks** re-run; its **authority decisions** do not. A
successor that would need a new approval, a wider write boundary, an enabled bypass or
a new egress authority is not a promotion target at all — it is a **different job**
requiring a new gate decision.

## Freshness on promotion

The benchmark record used to order the chain is re-checked against the TTL rules in
[benchmark-evidence.md](benchmark-evidence.md) at promotion time. A stale record is
refreshed, or the candidate is ranked without it. A promotion never proceeds on a
value that was valid only at routing time.

## Fail-safe

An exhausted chain leaves the job **blocked** and **terminal**. The run continues for
every job whose dependencies are unaffected. The report lists the job with the full
trigger chain, and with the `benchmark-degraded` state if ranking was degraded. The
state is never reported as `success`, `settled` or `accepted`.

The negatives: the fail-safe never substitutes a silent downgrade of controls, never
lowers a floor to find a successor, and never marks a partially produced artifact as
verified.

The tier consequences of a missing isolation capability are owned by
[safety-policy.md](safety-policy.md) and are not restated here.

## Interaction with the gate

A promoted attempt is a **new attempt** and must clear the **same** accept conditions
in [verification.md](verification.md). Promotion grants no credit from the earlier
attempt, changes no tier, and adds no approval.

A promoted attempt whose **content** then fails sends the job to the arbiter rather
than to a third runtime, so promotion cannot become a search for a passing answer.

## Recording

Every promotion records `promotionOf` and `promotionTrigger` on the new attempt, using
the attempt identity the attempt record already carries. Phase 5's trace joins them
through that identity.

This document asserts **no trace field of its own**, because
[trace-and-logging.md](trace-and-logging.md) owns the envelope.

## Degradation

- A single-candidate chain **fails safe immediately**, rather than falling back to an
  ineligible runtime.
- A chain with no eligible successor fails safe.
- When promotion is disabled by configuration, the failure is reported with its
  trigger rather than swallowed.

## Constants

| Constant | Value | Meaning |
|---|---|---|
| `MAX_PROMOTIONS_DEFAULT` | `2` | Promotions attempted when the job spec omits `fallback.maxPromotions`. |
| `MAX_PROMOTIONS_MAX` | `4` | The largest promotion budget a job spec may declare; a larger value is rejected, not clamped. |

This file is the owner. [job-spec.md](job-spec.md) validation cites it.

## Related

- [routing-policy.md](routing-policy.md) — eligibility, floors and the declared order
  this chain preserves as its head.
- [verification.md](verification.md) — the accept conditions a promoted attempt clears,
  and every escalation the "never promotes" list routes to.
- [failure-modes.md](failure-modes.md) — the failure classes, including the
  permission and authorization hard stop.
- [benchmark-evidence.md](benchmark-evidence.md) — the ranking that fills the tail,
  and its TTL rules.
- [job-spec.md](job-spec.md) — the `fallback` block, `retry.max_attempts` and the
  attempt record.
- [trace-and-logging.md](trace-and-logging.md) — the envelope that joins a promotion
  to the attempt it succeeded.
