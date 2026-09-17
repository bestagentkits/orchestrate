---
phase: 1
title: "Core contracts"
status: pending
priority: P0
effort: 8h
dependencies: []
---

# Phase 1: Core contracts

## Goal

Make the bottom of the orchestration stack uniform: one adapter interface every
runtime implements, one normalized profile schema that live probing fills in, and
one normalized event protocol that observation, retry, watchdog and arbiter all
read instead of runtime-specific output. Establish the destination table for
every heading in the files phase 7 deletes, so no rule is lost in the flip.

## Files to Create / Modify

- Create: `references/runtime-adapter-contract.md`
- Create: `references/runtime-profile.md`
- Create: `references/event-protocol.md`
- Modify: `plan.md` (destination table status only)

## Tasks & Steps

1. Write the **destination table** first. Every heading in the three files phase 7
   deletes or merges gets an owning file. Verified inventory of headings:

   | Source heading | Destination |
   | --- | --- |
   | `harness-profiles.md` §Profile Schema | `runtime-profile.md` |
   | `harness-profiles.md` §Confidence States | `runtime-profile.md` |
   | `harness-profiles.md` §Evidence Collection | `runtime-profile.md` |
   | `harness-profiles.md` §Safety Evidence (tool gating, write boundary, bypass controls) | `safety-policy.md` (phase 2) |
   | `harness-profiles.md` §Capture Quality | `runtime-profile.md` |
   | `harness-profiles.md` §Budget and Reliability Evidence | `runtime-profile.md` |
   | `harness-profiles.md` §Harness Enablement | `runtime-profile.md` |
   | `harness-profiles.md` §Selection Handoff | `routing-policy.md` (phase 2) |
   | `runtime-matrix.md` §Candidate Set (incl. classifier candidate rule) | `runtime-profile.md` |
   | `runtime-matrix.md` §Optional CLI Discovery (probe targets incl. `pi`, `omp`, `agy`, `grok`) | `runtimes/README.md` (phase 6) |
   | `runtime-matrix.md` §Live Matrix Record (`runtimes.json`) | `runtime-profile.md` |
   | `runtime-matrix.md` §CLI Probe Sequence | `runtime-profile.md` |
   | `runtime-matrix.md` §Internal Probe Sequence | `runtime-adapter-contract.md` |
   | `runtime-matrix.md` §Command Construction | `runtime-adapter-contract.md` |
   | `runtime-matrix.md` §OS Revalidation | `runtime-adapter-contract.md` |
   | `runtime-matrix.md` §Support States | `runtime-profile.md` |
   | `runtime-matrix.md` §Timeout Contract | `runtime-profile.md` |
   | `runtime-matrix.md` §Safety Gate | `safety-policy.md` (phase 2) |
   | `runtime-matrix.md` §Drift and Failure Handling | `runtime-profile.md` |
   | `runtime-matrix.md` §Verification Rule | `runtime-adapter-contract.md` |
   | `runtime-matrix.md` `ak orchestrate probe` accelerator surface | `runtime-profile.md` |
   | `model-routing.md` §Internal Branch (agent matching, internal model-pin handling) | `internal-routing.md` (phase 2) |
   | `model-routing.md` resolved-model-family independence rule | `verification.md` arbiter contract (phase 4) |

2. Write `runtime-adapter-contract.md`: the interface
   (`discover`, `probe`, `profile`, `start`, `observe`, `steer`, `cancel`,
   `resume`, `fork`, `capture`), required versus optional methods, what each
   returns, the conformance checks, the internal probe sequence, command
   construction rules, OS revalidation, and the verification rule that a
   capability exists only when live evidence proves it. State that the contract
   is implemented by CLI adapters and by the in-session adapter alike.
3. Write `runtime-profile.md`: candidate set, the **classifier candidate rule**,
   probe sequence, the `runtimes.json` record shape, support states, timeout
   contract, drift handling, capture quality, budget/reliability evidence,
   harness enablement, and the `ak orchestrate probe` accelerator. Reserve the
   auto-profiler heading for phase 4.
4. State the **classifier candidate rule** normatively, because the decision
   plane is otherwise inactive on the documented default run: when the plane is
   enabled, the classifier candidate joins discovery as an explicit
   `optional-discovery` candidate with a bounded probe budget and a required
   structured-output conformance check. It is not a job. Its record carries
   `role: classifier`. Every decision trace records `none | <candidate-id>` plus
   the reason, so "no classifier" is distinguishable from "decided
   deterministically".
5. Write `event-protocol.md`: the normalized event envelope, event kinds
   (lifecycle, tool, error, artifact, usage, permission, progress claim),
   required fields, sequence/cursor semantics, the common agent state machine
   (`queued → running → settled`, plus `blocked`, `interrupted`, `unsettled`),
   liveness/activity/progress separation, truncation markers, and redaction.
   State that an unsupported provider event is never fabricated into tool
   success, and that any provider-authored imperative text is carried as
   delimited untrusted data with a provenance label (phase 3 consumes this).
6. Cross-link the three files and keep route selection out of all three,
   pointing at `routing-policy.md` and `decision-plane.md` by name.

## Verification

```bash
S=plugins/orchestrate/skills/orchestrate/references
grep -c '^' $S/runtime-adapter-contract.md $S/runtime-profile.md $S/event-protocol.md
grep -n 'Internal Probe Sequence\|Command Construction\|OS Revalidation\|Verification Rule' $S/runtime-adapter-contract.md
grep -n 'role: classifier\|optional-discovery' $S/runtime-profile.md
grep -n 'untrusted\|provenance' $S/event-protocol.md
# every heading in the two absorbed files has a destination row above
grep -n '^## ' $S/harness-profiles.md $S/runtime-matrix.md
```

- [x] Every source heading appears in the destination table with an owner.
- [x] The classifier candidate rule is stated, with a recorded `none | id` trace field.
- [x] Each contract is the single authority for its own schema; no overlap.
- [x] Capability claims are phrased as evidence-dependent.
- [x] The internal probe sequence and command construction have a home in `runtime-adapter-contract.md`.
