# Oh My Pi (`omp`) Adapter

Adapter note for the Oh My Pi runtime. Implements
[runtime-adapter-contract.md](../references/runtime-adapter-contract.md).

**Status:** documented probe target. Not a support claim, and not in any
inventory until a probe is recorded. Being named here means only that this is
what to probe.

## Identity and probe focus

Confirm product identity before trusting a same-named executable. Reject a
shim that merely responds to `--version`.

The probe must establish, from live help and the installed package:
non-interactive entry, working-directory control, output capture, model or role
selection, approval and permission controls, extension loading, nested
task-agent behavior, and native time limits.

Upstream reference: the Oh My Pi README and the `can1357/oh-my-pi` repository.
Read the installed version's own documentation first; upstream may be ahead.

## Expected adapter capabilities

Probe each of these rather than assuming it:

- **`start`** — a documented print or JSON mode that returns one result per
  invocation, versus a long-lived RPC/ACP mode that requires a held-open stdin.
- **`observe`** — whether a structured event stream exists, or only a final
  result with harness-reported status.
- **`capture`** — where the final message lands, whether stdout can be redirected
  safely, and whether an explicit output-file option exists.
- **`profile`** — provider and model or role discovery for this installation.
- **`steer`, `cancel`, `resume`, `fork`** — each verified separately. RPC/ACP
  mode may support intervention that print mode does not.
- **Nested agents** — whether extensions or task agents can spawn children; if
  so, count that work in the run's concurrency and budget.

## Verification steps

1. Resolve the executable and record its absolute path and symlink target.
2. Bound a version and help probe with an external timeout.
3. Read live help for each capability above; consult official documentation only
   where help is ambiguous, and record what was checked.
4. Run the adapter conformance checks from
   [runtime-adapter-contract.md](../references/runtime-adapter-contract.md).
5. Record the `runtimes.json` profile with `role: runtime` and every unproven
   field as `unverified`.
6. Run a bounded smoke test in a scratch directory and confirm it settles with
   the runtime's own completion evidence.

## Capture tier

Prefer a structured event stream plus final result and exit status. Fall back to
bounded stdout/stderr with an explicit exit status. Treat final text only, or
output without trustworthy completion state, as advisory-only.

## Known failure signatures

| Symptom | Action |
| --- | --- |
| Help probe exceeds its budget | Raise the probe budget; a slow launcher is not a broken binary |
| Unknown flag or model | Re-read live help; rebuild the command. Never guess a replacement |
| Approval prompt with no non-interactive path | Mark `unavailable` for headless dispatch until the operator completes setup outside the run |
| Print mode exits without its completion event | Treat the attempt as `unsettled` per [event-protocol.md](../references/event-protocol.md) |
| Nested agents spawn unexpectedly | Count them in the budget, or disable them with a verified control |

## Risk posture defaults

Verify, do not trust: approval mode, tool gating granularity, write boundary, and
whether an OS sandbox applies on this host. A cwd argument is not a sandbox, and
an advertised sandbox flag is `unverified` until OS enforcement is confirmed.

## Independence caveat

OMP can resolve to the same provider and model family as another runtime.
Different executable names do not establish independent review; compare resolved
families per [verification.md](../references/verification.md).
