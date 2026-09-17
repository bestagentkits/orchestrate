---
title: "Universal runtime adapter layer + System-1 decision plane"
description: "Split route selection into a deterministic policy, a normalized runtime/event contract, and a provider-neutral System-1 decision plane that supplies probabilistic signals for routing, watching, triage, and pre-arbiter gating."
status: completed
priority: P1
effort: 5d
issue: 3
branch: ultra-orchestrate-with-jev
tags: [refactor, docs, orchestration, critical]
blockedBy: []
blocks: []
created: 2026-09-17
---

# Universal runtime adapter layer + System-1 decision plane

## Overview

Measured against this tree, the cost of supporting a new runtime is not a new
`*-sessions.md` plus a routing branch. `model-routing.md` is already
runtime-agnostic: it defers tiers, floors and selection to the live inventory.
The real, countable cost is distributed evidence work:

- **6 reference files** currently link `model-routing.md`, and `pi-sessions.md`
  is the only per-runtime session reference — so per-runtime knowledge already
  leaks into core at exactly one point and nowhere else.
- **4 files** link `runtime-matrix.md` and **5** link `harness-profiles.md`,
  whose control-evidence rules (tool gating, write boundary, bypass discipline)
  are what R1/R2 gating actually depends on.
- **3 surfaces** carry a second copy of the C1–C3 / R0–R3 tables — `README.md`,
  `site/index.html` — and they have already drifted from the authority
  (`model-routing.md:76` says "worktree **or stronger isolation** … **explicit
  checks** and arbiter review"; `README.md:73` drops the isolation clause;
  `site/index.html:588` drops the checks clause).
- **4 places** hard-code `1.8.0` (`plugin.json`, `SKILL.md` frontmatter, and
  `site/index.html:425,438,830`).

So the restructure is justified by duplication and drift that already exist, not
by an invented runtime-count problem. Three structural moves implement all eight
accepted proposals (P0–P3):

1. **Normalize the bottom of the stack.** One `RuntimeAdapter` contract, one
   normalized profile schema, one normalized event protocol.
2. **Split the middle of the stack.** Route selection separates into
   deterministic **hard policy** (safety, eligibility, floors, ranking) and a
   provider-neutral **System-1 decision plane** that returns bounded typed
   probability distributions.
3. **Keep authority where it belongs.** The decision plane never authorizes a
   safety decision, never emits a command, and never replaces the C3 arbiter.
   It supplies semantic signals; deterministic policy and the C3 judgment route
   decide.

Jev / TypeSafe is documented as the reference System-1 implementation and one
optional provider. It is never a requirement: the decision plane prefers a cheap
qualified candidate already in the live runtime inventory, and on classifier
absence the profile is written from deterministic probe and conformance results
alone.

## Goals

| # | Goal | Priority | Owning document |
|---|------|----------|-----------------|
| 1 | Universal `RuntimeAdapter` contract every runtime implements | P0 | `references/runtime-adapter-contract.md` |
| 2 | Normalized event protocol + common agent state machine | P0 | `references/event-protocol.md` |
| 3 | System-1 trace watchdog for stall/progress/intervention signals | P1 | `references/decision-plane.md` |
| 4 | Cross-runtime failure triage replacing per-runtime branching | P1 | `references/decision-plane.md` |
| 5 | Semantic router raising route quality above coarse task enums | P1 | `references/decision-plane.md` |
| 6 | Micro-arbiter that gates the C3 arbiter instead of replacing it | P2 | `references/verification.md` |
| 7 | Runtime auto-profiler: probe evidence → normalized capability profile | P2 | `references/runtime-profile.md` |
| 8 | Job-graph dedupe/overlap optimizer | P3 | `references/graph-optimizer.md` |

Two documents own two goals each on purpose: goals 3–5 are one contract with
three task schemas, and goals 1–2 are the two halves of one normalized
interface. The table above is the machine-checkable proposal→owner map that
replaces the earlier unfalsifiable "exactly one owning document" criterion.

## Non-goals

- No daemon, scheduler, account pool, or hosted service.
- No provider adapter for _running_ jobs. The System-1 classifier is dispatched
  through a runtime already present in the live inventory, so the
  "not a CLI dependency" and "no provider adapter" claims stay true.
- No change to the R0–R3 safety model, the worktree rule, or the requirement
  that R2 and above receive arbiter review.
- No copied catalog of runtimes, flags, models, or providers.
- No landing-page **redesign**. Version strings on the landing page must match
  the release (see phase 7), because leaving `1.8.0` there ships three
  contradicting versions.

## Deliverable shape

```text
plugins/orchestrate/skills/orchestrate/
  SKILL.md                              # rewritten pipeline + authority map
  references/
    runtime-adapter-contract.md         # P0  interface, conformance, command construction
    runtime-profile.md                  # P0  profile schema, probing, auto-profiler
    event-protocol.md                   # P0  normalized events + state machine
    safety-policy.md                    # P0  R0-R3, approval, authority, boundaries
    routing-policy.md                   # P1  deterministic eligibility/floors/ranking
    decision-plane.md                   # P1  System-1 contract + decision tasks
    verification.md                     # P2  checks, micro-arbiter gate, arbiter contract
    graph-optimizer.md                  # P3  dedupe/overlap/write-conflict reduction
    observation.md                      # extended: cursors over event-protocol
    job-spec.md                         # extended: decision trace + profile fields
    failure-modes.md                    # extended: triage handoff
    output-layout.md                    # extended: decision artifacts
    dispatch-hardening.md               # relinked to routing-policy/runtime-profile/verification
    metrics-and-self-improvement.md     # extended: calibration of decision signals
    internal-routing.md                 # reframed: the internal adapter
  runtimes/
    README.md                           # how to add an adapter + conformance suite
    pi.md                               # was pi-sessions.md
    pi-onboarding.md                    # moved
    omp.md agy.md grok.md               # existing probe targets
    claude.md codex.md gemini.md opencode.md aider.md   # unverified scaffolding
```

No new executable is added. This repo contains no code, no `package.json`, and
no CI, and its install path copies only the skill folder — so a repo-root or
skill-local Node linter would ship the repo's first executable and decay after
merge. Verification is expressed as grep assertions run at each phase exit.

## Phases

| Phase | Name | Status |
|---|---|---|
| 1 | [Core contracts](phase-01-core-contracts.md) | Pending |
| 2 | [Policy split](phase-02-policy-split.md) | Pending |
| 3 | [Decision plane](phase-03-decision-plane.md) | Pending |
| 4 | [Verification and profiler](phase-04-verification-profiler.md) | Pending |
| 5 | [Graph optimizer](phase-05-graph-optimizer.md) | Pending |
| 6 | [Runtime adapters](phase-06-runtime-adapters.md) | Pending |
| 7 | [Integration and release](phase-07-integration-release.md) | Pending |

Phases 1→2→3→4→5 are strictly sequential. Phase 6 depends only on phase 1.
Phase 7 depends on phases 5 and 6 and owns the single atomic path flip.

## Test strategy (TDD)

The deliverable is a normative document set, so its executable tests are
document-integrity assertions. There is no committed linter; each phase ends
with the greps it needs, and phase 7 runs the full tree sweep.

**Baseline honesty:** on the current tree, four of the five invariants below are
already green — all 13 references resolve from `SKILL.md`, the tier tables exist
in `model-routing.md` (plus two drifted copies), and the only `runtimes.json`
schema fence is in `runtime-matrix.md`. Only the denylist is red, and it is red
because the tree legitimately still owns those paths. So "test first" here
proves the assertions are wired up, not that they are sensitive to the change.
The discriminating test is the **proposal→owner map** above, and the
**per-phase exit conditions** in each phase file.

| Test | What it proves | Enforced |
|------|----------------|----------|
| Link resolution | Every `](path.md)` under the skill resolves | each phase exit, scoped to changed files |
| Denylist | No doc links a removed path | phase 7 only (it is red until the path flip) |
| Reachability | Every file under `references/` and `runtimes/` is linked by a resolved link | phase 7 |
| Presentation parity | `README.md` and `site/index.html` do not assert a control weaker than `safety-policy.md` | phase 7 |
| Boundary | `decision-plane.md` contains no accept/escalation table, no route field, and no command field | phase 4 and 7 |
| Secrets | No decision trace carries free-text classifier output | phase 3 and 7 |

Scope note: `README.md` and `site/index.html` are **presentation surfaces**.
They may summarize and link; they must not be the authority. The single-authority
rule therefore applies to `references/` + `runtimes/` only, and the two
presentation surfaces are checked for *parity*, not ownership.

**What these assertions are and are not.** Grep proves that a sentence exists, a
link resolves, and a token is absent. It cannot prove that R2 escalates to C3, or
that a calibration record is genuine. Nothing in this repo executes, so the
honest containment stack is: fail-closed wording, hard structural exclusions
independent of tier, the C3 arbiter as the actual backstop, and an auditable
record (decision trace, derived tier, accepted-without-C3 count) in the report.
The assertions below are for structural invariants only, and no document may
describe them as enforcement of the risk rule.

## Change manifest (what a reviewer should be able to verify)

```bash
# 1. denylist: no link to a removed path anywhere in the repo
grep -rnE '\]\((\./)?(model-routing|runtime-matrix|harness-profiles|arbiter-checklist)\.md\)' \
  --include='*.md' . | grep -v '^./plans/' || echo "denylist clean"

# 2. every reference file is reachable by a resolved link
for f in plugins/orchestrate/skills/orchestrate/references/*.md \
         plugins/orchestrate/skills/orchestrate/runtimes/*.md; do
  b=$(basename "$f")
  grep -rq "($b)" plugins/orchestrate/skills/orchestrate README.md || echo "UNREACHABLE $b"
done

# 3. exactly one version everywhere
grep -rn '1\.8\.0\|2\.0\.0' plugins README.md site .claude-plugin --include='*.json' --include='*.md' --include='*.html'

# 4. presentation parity: R2 must state isolation + checks + arbiter review
grep -n 'R2' README.md site/index.html plugins/orchestrate/skills/orchestrate/references/safety-policy.md
```

## Success criteria

- [ ] Every goal in the proposal→owner map resolves to a file that exists in the final tree.
- [ ] Every phase's own exit grep passes before the next phase starts.
- [ ] The phase-7 tree sweep is clean: denylist, reachability, version, parity, boundary.
- [ ] `README.md` states which runs receive C3 review and which may be micro-arbiter-accepted.
- [ ] All four `1.8.0` sites carry the new version, or the release notes say why not.
- [ ] `ak plan validate` passes, and the plan is linked to its tracking issue.
- [ ] PR reviewed, replied, labeled, merged; post-merge CI recorded (none present).

## Risks and open questions

- **External readers may bookmark old reference paths.** Mitigation: major
  version bump, and the README upgrade section carries the move map. The
  denylist must therefore match link syntax `](path.md)`, not bare mentions, so
  the move map itself does not trip it.
- **A probabilistic signal can quietly become a policy authority.** This is the
  highest-severity risk in the plan; the red-team found it live in an earlier
  draft (the micro-arbiter's accept predicate was not a risk-tier test).
  Mitigation: the escalation matrix keys on a **recorded risk tier** and admits
  only R0/R1; R2/R3 always escalate; the boundary grep is a structural
  assertion, not a keyword scan.
- **The micro-arbiter can be dead on arrival or unsafe.** With no calibration
  history, either nothing clears the threshold or an uncalibrated number
  becomes a gate. Mitigation: the no-C3 path is **disabled until a C3-audited,
  per-classifier, unexpired calibration record exists**; first-run behaviour is
  "observe and log only"; malformed, pooled-across-classifiers or stale records
  fail closed to C3. The tier is a deterministic derivation from declared
  attributes, and a missing or non-`{R0,R1}` tier is treated as R2. Approval
  changes, dispatch emission and shared-state mutation are excluded
  structurally, independent of tier.
- **The unverified runtime stubs could read as a support roster.** Five notes
  describe runtimes this repository never mentions. Mitigation: each is a
  one-page fenced stub with an "unverified — not a support claim, not in
  inventory" banner and an as-of date; the adapter index separates verified
  from unverified; and the index states that only a live-inventory probe makes
  an adapter selectable, so a doc note can never cause a dispatch.
- **The auto-profiler could make the decision plane load-bearing.** If a
  classifier outage turned every capability `unverified`, the run would collapse
  to advisory-only. Mitigation: the classifier only **annotates** probe
  evidence into a separate `classifier_hint` block, may never set `state`,
  `approval`, `toolGating`, `isolation` or `cwdControl`, and `unverified` means
  "the deterministic probe did not prove it".
- **Classifier egress before the safety gate.** The router and optimizer carry
  job prompts and repo context. Mitigation: every decision-plane call is
  classified and recorded as R0/observe, runs with tool grants off, occurs after
  the safety gate confirms controls, and needs a recorded egress authority
  naming the provider and the content classes sent.
- **Prompt injection through normalized error text.** A hostile error string
  could steer triage. Mitigation: classifier input is delimited untrusted data
  with provenance labels; the taxonomy selects only among pre-declared actions;
  and a classified `PERMISSION`/`SANDBOX`/`AUTH` result must still hit the
  existing hard stop and can never set `approval`.
- **The graph optimizer is cost work, not safety work.** It must never merge
  away an independence requirement. Mitigation: it runs after routing, takes the
  maximum on every risk dimension and the intersection on every permission
  dimension, refuses merges across differing pins/isolation/authority, and is
  materialized into the immutable prepared input so resume never re-optimizes.
- **Scope creep into code.** The repo has no runtime; these are contracts the
  coordinator follows. Mitigation: no executable is added; verification is grep.

## Validation Log

### Session 1 — 2026-09-17
**Trigger:** `/ak:vibe --advice --ship` on the accepted P0–P3 brainstorm; plan created by `/ak:plan --tdd`.
**Questions asked:** 4 (pre-plan) + 3 (post-red-team)

#### Confirmed Decisions

- System-1 sourcing: provider-neutral classifier dispatched through a live-inventory candidate; Jev/TypeSafe is the reference implementation and one optional provider; deterministic policy alone when no classifier is available.
- Restructure: full clean move, no compatibility stubs.
- `runtimes/*.md`: capability maps + verification checklists, no copied flags or model ids.
- Visible scope: skill docs + `SKILL.md` + README + version bump; no landing-page redesign.
- Red-team: apply all 15 deduplicated, evidence-verified findings.
- Doc verification: no committed linter; per-phase grep assertions plus a phase-7 tree sweep.
- Version: `2.0.0`.

#### Verification Results

- Claims checked: 22
- Verified: 20 | Failed: 2 | Unverified: 0
- Tier: Full (7 phases → 4 verification roles)
- Evidence baseline: 56 relative markdown links in the skill tree; 9 files link the six docs slated for removal or relocation; 4 sites hard-code `1.8.0`; `README.md:73` and `site/index.html:588` both drift from `model-routing.md:76`.

Failures and resolution:

1. `plan.md` frontmatter declared `issue: 3`, but issue 3 does not exist. Resolution: create the tracking issue in pipeline step 4, then write its real number into the frontmatter and rename the plan directory to `{date}-{issue}-{slug}`.
2. `arbiter-checklist.md` was listed for deletion in both phase 4 and phase 7. Resolution: **all** deletions moved to phase 7 so the path flip is atomic, and phase 7's list owns every one of them.

#### Whole-Plan Consistency Sweep

- `job-spec.md` owns machine fields in phases 1, 3, 4, 5, and 7 — no duplicate ownership.
- `runtime-profile.md` is created in phase 1 and extended in phases 4 and 6 — single-owner growth.
- `decision-plane.md` is created in phase 3 and extended in phases 4 and 5 — single-owner growth.
- Every deleted file heading has a named destination (phase 1 destination table).
- Dependency order is acyclic: 1→2→3→4→5, 6←1, 7←(5,6).
- No phase ends with a red gate: the denylist is evaluated only in phase 7, and link checks are scoped to the files a phase changed.
- Unresolved contradictions after this sweep: none.

## Red Team Review

Four hostile reviewers (Security Adversary, Failure Mode Analyst, Assumption
Destroyer, Scope & Complexity Critic) reviewed this plan against the live tree.
34 raw findings → 15 after deduplication and the evidence filter. Every accepted
finding's cited evidence was independently re-verified before adjudication.

| # | Sev | Finding | Lens | Disposition |
|---|-----|---------|------|-------------|
| 1 | Critical | Accept-without-C3 predicate keyed on `effect`/`importance`, never risk tier; R2 reachable with no arbiter | Security | Accept |
| 2 | Critical | No calibration floor, threshold owner, or fail-closed default; uncalibrated signal becomes a gate | Security, Assumption | Accept |
| 3 | Critical | Integrity gate red until phase 7; deletes precede repoints | Failure, Scope | Accept |
| 4 | Critical | `dispatch-hardening.md` relink unowned; cites a `runtime-matrix` section that does not exist | Failure, Assumption | Accept |
| 5 | Critical | Verifier scope undefined; single-authority scan already false (README/site drift) and blind to it | Failure, Security, Scope, Assumption | Accept |
| 6 | Critical | Repo-root executable is unrequested scope, outside the plugin payload, contradicts skill-relative script rule | Scope, Assumption | Accept |
| 7 | Critical | Auto-profiler makes the decision plane load-bearing; classifier outage collapses the run | Failure | Accept |
| 8 | Critical | Classifier candidate never joins the per-run candidate set → plane inactive on all-internal runs | Failure, Assumption | Accept |
| 9 | High | Delete list wider than the absorption map: 5 harness-profiles sections, 4 runtime-matrix sections, `agy`, `Internal Branch`, family-independence rule unowned | Failure, Scope | Accept |
| 10 | High | Attacker-influenceable error text reaches the classifier; triage can bypass existing permission hard stop | Security | Accept |
| 11 | High | Provider calls dispatched before the safety gate; no egress authority; call-shape invariant unenforceable on prompt-only runtimes | Security, Failure | Accept |
| 12 | High | Decision traces carry classifier free text with no redaction or export-exclusion rule | Security | Accept |
| 13 | High | Optimizer runs before the signals it must obey; merges drop pins/isolation/authority; resume re-optimization orphans attempts | Failure, Security, Assumption | Accept |
| 14 | High | Router cannot raise a floor set too low by the user's `task` enum; independence as a probability can weaken a hard rule | Assumption | Accept |
| 15 | High | Published acceptance guarantee silently invalidated; the 9 checklist questions have no answering party on the no-C3 path; `1.8.0`/site drift unowned | Scope, Assumption, Failure | Accept |

Rejected after evidence review: none. Two findings were narrowed rather than
rejected — the `runtimes/` set is kept at the brainstorm's named list (an
explicit user decision) but every note must be `unverified` scaffolding until a
live probe exists, and the "one owning document" criterion was replaced by the
proposal→owner map because goals 3–5 legitimately share one contract.

### Whole-Plan Consistency Sweep (post-red-team)

- All 15 dispositions are reflected in the phase files; no phase claims a
  mitigation that lives only in this table.
- The escalation predicate, calibration floor, and profiler-annotation rules
  appear in phases 3 and 4 with one owner each.
- Deletion is single-owner: phase 7 only.
- The version appears once per surface, and phase 7 lists all four sites.
- No phase's verification block can pass while a later phase's obligation is
  outstanding.
- Unresolved contradictions: none.
