"""Heuristic monthly-cost estimation for agents that don't declare a cost.

A small, explicit pricing table — not a live pricing API. Good enough to
give an Executive Report a plausible dollar figure for agents discovered
via upload/GitHub scan rather than leaving cost at $0. Keyed by substring
match against the declared model name so "gpt-4o-2024-08-06" still hits
the "gpt-4o" bucket.
"""

# (substring, monthly cost in cents) — checked in order, first match wins.
_MODEL_COST_CENTS: list[tuple[str, int]] = [
    ("gpt-4o-mini", 1500),
    ("gpt-4o", 8000),
    ("gpt-4-turbo", 12000),
    ("gpt-4", 12000),
    ("gpt-3.5", 2000),
    ("claude-3-opus", 15000),
    ("claude-3-5-sonnet", 9000),
    ("claude-3-sonnet", 9000),
    ("claude-3-haiku", 1800),
    ("gemini-1.5-pro", 8500),
    ("gemini-1.5-flash", 1500),
]

DEFAULT_COST_CENTS = 4000


def estimate_monthly_cost_cents(model: str | None) -> int:
    if not model:
        return DEFAULT_COST_CENTS
    needle = model.strip().lower()
    for substring, cost in _MODEL_COST_CENTS:
        if substring in needle:
            return cost
    return DEFAULT_COST_CENTS
