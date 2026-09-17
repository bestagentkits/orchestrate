# Runtime Matrix

`/orchestrate` builds a runtime matrix for each run. This reference defines
that live evidence contract; it is intentionally not a durable provider roster
or command catalog. Runtime installation, authentication, flags, models, and
safety behavior must be revalidated in the actual execution environment.

[model-routing.md](model-routing.md) is the sole authority for selecting among
verified candidates. [harness-profiles.md](harness-profiles.md) defines the
evidence fields used by that decision.

Probe candidates with a bounded local version and help check before trusting
any route. The probe never authenticates and never runs inference. An explicit
installation path handles an executable outside PATH, and a refresh discards
cached help evidence. A probe that exhausts its time budget is a probe-budget
failure, not a broken binary; raise the budget on a slow host. Probe Pi help
without extensions, because Pi otherwise loads every configured extension
package before printing help, so extension-provided flags are verified only at
dispatch.

Reuse discovery evidence only while runtime binary and version, account, host,
permissions, requested controls and model catalog remain unchanged; invalidate
on change or probe failure. Version is freshly probed; cached help is keyed by
resolved executable, version and config-file metadata and has a short expiry.
Metadata-preserving changes require a refresh. Advertised controls are not
verified execution guarantees.

Extend the probe report with a fresh, non-secret auth/readiness check and a
bounded task-relevant smoke test when the selected route requires them. Unknown
readiness cannot become a pass because an older cache or a successful help
command exists. On non-Unix hosts, a probe timeout bounds the direct child only;
it does not prove descendant cleanup.

With the AgentKit CLI installed, `ak orchestrate probe --json` performs this
version and help discovery; `--runtime` narrows candidates, repeated
`--path <id>=<executable>` handles explicit installations outside PATH,
`--refresh` discards cached help evidence, and `--timeout` raises the probe
budget.

## Candidate Set

Start with only candidates relevant to the requested run:

- explicit `runtime:` values in the job spec;
- entries in each job's `fallback_runtime` chain;
- `runtime: internal` when the current harness exposes an agent-dispatch
  interface;
- a runtime the user explicitly asks the coordinator to consider.

When the user asks to use other installed runtimes if available, discover
optional candidates through the active dispatcher's runtime registry and
explicit executable configuration. Use the optional CLI probes below for
requested candidates that have no dispatcher entry. A kit emitter or registry
entry is a discovery hint, not proof of a working headless runner.

Record whether each candidate is required by a job pin or optional discovery.
Skip unavailable optional candidates with a reason; do not block a qualified
route because another optional runtime is missing. Never substitute for a
pinned runtime without the user's authorization.

Treat each value as a candidate identifier, not proof of support. Do not add a
runtime because it appeared in an old report or this repository's history. Do
not install, update, authenticate, or alter configuration during discovery.

The current [job-spec.md](job-spec.md) and active dispatch implementation own
accepted identifiers. If they disagree, stop and report the contract mismatch
instead of inventing a mapping.

## Optional CLI Discovery

These names identify probe targets, not a support roster, model catalog, or
default route. When requested, consider Pi agent (`pi`), Oh My Pi (`omp`),
Google Antigravity CLI (`agy`), and Grok Build (`grok`) independently.

1. Resolve explicit executable configuration, then the current process PATH.
   If unresolved, inspect only the candidate's documented installation paths
   under the current user's home or package-manager bin directory. Record an
   outside-PATH executable's source and resolved symlink target; do not rewrite
   PATH, scan unrelated user directories, or silently switch binaries.
2. Bound version/help probes with an external timeout. Confirm product
   identity before trusting a same-named executable. A broken launcher is
   unavailable; a version response alone does not establish authentication.
3. Read the matching upstream reference below, then verify the selected
   invocation against installed help. Reuse an active dispatcher only when it
   exposes the controls the job needs; otherwise qualify a direct CLI route.

| Requested candidate | Upstream reference | Probe focus |
| --- | --- | --- |
| Pi agent (`pi`) | Installed package `docs/` and upstream GitHub repository `earendil-works/pi-mono`; session, dispatch and onboarding contract in [pi-sessions.md](pi-sessions.md) and [pi-onboarding.md](pi-onboarding.md) | Print/JSON versus RPC mode, provider/model resolution, tool and extension controls, explicit skill loading, project trust, run-scoped session directory and session identity |
| Oh My Pi (`omp`) | Oh My Pi README, upstream GitHub repository `can1357/oh-my-pi` | Print/JSON versus RPC/ACP mode, provider/model roles, cwd, approval, extensions, nested task agents, native time limit |
| Antigravity CLI (`agy`) | Google Antigravity headless documentation at `www.agy.dev/docs/cli/headless/` | Print input/output, model/agent discovery, sandbox on this OS, print timeout, conversation identity, instruction discovery |
| Grok Build (`grok`) | Grok Build CLI reference at `docs.x.ai/build/cli/reference` | Single-turn/prompt-file input, structured terminal result, model discovery, permission/sandbox controls, nested agents, session identity |

Do not copy Pi flags into OMP, equate an `agy` kit export with CLI execution
support, or equate a Grok model available inside Pi with the Grok Build runtime.
Verify whether native worktree flags actually apply in headless mode; otherwise
create the job worktree through the coordinator before launch.

Prefer a status-only, non-refreshing auth probe when advertised. Never use a
credential-printing command, a credential-output option, or read auth stores
to establish readiness. If no non-secret readiness probe exists, keep auth
unverified until an authorized bounded invocation proves it. Never start a
login, install, update, or configuration migration as discovery. A candidate
that a job or the user requires and that discovery reports missing or
unauthenticated leaves discovery and enters its onboarding reference as a
separate visible setup step (Pi: [pi-onboarding.md](pi-onboarding.md)), after
which it is probed again.

Record provider, resolved model, model family when evidenced, enabled
extensions, and nested-agent controls. Pi and OMP can select the same model
family as another runtime; different executable names do not prove independent
review. Disable unnecessary nested delegation using verified controls, or
account for it within the run's concurrency and budget before dispatch.

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
