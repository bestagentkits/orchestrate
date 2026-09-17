# Pi Adapter

This note is the Pi implementation of
[runtime-adapter-contract.md](../references/runtime-adapter-contract.md).
`/orchestrate` can dispatch Pi coding-agent (`pi`) sessions as headless
jobs and chain them through their session files. This reference explains how
to probe, dispatch, continue, capture and bound those sessions. It sits on top
of the evidence contract in [runtime-profile.md](../references/runtime-profile.md) and the
adapter contract in [runtime-adapter-contract.md](../references/runtime-adapter-contract.md);
route selection stays in [routing-policy.md](../references/routing-policy.md).

Flags named here are the ones the installed help advertised when this
reference was written. Pi changes between releases and user extensions add
their own flags, so verify every flag against `pi --help` on the host before
building a command. The bundled documentation of the installed package
(`docs/` next to its `package.json`) and the upstream `earendil-works/pi-mono`
repository are the sources for behavior that help text does not settle.

## When Pi is a candidate

The probe identifier and job-spec value for Pi is `pi`. Pi enters the
candidate set when a job pins it, a fallback chain lists it, or the user asks
for Pi sessions in the request. A request such as "run the scouts as pi
sessions" is an explicit ask: treat a missing or unauthenticated Pi as a job
requirement and run [pi-onboarding.md](pi-onboarding.md) as a visible setup
step, then probe again. Without such a request, a missing Pi is skipped with
a reason.

## Probe Pi

Run a bounded help probe — `pi --help` under an external timeout with
`--no-extensions` set. Pi otherwise loads every configured extension package
before printing help, which runs user code during discovery and can take far
longer than any probe budget. Extension-provided flags therefore do not appear
in probe evidence; verify them against live help before dispatch. A probe that
times out on a slow host needs a longer budget, not a different binary. With
the AgentKit CLI installed, `ak orchestrate probe --runtime pi --json` performs
this probe and reports a budget failure as `help-probe-timeout`.

Then extend the probe report with run-specific evidence:

- **Identity:** the help banner names the pi coding agent; record the
  resolved executable and version.
- **Readiness:** `pi auth check --provider <provider> --no-refresh --json`
  reports `ready` or `not_ready` with a reason and prints no credential. Use
  it for every provider the route may select. The `print-api-key`,
  `print-bearer-token` and `--credentials` forms emit secrets and are never
  part of discovery or capture.
- **Models:** `pi --list-models [search]` lists what this installation can
  resolve; record only the choices relevant to the run and the model family
  behind them.
- **Extensions:** `pi list` shows the packages that will load by default.
  Note the ones that spawn child agents, run background tasks, or manage
  worktrees, because they change concurrency and write behavior.

Record the candidate in `<run-dir>/runtimes.json` with `kind: cli`,
`headless: true`, the verified controls below, and `evidence` naming the
probe, the auth check and any bundled doc consulted.

## Session model

Every Pi run is a session: a JSONL tree that Pi saves under its session
directory, by default inside the user's profile and organized by working
directory. That is what makes Pi orchestrable beyond one-shot prompts:

- **Run-scoped storage.** Give each run its own directory with
  `--session-dir <run-dir>/pi-sessions`. Job sessions then live with the run
  capture, stay out of the user's own history, and can be resumed
  deterministically by later jobs.
- **Handle.** In `--mode json` the first stdout line is the session header
  `{"type":"session","id":...,"cwd":...}`. Store the id and the session file
  path in `<job-id>/session.json`; that is the job's resume handle.
- **Names.** Pass `--name <job-id>` so the session is identifiable in
  Pi's own picker and in the run report.
- **Continuation.** A dependent job continues its upstream session with
  `-c` (most recent session in that session directory) or with
  `--session <id|path>` when several jobs share the directory. This carries
  the upstream context without re-sending artifacts, verified by a
  two-step smoke run during authoring.
- **Variants.** `--fork <id|path>` starts a new session from an existing one,
  which suits fan-out over one scout result.
- **Ephemeral.** `--no-session` for smoke tests and throwaway probes.
- **Export.** `--export <file>` renders a session to HTML for the report.

A continued session is memory, not proof. Acceptance still verifies the
artifacts and checks declared in the job spec.

## Dispatch command shape

Illustrative template; every placeholder and flag is resolved from the live
profile before `prepare`:

```text
env PI_OFFLINE=1 pi -p --mode json \
  --session-dir <run-dir>/pi-sessions --name <job-id> \
  --provider <provider> --model <model> [--thinking <level>] \
  (--tools <allowlist> | --exclude-tools <denylist>) \
  (--no-approve | --approve) \
  [--no-extensions] [--no-skills --skill <path>] [--no-context-files] \
  @<run-dir>/<job-id>/prompt.md
```

- **Working directory.** Pi has no cwd flag; the coordinator starts the
  process inside the job's worktree. Record `cwdControl` as process-owned and
  remember that Pi's tools have no write boundary beyond that directory.
- **Prompt transport.** Pi reads `@<file>` arguments and positional messages.
  Write the prompt to a file under the job directory; never interpolate
  untrusted text into the shell command.
- **Offline startup.** `PI_OFFLINE=1` disables update checks and package
  installs at startup, so a job cannot mutate the user's profile mid-run.
  Package installation belongs to onboarding, not dispatch.
- **Timeout.** No native time limit is advertised. The coordinator-owned
  external timeout is the only bound.
- **Tool gating.** `--tools` and `--exclude-tools` take tool names across
  built-in and extension tools; `--no-tools` leaves a reasoning-only job. The
  built-in names appear in the help banner. A read-only job allows the read
  and search tools and excludes the shell, edit and write tools.
- **Approval and isolation.** Headless Pi has no per-operation approval and no
  built-in sandbox; it runs with the user's permissions. Profile it as
  `approval: auto` and `isolation: prompt-only`, which the risk policy accepts
  for read or report work and for writes only inside a coordinator-created
  worktree. Destructive or credentialed external work never runs on Pi alone.
- **Project trust.** Non-interactive modes show no trust prompt.
  `--no-approve` ignores project-local `.pi/*` resources and `.agents/skills`
  for the run; `--approve` trusts them. Default to `--no-approve` and load the
  specific skill the job needs with `--skill <path>`, which is additive even
  under `--no-skills` and needs no trust decision. Use `--approve` only when
  the job depends on the project's own AgentKit projection and the user
  already trusts that repository. Context files load regardless of trust
  unless `--no-context-files` is set.
- **Extensions.** User packages load by default, register their own flags and
  tools, and add startup time. A job that does not need them runs with
  `--no-extensions` (explicit `-e <path>` still loads). When extensions stay
  on, exclude child-agent and background-task tools by name or count their
  nested work in the run's concurrency and budget.
- **Model.** `--provider` and `--model` accept `provider/id` with an optional
  `:<level>` thinking suffix; `--thinking` sets the level. Record the resolved model
  family. Pi can select the same family as another runtime, so a Pi arbiter
  is not independent review by executable name alone.

## Capture

`--mode json` yields a structured event stream and is the preferred capture
tier: the session header, `message_end` records with the authoritative
assistant text, `tool_execution_*` events, and `agent_end` at settlement.
Cumulative usage rides on `message_update.usage`. Save stdout to
`<job-id>/events.jsonl`, stderr separately, and keep the exit status. The
supervisor's bounded redacted capture applies; note truncation and which
region survived. Plain `-p` returns final text only and supports advisory
work, not load-bearing checks.

An exit without `agent_end` in the stream is an unsettled attempt regardless
of exit status. A startup line about installing or updating packages means
the job ran without `PI_OFFLINE=1`; stop, record the mutation, and re-dispatch
offline.

## Intervention through RPC

`pi --mode rpc` runs a long-lived session driven by JSONL commands on stdin:
prompt, steer, follow-up, abort, state and session statistics, HTML export,
session switch and fork. It is the native intervention channel described in
[observation.md](../references/observation.md), but only for a harness that holds stdin
open and owns the process. The coordinator launches an argv and captures
output; verify whether the active supervisor drives stdin before promising RPC
intervention. When it does not, intervene by stopping the attempt through the
external timeout and continuing the same session in a new print-mode attempt
with `--session`.

## Parallel and nested sessions

Parallel Pi writers follow the worktree rules in SKILL.md: one worktree per
job and disjoint ownership. Jobs may share the run's session directory
because each session is its own file, but each job gets its own `--name`.
Prefer coordinator-level parallelism (`concurrency:` in the spec) over Pi
extensions that spawn child agents, so every attempt leaves evidence in the
run and stays inside the declared budget.

## Failure signatures

| Observation | Meaning | Action |
| --- | --- | --- |
| Probe help times out | Launcher startup exceeded the probe budget on this host | Re-probe with a longer budget |
| Auth check `not_ready` with `provider_not_found` | Provider name unknown to this installation | Check `--list-models` and the provider name; do not guess |
| Auth check `not_ready` without credentials | Provider not logged in | Onboarding auth step; the user logs in |
| Skill named in the prompt was not loaded | `--no-approve` skipped project-local resources | Pass `--skill <path>` explicitly |
| Stream ends without `agent_end` | Truncated or interrupted attempt | Treat as unsettled; inspect stderr and supervisor events |
| Unknown flag error | Help drift or an extension flag that is off | Re-read live help; rebuild the command |
