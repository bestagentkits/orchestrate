"""The twenty benchmark tasks.

Each entry names the grader that scores it, the task class it belongs to and
the prompt handed to the agent. Prompts describe an observable requirement or
symptom the way an issue report would; none of them names the hidden grader, and
none of them is written differently for the two variants, so the only variable
between the baseline and the candidate is how the work is organised.
"""

from __future__ import annotations

TASKS: list[dict] = [
    {
        "id": "due-datetime",
        "cohort": "datetime",
        "type": "bugfix",
        "grader": "TestDueParsing",
        "prompt": (
            "The JSON store in this project records due dates as ISO-8601 strings. When we "
            "compare tasks that came from different sources, two records describing the same "
            "instant come back unequal, because the UTC offset is thrown away; and a due date "
            "saved without an offset is treated as if it were local time.\n\n"
            "Make due-date parsing return a timezone-aware datetime in UTC. Two timestamps that "
            "denote the same instant must compare equal even when they were written with "
            "different offsets, and a timestamp written with no offset must be read as UTC."
        ),
    },
    {
        "id": "crash-safe-save",
        "cohort": "io",
        "type": "bugfix",
        "grader": "TestCrashSafeSave",
        "prompt": (
            "We have seen a corrupted store after a crash. The JSON document that holds the "
            "tasks is written in place, so a process that dies partway through serialization "
            "leaves a half-written file and the whole backlog is lost.\n\n"
            "Make saving crash-safe: either the new document is fully visible, or the previous "
            "document is still intact. A failed serialization must not damage the store that was "
            "already there."
        ),
    },
    {
        "id": "load-unwritten-path",
        "cohort": "io",
        "type": "bugfix",
        "grader": "TestLoadUnwrittenPath",
        "prompt": (
            "On a fresh project there is no store file yet, and the first read of an unwritten "
            "path fails instead of reporting an empty backlog.\n\n"
            "Reading a store path that has never been written must return no tasks rather than "
            "raising."
        ),
    },
    {
        "id": "pagination-bounds",
        "cohort": "boundary",
        "type": "bugfix",
        "grader": "TestPagination",
        "prompt": (
            "Paging is off by one: asking for the first page returns the tasks that belong to the "
            "second page.\n\n"
            "Pages are meant to be 1-based. A page past the end should come back empty, and a page "
            "number below 1 should behave like the first page."
        ),
    },
    {
        "id": "sort-due-order",
        "cohort": "boundary",
        "type": "bugfix",
        "grader": "TestSortByDue",
        "prompt": (
            "Sorting the backlog by due date crashes as soon as any task has no due date.\n\n"
            "Tasks that have a due date must come first, in due order. Tasks without a due date "
            "must form the tail, ordered by title among themselves. Sorting must not reorder the "
            "caller's list in place."
        ),
    },
    {
        "id": "tag-filter-union",
        "cohort": "semantics",
        "type": "bugfix",
        "grader": "TestTagFilter",
        "prompt": (
            "The tag filter is unusable for the dashboard: selecting two tags shows only the tasks "
            "that carry both, but we need the union.\n\n"
            "A task must be kept when it carries any one of the requested tags."
        ),
    },
    {
        "id": "duplicate-scan-cost",
        "cohort": "performance",
        "type": "performance",
        "grader": "TestDuplicateScanCost",
        "prompt": (
            "Importing a large backlog takes tens of seconds, because the duplicate-title check "
            "compares every task with every other task. It also reports only one id per collision, "
            "while we need every id involved.\n\n"
            "Make the scan handle a few thousand tasks in well under two seconds, and report every "
            "id whose normalized title collides, including the first one seen for that title."
        ),
    },
    {
        "id": "email-validation",
        "cohort": "validation",
        "type": "bugfix",
        "grader": "TestEmailValidation",
        "prompt": (
            "Email validation is far too permissive: it accepts almost anything containing an "
            "at-sign, and bad addresses reach the invite queue.\n\n"
            "Accept a value only when it has exactly one \"@\", a non-empty local part, and a "
            "domain containing a dot that is neither the first nor the last character of the "
            "domain. Reject anything containing whitespace."
        ),
    },
    {
        "id": "duration-parsing",
        "cohort": "parsing",
        "type": "feature",
        "grader": "TestDurationParsing",
        "prompt": (
            "Users write effort estimates as \"90m\", \"1h30m\" or \"1h 30m\", and the parser "
            "rejects everything except a single unit.\n\n"
            "Support a bare number as minutes, and the h and m units combined, optionally "
            "separated by whitespace. Reject text that is not a duration."
        ),
    },
    {
        "id": "slugify-transliteration",
        "cohort": "unicode",
        "type": "feature",
        "grader": "TestSlugify",
        "prompt": (
            "Slugs for non-English titles lose letters: \"Cafe\u0301 Cre\u0300me\" comes out as "
            "\"caf-cr\", because accented letters are dropped instead of being converted to their "
            "base letter.\n\n"
            "Accented Latin letters must transliterate to their base letter, so the slug is "
            "\"cafe-creme\". Runs of other characters collapse to a single hyphen, with no leading "
            "or trailing hyphen."
        ),
    },
    {
        "id": "truncate-limit",
        "cohort": "unicode",
        "type": "bugfix",
        "grader": "TestTruncate",
        "prompt": (
            "Truncated titles come back one character longer than the limit, because the ellipsis "
            "is added on top of the limit instead of inside it.\n\n"
            "The returned string must never exceed the limit, and must end with a single ellipsis "
            "character when shortening happened. A non-positive limit yields the empty string."
        ),
    },
    {
        "id": "tag-summary-dedupe",
        "cohort": "aggregation",
        "type": "bugfix",
        "grader": "TestTagSummary",
        "prompt": (
            "The per-tag summary over-counts: a task whose tag list repeats the same tag is "
            "counted twice for that tag.\n\n"
            "Each task must contribute exactly once to every distinct tag it carries, and the "
            "effort estimates must still be summed per tag."
        ),
    },
    {
        "id": "percentile-interpolation",
        "cohort": "statistics",
        "type": "feature",
        "grader": "TestPercentile",
        "prompt": (
            "The percentile helper returns one of the samples instead of interpolating, so the "
            "median of an even-sized list is wrong.\n\n"
            "Percentiles must interpolate between neighbouring samples, so the median of "
            "[1, 2, 3, 4] is 2.5. An empty input is an error."
        ),
    },
    {
        "id": "money-rounding",
        "cohort": "numerics",
        "type": "bugfix",
        "grader": "TestRounding",
        "prompt": (
            "Money amounts are rounded with binary floating point, so halfway values round the "
            "wrong way: 2.675 becomes 2.67 instead of 2.68.\n\n"
            "Round to two decimal places, halfway away from zero, based on the decimal value the "
            "caller wrote rather than the binary float that approximates it, and return a Decimal."
        ),
    },
    {
        "id": "retry-backoff",
        "cohort": "reliability",
        "type": "feature",
        "grader": "TestRetryWithBackoff",
        "prompt": (
            "The retry helper does not retry: a single failure is surfaced immediately, even "
            "though a bounded retry policy was requested.\n\n"
            "Attempt the call at most the requested number of times, waiting the base delay "
            "doubled for each elapsed attempt, and raise the last error once the attempts are "
            "exhausted."
        ),
    },
    {
        "id": "ttl-expiry",
        "cohort": "caching",
        "type": "bugfix",
        "grader": "TestTtlCache",
        "prompt": (
            "Cached entries never expire, so stale data is served forever.\n\n"
            "An entry must stop being visible once its TTL has elapsed, measured with the "
            "injected clock, and reading an unknown key must return the caller's default."
        ),
    },
    {
        "id": "token-bucket-refill",
        "cohort": "ratelimiting",
        "type": "bugfix",
        "grader": "TestTokenBucket",
        "prompt": (
            "The rate limiter never refills: once its initial tokens are spent it refuses "
            "everything, so long-running workers stall.\n\n"
            "Tokens must refill continuously at the configured rate from the time that has "
            "passed, capped at the bucket's capacity."
        ),
    },
    {
        "id": "csv-rfc4180",
        "cohort": "format",
        "type": "feature",
        "grader": "TestCsvExport",
        "prompt": (
            "The CSV export breaks as soon as a field contains a comma, a quote or a newline, and "
            "it does not produce the records the spec requires.\n\n"
            "Emit RFC 4180: a header row; fields quoted with double quotes when they contain a "
            "comma, a double quote, a carriage return or a line feed; embedded double quotes "
            "doubled; and records separated by CRLF."
        ),
    },
    {
        "id": "csv-formula-injection",
        "cohort": "security",
        "type": "security",
        "grader": "TestFormulaSanitizing",
        "prompt": (
            "A security review found formula injection in exported data: a task title beginning "
            "with \"=\" is executed as a formula when the export is opened in a spreadsheet.\n\n"
            "A value whose first character is \"=\", \"+\", \"-\" or \"@\" must be prefixed with a "
            "single apostrophe so a spreadsheet stores it as text. Values beginning with a tab or "
            "carriage return are treated the same way. Every other value is returned unchanged."
        ),
    },
    {
        "id": "cli-stats-command",
        "cohort": "cli",
        "type": "feature",
        "grader": "TestStatsCommand",
        "prompt": (
            "The CLI has no way to report backlog health, and the release notes already promise a "
            "`stats` command.\n\n"
            "Add a `stats` subcommand that takes a store path and prints a JSON object carrying "
            "the number of tasks, the number done and the number still open, then exits "
            "successfully."
        ),
    },
]

GRADER_MODULE = "taskflow_bench_tests.test_taskflow"
