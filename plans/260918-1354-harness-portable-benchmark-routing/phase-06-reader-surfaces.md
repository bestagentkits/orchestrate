---
phase: 6
title: "Reader surfaces and animated diagram"
status: pending
priority: P1
effort: "1.5d"
dependencies: [1, 2, 3, 4, 5]
---

# Phase 6: Reader surfaces and animated diagram

## Goal

The README and the landing page both describe the new behaviour — portability,
benchmark-ranked routing, promotion and fail-safe, tracing, and credentials — neither
surface still brands the skill as Claude-Code-only, and the landing page carries an
animated pipeline diagram in both languages, with no external asset and with animation
disabled for readers who ask for reduced motion.

## Files to Create / Modify

- Modify: `README.md` (harness framing, install section, four capability sections, the run-directory tree copy, reference index rows)
- Modify: `site/index.html` (kicker, install step, four capability sections, the run-directory tree copy, the animated diagram, EN + VI copy decks)

This phase does **not** touch version strings, the upgrade section, or the maintenance
sweep: phase 7 owns the release.

## Facts this phase must respect, verified by grep

- The Claude-Code-only branding is on the **landing page**, not in the README body: `site/index.html:412` (EN kicker, "A Claude Code Skill · MIT Licensed") and `:879` (VI kicker, "Một Claude Code Skill · Giấy phép MIT"). The README carries it as `README.md:5` ("**Multi-runtime agent orchestration for Claude Code.**") and `README.md:108` ("### As a Claude Code plugin"). Section 1's phase file records the same grep, so this phase is accountable for those four lines.
- `README.md:120` documents a second install path ("### As a plain skill"), so any claim that the marketplace is the only path is false.
- **Two of this phase's intended assertions are already green at baseline, so they prove nothing about the new work:** `grep -c 'prefers-reduced-motion' site/index.html` is `1` because `site/index.html:384-386` already carries a blanket `*, *::before, *::after { animation: none !important }` rule; and `grep -c 'aria-label' site/index.html` is `2` because the language and theme switchers already have one. Assertions must be written against the **new** artifacts.
- `grep -c '@keyframes' site/index.html` is **0** and `grep -c '<svg' site/index.html` is **0** at baseline, so those two are genuinely red-first.
- The page snapshots English copy from `innerHTML` and localizes by replacing a node's children (`site/index.html:984-985` and `:993-997`). **Putting `data-i18n` on the `<svg>` therefore destroys the diagram in Vietnamese mode**: the EN snapshot captures the whole SVG markup, and switching to VI removes every child and appends a translated string. The accessible name must come from a caption element that carries the key, referenced by `aria-labelledby` on the SVG.
- The page already has a seven-stage pipeline visual: `site/index.html:501` is "The seven-stage pipeline" with seven `.stage` articles. The new diagram must be named as a **different view of the same pipeline**, or the two compete.
- The run-directory tree is duplicated at `README.md:183-196` and in the site's `figOut` block; phase 5 updates them, and this phase must not re-diverge them.

## Tasks & Steps

### Task 6.1 — Make `README.md` harness-agnostic and document both install paths

- **Goal:** the README stops framing the skill as Claude-Code-only and leads with the new install path.
- **Target files:** `README.md` (the `:5` strapline, the `:108` heading, the `## Install` section).
- **Steps:**
  1. Reword `README.md:5` to state that this is an Agent Skills package that runs on any harness implementing that contract, naming Claude Code as one supported harness rather than the target.
  2. Reword the `### As a Claude Code plugin` heading to `### As a Claude Code plugin (one harness among many)`, or an equivalent that stops reading as the default path.
  3. In `## Install`, add the CLI path **before** the marketplace path, in a fenced `bash` block: `npx skills add bestagentkits/orchestrate`. Add two adjacent lines with one-line explanations: `npx skills add bestagentkits/orchestrate -g` for a global install, and `npx skills add bestagentkits/orchestrate -a <harness>` for a named harness.
  4. Add one sentence stating that the existing Claude Code marketplace install and the plain-skill copy at the section already in the file are both unchanged and still supported, so no reader is told to stop using them. Do **not** claim the marketplace is the only path.
  5. Add one markdown link to `plugins/orchestrate/skills/orchestrate/references/harness-portability.md` for the conformance surface and the per-harness paths.
- **Success criteria:** `:5` is harness-neutral, the install section leads with the CLI command, the existing paths are kept, and the portability owner is linked.
- **Verify:** `grep -c 'npx skills add bestagentkits/orchestrate' README.md` is `>= 1`; `grep -q 'harness-portability.md' README.md`; `grep -c 'As a plain skill' README.md` is `>= 1` (the existing path survived).

### Task 6.2 — Rebrand the landing page in both languages

- **Goal:** the landing page stops being the last surface that brands the skill as Claude-Code-only.
- **Target files:** `site/index.html` (the EN kicker, the VI deck's `kicker` value, the `<title>`, the install deck and colophon if they make the same claim).
- **Steps:**
  1. Replace `site/index.html:412`'s kicker text with a harness-neutral phrase (for example "An Agent Skills package · MIT Licensed").
  2. Replace the VI deck's `kicker` value at `:879` with the matching Vietnamese phrase.
  3. Check `<title>`, the install deck ("ships as a Claude Code plugin from its own marketplace") and the colophon ("Built for Claude Code") and reword each so it names Claude Code as one harness rather than the target. Keep the Claude Code install steps themselves, since that path still works.
  4. **Rebrand the fifth and sixth surfaces, which this phase previously missed because the sweep only greps the phrase "Claude Code Skill".** `.claude-plugin/marketplace.json:4` reads "Multi-runtime agent orchestration for Claude Code", and `site/index.html:6` carries the same claim in the `<title>`. Neither contains the swept phrase, so neither would have been caught. Reword both to a harness-neutral description, and add both to the phase-6 assertion below so a future sweep covers them.
  5. Add the `npx skills add bestagentkits/orchestrate` command to the install section, in both decks.
  6. Do not remove the Claude Code marketplace instructions — reorder and reframe them.
- **Success criteria:** no surface still says "Claude Code Skill"; the CLI install command appears in both decks; the marketplace path survives.
- **Verify:** `grep -c 'Claude Code Skill' site/index.html` is `0`; `grep -c 'npx skills add bestagentkits/orchestrate' site/index.html` is `>= 1`; `grep -c 'marketplace' site/index.html` is `>= 1`.

### Task 6.3 — Add the four capability sections to `README.md`

- **Goal:** each new behaviour is described for a reader, with a link to its owner and its bound.
- **Target files:** `README.md` (new subsections after the routing section; reference index rows).
- **Steps:**
  1. Add `### Benchmark-ranked routing`: state that routing ranks the already-eligible candidates by measured success rate, cost per task and task duration for a model at a given reasoning effort, that evidence is fetched from named sources and cached **between runs** at `.orchestrate/benchmarks.json` for a configurable period, and — in bold — that benchmarks **rank, never gate**: they cannot set eligibility, a floor, a tier, a control or an approval. State the bound: the cache TTL defaults to seven days and a job may not declare more than thirty days. Link `references/benchmark-evidence.md`.
  2. Add `### Promotion and fail-safe`: state that a quota limit, an outage or a crash promotes the job to the next candidate — after the same-runtime retry budget is exhausted, and honoring a declared `fallback_runtime` order first — within a bounded budget ending in a logged `blocked` state; and in bold that a **failed check never promotes** and a **permission or authorization stop never promotes**. State the bound: two promotions by default, four at most. Link `references/fallback-policy.md`.
  3. Add `### Trace and logs`: state that every routing decision, promotion, gate outcome and verdict carries one correlation identity, that the trace records fetch attempts as well as decisions, that it is redacted on write and excluded from exports unless reviewed, and that a run whose trace is incomplete must say so. Link `references/trace-and-logging.md`.
  4. Add `### Credentials`: state the four-step resolution order (process environment, project `.env`, the `skills/` directory `.env`, the skill's own `.env`), that the first location with a value wins, that the value is passed only through the inherited child environment, and that a shadowed source is reported. State that the key is never printed, never requested interactively and never committed — a missing key disables the decision plane instead. Do **not** reproduce any key value. State that this section is a parity-checked summary of `references/decision-plane.md`, which owns the order. Link it.
  5. Add four rows to the reference index table, one per new document.
- **Success criteria:** four sections exist, each with a working link and its owner-fixed bound where one exists; the negative rules are in bold; the credential section declares itself a summary.
- **Verify:** `grep -c 'Benchmark-ranked routing\|Promotion and fail-safe\|Trace and logs\|Credentials' README.md` is `>= 4`; `grep -c 'benchmark-evidence.md\|fallback-policy.md\|trace-and-logging.md\|decision-plane.md' README.md` is `>= 4`; `grep -c 'parity-checked summary' README.md` is `>= 1`.

### Task 6.4 — Add the four capability sections to the landing page in both languages

- **Goal:** the landing page describes the same behaviour as the README, not only the Claude Code install.
- **Target files:** `site/index.html` (a new `<section>` or an extension of an existing one; the `VI` deck).
- **Steps:**
  1. Add copy for the four capabilities from task 6.3, condensed to the page's editorial register, in the EN markup and mirrored in the `VI` deck. Keep each paragraph to three sentences at most.
  2. Give each capability its own `data-i18n` key so the section is translatable and assertable, and add every key to both decks.
  3. Reuse the existing section styles; do not introduce a new card or grid system.
- **Success criteria:** four new keys exist in the markup and in both decks, and each capability's copy is present.
- **Verify:** `grep -c 'data-i18n="capBench\|data-i18n="capPromote\|data-i18n="capTrace\|data-i18n="capCred' site/index.html` is `>= 4`; the i18n check in `## Verification` prints `i18n clean` with equal key counts.

### Task 6.5 — Build the animated pipeline diagram

- **Goal:** the landing page shows the pipeline moving, self-contained, accessible and localized.
- **Target files:** `site/index.html` (a new `<section>` after the routing section; new CSS in the existing `<style>` block; new `data-i18n` keys).
- **Steps:**
  1. Add the new `<section>` after the routing section, with a `sec-num` continuing the sequence, an `<h2 data-i18n="h2Flow">`, and a `<p class="sec-deck" data-i18n="deckFlow">` that **names the view**: state that this is the routing hops of the same pipeline the earlier section lists as stages, so the reader knows why the count differs from seven.
  2. Renumber the `sec-num` spans that follow. Record the exact insertion index and the spans moved in the phase notes, and assert the resulting sequence is contiguous and unique (task 6.8).
  3. Build the diagram as **inline SVG**, using the page's existing custom properties (`var(--ink)`, `var(--ink-soft)`, `var(--rule)`, `var(--accent)`, `var(--accent-2)`, `var(--paper-2)`) so it follows both themes. Give it `class="flow"` and `role="img"`.
  4. **Wire the accessible name correctly, avoiding the i18n trap.** Do **not** put `data-i18n` on the `<svg>`: add a `<figcaption id="flowCaption" data-i18n="flowCaption">` and set `aria-labelledby="flowCaption"` on the SVG. State in the phase notes why: a `data-i18n`-keyed `<svg>` is destroyed in VI mode, because `setLocalized` replaces the node's children with a translated string.
  5. Draw the main path as labelled nodes — probe, fetch, filter, rank, route, gate, dispatch, observe, check, verdict — plus a `decision plane` rail feeding `rank` and `gate`, a `promote` arrow leaving `dispatch` and re-entering `route`, and a `fail-safe` terminal node. Every node and edge must render in its static state with no animation applied, so the diagram is complete before any animation runs.
  6. Animate with CSS only: a travelling marker along the main path, a slower pulse on the plane rail, and a staggered highlight across the node labels. Use `@keyframes` and per-node `animation-delay`; add no JavaScript.
  7. Add a `@media (prefers-reduced-motion: reduce)` block that names the diagram's own classes and selectors — for example `.flow .marker, .flow .pulse, .flow .node-label { animation: none; }` — rather than relying on the pre-existing blanket rule. State in the phase notes that the blanket rule already exists, which is why the assertion in task 6.8 checks the **new** selectors by name and the `@keyframes` count against a baseline of `0`.
  8. Add a text list under the diagram with one `<li data-i18n="flowN…">` per stage, so the pipeline is readable as text as well as as a graphic.
  9. Add every new `data-i18n` key to both decks, including `flowCaption`. Keep node labels short enough to fit their shapes in both languages.
  10. Confirm no external request is added: no `<img>` with a remote source, no remote `<link>` stylesheet or font, no `@font-face` with a remote URL, no `srcset`, no `<iframe>`, no `xlink:href` or `<use>` pointing at a remote document, and no `url(http…)` in CSS.
- **Success criteria:** the diagram is inline SVG with CSS animation, names its own reduced-motion selectors, has an accessible name from a localized caption, has a text equivalent, adds no external request, and states that it is a different view of the pipeline.
- **Verify:** `grep -c '<svg' site/index.html` is `>= 1`; `grep -c '@keyframes' site/index.html` is `>= 1`; `grep -q 'aria-labelledby="flowCaption"' site/index.html`; `grep -c 'data-i18n="flowCaption"' site/index.html` is `1`; `grep -q 'reduced-motion' site/index.html` and the new selector block is present; the external-request check in `## Verification` prints nothing.

### Task 6.6 — Update the run-directory tree copies

- **Goal:** the reader-facing trees match the normative one.
- **Target files:** `README.md` (tree block), `site/index.html` (`figOut` block).
- **Steps:**
  1. Confirm phase 5 already added `trace.jsonl` and restored the missing `decisions.jsonl`, `calibration.json` **and `graph.json`** lines to both copies; if either copy still differs from `output-layout.md`, fix it here and record that it was fixed.
  2. Do **not** add the benchmark cache to either tree: it lives outside the run directory.
- **Success criteria:** the phase-5 tree-parity check prints `tree parity ok`.
- **Verify:** the tree-parity block in `## Verification` prints `tree parity ok`.

### Task 6.7 — Mirror every new key in the `VI` deck

- **Goal:** no English-only section ships.
- **Target files:** `site/index.html` (the `VI` object in the inline script).
- **Steps:**
  1. For every new `data-i18n` attribute added in tasks 6.2, 6.4 and 6.5, add the matching key to the `VI` deck.
  2. Run the i18n check and confirm the key sets match in both directions.
  3. Confirm no key is declared twice.
- **Success criteria:** the key sets match exactly in both directions.
- **Verify:** the i18n block in `## Verification` prints `i18n clean` and equal counts.

### Task 6.8 — Write assertions that can actually fail

- **Goal:** every new landing-page invariant has an assertion that is red before the work and green after.
- **Target files:** none for authoring; the checks live in `## Verification`.
- **Steps:**
  1. Record the baseline before editing: `@keyframes` count `0`, `<svg` count `0`, `prefers-reduced-motion` count `1`, `aria-label` count `2`, `sec-num` spans `8`.
  2. Replace the two pre-satisfied assertions with artifact-specific ones: assert that `@keyframes` **increased** from the recorded baseline, that the SVG carries `aria-labelledby="flowCaption"`, and that a reduced-motion rule names the diagram's own selectors.
  3. Replace the span **count** with a contiguity and uniqueness check: extract the span values, fail on any duplicate, and fail unless the set equals `01..N` for the observed `N`.
  4. Broaden the external-request pattern to cover `href="http`, `url(http`, `srcset=`, `@font-face`, `<iframe`, and `xlink:href`.
  5. Record the baseline and post-change values in the phase notes so a reviewer can see the assertions moved.
- **Success criteria:** the four assertions are artifact-specific, the span check detects a duplicate, and the baseline is recorded.
- **Verify:** the `sec-num`, reduced-motion and external-request checks in `## Verification` all pass, and a deliberately duplicated `sec-num` in a scratch copy makes the span check fail.

## Test matrix (TDD)

| Assertion | Baseline | Expected after | Control |
|---|---|---|---|
| `grep -c 'npx skills add bestagentkits/orchestrate' README.md` | `0` | `>= 1` | removing the line prints `0` |
| `grep -c 'Claude Code Skill' site/index.html` | `2` | `0` | re-adding the kicker prints `>= 1` |
| `grep -c '@keyframes' site/index.html` | `0` | `>= 1` | removing the animation prints `0` |
| `grep -c '<svg' site/index.html` | `0` | `>= 1` | — |
| `grep -q 'aria-labelledby="flowCaption"' site/index.html` | absent | match | removing the attribute fails it |
| A reduced-motion rule naming `.flow` selectors | absent | present | deleting the block fails it |
| `sec-num` contiguity and uniqueness | `1..8` | `1..9` | duplicating a value fails it |
| External-request pattern (broadened) | `0` | `0` | adding `<link href="https://…">` prints a hit |
| Four capability keys in markup and both decks | absent | present | dropping one deck entry prints `I18N FAIL` |
| R0–R3 parity on README and site | passes | passes | dropping a clause prints `PARITY FAIL` |
| Tree parity across the three copies | drifted | equal | removing a line from a copy fails it |
| Peer reachability of every `references/*.md` | passes | passes | removing a peer link (not the index row) prints it |

Note on the two rows whose baseline already passes: the R0–R3 parity and peer
reachability checks are carried-over invariants, not new work, and they are stated
as such. The four rows with a changing baseline are this phase's real tests.

## Failure Protocol

If any Verify step does not meet its stated pass condition, STOP this phase.
Do not improvise a fix, retry blindly, or reason around the failure.
Spawn the `kongming` subagent for next-step counsel and pass:
- the phase and task id,
- what you attempted (the steps you ran),
- the exact command and its full output,
- the pass condition it failed to meet.
Apply kongming's guidance, then re-run the Verify step.
If `kongming` cannot be spawned in this environment, STOP and report the same
failure evidence to the user. Never continue by self-reasoning.

## Verification

```bash
S=plugins/orchestrate/skills/orchestrate/references
grep -c 'npx skills add bestagentkits/orchestrate' README.md
grep -q 'harness-portability.md' README.md && echo "readme portability linked"
grep -c 'As a plain skill' README.md
grep -c 'Benchmark-ranked routing\|Promotion and fail-safe\|Trace and logs\|Credentials' README.md
grep -c 'Claude Code Skill' site/index.html
echo -n "keyframes (baseline was 0): "; grep -c '@keyframes' site/index.html
echo -n "svg (baseline was 0): "; grep -c '<svg' site/index.html
grep -q 'aria-labelledby="flowCaption"' site/index.html && echo "diagram accessible name wired"
grep -q 'prefers-reduced-motion' site/index.html && echo "reduced-motion rule present"
grep -n '\.flow[^{]*{' site/index.html | head
grep -c 'data-i18n="cap' site/index.html

# External-request check, broadened beyond the original three patterns.
grep -nE '<img[^>]+src="https?:|<link[^>]+href="https?:|url\(https?:|srcset=|@font-face|<iframe|xlink:href="https?:' site/index.html \
  || echo "no external request"

# sec-num contiguity and uniqueness.
python3 - <<'PY'
import re, pathlib
s = pathlib.Path("site/index.html").read_text(encoding="utf-8")
vals = re.findall(r'class="sec-num">([^<]+)<', s)
nums = [v.strip() for v in vals]
print("sec-num:", nums)
dups = sorted({n for n in nums if nums.count(n) > 1})
if dups: print("SEC-NUM DUPLICATE:", dups)
expected = ["%02d" % i for i in range(1, len(nums) + 1)]
if nums != expected: print("SEC-NUM NOT CONTIGUOUS, expected:", expected)
if not dups and nums == expected: print("sec-num ok")
PY

# i18n both ways.
python3 - <<'PY'
import re, pathlib
s = pathlib.Path("site/index.html").read_text(encoding="utf-8")
html = set(re.findall(r'data-i18n="([^"]+)"', s))
block = s.split("var VI = {",1)[1].split("\n  };",1)[0]
vi = set(re.findall(r'([A-Za-z0-9_]+)\s*:', re.sub(r'"(?:[^"\\]|\\.)*"', '""', block)))
print("HTML:", len(html), "VI:", len(vi))
if html - vi: print("I18N FAIL missing VI:", sorted(html - vi))
if vi - html: print("I18N FAIL orphan VI:", sorted(vi - html))
if not (html - vi) and not (vi - html): print("i18n clean")
PY

# Tree parity: the normative run-directory file list vs the two published copies.
# An explicit list, not a fence-anchored regex: the README copy is introduced by
# "plans/reports/orchestrate-<timestamp>/" and the landing page copy is HTML with
# tree-drawing prefixes, so a fence anchor extracts nothing from either.
python3 - <<'PY'
import pathlib
NORM = ["jobs.yaml", "state.json", "metrics.jsonl", "runtimes.json",
        "decisions.jsonl", "calibration.json", "report.md", "result.md",
        "graph.json", "events.jsonl", "trace.jsonl"]
bad = False
for name in ("README.md", "site/index.html"):
    s = pathlib.Path(name).read_text(encoding="utf-8")
    missing = [f for f in NORM if f not in s]
    bad = bad or bool(missing)
    print(f"TREE DRIFT {name} missing: {missing}" if missing else f"tree {name} complete")
print("TREE PARITY FAILED" if bad else "tree parity ok")
PY

# Carried-over parity and peer reachability.
check() { grep -qF "$2" "$1" || echo "PARITY FAIL $1 missing: $2"; }
for f in README.md site/index.html; do
  check "$f" "no unnecessary write or shell grant"
  check "$f" "no permission bypass"
  check "$f" "explicit checks and arbiter review"
  check "$f" "strongest verified controls"
done
for f in $S/*.md plugins/orchestrate/skills/orchestrate/runtimes/*.md; do
  b=$(basename "$f")
  peers=$(grep -rlE "\]\([^)]*/?$b\)" --include='*.md' --exclude="$b" \
    plugins/orchestrate/skills/orchestrate README.md | grep -v '/SKILL.md$' | wc -l)
  [ "$peers" -ge 1 ] || echo "UNREACHABLE-BY-PEER $b"
done
```

Expected: counts as specified; `0` for the kicker; `keyframes >= 1`; `svg >= 1`;
`diagram accessible name wired`; `reduced-motion rule present`; at least one
`.flow` selector printed; `no external request`; `sec-num ok`; `i18n clean`;
`tree parity ok`; nothing from the parity helper; and nothing from the
peer-reachability loop.
