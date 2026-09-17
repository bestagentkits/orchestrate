# Codex CLI Adapter

> **Status: unverified — not a support claim, not in inventory.**
> As of 2026-09-17 no live probe has been recorded for this runtime in this
> repository. This is a fenced stub, not a capability map. It asserts nothing
> about the runtime and is selectable only after a live probe records an
> `available` profile per [runtime-profile.md](../references/runtime-profile.md).

## What this stub is

Codex appears in this repository today only as an execution-mechanics example in
[dispatch-hardening.md](../references/dispatch-hardening.md): detached-process
survival, host-invisible capture, poller hygiene. Those notes describe how to run
a long headless job on a wrapped host; they are **not** a probe of the Codex
runtime, and they are not a capability claim.

## Probe focus

A future probe must establish, from the installed version's own help:

- the non-interactive execution entry surface;
- working-directory control and whether a native worktree flag applies in
  headless mode;
- model discovery and selection;
- sandbox and approval controls, and whether the sandbox is enforced on this OS;
- tool gating;
- structured event or JSON output, and the explicit output-message option if one
  exists;
- session identity, resume and fork behavior;
- any native turn or time budget.

## Verification steps

1. Resolve the executable and record its absolute path and symlink target.
2. Bound a version and help probe with an external timeout.
3. Verify each capability from live help; consult official documentation only
   where help is ambiguous, and record what was checked.
4. Run the full conformance checks in
   [runtime-adapter-contract.md](../references/runtime-adapter-contract.md).
5. Record the profile with `role: runtime`, writing every unproven control
   `unverified`.
6. Run a bounded smoke test and confirm it settles with the runtime's own
   completion evidence, not merely a zero exit status.

## Graduation

When a probe and conformance run are recorded in `runtimes.json`, replace this
stub with a full note using the template in [README.md](README.md). Until then,
this file carries no capability claim and grants no route.

## Independence caveat

No independence property can be claimed for an unprobed runtime. Independence is
verified from live inventory evidence and compared by resolved model family, per
[verification.md](../references/verification.md).
