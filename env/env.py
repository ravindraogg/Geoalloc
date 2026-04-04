from __future__ import annotations
import copy
from typing import Optional

from env.models import (
    Action,
    CountryObservation,
    CountryState,
    EnvState,
    Observation,
    StepInfo,
    StepResult,
)
from env.reward import compute_reward

# Transition constants
ALPHA = 0.3          # stability gain per allocation ratio unit
BETA = 0.15          # tension gain per allocation ratio unit (per enemy)
OVERFLOW_PENALTY = 0.5  # waste multiplier on overflow


class GeoAllocEnv:
    """
    OpenEnv-compliant deterministic resource allocation environment.
    """

    def __init__(self, initial_state: EnvState):
        self._initial_state: EnvState = initial_state.model_copy(deep=True)
        self._state: EnvState = initial_state.model_copy(deep=True)
        self._waste: float = 0.0
        self._total_demand: int = sum(c.demand for c in self._state.countries)

    # ------------------------------------------------------------------
    # OpenEnv interface
    # ------------------------------------------------------------------

    def reset(self) -> Observation:
        self._state = self._initial_state.model_copy(deep=True)
        self._waste = 0.0
        return self._make_observation()

    def state(self) -> dict:
        return self._state.model_dump()

    def step(self, action: Action) -> StepResult:
        obs, reward, done, info = self._step(action)
        return StepResult(observation=obs, reward=reward, done=done, info=info)

    # ------------------------------------------------------------------
    # Internal logic
    # ------------------------------------------------------------------

    def _step(self, action: Action):
        action_valid = True
        error: Optional[str] = None

        if action.type == "allocate":
            action_valid, error = self._validate_allocate(action)
            if action_valid:
                self._apply_allocate(action)

        # Advance time
        self._state.time_step += 1

        # Compute reward
        reward, avg_stability, unmet_demand_ratio, waste_ratio = compute_reward(
            countries=self._state.countries,
            global_tension=self._state.global_tension,
            waste=self._waste,
            total_demand=self._total_demand,
            action_valid=action_valid,
        )

        done = self._is_done()
        obs = self._make_observation()
        info = StepInfo(
            waste=self._waste,
            unmet_demand_ratio=unmet_demand_ratio,
            avg_stability=avg_stability,
            action_valid=action_valid,
            error=error,
        )
        return obs, reward, done, info

    def _validate_allocate(self, action: Action) -> tuple[bool, Optional[str]]:
        country = self._find_country(action.country_id)
        if country is None:
            return False, f"Unknown country_id: {action.country_id}"
        if action.amount > self._state.available_oil:
            return False, (
                f"Insufficient oil: requested {action.amount}, "
                f"available {self._state.available_oil}"
            )
        return True, None

    def _apply_allocate(self, action: Action) -> None:
        amount = action.amount
        self._state.available_oil -= amount

        country = self._find_country(action.country_id)
        country.received += amount

        demand = country.demand
        allocation_ratio = amount / demand if demand > 0 else 0.0

        # Update stability
        country.stability = min(1.0, country.stability + ALPHA * allocation_ratio)

        # Update global tension for each enemy
        enemies = country.enemies
        if enemies:
            self._state.global_tension = min(
                1.0,
                self._state.global_tension + BETA * allocation_ratio * len(enemies),
            )

        # Track waste (overflow)
        overflow = max(0, country.received - demand)
        self._waste += overflow * OVERFLOW_PENALTY

    def _is_done(self) -> bool:
        if self._state.time_step >= self._state.max_steps:
            return True
        if self._state.global_tension >= 1.0:
            return True
        all_satisfied = all(c.received >= c.demand for c in self._state.countries)
        if all_satisfied:
            return True
        return False

    def _find_country(self, country_id: str) -> Optional[CountryState]:
        for c in self._state.countries:
            if c.id == country_id:
                return c
        return None

    def _make_observation(self) -> Observation:
        country_obs = [
            CountryObservation(
                id=c.id,
                demand=c.demand,
                received=c.received,
                stability=c.stability,
                allies=list(c.allies),
                enemies=list(c.enemies),
                unmet_demand=max(0, c.demand - c.received),
            )
            for c in self._state.countries
        ]
        return Observation(
            available_oil=self._state.available_oil,
            countries=country_obs,
            global_tension=self._state.global_tension,
            time_step=self._state.time_step,
            max_steps=self._state.max_steps,
        )
