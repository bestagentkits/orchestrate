---
phase: 3
title: "Credential resolution and egress"
status: pending
priority: P0
effort: "0.75d"
dependencies: [2]
---

# Phase 3: Credential resolution and egress

## Goal

The reference provider's key is read from exactly one of four documented locations in
the user-specified order, is handed to the runtime only through the inherited child
environment, is never printed, prompted for, or committed, and a shadowed or
untrusted source is reported rather than silently preferred.

## Files to Create / Modify

- Modify: `plugins/orchestrate/skills/orchestrate/references/decision-plane.md` (the `## Provider sourcing` section)
- Modify: `plugins/orchestrate/skills/orchestrate/references/safety-policy.md` (the secrets/redaction section, as a pointer plus one reconciliation)
- Modify: `.gitignore` (repository root: ignore dotenv files)
- Modify: `README.md` (only the two lines that currently promise no credential category, so the release does not contradict itself; the full credential section is phase 6's)

## Facts this phase must respect, verified by grep

- `decision-plane.md:81-82` states the plane is dispatched through a runtime adapter and that there is "no bespoke provider client, and **no new credential category**".
- `README.md:94` says the plane "is sourced from a runtime **already in the live inventory**; there is no new provider dependency", and `README.md:441` says "no provider client and no credential category". Both are shipped claims that this phase makes false unless reconciled here.
- `safety-policy.md:125-127` forbids writing secrets, tokens, credential or dotenv values "into prompts, commands, logs, capture, decision traces, issues, PRs, plans or reports", and `:129-131` excludes any surface "that carries argv or environment values" from a diagnosis bundle.
- `.gitignore` contains exactly `.DS_Store`, `node_modules/`, `plans/reports/` and `*.log` — no dotenv entry.
- `output-layout.md:5,17` already marks `jobs.yaml` and `graph.json` private because they may carry argv or environment values.

## Tasks & Steps

### Task 3.1 — Add the resolution order to `decision-plane.md`

- **Goal:** the key source is specified, ordered, trust-annotated, and testable.
- **Target files:** `plugins/orchestrate/skills/orchestrate/references/decision-plane.md` (`## Provider sourcing`).
- **Steps:**
  1. In `## Provider sourcing`, add a subsection `### Credential resolution`. State the scope: this applies to the reference provider's key, and any additional provider this skill ever contacts follows the same order with its own variable name.
  2. State the variable name literally: `TYPESAFE_API_KEY`.
  3. Give the resolution order as an ordered list, in this exact sequence, and state that resolution stops at the first location that yields a non-empty value:
     1. the process environment (`process.env`);
     2. the project `.env`;
     3. the `skills/` directory `.env`;
     4. the skill's own `.env` (the directory containing `SKILL.md`).
  4. Add the **trust annotation** to each of locations 2–4 in the same list item: they are read paths inside a working tree, and a working tree is not trusted merely because the run is in it. State the consequence in one sentence: a credential read from a working-tree file is reported as such, and the egress authorization recorded for the call must name the credential source, so the run's authorization covers the identity that actually calls the provider and not merely the destination.
  5. Add the **delivery rule**: the value is handed to the runtime **only** through the inherited child environment. It is never passed as a command-line argument, never written to stdin, never placed in a prompt, and never exported by a scaffold that echoes the environment. State why in one sentence: `safety-policy.md:125-131` forbids writing a dotenv value into a command or any surface carrying argv or environment values, and the invocation surface is persisted for diagnosis.
  6. Add the never-print enumeration as one flat bullet set: never in session output, a log, a report, a trace record, a capture bundle, a decision trace, an issue, a PR, a plan, a plugin manifest or a commit — only presence or absence, the source location and the source's trust class are recorded.
  7. State the recording discipline: the trace and the report record `credentialSource` as one of `env`, `project-env`, `skills-env`, `skill-env` or `absent`, plus `credentialTrust` as `process` or `working-tree`. No value, length, prefix, suffix or hash of the key is ever recorded.
  8. State what happens on ambiguity, in two parts. First, precedence: an earlier location always wins, so the environment overrides a file and a project `.env` overrides a skill-directory one; a later location is never merged over an earlier one. Second, and this is the part this phase exists to add: a shadowed location is **recorded and reported** — the run's report carries a `credential-shadowed` token naming which source won and which was ignored — because a silently preferred working-tree credential is the failure mode where a user's own key stops being used without anyone noticing. Add the negative form: the report never prints anything about the value, only which location was used and which was shadowed.
  9. State the degradation rule: a missing key never fails the run. The plane is disabled for that run, deterministic policy proceeds, and the trace records `credentialSource: absent`.
  10. Add the interactive rule in the negative: the skill never prompts for a key and never instructs a user to paste one. If no source yields a value, the plane is disabled — prompting is not a fallback, because a secret typed into a session is a secret in a transcript.
  11. Link `harness-portability.md` for why the fourth path is expressed relative to `SKILL.md` rather than a fixed absolute path: skill directories differ per harness.
- **Success criteria:** the four paths appear once each, in the user-specified order, with `TYPESAFE_API_KEY` named; the child-environment delivery rule, the never-print enumeration, the shadowing report token and the degradation rule are all present.
- **Verify:** `grep -c 'TYPESAFE_API_KEY' <file>` is `>= 1`; the four path tokens appear in strictly increasing line order; `grep -q 'inherited child environment' <file>` matches; `grep -q 'credential-shadowed' <file>` matches; `grep -q 'credentialTrust' <file>` matches.

### Task 3.2 — Reconcile the "no credential category" claims

- **Goal:** the release does not ship a reference telling an agent to resolve a key while the README says no credential exists.
- **Target files:** `plugins/orchestrate/skills/orchestrate/references/decision-plane.md` (`## Provider sourcing`), `README.md` (lines 94 and 441).
- **Steps:**
  1. In `decision-plane.md`, amend the `no new credential category` sentence in place rather than contradicting it: state what remains true — the plane still has no bespoke provider client and adds no new *credential system*, because the key is the runtime's own provider credential surfaced through a documented read order — and what is now specified — where that key is read from and how it is delivered.
  2. In `README.md` at the two sentences named in the file list, make the same distinction in one clause each, so a reader who configures nothing learns that the plane is disabled rather than that nothing is needed.
  3. Add one sentence stating that this subsection is the single owner of the resolution order, and that the README's credential section (phase 6) is a **parity-checked summary**, not an independent contract. State that a change to the order here obliges the README copy to change with it.
- **Success criteria:** no surviving sentence asserts unconditionally that no credential exists; the ownership sentence exists; the two README lines are amended.
- **Verify:** `grep -n 'no new credential category' plugins/orchestrate/skills/orchestrate/references/decision-plane.md` still matches **and** the matched sentence contains "credential system"; `grep -c 'no credential category' README.md` is `0` or every remaining match is qualified by a neighbouring clause containing "disabled".

### Task 3.3 — Ignore dotenv files in the repository

- **Goal:** the documented read locations can never be committed.
- **Target files:** `.gitignore` (repository root).
- **Steps:**
  1. Add `.env` and `.env.*` to `.gitignore`, and add `!.env.example` so a template can still be committed deliberately.
  2. Add a one-line comment above the entry stating why: the skill documents four dotenv read locations, three of them inside a working tree, so the ignore rule is what keeps a documented path from becoming a published key.
  3. Do not add ignore rules for the run directory: `plans/reports/` is already ignored and the run directory lives under it.
- **Success criteria:** `.env` is ignored, `.env.example` is explicitly not ignored, and the reason is stated.
- **Verify:** `grep -c '^\.env' .gitignore` is `>= 1`; `grep -q '^!\.env\.example' .gitignore` matches; `git check-ignore -q .env && echo "ignored"` prints `ignored`; `git check-ignore -q .env.example && echo "BAD" || echo "example tracked"` prints `example tracked`.

### Task 3.4 — Land the pointer in the secrets owner and reconcile the contradiction

- **Goal:** `safety-policy.md` carries the pointer that the files list promises, and the two shipped sentences that contradict the new never-prompt rule are reconciled.
- **Target files:** `plugins/orchestrate/skills/orchestrate/references/safety-policy.md`, `plugins/orchestrate/skills/orchestrate/SKILL.md`.
- **Steps:**
  1. Add one bullet to the secrets/redaction section of `safety-policy.md`: a provider credential is read from a documented location by the owner in `decision-plane.md`; it is never printed, never requested interactively, and never written to a run artifact; and its absence degrades the decision plane rather than failing the run. Do **not** restate the four-path order — link `decision-plane.md` so the order keeps a single owner.
  2. Add the complementary negative rule: no run may add a key to a tracked file, and a dotenv file remaining in the working tree stays untracked and uncommitted.
  3. **Reconcile the contradiction.** `safety-policy.md:121` and `SKILL.md:220` both currently read "credentials are entered only by the user", which the never-prompt rule contradicts. Reword both to the precise statement: the coordinator never types, copies or stores a credential; a credential is read from a documented location or the capability that needs it is disabled. State which rule wins in the same sentence, so a reader is not left to choose.
  4. **Add the endpoint rule**, because the order governs the key and this is the half beside it. State that **only** the key variable is read from the four documented locations, and that provider endpoint, base-URL, proxy and organization overrides are read from the process environment or not at all — a working-tree dotenv may not redirect where the run connects, because that would send the user's content to an endpoint the user never approved under an authorization that names a different one.
  5. **Surface the shadow in the report block.** Add `credential-shadowed` to the report fields enumerated in `SKILL.md`'s Completion Report section, not only to `report.md` in the layout owner, so a shadowed key reaches the surface a user actually reads.
- **Success criteria:** the pointer exists in `safety-policy.md`; both "entered only by the user" sentences are reworded; the endpoint rule exists; and `credential-shadowed` appears in `SKILL.md`'s report block.
- **Verify:** `grep -q 'decision-plane.md' plugins/orchestrate/skills/orchestrate/references/safety-policy.md`; `grep -rn 'entered only by the user' plugins/orchestrate/skills/orchestrate | wc -l` is `0`; `grep -q 'endpoint, base-URL, proxy' plugins/orchestrate/skills/orchestrate/references/safety-policy.md`; `grep -q 'credential-shadowed' plugins/orchestrate/skills/orchestrate/SKILL.md`.

### Task 3.5 — Assert the no-leak invariant across the tree

- **Goal:** the phase's assertions can actually fail, and cover argv and committed files rather than only `echo`.
- **Target files:** none (commands only).
- **Steps:**
  1. Run every check in `## Verification`.
  2. Confirm the tracked-dotenv check and the argv check each fail when the thing they forbid is simulated in a scratch copy — not in the repository.
  3. Record the results in the phase notes.
- **Success criteria:** every check passes, and the two new controls each demonstrate a detectable failure.
- **Verify:** see `## Verification`.

## Test matrix (TDD)

| Assertion | Expected | Control |
|---|---|---|
| `grep -c 'TYPESAFE_API_KEY' $S/decision-plane.md` | `>= 1` | removing it prints `0` |
| Order of the four path tokens by line number | strictly increasing | swapping two path lines fails the check |
| `grep -q 'inherited child environment' $S/decision-plane.md` | match | — |
| `grep -q 'never passed as a command-line argument' $S/decision-plane.md` | match | — |
| `grep -q 'credential-shadowed' $S/decision-plane.md` | match | — |
| `grep -c 'process.env' $S/safety-policy.md` | `0` (the order is not duplicated there) | adding the list prints `>= 1` |
| `grep -q '^\.env' .gitignore` | match | removing the rule fails it |
| `git ls-files \| grep -c '\(^\|/\)\.env$'` | `0` | staging a scratch `.env` makes it print `>= 1` |
| No argv delivery: `grep -rn 'TYPESAFE_API_KEY' plugins README.md site \| grep -E '\-\-[a-z-]*key\|export .*TYPESAFE'` | nothing | a doc showing `--api-key=$TYPESAFE_API_KEY` prints a hit |
| `grep -rn 'echo .*TYPESAFE_API_KEY\|print.*TYPESAFE_API_KEY\|cat .*\.env' plugins README.md site CLAUDE.md` | nothing | a doc that prints the key prints a hit |

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
SKILL=plugins/orchestrate/skills/orchestrate/SKILL.md
grep -c 'TYPESAFE_API_KEY' "$S/decision-plane.md"
grep -n 'process\.env\|project `\.env`\|`skills/` directory\|skill.s own `\.env`' "$S/decision-plane.md"
grep -q 'inherited child environment' "$S/decision-plane.md" && echo "delivery rule present"
grep -q 'never passed as a command-line argument' "$S/decision-plane.md" && echo "no-argv rule present"
grep -q 'never requested interactively\|never prompts for a key' "$S/decision-plane.md" && echo "no-prompt rule present"
grep -q 'credential-shadowed' "$S/decision-plane.md" && echo "shadow report token present"
grep -q 'credentialTrust' "$S/decision-plane.md" && echo "trust class recorded"
grep -q 'credential system' "$S/decision-plane.md" && echo "reconciliation present"
grep -q 'parity-checked summary' "$S/decision-plane.md" && echo "readme ownership stated"
grep -q 'decision-plane.md' "$S/safety-policy.md" && echo "secrets pointer landed"
grep -q 'endpoint, base-URL, proxy' "$S/safety-policy.md" && echo "endpoint rule present"
echo -n "stale 'entered only by the user' (must be 0): "; grep -rc 'entered only by the user' plugins/orchestrate/skills/orchestrate | grep -v ':0' | wc -l
grep -q 'credential-shadowed' "$SKILL" && echo "shadow token in report block"
# Escaped dot: an unescaped `.` also matches "process environment", which is prose
# this file is allowed to contain, and would report a duplication that is not one.
grep -c 'process\.env' "$S/safety-policy.md"
grep -n '^\.env\|^!\.env\.example' .gitignore
git check-ignore -q .env && echo ".env ignored"
git ls-files | grep -c '\(^\|/\)\.env$'
grep -rn 'TYPESAFE_API_KEY' plugins README.md site | grep -E '\-\-[a-z-]*key|export .*TYPESAFE' || echo "no argv delivery documented"
grep -rn 'echo .*TYPESAFE_API_KEY\|print.*TYPESAFE_API_KEY\|cat .*\.env' plugins README.md site CLAUDE.md 2>/dev/null || echo "no key-printing guidance"
```

Expected: count `>= 1`; the four paths printed in order; every `present`/`recorded`/
`stated`/`landed` line; `0` for the duplicated-order check; `0` for the stale
sentence; the two `.gitignore` lines; `.env ignored`; `0` tracked dotenv files;
and both `no …` lines.

### Baseline table (measured before this phase's edits)

| Assertion | Baseline | After this phase | Proves |
|---|---|---|---|
| `grep -c 'TYPESAFE_API_KEY' $S/decision-plane.md` | `0` | `1` | the order is specified |
| `grep -q 'credential-shadowed' $S/decision-plane.md` | no match | match | shadowing is reported |
| `grep -q 'credential system' $S/decision-plane.md` | no match | match | the old claim is reconciled, not deleted |
| `grep -q 'decision-plane.md' $S/safety-policy.md` | `0` | match | the pointer landed in the secrets owner |
| `grep -rc 'entered only by the user' plugins/orchestrate/skills/orchestrate` | `2` | `0` | the contradiction is gone |
| `git check-ignore -q .env` | not ignored | ignored | a documented read path cannot be committed |
| `grep -q 'credential-shadowed' $SKILL` | no match | match | the shadow reaches the surface a user reads |
| `grep -q 'endpoint, base-URL, proxy' $S/safety-policy.md` | no match | match | the half beside the key is governed |

### Verification results

All assertions passed. Three were red on the first run, **all three caused by my own
wording**, and none by a missing rule:

- `inherited child environment` and `endpoint, base-URL, proxy` were each **split across
a line wrap**, so the literal the gate greps did not exist. Fixed by keeping each
required phrase contiguous. This is the second phase in a row where a line wrap broke a
gate; the rule that follows is stated plainly: **a phrase an assertion greps must not
be wrapped.**
- The phase's own `grep -c 'process.env' $S/safety-policy.md` reported `1` against an
expected `0`, because an **unescaped `.`** in the pattern also matches "process
environment" — prose this file is allowed to contain. Fixed by escaping the dot, which
makes the assertion test its actual intent. A control that copies the real four-path
order into the file reports `2`, so the gate still catches a duplication.

### Boundary note

The endpoint rule is the substantive addition here. Without it, the four-path order
governed only the key while a working-tree dotenv could still set a base URL or proxy —
sending the user's content to an endpoint the user never approved, under an
authorization naming a different source. That was the security review's real hole, and
it was not the shadowing it originally named.
