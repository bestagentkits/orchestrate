# Runtime Matrix

`/orchestrate` builds a runtime matrix for each run. This reference defines
that live evidence contract; it is intentionally not a durable provider roster
or command catalog. Runtime installation, authentication, flags, models, and
safety behavior must be revalidated in the actual execution environment.

[model-routing.md](model-routing.md) is the sole authority for selecting among
verified candidates. [harness-profiles.md](harness-profiles.md) defines the
evidence fields used by that decision.

## Candidate Set

Start with only candidates relevant to the requested run:

- explicit `runtime:` values in the job spec;
- entries in each job's `fallback_runtime` chain;
- `runtime: internal` when the current harness exposes an agent-dispatch
  interface;
- a runtime the user explicitly asks the coordinator to consider.

Treat each value as a candidate identifier, not proof of support. Do not add a
runtime because it appeared in an old report or this repository's history. Do
not install, update, authenticate, or alter configuration during discovery.

The current [job-spec.md](job-spec.md) and active dispatch implementation own
accepted identifiers. If they disagree, stop and report the contract mismatch
instead of inventing a mapping.

## Live Matrix Record

Write the inventory to `<run-dir>/runtimes.json`. Each candidate record should
contain at least:

```json
{
  "id": "<candidate-id>",
  "kind": "cli|internal|skill-run",
  "state": "available|constrained|unverified|unavailable",
  "binary": "<resolved-path-or-null>",
  "version": "<live-value-or-null>",
  "authenticated": true,
  "hostOS": "<live-os>",
  "models": ["<live-resolved-choice>"],
  "agents": [],
  "headless": true,
  "cwdControl": "enforced|argument-only|prompt-only|none|unverified",
  "approval": "per-operation|scoped|auto|none|unverified",
  "toolGating": "granular|coarse|none|unverified",
  "isolation": "os-sandbox|container|worktree|prompt-only|none|unverified",
  "nativeBudget": "<verified-control-or-null>",
  "externalTimeout": true,
  "capture": ["final-result", "exit-status"],
  "resume": "supported|unsupported|unverified",
  "evidence": ["<probe-or-current-official-doc>"],
  "notes": []
}
```

Never include tokens, cookies, credential values, raw environment variables,
or sensitive command arguments. Empty arrays and `null` are preferable to
guessed capability.

## CLI Probe Sequence

For each CLI candidate:

1. Resolve the executable using the active dispatcher or explicit user
   configuration. Record the absolute executable path without following a
   surprising shadow binary silently.
2. Run the runtime's non-mutating version command and live help.
3. From live help, verify the exact features needed by the job: headless
   invocation, cwd handling, output capture, model selection, permissions,
   native budgets, and resume.
4. If live help advertises a model or capability listing command, run it and
   record only the choices relevant to this run.
5. Use a non-mutating authentication/status probe when available. A runtime
   that would open an interactive login is `unavailable` for headless
   dispatch until the operator completes setup outside the run.
6. When help is ambiguous, consult current official documentation and record
   the exact source checked. Do not rely on copied command snippets.
7. Build a dry command template with redacted placeholders and validate its
   arguments before dispatch. Do not execute a write merely to test syntax.

An unknown flag or model is a failed probe. Re-check live help and current
official docs, then rebuild the command. Never guess a replacement or carry
flags between runtimes.

## Internal Probe Sequence

For `runtime: internal`, do not probe a binary:

1. list the agent types the current harness exposes;
2. read live agent descriptions, tools, permission boundaries, and model
   metadata when exposed;
3. record only agents available in this session;
4. mark unenforced prompt constraints and accounting-only timeouts plainly;
5. apply dispatch and capture behavior from
   [internal-routing.md](internal-routing.md).

An on-disk agent definition is supporting evidence, not proof that the current
session can dispatch it. Prefer the live harness list.

## Command Construction

Construct each CLI command from the verified live surface. A dispatch command
must establish or record:

- non-interactive/headless invocation;
- exact working directory;
- prompt transport that preserves content without shell interpolation;
- resolved model only when the route requires or supports model selection;
- least-privilege approval, tool, and write controls;
- structured or bounded output capture;
- coordinator-owned external timeout;
- redacted command capture in `<job-id>/command.txt`.

Use prompt files or stdin for multiline, quote-heavy, or untrusted text when
the live runtime supports them. Otherwise use the host shell's safe argument
passing; never concatenate untrusted prompt text into a shell command.

Do not add a permission bypass merely because the process is unattended. If
headless mode is inherently auto-approved, record the constraint and limit it
to work allowed by the risk policy.

## OS Revalidation

Record the host OS and shell before command construction. Verify rather than
assume:

- executable naming and installation path;
- quoting, stdin, and prompt-file behavior;
- path separators, path length, and worktree support;
- whether sandbox claims apply on this OS;
- how external process timeouts and cancellation work;
- whether extra writable roots weaken isolation.

When OS enforcement is weaker than the requested risk tier, use a stronger
external boundary or block the route. A worktree prevents edit collisions but
is not an OS sandbox.

## Support States

The live matrix uses evidence states rather than a permanent support tier:

| State | Required evidence | Allowed use |
| --- | --- | --- |
| `available` | Command, auth, required controls, and capture verified live | Eligible for routing |
| `constrained` | Dispatch verified, but controls or capture have known limits | Eligible only when policy accepts those limits |
| `unverified` | Candidate exists, but required behavior was not proven | Advisory/non-load-bearing work only |
| `unavailable` | Missing, unauthenticated, incompatible, or failed probe | Do not dispatch |

Runtime selection, capability floors, risk floors, and fallback acceptance are
defined only in [model-routing.md](model-routing.md).

## Timeout Contract

- Bound every CLI job with a coordinator-owned process timeout.
- Treat native wall-time, turn, or tool-call limits as defense in depth.
- On timeout, stop the process using the host's verified mechanism, preserve
  bounded partial output, mark the job failed, and block dependents.
- Internal timeouts are accounting-only unless the current harness proves a
  cancellation mechanism; scope those prompts tightly.

## Safety Gate

Before dispatch, confirm:

- runtime and model or agent were observed live;
- cwd and writable roots match the job;
- approval and tool controls meet the assigned risk tier;
- parallel writers are isolated in separate worktrees and own disjoint files;
- destructive or external actions have explicit user approval and rollback;
- prompt and capture paths cannot expose secrets;
- command flags were verified for this installed runtime and OS;
- a fallback will be re-profiled rather than inheriting the failed command.

If any required field is unknown, downgrade the candidate to `unverified` or
block it. Do not infer safety from a runtime brand or prior successful run.

## Drift and Failure Handling

- Version, help, authentication, or model-list changes invalidate the affected
  cached profile for this run.
- A command-line parse failure returns to the probe step once; it is not a
  reason to try guessed flags repeatedly.
- A runtime crash, timeout, or permission prompt is a job failure. Preserve
  evidence and apply the declared fallback through
  [model-routing.md](model-routing.md).
- Update evergreen docs only when the evidence procedure or safety invariant
  changes. Do not paste the newly observed provider catalog back into these
  references.

## Verification Rule

Before every dispatch, verify the selected runtime's current command and
controls from the live binary, supplementing with current official
documentation when necessary. Record the evidence in `runtimes.json` and the
resolved command in capture. Stale examples are never an execution contract.
