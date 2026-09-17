# Pi Onboarding

This reference brings the Pi coding agent (`pi`) from missing or
unauthenticated to `available` so that orchestrated jobs can run on it. It is
a visible setup step that runs after discovery reported the gap, never inside
discovery itself, and only for a candidate a job or the user asked for. The
session and dispatch contract lives in [pi-sessions.md](pi-sessions.md).

The portable-setup pattern here is adapted from
the unofficial `zuey-pi-setup` repository (`github.com/mrgoonie/zuey-pi-setup`),
which is cited as provenance and is not a dependency of this skill: Pi
has no config
export or import, but the `packages` array in its `settings.json` is a
manifest that Pi reinstalls from on startup, so carrying the manifest carries
the extension set. Upstream installation requirements (the Node floor,
package name, uninstall) are owned by the Pi quickstart in the
`earendil-works/pi-mono` repository; read them fresh rather than trusting a
copied pin.

## Decide whether to onboard

- Pi was pinned by a job, listed as a fallback, or named by the user, and the
  probe reports it missing, unidentified, or `not_ready`: onboard.
- Pi was only an optional discovery candidate: skip it with a reason and say
  that onboarding is available on request.

Apply AgentKit's mutation tiers. A global npm install is additive and
reversible, so proceed with a visible notice on stderr and no confirmation
prompt. Overwriting an existing Pi profile (`~/.pi/agent` or the directory in
`PI_CODING_AGENT_DIR`) is a destructive overwrite: snapshot the existing files
first and confirm. Credentials are the user's alone: the coordinator never
types, copies, or stores an API key or token, and never restores another
machine's `auth.json`.

## Steps

Order matters here because each step's verification feeds the next; keep
the sequence.

### 1. Detect

Resolve `command -v pi` and `pi --version`, then `node --version`. Node
version managers such as nvm and fnm install global packages per Node
version, so `pi` exists only in a shell that activated that version; record
the resolved path and its symlink target so dispatch uses the same binary the
probe saw. On Windows the setup scripts below need Git Bash or WSL.

### 2. Install

```bash
npm install -g @earendil-works/pi-coding-agent
```

Pin a version only when the user's setup manifest requires one. Report the
exact command and the tail of its output. If npm refuses to write to its
global prefix, switch to a user-writable prefix or a version manager rather
than elevating privileges. Rollback is `npm uninstall -g
@earendil-works/pi-coding-agent`.

### 3. Prepare the profile

Pi creates a minimal profile on first run, which is enough for orchestration:
fewer extensions mean faster startup, no nested agents, and no surprise
tools. Prefer this for a machine that only runs headless jobs.

Restore a portable setup instead when the user keeps one. In that pattern:

- `settings.json` carries the `packages` manifest plus model, theme and
  compaction defaults; Pi installs missing packages on the next start, which
  can take minutes with a large manifest.
- Rehearse into a scratch profile first with
  `PI_CODING_AGENT_DIR=<scratch-dir>` so nothing real is touched, then run the
  real restore with the existing `settings.json` snapshotted.
- Copy only setup files. Session history, missions, memory, package caches,
  `auth.json`, and any extension config that holds tokens (notification
  extensions are the usual case) stay out.
- Some extensions are inert or need an interactive first run; a desktop
  automation helper that requests OS accessibility permissions is one
  example. They do not block headless jobs but they will not work in them.
- Verify with `pi list` that the installed package count matches the
  manifest.

This skill ships and installs no such script, and no step here requires fetching
one from a third-party repository. Any script you bring to this
rehearsal-then-real sequence is unofficial and profile-overwriting by design:
read it first and take your own snapshot before running it.

### 4. Authenticate (user action)

Tell the user which provider the selected route needs. They either export the
provider's API key variable in the shell that will run the jobs, or run `pi`
interactively and use `/login` for an OAuth provider. The provider list and
variable names are in the installed package's `docs/providers.md`.

Verify afterwards with a readiness check that prints no secret:

```bash
pi auth check --provider <provider> --no-refresh --json
```

`ready` completes this step. `not_ready` with `provider_not_found` means the
provider name is wrong for this installation; `not_ready` without credentials
means the login did not land.

### 5. Make the skills reachable

Headless jobs load skills by explicit path, so put the skill where the jobs
will find it. Copying or linking this skill directory and passing
`--skill <path>` needs no project trust; project-scope resources under `.pi/`
do.

When you use AgentKit, its kit projection is the managed alternative:

```bash
ak kit init <kit> --target pi            # project scope: .pi/ in this repository
ak kit init <kit> --target pi --global   # user scope: the active Pi profile
```

Project-scope resources under `.pi/` require project trust in a headless
run (`--approve`), whereas a skill passed with `--skill <path>` loads without
a trust decision. Use `ak` for refresh and uninstall; never hand-edit the
generated extension.

### 6. Verify

Re-run the probe with a timeout that covers extension startup, then a smoke
test in a scratch directory that leaves no session behind:

```bash
# Coordinator-owned probe, with a timeout that covers extension startup
pi --version
pi auth check --provider <provider> --no-refresh --json

# Smoke test in a scratch directory that leaves no session behind
env PI_OFFLINE=1 pi -p --mode json --no-session --no-extensions --no-skills \
  --no-context-files "Reply with the single word READY"
```

With the AgentKit CLI installed, `ak orchestrate probe --runtime pi --json
--timeout 60s` performs the version and help half of this probe.

The stream must start with a `session` header and end with `agent_end`.
Record Pi in `<run-dir>/runtimes.json` as `available` with the probe, the
auth check and the smoke test as evidence.

### 7. Report

State what was installed and where, the observed version, the profile
decision, what the user still has to do, and the rollback command. An
onboarding that stops at authentication is still progress; report it as
blocked on the user with the exact remaining action.

## Portable setup: copy or leave

| Item | Carry | Reason |
| --- | --- | --- |
| `settings.json` | yes | packages manifest, model and TUI defaults |
| system-prompt append file, prompt templates, themes | yes | plain setup files |
| locally written extensions and their config | yes | not on npm, cannot be reinstalled |
| model catalog cache | optional | saves a refresh wait, harmless if stale |
| `auth.json` | no | API keys and OAuth tokens; log in on the new machine |
| `sessions/`, `missions/`, `memory/` | no | history and state, may hold internal data |
| `npm/`, `git/` package caches | no | reinstalled from the manifest |
| `trust.json` | no | contains the old machine's paths |
| generated `extensions/agentkit-*` | no | AgentKit kit projection regenerates them with correct absolute paths |
| configs holding tokens (notifications, webhooks) | no | credentials; reconfigure by hand |

## Troubleshooting

| Symptom | Cause | Fix |
| --- | --- | --- |
| `pi: command not found` right after install | version-manager shell has not activated that Node version | activate the version, or call the resolved binary path |
| Probe reason `help-probe-timeout` | extensions load before help prints | raise the probe `--timeout`; dispatch with `--no-extensions` when the job allows |
| First run stalls for minutes | packages manifest installing | wait once interactively or run `pi list` afterwards; dispatch with `PI_OFFLINE=1` |
| `EACCES` from npm | global prefix not writable | user-writable prefix or version manager, not elevated install |
| Setup scripts fail on Windows | run from PowerShell or cmd | use Git Bash or WSL |
| Project skills ignored in a headless run | project not trusted | `--skill <path>` or `--approve` for a trusted repository |
