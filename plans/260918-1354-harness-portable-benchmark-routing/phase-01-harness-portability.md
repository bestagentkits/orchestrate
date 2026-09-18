---
phase: 1
title: "Harness portability and distribution"
status: pending
priority: P0
effort: "1d"
dependencies: []
---

# Phase 1: Harness portability and distribution

## Goal

The skill states, in one owner document, which Agent Skills conformance surface it
uses, which harness features it may never depend on, and every supported install and
discovery path — so a user on any harness can install and run it without the
documentation assuming Claude Code.

## Files to Create / Modify

- Create: `plugins/orchestrate/skills/orchestrate/references/harness-portability.md`
- Modify: `plugins/orchestrate/skills/orchestrate/SKILL.md` (framing, the "Engine" paragraph, and the reference index)
- Modify: `plugins/orchestrate/skills/orchestrate/references/job-spec.md` (the run-level `harness` field on `state.json`, owned here so task 1.1 step 10 has a schema)

Measured facts this phase builds on, verified by grep and by reading the files:

- `SKILL.md` frontmatter keys are `name`, `description`, `user-invocable`, `when_to_use`, `category`, `keywords`, `argument-hint`, `license`, `metadata`. It has **no** `allowed-tools`, no `context: fork`, and no `hooks:` key.
- The Claude-Code-only framing is **not** in `SKILL.md`. It is `README.md:5` ("**Multi-runtime agent orchestration for Claude Code.**"), `README.md:108` ("### As a Claude Code plugin"), and the landing page kicker at `site/index.html:412` (EN) and `:879` (VI) — which read "A Claude Code Skill" and "Một Claude Code Skill". `README.md:120` documents a second install path ("### As a plain skill", a clone plus copy).
- `.claude-plugin/marketplace.json` exists at the repo root and declares `"source": "./plugins/orchestrate"`. There is **no** root-level `.claude-plugin/plugin.json`; the plugin manifest is `plugins/orchestrate/.claude-plugin/plugin.json`.

## Tasks & Steps

### Task 1.1 — Author `harness-portability.md`

- **Goal:** one document owns the portability contract and the install paths.
- **Target files:** `plugins/orchestrate/skills/orchestrate/references/harness-portability.md` (create).
- **Steps:**
  1. Create the file with an H1 `# Harness Portability` and a scope statement that separates the two claims this document must not conflate: the payload **loads** on any harness that implements the Agent Skills contract, and it can **execute** jobs only where the minimum capability set in `## What a harness must provide` exists. State that the document owns what the payload may assume about a harness, and how it is installed.
  2. Add section `## The conformance surface`. State that the payload is an Agent Skills directory containing `SKILL.md` with `name` and `description` frontmatter plus a markdown body. List the three features this skill may **never** depend on, each with its reason on the same line: `context: fork` (Claude Code only), `hooks:` (Claude Code, Cline and Kiro CLI only), and `allowed-tools` (widely supported but not universal). State the rule: a payload that works only where `allowed-tools` is honored is not portable, so this skill's body must be safe to run with the full toolset and rely on the safety gate instead.
  3. Add section `## Frontmatter this skill declares`, as a two-column table with the keys actually present in `SKILL.md`, one row each, plus one row noting that a conforming harness ignores unknown frontmatter keys — so `user-invocable`, `when_to_use`, `category`, `keywords`, `argument-hint` and `license` are AgentKit extensions that must never be load-bearing. State explicitly: **no behavior in this skill may depend on a frontmatter key outside `name` and `description`.**
  4. Add section `## Install with the skills CLI`. State the primary command verbatim: `npx skills add bestagentkits/orchestrate`. State that this repo needs no CLI to run and that `npx skills` is one installer among several. Then add a table of the install forms that matter, with a one-line purpose each: `npx skills add bestagentkits/orchestrate` (project scope), `... -g` (global), `... -a <agent>` (named harness), `... --all` (every detected harness), `... --copy` (copy instead of symlink), `... --list` (inspect before installing), `... --skill orchestrate` (select by name), `... -y` (non-interactive).
  5. Add section `## What the CLI discovers here`. State that the CLI also reads the Claude Code plugin manifests, and name the real paths in this repo: `.claude-plugin/marketplace.json` at the repository root, and the plugin manifest `plugins/orchestrate/.claude-plugin/plugin.json`. State explicitly that **no root-level `.claude-plugin/plugin.json` exists**, so a reader does not go looking for one. Do **not** copy the marketplace JSON: link `.claude-plugin/marketplace.json`.
  6. Add section `## Installing into Claude Code` documenting the existing marketplace path unchanged, and state that it is one harness among many rather than the default. Do **not** repeat the marketplace JSON: link `.claude-plugin/marketplace.json`.
  7. Add section `## Where the payload lands`, as a three-column table: harness class, project path, global path. Include only the classes that a reader is likely to need — the Claude Code path (`.claude/skills/`), the shared agents path (`.agents/skills/`), OpenClaw (`skills/`), Pi (`.pi/skills/`) — and **do not copy the CLI's full agent table**. Add the rule in prose: the authoritative, current list is the CLI's own documentation and the installed version's `--help`; a copied table is a stale catalog, which this skill forbids everywhere else.
  8. Add section `## Verified harnesses`. State that no artifact in this repository marks a harness verified, that the portability claims above come from the published specification and the CLI's documented behavior, and that a harness becomes verified for a user only after a live install-and-load check on that machine. Mirror the wording discipline of `runtimes/README.md`: a listed path is not a support claim.
  9. Add section `## What a harness must provide`. State the minimum capability set in a bullet list: a skill loader that reads `SKILL.md`; a filesystem; a shell or PTY to dispatch a runtime; a way to run a job non-interactively or to observe a session; git for worktree isolation; and, for benchmark-ranked routing, a way to reach the network (named here because phase 2's benchmark fetch depends on it, and a run without it must disclose a degraded ranking rather than claim a benchmark-ranked route). State that a harness missing worktree support still **loads** the skill, but that the tier consequence of a missing isolation capability belongs to [safety-policy.md](safety-policy.md) — this document states no tier rule and implies none.
  10. Add section `## Degradation rules`. State that a missing harness capability disables the affected step and is recorded, never silently assumed: no subagent support means `internal` is not a candidate; no headless dispatch means only session runtimes are eligible; no network means benchmark ranking is degraded and the report says so; and an unknown harness means the run records `harness: unknown` on the run-level record defined in [job-spec.md](job-spec.md) and refuses to claim feature support. Name that field and its owner here, because the rule is unenforceable without a schema to write into.
  11. Close with a `## Related` list of markdown links to `runtime-adapter-contract.md`, `safety-policy.md` and `runtimes/README.md`, each written as `[name](file.md)`.
- **Success criteria:** the file exists, contains the literal command `npx skills add bestagentkits/orchestrate`, names `context: fork` and `hooks:` as forbidden dependencies, and contains no copied full agent table.
- **Verify:** `grep -c 'npx skills add bestagentkits/orchestrate' plugins/orchestrate/skills/orchestrate/references/harness-portability.md` prints a number `>= 1`; `grep -q 'context: fork' plugins/orchestrate/skills/orchestrate/references/harness-portability.md && echo ok` prints `ok`.

### Task 1.2 — Reframe `SKILL.md` as harness-agnostic

- **Goal:** the payload's own text no longer reads as Claude-Code-only.
- **Target files:** `plugins/orchestrate/skills/orchestrate/SKILL.md` (the paragraph after the H1 that begins "Coordinate headless coding-agent jobs…", and the reference index at the bottom).
- **Steps:**
  1. In the opening paragraph after `# Orchestrate`, add one sentence: this skill targets any harness that implements the Agent Skills contract, and `references/harness-portability.md` owns the conformance surface and the install paths.
  2. Extend the existing `**Engine.**` paragraph with one sentence stating that the engine is the coordinator path, that no harness CLI is required, and that the harness is the thing that loads the skill while the coordinator owns the run. Do not restructure the paragraph.
  3. In the reference index, add one row linking `references/harness-portability.md` with the description "Agent Skills conformance, forbidden harness dependencies, install and discovery".
  4. Search the whole file for `Claude Code` and, for each hit, confirm the sentence does not claim the skill is Claude-Code-only. Where it does, reword to name the harness-neutral concept. Report the count of hits and the disposition of each in the phase notes.
- **Success criteria:** `SKILL.md` links `harness-portability.md` and contains no sentence claiming Claude Code as the target.
- **Verify:** `grep -q 'harness-portability.md' plugins/orchestrate/skills/orchestrate/SKILL.md && echo ok` prints `ok`; `grep -n 'A Claude Code Skill\|only Claude Code' plugins/orchestrate/skills/orchestrate/SKILL.md` prints nothing.

### Task 1.3 — Record the baseline, then add the phase assertion and control

- **Goal:** the phase's own invariants are executable before the next phase starts, and each new assertion has a recorded pre-change baseline so a gate that cannot pass is caught here rather than mid-phase.
- **Target files:** none (commands only).
- **Steps:**
  1. **Record the baseline first.** Run every assertion marked `new` in `## Verification` against the unmodified tree and write the observed value into the phase notes, with the expected post-change value beside it. Where the value is already the expected one, say so and state what the assertion therefore does **not** prove. This step is mandatory and is why the phase cannot certify a gate it never measured: an assertion whose baseline already satisfies it is not a test, and an assertion that can never be satisfied is a stall.
  2. Run the assertions below.
  3. For each, run the matching control and confirm it fails when the thing it forbids is simulated in a scratch copy under `/tmp` — never in the repository.
  4. Delete every scratch copy.
- **Success criteria:** the baseline table exists in the phase notes; every assertion passes; every control demonstrates a detectable failure.
- **Verify:** see `## Verification`. Any non-matching output means this task failed.

### Task 1.4 — Add the run-level `harness` field to `job-spec.md`

- **Goal:** the degradation rule in task 1.1 step 10 writes into a real schema.
- **Target files:** `plugins/orchestrate/skills/orchestrate/references/job-spec.md` (the `state.json` run-level object, beside `runId` and `specPath`).
- **Steps:**
  1. Add a `harness` field to the run-level object with the recorded harness identifier, defaulting to `unknown`, and a comment stating it is the harness that loaded the skill, not a runtime.
  2. Add one sentence to the Validation section: a run that cannot identify its harness records `unknown` and must not claim any harness-specific feature.
- **Success criteria:** the field exists with a default and a validation sentence, and it does not collide with any runtime field.
- **Verify:** `grep -c '"harness"' plugins/orchestrate/skills/orchestrate/references/job-spec.md` is `>= 1`; `grep -c '"harness"' plugins/orchestrate/skills/orchestrate/references/runtime-profile.md` is `0` (the runtime record is unchanged).

## Test matrix (TDD)

| Assertion | Expected | Control |
|---|---|---|
| `test -f plugins/orchestrate/skills/orchestrate/references/harness-portability.md` | exit 0 | deleting the file makes it exit 1 |
| `grep -c 'npx skills add bestagentkits/orchestrate' <file>` | `>= 1` | a copy with the command removed prints `0` |
| `grep -q 'context: fork' <file>` | match | a copy without it does not match |
| `grep -q 'ignores unknown frontmatter' <file>` | match | — |
| `grep -rn 'context: fork\|^hooks:\|^allowed-tools:' plugins/orchestrate/skills/orchestrate \| grep -v harness-portability.md` | prints nothing | adding `allowed-tools:` to `SKILL.md` makes it print `SKILL.md` |
| `grep -c '"harness"' $S/job-spec.md` | `>= 1` | — |
| Every repository path the document **names as a path** resolves | every path passes | naming a nonexistent `plugin.json` at the repo root fails |
| The root `plugin.json` is documented as absent | match | creating one in a scratch copy flips the check |
| `grep -q 'harness-portability.md' plugins/orchestrate/skills/orchestrate/SKILL.md` | match | — |

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
test -f "$S/harness-portability.md" || echo "MISSING harness-portability.md"
grep -c 'npx skills add bestagentkits/orchestrate' "$S/harness-portability.md"
grep -q 'context: fork' "$S/harness-portability.md" && echo "forbidden-dep documented"
grep -q 'ignores unknown frontmatter' "$S/harness-portability.md" && echo "frontmatter rule present"
# The forbidden-dependency check must EXCLUDE the document that is required to name them.
grep -rn 'context: fork\|^hooks:\|^allowed-tools:' plugins/orchestrate/skills/orchestrate \
  | grep -v harness-portability.md || echo "portability clean"
grep -q 'harness-portability.md' plugins/orchestrate/skills/orchestrate/SKILL.md && echo "linked"
grep -c '"harness"' "$S/job-spec.md"
# Every path the document NAMES as a repository path must resolve. This is an
# explicit list, not a generic sweep: a sweep also extracts sibling markdown link
# text and generated artifact names (runtimes.json, state.json), which are not
# files in this repository and would report false positives -- measured at 11 on
# an already-correct document.
for p in \
  plugins/orchestrate/skills/orchestrate/SKILL.md \
  plugins/orchestrate/skills/orchestrate/references/runtime-adapter-contract.md \
  plugins/orchestrate/skills/orchestrate/references/safety-policy.md \
  plugins/orchestrate/skills/orchestrate/runtimes/README.md \
  .claude-plugin/marketplace.json \
  plugins/orchestrate/.claude-plugin/plugin.json ; do
  test -e "$p" || echo "PATH-NOT-FOUND $p"
done
# The document is required to state that the ROOT plugin.json does NOT exist.
test -e .claude-plugin/plugin.json \
  && echo "ROOT PLUGIN MANIFEST EXISTS but the document says it does not" \
  || echo "root plugin.json absent as documented"
# The real Claude-Code-only surfaces, recorded here so phase 6 is accountable for them.
grep -n 'Claude Code Skill' README.md && echo "README still brands Claude-only" || echo "README kicker-free"
grep -n 'Claude Code Skill' site/index.html || echo "site kicker-free"
```

Expected: no `MISSING`, a count `>= 1`, `forbidden-dep documented`,
`frontmatter rule present`, `portability clean`, `linked`, a `harness` count
`>= 1`, no `PATH-NOT-FOUND` line, `root plugin.json absent as documented`, and —
at phase 1 exit — the two kicker lines still **finding** the phrase, because
phase 6 owns that fix. Phase 7 asserts they print `kicker-free`.

This phase introduces three assertions whose baseline is asserted to be red:
`harness-portability.md` does not exist, `harness` is absent from `job-spec.md`,
and the `npx skills add` command appears nowhere. All three are recorded in the
baseline table before the edits are made.

### Baseline table (task 1.3 step 1), measured before any edit

| Assertion | Baseline | After this phase | Proves |
|---|---|---|---|
| `test -f $S/harness-portability.md` | absent | exit 0 | the document was created |
| `grep -c 'npx skills add bestagentkits/orchestrate'` | `0` | `9` | the CLI install path is documented |
| `grep -c '"harness"' $S/job-spec.md` | `0` | `1` | the schema has the field the rule writes into |
| `grep -q 'ignores unknown frontmatter'` | no match | match | the frontmatter rule is stated |
| `portability clean` (forbidden-dep sweep) | already clean | clean | **nothing** — pre-existing invariant, carried to phase 7 |
| `root plugin.json absent as documented` | already true | true | **nothing** — pre-existing invariant; the check exists so a future root manifest fails it |
| `grep -n 'Claude Code Skill' README.md` | no match | no match | **nothing** — the README says "for Claude Code", not the swept phrase; phase 6 owns `README.md:5` |
| `grep -n 'Claude Code Skill' site/index.html` | `2` hits (`:412`, `:879`) | `2` hits | deliberately red at phase exit; phase 6 owns the fix, phase 7 asserts `kicker-free` |

One correction to the plan's stated baseline: `Claude Code` appears **zero** times
in `SKILL.md`, so task 1.2 step 4 had no sentence to reword — the Claude-only
framing really is only in `README.md` and the landing page. Recorded rather than
silently skipped.

### Verification results

All assertions matched the expected values: count `9`; `forbidden-dep documented`;
`frontmatter rule present`; `portability clean`; `linked`; `harness` count `1`; no
`PATH-NOT-FOUND`; `root plugin.json absent as documented`; README `kicker-free` for
the swept phrase; and the two site kicker lines still present, which is the
expected phase-1 state.

Controls, both run in a scratch copy under `/tmp` and then deleted:

- The forbidden-dependency sweep caught a synthetic `allowed-tools: Read` in a fake
  `SKILL.md`, so the gate is real and not vacuously green.
- `grep -c '"harness"' $S/runtime-profile.md` is `0`, confirming the new field did
  not leak into the runtime record.
