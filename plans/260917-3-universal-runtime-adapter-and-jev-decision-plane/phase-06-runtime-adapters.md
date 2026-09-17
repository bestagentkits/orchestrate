---
phase: 6
title: "Runtime adapters"
status: pending
priority: P1
effort: 9h
dependencies: [1]
---

# Phase 6: Runtime adapters

## Goal

Give the adapter contract somewhere to land. Move Pi out of core into an adapter
note, move Pi onboarding with it, and add one capability-map note per named
runtime. Notes are capability maps and verification checklists, never a command
or model catalog, and a note that no live probe has touched is explicitly
unverified.

## Files to Create / Modify

- Create: `runtimes/README.md`
- Create: `runtimes/pi.md` (from `references/pi-sessions.md`)
- Create: `runtimes/pi-onboarding.md` (from `references/pi-onboarding.md`)
- Create: `runtimes/omp.md`, `runtimes/agy.md`, `runtimes/grok.md` (existing probe targets)
- Create: `runtimes/claude.md`, `runtimes/codex.md`, `runtimes/gemini.md`, `runtimes/opencode.md`, `runtimes/aider.md` (unverified scaffolding)
- Modify: `references/internal-routing.md` (reframe as the internal adapter note)
- Modify: `references/runtime-profile.md` (link the adapter index)

Note: this phase **creates** the adapter notes. It does **not** delete
`references/pi-sessions.md` or `references/pi-onboarding.md`; phase 7 owns every
deletion. The originals stay until `runtimes/pi.md` and
`runtimes/pi-onboarding.md` are complete and relinked.

## Tasks & Steps

1. Write `runtimes/README.md`: the adapter-authoring procedure (implement the
   contract, run the deterministic probe, run conformance checks, record the
   profile, verify the smoke test) plus the rule that this directory is a set of
   capability maps, **not** a support roster and **not** a command catalog.
   Include the note template so every file is uniform, and carry the `pi`,
   `omp`, `agy` and `grok` probe targets forward from the file phase 7 deletes,
   including the existing `agy` probe focus and upstream reference so that
   documented target is not lost.
2. Use one uniform note template per runtime:
   - **Identity and probe focus** — how to tell this product from a same-named binary.
   - **Expected adapter capabilities** — which contract capabilities are expected, each phrased as a probe to run.
   - **Verification steps** — the exact live checks to run before routing.
   - **Capture tier** — preferred structured surface and its fallback.
   - **Known failure signatures** — symptom → probe again / onboard / block.
   - **Risk posture defaults** — approval and isolation expectations **to verify, not to trust**.
   - **Independence caveat** — different executable names do not prove a
     different model family, so this runtime is not independent review by
     executable name alone.
3. Move the Pi session and dispatch contract into `runtimes/pi.md` and the
   install/profile/authenticate contract into `runtimes/pi-onboarding.md`,
   preserving every verified procedure and the "verify flags against live help"
   caveat. Fold the header links that pointed at `runtime-matrix.md`,
   `harness-profiles.md` and `model-routing.md` into the new owners from phase 2,
   so the moved files do not arrive with dead links.
4. Rewrite `internal-routing.md` as the in-session adapter note: it implements
   the same contract for the native subagent mechanism, with its capture mapping,
   accounting-only timeout limits, and the `model-routing.md` §Internal Branch
   content phase 2 moved there.
5. Write the eight non-Pi notes. `omp`, `agy` and `grok` are existing documented
   probe targets. `claude`, `codex`, `gemini`, `opencode` and `aider` are named
   by the accepted brainstorm but appear nowhere in this repository, so each is
   written as a **fenced unverified stub**: a one-page stub pointing at the
   contract, carrying a leading `unverified — not a support claim, not in
   inventory` banner, an explicit "no live probe recorded" statement with an
   as-of date, and no capability asserted as available. A stub graduates to a
   full note only when a real run records a probe in `runtimes.json`.
6. Make the **index placement distinguish verified from unverified** in
   `runtimes/README.md`: verified adapters list first, unverified stubs sit under
   a clearly separated heading, and the README states that an unverified adapter
   is selectable only after a live-inventory probe confirms it. A doc note can
   never cause a dispatch, because the live inventory is what gates routing — say
   that plainly, so the directory cannot be read as a support roster.
7. Enforce the no-catalog rule as a **content** rule in the template, not a
   prefix regex. The earlier draft's regex (`^ *(pi|omp|...) +--[a-z]`) failed in
   both directions: it matched the `pi --version` probe line the Pi onboarding
   note legitimately preserves, while missing `env PI_OFFLINE=1 pi …` templates
   and `npm install -g …` lines. The rule is: a note may name a probe *command
   to run*, and must not contain a dispatch invocation template, a resolved
   model identifier, or a positive control claim.
8. Add the reachability constraint note: because every `runtimes/*.md` file must
   be linked, an unverified stub must be linked as "unverified — not in
   inventory" — the link must not advertise a support roster.

## Verification

```bash
S=plugins/orchestrate/skills/orchestrate
ls $S/runtimes
# no dispatch invocation templates or resolved model ids in any note
grep -rnE '(^|[[:space:]])env [A-Z_]+=.* (pi|omp|agy|grok|codex|claude|gemini|opencode|aider) ' $S/runtimes && echo "FAIL: invocation template" || echo "no invocation templates"
grep -rn 'gpt-|claude-[0-9]|gemini-[0-9]|o[0-9]-' $S/runtimes && echo "FAIL: model id" || echo "no resolved model ids"
# every note carries the template headings
for f in $S/runtimes/*.md; do grep -q 'Expected adapter capabilities' "$f" || echo "MISSING template: $f"; done
# unverified scaffolding is labelled, not advertised
grep -rn 'unverified' $S/runtimes/*.md | wc -l
# the agy target survived the move
grep -rn 'agy\|Antigravity' $S/runtimes/README.md $S/runtimes/agy.md | head
```

- [x] No file under `runtimes/` contains a dispatch invocation template or a resolved model id.
- [x] Every note uses the shared template headings and carries the independence caveat.
- [x] The `agy` probe target and its focus survived from the deleted file.
- [x] Pi onboarding content is preserved in full, only relocated, with no dead header links.
- [x] Notes for runtimes absent from this repo are labelled unverified scaffolding.
- [x] No file was deleted in this phase.
