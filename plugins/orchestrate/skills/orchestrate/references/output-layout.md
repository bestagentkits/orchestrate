# Output Layout

```text
<run-dir>/
  jobs.yaml             # private resolved input; do not export wholesale
  state.json            # authoritative attempts and acceptance fingerprints
  metrics.jsonl         # per-attempt observed outcomes
  runtimes.json         # current discovery and control evidence
  decisions.jsonl       # enumerated decision traces; exclude unless reviewed
  calibration.json      # per-classifier threshold, sample count and expiry
  trace.jsonl           # the correlated record; redacted on write
  report.md             # checks, arbiter verdict, integration and questions
  worktrees/<job-id>/   # isolated writes, one worktree per parallel writer; carries traceStatus
  <job-id>/
    result.md           # internal final output when declared as artifact
    artifacts/
<run-dir>/supervisor/<supervisor-run-id>/
  state.json
  graph.json            # private invocation; may contain argv/env
  events.jsonl          # bounded normalized observation journal
  output-<job-id>.log   # bounded redacted merged output
```

## Decision artifacts

`decisions.jsonl` holds the enumerated decision traces defined by
[decision-plane.md](decision-plane.md), one JSON object per decision. Every field
is a closed enum, a number, or a reference; **no free-text classifier output is
stored**. The file is excluded from diagnostic exports unless reviewed, matching
the private-invocation rule, because a trace references job inputs.

`calibration.json` is the per-classifier calibration record. Its fields, the constants it
is measured against, and the complete validity rule are owned by
[verification.md](verification.md); this file records where the artifact lives and does not
restate the rule.

A **durable** calibration record lives outside every run directory, at
`.orchestrate/calibration.json` relative to the project root, and is ignored by git. It is
not part of the run-directory tree above: it exists so a later run can reuse a record that
still satisfies the validity rule, and reuse always re-checks that rule against the current
classifier identity rather than trusting the file's presence.

Both artifacts are bounded and redacted on write, like every other capture
surface. Neither is an input to routing eligibility.

## The trace artifact and report completeness

`trace.jsonl` holds the correlated record defined by
[trace-and-logging.md](trace-and-logging.md). `report.md` carries a **`traceStatus`**
field, owned here, with the values `complete`, `partial` and `absent`, so that "the
report must say so" is implementable. A `partial` status requires the count of records
lost and the reason class from [failure-modes.md](failure-modes.md).

Record **schemas** for the trace and the decision trace belong to their owners
([trace-and-logging.md](trace-and-logging.md), [decision-plane.md](decision-plane.md)).
This document owns **where files live** and the report's completeness field, and
restates no field of those schemas. [benchmark-evidence.md](benchmark-evidence.md)
owns the one artifact that lives outside this tree.

## The durable benchmark cache

`CACHE_PATH` (`.orchestrate/benchmarks.json`) lives at the **project root**, outside
`<run-dir>/`. It is not part of a run, it is not captured by a run, and a run
directory does not contain it. It is owned by
[benchmark-evidence.md](benchmark-evidence.md), which also owns its TTL rules and the
record shape.

Because it spans runs, its entries carry `refreshedByRunId` rather than `runId`, and
they are exempt from the correlation rule that otherwise applies to every record in
every artifact. Do not try to correlate cache entries by run.

The cache holds no job content — never an input, an output, or a prompt.

## Export rules

Assemble a bounded observation bundle for diagnosis; never export a private
graph or job spec as a substitute. Internal handles and interventions belong to
the coordinator evidence and must not invent subprocess identity. Decision
traces and the calibration record follow the same exclusion rule as private
invocation files.
