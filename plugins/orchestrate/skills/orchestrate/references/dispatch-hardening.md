# Dispatch Hardening

Operational reality for dispatching long headless CLI jobs (notably `codex
exec`) from a **sandboxed or wrapped host** — IDE agent sandboxes such as Cursor,
tmux-less shells, and terminals whose event stream the coordinator cannot see.
These are execution mechanics, not route selection: routing stays owned by
[model-routing.md](model-routing.md); live command/flag/model verification stays
owned by [runtime-matrix.md](runtime-matrix.md).

Apply this reference whenever a job is expected to run longer than a few seconds,
runs detached, or writes a required artifact.

## Detached Process Survival

A sandboxed host can reap child processes when its own turn or shell context
ends. `nohup`/`disown` alone do **not** guarantee survival — the process often
stays inside the host's process tree and dies or is orphaned with it.

- Prefer a **supervisor that owns its own session**: `tmux new-session -d`
  (verify `tmux` is installed first) or, on macOS, a `launchd` job. These detach
  the worker from the coordinator's process tree so a long `codex exec` outlives
  the host turn.
- Fall back to `nohup … &` + `disown` only when no session supervisor exists,
  and treat completion as unproven until the artifact is verified.
- **Poll from outside the process tree.** Do not block the host turn waiting on
  the child. Write a `status.json` the worker updates, then poll that file (and
  the PID) independently. The coordinator's job is to observe state, not to hold
  the process open.
- Record the chosen supervisor (`tmux`/`launchd`/`nohup`) and the worker PID in
  `runtimes.json`/`state.json` so a resume can re-attach or re-poll.

## Capture That the Host Cannot Miss

A wrapped terminal often does not surface the child's streaming events, so an
"await the terminal" pattern silently misses completion.

- Redirect structured output to a file, not the terminal: capture the JSONL
  event stream to `stdout.txt` **and** write the final message to a file
  (`codex exec … -o result.md` / the runtime's `--output-last-message`
  equivalent, verified live).
- Treat the **file artifact** as the source of truth for completion, never the
  terminal scrollback.
- If the coordinator must produce `result.md` from a runtime that only prints to
  stdout, capture stdout and have the coordinator write the file — do not assume
  the child wrote it.

## Poller And Attempt Hygiene

Stale state is the top cause of false `DONE`.

- **Rotate before every attempt.** Delete or move the previous
  `status.json`, `result.md`, and stream captures into `attempt-<n>/` before
  redispatch. A leftover success file makes the poller report a fake completion.
- **Bind the poll to identity.** The poller confirms completion only when the
  `status.json` `startedAt` and worker `pid` match the attempt it launched. A
  matching status from an earlier attempt is not this attempt's result.
- **zsh gotcha:** in a zsh poller script, `status` is a readonly special
  variable. Name the loop variable `job_status` (or similar); assigning `status`
  aborts the script.

## Failure vs Transient Noise

Exit status and stderr both lie. Classify before failing a job.

- Fail the job only on a real signal: the runtime's `turn.failed` event, a
  non-zero process exit, or a **missing/empty required artifact**.
- Treat known transient stderr as noise, not failure: MCP `524` timeouts, model
  cache warm-up lines, malformed-agent-`toml` warnings, and similar startup
  chatter. Log them; do not abort on them.
- A clean exit with an empty `result.md` is still a failure (see runtime-matrix
  "Dispatch Result Verification"). Verify the artifact independently.

## Network-Dependent Jobs

Jobs that call `gh`, an MCP server, or any remote must not be able to hang the
whole coordinator turn on a network stall.

- **Embed the contract offline in the prompt.** Paste the issue/PR/plan text the
  job needs directly into its prompt rather than instructing it to fetch. A
  network failure then degrades one job, not the run.
- Give every network call its own bounded timeout inside the job, and keep the
  coordinator's external job timeout as the outer bound.
- If a required fetch fails, fail that job with the exact error and preserve
  partial capture; never let it silently wedge dependents.

## Plan Not On The Base Branch

When the plan/spec lives on a feature branch or worktree that the dispatch base
ref does not contain, a fresh job checks out the base and cannot see it.

- Before dispatch, **materialize the plan directory** the job needs: check out
  or copy the plan dir from its source branch/worktree into the job's `cwd`, or
  point the job at the worktree that already has it.
- Record the plan's **source** (branch, worktree path, or artifact) in
  `runtimes.json`/`state.json` so the arbiter and a later resume know where the
  reviewed content actually came from.

## Headless Plan-Review Jobs

Running an interview-driven plan skill headlessly needs an explicit prompt
contract, because the skill would otherwise wait on `ask_user`.

- **Disable interactive gates:** the prompt must instruct the job to skip
  `ask_user`/`AskUserQuestion` and instead **adjudicate itself** — for
  `validate`, answer each critical question with a recommended answer and mark
  confidence; for `red-team`, apply or defer each finding with a disposition.
- **Define the output contract:** findings/questions as a structured list with
  severity/disposition and file-cited evidence, so the arbiter can verify.
- **Arbiter cross-check:** a `red-team` that reports "no unresolved" while a
  companion `validate` still lists human-audit items is a contradiction — the
  arbiter fails the run until reconciled.
- **Scan companion artifacts after validate.** Do not trust `plan.md` alone: a
  `plan.html`, diagram, or exported summary can carry stale claims the markdown
  no longer makes. Diff the companion artifacts against the reviewed plan and
  flag drift.

## Skill Script Paths

Scripts bundled with a skill live in the **skill install directory**, not the
repo root. For example `scripts/worktree.cjs` resolves under the skill's own
path (`<skill-dir>/scripts/worktree.cjs`), which differs between a native
install, a plugin install, and a worktree checkout.

- Reference bundled scripts by an **absolute or skill-relative path** resolved at
  runtime, never as a bare repo-root-relative path.
- When documenting a script invocation, state that the path is skill-relative and
  show how to resolve it, so a job dispatched in a different `cwd` still finds it.
