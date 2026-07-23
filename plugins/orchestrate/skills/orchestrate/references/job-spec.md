# Job Spec

`/orchestrate` accepts YAML or turns a free-form request into YAML under the
run report directory. This file owns the durable data shape and execution
semantics. It does not own a runtime roster, model catalog, or provider route.

Resolve every runtime, model, agent, flag, and safety control from live evidence
before dispatch:

- [runtime-matrix.md](runtime-matrix.md): live candidate evidence;
- [model-routing.md](model-routing.md): the sole selection policy;
- [harness-profiles.md](harness-profiles.md): control evidence;
- [internal-routing.md](internal-routing.md): in-session agent mechanics.

## Schema

```yaml
version: 1
concurrency: 2
defaults:
  timeout: 10m
  effect: observe
  approval: inherit
  capture: true
jobs:
  - id: string
    runtime: string
    agent: string
    fallback_runtime: [string]
    task: scout | architecture | implement | review | audit | security | test | docs | mechanical
    importance: normal | high
    model: string
    cwd: string
    prompt: string
    skill: string
    allowed_tools: [string]
    disallowed_tools: [string]
    effect: observe | scoped-write | high-impact-write | external-destructive
    approval: inherit | require
    isolation: none | worktree
    timeout: 10m
    expected_output: string
    depends_on: [job-id]
    destructive: false
    checks: [string]
```

Candidate identifiers are opaque strings until the current run verifies them.
`agent` is meaningful only for in-session dispatch. `skill` is meaningful only
for the AgentKit skill-run branch. Do not copy a candidate list into this file.

`effect` and `approval` are normalized coordinator intent, not runtime flags.
The live harness profile maps them to verified native sandbox, permission, and
approval controls. Block a route when no verified mapping meets its risk tier.

## Required Fields

Every job includes:

- `id`, `runtime`, and `cwd`;
- exactly one executable intent through `prompt` or `skill`;
- `timeout` or `defaults.timeout`;
- `expected_output`;
- `model` or a routable `task`.

When `model` is present it is an explicit constraint, not proof of availability.
The live inventory gate still applies. An internal agent owns its configured
model, so internal jobs do not set `model`.

`isolation: worktree` is required for parallel writers in one repository and
for any write whose verified harness controls do not otherwise satisfy the
assigned risk tier. Worktree isolation prevents edit collisions; it does not
claim to be an operating-system sandbox.

`importance: high` raises capability and risk floors according to
[model-routing.md](model-routing.md). This schema never names the resulting
model or reasoning setting.

## Validation

Before stage construction:

1. Reject duplicate or unsafe job IDs and unknown dependency IDs.
2. Reject dependency cycles.
3. Resolve `cwd` and ensure it stays within the authorized workspace.
4. Require bounded timeout and capture for every job.
5. Verify each primary and fallback runtime in the live matrix.
6. Map effect, approval, and tool constraints to verified native controls.
7. Verify explicit model and agent constraints.
8. Reject parallel write overlap unless file ownership is disjoint and each
   writer has the required isolation.
9. Stop for explicit approval before destructive or external side effects.

Unknown flags, models, or controls fail validation. Re-read live help or current
official documentation; never guess a replacement.

## Execution Semantics

- Jobs with no dependencies form the first stage.
- A job starts only after every dependency succeeds.
- A stage may run up to `concurrency` jobs when ownership and isolation allow.
- Failed or timed-out dependencies block their dependents.
- A failed job is not retried unless the user explicitly requests it.
- Fallback selection reruns the full capability and risk gate for that runtime.
- Every state transition is atomically persisted before the next dispatch.

## Run State And Resume

`<run-dir>/state.json` is the tracker:

```json
{
  "runId": "<run-id>",
  "specPath": "jobs.yaml",
  "jobs": {
    "<job-id>": {
      "status": "queued|running|success|failed|blocked|interrupted",
      "runtime": "<verified-runtime>",
      "model": "<resolved-model-or-null>",
      "agent": "<resolved-agent-or-null>",
      "attempts": 1,
      "startedAt": "<timestamp-or-null>",
      "endedAt": null,
      "worktree": "<path-or-null>"
    }
  }
}
```

On resume:

- reuse successful outputs;
- convert interrupted `running` work to `interrupted` and preserve its partial
  capture under an attempt directory;
- require fresh approval before redispatching destructive work;
- recompute blocked jobs from current dependencies and live runtime evidence;
- rerun the arbiter whenever any reviewed job reruns.

## Capture Contract

CLI jobs write bounded, redacted capture:

```text
<run-dir>/<job-id>/
  command.txt
  stdout.txt
  stderr.txt
  status.json
  artifacts/
```

In-session jobs have no process surface. They write `result.md` plus
`status.json` with the resolved agent and a null process exit code. Never put
tokens, cookies, credentials, raw environment values, or private keys in any
capture. Mark truncation and preserve the first and last useful sections.

## Arbiter Contract

The coordinator reports `Arbiter: pass` only when:

- every required job succeeded;
- expected outputs and listed checks exist and pass;
- outputs do not contain unresolved contradictions;
- claims are supported by available evidence;
- unresolved questions are absent or explicitly accepted.

The arbiter route must satisfy the judgment floor in
[model-routing.md](model-routing.md). Independence is verified from the live
inventory, not asserted from a copied provider name.

## Illustrative Spec

Placeholders below must be resolved and verified before dispatch.

```yaml
version: 1
concurrency: 2
jobs:
  - id: scout-contract
    runtime: "<verified-read-runtime>"
    task: scout
    cwd: "<workspace-root>"
    prompt: "Map the contract owners and cite source evidence."
    timeout: 8m
    expected_output: "Source-backed contract map."

  - id: inspect-tests
    runtime: "<verified-read-runtime>"
    fallback_runtime: ["<verified-fallback-runtime>"]
    task: test
    cwd: "<workspace-root>"
    prompt: "Identify copied inventories and propose source-derived gates."
    timeout: 8m
    expected_output: "Test-coupling report with file evidence."

  - id: arbiter
    runtime: "<verified-judgment-runtime>"
    task: review
    cwd: "<workspace-root>"
    prompt: "Reconcile both reports and reject unsupported claims."
    depends_on: [scout-contract, inspect-tests]
    timeout: 8m
    expected_output: "Verified arbiter verdict."
```

The schema stays stable while live routing changes. Update the owning routing or
runtime reference when selection policy or evidence changes; do not refresh
examples with a new catalog.
