<div align="center">

# Orchestrate

**Multi-runtime agent orchestration for Claude Code.**

Coordinate staged or parallel jobs across live-verified coding-agent runtimes and
in-session subagents — routed by capability and risk, isolated in git worktrees,
fully captured, resumable, and blocked until an independent arbiter agrees.

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
- **Nothing is reported finished** until a separate arbiter — on an independently
  selected route, preferably a different model family — checks the claims against
  the evidence.

## Pipeline

| # | Stage | What it guarantees |
|---|-------|--------------------|
| 1 | Brainstorm & intake | Outcome, constraints and acceptance evidence are explicit. Secrets are refused at the door. If orchestration adds nothing, it says so. |
| 2 | Build the job graph | Jobs carry explicit `task`, `cwd`, timeout, expected output and file ownership. `depends_on` forms the stages. |
| 3 | Discover, profile, route | Live runtime inventory → harness profile → capability/risk route, recorded with its evidence source. |
| 4 | Apply the safety gate | Least privilege, permission bypass off, destructive/credentialed work needs approval for that exact scope. |
| 5 | Dispatch & capture | Worktrees created before dispatch, `state.json` updated on every transition, output bounded and redacted. |
| 6 | Arbiter review | Independent C3 route compares each result to its expected output and runs the declared checks. |
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
| `R2` isolated write | Parallel, high-impact, untrusted, or hard-to-revert changes | Separate worktree, enforced sandbox where available, explicit checks and arbiter review |
| `R3` external/destructive | Deploy, release, delete, credentialed side effects | Explicit user approval, preview/rollback plan; blocked when those controls are unavailable |

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
  jobs.yaml
  runtimes.json
  state.json
  report.md
  worktrees/<job-id>/
  <job-id>/
    command.txt      # CLI jobs only
    stdout.txt       # CLI jobs only
    stderr.txt       # CLI jobs only
    result.md        # internal jobs only
    status.json
    artifacts/
    attempt-<n>/
plans/reports/orchestrate-history.jsonl
```

## Reference files

The skill keeps each durable contract in exactly one place:

| File | Owns |
|---|---|
| [`SKILL.md`](plugins/orchestrate/skills/orchestrate/SKILL.md) | The pipeline, safety defaults, output layout, arbiter checklist |
| [`model-routing.md`](plugins/orchestrate/skills/orchestrate/references/model-routing.md) | Sole route-selection authority: capability/risk tiers, task defaults, fallback qualification |
| [`runtime-matrix.md`](plugins/orchestrate/skills/orchestrate/references/runtime-matrix.md) | Live candidate discovery, probing, command verification, `runtimes.json` |
| [`harness-profiles.md`](plugins/orchestrate/skills/orchestrate/references/harness-profiles.md) | Evidence schema for permissions, isolation, capture, budgets |
| [`internal-routing.md`](plugins/orchestrate/skills/orchestrate/references/internal-routing.md) | In-session subagent dispatch, capture, timeout, resume mechanics |
| [`job-spec.md`](plugins/orchestrate/skills/orchestrate/references/job-spec.md) | YAML schema and execution-state contract |

## What it is not

- **Not a daemon.** No scheduler, dashboard, account pool, or provider adapter. It
  coordinates runtimes that already exist on your machine.
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
