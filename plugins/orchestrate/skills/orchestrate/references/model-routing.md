# Model Routing

This file is the sole selection-policy authority for `/orchestrate`. It
decides which live runtime, model capability tier, and safety posture a job
needs. Other orchestrate references describe evidence collection or dispatch
mechanics and must link here instead of copying routes.

Routing is resolved at execution time. Runtime availability, model catalogs,
aliases, permission controls, and CLI flags are volatile. Never treat a model
name, provider catalog, or previous run as current evidence.

Scope: CLI runtimes and the `runtime: internal` branch. Preserve the internal
agent's configured model unless the live dispatch interface permits selection
and the user's pin or applicable routing policy requests it. Capability comes
from that interface, not a blanket assumption about all internal agents.

## Inputs

Classify every job before selecting a route:

- `task`: scout, architecture, implement, review, audit, security, test, docs,
  or mechanical;
- `importance`: normal or high;
- effect: read-only, scoped write, high-impact write, or destructive/external;
- evidence needs: structured capture, citations, test output, or artifacts;
- controls: sandbox, approval gate, tool restrictions, isolation, and timeout;
- constraints: explicit runtime/model/agent pin, budget, OS, and dependencies.

An explicit pin is a constraint, not proof that the route exists or is safe.

## Live Inventory Gate

Before routing any job, build the per-run inventory described in
[runtime-matrix.md](runtime-matrix.md) and profile each candidate with
[harness-profiles.md](harness-profiles.md). Record the result in
`<run-dir>/runtimes.json`.

For each candidate, verify in the actual run environment:

1. executable or internal-agent availability;
2. non-interactive authentication readiness without exposing credentials;
3. current headless command and required flags from live help or current
   official documentation;
4. models or agents currently selectable by that runtime;
5. sandbox, approval, tool-gating, cwd, timeout, capture, and resume behavior;
6. host-OS limitations that weaken any claimed control.

Unavailable, unverified, or insufficiently controlled candidates cannot
satisfy a route merely because an older report used them.

## Capability Tiers

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

## Risk Tiers

Risk determines the minimum harness controls independently of model
capability.

| Tier | Effect | Minimum controls |
| --- | --- | --- |
| **R0 observe** | Read/report only | Explicit cwd, bounded timeout, captured result, no unnecessary write or shell grant |
| **R1 scoped write** | Reversible edits in owned files | Scoped write boundary, tool restrictions, diff capture, no permission bypass |
| **R2 isolated write** | Parallel, high-impact, untrusted, or hard-to-revert changes | Separate worktree or stronger isolation, enforced sandbox where available, explicit checks and arbiter review |
| **R3 external/destructive** | Deploy, release, delete, credentialed, or other external side effect | Explicit user approval, preview/rollback plan, strongest verified controls; block when those controls are unavailable |

Secrets never belong in prompts, logs, inventory, or reports at any tier.

## Routing Rules

1. **Honor verified pins.** A pinned runtime, model, or agent must pass the live
   inventory and risk-control gate. If it does not, block or ask before
   changing the user's explicit constraint.
2. **Fan out cheaply, decide strongly.** Use C1 for independent volume work,
   then C3 for the job that synthesizes, judges, or arbitrates the outputs.
3. **Require independent judgment.** Review, audit, security, and arbiter jobs
   require C3. Prefer a different model family or independently configured
   agent from the primary producer when live inventory proves that diversity;
   otherwise disclose the same-family fallback.
4. **Match controls before cost.** Filter candidates by the job's risk tier
   before comparing latency, price, or convenience. An auto-approved or weakly
   isolated harness does not qualify for shared-tree writes.
5. **Use live aliases carefully.** Prefer a current stable alias or automatic
   selection mode when the runtime documents it. Pin an exact identifier only
   for a real reproducibility need, verify it immediately before dispatch, and
   record the resolved identifier in capture.
6. **Keep experimental routes non-load-bearing.** A candidate with unverified
   flags, authentication, controls, or output capture may contribute advisory
   evidence only and must be paired with a verified route.
7. **Escalate expensive failure.** `importance: high` implementation requires
   C3 and at least R2 controls. Use the strongest verified reasoning setting
   when the live runtime exposes one; never guess a setting or value.

## Task Defaults

These are capability and risk floors, not runtime or provider routes.

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

## Selection Procedure

For each job:

1. Determine its capability and risk floors.
2. Apply explicit user constraints.
3. Remove candidates that failed live availability, authentication, command,
   or control verification.
4. Remove candidates below either floor.
5. Rank the remainder by task fit, control strength, evidence quality,
   reliability, then cost and latency.
6. Prefer independent model-family evidence for C3 review when available.
7. Record the selected runtime, resolved model or agent, capability tier, risk
   tier, controls, evidence source, and fallback reason.

Compare resolved model families, not executable names: two different harnesses
may invoke the same provider/model. Unknown family metadata cannot establish
different-family review. Record separately when independence comes only from
a fresh, independently configured agent context.

If no candidate qualifies, mark the job `blocked`. Do not silently weaken the
risk posture or substitute a lower capability tier.

## Internal Branch

For `runtime: internal`:

- validate an explicit `agent:` against the live agent list;
- otherwise match the job's task and expected output to live agent
  descriptions and declared tools, choosing the most specific qualified
  agent;
- use a general-purpose agent only when it is present and meets the risk tier;
- honor `model:` only when the live internal dispatch interface supports that
  exact selection; otherwise preserve the pin and use a qualified CLI route;
- when model-family diversity or stronger isolation is required but cannot be
  proven internally, choose a verified CLI candidate or disclose a blocked
  fallback.

Dispatch and capture mechanics live in
[internal-routing.md](internal-routing.md).

## Fallbacks

Evaluate `fallback_runtime` entries through the same live gate and in declared
order. Recompute the resolved model, capability tier, controls, and command for
the new runtime. Never carry an identifier or flags from the failed runtime to
its fallback.

A fallback is acceptable only when it meets the same capability and risk
floors. Record every substitution in `status.json` and the coordinator report.

## Reasoning Controls

For C3 jobs, inspect the selected runtime's live help or current official docs
for a supported reasoning-depth control. Use the strongest setting justified
by the task and operator budget. If no verified control exists, select based on
the verified model capability tier and omit the setting. Never copy an old
configuration key or assume values are portable between runtimes.

## Worked Example

"Audit a settings surface, implement the accepted fix, then review it":

| Job | Task | Required route |
| --- | --- | --- |
| map-settings | `scout` | C1/R0, live verified read-only candidate |
| design-fix | `architecture` | C3/R0, depends on map-settings |
| implement-fix | `implement` | C2/R1, or C3/R2 when marked high importance |
| review-fix | `review` | C3/R0, independent model family when live and qualified |

Exact runtime, model, agent, and flags are resolved and recorded during that
run; this document does not preselect them.

## Operator Checklist

- `runtimes.json` reflects this host and this run.
- Every selected runtime and model or agent was found live.
- Capability and risk floors are recorded.
- No candidate relies on a copied provider catalog or stale command example.
- Permission bypasses are off unless the user explicitly approved the exact
  R3 action and external isolation makes the residual risk acceptable.
- Fallbacks meet the same floors as their primary route.
- The arbiter is C3 and its independence or same-family limitation is stated.
