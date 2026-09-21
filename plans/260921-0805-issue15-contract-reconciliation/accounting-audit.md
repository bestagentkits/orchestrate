# Independent accounting audit — implementation and measured result

This file records the accounting audit required by issue #15 Phase 2 ("The instrument must
independently audit its own accounting") and by the implementation objective's success
criterion 12. The audit lives in `tools/benchmark/verify_results.py`; its tests live in
`tools/benchmark/tests/test_accounting_audit.py`.

## What the audit recomputes

The audit trusts no recorded figure. For every measured trial it rebuilds, from the raw
session JSONL:

- **attributable cost** — the sum of `usage.cost.total` over the session files the trial
  claims, plus any file a dispatch wrote inside the trial workspace after escaping the shim;
- **tokens** — the same fields the runtime reports (`input`, `output`, `cacheRead`,
  `cacheWrite`, `reasoning`), recomputed per trial rather than trusted;
- **nested-dispatch cost** — every `pi` invocation writes its own session file, so a settled
  trial has one file for the top-level run plus one per dispatch. Fewer files than that is
  reported, because the missing ones are cost that belongs to no trial;
- **component totals** — the coordinator/worker/classifier/arbiter split in `trials.jsonl` is
  checked twice: that it sums to its own `totalCostUsd`, and that it agrees with the cost
  recomputed from the sessions;
- **unattributed cost** — cost in the session directory that no trial claims. Above a
  rounding tolerance this rejects the run, because it means some trial's cost is understated.

## Closing the late-write race

The measured defect was that a dispatched `pi` session can outlive the trial that started it:
the parent exits while the child is still appending to its session file, so a snapshot taken
immediately after the parent exits attributes that cost to nothing. In the recorded run this
left $0.78 in the session directory that no trial claimed, and it understated the candidate
arm specifically, because the baseline arm never dispatches.

Two changes close it:

1. **A settle window.** `settle_session_dir` polls the session directory until its file count
   and total cost hold still for three consecutive reads, bounded by a timeout, and the trial
   records `settled` and `settleWaitedSeconds` so a reader can see whether it settled.
2. **The audit as backstop.** The window bounds the race; it does not abolish it. A dispatch
   that lingers longer than the quiet window is still outside the snapshot, which is why
   unattributed cost is a rejection rather than a warning. This limitation is stated in the
   tests (`test_a_writer_that_outlasts_the_quiet_window_is_missed`) rather than left implicit.

## Evidence

Run from the repository root:

```bash
PYTHONPYCACHEPREFIX=/tmp/pyc python3 -m unittest discover -s tools -t .
```

Recorded outcome: **307 tests pass**. Two mutation checks, each confirmed applied by content
hash before the suite ran:

| Mutation | Result |
|---|---|
| Remove the unattributed-cost rejection | 1 test fails |
| Remove the token reconciliation | 1 test fails |

Restore verified by content hash `42a1d2573e0abf66fd8532ec0a3e8580` before re-running the
suite, then green.

## The audit against the recorded run

`plans/reports/bench-planeon` was rejected by the original audit at 0.6%. The rebuilt audit
reproduces the rejection with more evidence:

```text
trials checked      : 80 (skipped 0)
cost mismatches     : 9
token mismatches    : 36
component mismatches: 0
recorded total      : $204.272032
recomputed total    : $205.484251
unattributed cost   : $0.784462 across 1 file(s)
46 problem(s)
RESULT: REJECTED
```

The direction is unchanged and still favours the skill: the recorded figures understate the
candidate arm, so the measured negative result is robust to the correction. The token
discrepancy is larger in relative terms than the cost discrepancy (for example `output`
12991 recorded against 19616 recomputed on one trial), which is what a snapshot taken before
late writes land looks like.

## A second finding, and what it does not establish

The audit's nested-dispatch check reports a large gap on the candidate arm:

| Arm | Trials | Session files | Dispatches logged | Successes |
|---|---|---|---|---|
| astra-only | 40 | 40 | 0 | 40 |
| orchestrate | 40 | 166 | 446 | 16 |

So 446 dispatch invocations produced at most 126 session files beyond the 40 top-level runs.
One trial logged 10 dispatches and left a single session file.

**This is a warning, not a verdict, and the audit cannot resolve it.** Two explanations fit:

- a dispatch outlived the snapshot, so its session file was written after the trial was
  measured — the race the settle window addresses; or
- the invocation was a probe rather than dispatched work (`pi --version`, a catalog probe, a
  `--help`), which is a shim invocation that legitimately creates no session at all.

The audit deliberately reports the gap without choosing between them, because choosing would
require knowing what each invocation was. That question belongs to `settlement-confound`,
which must resolve it from the shim's own invocation log before any V1 baseline is defined.
Recording the gap as a warning rather than a rejection is the honest choice: a probe-heavy
arm would be rejected for something that is not an accounting error.
