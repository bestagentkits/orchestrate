# Issue #15 invariant fixtures — recorded results

This file records the fifteen negative fixtures required by issue #15's validation section
("Add/document checks that can fail when…") and by success criterion 11 of the implementation
objective. The fixtures live in `tools/contracts/invariants.py`; the assertions live in
`tools/contracts/tests/test_invariant_fixtures.py`.

## How a fixture counts as evidence

Each fixture pairs two behaviours and one predicate:

- the **contract behaviour**, taken from the owned implementation;
- the **broken behaviour** it replaced, executed on the same scenario;
- the **invariant predicate**, applied to both results.

A fixture is only evidence when the predicate holds on the contract behaviour *and* fails on
the broken behaviour. The test module asserts both directions for all fifteen, and adds a
third assertion that the two verdicts differ, so a fixture that cannot fail is refused rather
than counted. This is the discipline the repository's own maintenance guidance requires: an
assertion whose baseline already satisfies it proves nothing.

The checks are behavioural rather than prose-grepping. Fourteen call the owned implementation
and the retired rule on identical inputs and compare verdicts; only R01 is a scan, because a
hardcoded normative default is a property of text rather than of a code path.

## The recorded result

Command (run from the repository root; the cache prefix is required by instrument defect ID-1
in `instrument-defects.md`):

```bash
PYTHONPYCACHEPREFIX=/tmp/pyc-inv python3 -m unittest discover -s tools/contracts/tests -t .
```

Recorded outcome: **259 tests pass**, of which the fixture module contributes the fifteen
regressions below. `run_all()` reports `fixtures=15 contract_holds=15 broken_fails=15`.

| ID | Regression | Owner | Contract | Broken behaviour |
|---|---|---|---|---|
| R01 | A provider or model name introduced as a normative default | the whole normative payload | holds | fails |
| R02 | A missing cost interpreted as zero | `metrics-and-self-improvement.md` | holds | fails |
| R03 | Two normalized effort labels reaching one real mode become two candidates | `benchmark-evidence.md` | holds | fails |
| R04 | A low-sample perfect rate outranks a statistically stronger candidate | `benchmark-evidence.md` | holds | fails |
| R05 | Semantic routing called despite a decisive deterministic winner | `routing-policy.md` | holds | fails |
| R06 | Micro-arbiter called on a structurally C3-mandatory path | `verification.md` | holds | fails |
| R07 | Stale or incompatible calibration reused | `verification.md` | holds | fails |
| R08 | Cost-aware ranking restores a hard-filtered candidate | `routing-policy.md` | holds | fails |
| R09 | Pareto pruning removes a required independent-review route | `routing-policy.md` | holds | fails |
| R10 | Quota burn compared with API cash as though both were dollars | `metrics-and-self-improvement.md` | holds | fails |
| R11 | A budget or objective that does not state its cost dimension | `metrics-and-self-improvement.md` | holds | fails |
| R12 | A content failure feeding recovery cost or a promotion loop | `metrics-and-self-improvement.md` | holds | fails |
| R13 | A permission or sandbox hard stop turned into a promotion | `fallback-policy.md` | holds | fails |
| R14 | The route trace missing a field or carrying classifier prose | `trace-and-logging.md` | holds | fails |
| R15 | Quality evidence used without recording its scope or degradation | `benchmark-evidence.md` | holds | fails |

The nine bullets in issue #15's validation section map onto R01–R09 directly. R10–R15 cover
the remaining acceptance items that are negative-testable: the two cost-conflation rules, the
undeclared-dimension refusal, the two failure-class boundaries, and the trace and evidence
scope requirements.

## What the fixtures do not cover

- **R01 is a scan.** It detects a model-name shape (`brand` optionally followed by a digit)
  across the normative payload. A pasted model name that does not take that shape would not be
  caught, and a legitimate generic mention of a harness is deliberately not flagged. The
  scanner's own ability to detect a name is itself tested, so the check cannot pass by being
  unable to find anything.
- **No fixture measures a paid run.** Nothing here executes the provider-matrix experiment,
  which the objective forbids.
- **The fixtures test the owned modules, not the prose.** A reference document could state a
  rule that the module does not implement; that divergence is what the conflict register and
  the maintenance sweep are for, and it is not detectable from these fixtures alone.
