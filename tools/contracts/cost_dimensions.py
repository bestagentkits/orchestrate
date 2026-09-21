"""Reference implementation of the cost-dimension rules.

The normative rules live in
`plugins/orchestrate/skills/orchestrate/references/metrics-and-self-improvement.md`
under "Cost dimensions". This module exists so the rules can be exercised by a test.

The single most important property here is the one that is easiest to get wrong in a
hurry: **unknown is null, never zero.** A zero is a measurement; a null is the absence
of one. Treating the second as the first makes a missing measurement look like a free
route, which is a cost optimisation that silently buys the wrong answer.
"""

from __future__ import annotations

#: The three dimensions. They are not interchangeable and are never summed.
ACTUAL_MARGINAL = "actualMarginalCostUsd"
API_EQUIVALENT = "apiEquivalentCostUsd"
QUOTA_BURN = "quotaBurn"

COST_DIMENSIONS = (ACTUAL_MARGINAL, API_EQUIVALENT, QUOTA_BURN)


class CostError(ValueError):
    """Raised for a cost record or budget that violates the owned contract."""


def _known_number(value, name: str):
    """Validate one dimension value, returning ``None`` for an unmeasured dimension.

    One validator serves every entry point, so a caller cannot reach an arithmetic step
    with a value this module never checked, and a malformed value surfaces as this
    module's own error rather than a bare ``TypeError`` from deeper down.
    """
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise CostError(f"{name} must be a number or null, got {type(value).__name__}")
    if value < 0:
        raise CostError(f"{name} must not be negative")
    return value


def cost_record(**dimensions) -> dict:
    """Build a cost record, rejecting an unknown field and a non-null missing value.

    A dimension that was not measured must be omitted or passed as ``None``. Passing
    ``0`` asserts a measurement of zero, which is a different claim entirely.
    """
    unknown = set(dimensions) - set(COST_DIMENSIONS)
    if unknown:
        raise CostError(f"unknown cost dimension(s): {sorted(unknown)}")
    return {name: _known_number(dimensions.get(name), name) for name in COST_DIMENSIONS}


def total_cash(record: dict) -> int | float | None:
    """Sum only the dimensions that are cash, and only when they are known.

    Quota burn is deliberately excluded: it is an allowance consumed, not money, and
    adding it to dollars is the exact conflation the contract forbids. A null in any
    contributing dimension makes the total unknown rather than partially known.
    """
    actual = _known_number(record.get(ACTUAL_MARGINAL), ACTUAL_MARGINAL)
    api = _known_number(record.get(API_EQUIVALENT), API_EQUIVALENT)
    if actual is None or api is None:
        return None
    return actual + api


def assert_budget_declares_dimension(budget: dict) -> str:
    """Return the dimension a budget is denominated in, or refuse the budget.

    A budget is meaningless without its dimension: "budget: 20" cannot say whether it
    caps cash, price-equivalent usage, or a subscription allowance, and the three are
    not comparable.
    """
    dimension = budget.get("costDimension") if isinstance(budget, dict) else None
    if dimension is None:
        raise CostError("a budget must declare costDimension; an undeclared dimension is refused")
    if dimension not in COST_DIMENSIONS:
        raise CostError(f"unknown costDimension {dimension!r}; expected one of {list(COST_DIMENSIONS)}")
    limit = budget.get("limit")
    if limit is None:
        raise CostError("a budget must declare a limit")
    return dimension


def compare(left: dict, right: dict, dimension: str) -> int | None:
    """Compare two records on one dimension.

    Returns ``None`` rather than a verdict when either side is unknown, so an unknown
    can never win a comparison by default.
    """
    if dimension not in COST_DIMENSIONS:
        raise CostError(f"unknown cost dimension: {dimension!r}")
    a, b = left.get(dimension), right.get(dimension)
    if a is None or b is None:
        return None
    return (a > b) - (a < b)
