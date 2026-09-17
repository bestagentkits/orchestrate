---
phase: 5
title: "Graph optimizer"
status: pending
priority: P3
effort: 5h
dependencies: [4]
---

# Phase 5: Graph optimizer

## Goal

Reduce agent and token spend by detecting overlapping jobs in the accepted job
graph and merging or re-sequencing them, without touching the safety rules that
decide whether work may run, and without weakening an independence requirement.

## Files to Create / Modify

- Create: `references/graph-optimizer.md`
- Modify: `references/job-spec.md` (optimizer pass in validation; frozen reduction)
- Modify: `references/decision-plane.md` (graph-relation classification task)

## Tasks & Steps

1. Fix the ordering first. The optimizer consumes `review_independence_required`
   and the other router signals, so it runs **after** routing, as a pure
   post-routing re-sequencer. Correcting this matters because in the earlier
   draft the optimizer ran before the signals it was required to obey and before
   a classifier candidate existed.
2. Write `graph-optimizer.md`: the pairwise relation classification
   (`same_work`, `overlapping`, `dependency`, `independent`,
   `conflicting_write_scope`), what each relation implies, and the reduction
   rules — merge true duplicates, sequence a dependency, keep independent work
   parallel, refuse to merge any pair whose `owned_paths` intersect unless the
   `safety-policy.md` isolation rules are already satisfied.
3. State the **merge algebra** explicitly, because the earlier draft left every
   control dimension droppable:
   - **Maximum on every risk dimension** — worktree if any member needs one,
     strictest `effect`, strictest `approval`, `importance` raised to the
     highest member.
   - **Intersection on every permission dimension** — intersection of
     `allowed_tools`, union of `disallowed_tools`, union of `checks` and
     `verification`.
   - **Refuse to merge** when `model`, `agent`, `skill`, `isolation` or
     `authority` differ, when risk tiers differ, or when any member carries an
     explicit runtime pin.
   - **Never weaken** `review_independence_required`; a reduction that saves
     latency by collapsing an independence requirement is refused outright.
4. Make a merge an **approval-gated amendment to the prepared spec**, not a
   trace-only event, and make it survive resume:
   - the reduction is materialized into the private immutable resolved input
     that `job-spec.md` owns, before dispatch;
   - **resume never re-optimizes**; a re-run of the optimizer that would produce
     a different reduction forces a new run id, so `state.json` attempt ids and
     worktrees are never orphaned;
   - a proposed merge is recorded with its evidence and can be rejected by the
     coordinator; name the rejecter as the coordinator, not "the system".
5. State the hard limits: the optimizer may only reduce or re-sequence declared
   jobs. It never invents a job, never adds an edge that creates a cycle, and
   never changes a risk tier.
6. Degradation: with no classifier the optimizer pass is **skipped and recorded
   as `degraded`**, never as "no overlaps found". This keeps a cost optimization
   from being reported as an analysis result.
7. Note explicitly that graph construction remains System-2 (planner) work: the
   optimizer proposes reductions and does not author the plan.

## Verification

```bash
S=plugins/orchestrate/skills/orchestrate/references
grep -n 'never\|refuse\|reject' $S/graph-optimizer.md
grep -n 'conflicting_write_scope\|review_independence_required' $S/graph-optimizer.md
grep -n 'maximum on\|intersection on\|approval-gated\|frozen\|degraded' $S/graph-optimizer.md
grep -n 'resume never re-optimizes\|new run id' $S/graph-optimizer.md
```

- [x] The optimizer is positioned after routing in the documented pipeline.
- [x] Merge algebra takes the maximum on risk and the intersection on permission.
- [x] The reduction is materialized into the immutable input, and resume never re-optimizes.
- [x] Every reduction rule names the safety rule that can veto it.
- [x] No-classifier behaviour is recorded as `degraded`, not as "no overlaps".
- [x] The optimizer cannot introduce a job, edge, or tier change.
