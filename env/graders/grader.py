from __future__ import annotations
from typing import List
from env.models import CountryState


def clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def grade(
    countries: List[CountryState],
    global_tension: float,
    total_demand: int,
) -> float:
    """
    Deterministic scoring function.

    score = clamp(
        0.5 * avg_stability
        - 0.3 * global_tension
        - 0.2 * unmet_demand_ratio,
        0, 1
    )

    Returns float in [0.0, 1.0].
    """
    avg_stability = sum(c.stability for c in countries) / len(countries) if countries else 0.0

    if total_demand > 0:
        total_unmet = sum(max(0, c.demand - c.received) for c in countries)
        unmet_demand_ratio = min(total_unmet / total_demand, 1.0)
    else:
        unmet_demand_ratio = 0.0

    raw_score = (
        0.5 * avg_stability
        - 0.3 * global_tension
        - 0.2 * unmet_demand_ratio
    )

    # Normalize: theoretical range is [-0.5, 0.5] → map to [0, 1]
    normalized = (raw_score + 0.5) / 1.0
    return clamp(normalized, 0.0, 1.0)
