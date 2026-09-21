# Contract reconciliation register — issue #15

Milestone 1 of the issue #15 goal. This register is the required "contract analysis
showing conflicts found and how ownership was resolved" deliverable, and it is written
**before** any normative edit, because the repository rule is to stop and report a
mismatch rather than pick the newer-looking text.

Every entry gives file-and-line evidence, names **the owner that wins**, and states what
must change. Where a real ownership ruling is needed rather than a mechanical fix, it is
listed under *Open ownership questions* instead of being decided here.

Scope of the audit: `SKILL.md` and all nineteen `references/*.md`, read against issue
#15's twelve required design changes and its acceptance checklist.

## Summary

| # | Conflict | Owner that wins | Class |
| --- | --- | --- | --- |
| C1 | Record key uses normalized effort, not runtime + real mode | `benchmark-evidence.md` | Contradiction with requirement |
| C2 | Cross-vendor comparability restriction not consumed | `benchmark-evidence.md` | Consumer gap |
| C3 | "Comparable task class" referenced but not representable | `benchmark-evidence.md` | Missing dimension |
| C4 | No cost-dimension owner; one USD field conflates cash and price | `metrics-and-self-improvement.md` | Missing owner |
| C5 | `MINIMUM_SAMPLES` owned twice, under two names | `verification.md` | Direct ownership contradiction |
| C6 | Calibration validity rule restated in a non-owner | `verification.md` | Duplicated rule |
| C7 | Durable calibration unowned; placement contradicts run-local rule | `verification.md` | Contradiction + gap |
| C8 | Infrastructure vs content failure split has no owner | `metrics-and-self-improvement.md` | Missing owner |
| C9 | Micro-arbiter has no skip path when C3 is structural | `verification.md` | Missing rule |
| C10 | No value-of-information gate for the decision plane | `routing-policy.md` | Missing rule |
| C11 | Route-decision fields have no schema owner | `trace-and-logging.md` | Resolved by its existing answerability list |
| C12 | Load-bearing cost/quality schema in an on-demand reference | `metrics-and-self-improvement.md`, consumed via a policy-layer mediator | Resolved by existing precedent; residual risk recorded |
| C13 | Low-sample record may still be the deciding rank | `benchmark-evidence.md` | Contradiction with requirement |

## C1 — Route identity cannot distinguish real execution modes

**Evidence.** `benchmark-evidence.md:30` fixes the identity: "The key is the triple
`(provider, model, effortLevel)`." The record then carries three effort fields —
`effortLevel` (normalized), `effortRaw` ("the vendor's own parameter, verbatim") and
`effortClass` (`benchmark-evidence.md:38`) — and `benchmark-evidence.md:70-72` states that
`effortRaw`, not `effortLevel`, is the value a dispatch passes.

So the key is built from the *normalized label* while the value that determines real
execution sits outside it. Both failure directions issue #15 names are therefore live:
two raw modes that normalize to the same label collapse into one candidate, and two
normalized labels reaching one real mode remain two candidates. `runtime`/adapter is
absent from the key entirely, although `event-protocol.md:65` already separates
`provider`/`model`/`family` from the requested route.

**Owner that wins.** `benchmark-evidence.md` owns the record key and its fields.

**What changes.** The identity gains runtime/adapter and the real effort mode, so that
equivalence is decided by what the provider actually does. `effortClass: unmapped`
already provides the precedent that an unproven ladder is not a comparable one.

## C2 — A comparability restriction its consumer does not implement

**Evidence.** `benchmark-evidence.md:74-78`: "A candidate with `effortClass: unmapped`
is ranked **only** against candidates from the same provider, and is excluded from
cross-vendor comparison. An unmapped ladder is not a comparable one."

`routing-policy.md:159-166` (Selection procedure, step 5) ranks survivors "using
benchmark evidence per [benchmark-evidence.md] ... ordered by that document's three
signals" and says nothing about excluding unmapped candidates from cross-vendor
comparison.

**Owner that wins.** `benchmark-evidence.md` defines comparability.

**What changes.** `routing-policy.md`'s ranking procedure must consume the restriction,
or the restriction is decoration.

## C3 — "Comparable task class" is required by three documents and representable by none

**Evidence.** `benchmark-evidence.md:20` defines `successRate` as the share of
"comparable tasks the model completed successfully", and its authority order puts "this
project's own recorded outcomes for a comparable task class" first
(`benchmark-evidence.md:183`, Authority order, item 1). `metrics-and-self-improvement.md:5`
requires preserving "task class" so comparisons mean the same thing, and requires "a
meaningful sample of comparable jobs before suggesting routing changes". Yet the record
key (`benchmark-evidence.md:24`) carries no cohort or task-class dimension.

**Owner that wins.** `benchmark-evidence.md` owns the record key.

**What changes.** Add cohort/task scoping plus an explicit recorded degradation token
when ranking falls back to broader evidence. Issue #15 item 4 is otherwise unimplementable.

## C4 — No owner for cost semantics, and one USD field conflates two different things

**Evidence.** The payload's only cost representation is `costPerTaskUsd`
(`benchmark-evidence.md:21`, bounded by `COST_MAX_USD_PER_TASK = 100` at `benchmark-evidence.md:255`), described as
"Observed average cost per task. This is a measurement, **not** a price quote." That
description does not say whether the number is cash paid or public-price equivalent, and
nothing anywhere separates the two.

Cost is nonetheless load-bearing in routing: `routing-policy.md:137` rule 4 ("Match controls
before cost. Filter candidates by the job's risk tier before comparing latency, price or
convenience"), the no-record ordering (`routing-policy.md:165`, "reliability, then cost and latency"),
Reasoning controls (`routing-policy.md:216`), and
`routing-policy.md:37` §Inputs lists `budget` as a constraint. **`budget` has no
definition anywhere in the payload.**

Subscription quota appears only as a *failure mode*, never as an accounting dimension:
`fallback-policy.md:26`, `failure-modes.md:49`, `observation.md:69`,
`event-protocol.md:101`.

`metrics-and-self-improvement.md:7` already owns the correct instinct — "Unknown cost is
null, not free" — but the cost *schema* it would apply to does not exist.

**Owner that wins.** `metrics-and-self-improvement.md` owns local outcome fields and
already owns the null-not-free rule, so the cost-dimension schema belongs there;
`benchmark-evidence.md` owns the external figure and must declare which dimension it
carries.

**What changes.** `actualMarginalCostUsd`, `apiEquivalentCostUsd` and `quotaBurn` become
separable, unmeasurable stays `null`, and every budget or objective must name the
dimension it uses. This is the pairing that makes "do not compare subscription quota
with API cash as though both were USD" enforceable rather than aspirational.

## C5 — One constant, two names, two claimed owners

**Evidence.** `verification.md:143` states: "**Owner-fixed values.** These are
policy constants, owned here and nowhere else." Its table defines
`MINIMUM_SAMPLES = 30` (`verification.md:148`).

`job-spec.md` also defines it, under a different name and also calling it owner-fixed:
`job-spec.md:34` ("`minimum_samples: <integer> # owner-fixed policy floor; a value below
30 is rejected"), `job-spec.md:100`, `job-spec.md:142`, and `job-spec.md:273`
("`calibration.minimum_samples` is the **owner-fixed** floor for micro-arbiter
calibration").

`output-layout.md:33` attributes the constant to job-spec by name: "`minimum` (which must
equal the owner-fixed `calibration.minimum_samples` in [job-spec.md])".

So `verification.md` says "owned here and nowhere else" while `output-layout.md` names
`job-spec.md` as the owner of the same value. `decision-plane.md:240` already ruled: it
assigns "the owner-fixed minimum sample" to `verification.md`.

**Owner that wins.** `verification.md`, consistent with the ruling already recorded in
`decision-plane.md:239`.

**What changes.** `job-spec.md` keeps the *field* and its validation as a citation of the
constant, never as its definition. `output-layout.md` stops naming an owner for it. The
checklist token assertion at `verification.md:294` already tolerates the value appearing
in `job-spec.md` by design (`verification.md:291`), so a citation form satisfies it.

## C6 — A non-owner restates the calibration validity rule

**Evidence.** `output-layout.md:32-36` restates the minimum, the threshold floor, the
full-signal-set requirement, the agreement floor, and the expiry, and then adds a
normative fail-closed rule: "A missing, malformed, pooled-across-classifiers,
below-floor, incomplete-signal or expired record fails closed." It closes by conceding
"The constants and the complete validity rule are owned by
[verification.md](verification.md)." The same rule is owned at
`verification.md:180` ("A record that fails any clause is invalid and escalates").

`output-layout.md`'s own stated remit is "the run-directory and supervisor capture tree,
decision artifacts, and export rules" (`SKILL.md`, Authority Map).

**Owner that wins.** `verification.md` owns calibration validity.

**What changes.** `output-layout.md` keeps the path and the field names and cites the
owner, without restating the rule. This is the exact duplication the repository's
"every contract has exactly one owner" rule exists to prevent.

## C7 — Durable calibration has no owner and its placement contradicts the run-local rule

**Evidence.** `verification.md:129`: "`calibration.json` **in the run directory**";
`output-layout.md:10` lists `calibration.json` in the run tree.

A durable precedent already exists, owned elsewhere: `benchmark-evidence.md:193-206`
establishes a project-scoped durable cache at `.orchestrate/benchmarks.json`
"**outside** every run directory, so a later run in the same project reuses it", and
carves a scoped correlation exemption from `trace-and-logging.md`'s `runId` rule.

Two further rules interact badly with the tax issue #15 item 10 targets.
`verification.md:187`: "**First run.** With no valid record, the micro-arbiter
**observes and logs only** and C3 is mandatory for every job." A run-local record can
never become valid outside its own run, so every fresh run is a first run, and every job
pays the observation. `verification.md:178` makes an absent or expired record escalate,
so the observation cannot change the outcome it is paying for.

**Owner that wins.** `verification.md` owns calibration, including its validity and
lifecycle; `output-layout.md` owns where artifacts live. `trace-and-logging.md` retains
whatever correlation exemption is granted, since it owns the correlation rule.

**What changes.** Durability, the invalidation key set, and the bounded shadow-sampling
replacement for the unbounded first-run tax belong to `verification.md`; the durable
path belongs to `output-layout.md`. If a self-invalidation-proof design turns out to be
impossible, the blocker rule applies: report the contradiction rather than ship a weaker
contract.

## C8 — Nothing separates infrastructure failure from content failure for costing

**Evidence.** A failure taxonomy exists and is owned: `decision-plane.md`'s watchdog
output includes `failure_class` "distribution over the taxonomy in task 2", and
`decision-plane.md:404` lists the profiler's support flags; `failure-modes.md` owns the
classes and states that `recovery_class` "never selects a command, a flag, or a model"
(`failure-modes.md:13`).

Promotion triggers are owned by `fallback-policy.md:26` and already include "Quota or
rate-limit exhaustion". Content-failure behaviour is owned by `verification.md:60`
(a second content failure on a promoted attempt escalates rather than promoting again).

What no document owns is the *split* issue #15 item 12 needs: which observed failures may
feed an expected recovery cost and which may not. `metrics-and-self-improvement.md:3-5`
records "retries, intervention count and reason" without classifying them.

**Owner that wins.** `metrics-and-self-improvement.md` owns the derived local statistic;
`failure-modes.md` keeps the taxonomy; `fallback-policy.md` keeps the triggers.

**What changes.** Add the infrastructure/content classification as a derived metric that
feeds ranking only, leaving promotion triggers untouched. The existing
content-failure-escalates rule is preserved, not revisited.

## C9 — The micro-arbiter has no skip path when C3 is already structural

**Evidence.** `decision-plane.md:374-376` introduces the task unconditionally: "Runs
after deterministic checks pass, before any C3 arbiter call."
`verification.md:84-95` lists the structural escalations that make C3 mandatory
regardless of tier: review, audit, security, architecture, `importance: high`
implementation, parallel or untrusted-prompt writes, and "**any attempt carrying a
non-zero `riskFloorDelta`**". `verification.md:41` (Layer 2) and
`decision-plane.md:392-394` both describe the micro-arbiter as a gatekeeper that
"cannot accept work".

No document states that when a C3 escalation is structural, deterministic checks are
followed by a direct C3 call with no micro-arbiter invocation. So the gatekeeper is paid
for precisely where its verdict cannot avoid the call it gates.

**Owner that wins.** `verification.md` owns the escalation matrix and the accept
predicate; `decision-plane.md` owns the task definition and its invocation contract.

**What changes.** `verification.md` states the direct-to-C3 path; `decision-plane.md`
states the bounded invocation contract, including the shadow/calibration sample for
uncalibrated installations, which replaces the unbounded first-run observation in C7.

## C10 — No value-of-information gate for the decision plane

**Evidence.** `routing-policy.md:13` states the plane's role passively: "**Semantic
rank** — consumes scored needs from [decision-plane.md](decision-plane.md) when that
plane is enabled, as one ranking input among several, and no-ops without it."
`decision-plane.md` owns the call shape (one bounded prompt per decision), the input
rules, and the degradation table, and `decision-plane.md:70` covers classifier
sourcing at discovery.

Neither document conditions an invocation on whether its answer can change a permitted
decision, and neither defines the deterministic ambiguity or margin test that issue #15
item 9 requires to precede a call.

**Owner that wins.** `routing-policy.md` owns deterministic selection and therefore the
margin/ambiguity gate; `decision-plane.md` owns the call contract.

**What changes.** The skip/call conditions and the recorded
`semanticRouterCalled`/`semanticRouterReason`/`semanticRouterSkippedReason`/
`candidateMargin` fields are split accordingly, with the margin logic in routing policy
and never in the classifier.

## C11 — Route-decision fields have no schema owner

**Evidence.** `trace-and-logging.md:3-6` owns "the **span identifiers**, the
**correlation rule**, **retention**" and explicitly "states so in the negative" what it
does not own. The route-decision content is currently prose inside
`routing-policy.md` Selection procedure step 7 (selected runtime, resolved model,
`effortLevel`, `effortRaw`, capability tier, risk tier and derivation, both deltas,
controls, evidence source, fallback reason, `benchmarkRef`, `benchmark-degraded`), with
no schema. The decision trace *does* have a schema, owned by `decision-plane.md`'s
Decision trace section (runId, jobId, attempt, spanId, decision, candidate, reason,
inputRef, egressAuthority, riskTier, scores, applied, outcomeRef).

Issue #15 item 13 needs fields that belong to neither: Pareto prunes, candidate margin,
evidence scope and sample size, quality lower bound, cost dimensions, reliability,
expected recovery and C3 cost, expected verified cost, runner-up, semantic call or skip
reason, ranking degradation.

**Resolved during this audit.** The ruling already exists in the repository, so no guess is
needed. `trace-and-logging.md:105-115` owns "What must be answerable from the trace", and
that list already covers route decisions in three of its seven items: "Which candidates
passed the hard filter, which were rejected, and why"; "Which benchmark record ranked the
chosen candidate, and whether ranking was degraded"; "Which runtime, model and effort were
selected, and by which rule". A run whose trace cannot answer them is already declared
incomplete at `trace-and-logging.md:115`.

**Owner that wins.** `trace-and-logging.md` owns the trace schema and the answerability
requirement. `routing-policy.md` continues to own the *content* the route decision
records; `decision-plane.md` keeps its own plane-specific decision trace for
`decisions.jsonl`. The issue #15 fields extend the answerability list rather than
creating a third schema.

## C12 — A load-bearing cost and quality schema sits in an on-demand reference

**Evidence.** `SKILL.md`'s Authority Map places `metrics-and-self-improvement.md`,
`failure-modes.md` and `dispatch-hardening.md` in the **On-demand layer**, while
`routing-policy.md` sits in the Policy layer and must consume cost and quality evidence at
selection time.

C4 and C8 assign new load-bearing fields to that on-demand document. If it is not loaded
during a routing decision, the fields it owns are unavailable exactly when they are
needed.

**Resolved during this audit, by precedent.** The transitive chain already exists and is
the repository's chosen pattern: `routing-policy.md` references **no** on-demand document
directly (verified by grep), while `benchmark-evidence.md:94`
names `metrics-and-self-improvement.md` as the owner of the local-run fields it consumes.
So a policy-layer mediator already fronts the on-demand layer, and `routing-policy.md`
reaches local outcomes through it.

**Owner that wins.** `metrics-and-self-improvement.md` keeps owning the per-attempt and
cost fields, exactly as `metrics-and-self-improvement.md:41` claims ("this document owns
the fields"); `benchmark-evidence.md` owns the evidence semantics and cites them.

**What changes.** C4 and C8 must follow this precedent: new cost, quality and
reliability fields are defined in `metrics-and-self-improvement.md` and **consumed
through `benchmark-evidence.md`**, never referenced directly from `routing-policy.md`.

**Residual risk, recorded rather than dismissed.** A field owner that is only loaded on
demand can be absent at the moment routing needs it. The mitigation is that the
policy-layer mediator must carry every routing-critical field's *name and type*, so
definition can be deferred while availability cannot. If a later milestone finds a field
that routing must evaluate without the mediator, that field belongs in the policy layer
and this ruling should be revisited.

## C13 — A low-sample record may still be the deciding rank

**Evidence.** `benchmark-evidence.md:148`: "A `sampleSize` below `MIN_BENCHMARK_SAMPLES`
is recorded with `confidence: low`" (`MIN_BENCHMARK_SAMPLES = 30`). The consequence is
stated only for the single-source case at `benchmark-evidence.md:146-147`: a
single-source value "is recorded with `confidence: low` and **may not be the deciding
rank between two candidates**."

No equivalent bar attaches to a small-sample record, so a 3-of-3 record may outrank a
320-sample record on raw `successRate`. Issue #15's acceptance checklist requires the
opposite, and item 3 requires a deterministic, sample-size-aware conservative statistic.

**Owner that wins.** `benchmark-evidence.md`.

**What changes.** A documented deterministic estimator (Wilson lower bound or Beta lower
credible bound, whichever is simplest to defend) becomes the ranking statistic, recorded
with estimator identity and scope, and unable to touch eligibility or a floor.

## Existing owners to reuse rather than duplicate

Issue #15 introduces several concepts that already have partial owners. Creating a second
owner for any of these would be a defect:

| Concept | Existing owner | Reuse as |
| --- | --- | --- |
| Requested vs resolved route | `event-protocol.md:65,73` — `provider`, `model`, `family` recorded separately from the requested route | The requested/resolved split for model and effort |
| Effort vocabulary | `benchmark-evidence.md:55-70` — the normalized ladder, `effortRaw`, `effortClass` | The single effort vocabulary; no second ladder |
| Unknown cost is not zero | `metrics-and-self-improvement.md:7` | The null-not-free principle for all three cost dimensions |
| Failure taxonomy | `failure-modes.md` | The class list C8 splits into infrastructure vs content |
| Promotion triggers and bounds | `fallback-policy.md:26` | Untouched; C8 feeds ranking only |
| Durable project-scoped artifact + correlation exemption | `benchmark-evidence.md:193-206` | The precedent pattern for durable calibration in C7 |
| Correlation rule and retention | `trace-and-logging.md` | Envelope of whatever C11 rules |
| Deltas applied as `max(declared, semantic)` and risk delta forces C3 | `routing-policy.md:95-119` | The floor-raising rule, unchanged by any cost objective |

## Invariants explicitly confirmed intact and not to be touched

Re-read during this audit and found consistent, with no contradiction to report:
`benchmark-evidence.md`'s "What benchmark evidence may not do" list;
`routing-policy.md`'s "Never lower a floor solely to meet a budget" and the discarded
negative delta; `verification.md`'s fail-closed `riskTier` handling and the
content-failure escalation; `fallback-policy.md`'s same-or-stronger control comparison;
`internal-routing.md`'s model-ownership rule that different executables do not imply
different families; `safety-policy.md` as sole safety authority.

## Open ownership questions

None. Both questions raised during the audit are resolved above against evidence already
present in the repository, not against preference:

1. **C11** — `trace-and-logging.md` already owns route-decision answerability
   (`trace-and-logging.md:105-114`), so it owns the schema.
2. **C12** — the policy-layer mediator pattern already exists
   (`routing-policy.md` → `benchmark-evidence.md` → `metrics-and-self-improvement.md`), so
   the on-demand field owner stays where it is, with the residual risk recorded.

One item remains for the user rather than for this register: the repository's own rule is
that a contract mismatch is *reported*. Every conflict above is either resolved by an
existing owner or assigned to the owner the repository already names, so nothing here
needs a user ruling before C1, C2, C3, C5, C6, C9, C10 and C13 proceed.
