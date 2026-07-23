# Harness Profiles

This reference defines the evidence collected for each live orchestration
harness. It is not a runtime catalog and does not choose routes. The sole
selection policy is [model-routing.md](model-routing.md).

Harness behavior changes with the installed version, host OS, account policy,
and invocation mode. Build profiles during preflight and store them in
`<run-dir>/runtimes.json`; never reuse this document as proof that a runtime is
installed, authenticated, safe, or capable.

## Profile Schema

Record these fields for every candidate named by the job spec, fallback chain,
or current internal harness:

| Evidence | What to record |
| --- | --- |
| Identity | Runtime id, executable or internal mechanism, live version when exposed |
| Availability | Resolved path or live agent-list evidence; available, constrained, unavailable, or unverified |
| Authentication | Non-interactive readiness only; never credentials, tokens, or raw environment values |
| Headless entry | Verified command shape or internal dispatch mechanism |
| Working directory | Whether cwd can be pinned and how it is enforced |
| Model or agent discovery | Live listing mechanism and resolved choices; no copied catalog |
| Permissions | Approval modes, tool allow/deny controls, and whether headless mode auto-approves |
| Isolation | OS sandbox, container, worktree, prompt-only boundary, or none |
| Budgets | Native turn/tool/time controls plus coordinator-owned external timeout |
| Capture | Structured output, final-result capture, stderr, exit status, artifacts, and usage data |
| Resume | Supported session or job-state behavior, if verified |
| Enablement | Instruction files and skill locations actually loaded for this run |
| Host limits | OS, shell, quoting, path, or sandbox limitations that change the risk posture |
| Evidence source | Live help/probe and current official documentation consulted for ambiguous behavior |

Use `null` or `unverified` for unknowns. Do not turn absence of evidence into a
positive capability.

## Confidence States

| State | Meaning | Dispatch consequence |
| --- | --- | --- |
| **available** | Required headless path and controls were proven live | Eligible for policy evaluation |
| **constrained** | Dispatch works, but one or more controls are weaker than requested | Eligible only when the job's risk tier permits those limits |
| **unverified** | Installed or documented, but the required command, auth, model, or controls were not proven | Advisory work only; never load-bearing |
| **unavailable** | Missing, unauthenticated, incompatible, or failed probe | Remove from candidate set |

These states are evidence inputs. Capability and risk tier selection remains in
[model-routing.md](model-routing.md).

## Evidence Collection

For a CLI candidate:

1. Resolve the executable without installing or updating it.
2. Capture its live version and help output.
3. Verify only the flags the planned job needs: headless mode, cwd, output,
   model selection, permissions, and native budgets where applicable.
4. Use a live model-listing command only when the installed CLI advertises it.
5. Confirm authentication with a non-secret, non-mutating probe when possible.
6. Consult current official documentation for behavior that live help cannot
   establish, and record the page or command checked in the run inventory.
7. Run no write probe against the user's shared tree.

For `runtime: internal`, profile the current session's agent interface and live
agent definitions instead of a binary. See
[internal-routing.md](internal-routing.md).

Unknown flags, aliases, or model identifiers are probe failures. Re-verify the
candidate; never guess a replacement.

## Safety Evidence

Profile safety behavior by observed control, not product reputation.

- **Approval:** distinguish enforceable per-operation approval, scoped
  pre-approval, unconditional auto-approval, and unknown behavior.
- **Tool gating:** record whether read, write, shell, network, and external MCP
  access can be allowed or denied independently.
- **Write boundary:** record the enforced writable roots. A cwd argument alone
  is not a sandbox.
- **Isolation:** state whether the boundary is OS-enforced, containerized,
  worktree-only, prompt-only, or absent.
- **Timeout:** coordinator-owned process timeout is required for CLI jobs even
  when a native budget exists. Internal timeouts are accounting-only unless
  the current harness proves cancellation.
- **Bypass controls:** identify the live runtime's bypass options only to keep
  them disabled. Never add one to a default command.

An auto-approved or all-or-nothing write path is constrained for any shared
tree. It may handle read/report work; writing requires isolated R2 treatment
under [model-routing.md](model-routing.md). Destructive or external work still
requires explicit approval and the R3 gate.

## Capture Quality

Prefer evidence in this order when otherwise-qualified routes remain:

1. structured event stream plus final result, exit status, and artifacts;
2. bounded stdout/stderr plus explicit exit status;
3. final text only with harness-reported status;
4. unstructured output without trustworthy completion state.

Lower capture quality does not automatically disqualify R0 advisory work, but
it cannot support a load-bearing check whose result cannot be independently
verified. Record truncation and preserve useful first/last sections.

## Budget and Reliability Evidence

- Treat native turn, tool-call, or wall-time controls as defense in depth.
- Enforce an external process timeout for every CLI job.
- Record observed duration, status, usage, and cost only when the harness
  reports them reliably.
- Use cross-run metrics as advisory evidence after enough comparable samples;
  never let metrics silently rewrite routing policy.
- A beta, experimental, or partially verified path remains non-load-bearing
  until live evidence proves the controls required by the job.

## Harness Enablement

Before dispatch, verify the instruction and skill surfaces the live runtime
actually loads:

1. inspect current runtime documentation or live diagnostics for supported
   rules and skill locations;
2. confirm the relevant project/global instruction file and requested skill
   are present;
3. name the concrete skill path and expected output in the job prompt;
4. offer any needed AgentKit install or refresh as a visible setup step;
5. never install, update, authenticate, or mutate user configuration silently.

Do not maintain a copied table of runtime-specific paths here. The installed
runtime and AgentKit's current projection are execution-time evidence.

## Selection Handoff

After profiling, pass the candidates to
[model-routing.md](model-routing.md) with:

- live model or agent choices;
- capability evidence;
- permission, isolation, and timeout controls;
- capture confidence;
- OS limitations;
- authentication and availability state;
- cost/latency evidence when trustworthy.

That policy filters by risk first, then capability, reliability, evidence
quality, and budget. This file must not add task-to-runtime defaults or model
fallbacks.
