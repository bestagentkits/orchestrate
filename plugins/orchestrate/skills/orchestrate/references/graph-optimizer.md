# Graph Optimizer

This file is the single authority for **reducing the accepted job graph** before
dispatch. Its purpose is cost: fewer jobs, less token spend, fewer agents doing
overlapping work.

It is a cost optimization, not a safety mechanism. Where it disagrees with a
safety or independence rule, the safety rule wins and the reduction is refused.

- [routing-policy.md](routing-policy.md) owns floors and eligibility. The
  optimizer runs **after** routing.
- [safety-policy.md](safety-policy.md) owns the rules every reduction must
  respect, and the decisions no automated signal may make.
- [decision-plane.md](decision-plane.md) owns the graph-relation task that
  proposes relations.
- [job-spec.md](job-spec.md) owns the prepared input the reduction is frozen into.

## Position in the pipeline

```text
job graph → live inventory/profile → safety gate
  → hard filter → semantic rank
  → graph optimizer          ← here, post-routing
  → dispatch
```

The optimizer runs after routing because it consumes the router's
`review_independence_required` signal along with the derived tiers. Running it
earlier would mean re-sequencing work before knowing which independence
requirements apply, which is how a cost optimization silently removes a review.

Graph **construction** remains System-2 work: the planner authors the graph, and
the optimizer proposes reductions to it. The optimizer never authors a plan.

## Relation classification

For each pair of declared jobs, the decision plane proposes one relation from a
closed set, with a confidence.

| Relation | Meaning | Reduction |
| --- | --- | --- |
| `same_work` | The pair produces the same artifact for the same intent | Merge into one job |
| `overlapping` | Substantially shared input or output, but not identical | Merge when the merge algebra allows; otherwise sequence |
| `dependency` | One requires the other's output | Add or confirm an edge |
| `independent` | No shared input, output, or ownership | Keep parallel |
| `conflicting_write_scope` | `owned_paths` intersect | **Never merge.** Sequence, or assign separate worktrees with an explicit integration step |

A relation is a **proposal** with a confidence. The rules below are the decision.

## Reduction rules

1. Merge `same_work` pairs only when the merge algebra below permits it.
2. Sequence `dependency` pairs; never run them in the same stage.
3. Leave `independent` pairs parallel. Do not serialize them for tidiness.
4. Never merge `conflicting_write_scope` pairs. Route them through the worktree
   and ownership rules in [safety-policy.md](safety-policy.md), or sequence them.
5. Refuse any reduction that would weaken `review_independence_required`, reduce
   the number of independent reviews below what the router demanded, or collapse
   a review job into the job it reviews.
6. Refuse any reduction across differing risk tiers, differing `effect`,
   differing `agent`, differing `model`, differing `skill`, differing
   `isolation`, differing `authority` scope, or any pair where either member
   carries an explicit runtime pin.
7. Refuse any reduction that would remove the last C3 route for a C3-floored job.

Cost never justifies a reduction that fails any rule above. A saving that
weakens independence is not a saving.

## Merge algebra

When a merge is permitted, the merged job is derived field by field. Every
dimension resolves toward the stricter value; none is inherited from an
arbitrary member.

| Dimension | Resolution |
| --- | --- |
| `effect` | Maximum (strictest effect of any member) |
| risk tier | Maximum |
| `importance` | Maximum |
| `isolation` | Worktree if any member requires it, or stronger |
| `approval` | Strictest |
| `allowed_tools` | **Intersection** |
| `disallowed_tools` | **Union** |
| `checks`, `verification` | **Union** — every member's checks survive |
| `outputs` | Union |
| `timeout` | At least the maximum member timeout |
| `retry` | The most conservative policy of any member |
| `depends_on` | Union, minus internal edges between merged members |
| `authority` | Refuse to merge when scopes differ |
| `model`, `agent`, `skill` | Refuse to merge when they differ |

The asymmetry is deliberate: risk and permission dimensions widen to the
strictest member, and capability dimensions are never silently substituted.

## Hard limits

The optimizer may only **reduce or re-sequence declared jobs**. It never:

- invents a job, an artifact, or an output;
- adds an edge that creates a cycle;
- changes a job's capability or risk tier;
- removes a declared check, verification command, or output;
- merges across an explicit pin or a differing authority scope;
- weakens an independence requirement;
- deletes a job that is the sole reviewer of another job;
- act as an authority on safety. Every refusal it makes is a safety-policy
  refusal, not its own judgment.

## Approval and materialization

A merge is an **amendment to the prepared input**, not a silent rewrite and not a
trace-only event.

- The reduction is proposed with its evidence: the pair, the relation, the
  confidence, the applied algebra, and the reason any reduction was refused.
- The **coordinator** is the rejecter. There is no "system rejects" state; the
  reduction is applied only as an approved amendment.
- The accepted reduction is **materialized into the private immutable resolved
  input** that [job-spec.md](job-spec.md) owns, before dispatch. Downstream
  stages see the reduced graph as the declared graph.
- The prepared-input rules still hold after reduction: unique job ids, acyclic
  dependencies, no write overlap, bounded timeouts, verified runtimes. A
  reduction that would break one is refused by validation.

## Resume

- **Resume never re-optimizes.** The recorded reduction is reused as-is.
- If a re-run of the optimizer would produce a different reduction, that requires
  a **new run id**. It never mutates an existing run, because `state.json`
  attempt ids, worktrees and accepted artifacts are bound to the reduced graph,
  and re-writing it would orphan attempts and could start a second writer for
  work that already exists.
- A resumed run reconciles against the reduced graph exactly as
  [job-spec.md](job-spec.md) describes, with no optimizer pass.

## Degradation

With no eligible classifier candidate, the optimizer pass is **skipped** and
recorded as `degraded` with the reason.

It is never recorded as "no overlaps found", because that would report a skipped
analysis as a completed one. The graph goes to dispatch as declared.

## Decision trace

Every optimizer pass writes a trace per pair to `decisions.jsonl`, using the
schema in [decision-plane.md](decision-plane.md) with
`decision: graph_relation`:

- the pair and the proposed relation with its confidence;
- the reduction applied, or `none`;
- the refusal clause when refused, named from the reduction rules above;
- whether the reduction was applied, and the resulting prepared-input hash.

The trace is enumerated and carries no free-text classifier output, per
[output-layout.md](output-layout.md).
