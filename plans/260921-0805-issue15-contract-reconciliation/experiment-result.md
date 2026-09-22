# Experiment result: orchestration costs 6.7-9.9x the direct worker at identical success

This is the result of the issue #15 experiment: the worker frontier, then the router
ablation, run against the frozen manifest. It reports what was measured, what the
pre-registered conditions say, and — because this matters more than the headline — which
parts of the intended measurement **failed to happen at all**.

Artifacts: `plans/reports/exp15-frontier/` (360 trials), `plans/reports/exp15-ablation/`
(140 trials).

## Outcome

**Every arm solved every task. The orchestrate arms cost 6.7 to 9.9 times the direct worker
to do it.** The pre-registered improvement is not demonstrated: two of the five improvement
conditions fail, and the three that pass do so degenerately, carrying no information.

The routing mechanism the experiment was built to test **could not be measured**, because
the route trace payload the contract requires was never emitted, and because the policy had
no benchmark evidence available in its workspace. That is a finding about the design, not a
detail of it, and it is the most useful thing this run produced.

## What ran

| Stage | Trials | Spend | Audit |
|---|---|---|---|
| Worker frontier (6 models, 3 trials/task) | 360 | $25.1686 | **verified** |
| Router ablation (V0-V5 + VN, 1 trial/task) | 140 | $194.1764 | **REJECTED** |

Total $219.35 of a $400 cap. The ablation ran one trial per task rather than the
pre-registered three, by explicit decision after the frontier showed the fixture could not
discriminate quality; this makes the ablation a **pilot**, and the paired intervals below
are correspondingly weak. They are reported because they are decisive anyway: no interval
comes close to zero.

## The frontier: quality does not discriminate, cost does

Six worker arms, 20 tasks, 3 trials each. Eighteen of the twenty tasks were solved by all
six arms; only `cli-stats-command` and `csv-rfc4180` discriminated, and only against
`glm-5.3-flash`. Cost spanned 44x at equal quality: `deepseek-v4.1-flash` at $0.0042 per
task against `gpt-6-astra` at $0.1838, both at 60/60.

Full detail, including the Wilson bounds against the three quality floors and the Pareto
result, is in `frontier-result.md`. The consequence for this experiment: with success rates
at 0.93-1.00, the primary metric (verified cost per successful task) is very nearly plain
cost per task.

## The ablation: paired against the direct worker

V0 is a direct `gpt-6-astra` worker with no skill. VN is the new contract with no dispatch.
V1-V5 dispatch 9 to 12 times per trial.

| Arm | Success | $/task | Median | Dispatches | Paired saving vs V0 | 95% bootstrap CI |
|---|---|---|---|---|---|---|
| V0 | 20/20 | 0.2121 | 63.5 s | 0.0 | baseline | — |
| V1 | 20/20 | 2.0866 | 418.7 s | 10.6 | -982.4% | [-1148.1%, -826.4%] |
| V2 | 20/20 | 1.3318 | 298.9 s | 9.1 | -570.2% | [-689.6%, -468.8%] |
| V3 | 20/20 | 1.8947 | 414.3 s | 11.7 | -883.9% | [-1020.7%, -747.9%] |
| V4 | 20/20 | 1.7939 | 374.2 s | 10.7 | -813.3% | [-926.9%, -699.2%] |
| V5 | 20/20 | 1.9052 | 437.8 s | 10.8 | -887.9% | [-1029.8%, -748.0%] |
| VN | 20/20 | 0.4845 | 106.4 s | 0.0 | -151.1% | [-186.6%, -114.3%] |

Every interval lies entirely below zero, and none is near it. VN isolates the components:
the skill and directive alone cost 2.5x V0, and the dispatches account for the rest. Cost
per task is a ratio of 2.5x to 10.8x, and duration a ratio of 1.7x to 6.9x.

## The pre-registered judgement

The five improvement conditions from the frozen manifest:

| # | Condition | Verdict | Basis |
|---|---|---|---|
| 1 | Quality degradation stays inside the 5pp non-inferiority margin | **pass, degenerate** | every arm 20/20, so the difference is exactly 0 for every pair; the interval is degenerate and the condition carries no information |
| 2 | Verified-cost saving is positive and clears the 15% minimum | **FAIL** | the saving is negative for all six arms; the least bad is VN at -151% |
| 3 | No critical cohort regresses | **pass, degenerate** | no cohort regresses on success because nothing fails anywhere |
| 4 | No safety, control or independence invariant is weakened | **pass on available evidence** | the plane ran (79 `authority.json`, 80 `decisions.jsonl`); the C3 arbiter used a different model family in a fresh session |
| 5 | The accounting audit passes on the run | **FAIL** | `verify_results` returns REJECTED |

Two conditions fail. The three that pass pass because the fixture produced 100% success
everywhere, which is the degenerate direction: a fixture on which nothing fails cannot show
that a floor holds or that a cohort does not regress. Reporting them as passes would be
technically true and substantively empty.

## Why the mechanism was not measured

The experiment's sharpest prediction, derived from the frontier and the contract's own
pruning rule, was that a correct cost-aware router should select
`opencode-go/deepseek-v4.1-flash`, the single Pareto survivor. That prediction **cannot be
evaluated on this run**, for two independent reasons.

**The route trace payload was never emitted.** The contract in `trace-and-logging.md`
specifies a closed route payload carrying the selected route, the runner-up and margin, the
evidence cohort, the expected verified cost and the prune reasons. Across all 120 orchestrate
trials, `selectedModel`, `runnerUpMargin`, `evidenceCohort`, `expectedVerifiedCostUsd` and
`hardGateRejects` appear in **zero** files, including the session logs. The field names
appear in 100 files, and every one of those is a copy of the skill's own documentation
materialized into the workspace — a grep trap worth stating, because the first search I ran
read those as traces.

What the runs did produce is real but different: `decisions.jsonl` (plane decisions),
`authority.json` (egress authority), and `router-result.json` (the classifier's structured
answer). The plane works; the route payload that would let a reviewer check the routing
decision does not exist.

**The policy had no benchmark evidence to rank with.** Each trial runs in a fresh workspace
containing the fixture and the skill, and nothing else. The frontier's measurements live in
`plans/reports/exp15-frontier/`, which no trial can see. So the two-stage design — measure a
frontier, then route on it — is disconnected in this harness, and the policy correctly
reported the consequence. From one of its own reports:

> Benchmark ranking degraded: no comparable outcome/cost records. Cost and cache cost
> unknown, not zero. Usage telemetry retained where exposed in session events. Selected
> routes satisfy coordinator task-fit policy; no Pareto pruning asserted.

That is contract-compliant behaviour. With no comparable evidence, the policy must not
assert pruning, and it said so. Sixteen of 120 reports mention the degradation explicitly
and only one states that no pruning was asserted, so the declaration itself is not
systematic either.

The honest reading: the routing policy could not have selected the Pareto-dominant route on
this run, because it had no evidence and emitted no trace of its choice. The ablation
therefore measures the **overhead** of orchestration, not its routing quality.

## The audit rejection

`verify_results` returns REJECTED with 7 problems. They have two distinct causes, both
instrument-level, and both confined to one task (`pagination-bounds`):

1. **One orphan session file**, `2026-09-22T05-02-35-313Z_01a0c77e-8f30-7116-b502-abd0fd71fef6.jsonl`,
   worth $0.656086, belonging to the V1 attempt that was running when the first attempt was
   killed by a session restart. The resumed run re-ran that trial and claimed its own
   sessions, so this file is claimed by nothing. This is the `unattributed-cost` problem.
2. **A late write in V3 `pagination-bounds`.** Its own five session files sum to $1.855571
   against the $1.814090 recorded, a gap of $0.0415 (178,454 input tokens, 1,661,440 cache
   read tokens). A dispatch outlived the settle window, which is exactly the race
   `settlement-confound.md` identified and why unattributed cost is a rejection rather than
   a warning.

**Both errors make the orchestrate arms look cheaper than they were.** The orphan is
orchestrate spend that no trial claims, and the late write means V3's true cost is higher
than recorded. The headline is therefore robust to the rejection: correcting for both would
widen the gap, not close it. That is a statement about direction, not a substitute for a
passing audit, and the audit is reported as failed.

## Instrument defects, and what each would have caused

Ten defects were found and fixed in this goal. The last four were found by running the
experiment, and three of them would have produced a confident wrong answer:

| ID | Defect | What it would have caused |
|---|---|---|
| ID-3 | An extension silently re-routed the declared model | A reported 66x cost win that was the extension's substitution |
| ID-4 | `dominant_model` counted model changes instead of weighting cost | The field meant to catch ID-3 confirmed the wrong model |
| ID-5 | A provider rejection recorded as a task failure | "spark: 0/20", an availability fact reported as a quality verdict |
| ID-6 | An auth probe that invoked the model and could not fail | Readiness asserted for a provider whose model cannot run |
| ID-7 | Recorded cost is a price-table artifact | Cross-run cost comparison presented as evidence |
| ID-8 | The contamination guard flagged the treatment | "Every orchestrated arm was contaminated" |
| ID-9 | An 18-hour run died with the session | Hours bought only the trials already on disk |
| ID-10 | Any provider error treated as an unavailable model | Five successful trials recorded invalid |

ID-3 is the most dangerous: silent, cheap, and it produced a plausible positive result. ID-8
is the most instructive: a guard written to protect the experiment, applied without
discriminating on the arm's declared capability, would have invalidated every arm the
experiment exists to measure.

## Limitations

- **The ablation is a pilot.** One trial per task, not the pre-registered three. The paired
  intervals are wide in principle; they are decisive here only because the effect is large.
- **The fixture cannot discriminate quality.** 18 of 20 tasks are solved by every arm, so
  the experiment measures cost and cannot test quality-aware routing. The quality floors and
  the Wilson estimator are exercised by the contract's tests, not by this run.
- **Cost is an API-equivalent estimate, not money billed.** The account authenticates by
  OAuth. The primary metric is declared as `actualMarginalCostUsd` per the operator's
  decision; for this account that value is not money spent, and this report does not present
  it as such. Prices also changed by roughly 66x between two runs of the same model (ID-7),
  so these figures are comparable within this run and not to earlier ones.
- **The route trace is absent**, so conditions that depend on it are unverifiable and the
  routing decision cannot be audited from the artifacts.
- **The audit fails.** The run is not accounting-verified.
- **The measured configuration is skill-plus-directive**, not the skill alone, so V1 cannot
  separate the contract's rules from the harness directive's mandated workflow.
- **One effort level** (`high`) was measured, so effort is held constant rather than studied.

## What this does and does not establish

It establishes that, on a 20-task stdlib fixture that every candidate model solves, wrapping
the work in orchestration multiplied attributable cost by 2.5x to 10.8x at identical success.
The dispatch layer, not the skill text, accounts for most of it.

It does not establish that cost-aware routing is worthless. The policy never had the evidence
it needs to route on, and never emitted the trace that would show its choice. Those are
fixable preconditions, and they are the first thing a next experiment must fix: give the
policy a reachable evidence store, and require the route payload to be written, before
measuring whether it selects well.

## Unresolved questions

1. **Should the fixture be replaced?** A fixture where every arm scores 100% cannot test a
   quality floor, a cohort gate or a quality-cost trade-off. Raising task difficulty is the
   single change with the largest effect on what the next run can conclude.
2. **How should the policy receive benchmark evidence?** The frontier is currently
   unreadable from a trial workspace. Whether that means a mounted evidence store, a
   pre-seeded run-local record, or a different staging of the experiment is an open design
   decision, and it blocks the routing question.
3. **Is the missing route payload an agent-compliance failure or a contract-usability
   failure?** The contract specifies the payload; 120 trials produced none. Which side to fix
   depends on evidence this run does not contain.
4. **Should the orphan session be quarantined or kept?** It is currently kept in place, which
   is why the audit reports unattributed cost. Quarantining it would let the audit pass on
   the remaining accounting, at the cost of moving evidence out of the run directory.
