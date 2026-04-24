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
ALPHA = 0.3          # immediate stability gain factor
REFINERY_BETA = 0.5  # delayed stability gain factor (more efficient)
TENSION_BETA = 0.15  # tension gain factor per allocation
OVERFLOW_PENALTY = 0.5
TENSION_DECAY = 0.02 # decay per step


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
        prev_tension = self._state.global_tension

        # 1. Process Delayed Refining Effects (from previous step)
        for country in self._state.countries:
            if country.refined_buffer > 0:
                refined_gain = REFINERY_BETA * (country.refined_buffer / country.demand if country.demand > 0 else 0)
                country.stability = min(1.0, country.stability + refined_gain)
                country.refined_buffer = 0.0 # Clear buffer

        # 2. Process Current Action
        if action.type == "allocate":
            action_valid, error = self._validate_allocate(action)
            if action_valid:
                self._apply_allocate(action)

        # 3. Global Tension Decay
        self._state.global_tension = max(0.0, self._state.global_tension - TENSION_DECAY)

        # 4. Advance time
        self._state.time_step += 1

        tension_decreased = self._state.global_tension < prev_tension
        done = self._is_done()

        # Compute reward
        reward, avg_stability, unmet_demand_ratio, waste_ratio = compute_reward(
            countries=self._state.countries,
            global_tension=self._state.global_tension,
            action_type=action.type,
            tension_decreased=tension_decreased,
            action_valid=action_valid,
            is_done=done,
            waste=self._waste,
            total_demand=self._total_demand,
        )

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
        
        demand = country.demand
        capacity = country.refinery_capacity
        
        # Split allocation
        direct_use = amount * (1 - capacity)
        refined_use = amount * capacity

        # 1. Immediate Effect (Direct Consumption)
        direct_ratio = direct_use / demand if demand > 0 else 0.0
        country.stability = min(1.0, country.stability + ALPHA * direct_ratio)
        country.received += direct_use # Count direct use as received now

        # 2. Delayed Effect (Buffered)
        country.refined_buffer += refined_use

        # 3. Update global tension for each enemy (based on total allocated)
        total_ratio = amount / demand if demand > 0 else 0.0
        enemies = country.enemies
        if enemies:
            self._state.global_tension = min(
                1.0,
                self._state.global_tension + TENSION_BETA * total_ratio * len(enemies),
            )

        # Track waste (overflow)
        overflow = max(0, (country.received + country.refined_buffer) - demand)
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
                received=int(c.received),
                stability=c.stability,
                allies=list(c.allies),
                enemies=list(c.enemies),
                unmet_demand=int(max(0, c.demand - c.received)),
                refinery_capacity=c.refinery_capacity,
                refined_buffer=c.refined_buffer
            )
            for c in self._state.countries
        ]
        return Observation(
            available_oil=int(self._state.available_oil),
            countries=country_obs,
            global_tension=self._state.global_tension,
            time_step=self._state.time_step,
            max_steps=self._state.max_steps,
        )

    def predict_outcome(self, action: Action) -> dict:
        """
        Simulate the outcome of an action without mutating the state.
        """
        temp_env = copy.deepcopy(self)
        current_stability = sum(c.stability for c in self._state.countries) / len(self._state.countries)
        current_tension = self._state.global_tension
        
        temp_env.step(action)
        
        new_stability = sum(c.stability for c in temp_env._state.countries) / len(temp_env._state.countries)
        new_tension = temp_env._state.global_tension
        
        return {
            "stability_delta": new_stability - current_stability,
            "tension_delta": new_tension - current_tension
        }
