# Antigravity CLI (`agy`) Adapter

Adapter note for the Antigravity CLI runtime. Implements
[runtime-adapter-contract.md](../references/runtime-adapter-contract.md).

**Status:** documented probe target. Not a support claim, and not in any
inventory until a probe is recorded.

## Identity and probe focus

Confirm product identity before trusting a same-named executable. An AgentKit kit
export for `agy` is a discovery hint, **not** proof of headless execution
support; the probe must establish the CLI surface independently.

The probe must establish: print-mode input and output shape, model and agent
discovery, sandbox behavior **on this OS**, print timeout, conversation identity,
and instruction-file discovery.

Upstream reference: Google Antigravity headless documentation at
`www.agy.dev/docs/cli/headless/`. Read the installed version's help first.

## Expected adapter capabilities

Probe each of these rather than assuming it:

- **`start`** — a non-interactive print mode that accepts a prompt and returns a
  result without a TTY.
- **`observe`** — whether a structured or streamed event surface exists, or only
  a final printed result.
- **`capture`** — where the final result lands and whether an explicit output
  file is supported.
- **`profile`** — model and agent discovery for this installation.
- **`resume`** — whether a conversation identity can be continued.
- **Sandbox** — whether the advertised sandbox applies on this host, and what it
  actually bounds. Verify enforcement; an advertised sandbox is `unverified`.
- **Working directory** — whether cwd can be pinned and how it is enforced.

## Verification steps

1. Resolve the executable and record its absolute path and symlink target.
2. Bound a version and help probe with an external timeout.
3. Read live help for each capability above; consult the headless documentation
   only where help is ambiguous, and record what was checked.
4. Confirm whether a native print timeout exists; if not, the coordinator-owned
   external timeout is the only bound.
5. Run the adapter conformance checks from
   [runtime-adapter-contract.md](../references/runtime-adapter-contract.md).
6. Record the `runtimes.json` profile with `role: runtime`, and write the
   sandbox and approval fields `unverified` until enforcement is proven.

## Capture tier

Prefer a structured or streamed event surface plus a final result and exit
status. Fall back to bounded stdout with an explicit exit status. Printed final
text alone is advisory-only.

## Known failure signatures

| Symptom | Action |
| --- | --- |
| Help probe exceeds its budget | Raise the probe budget; do not switch binaries |
| Unknown flag or model | Re-read live help; never guess a replacement |
| Print mode requires an interactive terminal | Mark `unavailable` for headless dispatch |
| Sandbox advertised but unenforced on this OS | Record `unverified`; the worktree rule still applies, and destructive work stays blocked |
| Conversation identity absent | Treat `resume` and `fork` as unsupported for this route |

## Risk posture defaults

Verify, do not trust: whether print mode auto-approves, whether tool access can be
restricted, and what the sandbox actually contains. Never carry an approval or
isolation assumption across from another runtime.

## Independence caveat

`agy` can resolve to the same provider and model family as another runtime.
Different executable names do not establish independent review; compare resolved
families per [verification.md](../references/verification.md).
