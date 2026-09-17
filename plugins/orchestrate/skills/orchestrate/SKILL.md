---
name: orchestrate
description: "Coordinate staged or parallel jobs across live-verified coding-agent runtimes, agent sessions, and in-session subagents, using capability- and risk-based routing, worktree-isolated writes, resumable state, capture, safety gates, and independent arbiter review. Onboards a missing Pi runtime (install, profile, authentication, kit projection) as a visible setup step when a job or the user asks for Pi."
user-invocable: true
when_to_use: "Invoke when work should be split across multiple headless runtimes, agent sessions, or in-session subagents, routed by task capability and risk, isolated where needed, and reviewed before handoff; also when Pi must be installed and set up before it can take orchestrated jobs."
category: dev-tools
keywords: [orchestrate, headless, multi-agent, internal, subagents, pi, pi-sessions, onboarding, live-routing, model-routing, capability, risk, worktree, resume, parallel, arbiter]
argument-hint: "<job-spec.yaml | task description | --resume <run-dir>> [--yes] [--internal]"
license: MIT
metadata:
  author: bestagentkits
  version: "1.8.0"
---

# Orchestrate

Coordinate headless coding-agent jobs, agent sessions and in-session subagents
through a staged, captured, resumable workflow. The skill owns routing and
judgment; the coordinator owns deterministic plan state, process supervision
and observable evidence. No service or dashboard is required.

**Engine.** The coordinator path is canonical: it owns the run directory
described in [job-spec.md](references/job-spec.md), and nothing in this skill
requires the AgentKit CLI. When that CLI is installed, `ak orchestrate` is an
equivalent accelerator for the same contract — it must produce the same
run-directory state, so a run started one way can be resumed the other, and no
step depends on it being present.

Runtime and model catalogs drift. Resolve every route from live evidence;
never treat a runtime, provider, model, flag, or agent seen in this file or an
older report as currently available.

## Inputs

Accepted forms:

```bash
/orchestrate "research three implementation options and compare them"
/orchestrate "run the three scouts as pi sessions, then one arbiter"
/orchestrate plans/orchestrate-jobs.yaml [--yes]
/orchestrate --resume plans/reports/orchestrate-<timestamp>
```

Use a YAML job spec for repeatable runs; for a free-form request, write one
to `plans/reports/orchestrate-<timestamp>/jobs.yaml` before dispatch.

`--internal` is a routing preference, not a hard mode: it asks the selection
policy to consider in-session subagents first for jobs without an explicit
`runtime:`, and a job needing model selection or stronger isolation may still
use a live-verified CLI fallback. Never override an explicit runtime, model,
or agent pin silently. Naming a runtime in the request ("as pi sessions") is
an explicit ask: that candidate joins the set, and if it is missing or not
authenticated its onboarding runs as a visible setup step before routing.

## Authority Map

Keep durable facts in one place:

- [model-routing.md](references/model-routing.md) is the **sole route-selection
  authority**: capability tiers, risk tiers, task defaults, internal
  selection, fallback qualification, and model-family independence.
- [runtime-matrix.md](references/runtime-matrix.md): live candidate discovery,
  probing, command verification, OS evidence, `<run-dir>/runtimes.json`.
- [harness-profiles.md](references/harness-profiles.md): evidence schema for
  permissions, isolation, capture, budgets, and enablement.
- [internal-routing.md](references/internal-routing.md): in-session dispatch,
  capture, timeout, and resume mechanics.
- [pi-sessions.md](references/pi-sessions.md): Pi probing, session handles,
  dispatch shape, capture, and intervention limits.
- [pi-onboarding.md](references/pi-onboarding.md): installing, profiling,
  authenticating, and verifying a Pi runtime that a job requires.
- [job-spec.md](references/job-spec.md): the executable YAML and acceptance
  contract; the run-state schema and validation it defines own exact machine
  fields.
- [observation.md](references/observation.md): observation, intervention,
  diagnosis and evidence-based improvement.

When references disagree, stop and report the contract mismatch.

## Pipeline

### 1. Brainstorm and intake

- Clarify the desired outcome, constraints, non-goals, and acceptance evidence.
- Read the request or job spec; identify the workspace root, dependencies,
  destructive or external intent, expected outputs, and runtime constraints.
- Refuse any plan that would place secrets, credentials, private keys, dotenv
  values, or unrelated private data in prompts or capture.
- Prefer a direct single-agent workflow when orchestration adds no useful
  parallelism, staged dependency, runtime diversity, or arbiter value.

### 2. Build the job graph

- Convert the accepted outcome into jobs with explicit `task`, `cwd`, timeout,
  expected output, and file ownership.
- Use `depends_on` to form stages; run same-stage jobs concurrently only when
  ownership and outputs do not overlap.
- Mark public-contract, security-sensitive, cross-module, or hard-to-revert
  implementation as `importance: high`; set `isolation: worktree` for parallel
  writers, untrusted write prompts, and harnesses with a weak write boundary.
- Name the skill or instructions each headless job must load; a one-shot
  process cannot rely on automatic skill discovery.

### 3. Discover, profile, route, and onboard when required

- Reuse discovery evidence only while runtime binary/version, account, host,
  permissions, requested controls and model catalog remain unchanged;
  invalidate on change or probe failure. Resume reconciles existing attempts
  before dispatch.
- Build a live inventory per [runtime-matrix.md](references/runtime-matrix.md)
  and profile each candidate per
  [harness-profiles.md](references/harness-profiles.md); Pi candidates add
  the evidence in [pi-sessions.md](references/pi-sessions.md).
- When a pinned, fallback, or user-named candidate is missing or
  unauthenticated, run its onboarding as a visible setup step (Pi:
  [pi-onboarding.md](references/pi-onboarding.md)) and probe again. Discovery
  itself never installs or logs in, because a probe must not mutate the host.
- Pass the live evidence and job classification to
  [model-routing.md](references/model-routing.md); record the selected
  runtime, model or agent, capability tier, risk tier, controls, evidence
  source, and fallback reason. Do not restate or override its task defaults,
  tier floors, ranking, or fallback rules elsewhere.
- A missing, unauthenticated, unverified, or under-controlled candidate cannot
  satisfy a route. Re-profile fallbacks and rebuild their commands; never
  carry model names or flags between runtimes.
- Mark the job `blocked` when no candidate meets both capability and risk
  floors; never budget-route judgment or silently weaken safety.

### 4. Apply the safety gate

- Confirm every job's cwd, allowed files, writable roots, and expected side
  effects. Use least-privilege permission and tool controls verified on the
  live runtime, with every permission-bypass mode off by default.
- Record existing user authorization and its exact scope in `authority`.
  Request approval only for an action outside that scope; prior authorization
  stays valid without repeating `--yes`. A reference records the decision; it
  cannot grant authority by itself.
- Treat inherently auto-approved headless modes as constrained: read/report
  work or R2-isolated writes, never shared-tree destructive work. A worktree
  prevents edit collisions but is not an OS sandbox.
- Give every CLI process an external timeout; internal timeouts are
  accounting-only unless the current harness proves cancellation.

### 5. Dispatch, observe and verify

- Create required worktrees, resolve input handoffs, pin each cwd, and build
  each CLI invocation from the live profile with argument arrays and scoped
  tools. Prepare and reconcile the run directory before every dispatch; that
  contract is owned by [job-spec.md](references/job-spec.md).
- Persisted attempts and intended supervisor IDs precede launch.
  Reconciliation handles existing work before dispatch; never bypass an
  uncertain attempt by starting it again manually.
- Dispatch returned internal jobs through the native harness, preserving their
  attempt IDs. Store handles and capture per
  [internal-routing.md](references/internal-routing.md); accept only a settled
  attempt with verified artifacts and checks.
- Give Pi jobs a run-scoped session directory and store each session id as
  the resume handle; dependents continue or fork it per
  [pi-sessions.md](references/pi-sessions.md).
- Read the snapshot, the journal after a recorded cursor and bounded job output
  from a recorded byte offset, each per supervisor run with its own cursor;
  continue until every attempt is settled, not merely until an aggregate status
  reads failed.
- Supervisor deadlines and bounded redacted capture survive the client exit
  on supported platforms; elsewhere process supervision is an explicit
  capability gap, so use a qualified host/harness for jobs that need it.
- Apply the observation and intervention contract in
  [observation.md](references/observation.md): a quiet process is not proof
  of a stall, and a cancelled request is not proof of a stopped writer.
- Retry only within declared bounded policy after safe settlement and
  unchanged fingerprints. Unknown flags/models need fresh discovery;
  permission or external-effect failures need a scope-aware decision.

### 6. Run an arbiter review

- Wait for all runnable jobs to settle, then use a separate C3 judgment route
  selected by [model-routing.md](references/model-routing.md).
- Prefer independently configured or different-family review when live
  evidence proves it; disclose a same-family fallback. A Pi arbiter counts as
  independent only when its resolved model family differs.
- Compare each result with `expected_output` and the original intent, run the
  checks listed in the spec, and flag contradictions, unsupported claims,
  missing artifacts, safety gaps, timeouts, and failed checks. Do not
  summarize unverified work as complete.

### 7. Report

- Write `plans/reports/orchestrate-<timestamp>/report.md`.
- Include per-job status, capability/risk tier, resolved runtime and model or
  agent, artifacts, errors, arbiter verdict, checks, reproduction commands,
  worktree diffs awaiting integration, Pi session handles and exports,
  onboarding actions taken, and unresolved questions.
- Record effective model/effort, startup/fork/communication time and cache
  telemetry when exposed, alongside retries and cost. Unknown cache cost is
  not zero. Metrics never lower capability/risk floors, override explicit
  pins, or silently rewrite routing policy; keep per-attempt metrics in the
  run and aggregate comparable records without changing their evidence.

## Pi Sessions

Pi is orchestrable because every run is a resumable session file. The
coordinator keeps those files under the run directory, records each job's
session id as its handle, and chains dependent jobs by continuing or forking
the upstream session instead of re-sending its output. Headless Pi has no
sandbox and no per-operation approval, so its writes belong in a
coordinator-created worktree and it starts offline so a job cannot install
packages mid-run. Probe budgets, flags, capture and the RPC intervention
channel are in [pi-sessions.md](references/pi-sessions.md); install, profile,
authentication and kit projection are in
[pi-onboarding.md](references/pi-onboarding.md).

## Worktree Isolation

- Create one worktree per isolated job from the accepted base ref, on a
  unique branch under the run namespace, and set the job's cwd to it. Never
  share a worktree across jobs or reuse a failed attempt without an explicit
  recovery decision.
- Sequence jobs that must edit the same generated artifact, lockfile,
  migration sequence, or shared configuration. Separate worktrees defer those
  conflicts; they do not resolve them.
- Integration is coordinator-owned and follows the arbiter pass: summarize
  diffs first; merging or cherry-picking is a separate reviewed step.
- Remove only integrated or explicitly discarded worktrees; preserve failed
  ones for diagnosis and list them in the report.

## Job Spec

Full schema: [job-spec.md](references/job-spec.md). Placeholders below are
resolved after live discovery:

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

- Every job has an explicit cwd, timeout, expected output, and ownership;
  capture stays under `plans/reports/orchestrate-<timestamp>/` with secrets
  redacted from prompts, commands, logs, and reports.
- Start with read-only or scoped-write behavior.
- Permission bypasses stay off unless the user approved the exact action and
  a stronger external boundary contains the residual risk.
- Parallel writers use separate worktrees and disjoint ownership; failed
  output is preserved for diagnosis, never hidden or relabeled.
- Keep destructive and credentialed external actions off prompt-only
  isolation. Onboarding installs are visible and reversible; profile
  overwrites are snapshotted first; credentials are entered only by the user.

## On-demand References

- `references/output-layout.md`: run-directory and supervisor capture tree,
  plus the rules on exporting private graphs or job specs.
- `references/arbiter-checklist.md`: load at step 6; the final report is
  blocked until every question in it is answered.
- `references/failure-modes.md`: load when a job fails, times out, requests
  permission, is interrupted, or ownership or references disagree.
- `references/dispatch-hardening.md`: load for long, detached, or
  network-dependent jobs, and for hosts whose process tree reaps children.
- `references/metrics-and-self-improvement.md`: load when comparing run
  outcomes or considering a routing-policy change.

## Limitations

- Jobs share no implicit memory; pass artifacts through explicit dependencies.
  A continued Pi session carries context, not accepted proof.
- Internal jobs may lack force cancellation, per-job sandboxing, or model
  selection.
- CLI commands, models, authentication, and safety behavior drift; every run
  revalidates them. Worktrees need a git repository and disk headroom and do
  not provide process isolation.
- Metrics are advisory and cannot authorize an automatic route-policy change.
- Orchestrate coordinates existing runtimes; it adds no daemon, dashboard,
  account pool, or provider adapter. Onboarding installs a runtime the user
  asked for and stops at the credentials only the user can supply.
- Process supervision that survives the client exit is host-specific; record
  the host and harness limits per route instead of assuming lifecycle support.
  With the AgentKit CLI installed, its supervisor requires Darwin, and
  discovery elsewhere does not imply lifecycle support.

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
