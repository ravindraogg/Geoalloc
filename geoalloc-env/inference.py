"""
inference.py — GeoAllocEnv inference runner.
Follows the OpenEnv strict boilerplate format.
"""
import os
import json
import textwrap
from typing import List, Optional
from openai import OpenAI

# ── project imports ────────────────────────────────────────────────────────────
from env.env import GeoAllocEnv
from env.models import Action
from env.graders.grader import grade
from env.tasks.easy import make_easy_env
from env.tasks.medium import make_medium_env
from env.tasks.hard import make_hard_env

# ── env vars ───────────────────────────────────────────────────────────────────
IMAGE_NAME = os.getenv("IMAGE_NAME") or os.getenv("LOCAL_IMAGE_NAME")
API_KEY = os.getenv("HF_TOKEN") or os.getenv("API_KEY")
API_BASE_URL = os.getenv("API_BASE_URL") or "https://api.openai.com/v1"
MODEL_NAME = os.getenv("MODEL_NAME") or "LOCAL_STRATEGIC"
WEIGHTS_PATH = os.path.join("geoalloc_agent_grpo", "policy_weights.json")

# ── setup ──────────────────────────────────────────────────────────────────────
client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY if API_KEY else "no-key")

TASKS = [
    ("easy", make_easy_env),
    ("medium", make_medium_env),
    ("hard", make_hard_env),
]

SYSTEM_PROMPT = textwrap.dedent("""
    You are an AI agent controlling oil allocation in a geopolitical simulation.
    Each turn you receive an observation JSON and must return a single JSON action.
    Action formats (return ONLY valid JSON):
      {"type": "allocate", "country_id": "<id>", "amount": <integer>}
      {"type": "no_op"}
    
    STRATEGY:
    1. Meet demand for countries with 0 enemies first.
    2. Monitor global_tension; do not let it reach 1.0.
    3. Use small amounts for countries with many enemies.
""").strip()

def log_start(task: str, env: str, model: str) -> None:
    print(f"[START] task={task} env={env} model={model}", flush=True)

def log_step(step: int, action: str, reward: float, done: bool, error: Optional[str]) -> None:
    error_val = error if error else "null"
    done_val = str(done).lower()
    print(f"[STEP] step={step} action={action} reward={reward:.2f} done={done_val} error={error_val}", flush=True)

def log_end(success: bool, steps: int, score: float, rewards: List[float]) -> None:
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    print(f"[END] success={str(success).lower()} steps={steps} score={score:.3f} rewards={rewards_str}", flush=True)

def ask_local_strategic(observation_dict: dict) -> dict:
    """Uses the trained strategic heuristic weights."""
    try:
        with open(WEIGHTS_PATH, "r") as f:
            weights = json.load(f)
    except:
        weights = {"tension_threshold": 0.4, "stability_target": 0.6, "amount_fraction": 0.5}

    tension = observation_dict.get("global_tension", 0.0)
    oil = observation_dict.get("available_oil", 0)
    countries = observation_dict.get("countries", [])

    # STRATEGIC DELAY: Hold if tension is above threshold
    if tension > weights["tension_threshold"]:
        return {"type": "no_op"}

    if oil <= 0:
        return {"type": "no_op"}

    # Target the least stable country that hasn't met target
    candidates = [c for c in countries if c["stability"] < weights["stability_target"]]
    if not candidates:
        return {"type": "no_op"}

    # Sort by refinery capacity (strategic preference)
    candidates.sort(key=lambda x: (-x.get("refinery_capacity", 0.5), x["stability"]))
    target = candidates[0]
    
    amount = min(int(oil * weights["amount_fraction"]), oil)
    if amount < 1:
        return {"type": "no_op"}

    return {"type": "allocate", "country_id": target["id"], "amount": amount}

def ask_model(observation_dict: dict) -> dict:
    if MODEL_NAME == "LOCAL_STRATEGIC":
        return ask_local_strategic(observation_dict)
    
    user_msg = json.dumps(observation_dict, indent=2)
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ],
        temperature=0.0,
        max_tokens=256,
    )
    content = response.choices[0].message.content or "{}"
    raw = content.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"): raw = raw[4:]
    return json.loads(raw.strip())

def run_task(task_name: str, env_factory) -> None:
    env: GeoAllocEnv = env_factory()
    log_start(task=task_name, env="geoalloc", model=MODEL_NAME)
    
    rewards: List[float] = []
    steps_taken = 0
    score = 0.0
    success = False
    
    try:
        obs = env.reset()
        done = False
        
        while not done:
            steps_taken += 1
            obs_dict = obs.model_dump()
            error_msg = None
            action_str = "no_op"
            
            try:
                raw_action = ask_model(obs_dict)
                action = Action(**raw_action)
                action_str = f"allocate({action.country_id},{action.amount})" if action.type == "allocate" else "no_op"
            except Exception as e:
                action = Action(type="no_op")
                error_msg = str(e).replace("\n", " ")[:100]
            
            result = env.step(action)
            obs, reward, done = result.observation, result.reward, result.done
            
            if result.info.error and not error_msg:
                error_msg = result.info.error
            
            rewards.append(reward)
            log_step(step=steps_taken, action=action_str, reward=reward, done=done, error=error_msg)
            
            if steps_taken >= 20: # Safety cap
                done = True

        # Final grading logic
        state_raw = env.state()
        countries_obj = env._state.countries
        total_demand = sum(c.demand for c in countries_obj)
        score = grade(countries_obj, state_raw["global_tension"], total_demand)
        score = min(max(score, 0.0), 1.0)
        success = score >= 0.5

    finally:
        log_end(success=success, steps=steps_taken, score=score, rewards=rewards)

def main():
    for task_name, factory in TASKS:
        run_task(task_name, factory)

if __name__ == "__main__":
    main()
