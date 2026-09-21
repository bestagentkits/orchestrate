"""Reference implementation of the route-identity rules.

The normative rules live in
`plugins/orchestrate/skills/orchestrate/references/benchmark-evidence.md`
under "The route identity". This module exists so those rules can be exercised by a
test instead of only asserted in prose, which is the difference between a rule and a
claim that a rule exists.

Two properties are load-bearing and both are tested:

- identity is decided by the real execution mode, so two labels reaching one mode are
  one candidate;
- identity is not decided by the normalized label, so one label reaching two modes is
  two candidates.
"""

from __future__ import annotations

EFFORT_LEVELS = ("minimal", "low", "medium", "high", "xhigh", "max")

IDENTITY_FIELDS = ("runtime", "provider", "model", "family", "effortMode")


def route_key(record: dict) -> tuple | None:
    """Return the execution identity of a record, or ``None`` when it is undecidable.

    ``None`` is deliberately not a shared value. An undecidable identity must never
    collapse two records into one candidate, so the caller keeps such a record
    separate; see :func:`collapse_aliases`.
    """
    if not record.get("effortMode"):
        return None
    values = [record.get(field) for field in IDENTITY_FIELDS]
    if any(value in (None, "") for value in values):
        return None
    return tuple(values)


def is_comparable(left: dict, right: dict) -> bool:
    """Whether two records may be ranked against each other.

    An unmapped effort ladder is not a comparable one, so such a record is comparable
    only with a record from the same provider. This mirrors the `effortClass: unmapped`
    rule; it is a comparison rule and never an eligibility rule.
    """
    unmapped = {record.get("effortClass") for record in (left, right)} == {"unmapped"}
    if unmapped and left.get("provider") != right.get("provider"):
        return False
    return True


def collapse_aliases(records: list[dict]) -> list[dict]:
    """Collapse records that share an execution identity into one candidate.

    The representative keeps the strongest available evidence, and every label or raw
    value that was folded into it is appended to ``effortAliases`` so the collapse is
    auditable. A record whose identity is undecidable is never merged.
    """
    collapsed: list[dict] = []
    index: dict[tuple, dict] = {}
    for record in records:
        key = route_key(record)
        if key is None:
            entry = dict(record)
            entry["effortAliases"] = _aliases(record)
            entry["identityUndecidable"] = True
            collapsed.append(entry)
            continue
        if key not in index:
            entry = dict(record)
            entry["effortAliases"] = _aliases(record)
            index[key] = entry
            collapsed.append(entry)
            continue
        existing = index[key]
        for alias in _aliases(record):
            if alias not in existing["effortAliases"]:
                existing["effortAliases"].append(alias)
        existing["sampleSize"] = (existing.get("sampleSize") or 0) + (record.get("sampleSize") or 0)
    return collapsed


def _aliases(record: dict) -> list[str]:
    """The labels and raw values that identify this record's real mode."""
    aliases = list(record.get("effortAliases") or [])
    for field in ("effortLevel", "effortRaw"):
        value = record.get(field)
        if value and value not in aliases:
            aliases.append(value)
    return aliases


def distinct_identity_count(records: list[dict]) -> int:
    """How many distinct candidates a set of records represents."""
    return len(collapse_aliases(records))
