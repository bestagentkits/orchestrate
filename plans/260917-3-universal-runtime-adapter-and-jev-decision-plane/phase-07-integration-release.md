---
phase: 7
title: "Integration and release"
status: pending
priority: P1
effort: 8h
dependencies: [5, 6]
---

# Phase 7: Integration and release

## Goal

Make the new structure the only structure, in one atomic path flip. Rewrite
`SKILL.md` around the adapter boundary and the decision plane, update the README
index, upgrade notes and acceptance wording, bump the version on every surface
that carries one, repoint every inbound link, delete the superseded files, and
run the whole-tree verification sweep.

This phase owns **every deletion**. No earlier phase deletes a file, so no
intermediate phase can end with a dangling link.

## Files to Create / Modify

- Modify: `plugins/orchestrate/skills/orchestrate/SKILL.md` (Authority Map, Pipeline, Pi Sessions, Worktree Isolation, Safety Defaults, Limitations, Completion Report, `metadata.version`)
- Modify: `README.md`
- Modify: `plugins/orchestrate/.claude-plugin/plugin.json` (version, keywords)
- Modify: `.claude-plugin/marketplace.json` (description/keywords alignment; it carries no version field)
- Modify: `site/index.html` (version strings only — no redesign)
- Modify: `references/dispatch-hardening.md` (relink + phantom citation)
- Modify: `references/job-spec.md`, `references/output-layout.md` (decision-trace/profile/calibration fields, relinks)
- Modify: `references/observation.md`, `references/failure-modes.md`, `references/metrics-and-self-improvement.md` (relinks)
- Delete: `references/model-routing.md`, `references/runtime-matrix.md`, `references/harness-profiles.md`, `references/arbiter-checklist.md`, `references/pi-sessions.md`, `references/pi-onboarding.md`

## Tasks & Steps

1. Rewrite the `SKILL.md` **Authority Map** so every durable contract has exactly
   one owner under `references/` plus the adapter index under `runtimes/`. No
   Pi-specific authority remains in core; `runtimes/README.md` is the adapter index.
2. Update the `SKILL.md` **Pipeline** so the deterministic boundary and the
   decision plane are visible, and so the optimizer's ordering is correct:

   ```text
   intake → job graph → live inventory/profile → safety gate
     → hard filter → semantic rank → graph optimizer (post-routing)
     → dispatch → normalized events → trace watchdog → triage/retry
     → verification checks → micro-arbiter gate → C3 arbiter or accept → report
   ```

   State at each hop which layer owns the decision, and state what the
   integration step follows when the micro-arbiter path was taken (it must say
   the accepted-without-C3 count is recorded in the report).
3. Update the Pi Sessions, Worktree Isolation, Safety Defaults, Limitations and
   Completion Report sections: Pi moves to the adapter index; safety defaults
   point at `safety-policy.md`; the Limitations section records the
   decision-plane degradation behaviour, the classifier-independence caveat (a
   System-1 verdict is never independent review evidence for a C3 decision), and
   the fact that R2 and above always receive arbiter review.
4. Repoint `dispatch-hardening.md`: lines 7–8 currently link `model-routing.md`
   and `runtime-matrix.md`. Point routing at `routing-policy.md`, live
   command/flag/model verification at `runtime-profile.md`, and fix line 71's
   citation of a `runtime-matrix.md` section ("Dispatch Result Verification")
   that does not exist — point it at `verification.md`.
5. Update `README.md`:
   - reference-files table reflects the new tree; removed paths are gone;
   - pipeline table shows the decision plane and the corrected optimizer order;
   - the routing section splits into hard policy versus decision plane;
   - **acceptance wording states which runs receive C3 review and which may be
     micro-arbiter-accepted**, rather than implying every job is arbiter-reviewed;
   - replace the stale `## Upgrading from 1.4.x` heading with a version-agnostic
     `## Upgrading` section carrying the **move map** for 1.8.x → 2.0.0;
   - add the maintainer note describing the phase-7 grep sweep (there is no
     committed linter).
6. Bump the version to **2.0.0 on all four surfaces** (the earlier draft missed
   two): `plugin.json`, `SKILL.md` frontmatter `metadata.version`, and
   `site/index.html` at the byline (`:425`), the spec table (`:438`) and the
   i18n byline (`:830`). A landing-page *redesign* stays out of scope; a version
   string that contradicts the release does not.
7. Extend `job-spec.md` and `output-layout.md` with the machine fields owned by
   earlier phases: decision trace, `classifier_hint`, calibration record and
   threshold, floor delta, and the accepted-without-C3 count. `job-spec.md`
   remains the single owner of machine fields.
8. Delete the six superseded files, but only after their content is fully
   absorbed and the verification sweep below is clean. Then confirm every
   remaining reference resolves.
9. Run the full tree sweep, including the **presentation parity** check: the
   README and landing page must not assert a weaker control than
   `safety-policy.md`. Both currently drift from `model-routing.md:76`
   (`README.md:73` drops "or stronger isolation"; `site/index.html:588` drops
   "explicit checks").

## Verification

```bash
S=plugins/orchestrate/skills/orchestrate

# 1. denylist: no link to a removed path anywhere outside the plan move map
grep -rnE '\]\((\./)?(model-routing|runtime-matrix|harness-profiles|arbiter-checklist|pi-sessions|pi-onboarding)\.md\)' \
  --include='*.md' . | grep -v '^./plans/' || echo "denylist clean"

# 2. reachability: every reference and adapter note is linked by a resolved link
for f in $S/references/*.md $S/runtimes/*.md; do
  b=$(basename "$f")
  grep -rq "($b)" $S README.md || echo "UNREACHABLE $b"
done

# 3. one version everywhere
grep -rn '1\.8\.0' plugins README.md site .claude-plugin --include='*.json' --include='*.md' --include='*.html' && echo "FAIL: stale version" || echo "version clean"
grep -rn '2\.0\.0' plugins site .claude-plugin | wc -l

# 4. presentation parity with the R2 control definition
grep -n 'R2' README.md site/index.html $S/references/safety-policy.md

# 5. boundary: no accept/escalation table outside verification.md
grep -rln 'escalation matrix\|accept without C3' $S/references

# 6. the six files are gone and the two new trees exist
ls $S/references $S/runtimes
```

- [x] Denylist clean repo-wide (the plan's own move map is the only permitted mention, via the `plans/` exclusion).
- [x] Every file under `references/` and `runtimes/` is reachable by a resolved link.
- [x] `1.8.0` appears nowhere; `2.0.0` appears on all four surfaces.
- [x] README and site do not assert a control weaker than `safety-policy.md`.
- [x] The escalation matrix exists only in `verification.md`.
- [x] The six superseded files are deleted and no link points at them.
- [x] `ak plan validate` passes for this plan directory.
