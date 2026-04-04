"""
inference.py — GeoAllocEnv inference runner.

Strict stdout format:
  [START] task=<task_name> env=geoalloc model=<model_name>
  [STEP]  step=<n> action=<action_str> reward=<0.00> done=<true|false> error=<msg|null>
  [END]   success=<true|false> steps=<n> rewards=<r1,r2,...>
"""
from __future__ import annotations

import json
import os
import sys

from openai import OpenAI

# ── project imports ────────────────────────────────────────────────────────────
from env.env import GeoAllocEnv
from env.models import Action
from env.graders.grader import grade
from env.tasks.easy import make_easy_env
from env.tasks.medium import make_medium_env
from env.tasks.hard import make_hard_env

# ── env vars ───────────────────────────────────────────────────────────────────
API_BASE_URL: str = os.environ.get("API_BASE_URL", "https://api.openai.com/v1")
MODEL_NAME: str = os.environ.get("MODEL_NAME", "gpt-4o-mini")
HF_TOKEN: str = os.environ.get("HF_TOKEN", "")

# ── OpenAI client ──────────────────────────────────────────────────────────────
_api_key = HF_TOKEN if HF_TOKEN else os.environ.get("OPENAI_API_KEY", "no-key")
client = OpenAI(base_url=API_BASE_URL, api_key=_api_key)

# ── tasks registry ─────────────────────────────────────────────────────────────
TASKS: list[tuple[str, GeoAllocEnv]] = [
    ("easy", make_easy_env()),
    ("medium", make_medium_env()),
    ("hard", make_hard_env()),
]

SYSTEM_PROMPT = """You are an AI agent controlling oil allocation in a geopolitical simulation.

Each turn you receive an observation JSON and must return a single JSON action.

Action formats (return ONLY valid JSON, no markdown, no explanation):
  {"type": "allocate", "country_id": "<id>", "amount": <integer>}
  {"type": "no_op"}

CRITICAL RULES:
1. global_tension increases by 0.15 * (amount/demand) * number_of_enemies when you allocate to a country.
   If global_tension reaches 1.0, the episode ENDS immediately.
2. Countries with MORE enemies cause MORE tension. Allocate to them LAST and in SMALL amounts.
3. Countries with ZERO enemies are SAFE — allocate to them first.
4. Never allocate more than available_oil.
5. Never allocate more than a country's unmet_demand (demand - received).
6. Allocate enough to each country to meet demand — unmet demand lowers your score.

STRATEGY (follow this order):
1. First, allocate to countries with 0 enemies (safe, no tension increase).
2. Then, allocate small amounts to countries with 1 enemy.
3. Only allocate to countries with 2+ enemies if oil remains AND tension is low (< 0.5).
4. If global_tension > 0.7, use no_op to avoid ending the episode.
5. Split large allocations across multiple steps to control tension.
"""


def ask_model(observation_dict: dict) -> dict:
    """Call the LLM and parse the action JSON it returns."""
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
    content = response.choices[0].message.content
    if content is None:
        raise ValueError("Model returned empty/null content")
    raw = content.strip()
    # Strip markdown fences if present
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw.strip())


def run_task(task_name: str, env: GeoAllocEnv) -> None:
    obs = env.reset()
    print(f"[START] task={task_name} env=geoalloc model={MODEL_NAME}", flush=True)

    rewards: list[float] = []
    step = 0
    done = False

    while not done:
        obs_dict = obs.model_dump()
        error_msg = "null"
        action_str = "no_op"

        try:
            raw_action = ask_model(obs_dict)
            action = Action(**raw_action)
            action_str = (
                f"allocate({action.country_id},{action.amount})"
                if action.type == "allocate"
                else "no_op"
            )
        except Exception as exc:
            action = Action(type="no_op")
            action_str = "no_op"
            error_msg = str(exc).replace("\n", " ")[:120]

        result = env.step(action)
        obs = result.observation
        reward = result.reward
        done = result.done

        if result.info.error and error_msg == "null":
            error_msg = result.info.error

        rewards.append(reward)
        step += 1

        done_str = "true" if done else "false"
        print(
            f"[STEP] step={step} action={action_str} "
            f"reward={reward:.2f} done={done_str} error={error_msg}",
            flush=True,
        )

    # Final grading
    state_raw = env.state()
    countries_obj = env._state.countries
    total_demand = sum(c.demand for c in countries_obj)
    final_score = grade(
        countries=countries_obj,
        global_tension=state_raw["global_tension"],
        total_demand=total_demand,
    )
    success = final_score >= 0.5
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    print(
        f"[END] success={'true' if success else 'false'} "
        f"steps={step} rewards={rewards_str}",
        flush=True,
    )


def main() -> None:
    for task_name, env in TASKS:
        run_task(task_name, env)


if __name__ == "__main__":
    main()
