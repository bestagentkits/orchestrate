# Metrics and Self-Improvement

Use the executable run's `metrics.jsonl` plus arbiter evidence. Compare accepted
quality and first-pass verification, retries, intervention count and reason,
wall time, and usage/cost only when reported. Preserve runtime, provider, model
family, task class, inputs and budget so comparisons mean the same thing.
Unknown cost is null, not free; more output is not better work.

Turn a diagnosed failure into a bounded regression case, rerun with equivalent
inputs and checks, and compare the result. A meaningful sample of comparable
jobs is needed before suggesting routing changes. Record suggestions; change
routing policy only through a reviewed edit. Replaying event records does not
reproduce nondeterministic model execution.
