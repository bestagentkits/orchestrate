---
name: orchestrate
description: "Coordinate staged or parallel jobs across live-verified coding-agent runtimes and in-session subagents, using capability- and risk-based routing, worktree-isolated writes, resumable state, capture, safety gates, and independent arbiter review."
user-invocable: true
when_to_use: "Invoke when work should be split across multiple headless runtimes or in-session subagents, routed by task capability and risk, isolated where needed, and reviewed before handoff."
category: dev-tools
keywords: [orchestrate, headless, multi-agent, internal, subagents, live-routing, model-routing, capability, risk, worktree, resume, parallel, arbiter]
argument-hint: "<job-spec.yaml | task description | --resume <run-dir>> [--yes] [--internal]"
license: MIT
metadata:
  author: bestagentkits
  version: "1.4.0"
---

# Orchestrate

Coordinate headless coding-agent jobs and in-session subagents through a
staged, captured, resumable workflow. This is a skill-level coordinator, not a
new `ak` command or scheduler service.

Runtime and model catalogs drift. Resolve every route from live execution-time
evidence. Never treat a runtime, provider, model, alias, flag, or agent seen in
this file or an older report as currently available.

## Inputs

Accepted forms:

```bash
/orchestrate "research three implementation options and compare them"
/orchestrate "compare the auth options" --internal
/orchestrate plans/orchestrate-jobs.yaml
/orchestrate plans/orchestrate-jobs.yaml --yes
/orchestrate --resume plans/reports/orchestrate-<timestamp>
```

Use a YAML job spec for repeatable runs. For a free-form request, create a
temporary spec at `plans/reports/orchestrate-<timestamp>/jobs.yaml` before
dispatch.

`--internal` is a routing preference, not a hard mode. It asks the selection
policy to consider in-session subagents first for jobs without an explicit
`runtime:`. A job that needs a separately selectable model, stronger enforced
isolation, or a control the current harness lacks may use a live-verified CLI
fallback. Never override an explicit runtime, model, or agent pin silently.

## Authority Map

Keep durable facts in one place:

- [model-routing.md](references/model-routing.md) is the **sole route-selection
  authority**. It owns capability tiers, risk tiers, task defaults, internal
  selection, fallback qualification, and model-family independence.
- [runtime-matrix.md](references/runtime-matrix.md) owns live candidate
  discovery, probing, command verification, OS evidence, and
  `<run-dir>/runtimes.json`.
- [harness-profiles.md](references/harness-profiles.md) owns the evidence schema
  for permissions, isolation, capture, budgets, and enablement.
- [internal-routing.md](references/internal-routing.md) owns in-session dispatch,
  capture, timeout, and resume mechanics.
- [job-spec.md](references/job-spec.md) owns the YAML schema and execution-state
  contract.

Do not copy runtime or model catalogs into this file. When references disagree,
stop and report the contract mismatch.

## Pipeline

### 1. Brainstorm and intake

- Clarify the desired outcome, constraints, non-goals, and acceptance evidence.
- Read the request or job spec and identify the workspace root.
- Identify dependencies, destructive or external intent, expected outputs, and
  runtime constraints.
- Refuse any plan that would place secrets, tokens, credentials, cookies,
  private keys, dotenv values, or unrelated private data in prompts or capture.
- Prefer a direct single-agent workflow when orchestration would add no useful
  parallelism, staged dependency, runtime diversity, or arbiter value.

### 2. Build the job graph

- Convert the accepted outcome into jobs with explicit `task`, `cwd`, timeout,
  expected output, and file ownership.
- Use `depends_on` to form stages.
- Run same-stage jobs concurrently only when ownership and outputs do not
  overlap.
- Mark public-contract, security-sensitive, cross-module, or hard-to-revert
  implementation as `importance: high`.
- Set `isolation: worktree` for parallel writers, untrusted write prompts, and
  any harness whose write boundary is weaker than the job requires.
- Name the skill or instructions each headless job must load; do not rely on
  automatic skill discovery in a one-shot process.

### 3. Discover, profile, and route

- Build a live runtime inventory per
  [runtime-matrix.md](references/runtime-matrix.md).
- Profile each candidate per
  [harness-profiles.md](references/harness-profiles.md).
- Pass the live evidence and job classification to
  [model-routing.md](references/model-routing.md).
- Record the selected runtime, model or agent, capability tier, risk tier,
  controls, evidence source, and fallback reason.
- A missing, unauthenticated, unverified, or insufficiently controlled
  candidate cannot satisfy a route.
- Re-profile fallbacks and rebuild their commands; never carry model names or
  flags between runtimes.
- Mark the job `blocked` when no candidate meets both capability and risk
  floors. Never budget-route judgment or silently weaken safety.

### 4. Apply the safety gate

- Confirm every job's cwd, allowed files, writable roots, and expected side
  effects.
- Use least-privilege permission and tool controls verified on the live runtime.
- Keep every permission-bypass mode disabled by default.
- Require explicit user confirmation for `destructive: true`, deployment,
  release, deletion, credentialed access, or other external side effects unless
  the user already approved that exact scope through `--yes`.
- Treat inherently auto-approved headless modes as constrained. Limit them to
  read/report work or R2-isolated writes; never shared-tree destructive work.
- Remember that a worktree prevents edit collisions but is not an OS sandbox.
- Give every CLI process an external timeout. Treat internal timeouts as
  accounting-only unless the current harness proves cancellation.

### 5. Dispatch and capture

- Create each required worktree before dispatch and pin the job's cwd to it.
- Start independent jobs together only up to `concurrency`.
- Update `<run-dir>/state.json` on every job transition.
- For CLI jobs, capture redacted command, bounded stdout/stderr, exit status,
  wall time, artifacts, and usage when reliably reported.
- For `runtime: internal`, follow
  [internal-routing.md](references/internal-routing.md): one subagent per job,
  final text in `result.md`, resolved agent in `status.json`, and no fake
  subprocess fields.
- Mark timeout, permission prompt, unknown flag/model, or failed checks as
  failure. Do not retry silently.

### 6. Run an arbiter review

- Wait for all runnable jobs to settle.
- Use a separate C3 judgment route selected by
  [model-routing.md](references/model-routing.md).
- Prefer independently configured or different-family review when live
  evidence proves it; disclose a same-family fallback.
- Compare each result with `expected_output` and the original intent.
- Run the checks listed in the spec.
- Flag contradictions, unsupported claims, missing artifacts, safety gaps,
  timeouts, and failed checks.
- Do not summarize unverified work as complete.

### 7. Report

- Write `plans/reports/orchestrate-<timestamp>/report.md`.
- Include per-job status, selected capability/risk tier, resolved runtime and
  model or agent, artifacts, errors, arbiter verdict, checks, reproduction
  commands, worktree diffs awaiting integration, and unresolved questions.
- Append one metrics record per finished job to the cross-run history.
- Never let metrics or a previous run silently rewrite routing policy.

## Routing Invocation

After live inventory and profiling, invoke
[model-routing.md](references/model-routing.md) and record its resolved route.
Do not restate, override, or infer its task defaults, tier floors, candidate
ranking, internal-agent choice, or fallback rules elsewhere.

## Worktree Isolation

- Create one worktree per isolated job from the accepted base ref.
- Use a unique branch under the run namespace and set the job's cwd to that
  worktree.
- Never share a worktree across jobs or reuse a failed attempt without an
  explicit cleanup/recovery decision.
- Sequence jobs that must edit the same generated artifact, lockfile,
  migration sequence, or shared configuration. Separate worktrees defer those
  conflicts; they do not resolve them.
- Integration is coordinator-owned and happens only after the arbiter pass.
  Summarize diffs first; merging or cherry-picking is a separate reviewed step.
- Remove only integrated or explicitly discarded worktrees. Preserve failed
  worktrees for diagnosis and list them in the report.

## Metrics and Self-Improvement

Append one JSON line per finished job to
`plans/reports/orchestrate-history.jsonl` with:

- run id and job id;
- runtime and resolved model or agent;
- task, capability tier, and risk tier;
- duration, status, exit state, timeout, and attempts;
- arbiter verdict;
- usage/cost only when reliably reported by the harness.

Use a meaningful sample of comparable jobs before suggesting policy changes.
Include evidence-backed suggestions in the report; edit routing references only
through a separate human-reviewed change.

## Job Spec

Read [job-spec.md](references/job-spec.md) for the full schema. This abbreviated
example uses placeholders deliberately; preflight resolves them from live
evidence:

```yaml
version: 1
concurrency: 2
jobs:
  - id: scout-session-api
    runtime: internal
    task: scout
    cwd: <workspace-root>
    prompt: "Inspect the session API and report extension points."
    timeout: 10m
    expected_output: "Markdown report with files read and recommended seams."

  - id: independent-review
    runtime: <verified-cli-runtime>
    fallback_runtime: [<verified-fallback-runtime>]
    task: review
    cwd: <workspace-root>
    prompt: "Review the proposed change and verify its evidence."
    timeout: 10m
    expected_output: "Independent verdict with checks and unresolved risks."
```

Do not replace placeholders from memory. Resolve and record them during that
run.

## Safety Defaults

- Every job has an explicit cwd, timeout, expected output, and ownership.
- Capture stays under `plans/reports/orchestrate-<timestamp>/`.
- Redact secrets and sensitive values from prompts, commands, logs, and reports.
- Start with read-only or scoped-write behavior.
- Permission bypasses remain off unless the user approved the exact action and
  a stronger external isolation boundary contains the residual risk.
- Parallel writers use separate worktrees and disjoint ownership.
- Preserve failed output for diagnosis; never hide or relabel it.
- Keep destructive and credentialed external actions off prompt-only internal
  isolation.

## Output Layout

```text
plans/reports/orchestrate-<timestamp>/
  jobs.yaml
  runtimes.json
  state.json
  report.md
  worktrees/
    <job-id>/
  <job-id>/
    command.txt         # CLI jobs only
    stdout.txt          # CLI jobs only
    stderr.txt          # CLI jobs only
    result.md           # internal jobs only
    status.json
    artifacts/
    attempt-<n>/
plans/reports/orchestrate-history.jsonl
```

`status.json` records the resolved live route rather than a documented default:

```json
{
  "id": "independent-review",
  "runtime": "<resolved-runtime>",
  "model": "<resolved-model-or-null>",
  "agent": "<resolved-agent-or-null>",
  "task": "review",
  "capabilityTier": "C3",
  "riskTier": "R0",
  "status": "success",
  "exitCode": 0,
  "durationMs": 0,
  "timedOut": false,
  "attempts": 1,
  "worktree": null
}
```

## Arbiter Checklist

The final report is blocked until the arbiter answers:

- Did every required job produce its expected artifact?
- Did any job fail, time out, request permission, or emit uncertainty?
- Do outputs contradict each other?
- Were all listed checks run, and did they pass?
- Are claims supported by paths, command output, citations, tests, or artifacts?
- Did every route meet its capability and risk floor?
- Was runtime/model/agent availability revalidated for this run?
- Are destructive actions approved and reversible?
- Are unresolved questions listed plainly?

## Failure Modes

- **Missing or unauthenticated runtime:** evaluate declared fallbacks through
  the same live policy; otherwise block.
- **Missing internal agent:** re-resolve against the live agent list; use a CLI
  fallback only when it meets the same floors.
- **Unknown flag or model:** fail the attempt, return to live probe, and never
  guess a replacement.
- **Permission prompt:** stop the job and report the exact approval boundary.
- **Timeout:** preserve bounded partial output, fail the job, and block
  dependents.
- **Interrupted run:** reload `jobs.yaml` and `state.json`; keep successful
  outputs, preserve prior attempts, revalidate live routes, and redispatch only
  interrupted jobs.
- **Ambiguous ownership:** sequence the jobs or assign separate worktrees and
  an explicit integration step.
- **Reference disagreement:** stop and report the contract mismatch instead of
  choosing whichever copied route looks newer.

## Limitations

- Jobs do not share implicit memory; pass required artifacts through explicit
  dependencies.
- Internal jobs may not support force cancellation, per-job sandboxing, or
  model selection.
- CLI commands, models, authentication, and safety behavior drift; every run
  revalidates them.
- Worktrees require a git repository and disk headroom and do not provide
  process isolation.
- Metrics are advisory and cannot authorize an automatic route-policy change.
- Orchestrate coordinates existing runtimes; it does not add a daemon,
  dashboard, account pool, or provider adapter.

## Completion Report

End with:

```markdown
**Orchestrate Result**
- Spec: <path or inline request>
- Report: <plans/reports/orchestrate-.../report.md>
- Jobs: <success>/<failed>/<blocked>
- Arbiter: pass|fail|blocked
- Checks: <commands or none>

Unresolved questions:
- None
```
