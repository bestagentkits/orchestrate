# Routing Policy

This file is the single authority for **deterministic route selection**: the
eligibility filter, capability floors, task defaults, the ranking procedure,
fallbacks, pins and reasoning controls.

Route selection has two stages. This file owns both, and states who may influence
each:

1. **Hard filter** — deterministic. Removes candidates that fail availability,
   authentication, control or floor requirements. Nothing probabilistic may
   reinstate a filtered candidate.
2. **Semantic rank** — consumes scored needs from
   [decision-plane.md](decision-plane.md) when that plane is enabled, as one
   ranking input among several, and no-ops without it.

Routing is resolved at execution time. Runtime availability, model catalogs,
aliases, permission controls and CLI flags are volatile. Never treat a model
name, provider catalog, or previous run as current evidence.

- [safety-policy.md](safety-policy.md) owns risk tiers and the safety gate. This
  file must not restate them.
- [runtime-profile.md](runtime-profile.md) owns the live evidence being filtered.
- [internal-routing.md](internal-routing.md) owns in-session dispatch mechanics
  and the internal branch's agent matching.

## Inputs

Classify every job before selecting a route:

- `task`: scout, architecture, implement, review, audit, security, test, docs, or
  mechanical;
- `importance`: normal or high;
- effect: read-only, scoped write, high-impact write, or destructive/external;
- evidence needs: structured capture, citations, test output, or artifacts;
- controls: sandbox, approval gate, tool restrictions, isolation, and timeout;
- constraints: explicit runtime/model/agent pin, budget, OS, and dependencies.

An explicit pin is a constraint, not proof that the route exists or is safe.

## Live inventory gate

Before routing any job, build the per-run inventory described in
[runtime-profile.md](runtime-profile.md) and record it in
`<run-dir>/runtimes.json`.

For each candidate, verify in the actual run environment:

1. executable or internal-agent availability;
2. non-interactive authentication readiness without exposing credentials;
3. current headless command and required flags from live help or current official
   documentation;
4. models or agents currently selectable by that runtime;
5. sandbox, approval, tool-gating, cwd, timeout, capture, and resume behavior;
6. host-OS limitations that weaken any claimed control.

Unavailable, unverified, or insufficiently controlled candidates cannot satisfy a
route merely because an older report used them.

## Capability tiers

Select the minimum capability tier that can reliably produce and verify the
expected output.

| Tier | Required behavior | Typical work |
| --- | --- | --- |
| **C1 throughput** | Accurate search, extraction, summarization, and bounded repetitive changes | scout, docs, mechanical fan-out |
| **C2 delivery** | Multi-file implementation judgment, test design, and failure-path handling | normal implementation and tests |
| **C3 judgment** | Deep trade-off analysis, conflict resolution, security reasoning, and independent arbitration | architecture, review, audit, security, arbiter |

Capability is established from the live runtime catalog, operator policy, and
recent observed evidence when available. Marketing labels alone do not prove a
tier. If a candidate cannot be classified confidently, do not assign it a
load-bearing job.

## Task defaults

These are capability and risk **floors**, not runtime or provider routes. Risk
floor definitions live in [safety-policy.md](safety-policy.md).

| Task class | Capability floor | Default risk floor |
| --- | --- | --- |
| `scout` | C1 | R0 |
| `architecture` | C3 | R0 |
| `implement` | C2; C3 when `importance: high` | R1; R2 when parallel or high-impact |
| `review`, `audit`, `security` | C3 | R0 for review-only; match the effect if fixes are included |
| `test` | C2 | R0 for design, R1 for writing or execution artifacts |
| `docs` | C1 | R1 when files change |
| `mechanical` | C1 | R1; R2 for broad or parallel edits |
| arbiter | C3 | R0 |

Raise either floor when the prompt, files, trust boundary, or expected output
demands it. Never lower a floor solely to meet a budget.

## Floor-raising rule

A semantic signal may only **raise** a floor. This is the directional constraint
that keeps a probabilistic classifier from reducing rigor:

- Either delta from the semantic router (`capabilityFloorDelta`, `riskFloorDelta`)
  may raise its floor, and each is applied as `max(declared, semantic)`
  independently of the other. A negative or lowering delta is discarded, not
  applied.
- A **capability** floor raise (`capabilityFloorDelta`) changes which candidates are
  eligible.
- A **risk** floor raise (`riskFloorDelta`) is folded into the recorded
  `riskTier` by the coordinator — the field the escalation matrix reads — and it
  **forces a C3 escalation** per [verification.md](verification.md). A signal that
  raises the risk tier can never thereby make a job eligible for the no-C3 path;
  it can only add controls and an arbiter call. The plane still never authors a
  tier: it supplies a signed delta and the coordinator applies the maximum.
- `review_independence_required` can force C3 plus independent review onto a job
  the declared `task` labelled too cheaply. It can never remove that requirement.
- A `likely_mechanical` signal can lower nothing; it may only inform ranking among
  candidates that already meet both floors.
- A user-declared `task` that understates the work is corrected upward by these
  signals, never allowed to stand because "the spec said docs".

The unconditional independence rules are owned by
[safety-policy.md](safety-policy.md) and cannot be relaxed from this file.

## Task quality floor

Capability tiers say what class of work a route may do. They do not say how good a route
must be at it. The **quality floor** says that, and it is derived from the job rather than
from the provider:

| Job property | Effect on the floor |
| --- | --- |
| Verification strength | Strong deterministic verification **lowers** it; weak verification **raises** it |
| `importance: high` | Raises it |
| Judgment work — architecture, review, audit, security, arbiter | Raises it to the top band |
| Risk tier and effect | Raises it with the tier |

| Constant | Value | Meaning |
| --- | --- | --- |
| `QUALITY_FLOOR_STRONG_VERIFICATION` | `0.50` | Floor when a wrong answer is caught deterministically |
| `QUALITY_FLOOR_WEAK_VERIFICATION` | `0.85` | Floor when the outcome is judged rather than checked |
| `QUALITY_FLOOR_JUDGMENT` | `0.90` | Floor for judgment work, and for `importance: high` |

The selection rule:

> Choose the **cheapest** route whose conservative quality estimate clears the required
> quality floor, rather than the globally strongest available route.

The binding rules:

- The quality floor operates **after** capability eligibility. It never replaces, lowers
  or restates a C1/C2/C3 capability floor, and it never replaces the risk floor.
- The estimate it compares is the conservative lower bound owned by
  [benchmark-evidence.md](benchmark-evidence.md), never a raw success rate.
- A route whose quality evidence does not exist cannot clear a floor by default. Where the
  floor cannot be evaluated, the no-record degradation applies and the ordering falls back
  to the pre-existing deterministic order.
- A higher floor can only be satisfied by better evidence or a stronger route. Nothing
  here authorizes a route the hard filter removed.

## Verification strength

Verification strength is an explicit routing input, because a route whose output will be
checked cheaply and deterministically does not have to be chosen as though it would not be.

- **Strong deterministic verification** — hidden, unit or integration tests, deterministic
  schema validation, reproducible compile or type checks, exact output comparison — may
  justify preferring a **cheaper** route.
- **Weak verification** — architecture, subjective synthesis, review, audit, security
  judgment, public-contract decisions — requires stronger outcome evidence.

This is a **ranking** rule inside the candidates that already satisfy the required tier. It
must never silently lower C2 to C1 or C3 to C2: verification strength changes which eligible
route wins, never which routes are eligible.

Failures that verification strength cannot reach are handled where they belong: escalation
by [verification.md](verification.md), promotion by [fallback-policy.md](fallback-policy.md).

## Pareto pruning

Before any semantic routing, candidates that are strictly dominated are removed
deterministically, so a model call is never spent discovering that one route is
simultaneously more expensive, slower, and no better by the available evidence.

A candidate is **dominated** when another candidate is **no worse on every comparable
dimension** and **materially better on at least one**. The dimensions are the ones this
policy ranks on: quality lower bound, expected verified cost, latency, reliability, and
expected recovery cost.

| Constant | Value | Meaning |
| --- | --- | --- |
| `PARETO_TOLERANCE` | `0.05` | Relative difference below which two values are treated as equal, so measurement noise never prunes a candidate |

The binding rules:

- Pruning is **deterministic** and **comparable**: a candidate is compared only with
  candidates whose evidence is comparable — the same cohort scope and the same accounting
  mode. Evidence that is not comparable cannot establish dominance.
- A candidate is **never pruned** when it is needed for an explicit user pin, C3
  independence, stronger controls, fallback resilience, non-comparable evidence, or a
  different accounting constraint.
- A **missing dimension prevents** pruning rather than permitting it. An unknown value is
  not a value, so dominance cannot be established on it.
- Pruning affects **ranking only**. It never removes a candidate from eligibility and never
  satisfies a floor: by construction a pruned candidate was already eligible, and a pruned
  candidate is never one the hard filter removed.
- Every prune decision is recorded in the structured trace with the dominating candidate
  and the dimensions on which it won, and every protection is recorded with its reason.
  The trace fields themselves are owned by [trace-and-logging.md](trace-and-logging.md).

## Deterministic ambiguity gate

The semantic router is called only when its answer can change a permitted decision. This
rule is deterministic, and it lives here rather than in the classifier.

| Constant | Value | Meaning |
| --- | --- | --- |
| `SEMANTIC_MARGIN_THRESHOLD` | `0.15` | Relative objective margin above which the deterministic winner cannot be overturned by a semantic signal |

Call the semantic router when **any** of these hold:

- the top candidates are materially close — the relative objective margin between the best
  and the runner-up is below `SEMANTIC_MARGIN_THRESHOLD`;
- the task classification is ambiguous;
- a semantic signal could validly **raise** a floor or add a required constraint, which is
  possible whenever the required tier is below C3, the risk tier is below R3, or
  independence is not already required;
- requirements — context, session, sandbox, independence — are not clear from deterministic
  evidence.

Otherwise **skip** it. A decisive deterministic winner with no floor left that could rise
does not need a probabilistic second opinion, and paying for one is the cost this gate
exists to remove.

The gate records `semanticRouterCalled`, `semanticRouterReason`,
`semanticRouterSkippedReason` and `candidateMargin` on the decision trace. Those fields are
closed enums and numbers, never prose, and the schema that holds them is owned by
[decision-plane.md](decision-plane.md) and [trace-and-logging.md](trace-and-logging.md).

## Expected verified cost

Selection minimises one objective, evaluated on the route rather than on a model's
reputation, and applied **only** to candidates that already passed the hard gate and both
floors:

```text
ExpectedVerifiedCost(route) =
    routingOverhead
  + workerCost
  + verificationCost
  + P(infrastructureFailure) * expectedRecoveryCost
  + P(contentFailure)        * expectedEscalationCost
  + P(c3Required)            * expectedArbiterCost
```

| Constant | Value | Meaning |
| --- | --- | --- |
| `CONSERVATIVE_INFRASTRUCTURE_FAILURE_PROBABILITY` | `0.20` | Used when no local infrastructure-failure evidence exists |
| `CONSERVATIVE_CONTENT_FAILURE_PROBABILITY` | `0.20` | Used when no local content-failure evidence exists |
| `CONSERVATIVE_C3_REQUIRED_PROBABILITY` | `1.00` | Used when C3 necessity is not established, matching "escalation is the default; acceptance is the exception" |

The binding rules:

- A **cost** term that cannot be measured makes the objective **unknown** for that route.
  It is never treated as zero: a zero asserts a measurement, and an unmeasured route would
  then look free and win on price.
- An unavailable **probability** uses the conservative default above, never zero, and the
  substitution is recorded.
- An unknown objective is **never ranked as cheap**. It can neither win nor lose a cost
  comparison; such a route falls back to the pre-existing deterministic ordering.
- The objective states the **cost dimension** each cost term is denominated in; it never
  sums one dimension into another. The dimension vocabulary is owned by
  [metrics-and-self-improvement.md](metrics-and-self-improvement.md).
- Reliability evidence may refine the probability terms, and only infrastructure-failure
  evidence may feed `expectedRecoveryCost`; a content failure must not become a retry loop.
  Promotion triggers remain owned by [fallback-policy.md](fallback-policy.md).
- The objective never adds or removes a candidate, never changes a floor or a tier, and
  never overrides the C3 escalation owned by [verification.md](verification.md).

## Routing rules

1. **Honor verified pins.** A pinned runtime, model or agent must pass the live
   inventory and risk-control gate. If it does not, block or ask before changing
   the user's explicit constraint.
2. **Fan out cheaply, decide strongly.** Use C1 for independent volume work, then
   C3 for the job that synthesizes, judges or arbitrates the outputs.
3. **Require independent judgment.** Review, audit, security and arbiter jobs
   require C3, and that review must be independent of the producer. Prefer a
   different model family or a freshly and independently configured agent. When
   live inventory proves no such route exists, the verdict is **not independent**:
   label it `not-independent` in the report and the arbiter verdict, and either
   use a fresh, independently configured context as the minimum substitute or
   block. A recorded limitation is not a substitute for independence — see
   [verification.md](verification.md), which owns the independence rule.
4. **Match controls before cost.** Filter candidates by the job's risk tier before
   comparing latency, price or convenience. An auto-approved or weakly isolated
   harness does not qualify for shared-tree writes.
5. **Use live aliases carefully.** Prefer a current stable alias or automatic
   selection mode when the runtime documents it. Pin an exact identifier only for
   a real reproducibility need, verify it immediately before dispatch, and record
   the resolved identifier in capture.
6. **Keep experimental routes non-load-bearing.** A candidate with unverified
   flags, authentication, controls or output capture may contribute advisory
   evidence only and must be paired with a verified route.
7. **Escalate expensive failure.** `importance: high` implementation requires C3
   and at least R2 controls. Use the strongest verified reasoning setting when the
   live runtime exposes one; never guess a setting or value.

## Selection procedure

For each job:

1. Determine its capability and risk floors.
2. Apply explicit user constraints.
3. Remove candidates that failed live availability, authentication, command or
   control verification.
4. Remove candidates below either floor.
5. Rank the survivors using benchmark evidence per
   [benchmark-evidence.md](benchmark-evidence.md): a candidate with a record ranks
   ahead of a candidate without one, ordered by that document's three signals. A
   candidate with no record ranks last and is never assumed average; within the
   no-record group the pre-existing deterministic ordering applies — task fit,
   control strength, evidence quality, reliability, then cost and latency — so a
   missing record degrades the ordering and never blocks it. When the decision
   plane is enabled, its floor deltas have already raised floors, and its scored
   needs order candidates within the surviving set. It never adds or restores a
   candidate.
6. Prefer independent model-family evidence for C3 review when available.
7. Record the selected runtime, resolved model or agent, the chosen `effortLevel`
   and `effortRaw`, capability tier, risk tier including its derivation, both
   floor deltas, the controls, evidence source, and fallback reason. Also record
   the benchmark record reference that ranked the choice; where no record was
   available, record that the ranking was degraded (`benchmark-degraded`) and how
   many candidates were ranked without a record.

Compare resolved model families, not executable names: two different harnesses
may invoke the same provider/model. Unknown family metadata cannot establish
different-family review. Record separately when independence comes only from a
fresh, independently configured agent context.

If no candidate qualifies, mark the job `blocked`. Do not silently weaken the
risk posture or substitute a lower capability tier.

## Internal branch

For `runtime: internal`, apply the dispatch, capture, timeout and resume mechanics
in [internal-routing.md](internal-routing.md). That file owns explicit-agent
validation, description-based matching, general-purpose fallback, and internal
model-pin handling.

This file owns only the routing consequence: an internal candidate must meet the
same floors as any other, and when model-family diversity or stronger isolation
is required but cannot be proven internally, choose a verified CLI candidate or
disclose a blocked fallback.

## Fallbacks

Evaluate `fallback_runtime` entries through the same live gate and in declared order.
Recompute the resolved model, capability tier, controls and command for the
new runtime. Never carry an identifier or flags from the failed runtime to its
fallback.

The promotion chain — its triggers, its budget, its control comparison and its
terminal fail-safe — is owned by [fallback-policy.md](fallback-policy.md), which
preserves this section's declared order as the chain's head.

A fallback is acceptable only when it meets the same capability and risk floors.
Record every substitution in `status.json` and the coordinator report.

## Reasoning controls

For C3 jobs, inspect the selected runtime's live help or current official docs for
a supported reasoning-depth control. Use the strongest setting justified by the
task and operator budget. If no verified control exists, select based on the
verified model capability tier and omit the setting. Never copy an old
configuration key or assume values are portable between runtimes.

## Selection handoff

After profiling, accept from [runtime-profile.md](runtime-profile.md):
live model or agent choices; capability evidence; permission, isolation and
timeout controls; capture confidence; OS limitations; authentication and
availability state; and cost/latency evidence when trustworthy.

This policy then filters by risk first, then capability, reliability, evidence
quality and budget. No other file may add task-to-runtime defaults or model
fallbacks.

## Worked example

"Audit a settings surface, implement the accepted fix, then review it":

| Job | Task | Required route |
| --- | --- | --- |
| map-settings | `scout` | C1/R0, live verified read-only candidate |
| design-fix | `architecture` | C3/R0, depends on map-settings |
| implement-fix | `implement` | C2/R1, or C3/R2 when marked high importance or when the semantic router raises the floor |
| review-fix | `review` | C3/R0, independent model family when live and qualified |

Exact runtime, model, agent and flags are resolved and recorded during that run;
this document does not preselect them.

## Operator checklist

- `runtimes.json` reflects this host and this run.
- Every selected runtime and model or agent was found live.
- Capability and risk floors are recorded, including the
  `capabilityFloorDelta` and `riskFloorDelta` applied, and a non-zero
  `riskFloorDelta` was escalated to C3.
- No candidate relies on a copied provider catalog or stale command example.
- Permission bypasses are disabled. A runtime's bypass option is never enabled;
  the path for a job that needs more privilege is a scoped permission with
  explicit approval, a stronger external boundary, or `blocked` — all owned by
  [safety-policy.md](safety-policy.md).
- Fallbacks meet the same floors as their primary route, and the promotion chain
  that produces them is owned by [fallback-policy.md](fallback-policy.md).
- A fallback never weakens a control to restore availability, and a
  verification failure escalates rather than promoting.
- Benchmark evidence may not set eligibility, a floor, a tier, a control or an
  approval, and a candidate the hard filter removed is never restored by a good
  score. It ranks the survivors and nothing more. Where ranking was degraded, the
  report says so with `benchmark-degraded`.
- The arbiter is C3, and its independence is either proven from live model-family
  evidence or the verdict is labeled `not-independent`.
