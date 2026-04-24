"""
GeoAlloc Strategic Training Script - Final Kaggle Edition
Optimized for Tesla T4 / P100 with GRPO and Refinery Engine.
"""

import os
import sys
import json
import copy
import torch
import random
from typing import List, Optional, Literal
from pydantic import BaseModel, Field, model_validator

# 1. Dependency Management
def install_deps():
    try:
        import unsloth
        import trl
    except ImportError:
        print("Installing Unsloth and RL dependencies for Kaggle...")
        os.system("pip install --no-deps unsloth \"triton<3\" \"trl<0.9.0\" peft accelerate bitsandbytes")

if __name__ == "__main__":
    if "kaggle" in os.getcwd() or os.path.exists("/kaggle"):
        import socket
        try:
            socket.create_connection(("huggingface.co", 80), timeout=5)
            print("Internet Connection: OK")
        except OSError:
            print("CRITICAL: No Internet detected. Enable 'Internet' in Kaggle sidebar.")
            sys.exit(1)
        install_deps()

try:
    from unsloth import FastLanguageModel, PatchFastRL
    from trl import GRPOTrainer, GRPOConfig
    from datasets import Dataset
    IMPORTS_OK = True
except ImportError:
    IMPORTS_OK = False

if IMPORTS_OK:
    PatchFastRL("GRPO", FastLanguageModel)
else:
    print("ACTION REQUIRED: Click 'Run' -> 'Restart Session' in the Kaggle menu.")
    sys.exit(0)

# --- [CORE] ENVIRONMENT MODELS ---

class CountryState(BaseModel):
    id: str
    demand: int
    received: int = 0
    stability: float = Field(ge=0.0, le=1.0)
    allies: List[str] = Field(default_factory=list)
    enemies: List[str] = Field(default_factory=list)
    refinery_capacity: float = 0.5
    refined_buffer: float = 0.0

class EnvState(BaseModel):
    available_oil: int
    countries: List[CountryState]
    global_tension: float = Field(ge=0.0, le=1.0)
    time_step: int = 0
    max_steps: int = 15

class Action(BaseModel):
    type: Literal["allocate", "no_op"]
    country_id: Optional[str] = None
    amount: Optional[int] = None

    @model_validator(mode="after")
    def validate_action(self) -> "Action":
        if self.type == "allocate":
            if self.country_id is None or self.amount is None:
                raise ValueError("allocate requires country_id and amount")
        return self

# --- [CORE] SIMULATOR ENGINE ---

class GeoAllocEnv:
    def __init__(self, initial_state: EnvState):
        self._state = initial_state.model_copy(deep=True)

    def step(self, action: Action):
        prev_tension = self._state.global_tension
        valid = True
        
        # 1. Delayed Refining
        for c in self._state.countries:
            if c.refined_buffer > 0:
                c.stability = min(1.0, c.stability + 0.5 * (c.refined_buffer / c.demand if c.demand > 0 else 0))
                c.refined_buffer = 0.0
        
        # 2. Action Processing
        if action.type == "allocate":
            c = next((x for x in self._state.countries if x.id == action.country_id), None)
            if not c or action.amount > self._state.available_oil:
                valid = False
            else:
                self._state.available_oil -= action.amount
                direct = action.amount * (1 - c.refinery_capacity)
                c.stability = min(1.0, c.stability + 0.3 * (direct / c.demand if c.demand > 0 else 0))
                c.received += direct
                c.refined_buffer += action.amount * c.refinery_capacity
                if c.enemies:
                    self._state.global_tension = min(1.0, self._state.global_tension + 0.15 * (action.amount/c.demand) * len(c.enemies))

        self._state.global_tension = max(0.0, self._state.global_tension - 0.02)
        self._state.time_step += 1
        done = self._state.time_step >= self._state.max_steps or self._state.global_tension >= 1.0
        
        # Reward Calculation
        avg_stab = sum(c.stability for c in self._state.countries) / len(self._state.countries)
        reward = avg_stab - (0.7 * (self._state.global_tension ** 2))
        
        # Strategic Delay Bonus
        total_unmet = sum(max(0, c.demand - c.received) for c in self._state.countries)
        if action.type == "no_op" and self._state.global_tension < prev_tension and total_unmet > 0 and self._state.global_tension > 0.6:
            reward += 0.05
        
        if done and self._state.global_tension < 1.0: reward += 0.3
        if not valid: reward -= 0.1
        
        return self._state.model_dump(), max(-1.0, min(2.0, reward)), done

# --- TASK FACTORY ---

def make_hard_env():
    countries = [
        CountryState(id="ares", demand=70, stability=0.4, enemies=["hera"], refinery_capacity=0.3),
        CountryState(id="zeus", demand=60, stability=0.3, enemies=["athena"], refinery_capacity=0.7),
        CountryState(id="hera", demand=65, stability=0.35, enemies=["ares"], refinery_capacity=0.2)
    ]
    return GeoAllocEnv(EnvState(available_oil=160, global_tension=0.3, countries=countries))

# --- [RL] GRPO TRAINING ---

def train():
    if torch.cuda.is_available() and torch.cuda.get_device_capability()[0] < 7:
        print("CRITICAL: Incompatible GPU. Switch to T4 x2.")
        return

    MODEL_NAME = "unsloth/llama-3-8b-bnb-4bit"
    print(f"Loading {MODEL_NAME}...")
    model, tokenizer = FastLanguageModel.from_pretrained(model_name=MODEL_NAME, max_seq_length=1024, load_in_4bit=True, trust_remote_code=True)
    model = FastLanguageModel.get_peft_model(model, r=16, target_modules=["q_proj", "k_proj", "v_proj", "o_proj"], lora_alpha=16, use_gradient_checkpointing="unsloth")

    def reward_fn(completions, prompts, **kwargs):
        rewards = []

        for c, p in zip(completions, prompts):
            r = 0.0

            try:
                json_part = c.split("}")[-2] + "}"
                action = json.loads(json_part)

                # --- match with dataset ---
                target = p.get("action", None) if isinstance(p, dict) else kwargs.get("action", [None]*len(completions))[0] # Fallback just in case

                if target:
                    if action["type"] == target["type"]:
                        r += 0.2
                    if action.get("country_id") == target.get("country_id"):
                        r += 0.2

                r += 0.2  # valid JSON bonus

            except:
                rewards.append(-0.1)
                continue

            rewards.append(r)

        return rewards

    DATA_PATH = "/kaggle/input/datasets/ravindraog/traindataset/training_observations.json"
    local_data_path = "training_observations.json"
    if os.path.exists(DATA_PATH):
        with open(DATA_PATH, "r") as f:
            data = json.load(f)
    elif os.path.exists(local_data_path):
        with open(local_data_path, "r") as f:
            data = json.load(f)
    else:
        # Fallback to local sibling
        sibling_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "geoalloc-env", "training_observations.json")
        if os.path.exists(sibling_path):
            with open(sibling_path, "r") as f:
                data = json.load(f)
        else:
            data = [make_hard_env().reset().model_dump()]
            
    prompts = []
    for x in data[:100]:
        target_action = x.get("action", None)
        obs = {k: v for k, v in x.items() if k != "action"}
        prompt_text = f"""
Observation:
{json.dumps(obs)}

Give action in JSON:
{{"type": "...", "country_id": "...", "amount": ...}}
"""
        prompts.append({"prompt": prompt_text, "action": target_action})

    trainer = GRPOTrainer(
        model=model, reward_funcs=[reward_fn],
        args=GRPOConfig(
            output_dir="./geoalloc_model", 
            learning_rate=2e-5, 
            per_device_train_batch_size=1, 
            gradient_accumulation_steps=4, 
            num_train_epochs=1, 
            num_generations=4, 
            max_completion_length=512, 
            report_to="none"
        ),
        train_dataset=Dataset.from_list(prompts)
    )

    print("Executing GRPO Training...")
    trainer.train()
    model.save_pretrained("./geoalloc_final")
    print("Training Complete.")

if __name__ == "__main__":
    train()
