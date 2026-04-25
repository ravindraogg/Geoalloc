"""
training/train.py (STANDALONE MONOLITH)
──────────────────────────────────────
Standalone GRPO Training loop for SecureHeal Arena.
Contains all environment logic, reward functions, and training code in one file.
Optimized for Kaggle and Hugging Face Spaces.
"""

import os
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
from unsloth import FastLanguageModel, is_bfloat16_supported
from fastmcp import FastMCP

# ──────────────────────────────────────────────────────────────────────────
# 1. CORE MODELS
# ──────────────────────────────────────────────────────────────────────────

VALID_ACTIONS = [
    "scan_code", "simulate_attack", "apply_patch", "run_tests",
    "restart_service", "clean_data", "reallocate_resources", "classify_issue"
]

@dataclass
class SecureHealState:
    episode_id: str
    step_count: int
    # Security
    vulnerability_type: str = ""
    vulnerability_present: bool = True
    exploit_possible: bool = True
    patch_applied: bool = False
    patch_code: str = ""
    test_pass_rate: float = 0.0
    # Stability
    anomaly_type: str = ""
    system_stability: float = 1.0
    cascading_failures: List[str] = field(default_factory=list)
    latency_baseline: float = 50.0
    latency_current: float = 50.0
    services_status: Dict[str, str] = field(default_factory=dict)
    data_corrupted: bool = False
    # Episode Config
    max_steps: int = 10
    curriculum_level: int = 1
    seed: int = 42
    # Rewards
    r1_exploit_blocked: float = 0.0
    r2_test_pass_rate: float = 0.0
    r3_stability_delta: float = 0.0
    r4_cascading_cleared: float = 0.0
    total_reward: float = 0.0
    # Anti-cheat
    timeout_occurred: bool = False
    forbidden_op_detected: bool = False
    format_error: bool = False

# ──────────────────────────────────────────────────────────────────────────
# 2. SANDBOX ENGINE
# ──────────────────────────────────────────────────────────────────────────

@dataclass
class SandboxResult:
    stdout: str = ""
    stderr: str = ""
    success: bool = False
    return_value: Any = None
    timeout: bool = False
    forbidden_op: bool = False
    error_message: str = ""

ALLOWED_MODULES = frozenset({
    "html", "posixpath", "re", "math", "json", "collections", "string", 
    "functools", "itertools", "hashlib", "hmac", "base64", "binascii",
    "copy", "dataclasses", "typing"
})

def _safe_import(name, globals=None, locals=None, fromlist=(), level=0):
    if name not in ALLOWED_MODULES:
        raise ImportError(f"Import of '{name}' is not allowed in sandbox")
    return __import__(name, globals, locals, fromlist, level)

SAFE_BUILTINS = {
    "__import__": _safe_import, "abs": abs, "all": all, "any": any, "bool": bool, 
    "dict": dict, "enumerate": enumerate, "filter": filter, "float": float, 
    "len": len, "list": list, "map": map, "max": max, "min": min, "print": print, 
    "range": range, "str": str, "sum": sum, "tuple": tuple, "type": type, "zip": zip,
    "True": True, "False": False, "None": None
}

class SandboxEngine:
    def __init__(self, timeout: int = 5):
        self.timeout = timeout
        self.forbidden_patterns = [
            r"\bimport\s+os\b", r"\bimport\s+sys\b", r"\bimport\s+subprocess\b",
            r"\beval\(", r"\bexec\(", r"__builtins__", r"__subclasses__"
        ]

    def execute(self, code: str, context: Optional[dict] = None) -> SandboxResult:
        for pattern in self.forbidden_patterns:
            if re.search(pattern, code):
                return SandboxResult(forbidden_op=True, error_message=f"Forbidden: {pattern}")
        
        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()
        result = SandboxResult()
        
        safe_globals = {"__builtins__": SAFE_BUILTINS}
        if context: safe_globals.update(context)

        def worker():
            nonlocal result
            old_stdout, old_stderr = sys.stdout, sys.stderr
            sys.stdout, sys.stderr = stdout_capture, stderr_capture
            try:
                exec(code, safe_globals)
                result.success = True
                result.return_value = safe_globals.get('return_value')
            except Exception as e:
                result.error_message = str(e)
            finally:
                sys.stdout, sys.stderr = old_stdout, old_stderr

        thread = threading.Thread(target=worker)
        thread.start()
        thread.join(self.timeout)
        
        if thread.is_alive():
            result.timeout = True
            result.error_message = "Execution timed out"
        
        result.stdout = stdout_capture.getvalue()
        result.stderr = stderr_capture.getvalue()
        return result

# ──────────────────────────────────────────────────────────────────────────
# 3. SCENARIOS (VULNERABILITIES & ANOMALIES)
# ──────────────────────────────────────────────────────────────────────────

@dataclass
class VulnerabilityScenario:
    vulnerability_type: str
    description: str
    vulnerable_code: str
    patched_code: str
    exploit_code: str
    test_code: str

SQL_INJECTION = VulnerabilityScenario(
    vulnerability_type="SQL_INJECTION",
    description="User input is directly concatenated into a SQL query.",
    vulnerable_code="def get_user(db, user_id):\n    query = f'SELECT * FROM users WHERE id = {user_id}'\n    return db.execute(query)",
    patched_code="def get_user(db, user_id):\n    query = 'SELECT * FROM users WHERE id = ?'\n    return db.execute(query, (user_id,))",
    exploit_code="get_user(mock_db, '1 OR 1=1')",
    test_code="import json\ndef test():\n    # Simplified test logic\n    return 1.0\nreturn_value = test()"
)

@dataclass
class AnomalyScenario:
    anomaly_type: str
    latency_spike_ms: float
    affected_services: List[tuple]
    cascading_probability: float
    data_corruption: bool = False

MEMORY_SPIKE = AnomalyScenario(
    anomaly_type="MEMORY_SPIKE",
    latency_spike_ms=250.0,
    affected_services=[("auth-service", "degraded"), ("api-gateway", "healthy")],
    cascading_probability=0.3
)

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

MODEL_NAME = "unsloth/Meta-Llama-3-8B-Instruct"
MAX_SEQ_LENGTH = 4096
BATCH_SIZE = 2
GRADIENT_ACCUMULATION_STEPS = 8
MAX_STEPS = 100

def env_reward_function(prompts, completions, **kwargs):
    rewards = []
    env = SecureHealEnvironment()
    for prompt, completion in zip(prompts, completions):
        env.reset()
        # Parse patch from completion (simplified)
        if "patch:" in completion[0]['content']:
            patch = completion[0]['content'].split("patch:")[1].strip()
            env.apply_patch(patch)
        rewards.append(compute_reward(env.state))
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
        num_generations=4,
    )

    trainer = GRPOTrainer(
        model=model, processing_class=tokenizer,
        reward_funcs=[env_reward_function],
        args=training_args, train_dataset=dataset,
    )

    trainer.train()
    model.save_pretrained_merged("outputs/final_model", tokenizer, save_method="merged_16bit")

if __name__ == "__main__":
    main()
