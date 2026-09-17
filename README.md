<div align="center">

# Orchestrate

**Multi-runtime agent orchestration for Claude Code.**

Coordinate staged or parallel jobs across live-verified coding-agent runtimes,
coding-agent sessions and in-session subagents — routed by capability and risk,
isolated in git worktrees, fully captured, resumable, and blocked from
declaring success until deterministic checks pass and, for anything above
read-only or scoped-write work, an independent arbiter agrees.

[**Live site →**](https://sites.agentwiki.cc/s/rDUlzFFGwTCGPT0jo59FB/) ·
[Skill contract](plugins/orchestrate/skills/orchestrate/SKILL.md) ·
[Install](#install) ·
[MIT](LICENSE)

</div>

[![Orchestrate](assets/hero-light.png)](https://sites.agentwiki.cc/s/rDUlzFFGwTCGPT0jo59FB/)

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
  required. R0/R1 work may be accepted without a C3 call only with a valid
  calibration record. **R2, R3 and all judgment work always go to an independent
  C3 route**, or to a same-family fallback that is disclosed and recorded as a
  limitation.

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
| `R3` external/destructive | Deploy, release, delete, credentialed side effects | Explicit user approval, preview/rollback plan; blocked when those controls are unavailable |

Risk tiers are defined once, in
[`safety-policy.md`](plugins/orchestrate/skills/orchestrate/references/safety-policy.md);
the tables above summarize and link, they do not own the policy.

### The System-1 decision plane (optional)

Routing is deterministic. An optional, provider-neutral **decision plane** can
supply scored signals on top of it — how likely a trace is stalled, which
failure class an error belongs to, which capability a job actually needs — but
it never decides:

- It is sourced from a runtime **already in the live inventory**; there is no new
  provider dependency. Jev (TypeSafe) is the reference implementation and one
  optional provider.
- Its `floor_delta` may only **raise** a floor. A lowering signal is discarded.
- It never grants a permission, assigns a risk tier, emits a command, mutates
  shared state, weakens review independence, or replaces the C3 arbiter.
- With no eligible classifier it is **disabled** and deterministic policy decides.

Details: [`decision-plane.md`](plugins/orchestrate/skills/orchestrate/references/decision-plane.md).

## Install

### As a Claude Code plugin

```bash
/plugin marketplace add bestagentkits/orchestrate
```

```bash
/plugin install orchestrate@orchestrate
```

Restart Claude Code so the skill registers.

### As a plain skill

No plugin system required — copy the skill folder into your project or your home config:

```bash
git clone https://github.com/bestagentkits/orchestrate.git
cp -R orchestrate/plugins/orchestrate/skills/orchestrate ~/.claude/skills/
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

```text
plans/reports/orchestrate-<timestamp>/
  jobs.yaml            # private resolved input; do not export wholesale
  state.json           # authoritative attempts and acceptance fingerprints
  metrics.jsonl        # per-attempt observed outcomes
  runtimes.json        # current discovery and control evidence
  report.md            # checks, arbiter verdict, integration and questions
  worktrees/<job-id>/
  supervisor/<supervisor-run-id>/
    events.jsonl
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
| [`runtimes/pi.md`](plugins/orchestrate/skills/orchestrate/runtimes/pi.md) · [`pi-onboarding.md`](plugins/orchestrate/skills/orchestrate/runtimes/pi-onboarding.md) | Pi session/dispatch contract, and Pi install/auth/projection |
| [`runtimes/`](plugins/orchestrate/skills/orchestrate/runtimes) — `omp`, `agy`, `grok`, `claude`, `codex`, `gemini`, `opencode`, `aider` | Capability maps. `claude`, `codex`, `gemini`, `opencode` and `aider` are fenced **unverified stubs**, not support claims |

## Upgrading

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
- **Acceptance is now tiered and explicit.** R0/R1 work may be accepted without a
  C3 call only with a valid per-classifier calibration record; R2, R3 and all
  judgment work always escalate. The report states the accepted-without-C3 count.
- **Observation is normalized.** Every runtime's output is translated into one
  event protocol, so a new runtime adds an adapter rather than a branch in every
  consumer.
- **Runtime notes moved out of core.** Pi is no longer privileged in the skill's
owner–contract map; it is an adapter note like any other.

The skill name, the `/orchestrate` command, and the `--yes`, `--internal` and
`--resume` arguments are unchanged.

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

## Maintaining the docs

This repository ships no code, no `package.json` and no CI, so there is no
committed linter: a doc-integrity script would be its first executable, would sit
outside the published plugin payload, and would contradict the rule in
`dispatch-hardening.md` that bundled scripts resolve skill-relative rather than
from the repo root. Containment here is therefore **normative, not mechanical** —
and this section exists so that any maintainer can *re-run* it rather than trust
it.

Run the whole sweep before merging a change to this reference set. Every command
below is copy-pasteable, and the controls in step 2 verify that the checks
themselves work.

```bash
# 1. DENYLIST — no link to a deleted reference, and not to the old Pi location.
#    The alternation lives in a variable so this block cannot match itself.
refs='model-routing|runtime-matrix|harness-profiles|arbiter-checklist|pi-sessions'
grep -rnE "\]\([^)]*($refs)\.md\)" --include='*.md' . | grep -v '^\./plans/'
grep -rnE "\]\([^)]*references/pi-onboarding\.md\)" --include='*.md' . | grep -v '^\./plans/'
#    Both must print nothing.

# 2. CONTROLS — prove the denylist can catch a stale link and does not misfire.
#    The probe is assembled from parts so this block cannot match itself.
printf 'x [a](references/%s.md)\n' 'model-routing' > /tmp/stale.md
grep -qE "\]\([^)]*($refs)\.md\)" /tmp/stale.md && echo "control OK: stale caught" || echo "CONTROL FAILED"
printf 'x [a](runtimes/pi-%s.md)\n' 'onboarding' > /tmp/valid.md
grep -qE "\]\([^)]*references/pi-onboarding\.md\)" /tmp/valid.md && echo "CONTROL FAILED: valid flagged" || echo "control OK: valid relocated path not flagged"
rm -f /tmp/stale.md /tmp/valid.md

# 3. VERSION — exact surface counts, not merely "present".
test "$(grep -c '2\.0\.0' plugins/orchestrate/.claude-plugin/plugin.json)" = 1 || echo "FAIL plugin.json"
test "$(grep -c '2\.0\.0' plugins/orchestrate/skills/orchestrate/SKILL.md)" = 1 || echo "FAIL SKILL.md"
test "$(grep -c '2\.0\.0' site/index.html)" = 3 || echo "FAIL site (byline, spec table, vi i18n byline)"
grep -rn '1\.8\.0' plugins README.md site .claude-plugin --include='*.json' --include='*.md' --include='*.html' | grep -v 'README.md' && echo "FAIL stale version" || echo "version clean"

# 4. REACHABILITY — every reference and adapter note is linked by a peer,
#    whether the link is bare or path-qualified. A file must not count itself.
for f in plugins/orchestrate/skills/orchestrate/references/*.md \
         plugins/orchestrate/skills/orchestrate/runtimes/*.md; do
  b=$(basename "$f")
  grep -rqE "\]\([^)]*/?$b\)" --include='*.md' --exclude="$b" \
    plugins/orchestrate/skills/orchestrate README.md || echo "UNREACHABLE $b"
done

# 5. BOUNDARY — the accept predicate has exactly one owner.
grep -rln 'accept without C3' plugins/orchestrate/skills/orchestrate/references
#    Must print exactly: .../verification.md

# 6. PARITY — reader-facing surfaces must not state a weaker R2 control.
grep -n 'R2' README.md site/index.html plugins/orchestrate/skills/orchestrate/references/safety-policy.md
#    Each R2 row must mention worktree, checks, and arbiter review.

# 7. STUBS — unverified adapters stay unmistakably non-normative.
grep -L 'Status: unverified — not a support claim, not in inventory' \
  plugins/orchestrate/skills/orchestrate/runtimes/{claude,codex,gemini,opencode,aider}.md
#    Must print nothing.
```

**What these assertions do not do.** They prove that a sentence exists, a link
resolves, and a token is absent. They do **not** prove that R2 escalates, that a
calibration record is genuine, or that the decision plane holds no authority.
Those are semantic properties, and a grep cannot enforce a semantic rule. No
document in this set claims otherwise, and the two review passes that produced
this release found both of its Critical defects in exactly that gap — prose that
read correctly but meant the wrong thing. Treat the sweep as a regression net,
not as proof.

## What it is not

- **Not a daemon.** No scheduler, dashboard, account pool, or provider adapter. It
  coordinates runtimes that already exist on your machine. The optional decision
  plane is dispatched through a runtime already in your live inventory; it adds
  no provider client and no credential category.
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
