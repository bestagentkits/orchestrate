# Job Spec

`/orchestrate` accepts YAML or turns a free-form request into YAML under the
run report directory. This file owns the durable data shape and execution
semantics. It does not own a runtime roster, model catalog, or provider route.

Resolve every runtime, model, agent, flag, and safety control from live evidence
before dispatch:

- [runtime-profile.md](runtime-profile.md): live candidate evidence, the
  `runtimes.json` schema, and control evidence;
- [routing-policy.md](routing-policy.md): the sole selection policy;
- [safety-policy.md](safety-policy.md): risk tiers and the safety gate;
- [runtime-adapter-contract.md](runtime-adapter-contract.md): the adapter
  interface and command construction;
- [internal-routing.md](internal-routing.md): in-session agent mechanics.

## Schema

```yaml
version: 1
concurrency: 2
workspace_roots: [<authorized-workspace-root>]
defaults:
  timeout: 10m
  effect: observe
  approval: inherit
  capture: true
  benchmark:
    cacheTTLHours: <integer>        # default 168 (CACHE_TTL_DEFAULT_HOURS); above 720 (CACHE_TTL_MAX_HOURS) is rejected
  fallback:
    maxPromotions: <integer>        # default 2 (MAX_PROMOTIONS_DEFAULT); above 4 (MAX_PROMOTIONS_MAX) is rejected
calibration:
  minimum_samples: <integer>        # owner-fixed policy floor; a value below 30 is rejected
jobs:
  - id: string
    runtime: string
    agent: string
    fallback_runtime: [string]
    task: scout | architecture | implement | review | audit | security | test | docs | mechanical
    importance: normal | high
    model: string
    effort: minimal | low | medium | high | xhigh | max   # optional; absent means the router chooses by outcome
    cwd: string
    prompt: string
    skill: string
    allowed_tools: [string]
    disallowed_tools: [string]
    effect: observe | scoped-write | high-impact-write | external-destructive
    approval: inherit | require
    isolation: none | worktree
    timeout: 10m
    expected_output: string
    depends_on: [job-id]
    destructive: false
    checks: [string]                  # descriptive acceptance requirements
    authority: <existing-user-authorization-reference>
    owned_paths: [<relative-owned-path>]
    inputs:
      - path: <relative-input>
        sha256: <optional-expected-hash>
      - path: <relative-handoff-destination>
        from_job: <dependency-id>
        from_path: <declared-dependency-output>
    outputs:
      - path: <relative-artifact>
    invocation:                       # resolved CLI jobs only
      command: <verified-executable>
      args: [<verified-argument>]
    verification:                     # executable acceptance checks
      - command: <verified-check-executable>
        args: [<check-argument>]
    retry:
      max_attempts: 1
      backoff: 5s
      classes: [<retryable-class>]
    # Retry runs first for the same runtime, bounded by max_attempts; a promotion
    # happens only after that budget is exhausted. The combined dispatch ceiling for
    # one job is (1 + maxPromotions) x max(1, max_attempts).
    max_output_bytes: 1048576
```

Candidate identifiers are opaque strings until the current run verifies them.
`agent` is meaningful only for in-session dispatch. `skill` is meaningful only
for a skill-run branch. Do not copy a candidate list into this file.

`effect` and `approval` are normalized coordinator intent, not runtime flags.
The live harness profile maps them to verified native sandbox, permission, and
approval controls. Block a route when no verified mapping meets its risk tier.

## Required Fields

Every job includes:

- `id`, `runtime`, and `cwd`;
- exactly one executable intent through `prompt` or `skill`;
- `timeout` or `defaults.timeout`;
- `expected_output`;
- `model` or a routable `task`;
- `calibration.minimum_samples`, at or above the owner-fixed policy floor of 30,
  whenever the run may use the no-C3 acceptance path;
- `benchmark.cacheTTLHours` is **optional**: an absent value uses
  `CACHE_TTL_DEFAULT_HOURS`, and a value above `CACHE_TTL_MAX_HOURS` is rejected
  rather than clamped. Both constants are owned by
  [benchmark-evidence.md](benchmark-evidence.md);
- `effort` is optional, and when present must be one of the normalized ladder
  values. An explicit `effort` is a constraint the router honors; an absent one
  lets the router choose by measured outcome.

When `model` is present it is an explicit constraint, not proof of availability.
The live inventory gate still applies. Internal model selection is allowed only
when the current native dispatch interface proves that capability.

`isolation: worktree` is required for parallel writers in one repository and
for any write whose verified harness controls do not otherwise satisfy the
assigned risk tier. Worktree isolation prevents edit collisions; it does not
claim to be an operating-system sandbox.

`importance: high` raises capability and risk floors according to
[routing-policy.md](routing-policy.md). This schema never names the resulting
model or reasoning setting.

## Validation

Before stage construction:

1. Reject duplicate or unsafe job IDs and unknown dependency IDs.
2. Reject dependency cycles.
3. Resolve `cwd` and ensure it stays within the authorized workspace.
4. Require bounded timeout and capture for every job.
5. Verify each primary and fallback runtime in the live matrix.
6. Map effect, approval, and tool constraints to verified native controls.
7. Verify explicit model and agent constraints.
8. Reject parallel write overlap unless file ownership is disjoint and each
   writer has the required isolation.
9. Bind external/destructive work to existing scoped user authorization; ask
   only when the required scope has not been authorized. Never infer permission
   from an arbitrary nonempty authority string.
10. Run the graph optimizer pass per [graph-optimizer.md](graph-optimizer.md)
    after routing: apply only approved reductions, then re-run checks 1–9 against
    the reduced graph. A reduction that breaks any check above is refused.
11. Require `calibration.minimum_samples` to be an integer at or above the
    owner-fixed policy floor of 30 whenever the run may use the no-C3 path. A
    missing or lower value does **not** lower the bar: it disables
    acceptance-without-C3 for the run, and C3 remains mandatory.
12. Validate harness identity on the run-level record: a run that cannot identify
    the harness that loaded the skill records `harness: unknown` and must not
    claim any harness-specific feature. This field names the harness, never a
    runtime — the conformance surface and the degradation rules are owned by
    [harness-portability.md](harness-portability.md).
13. Reject a `benchmark.cacheTTLHours` above the owner-fixed maximum
    `CACHE_TTL_MAX_HOURS`. A rejected value **fails validation**; it is never
    clamped to the maximum.
14. Reject an `effort` outside the normalized ladder. A rejected value **fails
    validation**; it is never snapped to the nearest level.
15. Reject a `fallback.maxPromotions` above the owner-fixed maximum
    `MAX_PROMOTIONS_MAX`. A rejected value **fails validation**; it is never
    clamped to the maximum.

Unknown flags, models, or controls fail validation. Re-read live help or current
official documentation; never guess a replacement.

## Execution Semantics

- Jobs with no dependencies form the first stage.
- A job starts only after every dependency succeeds.
- A stage may run up to `concurrency` jobs when ownership and isolation allow.
- Failed or timed-out dependencies block their dependents.
- Default is one attempt. An explicit bounded retry policy permits only named
  failure classes after confirmed settlement and unchanged owned/input state.
  External/destructive effects and uncertain writers never retry automatically.
- Fallback selection reruns the full capability and risk gate for that runtime: what
  **re-runs** is availability and the per-concern control check, while what does **not**
  change is the job's tier, its approvals and its egress authority. A successor that
  would need a new approval, a wider write boundary, an enabled bypass or a new egress
  authority is a different job requiring a new gate decision, not a fallback.
- Every state transition is atomically persisted before the next dispatch.

## Preparation, State And Resume

`<run-dir>/state.json` is the authoritative tracker, owned by the coordinator
and written atomically before the next dispatch:

```json
{
  "runId": "<run-id>",
  "specPath": "jobs.yaml",
  "harness": "unknown",
  "jobs": {
    "<job-id>": {
      "status": "queued|running|success|failed|blocked|interrupted",
      "runtime": "<verified-runtime>",
      "model": "<resolved-model-or-null>",
      "agent": "<resolved-agent-or-null>",
      "attempts": 1,
      "worktree": "<path-or-null>",
      "riskTier": "R0|R1|R2|R3",
      "acceptedWithoutC3Count": 0,
      "attemptRecords": [
        {
          "attempt": 1,
          "model": "<resolved-model-or-null>",
          "effortLevel": "minimal|low|medium|high|xhigh|max|null",
          "effortRaw": "<vendor-effort-parameter-or-null>",
          "benchmarkRef": "<benchmark-record-key-or-null>",
          "promotionOf": "<attempt-ordinal-or-null>",
          "promotionTrigger": "<trigger-or-null>",
          "status": "queued|running|success|failed|blocked|interrupted",
          "startedAt": "<timestamp-or-null>",
          "endedAt": null,
          "tierDerivation": ["<declared-attribute>"],
          "capabilityFloorDelta": 0,
          "riskFloorDelta": 0,
          "riskTier": "R0|R1|R2|R3",
          "c3EscalationReason": "<reason-or-null>",
          "c3Verdict": "pass|fail|blocked|null",
          "acceptedWithoutC3": false,
          "laterOutcome": "<observed-outcome-or-null>",
          "decisionTraceRef": "<decisions.jsonl-sequence-or-null>"
        }
      ]
    }
  }
}
```

**Acceptance is recorded per attempt, not per job.** `attemptRecords[]` is the
authoritative record and the job-level `status`, `attempts`, `riskTier` and
`acceptedWithoutC3Count` are aggregates derived from it — the maximum tier and
the count of attempts accepted without a C3 call. A job-level field that
collapses several attempts never overrides an attempt record. This is what lets
calibration pair an accepted attempt with the C3 verdict that later contradicted
it, per [metrics-and-self-improvement.md](metrics-and-self-improvement.md).

The per-attempt `model`, `effortLevel`, `effortRaw` and `benchmarkRef` fields are
read by [metrics-and-self-improvement.md](metrics-and-self-improvement.md) for
per-attempt calibration and by [verification.md](verification.md) for the accept
record. They stay attempt-scoped and are never aggregated to the job level.

The attempt ordinal is the **join key** for `metrics.jsonl`, the trace and the events,
so no consumer may key on a timestamp. Spans are **not** stored here: the attempt record
is the durable unit and records the ordinal plus the promotion fields, while span detail
stays in the trace owned by [trace-and-logging.md](trace-and-logging.md). A reader should
not expect spans in both places.

`riskTier` on an attempt is the **recorded** tier the escalation matrix reads. It
is computed by the coordinator, never authored by a classifier, as the maximum of
two deterministic inputs:

```text
riskTier = max(tierDerivation, riskFloorDelta applied)
```

`tierDerivation` is the deterministic derivation from declared attributes owned by
[safety-policy.md](safety-policy.md). `riskFloorDelta` is the risk-floor part of
the semantic adjustment, and it may only **raise**. A negative or lowering value is
discarded. A missing or unparseable `riskTier` is treated as `R2`.

The two floor deltas are recorded separately, because they have different
consequences: `capabilityFloorDelta` affects which candidates are eligible, while
`riskFloorDelta` changes the tier, the required controls, and whether a C3 call is
mandatory. A non-zero `riskFloorDelta` means a probabilistic signal raised the
tier, and the escalation matrix in [verification.md](verification.md) always
escalates such an attempt.

`c3EscalationReason` records why the attempt was sent to C3, or `null` when it was
accepted on the micro-arbiter path. `c3Verdict` records the outcome of that call.
`laterOutcome` is the observed result that makes the attempt usable as calibration
ground truth. `decisionTraceRef` points at the enumerated trace in
`decisions.jsonl` described by [decision-plane.md](decision-plane.md) and
[output-layout.md](output-layout.md).

`calibration.minimum_samples` is the **owner-fixed** floor for micro-arbiter
calibration: the number of comparable C3-audited outcomes a per-classifier record
must contain before the no-C3 path may be used at all. It is a run-policy field,
set here and nowhere else, and it is independent of any record. Its value must be
at least the owner-fixed policy floor of 30; a lower value is rejected by
validation, and a missing value disables the no-C3 path. A calibration record
whose own `minimum` field does not equal this value is invalid, which is what
stops a record from validating itself. The calibration rules that consume it —
ground truth, per-classifier scoping, the agreement and threshold floors, expiry,
and fail-closed behaviour — are owned by [verification.md](verification.md).

After live routing, add authorized `workspace_roots`, relative `owned_paths`,
explicit `inputs`/`outputs` and a verified `invocation` for each CLI job. Keep
secrets out of the spec. `verification` contains executable argv arrays;
`checks` alone is descriptive and does not execute a shell command. Include a
report file among outputs for read-only and native jobs so acceptance is
inspectable.

Preparation writes a private immutable resolved input plus the initial state.
That input is final after any approved graph-optimizer reduction has been
materialized into it; it is never rewritten afterwards. Resume reuses the
recorded reduction and never re-optimizes.

Advancement reconciles execution attempts and returns newly dispatchable native
jobs plus supervisor run IDs. A completed CLI attempt waits for explicit
artifact acceptance. Reconcile again after observed transitions; this is not an
autonomous model-selection loop. Acceptance binds a native receipt to the exact
attempt; native completion claims still require artifact and check verification.
Never fabricate a process exit code for native work.

With the AgentKit CLI installed, this contract has a deterministic engine:

```bash
ak orchestrate prepare <jobs.yaml> <run-dir> --json
ak orchestrate advance <run-dir> --json
ak orchestrate plan-status <run-dir> --json
ak orchestrate accept <run-dir> <job-id> --attempt <attempt-id> --result <receipt.json> --json
```

Declared verification commands run under a persisted supervisor run. Acceptance
may report verification pending; retain the same receipt and repeat acceptance
after observing its run. A client interruption never authorizes a second set of
checks. On hosts without process supervision, declared subprocess checks remain
unsupported rather than silently losing their deadline guarantee.

Record the selected route separately from the receipt's observed identity and
its evidence source. An unknown actual provider or model stays absent;
executable names and requested flags do not attest which model performed the
work.

Resume reconciles rather than restarts:

- reuse a successful result only while its base revision, input fingerprints and
  output hashes remain valid; stale prerequisites invalidate dependent results
  and the arbiter;
- reconnect to a recorded supervisor run or native handle instead of creating
  another run or attempt;
- convert interrupted `running` work to `interrupted` and preserve its partial
  capture under an attempt directory;
- block ownership you cannot prove; a launch whose outcome is uncertain is a
  reconciliation problem, not a retry;
- require fresh approval before redispatching destructive work;
- recompute blocked jobs from current dependencies and live runtime evidence;
- rerun the arbiter whenever any reviewed job reruns.

Do not edit the prepared spec in place. Create worktrees before preparation.
Paths are relative to each job's `cwd` and must remain within its authorized
root. A handoff names a dependency's declared output and copies verified bytes
to a declared destination. Conflicting content is preserved and reported; the
engine does not silently merge code or overwrite user files. Integration of
source patches remains coordinator-owned.

Retries retain attempt identity and history plus backoff state. They require a
settled prior writer and unchanged relevant fingerprints; a crash, orphan, lost
native handle or uncertain external side effect is a reconciliation problem,
not a retryable provider failure. Record prior authority once and respect its
scope.

## Capture Contract

Capture is bounded and redacted before it is written to disk:

```text
<run-dir>/<job-id>/
  command.txt             # CLI jobs
  stdout.txt              # CLI jobs
  stderr.txt              # CLI jobs
  result.md               # internal and native jobs
  status.json
  session.json            # Pi jobs: session id and path
  native-<attempt-id>.json
  artifacts/
  attempt-<n>/
```

In-session jobs have no process surface. They write `result.md` plus
`status.json` with the resolved agent and a null process exit code. Never put
tokens, cookies, credentials, raw environment values, or private keys in any
capture.

The durable journal and bounded merged job log for supervised runs live under
`<run-dir>/supervisor/<supervisor-run-id>/`; read them per
[observation.md](observation.md). Private invocation files persist argv and
environment values for worker recovery, so they are excluded from diagnostic
exports rather than claimed to be absent from disk. Explicit truncation means
later content may be absent; never claim the tail survives when the supervisor
keeps only a bounded prefix.

## Arbiter Contract

The arbiter contract — the pass predicate, the independence requirement, the
family-comparison rule, and the reporting consequence — is owned by
[verification.md](verification.md). It is deliberately not restated here: this
file owns the machine fields, and acceptance is not one of them.

The only arbiter field this file defines is `acceptedWithoutC3` on the attempt
record above, which records whether the escalation matrix accepted the attempt
without a C3 call so the report can aggregate it.

The arbiter route must satisfy the judgment floor in
[routing-policy.md](routing-policy.md). Independence is verified from the live
inventory, not asserted from a copied provider name. The independence check
itself is owned by [verification.md](verification.md);
[safety-policy.md](safety-policy.md) owns only the rule that no automated signal
may weaken it.

## Illustrative Spec

Placeholders below must be resolved and verified before dispatch.

```yaml
version: 1
concurrency: 2
jobs:
  - id: scout-contract
    runtime: "<verified-read-runtime>"
    task: scout
    cwd: "<workspace-root>"
    prompt: "Map the contract owners and cite source evidence."
    timeout: 8m
    expected_output: "Source-backed contract map."

  - id: inspect-tests
    runtime: "<verified-read-runtime>"
    fallback_runtime: ["<verified-fallback-runtime>"]
    task: test
    cwd: "<workspace-root>"
    prompt: "Identify copied inventories and propose source-derived gates."
    timeout: 8m
    expected_output: "Test-coupling report with file evidence."

  - id: arbiter
    runtime: "<verified-judgment-runtime>"
    task: review
    cwd: "<workspace-root>"
    prompt: "Reconcile both reports and reject unsupported claims."
    depends_on: [scout-contract, inspect-tests]
    timeout: 8m
    expected_output: "Verified arbiter verdict."
```

The execution schema is versioned independently of live routing. Update the
owning routing or runtime reference when selection policy or evidence changes;
do not refresh examples with a new catalog.
