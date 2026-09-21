# Frozen experiment manifest and pre-registered analysis

This file documents the Phase 3 deliverable of issue #15: the frozen environment and the
analysis that was fixed before any result exists. The machine-readable manifest is
`experiment-manifest.json`, produced by `tools/benchmark/freeze_manifest.py`; the contract it
must satisfy is asserted by `tools/benchmark/tests/test_freeze_manifest.py`.

**No paid experiment was executed.** `paidRunExecuted` is `false` in the manifest, and
validation rejects a manifest that claims otherwise.

## Why a tool produces this rather than a hand-written document

Two rules of this repository meet here. No catalog value, model name, price or version may be
copied into the skill — so the frozen values belong in a run artifact, not in the contract.
And every measurement must resolve from live evidence at run time — so the manifest is
*resolved*, not transcribed. `freeze_manifest.py` therefore reads the runtime version from the
runtime, the commit from git, the catalog from the runtime's own listing, and the fixture
digests by recomputing them from the payload. A field it cannot resolve is recorded as `null`
with a capability state saying why.

## What was frozen

| Field | How it was resolved | Value at freeze |
|---|---|---|
| Runtime | `pi --version` | `pi 0.86.1` |
| Commit under test | `git rev-parse HEAD` | `a1ea8e9813f2…` on `benchmark` |
| Worktree cleanliness | `git status --porcelain` | recorded as a count of dirty files |
| Environment | the interpreter and platform | Python version, OS and machine |
| Catalog snapshot | the runtime's own model listing | a sha256 digest and a model count, never a list of names |
| Auth readiness | presence of the environment variables and the operator's env file | presence, source location and trust class only — **no value is read or stored** |
| Fixture | the payload's own digests, recomputed | `workspaceDigest` and `graderDigest`, both re-derived and confirmed to match |
| Pricing | not resolvable offline | `not-measured`, with the reason recorded |
| Time band | the freeze instant plus its maximum age | 14 days, with the invalidation triggers named |

The catalog snapshot stores a digest and a count rather than a list. That keeps the manifest
useful as a freeze record while keeping the catalog where it belongs: live runtime evidence.
Pricing is deliberately `not-measured`: a copied price would turn the frozen comparison into a
transcription, so the manifest records that prices must be captured at run time from the
provider's own usage report.

## Pre-registered analysis

Fixed before any result exists, so a result cannot choose its own test:

- **Primary metric** — verified cost per successful task: total end-to-end attributable cost
  divided by accepted successful tasks, over every attributable call (coordinator, worker,
  classifier, retry, fallback, micro-arbiter, C3 arbiter). The metric **declares its cost
  dimension** (`actualMarginalCostUsd`), and quota burn is never added to dollars.
- **Secondary metrics** — success rate, settlement rate, duration per successful task,
  dispatch cost share, non-settlement rate.
- **Non-inferiority margin** — 5 percentage points absolute on the success rate.
- **Minimum worthwhile saving** — 15% relative reduction in verified cost per successful task.
  A smaller positive saving is not claimed as an improvement.
- **Trial count** — 20 tasks × 3 trials × the declared arms, with the planned total derived
  from those numbers rather than asserted separately.
- **Stopping rule** — one interim look at 50% with alpha spent across the two looks (0.005
  interim, 0.045 final), a benefit stop when the interim saving bound clears the threshold and
  non-inferiority holds, and a futility stop when the success-rate interval lies entirely below
  the non-inferiority margin.
- **Stratification** — by task cohort and task type; every stratum reports its own paired
  estimate, and a pooled estimate alone is not reported as the result.
- **Paired procedure** — task-major, paired by (task, trial), so both arms of a pair run back
  to back and a slow period cannot land on one arm only.
- **Statistical tests** — paired bootstrap over task-level pairs for cost, a paired proportion
  difference with a Newcombe interval for success, non-inferiority from the lower bound, with
  the declared multiplicity handling.
- **Critical cohorts** — security-sensitive, C3-mandatory and independence-required cohorts may
  not regress at all. That is a gate, not a hypothesis test.
- **Improvement conditions** — the five conditions from issue #15, including that the
  accounting audit passes.

## The arms

V0 is the strong single-model baseline. **V1 is named "current routing policy (skill plus
harness directive)" deliberately**: the measured configuration in the recorded run was
skill-plus-directive, and the two are not separable without a further arm, so the manifest
records what was actually measured rather than overstating it (see `settlement-confound.md`).
V2 is the new deterministic router with the plane off, V3 adds the plane on value-positive
choices only, V4 adds a calibrated micro-arbiter, and V5 adds durable calibration reuse if the
durability contract is implemented. The oracle arm is computed offline and is explicitly marked
as never a policy.

## Worker-frontier protocol

Workers come first: the frozen catalog's models and effort modes are run directly on the frozen
fixture with no orchestration, to identify the local Pareto frontier over verified cost and
quality. That frontier is then frozen and becomes the candidate set for the router ablation.
The reason is stated in the manifest: measuring the router against an unfrozen candidate set
would confound the policy's effect with the composition of the candidate set. The coordinator
is held fixed during the ablation, and external leaderboards may seed hypotheses but never
enter the candidate set directly.

## Known limitations

- **The catalog snapshot is a digest, not a capability map.** It proves the catalog did not
  change; it does not record what each entry can do. Capability evidence must be captured at
  run time through the runtime's own probe.
- **Pricing is unmeasured**, so the manifest cannot by itself price a route. That is
  intentional and is why the primary metric declares its dimension.
- **The time band is a validity window, not a guarantee.** The invalidation triggers are named,
  but nothing enforces them; a re-freeze is a deliberate act.
- **The arms are declared, not run.** No arm in this manifest has been measured, and the
  objective forbids running the provider matrix here.
