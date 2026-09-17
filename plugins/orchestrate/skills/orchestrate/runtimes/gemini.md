# Gemini CLI Adapter

> **Status: unverified — not a support claim, not in inventory.**
> As of 2026-09-17 no live probe has been recorded for this runtime in this
> repository. This is a fenced stub, not a capability map. It asserts nothing
> about the runtime and is selectable only after a live probe records an
> `available` profile per [runtime-profile.md](../references/runtime-profile.md).

## What this stub is

The orchestration scope names the Gemini CLI as a runtime to support. This
repository contains no probe evidence for it. Nothing about its headless entry,
control surface, capture or resume behavior is known here.

## Probe focus

A future probe must establish, from the installed version's own help:

- the headless entry surface and whether it requires an explicit opt-in flag;
- working-directory control;
- model discovery and selection;
- approval and sandbox controls, and whether either is enforceable headlessly;
- tool gating;
- structured or streamed JSON output, and where the final result lands;
- session identity and continuation behavior;
- any native budget or timeout control.

## Verification steps

1. Resolve the executable and record its absolute path and symlink target.
2. Bound a version and help probe with an external timeout.
3. Establish identity before trusting any capability claim.
4. Run the full conformance checks in
   [runtime-adapter-contract.md](../references/runtime-adapter-contract.md).
5. Record the profile with `role: runtime`, writing every unproven control
   `unverified`.
6. Run a bounded smoke test and confirm it settles with the runtime's own
   completion evidence.

## Graduation

When a probe and conformance run are recorded in `runtimes.json`, replace this
stub with a full note using the template in [README.md](README.md). Until then,
this file carries no capability claim and grants no route.

## Independence caveat

No independence property can be claimed for an unprobed runtime. Independence is
verified from live inventory evidence and compared by resolved model family, per
[verification.md](../references/verification.md).
