from __future__ import annotations
from typing import List, Optional
from env.models import CountryState

# Reward constants
LAMBDA_TENSION = 0.7
DEMAND_MET_BONUS = 0.1
STRATEGIC_DELAY_BONUS = 0.05
SURVIVAL_BONUS = 0.3
INVALID_ACTION_PENALTY = -0.1


def compute_reward(
    countries: List[CountryState],
    global_tension: float,
    action_type: str = "allocate",
    tension_decreased: bool = False,
    action_valid: bool = True,
    is_done: bool = False,
    # Legacy params kept for backward compat but ignored
    waste: float = 0.0,
    total_demand: int = 0,
) -> tuple[float, float, float, float]:
    """
    Round 2 Consolidated Reward Function.

    R = avg_stability - λ × tension²
      + demand_met_bonus   (if all demand satisfied)
      + strategic_delay    (if no_op AND tension > 0.6 AND tension decreased)
      + survival_bonus     (if episode completed without tension blowout)
      - invalid_penalty    (if action was invalid)

    Returns (reward, avg_stability, unmet_demand_ratio, waste_ratio).
    """
    n = len(countries) if countries else 1
    avg_stability = sum(c.stability for c in countries) / n

    # Core: R = stability - λ * tension²
    reward = avg_stability - (LAMBDA_TENSION * (global_tension ** 2))

    # Demand satisfaction
    total_unmet = sum(max(0, c.demand - c.received) for c in countries)
    total_dem = sum(c.demand for c in countries) or 1
    unmet_ratio = min(total_unmet / total_dem, 1.0)

    if total_unmet == 0:
        reward += DEMAND_MET_BONUS

    # Strategic Delay Signal (the innovation)
    if (action_type == "no_op"
            and tension_decreased
            and total_unmet > 0
            and global_tension > 0.6):
        reward += STRATEGIC_DELAY_BONUS

    # Survival bonus
    if is_done and global_tension < 1.0:
        reward += SURVIVAL_BONUS

    # Invalid action penalty
    if not action_valid:
        reward += INVALID_ACTION_PENALTY

    reward = max(-1.0, min(2.0, reward))

    waste_ratio = min(waste / total_dem, 1.0) if total_dem > 0 else 0.0

    return reward, avg_stability, unmet_ratio, waste_ratio
