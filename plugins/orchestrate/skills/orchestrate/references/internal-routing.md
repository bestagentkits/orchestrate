# Internal Runtime

`runtime: internal` dispatches a job through the current harness's in-session
subagent mechanism instead of spawning a CLI process. This file owns internal
dispatch, capture, timeout, and resume mechanics. It does not own route
selection; apply [model-routing.md](model-routing.md) to the live internal
profile and any CLI fallbacks.

Internal dispatch is useful when the current session exposes a qualified
specialist and subprocess startup would add little value. It is not a sandbox:
agents inherit the session's permission posture unless the live harness proves
stronger enforcement.

## Live Discovery

Record internal availability in `<run-dir>/runtimes.json` during preflight:

1. Query the current harness for the agent types it can dispatch.
2. Capture each available agent's live name, description, declared tools,
   permission boundary, and model metadata when exposed.
3. Use project or user agent-definition files only as supporting evidence when
   the live list is unavailable; on-disk presence does not prove session
   availability.
4. Record unknown fields as unverified. Never assume a familiar agent name is
   installed or unchanged.

Do not maintain a copied agent roster here. Installed kits and harness versions
change the available set.

## Resolution Handoff

Apply the **Internal Branch** in
[model-routing.md](model-routing.md) to the live profile. That section alone
owns explicit-agent validation, description-based matching, general-purpose
fallback, model-independence handling, and the decision to use a CLI fallback
or block.

This file receives the resolved agent and records it, plus any substitution,
in `status.json`. It must not add task-to-agent defaults or concrete model
fallbacks.

Persist the native dispatch receipt separately at
`<run-dir>/<job-id>/native-<attempt-id>.json`: job/attempt ID, actual native
handle, observed model when supplied, supported observation/intervention
operations and timestamp. This is coordinator evidence; never hand-edit
`state.json` to add an unsupported field. Resolve that saved handle through the
same host on reconnect; a missing handle is uncertainty, not permission to
launch a second writer.

## Dispatch Contract

Dispatch one subagent per job. The prompt must include:

- task and expected output;
- exact `cwd`, plus worktree path when isolated;
- files the agent may read and write;
- relevant skill path and instruction files;
- risk limits, including forbidden external or destructive actions;
- listed checks the agent may run;
- `DO NOT COMMIT OR PUSH` unless the coordinator explicitly assigned that
  authority;
- instruction to return the deliverable as the final message.

Independent same-stage jobs may launch together up to `concurrency`. Parallel
writing jobs require disjoint ownership and separate worktrees. The prompt pins
the agent to its worktree, but that remains prompt-level isolation; never treat
it as an OS sandbox.

Internal jobs must not perform `destructive: true` or credentialed external
actions unless the live harness supplies controls that satisfy the R3 policy.
When it does not, route to a qualified externally isolated candidate or block.

## Tool Boundaries

- Agent-definition tool restrictions are enforceable only to the extent the
  current harness proves them.
- Job `allowed_tools` and `disallowed_tools` are advisory prompt constraints
  unless the harness exposes per-job enforcement.
- Record whether shell, write, network, and external-tool access can be denied
  independently.
- Do not infer least privilege from a specialist name or description.

If a job needs a control the current internal harness cannot enforce, the
internal candidate does not meet that risk tier.

## Capture Mapping

Internal jobs have no subprocess surface. Map the normal capture contract as
follows:

| CLI capture | Internal equivalent |
| --- | --- |
| `stdout.txt` | `result.md`, containing the subagent's final text |
| `stderr.txt` | none; harness errors go in `status.json.error` |
| `command.txt` | none; `status.json.agent` records dispatch identity |
| exit code | `null`; `status` records success, failed, blocked, or interrupted |

Example `status.json`:

```json
{
  "id": "scout-session-api",
  "runtime": "internal",
  "agent": "<resolved-live-agent>",
  "model": null,
  "task": "scout",
  "status": "success",
  "exitCode": null,
  "durationMs": 0,
  "timedOut": false,
  "attempts": 1,
  "worktree": null
}
```

When the harness reports usage or model identity reliably, record it as
observed metadata separately from the requested route.

## Model Ownership

The live dispatch interface determines model ownership. Consequences:

- keep the agent-defined model by default;
- use a model pin internally only when the current interface explicitly
  exposes that option and its value is live-verified;
- otherwise retain the pin and select a qualified CLI route that supports it;
- do not assume two internal agents use different model families unless live
  metadata proves it;
- if independent-family review is required but unprovable internally, use a
  qualified CLI route or disclose the blocked constraint.

## Timeout

Unless the live harness exposes cancellation, internal timeouts are
accounting-only. When a job exceeds its bound:

- mark the attempt timed out but unsettled until cancellation/completion is
  confirmed; timeout accounting alone cannot free its ownership;
- do not assume the underlying agent was force-killed;
- preserve late output with its original attempt identity; accept it only
  after checking current inputs, artifacts and cancellation outcome;
- scope future prompts more tightly instead of relying on timeout enforcement.

Never dispatch a second writer into the same ownership boundary while a timed
out internal agent may still be running.

## Resume

Resume uses durable plan state like other runtimes:

- revalidate input/base fingerprints and artifact hashes before reusing success;
- reconnect to the recorded native handle when the live harness supports it;
- inspect interrupted jobs before creating another attempt; unconfirmed
  cancellation or lost handles keep writers blocked;
- native continuity, follow-up, interrupt and model selection are independent
  capabilities, each recorded as supported, unsupported or unverified;
- prior partial evidence remains under `attempt-<n>/`;
- runtime and agent availability are revalidated before the new attempt.

## Boundaries

- Fire-and-collect is the fallback for minimal harnesses. When available,
  capture intermediate events and use native follow-up/interrupt controls.
- Persist job/attempt/native handle and the reason for each intervention.
  Follow-up continues the same attempt only when scope and ownership match;
  a changed task or replacement agent requires a new attempt.
- Never claim a sent interrupt has stopped a writer until the harness confirms
  a settled state. Never synthesize PID, PGID, exit code or heartbeat.
- Multi-session teamwork and teammate messaging belong to the team workflow,
  not orchestrate.
- A single uncomplicated scout usually does not justify orchestration overhead.
- Internal agents consume the current session's resources and permission
  posture.
- Prompt-level worktree isolation prevents expected edit overlap but does not
  contain arbitrary process or network access.
