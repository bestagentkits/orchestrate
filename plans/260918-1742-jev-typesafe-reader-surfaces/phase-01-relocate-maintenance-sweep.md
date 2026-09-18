---
phase: 1
title: "Relocate the maintenance sweep"
status: completed
priority: P1
effort: "0.25d"
dependencies: []
---

# Phase 1: Relocate the maintenance sweep

## Goal

The 18-step doc-integrity sweep lives in `docs/maintaining-the-docs.md`, runs green
from the repository root, and every surface that used to point at
`README.md#maintaining-the-docs` points at the new file instead — with one new
assertion so the pointer cannot dangle again.

## Files to Create / Modify

- Create: `docs/maintaining-the-docs.md` (the sweep and its framing, moved)
- Modify: `README.md` (replace the 414-line section with a short pointer)
- Modify: `AGENTS.md` (three references to the sweep's location)
- Modify: `.github/workflows/pages.yml` (the header comment)

## Facts this phase must respect, verified by grep

- `README.md:471` opens `## Maintaining the docs`; the section ends at `:884`, with
  `## What it is not` at `:885`. Of the 414 lines, `:505`–`:877` is the `bash` fence
  and 368 lines inside it are the sweep.
- The sweep's own paths are repository-root-relative (`plugins/…`, `site/index.html`,
  `.env.example`, `git ls-files`), so its CWD precondition is the repository root.
  `README.md`'s location made that implicit; the moved document must say it.
- Two self-referential comments name the host file and become wrong on the move:
  step 16's "this block is itself a greppable surface of README.md", and step 17's
  "a whole-file search matches this block's own NORM list" (still true, but it reads
  as README-specific beside the other).
- Step 12's key-print scan set is `plugins README.md site AGENTS.md CLAUDE.md`. It
  does not include `docs`, which is about to become a reader surface for the first
  time. The pattern is assembled from parts (`keypat='echo .*TYPESAFE''_API_KEY'`),
  so a literal in the moved file still cannot match itself.
- `AGENTS.md:14` and `AGENTS.md:55` carry the sweep's location, so those are the two
  path references to repoint. `AGENTS.md:68` — "A green sweep proves a token exists, not
  that a rule holds" — is the third mention of the sweep and carries no path, so it needs
  no edit. (The count matters: the manifest asserted three path occurrences before the
  count was measured, and the real figure is two.)
- `AGENTS.md` is itself swept for stale version strings (step 3 greps
  `2\.0\.0\|2\.0\.1\|2\.1\.0\|1\.8\.0` across `plugins site .claude-plugin AGENTS.md`),
  so the repointing edit must not introduce a version literal.

## Tasks & Steps

### Task 1.1 — Create `docs/maintaining-the-docs.md`

- **Goal:** the sweep and its framing are preserved verbatim apart from the changes
  the move itself requires.
- **Target file:** `docs/maintaining-the-docs.md`.
- **Steps:**
  1. Copy `README.md:471`–`:884` as the body, dropping the `## Maintaining the docs`
     heading in favour of a document-level `# Maintaining the docs`.
  2. Rewrite only the opening paragraph's framing so it states *why this is a
     document rather than a README section*: README is a published reader surface and
     a parity-checked summary, so maintainer material belongs under `docs/`
     (`AGENTS.md`'s own convention). Keep every other sentence of the rationale,
     including the `dispatch-hardening.md` reason against a committed script.
  3. Add the CWD precondition explicitly: run the sweep from the repository root.
  4. Fix the two self-referential comments that name README.md as the host file. The
     step-16 comment becomes "this block is itself a greppable surface of this
     document"; step 17's note keeps its meaning but drops the README-specific
     reading.
  5. Add step 19 to the sweep, guarding the move itself:
     - the document exists at `docs/maintaining-the-docs.md`;
     - `README.md` contains a link to it;
     - no file outside `plans/` still contains the old heading anchor.
     Numbering continues from 18 and the step carries a comment saying what failure it
     exists to catch (a pointer that dangles after a later move).
  6. Extend step 12's scan set with `docs`, now that `docs/` is a reader surface.
- **Success criteria:** the fence-extracted sweep is 387 lines — 368 moved verbatim,
  3 from extending step 12's comment to explain that `docs` joined the scan set, and
  16 for step 19 — and the document is self-contained without README.
- **Verify:** `sed -n '/^```bash$/,/^```$/p' docs/maintaining-the-docs.md | sed '1d;$d' | wc -l` → `387`.

### Task 1.2 — Replace the README section with a pointer

- **Goal:** README stops carrying maintainer material and still finds it.
- **Target file:** `README.md`.
- **Steps:**
  1. Delete `:471`–`:884`.
  2. Insert in its place a short `## Maintainer notes` section: one sentence saying
     the doc-integrity sweep lives in `docs/maintaining-the-docs.md`, with a relative
     link, and that it is the repository's verification mechanism.
- **Success criteria:** `grep -c '^## Maintaining the docs' README.md` is `0`;
  `grep -c 'docs/maintaining-the-docs.md' README.md` is `1`; `## What it is not`
  still follows.
- **Verify:** the two counts above, plus `grep -c '^## ' README.md` unchanged minus
  one (the removed heading) plus one (the new heading).

### Task 1.3 — Repoint `AGENTS.md`

- **Goal:** the agent context names the real location.
- **Target file:** `AGENTS.md`.
- **Steps:** update the two references that carry a path — the "What this repository is"
  claim and the `## How to verify a change` instruction — to
  `docs/maintaining-the-docs.md`, adding the repository-root precondition to the second.
  Keep the framing ("this is the verification mechanism") and the two disciplines
  unchanged; the closing "A green sweep proves a token exists" sentence names no path and
  is left alone.
- **Success criteria:** `grep -c 'docs/maintaining-the-docs.md' AGENTS.md` is `2` and
  `grep -c 'Maintaining the docs' AGENTS.md` is `0`.
- **Verify:** both counts, plus sweep step 3 for stale version literals.

### Task 1.4 — Repoint the Pages workflow comment

- **Goal:** the workflow's honesty claim stays true.
- **Target file:** `.github/workflows/pages.yml`.
- **Steps:** change the header comment to name `docs/maintaining-the-docs.md`.
- **Success criteria:** the workflow still runs no check and gates nothing; only the
  comment changes.
- **Verify:** `git diff --stat .github/workflows/pages.yml` shows comment-only
  changes; `grep -c 'docs/maintaining-the-docs.md' .github/workflows/pages.yml` is `1`.

## Verification

```bash
# From the repository root.
test -f docs/maintaining-the-docs.md
test "$(grep -c '^## Maintaining the docs' README.md)" = 0
test "$(grep -c 'docs/maintaining-the-docs.md' README.md)" = 1
test "$(grep -c 'docs/maintaining-the-docs.md' AGENTS.md)" = 2
test "$(grep -c 'docs/maintaining-the-docs.md' .github/workflows/pages.yml)" = 1
sed -n '/^```bash$/,/^```$/p' docs/maintaining-the-docs.md | sed '1d;$d' > /tmp/sweep-moved.sh
test "$(wc -l < /tmp/sweep-moved.sh)" = 387
bash /tmp/sweep-moved.sh
```

### Baseline table (measured before this phase's edits)

| Check | Baseline | Target | Mutation that must trip it |
| --- | --- | --- | --- |
| `grep -c '^## Maintaining the docs' README.md` | 1 | 0 | restoring the heading |
| `grep -c 'docs/maintaining-the-docs.md' README.md` | 0 | 1 | deleting the pointer (step 19) |
| `grep -c 'docs/maintaining-the-docs.md' AGENTS.md` | 0 | 2 | reverting one reference |
| `grep -c 'docs/maintaining-the-docs.md' .github/workflows/pages.yml` | 0 | 1 | reverting the comment |
| Whole sweep, from the new file | green | green | any of the above |

## Failure Protocol

If the moved sweep is not green from the repository root, stop and diagnose before
touching phase 2: a relocated gate that fails for a path reason would make every
later verification meaningless. Record the failing step and its output verbatim.
