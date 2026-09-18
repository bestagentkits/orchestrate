---
phase: 4
title: "Promotion chain and fail-safe"
status: pending
priority: P0
effort: "1.25d"
dependencies: [3]
---

# Phase 4: Promotion chain and fail-safe

## Goal

An infrastructure failure promotes the job to the next eligible candidate — honoring a
declared `fallback_runtime` order first and the benchmark ranking second — within a
bounded budget that composes with the existing retry policy, and an exhausted chain
ends in a logged terminal fail-safe, while a failed check still escalates.

## Files to Create / Modify

- Create: `plugins/orchestrate/skills/orchestrate/references/fallback-policy.md`
- Modify: `plugins/orchestrate/skills/orchestrate/references/routing-policy.md` (the `## Fallbacks` section, which owns declared order and re-gating, plus the operator checklist)
- Modify: `plugins/orchestrate/skills/orchestrate/references/failure-modes.md` (three failure classes; the permission/authorization hard stop)
- Modify: `plugins/orchestrate/skills/orchestrate/references/verification.md` (a promoted attempt clears the same gate)
- Modify: `plugins/orchestrate/skills/orchestrate/references/job-spec.md` (the `fallback` block; the re-gate sentence at the `retry` section; the attempt-record promotion fields; validation)
- Modify: `plugins/orchestrate/skills/orchestrate/SKILL.md` (reference index row)

## Facts this phase must respect, verified by grep

- A declared fallback mechanism **already exists** and is normative: `job-spec.md:35` declares `fallback_runtime: [string]`; `routing-policy.md:191-197` requires evaluating those entries "through the same live gate and **in declared order**" and recomputing controls; `failure-modes.md:17-20` says to evaluate declared fallbacks; `observation.md:86` says to "re-run the full live gate and both floors for the fallback; never inherit flags, identifiers or controls"; `safety-policy.md:147` says a fallback "will be re-profiled rather than inheriting the failed command". This phase must **not** silently replace that.
- A bounded retry mechanism also exists: `job-spec.md:69-71` defines `retry: {max_attempts, backoff, classes}` and `job-spec.md:141-144` states the default is one attempt and that an explicit bounded retry policy permits only named failure classes after confirmed settlement. `failure-modes.md:27-29` already classifies "rate limit, quota, transient network" as a **retryable provider failure**.
- `job-spec.md:144` states "Fallback selection reruns the full capability and risk gate for that runtime" — this is the sentence that must be reconciled with any "the gate is not re-decided" claim.
- `failure-modes.md:9-12` states a classified `PERMISSION`, `SANDBOX` or `AUTH` result "must still hit the hard stop for that entry", and `:23-24` forbids converting a permission prompt into "an automatic retry with a broader grant".
- The control fields are nine (`runtime-profile.md:222-223`) and the per-concern minimums are six concerns in `safety-policy.md:65-90`, with no cross-concern dominance relation defined anywhere.
- `routing-policy.md` has **no** `## Independence` section; the fallback prose is in `## Fallbacks` and the checklist bullet is the one this phase edits.
- `trace-and-logging.md` does not exist yet, so this phase must not assert a trace field; phase 5 owns the correlation identifiers.

## Owner-fixed constants introduced here

| Constant | Value | Meaning |
|---|---|---|
| `MAX_PROMOTIONS_DEFAULT` | `2` | Promotions attempted when the job spec omits `fallback.maxPromotions` |
| `MAX_PROMOTIONS_MAX` | `4` | The largest promotion budget a job spec may declare; a larger value is rejected, not clamped |

## Tasks & Steps

### Task 4.1 — Author `fallback-policy.md`

- **Goal:** one document owns promotion and the terminal fail-safe, without discarding the declared-order mechanism that already exists.
- **Target files:** `plugins/orchestrate/skills/orchestrate/references/fallback-policy.md` (create).
- **Steps:**
  1. Create the file with H1 `# Fallback and Fail-Safe` and a scope paragraph: this document owns what happens when a *runtime* fails. It does not own what happens when a *work product* fails (`verification.md`), eligibility (`routing-policy.md`), or the tier and controls (`safety-policy.md`).
  2. Add section `## Terminology`. Define **promotion** as moving one job's attempt to the next candidate in the promotion chain, creating a new attempt with its own record rather than editing the previous one. State that this is this document's reading of the request's "next promotion", and that a user-curated promotion list is not needed because the declared `fallback_runtime` field already provides a user-ordered list.
  3. Add section `## Promotion triggers`. State the rule first: **only an infrastructure failure promotes.** Then a table (`Trigger | Evidence | Notes`) listing exactly: quota or rate-limit exhaustion **after** the retry budget for the current candidate is exhausted; provider outage, meaning a transport error or repeated server error; process crash or spawn failure; a runtime binary missing since the probe; and a dispatch timeout attributable to the transport rather than to the work.
  4. Add the exclusion row or paragraph this phase exists to add, in the negative: an **authorization or permission failure never promotes**. A classified `PERMISSION`, `SANDBOX` or `AUTH` result is a hard stop owned by `failure-modes.md`, and promoting past it would be laundering a control decision into a different runtime. Name the owner and link it.
  5. Add section `## What never promotes`. Negative bullets, the first carrying the safety weight: a **failed check never promotes**, because promoting on a failed check is retrying until the check passes with extra steps; a failed or ambiguous arbiter verdict never promotes; contradictory evidence never promotes; a missing artifact never promotes; an uncertainty signal never promotes; a permission, sandbox or authorization stop never promotes; and a slow-but-working runtime never promotes on duration alone. State that every one of these escalates per `verification.md`.
  6. Add section `## Composition with retry`. This section resolves the collision with the existing budget, so state the precedence explicitly: for a given candidate, the same-runtime bounded retry policy in `job-spec.md` runs **first** and is bounded by `retry.max_attempts`; only when that budget is exhausted does a promotion occur. Define the combined ceiling in one formula the implementer can apply: dispatches for one job are at most `(1 + maxPromotions) x max(1, max_attempts)`, and state that this product is the single bound — not two independent bounds. State the owner: retry semantics stay with `job-spec.md`; this document owns when a promotion is allowed, and nothing here redefines a retry class.
  7. Add section `## Building the chain`, with a stated precedence, because the tree already defines one order: build the chain positionally as (1) the job's declared `fallback_runtime` entries, in declared order, then (2) the remaining hard-filter survivors in benchmark-ranked order. State that an explicit user order always wins over a benchmark score, and that the benchmark ranking therefore only fills the tail. State that a candidate enters the chain only if it (a) passed the hard filter under the **same** floors, (b) is not weaker on any control concern (below), (c) is re-probed live for availability at promotion time, and (d) has not already failed this job in this run. State the four exclusions in the negative: a rejected candidate never enters; a weak-on-any-concern candidate never enters; a candidate whose availability is only cached never enters; and a candidate already tried for this job is skipped to prevent cycling.
  8. Add section `## The control comparison`, because "same or stronger controls" was an undefined predicate. Define it by anchoring to the six concerns in `safety-policy.md:65-90`: approval, tool gating, write boundary, isolation, timeout and bypass. State the relation: a successor is weaker if it is weaker on **any one** concern, and a candidate weaker on any concern is excluded from the chain **regardless of how much stronger it is on the others** — the comparison is per-concern with no dominance or trade-off. State the two worked cases the definition must settle: a candidate with stronger isolation but weaker capture is weaker on capture and is excluded; and a candidate whose isolation is prompt-only is excluded from any chain for a job at R2 or above, because `safety-policy.md` keeps destructive and credentialed external actions off prompt-only isolation.
  9. Add section `## The budget`. State that promotions are bounded by `fallback.maxPromotions`, default `MAX_PROMOTIONS_DEFAULT`, maximum `MAX_PROMOTIONS_MAX`, with a value above the maximum rejected rather than clamped; each promotion is a new attempt with its own record; and exhausting the budget **is** the fail-safe condition, not an error to retry around.
  10. Add section `## Re-gating a successor`. Resolve the contradiction with `job-spec.md:144` explicitly, since both files are normative: what **does** re-run on promotion is availability and the control re-verification from step 7(b) — the successor is re-probed and must not be weaker on any concern; what does **not** change is the job's tier, its approvals and its egress authority, which were decided by the safety gate for this job and are not re-decided by a promotion. State that this is the precise reading of "reruns the full capability and risk gate": the gate's **eligibility and control checks** re-run, its **authority decisions** do not. State that a successor which would need a new approval, a wider write boundary, an enabled bypass or a new egress authority is not a promotion target at all — it is a different job requiring a new gate decision.
  11. Add section `## Freshness on promotion`. State that the benchmark record used to order the chain is re-checked against the TTL rules in `benchmark-evidence.md` at promotion time; a stale record is refreshed or the candidate is ranked without it, and the promotion never proceeds on a value that was valid only at routing time.
  12. Add section `## Fail-safe`. State the terminal behaviour: an exhausted chain leaves the job `blocked` and terminal; the run continues for every job whose dependencies are unaffected; the report lists the job with the full trigger chain and the `benchmark-degraded` state if ranking was degraded; and the state is never reported as `success`, `settled` or `accepted`. State the negatives: the fail-safe never substitutes a silent downgrade of controls, never lowers a floor to find a successor, and never marks a partially produced artifact as verified. State that the tier consequences of a missing isolation capability are owned by `safety-policy.md` and are not restated here.
  13. Add section `## Interaction with the gate`. State that a promoted attempt is a new attempt and must clear the **same** accept conditions in `verification.md`; promotion grants no credit from the earlier attempt, changes no tier, and adds no approval; and a promoted attempt whose **content** then fails sends the job to the arbiter rather than to a third runtime, so promotion cannot become a search for a passing answer.
  14. Add section `## Recording`. State that every promotion records `promotionOf` and `promotionTrigger` on the new attempt, using the attempt identity the attempt record already carries, and that the phase-5 trace joins them through that identity. State that this document asserts no trace field of its own, because `trace-and-logging.md` owns the envelope.
  15. Add section `## Degradation`. State: a single-candidate chain fails safe immediately rather than falling back to an ineligible runtime; a chain with no eligible successor fails safe; and when promotion is disabled by configuration, the failure is reported with its trigger rather than swallowed.
  16. Add section `## Constants`. Reproduce `MAX_PROMOTIONS_DEFAULT` and `MAX_PROMOTIONS_MAX` from this phase, and state that this file is the owner and that `job-spec.md` validation cites it.
  17. Close with `## Related` links to `routing-policy.md`, `verification.md`, `failure-modes.md`, `benchmark-evidence.md`, `job-spec.md`, `trace-and-logging.md`.
- **Success criteria:** the document exists; states the trigger rule; excludes authorization/permission stops; carries the negative "never promotes" block with the failed-check rule first; defines retry/promotion precedence and the combined ceiling; defines the per-concern control comparison; resolves the re-gate contradiction; states the budget and the constants.
- **Verify:** `grep -q 'only an infrastructure failure promotes' <file>`; `grep -q 'never promotes' <file>`; `grep -q 'authorization or permission failure never promotes' <file>`; `grep -q 'weaker on any concern\|weaker on \*\*any one\*\* concern' <file>`; `grep -q 'MAX_PROMOTIONS_MAX' <file>`; `grep -q 'max_attempts' <file>`.

### Task 4.2 — Reconcile `routing-policy.md`

- **Goal:** the declared-order owner and the new chain owner agree, and the negative rule is visible from routing.
- **Target files:** `plugins/orchestrate/skills/orchestrate/references/routing-policy.md` (`## Fallbacks`, and the operator-checklist bullet).
- **Steps:**
  1. In `## Fallbacks`, keep the existing declared-order and recompute text and add one sentence delegating the chain mechanics: the promotion chain, its triggers, its budget, its control comparison and its fail-safe are owned by `fallback-policy.md`, which preserves this section's declared order as the chain's head. **Rewrap the sentence at `routing-policy.md:191-192` in the same edit**: it currently reads "… evaluated through the same live gate and in declared" / "order.", so the contiguous phrase `in declared order` does not exist anywhere in the file and the assertion below reports `0` before a line of this phase is written. This is a whitespace-only rewrap; do not change the wording, and do not treat the red baseline as a defect in the document.
  2. Replace the operator-checklist bullet about fallbacks with one that keeps "Fallbacks meet the same floors as their primary route" and adds the pointer to `fallback-policy.md`.
  3. Add one checklist bullet in the negative: a fallback never weakens a control to restore availability, and a verification failure escalates rather than promoting.
- **Success criteria:** the declared-order text survives, the pointer exists, and the negative bullet exists.
- **Verify:** `grep -q 'fallback-policy.md' <file>`; `grep -q 'in declared order' <file>`; `grep -q 'never weakens a control' <file>`.

### Task 4.3 — Split failure classes in `failure-modes.md`

- **Goal:** a reader can tell which failures promote, which escalate, and which are evidence-plane failures that do neither.
- **Target files:** `plugins/orchestrate/skills/orchestrate/references/failure-modes.md`.
- **Steps:**
  1. Add a section `## Three failure classes` with exactly three rows or bullets: **transport or infrastructure** (a promotion candidate, bounded by `retry.max_attempts` then `fallback.maxPromotions`, owned by `fallback-policy.md`); **content or verification** (a hard stop that escalates to the arbiter per `verification.md`); and **evidence-plane write failure** (a trace, cache or metrics write that fails — it neither promotes nor escalates, it is recorded and the run continues with the affected evidence marked incomplete, because promoting on a trace-write failure would burn a promotion slot on a healthy runtime).
  2. Add one sentence stating that the three are never conflated, and that retrying a content failure on another runtime is forbidden because it selects for the answer rather than for the work.
  3. Add one sentence confirming that the existing permission/sandbox/authorization hard stop is unchanged and is not a promotion trigger, and link `fallback-policy.md`.
  4. Add links to `verification.md` and `fallback-policy.md`.
- **Success criteria:** the section names all three classes, the permission stop is confirmed unchanged, and both links resolve.
- **Verify:** `grep -q 'Three failure classes' <file>`; `grep -c 'evidence-plane write failure' <file>` is `>= 1`; `grep -q 'not a promotion trigger' <file>`; `grep -c 'fallback-policy.md' <file>` is `>= 1`.

### Task 4.4 — Guard the gate in `verification.md`

- **Goal:** promotion cannot buy credit at the acceptance gate.
- **Target files:** `plugins/orchestrate/skills/orchestrate/references/verification.md` (the escalation-matrix preamble).
- **Steps:**
  1. Add one paragraph: a promoted attempt is a **new** attempt and is evaluated from scratch; nothing carries over from the attempt it replaced; and a second content failure on a promoted attempt escalates to C3 rather than triggering another promotion.
  2. Add the link to `fallback-policy.md`.
- **Success criteria:** the paragraph and link exist, and the accept predicate is still stated only in this file.
- **Verify:** `grep -q 'promoted attempt' <file>`; `grep -rln 'Accept without a C3 call' plugins/orchestrate/skills/orchestrate/references` prints exactly `verification.md`.

### Task 4.5 — Declare the budget and the promotion fields

- **Goal:** the budget and the promotion identity are declared inputs with validation and named consumers.
- **Target files:** `plugins/orchestrate/skills/orchestrate/references/job-spec.md` (`defaults` block, the `retry` section, the attempt record, validation), `plugins/orchestrate/skills/orchestrate/SKILL.md` (index).
- **Steps:**
  1. In the `defaults:` block, add a `fallback:` sub-block with `maxPromotions: <integer>` and a comment stating the default and the owner-fixed maximum from `fallback-policy.md`.
  2. In the `retry` section, add one sentence stating the precedence: same-runtime retries run first and are bounded by `max_attempts`; a promotion occurs only after that budget is exhausted; and the combined dispatch ceiling is `(1 + maxPromotions) x max(1, max_attempts)`.
  3. Amend the existing "Fallback selection reruns the full capability and risk gate for that runtime" sentence to state precisely what re-runs (availability and the per-concern control check) and what does not (tier, approval, egress authority), matching `fallback-policy.md`.
  4. In the `state.json` **attempt record**, add `promotionOf` and `promotionTrigger`, referencing the attempt identity the record already carries. Do **not** introduce a new identifier here: the record's existing ordinal is the identity, and phase 5 builds the correlation envelope around it.
  5. Add a numbered validation step rejecting a `maxPromotions` above the owner-fixed maximum, **appended** after the existing last step, with the same range note as phase 2 task 2.3 step 4.
  6. Add one `SKILL.md` index row linking `references/fallback-policy.md`, described as "Promotion chain, triggers, budget, control comparison, and the terminal fail-safe".
- **Success criteria:** `maxPromotions` appears with default and maximum, the retry precedence sentence exists, the re-gate sentence is amended, the two attempt fields exist, and the link resolves.
- **Verify:** `grep -c 'maxPromotions' <file>` is `>= 2`; `grep -q 'combined dispatch ceiling' <file>`; `grep -q 'what does not change is the job.s tier\|tier, its approvals and its egress authority' <file>`; `grep -q 'promotionOf' <file>`; `grep -q 'fallback-policy.md' plugins/orchestrate/skills/orchestrate/SKILL.md`.

## Test matrix (TDD)

| Assertion | Expected | Control |
|---|---|---|
| `test -f $S/fallback-policy.md` | exit 0 | deleting it exits 1 |
| `grep -q 'only an infrastructure failure promotes' $S/fallback-policy.md` | match | — |
| `grep -q 'authorization or permission failure never promotes' $S/fallback-policy.md` | match | — |
| `grep -q 'MAX_PROMOTIONS_MAX' $S/fallback-policy.md` | match | — |
| `grep -q 'max_attempts' $S/fallback-policy.md` | match | — |
| `grep -q 'in declared order' $S/routing-policy.md` | match (preserved) | deleting the declared-order clause fails it |
| `grep -q 'Three failure classes' $S/failure-modes.md` | match | — |
| `grep -q 'promoted attempt' $S/verification.md` | match | — |
| `grep -rln 'Accept without a C3 call' $S` | exactly `verification.md` | adding the phrase to `fallback-policy.md` prints two files |
| `grep -c 'maxPromotions' $S/job-spec.md` | `>= 2` | — |
| `grep -q 'combined dispatch ceiling' $S/job-spec.md` | match | — |
| Peer reachability of `fallback-policy.md` | ≥1 peer that is not `SKILL.md` | removing the `routing-policy.md` link leaves the index row only, so peers are counted, not the row |

**Baselines recorded before this phase's edits.** Two assertions were **red at phase
entry**, and both are recorded so the red is known to be a defect and not a missing
rule:

- `grep -q 'in declared order' $S/routing-policy.md` returned `0`: the phrase was split
  across `routing-policy.md:191-192` by a line wrap. The whitespace-only rewrap in task
  4.2 step 1 turns it green, and it did.
- `grep -q 'promotionOf' $S/job-spec.md` returned `0`, and `grep -c 'maxPromotions'`
  returned `0`: neither field existed. Task 4.5 introduces them.

### Verification results

All assertions passed on the first run, with no wording alignment needed:
`trigger rule present`, `auth-stop exclusion present`, `control comparison defined`,
`retry precedence present`, `constants present`, `routing linked`, `declared order
preserved`, `routing negative present`, `three classes present`, `permission stop
confirmed`, `gate guard present`, `ceiling stated`, `promotion identity recorded`,
`SKILL linked`; `maxPromotions` count `3`; the boundary grep printing exactly
`.../verification.md`, so the accept predicate still has one owner; and peer links `4`.

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
test -f "$S/fallback-policy.md" || echo "MISSING fallback-policy.md"
grep -q 'only an infrastructure failure promotes' "$S/fallback-policy.md" && echo "trigger rule present"
grep -q 'authorization or permission failure never promotes' "$S/fallback-policy.md" && echo "auth-stop exclusion present"
grep -q 'weaker on any concern' "$S/fallback-policy.md" && echo "control comparison defined"
grep -q 'max_attempts' "$S/fallback-policy.md" && echo "retry precedence present"
grep -q 'MAX_PROMOTIONS_MAX' "$S/fallback-policy.md" && echo "constants present"
grep -q 'fallback-policy.md' "$S/routing-policy.md" && echo "routing linked"
grep -q 'in declared order' "$S/routing-policy.md" && echo "declared order preserved" || echo "DECLARED ORDER PHRASE SPLIT BY WRAP -- see task 4.2 step 1"
grep -q 'never weakens a control' "$S/routing-policy.md" && echo "routing negative present"
grep -q 'Three failure classes' "$S/failure-modes.md" && echo "three classes present"
grep -q 'promoted attempt' "$S/verification.md" && echo "gate guard present"
grep -rln 'Accept without a C3 call' "$S"
grep -c 'maxPromotions' "$S/job-spec.md"
grep -q 'combined dispatch ceiling' "$S/job-spec.md" && echo "ceiling stated"
grep -q 'fallback-policy.md' plugins/orchestrate/skills/orchestrate/SKILL.md && echo "SKILL linked"
b=$(basename "$S/fallback-policy.md")
echo "peer links (must be >= 1): $(grep -rlE "\]\([^)]*/?$b\)" --include='*.md' --exclude="$b" plugins/orchestrate/skills/orchestrate README.md | wc -l)"
```

Expected: no `MISSING`; every `present`/`defined`/`linked`/`preserved`/`stated`
line; the boundary grep printing exactly `.../verification.md`; a count `>= 2`;
and a peer-link count `>= 1`.
