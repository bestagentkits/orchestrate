---
title: "Publish the Jev (TypeSafe) reference-provider story and relocate the maintenance sweep"
description: "Move the doc-integrity sweep out of README into docs/, repointing AGENTS.md and the Pages workflow, and add the Jev (TypeSafe) reference-provider story — what it is, why it backs the six decision tasks, and how its provider key is configured — to README and the landing page in both copy decks, without copying a single vendor measurement."
status: completed
priority: P2
effort: "0.5d"
issue: 13
branch: jev-docs
tags: [docs, reader-surfaces, credentials, maintenance]
blockedBy: []
blocks: []
created: 2026-09-18
---

# Publish the Jev (TypeSafe) reference-provider story and relocate the maintenance sweep

## Overview

Two requests, one of which is a contract change rather than a copy edit.

1. **The Jev story is missing from the reader surfaces.** `decision-plane.md:74`
   names Jev (TypeSafe) as "the design this contract was written against, and as one
   optional provider", and `SKILL.md:313` repeats it. Neither reader surface says
   *what Jev is*, *why a System-1 model is the right shape for the six decision
   tasks*, or *which variable carries its key* — `README.md`'s Credentials section
   never names `TYPESAFE_API_KEY`, so the only place a reader meets the variable is
   `.env.example`. The request is to close that gap on both surfaces.

2. **`## Maintaining the docs` leaves `README.md`.** That section is 414 lines
   (471–884) of which 368 are the executable sweep, and it is the repository's only
   verification mechanism: `AGENTS.md:14` calls a change here "verified by the
   maintenance sweep in `README.md`, not by a test suite", `AGENTS.md:55` says to
   run it, and `pages.yml:5-6` points at it. Removing it from README therefore has
   to preserve the sweep, not just delete prose — the chosen resolution is to move
   it to `docs/maintaining-the-docs.md` and repoint every reference.

Both changes are constrained by the repository's own rules, and the constraints are
the interesting part of this plan:

- **No copied measurement.** `AGENTS.md` forbids pasting "any benchmark value, model
  name, flag, version number, price or leaderboard row". TypeSafe publishes exactly
  those for Jev (speed and cost multipliers, per-token prices, model IDs), so the
  strengths have to be stated in the contract's own qualitative vocabulary.
- **One owner per concern.** The four-step `TYPESAFE_API_KEY` read order is owned by
  `decision-plane.md`. README may summarise it (it already declares itself a
  parity-checked summary); a third full restatement is not allowed, so the site
  sub-block points at the owner instead of repeating the list.
- **Credential values are never printed, prompted for or committed.** The release's
  own verification table forbids documenting `export …TYPESAFE…` or `--api-key=`, so
  "how to configure the key" must be written as *where the value is read from and
  how it is created*, never as a copy-pasteable export.
- **The accept predicate has exactly one owner** (`verification.md`). The Jev prose
  must not restate the accept conditions.
- **The landing page's numbering is gated.** Sweep step 14 asserts the `sec-num`
  sequence is exactly `01..10`, so Jev is added as a sub-block inside an existing
  section rather than as a new numbered one.

## Goals

1. `docs/maintaining-the-docs.md` carries the sweep, runnable from the repository
   root, and `README.md` carries a one-line pointer instead of the section.
2. Every reference to the sweep's old location is repointed: `AGENTS.md` (three
   sites) and `.github/workflows/pages.yml` (one comment).
3. `README.md` gains a `### Jev (TypeSafe), the reference System-1 model` subsection
   that states what Jev is, why the plane's six decision tasks can consume it, and
   that it is optional and never required.
4. `README.md`'s Credentials section names `TYPESAFE_API_KEY`, points at the owner of
   the read order, and states the egress-authorization precondition — a key alone is
   not sufficient.
5. `site/index.html` gains a Jev sub-block in the existing decision-plane section
   (`sec-num 04`) with a Vietnamese entry for every new `data-i18n` key.
6. The relocated sweep stays green, and the move is guarded by one new assertion so
   the pointer cannot dangle again.

## Non-goals

- **No new numbered section** on the landing page, and no change to the `01..10`
  sequence or to any other verified gate.
- **No change to the contract.** `decision-plane.md`, `SKILL.md` and the rest of
  `references/` are untouched: this plan changes reader surfaces only.
- **No vendored TypeSafe copy.** No request shape, endpoint, SDK snippet, curl
  example, model ID, price or multiplier is reproduced — documenting a direct API call
  would also contradict the contract's own "no bespoke provider client".
- **No sweeping denylist for measurements.** The relocated doc states that the
  no-copied-measurement rule is a review item a grep cannot enforce; adding a
  partial token denylist would contradict that stated position and read as complete
  when it is not. It stays a one-off check recorded in the validation log.
- **No new CI gate.** `pages.yml` still gates nothing; it only publishes `site/`.

## Deliverable shape

- `docs/maintaining-the-docs.md` — new; the sweep plus its framing, with an explicit
  "run from the repository root" instruction and one new step 19 guarding the
  pointer.
- `README.md` — `## Maintaining the docs` replaced by a short `## Maintainer notes`
  pointer; new Jev subsection under Routing; Credentials section names the variable
  and the egress precondition.
- `site/index.html` — one sub-block in `sec-num 04`, one small stylesheet rule, and
  the matching `VI` copy-deck entries.
- `AGENTS.md`, `.github/workflows/pages.yml` — repointed references only.
- `plans/260918-1742-jev-typesafe-reader-surfaces/` — this plan and its three phases.

## Phases

| Phase | Name | Status |
| --- | --- | --- |
| 1 | [Relocate the maintenance sweep](phase-01-relocate-maintenance-sweep.md) | Complete |
| 2 | [Jev reader surfaces](phase-02-jev-reader-surfaces.md) | Complete |
| 3 | [Verification, review and release](phase-03-verification-release.md) | Complete |

Phase 1 is independent of phase 2 and touches disjoint files, so either order is
valid; it runs first here because phase 2's verification is the relocated sweep.
Phase 3 depends on both and owns the evidence, the review and the release.

## Test strategy

There is no test runner in this repository, so the strategy follows `AGENTS.md`:
**the sweep is the executable part of the contract**, and a new assertion is only
trustworthy if its baseline was recorded first and if it is provably red under
mutation.

1. **Baseline before editing.** The sweep was extracted from `README.md` at
   `471..884` and run on the unmodified tree. Result: **green** — no `FAIL`,
   `MISSING`, `UNREACHABLE`, `PARITY FAIL`, `STUB FAIL`, `I18N FAIL`, `CONTROL
   FAILED`, `CONSTANT FAIL`, `NO PEER LINK`, `TREE DRIFT`, `FLOW LOOP`, `IR/SVG
   MISMATCH`, `UNMAPPED FAMILY`, `OCCLUDED LABEL` or `EDGE HIDING` string appeared.
   Informational lines were the expected `control OK` (×3), `version clean`,
   `portability clean`, `duplicated order (must be 1 file): 1`, `.env ignored`,
   `no key-printing guidance`, `trace artifact listed`, `completeness field defined`,
   `no external requests`, `branding clean`, `harness-neutral`.
2. **Re-run after the move, from the new location and from the repository root.**
   The sweep uses repository-root-relative paths, so the CWD requirement is now
   stated in the doc rather than implied by README's own location.
3. **Mutation control for the new step 19.** Delete the README pointer and confirm
   step 19 reports; restore it and confirm it is silent. An assertion that cannot
   fail is not a gate.
4. **One-off constraint scans** (recorded in phase 3, not added to the sweep):
   forbidden key-documentation patterns, vendor-figure patterns, i18n coverage,
   `sec-num` sequence, and the four parity literals.
5. **Visual check.** Render the page and confirm the sub-block is styled and the
   Vietnamese deck renders it, in both themes.

## Change manifest (what a reviewer should be able to verify)

| # | Assertion | Command | Baseline | Target |
| --- | --- | --- | --- | --- |
| 1 | README no longer owns the sweep | `grep -c '^## Maintaining the docs' README.md` | 1 | 0 |
| 2 | README points at the new owner | `grep -c 'docs/maintaining-the-docs.md' README.md` | 0 | 1 |
| 3 | The sweep moved intact | `sed -n '/^```bash$/,/^```$/p' docs/maintaining-the-docs.md \| sed '1d;$d' \| wc -l` | absent | 387 |
| 4 | AGENTS.md repointed | `grep -c 'docs/maintaining-the-docs.md' AGENTS.md` | 0 | 2 |
| 5 | Pages workflow repointed | `grep -c 'docs/maintaining-the-docs.md' .github/workflows/pages.yml` | 0 | 1 |
| 6 | No surface still points README at the sweep | `grep -rn 'Maintaining the docs' --include='*.md' --include='*.yml' . \| grep -v '^./plans/'` | 5 | ≤1 (the pointer's own wording only, if any) |
| 7 | README names the variable | `grep -c 'TYPESAFE_API_KEY' README.md` | 0 | ≥1 |
| 8 | The read order still has one owner | `grep -rl 'process\.env' plugins/orchestrate/skills/orchestrate/references \| wc -l` | 1 | 1 |
| 9 | No key documentation | sweep step 12 — its pattern is assembled from parts so the guard cannot match itself | none | none |
| 10 | No vendor measurement | `grep -rniE 'MTok\|per million\|\$[0-9]+\.[0-9]\|\$[0-9]{2,}\|193\.6\|444\.6\|jev-latest\|jev-preview\|jev-[0-9]\|x faster\|x cheaper' README.md site/index.html` | none | none |
| 11 | Landing page numbering intact | `grep -o '<span class="sec-num">[0-9]*</span>' site/index.html \| grep -o '[0-9]*' \| tr '\n' ' '` | `01 02 … 10 ` | unchanged |
| 12 | Copy-deck parity | sweep step 8 | green | green |
| 13 | Parity literals survive both surfaces | sweep step 6 | green | green |
| 14 | Jev stays optional | `grep -q 'reference implementation' README.md && grep -qi 'never a requirement\|not required' README.md` | n/a | true |

Baseline note for #10, recorded after the first attempt failed its own discipline:
the initial pattern used `\$[0-9]` and scanned `docs/` as well, and it reported one hit
at **baseline** — the relocated sweep's own `check() { … "$2" … }` line, where `$2` is a
shell positional parameter, not a price. An assertion whose baseline already trips
proves nothing, so the pattern was narrowed to price-shaped literals (`$0.042`, `$42`)
and the scan to the two prose surfaces whose copy actually changes; the executable shell
in the maintenance document is not where a vendor figure would be pasted. Baseline under
the corrected instrument: **empty**, and empty again after the change.

Baseline note for #9: the same trap applies to a hand-rolled try at this scan. Writing
`echo .*TYPESAFE` as a literal matches the sweep's own self-protecting `keypat` line, so
the instrument is the sweep's step 12 — which assembles the pattern from parts for
exactly that reason and reports `no key-printing guidance` at baseline and after.

## Success criteria

- The relocated sweep is green when run from the repository root, and step 19 is
  red when the README pointer is removed.
- Both reader surfaces describe Jev as the **reference** and **optional**
  implementation, and neither claims it is required or reachable in every run.
- A reader can find the variable name on both surfaces and reach the owner of the
  read order in one hop, without any surface documenting how to print or export it.
- No vendor measurement, model ID, price or version is reproduced anywhere.
- The PR records the deviation from the answered placement question: the Jev
  sub-block sits in the decision-plane section (`sec-num 04`), not the routing
  section (`sec-num 03`), because that section owns the topic and mirrors README's
  subsection — the answered constraint it preserves is "no new numbered section".

## Risks and open questions

- **The relocation is a contract edit, not a copy edit.** `AGENTS.md:14` asserts how
  a change here is verified; if any reference is missed, the repository claims a
  verification step that does not exist where it says it does. Mitigated by
  change-manifest items 4–6 plus the new sweep step 19.
- **The sweep now has a CWD precondition that README's position made implicit.**
  Stated explicitly in the moved document; a maintainer running it from `docs/`
  would otherwise see every path-based check fail at once.
- **A reader may still want the TypeSafe figures the invariant refuses.** The honest
  answer is that they live in TypeSafe's own material, which both surfaces link;
  reproducing them here is what the repository forbids.
- **Open question (for the human reviewer, not a blocker):** whether the maintainer
  sweep should eventually become a committed script. The relocation does not change
  the existing rationale against it (`dispatch-hardening.md`'s skill-relative script
  rule), so it stays normative.

## Validation Log

### Session 1 — 2026-09-18

- Baseline sweep extracted from `README.md:471-884` (`awk`), block delimited by the
  first `^```bash$` and the next `^```$`, 368 lines, run from the repository root:
  **green**, as itemised under Test strategy.
- `gh repo view` → `bestagentkits/orchestrate`, default branch `main`; branch
  `jev-docs` is an isolated worktree and is level with `origin/main` (`1d51791`) —
  `git rev-list --left-right --count origin/main...HEAD` = `0 0`.
- Source issue: #13. Labels `ready to cook`, `in progress`, `ready to ship stable`
  and `ready to ship beta` exist.
- Placement decision (answered by the user): sub-block in an existing section, no new
  numbered section; qualitative strengths only, no vendor figures; sweep relocated to
  `docs/` with a README pointer.

### Session 1 — review pass and final state

An independent advisory review of the full diff raised two items that were accepted and
fixed, two that were already satisfied in the tree, and one that needed the owner:

- **Accepted — partial restatement of the credential order.** The site's key card had
  said the variable "is read from the four locations documented in `decision-plane.md` —
  the process environment first". The clause restated part of an order owned by
  `decision-plane.md` in prose that no `process.env` grep would catch, so it was removed
  from both decks. The card now points at the owner without reproducing any of the order.
- **Accepted — placement needed the owner, not disclosure.** The answered option named the
  routing section (`sec-num 03`) while the sub-block was placed in the decision-plane
  section (`sec-num 04`). The user confirmed `sec-num 04` explicitly, so the deviation is
  now an acknowledged decision rather than a silent one.
- **Already satisfied — repo-root precondition.** The review asked whether the moved
  document states it; it does, in the paragraph beginning "Run the whole sweep before
  merging a change to this reference set", which adds "**Run it from the repository
  root**" and explains that the document's own location is not its working directory.
- **Already satisfied — the pointer names the exact path.** `README.md` links
  `[docs/maintaining-the-docs.md](docs/maintaining-the-docs.md)` from the position the old
  section occupied.
- **Checked — the extended step 12 cannot match itself.** Adding `docs` to the scan set
  does not sweep the relocated file's own `keypat` literal: the pattern is assembled from
  parts, and the run reports `no key-printing guidance` both before and after the move.

Final manifest state after the review fixes: items 1–14 all pass as tabulated; the
relocated sweep prints no failure string; mutation controls A (README pointer), B (a
Vietnamese entry) and C (`sec-num`) each turn the corresponding assertion red and the tree
restores byte-identically afterwards. The sub-block renders in English and Vietnamese, in
light and dark, and the revised key sentence and the TypeSafe anchor were re-checked in
both decks after the edit.
