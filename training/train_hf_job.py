"""
training/train_hf_job.py
────────────────────────
GRPO training for SecureHeal Agent — A100 80GB with early stopping + auto-save.
"""

import os
import random
import torch
from datasets import Dataset
from unsloth import FastLanguageModel
from trl import GRPOConfig, GRPOTrainer
from transformers import TrainerCallback

# ────────────────────── Config (A100 80GB) ──────────────────────

MODEL_NAME = "unsloth/llama-3-8b-Instruct-bnb-4bit"
MAX_SEQ_LENGTH = 2048
LORA_RANK = 32
BATCH_SIZE = 8
GRADIENT_ACCUMULATION_STEPS = 2
MAX_STEPS = 200                 # Fits within 2h on A100
NUM_GENERATIONS = 8
MAX_COMPLETION_LENGTH = 512
SAVE_TO_HUB = True
HUB_MODEL_ID = os.environ.get("HF_MODEL_ID", "Nitesh-Reddy/secureheal-agent-v2")

# Early stopping config
EARLY_STOP_PATIENCE = 50        # Stop if no reward improvement for 50 steps
EARLY_STOP_MIN_REWARD = 4.0     # Only start checking after reaching this reward
SAVE_BEST_EVERY = 50            # Check and save best model every 50 steps


# ────────────────────── Early Stopping + Best Model Callback ────

class BestModelCallback(TrainerCallback):
    """
    Tracks reward during training:
    - Saves model to Hub whenever reward improves
    - Stops training early if reward plateaus
    """
    def __init__(self, model, tokenizer, patience=50, min_reward=4.0):
        self.model = model
        self.tokenizer = tokenizer
        self.best_reward = -float("inf")
        self.best_step = 0
        self.patience = patience
        self.min_reward = min_reward
        self.saves = 0

    def on_log(self, args, state, control, logs=None, **kwargs):
        if logs is None:
            return

        reward = logs.get("reward")
        if reward is None:
            return

        step = state.global_step
        print(f"\n📊 Step {step}: reward={reward:.3f} (best={self.best_reward:.3f} at step {self.best_step})")

        # Save if reward improved
        if reward > self.best_reward:
            self.best_reward = reward
            self.best_step = step
            self.saves += 1

            # Save to Hub every improvement (but not too frequently)
            if step >= 20 and (self.saves <= 3 or step % SAVE_BEST_EVERY == 0 or reward > self.min_reward):
                self._save_to_hub(step, reward)

        # Early stopping: if we've reached a good reward and haven't improved
        elif reward >= self.min_reward and (step - self.best_step) >= self.patience:
            print(f"\n🛑 EARLY STOPPING at step {step}!")
            print(f"   Best reward {self.best_reward:.3f} was at step {self.best_step}")
            print(f"   No improvement for {step - self.best_step} steps")
            self._save_to_hub(step, reward, tag="final")
            control.should_training_stop = True

    def _save_to_hub(self, step, reward, tag="best"):
        hf_token = os.environ.get("HF_TOKEN")
        if not hf_token:
            print("⚠️ No HF_TOKEN, skipping Hub push")
            return

        print(f"\n💾 Saving {tag} model (step {step}, reward {reward:.3f}) to Hub...")
        try:
            self.model.push_to_hub_merged(
                HUB_MODEL_ID,
                self.tokenizer,
                save_method="merged_16bit",
                token=hf_token,
                commit_message=f"{tag}: step={step} reward={reward:.3f}",
            )
            print(f"✅ Model pushed to https://huggingface.co/{HUB_MODEL_ID}")
        except Exception as e:
            print(f"⚠️ Hub push failed: {e}")


# ────────────────────── Dataset ─────────────────────────────

def build_training_dataset():
    prompts = [
        "You are an autonomous SRE and Security agent. A system is degraded. "
        "Use tools like scan_code, simulate_attack, apply_patch, run_tests, "
        "restart_service, clean_data, reallocate_resources, and classify_issue. "
        "Output each action as <tool_call>tool_name({\"param\": \"value\"})</tool_call>. "
        "End with DONE when finished.",

        "System alert: High latency detected. Diagnose and fix the issue. "
        "Available tools: scan_code, classify_issue, restart_service, reallocate_resources, run_tests. "
        "Format: <tool_call>tool_name({\"param\": \"value\"})</tool_call>. Say DONE when complete.",

        "A SQL injection vulnerability has been detected in the auth module. "
        "Step 1: scan_code to find it. Step 2: simulate_attack to confirm. "
        "Step 3: apply_patch to fix. Step 4: run_tests to verify. "
        "Use <tool_call>...</tool_call> format. End with DONE.",

        "Memory usage is spiking. Use classify_issue to diagnose, clean_data to clear corruption, "
        "reallocate_resources to rebalance, and restart_service if needed. "
        "Format each action as <tool_call>tool_name({\"arg\": \"val\"})</tool_call>. Finish with DONE.",

        "Multiple cascading failures detected. Triage with classify_issue, "
        "then systematically restart_service and reallocate_resources. "
        "Output: <tool_call>classify_issue({\"target\": \"all\"})</tool_call> then DONE.",

        "XSS vulnerability reported. Scan with scan_code, confirm with simulate_attack, "
        "fix with apply_patch, verify with run_tests. "
        "Use <tool_call>tool({\"key\": \"val\"})</tool_call> format. End with DONE when stable.",

        "Database connection pool exhausted. Clean stale connections with clean_data, "
        "reallocate_resources to the DB tier, restart_service if needed. "
        "Format: <tool_call>tool_name({...})</tool_call>. Say DONE at the end.",

        "A command injection vulnerability was found in the API gateway. "
        "Use scan_code to locate, simulate_attack to test, apply_patch to fix, run_tests to verify. "
        "Output structured tool calls and finish with DONE.",
    ]

    dataset_dict = {
        "prompt": [[{"role": "user", "content": random.choice(prompts)}] for _ in range(500)]
    }
    return Dataset.from_dict(dataset_dict)


# ────────────────────── Reward Pipeline ───────────────────────

VALID_TOOLS = {
    "scan_code", "simulate_attack", "apply_patch", "run_tests",
    "restart_service", "clean_data", "reallocate_resources", "classify_issue",
}

def tool_usage_reward(prompts, completions, **kwargs):
    rewards = []
    for completion in completions:
        text = completion[0]["content"].lower()
        tools_used = sum(1 for tool in VALID_TOOLS if tool in text)
        score = min(tools_used / 2.0, 1.0) if tools_used > 0 else -0.2
        if "<tool_call>" in text:
            wrapped_tools = sum(1 for tool in VALID_TOOLS
                                if f"<tool_call>{tool}" in text or f"<tool_call> {tool}" in text)
            score += min(wrapped_tools * 0.3, 0.5)
        rewards.append(min(score, 1.5))
    return rewards

def format_reward_function(prompts, completions, **kwargs):
    rewards = []
    for completion in completions:
        text = completion[0]["content"]
        score = 0.0
        if "<tool_call>" in text and "</tool_call>" in text:
            score += 0.6
        elif "<tool_call>" in text or "</tool_call>" in text:
            score += 0.3
        if "{" in text and "}" in text:
            score += 0.2
        stripped = text.rstrip()
        if "DONE" in text.upper() or stripped.endswith("</tool_call>"):
            score += 0.5
        word_count = len(text.split())
        if word_count > 350:
            score -= 0.4
        if score == 0.0:
            score = -0.2
        rewards.append(max(min(score, 1.5), -1.0))
    return rewards

def reasoning_reward(prompts, completions, **kwargs):
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
        score = min((hits - 1) / 5.0, 1.0) if hits > 0 else -0.3
        rewards.append(score)
    return rewards

def quality_reward(prompts, completions, **kwargs):
    rewards = []
    for completion in completions:
        text = completion[0]["content"]
        word_count = len(text.split())
        stripped = text.rstrip()
        terminated = ("DONE" in text.upper() or
                      stripped.endswith("</tool_call>") or
                      stripped.endswith("."))
        if word_count < 15:
            score = -0.5
        elif word_count < 30:
            score = 0.0
        elif word_count <= 200 and terminated:
            score = 0.8
        elif word_count <= 200:
            score = 0.3
        elif word_count <= 350:
            score = 0.0
        else:
            score = -0.5
        rewards.append(score)
    return rewards


# ────────────────────── Main Training Loop ─────────────────────

def main():
    print("=" * 60)
    print("SecureHeal Agent — GRPO Training (A100 + Early Stopping)")
    print("=" * 60)

    print(f"\nConfig: batch={BATCH_SIZE}, grad_accum={GRADIENT_ACCUMULATION_STEPS}, "
          f"num_gen={NUM_GENERATIONS}, max_completion={MAX_COMPLETION_LENGTH}")
    print(f"Early stopping: patience={EARLY_STOP_PATIENCE}, min_reward={EARLY_STOP_MIN_REWARD}")

    print("\nInitializing model...")
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=MODEL_NAME,
        max_seq_length=MAX_SEQ_LENGTH,
        dtype=torch.float16,
        load_in_4bit=True,
    )

    model = FastLanguageModel.get_peft_model(
        model,
        r=LORA_RANK,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
        lora_alpha=LORA_RANK,
        lora_dropout=0,
        bias="none",
        use_gradient_checkpointing="unsloth",
    )

    print("Building dataset...")
    dataset = build_training_dataset()

    print("Configuring GRPO Trainer...")
    training_args = GRPOConfig(
        output_dir="outputs/secureheal-agent-v1",
        learning_rate=1e-5,
        lr_scheduler_type="cosine",
        max_steps=MAX_STEPS,
        per_device_train_batch_size=BATCH_SIZE,
        gradient_accumulation_steps=GRADIENT_ACCUMULATION_STEPS,
        weight_decay=0.01,
        warmup_steps=30,
        logging_steps=10,
        save_steps=50,
        bf16=False,
        fp16=True,
        # GRPO
        beta=0.01,
        num_generations=NUM_GENERATIONS,
        max_completion_length=MAX_COMPLETION_LENGTH,
        report_to="none",
    )

    # Create early stopping + best model callback
    best_model_cb = BestModelCallback(
        model=model,
        tokenizer=tokenizer,
        patience=EARLY_STOP_PATIENCE,
        min_reward=EARLY_STOP_MIN_REWARD,
    )

    trainer = GRPOTrainer(
        model=model,
        processing_class=tokenizer,
        reward_funcs=[tool_usage_reward, format_reward_function, reasoning_reward, quality_reward],
        args=training_args,
        train_dataset=dataset,
        callbacks=[best_model_cb],
    )

    print("\nStarting GRPO training with early stopping...")
    trainer.train()

    # Final save (in case early stopping didn't trigger)
    print("\nFinal save...")
    hf_token = os.environ.get("HF_TOKEN")
    if SAVE_TO_HUB and hf_token:
        print(f"Pushing final model to {HUB_MODEL_ID}...")
        model.push_to_hub_merged(
            HUB_MODEL_ID,
            tokenizer,
            save_method="merged_16bit",
            token=hf_token,
            commit_message=f"final: step={trainer.state.global_step} best_reward={best_model_cb.best_reward:.3f}",
        )
        print(f"✅ Model at https://huggingface.co/{HUB_MODEL_ID}")

    print(f"\n{'=' * 60}")
    print(f"Training complete! Best reward: {best_model_cb.best_reward:.3f} at step {best_model_cb.best_step}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
