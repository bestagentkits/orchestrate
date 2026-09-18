# Runtime Adapters

This directory is the **adapter index**. Each file is a capability map for one
runtime: what to probe, how to verify it, what it captures, how it fails, and
what to be suspicious of.

It is not a support roster and not a command catalog. Nothing here is proof that
a runtime is installed, authenticated, safe or capable. A doc note can never
cause a dispatch: only the live inventory described in
[runtime-profile.md](../references/runtime-profile.md) makes an adapter
selectable, and only a verified `available` state makes it eligible for routing.

The interface every adapter implements is owned by
[runtime-adapter-contract.md](../references/runtime-adapter-contract.md).

## What a note may and may not contain

The rule has three tiers, because a blanket ban is both unsatisfiable and
useless: the two Pi notes must preserve their verified procedure, while a stub
has no evidence behind anything it would copy.

**Forbidden in every note, without exception:**

- a resolved model identifier or a model list;
- a positive control claim. A control is written as something to verify, never as
  something the runtime has;
- a runtime-specific error string treated as a contract.

**Forbidden in a fenced unverified stub or an unprobed capability map:**

- any dispatch invocation, in any form. There is no evidence behind it.

**Permitted only in a verified adapter note:**

- the verified procedure, including an illustrative command shape, provided the
  note carries an adjacent instruction to verify every placeholder and flag
  against live help before use. That caveat is what makes the procedure evidence
  rather than a copied catalog, and it is mandatory, not decorative.

Either way, a note names **what to probe**, never **what the answer will be**.
The verification rule in
[runtime-adapter-contract.md](../references/runtime-adapter-contract.md) is what
makes a capability real.

## Note structure

Three structures exist, and mixing them is what makes an index dishonest:

| Note kind | Structure | Marked by |
| --- | --- | --- |
| **Full note** | the template below | a recorded live probe in `runtimes.json` |
| **Fenced unverified stub** | the stub template below | the leading banner and an as-of date |
| **Relocated verified note** | its own headings | the index row |

A **relocated verified note** keeps its own structure. The two Pi files were
moved out of core with their verified procedures intact, and their headings are
richer than the template; rewriting them to match a template would discard
verified detail for cosmetic uniformity. Relocated notes are marked as such in
the index.

A **stub** uses its own shorter structure, because it has no capability to map:
banner, what the stub is, probe focus, verification steps, graduation, and the
independence caveat. Forcing stub content into the full-note headings would
produce sections that assert nothing under headings that promise a capability
map.

## Adding an adapter

1. **Implement the contract.** Provide `discover`, `probe`, `profile`, `start`,
   `observe`, `capture`, and any optional methods the runtime supports.
2. **Run the deterministic probe.** Version, help, model or agent discovery,
   readiness, and a bounded smoke test, per
   [runtime-profile.md](../references/runtime-profile.md). No install, no login.
3. **Run the conformance checks.** All seven, from
   [runtime-adapter-contract.md](../references/runtime-adapter-contract.md).
4. **Record the profile.** Write the `runtimes.json` record with every unproven
   field as `unverified`. The annotation-only rule for `classifier_hint` is owned
   by [runtime-profile.md](../references/runtime-profile.md) and is not restated
   here.
5. **Verify the smoke test.** It must settle with the runtime's own completion
   evidence, not merely exit zero.
6. **Write the note** using the template below, and list it in the index.

A note that no live probe has touched is written as a **fenced unverified stub**:
one page, a leading banner, an as-of date, and no capability asserted as
available. It graduates to a full note only when a run records a probe in
`runtimes.json`.

## Note template

A newly authored note uses these headings, in this order:

| Heading | Contents |
| --- | --- |
| **Identity and probe focus** | How to tell this product from a same-named binary; what the probe must establish |
| **Expected adapter capabilities** | Which contract capabilities are expected, each phrased as a probe to run |
| **Verification steps** | The exact live checks to run before routing |
| **Capture tier** | Preferred structured surface and its fallback |
| **Known failure signatures** | Symptom → probe again / onboard / block |
| **Risk posture defaults** | Approval and isolation expectations **to verify, not to trust** |
| **Independence caveat** | Different executable names do not prove a different model family |

A stub uses this structure instead:

| Heading | Contents |
| --- | --- |
| banner | `Status: unverified — not a support claim, not in inventory`, plus an as-of date |
| **What this stub is** | why no evidence exists, and that writing a map from memory is the failure this skill forbids |
| **Probe focus** | what a future probe must establish from live help |
| **Verification steps** | the probe and conformance sequence, ending in a recorded profile |
| **Graduation** | the condition that replaces the stub with a full note |
| **Independence caveat** | no independence property can be claimed for an unprobed runtime |

## Index

### Documented adapters

A row here means a **written note exists**. It is not a support claim and not a
verification: no artifact in this repository marks an adapter verified. Only a
live probe recorded in `runtimes.json` makes an adapter selectable, and only a
verified `available` state makes it eligible for routing.

| Adapter | Role | Note |
| --- | --- | --- |
| Pi agent (`pi`) | job runtime | [pi.md](pi.md) — full note written from an authoring-time smoke run; still requires a live probe for the current host, onboarding in [pi-onboarding.md](pi-onboarding.md) |
| In-session subagents (`internal`) | job runtime | [internal-routing.md](../references/internal-routing.md) |

### Documented probe targets

These runtimes are named as probe targets because they have a documented
upstream surface. Their notes describe what to probe. Being listed is **not** a
support claim, and none of them is in any inventory until a probe runs.

This table answers *what to probe*; the table above answers *whether a note
exists*. `pi` appears in both on purpose.

| Target | Note | Upstream reference | Probe focus |
| --- | --- | --- | --- |
| Pi agent (`pi`) | [pi.md](pi.md) | Installed package docs and upstream repository `earendil-works/pi-mono` | Print/JSON versus RPC mode, provider and model resolution, tool and extension controls, explicit skill loading, project trust, run-scoped session directory, session identity |
| Oh My Pi (`omp`) | [omp.md](omp.md) | Oh My Pi README, upstream repository `can1357/oh-my-pi` | Print/JSON versus RPC/ACP mode, provider and model roles, cwd, approval, extensions, nested task agents, native time limit |
| Antigravity CLI (`agy`) | [agy.md](agy.md) | Google Antigravity headless documentation at `www.agy.dev/docs/cli/headless/` | Print input/output, model and agent discovery, sandbox on this OS, print timeout, conversation identity, instruction discovery |
| Grok Build (`grok`) | [grok.md](grok.md) | Grok Build CLI reference at `docs.x.ai/build/cli/reference` | Single-turn and prompt-file input, structured terminal result, model discovery, permission and sandbox controls, nested agents, session identity |

Do not copy Pi flags into OMP, equate an `agy` kit export with CLI execution
support, or equate a Grok model available inside another runtime with the Grok
Build runtime. Verify whether a native worktree flag actually applies in headless
mode; otherwise create the job worktree through the coordinator before launch.

### Unverified stubs

These runtimes are named by the accepted orchestration scope but appear nowhere
in this repository's evidence. Each note is a **fenced stub**: it states the
probe focus and asserts no capability. A stub is in no inventory and is
selectable only after a live probe records an `available` profile.

| Target | Note | Status |
| --- | --- | --- |
| Claude Code | [claude.md](claude.md) | unverified — not in inventory |
| Codex CLI | [codex.md](codex.md) | unverified — not in inventory |
| Gemini CLI | [gemini.md](gemini.md) | unverified — not in inventory |
| OpenCode | [opencode.md](opencode.md) | unverified — not in inventory |
| Aider | [aider.md](aider.md) | unverified — not in inventory |

## Independence

Two adapters can resolve to the same provider and model. Different executable
names do not establish independent review. Independence is verified from live
inventory evidence and compared by resolved model family, per
[verification.md](../references/verification.md). A note therefore carries an
independence caveat rather than a claim.
