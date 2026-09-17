# Grok Build (`grok`) Adapter

Adapter note for the Grok Build CLI runtime. Implements
[runtime-adapter-contract.md](../references/runtime-adapter-contract.md).

**Status:** documented probe target. Not a support claim, and not in any
inventory until a probe is recorded.

## Identity and probe focus

Confirm product identity before trusting a same-named executable. A Grok model
available **inside another runtime** is not the Grok Build runtime; do not equate
them.

The probe must establish: single-turn and prompt-file input, the structured
terminal result, model discovery, permission and sandbox controls, nested agent
behavior, and session identity.

Upstream reference: the Grok Build CLI reference at
`docs.x.ai/build/cli/reference`. Read the installed version's help first.

## Expected adapter capabilities

Probe each of these rather than assuming it:

- **`start`** — a non-interactive single-turn invocation, and whether a prompt
  file is accepted (preferred over inline prompt text).
- **`observe`** — the shape of the structured terminal result, and whether
  incremental events exist or only a final structured object.
- **`capture`** — how the structured result is retrieved and whether it can be
  redirected to a file.
- **`profile`** — model discovery for this installation.
- **`resume`** — whether session identity exists and can be continued or forked.
- **Permission and sandbox controls** — what can be restricted, and whether any
  control is enforceable in a headless invocation.
- **Nested agents** — whether the runtime can spawn child agents; if so, count
  that work in the run's concurrency and budget.

## Verification steps

1. Resolve the executable and record its absolute path and symlink target.
2. Bound a version and help probe with an external timeout.
3. Read live help for each capability above; consult the CLI reference only where
   help is ambiguous, and record what was checked.
4. Prefer prompt-file transport over inline text; verify it against live help
   rather than assuming the flag.
5. Run the adapter conformance checks from
   [runtime-adapter-contract.md](../references/runtime-adapter-contract.md).
6. Record the `runtimes.json` profile with `role: runtime` and every unproven
   field as `unverified`.

## Capture tier

Prefer the structured terminal result plus exit status. Fall back to bounded
stdout with an explicit exit status. Unstructured output without trustworthy
completion state is advisory-only and cannot support a load-bearing check.

## Known failure signatures

| Symptom | Action |
| --- | --- |
| Help probe exceeds its budget | Raise the probe budget |
| Unknown flag or model | Re-read live help; never guess a replacement |
| Structured result absent on exit | Treat the attempt as `unsettled` per [event-protocol.md](../references/event-protocol.md) |
| Permission prompt with no headless path | Mark `unavailable` until the operator completes setup outside the run |
| Nested agents spawn unexpectedly | Count them in the budget, or disable them with a verified control |

## Risk posture defaults

Verify, do not trust: approval mode, tool gating, write boundary, and whether a
sandbox applies on this host. Verify whether a native worktree flag applies in
headless mode; otherwise create the job worktree through the coordinator before
launch.

## Independence caveat

`grok` can resolve to the same provider and model family as another runtime, and
a Grok model reachable through a different runtime is not evidence of a separate
family. Compare resolved families per
[verification.md](../references/verification.md).
