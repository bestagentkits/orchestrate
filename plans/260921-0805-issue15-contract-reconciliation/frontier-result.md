# Worker-frontier result: the fixture does not discriminate quality

This records the first pre-registered step of the issue #15 experiment, the worker
frontier. It is the step that fixes the candidate set the router is later measured
against. The result is decisive and it narrows what the remaining steps can show.

Artifact: `plans/reports/exp15-frontier/` (360 trials, audit verified).

## What ran

Six worker arms, each a direct single-model run with no skill and the decision plane off,
over the same 20-task fixture, three trials per task.

| Arm | Success | Wilson LB | Clears strong | Clears weak | Clears judgment | $/task | Median s |
|---|---|---|---|---|---|---|---|
| `openai-codex/gpt-6-astra` | 60/60 | 0.940 | yes | yes | yes | 0.1838 | 54.7 |
| `openai-codex/gpt-5.6-terra` | 60/60 | 0.940 | yes | yes | yes | 0.0524 | 60.8 |
| `openai-codex/gpt-5.5` | 60/60 | 0.940 | yes | yes | yes | 0.1380 | 41.0 |
| `opencode-go/glm-5.3` | 60/60 | 0.940 | yes | yes | yes | 0.0362 | 31.1 |
| `opencode-go/deepseek-v4.1-flash` | 60/60 | 0.940 | yes | yes | yes | 0.0042 | 19.8 |
| `opencode-go/glm-5.3-flash` | 56/60 | 0.841 | yes | no | no | 0.0049 | 37.2 |

Total spend $25.1686 of a $150 cap. The audit reproduces the recorded accounting exactly
(0 cost mismatches, 0 token mismatches, 0 component mismatches, $0.000000 unattributed),
which makes this the first paid run in this goal whose accounting is verified rather than
rejected.

The floors are the pinned contract values: strong verification 0.50, weak verification
0.85, judgment 0.90. The Wilson lower bound is computed with the contract's own estimator,
`QUALITY_CONFIDENCE_Z = 1.96`.

## The finding: quality is nearly constant, cost is not

**Eighteen of the twenty tasks were solved by all six arms.** Only two tasks discriminated
at all, and only against one arm:

- `cli-stats-command` — `glm-5.3-flash` failed
- `csv-rfc4180` — `glm-5.3-flash` failed

Every other task is solved by every arm, including the cheapest one. Meanwhile cost spans
44x across arms that are tied on quality: `deepseek-v4.1-flash` at $0.0042 per task against
`gpt-6-astra` at $0.1838 per task, both at 60/60.

Two consequences follow, and they matter more than the ranking itself.

1. **The quality dimension is nearly a constant on this fixture.** The pre-registered
   primary metric is verified cost per successful task. With success rates at 0.93-1.00,
   that metric is very close to plain cost per task, so the experiment measures routing
   *cost* behaviour rather than quality-aware routing. The quality floors are not
   decorative — they exclude `glm-5.3-flash` under two of three tiers — but they cannot
   separate the five arms that are tied at the top.
2. **The candidate set collapses to one route under the contract's own rules.** Running the
   contract's `pareto.prune` over the measured arms with all ranking dimensions complete
   leaves exactly one survivor:

   ```text
   survivors: ['W-opencode-go-deepseek-v4.1-flash']
   ```

   It dominates the other five on `expectedVerifiedCostUsd` and `durationSeconds`, and
   dominates `glm-5.3-flash` on `qualityLowerBound` as well.

## What this licenses the ablation to test

Because the frontier is a pre-registered step and the pruning rule is part of the frozen
contract, the following is a **derived prediction**, not a post-hoc hypothesis added to the
pre-registration:

> Given this candidate set and this fixture, a correct cost-aware router should select
> `opencode-go/deepseek-v4.1-flash` for every task, and its route traces should say so.

That is a falsifiable claim about the ablation's trace payload, and it is the sharpest test
available from this fixture. It tests whether the policy's gates, floors, expected-cost
terms and pruning actually select the route the contract implies. It does **not** test
whether quality-aware routing improves outcomes, because this fixture cannot pose that
question.

A null or negative ablation result therefore has a specific reading: it would mean the
policy failed to select a route that the contract's own rules identify as dominant, not
that cost-aware routing is worthless in general.

## A usability defect found by using the contract

`pareto.prune` keys candidates by `name`. Called with candidates that carry `route` but not
`name`, it does not raise: every name is `None`, the first prune inserts `None` into
`pruned_names`, and the survivor filter then removes **every** candidate, returning
`survivors == []` and a single trace entry with `candidate: null`. Deleting the whole
candidate set is the least safe possible outcome, and it arrives silently.

This is recorded rather than fixed, for a reason that is itself part of the method: the
ablation arms V2-V5 and VN read the skill from the working tree, so any edit to the payload
between now and the ablation would change the treatment being measured. The fix belongs in
the same change as the next payload revision, not in the middle of an experiment. The
module's own docstring claims every protection is fail-closed; a missing `name` currently
fails in the one direction that removes all routes.

## Limitations

- **One trial per (arm, task) cell is not the limitation here** — three trials were run per
  cell. The limitation is the fixture: 20 tasks, 18 of which no arm fails.
- **Cost is an API-equivalent estimate, not money billed.** This account authenticates with
  an OAuth login, and the recorded per-token prices changed by roughly 66x between two runs
  of the same model (see `instrument-defects.md`, ID-7). The arms here are comparable to
  each other because they share one frozen price table; they are not comparable to the
  earlier plane-on run.
- **The candidate set is six models, not the catalog.** Fourteen candidates were probed and
  thirteen were usable; `gpt-5.3-codex-spark` is listed by the catalog and refused by this
  account, so it was excluded before any arm was planned.
- **Only one effort level was measured** (`high`), so effort is held constant rather than
  studied.
