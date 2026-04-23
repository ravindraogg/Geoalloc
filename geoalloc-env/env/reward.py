from __future__ import annotations
from typing import List
from env.models import CountryState

# Reward weights
W1 = 0.5  # avg stability
W2 = 0.2  # global tension
W3 = 0.2  # unmet demand ratio
W4 = 0.1  # waste ratio

INVALID_ACTION_PENALTY = -0.1


def compute_reward(
    countries: List[CountryState],
    global_tension: float,
    waste: float,
    total_demand: int,
    action_valid: bool,
) -> tuple[float, float, float, float]:
    """
    Returns (reward, avg_stability, unmet_demand_ratio, waste_ratio).
    reward is clamped to [0, 1].
    """
    if total_demand == 0:
        unmet_demand_ratio = 0.0
        waste_ratio = 0.0
    else:
        total_unmet = sum(max(0, c.demand - c.received) for c in countries)
        unmet_demand_ratio = min(total_unmet / total_demand, 1.0)
        waste_ratio = min(waste / total_demand, 1.0)

    avg_stability = sum(c.stability for c in countries) / len(countries) if countries else 0.0

    raw = (
        W1 * avg_stability
        - W2 * global_tension
        - W3 * unmet_demand_ratio
        - W4 * waste_ratio
    )

    if not action_valid:
        raw += INVALID_ACTION_PENALTY

    # Normalize: theoretical min ≈ -(W2+W3+W4) = -0.5, max = W1 = 0.5
    # Map [-0.5, 0.5] → [0, 1]
    normalized = (raw + 0.5) / 1.0
    reward = max(0.0, min(1.0, normalized))

    return reward, avg_stability, unmet_demand_ratio, waste_ratio
