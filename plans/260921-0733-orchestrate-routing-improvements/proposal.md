# Routing and cost improvements for the `orchestrate` skill

An evidence-based proposal. Every claim below is tied to a measurement in
`plans/reports/bench-planeon/`, and the parts that the measurement contradicts are
stated as refuted rather than quietly dropped.

## Contract

**Outcome.** `orchestrate` completes more jobs at lower cost per successful task,
using model and provider routing as a lever that actually moves the number.

**Constraints.**
- The repository's central invariant holds: no benchmark value, model name, flag,
  version number or leaderboard row may be copied into the skill payload. This
  document lives outside the payload and proposes changes in prose.
- `routing-policy.md` owns eligibility, capability floors, task defaults and the
  ranking procedure. One owner per concern: this proposal must change the owner
  or add nothing.
- `routing-policy.md`: "Never lower a floor solely to meet a budget." No proposal
  here trades a floor for a price.
- Nothing probabilistic may set eligibility, a floor, a tier or an approval.

**Non-goals.**
- Not a rewrite of the routing policy, and not a new routing mechanism.
- Not a claim that the decision plane caused any of this. It did not.
- Not a proposal to re-run the benchmark; the measurement needed is named where
  a change cannot be justified without it.

**Acceptance criteria.** A change is complete when it is stated in its owning
reference, the assertion in `docs/maintaining-the-docs.md` that guards that
concept is updated, and the sweep runs green from the repository root. Where the
change alters routing behaviour, the accompanying measurement must report
cost per **successful** task, not cost per attempt.

## What the measurement found

Twenty tasks, two trials, two variants, 80/80 trials, $205.31 of a $400 cap.

| | `astra-only` (baseline) | `orchestrate` |
| --- | --- | --- |
| Success | 40/40 (100%) | 16/40 (40%) |
| Cost per attempt | $1.01 | $4.09 |
| Cost per **successful** task | $1.01 | $10.23 |
| Median duration | 134 s | 515 s |

Paired across 40 pairs: the skill was cheaper on **0/40**, faster on **0/40**, won
**0/40** and tied 16. Mean cost delta +$3.08, mean duration delta +409 s.

Two caveats carried forward. The audit gate `verify_results` rejects this run:
nine candidate trials understate cost by 0.6% because a dispatch that outlives its
parent trial keeps writing to its session file after the trial snapshots cost.
The bias understates the candidate, so the negative result is robust to it. And
the plane was wired by the harness rather than enabled out of the box, so nothing
here is the plane's isolated contribution.

## Diagnosis

Three explanations were candidates. Two do not survive contact with the data.

**Refuted: dispatching to cheaper or weaker models caused the failures.** This was
the working hypothesis and it is wrong. Success by model used, across the
candidate arm:

| Model used in the trial | Trials | Succeeded |
| --- | --- | --- |
| `openai-codex/gpt-5.5` | 30 | 14 (47%) |
| `deepseek/deepseek-v4-pro` | 22 | 11 (50%) |
| `opencode-go/deepseek-v4.1-flash` | 17 | 8 (47%) |
| the coordinator itself | 40 | 16 (40%) |

Every dispatch model succeeded at least as often as the coordinator. Fewer models
was worse, not better: trials using four distinct models succeeded 6/12 (50%),
trials using one succeeded 1/6 (17%). Routing *quality* is not the defect.

**Not supported as a cost lever: selecting cheaper routes.** Measured cost split
inside the candidate arm:

| Component | Cost | Share |
| --- | --- | --- |
| Coordinator turns | $157.58 | **96%** |
| All dispatched work, every model | $6.24 | **4%** |

Dispatch is already cheap and already diverse. Driving dispatch cost to zero
would change total candidate cost by four percent. This is the finding that
should redirect the effort: the requested lever has almost no headroom.

**Best supported: the pipeline frequently does not settle.** Splitting candidate
trials by whether the run reached its own reporting stage:

| `report.md` written | Trials | Succeeded |
| --- | --- | --- |
| Yes | 18 | **15 (83%)** |
| No | 22 | **1 (5%)** |

Twenty-two of forty candidate trials never wrote `report.md`. In the inspected
failure, `jobs.yaml` was declared correctly — `owned_paths`, `isolation: worktree`,
a `verification` command, a model and an effort — and the decision plane answered
`reason: ok` with `review_independence_required: true` at confidence 0.99 and a
recorded `egressAuthority`. What is missing is settlement: no `state.json`, no
job `result.md`, no `report.md`, and the graded working tree still carried the
seeded defect verbatim (`datetime(2026, 1, 2, 3, 0) != datetime(2026, 1, 1, 22, 0)`).

That shape matches the contract's own timeout rule, which is the strongest
contract-level lead: `internal-routing.md` states that internal timeouts are
"accounting-only", that a timed-out attempt stays **unsettled** until
cancellation or completion is confirmed, and that ownership cannot be freed by
timeout accounting alone. The `implement` job carried `timeout: 5m` while the
trial ran 392 s across 13 dispatches. Where the harness exposes no cancellation,
an attempt that exceeds its bound has no path to a terminal state, so settlement
cannot complete and the work never reaches the graded tree — while the
coordinator keeps spending turns, which is exactly the 96% above.

**Threat to this diagnosis, stated plainly.** The harness directive required all
dispatch as headless `pi` invocations and forbade in-session subagents, to make
cost attributable. If the skill's normal settlement path depends on awaiting an
in-session subagent, my instrumentation suppressed settlement and the 22 missing
`report.md` files are partly an artifact of how I measured, not a skill defect.
The correlation is strong but observational, and this confound is not resolved by
the data I have. It must be resolved before any of P1 is implemented.

## Proposals

**P1 — Give every attempt a bounded, terminal settlement path. (Highest value;
quality.)**
Evidence: 83% success when the run reaches its reporting stage, 5% when it does
not. Change: an attempt whose bound is exceeded must reach a recorded terminal
state — `failed` or `escalated`, never "unsettled forever" — so settlement cannot
block the run. This cannot lower a floor: it may only end an attempt, which is a
narrowing. Owner: `internal-routing.md` §Timeout, with `dispatch-hardening.md`.
Risk: ending an attempt early could discard work that would have completed; the
contract already prefers tight prompts over timeout enforcement, so the change
must record the bound as an input to future prompt scoping.
Acceptance: a run where a job exceeds its bound still produces `report.md`, and
the trace shows the attempt's terminal state.
First, resolve the confound above.

**P2 — Cut the coordinator's own turn cost. (Highest value; cost.)**
Evidence: the coordinator is 96% of candidate cost, and dispatch models are not
worse than it. Change: discharge more of the pipeline inside jobs and fewer
coordinator turns — the metric to move is coordinator turns per settled job, not
dispatch price. Owner: `routing-policy.md` §Selection procedure, with
`metrics-and-self-improvement.md`.
Risk: moving work out of the coordinator can move verification out with it; the
arbiter independence requirement must not be discharged by the writer.

**P3 — Bind route selection to measured outcome evidence, not to price.**
Evidence: routing already spans five models and providers, so breadth is not the
gap; and `calibration.json` was absent in the measured run, so the plane was
uncalibrated and deterministic policy decided. Change: where
`benchmark-evidence.md` and the calibration gate already provide measured
outcome evidence, make the selection procedure consume it. Do not encode a price
preference: the invariant forbids copying values, and price is not outcome.
Owner: `routing-policy.md`; the measurement contract stays with
`benchmark-evidence.md`.

**P4 — Guard the budget rule while doing any of the above.**
Evidence: the cheapest available lever is dispatch, at 4%, which is precisely the
lever most likely to be pulled under budget pressure. Change: state in
`routing-policy.md` that a budget may end an attempt or skip optional work, and
may never lower a capability or risk floor. The rule exists ("never lower a floor
solely to meet a budget"); what is missing is that the cheapest-looking lever is
the one it must bind hardest.

## Trade-offs

**Approach A — optimise model selection for price (what was implied).**
Assumption: dispatch cost is a material share. Fails first when the share is
measured, which it now has been: 4%. Worst case: perfect routing saves 4% while
the pipeline still fails 55% of the time.

**Approach B — fix settlement first, then revisit routing.**
Assumption: failure is dominated by non-completion rather than by route choice.
Fails first if the missing-`report.md` correlation is an artifact of the harness
directive, which is unresolved. Worst case: effort spent on a defect that is mine.

**Approach C — run a cheaper coordinator model outright.**
Assumption: a cheaper model orchestrates as well. Unverified: every trial held
the coordinator constant by design, so the measurement says nothing about it, and
the trials that delegated most did best. Fails first at the acceptance gate, where
a cheaper coordinator that mis-settles is worse than an expensive one that
settles.

## Better approaches

An approach superior to the one implied was found: **settlement, not routing, is
the lever.** The implied approach optimises a component holding 4% of cost, so
its best plausible case cannot reach the stated outcome; the measured correlation
between pipeline completion and success (83% vs 5%) points at the component that
decides the result. Routing remains worth improving only after completion is
reliable, because a cheaper route into a pipeline that does not settle buys
nothing.

## What this does not claim

- The decision plane is not implicated: 122 adapter calls, zero provider errors,
  and the `router` verdicts returned `ok` with recorded egress authority.
- No claim that any dispatch model is unsuitable. The data says the opposite.
- No claim that the cost figures are exact: the audit gate rejects this run at
  0.6% understatement, in the candidate's favour.

## Unresolved

1. The harness confound. Whether missing settlement is a skill defect or an
   artifact of forbidding in-session subagents is not settled, and P1 depends on
   the answer.
2. Why the coordinator spent 96% while the pipeline failed. The 96% share is
   measured; its internal breakdown is not, so P2 has a target without a number.
3. Whether a cheaper coordinator orchestrates as well. Not measured by design.
4. The audit gate still rejects the run until the late-write race in
   `run_benchmark.py` is fixed.
