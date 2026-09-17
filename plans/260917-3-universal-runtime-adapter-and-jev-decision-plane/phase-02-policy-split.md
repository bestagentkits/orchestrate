---
phase: 2
title: "Policy split"
status: pending
priority: P0
effort: 6h
dependencies: [1]
---

# Phase 2: Policy split

## Goal

Separate the two responsibilities currently fused in `model-routing.md`:
deterministic hard policy (safety, eligibility, floors, ranking, fallbacks, pins)
and semantic classification, which moves to the decision plane in phase 3.
Extract the safety boundaries buried in `SKILL.md`, `runtime-matrix.md` and
`harness-profiles.md` into one `safety-policy.md`. Both new files become the
authority immediately, so every inbound link must be repointed in this phase
rather than deferred.

## Files to Create / Modify

- Create: `references/safety-policy.md`
- Create: `references/routing-policy.md`
- Modify: `references/job-spec.md` (link `model-routing.md` → `routing-policy.md`)
- Modify: `references/internal-routing.md` (absorbs §Internal Branch; relink)
- Modify: `references/dispatch-hardening.md` (relink to `routing-policy.md` / `runtime-profile.md`)
- Modify: `references/runtime-matrix.md`, `references/harness-profiles.md` (relink to the new owners)
- Modify: `references/pi-sessions.md` (relink; it moves to `runtimes/pi.md` in phase 6)
- Modify: `SKILL.md` (link targets only — the Authority Map rewrite stays in phase 7)

## Tasks & Steps

1. Write `safety-policy.md`: R0–R3 tiers and their minimum controls, including
   the absorbed `harness-profiles.md` §Safety Evidence rules (approval
   distinguishability, tool gating, enforced write boundary, isolation
   strength, timeout ownership, bypass discipline) and
   `runtime-matrix.md` §Safety Gate. Add permission/approval rules, the
   authority model (existing authorization versus requesting new approval), the
   worktree-is-not-a-sandbox rule, the constrained-headless rule, destructive /
   external blocking conditions, secret handling, and an explicit
   **what the decision plane may never authorize** clause.
2. Write `routing-policy.md` from the deterministic half of `model-routing.md`:
   inputs, live inventory gate, capability tiers C1–C3, task defaults as
   **floors**, the deterministic eligibility filter, selection procedure,
   fallbacks, pins, reasoning controls, worked example, operator checklist, and
   the blocked-not-downgraded rule.
3. Move `model-routing.md` §Internal Branch into `internal-routing.md`, which
   already owns internal dispatch mechanics. It must absorb explicit-agent
   validation, description-based matching, general-purpose fallback, and
   internal model-pin handling.
4. State the layering normatively in both new files:
   `safety-policy.md` decides what may run; `routing-policy.md` decides
   eligibility and rank; the decision plane only supplies scored evidence to
   that rank.
5. Add the **floor-raising rule** to `routing-policy.md`: a semantic signal may
   only *raise* a capability or risk floor, never lower one. Add
   `review_independence_required` explicitly as non-lowering. Add the same
   independence requirement to the never-list in `safety-policy.md`.
6. Repoint every inbound link in this phase. Verified file set (grep, not
   assumption — `observation.md` does **not** link `model-routing.md`):

   ```bash
   S=plugins/orchestrate/skills/orchestrate
   grep -rln 'model-routing\.md' $S --include='*.md'
   # → internal-routing.md, runtime-matrix.md, harness-profiles.md,
   #   pi-sessions.md, dispatch-hardening.md, job-spec.md, SKILL.md
   grep -rln 'runtime-matrix\.md\|harness-profiles\.md' $S --include='*.md'
   ```

   `SKILL.md` gets link-target-only edits here (its prose and Authority Map are
   rewritten in phase 7). Exit condition: no inbound reference to
   `model-routing.md` / `runtime-matrix.md` / `harness-profiles.md` remains
   except inside the two files being absorbed, which phase 7 deletes.
7. Fix the pre-existing stale reference while editing:
   `dispatch-hardening.md:71` cites a "Dispatch Result Verification" section
   that does not exist in `runtime-matrix.md`. Point it at `verification.md`.

## Verification

```bash
S=plugins/orchestrate/skills/orchestrate
grep -rn 'model-routing\.md' $S --include='*.md' | grep -v 'SKILL.md' | grep -v 'runtime-matrix.md' | grep -v 'harness-profiles.md' || echo "relinks clean"
grep -n 'C1\|C3' $S/references/routing-policy.md | head -5
grep -n 'R0\|R3' $S/references/safety-policy.md | head -5
grep -n 'may only raise\|never lower' $S/references/routing-policy.md
grep -n 'Internal Branch\|internal model' $S/references/internal-routing.md
grep -c 'Dispatch Result Verification' $S/references/dispatch-hardening.md
```

- [x] Tier **definitions** live only in `routing-policy.md` (capability) and
      `safety-policy.md` (risk). Floors may be *referenced* from routing-policy,
      which is why the earlier "risk tiers only in one file" wording was wrong.
- [x] `routing-policy.md` contains no task→runtime or task→model route.
- [x] The floor-raising rule and the independence non-lowering clause are present.
- [x] `safety-policy.md` names the decision plane explicitly as a non-authority.
- [x] Phase 2's exit grep passes with no deferred relink.
