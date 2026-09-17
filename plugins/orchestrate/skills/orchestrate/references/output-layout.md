# Output Layout

```text
<run-dir>/
  jobs.yaml             # private resolved input; do not export wholesale
  state.json            # authoritative attempts and acceptance fingerprints
  metrics.jsonl         # per-attempt observed outcomes
  runtimes.json         # current discovery and control evidence
  decisions.jsonl       # enumerated decision traces; exclude unless reviewed
  calibration.json      # per-classifier threshold, sample count and expiry
  report.md             # checks, arbiter verdict, integration and questions
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

`calibration.json` holds the per-classifier threshold with its sample count, its
`minimum` (which must equal the owner-fixed `calibration.minimum_samples` in
[job-spec.md](job-spec.md)), and its expiry. These are owned by the escalation
matrix in [verification.md](verification.md). A missing, malformed,
pooled-across-classifiers or expired record fails closed.

Both artifacts are bounded and redacted on write, like every other capture
surface. Neither is an input to routing eligibility.

## Export rules

Assemble a bounded observation bundle for diagnosis; never export a private
graph or job spec as a substitute. Internal handles and interventions belong to
the coordinator evidence and must not invent subprocess identity. Decision
traces and the calibration record follow the same exclusion rule as private
invocation files.
