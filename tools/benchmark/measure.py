"""Shared numeric coercion for the benchmark tooling.

Measurement files are written incrementally and may carry a missing field, a
null or a malformed value. Callers want a usable number rather than an
exception, so every conversion goes through one of these helpers instead of
being repeated at each call site.
"""

from __future__ import annotations


def as_float(value) -> float:
    """Coerce a possibly-missing measurement to a float, defaulting to zero."""
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def as_int(value) -> int:
    """Coerce a possibly-missing count to an int, defaulting to zero."""
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0
