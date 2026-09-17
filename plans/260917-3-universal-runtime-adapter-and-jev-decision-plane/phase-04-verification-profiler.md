---
phase: 4
title: "Verification and profiler"
status: pending
priority: P2
effort: 6h
dependencies: [3]
---

# Phase 4: Verification and profiler

## Goal

Add the two cost/latency reducers, with the safety holes the red-team found
closed: a micro-arbiter gated on a **recorded risk tier** and a **calibration
sample**, and a runtime auto-profiler that annotates probe evidence instead of
deciding capability.

## Files to Create / Modify

- Create: `references/verification.md`
- Modify: `references/runtime-profile.md` (auto-profiler section)
- Modify: `references/decision-plane.md` (micro-arbiter + profiler-classification + graph-relation task schemas)
- Modify: `references/metrics-and-self-improvement.md` (calibration + arbiter-gate telemetry)
- Modify: `references/job-spec.md` (threshold/calibration fields, accepted-without-C3 count)

## Tasks & Steps

1. Write `verification.md`: the three verification layers in order —
   deterministic checks (artifact exists, declared check commands pass, hashes
   match, outputs non-contradictory), the System-1 micro-arbiter (`artifact
   matches expected_output`, `claims supported by evidence`, `materially
   unresolved` as probabilities), and the C3 arbiter contract. Carry all nine
   existing arbiter-checklist questions into the file, and state explicitly
   **who answers each one when C3 is skipped** (the coordinator's deterministic
   fields plus the recorded micro-arbiter signals), and which questions force
   C3 escalation regardless.
2. Define the **escalation matrix** as a risk-tier test, not an effect test.
   Accept without C3 only when **all** hold:
   - the **recorded** risk tier is `R0` or `R1` (R2 and R3 always escalate, which
     closes the parallel/untrusted/hard-to-revert hole);
   - `importance: normal`;
   - every deterministic check passed;
   - a calibration record exists meeting the minimum sample below;
   - all micro-arbiter signals clear the recorded threshold;
   - the classifier returned well-formed output with no low-confidence flag.

   Always escalate to C3 for security, architecture, high-impact
   implementation, external/destructive work, parallel or untrusted-prompt
   writes, contradictory evidence, and any malformed or low-confidence output.
   The micro-arbiter is a gatekeeper for the arbiter, never a replacement.

   **Tier derivation and fail-closed assignment.** The tier is not free text and
   is not chosen by the agent that benefits from the accept. It is a
   deterministic derivation from declared job attributes, evaluated **before
   execution** and recorded on the attempt:

   | Declared attribute | Derived tier |
   | --- | --- |
   | read/report only, no mutating effect | R0 |
   | reversible edits inside owned paths | R1 |
   | untrusted prompt or input, parallel writer, high-impact or hard-to-revert change, or a candidate whose controls are unverified | R2 |
   | deploy, release, delete, credentialed or other external side effect | R3 |

   **Fail closed on absence:** a tier field that is missing, unparseable, or not
   in `{R0, R1}` is treated as **R2**, so a mis-tiered or absent tier escalates
   rather than bypasses. This is the one clause in the whole matrix a grep can
   meaningfully assert, so assert it explicitly.

3. Define **structural exclusions independent of tier.** These are hard
   invariants, not tier outcomes: the micro-arbiter may never accept a job that
   sets `approval`, emits a dispatch command, or mutates shared state outside its
   owned paths. Those always escalate, even when the tier reads R0/R1. State this
   in `SKILL.md`'s Limitations section as a hard invariant.

4. Define **calibration** concretely, because the previous draft was circular
   (the threshold could only come from telemetry the gate produced) and
   dead-on-arrival (no history means nothing ever clears):
   - **First-run behaviour is unambiguous:** with no calibration record, the
     micro-arbiter **observes and logs only**; C3 stays mandatory for every
     job. This is a documented degraded mode, not a failure.
   - The calibration ground truth must be **C3-audited outcomes**, never
     micro-arbiter-accepted runs — otherwise the floor is computed over runs the
     gate already approved and the feedback loop has no reference.
   - Calibration is **per classifier candidate**, never pooled across runtimes or
     models, and the record names the candidate id it was measured on.
   - A calibration record exists once **N comparable C3-audited outcomes** show
     measured agreement between the micro-arbiter verdict and the C3 verdict.
     Name N as an explicit minimum and record the sample count with the threshold.
   - The record carries an **expiry/staleness trigger**. A threshold that never
     re-validates drifts into permission, so a stale record escalates.
   - Record the threshold's **field name, value, units, classifier id, sample
     count and expiry** in `job-spec.md`-owned fields, not in prose.
   - Fail closed: a missing, malformed, pooled-across-classifiers or stale
     calibration record escalates.
5. Add the **auto-profiler** section to `runtime-profile.md`. This is the
   highest-risk item in the phase; the rule must be explicit that the classifier
   only **annotates**:
   - **Evidence-backed fields** (`state`, `approval`, `toolGating`,
     `isolation`, `cwdControl`, `headless`, `capture`, `resume`) are settable
     only by deterministic probe and conformance results.
   - A separate **`classifier_hint`** block carries the probabilities
     (`supports_headless`, `supports_resume`, `supports_stream_events`,
     `supports_model_selection`, `supports_tool_gating`, `supports_sandbox`,
     `supports_fork`, `supports_native_timeout`). It is explicitly ineligible
     for routing eligibility.
   - No probability may set an evidence-backed field. A control claim that
     `runtime-matrix.md` today calls unenforced stays `unverified` regardless of
     classifier confidence.
   - **On classifier absence the profile is written from deterministic probe and
     conformance results alone.** `unverified` means "the probe did not prove
     it", never "the model did not confirm it" — so a classifier outage degrades
     the plane, never the run.
   - Commands come from the adapter and live verification, never from the model.
6. Extend `metrics-and-self-improvement.md` with calibration and arbiter-gate
   telemetry: how often the micro-arbiter accepted, how often C3 escalated,
   whether an accepted job later failed, and the agreement rate between the two
   verdicts. This is the input to raising or lowering the threshold, and it is
   also the source of the `accepted-without-C3` count the report must carry.
7. Add the boundary assertion to this phase's exit: `decision-plane.md` must not
   contain an accept/escalation table or a route field — the escalation matrix
   lives only in `verification.md`.

## Verification

```bash
S=plugins/orchestrate/skills/orchestrate/references
grep -n 'R0\|R1\|R2\|R3' $S/verification.md | head -10
grep -n 'R2 and R3 always escalate\|recorded risk tier' $S/verification.md
grep -n 'observe and log only\|minimum\|fail closed\|calibration record' $S/verification.md
grep -n 'classifier_hint\|may not set\|unverified means' $S/runtime-profile.md
grep -n 'accepted-without-C3\|agreement rate' $S/metrics-and-self-improvement.md
# nine checklist questions preserved
grep -c '^-' $S/arbiter-checklist.md   # baseline before deletion (phase 7 removes the file)
# boundary: escalation table must NOT be in decision-plane.md
grep -c 'escalation matrix' $S/decision-plane.md
```

- [x] The accept predicate keys on a **recorded risk tier**, and R2/R3 always escalate.
- [x] First-run behaviour is "C3 mandatory, micro-arbiter logs only".
- [x] Threshold field, units, owner and minimum sample are all named.
- [x] `classifier_hint` is separate and cannot set an evidence-backed field.
- [x] All nine checklist questions survive, with a named answering party on the no-C3 path.
- [x] The escalation matrix appears only in `verification.md`.
