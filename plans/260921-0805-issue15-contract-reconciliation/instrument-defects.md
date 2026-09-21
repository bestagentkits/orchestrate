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

## Standing rule for this goal

A test result is only accepted when the identity of the executed code is established, not
assumed. Content hashes, and a forced recompilation where mutation is involved, are the
minimum evidence for that claim.
