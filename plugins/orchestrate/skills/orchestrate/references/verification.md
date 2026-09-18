# Verification

This file is the single authority for **acceptance**: the verification layers, the
escalation matrix that decides whether a C3 arbiter call is required, the
calibration that makes the micro-arbiter usable, the arbiter contract, and
presentation parity.

- [decision-plane.md](decision-plane.md) defines the micro-arbiter task and its
  probability outputs. It defines no acceptance rule.
- [safety-policy.md](safety-policy.md) owns risk tiers and the decisions no
  automated signal may make.
- [runtime-profile.md](runtime-profile.md) owns the control evidence referenced
  by the arbiter route check.
- [job-spec.md](job-spec.md) owns the machine fields referenced here.

## Three layers

Verification runs in order. A layer does not start until the previous one passes.

### Layer 1 — deterministic checks

Executable, reproducible, and owned by the job spec:

- every declared artifact exists, and its hash matches when an expected hash is
  declared;
- every declared `verification` command ran and exited successfully;
- the outputs do not contradict each other;
- a truncated or empty declared artifact is a failure regardless of exit status;
- the attempt is `settled` per [event-protocol.md](event-protocol.md). An
  `unsettled` attempt cannot be accepted at any layer;
- the **injection fixture** ran: a job whose output contains a hostile,
  provider-authored instruction (for example an error string that says to
  approve and re-run) must not change the declared action set, set `approval`,
  or widen a control. The check is run by the coordinator, and its result is
  recorded. Until it has run for the attempt, injection resistance is
  `unverified` and must not be described as tested.

A failing deterministic check fails the attempt. No probabilistic signal can
overrule it.

### Layer 2 — micro-arbiter

The System-1 task defined in [decision-plane.md](decision-plane.md) produces
`artifact_matches_expected_output`, `claims_supported_by_evidence` and
`materially_unresolved` as probabilities, plus `well_formed` and
`low_confidence`.

This layer produces **signals**, not an acceptance. The escalation matrix below
consumes them.

### Layer 3 — C3 arbiter

A separate judgment route from [routing-policy.md](routing-policy.md) compares
each result with `expected_output` and the original intent, runs the declared
checks, and answers the arbiter questions below.

## Escalation matrix

A **promoted attempt** is a new attempt and is evaluated from scratch: nothing carries
over from the attempt it replaced. A second content failure on a promoted attempt
escalates to C3 rather than triggering another promotion, so promotion can never become
a search for a passing answer. See [fallback-policy.md](fallback-policy.md).

Accept without a C3 call only when **all** hold:

1. the **attempt's recorded** risk tier is `R0` or `R1`, **and** no risk-floor
   raise (`riskFloorDelta`) was applied to it;
2. `importance: normal`;
3. every Layer 1 deterministic check passed and the attempt is `settled`;
4. a **valid calibration record** exists for the classifier candidate in use
   (below);
5. every micro-arbiter signal clears the recorded threshold **in its own
   direction**, per the signal-direction table below;
6. the micro-arbiter returned `well_formed: true` and `low_confidence: false`;
7. the job does not set `approval`, does not emit a dispatch, and does not mutate
   shared state outside its owned paths;
8. the **injection fixture** ran for this attempt and recorded no change to the
   declared action set;
9. the run accepts no job whose artifact is itself a **verdict** on another job's
   work — a `review`, `audit`, `security` or arbiter result.

Otherwise escalate to C3. Escalation is the default; acceptance is the exception.

**Always escalate to C3 regardless of tier**, because these are judgment:

- security, audit, or any security-sensitive change;
- **`review`, or any job whose declared artifact is a verdict on another job's
  work.** A verdict is judgment output, and a micro-arbiter is by its own
  definition not independent review evidence;
- architecture or public-contract decisions;
- `importance: high` implementation;
- external, destructive, credentialed, or otherwise hard-to-reverse work;
- parallel or untrusted-prompt writes;
- **any attempt carrying a non-zero `riskFloorDelta`**, because a probabilistic
  signal moved the tier;
- contradictory evidence between outputs or checks;
- any malformed, out-of-vocabulary, or low-confidence micro-arbiter result;
- a missing, invalid, or expired calibration record;
- **an absent or failing injection-fixture result**;
- a job that sets `approval`, emits a dispatch, or mutates shared state.

### Fail-closed rules

- A **missing or unparseable** `riskTier` is treated as `R2`, so it escalates. A
  declared `R2` or `R3` keeps its own tier and controls. This clause catches an
  absent or corrupt value; it never relabels or lowers a declared tier, so an
  `R3` job still carries the R3 controls.
- Approval changes, dispatch emission, and shared-state mutation are excluded
  **structurally**, independent of tier. They are not tier outcomes.
- The micro-arbiter can never accept a job whose `review_independence_required`
  signal is raised, and can never weaken the unconditional independence
  requirement owned by [safety-policy.md](safety-policy.md).
- A micro-arbiter acceptance is recorded with `acceptedWithoutC3: true` on the
  attempt, and the report aggregates the count. An unrecorded acceptance is a
  contract violation.

## Calibration

The micro-arbiter's threshold is only meaningful if it has been measured.

**Ground truth.** Calibration compares micro-arbiter verdicts against
**C3-audited** outcomes. Runs the micro-arbiter itself accepted are never used as
ground truth — that would measure the gate against itself.

**Scope.** Calibration is **per classifier candidate**. Records are never pooled
across runtimes, models, or providers, because agreement does not transfer
between them. A record names the candidate id it was measured on.

**Record.** `calibration.json` in the run directory carries:

| Field | Meaning |
| --- | --- |
| `classifier` | the candidate id measured |
| `threshold` | the numeric cut-off applied to each signal; must be at or above `INITIAL_THRESHOLD` |
| `signals` | which signals the threshold applies to |
| `units` | the probability scale, recorded explicitly |
| `sampleCount` | comparable C3-audited outcomes observed |
| `minimum` | the owner-fixed minimum this record was validated against |
| `agreement` | measured agreement between micro-arbiter and C3 verdicts |
| `measuredAt` | when the sample was taken |
| `expiresAt` | when the record stops being valid |

**Owner-fixed values.** These are policy constants, owned here and nowhere else.
A record cannot supply them, and a run cannot lower them.

| Constant | Value | Meaning |
| --- | --- | --- |
| `MINIMUM_SAMPLES` | `30` | Comparable C3-audited outcomes a record must carry before the no-C3 path may be used at all |
| `AGREEMENT_FLOOR` | `0.95` | Minimum measured agreement between micro-arbiter and C3 verdicts |
| `INITIAL_THRESHOLD` | `0.90` | Numeric cut-off every signal is measured against |
| `UNITS` | `probability` in `[0,1]` | Scale of every signal and of the threshold |

**Signal direction.** One threshold is applied with a per-signal direction,
because `materially_unresolved` is harmful when it is **high**:

| Signal | Clears when |
| --- | --- |
| `artifact_matches_expected_output` | `>= threshold` |
| `claims_supported_by_evidence` | `>= threshold` |
| `materially_unresolved` | `< threshold` |

"Every micro-arbiter signal clears the recorded threshold" in the escalation
matrix means exactly the comparison in this table, per signal. A signal that is
absent, non-numeric, or outside `[0,1]` is malformed and escalates.

**Validity.** A record is valid only when **all** hold:

- `classifier` names the candidate in use for this attempt;
- `sampleCount` meets `calibration.minimum_samples`, and the record's `minimum`
  equals that same value;
- that value is at or above `MINIMUM_SAMPLES`;
- `agreement` is at or above `AGREEMENT_FLOOR` — a record measuring *disagreement*
  with C3 is invalid, not merely weak;
- `threshold` is at or above `INITIAL_THRESHOLD`;
- `signals` equals the **full** declared signal set above, not a subset, so a
  harmful signal cannot be left unmeasured;
- `units` is declared;
- `expiresAt` has not passed.

A record that fails any clause is invalid and escalates. Because the floors are
constants owned here, a record cannot validate itself and a run cannot lower its
own bar by configuration.

**Expiry.** A record that has not re-validated by `expiresAt` is stale and
escalates. A threshold that never re-validates drifts into permission.

**First run.** With no valid record, the micro-arbiter **observes and logs only**
and C3 is mandatory for every job. This is a documented degraded mode, not a
failure, and it is the correct default for a fresh install.

**Changing the threshold.** Raising or lowering a threshold is a reviewed edit
backed by `metrics.jsonl` evidence and the recorded agreement rate. Neither
metrics nor any agent may silently rewrite it.

## Arbiter questions

The final report is blocked until every question is answered. The right-hand
column names the answering party. On the micro-arbiter path, `acceptedWithoutC3:
true` records that Layer 1 plus a valid calibrated micro-arbiter verdict supplied
the answer; the questions do not disappear.

| # | Question | Answered by |
| --- | --- | --- |
| 1 | Did every required job produce its expected artifact? | Layer 1 artifact existence and hash |
| 2 | Did any job fail, time out, request permission, or emit uncertainty? | `state.json` status plus normalized `error`/`permission` events |
| 3 | Do outputs contradict each other? | Layer 1 cross-output check; **forces C3** if a contradiction is found |
| 4 | Were all listed checks run, and did they pass? | Layer 1 `verification` command results |
| 5 | Are claims supported by paths, command output, citations, tests, or artifacts? | micro-arbiter `claims_supported_by_evidence` on the no-C3 path; the C3 arbiter otherwise |
| 6 | Did every route meet its capability and risk floor? | `routing-policy.md` recorded floors plus the attempt's recorded `riskTier`, including any `riskFloorDelta` applied |
| 7 | Was runtime/model/agent availability revalidated for this run? | `runtimes.json` evidence timestamps |
| 8 | Are destructive actions approved and reversible? | `safety-policy.md` authority record; **forces C3** when destructive work is in scope |
| 9 | Are unresolved questions listed plainly? | the report's unresolved-questions section; **forces C3** when any remain |

Questions 3, 8 and 9 force escalation. They are never answerable by a
probabilistic signal, because each is a contradiction, an authority fact, or an
open question — not a similarity judgment.

## Arbiter contract

A C3 verdict of `pass` requires all of:

- every required job succeeded;
- expected outputs and listed checks exist and pass;
- outputs contain no unresolved contradictions;
- claims are supported by available evidence;
- unresolved questions are absent or explicitly accepted.

The arbiter route must satisfy the judgment floor in
[routing-policy.md](routing-policy.md).

**Independence.** Independence is verified from the live inventory, never
asserted from a provider name or an executable name. Compare resolved model
families: two different harnesses may invoke the same provider and model, which
is not independent review.

This requirement is **binding**, not a preference with a disclosure fallback. When
live inventory proves no different-family route exists:

1. the verdict is **not independent** — label it `not-independent` in the arbiter
   verdict and in the report; and
2. the review may proceed only with a fresh, independently configured agent
   context as the minimum substitute; otherwise the job is `blocked`.

Recording a same-family limitation is required, and is never sufficient on its
own. [safety-policy.md](safety-policy.md) owns the rule that no automated signal
may weaken this requirement; this file owns how it is measured and reported.

A System-1 micro-arbiter verdict is **never** independent review evidence for a
C3 decision. It is a gate, not a reviewer.

## Presentation parity

This section is the **sole owner** of the parity rule.
[safety-policy.md](safety-policy.md) owns the control values; this file owns the
rule that presentation surfaces must not weaken them, and
[README.md](../../../../../README.md) reproduces the check.

Reader-facing surfaces — `README.md`, the landing page, and plugin metadata — may
summarize acceptance but must not promise more or less than this file states:

- They must not claim that every job is arbiter-reviewed, because R0/R1 work may
  be micro-arbiter-accepted under the conditions above.
- They must not state a weaker control for **any** tier than
  [safety-policy.md](safety-policy.md) defines — not only R2. Parity is checked
  for all four tiers, each against its own required clauses:

| Tier | Clause that must survive any summary |
| --- | --- |
| R0 | explicit cwd, bounded timeout, captured result, no unnecessary write or shell grant |
| R1 | scoped write boundary, tool restrictions, diff capture, no permission bypass |
| R2 | worktree **or stronger isolation**, sandbox where available, checks **and** arbiter review |
| R3 | explicit user approval, preview/rollback plan, **strongest verified controls**, block when unavailable |

- Where a summary and an authority disagree, the summary is corrected, and the
  disagreement is reported rather than resolved silently.

## Text assertions

These assertions prove that a sentence exists, that a link resolves, and that a
token is absent. They do **not** prove that R2 escalates, that a calibration
record is genuine, or that the boundary in the previous paragraph holds — a grep
cannot enforce a semantic rule, and no document in this set may claim it does.

```bash
S=plugins/orchestrate/skills/orchestrate/references
grep -n 'R0\|R1\|R2\|R3' $S/verification.md | head
grep -ni 'always escalate' $S/verification.md
grep -n 'observes and logs only\|sampleCount\|expiresAt\|C3-audited' $S/verification.md
grep -n 'acceptedWithoutC3' $S/verification.md $S/job-spec.md
# the two floors and the risk-delta escalation
# note: these two tokens also appear here, in this checklist, by design
grep -n 'riskFloorDelta' $S/verification.md $S/job-spec.md
# owner-fixed calibration floors
grep -n 'MINIMUM_SAMPLES\|AGREEMENT_FLOOR\|INITIAL_THRESHOLD' $S/verification.md
# a verdict job always escalates
grep -n 'verdict on another job' $S/verification.md
# parity covers every tier, not only R2
grep -n 'weaker control for \*\*any\*\* tier' $S/verification.md
grep -c '^| [0-9] ' $S/verification.md   # nine arbiter questions
# boundary: the accept predicate must not appear in the plane's own doc
grep -n 'accept without C3' $S/decision-plane.md && echo "FAIL: leaked" || echo "boundary clean"
```
