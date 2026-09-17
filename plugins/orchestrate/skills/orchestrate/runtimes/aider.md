# Aider Adapter

> **Status: unverified — not a support claim, not in inventory.**
> As of 2026-09-17 no live probe has been recorded for this runtime in this
> repository. This is a fenced stub, not a capability map. It asserts nothing
> about the runtime and is selectable only after a live probe records an
> `available` profile per [runtime-profile.md](../references/runtime-profile.md).

## What this stub is

The orchestration scope names Aider as a runtime to support. This repository
contains no probe evidence for it. Nothing about its scripting mode, output
capture, session model, or control surface is known here.

Aider is mentioned in the accepted scope as a runtime with a less sophisticated
harness than the others. That expectation is **not** evidence, and this stub
asserts no capability: a "weaker" runtime still needs a real probe before it
carries any job.

## Probe focus

A future probe must establish, from the installed version's own help:

- the scripting or non-interactive entry surface, and how a prompt is supplied;
- working-directory control and file-scoping options;
- model discovery and selection;
- whether any approval, tool-gating or sandbox control exists, since a runtime
  without enforceable controls is capped at advisory or isolated work;
- output capture, and whether an explicit output file exists;
- whether any session or resume concept exists at all;
- any native budget or timeout control.

## Verification steps

1. Resolve the executable and record its absolute path and symlink target.
2. Bound a version and help probe with an external timeout.
3. Establish identity before trusting any capability claim.
4. Run the full conformance checks in
   [runtime-adapter-contract.md](../references/runtime-adapter-contract.md). A
   missing required control is a conformance failure, not a limitation to work
   around.
5. Record the profile with `role: runtime`, writing every unproven control
   `unverified`. Where no control exists, record that plainly rather than writing
   a permissive default.
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
