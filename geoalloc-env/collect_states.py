import json
import random
import os
import sys

# Add current dir to path to ensure imports work
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from env.tasks.hard import make_hard_env
from env.tasks.medium import make_medium_env
from env.tasks.easy import make_easy_env
from env.models import Action


def collect_diverse_states(n_episodes=20, steps_per_env=15):
    """
    Rollout the environment with random actions to collect a diverse set of
    geopolitical states (low/high tension, different refinery buffers).
    Uses all three difficulty tiers for maximum diversity.
    """
    states = []
    env_factories = [make_easy_env, make_medium_env, make_hard_env]

    print(f"Starting state collection: {n_episodes} episodes across 3 tiers...")

    for i in range(n_episodes):
        # Cycle through difficulty tiers
        factory = env_factories[i % len(env_factories)]
        env = factory()
        obs = env.reset()
        states.append(obs.model_dump())

        for _ in range(steps_per_env):
            # 50% allocate, 50% no_op — only valid actions
            r = random.random()
            if r < 0.5 and env._state.available_oil > 0:
                country = random.choice(obs.countries)
                unmet = max(0, country.demand - country.received)
                max_alloc = min(unmet, env._state.available_oil)
                if max_alloc >= 1:
                    amount = random.randint(1, max_alloc)
                    action = Action(type="allocate", country_id=country.id, amount=amount)
                else:
                    action = Action(type="no_op")
            else:
                action = Action(type="no_op")

            result = env.step(action)
            obs = result.observation
            states.append(obs.model_dump())
            if result.done:
                break

    # Deduplicate states based on key metrics
    unique_states = {}
    for s in states:
        total_unmet = sum(c['unmet_demand'] for c in s['countries'])
        key = (round(s['global_tension'], 2), total_unmet, s['time_step'])
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
