---
name: orchestrate
description: "Coordinate staged or parallel jobs across live-verified coding-agent runtimes, agent sessions, and in-session subagents through one runtime-adapter contract and a normalized event protocol, routed by deterministic capability- and risk-based policy with an optional provider-neutral System-1 decision plane that watches traces, triages failures, and gates independent arbiter review. Worktree isolation, resumable state, capture, and safety gates included; onboards a missing Pi runtime as a visible setup step when a job or the user asks for it."
user-invocable: true
when_to_use: "Invoke when work should be split across multiple headless runtimes, agent sessions, or in-session subagents, routed by task capability and risk, isolated where needed, and reviewed before handoff; also when Pi must be installed and set up before it can take orchestrated jobs, or when a new runtime adapter needs to be probed and conformed."
category: dev-tools
keywords: [orchestrate, headless, multi-agent, runtime-adapter, event-protocol, decision-plane, subagents, pi, onboarding, live-routing, routing-policy, safety-policy, capability, risk, worktree, resume, parallel, arbiter, calibration]
argument-hint: "<job-spec.yaml | task description | --resume <run-dir>> [--yes] [--internal]"
license: MIT
metadata:
  author: bestagentkits
  version: "2.2.0"
---

# Orchestrate

Coordinate headless coding-agent jobs, agent sessions and in-session subagents
through a staged, captured, resumable workflow. The skill owns routing and
judgment; the coordinator owns deterministic plan state, process supervision and
observable evidence. No service or dashboard is required. This skill targets any
harness that implements the Agent Skills contract;
[harness-portability.md](references/harness-portability.md) owns the conformance
surface, the harness features this skill may never depend on, and the install paths.

**Engine.** The coordinator path is canonical: it owns the run directory
described in [job-spec.md](references/job-spec.md), and nothing in this skill
requires the AgentKit CLI. When that CLI is installed, `ak orchestrate` is an
equivalent accelerator for the same contract — it must produce the same
run-directory state, so a run started one way can be resumed the other, and no
step depends on it being present. The engine is the coordinator path, and no
harness CLI is required: the harness is the thing that loads this skill, while
the coordinator owns the run.

Runtime and model catalogs drift. Resolve every route from live evidence; never
treat a runtime, provider, model, flag, or agent seen in this file or an older
report as currently available.

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

Keep durable facts in one place. Every contract below has exactly one owner.

**Runtime layer**

- [harness-portability.md](references/harness-portability.md): the Agent Skills
  conformance surface, the three harness features this skill may never depend on,
  and every install and discovery path.
- [runtime-adapter-contract.md](references/runtime-adapter-contract.md): the
  adapter interface, conformance, command construction, OS revalidation.
- [runtime-profile.md](references/runtime-profile.md): live candidate discovery
  including the classifier role, probing, `runtimes.json`, support states,
  timeouts, and the annotation-only auto-profiler.
- [benchmark-evidence.md](references/benchmark-evidence.md): measured **outcome**
  evidence — the route identity a record is keyed on, the sample-size-aware quality
  bound, the cohort-scoped evidence hierarchy and its recorded degradation, cost per
  task and duration per reasoning effort — plus its sources, its durable cache, and the
  limits on what it may decide.
- [event-protocol.md](references/event-protocol.md): the normalized event
  envelope, event kinds, cursor semantics, the agent state machine, and the
  redaction and provenance rules.
- [runtimes/README.md](runtimes/README.md): the adapter index, the authoring
  procedure, and the `pi`, `omp`, `agy` and `grok` probe targets.
- [internal-routing.md](references/internal-routing.md): the internal adapter —
  in-session dispatch, capture, timeout, resume, and agent resolution.

**Policy layer**

- [safety-policy.md](references/safety-policy.md): the **sole safety authority** —
  risk tiers R0–R3 and their minimum controls, approval and authority, isolation
  boundaries, secret handling, and the decisions no automated signal may make.
- [routing-policy.md](references/routing-policy.md): the **sole route-selection
  authority** — the expected-verified-cost objective, the deterministic hard filter,
  capability tiers C1–C3, task floors and verification strength, deterministic Pareto
  pruning and its protections, the value-of-information gate, ranking, fallbacks and
  reasoning controls.
- [fallback-policy.md](references/fallback-policy.md): the promotion chain, its
  triggers and budget, the per-concern control comparison, and the terminal
  fail-safe.
- [trace-and-logging.md](references/trace-and-logging.md): span identifiers, the
  correlation rule, the closed `route` payload a decision must be explainable from,
  retention and export.
- [decision-plane.md](references/decision-plane.md): the **sole System-1
  authority** — provider sourcing, call and input rules, when a call is worth making,
  the six decision tasks, the decision trace, and the authority the plane does not have.

**Execution layer**

- [job-spec.md](references/job-spec.md): the executable YAML and the machine
  fields acceptance consumes; the run-state schema and validation it defines own
  exact machine fields. Acceptance itself is owned by
  [verification.md](references/verification.md).
- [output-layout.md](references/output-layout.md): the run-directory and
  supervisor capture tree, decision artifacts, and export rules.
- [observation.md](references/observation.md): observation, watchdog handoff,
  intervention, diagnosis and evidence-based improvement.
- [verification.md](references/verification.md): the three verification layers,
  the **escalation matrix**, when a structurally mandatory escalation goes straight to
  C3, calibration with its durability and invalidation rules, and the arbiter contract.
- [graph-optimizer.md](references/graph-optimizer.md): graph reduction, the merge
  algebra, and every refusal condition.

**On-demand layer**

- [failure-modes.md](references/failure-modes.md)
- [dispatch-hardening.md](references/dispatch-hardening.md)
- [metrics-and-self-improvement.md](references/metrics-and-self-improvement.md)

When references disagree, stop and report the contract mismatch.

## Pipeline

```text
intake
  ↓
job graph                        (System 2: the planner authors it)
  ↓
live inventory + profile         runtime-profile.md
  ↓
═════════════ deterministic safety boundary ═════════════
safety gate                      safety-policy.md — what may run
  ↓
hard filter                      routing-policy.md — eligibility, floors
  ↓
semantic rank                    decision-plane.md supplies signals → routing-policy.md applies them
  ↓
graph optimizer                  graph-optimizer.md — post-routing reduction
  ↓
═════════════════════════════════════════════════════════
dispatch                         runtime-adapter-contract.md + verified profile
  ↓
normalized events                event-protocol.md
  ↓
trace watchdog                   decision-plane.md signals → observation.md rules
  ↓
triage / retry                   decision-plane.md taxonomy → failure-modes.md hard stop
  ↓
deterministic checks             verification.md layer 1
  ↓
micro-arbiter gate               verification.md escalation matrix
  ↓
     accept ────────────────────────────────► report
        │
        └── escalate ──► C3 arbiter ──────────► report
                         verification.md layer 3
```

**Which layer owns each hop.** The planner owns the graph. The safety gate owns
whether anything runs. The hard filter owns eligibility and floors; the decision
plane supplies scored signals, `capabilityFloorDelta`, and `riskFloorDelta`, which
may only raise a floor — a risk-floor raise also forces C3. The optimizer owns
reduction, after routing. Deterministic checks own failure. The escalation matrix
owns acceptance. The C3 arbiter owns judgment where escalated. Nothing
probabilistic decides any of these.

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
- Build a live inventory per [runtime-profile.md](references/runtime-profile.md);
  Pi candidates add the evidence in [runtimes/pi.md](runtimes/pi.md).
- When a pinned, fallback, or user-named candidate is missing or
  unauthenticated, run its onboarding as a visible setup step (Pi:
  [runtimes/pi-onboarding.md](runtimes/pi-onboarding.md)) and probe again.
  Discovery itself never installs or logs in, because a probe must not mutate
  the host.
- Pass the live evidence and job classification to
  [routing-policy.md](references/routing-policy.md); record the selected
  runtime, model or agent, capability tier, risk tier, controls, evidence
  source, the applied floor deltas, and fallback reason. Do not restate or override
  its task defaults, tier floors, ranking, or fallback rules elsewhere.
- A missing, unauthenticated, unverified, or under-controlled candidate cannot
  satisfy a route. Re-profile fallbacks and rebuild their commands; never
  carry model names or flags between runtimes.
- Mark the job `blocked` when no candidate meets both capability and risk
  floors; never budget-route judgment or silently weaken safety.

### 4. Apply the safety gate

Owned by [safety-policy.md](references/safety-policy.md). This is the single
brief in this file; the authority is that file.

- Confirm every job's cwd, allowed files, writable roots, and expected side
  effects. Use least-privilege permission and tool controls verified on the
  live runtime, with every permission-bypass mode off by default.
- Record existing user authorization and its exact scope in `authority`. Request
  approval only for an action outside that scope; prior authorization stays
  valid without repeating `--yes`.
- Treat inherently auto-approved headless modes as constrained: read/report
  work or R2-isolated writes, never shared-tree destructive work. A worktree
  prevents edit collisions but is not an OS sandbox.
- Keep destructive and credentialed external actions off prompt-only isolation.
  Never enable a permission-bypass flag: a job that needs more privilege gets a
  scoped permission with explicit approval, a stronger external boundary, or it is
  blocked. The rule and its reasoning are owned by
  [safety-policy.md](references/safety-policy.md). Onboarding installs are visible
  and reversible; profile overwrites are snapshotted first. The coordinator never
  types, copies or stores a credential: it is read from a documented location, or
  the capability that needs it is disabled.
- Start with read-only or scoped-write behavior. Parallel writers use separate
  worktrees and disjoint ownership, and failed output is preserved for diagnosis
  rather than hidden or relabeled.
- Capture stays under `plans/reports/orchestrate-<timestamp>/`, with secrets
  redacted from prompts, commands, logs, decision traces, and reports.
- Give every CLI process an external timeout.

### 5. Dispatch, observe and verify

- Create required worktrees, resolve input handoffs, pin each cwd, and build
  each CLI invocation from the live profile with argument arrays and scoped
  tools. Prepare and reconcile the run directory before every dispatch; that
  contract is owned by [job-spec.md](references/job-spec.md).
- Persisted attempts and intended supervisor IDs precede launch.
  Reconciliation handles existing work before dispatch; never bypass an
  uncertain attempt by starting it again manually.
- Dispatch returned internal jobs through the native harness, preserving their
  attempt IDs, per [internal-routing.md](references/internal-routing.md).
- Give Pi jobs a run-scoped session directory and store each session id as
  the resume handle; dependents continue or fork it per
  [runtimes/pi.md](runtimes/pi.md).
- Read the snapshot, the journal after a recorded cursor and bounded job output
  from a recorded byte offset, each per supervisor run with its own cursor;
  continue until every attempt is settled, not merely until an aggregate status
  reads failed.
- Supervisor deadlines and bounded redacted capture survive the client exit
  on supported platforms; elsewhere process supervision is an explicit
  capability gap.
- Apply the observation and intervention contract in
  [observation.md](references/observation.md), and the normalized event rules in
  [event-protocol.md](references/event-protocol.md): a quiet process is not proof
  of a stall, an exit without settlement evidence is `unsettled`, and a cancelled
  request is not proof of a stopped writer.
- Retry only within declared bounded policy after safe settlement and
  unchanged fingerprints, per [failure-modes.md](references/failure-modes.md).

### 6. Verify and review

- Run the deterministic checks in [verification.md](references/verification.md)
  layer 1. A failing check fails the attempt; no probabilistic signal overrules
  it.
- Consult the escalation matrix. Accept without a C3 call only when the
  attempt's **recorded** risk tier is R0 or R1 with no risk-floor delta applied, a
  valid per-classifier calibration record exists, and every other condition holds.
  Otherwise escalate.
- **R2 and R3 always escalate to C3.** So do security and audit, `review` or any
  job whose artifact is a verdict on another job's work, architecture, high-impact
  implementation, external/destructive work, any attempt whose tier was raised by
  a `riskFloorDelta`, contradictory evidence, an absent injection-fixture result,
  and any malformed or low-confidence micro-arbiter result.
- For C3, use a separate judgment route selected by
  [routing-policy.md](references/routing-policy.md). Prefer a different model
  family or a freshly and independently configured agent. When live evidence
  proves no independent route exists, label the verdict `not-independent` and
  either substitute a fresh, independently configured context or block.
- A System-1 micro-arbiter verdict is **never** independent review evidence for a
  C3 decision. It is a gate, not a reviewer.

### 7. Report

- Write `plans/reports/orchestrate-<timestamp>/report.md`.
- Include per-job status, capability/risk tier with its derivation, resolved
  runtime and model or agent, artifacts, errors, arbiter verdict, checks,
  reproduction commands, worktree diffs awaiting integration, Pi session handles
  and exports, onboarding actions taken, **the accepted-without-C3 count**, and
  unresolved questions.
- Record effective model/effort, startup/fork/communication time and cache
  telemetry when exposed, alongside retries and cost. Unknown cache cost is
  not zero. Metrics never lower capability/risk floors, override explicit
  pins, or silently rewrite routing policy.

## Decision plane (optional)

The System-1 decision plane is provider-neutral and optional. It prefers a
`role: classifier` candidate already in `runtimes.json` that proves structured
output and verified tool gating. Jev (TypeSafe) is the reference implementation
and one optional provider — never a requirement.

It supplies scored signals for the trace watchdog, failure triage, semantic
routing, the micro-arbiter gate, profiling, and graph relations. It never
authorizes a safety decision, sets `approval`, emits a dispatch, mutates shared
state, weakens review independence, or replaces the C3 arbiter.

**Degradation is normal.** With no eligible classifier, a timeout, or malformed
output, the affected decision records `none` and deterministic policy decides.
A classifier outage never blocks a run and never re-labels a runtime: `unverified`
means the deterministic probe did not prove the behavior, not that the model did
not confirm it.

See [decision-plane.md](references/decision-plane.md).

## Pi Sessions

Pi is orchestrable because every run is a resumable session file. The
coordinator keeps those files under the run directory, records each job's
session id as its handle, and chains dependent jobs by continuing or forking
the upstream session instead of re-sending its output. Headless Pi has no
sandbox and no per-operation approval, so its writes belong in a
coordinator-created worktree and it starts offline so a job cannot install
packages mid-run.

Probe budgets, flags, capture and the RPC intervention channel are in
[runtimes/pi.md](runtimes/pi.md); install, profile, authentication and kit
projection are in [runtimes/pi-onboarding.md](runtimes/pi-onboarding.md).

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

## On-demand References

- [failure-modes.md](references/failure-modes.md): load when a job fails, times
  out, requests permission, is interrupted, or ownership or references disagree.
- [dispatch-hardening.md](references/dispatch-hardening.md): load for long,
  detached, or network-dependent jobs, and for hosts whose process tree reaps
  children.
- [metrics-and-self-improvement.md](references/metrics-and-self-improvement.md):
  load when comparing run outcomes, auditing arbiter-gate telemetry, or
  considering a routing-policy change.

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
- **The decision plane is inert without an eligible classifier candidate**, which
  is the normal state on a host whose only inventory entry is the internal
  agent. This is by design: deterministic policy is sufficient on its own, and
  the plane is never load-bearing for safety. Whether an installed classifier
  will ever be eligible in practice is not verifiable from documentation.
- **A System-1 verdict is not independent review.** It gates the arbiter; it does
  not replace it, and it is never evidence of independence.
- **R2 and above always receive arbiter review.** Acceptance without a C3 call is
  limited to R0/R1 with a valid calibration record.

## Completion Report

End with:

```markdown
**Orchestrate Result**
- Spec: <path or inline request>
- Report: <plans/reports/orchestrate-.../report.md>
- Jobs: <success>/<failed>/<blocked>
- Arbiter: pass|fail|blocked
- Accepted without C3: <n> of <total> (R0/R1 only)
- Decision plane: enabled(<candidate>)|disabled|degraded(<reason>)
- Credentials: `credentialSource`=<env|project-env|skills-env|skill-env|absent> `credentialTrust`=<process|working-tree> `credential-shadowed`=<none|the ignored source>
- Checks: <commands or none>

Unresolved questions:
- None
```
