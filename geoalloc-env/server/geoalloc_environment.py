"""
GeoAlloc Environment Implementation for OpenEnv server.
"""
from __future__ import annotations
from uuid import uuid4
import sys
import os

from openenv.core.env_server.interfaces import Environment
from openenv.core.env_server.types import State

# Ensure root is in PATH for Docker and local execution
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from env.models import GeoAllocAction, GeoAllocObservation, CountryState, EnvState, CountryObservation

# Transition constants
ALPHA = 0.3
BETA = 0.15
OVERFLOW_PENALTY = 0.5
W1, W2, W3, W4 = 0.5, 0.2, 0.2, 0.1
INVALID_ACTION_PENALTY = -0.1
TENSION_DECAY = 0.02
STRATEGIC_DELAY_BONUS = 0.05
LAMBDA_TENSION = 0.7
DEMAND_MET_BONUS = 0.1

def _compute_reward(countries, global_tension, action_type, tension_decreased, action_valid, is_done=False):
    avg_stability = sum(c.stability for c in countries) / len(countries) if countries else 0.0
    
    # Core Formula: Reward = Stability - lambda * Tension^2
    reward = avg_stability - (LAMBDA_TENSION * (global_tension ** 2))
    
    # Demand Met Bonus
    total_unmet = sum(max(0, c.demand - c.received) for c in countries)
    if total_unmet == 0:
        reward += DEMAND_MET_BONUS
    
    # Strategic Delay Signal (Innovation)
    if action_type == "no_op" and tension_decreased and total_unmet > 0 and global_tension > 0.6:
        reward += STRATEGIC_DELAY_BONUS
        
    # Survival Bonus (Round 2)
    if is_done and global_tension < 1.0:
        reward += 0.3
        
    if not action_valid:
        reward += INVALID_ACTION_PENALTY
        
    return max(-1.0, min(2.0, reward)), avg_stability, total_unmet

import json
import random

def _default_state() -> EnvState:
    try:
        with open(os.path.join(os.path.dirname(__file__), 'countries.json'), 'r') as f:
            country_coords = json.load(f)
    except Exception:
        country_coords = {"Ares": [0,0], "Zeus": [10,10]}

    countries = []
    all_names = list(country_coords.keys())
    
    # Initialize all countries with randomized demand and stability
    for name in all_names:
        # Mythological countries get special initial states if they exist in the names
        # Or we can just randomize everyone
        demand = random.randint(30, 90)
        stability = random.uniform(0.3, 0.7)
        
        # Simple relationship logic: pick 1-2 random enemies
        enemies = random.sample([n for n in all_names if n != name], k=random.randint(0, 2))
        
        countries.append(CountryState(
            id=name, 
            demand=demand, 
            received=0, 
            stability=stability, 
            allies=[], 
            enemies=enemies
        ))

    return EnvState(
        available_oil=5000, # Scaled for global demand
        global_tension=0.2, 
        time_step=0, 
        max_steps=50,
        countries=countries,
    )

class GeoAllocEnvironment(Environment):
    SUPPORTS_CONCURRENT_SESSIONS: bool = True

    def __init__(self):
        self._initial_state = _default_state()
        self.reset()

    def reset(self) -> GeoAllocObservation:
        self._env_state = self._initial_state.model_copy(deep=True)
        self._waste = 0.0
        self._total_demand = sum(c.demand for c in self._env_state.countries)
        self._state = State(episode_id=str(uuid4()), step_count=0)
        return self._make_observation(done=False, reward=0.0)

    def step(self, action: GeoAllocAction) -> GeoAllocObservation:
        prev_tension = self._env_state.global_tension
        action_valid = True
        reasoning = ""
        
        if action.type == "allocate":
            action_valid = self._validate_and_apply(action)
            if action_valid:
                reasoning = f"Strategic Deployment: Allocated {action.amount} units to {action.country_id} to reinforce regional stability."
            else:
                reasoning = f"Deployment Failure: Requested allocation for {action.country_id} exceeded available reserves or invalid sector."
        elif action.type == "no_op":
            # Tension Decay Logic (Round 2: only on no_op)
            self._env_state.global_tension = max(0.0, self._env_state.global_tension - TENSION_DECAY)
            reasoning = "Tactical Restraint: Initiating strategic delay to facilitate geopolitical tension decay."
        elif action.type == "probe":
            if self._env_state.available_oil >= 1 and action.country_id not in self._env_state.probed_countries:
                self._env_state.available_oil -= 1
                self._env_state.probed_countries.append(action.country_id)
                reasoning = f"Intelligence Gathering: Probed {action.country_id} to identify latent threat vectors."
            else:
                action_valid = False
                reasoning = f"Intelligence Failure: Insufficient resources or redundant probe for {action.country_id}."
        
        tension_decreased = self._env_state.global_tension < prev_tension
        
        self._env_state.time_step += 1
        self._state.step_count = self._env_state.time_step
        
        # Process Events Lifecycle
        for event in self._env_state.active_events:
            event.remaining_turns -= 1
        self._env_state.active_events = [e for e in self._env_state.active_events if e.remaining_turns > 0]

        done = self._is_done()
        reward, _, _ = _compute_reward(
            self._env_state.countries, 
            self._env_state.global_tension,
            action.type,
            tension_decreased,
            action_valid,
            is_done=done
        )
        
        return self._make_observation(done=done, reward=reward, reasoning=reasoning)

    @property
    def state(self) -> State: return self._state

    def _validate_and_apply(self, action: GeoAllocAction) -> bool:
        c = next((c for c in self._env_state.countries if c.id == action.country_id), None)
        if c is None or action.amount > self._env_state.available_oil: return False
        
        self._env_state.available_oil -= action.amount
        c.received += action.amount
        
        ratio = action.amount / c.demand if c.demand > 0 else 0.0
        c.stability = min(1.0, c.stability + ALPHA * ratio)
        
        # Calculate Tension Multiplier from Events
        multiplier = 1.0
        for event in self._env_state.active_events:
            if c.id in event.affected_countries:
                multiplier *= event.tension_multiplier

        if c.enemies:
            self._env_state.global_tension = min(1.0, self._env_state.global_tension + (BETA * multiplier) * ratio * len(c.enemies))
        
        self._waste += max(0, c.received - c.demand) * OVERFLOW_PENALTY
        return True

    def _is_done(self) -> bool:
        if self._env_state.time_step >= self._env_state.max_steps: return True
        if self._env_state.global_tension >= 1.0: return True
        return all(c.received >= c.demand for c in self._env_state.countries)

    def _init_params(self, params: dict): pass

    def _make_observation(self, done: bool, reward: float, reasoning: str = "") -> GeoAllocObservation:
        country_obs = [
            CountryObservation(
                id=c.id, demand=c.demand, received=c.received, stability=c.stability,
                allies=list(c.allies), 
                enemies=list(c.enemies) if c.id in self._env_state.probed_countries else [], 
                unmet_demand=max(0, c.demand - c.received),
            )
            for c in self._env_state.countries
        ]
        return GeoAllocObservation(
            available_oil=self._env_state.available_oil, countries=country_obs,
            global_tension=self._env_state.global_tension, time_step=self._env_state.time_step,
            max_steps=self._env_state.max_steps, done=done, reward=reward,
            reasoning=reasoning,
            active_events=list(self._env_state.active_events)
        )
