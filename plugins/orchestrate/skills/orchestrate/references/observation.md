# Observation and improvement

A background agent must remain inspectable by the coordinating agent and the
operator. Visibility means durable evidence and actionable controls, not an
open terminal window. Observation, verification and a controlled comparison
complete the improvement loop.

## Before dispatch

Record the job, attempt, supervisor run or native handle, requested and observed
runtime/provider/model, owned paths, input artifacts, deadline and acceptance
checks. A command name alone does not identify the underlying model family.

Choose evidence requirements per job. Short advisory work may need a final
result only. A long-running writer needs a durable handle, bounded capture,
completion evidence and a way to confirm cancellation. If the selected runtime
cannot provide these, choose another qualified route or disclose the blocked
requirement. Do not invent a common capability all runtimes must implement.

## Observe incrementally

Read these coordinator-owned surfaces, each with its own cursor:

| Surface | Where it lives |
| --- | --- |
| Snapshot | `<run-dir>/state.json` |
| Journal page | `<run-dir>/supervisor/<supervisor-run-id>/events.jsonl`, read after a recorded sequence cursor |
| Bounded job output | `<run-dir>/<job-id>/stdout.txt`, or `output-<job-id>.log` for supervised jobs, read from a recorded byte offset |
| Observation bundle | the persisted snapshot, one journal page and the captured output assembled together |

These paths are authoritative. With the AgentKit CLI installed,
`ak orchestrate status|events|output|diagnose <run-id>` reads the same surfaces.

- Keep a cursor per supervisor run and consume every page while `has_more`.
  Deduplicate by run and sequence; attempts distinguish retries.
- Snapshot status includes `all_settled`. A failed job can have live siblings;
  their ownership remains occupied. Orphaned/unknown work is unsettled.
- The supervisor records normalized lifecycle/tool/error/artifact events and
  parent identity when the runtime exposes them. Unsupported or malformed
  provider events are not fabricated into tool success.
- Keep liveness, activity and progress separate. Process identity establishes
  liveness; output/tool events establish activity; artifact/check validation
  establishes accepted progress. Provider progress is only a reported claim.
- A timestamp is meaningful only for what actually updated it. Never turn a
  launcher timestamp into a heartbeat, or tool-call count into percent done.
- Check `truncated`, `events_truncated`, `output_truncated` and observation
  errors. Absence of events after truncation is not absence of work.
- Capture is bounded before persistence and redacted. Prefer file/stdin prompt
  transport where supported; private invocation files still contain argv/env
  and must never be exported as a diagnostic bundle.

Use bounded waits and backoff when unchanged. Report new findings, completion,
errors or requests for input; repeated unchanged polling is noise. Read output
only when the event/snapshot cannot answer the current diagnostic question.

## Intervene with evidence

Stop a supervised run through its own supervisor process and confirm settled
state. Never signal from a copied PID. For internal jobs, use live native
follow-up/interrupt when supported and retain the handle, reason and outcome in
coordinator evidence. A request sent is not cancellation confirmed.

A suspected stall warrants inspection: current tool, last output, deadline,
permission request, quota/backoff, dependency and provider error. Silence alone
must not trigger replacement. No second writer may occupy the same boundary
while the previous process or native agent is uncertain.

Continue an attempt only when its scope still matches. Scope changes, runtime
fallbacks or replacement agents produce a new attempt with refreshed route
proof. Preserve the old attempt's partial output and worktree. Existing user
authority persists within its recorded scope; a retry does not expand it.

### Watchdog signals

When the decision plane is enabled, its trace watchdog supplies scored evidence
about the attempt — whether it looks stalled, whether accepted progress is
happening, whether intervention is likely needed, and a recommended action.

Treat that as evidence feeding a deterministic rule, never as the decision:

| Watchdog signal | Deterministic action owned by this file |
| --- | --- |
| `continue` | Keep observing; take no action |
| `steer` | Send a follow-up only when the live harness has proven `steer`, and record the reason |
| `retry` | Apply the bounded retry policy in [job-spec.md](job-spec.md), only after confirmed settlement and unchanged fingerprints |
| `fallback_runtime` | Re-run the full live gate and both floors for the fallback; never inherit flags, identifiers or controls |
| `escalate` | Report to the operator with the evidence that produced the signal |
| `abort` | Abort only with the settlement evidence below. A classifier verdict alone never aborts a writer |

A watchdog verdict does not replace the settlement requirement: a quiet process
is still not proof of a stall, and a cancel request is still not proof of a
stopped writer. Record the signal, the action taken and the reason in the
decision trace defined by [decision-plane.md](decision-plane.md).

## Diagnose, replay and measure

A diagnosis bundle is a bounded persisted snapshot, one journal page, captured
output, the decision traces for the attempts involved, and explicit
missing-evidence fields. It excludes invocation/environment files. Decision
traces are enumerated and carry no free-text classifier output, but they are
also excluded from a bundle unless reviewed, because they reference job inputs.
Read the journal and output surfaces to fetch omitted pages; the live identity
check is separate. Review the bundle before sharing.

Replaying a journal reconstructs observations; it never re-executes tools or
promises deterministic model behavior. Convert the failure into a regression
case with fixed inputs, checks and a bounded budget. Compare first-pass accepted
results, artifact correctness, retries, interventions, time and observed cost.
Keep unknown usage/cost unknown and separate transport failure from bad output.

Aggregate comparable run-local metrics only. Include arbiter verdict and scope
when interpreting success rates. Better visibility supplies evidence; a verified
change and repeated evaluation establish improvement. Neither metrics nor an
agent may silently rewrite routing policy.
