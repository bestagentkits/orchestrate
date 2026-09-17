# Runtime Profile

This file is the single authority for **live runtime evidence**: the candidate
set, the probe sequence, the `runtimes.json` record schema, support states, the
timeout contract, drift handling, and the auto-profiler procedure.

It is not a runtime roster, not a command catalog, and not a model list. Runtime
availability, model catalogs, aliases, permission controls and CLI flags are
volatile; never treat a model name, provider catalog or previous run as current
evidence.

- [runtime-adapter-contract.md](runtime-adapter-contract.md) owns the adapter
  interface, command construction and conformance.
- [routing-policy.md](routing-policy.md) owns route selection.
- [safety-policy.md](safety-policy.md) owns the safety gate and risk tiers.
- [event-protocol.md](event-protocol.md) owns normalized observation events.
- [runtimes/README.md](../runtimes/README.md) owns the per-runtime probe focus.

## Candidate Set

Start with only candidates relevant to the requested run:

- explicit `runtime:` values in the job spec;
- entries in each job's `fallback_runtime` chain;
- `runtime: internal` when the current harness exposes an agent-dispatch
  interface;
- a runtime the user explicitly asks the coordinator to consider;
- the decision-plane classifier candidate, when the plane is enabled (below).

When the user asks to use other installed runtimes if available, discover
optional candidates through the active dispatcher's runtime registry and
explicit executable configuration. Use the probe focus in the matching
`runtimes/` note for requested candidates that have no dispatcher entry. A kit
emitter or registry entry is a discovery hint, not proof of a working headless
runner.

Record whether each candidate is required by a job pin or is optional discovery.
Skip unavailable optional candidates with a reason; do not block a qualified
route because another optional runtime is missing. Never substitute for a pinned
runtime without the user's authorization.

Treat each value as a candidate identifier, not proof of support. Do not add a
runtime because it appeared in an old report or this repository's history. Do
not install, update, authenticate or alter configuration during discovery.

The job-spec schema and the active dispatch implementation own accepted
identifiers. If they disagree, stop and report the contract mismatch instead of
inventing a mapping.

### Classifier candidate

The decision plane is a consumer of runtimes, not a job. It needs its own
candidate or it is inert on a run whose jobs are all `runtime: internal`:

- When the plane is enabled, the classifier joins discovery as an explicit
  `optional-discovery` candidate with a bounded probe budget.
- It must satisfy a **structured-output conformance check**: the probe proves
  the runtime can return a schema-constrained result. A runtime that cannot is
  not eligible, regardless of capability.
- Its record carries `role: classifier` and is **enabled only while `state` is
  `available` with verified tool gating** that permits withholding every tool.
- The classifier is never counted as satisfying a job route, and its presence
  never raises any floor.
- Every decision trace records `none | <candidate-id>` plus the reason, so "the
  plane was disabled" is distinguishable from "the plane decided
  deterministically".

Enabling the plane does not make it load-bearing: see
[decision-plane.md](decision-plane.md) for the degradation rules.

## Profile Schema

Record these fields for every candidate named by the job spec, fallback chain,
classifier role, or current internal harness:

| Evidence | What to record |
| --- | --- |
| Identity | Runtime id, `role` (`runtime` or `classifier`), executable or internal mechanism, live version when exposed |
| Availability | Resolved path or live agent-list evidence, plus one support state (below) |
| Authentication | Non-interactive readiness only; never credentials, tokens or raw environment values |
| Headless entry | Verified command shape or internal dispatch mechanism |
| Working directory | Whether cwd can be pinned and how it is enforced |
| Model or agent discovery | Live listing mechanism and resolved choices; no copied catalog |
| Provider identity | Resolved provider and model family when exposed; different harnesses may share a model |
| Extension and nested-agent controls | Enabled extensions and child-agent tools, enforcement and limits; include nested work in concurrency and budget accounting |
| Permissions | Approval modes, tool allow/deny controls, and whether headless mode auto-approves |
| Isolation | OS sandbox, container, worktree, prompt-only boundary, or none |
| Budgets | Native turn/tool/time controls plus coordinator-owned external timeout |
| Capture | Structured output, final-result capture, stderr, exit status, artifacts, usage data |
| Resume | Supported session or job-state behavior, if verified |
| Observation | Durable handle, incremental cursor, event fidelity, last real progress, gaps and truncation |
| Intervention | Native follow-up, interrupt, cancel confirmation, reconnect, and per-job model selection; verify each separately |
| Enablement | Instruction files and skill locations actually loaded for this run |
| Host limits | OS, shell, quoting, path or sandbox limitations that change the risk posture |
| Evidence source | Live help/probe and current official documentation consulted for ambiguous behavior |
| Classifier hint | Decision-plane probabilities only; never eligible for routing (see Auto-profiler) |

Use `null` or `unverified` for unknowns. Absence of evidence is never a positive
capability.

## Support States

States are evidence inputs. Risk-tier and capability-floor decisions belong to
[safety-policy.md](safety-policy.md) and [routing-policy.md](routing-policy.md).

| State | Required evidence | Allowed use |
| --- | --- | --- |
| `available` | Command, auth, required controls and capture verified live | Eligible for routing |
| `constrained` | Dispatch verified, but controls or capture have known limits | Eligible only when policy accepts those limits |
| `unverified` | Candidate exists, but required behavior was not proven | Advisory/non-load-bearing work only |
| `unavailable` | Missing, unauthenticated, incompatible, or failed probe | Do not dispatch |

**`unverified` means the deterministic probe did not prove the behavior.** It
never means "the classifier did not confirm it". A classifier outage cannot
demote an otherwise-proven runtime, and a classifier verdict cannot promote an
unproven one.

## Probe Sequence

Probe candidates with a bounded version and help check before trusting any
route. The probe never authenticates and never runs inference. An explicit
installation path handles an executable outside PATH, and a refresh discards
cached help evidence. A probe that exhausts its time budget is a probe-budget
failure, not a broken binary; raise the budget on a slow host. Probe Pi help
without extensions, because Pi otherwise loads every configured extension
package before printing help, so extension-provided flags are verified only at
dispatch.

For each CLI candidate:

1. Resolve the executable using the active dispatcher or explicit user
   configuration. If unresolved, inspect only the candidate's documented
   installation paths under the current user's home or package-manager bin
   directory. Record an outside-PATH executable's source and resolved symlink
   target; do not rewrite `PATH`, scan unrelated user directories, or silently
   switch binaries. Reuse an active dispatcher only when it exposes the controls
   the job needs; otherwise qualify a direct CLI route.
2. Run the runtime's non-mutating version command and live help.
3. From live help, verify the exact features the job needs: headless invocation,
   cwd handling, output capture, model selection, permissions, native budgets,
   and resume.
4. If live help advertises a model or capability listing command, run it and
   record only the choices relevant to this run.
5. Use a non-mutating authentication/status probe when available. A runtime that
   would open an interactive login is `unavailable` for headless dispatch until
   the operator completes setup outside the run.
6. When help is ambiguous, consult current official documentation and record the
   exact source checked. Do not rely on copied command snippets.
7. Build a dry command template with redacted placeholders and validate its
   arguments before dispatch. Do not execute a write merely to test syntax.

An unknown flag or model is a failed probe. Re-check live help and current
official docs, then rebuild the command. Never guess a replacement or carry
flags between runtimes.

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

Prefer a status-only, non-refreshing auth probe when advertised. Never use a
credential-printing command, a credential-output option, or read auth stores to
establish readiness. If no non-secret readiness probe exists, keep auth
unverified until an authorized bounded invocation proves it. Never start a
login, install, update or configuration migration as discovery. A candidate that
a job or the user requires and that discovery reports missing or unauthenticated
leaves discovery and enters its onboarding reference as a separate visible setup
step, after which it is probed again.

Record provider, resolved model, model family when evidenced, enabled
extensions, and nested-agent controls. Two runtimes can select the same model
family; different executable names do not prove independent review. Disable
unnecessary nested delegation using verified controls, or account for it within
the run's concurrency and budget before dispatch.

With the AgentKit CLI installed, `ak orchestrate probe --json` performs this
version and help discovery; `--runtime` narrows candidates, repeated
`--path <id>=<executable>` handles explicit installations outside PATH,
`--refresh` discards cached help evidence, and `--timeout` raises the probe
budget.

## Live Matrix Record

Write the inventory to `<run-dir>/runtimes.json`. Each candidate record contains
at least:

```json
{
  "id": "<candidate-id>",
  "role": "runtime|classifier",
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
  "structuredOutput": "supported|unsupported|unverified",
  "evidence": ["<probe-or-current-official-doc>"],
  "notes": []
}
```

The control fields (`state`, `approval`, `toolGating`, `isolation`,
`cwdControl`, `headless`, `capture`, `resume`, `structuredOutput`) are
**evidence-backed**: only deterministic probe and conformance results may set
them. A classifier's opinion of a control goes in the `classifier_hint` block
and never in these fields.

Never include tokens, cookies, credential values, raw environment variables, or
sensitive command arguments. Empty arrays and `null` are preferable to guessed
capability.

## Capture Quality

Prefer evidence in this order when otherwise-qualified routes remain:

1. structured event stream plus final result, exit status and artifacts;
2. bounded stdout/stderr plus explicit exit status;
3. final text only with harness-reported status;
4. unstructured output without trustworthy completion state.

Lower capture quality does not automatically disqualify R0 advisory work, but it
cannot support a load-bearing check whose result cannot be independently
verified. Record truncation and which capture region is retained; never claim
the tail survives when the supervisor keeps only a bounded prefix.

Observation is an admission requirement tied to the job. A short advisory job can
use final-result capture. A long-running writer requires a durable handle,
bounded capture, identifiable completion and confirmed cancellation before
replacement. Reject only the missing capabilities that job requires.

Distinguish three signals: a verified live process is **liveness**; output and
tool events are **activity**; accepted artifacts and checkpoints are
**progress**. Silence is not failure and token volume is not progress.
Unsupported observations remain unknown. Never require hidden reasoning or
fabricate a completion percentage.

## Budget and Reliability Evidence

- Treat native turn, tool-call or wall-time controls as defense in depth.
- Enforce an external process timeout for every CLI job.
- Record observed duration, status, usage and cost only when the harness reports
  them reliably.
- Use cross-run metrics as advisory evidence after enough comparable samples;
  never let metrics silently rewrite routing policy.
- A beta, experimental or partially verified path remains non-load-bearing until
  live evidence proves the controls the job requires.

## Harness Enablement

Before dispatch, verify the instruction and skill surfaces the live runtime
actually loads:

1. inspect current runtime documentation or live diagnostics for supported rules
   and skill locations;
2. confirm the relevant project/global instruction file and requested skill are
   present;
3. name the concrete skill path and expected output in the job prompt;
4. offer any needed AgentKit install or refresh as a visible setup step;
5. never install, update, authenticate or mutate user configuration silently.

Do not maintain a copied table of runtime-specific paths. The installed runtime
and AgentKit's current projection are execution-time evidence.

## Auto-profiler

The auto-profiler turns deterministic probe evidence into a normalized profile,
with the decision plane permitted to **annotate** that evidence and nothing more.

Procedure:

1. The deterministic probe collects version, help, model list, readiness and a
   bounded smoke test, per the probe sequence above.
2. Conformance checks from
   [runtime-adapter-contract.md](runtime-adapter-contract.md) set the
   evidence-backed control fields.
3. The decision plane, when an eligible `role: classifier` candidate exists,
   answers the capability questions as probabilities over that evidence:
   `supports_headless`, `supports_resume`, `supports_stream_events`,
   `supports_model_selection`, `supports_tool_gating`, `supports_sandbox`,
   `supports_fork`, `supports_native_timeout`.
4. Those probabilities are written to a separate **`classifier_hint`** block.

Binding rules, because this is where a probabilistic signal could quietly become
a capability claim:

- **No probability may set an evidence-backed field.** A hint cannot change
  `state`, `approval`, `toolGating`, `isolation`, `cwdControl`, `headless`,
  `capture`, `resume` or `structuredOutput`.
- **A hint is ineligible for routing.** It may order candidates only after the
  deterministic hard filter has already decided eligibility.
- **A control claim that the probe could not prove stays `unverified`** no matter
  how confident the classifier is. An advertised sandbox flag whose OS
  enforcement is unverified is `unverified`, not `os-sandbox`.
- **On classifier absence, timeout or malformed output the profile is written
  from deterministic probe and conformance results alone.** A classifier outage
  degrades the plane; it never degrades, blocks or re-labels a run.
- **Commands come from the adapter and live verification, never from the model.**
  The profiler interprets evidence; it does not author an invocation.

## Drift and Failure Handling

- Version, help, authentication or model-list changes invalidate the affected
  cached profile for this run.
- A command-line parse failure returns to the probe step once; it is not a reason
  to try guessed flags repeatedly.
- A runtime crash, timeout or permission prompt is a job failure. Preserve
  evidence and apply the declared fallback through
  [routing-policy.md](routing-policy.md).
- Update evergreen docs only when the evidence procedure or a safety invariant
  changes. Do not paste a newly observed provider catalog back into these
  references.

## Timeout Contract

- Bound every CLI job with a coordinator-owned process timeout.
- Treat native wall-time, turn or tool-call limits as defense in depth.
- On timeout, stop the process using the host's verified mechanism, preserve
  bounded partial output, mark the job failed, and block dependents.
- Internal timeouts are accounting-only unless the current harness proves a
  cancellation mechanism; scope those prompts tightly.
