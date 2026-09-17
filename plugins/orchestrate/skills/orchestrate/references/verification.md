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

Accept without a C3 call only when **all** hold:

1. the **recorded** risk tier is `R0` or `R1`;
2. `importance: normal`;
3. every Layer 1 deterministic check passed and the attempt is `settled`;
4. a **valid calibration record** exists for the classifier candidate in use
   (below);
5. every micro-arbiter signal clears the recorded threshold;
6. the micro-arbiter returned `well_formed: true` and `low_confidence: false`;
7. the job does not set `approval`, does not emit a dispatch, and does not mutate
   shared state outside its owned paths.

Otherwise escalate to C3. Escalation is the default; acceptance is the exception.

**Always escalate to C3 regardless of tier**, because these are judgment:

- security, audit, or any security-sensitive change;
- architecture or public-contract decisions;
- `importance: high` implementation;
- external, destructive, credentialed, or otherwise hard-to-reverse work;
- parallel or untrusted-prompt writes;
- contradictory evidence between outputs or checks;
- any malformed, out-of-vocabulary, or low-confidence micro-arbiter result;
- a missing, invalid, or expired calibration record;
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
| `threshold` | the numeric cut-off applied to each signal |
| `signals` | which signals the threshold applies to |
| `units` | the probability scale, recorded explicitly |
| `sampleCount` | comparable C3-audited outcomes observed |
| `minimum` | the owner-fixed minimum this record was validated against |
| `agreement` | measured agreement between micro-arbiter and C3 verdicts |
| `measuredAt` | when the sample was taken |
| `expiresAt` | when the record stops being valid |

**Minimum sample.** The minimum is **owner-fixed, not self-declared**: it is the
`calibration.minimum_samples` run-policy field defined in
[job-spec.md](job-spec.md), independent of any record. A
record is valid only when `sampleCount` meets that fixed minimum **and** its
`minimum` field equals it. A record that omits the field, or declares a lower
minimum than the policy value, is invalid and escalates — otherwise a record
would validate itself.

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
| 6 | Did every route meet its capability and risk floor? | `routing-policy.md` recorded floors plus the recorded `riskTier` |
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
is not independent review. When only a same-family route is available, disclose
it explicitly and record it as a limitation.

A System-1 micro-arbiter verdict is **never** independent review evidence for a
C3 decision. It is a gate, not a reviewer.

## Presentation parity

Reader-facing surfaces — `README.md`, the landing page, and plugin metadata — may
summarize acceptance but must not promise more or less than this file states:

- They must not claim that every job is arbiter-reviewed, because R0/R1 work may
  be micro-arbiter-accepted under the conditions above.
- They must not state a weaker R2 control than
  [safety-policy.md](safety-policy.md) defines.
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
grep -c '^| [0-9] ' $S/verification.md   # nine arbiter questions
# boundary: the accept predicate must not appear in the plane's own doc
grep -n 'accept without C3' $S/decision-plane.md && echo "FAIL: leaked" || echo "boundary clean"
```
