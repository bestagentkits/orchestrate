---
phase: 3
title: "Verification, review and release"
status: completed
priority: P0
effort: "0.25d"
dependencies: [1, 2]
---

# Phase 3: Verification, review and release

## Goal

The change is proven against the repository's own mechanism rather than asserted: the
relocated sweep is green, the new assertion is red under mutation, the one-off
constraint scans are recorded with their measured output, the page is checked as
rendered, and the result is reviewed before it ships.

## Files to Create / Modify

- Modify: `plans/260918-1742-jev-typesafe-reader-surfaces/plan.md` (validation log)
- Create: `plans/reports/docs-260918-1742-jev-typesafe-reader-surfaces.md` (the report,
  under the git-ignored `plans/reports/`)

## Tasks & Steps

### Task 3.1 — Run the relocated sweep and prove the new assertion is live

- **Steps:**
  1. Extract the fence from `docs/maintaining-the-docs.md`, run it from the repository
     root, and diff its informational output against the phase-0 baseline recorded in
     `plan.md`. Any *new* failure string is a regression; the informational lines must
     be the same set plus step 19's silence.
  2. Mutation control: remove the README pointer, re-run, and confirm step 19 reports;
     restore it and confirm step 19 is silent. Record both outputs verbatim.
  3. Mutation control for the move: point one AGENTS.md reference back at `README.md`
     and confirm step 19's stale-anchor clause reports.
- **Success criteria:** green with the pointer present; red with it absent; restored
  green.

### Task 3.2 — One-off constraint scans

Record the measured output of each, and state explicitly that they are **not** added to
the sweep:

| Check | Command | Expected |
| --- | --- | --- |
| Forbidden key documentation | sweep step 12, whose pattern is assembled from parts so the guard cannot match itself | `no key-printing guidance` |
| Vendor measurement | `grep -rniE 'MTok\|per million\|\$[0-9]+\.[0-9]\|\$[0-9]{2,}\|193\.6\|444\.6\|jev-latest\|jev-preview\|jev-[0-9]\|x faster\|x cheaper' README.md site/index.html` | nothing |
| Copy-deck parity | sweep step 8 | green |
| Numbering | sweep step 14 `sec-num` | `01..10` |
| Parity literals | sweep step 6 | green |
| Single owner of the order | `grep -rl 'process\.env' "$S" \| wc -l` | `1` |
| No dangling sweep reference | `grep -rn 'Maintaining the docs' --include='*.md' --include='*.yml' . \| grep -v '^./plans/'` | nothing |

The vendor-measurement denylist is deliberately **not** added as a sweep step: the
relocated document itself states that the no-copied-measurement rule is "a review item
a grep cannot enforce, because any token check would have to name the token it
forbids". Adding a partial list would contradict that and read as complete. Its
baseline is recorded here so a reviewer can see it was measured, not assumed.

**Baseline discipline, applied to these two scans themselves.** The first version of the
vendor scan used `\$[0-9]` across `docs/` and reported one hit at baseline — the moved
sweep's `check() { … "$2" … }` line, a shell positional parameter. The first version of
the key scan wrote `echo .*TYPESAFE` literally and matched the sweep's own self-protecting
`keypat` line. Both were non-assertions: one tripped before any edit, the other flagged
the instrument instead of a violation. The corrected instruments are the tightened price
pattern over `README.md` and `site/index.html`, and step 12's part-assembled guard. Recorded
here because a green result from a broken scan is worse than no scan.

### Task 3.3 — Visual check of the landing page

- **Steps:** render `site/index.html` and capture the decision-plane section with the
  sub-block, in English and Vietnamese, in light and dark. Confirm the sub-block
  inherits the section's typography, that the Vietnamese copy replaces it rather than
  leaving English behind, and that nothing overflows its card.
- **Success criteria:** the sub-block is styled and both decks render; no unstyled or
  duplicated copy.
- **Evidence:** screenshots recorded in the report; the page's own
  `localStorage`-backed language switch exercised rather than assumed.

### Task 3.4 — Independent review

- **Steps:** review the full diff for: dangling references, a second owner of the key
  order or the accept predicate, a widened gate, leaked vendor figures, an `export`/
  argv key path, an i18n key without a VI entry, a `sec-num` change, and any rewording
  that weakens an R0–R3 control clause.
- **Success criteria:** no Critical or Important finding open; Minors either fixed or
  recorded with a reason.
- **Evidence:** the finding list with severity counts in the report, never a score.

### Task 3.5 — Release

- **Steps:** commit on `jev-docs`; update issue #13 to `in progress` before the
  implementation commit and to `ready to ship stable` after review; open the PR with
  the deviation note (Jev sub-block in `sec-num 04`, not `sec-num 03`) and the
  verification evidence; review/fix/reply; merge; then watch the Pages workflow for
  the merge commit — it is path-filtered to `site/**` and `pages.yml`, so this PR
  should trigger it because it edits `site/index.html`, and the published page must
  match the source byte-for-byte afterwards.
- **Success criteria:** PR merged, Pages run green for the merge commit, the live page
  shows the sub-block.
- **Note:** `pages.yml` is path-filtered, so a run is expected here; the previous
  merged PR (#12) correctly triggered none because it touched no `site/**` path.

## Verification

```bash
# Final: whole sweep from the new owner, from the repository root.
sed -n '/^```bash$/,/^```$/p' docs/maintaining-the-docs.md | sed '1d;$d' > /tmp/final-sweep.sh
bash /tmp/final-sweep.sh
```

### Baseline table (measured before this phase's edits)

| Check | Baseline | Target | Mutation that must trip it |
| --- | --- | --- | --- |
| Relocated sweep | green (pre-move, as extracted from README) | green | any regression above |
| Step 19 (new) | absent | silent | deleting the README pointer |
| `sec-num` sequence | `01..10` | `01..10` | adding a numbered section |
| Copy-deck parity | green | green | dropping a VI entry |
| Parity literals | green | green | rewording `r2` |

## Failure Protocol

A failing verification step stops the release. Diagnose from the recorded baseline
rather than from the failing output alone, and if the same failure survives two
materially equivalent fixes, escalate for counsel instead of trying a third variant.
