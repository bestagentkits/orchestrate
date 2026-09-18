---
phase: 2
title: "Jev reader surfaces"
status: completed
priority: P1
effort: "0.25d"
dependencies: []
---

# Phase 2: Jev reader surfaces

## Goal

Both reader surfaces state what Jev (TypeSafe) is, why a System-1 model is the right
shape for the decision plane's six tasks, and where its provider key is read from —
with Jev described as the reference and optional implementation throughout, and with
no vendor measurement reproduced.

## Files to Create / Modify

- Modify: `README.md` (a new `### Jev (TypeSafe), the reference System-1 model`
  subsection under Routing; the `### Credentials` section)
- Modify: `site/index.html` (a sub-block inside the decision-plane section, one
  stylesheet rule, and the matching `VI` copy-deck entries)

## Facts this phase must respect, verified by grep

- The owning documents that must not be contradicted:
  `decision-plane.md:74` — Jev "is named here as the design this contract was written
  against, and as one optional provider … It is never required. No step in
  `/orchestrate` may depend on it being present, installed, or reachable."
  `decision-plane.md:92` — "The variable name is `TYPESAFE_API_KEY`."
  `decision-plane.md:96-107` — the four locations, in order, plus the rule that only
  the key is read from a dotenv.
  `SKILL.md:310-315` — the plane "prefers a `role: classifier` candidate already in
  `runtimes.json`"; Jev is "the reference implementation and one optional provider —
  never a requirement."
- **The read order has exactly one owner.** Sweep step 12 asserts
  `grep -rl 'process\.env' $S | wc -l` is `1` (i.e. only `decision-plane.md`), and
  `README.md` already declares its Credentials section a "parity-checked summary".
  The new Jev prose therefore must not list the four locations a second time inside
  README; it names the variable and points at the owner. `site/index.html:684`
  (`capCredB`) already says "four documented locations in a fixed order" without
  enumerating them — a sub-block that enumerates them would be the page's second
  statement.
- **The accept predicate has one owner** (`verification.md`, sweep step 5). The Jev
  prose must not restate the conditions under which an attempt is accepted without a
  C3 call.
- **The landing page's numbering is gated.** Sweep step 14 asserts the `sec-num`
  sequence is exactly `01 02 03 04 05 06 07 08 09 10`, so the sub-block must not
  introduce a `sec-num`. The decision-plane section is `site/index.html:658` and is
  the topic's owner; the routing section is `:629`.
- **The no-external-request gate is a subresource pattern.** Sweep step 14 greps for
  `<img src="https:`, `<link href="https:`, `<script src="https:`, `url(https:`,
  `@import … https:`, `fetch(`, `srcset=`, `@font-face`, `<iframe`, `poster="https:`
  and `xlink:href="https:`. An `<a href="https://…">` is therefore safe; a stylesheet
  `url(https:)` or any `fetch(` is not.
- **Copy-deck parity.** Sweep step 8 requires every `data-i18n` key to have a
  matching `VI` entry, and the EN deck is derived from the DOM at load
  (`site/index.html:1419-1420`), so the English copy lives in the markup.
- **Parity literals.** Sweep step 6 requires both `README.md` and `site/index.html`
  to contain "no unnecessary write or shell grant", "no permission bypass",
  "explicit checks and arbiter review" and "strongest verified controls". The
  `r0`–`r3` entries carry these on the site and the risk-tier table carries them in
  README; neither may be reworded.
- **Version counts.** Sweep step 3 requires `grep -c '2\.2\.0' site/index.html` to
  stay `3`, so no version literal may be added to the page.

## Tasks & Steps

### Task 2.1 — README: the Jev subsection

- **Goal:** a reader learns what Jev is and why the plane's tasks can consume it.
- **Target file:** `README.md`, immediately after `### The System-1 decision plane
  (optional)` (which ends at `:105`) and before `### Benchmark-ranked routing`.
- **Steps:**
  1. Open with what Jev is: TypeSafe's System One model, the design the plane's
     contract was written against, and one optional provider behind it — never a
     requirement, never the only way to run the plane.
  2. State the three properties in the contract's own vocabulary: a decision comes
     back as a value from a pre-declared set (so no free text has to be repaired into
     a policy field); every answer carries its own probability (which is what lets a
     floor be *raised* and a weak signal be discarded); and a choice arrives with the
     runner-up probabilities beside it, so low confidence is expressible rather than
     forced into a confident wrong answer.
  3. Name the six tasks the plane runs — trace watchdog, failure triage, semantic
     router, micro-arbiter, profiler classification, graph relation — and say which
     kind of signal each consumes, linking `decision-plane.md` rather than restating
     its schema.
  4. Restate the boundary in one clause: a Jev verdict is scored evidence for a
     deterministic predicate, and never an acceptance, a tier or a control.
  5. Link TypeSafe once, e.g. `[TypeSafe](https://typesafe.ai)`, as the vendor
     material's location rather than a reproduction of it.
- **Success criteria:** no measurement, model ID, price or version appears; Jev is
  described as optional in the same paragraph that names it as the reference; no
  accept-predicate restatement.
- **Verify:** change-manifest items 7, 10 and 14; sweep steps 5, 6 and 12.

### Task 2.2 — README: name the variable and the egress precondition

- **Goal:** "how to configure the Jev API key" is answerable from README without
  restating the owner's order and without documenting a key export.
- **Target file:** `README.md`, `### Credentials`.
- **Steps:**
  1. Name the variable: for the reference provider it is `TYPESAFE_API_KEY`.
  2. Say where the *key* comes from: it is created in TypeSafe's own console, not
     generated, echoed or derived by this repository — and `.env.example` ships the
     name with no value, so the template can be committed while a real key cannot.
  3. Keep the existing prose order sentence as the single README statement of the
     order and point at `decision-plane.md` as its owner (already the case).
  4. Add the precondition a key alone does not satisfy: a call also needs a recorded
     **egress authorization** naming the provider and the credential source, because
     sending state to a provider is an external side effect; with no key **or** no
     such authorization the plane is disabled for the run, never silently re-routed.
  5. Do **not** add an `export`, a `--api-key` flag, a curl example, a request shape
     or an endpoint. A documented direct call would also contradict the contract's
     "no bespoke provider client".
- **Success criteria:** `TYPESAFE_API_KEY` appears in README; the order list still
  appears exactly once in README and once in its owner; no forbidden pattern matches.
- **Verify:** change-manifest items 7, 8 and 9; sweep step 12.

### Task 2.3 — Landing page: the sub-block and its copy deck

- **Goal:** the page carries the same story, in both decks, without touching a
  verified gate.
- **Target file:** `site/index.html`.
- **Steps:**
  1. Add one stylesheet rule for the sub-block rhythm (a single margin utility is
     enough; do not introduce a new colour, family or size).
  2. Insert the sub-block after the last paragraph of the decision-plane section
     (`planeAdapters`, around `:693`) and before that section's `</div>`. Reuse the
     existing `.two-col` / `.tier-card` / `.tier` vocabulary so it reads as part of
     the page: one card for what Jev is and why the tasks consume it, one for how the
     key is configured.
  3. Give **every** new element a `data-i18n` key, and give the English copy in the
     markup.
  4. Add the matching Vietnamese entries to the `VI` object (`:1284`), matching the
     surrounding voice and keeping `<code>`, `<b>` and `<a>` markup valid.
  5. Keep any external reference as `<a href>`; add no subresource, no `fetch(` and no
     `url(https:)`.
  6. Do not add a `sec-num`, do not renumber anything, and do not introduce a version
     literal.
- **Success criteria:** sweep steps 6, 8 and 14 are green; the `sec-num` sequence is
  unchanged; the new section renders in both decks.
- **Verify:** the sweep, plus the visual check in phase 3.

## Verification

```bash
# From the repository root.
S=plugins/orchestrate/skills/orchestrate/references
grep -c 'TYPESAFE_API_KEY' README.md                       # >= 1
grep -c 'TYPESAFE_API_KEY' site/index.html                 # >= 1
test "$(grep -rl 'process\.env' "$S" | wc -l)" = 1         # order still single-owner
grep -rnE 'export .*TYPESAFE|--[a-z-]*key[= ]|cat .*[.]env|echo .*TYPESAFE' \
  README.md site AGENTS.md docs                            # must print nothing
grep -rniE 'MTok|per million|\$[0-9]|193\.6|444\.6|jev-latest|jev-preview|jev-[0-9]|x faster|x cheaper' \
  README.md site/index.html docs                            # must print nothing
```

### Baseline table (measured before this phase's edits)

| Check | Baseline | Target | Mutation that must trip it |
| --- | --- | --- | --- |
| `grep -c 'TYPESAFE_API_KEY' README.md` | 0 | ≥1 | reverting the Credentials edit |
| `grep -c 'TYPESAFE_API_KEY' site/index.html` | 0 | ≥1 | reverting the sub-block |
| `grep -rl 'process\.env' $S \| wc -l` | 1 | 1 | copying the order into README |
| Forbidden key-documentation pattern | none | none | adding an `export …TYPESAFE…` line |
| Vendor-figure pattern | none | none | pasting a price or a model ID |
| Sweep steps 6, 8, 14 | green | green | removing a `data-i18n` VI entry |

## Failure Protocol

If a verified gate fails after the copy edit, fix the copy rather than the gate. The
only admissible reason to touch the sweep is the relocation in phase 1; a wording
change that requires editing a grep is the failure mode `AGENTS.md` calls a gate that
"looks like a failing rule".
