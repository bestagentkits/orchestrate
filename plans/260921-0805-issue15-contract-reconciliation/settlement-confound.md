# Missing pipeline settlement — skill defect or harness artifact?

This file answers the question that had to be settled before any V1 baseline could be defined:
why 22 of the 40 candidate trials wrote no `report.md`, and whether that is an artifact of the
harness directive rather than a property of the skill under test.

Source data: `plans/reports/bench-planeon` (80 trials, `results.jsonl`), the harness's own
`invocations.log`, and the trial workspaces. **No paid run was executed to answer this
question**; every number below is re-derived from records that already existed.

## The two explanations

- **Harness artifact.** The directive mandates a workflow — dispatch every unit of work as a
  headless `pi` session, use no in-session subagents, register the decision plane's classifier,
  probe the runtime — and that workflow is expensive enough that trials run out of time, budget
  or context before finishing. On this reading the failures measure the directive.
- **Candidate defect.** The skill's contract requires driving the pipeline to a settled,
  verified, reported outcome. Trials that stop before that have violated the contract
  regardless of how they were asked to work.

## The test, and why it discriminates

The two explanations make different predictions about how a failed trial ends. An artifact
exhausts a resource, so it should end at the resource boundary — a timeout, a non-zero exit, a
duration pressed against the cap. A premature stop should end *normally and early*.

| Observation | Candidate arm | Reading |
|---|---|---|
| `status` on all 40 trials | `ok` | no trial timed out |
| `agentExitCode` on all 40 trials | `0` | no trial failed to run |
| Maximum duration | 1139 s against a 1500 s cap | nothing pressed the boundary |
| Mean duration, failures | 433 s | failures stopped **earlier** than successes |
| Mean duration, successes | 716 s | successes used more of the budget |
| Probe calls per trial, failures | 8.2 | probe traffic does not separate the groups |
| Probe calls per trial, successes | 7.6 | the directive's probe step is not the discriminator |
| Session dispatches per trial, failures | 3.0 | dispatch volume does not separate the groups |
| Session dispatches per trial, successes | 3.5 | |

The baseline arm is the control: it ran the same fixture, the same shim, the same 1500 s cap
and the same grader, with no orchestrate directive, and succeeded **40/40**. The harness is
therefore demonstrably satisfiable on these tasks.

**Verdict: the harness-artifact explanation is refuted.** No resource was exhausted; the
failures are faster than the successes and end cleanly, which is what a premature stop looks
like, not what exhaustion looks like.

## What the candidate arm did produce

Artifacts were located recursively, because the skill writes under `plans/reports/` rather than
at the workspace root — an earlier check that looked only at the root reported zero for both
arms and was wrong.

| Artifact | astra-only (40) | orchestrate (40) |
|---|---|---|
| `jobs.yaml` | 0 | 40 |
| `decisions.jsonl` | 0 | 40 |
| `runtimes.json` | 0 | 40 |
| `state.json` | 0 | 39 |
| `report.md` | 0 | 18 |
| `result.md` | 0 | 14 |

The baseline arm writes none of the skill's artifacts, as expected. The candidate arm started
the pipeline in 40 of 40 trials and recorded state in 39, but settled in fewer than half.

Cross-tabulated against the grader:

| `report.md` | success | failure |
|---|---|---|
| present (18) | 15 | 3 |
| absent (22) | 1 | 21 |

So 15 of 16 successes settled the pipeline and 21 of 24 failures did not. This is the same
83%-versus-5% separation seen earlier, now reproduced with the artifact search corrected.

Cross-tabulated against state:

| `state.json` | success | failure |
|---|---|---|
| present (39) | 16 | 23 |
| absent (1) | 0 | 1 |

That is the sharpest single result: **23 trials recorded pipeline state and still did not reach
a verified outcome.** The skill began, persisted, and did not finish the job it had started.

## Finding

The missing settlement is a **candidate defect, not a harness artifact**. Trials end cleanly and
early with the pipeline state written and the work unverified, which matches the behaviour the
harness had already caught once (a candidate that stopped after planning). The directive's
probe and dispatch requirements are not the discriminator: probe and dispatch volumes are
essentially identical between the groups that succeeded and the groups that did not.

## The confound that remains, stated rather than resolved

The directive is not the skill. It mandates headless `pi` dispatch, forbids in-session
subagents, and requires registering the decision plane, so the measured arm is *skill plus
directive*. This analysis separates "resource exhaustion" from "premature stop"; it cannot
separate "the skill's contract is not driven to completion" from "the directive's mandated
workflow induces the premature stop".

Separating those requires a V1 arm that runs the same skill under a directive without the
dispatch mandate, which is a paid experiment and therefore out of scope here. **This is
recorded as a required element of the V1 definition in the experiment manifest**, so the
confound cannot quietly disappear into a baseline that never tested it.

## Consequence for V1

- V1 must not be reported as "the skill's policy", because the measured configuration is
  skill-plus-directive. The manifest names the arm accordingly.
- The settlement rate (18/40 here) is a first-class outcome for the router ablation, not a
  footnote: a policy that lowers cost per completed trial while raising the non-settlement rate
  has not saved anything, and the pre-registered metric must be cost per *successful* task.
- The accounting audit's nested-dispatch warning is resolved by the same evidence: the shim log
  shows 320 of 450 invocations were probes (`--help`, `--version`, `--list-models`, `auth
  check`), which create no session by design. The dispatch-versus-session-file gap is probe
  traffic, not a snapshot race, so no accounting correction is owed for it.
