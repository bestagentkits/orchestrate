# OpenCode Adapter

> **Status: unverified — not a support claim, not in inventory.**
> As of 2026-09-17 no live probe has been recorded for this runtime in this
> repository. This is a fenced stub, not a capability map. It asserts nothing
> about the runtime and is selectable only after a live probe records an
> `available` profile per [runtime-profile.md](../references/runtime-profile.md).

## What this stub is

The orchestration scope names OpenCode as a runtime to support. This repository
contains no probe evidence for it. Nothing about its run surface, structured
event output, session model, or control surface is known here.

## Probe focus

A future probe must establish, from the installed version's own help:

- the non-interactive run entry surface, and whether a headless server mode
  exists separately;
- working-directory control;
- model discovery and selection;
- approval and tool gating controls;
- structured event output, and whether events are streamed or emitted as a final
  document;
- session identity, listing, continuation and fork behavior;
- any native budget or timeout control.

## Verification steps

1. Resolve the executable and record its absolute path and symlink target.
2. Bound a version and help probe with an external timeout.
3. Establish identity before trusting any capability claim.
4. Run the full conformance checks in
   [runtime-adapter-contract.md](../references/runtime-adapter-contract.md).
5. Record the profile with `role: runtime`, writing every unproven control
   `unverified`. A headless server mode is a separate surface with its own
   controls; probe it separately if it will be used.
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
