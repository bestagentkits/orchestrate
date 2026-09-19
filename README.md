<div align="center">

# Orchestrate

**Multi-runtime agent orchestration for any coding-agent harness.**

An Agent Skills package: it runs on any harness that implements that contract, with
Claude Code as one supported harness among many. The
[harness portability contract](plugins/orchestrate/skills/orchestrate/references/harness-portability.md)
owns the conformance surface and the per-harness install and discovery paths.

Coordinate staged or parallel jobs across live-verified coding-agent runtimes,
coding-agent sessions and in-session subagents — routed by capability and risk,
isolated in git worktrees, fully captured, resumable, and blocked from
declaring success until deterministic checks pass and, for anything above
read-only or scoped-write work, an independent arbiter agrees.

[**Live site →**](https://bestagentkits.github.io/orchestrate/) ·
[Skill contract](plugins/orchestrate/skills/orchestrate/SKILL.md) ·
[Install](#install) ·
[MIT](LICENSE)

</div>

[![Orchestrate](assets/hero-light.png)](https://bestagentkits.github.io/orchestrate/)

---

## Why

Fanning work out to several agents takes one loop. What it costs you is everything
that makes the result believable: two agents editing the same file, a runtime that
silently vanished, a model name that stopped existing last week, a permission prompt
swallowed by a headless process, and a cheerful summary claiming success nobody verified.

Orchestrate treats those as the actual problem:

- **Every route is resolved from live evidence** at execution time — never from a
  catalog written into a file. Runtimes, models, aliases, flags and agents are all
  re-probed per run.
- **Every parallel writer gets its own git worktree**, branched from the accepted base ref.
- **Every job records** its redacted command, bounded stdout/stderr, exit status, wall
  time and artifacts under one run directory.
- **Nothing is reported finished** until it clears verification. Deterministic
  checks run first; then an escalation gate decides whether a C3 arbiter is
  required. An attempt may be accepted without a C3 call only when its recorded
  tier is R0/R1 with no risk-floor raise, a valid per-classifier calibration
  record exists, and every other gate condition holds. **R2, R3 and all judgment
  work always go to an independent C3 route.** When no independent route exists,
  the verdict is labeled `not-independent` and the job is blocked unless a fresh,
  independently configured context substitutes for it.

## Pipeline

| # | Stage | What it guarantees |
|---|-------|--------------------|
| 1 | Brainstorm & intake | Outcome, constraints and acceptance evidence are explicit. Secrets are refused at the door. If orchestration adds nothing, it says so. |
| 2 | Build the job graph | Jobs carry explicit `task`, `cwd`, timeout, expected output and file ownership. `depends_on` forms the stages. |
| 3 | Discover, profile, route, optimize | Live runtime inventory → profile → deterministic capability/risk filter → optional System-1 semantic rank (may only raise a floor) → graph optimizer. Recorded with its evidence source. A pinned runtime that is missing is onboarded as a visible setup step. |
| 4 | Apply the safety gate | Least privilege, permission bypass off, destructive/credentialed work needs approval for that exact scope. The tier is derived deterministically from declared attributes, and an absent tier fails closed to R2. |
| 5 | Dispatch, observe, verify | Worktrees created before dispatch, `state.json` updated on every transition, output bounded and redacted, normalized events, every attempt observed until settled. |
| 6 | Verify and review | Deterministic checks first. Then the escalation gate: R0/R1 with a valid per-classifier calibration record may be accepted; R2 above that, and all judgment work, go to an independent C3 route. |
| 7 | Report | One `report.md` with statuses, resolved routes, artifacts, verdict, repro commands and unresolved questions. |

## Routing

Two independent axes. A job runs only where **both** floors are met — otherwise it is
marked `blocked`, never quietly downgraded.

**Capability**

| Tier | Required behavior | Typical work |
|---|---|---|
| `C1` throughput | Accurate search, extraction, summarization, bounded repetitive changes | scout, docs, mechanical fan-out |
| `C2` delivery | Multi-file implementation judgment, test design, failure-path handling | normal implementation and tests |
| `C3` judgment | Deep trade-off analysis, conflict resolution, security reasoning, independent arbitration | architecture, review, audit, arbiter |

**Risk**

| Tier | Effect | Minimum controls |
|---|---|---|
| `R0` observe | Read/report only | Explicit cwd, bounded timeout, captured result, no unnecessary write or shell grant |
| `R1` scoped write | Reversible edits in owned files | Scoped write boundary, tool restrictions, diff capture, no permission bypass |
| `R2` isolated write | Parallel, high-impact, untrusted, or hard-to-revert changes | Separate worktree **or stronger isolation**, enforced sandbox where available, **explicit checks and arbiter review** |
| `R3` external/destructive | Deploy, release, delete, credentialed, or other external side effect | Explicit user approval, preview/rollback plan, **strongest verified controls**; blocked when those controls are unavailable |

Risk tiers are defined once, in
[`safety-policy.md`](plugins/orchestrate/skills/orchestrate/references/safety-policy.md);
the tables above summarize and link, they do not own the policy.

### The System-1 decision plane (optional)

Routing is deterministic. An optional, provider-neutral **decision plane** can
supply scored signals on top of it — how likely a trace is stalled, which
failure class an error belongs to, which capability a job actually needs — but
it never decides:

- It is sourced from a runtime **already in the live inventory**; there is no new
  provider dependency and no new credential system. Jev (TypeSafe) is the reference
  implementation and one optional provider. The plane reads the runtime's own
  provider credential from a documented resolution order; configure nothing and the
  plane is **disabled**, not silently re-routed.
- Its `floor_delta` splits into `capabilityFloorDelta` and `riskFloorDelta`. Both
  may only **raise** a floor, and a lowering signal is discarded. A risk-floor
  raise changes the recorded tier, adds controls, and always escalates to C3 — so
  a probabilistic signal can shrink the no-C3 path, never widen it.
- It never grants a permission, assigns a risk tier, emits a command, mutates
  shared state, weakens review independence, or replaces the C3 arbiter.
- With no eligible classifier it is **disabled** and deterministic policy decides.

Details: [`decision-plane.md`](plugins/orchestrate/skills/orchestrate/references/decision-plane.md).

### Jev (TypeSafe), the reference System-1 model

Jev is the model this contract was written against, and **one optional provider** behind
it — never a requirement, and never the only way to run the plane.
[TypeSafe](https://typesafe.ai) builds what it calls System One models: instead of
generating text for a program to parse, they answer a declared set of typed questions
about a piece of state and return a probability for each answer. Three properties are why
the plane is shaped the way it is:

- **Typed answers, no repair step.** A decision arrives as a value from a pre-declared
  set, so nothing has to be coerced out of free text into a policy field, and an answer
  outside that set is a malformed result rather than a plausible one.
- **A distribution, not a verdict.** A choice comes back with the runner-up
  probabilities beside it, which is what lets a low-confidence decision be expressed
  instead of rounded into a confident wrong answer.
- **Calibrated confidence.** Every answer carries its own probability, which is what
  lets a floor be **raised** from a signal, and a weak signal be discarded rather than
  acted on.

That shape is what the plane's six decision tasks consume, and it is why Jev is named
against each of them: the **trace watchdog** and **failure triage** score probabilities
over an enumerated state and error taxonomy; the **semantic router** supplies the floor
deltas and the ranking needs; the **micro-arbiter** proposes the flags a deterministic
predicate consumes; **profiler classification** writes an annotation-only hint block; and
**graph relation** proposes a relation over a closed set. In all six, the result is
scored evidence for a deterministic predicate, never the decision itself.

Configure the key, or configure nothing. Because the plane is dispatched through a runtime
already in the live inventory, it adds no provider client and no second credential system:
with no eligible classifier, no key, or no recorded egress authorization it is **disabled**
for that run and deterministic policy decides. The variable is named under [Credentials](#credentials);
the read order and the call contract are owned by
[`decision-plane.md`](plugins/orchestrate/skills/orchestrate/references/decision-plane.md).

### Benchmark-ranked routing

Routing ranks the candidates that already survived the hard filter, using measured
success rate, cost per task and task duration for a model at a given reasoning effort.
That evidence is fetched from named sources and cached **between runs** at
`.orchestrate/benchmarks.json` for a configurable period. Benchmarks **rank, never
gate**: they cannot set eligibility, a floor, a tier, a control or an approval. The
cache TTL defaults to seven days, and a job may not declare more than thirty.
See [references/benchmark-evidence.md](plugins/orchestrate/skills/orchestrate/references/benchmark-evidence.md).

### Promotion and fail-safe

A quota limit, an outage or a crash promotes the job to the next candidate — after the
same-runtime retry budget is exhausted, and honoring a declared `fallback_runtime` order
first — within a bounded budget that ends in a logged `blocked` state. A **failed check
never promotes**, and a **permission or authorization stop never promotes**. Two
promotions by default, four at most. See
[references/fallback-policy.md](plugins/orchestrate/skills/orchestrate/references/fallback-policy.md).

### Trace and logs

Every routing decision, promotion, gate outcome and verdict carries one correlation
identity, and the trace records fetch attempts as well as decisions. It is redacted on
write and excluded from exports unless reviewed, and a run whose trace is incomplete
must say so rather than implying a complete audit trail. See
[references/trace-and-logging.md](plugins/orchestrate/skills/orchestrate/references/trace-and-logging.md).

### Credentials

For the reference provider the variable is `TYPESAFE_API_KEY`; the key is created in
TypeSafe's own console, and nothing in this repository generates, reveals or stores it. It
is read from the process environment, then the project `.env`, then the `skills/`
directory `.env`, then the skill's own `.env`; the first location with a value wins. The
value is passed **only** through the inherited child environment, and a shadowed source is
reported. The key is never printed, never requested interactively and never committed — a
missing key disables the decision plane instead. `.env.example` at the repository root
carries the variable name and no value, so the template can be committed while `.env`
stays ignored.

A key on its own is not a licence to call the provider. A decision-plane call also
requires a recorded **egress authorization** naming the provider and the credential
source, because sending state to a provider is an external side effect. With no key **or**
no recorded authorization the plane is disabled for the run and deterministic policy
proceeds; it is never silently re-routed to another provider.

This section is a **parity-checked summary** of
[references/decision-plane.md](plugins/orchestrate/skills/orchestrate/references/decision-plane.md),
which owns the read order.

## Install

### With the skills CLI

```bash
npx skills add bestagentkits/orchestrate
```

```bash
npx skills add bestagentkits/orchestrate -g            # install for the current user
npx skills add bestagentkits/orchestrate -a <harness>  # install for one named harness
```

The Claude Code marketplace install and the plain-skill copy below are both unchanged
and still supported: the CLI is an additional path, not a replacement.

### As a Claude Code plugin (one harness among many)

```bash
/plugin marketplace add bestagentkits/orchestrate
```

```bash
/plugin install orchestrate@orchestrate
```

Restart Claude Code so the skill registers.

### As a plain skill

No plugin system required — copy the skill folder into your project or your home config.
The destination depends on the harness; `.claude/skills/` is only the Claude Code
convention, and [the portability contract](plugins/orchestrate/skills/orchestrate/references/harness-portability.md)
lists the others:

```bash
git clone https://github.com/bestagentkits/orchestrate.git
cp -R orchestrate/plugins/orchestrate/skills/orchestrate ~/.claude/skills/   # Claude Code
# other harnesses read their own path, for example ~/.agents/skills/ or ~/.pi/skills/
```

## Usage

```bash
/orchestrate "research three caching strategies and compare them"
```

```bash
/orchestrate "refactor the session API" --internal
```

```bash
/orchestrate plans/jobs.yaml --yes
```

```bash
/orchestrate --resume plans/reports/orchestrate-<timestamp>
```

`--internal` is a routing *preference*, not a hard mode: it asks the selection policy
to consider in-session subagents first for jobs without an explicit `runtime:`.
`--yes` pre-approves the exact destructive scope described in the spec.

### Job spec

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
    depends_on: [scout-session-api]
    importance: high
    isolation: worktree
    timeout: 10m
    expected_output: "Independent verdict with checks and unresolved risks."
```

Placeholders are deliberate. They are resolved and recorded from live evidence during
the run — never filled in from memory. See
[`job-spec.md`](plugins/orchestrate/skills/orchestrate/references/job-spec.md) for the
full schema.

### Output layout

This block is a summary of the [normative tree](plugins/orchestrate/skills/orchestrate/references/output-layout.md),
which owns the layout.

```text
plans/reports/orchestrate-<timestamp>/
  jobs.yaml            # private resolved input; do not export wholesale
  state.json           # authoritative attempts and acceptance fingerprints
  metrics.jsonl        # per-attempt observed outcomes
  runtimes.json        # current discovery and control evidence
  decisions.jsonl      # enumerated decision traces; exclude unless reviewed
  calibration.json     # per-classifier threshold, sample count and expiry
  trace.jsonl          # the correlated record; redacted on write
  report.md            # checks, arbiter verdict, integration; carries traceStatus
  worktrees/<job-id>/
  supervisor/<supervisor-run-id>/
    events.jsonl
    graph.json
    output-<job-id>.log
  <job-id>/
    command.txt          # CLI jobs
    stdout.txt           # CLI jobs
    stderr.txt           # CLI jobs
    result.md            # internal and native jobs
    session.json         # Pi jobs
    status.json
    native-<attempt-id>.json
    artifacts/
    attempt-<n>/
```

The tree above is a summary. [`output-layout.md`](plugins/orchestrate/skills/orchestrate/references/output-layout.md)
owns the run-directory and supervisor contract, and
[`job-spec.md`](plugins/orchestrate/skills/orchestrate/references/job-spec.md)
owns the per-job capture contract.

## Reference files

The skill keeps each durable contract in exactly one place, and it says which
one owns what:

| File | Owns |
|---|---|
| [`SKILL.md`](plugins/orchestrate/skills/orchestrate/SKILL.md) | The pipeline, dispatch, safety gate, limitations |
| [`runtime-adapter-contract.md`](plugins/orchestrate/skills/orchestrate/references/runtime-adapter-contract.md) | The adapter interface, conformance, command construction, OS revalidation |
| [`runtime-profile.md`](plugins/orchestrate/skills/orchestrate/references/runtime-profile.md) | Candidate discovery (including the classifier role), probing, `runtimes.json`, support states, timeouts, auto-profiler |
| [`event-protocol.md`](plugins/orchestrate/skills/orchestrate/references/event-protocol.md) | Normalized event envelope and kinds, cursor semantics, agent state machine, redaction and provenance |
| [`safety-policy.md`](plugins/orchestrate/skills/orchestrate/references/safety-policy.md) | **Sole safety authority**: risk tiers R0–R3, minimum controls, approval and authority, isolation, secrets, and what no signal may decide |
| [`routing-policy.md`](plugins/orchestrate/skills/orchestrate/references/routing-policy.md) | **Sole route-selection authority**: hard filter, capability tiers, task floors, floor-raising, ranking, fallbacks, reasoning controls |
| [`decision-plane.md`](plugins/orchestrate/skills/orchestrate/references/decision-plane.md) | The System-1 contract, provider sourcing, six decision tasks, the decision trace, and its non-authority |
| [`harness-portability.md`](plugins/orchestrate/skills/orchestrate/references/harness-portability.md) | The Agent Skills conformance surface, the forbidden harness dependencies, and every install and discovery path |
| [`benchmark-evidence.md`](plugins/orchestrate/skills/orchestrate/references/benchmark-evidence.md) | Measured outcome evidence, its sources, the durable cross-run cache, and what it may never decide |
| [`fallback-policy.md`](plugins/orchestrate/skills/orchestrate/references/fallback-policy.md) | The promotion chain, its triggers and budget, the per-concern control comparison, and the terminal fail-safe |
| [`trace-and-logging.md`](plugins/orchestrate/skills/orchestrate/references/trace-and-logging.md) | Span identifiers, the correlation rule, retention and export |
| [`verification.md`](plugins/orchestrate/skills/orchestrate/references/verification.md) | The three verification layers, the **escalation matrix**, calibration, arbiter contract, presentation parity |
| [`graph-optimizer.md`](plugins/orchestrate/skills/orchestrate/references/graph-optimizer.md) | Graph reduction, merge algebra, refusal conditions, resume semantics |
| [`internal-routing.md`](plugins/orchestrate/skills/orchestrate/references/internal-routing.md) | The internal adapter: in-session dispatch, capture, timeout, resume, agent resolution |
| [`job-spec.md`](plugins/orchestrate/skills/orchestrate/references/job-spec.md) | YAML schema, run-state and resume contract, capture contract, machine fields |
| [`observation.md`](plugins/orchestrate/skills/orchestrate/references/observation.md) | Incremental observation, watchdog handoff, intervention, diagnosis |
| [`failure-modes.md`](plugins/orchestrate/skills/orchestrate/references/failure-modes.md) | Hard stops for failure, timeout, permission, interruption, ownership |
| [`dispatch-hardening.md`](plugins/orchestrate/skills/orchestrate/references/dispatch-hardening.md) | Long, detached and network-dependent job mechanics on sandboxed hosts |
| [`output-layout.md`](plugins/orchestrate/skills/orchestrate/references/output-layout.md) | Run-directory and supervisor capture tree, decision artifacts, export rules |
| [`metrics-and-self-improvement.md`](plugins/orchestrate/skills/orchestrate/references/metrics-and-self-improvement.md) | Run comparison, arbiter-gate telemetry, calibration inputs |
| [`runtimes/README.md`](plugins/orchestrate/skills/orchestrate/runtimes/README.md) | The adapter index, the authoring procedure, and the per-runtime probe targets |
| [`runtimes/pi.md`](plugins/orchestrate/skills/orchestrate/runtimes/pi.md) · [`pi-onboarding.md`](plugins/orchestrate/skills/orchestrate/runtimes/pi-onboarding.md) | Pi session/dispatch contract and Pi install/auth/projection. A full note written from an authoring-time smoke run — not a live probe for your host, which every run still requires |
| [`runtimes/`](plugins/orchestrate/skills/orchestrate/runtimes) — `omp`, `agy`, `grok`, `claude`, `codex`, `gemini`, `opencode`, `aider` | Adapter index. `omp`, `agy` and `grok` are documented probe targets; `claude`, `codex`, `gemini`, `opencode` and `aider` are fenced **unverified stubs**. None of the eight is a support claim, and none is in any inventory until a probe is recorded |

## Upgrading

### From 2.1.0 to 2.2.0

An **additive** release — 2.2.0 removes no file and changes no path. The `/orchestrate`
command, its arguments and the `jobs.yaml` schema are unchanged, so an existing spec
still validates. Four reference documents are added, `.gitignore` gains dotenv and
cache rules, and five visible behaviours change.

What you will notice:

- **It installs through the skills CLI.** `npx skills add bestagentkits/orchestrate`
  installs the payload on any harness that implements Agent Skills. The Claude Code
  marketplace install and the plain-skill copy both still work; the skill is no longer
  documented as Claude-Code-only.
- **Routing is ranked by benchmark evidence.** Candidates that already passed the hard
  filter are ordered by measured success rate, cost per task and task duration at a
  given reasoning effort, and that evidence is cached **between runs** at
  `.orchestrate/benchmarks.json`.
- **Infrastructure failures promote.** A quota limit, an outage or a crash moves the
  job to the next candidate, after the same-runtime retry budget and honouring a
  declared `fallback_runtime` order first, within a bounded budget that ends in a
  logged `blocked` state.
- **Credentials resolve from four documented locations** — process environment, project
  `.env`, the `skills/` directory `.env`, then the skill's own `.env` — and the value is
  passed only through the inherited child environment, never as an argument or in a
  prompt.
- **The trace gains span identifiers**, so operations inside one attempt are
  distinguishable and a promoted attempt is distinguishable from a retry.

Two rules got stricter, and both are worth knowing before you rely on the new paths:

- Benchmark evidence **cannot** change eligibility, a floor, a tier, a control or an
  approval. It ranks candidates; it never gates them.
- A **failed check never promotes**, and neither does a permission or authorization
  stop. Promoting past either would be retrying until the check passes.

New reference documents:

- [`references/harness-portability.md`](plugins/orchestrate/skills/orchestrate/references/harness-portability.md)
- [`references/benchmark-evidence.md`](plugins/orchestrate/skills/orchestrate/references/benchmark-evidence.md)
- [`references/fallback-policy.md`](plugins/orchestrate/skills/orchestrate/references/fallback-policy.md)
- [`references/trace-and-logging.md`](plugins/orchestrate/skills/orchestrate/references/trace-and-logging.md)

New in 2.2.0, owner-fixed constants:

- Cache TTL: `CACHE_TTL_DEFAULT_HOURS` = 168 (seven days), `CACHE_TTL_MAX_HOURS` = 720
  (thirty days).
- Promotion budget: `MAX_PROMOTIONS_DEFAULT` = 2, `MAX_PROMOTIONS_MAX` = 4.

Also fixed in 2.2.0: a corrupted sentence in `routing-policy.md` that read "its the
floor deltas have already raised floors". It was found while rewriting that step and
corrected in place.

### From 1.8.x to 2.0.0 — breaking

**This release is breaking for anyone who linked to or bookmarked the old
reference files.** Six paths stop existing and two of them are renamed rather
than deleted, so a stale link may resolve to nothing or to a different contract
than the reader expects. There are no redirect stubs, deliberately: a stub would
create a second place a contract appears to live, which is the defect this
release exists to remove.

| 1.8.x path | 2.0.0 status | Destination |
|---|---|---|
| `references/model-routing.md` | **deleted** | Split: `routing-policy.md` (deterministic selection) and `decision-plane.md` (semantic signals) |
| `references/runtime-matrix.md` | **deleted** | Merged into `runtime-profile.md` and `runtime-adapter-contract.md` |
| `references/harness-profiles.md` | **deleted** | Merged into `runtime-profile.md` and `safety-policy.md` |
| `references/arbiter-checklist.md` | **deleted** | Absorbed into `verification.md` |
| `references/pi-sessions.md` | **renamed and moved** | `runtimes/pi.md` |
| `references/pi-onboarding.md` | **renamed and moved** | `runtimes/pi-onboarding.md` |

If you maintain automation that reads these files, update the paths. If you only
invoke `/orchestrate`, nothing is required.

What else changed:

- **Routing is now explicitly two-stage.** A deterministic hard filter decides
  eligibility and floors; an optional provider-neutral System-1 plane supplies
  scored signals that may only *raise* a floor. Safety authority did not move: it
  is consolidated in `safety-policy.md`.
- **Acceptance is now tiered and explicit.** A no-C3 acceptance requires an
  attempt whose recorded tier is R0/R1, no risk-floor raise, a valid
  per-classifier calibration record meeting owner-fixed floors, and every other
  gate condition. R2, R3, any verdict job, and any tier raised by a semantic
  signal always escalate. Acceptance is recorded per attempt, and the report
  states the accepted-without-C3 count.
- **Observation is normalized.** Every runtime's output is translated into one
  event protocol, so a new runtime adds an adapter rather than a branch in every
  consumer.
- **Runtime notes moved out of core.** Pi is no longer privileged in the skill's
owner–contract map; it is an adapter note like any other.

The skill name, the `/orchestrate` command, and the `--yes`, `--internal` and
`--resume` arguments are unchanged.

### From 2.0.0 to 2.1.0

A defect-fix release that closes two holes in the acceptance gate and tightens
several allowances. No file path changes, and the `/orchestrate` command, its
arguments and the `jobs.yaml` schema are unchanged, so an existing spec still
validates. It is a minor rather than a patch release because two things a reader or
a tool may depend on did change: `state.json` records acceptance per attempt, and
a job whose risk floor a semantic signal raises now escalates to C3.

If you invoke `/orchestrate`, every change below only makes the gate stricter:

- **A risk-floor raise now reaches the field the gate reads.** The semantic
  router's adjustment is recorded as two separate deltas,
  `capabilityFloorDelta` and `riskFloorDelta`. The recorded `riskTier` is
  `max(tierDerivation, riskFloorDelta)`, and any attempt carrying a non-zero
  `riskFloorDelta` always escalates to C3. Previously a raise could leave
  `riskTier` reading R1 while `routing-policy.md` treated the job as R2, so the
  acceptance gate read a weaker tier than the router acted on.
- **Calibration can no longer be satisfied by an empty record.** The micro-arbiter
  path requires at least 30 comparable C3-audited outcomes, measured agreement of
  at least 0.95, a threshold of at least 0.90, and a record covering all three
  signals. Those are policy constants owned by `verification.md`, so a job spec can
  no longer set its own bar; a missing or lower `calibration.minimum_samples`
  disables the no-C3 path instead of lowering it.
- **Signal direction is explicit.** `artifact_matches_expected_output` and
  `claims_supported_by_evidence` must be `>= threshold`;
  `materially_unresolved` must be `< threshold`.
- **Review verdicts always escalate.** `review`, and any job whose artifact is a
  verdict on another job's work, escalated only by convention before; they are now
  in the always-escalate list.
- **Permission bypasses are never enabled.** The exception that permitted a bypass
  with approval is removed. A job needing more privilege gets scoped permissions,
  a stronger external boundary, or `blocked`.
- **Review independence is binding.** With no different-family route, the verdict
  is labeled `not-independent` and the job is blocked unless a fresh,
  independently configured context substitutes.
- **The decision plane may not authorize its own egress.** Sending prompts or
  repository context to a provider requires a recorded user-authorization scope;
  with none, the plane is disabled for the run.
- **Acceptance is recorded per attempt.** `state.json` gains `attemptRecords[]` and
  the job-level fields become aggregates, because calibration needs the
  per-attempt pairing. The job-level `floorDelta` is replaced by the per-attempt
  `capabilityFloorDelta` and `riskFloorDelta`, which are recorded separately
  because only the risk delta changes the tier and forces a C3 call. Each attempt
  also records the `model` it resolved and the reasoning effort it ran at
  (`effortLevel`, `effortRaw`), so a promoted attempt's values never overwrite its
  predecessor's.

### From 1.4.x to 1.8.0

- **Metrics moved into the run.** 1.4.x appended to
  `plans/reports/orchestrate-history.jsonl`. 1.8.0 writes a per-attempt
  `metrics.jsonl` inside each run directory and aggregates only comparable
  records when comparing runs. An existing history file is left in place and is
  simply no longer written to.
- **Agent sessions joined the runtime set.** Pi sessions became a first-class job
  target with their own probing, dispatch, capture and onboarding references.
- **Observation and intervention became explicit.** A run declares what liveness,
  activity and accepted progress mean for each job, instead of treating a quiet
  process as finished work.

## Maintainer notes

The doc-integrity sweep that verifies this reference set lives in
[docs/maintaining-the-docs.md](docs/maintaining-the-docs.md). Run it from the
repository root before merging a change here; it is the repository's verification
mechanism, in place of a test suite.

## What it is not

- **Not a daemon.** No scheduler, dashboard, account pool, or provider adapter. It
  coordinates runtimes that already exist on your machine. The optional decision
  plane is dispatched through a runtime already in your live inventory; it adds
  no provider client and no credential system, only a documented read order for the
  runtime's own provider key. With no key configured the plane is **disabled**.
- **Not a CLI dependency.** The coordinator owns the run directory described in
  `job-spec.md`. If the AgentKit CLI is installed, `ak orchestrate` supplies a
  deterministic engine for that same contract — it is never required.
- **Not a sandbox.** A git worktree prevents edit collisions between agents. It does
  not isolate processes, the network, or the filesystem.
- **Not shared memory.** Jobs share nothing implicitly; anything a downstream job needs
  must travel through an explicit dependency.
- **Not a stable catalog.** CLI commands, models, auth and safety behavior drift
  constantly. Every run revalidates them — that is the point.

## Credits

Extracted from the [AgentKit](https://agentkit.best) engineer kit and published
standalone by [bestagentkits](https://github.com/bestagentkits).

## License

[MIT](LICENSE)
