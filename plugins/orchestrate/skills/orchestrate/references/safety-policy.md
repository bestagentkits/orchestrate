# Safety Policy

This file is the single authority for **what may run**. It owns the risk tiers,
the minimum controls each tier requires, permission and approval rules, the
authority model, isolation boundaries, secret handling, and the list of decisions
no automated signal may make.

It does not select a route and does not score candidates.

- [routing-policy.md](routing-policy.md) owns eligibility, capability floors,
  ranking and fallbacks.
- [runtime-profile.md](runtime-profile.md) owns the control evidence that this
  policy consumes.
- [decision-plane.md](decision-plane.md) supplies signals; it holds no authority
  here.
- [verification.md](verification.md) owns acceptance and the arbiter contract.

When this file and any other disagree about a control, this file wins, and the
disagreement is reported as a contract mismatch rather than resolved silently.

## Risk Tiers

Risk determines the minimum harness controls independently of model capability.
A job runs only where both its capability floor and its risk floor are met.

| Tier | Effect | Minimum controls |
| --- | --- | --- |
| **R0 observe** | Read/report only | Explicit cwd, bounded timeout, captured result, no unnecessary write or shell grant |
| **R1 scoped write** | Reversible edits in owned files | Scoped write boundary, tool restrictions, diff capture, no permission bypass |
| **R2 isolated write** | Parallel, high-impact, untrusted, or hard-to-revert changes | Separate worktree **or stronger isolation**, enforced sandbox where available, **explicit checks and arbiter review** |
| **R3 external/destructive** | Deploy, release, delete, credentialed, or other external side effect | Explicit user approval, preview/rollback plan, strongest verified controls; block when those controls are unavailable |

Secrets never belong in prompts, logs, inventory or reports at any tier.

The R2 clause is deliberate and complete: worktree **or** stronger, sandbox where
available, checks **and** arbiter review. A presentation surface that states less
than this is wrong; see Presentation parity in
[verification.md](verification.md).

## Tier derivation

The tier is a deterministic derivation from declared job attributes, evaluated
**before execution** and recorded on the attempt.

| Declared attribute | Derived tier |
| --- | --- |
| read/report only, no mutating effect | R0 |
| reversible edits inside owned paths | R1 |
| untrusted prompt or input, parallel writer, high-impact or hard-to-revert change, or a candidate whose required controls are unverified | R2 |
| deploy, release, delete, credentialed or other external side effect | R3 |

**Fail closed on absence.** A tier field that is **missing or unparseable** is
treated as **R2**. A declared `R2` or `R3` keeps its own tier and its own
controls; a declared `R0` or `R1` is taken as declared. This clause exists to
catch an absent or corrupt value. It never relabels a declared tier and never
lowers one — in particular, a `R3` job keeps the R3 controls above.

Raise a tier when the prompt, files, trust boundary or expected output demands
it. Never lower a tier to meet a budget. A semantic **risk-floor raise is a
raise**: the coordinator applies it as `max(derived, riskFloorDelta)`, it changes
the required controls, and the attempt always escalates per
[verification.md](verification.md). The signal supplies the delta; it never writes
the tier.

## Minimum controls by concern

Profile safety behavior by observed control, never product reputation.

- **Approval.** Distinguish enforceable per-operation approval, scoped
  pre-approval, unconditional auto-approval, and unknown behavior. Unknown is not
  permissive.
- **Tool gating.** Record whether read, write, shell, network and external MCP
  access can be allowed or denied independently.
- **Write boundary.** Record the enforced writable roots. A cwd argument alone is
  not a sandbox.
- **Isolation.** State whether the boundary is OS-enforced, containerized,
  worktree-only, prompt-only, or absent.
- **Timeout.** A coordinator-owned process timeout is required for CLI jobs even
  when a native budget exists. Internal timeouts are accounting-only unless the
  current harness proves cancellation.
- **Bypass controls.** Identify the live runtime's bypass options only to keep
  them disabled. Never add one to a default command, and never enable one for a
  job. There is no approval that makes a bypass flag the right answer: a job that
  needs more privilege gets a scoped permission with explicit approval, a stronger
  external boundary, or `blocked` — never a disabled control switched back on.

An auto-approved or all-or-nothing write path is **constrained** for any shared
tree. It may handle read/report work; writing requires isolated R2 treatment.
Destructive or external work still requires explicit approval and the R3 gate.

## Approval and authority

- Confirm every job's cwd, allowed files, writable roots and expected side
  effects before dispatch.
- Use least-privilege permission and tool controls verified on the live runtime,
  with every permission-bypass mode off by default.
- Record existing user authorization and its exact scope in `authority`. Request
  approval only for an action outside that scope; prior authorization stays valid
  without repeating `--yes`.
- A reference records a decision; it cannot grant authority by itself. Never
  infer permission from an arbitrary non-empty authority string.
- **Egress is an external side effect.** Sending a prompt, repository context,
  normalized error text or artifact names to a third-party provider is R3 work.
  It needs its own authorized scope, and the decision plane may never authorize
  its own egress by classifying its own call as harmless. With no recorded egress
  authorization, the plane is disabled for that run and deterministic policy
  proceeds.
- A retry does not expand authority. Scope changes require a fresh decision.
- Treat inherently auto-approved headless modes as constrained: read/report work
  or R2-isolated writes, never shared-tree destructive work.

## Isolation boundaries

- Give every CLI process an external timeout.
- A worktree prevents edit collisions between agents. It does **not** isolate
  processes, the network, or the filesystem, and it is not an OS sandbox.
- Parallel writers use separate worktrees and disjoint ownership.
- Failed output is preserved for diagnosis, never hidden or relabeled.
- Keep destructive and credentialed external actions off prompt-only isolation.
- Onboarding installs are visible and reversible; profile overwrites are
  snapshotted first; credentials are entered only by the user.

## Secret handling

- Never write secrets, tokens, credentials, private keys, dotenv values, or
  unrelated private data into prompts, commands, logs, capture, decision traces,
  issues, PRs, plans or reports.
- Redact before persistence, not at read time.
- Refuse a plan that would place secrets in a prompt or in capture.
- A diagnosis bundle excludes private invocation files and any surface that
  carries argv or environment values.

## Presentation parity

The parity rule — which surfaces are covered, the per-tier clauses that must
survive a summary, and the correction procedure — is owned by
[verification.md](verification.md). This file owns the control values those
surfaces must not weaken. A summary is never the authority.

## The safety gate

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
block it. Do not infer safety from a runtime brand or a prior successful run.

## What no automated signal may decide

This list binds the decision plane, the micro-arbiter, the graph optimizer, and
any future scoring mechanism. None of them may:

- grant, widen, or infer a permission or approval;
- assign or lower a risk tier, or override any R0–R3 control. A signal may raise
  a floor; the coordinator applies a risk-floor raise as
  `max(derived, riskFloorDelta)` and the attempt escalates, but the signal never
  writes the tier itself;
- authorize its own egress, or treat a self-issued classification as a control;
- decide that a destructive or external action is authorized;
- emit, select or rewrite a dispatch command;
- mutate shared state outside a job's owned paths;
- relax a hard stop in [failure-modes.md](failure-modes.md), including a
  permission, sandbox or authentication stop;
- weaken a **review independence** requirement, including the unconditional
  requirement that review, audit, security and arbiter work be performed
  independently of the producer. When no independent route exists the verdict is
  labeled `not-independent`, and the job is `blocked` unless a fresh,
  independently configured context substitutes for it. Recording the limitation is
  required and is never sufficient on its own;
- replace the C3 arbiter, or accept work the escalation matrix in
  [verification.md](verification.md) sends to it;
- issue a final security verdict.

These are structural exclusions, not tier outcomes. They hold even when a job's
derived tier reads R0 or R1. Signalling mechanisms supply evidence; the
coordinator, this policy, and the C3 judgment route decide.
