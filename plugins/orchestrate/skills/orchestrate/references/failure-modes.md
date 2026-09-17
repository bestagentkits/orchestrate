# Failure Modes

Each entry below is a **hard stop** or a bounded decision. When the decision
plane is enabled it may supply a suggested `failure_class` and
`recovery_class` from the closed taxonomy in
[decision-plane.md](decision-plane.md). That suggestion is evidence, not
authority:

- A classified `PERMISSION`, `SANDBOX` or `AUTH` result **must still hit the
  hard stop for that entry**. Classification does not soften it.
- `request_approval` is a report, never an approval. Nothing here can set
  `approval` or widen a tool grant.
- `recovery_class` never selects a command, a flag, or a model.
- A class that conflicts with the entry's required action is discarded, and the
  divergence is recorded in the decision trace.

- **Missing or unauthenticated runtime:** evaluate declared fallbacks through
  the same live policy; otherwise block.
- **Missing internal agent:** re-resolve against the live agent list; use a CLI
  fallback only when it meets the same floors.
- **Unknown flag or model:** fail the attempt, return to live probe, and never
  guess a replacement.
- **Permission prompt:** stop the job and report the exact approval boundary.
  Do not convert it into an automatic retry with a broader grant.
- **Timeout:** preserve bounded partial output, fail the job, and block
  dependents.
- **Retryable provider failure** (rate limit, quota, transient network): retry
  only within the bounded policy declared in [job-spec.md](job-spec.md), only
  after confirmed settlement and unchanged owned/input state.
- **Interrupted run:** reload the prepared plan and reconcile: re-read
  persisted state, validate accepted inputs and artifacts, reconnect to the
  existing supervisor attempts, and block ownership you cannot prove. Internal
  handles require equivalent native inspection. Do not redispatch merely
  because a client died.
- **Ambiguous ownership:** sequence the jobs or assign separate worktrees and
  an explicit integration step.
- **Reference disagreement:** stop and report the contract mismatch instead of
  choosing whichever copied route looks newer.
- **Unsettled attempt:** an exit without settlement evidence, a lost handle, or
  an unconfirmed cancellation is a reconciliation problem, not a retry. Block
  the ownership boundary and preserve `attempt-<n>/` evidence.
- **Decision-plane unavailable:** continue under deterministic policy; record
  `none` with the reason. A disabled or degraded plane never blocks a run and
  never changes a hard stop.
