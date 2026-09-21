# Issue #15 — final implementation report

Branch `benchmark` at `a1ea8e9`, with this goal's work uncommitted on top. This report states
the verified repository state, not the intent, and it records what was **not** done as
carefully as what was.

**No paid experiment was executed.** The provider matrix is unrun, no arm from the manifest has
been measured, and no model or provider is named a winner anywhere in the payload or the
reader surfaces.

## 1. Outcome

The `orchestrate` skill now expresses a provider-neutral, model-neutral, cost-aware routing
contract whose selection objective is the lowest expected verified cost to a verified
successful outcome, inside the existing safety, capability, quality and independence
constraints. All three phases are delivered: Phase 1 contracts, Phase 2 instrumentation with an
independent accounting audit, and Phase 3 a frozen manifest with a pre-registered analysis.

Evidence at a glance:

| Check | Result |
|---|---|
| Contract and instrumentation tests | **337 pass** |
| Repository maintenance sweep, from the repository root | **clean, no FAIL** |
| Invariant fixtures able to fail | **15 of 15** |
| Mutation checks, per module | every mutation failed at least one test |
| Zero-cost end-to-end smoke | **PASS**, 0 paid provider calls |
| Recorded plane-on benchmark run | **REJECTED** by the audit (accounting does not reproduce) |
| Paid experiment | **not run** |

## 2. Files changed

**Modified — normative references** (`plugins/orchestrate/skills/orchestrate/references/`):

| File | Change |
|---|---|
| `benchmark-evidence.md` | the route identity keyed on the real execution mode; sample-size-aware quality uncertainty; the cohort-scoped evidence hierarchy with recorded degradation |
| `routing-policy.md` | the expected-verified-cost objective; the task quality floor and verification strength; deterministic Pareto pruning with its protections; the value-of-information gate |
| `metrics-and-self-improvement.md` | the three cost dimensions; the failure-class recording split and which evidence feeds recovery cost |
| `verification.md` | direct-to-C3 for a structurally mandatory escalation; bounded shadow sampling; calibration durability and invalidation |
| `decision-plane.md` | value of information; the micro-arbiter is not invoked when C3 is already mandatory |
| `trace-and-logging.md` | the closed `route` payload a decision must be explainable from |
| `job-spec.md` | stopped claiming ownership of a constant whose value `verification.md` owns |
| `output-layout.md` | stopped restating the calibration validity rule; records where the artifact lives |

**Modified — reader surfaces and the sweep:** `SKILL.md` (five authority-map descriptions
brought into line), `README.md` (a "Cost-aware routing" section and the fanned-out constants),
`site/index.html` (the English DOM and the Vietnamese deck updated together),
`docs/maintaining-the-docs.md` (a new §15 gate).

**Modified — tooling:** `tools/benchmark/run_benchmark.py` (per-model cost attribution, token
field presence, role and trace readers, runtime identity, the settle window, the full-schema
trial record), `tools/benchmark/verify_results.py` (the audit rebuilt as an importable
function), `tools/benchmark/analyze.py` (an inline note on a resolver false positive).

**New — reference implementations and their tests** (`tools/contracts/`): `route_identity`,
`cost_dimensions`, `quality`, `routing`, `pareto`, `expected_cost`, `voi_gate`,
`micro_arbiter`, `calibration`, `reliability`, `trace_route`, `invariants`, with a test module
for each and an `__init__.py` in both test directories.

**New — instrumentation** (`tools/benchmark/`): `trial_schema.py`, `freeze_manifest.py`,
`smoke.py`, and three test modules.

**New — evidence** (`plans/260921-0805-issue15-contract-reconciliation/`):
`conflict-register.md` (378 lines), `instrument-defects.md`, `invariant-regressions.md`,
`accounting-audit.md`, `settlement-confound.md`, `experiment-manifest.md` with its JSON,
`smoke.md`, and this report.

## 3. Normative ownership changes

`conflict-register.md` records **13 contradictions** (C1–C13) with file and line evidence, names
the owner that wins for each, and states what changes. All 63 citations were verified in range
and all 27 anchors verified at the exact cited line. No rule was duplicated into a second owner.

The resolutions that changed behaviour:

- **C1 route identity was too narrow** — keyed on a normalized label, so two labels reaching one
  real execution mode became two candidates. Now keyed on what the provider executes.
- **C4 no cost-dimension owner** — one `costUsd` field served three incomparable quantities.
  `metrics-and-self-improvement.md` now owns the three dimensions.
- **C5 `MINIMUM_SAMPLES` had two owners** — `verification.md` says "owned here and nowhere else"
  while `job-spec.md` and `output-layout.md` attributed it elsewhere. `verification.md` wins, per
  the ownership rule in `decision-plane.md`; the other two now cite rather than claim.
- **C6/C7 durable calibration was unowned and contradicted** — `output-layout.md` restated the
  validity rule and placed the artifact run-locally. It now describes only the location, and
  `verification.md` owns the rule.
- **C8 the infrastructure/content failure split was unowned** — now owned by
  `metrics-and-self-improvement.md`, referencing `failure-modes.md` for the classes themselves.
- **C9 the micro-arbiter had no skip path**, **C10 there was no value-of-information gate** —
  both now have owners and rules.
- **C11/C12** were resolved from existing evidence rather than guessed:
  `trace-and-logging.md:105-115` already owns route-decision answerability, and the
  `routing-policy.md` → `benchmark-evidence.md` → `metrics-and-self-improvement.md` mediator
  precedent covers the other.
- **C13 a low-sample record could still be the deciding rank** — closed by the quality bound.

## 4. Schema changes

- **The route identity** is `(runtime, provider, model, family, effortMode)`. Two normalized
  effort labels reaching one real mode collapse to one candidate; an undecidable identity is
  never merged.
- **Cost** is three separable dimensions — `actualMarginalCostUsd`, `apiEquivalentCostUsd`,
  `quotaBurn` — with unknown as `null` and never zero, quota never added to dollars, and a budget
  that does not declare its dimension refused.
- **The trace's `route` payload** grew from 9 fields to a closed set covering hard-gate survivors
  and rejects, prunes and their reasons, evidence cohort/sample/degradation, the quality bound and
  its estimator, the three cost dimensions and the declared one, infrastructure failure
  probability and the feeding class, expected recovery/escalation/C3 cost, selected effort, the
  expected verified cost, the runner-up and its margin, and whether the semantic router ran and
  why. It is closed in both directions, and a reason is an enum rather than classifier prose.
- **The trial record** carries 39 required fields, 14 of them provider-dependent and each
  carrying a capability state from a closed vocabulary (`exposed`, `derived`,
  `not-exposed-by-provider`, `not-measured`). A field the provider does not report can only be
  `null` with a stated reason, and a derived field must record its basis.
- **Durable calibration** is scoped to provider, model, version, decision schema, prompt
  contract, signal set and threshold policy, expires, invalidates fail-closed on any change, and
  cannot validate itself because the floors come from the owner rather than the record.

## 5. New invariants

Fifteen negative fixtures (`tools/contracts/invariants.py`), each pairing the contract behaviour
with the behaviour it replaced and an invariant predicate. The test module asserts the predicate
holds on the contract, fails on the broken behaviour, and that the two verdicts differ, so a
fixture that cannot fail is refused rather than counted. Fourteen are behavioural; only the
"no model name as a normative default" check is a scan, and its ability to detect a name is
itself tested. Recorded in `invariant-regressions.md`.

Beyond the fixtures, the contract modules encode: unknown is never zero; missing dimension
prevents pruning; protections cannot be pruned away; a content failure never promotes; a
permission stop never promotes; a record cannot validate itself; an unobservable classifier
version refuses durability; and an incomplete trace cannot be reconstructed.

## 6. Tests run, and their results

```bash
PYTHONPYCACHEPREFIX=/tmp/pyc python3 -m unittest discover -s tools -t .
# Ran 337 tests ... OK
```

The cache prefix is required by instrument defect **ID-1**: a stale `__pycache__` from a mutant
was loaded despite byte-identical source, which made a correct restore look broken and would
equally have made a broken file look verified. Restores are now verified by content hash first,
then by the suite.

Mutation checks, each confirmed applied by content hash before the suite ran:

| Module | Mutation | Outcome |
|---|---|---|
| `route_identity` | legacy `(provider, model, effortLevel)` key | 3 failures |
| `cost_dimensions` | "unknown = free" | 2 failures |
| `quality` | raw-rate ordering | 2 failures |
| `routing` | two mutations | 3 failures each |
| `pareto` | ignore protections / always comparable | 5 / 2 failures |
| `expected_cost` | unknown cost = 0 / unknown probability = 0 | 4 / 2 failures |
| `voi_gate` | no margin threshold / ignore floor raisability | 4 / 1 failures |
| `micro_arbiter` | ignore structural escalation / no shadow ceiling | 11 / 1 failures |
| `calibration` | record trusts its own minimum / no version check | 4 / 4 failures |
| `reliability` | everything feeds recovery cost / content may promote | 3 / 7 failures |
| `trace_route` | tolerate unknown fields / allow prose | 1 / 7 failures |
| `trial_schema` | allow fabrication / drop null-value agreement | 1 / 2 failures |
| `verify_results` | drop unattributed-cost rejection / drop token check | 1 / 1 failure |

**A failure worth reporting rather than burying.** The first `trial_schema` mutation cycle
reported both mutations as *surviving*. The cause was not a weak contract but a weak
instrument: `tools/benchmark/tests/` had no `__init__.py`, so `unittest discover` never
collected the 31 new tests and the total stayed at 259. Adding the file raised the total to 290
and both mutations then failed as expected. This is recorded as instrument defect **ID-2**, and
the procedure now requires a new test file to be shown to change the discovered total before its
result is used.

## 7. The accounting audit rejects the recorded run

`verify_results.py` now recomputes per-trial cost, tokens, nested-dispatch cost, the component
split and unattributed cost from the raw session files. Against `plans/reports/bench-planeon` it
**rejects** the run:

```text
trials checked : 80   cost mismatches : 9   token mismatches : 36
recorded total : $204.272032   recomputed total : $205.484251
unattributed   : $0.784462 across 1 file(s)    46 problem(s)   RESULT: REJECTED
```

The recorded figures understate the candidate arm by 0.59%, so the measured negative result is
robust to the correction. The audit passes on a deliberately consistent synthetic run and fails
on a deliberately inconsistent one, which is asserted by tests.

## 8. Known limitations

- **The measured arm is skill-plus-directive, not the skill.** The harness directive mandates
  headless `pi` dispatch, forbids in-session subagents and requires registering the decision
  plane. `settlement-confound.md` refutes the resource-exhaustion explanation (all 40 candidate
  trials ended `status=ok` with exit code 0, the maximum duration was 1139 s against a 1500 s
  cap, failures were *faster* than successes, and the control arm succeeded 40/40 under the same
  shim and cap) and finds the missing settlement is a candidate defect — 23 trials recorded
  `state.json` and still reached no verified outcome. But separating "the skill's contract" from
  "the directive's mandated workflow" needs a V1 arm without the dispatch mandate, which is a
  paid experiment. This is recorded as a required element of the V1 definition rather than
  allowed to disappear.
- **The settle window bounds the race, it does not abolish it.** A dispatch that lingers longer
  than the quiet window is still outside the snapshot, which is why unattributed cost is a
  rejection rather than a warning. Stated in the tests.
- **The catalog snapshot is a digest, not a capability map.** It proves the catalog did not
  change; it does not record what each entry can do.
- **Pricing is deliberately unmeasured** in the manifest, because a copied price would make the
  frozen comparison a transcription. Prices must be captured at run time.
- **The smoke does not exercise the grader's success path.** Both smoke trials fail the grader by
  design, since the smoke tests the instrument rather than the agent.
- **The fixtures test the owned modules, not the prose.** A reference could state a rule the
  module does not implement; that divergence is what the conflict register and the sweep are for.
- **The time band is not enforced.** Its invalidation triggers are named, but a re-freeze is a
  deliberate act.
- **Two small items remain open for the user**: reverting `ak insights consent --collection=true`,
  and deleting the untracked `tools/benchmark/tmp/bs.json`.

## 9. Remaining experiment steps

The manifest in `experiment-manifest.json` freezes the environment and pre-registers the
analysis. What remains is execution, in this order:

1. **Re-freeze immediately before running**, and confirm the runtime version, catalog digest,
   commit, and fixture and grader digests still match. Any change invalidates the band.
2. **Capture pricing at run time** from the provider's own usage report, since the manifest
   deliberately does not carry a price.
3. **Run the worker frontier first**: the frozen catalog's models and effort modes directly on
   the frozen fixture with no orchestration, to identify the local Pareto frontier over verified
   cost and quality, then freeze that frontier as the router's candidate set.
4. **Run the router ablation** with the coordinator held fixed: V0, V1, V2, V3, V4, and V5 only
   if the durability contract is implemented.
5. **Add the missing arm** that runs the skill without the headless-dispatch mandate, so the
   skill-versus-directive confound in §8 is measured rather than assumed.
6. **Audit the run** and require the accounting audit to pass before any result is reported.
7. **Judge only against the pre-registered conditions**: the non-inferiority margin, the minimum
   worthwhile saving, no critical-cohort regression, no weakened invariant, and a passing audit.
8. **Re-run `freeze_manifest.py`** and validate it, so the executed run names the environment it
   was measured against.
