import os
import torch
import json
from tqdm import tqdm
from trl import GRPOTrainer, GRPOConfig
from transformers import AutoTokenizer
from unsloth import FastLanguageModel, PatchFastRL
from datasets import Dataset

# Project Imports
from env.env import GeoAllocEnv
from env.models import Action, EnvState, CountryState
from env.tasks.hard import make_hard_env

# Apply Unsloth's Patch for RL
PatchFastRL("GRPO", FastLanguageModel)

# 1. Configuration
MODEL_NAME = "unsloth/llama-3-8b-bnb-4bit"
MAX_SEQ_LENGTH = 1024 # Increased for reasoning traces
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
OUTPUT_DIR = "./geoalloc_agent_grpo"

# 2. Load Model & Tokenizer with Unsloth
model, tokenizer = FastLanguageModel.from_pretrained(
    model_name=MODEL_NAME,
    max_seq_length=MAX_SEQ_LENGTH,
    load_in_4bit=True,
    fast_inference=True,
)

# Unsloth Training Configuration
model = FastLanguageModel.get_peft_model(
    model,
    r=16,
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
    lora_alpha=16,
    lora_dropout=0,
    bias="none",
    use_gradient_checkpointing="unsloth",
    random_state=42,
)

# 3. Prompt Template (Updated for Reasoning)
SYSTEM_PROMPT = """
You are a Geopolitical Resource Allocator. 
Objective: Sustain global stability while managing limited oil.
Respond with your reasoning inside <thought> tags, then provide the JSON Action.

STRATEGIC DIRECTIVE:
1. When global_tension is high (>0.6), use "no_op" to trigger geopolitical cooling.
2. Meet demand only when tension is manageable.
3. You receive a bonus for necessary "no_op" delays.

Action Format:
<thought>
Reasoning about current state and tension...
</thought>
{"type": "allocate", "country_id": "ID", "amount": X} 
OR
{"type": "no_op"}
"""

# 4. GRPO Reward Functions
def reward_env_step(completions, **kwargs):
    """
    Reward based on environment feedback for the action.
    """
    rewards = []
    # This expects a single step environment interaction
    # In a real GRPO loop for long-horizon, we might run full trajectories
    for completion in completions:
        try:
            # Extract JSON from completion
            json_str = completion.split("</thought>")[-1].strip()
            action_dict = json.loads(json_str)
            action = Action(**action_dict)
            
            # Create temporary env for evaluation
            # (In production, you'd pass the specific env state via kwargs)
            env = make_hard_env() 
            result = env.step(action)
            rewards.append(result.reward)
        except Exception:
            rewards.append(-0.5) # Penalty for invalid format or logic
    return rewards

def reward_reasoning_format(completions, **kwargs):
    """
    Reward for using the <thought> tags correctly.
    """
    rewards = []
    for completion in completions:
        if "<thought>" in completion and "</thought>" in completion:
            rewards.append(0.2)
        else:
            rewards.append(0.0)
    return rewards

# 5. Dataset Preparation
def prepare_dataset():
    obs_path = os.path.join(os.path.dirname(__file__), "training_observations.json")
    if not os.path.exists(obs_path):
        print("Warning: training_observations.json not found. Using default reset state.")
        raw_states = [make_hard_env().reset().model_dump()]
    else:
        with open(obs_path, "r") as f:
            raw_states = json.load(f)
    
    print(f"Loaded {len(raw_states)} states for training.")
    
    prompts = []
    for state in raw_states:
        # Create a prompt for each unique state
        prompt = f"{SYSTEM_PROMPT}\nObservation: {json.dumps(state)}\nAction:"
        prompts.append({"prompt": prompt})
        
    return Dataset.from_list(prompts)

# 6. Training Setup
def train():
    dataset = prepare_dataset()

    training_args = GRPOConfig(
        output_dir=OUTPUT_DIR,
        learning_rate=1e-5,
        per_device_train_batch_size=1,
        gradient_accumulation_steps=8,
        num_train_epochs=1,
        max_prompt_length=768,
        max_completion_length=512,
        num_generations=4, # Number of trajectories per prompt
        report_to="none", # Set to "wandb" if you have an account
        logging_steps=1,
    )

    trainer = GRPOTrainer(
        model=model,
        reward_funcs=[reward_env_step, reward_reasoning_format],
        args=training_args,
        train_dataset=dataset,
    )

    print("Starting Round 2 Training: GRPO Strategic Delay Loop...")
    trainer.train()

    # Save the fine-tuned adapter
    model.save_pretrained(OUTPUT_DIR)
    tokenizer.save_pretrained(OUTPUT_DIR)
    print(f"Training Complete. Model saved to {OUTPUT_DIR}")

if __name__ == "__main__":
    if DEVICE == "cpu":
        print("WARNING: GPU not found. Unsloth/GRPO requires a GPU.")
    
    train()
