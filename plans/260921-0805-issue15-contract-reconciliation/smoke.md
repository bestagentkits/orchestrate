# Zero-cost end-to-end smoke test

Recorded evidence for the `smoke` deliverable of issue #15. The script is
`tools/benchmark/smoke.py`; the artifact it produces is `plans/reports/issue15-smoke/`.

## What it does

It runs the **real harness** — `run_benchmark.main` — with a stub `pi` first on `PATH`. The
stub answers version and catalog probes, writes a session file in the runtime's own JSONL
shape, leaves a `route` and a `gate` record in the workspace, and exits. Nothing is mocked out
inside the harness: fixture materialization, the shim, the settle window, session accounting,
the full-schema trial record, the trace readers and the audit all execute as they do in a real
run.

The stub deliberately does **not** fix the fixture, so the grader fails. The smoke is testing
the instrumentation, not the agent, and a failing grade is an outcome that must still be
recorded, audited and reconciled.

Cost: **zero paid provider calls**. The only cost in the artifact is a fixed constant the stub
declares so the accounting path has a non-zero number to reconcile.

## Recorded result

Command (from the repository root):

```bash
PYTHONPYCACHEPREFIX=/tmp/pyc python3 -m tools.benchmark.smoke
```

```text
results records : 2
trial records   : 2
route traces    : 2 of 2
  astra-only   c3Required=False c3Reason=None evidenceScope=smoke-cohort modelFamily=model
  orchestrate  c3Required=False c3Reason=None evidenceScope=smoke-cohort modelFamily=model

audit verdict   : verified
cost mismatches : 0
token mismatches: 0
unattributed    : $0.000000 across 0 file(s)
total cost      : $0.025000 (stub-declared, no provider called)

PASS: the instrumented harness ran end to end and the accounting audit verified it
      paid provider calls: 0
```

What each line establishes:

- **2 result records and 2 trial records** — both arms ran, and the legacy results file and the
  full-schema trials file were both written.
- **2 of 2 route traces** — the trace reader found the `route` record in the workspace and its
  payload passed the trace owner's own closed-schema validation. `c3Required` was derived from
  the `gate` record rather than assumed, `evidenceScope` came from the route payload's cohort,
  and `modelFamily` was derived with its basis recorded.
- **audit verdict verified with 0 mismatches** — the recorded cost and tokens reproduce from
  the raw session files, the component split reconciles, and nothing is unattributed.
- **0 paid provider calls** — the provider matrix was not touched.

## A defect the smoke caught

The first smoke run failed on `route traces: 0 of 2`, and the cause was in the stub rather than
in the harness: the route payload had been embedded through a double `json.dumps` and a `repr`,
so the trace file carried the payload as a **string**, and the trace owner correctly refused it
because its schema requires an object. The stub was fixed to embed the mapping directly.

The failure is worth recording because it is the behaviour the contract wants: an invalid trace
payload is rejected rather than coerced, and the smoke surfaces it as a hard failure instead of
a passing run with an empty trace.

## What this smoke does not establish

- **It does not measure the skill.** The stub is not a model and takes no decision; the smoke
  proves the instrument works, not that any routing policy is better.
- **It does not exercise the grader's success path.** Both trials fail the grader by design, so
  `success=True` is never produced here. That path is exercised by the recorded benchmark run
  and by the contract tests.
- **It is not the experiment.** No arm from the manifest was run, and the paid matrix remains
  unexecuted.
