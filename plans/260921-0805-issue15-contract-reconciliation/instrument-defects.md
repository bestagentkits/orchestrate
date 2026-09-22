# Instrument defects found while verifying the issue #15 contracts

Companion to `conflict-register.md`. The register covers contradictions between the
normative references; this file covers defects in the **verification apparatus itself**.
They are recorded separately because a broken instrument produces confident wrong answers
about contracts that are perfectly correct.

Each entry states the defect, the evidence that established it, why it matters, and the
procedure that replaces it. A defect that only gets fixed without being written down comes
back.

## ID-1 — Stale bytecode silently defeated a mutation-test restore

**Severity: high.** This one made a correct source file look broken, and it would equally
have made a *broken* file look verified.

### What happened

Mutation testing was used to prove that the new contract tests can fail. The procedure was:
copy the module to a backup, patch it to the legacy behaviour, run the suite and confirm
failures, then copy the backup back and confirm the suite passes again.

For `tools/contracts/routing.py` the restore appeared to fail. After restoring from a
byte-identical backup, three tests still failed, consistently.

### Evidence

- The restored file's hash equalled the pre-mutation hash exactly
  (`md5 1728929fdfcfb7694405f17d5a01744b`), and contained no trace of the mutation.
- `sed` and `inspect.getsource` both showed the **correct** source:
  `return tier_rank(tier) >= tier_rank(required_tier)`.
- `dis.dis` on the loaded function showed the **mutant's** bytecode instead: the tier
  comparison was absent and the function ended in `RETURN_CONST True`.
- A direct call returned `True` for `clears_capability({"capabilityTier": "C1"}, "C2")`,
  which the correct source cannot produce.
- Loading with `PYTHONPYCACHEPREFIX=/tmp/pyc-fresh`, which forces recompilation from
  source, returned the correct `False`.

So the source was right and the executing bytecode was wrong: `__pycache__` still held the
compiled mutant, and it was loaded in preference to recompiling.

### Why it matters

Mutation testing is only evidence if the code under test is provably the code on disk.
With a stale cache, both directions of the claim are unsound:

- a "the fixture fails as expected" result may be measuring a mutation that is no longer
  present;
- a "restored and green" result may be measuring whatever bytecode happens to be cached.

This is the same class of defect the repository already warns about for the maintenance
sweep: a check that is green while measuring the wrong artifact proves nothing. It is
worth noting the direction of the risk here — the failure was loud (tests failed after a
correct restore), but the mirror case is silent: a restore that appears to pass because
the cached mutant happens to satisfy the suite.

### Procedure that replaces it

1. Any run that exercises mutated code, and any run that verifies a restore, sets
   `PYTHONPYCACHEPREFIX` to a scratch directory so compilation always happens from source.
2. The restore is verified by **content hash first**, then by the suite, and the hash is
   recorded. A hash match without a green suite, or a green suite without a hash match, is
   treated as a failure rather than a pass.
3. Where a test's outcome is load-bearing, the loaded bytecode is inspected for the
   specific change under test rather than inferred from the suite's exit status alone.

### Side effect on earlier results

The earlier mutation cycles for `route_identity.py`, `cost_dimensions.py` and `quality.py`
were checked for this defect. In each case the post-restore suite was green, which is only
possible if the cached bytecode matched the restored source, so those results stand. All
four modules were then re-run with a clean cache prefix and passed.

## ID-2 — A test directory without `__init__.py` sat outside discovery

**Severity: high.** Thirty-one tests never ran, and two mutations appeared to survive because
the tests that would have caught them were never collected.

### What happened

The instrumentation tests were added under `tools/benchmark/tests/`, and the suite was run as
`python3 -m unittest discover -s tools -t .`. The reported count stayed at exactly the number
of contract tests, and every run printed `OK`.

While re-running mutation checks for the trial schema, both mutations were confirmed applied
by content hash and both suites still came back `OK`. That is the signature of a test that is
not being executed rather than a test that cannot fail, so the count itself was checked: it
had not changed after adding a file with thirty-one test methods.

### Evidence

- `tools/benchmark/tests/` had no `__init__.py`. `unittest discover` does not recurse into a
  subdirectory that is not an importable package, so the new module was skipped silently.
- The discovery total was 259 both before and after the instrumentation tests were added.
- After adding `tools/benchmark/tests/__init__.py`, the same command reported **290**, and the
  two mutations then failed with 1 and 2 failures respectively.

### Why it matters

This is a quieter relative of ID-1 and it produced the same false confidence. A green suite
that does not contain the test in question is indistinguishable, from the outside, from a
green suite that does. It also propagated outward: the mutation evidence for this module was
briefly recorded as "mutations survived", which would have been reported as a genuine gap in
the contract.

### Procedure that replaces it

1. Every test directory carries an `__init__.py`, so it is an importable package.
2. A new test file is confirmed to change the discovered total before its result is used.
3. Mutation results are only accepted after the mutation is confirmed present by content hash
   **and** the failing count is non-zero. A mutation that "survives" is treated as a
   discovery problem until the test is shown to run.

## ID-3 — An installed extension silently re-routed the declared model

### What happened

The first worker-frontier run declared six models and measured one. Every arm's session
opened with `model_change -> <the declared model>` and then immediately switched to
`opencode-go/deepseek-v4.1-flash`, which then performed **100% of the paid work**. The
declared model appeared in the session as a `model_change` with no usage at all.

### Evidence

- Per-model cost attribution over the session JSONL: `opencode-go/deepseek-v4.1-flash`
  $0.013094 of $0.013094 (100.0%) for an arm declaring `openai-codex/gpt-6-astra`.
- The same model on the same task cost $0.975084 in the earlier plane-on run, where the
  session's only model was `openai-codex/gpt-6-astra`. The apparent 66x saving was the
  extension's substitution, not a policy improvement.
- Isolation, one trivial call each:
  - `--no-skills --provider openai-codex --model gpt-6-astra` -> `gpt-6-astra` **then
    `opencode-go/deepseek-v4.1-flash`**.
  - `--no-extensions --no-skills --provider openai-codex --model gpt-6-astra` ->
    `openai-codex/gpt-6-astra` only.
- Auth was not the cause: `pi auth check --provider {openai-codex,opencode-go,deepseek}
  --json` reported `status: ready` for all three while the substitution still happened.

### Why it matters

Every arm in that run was labelled with a model that did not run. Because the substituted
model was far cheaper, the contamination also inverted the headline metric: the run would
have been reported as a large cost win for the new policy. This is the single most
dangerous defect found in this goal, because it is silent, it is cheap, and it produces a
plausible positive result.

### Procedure that replaces it

1. The harness always passes `--no-extensions`, exactly as it already passed `--no-skills`.
2. A trial is resolved by **cost weight**, not by `model_change` count, and any paid model
   other than the declared one sets `armContaminated` and lists the offenders in
   `foreignModels`.
3. A trial with no paid model at all resolves to `unknown`, never to the declared model.

## ID-4 — `dominant_model` counted `model_change` entries instead of weighting by cost

### What happened

The field whose purpose is to detect ID-3 reported the *declared* model as the resolved
one. Both models had exactly one `model_change` entry, and `max()` over a dict of equal
counts returns the first key encountered — the declared model.

### Evidence

Every contaminated trial recorded `requestedProvider/requestedModel` identical to
`resolvedProvider/resolvedModel`, while the cost attribution showed the work was done
entirely by a different model. The instrument agreed with the arm's own label and thereby
confirmed it.

### Why it matters

An instrument that reports the requested value as the resolved value is worse than no
instrument: it converts a detectable mismatch into a false confirmation, and it does so in
the field a reviewer would check first.

### Procedure that replaces it

Resolution is a function of paid cost (`resolve_models`), returning the dominant model, the
full set of paid models, and a contamination verdict. Counting activity is retained only
for the raw `models` tally.

## ID-5 — A provider rejection was recorded as a task failure

### What happened

`gpt-5.3-codex-spark` is listed by the live catalog and refused by a ChatGPT-account login.
`pi` exits 0 in that case, so the harness recorded `status: ok`, `agentExitCode: 0`,
`success: False`, `costUsd: 0.0000`, `durationSeconds: 3.78` — an availability fact stored
as a quality verdict.

### Evidence

The provider's own message, from the model's JSON stream:

```text
Codex error: The 'gpt-5.3-codex-spark' model is not supported when using Codex with a ChatGPT account.
```

Left unhandled, this would have appeared in the frontier table as "`gpt-5.3-codex-spark`:
0/20 tasks" — indistinguishable from a model that ran and failed.

### Why it matters

A candidate-set measurement must not silently convert "cannot run here" into "ran badly".
The frontier's whole purpose is to rank models, and this defect would have removed a model
for a reason that has nothing to do with its capability.

### Procedure that replaces it

1. `provider_error()` reads the trial's session files for `stopReason: error` with an
   `errorMessage`; such a trial is `status: invalid` with
   `failureClass: infrastructure`, and is excluded from quality verdicts.
2. `tools/benchmark/probe_models.py` runs one trivial call per candidate **before** arms are
   planned, and records `usable` with the provider's rejection message. On this machine it
   found 13 of 14 candidates usable, with `gpt-5.3-codex-spark` the sole rejection.

## ID-6 — The auth-readiness probe invoked the model instead of checking auth

### What happened

`pi auth list` and `pi --no-extensions auth check --provider X` are not valid commands in
this pi version. Rather than failing, pi treated the argument text as a **prompt**, called a
model, and returned prose. That prose was briefly read as a readiness report, and the call
was billable.

### Evidence

- `pi auth status` -> `Error: Unknown auth command "status". Use "pi auth print-api-key",
  "pi auth print-bearer-token", or "pi auth check".`
- `pi auth check` (no provider) -> `Error: Auth checks require --provider <provider> or
  --model <model>`.
- `pi auth check --provider openai-codex --json` -> `{"status":"ready","provider":"openai-codex","authType":"oauth"}`.
- The manifest's frozen `authReadiness` was derived from **env-file presence**, not from a
  probe, so it asserted readiness that no probe had established.

### Why it matters

A readiness check that spends money, returns model prose, and cannot fail is not a check.
It also produced a false negative in the opposite direction: readiness was reported for a
provider whose model the account cannot actually run (ID-5).

### Procedure that replaces it

Readiness is established by `pi auth check --provider <provider> --json` and by the model
probe in `probe_models.py`. Presence of a credential source is recorded as provenance, never
as readiness.

## ID-7 — The recorded cost is a price-table artifact, not money spent

### What happened

The same provider and model recorded `usage.cost` for input tokens at **$10 per 1M** in the
earlier run and **$0.15 per 1M** in this one — a 66x difference with no change in the model,
the provider or the workload.

### Evidence

- Earlier run: `input=24607 -> cost.input=0.24607`.
- Later run: `input=40425 -> cost.input=0.00606375`.
- Both sessions name `openai-codex/gpt-6-astra` as their model.

### Why it matters

Cost is the primary metric of the pre-registered analysis, and it is computed by pi from a
price table that can change between runs and between catalog refreshes. Two consequences:

1. Cost is comparable **only within one frozen price table**. Cross-run cost comparisons are
   not evidence, and the earlier $400 projection was built on the inflated table.
2. This account authenticates with an OAuth (ChatGPT-account) login, so the recorded value
   is an API-equivalent estimate rather than money billed. That is why the manifest
   separates `actualMarginalCostUsd` from `apiEquivalentCostUsd`; the pilot must declare
   which dimension it reports and must not present one as the other.

### Procedure that replaces it

The catalog digest is frozen with the manifest and re-checked at run start, so the price
table in force is recorded with the results. Any cost comparison across runs whose catalog
digests differ is reported as incomparable rather than as a finding.

## ID-8 — The contamination guard flagged the treatment as the defect

### What happened

The first ablation attempt marked **every orchestrate arm** contaminated. V1 through V5 each
recorded three contaminated trials, naming `deepseek/deepseek-v4-pro`,
`openai-codex/gpt-5.5` and `opencode-go/deepseek-v4.1-flash` as having done uninvited paid
work. Those arms dispatch 10 to 18 times per trial **by design**: delegating to other models
is the treatment the experiment exists to measure.

### Evidence

The guard was built for ID-3, where a non-dispatching arm's declared model was silently
replaced. The recorded footprint separates the two cases without ambiguity:

| Arm | Dispatches per trial | Paid models | Old verdict | Correct verdict |
|---|---|---|---|---|
| V0 | 0, 0, 0, 0 | 1 | clean | clean |
| V1 | 11, 13, 12 | 4 | contaminated x3 | clean |
| V2 | 10, 11, 10 | 4 | contaminated x3 | clean |
| V3 | 12, 13, 11 | 5 | contaminated x3 | clean |
| V4 | 13, 18, 10 | 4 | contaminated x3 | clean |
| V5 | 13, 13, 11 | 5 | contaminated x3 | clean |
| VN | 0, 0, 0 | 1 | clean | clean |

The discriminator is the arm's own declaration: `directive == "orchestrate"` **and** no
`noDispatchNote`. VN carries the orchestrate directive *and* the no-dispatch note, and its
zero dispatch count confirms the note was honoured.

### Why it matters

A guard that reports intended behaviour as a defect is as damaging as one that misses a real
defect, and here it would have been worse: it invalidated exactly the arms the experiment
was built to measure. Had the verdict been trusted, the ablation would have been reported as
"every orchestrated arm was contaminated", which is a statement about the instrument
presented as a statement about the policy.

### Procedure that replaces it

1. `arm_may_dispatch(spec)` derives the expectation from the arm spec, not from the arm's
   name or from the run's variant list.
2. A **dispatching** arm is contaminated only when its declared coordinator did no paid work
   at all — the ID-3 failure mode.
3. A **non-dispatching** arm is contaminated when any other model did paid work.
4. The verdict carries the reason, so a warning states which rule fired rather than only that
   one did.

## ID-9 — An 18-hour run died because it was a child of the session

### What happened

The first ablation attempt stopped at 22 of 140 trials when the Pi session restarted. The
harness was an ordinary child of the session process, so it was terminated with the session.
Nothing was corrupted; the run simply stopped, and the elapsed hours bought only the trials
already on disk.

### Evidence

- The harness PID recorded at launch was absent, and no `run_benchmark` process remained.
- The log's final line was trial 22; `results.jsonl` held 22 rows and no partial record.
- Relaunching with `--resume` reported `22 trial already recorded, skipping them` and
  `budget already spent $33.3209`.

### Why it matters

A long run whose survival depends on the interactive session is not a long run; it is a run
that happens to survive. The failure is silent in the sense that matters: the artifact looks
complete and internally consistent, and only the missing trials reveal that it stopped.

### Procedure that replaces it

1. The harness is launched detached (`setsid nohup`), so session teardown does not reach it.
2. `--resume` re-derives the spent budget from the sessions already on disk rather than
   restarting the count, which keeps the cap meaningful across restarts. Note the small
   difference that makes this worth stating: the counter read $33.3209 while the recorded
   trials summed to $32.6648, because one interrupted trial's sessions were on disk without
   a result record. The counter is the conservative figure, which is the right direction for
   a budget.

## ID-10 — Any provider error was treated as an unavailable model

### What happened

`provider_error()` marked a trial `invalid` on the first `stopReason: error` carrying an
`errorMessage` anywhere in the session. Five ablation trials were therefore recorded as
invalid **while succeeding**, each with real cost and 10 to 14 dispatches:

| Trial | Cost | Duration | Dispatches | Recorded | Truth |
|---|---|---|---|---|---|
| V1 `slugify-transliteration` | $3.2530 | 939.9 s | 10 | invalid | succeeded |
| V5 `tag-summary-dedupe` | $2.1055 | 425.8 s | 12 | invalid | succeeded |
| V5 `money-rounding` | $1.8935 | 458.6 s | 12 | invalid | succeeded |
| V3 `tag-filter-union` | $1.8040 | 422.6 s | 14 | invalid | succeeded |
| V3 `csv-rfc4180` | $1.7910 | 533.1 s | 13 | invalid | succeeded |

The three messages involved are not the same kind of event:

- `Codex error: The 'gpt-5.3-codex-spark' model is not supported when using Codex with a ChatGPT account.`
- `WebSocket error`
- `Codex error: Our servers are currently overloaded. Please try again.`

The genuine case (ID-5) looked like this: cost $0.0000, duration 3.8 s, no paid work at all.

### Why it matters

Two of the three messages are transient, and the third is not even a failure of the trial's
own model: an orchestrator **probes** candidate models as part of its job, so it encounters
refusals by design. Treating every such error as an availability verdict did two things. It
discarded five valid observations, and it buried a real finding inside a false alarm — the
orchestrate arms dispatch to `gpt-5.3-codex-spark`, a model this account cannot run, so part
of their spend is spent discovering a capability the live catalog alone does not reveal.

### Procedure that replaces it

`classify_provider_error(rejection, cost_usd)` returns `none`, `invalid` or `recovered`. Only
a rejection with **no paid work behind it** is `invalid`. A rejection with paid work behind it
is `recovered`: the trial is kept, and the message is recorded in `recoveredError` as a
reliability observation rather than an availability verdict.

### Residual, stated because it affects the results

The ablation process already had the old rule loaded when it wrote its records, so the
stored `status` field carries the old verdict for every trial it wrote. The analysis
therefore **recomputes** the verdict from `failure` and `costUsd` for all trials instead of
trusting the stored `status`. Under the corrected rule, none of the 140 trials is `invalid`
and five are `recovered`; no model was refused outright during the ablation.

## Standing rule for this goal

A test result is only accepted when the identity of the executed code is established, not
assumed. Content hashes, and a forced recompilation where mutation is involved, are the
minimum evidence for that claim.

A benchmark result is only accepted when the identity of the executed **model** is
established, not declared. The arm's label is a request; only paid usage shows what ran.
For the same reason, a readiness claim must come from a probe that can fail, and a cost
claim must name the price table and the cost dimension it belongs to.
