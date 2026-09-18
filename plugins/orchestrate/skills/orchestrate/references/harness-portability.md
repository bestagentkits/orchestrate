# Harness Portability

This document owns what the payload may assume about the harness that loads it, and
how the payload is installed. It is the only place those two questions are answered.

It makes two claims, and they are deliberately separate:

- **Loads.** The payload is a conforming Agent Skills directory, so any harness that
  implements the Agent Skills contract reads and can invoke it.
- **Can execute jobs.** A job needs the minimum capability set in
  [What a harness must provide](#what-a-harness-must-provide). A harness that loads
  the skill but lacks one of those capabilities still loads it; the affected step is
  disabled and recorded rather than assumed.

A harness must never be described as supported because it appears in a table here.
See [Verified harnesses](#verified-harnesses).

## The conformance surface

The payload is an Agent Skills directory: a `SKILL.md` carrying `name` and
`description` frontmatter plus a markdown body, alongside the reference documents it
links. That is the whole contract. Everything else this repository ships — plugin
manifests, a landing page, a README — is packaging for a particular installer and is
not part of the format.

There are exactly three harness features this skill may **never** depend on. Each is
listed with its reason, because the reason is what makes the rule checkable:

| Feature | Why it may not be load-bearing |
|---|---|
| `context: fork` | Claude Code only. A payload that needs a forked context is inert elsewhere. |
| `hooks:` | Claude Code, Cline and Kiro CLI only. Hook names and lifecycle semantics are not standardized. |
| `allowed-tools` | Widely supported but not universal, and the supported tool names are not standardized across harnesses. |

The rule that follows: **the body of this skill must be safe to run with the full
toolset.** A payload that is only safe where `allowed-tools` is honored is not
portable, so this skill never relies on tool restriction to stay inside its safety
boundary. It relies on the safety gate instead, which is enforced by the coordinator
in [safety-policy.md](safety-policy.md) and does not depend on what the harness
permits.

## Frontmatter this skill declares

These are the keys actually present in `SKILL.md`. The first two are the format; the
rest are extensions.

| Key | Status |
|---|---|
| `name` | Agent Skills format. Load-bearing. |
| `description` | Agent Skills format. Load-bearing — it is how a harness decides whether to load the skill. |
| `user-invocable` | AgentKit extension. Never load-bearing. |
| `when_to_use` | AgentKit extension. Never load-bearing. |
| `category` | AgentKit extension. Never load-bearing. |
| `keywords` | AgentKit extension. Never load-bearing. |
| `argument-hint` | AgentKit extension. Never load-bearing. |
| `license` | Metadata only. Never load-bearing. |
| `metadata` | Metadata only, including the skill version. Never load-bearing. |
| (unknown keys) | A conforming harness ignores unknown frontmatter. That tolerance is exactly why an extension key cannot be depended on. |

**No behavior in this skill may depend on a frontmatter key outside `name` and
`description`.** A harness that ignores unknown frontmatter ignores every AgentKit
extension listed above, and must still get the same behavior.

## Install with the skills CLI

The primary install command, verbatim:

```bash
npx skills add bestagentkits/orchestrate
```

This repository needs no CLI to run, and this is one installer among several — the
marketplace path in [Installing into Claude Code](#installing-into-claude-code) and the
clone-and-copy path in `README.md` both remain valid.

| Form | Purpose |
|---|---|
| `npx skills add bestagentkits/orchestrate` | Install into the current project. |
| `npx skills add bestagentkits/orchestrate -g` | Install globally for the current user. |
| `npx skills add bestagentkits/orchestrate -a <agent>` | Install for one named harness only. |
| `npx skills add bestagentkits/orchestrate --all` | Install to every detected harness. |
| `npx skills add bestagentkits/orchestrate --copy` | Copy files instead of symlinking them. |
| `npx skills add bestagentkits/orchestrate --list` | Inspect what would be installed, without installing. |
| `npx skills add bestagentkits/orchestrate --skill orchestrate` | Select the skill by name when a repository holds several. |
| `npx skills add bestagentkits/orchestrate -y` | Non-interactive; accept defaults. |

## What the CLI discovers here

The CLI also reads the Claude Code plugin manifests. The real paths in this
repository are:

- `.claude-plugin/marketplace.json` at the repository root — the marketplace
  definition.
- `plugins/orchestrate/.claude-plugin/plugin.json` — the plugin manifest.

**There is no root-level `.claude-plugin/plugin.json`.** A reader looking for one is
looking for a file that does not exist; the plugin manifest is the one under
`plugins/orchestrate/`. The marketplace definition itself is not copied here — read
[the manifest](../../../../.claude-plugin/marketplace.json) for its current contents,
because a copied manifest would go stale.

## Installing into Claude Code

The existing marketplace install is unchanged and still supported: add the
marketplace, then install the plugin from it. This is **one harness among many**, not
the default and not the target. The manifest that defines it is
`.claude-plugin/marketplace.json`, and it is the authority for the marketplace name
and the plugin source path — do not restate them here.

## Where the payload lands

| Harness class | Project path | Global path |
|---|---|---|
| Claude Code | `.claude/skills/orchestrate/` | `~/.claude/skills/orchestrate/` |
| Shared agents convention | `.agents/skills/orchestrate/` | `~/.agents/skills/orchestrate/` |
| OpenClaw | `skills/orchestrate/` | `~/.openclaw/skills/orchestrate/` |
| Pi | `.pi/skills/orchestrate/` | `~/.pi/skills/orchestrate/` |

**The authoritative and current list is the CLI's own documentation and the installed
version's `--help`.** This table names the classes a reader is most likely to need and
deliberately does not reproduce the installer's full agent catalog: a copied catalog
goes stale, which is the same rule this skill applies to runtime, model and flag
catalogs everywhere else. Resolve the path for your harness from live evidence.

## Verified harnesses

**No artifact in this repository marks a harness as verified.** The portability claims
above come from the published Agent Skills specification and from the installer's
documented behavior; neither is evidence that the payload loads on a given machine.

A harness becomes verified for a user only after a live install-and-load check on that
machine: the skill is installed, invoked, and observed to load and route. Until then,
treat it as untested. This mirrors the wording discipline in
[runtimes/README.md](../runtimes/README.md) — a listed path is not a support claim, and
a listed harness is not a verified one.

## What a harness must provide

The minimum capability set for executing jobs:

- A skill loader that reads `SKILL.md` and can invoke the skill.
- A filesystem the coordinator can write a run directory to.
- A shell or PTY, to dispatch a runtime.
- A way to run a job non-interactively, or a session that can be observed.
- Git, for worktree isolation.
- Network access, if benchmark-ranked routing is wanted. This is named here because
  the benchmark fetch depends on it, and a run without it must disclose a degraded
  ranking rather than claim a benchmark-ranked route.

A harness that lacks worktree support still **loads** this skill. What a missing
isolation capability does to the risk tier is a safety question, and it is answered
only in [safety-policy.md](safety-policy.md). This document states no tier rule and
implies none.

## Degradation rules

A missing harness capability disables the affected step and is recorded. It is never
silently assumed.

- **No subagent support:** `internal` is not a candidate for that run.
- **No headless dispatch:** only session runtimes are eligible.
- **No network:** benchmark ranking is degraded, and the report says so. The route is
  never described as benchmark-ranked when no benchmark evidence was fetched.
- **Unknown harness:** the run records `harness: unknown` on the run-level record
  defined in [job-spec.md](job-spec.md), and refuses to claim any harness-specific
  feature.

The `harness` field is named here and owned by
[job-spec.md](job-spec.md) — the rule above is unenforceable without a schema to write
the value into.

## Related

- [runtime-adapter-contract.md](runtime-adapter-contract.md) — what a conformed
  runtime adapter must expose.
- [safety-policy.md](safety-policy.md) — the sole safety authority, including the tier
  consequences of a missing isolation capability.
- [runtimes/README.md](../runtimes/README.md) — the per-runtime capability map and its
  listing discipline.
