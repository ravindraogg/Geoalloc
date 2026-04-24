"""
GeoAlloc Environment Implementation for OpenEnv server.
Optimized for Round 2: Refineries & Strategic Foresight.
"""
from __future__ import annotations
from uuid import uuid4
import sys
import os
import random
import json

from openenv.core.env_server.interfaces import Environment
from openenv.core.env_server.types import State

# Ensure root is in PATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from env.models import Action, Observation, CountryState, EnvState
from env.env import GeoAllocEnv

def _default_state() -> EnvState:
    try:
        with open(os.path.join(os.path.dirname(__file__), 'countries.json'), 'r') as f:
            country_coords = json.load(f)
    except Exception:
        country_coords = {"ares": [38,23], "zeus": [40,22], "hera": [36,24], "poseidon": [30,-30], "athena": [38,20]}

    countries = []
    all_names = list(country_coords.keys())
    
    for name in all_names:
        demand = random.randint(40, 80)
        stability = random.uniform(0.3, 0.6)
        # Randomize refinery capacity for strategic diversity
        refinery_capacity = random.uniform(0.3, 0.8)
        enemies = random.sample([n for n in all_names if n != name], k=random.randint(0, 2))
        
        countries.append(CountryState(
            id=name, 
            demand=demand, 
            received=0, 
            stability=stability, 
            allies=[], 
            enemies=enemies,
            refinery_capacity=refinery_capacity,
            refined_buffer=0.0
        ))

    return EnvState(
        available_oil=2000, 
        global_tension=0.2, 
        time_step=0, 
        max_steps=30,
        countries=countries,
    )

class GeoAllocEnvironment(Environment):
    SUPPORTS_CONCURRENT_SESSIONS: bool = True

    def __init__(self):
        self._inner_env = GeoAllocEnv(_default_state())
        self._state = State(episode_id=str(uuid4()), step_count=0)

    def reset(self) -> Observation:
        self._inner_env.reset()
        self._state = State(episode_id=str(uuid4()), step_count=0)
        return self._make_projections(self._inner_env.step(Action(type="no_op", amount=0)).observation)

    def step(self, action: Action) -> Observation:
        res = self._inner_env.step(action)
        self._state.step_count = self._inner_env._state.time_step
        
        # Add reasoning based on action
        reasoning = ""
        if action.type == "no_op":
            reasoning = "Tactical Restraint: Facilitating tension decay and refinery throughput."
        else:
            reasoning = f"Strategic Allocation: {action.amount}u to {action.country_id} (Split for refining)."

        obs = res.observation
        obs.done = res.done
        obs.reward = res.reward
        obs.reasoning = reasoning
        
        return self._make_projections(obs)

    def _make_projections(self, obs: Observation) -> Observation:
        """
        Calculates projected outcomes for the Decision Mode.
        """
        # 1. No-Op Projection
        no_op_proj = self._inner_env.predict_outcome(Action(type="no_op"))
        
        # 2. Allocation Projection (Assume 50 units to first country for sample)
        sample_id = obs.countries[0].id
        alloc_proj = self._inner_env.predict_outcome(Action(type="allocate", country_id=sample_id, amount=50))
        
        obs.projection = {
            "no_op": no_op_proj,
            "allocate": alloc_proj
        }
        return obs

    @property
    def state(self) -> State: return self._state

    def _init_params(self, params: dict): pass
