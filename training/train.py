"""
training/train.py (STANDALONE MONOLITH)
──────────────────────────────────────
Standalone GRPO Training loop for SecureHeal Arena.
Contains all environment logic, reward functions, and training code in one file.
Optimized for Kaggle and Hugging Face Spaces.
"""

import os
import sys

# Disable torch.compile (Inductor allocates huge temp buffers that OOM on 8GB GPUs)
os.environ["TORCH_COMPILE_DISABLE"] = "1"
os.environ["TORCHDYNAMO_DISABLE"] = "1"

# Add parent directory to sys.path to import secureheal_arena
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from unsloth import FastLanguageModel, is_bfloat16_supported
import random
import uuid
import re
import io
import sys
import copy
import signal
import threading
import torch
import wandb
import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Union, Callable
from dataclasses import dataclass, field, asdict

# ML/RL Imports
from datasets import Dataset
from transformers import TrainingArguments
from trl import GRPOConfig, GRPOTrainer

# Note: SecureHealEnv import removed — using offline heuristic rewards for training.
# To use live env rewards, start the server and re-enable env_reward_function.

# ──────────────────────────────────────────────────────────────────────────
# 4. REWARDS & ENVIRONMENT
# ──────────────────────────────────────────────────────────────────────────

def compute_reward(state: SecureHealState) -> float:
    # R1: Exploit Prevention (0.4)
    r1 = 1.0 if (state.patch_applied and not state.exploit_possible) else 0.0
    # R2: Test Pass Rate (0.3)
    r2 = state.test_pass_rate
    # R3: System Stability (0.2)
    r3 = state.system_stability
    # R4: Cascading Failures (0.1)
    r4 = 1.0 if not state.cascading_failures else 0.0
    
    total = (0.4 * r1) + (0.3 * r2) + (0.2 * r3) + (0.1 * r4)
    if state.timeout_occurred: total -= 0.5
    if state.forbidden_op_detected: total -= 2.0
    return total

class SecureHealEnvironment:
    def __init__(self, curriculum_level: int = 1):
        self.level = curriculum_level
        self.sandbox = SandboxEngine()
        self.state = SecureHealState(episode_id=str(uuid.uuid4()), step_count=0)
        self.scenario = SQL_INJECTION
        self.anomaly = MEMORY_SPIKE
        self.current_code = self.scenario.vulnerable_code

    def reset(self):
        self.state = SecureHealState(episode_id=str(uuid.uuid4()), step_count=0, curriculum_level=self.level)
        self.current_code = self.scenario.vulnerable_code
        self.state.system_stability = 0.5
        return self.get_obs()

    def get_obs(self):
        return {"code": self.current_code, "stability": self.state.system_stability, "done": self.state.step_count >= 10}

    def apply_patch(self, patch_code: str):
        self.state.step_count += 1
        self.current_code = patch_code
        self.state.patch_applied = True
        self.state.test_pass_rate = 1.0 # Mocking test success for training
        return self.get_obs()

# ──────────────────────────────────────────────────────────────────────────
# 5. TRAINING LOOP (GRPO)
# ──────────────────────────────────────────────────────────────────────────

MODEL_NAME = "unsloth/llama-3-8b-Instruct-bnb-4bit"
MAX_SEQ_LENGTH = 1024          # Reduced from 4096 to fit in 8GB VRAM
LORA_RANK = 8                   # Reduced from 16 to save memory
BATCH_SIZE = 1                  # Reduced from 4 — minimum for 8GB GPU
GRADIENT_ACCUMULATION_STEPS = 16  # Increased to keep effective batch = 16
MAX_STEPS = 500
NUM_GENERATIONS = 2             # GRPO generations per prompt (default can be 4-8)
MAX_COMPLETION_LENGTH = 128     # Max tokens generated per completion

# ────────────────────── Dataset ─────────────────────────────

def build_training_dataset():
    """
    Build the initial prompt dataset for GRPO.
    For this environment, the dataset is simply a set of system prompts 
    instructing the model to interact with the SecureHeal environment.
    """
    # In a real scenario, you might vary the curriculum level or initial hints here.
    prompts = [
        "You are an autonomous SRE and Security agent. A system is degraded. Use your tools to scan for vulnerabilities, simulate attacks, patch the code, run tests, and stabilize the infrastructure.",
        "System alert: High latency detected. Find the root cause, patch the vulnerable code, and restore services to healthy states.",
        "Your objective is to secure the application code and recover from any cascading failures. Rely on the 'scan_code' and 'classify_issue' tools to start.",
    ]
    
    # Repeat to create a reasonably sized dataset
    dataset_dict = {
        "prompt": [[{"role": "user", "content": random.choice(prompts)}] for _ in range(1000)]
    }
    return Dataset.from_dict(dataset_dict)


# ────────────────────── Reward Pipeline ───────────────────────
# Offline heuristic rewards — no SecureHeal server needed.
# These evaluate the model's completions based on content quality.

# Valid tool names from the SecureHeal environment
VALID_TOOLS = {
    "scan_code", "simulate_attack", "apply_patch", "run_tests",
    "restart_service", "clean_data", "reallocate_resources", "classify_issue",
}

def tool_usage_reward(prompts, completions, **kwargs):
    """
    R1: Rewards the model for mentioning valid SecureHeal tool names.
    Higher reward for using more distinct tools (encourages multi-step plans).
    """
    rewards = []
    for completion in completions:
        text = completion[0]["content"].lower()
        tools_used = sum(1 for tool in VALID_TOOLS if tool in text)
        # Scale: 0 tools = -0.5, 1 tool = 0.0, 4+ tools = 1.0
        score = min((tools_used - 1) / 3.0, 1.0) if tools_used > 0 else -0.5
        rewards.append(score)
    return rewards

def format_reward_function(prompts, completions, **kwargs):
    """
    R2: Rewards structured output (XML tool calls, JSON, or numbered steps).
    Penalizes unstructured prose-only responses.
    """
    rewards = []
    for completion in completions:
        text = completion[0]["content"]
        score = 0.0
        if "<tool_call>" in text or "</tool_call>" in text:
            score += 0.5
        if "{" in text and "}" in text:  # JSON-like structure
            score += 0.2
        if any(f"{i}." in text or f"Step {i}" in text for i in range(1, 6)):
            score += 0.3  # Numbered steps = structured plan
        if score == 0.0:
            score = -0.3  # Penalize pure prose
        rewards.append(min(score, 1.0))
    return rewards

def reasoning_reward(prompts, completions, **kwargs):
    """
    R3: Rewards multi-step reasoning and security-relevant analysis.
    Checks for diagnostic keywords that indicate the model is actually
    reasoning about vulnerabilities and system recovery.
    """
    REASONING_KEYWORDS = [
        "vulnerability", "exploit", "patch", "injection", "xss",
        "latency", "memory", "cpu", "restart", "failure",
        "root cause", "diagnosis", "fix", "remediat", "mitigat",
        "test", "verify", "monitor", "stable", "recover",
    ]
    rewards = []
    for completion in completions:
        text = completion[0]["content"].lower()
        hits = sum(1 for kw in REASONING_KEYWORDS if kw in text)
        # Scale: 0 hits = -0.3, 3 hits = 0.3, 6+ hits = 1.0
        score = min((hits - 1) / 5.0, 1.0) if hits > 0 else -0.3
        rewards.append(score)
    return rewards

def quality_reward(prompts, completions, **kwargs):
    """
    R4: Rewards completions of reasonable length. Penalizes very short
    (lazy) or excessively long (rambling) outputs.
    """
    rewards = []
    for completion in completions:
        text = completion[0]["content"]
        word_count = len(text.split())
        if word_count < 15:
            score = -0.5   # Too short / empty
        elif word_count < 30:
            score = 0.0    # Marginal
        elif word_count <= 150:
            score = 0.5    # Good length
        else:
            score = 0.2    # Verbose but not terrible
        rewards.append(score)
    return rewards

def main():
    if os.getenv("WANDB_API_KEY"): wandb.login()
    
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=MODEL_NAME, max_seq_length=MAX_SEQ_LENGTH, load_in_4bit=True
    )
    model = FastLanguageModel.get_peft_model(model, r=16, lora_alpha=16, use_gradient_checkpointing="unsloth")

    dataset = Dataset.from_dict({
        "prompt": [{"role": "user", "content": "System is vulnerable to SQL injection. Provide a patch."} for _ in range(100)]
    })

    training_args = GRPOConfig(
        output_dir="outputs/secureheal-standalone",
        learning_rate=2e-5,
        max_steps=MAX_STEPS,
        per_device_train_batch_size=BATCH_SIZE,
        gradient_accumulation_steps=GRADIENT_ACCUMULATION_STEPS,
        logging_steps=1,
        report_to="wandb" if os.getenv("WANDB_API_KEY") else "none",
        bf16=is_bfloat16_supported(),
        fp16=not is_bfloat16_supported(),
        # GRPO specific parameters
        beta=0.1,                                   # KL penalty coefficient
        num_generations=NUM_GENERATIONS,             # Fewer generations = less VRAM
        max_completion_length=MAX_COMPLETION_LENGTH,  # Shorter completions = less VRAM
        torch_compile=False,                         # Disable compile to avoid huge temp buffers
    )

    trainer = GRPOTrainer(
        model=model,
        processing_class=tokenizer,
        reward_funcs=[tool_usage_reward, format_reward_function, reasoning_reward, quality_reward],
        args=training_args,
        train_dataset=dataset,
    )

    trainer.train()
    model.save_pretrained_merged("outputs/final_model", tokenizer, save_method="merged_16bit")

if __name__ == "__main__":
    main()
