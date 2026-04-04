"""
GeoAlloc Environment Implementation for OpenEnv server.

Wraps the existing GeoAllocEnv as an OpenEnv-compatible Environment
with reset(), step(), and state property.
"""
from __future__ import annotations
from uuid import uuid4

from openenv.core.env_server.interfaces import Environment
from openenv.core.env_server.types import State

try:
    from models import GeoAllocAction, GeoAllocObservation, CountryState, EnvState, CountryObservation
except (ImportError, ModuleNotFoundError):
    try:
        from ..models import GeoAllocAction, GeoAllocObservation, CountryState, EnvState, CountryObservation
    except (ImportError, ModuleNotFoundError):
        import sys
        import os
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from models import GeoAllocAction, GeoAllocObservation, CountryState, EnvState, CountryObservation


# Transition constants
ALPHA = 0.3
BETA = 0.15
OVERFLOW_PENALTY = 0.5

# Reward weights
W1 = 0.5
W2 = 0.2
W3 = 0.2
W4 = 0.1
INVALID_ACTION_PENALTY = -0.1


def _compute_reward(countries, global_tension, waste, total_demand, action_valid):
    if total_demand == 0:
        unmet_demand_ratio = 0.0
        waste_ratio = 0.0
    else:
        total_unmet = sum(max(0, c.demand - c.received) for c in countries)
        unmet_demand_ratio = min(total_unmet / total_demand, 1.0)
        waste_ratio = min(waste / total_demand, 1.0)

    avg_stability = sum(c.stability for c in countries) / len(countries) if countries else 0.0

    raw = W1 * avg_stability - W2 * global_tension - W3 * unmet_demand_ratio - W4 * waste_ratio
    if not action_valid:
        raw += INVALID_ACTION_PENALTY

    normalized = (raw + 0.5) / 1.0
    return max(0.0, min(1.0, normalized)), avg_stability, unmet_demand_ratio, waste_ratio


# Default task: medium difficulty
def _default_state() -> EnvState:
    return EnvState(
        available_oil=130,
        global_tension=0.1,
        time_step=0,
        max_steps=12,
        countries=[
            CountryState(id="gamma", demand=60, received=0, stability=0.5, allies=[], enemies=["delta"]),
            CountryState(id="delta", demand=50, received=0, stability=0.5, allies=[], enemies=["gamma"]),
            CountryState(id="epsilon", demand=40, received=0, stability=0.7, allies=["gamma"], enemies=[]),
        ],
    )


class GeoAllocEnvironment(Environment):
    """
    OpenEnv-compatible GeoAlloc environment.

    Strategic resource allocation under geopolitical constraints.
    """

    SUPPORTS_CONCURRENT_SESSIONS: bool = True

    def __init__(self):
        self._initial_state = _default_state()
        self._env_state = self._initial_state.model_copy(deep=True)
        self._waste = 0.0
        self._total_demand = sum(c.demand for c in self._env_state.countries)
        self._state = State(episode_id=str(uuid4()), step_count=0)

    def reset(self) -> GeoAllocObservation:
        self._env_state = self._initial_state.model_copy(deep=True)
        self._waste = 0.0
        self._total_demand = sum(c.demand for c in self._env_state.countries)
        self._state = State(episode_id=str(uuid4()), step_count=0)
        return self._make_observation(done=False, reward=0.0)

    def step(self, action: GeoAllocAction) -> GeoAllocObservation:  # type: ignore[override]
        action_valid = True
        if action.type == "allocate":
            action_valid = self._validate_and_apply(action)

        self._env_state.time_step += 1
        self._state.step_count = self._env_state.time_step

        reward, _, _, _ = _compute_reward(
            self._env_state.countries, self._env_state.global_tension,
            self._waste, self._total_demand, action_valid,
        )

        done = self._is_done()
        return self._make_observation(done=done, reward=reward)

    @property
    def state(self) -> State:
        return self._state

    def _validate_and_apply(self, action: GeoAllocAction) -> bool:
        country = next((c for c in self._env_state.countries if c.id == action.country_id), None)
        if country is None:
            return False
        if action.amount > self._env_state.available_oil:
            return False

        self._env_state.available_oil -= action.amount
        country.received += action.amount

        allocation_ratio = action.amount / country.demand if country.demand > 0 else 0.0
        country.stability = min(1.0, country.stability + ALPHA * allocation_ratio)

        if country.enemies:
            self._env_state.global_tension = min(
                1.0, self._env_state.global_tension + BETA * allocation_ratio * len(country.enemies)
            )

        overflow = max(0, country.received - country.demand)
        self._waste += overflow * OVERFLOW_PENALTY
        return True

    def _is_done(self) -> bool:
        if self._env_state.time_step >= self._env_state.max_steps:
            return True
        if self._env_state.global_tension >= 1.0:
            return True
        if all(c.received >= c.demand for c in self._env_state.countries):
            return True
        return False

    def _make_observation(self, done: bool, reward: float) -> GeoAllocObservation:
        country_obs = [
            CountryObservation(
                id=c.id, demand=c.demand, received=c.received,
                stability=c.stability, allies=list(c.allies),
                enemies=list(c.enemies), unmet_demand=max(0, c.demand - c.received),
            )
            for c in self._env_state.countries
        ]
        return GeoAllocObservation(
            available_oil=self._env_state.available_oil,
            countries=country_obs,
            global_tension=self._env_state.global_tension,
            time_step=self._env_state.time_step,
            max_steps=self._env_state.max_steps,
            done=done,
            reward=reward,
        )
