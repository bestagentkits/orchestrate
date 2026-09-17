# Runtime Adapter Contract

This file is the single authority for **what an orchestration runtime adapter
is**. It defines the interface every runtime implements, what each method
returns, how a command is constructed, how the host OS is revalidated, and what
conformance means. It is not a runtime roster, not a command catalog, and not a
model list.

- [runtime-profile.md](runtime-profile.md) owns the probe sequence, the
  `runtimes.json` record schema, and support states.
- [routing-policy.md](routing-policy.md) owns route selection.
- [safety-policy.md](safety-policy.md) owns what may run at each risk tier.
- [runtimes/README.md](../runtimes/README.md) owns the per-runtime authoring
  procedure and the adapter index.

A capability exists only when live evidence proves it. Declaring a capability in
an adapter note, a previous report, or this file proves nothing.

## Two implementations

The contract has exactly two shapes:

| Shape | Implemented by | Dispatch mechanism |
| --- | --- | --- |
| **CLI adapter** | a headless executable | `start` launches a process; `observe` reads its capture |
| **Internal adapter** | the current harness's in-session subagent mechanism | `start` dispatches a native agent; `observe` reads the native handle |

[runtimes/README.md](../runtimes/README.md) is the adapter index.
`internal-routing.md` documents the internal adapter's dispatch, capture,
timeout and resume mechanics; it implements this same contract and must not
restate route selection.

## Interface

An adapter implements the methods below. **Required** methods must work for any
runtime eligible to receive a load-bearing job. **Optional** methods may be
absent; absence is recorded as `unsupported`, never assumed to work.

| Method | Requirement | Returns |
| --- | --- | --- |
| `discover()` | required | Candidate identities this host can see, with resolved executable path or native mechanism, without installing or authenticating |
| `probe()` | required | Bounded version/help/readiness/model evidence, per [runtime-profile.md](runtime-profile.md) |
| `profile()` | required | One normalized profile record for `runtimes.json` |
| `start(job)` | required | A durable handle, or an explicit failure |
| `observe(handle)` | required | Normalized events per [event-protocol.md](event-protocol.md) plus a settlement state |
| `capture(handle)` | required | Bounded, redacted output, exit status, declared artifacts |
| `steer(handle, instruction)` | optional | Whether the instruction was delivered; never assume delivery implies effect |
| `cancel(handle)` | optional | Confirmed settled state, or an explicit unconfirmed result |
| `resume(handle)` | optional | A continued handle bound to the same session identity |
| `fork(handle)` | optional | A new handle branched from an existing session |

Rules that follow from the interface:

- **Absence is not capability.** A missing `cancel` means cancellation is
  unverified; it does not mean the runtime stops when asked.
- **`steer` is not `cancel`.** A request sent is not a writer stopped.
- **`observe` must distinguish liveness, activity and progress**, because the
  trace watchdog consumes all three separately.
- **`capture` is bounded before persistence and redacted.** An adapter never
  writes unbounded or unredacted output to disk.
- **A handle is evidence, not proof.** Persisting a handle establishes
  identity; it does not establish that the work succeeded.

## What the profile must expose

`profile()` writes the record schema owned by
[runtime-profile.md](runtime-profile.md). At minimum it separates:

- identity and availability;
- authentication readiness (never credentials);
- headless entry and working-directory control;
- model or agent discovery and resolved family;
- permission, tool-gating and isolation controls **as verified**;
- capture tier and observation fidelity;
- resume/fork support;
- native budgets and coordinator-owned external timeout;
- `role`, which is `runtime` for a job-capable runtime and `classifier` for a
  decision-plane candidate.

## Internal probe sequence

For the internal adapter, do not probe a binary:

1. list the agent types the current harness exposes;
2. read live agent descriptions, tools, permission boundaries and model metadata
   when exposed;
3. record only agents available in this session;
4. mark unenforced prompt constraints and accounting-only timeouts plainly;
5. apply dispatch and capture behavior from
   [internal-routing.md](internal-routing.md).

An on-disk agent definition is supporting evidence, not proof that the current
session can dispatch it. Prefer the live harness list.

## Command construction

Construct each CLI command from the verified live surface. A dispatch command
must establish or record:

- non-interactive/headless invocation;
- exact working directory;
- prompt transport that preserves content without shell interpolation;
- resolved model only when the route requires or supports model selection;
- least-privilege approval, tool and write controls;
- structured or bounded output capture;
- coordinator-owned external timeout;
- redacted command capture in `<job-id>/command.txt`.

Use prompt files or stdin for multiline, quote-heavy or untrusted text when the
live runtime supports them. Otherwise use the host shell's safe argument
passing. Never concatenate untrusted prompt text into a shell command.

Do not add a permission bypass merely because the process is unattended. If
headless mode is inherently auto-approved, record the constraint and limit it to
work the risk policy allows.

## OS revalidation

Record the host OS and shell before command construction. Verify rather than
assume:

- executable naming and installation path;
- quoting, stdin and prompt-file behavior;
- path separators, path length and worktree support;
- whether sandbox claims apply on this OS;
- how external process timeouts and cancellation work;
- whether extra writable roots weaken isolation.

When OS enforcement is weaker than the requested risk tier, use a stronger
external boundary or block the route. A worktree prevents edit collisions but is
not an OS sandbox.

## Conformance

An adapter conforms when all of the following are proven on this host, for this
installed version:

1. `discover` and `probe` complete within their budget without installing,
   authenticating or mutating the host;
2. `profile` emits a record satisfying the schema, with every unproven field
   written `unverified`;
3. `start` launches the job through the verified command, in the pinned cwd,
   with the assigned controls;
4. `observe` yields normalized events that identify settlement, and does not
   fabricate tool success from an unsupported provider event;
5. `capture` produces bounded, redacted output plus a real exit status or an
   explicit native-result equivalent;
6. every required control the job's risk tier depends on is verified, not
   advertised;
7. an adapter note exists under `runtimes/` and is linked from the index.

A non-conforming adapter is not load-bearing. It may contribute advisory
evidence only, and only when paired with a verified route.

## Verification rule

Before every dispatch, verify the selected runtime's current command and
controls from the live binary, supplementing with current official documentation
when necessary. Record the evidence in `runtimes.json` and the resolved command
in capture. Stale examples are never an execution contract.

This is the rule an adapter note must defer to: the note names *what to probe*,
never *what the answer will be*.
