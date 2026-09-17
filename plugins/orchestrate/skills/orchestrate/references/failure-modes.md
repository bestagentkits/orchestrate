# Failure Modes

- **Missing or unauthenticated runtime:** evaluate declared fallbacks through
  the same live policy; otherwise block.
- **Missing internal agent:** re-resolve against the live agent list; use a CLI
  fallback only when it meets the same floors.
- **Unknown flag or model:** fail the attempt, return to live probe, and never
  guess a replacement.
- **Permission prompt:** stop the job and report the exact approval boundary.
- **Timeout:** preserve bounded partial output, fail the job, and block
  dependents.
- **Interrupted run:** reload the prepared plan and reconcile: re-read
  persisted state, validate accepted inputs and artifacts, reconnect to the
  existing supervisor attempts, and block ownership you cannot prove. Internal
  handles require equivalent native inspection. Do not redispatch merely
  because a client died.
- **Ambiguous ownership:** sequence the jobs or assign separate worktrees and
  an explicit integration step.
- **Reference disagreement:** stop and report the contract mismatch instead of
  choosing whichever copied route looks newer.
