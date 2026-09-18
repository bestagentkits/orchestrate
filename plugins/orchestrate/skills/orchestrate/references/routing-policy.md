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

- `floor_delta` from the semantic router may raise **either** floor, and is applied
  as `max(declared, semantic)` on each independent of the other. A negative or
  lowering delta is discarded, not applied.
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
5. Rank the remainder by task fit, control strength, evidence quality,
   reliability, then cost and latency. When the decision plane is enabled, its
   `floor_delta` has already raised floors and its scored needs order candidates
   within the surviving set. It never adds or restores a candidate.
6. Prefer independent model-family evidence for C3 review when available.
7. Record the selected runtime, resolved model or agent, capability tier, risk
   tier including its derivation, both floor deltas, the controls, evidence
   source, and fallback reason.

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

Evaluate `fallback_runtime` entries through the same live gate and in declared
order. Recompute the resolved model, capability tier, controls and command for the
new runtime. Never carry an identifier or flags from the failed runtime to its
fallback.

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
- Fallbacks meet the same floors as their primary route.
- The arbiter is C3, and its independence is either proven from live model-family
  evidence or the verdict is labeled `not-independent`.
