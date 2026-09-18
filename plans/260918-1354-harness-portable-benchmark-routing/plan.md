---
title: "Harness-portable distribution + benchmark-driven routing"
description: "Make the skill harness-agnostic and installable through the npx skills CLI, add benchmark evidence (success rate, cost per task, duration per reasoning effort) as a cached ranking input, and add a promotion/fail-safe chain, a correlated trace contract, and owner-fixed credential resolution."
status: pending
priority: P1
effort: 5d
issue: 8
branch: feat/harness-portable-benchmark-routing
tags: [feature, docs, orchestration, critical]
blockedBy: []
blocks: []
created: 2026-09-18
---

# Harness-portable distribution + benchmark-driven routing

## Overview

The skill currently ships as a Claude Code plugin and routes from live probe
evidence alone. Both limits are now measurable against the tree, not assumed:

- **The payload is already portable; the packaging and the framing are not.**
  `SKILL.md` carries no `allowed-tools`, no `context: fork` and no Hooks — the three
  features the Agent Skills ecosystem treats as harness-specific — so the payload is
  already spec-shaped. What blocks other harnesses is the framing and the install
  documentation: `README.md:5` says "**Multi-runtime agent orchestration for Claude
  Code.**", `README.md:108` is "### As a Claude Code plugin", and the landing-page
  kicker at `site/index.html:412` (EN) and `:879` (VI) reads "A Claude Code Skill" /
  "Một Claude Code Skill". Two install paths are already documented (`README.md:108`
  marketplace and `README.md:120` plain-skill copy), and neither is the `npx skills`
  CLI this release adds.
- **Routing ranks on availability and control, never on outcome.** The current
  hard filter answers "can this candidate run the job" and "is it controlled
  enough". Nothing answers "is it *good* at this job, and at what cost and
  latency". A candidate can be eligible, cheap and slow at the same time, and the
  tie-break is unspecified.
- **Failure handling stops at the job boundary.** `failure-modes.md` owns hard
  stops, and the `## Fallbacks` section of `routing-policy.md` requires declared
  fallback entries to be evaluated "through the same live gate and **in declared
  order**" — but there is no promotion chain: a runtime that hits a quota limit
  mid-run has no defined successor beyond the declared list, no bounded budget that
  composes with the existing `retry.max_attempts`, and no terminal fail-safe state.
- **Telemetry exists and is partly correlated, but only at run and job level.**
  `events.jsonl` and `state.json` already share `runId` and `jobId`
  (`event-protocol.md:40-42`, `job-spec.md:154`), so the corpus is not uncorrelated.
  What is missing is an attempt-level pairing rule for a promoted attempt, any span
  identifier to separate operations inside one attempt, and any identifier at all on
  `decisions.jsonl` (`decision-plane.md:365-377`) — so "why did attempt 3 land on
  runtime Y" still needs timestamp matching across four files.
- **Credential handling is unspecified.** `decision-plane.md` requires a recorded
  egress authority and `safety-policy.md` refuses secrets at intake, but neither
  says where a provider key is *read* from. The reference provider needs one, so
  today the answer is implicit.

Five structural moves, one per defect:

1. **Separate portability from packaging.** One `harness-portability.md` owns the
   Agent Skills conformance surface, what the payload may not depend on, and every
   install/discovery path per harness and per CLI.
2. **Add an evidence class, not an authority.** `benchmark-evidence.md` owns
   benchmark records keyed by `(provider, model, effort)`, the untrusted-input rules
   that make fetched numbers safe to parse, and a **durable cross-run cache** at
   `.orchestrate/benchmarks.json` with owner-fixed TTL bounds. Routing may **rank**
   with them; eligibility, floors, tier and controls stay with deterministic policy.
   This preserves the 2.0.0/2.1.0 invariant that a probabilistic input may only
   tighten a gate, never widen it.
3. **Bound the failure chain without discarding what exists.** `fallback-policy.md`
   owns promotion triggers, the chain, the per-concern control comparison, the budget
   and the terminal fail-safe. It **composes with** two mechanisms the tree already
   has rather than replacing them: the declared `fallback_runtime` order
   (`routing-policy.md:191-197`) supplies the head of the chain, and the bounded retry
   policy (`job-spec.md:69-71`) runs first so promotion happens only after it is
   exhausted. One rule carries the safety weight: a **verification failure is never a
   promotion trigger**, and neither is a permission or authorization stop.
4. **Extend the record that already exists.** `trace-and-logging.md` owns the span
   identifiers and the correlation rule, and states its boundary against the four
   owners it joins: `event-protocol.md` keeps the envelope and kinds, `job-spec.md`
   keeps `state.json`, `decision-plane.md` keeps the decision-trace fields, and
   `output-layout.md` keeps the layout. The attempt identity stays the ordinal the
   attempt record already carries; **no second spelling is introduced**.
5. **Fix the credential path.** `decision-plane.md` owns the four-step
   `TYPESAFE_API_KEY` lookup order and the never-print / never-prompt rules.

Jev / TypeSafe stays what 2.0.0 made it: the reference decision-plane
implementation and one optional provider, never a requirement. The benchmark
sources are likewise named by URL and never copied by value.

## Goals

| # | Goal | Priority | Owning document |
|---|------|----------|-----------------|
| 1 | The skill **loads** on any Agent Skills harness, and states the capability set it needs to execute jobs | P0 | `references/harness-portability.md` |
| 2 | Install and discovery documented for the `npx skills` CLI (project, global, per-agent) alongside the two existing paths | P0 | `references/harness-portability.md` |
| 3 | Benchmark evidence — success rate, cost per task, task duration, per model per reasoning effort — as a ranking input, cached **between runs** with a configurable TTL and owner-fixed bounds | P0 | `references/benchmark-evidence.md` |
| 4 | A bounded promotion chain that honors a declared `fallback_runtime` order and composes with the existing retry budget, ending in a logged fail-safe state | P0 | `references/fallback-policy.md` |
| 5 | Span identifiers and one correlation rule over the identity the corpus already has, joining events, decisions, metrics, attempts and verdicts | P1 | `references/trace-and-logging.md` |
| 6 | Owner-fixed `TYPESAFE_API_KEY` resolution order, child-environment delivery, and never-print / never-prompt / never-commit rules | P1 | `references/decision-plane.md` |
| 7 | Reader surfaces updated, including an animated pipeline diagram on the landing page, plus an agent-context file | P1 | `README.md`, `site/index.html`, `AGENTS.md`, `CLAUDE.md` |

Goals 1–2 share one document on purpose: both answer "how does this payload reach a
harness", one at the contract level and one at the CLI level. The table above is the
machine-checkable goal→owner map.

## Non-goals

- No daemon, scheduler, account pool, hosted service, or provider adapter for
  *running* jobs.
- No change to the R0–R3 model, the worktree rule, or the requirement that R2 and
  above receive arbiter review.
- **No benchmark value, model name, or leaderboard row is copied into the skill.**
  Sources are named by URL; values are fetched at run time.
- **No benchmark-driven gate change.** Benchmarks rank candidates that already
  passed the hard filter. They cannot set eligibility, a floor, a tier, a control,
  an approval, or an egress authority.
- **No replacement of the declared fallback mechanism.** `fallback_runtime` keeps its
  declared-order semantics; promotion extends it rather than superseding it.
- **No second spelling of the attempt identity.** The ordinal the attempt record
  already uses is the identity; nothing named `attemptId` is introduced.
- **No second pipeline vocabulary on the landing page.** The new diagram is presented
  as the routing hops of the pipeline the page already lists as seven stages.
- No new executable. The repo ships no code, and verification stays grep-based.
- No landing-page redesign. The animated diagram is an addition inside the existing
  editorial style.
- No automatic credential acquisition. The skill reads a key from a documented
  location; it never asks for one interactively and never writes one anywhere.

## Deliverable shape

```text
plugins/orchestrate/skills/orchestrate/
  SKILL.md                              # portable framing, new pipeline hops, links
  references/
    harness-portability.md              # NEW  spec surface, forbidden deps, install/discovery
    benchmark-evidence.md               # NEW  record schema, sources, effort ladder, cache
    fallback-policy.md                  # NEW  promotion triggers, chain, budget, fail-safe
    trace-and-logging.md                # NEW  trace envelope, correlation, retention, export
    routing-policy.md                   # ranking step gains benchmark evidence; declared fallback order preserved
    job-spec.md                         # benchmark + effort fields, promotion fields, run-level harness, validation
    runtime-profile.md                  # benchmark evidence is not probe evidence
    decision-plane.md                   # key resolution order; decision trace gains the identifiers it lacks
    safety-policy.md                    # pointer: never print, never prompt, never commit
    failure-modes.md                    # three failure classes; the permission stop stays a hard stop
    verification.md                     # a promoted attempt clears the same gate
    event-protocol.md                   # envelope owner: gains spanId and parentSpanId
    output-layout.md                    # trace.jsonl, the cache's location outside the run dir, report completeness
    observation.md                      # events carry the identity; kinds stay owned elsewhere
    metrics-and-self-improvement.md     # local metrics are benchmark evidence of record
.gitignore                              # .env, .env.*, and the durable cache directory
README.md                               # portability, install, benchmark, fallback, trace, credentials
site/index.html                         # same, plus the animated diagram (EN + VI)
AGENTS.md                               # NEW  agent context (harness-neutral, primary)
CLAUDE.md                               # NEW  pointer to AGENTS.md only
```

## Phases

| Phase | Name | Status |
|---|---|---|
| 1 | [Harness portability and distribution](phase-01-harness-portability.md) | Pending |
| 2 | [Benchmark evidence and cache](phase-02-benchmark-evidence.md) | Pending |
| 3 | [Credential resolution and egress](phase-03-credential-resolution.md) | Pending |
| 4 | [Promotion chain and fail-safe](phase-04-promotion-fallback.md) | Pending |
| 5 | [Correlated trace and logging](phase-05-trace-logging.md) | Pending |
| 6 | [Reader surfaces and animated diagram](phase-06-reader-surfaces.md) | Pending |
| 7 | [Agent context and release](phase-07-agent-context-release.md) | Pending |

Phases 1→2→3→4→5 are strictly sequential: each edits a document the next one
extends, and phase 2's ranking step is what phase 4 promotes within. Phase 6
depends on 1–5 because it summarizes them. Phase 7 depends on 6 and owns the
version bump and the whole-tree sweep.

## Test strategy (TDD)

The deliverable is a normative document set with no runtime, so its executable
tests are document-integrity assertions. There is no committed linter; each phase
ends with the greps it needs, and phase 7 runs the full tree sweep.

**Write the assertion first, in the same phase that authors the text.** For each
new invariant the plan states the grep and its expected output *before* the
prose, so a passing grep cannot be satisfied by rewording after the fact. Every
new assertion carries a control that proves it can fail — phase 7's sweep carries
the shared ones, and each phase carries its own.

**Baseline honesty, and a correction after red-team.** For the four new reference
documents the assertions are genuinely red-first: the files do not exist, so a
green run at a phase exit is only possible after the file exists with the required
tokens. But three of phase 6's originally planned assertions were **already green
before any work**: `prefers-reduced-motion` matches because a blanket rule exists
at `site/index.html:384-386`, `aria-label` matches on the language and theme
switchers, and the external-request pattern returns `0` on a page that has no
external request to find. Phase 6 now records each baseline and asserts the
**change** instead — the `@keyframes` count rising from `0`, the SVG's own
`aria-labelledby`, a reduced-motion rule naming the diagram's selectors, and a
broadened external-request pattern. The same correction removed a
`sec-num`-count check that could not detect a duplicate.

| Test | What it proves | Enforced |
|------|----------------|----------|
| Portability surface | `harness-portability.md` names the spec surface and the forbidden dependencies | phase 1 |
| CLI reference | The `npx skills add` form is present on the reference, README and site | phases 1, 6 |
| Effort ladder | `benchmark-evidence.md` defines the normalized ladder and the raw-parameter rule | phase 2 |
| Ranking-only rule | `routing-policy.md` states benchmarks cannot set eligibility, floors or tier | phase 2 |
| Credential order | `decision-plane.md` carries the four paths in order, and the never-print rule | phase 3 |
| Promotion safety | `fallback-policy.md` states a verification failure is not a promotion trigger | phase 4 |
| Trace correlation | The span ids exist in the new document **and in their owners** (`event-protocol.md`, `decision-plane.md`), and the invented `attemptId` spelling appears nowhere | phase 5 |
| Cache lifetime | The cache path is outside the run tree and git-ignored, and the run tree does not list it | phases 2, 5 |
| Tree parity | The run-directory tree is identical in its three copies | phases 5, 6, 7 |
| Credential safety | The four paths exist in order, delivery is child-environment only, `.env` is ignored, and no dotenv file is tracked | phases 3, 7 |
| Promotion safety | A verification failure and a permission/authorization stop are both non-promoting, and the control comparison is per-concern | phase 4 |
| Constants fan-out | Each owner-fixed constant appears in its owner, in `job-spec.md` validation and in the README | phase 7 |
| Animation | The landing page animates from a recorded `@keyframes` baseline of `0`, names its own reduced-motion selectors, and adds no external request | phase 6 |
| Section numbering | `sec-num` values are contiguous and unique — not merely counted | phases 6, 7 |
| Boundary (carried over) | The accept predicate still has exactly one owner | phases 5, 7 |
| Parity (carried over) | R0–R3 clauses still survive on README and site | phases 6, 7 |
| i18n | Every `data-i18n` key resolves in both decks | phases 6, 7 |
| Peer reachability | Every reference and runtime note is linked by a **peer**, not only by the `SKILL.md` index row | phases 1, 2, 4, 5, 7 |
| No copied measurement | **Review item, not a grep.** A pasted leaderboard row is indistinguishable from prose | phase 2 and 6 review |

**What these assertions are and are not.** Grep proves that a sentence exists, a
link resolves, and a token is absent. It cannot prove that a promotion chain
terminates, that a benchmark record is real, that a cache is fresh, or that a key
was read from the right file. So the honest containment stack stays what 2.1.0
established: fail-closed wording, structural exclusions, the deterministic gate as
the actual authority, and an auditable record. No document in this set may
describe the greps as enforcement of a routing or safety rule.

## Change manifest (what a reviewer should be able to verify)

```bash
S=plugins/orchestrate/skills/orchestrate/references

# 1. New owners exist and are reachable FROM A PEER, not merely from the index row.
for f in harness-portability benchmark-evidence fallback-policy trace-and-logging; do
  test -f "$S/$f.md" || echo "MISSING $f.md"
  b="$f.md"
  peers=$(grep -rlE "\]\([^)]*/?$b\)" --include='*.md' --exclude="$b" \
    plugins/orchestrate/skills/orchestrate README.md | grep -v '/SKILL.md$' | wc -l)
  [ "$peers" -ge 1 ] || echo "UNREACHABLE-BY-PEER $b"
done

# 2. Portability: no forbidden dependency, EXCLUDING the document required to name them.
grep -rn 'context: fork\|^hooks:\|^allowed-tools:' plugins/orchestrate/skills/orchestrate \
  | grep -v harness-portability.md || echo "portability clean"

# 3. Install path documented on all three surfaces
for f in "$S/harness-portability.md" README.md site/index.html; do
  grep -q 'npx skills add bestagentkits/orchestrate' "$f" || echo "INSTALL PATH MISSING $f"
done

# 4. Benchmark evidence may rank, never gate; and the cache outlives a run
for f in "$S/benchmark-evidence.md" "$S/routing-policy.md"; do
  grep -q 'may not set' "$f" || echo "NEGATIVE RULE MISSING $f"
done
grep -q 'CACHE_TTL_MAX_HOURS' "$S/benchmark-evidence.md" || echo "TTL BOUND MISSING"
git check-ignore -q .orchestrate/benchmarks.json || echo "CACHE NOT IGNORED"

# 5. A failed check and a permission stop never promote; retry runs first
grep -q 'not a promotion trigger' "$S/fallback-policy.md" || echo "FAILED-CHECK RULE MISSING"
grep -q 'authorization or permission failure never promotes' "$S/fallback-policy.md" || echo "AUTH-STOP RULE MISSING"
grep -q 'max_attempts' "$S/fallback-policy.md" || echo "RETRY PRECEDENCE MISSING"
# BASELINE: red at phase entry -- the phrase is split by a line wrap at
# routing-policy.md:191-192, so this reports DECLARED ORDER LOST until task 4.2
# rewraps the sentence. That rewrap is a whitespace-only edit and is mandatory.
grep -q 'in declared order' "$S/routing-policy.md" || echo "DECLARED ORDER LOST"

# 6. Credentials: order once, delivery by child environment, nothing committed
grep -q 'inherited child environment' "$S/decision-plane.md" || echo "DELIVERY RULE MISSING"
test "$(grep -c 'process.env' "$S/safety-policy.md")" = 0 || echo "ORDER DUPLICATED"
test "$(git ls-files | grep -c '\(^\|/\)\.env$')" = 0 || echo "TRACKED DOTENV FILE"
grep -rn 'echo .*TYPESAFE_API_KEY\|print.*TYPESAFE_API_KEY' plugins README.md site AGENTS.md CLAUDE.md 2>/dev/null \
  && echo "KEY-PRINTING GUIDANCE" || echo "no key-printing guidance"

# 7. Trace correlation lives in the owners, and the invented spelling is absent
grep -q 'spanId' "$S/event-protocol.md" || echo "ENVELOPE NOT EXTENDED"
grep -q 'spanId' "$S/decision-plane.md" || echo "DECISION TRACE NOT JOINED"
grep -q 'trace.jsonl' "$S/output-layout.md" || echo "TRACE ARTIFACT MISSING"
grep -q 'traceStatus' "$S/output-layout.md" || echo "COMPLETENESS FIELD MISSING"
grep -rn 'attemptId' plugins README.md site && echo "INVENTED ID PRESENT" || echo "no invented id"

# 8. Landing page: animation, accessible name, no external request, numbering
python3 - <<'PY'
import re, pathlib
s = pathlib.Path("site/index.html").read_text(encoding="utf-8")
for label, cond in (
    ("keyframes present", "@keyframes" in s),
    ("inline svg present", "<svg" in s),
    ("diagram accessible name wired", 'aria-labelledby="flowCaption"' in s),
    ("reduced-motion names .flow", re.search(r'prefers-reduced-motion[^}]*\{[^}]*\.flow', s, re.S) is not None),
):
    if not cond: print("LANDING FAIL", label)
ext = re.findall(r'<img[^>]+src="https?:|<link[^>]+href="https?:|url\(https?:|srcset=|@font-face|<iframe|xlink:href="https?:', s)
if ext: print("EXTERNAL REQUEST", ext[:3])
nums = [v.strip() for v in re.findall(r'class="sec-num">([^<]+)<', s)]
dups = sorted({n for n in nums if nums.count(n) > 1})
if dups: print("SEC-NUM DUPLICATE", dups)
if nums != ["%02d" % i for i in range(1, len(nums) + 1)]: print("SEC-NUM NOT CONTIGUOUS", nums)
print("landing ok" if not dups else "landing failed")
PY

# 9. No shipped surface still brands the skill Claude-only
grep -n 'Claude Code Skill' README.md site/index.html && echo "CLAUDE-ONLY BRANDING" || echo "no claude-only branding"

# 10. Version, including the sweep's own literals
test "$(grep -c '2\.2\.0' plugins/orchestrate/.claude-plugin/plugin.json)" = 1 || echo "FAIL plugin.json"
test "$(grep -c '2\.2\.0' plugins/orchestrate/skills/orchestrate/SKILL.md)" = 1 || echo "FAIL SKILL.md"
test "$(grep -c '2\.2\.0' site/index.html)" = 3 || echo "FAIL site"
test "$(grep -c '2\\.2\\.0' README.md)" -ge 1 || echo "FAIL sweep literals"
grep -rn '2\.1\.0' plugins site .claude-plugin --include='*.json' --include='*.md' --include='*.html' \
  && echo "FAIL stale version" || echo "version clean"
```

## Success criteria

- [ ] Every goal in the goal→owner map resolves to a file that exists in the final tree.
- [ ] `SKILL.md` contains no harness-specific frontmatter dependency, and no shipped surface still says "Claude Code Skill".
- [ ] `npx skills add bestagentkits/orchestrate` is documented, both existing install paths survive, and the document explains that no CLI is required to run the skill.
- [ ] Benchmarks rank and never gate, the cache is durable and git-ignored, and a degraded ranking is disclosed in the report rather than reported as success.
- [ ] A verification failure and a permission/authorization stop never promote; the declared `fallback_runtime` order is preserved; retry runs before promotion; the control comparison is per-concern with no trade-off.
- [ ] The span identifiers exist in the new document **and in their owners**, the attempt identity is not duplicated under a second name, and the decision trace is joinable for the first time.
- [ ] The key resolution order is exactly the four documented paths, delivery is child-environment only, `.env` is ignored, no dotenv file is tracked, and nothing prints or prompts for a key.
- [ ] README and the landing page both describe the new behaviour, the landing page animates with a localized accessible name, and the run-directory tree is identical in its three copies.
- [ ] Existing invariants survive: the accept predicate has one owner, R0–R3 parity holds, i18n is complete, and every reference is reachable from a peer.
- [ ] `ak plan validate` passes and the plan is linked to its tracking issue.
- [ ] PR reviewed, replied, labeled `ready to ship stable`, merged; post-merge CI (Pages) recorded.

## Risks and open questions

- **Benchmark data becomes a de facto authority.** This is the highest-severity risk: the user's request is to route *by* benchmarks, and the 2.0.0/2.1.0 invariant is that no probabilistic input may widen a gate. Mitigation: benchmark evidence is a **ranking input inside the surviving eligible set**, it may never add or restore a candidate, and the negative form ("may not set eligibility, a floor, a tier, a control, or an approval") is asserted by grep on two files. Availability still comes from the live probe, never from the cache.
- **Effort ladders are not comparable across vendors.** OpenAI exposes a discrete reasoning-effort parameter, Anthropic exposes a thinking budget, and other providers expose their own scale. Comparing a vendor's "medium" to another's is an assumption. Mitigation: the record stores the **normalized ladder position and the vendor's raw parameter**; a candidate whose ladder cannot be mapped is excluded from cross-vendor comparison and ranked only within its own family, and the record marks which comparison class it belongs to.
- **The local machine's provider set is not the benchmark's population.** The user's available models may be a strict subset of a leaderboard, and a benchmark may cover a provider the user cannot reach. Mitigation: benchmark search runs **per candidate that already passed the hard filter**, so an unreachable provider is never fetched, and a candidate with no benchmark record is ranked last rather than assumed average.
- **Cost per task is not a price list.** Benchmarks report observed cost per task, which includes token counts the job will not reproduce. Mitigation: cost is a ranking signal with a recorded source and retrieval time, the record states that it is an observed average and not a quote, and a budget ceiling is still enforced by the deterministic filter.
- **Promotion degenerates into retry-until-pass.** A pool of runtimes plus a failure signal is one loose rule away from "try another model until the check goes green". Mitigation: promotion triggers are **infrastructure failures only** (quota, auth, outage, crash, transport), a verification failure escalates instead, the budget is bounded, and the promoted attempt must clear the same gate — a second content failure goes to the arbiter, not to a third runtime.
- **Promotion bypasses the safety gate.** Promoting to a candidate with weaker controls would launder a control decision. Mitigation: the chain is built from the already-eligible ranked set, a promoted candidate is re-probed live, floors and tier are unchanged, and the safety gate is not re-decided. A chain with no eligible successor fails safe to `blocked`.
- **The cache goes stale and routes on obsolete data.** Mitigation: the TTL is configurable in the job spec with an owner-fixed maximum, a stale entry is refreshed before it ranks, a failed refresh degrades to "no benchmark record" rather than to a stale number, and the cache never answers availability.
- **Traces leak secrets or private repo content.** Mitigation: trace records are schema-closed with enumerated kinds and no free text, redaction happens on write, and the trace is excluded from diagnostic exports unless reviewed — the same rule the decision trace already carries.
- **The credential order is read as permission to keep keys in a repo.** A `.env` next to the skill could be committed. Mitigation: the document states the order is a **read** order, that a repo-tracked `.env` remains refused by `safety-policy.md`, that the key is never printed to session output, never committed, and never requested interactively, and that a missing key disables the plane rather than prompting.
- **Four new references could duplicate existing owners.** Mitigation: each new document owns exactly one concern, the existing owners keep theirs, and every cross-reference is a pointer rather than a restatement; the phase-7 sweep re-checks the boundary and parity invariants that would catch a second copy.
- **A harness could be claimed as supported without a live check.** The `npx skills` CLI lists install paths for many harnesses, which is not evidence that *this* payload loads and behaves there. Mitigation: the portability document separates "the spec says this is portable" from "this was verified on that harness", marks unverified harnesses as unverified exactly as `runtimes/README.md` does for runtimes, and requires a live check before a harness is listed as verified.
- **Scope creep into a second landing-page redesign.** Mitigation: the diagram is
  additive inside the existing style and is presented as the routing hops of the
  pipeline the page already lists as seven stages, so the two visuals do not
  compete. Its assertions are artifact-specific rather than pre-satisfied, and no
  existing section is restructured.

### Risks added by the red-team pass

- **The benchmark cache is useless if it is run-scoped.** This was the plan's own
  most serious defect: a per-run artifact cannot serve a later run, so the requested
  speed-up would never happen. Mitigation: task 2.1 step 10 fixes the lifetime as
  project-scoped at `.orchestrate/benchmarks.json`, outside every run directory;
  phase 5's tree parity check asserts the run tree does *not* list it; and the
  correlation rule carries an explicit exemption scoped to that one artifact.
- **A working-tree credential can silently shadow the user's own key.** With the
  user-specified order, a cloned project's `.env` wins over the skill's. The order is
  a requirement, so the mitigation is disclosure and trust annotation rather than
  reordering: a shadowed source is reported with a `credential-shadowed` token, the
  source's trust class is recorded, and the egress authorization must name the
  credential source so the run authorizes the identity that actually calls out.
- **The key would leak through the delivery path, not through an `echo`.** A markdown
  skill can only authenticate by handing the value to a subprocess, and argv is
  persisted for diagnosis. Mitigation: the value is delivered **only** through the
  inherited child environment, never as an argument, on stdin, or in a prompt, the
  never-print enumeration names those surfaces, and the sweep asserts no argv form
  is documented.
- **Retry and promotion could multiply into an unbounded dispatch storm.** Each
  mechanism was bounded on its own and nothing bounded their composition.
  Mitigation: retries run first within `retry.max_attempts`, promotion only follows
  exhaustion, and the plan states the single combined ceiling
  `(1 + maxPromotions) x max(1, max_attempts)`.
- **A promotion could launder a control decision.** Promotion to a differently
  controlled candidate would re-decide what the safety gate decided. Mitigation: the
  chain excludes any candidate weaker on **any one** of the six control concerns in
  `safety-policy.md:65-90`; a permission or authorization stop is never a promotion
  trigger; and what re-runs on promotion (availability, controls) is stated
  separately from what does not (tier, approval, egress authority) in both owners.
- **"Same or stronger controls" was an undefined predicate.** Mitigation: task 4.1
  step 8 replaces it with a per-concern comparison anchored to the six documented
  concerns, with two worked cases and an asserted sentence.
- **A fetched page could decide the route.** The parsed number *is* the ranking
  order, so an injected value moves a candidate to the head of the chain.
  Mitigation: bounds on every numeric field, a two-source agreement floor, a
  dropped-imperative rule, a domain allowlist with no redirect following, a reject
  path that yields no record, and a hostile-page fixture that must produce no record.
- **The trace could be silently partial.** "The report must say so" had nothing to
  write into, because `report.md` had no schema owner. Mitigation: `output-layout.md`
  gains a `traceStatus` field with `complete`/`partial`/`absent`, a trace-write
  failure is the third failure class in `failure-modes.md` and never consumes a
  promotion, and phase 7 asserts the field exists.
- **A promoted attempt had no identity to be recorded under.** Mitigation: the plan no
  longer invents an identifier; it reuses the attempt ordinal the record already
  carries, states the retry-versus-promotion pairing rule, and asserts the invented
  spelling appears nowhere.
- **Three of phase 6's assertions would have passed before the work.** Mitigation:
  each records its baseline and asserts the change, and the `sec-num` count became a
  contiguity-and-uniqueness check.
- **The release gate would have been red by construction.** The sweep hard-codes the
  version by exact count, and no step updated those literals. Mitigation: task 7.2
  step 4 updates them in the same edit as the bump and states that this is a literal
  update, not a weakening.

## Validation Log

### Session 1 — 2026-09-18
**Trigger:** `/ak:vibe --advice --ship` on a 7-item improvement request; plan created by `/ak:plan --tdd`.
**Questions asked:** 3 (pre-plan)

#### Confirmed Decisions

- Harness portability: one owner document for both the spec surface and the CLI install paths.
- Benchmark authority: rank-only. Eligibility, floors, tier, controls and approval stay deterministic. This resolves the request's "route by benchmark" against the 2.0.0/2.1.0 invariant without weakening either.
- Effort: a new routing dimension recorded as normalized ladder position plus the vendor's raw parameter.
- Promotion triggers: infrastructure failure only; a verification failure escalates.
- Credential sources: read-only resolution in four steps; a missing key disables the plane and never prompts.
- Version: `2.2.0` (additive; no path is removed, so not major).
- Verification: grep assertions plus controls, with the "no copied measurement" rule explicitly out of grep's reach.

#### Verification Results

- Claims checked against the tree at planning time: 12
- Verified: 8 | **Failed: 4** — all four were citation errors, corrected after the red-team fact-check (see the Red Team Review for the evidence).
- Evidence baseline, corrected: `SKILL.md` has no `allowed-tools`, `context: fork` or Hooks; `claude` is absent from this host while `pi`, `omp`, `npx` and `node` are present; the Claude-only framing is `README.md:5`, `README.md:108`, `site/index.html:412` and `site/index.html:879` — **not** `README.md:8`; a second install path exists at `README.md:120`; the telemetry artifacts already share `runId` and `jobId` (`event-protocol.md:40-42`, `job-spec.md:154`), so the real gap is a span identifier, an attempt-pairing rule and any identifier on `decisions.jsonl`; `decision-plane.md` specifies an egress authority but no key source, and its `:82` states there is no new credential category.

#### Whole-Plan Consistency Sweep

- Owner map: each of the 7 goals names exactly one owning document; no document owns two goals, and `harness-portability.md` owns goals 1–2 by explicit exception with its rationale stated.
- Single-owner growth: `decision-plane.md` is extended in phase 3 and joined in phase 5 — sequential, no parallel writer.
- `routing-policy.md` is edited in phase 2 (ranking) and phase 4 (promotion pointer plus the preserved declared-order text) — sequential.
- `output-layout.md` keeps the directory tree, the cache's location and the report's completeness field; `trace-and-logging.md` owns the span identifiers and the correlation rule; `event-protocol.md` keeps the envelope and kinds. The boundary is stated in all three after the red-team correction.
- `job-spec.md` is edited by phases 1, 2, 4 and 5 — sequential, and each names what it adds.
- Dependency order is acyclic: 1→2→3→4→5, 6←(1..5), 7←6.
- Unresolved contradictions after this sweep: none.

## Red Team Review

Four hostile reviewers (Security Adversary, Failure Mode Analyst, Assumption Destroyer, Scope & Complexity Critic) read the full plan set and verified their claims against the tree at `1993a8b`. **40 raw findings → 28 distinct defects after deduplication.** Every finding carried `file:line` evidence, so none was rejected by the evidence filter.

The documented cap is 15 findings. It was exceeded deliberately here: the surviving Critical and High clusters were each independently evidence-verified, and several of them make the plan unimplementable as written — a phase whose exit gate can never pass, a cache whose TTL can never do anything, and a release step that guarantees a red gate. Capping at 15 would have meant shipping those knowingly.

### Critical and High findings, adjudicated

| # | Sev | Finding | Lens | Disposition |
|---|-----|---------|------|-------------|
| 1 | Critical | Phase 1's exit gate can never print `portability clean`, because the document the phase requires contains the very token the gate greps for; the test matrix already knew the right expectation while the verification block contradicted it, and `plan.md` and phase 7 inherited the same bug | Failure | **Accept** — the check now excludes `harness-portability.md`, and phase 1 also asserts the real Claude-only surfaces so phase 6 is accountable |
| 2 | Critical | The benchmark cache is placed in `<run-dir>/`, a per-run directory, while its control is a wall-clock TTL whose whole purpose is to survive between runs — so the TTL is unreachable and the requested speed-up never happens | Assumption, Failure | **Accept** — the cache is now project-scoped at `.orchestrate/benchmarks.json`, outside every run tree, git-ignored, with an explicit correlation exemption and asserted TTL bounds |
| 3 | Critical | Three of the four credential read locations live inside a working tree and `.gitignore` has no dotenv rule, so the documented path can be committed — and the default `npx skills` install symlinks into the source payload | Assumption, Security | **Accept** — `.env`/`.env.*` (with `!.env.example`) added to `.gitignore` in phase 3, with a tracked-dotenv assertion in the sweep |
| 4 | Critical | The plan never says how the key reaches the subprocess, and every available path is one `safety-policy.md:125-131` already forbids; the phase's only leak check matches `echo`/`print` idioms | Security | **Accept** — delivery is now the inherited child environment only, never argv, stdin or a prompt; the never-print list names those surfaces and an argv assertion was added |
| 5 | Critical | The plan invents `attemptId`, which exists nowhere in the tree, while `event-protocol.md` owns the envelope and already carries `runId`/`jobId`/`attempt` — and phase 5 never touches that owner, so the join matches nothing | Security, Scope, Failure | **Accept** — the `attempt` ordinal is the identity, `event-protocol.md` and `job-spec.md` are phase-5 targets, and the invented spelling is asserted absent |
| 6 | Critical | Phase 4 replaces the declared `fallback_runtime` order and the existing "reruns the full capability and risk gate" rule with a benchmark-ranked chain, and never mentions the field that already exists | Security, Assumption, Failure | **Accept** — declared order is the head of the chain and benchmark ranking fills the tail; what re-runs (availability, controls) and what does not (tier, approval, egress) is stated in both owners |
| 7 | Critical | Phase 2's premise is false (the telemetry artifacts already share `runId`), phase 5's join table names the wrong event owner, and `decisions.jsonl` carries no identifier at all — the real gap is never stated | Scope, Security | **Accept** — the plan now states the accurate baseline and the three genuine gaps |
| 8 | Critical | Phase 2 puts `effortLevel`/`effortRaw` beside the job-level `model`, contradicting the per-attempt aggregate doctrine and collapsing across promoted attempts; it names one of five consumers | Scope | **Accept** — the fields moved inside `attemptRecords[]`, and three consumers are named |
| 9 | Critical | The run-directory tree is duplicated in three documents and only one is updated; both copies are already missing `decisions.jsonl` and `calibration.json` | Assumption, Scope | **Accept** — all three copies updated and a tree-parity check added |
| 10 | High | Permission and authorization failures are listed as promotion triggers, contradicting the hard stop in `failure-modes.md:9-12,23-24` — promotion would launder a control decision | Failure | **Accept** — authorization and permission stops are explicitly never a promotion trigger |
| 11 | High | `fallback.maxPromotions` silently collides with the existing bounded retry in `job-spec.md:69-71`; nothing states which budget an event consumes or what the combined ceiling is | Assumption, Failure | **Accept** — retry runs first, promotion follows exhaustion, and the combined ceiling is stated as one formula |
| 12 | High | "The same or stronger controls" is undefined, so promotion can land an R2 job on a prompt-only candidate | Security | **Accept** — a per-concern comparison anchored to the six documented concerns, with two worked cases and an assertion |
| 13 | High | Benchmark numbers parsed from fetched pages decide both the route and the chain, defended by one unasserted prose sentence; the standard `decision-plane.md` already applies to hostile input is stricter | Security | **Accept** — domain allowlist, numeric bounds, a two-source agreement floor, imperative draining, a reject path, and a hostile-page fixture |
| 14 | High | No phase defines who fetches a benchmark, and phase 1's minimum harness capability set has no network — so the headline feature can degrade to the pre-existing ordering on every run and report success | Failure | **Accept** — the fetch mechanism, its egress authorization, its bounds and a `benchmark-degraded` report token are now specified |
| 15 | High | A trace-write failure is unclassified, unreportable and unasserted; `report.md` has no schema owner, so "the report must say so" had no field to write into | Failure | **Accept** — a third non-promoting failure class plus a `traceStatus` field owned by `output-layout.md` |
| 16 | High | "The benchmark step runs after the safety gate" is false in the documented pipeline and would require `routing-policy.md` to restate the gate, which its own line 21 forbids | Failure | **Accept** — replaced with the verifiable claim about the hard-filter survivor set, and the gate-ordering claim is asserted absent |
| 17 | High | Credential resolution is added while three shipped statements promise there is no credential category, and no step reconciles them | Scope, Security | **Accept** — `decision-plane.md:82` and the two README lines are reconciled, and the README copy is declared a parity-checked summary |
| 18 | High | `harness: unknown` is mandated with no schema to write into — no artifact has a `harness` field | Scope | **Accept** — phase 1 now owns a run-level `harness` field in `job-spec.md` |
| 19 | High | The landing page's actual Claude-only branding (the EN and VI kickers) is never scheduled for a fix, and phase 6 orders a rewrite of a string that is not in the README | Failure, Scope | **Accept** — tasks 6.1 and 6.2 target the four real surfaces, with a sweep check that neither file still says "Claude Code Skill" |
| 20 | High | Several of phase 6's assertions are already green before the work (`prefers-reduced-motion` at `site:384-386`, `aria-label` on the switchers), so they cannot prove the diagram | Security, Assumption, Scope | **Accept** — each asserts a recorded baseline change, and the `sec-num` count became a contiguity check |
| 21 | High | A `data-i18n` key on the `<svg>` would make Vietnamese mode delete the entire diagram, because localization replaces a node's children — and the i18n check would still report clean | Scope | **Accept** — the accessible name comes from a localized `<figcaption>` referenced by `aria-labelledby` |
| 22 | High | Phase 7 guarantees a red release gate: the sweep's exact version literals are never updated, and the instruction names a `version:` key that does not exist at that level | Security, Failure, Scope | **Accept** — the literals are updated in the same edit as the bump, and the key is named as `metadata.version` |
| 23 | High | Phase 6 promises the landing page four capability sections with no task and no assertion for them | Scope | **Accept** — task 6.4 owns the page copy with its own keys and assertion |

### Medium findings, adjudicated

| # | Finding | Lens | Disposition |
|---|---------|------|-------------|
| 24 | The "reachability" control is wrong: peers link the new documents, so removing the `SKILL.md` index row leaves the check green | Security | **Accept** — all reachability checks now count peers and exclude `SKILL.md` |
| 25 | New owner-fixed constants (cache TTL, promotion budget) are deferred to authoring time and fanned out to no reader surface, unlike the calibration floors | Assumption | **Accept** — both are pinned now with defaults and maxima, and phase 7 asserts the fan-out |
| 26 | Phase 2 asserts the cache is listed in `output-layout.md` while deferring that edit to phase 5, so phase 2 can exit green with a false cross-reference | Assumption, Scope | **Accept** — resolved by the lifetime change: the cache is outside the run tree and phase 2 owns that statement |
| 27 | Phase 3 forbids restating the credential order while phase 6 mandates it | Assumption | **Accept** — `decision-plane.md` now states the README copy is parity-checked, not independent |
| 28 | Phase 1's portability promise is contradicted by its own capability list, and it names a `plugin.json` path that does not exist at the repo root | Assumption, Security | **Accept** — the promise is split into "loads" versus "executes", and the manifest paths are corrected |
| 29 | Phase 6's `sec-num` renumbering has no completion check and the insertion point is ambiguous | Failure, Scope | **Accept** — a contiguity-and-uniqueness check replaces the span count |
| 30 | The new nine-node diagram competes with the page's existing seven-stage pipeline | Scope | **Accept** — the section deck now names it as the routing-hops view of the same pipeline |
| 31 | Phase 1 states an R2 tier consequence for a harness without worktrees, outside the tier owner | Scope | **Accept** — replaced with a pointer; the tier rule stays in `safety-policy.md` |
| 32 | Four citation defects send the implementation to the wrong files (`README.md:8`, `routing-policy.md:141`, a nonexistent `## Independence` section, `## Selection` for `## Selection procedure`) | Security, Failure, Scope | **Accept** — every citation re-derived by grep and corrected |

### Rejected after evidence review

- **Reordering the credential precedence so the skill-owned location wins.** Rejected as a change to the plan's scope: the user specified the order explicitly, so it is a constraint, not a defect. The security concern behind the finding is real and is addressed by disclosure, trust annotation and the `.gitignore` rule instead. This is recorded in the plan as a deliberate constraint rather than a silent override.
- **Cutting the benchmark feature as too risky.** Rejected: it is the user's explicit request. The finding's substance (untrusted numbers deciding a route) was accepted and mitigated rather than used to cut requested scope.
- **Dropping the animated diagram to avoid the reduced-motion and i18n traps.** Rejected for the same reason; both traps are accepted as defects in the plan's instructions and fixed.

### Post-red-team advisory pass (kongming, `--advice` checkpoint)

A second read-only pass ran after the red-team corrections, as the `--advice`
checkpoint after the plan gates. It raised 12 items; I verified every checkable claim
against the pre-change tree before adopting any, and all 12 were accurate. The
dominant finding was a **class**, not an instance: the red team had fixed two
"gate that cannot pass" defects but never swept the class, and this pass found four
more, one of which spanned the two phases that own the reader-facing trees. Because
these gates are the plan's only verification mechanism and the Failure Protocol makes
a red gate a hard stop, the likely resolution under pressure would have been to edit
the assertion — which is indistinguishable, in the resulting diff, from weakening it.
The repair is therefore twofold: fix the four gates, and add a *record the baseline
first* step to every phase, which is the convention that would have caught all four.

| # | Gate defect (verified against the pre-change tree) | Repair |
|---|---|---|
| A1 | Phase 1's path loop reported **11 false positives** on an already-correct document: it extracts sibling markdown link text and generated artifact names (`runtimes.json`), then tests only two prefixes. Reproduced on `references/decision-plane.md`. | Replaced the sweep with an explicit path list plus the one negative check. |
| A2 | Phase 4's `grep -q 'in declared order'` returns **0** at entry: `routing-policy.md:191-192` splits the phrase across a line wrap. Task 4.2 said to *keep* the existing text, guaranteeing the assertion stays red. | Task 4.2 now requires a whitespace-only rewrap, with the red baseline recorded. |
| A3 | The tree-parity block reused in phases 5 and 6 **could never print `tree parity ok`**, three independent ways: the README copy is introduced by `plans/reports/…` not `<run-dir>/`; the landing-page copy is HTML with `├──` prefixes and no fence at all; and `graph.json` is in the normative tree and in neither copy. | Replaced the fence-anchored regex with an explicit normative file list, and added `graph.json` to task 5.6. |
| A4 | Phase 7's fan-out loop demanded `MINIMUM_SAMPLES` appear in `job-spec.md` and `README.md`, where it has never appeared: it is owned by `verification.md`, and `job-spec.md` uses the lowercase field `calibration.minimum_samples`. Measured `owner=1, jobspec=0, readme=0`. | Loop rescoped to the constants this release introduces; the carried-over constant gets an accurate shape assertion instead. |

| # | Gap found | Repair |
|---|---|---|
| B1 | Only the key variable was governed; a working-tree `.env` could still redirect **endpoint, base-URL or proxy**, sending content to an unapproved endpoint under an authorization naming a different source. | Task 3.4 now states that only the key is read from the four locations, and endpoint configuration comes from the process environment or not at all. |
| B2 | `safety-policy.md` was listed as a phase-3 target but **no task edited it**, and two shipped sentences (`safety-policy.md:121`, `SKILL.md:220`) still said credentials "are entered only by the user", contradicting never-prompt. | New task 3.4 lands the pointer and reconciles both sentences, stating which rule wins. |
| B3 | `credential-shadowed` reached only `report.md`, not the surface a user reads. | Added to `SKILL.md`'s report block. |
| B4 | Benchmark fetch was **per candidate**, not per `(candidate, effort level)`, so the corpus could hold one row per model and the effort-by-outcome request would be unmet. | Task 2.1 step 7 now enumerates the declared ladder, bounded by `EFFORT_LEVELS_MAX_PER_CANDIDATE`. |
| B5 | The **model-name join** was unspecified: a leaderboard names models in its own vocabulary, and a mis-join would rank a candidate on another model's numbers — invisible, because the trace payload is schema-closed. | Task 2.1 step 6 now requires an explicit per-source mapping with an unmatched name yielding no record. |
| B6 | The trace's bounds were named but **unpinned**, the same defect 2.1.0 had to fix for the calibration floors. | Task 5.1 step 8 now fixes `TRACE_MAX_RECORDS`, `TRACE_MAX_BYTES`, `TRACE_ROTATE_AT_BYTES`, `TRACE_RETAIN_RUNS`. |
| B7 | Two branding surfaces were outside the sweep because they lack the swept phrase: `.claude-plugin/marketplace.json:4` and `site/index.html:6` (the `<title>`). | Added to task 6.2's rebrand list and the phase-6 assertion. |
| B8 | The release answered "an agent-context file" with `CLAUDE.md`, naming the file after the one harness the release is un-branding. | Phase 7 now creates `AGENTS.md` as the primary and `CLAUDE.md` as a five-line pointer. |

Two things this pass affirmed rather than changed, recorded so the reasoning is not
re-litigated at PR review: benchmarks ranking the eligible set **does** deliver
"route by benchmark" (satisfying it more literally would mean letting a probabilistic
input widen a gate, repealing the 2.0.0/2.1.0 invariant), and the credential order
stays exactly as the user specified because it is a constraint, with the security
objection answered by disclosure rather than reordering.

### Whole-Plan Consistency Sweep (post-red-team)

- **Decision deltas applied:** the cache's lifetime and path; the attempt identity (ordinal, not a new id); the promotion chain's precedence against `fallback_runtime` and `retry`; the credential delivery mechanism and its trust annotation; the trace's ownership boundary across four files; the `harness` field's owner; the version-literal update; the tree-parity requirement; the landing page's accessible-name mechanism.
- **Stale-term search:** `attemptId` now appears only as a thing the plan forbids, and phase 5 asserts its absence. `floor_delta` does not appear in this plan. The word "cache" now always refers to the durable project-scoped artifact, never the probe cache owned by `runtime-profile.md`. The word "stage" is used for the seven README stages and "hop" for the diagram's nodes, including in the diagram's own deck.
- **Superseded implementation details:** the six originally planned landing-page assertions were replaced by artifact-specific ones; the `-L`-style count checks were replaced by uniqueness and contiguity; the phase-2 cross-reference to `output-layout.md` was resolved by the lifetime decision rather than by moving an edit.
- **Duplicate prose:** the credential order is stated once in `decision-plane.md` and the README copy is declared a parity-checked summary; the run-directory tree is normative in `output-layout.md` with two summaries under a parity check; the control-reversion rule is stated in `fallback-policy.md` and pointed to from `routing-policy.md`.
- **Reconciled:** `plan.md` summaries, the goal→owner map, the phase dependency chain, the success criteria and the risks table all reflect the applied findings; no phase now asserts a token another phase is responsible for creating, except where the phase order guarantees it (phases 1→5 are strictly sequential, and phase 6 depends on all five).
- **Unresolved contradictions: none.**
- **Assertion baselines:** every phase now records each new assertion's value against the pre-change tree before editing, and names which assertions are deliberately red at entry and what turns them green. This convention exists because six assertions in the first draft could not have changed state at all; it is recorded in phase 1 task 1.3 and mirrored in the phases that introduce red-first gates.

**Interpretation recorded, not open:** whether "next promotion" means the next-ranked eligible candidate or a user-curated list. The request's wording is ambiguous, but the tree already provides a user-ordered list in `fallback_runtime`, so no new mechanism is needed: the declared order is the head of the chain and the benchmark ranking fills the tail. The plan implements that reading and states it in `fallback-policy.md` under `## Terminology`, so a reader who meant something else can see exactly what was assumed.
