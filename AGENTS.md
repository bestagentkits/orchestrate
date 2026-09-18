# AGENTS.md

Agent context for this repository. Read this before editing anything here.

## What this repository is

It ships **documentation, not code**. There is no build, no test runner, no package
manager and no published binary. The payload is a Claude Code plugin that is also a
plain Agent Skills directory, so the shipped artifact is markdown plus a single static
landing page.

The only automation is `.github/workflows/pages.yml`, which publishes `site/` to
GitHub Pages. There is no test CI. **A change here is verified by the maintenance
sweep in `docs/maintaining-the-docs.md`, not by a test suite.**

## Which files are authoritative

- `plugins/orchestrate/skills/orchestrate/references/` — **authoritative** contracts,
  one owner per concern. This is the specification.
- `plugins/orchestrate/skills/orchestrate/runtimes/` — **authoritative** adapter index
  and per-runtime capability maps.
- `plugins/orchestrate/skills/orchestrate/SKILL.md` — the entry document and the
  authority map.
- `README.md` and `site/index.html` — **parity-checked summaries**. They are reader
  surfaces, never the source of truth. When they disagree with `references/`, the
  reference wins and the summary is the bug.

**No behavior may depend on a frontmatter key outside `name` and `description`.** The
other keys are AgentKit extensions, and a conforming harness ignores them.

## Rules that a change must not break

- **Never copy a catalog or a measurement.** No benchmark value, model name, flag,
  version number, price or leaderboard row may be pasted or copied into the skill.
  Resolve from live evidence at run time. This is the repository's central invariant,
  and it is a review item a grep cannot enforce.
- **The accept predicate has exactly one owner.** "Accept without a C3 call" is stated
  only in `verification.md`. No other file may restate it.
- **Credential values are never printed, prompted for, or committed.** Only presence
  or absence, the source location and the source's trust class are recorded. The
  resolution order is owned by `decision-plane.md`.
- **Owner-fixed constants are pinned in their owning document** and fanned out to
  `job-spec.md` validation and the README summary. A bound that is named but unpinned
  cannot be asserted, which is a defect this repository has had to fix twice.
- **Every contract has exactly one owner.** Before adding a rule, find its owner; do
  not create a second one. When two references disagree, stop and report the mismatch
  rather than picking the newer-looking text.
- **No permission bypass, ever.** A job needing more privilege gets a scoped
  permission with explicit approval, a stronger boundary, or `blocked`.
- **Probabilistic input may never widen a gate.** Benchmark evidence ranks candidates;
  it cannot set eligibility, a floor, a tier, a control or an approval.

## How to verify a change

Run the numbered sweep in `docs/maintaining-the-docs.md`, **from the repository
root**. It is the verification mechanism, and its assertions are the contract's
executable part.

Two disciplines make the sweep trustworthy, and both exist because their absence caused
real defects here:

1. **Record an assertion's baseline before editing.** An assertion whose baseline
   already satisfies it proves nothing; an assertion that can never be satisfied stalls
   the work. Several gates in this repository's history were one or the other.
2. **An exact phrase an assertion greps must survive formatting.** Do not wrap it across
   lines, do not bold part of it, and match its case. A gate that fails on wording
   looks like a failing rule.

A green sweep proves a token exists, not that a rule holds. Review the rule itself.

## Repository conventions

- Markdown files are created under `plans/` or `docs/` — not at the repository root —
  unless a task explicitly says otherwise. `plans/reports/` is git-ignored.
- The landing page holds two copy decks: **English is derived from the DOM** at load
  time (`EN[el.dataset.i18n] = el.innerHTML`), while Vietnamese is a literal object.
  Adding a `data-i18n` element therefore **requires** adding the matching Vietnamese
  key, or parity breaks.
- Dotenv files are git-ignored; `.env.example` is deliberately not.
