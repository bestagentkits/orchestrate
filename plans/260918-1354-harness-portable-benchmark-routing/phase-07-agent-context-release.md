---
phase: 7
title: "Agent context and release"
status: pending
priority: P1
effort: "0.75d"
dependencies: [6]
---

# Phase 7: Agent context and release

## Goal

The repository has an agent-context file describing its invariants, the version is
`2.2.0` on every surface **including the maintenance sweep's own version literals**, and
the whole-tree sweep passes with a control for every assertion.

## Files to Create / Modify

- Create: `AGENTS.md` (agent context; `/ak-docs agent-context`) and `CLAUDE.md` (a one-line pointer to `AGENTS.md`, for the harness that reads that name).
- Modify: `plugins/orchestrate/.claude-plugin/plugin.json` (version)
- Modify: `plugins/orchestrate/skills/orchestrate/SKILL.md` (version — at `metadata.version`, **not** a top-level key)
- Modify: `site/index.html` (three version occurrences: English byline, spec table, Vietnamese byline)
- Modify: `README.md` (the `2.1.0 → 2.2.0` upgrade section, the maintenance sweep's **version literals and new steps**)
- Modify: `plans/260918-1354-harness-portable-benchmark-routing/plan.md` (the real issue number)

## Facts this phase must respect, verified by grep

- The version lives at `SKILL.md:12` as a **nested** key under `metadata:` (lines 10–12). There is no top-level `version:` key. Writing one would produce two version fields and make the count assertion return `2`.
- The repository's only verification mechanism hard-codes the current version by **exact count**: `README.md:374-377` asserts `2.1.0` appears once in `plugin.json`, once in `SKILL.md` and three times in `site/index.html`. Those three lines are what this phase must update; a release that bumps the surfaces without updating them prints three `FAIL` lines and stops under the Failure Protocol.
- `README.md:282` is the historical `### From 2.0.0 to 2.1.0` heading. It stays, which is why the stale-version grep excludes `README.md`.
- The sweep currently has **8** numbered steps (`grep -c '^# [0-9]' README.md`).
- `AGENTS.md` and `CLAUDE.md` are both absent, so `agent-context` creates rather than refreshes. The primary file must be `AGENTS.md`: a release whose whole thesis is harness portability cannot answer "an agent-context file" with a file named after a single harness while phase 1 asserts that no shipped surface brands itself for one. `CLAUDE.md` is created alongside as a pointer, not as a second context file, so there is exactly one owner of the content.

## Tasks & Steps

### Task 7.1 — Author the agent context with `/ak-docs agent-context`

- **Goal:** an agent opening this repository learns its invariants before editing.
- **Target files:** `AGENTS.md` (create), `CLAUDE.md` (create, pointer only).
- **Steps:**
  1. Run the `ak-docs` skill in `agent-context` mode. Confirm the command reports **creation**, since the file does not exist.
  2. Confirm the generated file covers: that the repository ships no code and no CI other than the Pages workflow; that `references/` plus `runtimes/` are authoritative while `README.md` and `site/index.html` are parity-checked summaries; that no benchmark value, model name, flag or leaderboard row may be copied into the skill; that the accept predicate has exactly one owner; that credential values are never printed, prompted for or committed; that owner-fixed constants are pinned in their owning document and fanned out to `job-spec.md` validation and the README; and that the maintenance sweep in `README.md` is the verification mechanism.
  3. Do not restructure generated output. If a required fact is missing, add it as a bullet in the existing section structure rather than adding a new top-level section.
- **Success criteria:** `AGENTS.md` exists and names the authoritative set, the no-copied-catalog rule, the constant fan-out rule and the sweep; `CLAUDE.md` contains a pointer to it and no duplicated content.
- **Verify:** `test -f AGENTS.md` exits `0`; `grep -c 'references/' AGENTS.md` is `>= 1`; `grep -q 'sweep' AGENTS.md` matches; `grep -qi 'copied' AGENTS.md` matches; `grep -q 'AGENTS.md' CLAUDE.md` matches; and `wc -l < CLAUDE.md` is `<= 5`, which is what keeps the pointer from becoming a second copy.

### Task 7.2 — Bump the version to 2.2.0 on every surface, including the sweep

- **Goal:** one version everywhere, the sweep's own literals updated, and the upgrade section explains why it is minor.
- **Target files:** `plugins/orchestrate/.claude-plugin/plugin.json`, `plugins/orchestrate/skills/orchestrate/SKILL.md`, `site/index.html`, `README.md` (upgrade section **and** the sweep's version step).
- **Steps:**
  1. Set `"version": "2.2.0"` in `plugin.json`.
  2. Set the value at **`metadata.version`** in `SKILL.md` — the key at `SKILL.md:12` under the existing `metadata:` mapping. Do **not** add a top-level `version:` key, and leave `metadata.author` untouched.
  3. Replace all three `2.1.0` occurrences in `site/index.html` — the English byline, the spec-table value and the Vietnamese byline — with `2.2.0`.
  4. **Update the sweep's version assertions in the same edit.** In the README's maintenance sweep step 3, replace the three `2\.1\.0` literals with `2\.2\.0` and keep the expected counts at `1`, `1` and `3`. State in the phase notes that this is a version literal update, not a weakening of the assertion, and that the counts are unchanged because the number of surfaces is unchanged.
  5. Add a `### From 2.1.0 to 2.2.0` section above the `2.0.0` section. State that it is additive: no file is removed and no path changes; four new references are added; `.gitignore` gains dotenv and cache rules; and the visible behaviour changes are that the skill installs through the `npx skills` CLI, routing ranks with benchmark evidence cached between runs, infrastructure failures promote within a bounded budget, credentials resolve from four documented locations through the child environment, and the trace gains span identifiers. State the two negative rules explicitly: benchmark evidence **cannot** change eligibility, a floor, a tier, a control or an approval, and a **failed check never promotes**.
  6. List the four new reference paths in the upgrade section, and list the two new owner-fixed constant families (cache TTL and promotion budget) with their values, so an existing reader learns both the new files and the new bounds.
- **Success criteria:** the version is `2.2.0` on all three surfaces; the sweep asserts `2.2.0` with counts `1/1/3`; no `2.1.0` remains outside the README history; the upgrade section states both negative rules and both constant families.
- **Verify:** the version block in `## Verification` prints `1`, `1`, `3`, `version clean`; `grep -c '2\\.2\\.0' README.md` is `>= 4` (upgrade heading, upgrade body, three sweep literals); `grep -q 'failed check never promotes' README.md`.

### Task 7.3 — Extend the maintenance sweep

- **Goal:** the sweep covers the new invariants without weakening any existing one.
- **Target files:** `README.md` (the `## Maintaining the docs` sweep block).
- **Steps:**
  1. Add a step asserting the four new reference files exist, and that each is reachable from a **peer** document rather than only from `SKILL.md`'s index row. State why the peer requirement exists: the index row alone survives a broken cross-reference, which is what the earlier control for this check got wrong.
  2. Add a step asserting the portability invariant: no `context: fork`, no `hooks:` and no `allowed-tools:` in the payload **excluding the portability document that is required to name them**, and the `npx skills add` command present on the reference, the README and the site.
  3. Add a step asserting the two negative safety rules: benchmark evidence may not set eligibility, a floor, a tier, a control or an approval, and a failed check is not a promotion trigger. Locate both by `grep` on the owning files.
  4. Add a step asserting the credential invariants: the four resolution paths appear in `decision-plane.md` in order and nowhere else; no document instructs printing or passing the key on a command line; `.env` is git-ignored and no dotenv file is tracked.
  5. Add a step asserting the trace invariant: the span identifiers appear in the new document **and in their owners** (`event-protocol.md`, `decision-plane.md`), and `output-layout.md` lists `trace.jsonl` and defines the report's completeness field.
  6. Add a step asserting the landing-page invariants that can actually fail: inline `<svg>` present, `@keyframes` present, the SVG's accessible name wired through `aria-labelledby`, a reduced-motion rule naming the diagram's own selectors, no external request under a broadened pattern, and a contiguous unique `sec-num` sequence.
  7. Add a step asserting the owner-fixed constants are fanned out: each constant value appears in its owner, in `job-spec.md` validation and in the README.
  8. Add a step asserting that neither `README.md` nor `site/index.html` still contains `Claude Code Skill`.
  9. Renumber the existing steps so the sequence stays ordered, and keep every existing assertion — boundary, parity, i18n, version, stubs — unchanged in substance except the version literals updated in task 7.2 step 4.
  10. Extend the sweep's preamble with the honesty note: state that the "no copied measurement" rule is a review item a grep cannot enforce, and that a grep proves a token exists rather than that a rule holds, so a green sweep is not proof that no benchmark value was pasted.
- **Success criteria:** the sweep contains the new steps, every prior step survives, the honesty note is present, and the step count increased by the number of steps added.
- **Verify:** `grep -c '^# [0-9]' README.md` is greater than the recorded baseline of `8`; `grep -q 'no copied measurement' README.md`; `grep -q 'Accept without a C3 call' README.md` still matches.

### Task 7.4 — Run the whole-tree sweep with controls

- **Goal:** every assertion passes, and every assertion can fail.
- **Target files:** none (commands only).
- **Steps:**
  1. Run every numbered step of the README sweep in order.
  2. For each **new** assertion, run its control and confirm the predicted failure appears. At minimum: duplicate a `sec-num` in a scratch copy (span check must fail); add a remote `<link>` to a scratch copy (external-request check must fail); stage a scratch `.env` (tracked-dotenv check must fail); remove the ignore rule in a scratch copy (`git check-ignore` must fail); add `allowed-tools:` to a scratch `SKILL.md` (portability check must fail).
  3. Do not run any control inside the real repository; use a scratch copy under `/tmp` and delete it afterwards.
  4. Record each step's result, including the steps that print nothing, in the phase notes.
  5. Add the real tracking issue number to `plan.md` frontmatter as `issue: <n>`.
- **Success criteria:** all steps pass; every new control demonstrates a detectable failure; the plan frontmatter carries the issue number.
- **Verify:** the sweep prints only its expected success lines, every control prints the failure it predicts, and `grep -q '^issue: [0-9]' plans/260918-1354-harness-portable-benchmark-routing/plan.md` matches.

## Test matrix (TDD)

| Assertion | Expected | Control |
|---|---|---|
| `test -f AGENTS.md` | exit 0 | deleting it exits 1 |
| `wc -l < CLAUDE.md` | `<= 5` | growing it into a second context file fails |
| `grep -c '2\.2\.0' plugins/orchestrate/.claude-plugin/plugin.json` | `1` | — |
| `grep -c '2\.2\.0' plugins/orchestrate/skills/orchestrate/SKILL.md` | `1` | adding a top-level `version:` prints `2` |
| `grep -c '2\.2\.0' site/index.html` | `3` | — |
| `grep -n '2\.2\.0' README.md \| grep -c 'test '` | `3` (the three sweep literals) | leaving them at `2.1.0` prints `0` and the sweep fails |
| `grep -rn '2\.1\.0' plugins site .claude-plugin` | nothing | leaving one byline prints a hit |
| `grep -q 'no copied measurement' README.md` | match | — |
| `grep -c '^# [0-9]' README.md` | `> 8` | — |
| Every README sweep step | passes | each step's own control |
| `grep -q '^issue: [0-9]' plans/260918-1354-*/plan.md` | match | — |
| `ak plan validate plans/260918-1354-*` | valid | — |

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
test -f AGENTS.md && echo "agent context present" || echo "MISSING AGENTS.md"
grep -c 'references/' AGENTS.md
grep -q 'sweep' AGENTS.md && echo "sweep referenced"
grep -qi 'copied' AGENTS.md && echo "no-copied-catalog rule present"
grep -q 'AGENTS.md' CLAUDE.md && echo "pointer present"
echo -n "CLAUDE.md lines (must be <= 5): "; wc -l < CLAUDE.md

# Version surfaces, including the sweep's own literals.
test "$(grep -c '2\.2\.0' plugins/orchestrate/.claude-plugin/plugin.json)" = 1 || echo "FAIL plugin.json"
test "$(grep -c '2\.2\.0' plugins/orchestrate/skills/orchestrate/SKILL.md)" = 1 || echo "FAIL SKILL.md"
test "$(grep -c '2\.2\.0' site/index.html)" = 3 || echo "FAIL site"
echo -n "sweep version literals (must be 3): "
grep -n "2\\\\.2\\\\.0" README.md | grep -c 'test '
grep -rn '2\.1\.0' plugins site .claude-plugin --include='*.json' --include='*.md' --include='*.html' \
  && echo "FAIL stale version" || echo "version clean"

# New owners and their invariants.
for f in harness-portability benchmark-evidence fallback-policy trace-and-logging; do
  test -f "$S/$f.md" || echo "MISSING $f.md"
done
grep -rn 'context: fork\|^hooks:\|^allowed-tools:' plugins/orchestrate/skills/orchestrate \
  | grep -v harness-portability.md || echo "portability clean"
grep -q 'may not set or change eligibility' "$S/benchmark-evidence.md" && echo "benchmark negative rule present"
grep -q 'authorization or permission failure never promotes' "$S/fallback-policy.md" && echo "promotion exclusion present"
grep -c 'TYPESAFE_API_KEY' "$S/decision-plane.md"
grep -q 'inherited child environment' "$S/decision-plane.md" && echo "credential delivery rule present"
git ls-files | grep -c '\(^\|/\)\.env$'
git check-ignore -q .orchestrate/benchmarks.json && echo "cache ignored"
grep -c 'spanId' "$S/event-protocol.md" "$S/decision-plane.md"
grep -q 'trace.jsonl' "$S/output-layout.md" && echo "trace artifact listed"
grep -q 'traceStatus' "$S/output-layout.md" && echo "completeness field defined"

# Owner-fixed constants fan-out. Before running this block, confirm every constant
# THIS release introduces appears in its owner document, in `job-spec.md`'s
# `defaults:` block where it is a job input, and in the README knob list; add any
# missing reference here, because this is the phase that owns the release sweep.
#
# `MINIMUM_SAMPLES` is deliberately NOT in the loop. It is carried over from 2.1.0.
for c in CACHE_TTL_DEFAULT_HOURS CACHE_TTL_MAX_HOURS MAX_PROMOTIONS_DEFAULT MAX_PROMOTIONS_MAX EFFORT_LEVELS_MAX_PER_CANDIDATE; do
  printf '%-34s owner=%s jobspec=%s readme=%s\n' "$c" \
    "$(grep -rl "$c" "$S" | wc -l)" \
    "$(grep -c "$c" "$S/job-spec.md")" \
    "$(grep -c "$c" README.md)"
done
# Carried-over 2.1.0 constant: assert its real shape, not an invented fan-out.
# It is owned by verification.md, referenced from job-spec.md as the lowercase
# field `calibration.minimum_samples`, and never named in the README -- so a loop
# demanding `readme >= 1` for it would fail on contact and stall the release.
echo -n "MINIMUM_SAMPLES owner file(s): "; grep -rl 'MINIMUM_SAMPLES' "$S" | tr '\n' ' '; echo
echo -n "job-spec lowercase minimum_samples count: "; grep -c 'minimum_samples' "$S/job-spec.md"

# Kicker and carried-over invariants.
grep -n 'Claude Code Skill' README.md site/index.html || echo "no claude-only branding"
grep -rln 'Accept without a C3 call' "$S"
grep -q 'no copied measurement' README.md && echo "honesty note present"
echo -n "sweep steps: "; grep -c '^# [0-9]' README.md

ak plan validate plans/260918-1354-harness-portable-benchmark-routing 2>&1 | tail -3
```

Expected: `agent context present`; a `references/` count `>= 1`; `sweep referenced`;
`no-copied-catalog rule present`; no `FAIL` line from the version checks; `3` for
the sweep literals; `version clean`; no `MISSING`; `portability clean`; both rule
lines; counts `>= 1`; `credential delivery rule present`; `0` tracked dotenv files;
`cache ignored`; span counts `>= 1` in both owners; `trace artifact listed`;
`completeness field defined`; a fan-out line per constant with `owner >= 2` and
nonzero `jobspec` and `readme`; `no claude-only branding`; the boundary grep
printing exactly `.../verification.md`; `honesty note present`; a sweep-step count
greater than `8`; and a valid plan.
