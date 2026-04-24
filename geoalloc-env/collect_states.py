import json
import random
import os
import sys

# Add current dir to path to ensure imports work
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from env.tasks.hard import make_hard_env
from env.models import Action

def collect_diverse_states(n_episodes=20, steps_per_env=15):
    """
    Rollout the environment with random actions to collect a diverse set of 
    geopolitical states (low/high tension, different unmet demands).
    """
    states = []
    
    print(f"Starting state collection: {n_episodes} episodes...")
    
    for i in range(n_episodes):
        env = make_hard_env()
        obs = env.reset()
        # Store as dict
        states.append(obs.model_dump())
        
        for _ in range(steps_per_env):
            # Biased random action: 40% allocate, 40% no_op, 20% probe
            r = random.random()
            if r < 0.4:
                country = random.choice(obs.countries if hasattr(obs, 'countries') else obs.observation.countries)
                # Random amount up to demand
                amount = random.randint(1, max(1, int(country.demand - country.received)))
                action = Action(type="allocate", country_id=country.id, amount=amount)
            elif r < 0.8:
                action = Action(type="no_op")
            else:
                country = random.choice(obs.countries if hasattr(obs, 'countries') else obs.observation.countries)
                action = Action(type="probe", country_id=country.id)
                
            result = env.step(action)
            obs = result.observation
            states.append(obs.model_dump())
            if result.done:
                break
                
    # Deduplicate states based on a few key metrics to keep variety
    unique_states = {}
    for s in states:
        total_unmet = sum(c['unmet_demand'] for c in s['countries'])
        key = (round(s['global_tension'], 2), total_unmet)
        if key not in unique_states:
            unique_states[key] = s
            
    final_states = list(unique_states.values())
    
    output_path = os.path.join(os.path.dirname(__file__), "training_observations.json")
    with open(output_path, "w") as f:
        json.dump(final_states, f, indent=2)
        
    print(f"Success! Collected {len(final_states)} diverse states.")
    print(f"Saved to: {output_path}")

if __name__ == "__main__":
    collect_diverse_states()
