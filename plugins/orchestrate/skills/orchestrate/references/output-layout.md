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
  report.md             # checks, arbiter verdict, integration and questions; carries traceStatus
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

`calibration.json` holds the per-classifier record: the sample count, its
`minimum` (which must equal the owner-fixed `calibration.minimum_samples` in
[job-spec.md](job-spec.md)), the `threshold` (at or above the owner-fixed
`INITIAL_THRESHOLD`), the `signals` covered (which must be the full declared set,
so a harmful signal cannot be left unmeasured), the measured `agreement` (at or
above `AGREEMENT_FLOOR`), and the expiry. The constants and the complete validity
rule are owned by [verification.md](verification.md). A missing, malformed,
pooled-across-classifiers, below-floor, incomplete-signal or expired record fails
closed.

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
